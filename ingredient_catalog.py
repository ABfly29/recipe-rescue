"""Ingredient vocabulary: names, Hindi/Hinglish aliases, and illustrative price/nutrition data.

Units and conventions (all values are rough, illustrative Indian-market estimates):
  * unit "g" / "ml": ``price`` is INR per 1 kg / 1 litre, ``kcal`` is per 100 g / 100 ml.
  * unit "pc":       ``price`` is INR per piece,          ``kcal`` is per piece.
  * Grains, pulses and flours are measured raw/dry.
  * ``staple`` ingredients (oil, salt, spices, ginger...) are assumed to be in the pantry
    by default when matching, but are still included in cost and calorie totals.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ingredient:
    id: str
    en: str
    hi: str
    aliases: tuple
    unit: str          # "g", "ml" or "pc"
    price: float       # INR per kg / L (g, ml) or per piece (pc)
    kcal: float        # per 100 g / 100 ml, or per piece
    category: str
    veg: bool = True
    staple: bool = False

    @property
    def price_per_unit(self) -> float:
        """INR per single g / ml / piece."""
        return self.price / 1000 if self.unit in ("g", "ml") else self.price

    @property
    def kcal_per_unit(self) -> float:
        """kcal per single g / ml / piece."""
        return self.kcal / 100 if self.unit in ("g", "ml") else self.kcal

    @property
    def label(self) -> str:
        return f"{self.en} · {self.hi}"


CATALOG: dict = {}


def _add(id, en, hi, aliases, unit, price, kcal, category, veg=True, staple=False):
    CATALOG[id] = Ingredient(
        id, en, hi, tuple(a for a in aliases.split("|") if a), unit, price, kcal,
        category, veg, staple,
    )


# --- Vegetables -----------------------------------------------------------------------
_add("onion", "Onion", "प्याज़", "pyaz|pyaj|pyaaj|piyaz|pyaaz|kanda|onions|pyas|pyaz", "g", 40, 40, "Vegetables")
_add("tomato", "Tomato", "टमाटर", "tamatar|tamato|tomatoe|tamaatar|tomatoes|tmatar|timatar", "g", 40, 18, "Vegetables")
_add("potato", "Potato", "आलू", "aloo|alu|aaloo|batata|potatoes|aalu", "g", 30, 77, "Vegetables")
_add("cauliflower", "Cauliflower", "गोभी", "gobi|gobhi|phool gobi|phulgobi|phoolgobhi|cauli|gobi phool", "g", 50, 25, "Vegetables")
_add("cabbage", "Cabbage", "पत्ता गोभी", "patta gobi|patta gobhi|band gobi|bandgobhi|cabbage", "g", 30, 25, "Vegetables")
_add("peas", "Green Peas", "मटर", "matar|mutter|mattar|hara matar|green peas|peas", "g", 100, 81, "Vegetables")
_add("spinach", "Spinach", "पालक", "palak|paalak|spinach|palak leaves", "g", 40, 23, "Vegetables")
_add("capsicum", "Capsicum", "शिमला मिर्च", "shimla mirch|shimla mirchi|bell pepper|capsicum|simla mirch", "g", 60, 20, "Vegetables")
_add("carrot", "Carrot", "गाजर", "gajar|gajjar|carrots|gaajar", "g", 50, 41, "Vegetables")
_add("brinjal", "Brinjal", "बैंगन", "baingan|baigan|baingun|eggplant|aubergine|brinjal", "g", 40, 25, "Vegetables")
_add("okra", "Okra", "भिंडी", "bhindi|bhendi|lady finger|ladyfinger|ladies finger|okra", "g", 60, 33, "Vegetables")
_add("bottle_gourd", "Bottle Gourd", "लौकी", "lauki|louki|ghia|doodhi|dudhi|bottle gourd", "g", 30, 14, "Vegetables")
_add("cucumber", "Cucumber", "खीरा", "kheera|kheera|khira|kakdi|cucumber", "g", 30, 15, "Vegetables")
_add("mushroom", "Mushroom", "मशरूम", "khumb|khumbi|mushrooms|mashroom", "g", 200, 22, "Vegetables")
_add("lemon", "Lemon", "नींबू", "nimbu|nimboo|lime|lemon|neembu", "pc", 5, 17, "Vegetables")
_add("green_chilli", "Green Chilli", "हरी मिर्च", "hari mirch|hari mirchi|green chili|green chilly|green chillies|hari mirchi|mirch|mirchi", "g", 80, 40, "Vegetables", staple=True)
_add("coriander_leaves", "Coriander Leaves", "धनिया पत्ती", "dhaniya|dhania|hara dhaniya|dhaniya patta|cilantro|coriander|coriander leaf", "g", 80, 23, "Vegetables", staple=True)
_add("ginger", "Ginger", "अदरक", "adrak|adarak|ginger|adrakh", "g", 120, 80, "Vegetables", staple=True)
_add("garlic", "Garlic", "लहसुन", "lehsun|lasun|lahsun|lasan|garlic|lehsan", "g", 150, 149, "Vegetables", staple=True)

# --- Dairy, eggs, meat ----------------------------------------------------------------
_add("paneer", "Paneer", "पनीर", "panir|panner|paner|cottage cheese|panneer|paneeer", "g", 360, 265, "Dairy")
_add("curd", "Curd", "दही", "dahi|dahee|yogurt|yoghurt|curd|dhai|dahi curd", "g", 80, 61, "Dairy")
_add("milk", "Milk", "दूध", "doodh|dudh|milk|dood", "ml", 56, 62, "Dairy")
_add("butter", "Butter", "मक्खन", "makhan|makkhan|butter|makhhan", "g", 540, 717, "Dairy")
_add("ghee", "Ghee", "घी", "ghee|desi ghee|ghi|clarified butter", "g", 600, 880, "Dairy", staple=True)
_add("cream", "Cream", "क्रीम", "malai|fresh cream|cream|kareem", "g", 240, 340, "Dairy")
_add("egg", "Egg", "अंडा", "anda|ande|eggs|egg|andey", "pc", 7, 72, "Protein", veg=False)
_add("chicken", "Chicken", "चिकन", "murgi|murga|chicken|chiken|murg", "g", 220, 239, "Protein", veg=False)
_add("fish", "Fish", "मछली", "machli|machhi|machhli|fish|macchi", "g", 350, 130, "Protein", veg=False)
_add("mutton", "Mutton", "मटन", "gosht|gosth|mutton|lamb|meat", "g", 750, 250, "Protein", veg=False)

# --- Grains, flours, pulses -----------------------------------------------------------
_add("rice", "Rice", "चावल", "chawal|chaawal|chaaval|basmati|rice|chawaal|bhaat", "g", 90, 360, "Grains")
_add("atta", "Wheat Flour", "आटा", "atta|aata|wheat flour|gehun ka atta|gehu atta", "g", 40, 340, "Grains")
_add("maida", "Refined Flour", "मैदा", "maida|refined flour|all purpose flour|maaida", "g", 45, 364, "Grains")
_add("besan", "Gram Flour", "बेसन", "besan|gram flour|chickpea flour|baisan", "g", 90, 387, "Grains")
_add("suji", "Semolina", "सूजी", "suji|sooji|rava|rawa|semolina|sooji rava", "g", 55, 360, "Grains")
_add("poha", "Flattened Rice", "पोहा", "poha|pauwa|flattened rice|chivda|chiwda|powa", "g", 110, 346, "Grains")
_add("toor_dal", "Toor Dal", "तूर दाल", "toor dal|arhar dal|arhar|tuvar dal|toor|tur dal|dal|daal|dhal|lentils|lentil", "g", 140, 343, "Pulses")
_add("moong_dal", "Moong Dal", "मूंग दाल", "moong dal|mung dal|moong daal|moong|mung|dal|daal|dhal|lentils|lentil", "g", 120, 347, "Pulses")
_add("masoor_dal", "Masoor Dal", "मसूर दाल", "masoor dal|masur dal|masoor|red lentils|dal|daal|dhal|lentils|lentil", "g", 100, 353, "Pulses")
_add("chana_dal", "Chana Dal", "चना दाल", "chana dal|chane ki dal|bengal gram|chana|dal|daal|dhal|lentils|lentil", "g", 100, 360, "Pulses")
_add("urad_dal", "Urad Dal", "उड़द दाल", "urad dal|urad|udad dal|black gram|dal|daal|dhal|lentils|lentil", "g", 130, 341, "Pulses")
_add("chickpeas", "Chickpeas", "छोले", "chole|chhole|kabuli chana|chana|chickpea|chickpeas|safed chana|cholay", "g", 110, 364, "Pulses")
_add("rajma", "Kidney Beans", "राजमा", "rajma|rajmah|kidney beans|kidney bean|razma", "g", 140, 333, "Pulses")

# --- Nuts, pantry staples and spices --------------------------------------------------
_add("peanuts", "Peanuts", "मूंगफली", "moongfali|mungfali|peanut|peanuts|singdana|groundnut", "g", 150, 567, "Nuts")
_add("cashew", "Cashew", "काजू", "kaju|cashews|cashew|kajoo", "g", 900, 553, "Nuts")
_add("oil", "Cooking Oil", "तेल", "tel|oil|cooking oil|mustard oil|refined oil|sarson ka tel|teil", "ml", 150, 828, "Pantry", staple=True)
_add("salt", "Salt", "नमक", "namak|namk|salt|nmak", "g", 20, 0, "Pantry", staple=True)
_add("sugar", "Sugar", "चीनी", "cheeni|chini|shakkar|sugar|sakkar", "g", 45, 387, "Pantry", staple=True)
_add("turmeric", "Turmeric", "हल्दी", "haldi|haldee|turmeric|halddi", "g", 200, 312, "Spices", staple=True)
_add("chilli_powder", "Red Chilli Powder", "लाल मिर्च पाउडर", "lal mirch|lal mirchi|red chilli|red chili|chilli powder|chili powder|mirch powder|lal mirch powder|mirch|mirchi", "g", 300, 282, "Spices", staple=True)
_add("coriander_powder", "Coriander Powder", "धनिया पाउडर", "dhania powder|dhaniya powder|coriander powder|dhaniya|dhania|coriander", "g", 200, 298, "Spices", staple=True)
_add("cumin", "Cumin Seeds", "जीरा", "jeera|zeera|jira|cumin|cumin seeds|jeeraa", "g", 350, 375, "Spices", staple=True)
_add("mustard_seeds", "Mustard Seeds", "राई", "rai|sarson|mustard|mustard seeds|raai", "g", 120, 508, "Spices", staple=True)
_add("garam_masala", "Garam Masala", "गरम मसाला", "garam masala|garam masaala|garammasala", "g", 600, 350, "Spices", staple=True)
_add("kasuri_methi", "Kasuri Methi", "कसूरी मेथी", "kasuri methi|kasoori methi|dried fenugreek|kasuri", "g", 300, 300, "Spices", staple=True)

# Ingredients that take part in recognition and chip selection, in display order.
ALL_IDS = list(CATALOG)


def get(ingredient_id: str) -> Ingredient:
    return CATALOG[ingredient_id]
