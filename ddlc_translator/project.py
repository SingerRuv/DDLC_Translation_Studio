"""SQLite project storage."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relative_path TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    source_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS strings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    line INTEGER NOT NULL,
    original TEXT NOT NULL,
    translation TEXT NOT NULL DEFAULT '',
    context TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
);
"""


class Project:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.path / "project.sqlite3"
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def set_meta(self, key, value):
        self.db.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(key), str(value)))
        self.db.commit()

    def get_meta(self, key, default=""):
        row = self.db.execute(
            "SELECT value FROM meta WHERE key = ?", (str(key),)).fetchone()
        return row["value"] if row else default

    def add_file(self, relative_path, kind="script", source_hash="",
                 commit=True):
        relative_path = str(relative_path).replace("\\", "/")
        self.db.execute(
            "INSERT OR IGNORE INTO files(relative_path, kind, source_hash) "
            "VALUES(?, ?, ?)", (relative_path, str(kind), str(source_hash)))
        if commit:
            self.db.commit()
        row = self.db.execute(
            "SELECT id FROM files WHERE relative_path = ?",
            (relative_path,)).fetchone()
        return row["id"]

    def add_string(self, file_id, line, original, context="",
                   commit=True):
        row = self.db.execute(
            "SELECT id FROM strings WHERE file_id = ? AND line = ? AND "
            "original = ?", (file_id, line, original)).fetchone()
        if row:
            return row["id"]
        cursor = self.db.execute(
            "INSERT INTO strings(file_id, line, original, context) "
            "VALUES(?, ?, ?, ?)",
            (file_id, line, original, context))
        if commit:
            self.db.commit()
        return cursor.lastrowid

    def strings(self, status=None):
        query = (
            "SELECT strings.*, files.relative_path FROM strings "
            "JOIN files ON files.id = strings.file_id ")
        params = ()
        if status:
            query += "WHERE strings.status = ? "
            params = (status,)
        query += "ORDER BY files.relative_path, strings.line, strings.id"
        return self.db.execute(query, params).fetchall()

    def set_translation(self, string_id, translation):
        self.db.execute(
            "UPDATE strings SET translation = ?, status = ? WHERE id = ?",
            (translation, "translated" if translation.strip() else "pending",
             string_id))
        self.db.commit()

    def get_string(self, string_id):
        return self.db.execute(
            "SELECT strings.*, files.relative_path FROM strings "
            "JOIN files ON files.id = strings.file_id WHERE strings.id = ?",
            (string_id,)).fetchone()

    def files(self):
        return self.db.execute(
            "SELECT * FROM files ORDER BY relative_path").fetchall()

    @contextmanager
    def transaction(self):
        try:
            yield
        except Exception:
            self.db.rollback()
            raise
        else:
            self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
