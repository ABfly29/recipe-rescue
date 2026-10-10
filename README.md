# Recipe Rescue

Cook with what you have. Type ingredients in Hindi, English or Hinglish (typos are fine), pick a
meal, and get exact matches plus recipes one or two ingredients away. All recipes live in a local
SQLite database; there are no AI APIs, accounts or network calls.

## Setup and run

```
pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. The app creates `data/recipe_rescue.db` on first start and loads 27
starter recipes. To load the full dataset, import it once (below). After that the app reads
recipes **only** from SQLite; the dataset files are never needed again.

## Importing the dataset

The "6000+ Indian Food Recipes" files (CSV and XLSX) are not part of this repository and must not
be committed (`*.csv`, `*.xlsx` and `data/` are git-ignored).

```
python -m tools.import_dataset "C:\path\to\dataset folder" --dry-run   # parse and report, write nothing
python -m tools.import_dataset "C:\path\to\dataset folder"             # real import
```

The CSV needs nothing extra. To also read the XLSX copy, run `pip install -r requirements-import.txt`
(otherwise it is skipped with a note; it contains the same rows).

What the import does:

- **Idempotent**: recipes are keyed by source URL and by a hash of name + ingredients + instructions,
  so rerunning never creates duplicates. Existing rows are never modified, dropped or reset.
- **Atomic**: one transaction; any error rolls everything back. An automatic backup of an existing
  database is taken first (`data/backups/`).
- **Faithful**: original names, ingredient text and instructions are stored untouched. Parsed
  ingredient rows add a normalised name and a matching key. A time or servings value of 0 in the
  source means "unknown" and is stored as NULL. Cost, calories and quantities are never invented:
  dataset recipes have no price or calorie data, so those columns are NULL and the app shows "n/a".
- **Validated**: records with no name, ingredients or instructions are rejected (kept in
  `import_rejects` with the full original row). A report with total rows, imported, duplicates,
  rejected and missing-field counts is printed and saved to `data/import_reports/`.

Derived fields (documented, rule-based, reversible): `recipe_meals` maps the dataset's `Course`
to Breakfast / Lunch / Dinner / Snacks / Dessert (unrecognised values get no meal);
`diet_type` maps `Diet` (Diabetic Friendly, Gluten Free and Sugar Free say nothing about meat, so
they stay `unknown`); `is_staple` marks oil, salt, spices, ginger, garlic and chillies, which
matching assumes you own unless you switch that off in Filters.

## Backup and preserving your data

`data/recipe_rescue.db` is **not** in Git. It holds your imported data, so keep it safe:

```
python -m tools.backup_db                  # data/backups/recipe_rescue_<timestamp>.db (keeps newest 10)
python -m tools.backup_db --keep 30
python -m tools.backup_db --verify data/backups/<file>.db
```

Backups use SQLite's online backup API (safe while the app runs) and are integrity-checked. To
restore, stop the app and copy a verified backup over `data/recipe_rescue.db`. Copy `data/backups/`
to cloud storage or an external drive regularly; the whole `data/` folder is git-ignored. If the
database is lost, rerunning the import against the dataset files rebuilds it.

## Tests

```
python -m unittest discover -s tests -t .
```

Tests use temporary databases and a small synthetic fixture; they never touch `data/recipe_rescue.db`.

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit UI (reads SQLite only) |
| `recipe_store.py` | Database-backed matching, ranking, search and recipe loading |
| `db.py` | Connection and additive schema migrations |
| `tools/import_dataset.py` | One-off dataset importer and report |
| `tools/backup_db.py` | Database backup / verify |
| `ingredient_parser.py`, `recipe_ingest.py` | Ingredient line parsing; idempotent write path |
| `curated_seed.py`, `recipe_data.py`, `nutrition.py` | 27 starter recipes with illustrative cost/calories |
| `normalizer.py`, `ingredient_catalog.py` | Hindi/English/Hinglish recognition and ingredient vocabulary |
| `ui_components.py`, `styles.py` | HTML cards and CSS |
| `legacy_react/` | Earlier React prototype (safe to delete) |

## Notes

- The ingredient picker offers the built-in catalogue plus the common ingredients found in the
  database (e.g. karela). Restart the app after a new import so the vocabulary reloads.
- Starter-recipe costs and calories are illustrative estimates, not exact values.
- Recipe pages link back to their source site (Archana's Kitchen URLs from the dataset).
