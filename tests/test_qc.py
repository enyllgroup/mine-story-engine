"""Exercise actual decoded frames, not just FFmpeg argument construction."""
from pathlib import Path
import subprocess

from minestory.qc import inspect_video, _check_timing


def _video(path: Path, source: str, seconds=2):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source,
                    "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000",
                    "-t", str(seconds), "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


def test_detects_real_black_frames_and_duration_mismatch(tmp_path):
    video = tmp_path / "black.mp4"
    _video(video, "color=c=black:s=144x256:r=30")
    result = inspect_video(video, transcript={"duration": 3, "words": [{"word": "teste", "start": 0, "end": 1}]}, output_dir=tmp_path / "qc")
    codes = {issue["code"] for issue in result["issues"]}
    assert "black_frames" in codes
    assert "narration_duration" in codes
    assert result["technical_gates_passed"] is False
    assert (tmp_path / "qc/contact_sheet.jpg").exists()


def test_passes_technical_media_checks_without_claiming_semantics(tmp_path):
    video = tmp_path / "moving.mp4"
    _video(video, "testsrc2=s=144x256:r=30")
    result = inspect_video(video, output_dir=tmp_path / "qc")
    assert result["status"] == "technical_pass", result
    assert result["technical_gates_passed"]
    assert "semantic match between narration and visible events" in result["unverified"]
    assert result["frame_analysis"]["sample_count"] >= 2


def test_detects_scenes_gaps_and_invalid_word_timestamps():
    issues = _check_timing(
        {"words": [{"word": "teste", "start": 2, "end": 1}]},
        {"scenes": [{"id": "s1", "start": 1, "end": 2, "actors": [], "props": [], "blocks": []}]}, 3,
    )
    assert {i["code"] for i in issues} >= {"word_timing", "scene_coverage", "scene_end", "empty_scene"}
