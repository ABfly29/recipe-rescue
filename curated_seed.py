"""Seed the hand-written starter recipes (recipe_data.py) into SQLite.

Idempotent: recipes already present (by source key or content hash) are left untouched.
These are the only recipes with price/calorie estimates; they use the illustrative
catalogue values. Imported dataset recipes have NULL (unknown) cost and calories.
"""
from ingredient_catalog import CATALOG
from nutrition import estimate
from recipe_data import RECIPES
from recipe_ingest import INSERTED, content_hash, curated_ingredient, insert_recipe, now_iso, refresh_vocab

SOURCE = "curated"


def _diet_type(recipe) -> str:
    ids = [i for i, _ in recipe.ingredients]
    if recipe.vegetarian:
        return "vegetarian"
    return "eggetarian" if "egg" in ids and not any(
        CATALOG[i].veg is False and i != "egg" for i in ids) else "non_vegetarian"


def seed_curated(conn, commit: bool = True) -> int:
    """Insert missing curated recipes; returns how many were added.

    Pass ``commit=False`` when called inside a larger transaction (the dataset import).
    """
    added = 0
    for r in RECIPES:
        est = estimate(r)
        ingredients = [curated_ingredient(pos, item, CATALOG[item.ingredient_id])
                       for pos, item in enumerate(est.items, 1)]
        ingredients_raw = ", ".join(i.original_text for i in ingredients)
        instructions = "\n".join(r.steps)
        record = {
            "source": SOURCE, "source_key": str(r.id), "name": r.name,
            "content_hash": content_hash(r.name, ingredients_raw, instructions),
            "diet": "Vegetarian" if r.vegetarian else "Non Vegetarian", "diet_type": _diet_type(r),
            "course": r.meals[0], "cuisine": "North Indian",
            "total_time_min": r.time_min, "servings": r.servings,
            "ingredients_raw": ingredients_raw, "instructions": instructions,
            "difficulty": r.difficulty, "emoji": r.emoji, "image_url": r.image or None,
            "est_total_cost": est.total_cost, "est_total_kcal": est.total_kcal,
            "estimate_basis": "illustrative catalogue prices and typical nutrition values",
            "created_at": now_iso(),
        }
        meals = [(m, i == 0) for i, m in enumerate(r.meals)]
        if insert_recipe(conn, record, ingredients, meals) == INSERTED:
            added += 1
    if added:
        refresh_vocab(conn)
    if commit:
        conn.commit()
    return added
