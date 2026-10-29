"""Original, reproducible pixel assets. Uses only the Python standard library.

No game files, third-party textures or network calls are used. Dimensions follow
Minecraft's block and character language; pixel patterns are original artwork.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import struct
import uuid
import zlib
from pathlib import Path

VERSION = "1.0.0"
LICENSE = "CC0-1.0"
PALETTE = {
    "grass_top": (91, 139, 55), "grass_side": (129, 91, 58),
    "dirt": (129, 91, 58), "stone": (126, 128, 125),
    "planks": (167, 132, 78), "log_top": (160, 125, 75),
    "log_side": (99, 76, 44), "leaves": (58, 112, 44),
    "sand": (216, 204, 149), "water": (49, 104, 180),
    "brick": (149, 81, 65), "card": (227, 191, 68),
    "skin": (186, 134, 95), "cloth_teal": (39, 145, 143),
    "cloth_amber": (218, 157, 57), "pants": (57, 67, 112),
    "dark": (42, 42, 44), "hair": (63, 43, 30),
    "face": (186, 134, 95), "shirt_front": (39, 145, 143),
    "snow": (236, 244, 241), "gold": (226, 182, 50),
    "iron": (177, 184, 180), "glass": (162, 212, 220),
    "obsidian": (43, 31, 63), "redstone": (158, 41, 35),
    "sun": (248, 207, 75), "earth": (61, 119, 157),
}


def _rgb(rgb, amount=0):
    return tuple(max(0, min(255, int(c + amount))) for c in rgb)


def _texture(name: str, size: int = 16):
    rng = random.Random("minestory-original:" + name)
    base = PALETTE[name]
    pixels = [[base for _ in range(size)] for _ in range(size)]

    def rect(x, y, w, h, color):
        for yy in range(max(0, y), min(size, y + h)):
            for xx in range(max(0, x), min(size, x + w)):
                pixels[yy][xx] = color

    # Flat, restrained 1–3 pixel clusters, deliberately not photographic noise.
    if name not in {"face", "card", "shirt_front"}:
        for _ in range(size * 2):
            x, y = rng.randrange(size), rng.randrange(size)
            rect(x, y, rng.choice([1, 2, 3]), rng.choice([1, 1, 2]),
                 _rgb(base, rng.choice([-14, -8, 7, 12])))
    if name in {"dirt", "grass_side"}:
        for x, y in [(2, 6), (11, 3), (7, 12), (14, 10)]:
            rect(x, y, 2, 1, (103, 87, 72))
            rect(x + 1, y + 1, 1, 1, (147, 114, 81))
    if name == "grass_side":
        for x in range(size):
            height = [4, 3, 4, 5, 4, 3, 3, 4, 6, 4, 3, 4, 5, 4, 4, 3][x % 16]
            rect(x, 0, 1, height, _rgb(PALETTE["grass_top"], rng.choice([-8, 0, 8])))
    if name == "grass_top":
        for x, y in [(2, 3), (10, 8), (6, 13), (13, 2)]:
            rect(x, y, 3, 1, (104, 150, 59))
            rect(x + 1, y + 1, 1, 2, (77, 126, 47))
    if name == "stone":
        for x, y in [(0, 4), (7, 2), (4, 11), (12, 8), (9, 15)]:
            rect(x, y, 4, 1, (109, 112, 109))
            rect(x + 1, y + 1, 3, 1, (139, 141, 137))
    if name == "planks":
        for y in [3, 7, 11, 15]:
            rect(0, y, size, 1, (116, 87, 50))
            rect(0, max(0, y - 1), size, 1, (177, 143, 87))
        for x, y in [(5, 0), (12, 4), (3, 8), (10, 12)]:
            rect(x, y, 1, 3, (132, 99, 57))
            rect((x + 7) % 16, y + 1, 3, 1, (145, 111, 65))
    if name == "log_side":
        for x in [0, 4, 7, 12, 15]:
            rect(x, 0, 1, size, (65, 52, 33))
            rect(min(x + 1, 15), 0, 1, size, (127, 100, 57))
        rect(5, 4, 1, 5, (92, 65, 36))
    if name == "log_top":
        for inset in [0, 3, 6]:
            color = (108, 80, 44)
            rect(inset, inset, size - 2 * inset, 1, color)
            rect(inset, size - inset - 1, size - 2 * inset, 1, color)
            rect(inset, inset, 1, size - 2 * inset, color)
            rect(size - inset - 1, inset, 1, size - 2 * inset, color)
    if name == "leaves":
        for x, y in [(1, 2), (8, 1), (5, 7), (12, 10), (2, 13), (11, 5)]:
            rect(x, y, 3, 2, (45, 88, 34))
            rect(x, y - 1, 2, 1, (76, 133, 48))
    if name == "water":
        for x, y, w in [(1, 2, 5), (9, 6, 6), (3, 11, 7), (12, 14, 4)]:
            rect(x, y, w, 1, (74, 131, 201))
    if name == "brick":
        for y in [3, 7, 11, 15]:
            rect(0, y, 16, 1, (171, 161, 142))
        for x, y in [(6, 0), (13, 0), (2, 4), (10, 4), (6, 8), (14, 8), (2, 12), (10, 12)]:
            rect(x, y, 1, 3, (171, 161, 142))
    if name == "face":
        rect(0, 0, 16, 4, PALETTE["hair"])
        rect(0, 3, 2, 7, PALETTE["hair"])
        rect(14, 3, 2, 7, PALETTE["hair"])
        rect(2, 7, 4, 2, (241, 237, 221))
        rect(10, 7, 4, 2, (241, 237, 221))
        rect(4, 7, 2, 2, (42, 72, 87))
        rect(10, 7, 2, 2, (42, 72, 87))
        rect(7, 9, 2, 3, (162, 111, 77))
        rect(5, 13, 6, 1, (108, 71, 54))
        rect(4, 4, 2, 1, (104, 72, 46))
        rect(11, 4, 3, 1, (104, 72, 46))
    if name == "shirt_front":
        rect(5, 0, 6, 2, PALETTE["skin"])
        rect(6, 2, 4, 1, PALETTE["skin"])
        rect(4, 0, 1, 3, (23, 108, 105))
        rect(11, 0, 1, 3, (23, 108, 105))
        rect(2, 9, 2, 5, (32, 129, 125))
        rect(11, 6, 2, 7, (47, 155, 146))
        rect(0, 14, 16, 2, (33, 127, 121))
    if name == "card":
        rect(1, 1, 14, 14, (240, 217, 130))
        rect(2, 2, 12, 7, (50, 87, 116))
        rect(6, 3, 4, 4, (100, 178, 143))
        rect(4, 6, 8, 2, (71, 132, 105))
        rect(3, 10, 10, 1, (154, 119, 57))
        rect(3, 12, 7, 1, (154, 119, 57))
        rect(3, 14, 4, 1, (154, 119, 57))
        rect(12, 13, 2, 2, (219, 158, 46))
    if name == "earth":
        for x, y, w, h in [(1, 3, 5, 4), (4, 7, 3, 5), (10, 2, 5, 5), (9, 7, 3, 2), (12, 11, 3, 3)]:
            rect(x, y, w, h, (85, 132, 64))
        rect(0, 0, 16, 1, (208, 224, 223))
        rect(0, 15, 16, 1, (208, 224, 223))
    if name == "sun":
        for x, y in [(2, 3), (8, 8), (12, 2), (4, 12)]:
            rect(x, y, 3, 2, (246, 177, 46))
    return pixels


def _png_bytes(pixels):
    height, width = len(pixels), len(pixels[0])
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _write_immutable(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Asset version collision: {path}. Increment VERSION; originals are preserved.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _bbmodel(name, elements, textures):
    """Editable native Blockbench free-model document; units are 1/16 block."""
    result = {"meta": {"format_version": "4.10", "model_format": "free", "box_uv": False},
              "name": name, "model_identifier": "minestory:" + name, "visible_box": [1, 3, 1],
              "resolution": {"width": 16, "height": 16}, "elements": [], "outliner": [],
              "textures": []}
    import base64
    for index, (texture_name, png) in enumerate(textures):
        result["textures"].append({"path": "", "name": texture_name + ".png", "folder": "",
            "namespace": "minestory", "id": str(index), "particle": index == 0,
            "render_mode": "normal", "visible": True, "mode": "bitmap", "saved": False,
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "minestory:texture:" + texture_name)),
            "source": "data:image/png;base64," + base64.b64encode(png).decode()})
    for item in elements:
        index = item.pop("texture", 0)
        element_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "minestory:" + name + ":" + item["name"]))
        item.update({"uuid": element_id, "autouv": 0, "color": 0, "visibility": True,
                     "faces": {side: {"uv": [0, 0, 16, 16], "texture": index}
                               for side in ["north", "east", "south", "west", "up", "down"]}})
        result["elements"].append(item)
        result["outliner"].append(element_id)
    return json.dumps(result, ensure_ascii=False, indent=2).encode()


def generate_assets(root: Path | str) -> dict:
    """Create an immutable versioned library and return its serializable manifest.

    `manifest['textures'][name]` gives the absolute PNG path. Files already
    matching this version are reused. No output from earlier versions is removed.
    """
    root = Path(root).expanduser().resolve()
    destination = root / "original" / VERSION
    textures, entries = {}, []
    generated = {}
    for name in PALETTE:
        data = _png_bytes(_texture(name))
        path = destination / "textures" / f"{name}.png"
        _write_immutable(path, data)
        textures[name] = str(path)
        generated[name] = data
        entries.append({"id": f"minestory:{name}", "type": "pixel_texture", "path": str(path.relative_to(root)),
                        "sha256": hashlib.sha256(data).hexdigest(), "version": VERSION, "license": LICENSE,
                        "dimensions": [16, 16], "source": "original procedural artwork"})
    character = _bbmodel("lia", [
        {"name": "head", "from": [-4, 24, -4], "to": [4, 32, 4], "origin": [0, 24, 0], "texture": 0},
        {"name": "body", "from": [-4, 12, -2], "to": [4, 24, 2], "origin": [0, 24, 0], "texture": 1},
        {"name": "left_arm", "from": [-8, 12, -2], "to": [-4, 24, 2], "origin": [-6, 23, 0], "texture": 1},
        {"name": "right_arm", "from": [4, 12, -2], "to": [8, 24, 2], "origin": [6, 23, 0], "texture": 1},
        {"name": "left_leg", "from": [-4, 0, -2], "to": [0, 12, 2], "origin": [-2, 12, 0], "texture": 2},
        {"name": "right_leg", "from": [0, 0, -2], "to": [4, 12, 2], "origin": [2, 12, 0], "texture": 2}],
        [(name, generated[name]) for name in ["face", "cloth_teal", "pants"]])
    card = _bbmodel("discovery_card", [{"name": "card", "from": [-4, 0, -0.25], "to": [4, 12, 0.25],
                                      "origin": [0, 0, 0], "texture": 0}], [("card", generated["card"])])
    for name, data in [("lia.bbmodel", character), ("discovery_card.bbmodel", card)]:
        path = destination / "models" / name
        _write_immutable(path, data)
        entries.append({"id": "minestory:" + path.stem, "type": "blockbench_model", "path": str(path.relative_to(root)),
                        "sha256": hashlib.sha256(data).hexdigest(), "version": VERSION, "license": LICENSE})
    license_text = ("Original MineStory assets\n\nLicense: CC0 1.0 Universal (CC0-1.0).\n"
                    "To the extent possible under law, the authors dedicate their original artwork\n"
                    "and procedural asset designs to the public domain.\n"
                    "https://creativecommons.org/publicdomain/zero/1.0/\n\n"
                    "These textures are original artwork and contain no extracted Minecraft files.\n"
                    "Minecraft is a trademark of Mojang/Microsoft; this project is unaffiliated.\n").encode()
    _write_immutable(destination / "LICENSE.txt", license_text)
    manifest = {"schema_version": 1, "version": VERSION, "license": LICENSE, "root": str(root),
                "textures": textures, "assets": entries,
                "characters": {"lia": {"model": str(destination / "models/lia.bbmodel"), "palette": "teal"},
                               "nilo": {"model": str(destination / "models/lia.bbmodel"), "palette": "amber"}},
                "style": {"texture_filter": "nearest", "block_pixels": 16, "character_height_blocks": 2,
                          "palette": {name: list(color) for name, color in PALETTE.items()}}}
    # On disk the manifest is portable; callers receive resolved absolute paths.
    stored_manifest = dict(manifest)
    stored_manifest["root"] = "."
    stored_manifest["textures"] = {name: str(Path(path).relative_to(root)) for name, path in textures.items()}
    stored_manifest["characters"] = {name: {**info, "model": str(Path(info["model"]).relative_to(root))}
                                      for name, info in manifest["characters"].items()}
    manifest_path = destination / "manifest.json"
    serialized = json.dumps(stored_manifest, ensure_ascii=False, indent=2).encode()
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old.get("root") != ".":
            # Migrate only the path-only manifest produced by prerelease 1.0.0.
            manifest_path.write_bytes(serialized)
        else:
            _write_immutable(manifest_path, serialized)
    else:
        _write_immutable(manifest_path, serialized)
    return manifest


def register_voxel_asset(root: Path | str, name: str, voxels: list, metadata: dict | None = None) -> dict:
    """Persist newly directed cuboid geometry with a content hash for reuse."""
    payload = {"schema_version": 1, "name": name, "voxels": voxels, "metadata": metadata or {}, "license": LICENSE}
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode()
    digest = hashlib.sha256(data).hexdigest()
    path = Path(root).expanduser().resolve() / "custom" / digest[:16] / "asset.json"
    _write_immutable(path, data)
    return {"id": "custom:" + digest[:16], "name": name, "path": str(path), "sha256": digest, "license": LICENSE}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="library")
    args = parser.parse_args()
    manifest = generate_assets(args.output)
    print(json.dumps({"assets": len(manifest["assets"]), "version": VERSION,
                      "manifest": str(Path(args.output).resolve() / "original" / VERSION / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
