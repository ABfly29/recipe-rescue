"""Import the "6000+ Indian Food Recipes" dataset (CSV and/or XLSX) into the SQLite database.

    python -m tools.import_dataset "C:\\path\\to\\dataset folder"
    python -m tools.import_dataset "<folder>" --dry-run      # report only, nothing written

The dataset files are only read here, once; the app never touches them. The import is
idempotent (recipes are keyed by source URL and by a content hash), additive (existing rows
are never changed or removed), atomic (one transaction) and backs the database up first.
Unknown values (zero times, blank fields) are stored as NULL, never guessed.
"""
import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import db
from curated_seed import seed_curated
from ingredient_parser import parse_ingredient_list
from recipe_ingest import EXISTS, content_hash, insert_recipe, now_iso, refresh_vocab
from tools.backup_db import backup

SOURCE = "indian_food_dataset"
REPORT_DIR = db.PROJECT_DIR / "data" / "import_reports"
FIELDS = ["RecipeName", "TranslatedRecipeName", "Ingredients", "TranslatedIngredients",
          "PrepTimeInMins", "CookTimeInMins", "TotalTimeInMins", "Servings", "Cuisine",
          "Course", "Diet", "Instructions", "TranslatedInstructions", "URL"]
ZERO_MEANS_UNKNOWN = ("PrepTimeInMins", "CookTimeInMins", "TotalTimeInMins")
SERVINGS_OUTLIER = 30

DIET_TYPES = {
    "vegetarian": "vegetarian", "high protein vegetarian": "vegetarian",
    "no onion no garlic (sattvic)": "vegetarian", "vegan": "vegan",
    "non vegeterian": "non_vegetarian", "high protein non vegetarian": "non_vegetarian",
    "eggetarian": "eggetarian",
    # Diabetic Friendly / Gluten Free / Sugar Free Diet say nothing about meat -> unknown
}


def meals_for_course(course: str) -> list:
    """Map the dataset's Course to app meals as ``[(meal, is_primary)]`` (may be empty)."""
    c = (course or "").strip().lower()
    if "breakfast" in c:
        return [("Breakfast", True)]
    if c == "brunch":
        return [("Breakfast", True), ("Lunch", True)]
    if c == "lunch":
        return [("Lunch", True)]
    if c == "dinner":
        return [("Dinner", True)]
    if c in ("main course", "side dish", "one pot dish"):
        return [("Lunch", True), ("Dinner", True)]
    if c in ("snack", "appetizer"):
        return [("Snacks", True)]
    if c == "dessert":
        return [("Dessert", True)]
    return []   # e.g. dirty values such as 'Vegetarian' or 'Vegan' in the Course column


# --- reading -----------------------------------------------------------------------
def read_csv(path: Path):
    csv.field_size_limit(2 ** 30)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


def read_xlsx(path: Path):
    import openpyxl  # only needed when importing from Excel; not an app dependency
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = wb.active.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    for values in rows:
        yield {h: ("" if v is None else str(v)) for h, v in zip(header, values)}
    wb.close()


def find_files(folder: Path) -> list:
    if folder.is_file():
        return [folder]
    files = sorted(folder.glob("*.csv")) + sorted(folder.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .csv or .xlsx files found in {folder}")
    return files


# --- per-row processing --------------------------------------------------------------
def clean(value) -> str:
    return (value or "").strip() if isinstance(value, str) or value is None else str(value).strip()


def to_int(value):
    try:
        return int(float(clean(value)))
    except ValueError:
        return None


def positive_or_none(value):
    n = to_int(value)
    return n if n and n > 0 else None


def build_record(row: dict, run_id: int):
    """Return ``(record, parsed_ingredients, meals, rejection_reasons)`` for a raw row."""
    name = clean(row.get("RecipeName"))
    instructions = row.get("Instructions") or ""
    ingredients_raw = row.get("Ingredients") or ""
    translated_ingredients = row.get("TranslatedIngredients") or ""
    parse_source = translated_ingredients.strip() or ingredients_raw.strip()
    parsed = parse_ingredient_list(parse_source)

    reasons = []
    if not name:
        reasons.append("missing_name")
    if not instructions.strip():
        reasons.append("missing_instructions")
    if not parsed:
        reasons.append("missing_ingredients")
    if reasons:
        return None, None, None, reasons

    url = clean(row.get("URL"))
    srno = to_int(row.get("Srno"))
    record = {
        "source": SOURCE,
        "source_key": url or f"srno:{srno}",
        "source_srno": srno,
        "source_url": url or None,
        "content_hash": content_hash(name, ingredients_raw or translated_ingredients, instructions),
        "name": name,
        "translated_name": clean(row.get("TranslatedRecipeName")) or None,
        "cuisine": clean(row.get("Cuisine")) or None,
        "course": clean(row.get("Course")) or None,
        "diet": clean(row.get("Diet")) or None,
        "diet_type": DIET_TYPES.get(clean(row.get("Diet")).lower(), "unknown"),
        "prep_time_min": positive_or_none(row.get("PrepTimeInMins")),
        "cook_time_min": positive_or_none(row.get("CookTimeInMins")),
        "total_time_min": positive_or_none(row.get("TotalTimeInMins")),
        "servings": positive_or_none(row.get("Servings")),
        "ingredients_raw": ingredients_raw or None,
        "translated_ingredients_raw": translated_ingredients or None,
        "instructions": instructions,
        "translated_instructions": row.get("TranslatedInstructions") or None,
        "import_run_id": run_id,
        "created_at": now_iso(),
    }
    return record, parsed, meals_for_course(record["course"]), []


def missing_fields(row: dict, stats: Counter):
    for field in FIELDS:
        value = (row.get(field) or "").strip() if isinstance(row.get(field), str) else row.get(field)
        if value in (None, ""):
            stats[f"{field}: blank"] += 1
        elif field in ZERO_MEANS_UNKNOWN and to_int(value) == 0:
            stats[f"{field}: 0 (stored as unknown/NULL)"] += 1
        elif field == "Servings" and to_int(value) in (None, 0):
            stats["Servings: 0 (stored as unknown/NULL)"] += 1


# --- the import ------------------------------------------------------------------------
def run_import(conn, files: list, dry_run: bool = False) -> dict:
    started = now_iso()
    run_id = conn.execute(
        "INSERT INTO import_runs (started_at, source_files, status) VALUES (?, ?, 'running')",
        (started, json.dumps([str(f) for f in files]))).lastrowid
    conn.commit()

    report = {"started_at": started, "dry_run": dry_run, "files": {},
              "totals": Counter(), "missing_fields": Counter(), "reject_reasons": Counter(),
              "ingredient_lines": Counter(), "meal_mapping": Counter(), "diet_types": Counter(),
              "notes": []}
    seen_keys, seen_hashes, seen_rows, rejected_keys = {}, set(), set(), set()
    try:
        conn.execute("BEGIN")
        for path in files:
            reader = read_xlsx if path.suffix.lower() == ".xlsx" else read_csv
            if reader is read_xlsx:
                try:
                    import openpyxl  # noqa: F401
                except ImportError:
                    report["notes"].append(f"{path.name} skipped: openpyxl is not installed "
                                           "(pip install -r requirements-import.txt)")
                    continue
            per_file = Counter()
            for row in reader(path):
                per_file["rows"] += 1
                row_key = clean(row.get("URL")) or f"srno:{clean(row.get('Srno'))}"
                if row_key not in seen_rows:      # field statistics count each recipe once
                    seen_rows.add(row_key)
                    missing_fields(row, report["missing_fields"])
                    if (to_int(row.get("Servings")) or 0) > SERVINGS_OUTLIER:
                        report["totals"]["servings_over_30 (kept as given)"] += 1
                record, parsed, meals, reasons = build_record(row, run_id)
                if reasons:
                    per_file["rejected"] += 1
                    key = row_key
                    if key not in rejected_keys:
                        rejected_keys.add(key)
                        report["totals"]["rejected_unique"] += 1
                        for reason in reasons:
                            report["reject_reasons"][reason] += 1
                    for reason in reasons:
                        conn.execute(
                            "INSERT OR IGNORE INTO import_rejects (source, source_key, reason, raw_json, "
                            "import_run_id) VALUES (?,?,?,?,?)",
                            (SOURCE, key, reason, json.dumps(row, ensure_ascii=False), run_id))
                    continue
                if record["source_key"] in seen_keys or record["content_hash"] in seen_hashes:
                    per_file["duplicate_in_input"] += 1
                    if seen_keys.get(record["source_key"], record["content_hash"]) != record["content_hash"]:
                        report["totals"]["conflicting_duplicates (same key, different content)"] += 1
                    continue
                seen_keys[record["source_key"]] = record["content_hash"]
                seen_hashes.add(record["content_hash"])
                if insert_recipe(conn, record, parsed, meals) == EXISTS:
                    per_file["already_in_database"] += 1
                    continue
                per_file["imported"] += 1
                report["diet_types"][record["diet_type"]] += 1
                for meal, _ in meals:
                    report["meal_mapping"][meal] += 1
                if not meals:
                    report["meal_mapping"]["(no meal mapped)"] += 1
                report["ingredient_lines"]["total"] += len(parsed)
                report["ingredient_lines"]["with_quantity"] += sum(bool(p.quantity_text) for p in parsed)
                report["ingredient_lines"]["mapped_to_catalogue"] += sum(bool(p.canonical_id) for p in parsed)
                report["ingredient_lines"]["flagged_staple"] += sum(p.is_staple for p in parsed)
            report["files"][path.name] = dict(per_file)
            for k, v in per_file.items():
                report["totals"][k] += v
        report["curated_seed_added"] = seed_curated(conn, commit=False)
        report["vocab_entries"] = refresh_vocab(conn)
        report["totals"]["recipes_in_database"] = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        report["finished_at"] = now_iso()
        report["status"] = "dry-run (rolled back)" if dry_run else "completed"
        report = _plain(report)
        if dry_run:
            conn.rollback()
        else:
            conn.execute("UPDATE import_runs SET finished_at=?, status='completed', report_json=? WHERE id=?",
                         (report["finished_at"], json.dumps(report, ensure_ascii=False), run_id))
            conn.commit()
        return report
    except BaseException:
        conn.rollback()
        conn.execute("UPDATE import_runs SET finished_at=?, status='failed' WHERE id=?", (now_iso(), run_id))
        conn.commit()
        raise


def _plain(obj):
    if isinstance(obj, Counter):
        return dict(obj)
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    return obj


def verify_database(conn) -> list:
    """Return a list of problems (empty = healthy)."""
    problems = []
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        problems.append("PRAGMA integrity_check failed")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        problems.append("foreign key violations found")
    checks = {
        "recipes without ingredients": "SELECT COUNT(*) FROM recipes r WHERE NOT EXISTS "
                                       "(SELECT 1 FROM recipe_ingredients i WHERE i.recipe_id = r.id)",
        "duplicate (source, source_key)": "SELECT COUNT(*) FROM (SELECT 1 FROM recipes GROUP BY source, "
                                          "source_key HAVING COUNT(*) > 1)",
        "duplicate content hashes": "SELECT COUNT(*) FROM (SELECT 1 FROM recipes GROUP BY content_hash "
                                    "HAVING COUNT(*) > 1)",
        "recipes without instructions": "SELECT COUNT(*) FROM recipes WHERE TRIM(instructions) = ''",
        "zero stored as time": "SELECT COUNT(*) FROM recipes WHERE prep_time_min = 0 OR cook_time_min = 0 "
                               "OR total_time_min = 0",
        "dataset recipes with invented cost/kcal": "SELECT COUNT(*) FROM recipes WHERE source != 'curated' "
                                                   "AND (est_total_cost IS NOT NULL OR est_total_kcal IS NOT NULL)",
    }
    for label, sql in checks.items():
        n = conn.execute(sql).fetchone()[0]
        if n:
            problems.append(f"{label}: {n}")
    return problems


def format_report(report: dict) -> str:
    t = report["totals"]
    lines = [
        "=" * 64, "RECIPE RESCUE - DATASET IMPORT REPORT", "=" * 64,
        f"Status:                      {report['status']}",
        f"Total rows read:             {t.get('rows', 0)}",
        f"Imported (new recipes):      {t.get('imported', 0)}",
        f"Already in database (skip):  {t.get('already_in_database', 0)}",
        f"Duplicates within input:     {t.get('duplicate_in_input', 0)}",
        f"Rejected records (unique):   {t.get('rejected_unique', 0)}   "
        f"({t.get('rejected', 0)} rejected rows across files)",
    ]
    for reason, n in sorted(report["reject_reasons"].items()):
        lines.append(f"    - {reason}: {n}")
    conflicts = t.get("conflicting_duplicates (same key, different content)", 0)
    lines.append(f"Duplicates whose content differs between files: {conflicts}")
    lines.append(f"Recipes now in database:     {t.get('recipes_in_database', 0)}")
    lines.append("\nPer file:")
    for name, stats in report["files"].items():
        lines.append(f"  {name}: " + ", ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    lines.append("\nMissing / unknown fields (all rows read):")
    for k, v in sorted(report["missing_fields"].items()):
        lines.append(f"  {k}: {v}")
    il = report["ingredient_lines"]
    if il:
        lines.append(f"\nIngredient lines (newly imported): {il.get('total', 0)} total, "
                     f"{il.get('with_quantity', 0)} with a quantity, "
                     f"{il.get('mapped_to_catalogue', 0)} mapped to the built-in catalogue")
    lines.append(f"Meal mapping (new recipes):  {report['meal_mapping']}")
    lines.append(f"Diet types (new recipes):    {report['diet_types']}")
    lines.append(f"Other: servings over 30 kept as given: {t.get('servings_over_30 (kept as given)', 0)}")
    lines += [f"Note: {n}" for n in report["notes"]]
    lines.append("Cost and calories for dataset recipes are NOT in the source and are stored as unknown.")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("dataset", help="folder containing the dataset files (or a single file)")
    parser.add_argument("--dry-run", action="store_true", help="parse and report, then roll back")
    parser.add_argument("--no-backup", action="store_true", help="skip the automatic pre-import backup")
    args = parser.parse_args(argv)

    files = find_files(Path(args.dataset))
    path = db.db_path()
    conn = db.connect(path)
    db.migrate(conn)
    has_data = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] > 0
    if has_data and not args.dry_run and not args.no_backup:
        conn.close()
        print(f"Backed up existing database to {backup(path)}")
        conn = db.connect(path)
    try:
        report = run_import(conn, files, dry_run=args.dry_run)
        problems = [] if args.dry_run else verify_database(conn)
    except sqlite3.Error as exc:
        print(f"Import failed and was rolled back: {exc}")
        return 1
    finally:
        conn.close()

    text = format_report(report)
    report["verification_problems"] = problems
    print(text)
    print("\nVerification:", "skipped (dry run)" if args.dry_run else ("OK" if not problems else problems))
    if not args.dry_run:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = report["finished_at"].replace(":", "").replace("-", "")
        (REPORT_DIR / f"import_{stamp}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        (REPORT_DIR / f"import_{stamp}.txt").write_text(text, encoding="utf-8")
        print(f"Report saved to {REPORT_DIR}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
