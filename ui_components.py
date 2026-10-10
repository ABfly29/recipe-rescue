"""Pure HTML builders for the Streamlit UI (kept separate so they can be unit tested).

Every value that comes from the database is HTML-escaped. Unknown values (cost, calories,
time, servings) are shown as "n/a" rather than guessed.
"""
import html
from urllib.parse import quote, urlparse

_TINTS = ["#E3EEDF", "#F6E6C8", "#E9E2F0", "#DCEBF0", "#F4DCD3", "#E6EAD0"]
_MEAL_EMOJI = {"Breakfast": "🍳", "Lunch": "🍛", "Dinner": "🍲", "Snacks": "🥟", "Dessert": "🍮"}


def esc(text) -> str:
    return html.escape(str(text))


def _fallback_svg(emoji: str, tint: str) -> str:
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='480' height='240'>"
           f"<rect width='100%' height='100%' fill='{tint}'/>"
           f"<text x='50%' y='54%' font-size='96' text-anchor='middle' "
           f"dominant-baseline='middle'>{emoji}</text></svg>")
    return "data:image/svg+xml;utf8," + quote(svg)


def emoji_for(recipe) -> str:
    return recipe.emoji or (_MEAL_EMOJI.get(recipe.meals[0], "🍽️") if recipe.meals else "🍽️")


def safe_url(url) -> str:
    """Only http(s) URLs are ever placed in links or CSS."""
    if url and urlparse(url).scheme in ("http", "https") and "'" not in url and '"' not in url:
        return url
    return ""


def image_css(recipes) -> str:
    """CSS class per displayed recipe: photo (if any) over a themed illustration fallback."""
    rules = []
    for r in recipes:
        layers = []
        if safe_url(r.image_url):
            layers.append(f"url('{r.image_url}')")
        layers.append(f"url(\"{_fallback_svg(emoji_for(r), _TINTS[r.id % len(_TINTS)])}\")")
        rules.append(f".rimg-{r.id}{{background-image:{','.join(layers)};}}")
    return "<style>" + "".join(rules) + "</style>"


def chips(names, cls="") -> str:
    return "".join(f'<span class="chip {cls}">{esc(n)}</span>' for n in names)


def rupees(value: float) -> str:
    return f"₹{value:,.0f}"


def _veg_class(recipe) -> str:
    return {True: "", False: " nonveg", None: " unknownveg"}[recipe.vegetarian]


def card_html(match) -> str:
    r = match.recipe
    badge = ('<span class="badge">Ready to cook</span>' if match.exact
             else f'<span class="badge near">Missing {len(match.missing)}</span>')
    time_txt = f"{r.time_min} min" if r.time_min else "time n/a"
    cost = (f"≈ {rupees(r.est_total_cost)} · {rupees(r.cost_per_serving)}/serving"
            if r.est_total_cost is not None and r.cost_per_serving is not None
            else "cost n/a")
    kcal = (f"🔥 ≈ {r.kcal_per_serving:,.0f} kcal/serving" if r.kcal_per_serving is not None
            else "🔥 calories n/a")
    serves = f"Serves {r.servings}" if r.servings else "servings n/a"
    tags = [f"⏱ {time_txt}"]
    if r.difficulty:
        tags.append(r.difficulty)
    tags += [cost, kcal, serves]
    meta = "".join(f"<span>{esc(t)}</span>" for t in tags)
    sub = " · ".join(x for x in (r.cuisine, r.course) if x)
    missing = (f'<div class="chips"><span class="tiny">Missing: </span>{chips(match.missing, "miss")}</div>'
               if match.missing else "")
    return (
        f'<div class="rcard"><div class="rimg rimg-{r.id}">{badge}</div>'
        f'<div class="rbody"><h3><span class="vegdot{_veg_class(r)}"></span>{esc(r.display_name)}</h3>'
        f'<div class="tiny" style="margin:-.3rem 0 .4rem">{esc(sub)}</div>'
        f'<div class="meta">{meta}</div>{missing}</div></div>'
    )


def details_html(match) -> str:
    """Ingredient list (with cost/kcal for curated recipes) for the expandable section."""
    r = match.recipe
    missing = set(match.missing)
    if r.is_curated:
        rows = "".join(
            f'<tr class="{"miss" if i.name in missing else ""}"><td>{esc(i.name)}'
            f'{" (missing)" if i.name in missing else ""}</td><td>{esc(i.quantity_text)} {esc(i.unit)}</td>'
            f'<td class="n">≈ ₹{i.est_cost:,.1f}</td><td class="n">≈ {i.est_kcal:,.0f}</td></tr>'
            for i in r.ingredients)
        return (
            '<table class="est-table"><tr><th>Ingredient</th><th>Quantity</th>'
            '<th class="n">Cost</th><th class="n">kcal</th></tr>' + rows +
            f'<tr><th>Total ({r.servings} servings)</th><th></th>'
            f'<th class="n">≈ ₹{r.est_total_cost:,.0f}</th><th class="n">≈ {r.est_total_kcal:,.0f}</th></tr>'
            '</table><p class="tiny">Illustrative estimates only, not exact values.</p>')
    items = "".join(
        f'<li class="{"miss" if i.name in missing else ""}">{esc(i.original_text)}'
        f'{" <b>(missing)</b>" if i.name in missing else ""}</li>' for i in r.ingredients)
    return (f'<ul class="ing-list">{items}</ul>'
            '<p class="tiny">Ingredients exactly as published. Cost and calories are not available '
            'for this recipe.</p>')


def source_link_html(recipe) -> str:
    url = safe_url(recipe.source_url)
    if not url:
        return ""
    host = urlparse(url).netloc.replace("www.", "")
    return f'<p class="tiny">Source: <a href="{esc(url)}" target="_blank" rel="noopener">{esc(host)}</a></p>'
