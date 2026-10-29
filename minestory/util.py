"""Atomic files, diagnostics and subprocesses shared by the pipeline."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)

def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def run(args, *, cwd=None, log=None, timeout=None):
    """Never invoke a shell or interpolate a user filename into shell text."""
    if log:
        with Path(log).open("a", encoding="utf-8") as stream:
            stream.write("\n" + json.dumps([str(a) for a in args]) + "\n")
            stream.flush()
            result = subprocess.run([str(a) for a in args], cwd=cwd, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            tail = Path(log).read_text(errors="replace")[-3000:]
            raise RuntimeError(f"{args[0]} terminou com código {result.returncode}. Log: {log}\n{tail}")
        return result
    return subprocess.run([str(a) for a in args], cwd=cwd, check=True,
                          capture_output=True, text=True, timeout=timeout)

def event(job, stage, **details):
    value = {"at": time.time(), "stage": stage, **details}
    with (Path(job) / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
    print(f"[MineStory] {stage}" + (f": {details['message']}" if 'message' in details else ""), flush=True)
