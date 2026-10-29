"""Data-only scene contract shared by the director and Blender renderer.

No Python expressions, filesystem paths, commands or scripts are scene primitives.
All animation timestamps are relative seconds within their scene.
"""
from __future__ import annotations

import math
import re
from typing import Any

ACTIONS = {"walk", "run", "jump", "point", "hold", "give", "receive", "sit", "fall", "surprise", "fear", "joy", "look"}
ANIMATIONS = {"move", "rotate", "grow", "appear", "disappear", "orbit"}
ENVIRONMENTS = {"village", "market", "space", "laboratory", "forest", "desert", "ocean", "snow", "night", "underground"}
MATERIALS = {"grass", "grass_top", "grass_side", "dirt", "stone", "planks", "log", "leaves", "sand", "water", "brick", "card", "skin", "cloth_teal", "cloth_amber", "pants", "dark", "gold", "red", "white", "sun", "blue"}
PROP_KINDS = {"card", "planet", "sun", "black_hole", "coin", "chest", "custom", "cube", "tree", "house", "machine", "telescope", "animal", "book", "crystal", "building", "cell", "vehicle", "chart", "heart", "galaxy", "earth", "moon"}

class SceneValidationError(ValueError):
    pass


def _finite(value: Any, name: str, low: float = -1000, high: float = 1000) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise SceneValidationError(f"{name}: número finito em [{low}, {high}] necessário")
    return float(value)


def _vector(value: Any, name: str, low: float = -100, high: float = 100) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SceneValidationError(f"{name}: vetor de 3 números necessário")
    for i, v in enumerate(value):
        _finite(v, f"{name}[{i}]", low, high)


def validate_storyboard(storyboard: dict, expected_duration: float | None = None) -> dict:
    """Validate timing, resource bounds, references and supported executable vocabulary.

    Returns the same object for convenient use in a pipeline. Unknown object kinds
    can be realized through custom cuboids rather than executable plugin code.
    """
    if not isinstance(storyboard, dict):
        raise SceneValidationError("Storyboard deve ser um objeto JSON")
    duration = _finite(storyboard.get("duration"), "duration", 0.02, 21600)
    if expected_duration is not None and abs(duration - expected_duration) > 0.04:
        raise SceneValidationError("Storyboard alterou a duração da narração")
    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 4096:
        raise SceneValidationError("scenes deve conter entre 1 e 4096 cenas")
    previous = 0.0
    scene_ids = set()
    for s, scene in enumerate(scenes):
        prefix = f"scenes[{s}]"
        if not isinstance(scene, dict):
            raise SceneValidationError(f"{prefix}: objeto necessário")
        sid = scene.get("id")
        if not isinstance(sid, str) or sid in scene_ids or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",sid):
            raise SceneValidationError(f"{prefix}: id inválido ou repetido")
        scene_ids.add(sid)
        start = _finite(scene.get("start"), prefix + ".start", 0, duration)
        end = _finite(scene.get("end"), prefix + ".end", 0, duration)
        if abs(start - previous) > 0.025 or end <= start:
            raise SceneValidationError(f"{prefix}: gap, sobreposição ou duração vazia")
        previous = end
        length = end - start
        if scene.get("environment") not in ENVIRONMENTS:
            raise SceneValidationError(f"{prefix}: ambiente desconhecido")
        if not isinstance(scene.get("narration"), str) or not isinstance(scene.get("objective"), str):
            raise SceneValidationError(f"{prefix}: narration/objective devem ser texto")
        if scene.get("transition","cut") != "cut":
            raise SceneValidationError("Transição não implementada; use cut ou construa a transição com props animados")
        if scene.get("effects"):
            raise SceneValidationError("Efeitos extras exigem props animados; partículas de reação são geradas pelas ações")
        actors, props, blocks = scene.get("actors", []), scene.get("props", []), scene.get("blocks", [])
        if not isinstance(actors, list) or len(actors) > 12 or not isinstance(props, list) or len(props) > 64 or not isinstance(blocks, list) or len(blocks) > 1000:
            raise SceneValidationError(f"{prefix}: número de assets acima do limite")
        ids = [o.get("id") for o in actors + props]
        if any(not isinstance(i, str) or not i or len(i) > 80 for i in ids) or len(set(ids)) != len(ids):
            raise SceneValidationError(f"{prefix}: ids de objetos inválidos ou repetidos")
        prop_ids = {p["id"] for p in props}
        for actor in actors:
            _vector(actor.get("position"), prefix + ".actor.position", -15, 15)
            for action in actor.get("actions", []):
                if action.get("type") not in ACTIONS:
                    raise SceneValidationError(f"{prefix}: ação não suportada: {action.get('type')}")
                a = _finite(action.get("start"), "action.start", 0, length + 0.01)
                b = _finite(action.get("end"), "action.end", 0, length + 0.01)
                if b < a:
                    raise SceneValidationError("Ação termina antes do começo")
                if "target" in action:
                    _vector(action["target"], "action.target", -20, 20)
                if action.get("object") is not None and action["object"] not in prop_ids:
                    raise SceneValidationError(f"{prefix}: referência de prop ausente {action['object']}")
        for prop in props:
            if prop.get("kind") not in PROP_KINDS:
                raise SceneValidationError(f"{prefix}: kind desconhecido; utilize kind=custom e voxels")
            _vector(prop.get("position"), prefix + ".prop.position", -30, 30)
            scale = prop.get("scale", 1)
            if isinstance(scale, (list, tuple)):
                _vector(scale, "prop.scale", 0.001, 15)
            else:
                _finite(scale, "prop.scale", 0.001, 15)
            if prop.get("material", "stone") not in MATERIALS:
                raise SceneValidationError("Material não suportado")
            voxels = prop.get("voxels", [])
            if prop["kind"] in {"tree","house","machine","book","crystal","building","cell","vehicle","heart","galaxy"} and not voxels:
                raise SceneValidationError(f"{prop['kind']} exige voxels explícitos: não há modelo nativo desse objeto no renderer")
            if len(voxels) > 400:
                raise SceneValidationError("Asset custom excede 400 cuboides")
            for voxel in voxels:
                _vector(voxel.get("position"), "voxel.position", -15, 15)
                _vector(voxel.get("size", [1, 1, 1]), "voxel.size", 0.001, 15)
                if voxel.get("material", prop.get("material", "stone")) not in MATERIALS:
                    raise SceneValidationError("Material de cuboide não suportado")
            for animation in prop.get("animations", []):
                if animation.get("type") not in ANIMATIONS:
                    raise SceneValidationError("Animação não suportada")
                a = _finite(animation.get("start"), "animation.start", 0, length + 0.01)
                b = _finite(animation.get("end"), "animation.end", 0, length + 0.01)
                if b < a:
                    raise SceneValidationError("Animação termina antes de começar")
                if "to" in animation:
                    _vector(animation["to"], "animation.to", -30, 30)
        for block in blocks:
            _vector(block.get("position"), "block.position", -50, 50)
            if block.get("material") not in MATERIALS:
                raise SceneValidationError("Material de bloco não suportado")
        camera = scene.get("camera", {})
        _vector(camera.get("position"), "camera.position", -50, 50)
        _vector(camera.get("target"), "camera.target", -30, 30)
        if "end_position" in camera:
            _vector(camera["end_position"], "camera.end_position", -50, 50)
        _finite(camera.get("scale", 8), "camera.scale", 3, 30)
        for event in scene.get("sound_events", []):
            _finite(event.get("time"), "sound.time", 0, length + 0.01)
            _finite(event.get("gain", 0.15), "sound.gain", 0, 0.5)
    if abs(previous - duration) > 0.025:
        raise SceneValidationError("Storyboard não cobre a duração integral")
    return storyboard


def _strict_obj(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}

VEC = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}
STR = {"type": "string"}
NUM = {"type": "number"}
ACTION_SCHEMA = _strict_obj({"type": {"type": "string", "enum": sorted(ACTIONS)}, "start": NUM, "end": NUM, "target": VEC, "object": {"type": ["string", "null"]}})
ANIMATION_SCHEMA = _strict_obj({"type": {"type": "string", "enum": sorted(ANIMATIONS)}, "start": NUM, "end": NUM, "to": VEC})
VOXEL_SCHEMA = _strict_obj({"position": VEC, "size": VEC, "material": {"type": "string", "enum": sorted(MATERIALS)}})
ACTOR_SCHEMA = _strict_obj({"id": STR, "position": VEC, "color": {"type": "string", "enum": ["teal", "amber", "red", "blue"]}, "actions": {"type": "array", "items": ACTION_SCHEMA}})
PROP_SCHEMA = _strict_obj({"id": STR, "kind": {"type": "string", "enum": sorted(PROP_KINDS)}, "position": VEC, "scale": NUM, "material": {"type": "string", "enum": sorted(MATERIALS)}, "voxels": {"type": "array", "items": VOXEL_SCHEMA}, "animations": {"type": "array", "items": ANIMATION_SCHEMA}})
SCENE_PLAN_SCHEMA = _strict_obj({
    "beat_index": {"type": "integer"}, "objective": STR,
    "environment": {"type": "string", "enum": sorted(ENVIRONMENTS)},
    "semantic_tags": {"type": "array", "items": STR},
    "actors": {"type": "array", "items": ACTOR_SCHEMA},
    "props": {"type": "array", "items": PROP_SCHEMA},
    "blocks": {"type": "array", "items": _strict_obj({"position": VEC, "material": {"type": "string", "enum": sorted(MATERIALS)}})},
    "camera": _strict_obj({"position": VEC, "target": VEC, "end_position": VEC, "scale": NUM}),
})
MODEL_PLAN_SCHEMA = _strict_obj({"title": STR, "scenes": {"type": "array", "items": SCENE_PLAN_SCHEMA}})
