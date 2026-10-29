#!/usr/bin/env python3
"""Shared implementation for local MineStory skills; no extra services."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    skill = os.environ.get("MINESTORY_SKILL", "")
    delegated = {
        "narration-analyzer": "analyze", "visual-director": "plan",
        "minecraft-world-builder": "render", "minecraft-character-animator": "render",
        "minecraft-scene-director": "render", "minecraft-camera-director": "render",
        "render-pipeline": "produce", "visual-quality-control": "qc",
    }
    if skill in delegated:
        sys.argv = [f"minestory ({skill})", delegated[skill], *sys.argv[1:]]
        runpy.run_module("minestory", run_name="__main__")
        return
    parser = argparse.ArgumentParser(description=f"Execute the MineStory {skill} skill")
    if skill == "minecraft-asset-creator":
        parser.add_argument("--output", default=str(ROOT / "library"))
        parser.add_argument("--custom", help="JSON asset definition to catalog without changing its source")
        parser.add_argument("--license", default="user-provided", help="License of the supplied custom definition")
        args = parser.parse_args()
        from minestory.assets import generate_assets
        manifest = generate_assets(args.output)
        result = {"version": manifest["version"], "assets": len(manifest["assets"]), "root": args.output}
        if args.custom:
            from minestory.library import Library
            definition = load(args.custom)
            if not isinstance(definition, dict) or not definition.get("voxels"):
                parser.error("Custom asset must be a JSON object with a non-empty voxels list")
            result["custom_hash"] = Library(args.output).add(args.custom, kind="prop-definition", license=args.license)
        emit(result)
    elif skill == "subtitle-director":
        parser.add_argument("transcript")
        parser.add_argument("--output", required=True)
        parser.add_argument("--width", type=int, default=1080)
        parser.add_argument("--height", type=int, default=1920)
        parser.add_argument("--font", default="Pixelify Sans")
        parser.add_argument("--font-path")
        args = parser.parse_args()
        from minestory.captions import write_captions
        emit(write_captions(load(args.transcript), args.output, width=args.width, height=args.height,
                            font=args.font, font_path=args.font_path))
    elif skill == "sound-designer":
        parser.add_argument("storyboard")
        parser.add_argument("--audio", required=True)
        parser.add_argument("--output", required=True)
        args = parser.parse_args()
        from minestory.sound import build_soundtrack, mix_audio
        storyboard = load(args.storyboard)
        destination = Path(args.output)
        destination.mkdir(parents=True, exist_ok=True)
        result = {"effects": build_soundtrack(storyboard, float(storyboard["duration"]), destination / "effects.wav")}
        result["mix"] = mix_audio(args.audio, destination / "effects.wav", destination / "audio_mix.wav", float(storyboard["duration"]))
        (destination / "sound_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        emit(result)
    else:
        parser.error(f"Unsupported MineStory skill: {skill}")


if __name__ == "__main__":
    main()
