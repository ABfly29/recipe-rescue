"""Read access to recipes: everything the app shows comes from SQLite through this module.

Nothing here reads CSV/Excel files. ``open_store`` creates/migrates the database and seeds the
small curated recipe set, both idempotently.
"""
import re
from dataclasses import dataclass, field

import db
from curated_seed import seed_curated
from ingredient_catalog import ALL_IDS, CATALOG
from normalizer import build_index, normalize

DIET_TYPES = {
    "Vegetarian": ("vegetarian", "vegan"),
    "Non-vegetarian": ("non_vegetarian", "eggetarian"),
}
TIME_SQL = ("COALESCE(r.total_time_min, NULLIF(COALESCE(r.prep_time_min, 0) "
            "+ COALESCE(r.cook_time_min, 0), 0))")


def open_store(path=None):
    """Connect, apply pending migrations, and make sure the curated recipes exist."""
    conn = db.connect(path)
    db.migrate(conn)
    seed_curated(conn)
    return conn


# --- data classes ---------------------------------------------------------------------
@dataclass
class IngredientView:
    position: int
    original_text: str
    name: str
    key: str
    quantity_text: str = None
    unit: str = None
    note: str = None
    is_staple: bool = False
    est_cost: float = None
    est_kcal: float = None


@dataclass
class RecipeView:
    id: int
    source: str
    name: str
    translated_name: str
    source_url: str
    cuisine: str
    course: str
    diet: str
    diet_type: str
    meals: tuple
    time_min: int           # None = unknown
    prep_time_min: int
    cook_time_min: int
    servings: int           # None = unknown
    difficulty: str
    emoji: str
    image_url: str
    est_total_cost: float   # None = unknown
    est_total_kcal: float   # None = unknown
    instructions: str
    translated_instructions: str
    ingredients: list = field(default_factory=list)

    @property
    def is_curated(self) -> bool:
        return self.source == "curated"

    @property
    def cost_per_serving(self):
        if self.est_total_cost is None or not self.servings:
            return None
        return self.est_total_cost / self.servings

    @property
    def kcal_per_serving(self):
        if self.est_total_kcal is None or not self.servings:
            return None
        return self.est_total_kcal / self.servings

    @property
    def vegetarian(self):
        """True / False, or None when the source does not say."""
        if self.diet_type in ("vegetarian", "vegan"):
            return True
        if self.diet_type in ("non_vegetarian", "eggetarian"):
            return False
        return None

    @property
    def display_name(self) -> str:
        """Original title, or the English translation when the original is in Devanagari."""
        if self.translated_name and re.search(r"[ऀ-ॿ]", self.name):
            return self.translated_name
        return self.name

    @property
    def method(self) -> str:
        return (self.translated_instructions or self.instructions or "").strip()


@dataclass
class Match:
    recipe: RecipeView
    required: int
    have: int
    missing: tuple          # display names of missing required ingredients (unique)
    score: float

    @property
    def exact(self) -> bool:
        return not self.missing


@dataclass
class MatchRow:
    recipe_id: int
    required: int
    have: int
    score: float


@dataclass
class Vocabulary:
    index: object                     # normalizer.Index
    labels: dict                      # ingredient id -> display label
    options: list                     # ids offered in the ingredient picker

    def label(self, ingredient_id: str) -> str:
        return self.labels.get(ingredient_id) or ingredient_id.title()


def load_vocabulary(conn, min_count: int = 20) -> Vocabulary:
    """Catalogue ingredients plus common database ingredients that the catalogue lacks."""
    extra, labels = {}, {i: CATALOG[i].label for i in ALL_IDS}
    taken = build_index().alias_ids
    rows = conn.execute(
        "SELECT ingredient_key, aliases, recipe_count FROM ingredient_vocab "
        "WHERE canonical_id IS NULL AND is_staple = 0 AND recipe_count >= ? "
        "ORDER BY recipe_count DESC, ingredient_key", (min_count,)).fetchall()
    for row in rows:
        key = row["ingredient_key"]
        if key in CATALOG or len(key) < 3:
            continue
        extra[key] = (key, tuple(a for a in row["aliases"].split("|") if a and normalize(a) not in taken))
        labels[key] = key.title()
    return Vocabulary(build_index(extra), labels, [*ALL_IDS, *extra])


# --- matching -------------------------------------------------------------------------
def find_matches(conn, have, meal: str, assume_staples: bool = True, max_missing: int = 2,
                 diet: str = "All", max_time: int = 0, max_cost_per_serving: float = 0) -> list:
    """Rank recipes for ``meal`` by how well the owned ingredient keys cover them.

    Exact matches (nothing missing) come first. Then ordering is by coverage, best-fit
    meal, fewer missing ingredients and number of owned ingredients used. Staples
    (oil, salt, spices...) are ignored when ``assume_staples``.
    Returns lightweight MatchRow objects; use ``load_matches`` for display data.
    """
    have = list(dict.fromkeys(have))
    if not have:
        return []
    marks = ",".join("?" * len(have))
    params = [meal]
    where = ["a.have >= 1", "a.required - a.have <= ?"]
    filters_params = [max_missing]
    if diet in DIET_TYPES:
        types = DIET_TYPES[diet]
        where.append(f"r.diet_type IN ({','.join('?' * len(types))})")
        filters_params += types
    if max_time:
        where.append(f"{TIME_SQL} <= ?")
        filters_params.append(max_time)
    if max_cost_per_serving:   # recipes with unknown cost cannot be shown as within budget
        where.append("r.est_total_cost IS NOT NULL AND r.servings > 0 "
                     "AND r.est_total_cost * 1.0 / r.servings <= ?")
        filters_params.append(max_cost_per_serving)
    sql = f"""
        WITH req AS (
            SELECT ri.recipe_id, ri.ingredient_key AS k
            FROM recipe_ingredients ri
            JOIN recipe_meals rm ON rm.recipe_id = ri.recipe_id AND rm.meal = ?
            {"WHERE ri.is_staple = 0" if assume_staples else ""}
            GROUP BY ri.recipe_id, ri.ingredient_key
        ), agg AS (
            SELECT recipe_id, COUNT(*) AS required,
                   SUM(CASE WHEN k IN ({marks}) THEN 1 ELSE 0 END) AS have
            FROM req GROUP BY recipe_id
        )
        SELECT a.recipe_id, a.required, a.have,
               100.0 * a.have / a.required + 10 * m.is_primary - 8 * (a.required - a.have)
                   + 0.5 * MIN(a.have, 10) AS score
        FROM agg a
        JOIN recipes r ON r.id = a.recipe_id
        JOIN recipe_meals m ON m.recipe_id = a.recipe_id AND m.meal = ?
        WHERE {' AND '.join(where)}
        ORDER BY (a.required > a.have), score DESC, r.name, r.id
    """
    params += have + [meal] + filters_params
    return [MatchRow(r["recipe_id"], r["required"], r["have"], r["score"])
            for r in conn.execute(sql, params)]


def load_recipes(conn, ids) -> dict:
    """RecipeView objects (with ingredients) for the given recipe ids."""
    ids = list(ids)
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    meals = {}
    for r in conn.execute(f"SELECT recipe_id, meal FROM recipe_meals WHERE recipe_id IN ({marks}) "
                          "ORDER BY is_primary DESC, meal", ids):
        meals.setdefault(r["recipe_id"], []).append(r["meal"])
    ingredients = {}
    for r in conn.execute(f"SELECT * FROM recipe_ingredients WHERE recipe_id IN ({marks}) "
                          "ORDER BY recipe_id, position", ids):
        ingredients.setdefault(r["recipe_id"], []).append(IngredientView(
            r["position"], r["original_text"], display_name(r["name_original"], r["canonical_id"]),
            r["ingredient_key"], r["quantity_text"], r["unit"], r["note"], bool(r["is_staple"]),
            r["est_cost"], r["est_kcal"]))
    out = {}
    for r in conn.execute(f"SELECT * FROM recipes r WHERE id IN ({marks})", ids):
        time_min = r["total_time_min"] or (
            ((r["prep_time_min"] or 0) + (r["cook_time_min"] or 0)) or None)
        out[r["id"]] = RecipeView(
            r["id"], r["source"], r["name"], r["translated_name"], r["source_url"], r["cuisine"],
            r["course"], r["diet"], r["diet_type"], tuple(meals.get(r["id"], ())), time_min,
            r["prep_time_min"], r["cook_time_min"], r["servings"], r["difficulty"], r["emoji"],
            r["image_url"], r["est_total_cost"], r["est_total_kcal"], r["instructions"],
            r["translated_instructions"], ingredients.get(r["id"], []))
    return out


def display_name(name_original: str, canonical_id: str = None) -> str:
    if canonical_id in CATALOG:
        return CATALOG[canonical_id].en
    cleaned = re.sub(r"\([^)]*\)", "", name_original or "")
    return re.sub(r"\s+", " ", cleaned).strip(" -,") or (name_original or "").strip()


def missing_for(recipe, have, assume_staples: bool = True) -> tuple:
    """Unique display names of the recipe's required ingredients that are not in ``have``."""
    missing, seen = [], set()
    for ing in recipe.ingredients:
        if ing.key in have or ing.key in seen or (assume_staples and ing.is_staple):
            continue
        seen.add(ing.key)
        missing.append(ing.name)
    return tuple(missing)


def to_matches(recipes, have, assume_staples: bool = True) -> list:
    """Match objects for already-loaded recipes (used by text search)."""
    have = set(have)
    out = []
    for r in recipes:
        req = {i.key for i in r.ingredients if not (assume_staples and i.is_staple)}
        owned = len(req & have)
        out.append(Match(r, len(req), owned, missing_for(r, have, assume_staples), 0.0))
    return out


def load_matches(conn, rows, have, assume_staples: bool = True) -> list:
    """Turn MatchRows into Match objects with the (unique) missing ingredient names."""
    recipes = load_recipes(conn, [r.recipe_id for r in rows])
    have = set(have)
    return [Match(recipes[row.recipe_id], row.required, row.have,
                  missing_for(recipes[row.recipe_id], have, assume_staples), row.score)
            for row in rows]


# --- text search ----------------------------------------------------------------------
def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def search_recipes(conn, text: str, meal: str = None, diet: str = "All", limit: int = 24) -> list:
    """Recipes whose name or ingredients contain every word of ``text`` (best name matches first)."""
    words = [w for w in re.split(r"\s+", (text or "").strip().lower()) if w]
    if not words:
        return []
    where, params = [], []
    for w in words:
        where.append("(LOWER(r.name) LIKE ? ESCAPE '\\' OR LOWER(COALESCE(r.translated_name,'')) LIKE ? ESCAPE '\\' "
                     "OR EXISTS (SELECT 1 FROM recipe_ingredients i WHERE i.recipe_id = r.id "
                     "AND i.name_normalized LIKE ? ESCAPE '\\'))")
        params += [_like(w)] * 3
    if meal:
        where.append("EXISTS (SELECT 1 FROM recipe_meals m WHERE m.recipe_id = r.id AND m.meal = ?)")
        params.append(meal)
    if diet in DIET_TYPES:
        where.append(f"r.diet_type IN ({','.join('?' * len(DIET_TYPES[diet]))})")
        params += DIET_TYPES[diet]
    phrase = _like(" ".join(words))
    sql = (f"SELECT r.id FROM recipes r WHERE {' AND '.join(where)} "
           "ORDER BY (LOWER(r.name) LIKE ? ESCAPE '\\') DESC, LENGTH(r.name), r.name LIMIT ?")
    ids = [r["id"] for r in conn.execute(sql, params + [phrase, limit])]
    loaded = load_recipes(conn, ids)
    return [loaded[i] for i in ids]


def summary(conn) -> dict:
    """Counts for display and diagnostics."""
    q = lambda sql: conn.execute(sql).fetchone()[0]
    return {
        "recipes": q("SELECT COUNT(*) FROM recipes"),
        "curated": q("SELECT COUNT(*) FROM recipes WHERE source = 'curated'"),
        "imported": q("SELECT COUNT(*) FROM recipes WHERE source != 'curated'"),
        "ingredient_lines": q("SELECT COUNT(*) FROM recipe_ingredients"),
    }
