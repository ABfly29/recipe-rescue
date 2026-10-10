"""Test helpers: every test works on a throw-away SQLite file, never on data/recipe_rescue.db."""
import os
import tempfile
from pathlib import Path

import db
from tools.import_dataset import find_files, run_import

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini_dataset.csv"


class TempDatabase:
    """Context manager that points RECIPE_RESCUE_DB at a temporary file."""

    def __enter__(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "test.db"
        self._old = os.environ.get("RECIPE_RESCUE_DB")
        os.environ["RECIPE_RESCUE_DB"] = str(self.path)
        return self

    def __exit__(self, *exc):
        if self._old is None:
            os.environ.pop("RECIPE_RESCUE_DB", None)
        else:
            os.environ["RECIPE_RESCUE_DB"] = self._old
        self._dir.cleanup()


def import_fixture(path):
    conn = db.connect(path)
    db.migrate(conn)
    try:
        return run_import(conn, find_files(FIXTURE))
    finally:
        conn.close()
