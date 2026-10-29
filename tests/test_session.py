"""The conversation prepares audio and authors a data-only plan, with no API.

Only ASR is replaced: file hashing, packets, beat splitting and preservation are
the real implementation. Tests stop at guards before expensive rendering.
"""
import json
import wave

import pytest

from minestory import session
import minestory.library as library_module
from minestory.scene_schema import SceneValidationError
from minestory.util import content_hash, file_hash


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    audio = tmp_path / "narracao.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 32000)
    transcript = {"duration": 2.0, "language": "pt", "text": "Olá.",
                  "words": [{"word": "Olá.", "start": .3, "end": 1.3}],
                  "audio_sha256": file_hash(audio)}
    calls = []

    def asr(path, cache, **kwargs):
        calls.append({"path": path, "cache": cache, **kwargs})
        return transcript

    monkeypatch.setattr(session, "analyze", asr)
    monkeypatch.setattr(session, "ROOT", tmp_path)
    monkeypatch.setattr(library_module, "ROOT", tmp_path)
    job = tmp_path / "job"
    report = session.prepare(audio, output=job)
    return audio, transcript, job, report, calls


def test_prepare_creates_hashed_packet_for_active_conversation(prepared):
    audio, transcript, job, report, calls = prepared
    packet = json.loads((job / "director_request.json").read_text())
    assert report["status"] == "awaiting_session_direction"
    assert report["director"]["backend"] == "codex-session"
    assert packet["input_sha256"] == file_hash(audio)
    assert packet["transcript_sha256"] == content_hash(transcript)
    assert packet["beats"][0]["narration"] == "Olá."
    assert packet["beats"][0]["start"] == 0
    assert packet["beats"][0]["end"] == 2
    assert "plan_schema" in packet
    assert calls[0]["language"] == "pt"
    assert len(calls) == 1
    assert not (job / "video_preview.mp4").exists()


def test_prepare_preserves_an_existing_production(prepared):
    audio, _, job, _, calls = prepared
    before = (job / "production_report.json").read_bytes()
    with pytest.raises(FileExistsError, match="preservada"):
        session.prepare(audio, output=job)
    assert len(calls) == 1
    assert (job / "production_report.json").read_bytes() == before


def test_finish_refuses_audio_changed_after_prepare(prepared):
    audio, _, job, _, _ = prepared
    audio.write_bytes(audio.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Áudio modificado"):
        session.finish(job)
    assert not (job / "video_preview.mp4").exists()


def test_finish_refuses_changed_transcript(prepared):
    _, transcript, job, _, _ = prepared
    transcript["words"][0]["word"] = "Outra."
    (job / "transcript.json").write_text(json.dumps(transcript))
    with pytest.raises(ValueError, match="Transcrição modificada"):
        session.finish(job)


def test_finish_preserves_completed_job(prepared):
    _, _, job, report, _ = prepared
    report["status"] = "completed"
    (job / "production_report.json").write_text(json.dumps(report))
    before = (job / "production_report.json").read_bytes()
    with pytest.raises(FileExistsError, match="concluída preservada"):
        session.finish(job)
    assert (job / "production_report.json").read_bytes() == before


@pytest.mark.parametrize("scenes", [[], [{"beat_index": 0}, {"beat_index": 0}]])
def test_finish_rejects_direction_that_omits_or_duplicates_beats_and_records_failure(prepared, scenes):
    _, _, job, _, _ = prepared
    (job / "direction_plan.json").write_text(json.dumps({"title": "Invalid test plan", "scenes": scenes}))
    with pytest.raises(SceneValidationError, match="omitiu"):
        session.finish(job)
    assert not (job / "video_preview.mp4").exists()
    report = json.loads((job / "production_report.json").read_text())
    assert report["status"] == "failed"
    assert report["errors"][-1]["type"] == "SceneValidationError"


def test_prepare_records_an_asr_failure_without_claiming_direction(prepared, monkeypatch):
    audio, _, job, _, _ = prepared

    def failing_asr(*args, **kwargs):
        raise RuntimeError("ASR fixture failure")

    monkeypatch.setattr(session, "analyze", failing_asr)
    failed = job.parent / "failed-job"
    with pytest.raises(RuntimeError, match="ASR fixture failure"):
        session.prepare(audio, output=failed)
    report = json.loads((failed / "production_report.json").read_text())
    assert report["status"] == "failed"
    assert report["errors"] == [{"type": "RuntimeError", "message": "ASR fixture failure"}]
    assert not (failed / "director_request.json").exists()
