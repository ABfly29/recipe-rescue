import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.helpers import TempDatabase, import_fixture

APP = Path(__file__).resolve().parent.parent / "app.py"


_tmp = None


def setUpModule():
    global _tmp
    _tmp = TempDatabase().__enter__()
    import_fixture(_tmp.path)


def tearDownModule():
    _tmp.__exit__()


def fresh_app():
    return AppTest.from_file(str(APP), default_timeout=60).run()


def submit(at, text):
    at.text_input(key="raw_text").set_value(text)
    at.button[0].click()
    return at.run()


class AppSmokeTests(unittest.TestCase):
    def test_starts_with_empty_state(self):
        at = fresh_app()
        self.assertFalse(at.exception)
        self.assertTrue(any("Start with what is in your kitchen" in m.value for m in at.markdown))

    def test_typed_ingredients_produce_results(self):
        at = submit(fresh_app(), "panor, tamato, pyaj, rice, dahi, capsicum")
        self.assertFalse(at.exception)
        self.assertEqual(set(at.multiselect[0].value),
                         {"paneer", "tomato", "onion", "rice", "curd", "capsicum"})
        page = " ".join(m.value for m in at.markdown)
        self.assertIn("Exact Matches", page)
        self.assertIn("Auto-corrected", page)

    def test_ambiguous_word_asks_for_confirmation(self):
        at = submit(fresh_app(), "dal, onion")
        self.assertFalse(at.exception)
        self.assertTrue(any("Not sure about" in m.value for m in at.markdown))
        self.assertEqual(at.multiselect[0].value, ["onion"])

    def test_imported_recipe_is_found_from_the_database(self):
        at = submit(fresh_app(), "aloo, gobi, pyaz")
        self.assertFalse(at.exception)
        at.session_state["meal"] = "Lunch"
        at.run()
        page = " ".join(m.value for m in at.markdown)
        self.assertIn("Test Aloo Gobi Recipe", page)
        self.assertIn("cost n/a", page)

    def test_meal_change_keeps_ingredients(self):
        at = submit(fresh_app(), "egg, onion, tomato")
        at.session_state["meal"] = "Breakfast"
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(set(at.multiselect[0].value), {"egg", "onion", "tomato"})


if __name__ == "__main__":
    unittest.main()
