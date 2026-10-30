#!/usr/bin/env python3
"""Finish an actual native Mine-imator MP4 and inspect its decoded frames.

No renderer, 3D generator, upscale, voice synthesis, or playback speed change is
performed here. Inputs must already be 1080x1920 at 30 or 60 FPS. The narration
defines the duration; a short native clip is rejected instead of being padded.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from minestory.audio import probe_audio, validate_transcript
from minestory.qc import probe_media


def file_hash(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_new_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def positive_mib(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size cap must be a number of MiB") from exc
    if not math.isfinite(number) or not 1 <= number <= 4096:
        raise argparse.ArgumentTypeError("size cap must be finite and between 1 and 4096 MiB")
    return number


def encoder_limit(max_mib: float | None, duration: float) -> dict | None:
    if max_mib is None:
        return None
    cap_bytes = math.floor(max_mib * 1024 * 1024)
    # Reserve 20% for VBV startup bursts/container overhead. AAC remains 192k;
    # only the constrained-CRF video bitrate changes, never size/FPS/timing.
    maxrate_kbps = math.floor((cap_bytes * 8 / duration * .80 - 192000) / 1000)
    if maxrate_kbps < 128:
        raise ValueError("Size cap is too small for this narration duration and 192k AAC")
    return {"max_mib": max_mib, "max_bytes": cap_bytes, "safety_fraction": .80,
            "audio_bitrate_bps": 192000, "video_maxrate_kbps": maxrate_kbps,
            "video_bufsize_kbps": maxrate_kbps * 2, "mode": "CRF18 with x264 VBV constraint",
            "final_size_gate": "actual file bytes must not exceed max_bytes"}


def media_video(path: Path) -> dict:
    media = probe_media(path)
    visual = next((s for s in media["streams"] if s.get("codec_type") == "video"), None)
    if visual is None:
        raise ValueError("Native file has no video stream")
    fps = float(Fraction(visual.get("avg_frame_rate", "0/1")))
    duration = float(visual.get("duration") or media["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid native video duration")
    return {"probe": media, "stream": visual, "fps": fps, "duration": duration,
            "width": int(visual["width"]), "height": int(visual["height"])}


def parse_ass_time(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def check_inputs(video: Path, audio: Path, job: Path, captions: bool) -> dict:
    native = media_video(video)
    if (native["width"], native["height"]) != (1080, 1920):
        raise ValueError("Native export must be 1080x1920; no upscale is permitted")
    if min(abs(native["fps"] - 30), abs(native["fps"] - 60)) > .02:
        raise ValueError("Native export must be 30 or 60 FPS; no retiming is permitted")
    narration = probe_audio(audio)
    if native["duration"] + 1 / native["fps"] < narration["duration"]:
        raise ValueError("Native animation ends before the narration; export more real animated frames")
    transcript_path = job / "transcript.json"
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    validate_transcript(transcript)
    if abs(float(transcript["duration"]) - narration["duration"]) > .03:
        raise ValueError("Transcript duration differs from supplied narration")
    if transcript.get("audio_sha256") != file_hash(audio):
        raise ValueError("Transcript is not bound to the supplied narration SHA256")
    events = []
    if captions:
        for line in (job / "legendas.ass").read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                start, end = parse_ass_time(parts[1]), parse_ass_time(parts[2])
                if not 0 <= start < end <= narration["duration"] + .025:
                    raise ValueError("ASS cue extends outside narration or has invalid timing")
                events.append({"start": start, "end": end})
        if not events:
            raise ValueError("ASS file contains no timed caption events")
        if not (ROOT / "assets/fonts/PixelifySans.ttf").is_file():
            raise ValueError("Licensed Pixelify Sans font is unavailable")
    return {"native": {k: v for k, v in native.items() if k not in {"probe", "stream"}},
            "narration": narration, "narration_sha256": file_hash(audio),
            "transcript": str(transcript_path), "word_count": len(transcript["words"]),
            "forced_alignment": transcript.get("transcription", {}).get("forced_alignment", False),
            "caption_events": len(events), "captions": captions}


def runs(flags: list[bool], step: float, minimum: float) -> list[dict]:
    result, first = [], None
    for index, flag in enumerate(flags + [False]):
        if flag and first is None:
            first = index
        elif not flag and first is not None:
            if (index - first) * step + 1e-9 >= minimum:
                result.append({"start": round(first * step, 4), "end": round(index * step, 4)})
            first = None
    return result


def inspect_native_output(path: Path, expected: float, work: Path) -> dict:
    media = media_video(path)
    stream = media["stream"]
    audio = next((s for s in media["probe"]["streams"] if s.get("codec_type") == "audio"), None)
    issues = []
    if stream.get("codec_name") != "h264" or stream.get("pix_fmt") != "yuv420p":
        issues.append({"severity": "error", "code": "video_codec"})
    if audio is None or audio.get("codec_name") != "aac":
        issues.append({"severity": "error", "code": "audio_codec"})
    if (media["width"], media["height"]) != (1080, 1920):
        issues.append({"severity": "error", "code": "dimensions"})
    drift = abs(media["duration"] - expected)
    if drift > max(.04, 1 / media["fps"] + .012):
        issues.append({"severity": "error", "code": "duration", "difference_seconds": drift})
    audio_duration = float(audio.get("duration", expected)) if audio else 0
    if abs(audio_duration - expected) > .06:
        issues.append({"severity": "error", "code": "narration_duration"})

    # Decode every real output frame. Only contact-sheet/static samples are held
    # in memory. The upper 68% excludes the entire default caption band,
    # including glyph ascenders and outlines above the 73.5% center line.
    width, height = 216, 384
    stride = width * height * 3
    sample_every = max(1, round(media["fps"] / 2))
    black_flags, samples, sample_times = [], [], []
    command = ["ffmpeg", "-v", "error", "-threads", "2", "-i", str(path), "-an",
               "-vf", f"scale={width}:{height}:flags=area", "-fps_mode", "passthrough",
               "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        assert process.stdout is not None
        try:
            index = 0
            while True:
                chunk = process.stdout.read(stride)
                if not chunk:
                    break
                if len(chunk) != stride:
                    raise RuntimeError("Partial decoded frame")
                frame = np.frombuffer(chunk, dtype=np.uint8).reshape(height, width, 3)
                black_flags.append(bool(np.mean(np.max(frame, axis=2) < 8) > .985))
                if index % sample_every == 0:
                    samples.append(frame.copy())
                    sample_times.append(index / media["fps"])
                index += 1
            code = process.wait(timeout=30)
            if code:
                errors.seek(0)
                raise RuntimeError(errors.read().decode(errors="replace")[-2000:])
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
    if not black_flags:
        raise ValueError("No output frames decoded")
    black_spans = runs(black_flags, 1 / media["fps"], 1 / media["fps"])
    if black_spans:
        issues.append({"severity": "error", "code": "black_frames", "spans": black_spans})
    upper = np.asarray(samples)[:, :round(height * .68)].astype(np.float32)
    differences = np.abs(np.diff(upper, axis=0)).mean(axis=(1, 2, 3))
    static_spans = runs((differences < .12).tolist(), sample_every / media["fps"], 3)
    if static_spans:
        issues.append({"severity": "warning", "code": "possible_freeze", "spans": static_spans})
    indices = np.unique(np.linspace(0, len(samples) - 1, min(20, len(samples)), dtype=int))
    columns = min(5, len(indices))
    sheet = Image.new("RGB", (columns * (width + 12) + 12,
                             math.ceil(len(indices) / columns) * (height + 30) + 12), "#171b22")
    draw = ImageDraw.Draw(sheet)
    for position, index in enumerate(indices):
        x, y = 12 + position % columns * (width + 12), 12 + position // columns * (height + 30)
        sheet.paste(Image.fromarray(samples[index]), (x, y))
        draw.text((x + 3, y + height + 6), f"{sample_times[index]:.2f} s", fill="white")
    sheet.save(work / "contact_sheet.jpg", quality=92)
    return {
        "renderer": "native Mine-imator export supplied as input",
        "media": {k: v for k, v in media.items() if k not in {"probe", "stream"}},
        "video_codec": stream.get("codec_name"), "audio_codec": audio.get("codec_name") if audio else None,
        "source_narration_duration": expected, "audio_duration": audio_duration,
        "narration_duration_error_seconds": round(drift, 6),
        "decoded_frames": len(black_flags), "black_spans": black_spans,
        "static_spans": static_spans, "static_sample_fps": media["fps"] / sample_every,
        "thresholds": {"black_pixel_value": 8, "black_pixel_fraction": .985,
                       "static_sample_mean_difference": .12, "static_warning_seconds": 3,
                       "static_region_upper_fraction": .68},
        "issues": issues, "technical_gates_passed": not any(x["severity"] == "error" for x in issues),
        "status": "needs_visual_review",
        "unverified": ["semantic correspondence of events and narration", "vanilla fidelity",
                       "character/object cropping and continuity", "caption readability and acoustic word accuracy"],
        "caption_alignment_note": "Whisper acoustic estimates; not independent forced alignment",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True, help="MP4 exported by Mine-imator itself")
    parser.add_argument("--audio", type=Path, required=True, help="Original unchanged narration")
    parser.add_argument("--job", type=Path, required=True, help="Job containing transcript.json and legendas.ass")
    parser.add_argument("--captions", choices=("on", "off"), default="on")
    parser.add_argument("--max-mib", type=positive_mib,
                        help="Optional actual file cap in MiB; constrained CRF18 with 20%% bitrate reserve")
    parser.add_argument("--check-only", action="store_true", help="Read-only input validation, without rendering or writing")
    args = parser.parse_args()
    video, audio, job = args.video.resolve(), args.audio.resolve(), args.job.resolve()
    inputs = check_inputs(video, audio, job, args.captions == "on")
    limit = encoder_limit(args.max_mib, inputs["narration"]["duration"])
    if args.check_only:
        print(json.dumps({**inputs, "encoder_limit": limit}, ensure_ascii=False, indent=2))
        return
    final = job / "video_final.mp4"
    for name in ("video_final.mp4", "finish_report.json", "qc_report.json", "contact_sheet.jpg"):
        if (job / name).exists():
            raise SystemExit(f"Preserving existing {name}; use a new production version/job directory")
    work = Path(tempfile.mkdtemp(prefix=".finish-", dir=job))
    temporary = work / "video_final.mp4"
    report = {"status": "running", "input": inputs, "native_video": str(video),
              "output": str(final), "native_video_sha256": file_hash(video),
              "renderer_substitution": False, "upscale": False, "narration_speed": 1,
              "narration_gain": 1, "music": False, "effects": False,
              "work_directory": str(work), "encoder_limit": limit}
    started = time.monotonic()
    try:
        command = ["ffmpeg", "-n", "-hide_banner", "-nostdin", "-threads", "2",
                   "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0"]
        if args.captions == "on":
            shutil.copy2(job / "legendas.ass", work / "captions.ass")
            (work / "fonts").symlink_to(ROOT / "assets/fonts", target_is_directory=True)
            command.extend(["-vf", "ass=captions.ass:fontsdir=fonts"])
        command.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-threads", "2"])
        if limit is not None:
            command.extend(["-maxrate", f"{limit['video_maxrate_kbps']}k",
                            "-bufsize", f"{limit['video_bufsize_kbps']}k"])
        command.extend([
                        "-pix_fmt", "yuv420p", "-fps_mode", "passthrough", "-c:a", "aac",
                        "-b:a", "192k", "-ar", "48000", "-t", str(inputs["narration"]["duration"]),
                        "-movflags", "+faststart", str(temporary)])
        report["ffmpeg_command"] = command
        with (work / "ffmpeg.log").open("w") as log:
            subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
        if limit is not None:
            report["encoder_limit"]["actual_bytes"] = temporary.stat().st_size
            if temporary.stat().st_size > limit["max_bytes"]:
                raise RuntimeError("Encoded file exceeds actual size cap; temporary file retained, final not published")
        qc = inspect_native_output(temporary, inputs["narration"]["duration"], work)
        qc["video"] = str(final)
        qc["contact_sheet"] = str(job / "contact_sheet.jpg")
        qc["word_timestamps_validated_against_original_audio"] = True
        qc["source_audio_sha256"] = inputs["narration_sha256"]
        qc["encoder_limit"] = report["encoder_limit"]
        write_new_json(job / "qc_report.json", qc)
        os.link(work / "contact_sheet.jpg", job / "contact_sheet.jpg")
        if not qc["technical_gates_passed"]:
            raise RuntimeError("Technical QC failed; temporary video preserved, final output not published")
        # link() is atomic and fails if final already exists; no production can
        # be overwritten even if another process creates it after preflight.
        os.link(temporary, final)
        temporary.unlink()
        report.update(status="needs_visual_review", technical_gates_passed=True,
                      output_sha256=file_hash(final), elapsed_seconds=round(time.monotonic() - started, 3),
                      output_bytes=final.stat().st_size)
        if inputs["narration"]["duration"] < 60:
            report["editorial_notice"] = "Teste abaixo de 60s pode não cumprir a duração do Programa de Recompensas do TikTok; narração não ampliada."
    except Exception as exc:
        report.update(status="failed", error=str(exc), elapsed_seconds=round(time.monotonic() - started, 3))
        write_new_json(job / "finish_report.json", report)
        raise
    write_new_json(job / "finish_report.json", report)
    print(json.dumps({"video": str(final), "technical_gates_passed": True,
                      "visual_review_required": True, "duration": inputs["narration"]["duration"]}, indent=2))


if __name__ == "__main__":
    main()
