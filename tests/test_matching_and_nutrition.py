import unittest

from ingredient_catalog import CATALOG
from nutrition import estimate
from recipe_data import MEALS, RECIPES, Recipe


def make_recipe(ingredients, servings=2, meals=("Dinner",)):
    return Recipe(99, "Test", meals, 20, "Easy", servings, "🍽", tuple(ingredients), ("Cook.",))


class NutritionTests(unittest.TestCase):
    def test_ingredient_cost_and_calories(self):
        est = estimate(make_recipe([("onion", 100), ("oil", 10), ("egg", 2)], servings=1))
        onion, oil, egg = est.items
        self.assertAlmostEqual(onion.cost, 4.0)                    # 100 g at 40/kg
        self.assertAlmostEqual(onion.kcal, 40)
        self.assertAlmostEqual(oil.cost, 1.5)                      # 10 ml at 150/L
        self.assertAlmostEqual(oil.kcal, 82.8)                     # 828 kcal / 100 ml
        self.assertAlmostEqual(egg.cost, 14)                       # 2 pieces at 7
        self.assertAlmostEqual(egg.kcal, 144)

    def test_totals_and_per_serving(self):
        est = estimate(make_recipe([("onion", 100), ("oil", 10)], servings=4))
        self.assertAlmostEqual(est.total_cost, 4.0 + 1.5)
        self.assertAlmostEqual(est.cost_per_serving, 5.5 / 4)
        self.assertAlmostEqual(est.total_kcal, 40 + 82.8)
        self.assertAlmostEqual(est.kcal_per_serving, (40 + 82.8) / 4)

    def test_quantity_changes_totals(self):
        a = estimate(make_recipe([("paneer", 100)]))
        b = estimate(make_recipe([("paneer", 200)]))
        self.assertAlmostEqual(b.total_cost, 2 * a.total_cost)
        self.assertAlmostEqual(b.total_kcal, 2 * a.total_kcal)

    def test_every_recipe_has_sane_estimates(self):
        for r in RECIPES:
            est = estimate(r)
            self.assertGreater(est.cost_per_serving, 5, r.name)
            self.assertLess(est.cost_per_serving, 250, r.name)
            self.assertGreater(est.kcal_per_serving, 50, r.name)
            self.assertLess(est.kcal_per_serving, 1200, r.name)


class DataTests(unittest.TestCase):
    def test_enough_recipes_with_valid_data(self):
        self.assertGreaterEqual(len(RECIPES), 20)
        for r in RECIPES:
            ids = [i for i, _ in r.ingredients]
            self.assertEqual(len(ids), len(set(ids)), f"duplicate ingredient in {r.name}")
            self.assertTrue(all(i in CATALOG for i in ids), r.name)
            self.assertTrue(all(q > 0 for _, q in r.ingredients), r.name)
            self.assertTrue(set(r.meals) <= set(MEALS), r.name)
        self.assertEqual(len({r.id for r in RECIPES}), len(RECIPES))

    def test_every_meal_has_recipes(self):
        for meal in MEALS:
            self.assertGreaterEqual(sum(meal in r.meals for r in RECIPES), 4, meal)

    def test_vegetarian_flag(self):
        by_name = {r.name: r for r in RECIPES}
        self.assertTrue(by_name["Palak Paneer"].vegetarian)
        self.assertFalse(by_name["Chicken Curry"].vegetarian)
        self.assertFalse(by_name["Egg Curry"].vegetarian)


if __name__ == "__main__":
    unittest.main()
