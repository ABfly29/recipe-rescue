"""Parse free-text ingredient lines ("1-1/2 cups Rice - soaked") into structured rows.

Nothing is invented: quantities are kept as written (``quantity_text``) and only converted
to a number when that is unambiguous. The original line is always preserved by the caller.
"""
import re
from dataclasses import dataclass, field

from ingredient_catalog import CATALOG
from normalizer import lookup_exact, normalize

UNITS = {
    "cup", "cups", "tablespoon", "tablespoons", "tbsp", "teaspoon", "teaspoons", "tsp",
    "inch", "inches", "gram", "grams", "gm", "g", "kg", "kilogram", "ml", "litre", "litres",
    "liter", "liters", "l", "pinch", "pinches", "sprig", "sprigs", "bunch", "bunches",
    "clove", "cloves", "pod", "pods", "piece", "pieces", "slice", "slices", "handful",
    "stick", "sticks", "drop", "drops", "dash", "can", "cans", "packet", "packets",
    "glass", "glasses", "leaf", "leaves", "ounce", "ounces", "oz", "pound", "pounds", "lb",
    "cubes", "cube", "strand", "strands", "bulb", "bulbs", "pinches",
}

# Leading words that only describe an ingredient and may be dropped when looking it up.
DESCRIPTORS = {
    "red", "green", "yellow", "white", "baby", "desi", "small", "big", "large", "medium",
    "ripe", "raw", "fresh", "freshly", "finely", "sunflower", "olive", "vegetable", "refined",
    "groundnut", "sesame", "coconut", "organic", "boiled", "light", "extra", "virgin",
    "thick", "thin", "tender", "firm", "whole", "mixed", "good", "quality",
}

# Basic pantry items assumed available when "assume staples" is on (besides catalogue staples).
PANTRY_NAMES = {
    "water", "salt", "oil", "ghee", "sugar", "black pepper", "pepper", "peppercorns",
    "whole black peppercorns", "black peppercorns", "cardamom", "green cardamom", "cinnamon",
    "cinnamon stick", "cloves", "bay leaf", "bay leaves", "asafoetida", "hing", "curry leaves",
    "cumin", "cumin seeds", "mustard seeds", "turmeric powder", "turmeric", "red chilli powder",
    "chilli powder", "coriander powder", "garam masala", "garam masala powder", "kashmiri chilli powder",
    "chaat masala", "fenugreek seeds", "methi seeds", "fennel seeds", "saunf", "ginger", "garlic",
    "green chilli", "green chillies", "coriander leaves", "coriander", "kasuri methi", "sunflower oil",
    "vegetable oil", "cooking oil", "olive oil", "mustard oil", "rock salt", "sendha namak",
    "black salt", "ice", "ice cubes", "star anise", "nutmeg", "mace", "dry red chillies",
    "red chillies", "whole red chillies", "jaggery",
}

def _strip_descriptors(name: str) -> str:
    words = name.split()
    while len(words) > 1 and words[0] in DESCRIPTORS:
        words.pop(0)
    return " ".join(words)


_NUMBER = r"(?:\d+\s+\d+/\d+|\d+-\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
_QTY_RE = re.compile(rf"^\s*(?P<qty>{_NUMBER}(?:\s*(?:-|to)\s*{_NUMBER})?)\s+(?=\S)", re.I)
_UNICODE_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}
_PAREN_RE = re.compile(r"\(([^)]*)\)")


@dataclass
class ParsedIngredient:
    position: int
    original_text: str
    quantity_text: str = None
    quantity_value: float = None
    unit: str = None
    name_original: str = ""
    name_normalized: str = ""
    ingredient_key: str = ""
    canonical_id: str = None
    note: str = None
    is_staple: bool = False
    aliases: list = field(default_factory=list)   # parenthetical alternative names


def split_items(raw: str) -> list:
    """Split on commas that are not inside parentheses."""
    items, depth, current = [], 0, []
    for ch in raw or "":
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == "," and depth == 0:
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    return [i.strip() for i in items if i.strip()]


def _quantity_value(text: str):
    """Numeric value for plain numbers/fractions/mixed numbers; None for ranges."""
    text = text.strip()
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            return float(text)
        if re.fullmatch(r"\d+/\d+", text):
            n, d = text.split("/")
            return int(n) / int(d)
        m = re.fullmatch(r"(\d+)[\s-](\d+)/(\d+)", text)
        if m:
            return int(m[1]) + int(m[2]) / int(m[3])
    except ZeroDivisionError:
        return None
    return None


def normalize_name(name: str) -> str:
    """Matching form of an ingredient name: lowercase, no brackets, no filler words."""
    name = _PAREN_RE.sub(" ", name)
    name = normalize(name)
    words = [w for w in name.split() if w not in {"of", "the", "a", "an", "to", "taste", "few"}]
    out = " ".join(words)
    # simple singularisation of the last word (tomatoes -> tomato, onions -> onion)
    if len(out) > 4 and out.endswith("oes"):
        out = out[:-2]
    elif len(out) > 4 and out.endswith("ies"):
        out = out[:-3] + "y"
    elif len(out) > 4 and out.endswith("s") and not out.endswith(("ss", "us", "is", "leaves")):
        out = out[:-1]
    return out


def find_catalog_id(name_normalized: str, aliases=()):
    """Exact catalogue lookup; may drop leading descriptor words (e.g. 'red onion' -> onion)."""
    candidates = [name_normalized, *(normalize(a) for a in aliases)]
    for cand in candidates:
        words = cand.split()
        for start in range(len(words)):
            if start and words[start - 1] not in DESCRIPTORS:
                break
            hit = lookup_exact(" ".join(words[start:]))
            if hit:
                return hit
    return None


def parse_ingredient(position: int, text: str) -> ParsedIngredient:
    row = ParsedIngredient(position=position, original_text=text)
    rest = text.strip()
    for frac, value in _UNICODE_FRACTIONS.items():
        if rest.startswith(frac):
            row.quantity_text, row.quantity_value = frac, value
            rest = rest[1:].strip()
            break
    else:
        m = _QTY_RE.match(rest)
        if m:
            row.quantity_text = m["qty"].strip()
            row.quantity_value = _quantity_value(row.quantity_text)
            rest = rest[m.end():]
    first = rest.split(None, 1)
    if first and row.quantity_text and first[0].lower().strip(".") in UNITS:
        row.unit = first[0].lower().strip(".")
        rest = first[1] if len(first) > 1 else ""
    name, _, note = rest.partition(" - ")
    row.name_original = name.strip() or text.strip()
    row.note = note.strip() or None
    for group in _PAREN_RE.findall(name):
        row.aliases += [a.strip() for a in re.split(r"[/;]", group) if a.strip()]
    row.name_normalized = normalize_name(row.name_original) or normalize(text)
    plain = normalize(_PAREN_RE.sub(" ", row.name_original))   # unsingularised, for alias lookup
    row.canonical_id = (find_catalog_id(plain, row.aliases)
                        or find_catalog_id(row.name_normalized, row.aliases))
    row.ingredient_key = row.canonical_id or row.name_normalized
    row.is_staple = bool(
        (row.canonical_id and CATALOG[row.canonical_id].staple)
        or row.name_normalized in _PANTRY
        or _strip_descriptors(row.name_normalized) in _PANTRY
    )
    return row


def parse_ingredient_list(raw: str) -> list:
    return [parse_ingredient(i, item) for i, item in enumerate(split_items(raw), 1)]


_PANTRY = {normalize_name(n) for n in PANTRY_NAMES}
