"""SQLite connection and schema migrations for Recipe Rescue.

The database lives in ``data/recipe_rescue.db`` (override with the RECIPE_RESCUE_DB
environment variable). Migrations only ever create tables/indexes that are missing;
nothing here drops, truncates or resets existing data.
"""
import os
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_DIR / "data" / "recipe_rescue.db"


def db_path() -> Path:
    return Path(os.environ.get("RECIPE_RESCUE_DB") or DEFAULT_DB_PATH)


MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,                 -- 'curated' or 'indian_food_dataset'
    source_key TEXT NOT NULL,             -- stable id within the source (URL for the dataset)
    source_srno INTEGER,                  -- original row number in the dataset, if any
    source_url TEXT,
    content_hash TEXT NOT NULL,           -- hash of normalised name+ingredients+instructions
    name TEXT NOT NULL,
    translated_name TEXT,
    cuisine TEXT,
    course TEXT,                          -- original Course value, unmodified
    diet TEXT,                            -- original Diet value, unmodified
    diet_type TEXT NOT NULL DEFAULT 'unknown',
        -- vegetarian | vegan | eggetarian | non_vegetarian | unknown (derived from diet)
    prep_time_min INTEGER,                -- NULL = unknown (the dataset uses 0 for unknown)
    cook_time_min INTEGER,
    total_time_min INTEGER,
    servings INTEGER,
    ingredients_raw TEXT,                 -- original ingredient text, untouched
    translated_ingredients_raw TEXT,
    instructions TEXT NOT NULL,           -- original instructions, untouched
    translated_instructions TEXT,
    difficulty TEXT,
    emoji TEXT,
    image_url TEXT,
    est_total_cost REAL,                  -- NULL = unknown; only set where prices are known
    est_total_kcal REAL,                  -- NULL = unknown
    estimate_basis TEXT,
    import_run_id INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (source, source_key),
    UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS recipe_meals (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    meal TEXT NOT NULL,                   -- Breakfast | Lunch | Dinner | Snacks | Dessert
    is_primary INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (recipe_id, meal)
);
CREATE INDEX IF NOT EXISTS ix_recipe_meals_meal ON recipe_meals(meal);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    original_text TEXT NOT NULL,          -- the ingredient line exactly as in the source
    quantity_text TEXT,                   -- e.g. '1-1/2'; NULL when absent
    quantity_value REAL,                  -- only when unambiguous (no ranges); else NULL
    unit TEXT,
    name_original TEXT NOT NULL,          -- ingredient name as written (without quantity/unit)
    name_normalized TEXT NOT NULL,        -- lowercase, descriptors removed, for matching
    ingredient_key TEXT NOT NULL,         -- catalogue id when recognised, else name_normalized
    canonical_id TEXT,                    -- catalogue id when recognised
    note TEXT,                            -- preparation note, e.g. 'thinly sliced'
    is_staple INTEGER NOT NULL DEFAULT 0,
    est_cost REAL,                        -- NULL = unknown
    est_kcal REAL,                        -- NULL = unknown
    UNIQUE (recipe_id, position)
);
CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_key ON recipe_ingredients(ingredient_key);
CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);

CREATE TABLE IF NOT EXISTS ingredient_vocab (
    ingredient_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    canonical_id TEXT,
    aliases TEXT NOT NULL DEFAULT '',     -- '|' separated alternative names seen in recipes
    recipe_count INTEGER NOT NULL DEFAULT 0,
    is_staple INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    source_files TEXT,
    status TEXT NOT NULL,                 -- running | completed | failed
    report_json TEXT
);

CREATE TABLE IF NOT EXISTS import_rejects (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_key TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT NOT NULL,               -- full rejected record, so nothing is lost
    import_run_id INTEGER,
    UNIQUE (source, source_key, reason)
);
"""

MIGRATIONS = {1: MIGRATION_1}


def connect(path=None) -> sqlite3.Connection:
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Apply any missing migrations (idempotent, additive only). Returns schema version."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number in sorted(MIGRATIONS):
        if number > version:
            conn.executescript(MIGRATIONS[number])
            conn.execute(f"PRAGMA user_version = {number}")
            conn.commit()
            version = number
    return version
