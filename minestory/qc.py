"""Evidence-based technical video inspection. No semantic/visual approval is implied.

This module intentionally has no OCR/model dependency. It inspects actual decoded
frames and media streams, checks the planning data, and emits a contact sheet for
human/agent visual review. All thresholds and unverified areas are reported.
"""
from __future__ import annotations

import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


def _json_input(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


def probe_media(path: str | Path) -> dict:
    """Read streams without relying on file extensions or shell interpolation."""
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if run.returncode:
        raise RuntimeError(f"ffprobe failed: {run.stderr[-2000:]}")
    return json.loads(run.stdout)


def _duration(stream: dict, fallback: float = 0.0) -> float:
    try:
        return float(stream.get("duration", fallback))
    except (ValueError, TypeError):
        return fallback


def _sample_frames(path: Path, duration: float, width: int = 144, height: int = 256) -> tuple[np.ndarray, float]:
    # Up to 180 actual decoded frames; long productions are sampled less densely.
    sample_fps = min(1.0, 180.0 / max(duration, 1.0))
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-threads", "1", "-i", str(path), "-an",
         "-vf", f"fps={sample_fps},scale={width}:{height}:flags=area", "-frames:v", "181",
         "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"],
        capture_output=True, timeout=max(90, int(duration * 3)),
    )
    if result.returncode:
        raise RuntimeError(f"Frame decode failed: {result.stderr.decode(errors='replace')[-2000:]}")
    stride = width * height * 3
    count = len(result.stdout) // stride
    if not count:
        raise RuntimeError("No frames could be decoded from the rendered video")
    return np.frombuffer(result.stdout[:count * stride], dtype=np.uint8).reshape(count, height, width, 3), sample_fps


def _runs(flags: list[bool], step: float, minimum: float) -> list[dict]:
    spans = []
    first = None
    for i, flag in enumerate(flags + [False]):
        if flag and first is None:
            first = i
        if not flag and first is not None:
            if (i - first) * step >= minimum:
                spans.append({"start": round(first * step, 3), "end": round(i * step, 3)})
            first = None
    return spans


def _check_timing(transcript: dict | None, storyboard: dict | None, duration: float) -> list[dict]:
    issues = []
    if transcript is not None:
        words = transcript.get("words", [])
        if not words:
            issues.append({"severity": "error", "code": "empty_transcript", "detail": "No aligned spoken words"})
        last_start = -math.inf
        for i, word in enumerate(words):
            try:
                start, end = float(word["start"]), float(word["end"])
                valid = all(math.isfinite(v) for v in (start, end)) and 0 <= start <= end <= duration + .15 and start >= last_start - .03
            except (KeyError, TypeError, ValueError):
                valid = False
            if not valid:
                issues.append({"severity": "error", "code": "word_timing", "detail": f"Invalid aligned word index {i}"})
            else:
                last_start = start
    if storyboard is not None:
        scenes = storyboard.get("scenes", [])
        if not scenes:
            issues.append({"severity": "error", "code": "empty_storyboard", "detail": "Storyboard has no scenes"})
        last_end = 0.0
        signatures: dict[str, int] = {}
        for scene in scenes:
            sid = str(scene.get("id", "unknown"))
            try:
                start, end = float(scene["start"]), float(scene["end"])
                if abs(start - last_end) > .10 or end <= start:
                    issues.append({"severity": "error", "code": "scene_coverage", "scene": sid,
                                   "detail": "Scene gap, overlap or invalid interval"})
                last_end = end
            except (KeyError, ValueError, TypeError):
                issues.append({"severity": "error", "code": "scene_timing", "scene": sid, "detail": "Missing numeric scene timing"})
                continue
            if not (scene.get("actors") or scene.get("props") or scene.get("blocks")):
                issues.append({"severity": "error", "code": "empty_scene", "scene": sid,
                               "detail": "Scene has no actors, props or explicit blocks"})
            actors = scene.get("actors", [])
            props = scene.get("props", [])
            animation_count = sum(len(a.get("actions", [])) for a in actors) + sum(len(p.get("animations", [])) for p in props)
            camera = scene.get("camera", {})
            camera_moves = camera.get("end_position") and camera.get("end_position") != camera.get("position")
            if end - start > 3.5 and not animation_count and not camera_moves:
                issues.append({"severity": "warning", "code": "static_plan", "scene": sid,
                               "detail": "No planned animation or camera change in a long scene"})
            signature = json.dumps({"environment": scene.get("environment"), "props": [p.get("kind") for p in props],
                                    "actions": [[a.get("type") for a in actor.get("actions", [])] for actor in actors]}, sort_keys=True)
            signatures[signature] = signatures.get(signature, 0) + 1
        if scenes and abs(last_end - duration) > .15:
            issues.append({"severity": "error", "code": "scene_end", "detail": "Storyboard does not end with narration"})
        if scenes and max(signatures.values(), default=0) > max(3, len(scenes) * .55):
            issues.append({"severity": "warning", "code": "repetition", "detail": "A majority of scenes share the same environment/props/actions"})
    return issues


def _contact_sheet(frames: np.ndarray, fps: float, output: Path) -> None:
    indices = np.unique(np.linspace(0, len(frames) - 1, min(20, len(frames)), dtype=int))
    columns = min(5, len(indices))
    rows = math.ceil(len(indices) / columns)
    w, h = frames.shape[2], frames.shape[1]
    sheet = Image.new("RGB", (columns * (w + 12) + 12, rows * (h + 32) + 12), "#171b22")
    draw = ImageDraw.Draw(sheet)
    for i, index in enumerate(indices):
        x, y = 12 + i % columns * (w + 12), 12 + i // columns * (h + 32)
        sheet.paste(Image.fromarray(frames[index]), (x, y))
        draw.text((x + 2, y + h + 6), f"{index / fps:.1f} s", fill="white")
    sheet.save(output)


def _render_metadata(video: Path) -> tuple[list[dict], list[dict]]:
    """Read projection measurements generated by Blender, if the job has them."""
    evidence, issues = [], []
    manifest = video.parent / "scene_cache.json"
    if not manifest.is_file():
        return evidence, issues
    try:
        clips = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return evidence, issues
    for clip in clips:
        source = Path(clip["path"]).parent / "frames/render_metadata.json"
        if not source.is_file():
            continue
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sid = str(clip.get("id", data.get("scene_id", "unknown")))
        projections = data.get("projections", [])
        actor_clipped = [p for p in projections if p.get("kind") == "actor" and p.get("in_frame") is False]
        # Blender reports normalized image coordinates with origin at bottom left.
        # Captions are centered at image y=.735 from the top, i.e. .265 here.
        caption_overlap = [p for p in projections if p.get("kind") == "actor" and len(p.get("bounds", [])) == 4
                           and p["bounds"][1] < .29 and p["bounds"][3] > .24
                           and p["bounds"][0] < .85 and p["bounds"][2] > .08]
        evidence.append({"scene": sid, "metadata": str(source), "projection_samples": len(projections),
                         "actor_clipped_samples": len(actor_clipped),
                         "actor_caption_overlap_samples": len(caption_overlap),
                         "missing_textures": data.get("missing_textures", [])})
        if data.get("missing_textures"):
            issues.append({"severity": "error", "code": "missing_textures", "scene": sid,
                           "detail": "Renderer reported missing texture materials", "materials": data["missing_textures"]})
        if actor_clipped:
            issues.append({"severity": "warning", "code": "actor_framing", "scene": sid,
                           "detail": "Measured actor bounds leave the frame; inspect whether the exit is intentional",
                           "samples": actor_clipped[:8]})
        if caption_overlap:
            issues.append({"severity": "warning", "code": "caption_actor_overlap", "scene": sid,
                           "detail": "Actor projected bounds intersect the caption band; inspect visibility",
                           "samples": caption_overlap[:8]})
    return evidence, issues


def inspect_video(video: str | Path, transcript=None, storyboard=None, output_dir=None) -> dict:
    """Inspect a rendered file and write ``qc_report.json``/``contact_sheet.jpg``.

    ``technical_pass`` only means all *implemented automated technical gates*
    passed. Semantic correctness, pixel-art fidelity, caption legibility and
    visual continuity remain explicit review items even when no flags occur.
    Input transcript/storyboard may be dictionaries or JSON paths.
    """
    path = Path(video).resolve()
    out = Path(output_dir).resolve() if output_dir is not None else path.parent / "qc"
    out.mkdir(parents=True, exist_ok=True)
    transcript, storyboard = _json_input(transcript), _json_input(storyboard)
    report: dict[str, Any] = {
        "version": 1, "video": str(path), "status": "needs_review", "issues": [],
        "scope": "Technical gates on decoded media and supplied timing data; semantic or artistic approval is not automated",
        "unverified": ["semantic match between narration and visible events", "vanilla Minecraft fidelity",
                       "caption legibility, actual burned-in word highlight and exact display timing",
                       "occlusion, object/character cropping, continuity and acting quality"],
        "thresholds": {"black_pixel_value": 8, "black_pixel_fraction": .985,
                       "static_sample_mean_difference": .12, "static_warning_seconds": 5.0,
                       "narration_duration_tolerance_seconds": .12},
    }
    issues = report["issues"]
    try:
        media = probe_media(path)
        streams = media.get("streams", [])
        visual = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if visual is None:
            raise ValueError("Rendered file has no video stream")
        container_duration = _duration(media.get("format", {}))
        duration = _duration(visual, container_duration)
        fps = float(Fraction(visual.get("avg_frame_rate", "0/1")))
        width, height = int(visual["width"]), int(visual["height"])
        report["media"] = {"duration": duration, "container_duration": container_duration,
                           "width": width, "height": height, "fps": fps,
                           "video_codec": visual.get("codec_name"), "pixel_format": visual.get("pix_fmt"),
                           "audio_codec": audio.get("codec_name") if audio else None,
                           "audio_duration": _duration(audio) if audio else None}
        if abs(width / height - 9 / 16) > .006:
            issues.append({"severity": "error", "code": "aspect_ratio", "detail": "Expected 9:16 portrait video"})
        if min(abs(fps - 30), abs(fps - 60)) > .02:
            issues.append({"severity": "error", "code": "frame_rate", "detail": "Expected 30 or 60 fps"})
        if visual.get("codec_name") != "h264" or visual.get("pix_fmt") != "yuv420p":
            issues.append({"severity": "error", "code": "video_format", "detail": "Expected H.264 yuv420p for social platforms"})
        if audio is None or audio.get("codec_name") != "aac":
            issues.append({"severity": "error", "code": "audio_format", "detail": "Expected an AAC narration stream"})
        elif abs(_duration(audio, duration) - duration) > .15:
            issues.append({"severity": "error", "code": "av_duration", "detail": "Audio and video durations differ by more than 150 ms"})
        expected = (transcript or storyboard or {}).get("duration")
        if expected is not None:
            drift = abs(duration - float(expected))
            report["narration_duration_error_seconds"] = round(drift, 6)
            if drift > .12:
                issues.append({"severity": "error", "code": "narration_duration", "detail": f"Video differs from source narration by {drift:.3f}s"})
        issues.extend(_check_timing(transcript, storyboard, float(expected) if expected is not None else duration))
        render_evidence, render_issues = _render_metadata(path)
        issues.extend(render_issues)
        report["render_measurements"] = render_evidence
        if render_evidence:
            report["unverified"][3] = "actual occlusion, unsampled object/character cropping, continuity and acting quality"
        frames, sample_fps = _sample_frames(path, duration)
        black = np.mean(np.max(frames, axis=3) < 8, axis=(1, 2)) > .985
        black_spans = _runs(black.tolist(), 1 / sample_fps, 1 / sample_fps)
        # Ignore caption area in freeze detection: moving text must not conceal a
        # frozen scene. Actual upper 72% of each sampled frame is compared.
        upper = frames[:, :int(frames.shape[1] * .72), :, :].astype(np.float32)
        differences = np.abs(np.diff(upper, axis=0)).mean(axis=(1, 2, 3))
        freeze_spans = _runs((differences < .12).tolist(), 1 / sample_fps, 5.0)
        report["frame_analysis"] = {"sample_count": len(frames), "sample_fps": sample_fps,
                                    "black_spans": black_spans, "static_spans": freeze_spans,
                                    "mean_scene_frame_difference": round(float(differences.mean()), 5) if len(differences) else None,
                                    "coverage": "Periodic decoded frames; sub-sample glitches can be missed"}
        if black_spans:
            issues.append({"severity": "error", "code": "black_frames", "detail": "Decoded black frames found", "spans": black_spans})
        if freeze_spans:
            issues.append({"severity": "warning", "code": "possible_freeze", "detail": "Scene region changes very little; compare with intended pauses", "spans": freeze_spans})
        affected = {str(i["scene"]) for i in issues if "scene" in i}
        for scene in (storyboard or {}).get("scenes", []):
            for span in black_spans + freeze_spans:
                if float(scene.get("start", 0)) < span["end"] and float(scene.get("end", 0)) > span["start"]:
                    affected.add(str(scene.get("id")))
        report["affected_scenes"] = sorted(affected)
        contact = out / "contact_sheet.jpg"
        _contact_sheet(frames, sample_fps, contact)
        report["contact_sheet"] = str(contact)
        if duration < 60:
            report["editorial_notice"] = "Audio shorter than 60 seconds may not meet TikTok Creator Rewards duration requirements; narration was not extended"
        report["technical_gates_passed"] = not any(i["severity"] == "error" for i in issues)
        report["status"] = "technical_pass" if not issues else "needs_review"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, ZeroDivisionError) as exc:
        issues.append({"severity": "error", "code": "inspection_failed", "detail": str(exc)})
        report["technical_gates_passed"] = False
    (out / "qc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
