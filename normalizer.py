"""Local, deterministic ingredient recognition for Hindi / English / Hinglish free text.

Pipeline for each comma-separated token:
  1. exact alias match (English, Hindi script, Hinglish spellings)
  2. exact *phonetic* match (e.g. "pyaaj" and "pyaj" share a key)
  3. fuzzy match with difflib on both raw and phonetic forms
       - high score with a clear margin  -> auto-corrected ("fuzzy")
       - medium score or several close candidates, or an alias shared by
         several ingredients (e.g. "dal") -> "confirm": the user must choose
       - otherwise                       -> "unknown"
No network access and no AI services are involved.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ingredient_catalog import CATALOG

AUTO_THRESHOLD = 0.80      # minimum similarity to silently auto-correct
CONFIRM_THRESHOLD = 0.60   # minimum similarity to offer as a suggestion
AUTO_MARGIN = 0.08         # best must beat the runner-up (other ingredient) by this much
MIN_AUTO_LENGTH = 5        # very short words are never auto-corrected

MATCHED, FUZZY, CONFIRM, UNKNOWN = "matched", "fuzzy", "confirm", "unknown"

_STOPWORDS = {"fresh", "chopped", "sliced", "diced", "of", "some", "the", "a", "my",
              "i", "have", "ka", "ki", "ke", "and", "aur", "with", "kg", "gm", "gram"}
_SPLIT_RE = re.compile(r"[,;\n|/+&]+|\band\b|\baur\b", re.IGNORECASE)


def normalize(text: str) -> str:
    """Lowercase, drop punctuation (keeping Devanagari), collapse whitespace."""
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\sऀ-ॿ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_PHONETIC_RULES = [
    ("chh", "ch"), ("bh", "b"), ("dh", "d"), ("gh", "g"), ("kh", "k"), ("th", "t"),
    ("ph", "f"), ("sh", "s"), ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"),
    ("uu", "u"), ("w", "v"), ("z", "j"), ("y", "i"),
]


def phonetic(text: str) -> str:
    """Rough phonetic key so spelling variants of the same sound collide."""
    for src, dst in _PHONETIC_RULES:
        text = text.replace(src, dst)
    return re.sub(r"(.)\1+", r"\1", text)  # collapse doubled letters


# --- Index construction -------------------------------------------------------------
@dataclass
class Index:
    alias_ids: dict     # normalised alias -> [ingredient ids]
    phon_ids: dict      # phonetic key -> [ingredient ids]
    entries: list       # (alias, phonetic alias, ingredient id) for fuzzy search


def build_index(extra=None) -> "Index":
    """Index over the built-in catalogue plus optional extra vocabulary.

    ``extra`` maps an ingredient id to ``(display_name, aliases)``; it is how ingredients
    that exist only in the recipe database become recognisable.
    """
    names_by_id = {ing.id: {ing.id.replace("_", " "), ing.en, ing.hi, *ing.aliases}
                   for ing in CATALOG.values()}
    for ing_id, (display, aliases) in (extra or {}).items():
        if ing_id not in names_by_id:
            names_by_id[ing_id] = {display, *aliases}
    alias_ids, phon_ids, entries = {}, {}, []
    for ing_id, names in names_by_id.items():
        for name in names:
            alias = normalize(name)
            if not alias:
                continue
            for table, key in ((alias_ids, alias), (phon_ids, phonetic(alias))):
                ids = table.setdefault(key, [])
                if ing_id not in ids:
                    ids.append(ing_id)
            entries.append((alias, phonetic(alias), ing_id))
    return Index(alias_ids, phon_ids, entries)


DEFAULT_INDEX = build_index()


def lookup_exact(text: str, index: "Index" = None):
    """Ingredient id only if ``text`` is an unambiguous exact alias (no fuzzy/phonetic guess)."""
    index = index or DEFAULT_INDEX
    token = normalize(text)
    for form in (token, token[:-1] if token.endswith("s") and len(token) > 3 else token):
        ids = index.alias_ids.get(form)
        if ids and len(ids) == 1:
            return ids[0]
    return None


@dataclass
class Detection:
    raw: str
    status: str
    ingredient_id: str = ""            # set for matched / fuzzy
    candidates: list = field(default_factory=list)  # set for confirm
    score: float = 1.0


@dataclass
class ParseResult:
    accepted: list = field(default_factory=list)      # unique ingredient ids, in input order
    corrections: list = field(default_factory=list)   # (raw, ingredient_id) auto-corrected
    pending: list = field(default_factory=list)       # Detections needing confirmation
    unknown: list = field(default_factory=list)       # raw tokens we could not recognise


MAX_AUTO_EDITS = 2   # auto-correct only typo-sized differences ("panor" -> "paneer")


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _score(token: str, token_phon: str, alias: str, alias_phon: str) -> float:
    return max(SequenceMatcher(None, token, alias).ratio(),
               SequenceMatcher(None, token_phon, alias_phon).ratio())


def recognize(raw: str, index: Index = None) -> Detection:
    """Classify a single ingredient word/phrase."""
    index = index or DEFAULT_INDEX
    token = normalize(raw)
    if not token:
        return Detection(raw, UNKNOWN, score=0.0)
    candidates_forms = [token]
    if token.endswith("s") and len(token) > 3:
        candidates_forms.append(token[:-1])
    token_phon = phonetic(token)

    for form in candidates_forms:  # 1. exact alias
        ids = index.alias_ids.get(form)
        if ids:
            return _exact(raw, ids)
    ids = index.phon_ids.get(token_phon)  # 2. exact phonetic
    if ids:
        return _exact(raw, ids)

    best, best_alias = {}, {}         # 3. fuzzy
    for alias, alias_phon, ing_id in index.entries:
        s = _score(token, token_phon, alias, alias_phon)
        if s > best.get(ing_id, 0.0):
            best[ing_id], best_alias[ing_id] = s, alias
    ranked = sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))
    top_id, top = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

    if len(token) < 4:
        auto_ok = False
        floor = 0.67
    else:
        auto_ok = (top >= AUTO_THRESHOLD and len(token) >= MIN_AUTO_LENGTH
                   and top - runner_up >= AUTO_MARGIN
                   and _edit_distance(token, best_alias[top_id]) <= MAX_AUTO_EDITS)
        floor = CONFIRM_THRESHOLD
    if auto_ok:
        return Detection(raw, FUZZY, ingredient_id=top_id, score=top)
    if top >= floor:
        close = [i for i, s in ranked[:3] if s >= floor and top - s <= 0.15]
        return Detection(raw, CONFIRM, candidates=close, score=top)
    return Detection(raw, UNKNOWN, score=top)


def _exact(raw: str, ids: list) -> Detection:
    if len(ids) == 1:
        return Detection(raw, MATCHED, ingredient_id=ids[0])
    return Detection(raw, CONFIRM, candidates=list(ids))  # ambiguous alias, e.g. "dal"


def _split(text: str) -> list:
    return [seg.strip() for seg in _SPLIT_RE.split(text) if seg.strip()]


def _detect_segment(segment: str, index: Index) -> list:
    """Whole phrase first ("green peas"); word by word ("onion tomato") if it is not a plausible
    single ingredient and every word is recognisable."""
    whole = recognize(segment, index)
    if " " not in normalize(segment) or whole.status == MATCHED or whole.score >= 0.75:
        return [whole]
    words = [w for w in normalize(segment).split() if w not in _STOPWORDS]
    parts = [recognize(w, index) for w in words]
    if parts and all(p.status != UNKNOWN for p in parts):
        return parts
    return [whole]


def parse_ingredients(text: str, index: Index = None) -> ParseResult:
    """Turn free text into accepted ingredient ids plus items needing attention."""
    result = ParseResult()
    seen_pending = set()
    for segment in _split(text or ""):
        for det in _detect_segment(segment, index or DEFAULT_INDEX):
            if det.status in (MATCHED, FUZZY):
                if det.ingredient_id not in result.accepted:        # duplicate prevention
                    result.accepted.append(det.ingredient_id)
                    if det.status == FUZZY:
                        result.corrections.append((det.raw.strip(), det.ingredient_id))
            elif det.status == CONFIRM:
                key = tuple(sorted(det.candidates))
                if key not in seen_pending:
                    seen_pending.add(key)
                    result.pending.append(det)
            elif det.raw.strip() not in result.unknown:
                result.unknown.append(det.raw.strip())
    return result
