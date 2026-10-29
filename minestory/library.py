"""Content-addressed resource catalogue; immutable files and SQLite history."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import sqlite3
import time
from .util import ROOT, content_hash, file_hash, write_json

class Library:
    def __init__(self, directory=None):
        self.root = Path(directory or ROOT / "library").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "catalog.sqlite3"
        with self.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS resources (hash TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, path TEXT NOT NULL, metadata TEXT NOT NULL, created REAL NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS usages (job TEXT NOT NULL, hash TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(job, hash))")

    def connect(self):
        conn = sqlite3.connect(self.db, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, path, *, kind="custom", name=None, license="user-provided", metadata=None):
        source = Path(path).resolve()
        digest = file_hash(source)
        destination = self.root / "objects" / digest[:2] / (digest + source.suffix.lower())
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
        data = {"license": license, **(metadata or {})}
        with self.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO resources VALUES (?,?,?,?,?,?)", (digest, kind, name or source.stem, str(destination.relative_to(self.root)), json.dumps(data, ensure_ascii=False), time.time()))
        return digest

    def list(self, kind=None):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM resources" + (" WHERE kind=?" if kind else "") + " ORDER BY created", (kind,) if kind else ()).fetchall()
        return [{**dict(row), "metadata": json.loads(row["metadata"])} for row in rows]

    def remember(self, storyboard, job):
        hashes = []
        for scene in storyboard["scenes"]:
            # Store concrete parameterized assets, never a promise of a missing model.
            for item in scene.get("props", []):
                definition = {k:v for k,v in item.items() if k not in {"animations", "position", "id"}}
                digest = content_hash(definition)
                path = self.root / "definitions" / f"{digest}.json"
                if not path.exists():
                    write_json(path, definition)
                hashes.append(self.add(path, kind="prop-definition", name=item.get("kind", "custom"), license="MIT", metadata={"generator":"minestory", "schema":1}))
            for actor in scene.get("actors", []):
                definition = {"rig":"minestory-original-32", "color":actor.get("color", "teal"), "proportions":"8x8x8 head; 8x12x4 torso; 4x12x4 limbs"}
                digest = content_hash(definition)
                path = self.root / "definitions" / f"{digest}.json"
                if not path.exists():
                    write_json(path, definition)
                hashes.append(self.add(path, kind="character-definition", name=actor.get("id", "actor"), license="MIT"))
        with self.connect() as conn:
            conn.executemany("INSERT OR IGNORE INTO usages VALUES (?,?,?)", [(str(job), h, time.time()) for h in hashes])
        return sorted(set(hashes))
