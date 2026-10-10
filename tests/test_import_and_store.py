import json
import sqlite3
import unittest
from pathlib import Path

import db
import recipe_store as store
from tests.helpers import FIXTURE, TempDatabase, import_fixture
from tools import backup_db
from tools.import_dataset import find_files, run_import, verify_database

ROOT = Path(__file__).resolve().parent.parent


class ImportTests(unittest.TestCase):
    def test_report_counts(self):
        with TempDatabase() as t:
            report = import_fixture(t.path)
        totals = report["totals"]
        self.assertEqual(totals["rows"], 8)
        self.assertEqual(totals["imported"], 5)              # rows 1, 2, 3, 7, 8
        self.assertEqual(totals["duplicate_in_input"], 2)    # rows 4 (same URL) and 5 (same content)
        self.assertEqual(totals["rejected"], 1)
        self.assertEqual(report["reject_reasons"], {"missing_ingredients": 1})
        self.assertEqual(report["missing_fields"]["Ingredients: blank"], 1)

    def test_import_is_idempotent(self):
        with TempDatabase() as t:
            import_fixture(t.path)
            conn = db.connect(t.path)
            before = {tbl: conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                      for tbl in ("recipes", "recipe_ingredients", "recipe_meals", "import_rejects")}
            conn.close()
            second = import_fixture(t.path)
            conn = db.connect(t.path)
            after = {tbl: conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                     for tbl in before}
            conn.close()
        self.assertEqual(before, after)
        self.assertEqual(second["totals"].get("imported", 0), 0)
        self.assertEqual(second["totals"]["already_in_database"], 5)

    def test_existing_data_is_preserved(self):
        with TempDatabase() as t:
            conn = db.connect(t.path)
            db.migrate(conn)
            conn.execute("INSERT INTO recipes (source, source_key, content_hash, name, instructions, created_at) "
                         "VALUES ('mine', '1', 'hash-mine', 'My Own Recipe', 'Cook.', '2026-01-01')")
            conn.commit()
            conn.close()
            import_fixture(t.path)
            import_fixture(t.path)
            conn = db.connect(t.path)
            self.assertEqual(conn.execute("SELECT name FROM recipes WHERE source = 'mine'").fetchone()[0],
                             "My Own Recipe")
            conn.close()

    def test_originals_preserved_and_unknowns_not_invented(self):
        with TempDatabase() as t:
            import_fixture(t.path)
            conn = db.connect(t.path)
            conn.row_factory = sqlite3.Row
            hindi = conn.execute("SELECT * FROM recipes WHERE name = 'Test Hindi Aloo Pyaz'").fetchone()
            self.assertEqual(hindi["ingredients_raw"], "2 आलू,1 प्याज़")           # original kept
            self.assertEqual(hindi["translated_ingredients_raw"], "2 Potato,1 Onion")
            karela = conn.execute("SELECT * FROM recipes WHERE name = 'Test Karela Fry'").fetchone()
            self.assertIsNone(karela["prep_time_min"])
            self.assertIsNone(karela["cook_time_min"])
            self.assertIsNone(karela["total_time_min"])
            self.assertEqual(karela["diet_type"], "vegan")
            egg = conn.execute("SELECT * FROM recipes WHERE name = 'Test Egg Bhurji'").fetchone()
            self.assertIsNone(egg["prep_time_min"])          # 0 in the source means unknown
            self.assertEqual(egg["cook_time_min"], 10)
            kheer = conn.execute("SELECT diet_type FROM recipes WHERE name = 'Test Kheer'").fetchone()
            self.assertEqual(kheer[0], "unknown")            # 'Diabetic Friendly' says nothing about meat
            imported = conn.execute("SELECT COUNT(*) FROM recipes WHERE source != 'curated' AND "
                                    "(est_total_cost IS NOT NULL OR est_total_kcal IS NOT NULL)").fetchone()[0]
            self.assertEqual(imported, 0)                    # no invented prices or calories
            self.assertEqual(verify_database(conn), [])
            conn.close()

    def test_ingredients_parsed_with_original_and_normalized_names(self):
        with TempDatabase() as t:
            import_fixture(t.path)
            conn = db.connect(t.path)
            rows = conn.execute(
                "SELECT i.* FROM recipe_ingredients i JOIN recipes r ON r.id = i.recipe_id "
                "WHERE r.name = 'Test Aloo Gobi Recipe' ORDER BY position").fetchall()
            conn.close()
        by_pos = {r["position"]: r for r in rows}
        self.assertEqual(by_pos[2]["original_text"], "1 Cauliflower (Gobi) - chopped")
        self.assertEqual(by_pos[2]["name_original"], "Cauliflower (Gobi)")
        self.assertEqual(by_pos[2]["canonical_id"], "cauliflower")
        self.assertEqual(by_pos[2]["note"], "chopped")
        self.assertEqual(by_pos[1]["ingredient_key"], "potato")
        self.assertEqual(by_pos[4]["is_staple"], 1)          # salt
        self.assertIsNone(by_pos[4]["quantity_text"])        # 'to taste' has no invented quantity

    def test_meal_mapping(self):
        with TempDatabase() as t:
            import_fixture(t.path)
            conn = db.connect(t.path)
            meals = lambda name: {r[0] for r in conn.execute(
                "SELECT meal FROM recipe_meals m JOIN recipes r ON r.id = m.recipe_id WHERE r.name = ?", (name,))}
            self.assertEqual(meals("Test Aloo Gobi Recipe"), {"Lunch"})
            self.assertEqual(meals("Test Egg Bhurji"), {"Breakfast"})
            self.assertEqual(meals("Test Karela Fry"), {"Snacks"})
            self.assertEqual(meals("Test Hindi Aloo Pyaz"), set())    # dirty Course value -> unknown
            conn.close()

    def test_dry_run_writes_nothing(self):
        with TempDatabase() as t:
            conn = db.connect(t.path)
            db.migrate(conn)
            report = run_import(conn, find_files(FIXTURE), dry_run=True)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0], 0)
            conn.close()
        self.assertEqual(report["totals"]["imported"], 5)

    def test_backup_is_verified_and_restorable(self):
        with TempDatabase() as t:
            import_fixture(t.path)
            dest = backup_db.backup(t.path, Path(t.path).parent / "backups", keep=2)
            info = backup_db.verify(dest)
            self.assertEqual(info["integrity"], "ok")
            self.assertEqual(info["recipes"], 5 + 27)        # imported + curated
            for _ in range(3):
                backup_db.backup(t.path, Path(t.path).parent / "backups", keep=2)
            self.assertEqual(len(list((Path(t.path).parent / "backups").glob("*.db"))), 2)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDatabase().__enter__()
        import_fixture(self._tmp.path)
        self.conn = store.open_store(self._tmp.path)

    def tearDown(self):
        self.conn.close()
        self._tmp.__exit__()

    def names(self, rows):
        return [r.recipe.name for r in store.load_matches(self.conn, rows, [])]

    def test_open_store_is_idempotent(self):
        before = store.summary(self.conn)
        store.open_store(self._tmp.path).close()
        self.assertEqual(store.summary(self.conn), before)
        self.assertEqual(before["curated"], 27)
        self.assertEqual(before["imported"], 5)

    def test_exact_then_near_and_meal_filter(self):
        have = ["paneer", "capsicum", "onion", "tomato"]
        rows = store.find_matches(self.conn, have, "Dinner")
        matches = store.load_matches(self.conn, rows, have)
        names = [m.recipe.name for m in matches]
        self.assertIn("Kadai Paneer", names)
        flags = [m.exact for m in matches]
        self.assertEqual(flags, sorted(flags, reverse=True))
        self.assertTrue(all("Dinner" in m.recipe.meals for m in matches))
        self.assertNotIn("Poha", names)

    def test_changing_meal_keeps_ingredients(self):
        have = ["egg", "onion", "tomato"]
        b = self.names(store.find_matches(self.conn, have, "Breakfast"))
        d = self.names(store.find_matches(self.conn, have, "Dinner"))
        self.assertIn("Masala Omelette", b)
        self.assertIn("Egg Curry", d)

    def test_imported_recipes_are_matched_by_database_ingredients(self):
        have = ["potato", "cauliflower", "onion"]
        rows = store.find_matches(self.conn, have, "Lunch")
        matches = store.load_matches(self.conn, rows, have)
        hit = [m for m in matches if m.recipe.name == "Test Aloo Gobi Recipe"][0]
        self.assertTrue(hit.exact)                            # oil and salt are staples
        self.assertIsNone(hit.recipe.est_total_cost)          # unknown, not invented
        self.assertIsNone(hit.recipe.kcal_per_serving)

    def test_missing_lists_are_unique_and_limited(self):
        for meal in ("Breakfast", "Lunch", "Dinner", "Snacks"):
            rows = store.find_matches(self.conn, ["onion"], meal)
            for m in store.load_matches(self.conn, rows, ["onion"]):
                self.assertEqual(len(m.missing), len(set(m.missing)))
                self.assertLessEqual(len(m.missing), 2)
        strict = store.find_matches(self.conn, ["onion", "paneer", "tomato"], "Dinner", max_missing=0)
        self.assertTrue(strict and all(r.have == r.required for r in strict))

    def test_staples_toggle(self):
        with_staples = store.find_matches(self.conn, ["potato", "cauliflower", "onion"], "Lunch",
                                          assume_staples=True, max_missing=0)
        without = store.find_matches(self.conn, ["potato", "cauliflower", "onion"], "Lunch",
                                     assume_staples=False, max_missing=0)
        self.assertGreater(len(with_staples), len(without))

    def test_no_owned_ingredient_means_no_match(self):
        self.assertEqual(store.find_matches(self.conn, ["cashew"], "Dinner"), [])
        self.assertEqual(store.find_matches(self.conn, [], "Dinner"), [])

    def test_filters(self):
        have = ["chicken", "onion", "tomato", "curd", "paneer"]
        def run(**kw):
            return store.load_matches(self.conn, store.find_matches(self.conn, have, "Dinner", **kw), have)
        self.assertTrue(all(m.recipe.vegetarian for m in run(diet="Vegetarian")))
        nonveg = run(diet="Non-vegetarian")
        self.assertTrue(nonveg and not any(m.recipe.vegetarian for m in nonveg))
        self.assertTrue(all(m.recipe.time_min and m.recipe.time_min <= 30 for m in run(max_time=30)))
        cheap = run(max_cost_per_serving=40)
        self.assertTrue(cheap and all(m.recipe.cost_per_serving <= 40 for m in cheap))

    def test_unknown_cost_hidden_under_budget_filter(self):
        have = ["potato", "cauliflower", "onion"]
        rows = store.find_matches(self.conn, have, "Lunch", max_cost_per_serving=500)
        self.assertNotIn("Test Aloo Gobi Recipe", self.names(rows))

    def test_search(self):
        names = [r.name for r in store.search_recipes(self.conn, "karela")]
        self.assertEqual(names, ["Test Karela Fry"])
        self.assertIn("Palak Paneer", [r.name for r in store.search_recipes(self.conn, "palak paneer")])
        self.assertEqual(store.search_recipes(self.conn, ""), [])
        self.assertEqual(store.search_recipes(self.conn, "50%_"), [])      # wildcards are escaped
        self.assertEqual([r.name for r in store.search_recipes(self.conn, "egg", diet="Vegetarian")], [])

    def test_vocabulary_includes_database_ingredients(self):
        from normalizer import parse_ingredients
        vocab = store.load_vocabulary(self.conn, min_count=1)
        self.assertIn("karela", vocab.options)
        self.assertEqual(parse_ingredients("karela, pyaz", vocab.index).accepted, ["karela", "onion"])

    def test_noisy_bracket_aliases_are_not_trusted(self):
        from normalizer import parse_ingredients
        from recipe_ingest import refresh_vocab
        # "bitter gourd" appears once in brackets: below the default threshold of 3 sightings
        vocab = store.load_vocabulary(self.conn, min_count=1)
        self.assertEqual(parse_ingredients("bitter gourd", vocab.index).accepted, [])
        refresh_vocab(self.conn, alias_min_count=1)
        vocab = store.load_vocabulary(self.conn, min_count=1)
        self.assertEqual(parse_ingredients("bitter gourd", vocab.index).accepted, ["karela"])
        refresh_vocab(self.conn)    # restore default behaviour
        # a harvested alias can never override a built-in one such as 'dahi' -> curd
        self.assertEqual(parse_ingredients("dahi", store.load_vocabulary(self.conn, 1).index).accepted, ["curd"])


class NoDatasetAtRuntimeTests(unittest.TestCase):
    def test_app_modules_never_read_dataset_files(self):
        for name in ("app.py", "recipe_store.py", "curated_seed.py", "db.py", "ui_components.py",
                     "recipe_ingest.py", "ingredient_parser.py"):
            source = (ROOT / name).read_text(encoding="utf-8")
            for banned in ("import csv", "openpyxl", "pandas", "read_csv", "read_excel", "Downloads"):
                self.assertNotIn(banned, source, f"{name} mentions {banned}")

    def test_dataset_files_are_not_in_the_repository(self):
        found = [p for p in ROOT.rglob("*") if p.suffix.lower() in (".csv", ".xlsx", ".xls")
                 and ".venv" not in p.parts and "legacy_react" not in p.parts
                 and "fixtures" not in p.parts]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
