"""Back up the Recipe Rescue SQLite database.

    python -m tools.backup_db              # writes data/backups/recipe_rescue_<timestamp>.db
    python -m tools.backup_db --keep 20    # keep the 20 newest backups (default 10)
    python -m tools.backup_db --verify data/backups/recipe_rescue_20260101_120000.db

Uses SQLite's online backup API, so it is safe even while the app is running.
To restore, stop the app and copy a verified backup over data/recipe_rescue.db.
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from db import PROJECT_DIR, db_path

BACKUP_DIR = PROJECT_DIR / "data" / "backups"
PREFIX = "recipe_rescue_"


def verify(path) -> dict:
    """Integrity check plus basic row counts for a database file (opened read-only)."""
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("recipes", "recipe_ingredients", "recipe_meals")}
    finally:
        conn.close()
    return {"integrity": integrity, **counts}


def backup(source=None, dest_dir=None, keep: int = 10) -> Path:
    source = Path(source) if source else db_path()
    if not source.exists():
        raise FileNotFoundError(f"No database to back up at {source}")
    dest_dir = Path(dest_dir) if dest_dir else BACKUP_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{PREFIX}{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    src, dst = sqlite3.connect(source), sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    result = verify(dest)
    if result["integrity"] != "ok":
        dest.unlink()
        raise RuntimeError(f"Backup failed integrity check: {result['integrity']}")
    if keep > 0:   # prune only files this tool created
        old = sorted(dest_dir.glob(f"{PREFIX}*.db"))[:-keep]
        for path in old:
            path.unlink()
    return dest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--keep", type=int, default=10, help="number of backups to keep")
    parser.add_argument("--verify", metavar="FILE", help="verify an existing backup and exit")
    args = parser.parse_args(argv)
    if args.verify:
        print(verify(args.verify))
        return 0
    dest = backup(keep=args.keep)
    print(f"Backup written: {dest}")
    print(verify(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
