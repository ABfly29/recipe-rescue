"""Global CSS for the Recipe Rescue UI."""

CSS = """
<style>
:root {
  --green: #1F5C3A; --green-dark: #144329; --green-soft: #E3EEDF;
  --cream: #FBF6E9; --cream-deep: #F1EAD3; --ink: #1E2A22; --muted: #5C6B60;
  --line: #E2D9BD; --amber: #A8530B; --amber-soft: #FBE7CF;
}
.stApp { background: var(--cream); color: var(--ink); }
/* quiet Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; height: 0; }
.block-container { max-width: 1080px; padding: 0 1.25rem 4rem; }
h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; color: var(--green-dark); letter-spacing: -.01em; }

/* top navigation */
.nav { display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: 1.1rem 0; border-bottom: 1px solid var(--line); margin-bottom: 1.8rem; }
.brand { display: flex; align-items: center; gap: .6rem; font-family: Georgia, serif;
  font-size: 1.35rem; font-weight: 700; color: var(--green-dark); }
.brand .logo { background: var(--green); border-radius: 10px; width: 36px; height: 36px;
  display: inline-flex; align-items: center; justify-content: center; font-size: 1.15rem; }
.nav-links { display: flex; gap: 1.4rem; font-size: .92rem; }
.nav-links a { color: var(--ink) !important; text-decoration: none; font-weight: 500; }
.nav-links a:hover { color: var(--green) !important; text-decoration: underline; }

/* hero */
.hero h1 { font-size: 3rem; line-height: 1.05; margin: 0 0 .5rem; }
.hero p { font-size: 1.1rem; color: var(--muted); max-width: 36rem; margin: 0 0 1.4rem; }
.eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .75rem;
  font-weight: 700; color: var(--green); margin-bottom: .5rem; }

/* inputs */
[data-testid="stForm"] { background: #fff; border: 1px solid var(--line); border-radius: 18px;
  padding: 1.1rem 1.2rem; box-shadow: 0 6px 24px rgba(31,92,58,.08); }
[data-testid="stTextInput"] input { font-size: 1.15rem; padding: .85rem 1rem; color: var(--ink);
  background: #fff; border-radius: 12px; }
[data-testid="stTextInput"] label p { font-weight: 600; font-size: 1rem; color: var(--green-dark); }
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; border: 1px solid var(--line); background: #fff; color: var(--ink);
  font-weight: 600; padding: .55rem 1.1rem; }
.stButton > button:hover { border-color: var(--green); color: var(--green); }
[data-testid="stFormSubmitButton"] > button, .stButton > button[kind="primary"] {
  background: var(--green); border-color: var(--green); }
[data-testid="stFormSubmitButton"] > button p, .stButton > button[kind="primary"] p { color: #fff; }
[data-testid="stFormSubmitButton"] > button:hover { background: var(--green-dark); color: #fff; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] { background: var(--green-soft); color: var(--green-dark);
  border-radius: 999px; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] span { color: var(--green-dark); }

/* sections */
.section-title { display: flex; align-items: baseline; gap: .7rem; margin: 2.2rem 0 .3rem; }
.section-title h2 { margin: 0; font-size: 1.7rem; }
.section-title .count { background: var(--green-soft); color: var(--green-dark); border-radius: 999px;
  padding: .1rem .7rem; font-size: .85rem; font-weight: 600; }
.section-sub { color: var(--muted); margin: 0 0 1rem; }
.label { font-weight: 700; font-size: .8rem; text-transform: uppercase; letter-spacing: .1em;
  color: var(--muted); margin: 1.4rem 0 .4rem; }

/* summary stats */
.stats { display: flex; gap: .8rem; flex-wrap: wrap; margin: 1rem 0 .4rem; }
.stat { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: .6rem 1rem; min-width: 110px; }
.stat b { display: block; font-family: Georgia, serif; font-size: 1.5rem; color: var(--green-dark); }
.stat span { font-size: .78rem; color: var(--muted); }

/* notices */
.note { background: var(--green-soft); color: var(--green-dark); border-radius: 12px;
  padding: .55rem .9rem; margin: .5rem 0; font-size: .92rem; }
.note.warn { background: var(--amber-soft); color: #6B3306; }
.empty { background: #fff; border: 1px dashed var(--line); border-radius: 18px; padding: 2rem 1.5rem;
  text-align: center; color: var(--muted); margin: 1rem 0; }
.empty h3 { margin: 0 0 .4rem; }

/* recipe card */
.rcard { background: #fff; border: 1px solid var(--line); border-radius: 18px; overflow: hidden;
  box-shadow: 0 2px 12px rgba(31,92,58,.07); margin-bottom: .4rem; }
.rimg { height: 160px; background-size: cover; background-position: center; position: relative; }
.badge { position: absolute; top: 10px; left: 10px; background: var(--green); color: #fff;
  font-size: .75rem; font-weight: 700; padding: .2rem .65rem; border-radius: 999px; }
.badge.near { background: var(--amber); }
.rbody { padding: .85rem 1rem 1rem; }
.rbody h3 { margin: 0 0 .5rem; font-size: 1.15rem; }
.meta { display: flex; flex-wrap: wrap; gap: .3rem .5rem; font-size: .82rem; color: var(--ink); }
.meta span { background: var(--cream); border-radius: 8px; padding: .15rem .5rem; }
.vegdot { display: inline-block; width: 11px; height: 11px; border-radius: 3px; border: 2px solid #2e8b57;
  position: relative; margin-right: .3rem; vertical-align: -1px; }
.vegdot.nonveg { border-color: #b3261e; }
.vegdot::after { content: ""; position: absolute; inset: 2px; border-radius: 50%; background: #2e8b57; }
.vegdot.nonveg::after { background: #b3261e; }
.vegdot.unknownveg { border-color: #8a8a8a; }
.vegdot.unknownveg::after { background: #8a8a8a; }
.ing-list { margin: 0 0 .4rem; padding-left: 1.1rem; font-size: .88rem; }
.ing-list li.miss { color: #6B3306; }
.chips { margin-top: .6rem; }
.chip { display: inline-block; background: var(--green-soft); color: var(--green-dark); border-radius: 999px;
  padding: .12rem .65rem; font-size: .78rem; margin: 0 .3rem .3rem 0; }
.chip.miss { background: var(--amber-soft); color: #6B3306; }
.tiny { font-size: .78rem; color: var(--muted); }
.est-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.est-table th, .est-table td { text-align: left; padding: .3rem .4rem; border-bottom: 1px solid var(--line); }
.est-table td.n, .est-table th.n { text-align: right; }
.est-table tr.miss td { color: #6B3306; }

@media (max-width: 640px) {
  .hero h1 { font-size: 2.1rem; }
  .nav-links { display: none; }
  .rimg { height: 140px; }
  .rbody { padding: .7rem .8rem .8rem; }
  .section-title h2 { font-size: 1.4rem; }
}
</style>
"""
