#!/usr/bin/env python3
"""Executable adapter for the MineStory minecraft-world-builder skill."""
from pathlib import Path
import os
import runpy
import sys

root = Path(__file__).resolve().parents[4]
python = root / ".venv/bin/python"
if python.exists() and Path(sys.executable).absolute() != python.absolute():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path.insert(0, str(root))
os.environ["MINESTORY_SKILL"] = "minecraft-world-builder"
runpy.run_path(str(root / ".agents/skills/_runner.py"), run_name="__main__")
