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

    def definition(self,kind,name,value,license="CC0-1.0"):
        digest=content_hash({"kind":kind,"value":value})
        path=self.root/"definitions"/f"{digest}.json"
        if not path.exists():
            write_json(path,{"kind":kind,"schema":1,"value":value})
        return self.add(path,kind=kind,name=name,license=license)

    def remember(self, storyboard, job):
        hashes = []
        from .assets import generate_assets
        manifest=generate_assets(self.root/"assets")
        for asset in manifest["assets"]:
            hashes.append(self.add(self.root/"assets"/asset["path"],kind=asset["type"],name=asset["id"],license=asset["license"],
                                   metadata={"version":asset["version"],"source":"original procedural artwork"}))
        hashes.append(self.definition("rig-definition","original-32",{"head":[8,8,8],"torso":[8,12,4],"limbs":[4,12,4],"units":"pixels/16 per block","renderer":"minestory Blender hierarchy"}))
        hashes.append(self.definition("lighting-definition","flat-pixel",{"engine":"BLENDER_WORKBENCH","studio_light":"paint.sl","texture_filter":"Closest","specular":False,"cast_shadows":False}))
        for scene in storyboard["scenes"]:
            hashes.append(self.definition("environment-definition",scene["environment"],{"environment":scene["environment"],"blocks":scene.get("blocks",[])}))
            hashes.append(self.definition("camera-definition",scene["id"],scene["camera"]))
            hashes.append(self.definition("transition-definition","cut",{"type":"cut"}))
            hashes.append(self.definition("scene-definition",scene["id"],{k:v for k,v in scene.items() if k not in {"narration","objective","semantic_tags"}}))
            # Store concrete parameterized assets, never a promise of a missing model.
            for item in scene.get("props", []):
                definition = {k:v for k,v in item.items() if k not in {"animations", "position", "id"}}
                digest = content_hash(definition)
                path = self.root / "definitions" / f"{digest}.json"
                if not path.exists():
                    write_json(path, definition)
                hashes.append(self.add(path, kind="prop-definition", name=item.get("kind", "custom"), license="MIT", metadata={"generator":"minestory", "schema":1}))
            for actor in scene.get("actors", []):
                if actor.get("actions"):
                    hashes.append(self.definition("animation-definition",actor["id"],{"rig":"original-32","timing":"relative seconds; adapt to new narration","actions":actor["actions"]}))
                definition = {"rig":"minestory-original-32", "color":actor.get("color", "teal"), "proportions":"8x8x8 head; 8x12x4 torso; 4x12x4 limbs"}
                digest = content_hash(definition)
                path = self.root / "definitions" / f"{digest}.json"
                if not path.exists():
                    write_json(path, definition)
                hashes.append(self.add(path, kind="character-definition", name=actor.get("id", "actor"), license="MIT"))
            for item in scene.get("props",[]):
                if item.get("animations"):
                    hashes.append(self.definition("prop-animation-definition",item["id"],item["animations"]))
            from .sound import _effect,_write_wav
            for sound in scene.get("sound_events",[]):
                name=sound.get("type","item")
                path=self.root/"sounds"/(content_hash({"original_synth":1,"name":name})+".wav")
                if not path.exists():
                    _write_wav(path,_effect(name))
                hashes.append(self.add(path,kind="sound-effect",name=name,license="CC0-1.0",metadata={"generator":"original procedural waveform","synth_version":1}))
        with self.connect() as conn:
            conn.executemany("INSERT OR IGNORE INTO usages VALUES (?,?,?)", [(str(job), h, time.time()) for h in hashes])
        return sorted(set(hashes))
