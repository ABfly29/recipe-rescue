import unittest

from normalizer import CONFIRM, UNKNOWN, parse_ingredients, recognize


class NormalizerTests(unittest.TestCase):
    def accepted(self, text):
        return parse_ingredients(text).accepted

    def test_required_typos(self):
        self.assertEqual(self.accepted("panor"), ["paneer"])
        self.assertEqual(self.accepted("tamato"), ["tomato"])
        self.assertEqual(self.accepted("pyaj"), ["onion"])

    def test_rice_and_dahi(self):
        self.assertEqual(self.accepted("rice, dahi"), ["rice", "curd"])

    def test_full_example(self):
        self.assertEqual(self.accepted("panor, onion, tomato, rice, dahi"),
                         ["paneer", "onion", "tomato", "rice", "curd"])

    def test_hindi_script_and_hinglish(self):
        self.assertEqual(self.accepted("आलू, प्याज़, दही"), ["potato", "onion", "curd"])
        self.assertEqual(self.accepted("aloo pyaz tamatar"), ["potato", "onion", "tomato"])
        self.assertEqual(self.accepted("PYAAJ, Tamaatar, Paneer"), ["onion", "tomato", "paneer"])

    def test_phonetic_variants(self):
        self.assertEqual(self.accepted("gobhi"), ["cauliflower"])
        self.assertEqual(self.accepted("bhindee"), ["okra"])

    def test_corrections_are_reported(self):
        res = parse_ingredients("panor, onion")
        self.assertEqual(res.corrections, [("panor", "paneer")])

    def test_unknown_ingredient(self):
        res = parse_ingredients("xylophone, onion")
        self.assertEqual(res.accepted, ["onion"])
        self.assertEqual(res.unknown, ["xylophone"])
        self.assertEqual(recognize("qzxwv").status, UNKNOWN)

    def test_ambiguous_asks_for_confirmation(self):
        res = parse_ingredients("dal")
        self.assertEqual(res.accepted, [])
        self.assertEqual(len(res.pending), 1)
        self.assertIn("toor_dal", res.pending[0].candidates)
        self.assertIn("moong_dal", res.pending[0].candidates)
        self.assertEqual(parse_ingredients("mirch").pending[0].status, CONFIRM)

    def test_low_confidence_asks_for_confirmation(self):
        self.assertEqual(recognize("ric").status, CONFIRM)   # too short to guess silently

    def test_similar_but_different_words_are_not_silently_corrected(self):
        res = parse_ingredients("bitter gourd")        # close to 'bottle gourd' but not a typo of it
        self.assertEqual(res.accepted, [])
        self.assertEqual(recognize("bitter gourd").status, CONFIRM)

    def test_duplicates_removed(self):
        self.assertEqual(self.accepted("dahi, curd, yogurt, दही, onion, pyaz, onions"),
                         ["curd", "onion"])
        self.assertEqual(self.accepted("paneer, panor, panir"), ["paneer"])

    def test_empty_and_noise(self):
        res = parse_ingredients(" , ;; ")
        self.assertEqual((res.accepted, res.pending, res.unknown), ([], [], []))

    def test_separators(self):
        self.assertEqual(self.accepted("onion and tomato aur aloo; rice"),
                         ["onion", "tomato", "potato", "rice"])


if __name__ == "__main__":
    unittest.main()
