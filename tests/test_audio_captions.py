"""Checks use actual PCM/FFmpeg and assert subtitle timing/readability invariants."""
from pathlib import Path
import json
import math
import re
import shutil
import wave
import numpy as np
import pytest

from minestory.audio import detect_silence, probe_audio, validate_transcript
from minestory.captions import groups, write_captions
from minestory.sound import build_soundtrack, mix_audio


def make_wav(path, seconds=2, speech_until=.8):
    rate = 22050
    t = np.arange(round(seconds * rate)) / rate
    values = (.3 * np.sin(2 * np.pi * 220 * t) * (t < speech_until) * (t > .1))
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, len(values), "NONE", "not compressed"))
        out.writeframes((values * 32767).astype("<i2").tobytes())
    return path


def test_probe_and_real_silence_boundaries(tmp_path):
    p = make_wav(tmp_path / "sinal com espaço.wav")
    metadata = probe_audio(p)
    assert metadata["duration"] == pytest.approx(2, abs=.001)
    assert metadata["sample_rate"] == 22050
    pauses = detect_silence(p, metadata["duration"], min_duration=.3)
    assert pauses[-1]["start"] == pytest.approx(.8, abs=.025)
    assert pauses[-1]["end"] == pytest.approx(2, abs=.025)


def sample_transcript():
    tokens = ["Por", "que", "a", "carta", "vale", "tanto?", "O", "Sol", "desapareceu."]
    return {"duration": 6., "words": [{"word": token, "start": i * .5,
                "end": i * .5 + .35, "probability": .97} for i, token in enumerate(tokens)]}


def test_caption_spoken_content_highlight_and_safe_zone(tmp_path):
    transcript = sample_transcript()
    info = write_captions(transcript, tmp_path)
    srt = Path(info["srt"]).read_text()
    text = " ".join(line for line in srt.splitlines() if line and "-->" not in line and not line.isdigit())
    assert text == " ".join(w["word"] for w in transcript["words"])
    assert all(len(chunk) <= 4 for chunk in groups(transcript["words"]))
    ass = Path(info["ass"]).read_text(encoding="utf-8-sig")
    highlights = [line for line in ass.splitlines() if line.startswith("Dialogue") and "&H004AE2FF&" in line]
    assert len(highlights) == len(transcript["words"])
    for cue in info["cue_metadata"]:
        assert .65 < cue["anchor"][1] / 1920 < .8
        assert .4 < cue["anchor"][0] / 1080 < .5
    assert "PlayResX: 1080" in ass and "PlayResY: 1920" in ass


def test_caption_escapes_untrusted_ass_overrides(tmp_path):
    transcript = {"duration": 1, "words": [{"word": r"{\pos(0,0)}", "start": 0, "end": .5}]}
    info = write_captions(transcript, tmp_path)
    text = Path(info["ass"]).read_text(encoding="utf-8-sig")
    assert r"{\pos(0,0)}" not in text


def test_reject_invalid_transcript():
    transcript = sample_transcript()
    transcript["words"][0]["end"] = 9
    with pytest.raises(ValueError, match="inválido"):
        validate_transcript(transcript)


def test_sfx_relative_timing_original_wav_and_duration_mix(tmp_path):
    narration = make_wav(tmp_path / "voz.wav")
    effects = tmp_path / "fx.wav"
    board = {"scenes": [{"start": 1., "sound_events": [{"type": "discovery", "time": .2, "gain": .4}]}]}
    report = build_soundtrack(board, 2., effects)
    assert report["count"] == 1 and report["events"][0]["time"] == pytest.approx(1.2)
    with wave.open(str(effects), "rb") as h:
        values = np.frombuffer(h.readframes(h.getnframes()), dtype="<i2")
        assert h.getnframes() / h.getframerate() == 2.
        assert np.max(np.abs(values[:round(1.2*h.getframerate())])) == 0
        assert np.max(np.abs(values[round(1.2*h.getframerate()):])) > 0
    output = tmp_path / "mixed.wav"
    mix = mix_audio(narration, effects, output, 2.)
    assert probe_audio(output)["duration"] == pytest.approx(2., abs=.025)
    assert mix["narration_speed"] == 1. and mix["narration_gain"] == 1.
