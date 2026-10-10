"""Estimated cost (INR) and calories for a recipe, from catalogue prices and nutrition data.

Everything here is an illustrative estimate, not an exact value.
"""
from dataclasses import dataclass

from ingredient_catalog import CATALOG


@dataclass(frozen=True)
class LineItem:
    ingredient_id: str
    name: str
    quantity: float
    unit: str
    cost: float     # INR for this quantity
    kcal: float     # kcal for this quantity


@dataclass(frozen=True)
class RecipeEstimate:
    items: tuple
    servings: int
    total_cost: float
    cost_per_serving: float
    total_kcal: float
    kcal_per_serving: float


def estimate(recipe, catalog=CATALOG) -> RecipeEstimate:
    """Sum quantity-weighted cost and calories, then divide by servings for per-serving values."""
    items = []
    for ing_id, qty in recipe.ingredients:
        ing = catalog[ing_id]
        items.append(LineItem(
            ing_id, ing.en, qty, ing.unit,
            cost=qty * ing.price_per_unit,
            kcal=qty * ing.kcal_per_unit,
        ))
    total_cost = sum(i.cost for i in items)
    total_kcal = sum(i.kcal for i in items)
    servings = max(recipe.servings, 1)
    return RecipeEstimate(
        tuple(items), servings, total_cost, total_cost / servings,
        total_kcal, total_kcal / servings,
    )


def format_quantity(item: LineItem) -> str:
    qty = int(item.quantity) if float(item.quantity).is_integer() else item.quantity
    return f"{qty} {item.unit}"
