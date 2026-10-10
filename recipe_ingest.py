"""Shared, idempotent write path for recipes (used by the dataset importer and the curated seed)."""
import hashlib
import re
from datetime import datetime, timezone

from ingredient_parser import ParsedIngredient


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _squash(text) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def content_hash(name, ingredients_raw, instructions) -> str:
    """Identity of a recipe's content, so the same recipe is never stored twice."""
    payload = "\x1f".join(_squash(x) for x in (name, ingredients_raw, instructions))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


RECIPE_COLUMNS = (
    "source", "source_key", "source_srno", "source_url", "content_hash", "name", "translated_name",
    "cuisine", "course", "diet", "diet_type", "prep_time_min", "cook_time_min", "total_time_min",
    "servings", "ingredients_raw", "translated_ingredients_raw", "instructions",
    "translated_instructions", "difficulty", "emoji", "image_url", "est_total_cost",
    "est_total_kcal", "estimate_basis", "import_run_id", "created_at",
)

INSERTED, EXISTS = "inserted", "exists"


def insert_recipe(conn, record: dict, ingredients: list, meals: list) -> str:
    """Insert one recipe with its ingredients and meals unless it already exists.

    Existing rows are never modified. ``meals`` is a list of ``(meal, is_primary)``.
    Returns INSERTED or EXISTS.
    """
    found = conn.execute(
        "SELECT 1 FROM recipes WHERE (source = ? AND source_key = ?) OR content_hash = ?",
        (record["source"], record["source_key"], record["content_hash"]),
    ).fetchone()
    if found:
        return EXISTS
    values = dict.fromkeys(RECIPE_COLUMNS)
    values.update(record)
    values.setdefault("created_at", now_iso())
    if not values["created_at"]:
        values["created_at"] = now_iso()
    if not values["diet_type"]:
        values["diet_type"] = "unknown"
    cur = conn.execute(
        f"INSERT INTO recipes ({','.join(RECIPE_COLUMNS)}) VALUES ({','.join('?' * len(RECIPE_COLUMNS))})",
        [values[c] for c in RECIPE_COLUMNS],
    )
    recipe_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO recipe_meals (recipe_id, meal, is_primary) VALUES (?, ?, ?)",
        [(recipe_id, meal, int(primary)) for meal, primary in meals],
    )
    conn.executemany(
        "INSERT INTO recipe_ingredients (recipe_id, position, original_text, quantity_text, "
        "quantity_value, unit, name_original, name_normalized, ingredient_key, canonical_id, "
        "note, is_staple, est_cost, est_kcal) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(recipe_id, i.position, i.original_text, i.quantity_text, i.quantity_value, i.unit,
          i.name_original, i.name_normalized, i.ingredient_key, i.canonical_id, i.note,
          int(i.is_staple), getattr(i, "est_cost", None), getattr(i, "est_kcal", None))
         for i in ingredients],
    )
    return INSERTED


def refresh_vocab(conn, alias_limit: int = 6, alias_min_count: int = 3) -> int:
    """Rebuild ingredient_vocab rows from recipe_ingredients (upsert; never drops anything)."""
    rows = conn.execute(
        "SELECT ingredient_key, MIN(canonical_id) AS canonical_id, MAX(is_staple) AS is_staple, "
        "COUNT(DISTINCT recipe_id) AS n FROM recipe_ingredients GROUP BY ingredient_key"
    ).fetchall()
    # Alternative names come from bracketed text such as "Curd (Dahi)". Brackets are noisy, so an
    # alias is kept only if it is seen at least 3 times for this ingredient and this ingredient
    # accounts for most of its occurrences across all ingredients.
    per_key, totals = {}, {}
    for r in conn.execute("SELECT ingredient_key, original_text FROM recipe_ingredients"):
        for group in re.findall(r"\(([^)]*)\)", r["original_text"]):
            for alias in re.split(r"[/;]", group):
                alias = alias.strip().lower()
                if 2 < len(alias) < 30 and not re.search(r"\d", alias):
                    bucket = per_key.setdefault(r["ingredient_key"], {})
                    bucket[alias] = bucket.get(alias, 0) + 1
                    totals[alias] = totals.get(alias, 0) + 1
    aliases = {k: {a: n for a, n in b.items() if n >= alias_min_count and n >= 0.6 * totals[a]}
               for k, b in per_key.items()}
    conn.executemany(
        "INSERT INTO ingredient_vocab (ingredient_key, display_name, canonical_id, aliases, "
        "recipe_count, is_staple) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(ingredient_key) DO UPDATE SET canonical_id = excluded.canonical_id, "
        "aliases = excluded.aliases, recipe_count = excluded.recipe_count, is_staple = excluded.is_staple",
        [(r["ingredient_key"], r["ingredient_key"], r["canonical_id"],
          "|".join(a for a, _ in sorted(aliases.get(r["ingredient_key"], {}).items(),
                                         key=lambda kv: (-kv[1], kv[0]))[:alias_limit]),
          r["n"], r["is_staple"]) for r in rows],
    )
    return len(rows)


def curated_ingredient(position, item, ing) -> ParsedIngredient:
    """ParsedIngredient for a curated recipe line (known quantity, with illustrative estimates)."""
    qty = item.quantity
    unit_label = {"g": "g", "ml": "ml", "pc": "pc"}[item.unit]
    text = f"{int(qty) if float(qty).is_integer() else qty} {unit_label} {ing.en}"
    row = ParsedIngredient(
        position=position, original_text=text, quantity_text=str(qty), quantity_value=float(qty),
        unit=unit_label, name_original=ing.en, name_normalized=ing.en.lower(),
        ingredient_key=ing.id, canonical_id=ing.id, is_staple=ing.staple,
    )
    row.est_cost, row.est_kcal = item.cost, item.kcal
    return row
