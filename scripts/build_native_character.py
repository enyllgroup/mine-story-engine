#!/usr/bin/env python3
"""Build a private original .mimodel rig from a channel identity profile."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from minestory.native_character import build_character,preview_project
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--profile',required=True,type=Path)
p.add_argument('--library-version',required=True,type=Path)
p.add_argument('--preview-project',type=Path)
p.add_argument('--quality',choices=['preview','final'],default='preview')
a=p.parse_args()
model=build_character(json.loads(a.profile.read_text()),a.library_version)
if a.preview_project:preview_project(model,a.preview_project,a.quality)
print(json.dumps({'character_version':str(model),'review_status':'awaiting_user_review','native_validation':'pending native load/render','preview_project':str(a.preview_project) if a.preview_project else None}))
