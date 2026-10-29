"""Preservation/resume guards, using real local media and actual QC."""
import copy
import json
from pathlib import Path
import subprocess
import wave

import pytest

from minestory.pipeline import PROFILES, produce, render_storyboard
from minestory.util import content_hash, file_hash


@pytest.fixture
def inputs(tmp_path):
    audio = tmp_path / "audio.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 32000)
    transcript = {"duration": 2.0, "language": "pt", "text": "Teste.",
                  "audio_sha256": file_hash(audio),
                  "words": [{"word": "Teste.", "start": .3, "end": 1.3}]}
    storyboard = {"duration": 2., "scenes": [{"id": "scene_001", "start": 0., "end": 2.,
                  "environment": "laboratory", "narration": "Teste.", "objective": "Fixture de teste de guarda",
                  "actors": [], "blocks": [], "props": [{"id": "cube", "kind": "cube", "position": [0, 0, 1],
                  "scale": .3, "material": "stone", "animations": []}],
                  "camera": {"position": [3, -6, 5], "target": [0, 0, 1], "scale": 7.2}}]}
    return audio, transcript, storyboard


def _resume_marker(job, audio, transcript, storyboard, quality="preview"):
    payload = {"storyboard": content_hash(storyboard), "transcript": content_hash(transcript),
               "audio": file_hash(audio), "profile": PROFILES[quality], "captions": True}
    (job / f"render-inputs-{quality}.json").write_text(json.dumps(payload))


def _existing_video(path: Path, black=False):
    source = "color=c=black:s=360x640:r=30" if black else "testsrc2=s=360x640:r=30"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "2",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(path)], check=True)


def test_render_preserves_nonempty_output_directory(tmp_path, inputs):
    audio, transcript, storyboard = inputs
    job = tmp_path / "existing"
    job.mkdir()
    sentinel = job / "personal-file.txt"
    sentinel.write_text("preserve exactly")
    with pytest.raises(FileExistsError, match="preservado"):
        render_storyboard(storyboard, audio, job, transcript=transcript)
    assert sentinel.read_text() == "preserve exactly"
    assert list(job.iterdir()) == [sentinel]


def test_render_refuses_transcript_for_another_audio(tmp_path, inputs):
    audio, transcript, storyboard = inputs
    transcript["audio_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="outro áudio"):
        render_storyboard(storyboard, audio, tmp_path / "job", transcript=transcript)
    assert not (tmp_path / "job/video_preview.mp4").exists()


def test_render_refuses_duration_different_from_audio(tmp_path, inputs):
    audio, transcript, storyboard = inputs
    transcript["duration"] = 3
    with pytest.raises(ValueError, match="Duração da transcrição"):
        render_storyboard(storyboard, audio, tmp_path / "job", transcript=transcript)


def test_produce_resume_refuses_changed_audio_hash_without_overwriting_report(tmp_path, inputs):
    audio, _, _ = inputs
    job = tmp_path / "job"
    job.mkdir()
    report = job / "production_report.json"
    report.write_text(json.dumps({"input_sha256": "wrong", "status": "failed"}))
    before = report.read_bytes()
    with pytest.raises(ValueError, match="áudio difere"):
        produce(audio, resume=job)
    assert report.read_bytes() == before


def test_render_resume_refuses_modified_inputs(tmp_path, inputs):
    audio, transcript, storyboard = inputs
    job = tmp_path / "job"
    job.mkdir()
    _resume_marker(job, audio, transcript, storyboard)
    modified = copy.deepcopy(storyboard)
    modified["scenes"][0]["objective"] = "Outra direção"
    before = (job / "render-inputs-preview.json").read_bytes()
    with pytest.raises(ValueError, match="Entradas do job foram modificadas"):
        render_storyboard(modified, audio, job, transcript=transcript, _allow_job_files=True)
    assert (job / "render-inputs-preview.json").read_bytes() == before


def test_render_resume_reinspects_existing_media_without_overwriting(tmp_path, inputs):
    audio, transcript, storyboard = inputs
    job = tmp_path / "job"
    job.mkdir()
    video = job / "video_preview.mp4"
    _existing_video(video)
    _resume_marker(job, audio, transcript, storyboard)
    before = file_hash(video)
    result = render_storyboard(storyboard, audio, job, transcript=transcript, _allow_job_files=True)
    assert result["resumed_existing_video"] is True
    assert result["qc"]["technical_gates_passed"]
    assert Path(result["qc"]["video"]).is_file()
    assert file_hash(video) == before
    assert (job / "qc/contact_sheet.jpg").is_file()


def test_render_resume_refuses_existing_video_that_fails_actual_qc(tmp_path, inputs):
    audio, transcript, storyboard = inputs
    job = tmp_path / "job"
    job.mkdir()
    video = job / "video_preview.mp4"
    _existing_video(video, black=True)
    _resume_marker(job, audio, transcript, storyboard)
    before = file_hash(video)
    with pytest.raises(RuntimeError, match="QC técnico da retomada falhou"):
        render_storyboard(storyboard, audio, job, transcript=transcript, _allow_job_files=True)
    assert file_hash(video) == before
    qc = json.loads((job / "qc/qc_report.json").read_text())
    assert qc["technical_gates_passed"] is False
    assert "black_frames" in {i["code"] for i in qc["issues"]}

def test_final_resume_refuses_preview_dimensions_even_with_final_marker(tmp_path,inputs):
    audio,transcript,storyboard=inputs
    job=tmp_path/"job"
    job.mkdir()
    _existing_video(job/"video_final.mp4")
    _resume_marker(job,audio,transcript,storyboard,quality="final")
    with pytest.raises(RuntimeError,match="QC técnico da retomada falhou"):
        render_storyboard(storyboard,audio,job,quality="final",transcript=transcript,_allow_job_files=True)
    qc=json.loads((job/"qc/qc_report.json").read_text())
    assert "profile_dimensions" in {i["code"] for i in qc["issues"]}
