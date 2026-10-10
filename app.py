"""Recipe Rescue - cook with what you have. Run with: python -m streamlit run app.py

All recipes are read from the local SQLite database (data/recipe_rescue.db). To load the
full recipe dataset into it, see README.md ("Importing the dataset").
"""
import streamlit as st

import db
import recipe_store as store
from normalizer import parse_ingredients
from recipe_data import MEALS
from styles import CSS
from ui_components import card_html, details_html, esc, image_css, source_link_html

st.set_page_config(page_title="Recipe Rescue · Aaj kya banayein?", page_icon="🍛", layout="wide")

MEAL_ICONS = {"Breakfast": "🌅", "Lunch": "☀️", "Dinner": "🌙", "Snacks": "🍿"}
SAMPLE_INPUT = "panor, onion, tomato, rice, dahi"
GRID_COLUMNS = 3


@st.cache_resource(show_spinner="Opening recipe database…")
def init_store(path: str):
    """Create/migrate the database once per process and load the ingredient vocabulary."""
    conn = store.open_store(path)
    try:
        return store.load_vocabulary(conn), store.summary(conn)
    finally:
        conn.close()


DB_PATH = str(db.db_path())
vocab, stats = init_store(DB_PATH)
conn = db.connect(DB_PATH)

# ---- session state -------------------------------------------------------------------
for key, default in (("ingredients", []), ("pending", []), ("unknown", []),
                     ("corrections", []), ("raw_text", "")):
    st.session_state.setdefault(key, default)


def _add_ids(ids):
    current = list(st.session_state.ingredients)
    st.session_state.ingredients = current + [i for i in ids if i not in current]


def on_add():
    result = parse_ingredients(st.session_state.raw_text, vocab.index)
    _add_ids(result.accepted)
    st.session_state.pending = [{"raw": d.raw, "candidates": d.candidates} for d in result.pending]
    st.session_state.unknown = result.unknown
    st.session_state.corrections = result.corrections
    st.session_state.raw_text = ""


def on_sample():
    st.session_state.raw_text = SAMPLE_INPUT
    on_add()


def on_confirm(index, ingredient_id):
    _add_ids([ingredient_id])
    st.session_state.pending.pop(index)


def on_skip(index):
    st.session_state.pending.pop(index)


def on_clear():
    st.session_state.ingredients = []
    st.session_state.pending = []
    st.session_state.unknown = []
    st.session_state.corrections = []


def short_label(ingredient_id):
    return vocab.label(ingredient_id).split(" · ")[0]


# ---- page chrome ---------------------------------------------------------------------
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="nav"><div class="brand"><span class="logo">🍛</span>Recipe Rescue</div>'
    '<div class="nav-links"><a href="#discover">Discover</a><a href="#results">Recipes</a>'
    '<a href="#about-estimates">About estimates</a></div></div>'
    '<div class="hero" id="discover"><div class="eyebrow">North Indian home cooking</div>'
    '<h1>Aaj kya banayein?</h1>'
    '<p>Tell us what is in your kitchen, in Hindi, English or Hinglish. '
    'We will find what you can cook right now, or with one or two more ingredients.</p></div>',
    unsafe_allow_html=True,
)

# ---- ingredient input ----------------------------------------------------------------
with st.form("add_ingredients", border=True):
    st.text_input("What ingredients do you have?", key="raw_text",
                  placeholder="panor, onion, tomato, rice, dahi")
    st.form_submit_button("Add ingredients", type="primary", on_click=on_add, width="stretch")

if st.session_state.corrections:
    fixes = ", ".join(f"“{esc(raw)}” → {esc(short_label(i))}"
                      for raw, i in st.session_state.corrections)
    st.markdown(f'<div class="note">Auto-corrected: {fixes}. Remove any chip below if that is wrong.</div>',
                unsafe_allow_html=True)

for idx, item in enumerate(list(st.session_state.pending)):
    st.markdown(f'<div class="note warn">Not sure about “<b>{esc(item["raw"])}</b>”. Which did you mean?</div>',
                unsafe_allow_html=True)
    cols = st.columns(len(item["candidates"]) + 1)
    for col, cand in zip(cols, item["candidates"]):
        col.button(short_label(cand), key=f"confirm_{idx}_{cand}", on_click=on_confirm,
                   args=(idx, cand), width="stretch")
    cols[-1].button("None of these", key=f"skip_{idx}", on_click=on_skip, args=(idx,),
                    width="stretch")

if st.session_state.unknown:
    names = ", ".join(f"“{esc(u)}”" for u in st.session_state.unknown)
    st.markdown(f'<div class="note warn">We did not recognise {names}. '
                'Check the spelling, or pick it from the list below.</div>', unsafe_allow_html=True)

st.markdown('<div class="label">Your ingredients</div>', unsafe_allow_html=True)
st.multiselect("Detected ingredients (edit, remove or add)", options=vocab.options,
               format_func=vocab.label, key="ingredients",
               placeholder="Type above, or search and pick an ingredient here",
               label_visibility="collapsed")
have = list(st.session_state.ingredients)

# ---- meal and filters ----------------------------------------------------------------
st.markdown('<div class="label">Meal</div>', unsafe_allow_html=True)
meal = st.segmented_control("Meal", MEALS, default="Dinner", key="meal",
                            format_func=lambda m: f"{MEAL_ICONS[m]} {m}",
                            label_visibility="collapsed", width="stretch")
meal = meal or "Dinner"   # the control can be deselected; fall back to a sensible meal

with st.expander("Filters", expanded=False):
    f1, f2, f3, f4, f5 = st.columns(5)
    diet = f1.selectbox("Diet", ["All", "Vegetarian", "Non-vegetarian"])
    max_time = f2.select_slider("Max cooking time", options=[0, 20, 30, 45, 60],
                                format_func=lambda v: "Any" if v == 0 else f"{v} min",
                                help="Recipes with no cooking time in the source are hidden when a limit is set.")
    budget = f3.select_slider("Budget per serving", options=[0, 30, 50, 80, 120],
                              format_func=lambda v: "Any" if v == 0 else f"≤ ₹{v}",
                              help="Only recipes with a price estimate can be shown when a budget is set.")
    max_missing = f4.selectbox("Max missing ingredients", [0, 1, 2], index=2)
    per_section = f5.selectbox("Recipes per section", [12, 24, 48], index=0)
    assume_staples = st.toggle("I have basic staples (oil, salt, spices, ginger, garlic, chillies)",
                               value=True)

# ---- results -------------------------------------------------------------------------
st.markdown('<div id="results"></div>', unsafe_allow_html=True)


def render_grid(matches):
    st.markdown(image_css([m.recipe for m in matches]), unsafe_allow_html=True)
    for start in range(0, len(matches), GRID_COLUMNS):
        cols = st.columns(GRID_COLUMNS, gap="medium")
        for col, m in zip(cols, matches[start:start + GRID_COLUMNS]):
            with col:
                st.markdown(card_html(m), unsafe_allow_html=True)
                with st.expander("Ingredients & method"):
                    st.markdown(details_html(m), unsafe_allow_html=True)
                    st.markdown("**Method**")
                    if m.recipe.is_curated:
                        for n, step in enumerate(m.recipe.method.split("\n"), 1):
                            st.markdown(f"{n}. {step}")
                    else:
                        st.text(m.recipe.method)
                    st.markdown(source_link_html(m.recipe), unsafe_allow_html=True)


def section(title, subtitle, matches, total):
    shown = f"{len(matches)} of {total}" if total > len(matches) else str(total)
    st.markdown(f'<div class="section-title"><h2>{title}</h2>'
                f'<span class="count">{shown}</span></div>'
                f'<p class="section-sub">{subtitle}</p>', unsafe_allow_html=True)
    render_grid(matches)


def empty(title, body):
    st.markdown(f'<div class="empty"><h3>{title}</h3>{body}</div>', unsafe_allow_html=True)


tab_match, tab_search = st.tabs(["Cook with what I have", "Search recipes"])

with tab_match:
    if not have:
        empty("Start with what is in your kitchen",
              "Type a few ingredients above, like <b>aloo, pyaz, tamatar, dahi</b>.")
        st.button("Try an example", on_click=on_sample)
    else:
        rows = store.find_matches(conn, have, meal, assume_staples, max_missing, diet, max_time, budget)
        unfiltered = store.find_matches(conn, have, meal, assume_staples, max_missing) if not rows else rows
        exact_rows = [r for r in rows if r.have == r.required]
        near_rows = [r for r in rows if r.have < r.required]
        st.markdown(
            f'<div class="stats"><div class="stat"><b>{len(have)}</b><span>ingredients</span></div>'
            f'<div class="stat"><b>{len(exact_rows)}</b><span>ready to cook</span></div>'
            f'<div class="stat"><b>{len(near_rows)}</b><span>almost there</span></div></div>',
            unsafe_allow_html=True)
        st.button("Clear ingredients", on_click=on_clear)

        if exact_rows:
            section("Exact Matches", f"You can make these {meal.lower()} recipes right now.",
                    store.load_matches(conn, exact_rows[:per_section], have, assume_staples),
                    len(exact_rows))
        if near_rows:
            section("You're Almost There", "Just one or two ingredients away.",
                    store.load_matches(conn, near_rows[:per_section], have, assume_staples),
                    len(near_rows))
        if not rows:
            if unfiltered:
                empty("Your filters hide every recipe",
                      "Try a different diet, a longer cooking time or a bigger budget.")
            else:
                empty(f"No {meal.lower()} recipes yet",
                      "Add a few more ingredients, allow more missing items, or try another meal.")

with tab_search:
    query = st.text_input("Search by recipe name or ingredient", key="search_text",
                          placeholder="e.g. paneer tikka, karela, rajma")
    if query.strip():
        found = store.to_matches(store.search_recipes(conn, query, diet=diet, limit=per_section),
                                 have, assume_staples)
        if found:
            st.caption(f"Showing up to {per_section} recipes. Missing ingredients are based on your list above.")
            render_grid(found)
        else:
            empty("No recipes found", "Try fewer words or a different spelling.")
    else:
        empty("Search the recipe database", "Type part of a recipe name or an ingredient.")

if stats["imported"] == 0:
    st.markdown('<div class="note warn" style="margin-top:2rem">Only the starter recipes are loaded. '
                'Import the full dataset into the local database (see README: “Importing the dataset”).</div>',
                unsafe_allow_html=True)
st.markdown(
    '<div id="about-estimates" class="note" style="margin-top:3rem">'
    f'<b>About the data.</b> {stats["recipes"]:,} recipes in the local database. Cost and calorie '
    'estimates exist only for the starter recipes and use illustrative average Indian prices and '
    'typical nutrition values; imported recipes show “n/a” because the source has no such data.</div>',
    unsafe_allow_html=True)
conn.close()
