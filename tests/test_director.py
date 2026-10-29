import copy
import json
import math

import pytest

from minestory.director import compile_plan, generate, procedural_plan, split_beats
from minestory.scene_schema import SceneValidationError, validate_storyboard


def narration(text, step=.45):
    words = text.split()
    return {"duration": round(len(words) * step + .2, 6), "text": text, "language": "pt", "words": [{"word": w, "start": round(i * step + .1, 6), "end": round((i + 1) * step - .03, 6)} for i, w in enumerate(words)]}


def test_timeline_covers_original_audio_and_never_rewrites_words():
    t = narration("Um colecionador encontrou uma carta rara. Muitas pessoas disputam um único objeto. Por isso o preço aumenta muito no leilão. Depois a carta troca de mãos.")
    s = generate(t, backend="procedural")
    validate_storyboard(s, t["duration"])
    assert s["scenes"][0]["start"] == 0
    assert s["scenes"][-1]["end"] == t["duration"]
    assert " ".join(x["narration"] for x in s["scenes"]) == t["text"]
    assert not s["director"]["generative"]
    for a, b in zip(s["scenes"], s["scenes"][1:]):
        assert a["end"] == b["start"]


def test_two_unrelated_topics_use_different_resources_and_events():
    cards = generate(narration("Uma carta rara vale muito dinheiro. Muitos colecionadores disputam um único objeto no leilão."), backend="procedural")
    solar = generate(narration("O que aconteceria se o Sol desaparecesse? A luz ainda viajaria durante oito minutos. A Terra perderia sua órbita e tudo ficaria escuro e frio."), backend="procedural")
    c = {p["kind"] for s in cards["scenes"] for p in s["props"]}
    p = {p["kind"] for s in solar["scenes"] for p in s["props"]}
    assert "card" in c and "planet" in p and "sun" in p
    assert c != p
    assert any(a["type"] == "disappear" for s in solar["scenes"] for p in s["props"] for a in p["animations"])
    assert any(s["actors"] for s in cards["scenes"])


def test_new_object_is_described_by_cuboids_and_actor_interacts():
    s = generate(narration("O cientista descobriu um telescópio novo e apontou para o instrumento científico."), backend="procedural")
    prop = next(p for p in s["scenes"][0]["props"] if p["kind"] == "custom")
    assert len(prop["voxels"]) >= 3
    assert any(a["type"] == "point" for a in s["scenes"][0]["actors"][0]["actions"])


@pytest.mark.parametrize("mutation", ["nan", "missing_prop", "gap", "unknown_action", "oversized_voxels"])
def test_validator_rejects_unsafe_or_incoherent_execution_data(mutation):
    s = generate(narration("O colecionador encontrou uma carta rara."), backend="procedural")
    scene = s["scenes"][0]
    if mutation == "nan":
        scene["camera"]["position"][0] = float("nan")
    elif mutation == "missing_prop":
        scene["actors"][0]["actions"].append({"type": "hold", "start": 0, "end": 1, "object": "missing"})
    elif mutation == "gap":
        scene["start"] = .3
    elif mutation == "unknown_action":
        scene["actors"][0]["actions"].append({"type": "exec", "start": 0, "end": 1, "command": "touch should-never-run"})
    else:
        scene["props"][0]["voxels"] = [{}] * 401
    with pytest.raises(SceneValidationError):
        validate_storyboard(s)


def test_silence_is_not_used_as_an_excuse_to_invent_words():
    with pytest.raises(ValueError, match="não contém palavras"):
        generate({"duration": 8, "text": "", "words": []}, backend="procedural")


def test_model_cannot_omit_a_beat_or_change_narration_clock():
    t = narration("Uma carta rara vale dinheiro. Depois muitas pessoas chegaram ao leilão. O valor começou a crescer. O comprador encontrou um objeto especial.")
    beats = split_beats(t)
    p = procedural_plan(t, beats)
    p["scenes"] = []
    with pytest.raises(SceneValidationError, match="omitiu"):
        compile_plan(p, beats, t["duration"], "llama")
