"""CPU transcription of supplied narration. No speech synthesis in production."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

LOG = logging.getLogger(__name__)
SCHEMA_VERSION = 2


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Ferramenta necessária ausente: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{args[0]} falhou: {exc.stderr[-2500:]}") from exc


def probe_audio(audio_path: str | Path) -> dict[str, Any]:
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Narração não encontrada: {path}")
    result = _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    data = json.loads(result.stdout)
    streams = [s for s in data["streams"] if s["codec_type"] == "audio"]
    if not streams:
        raise ValueError("O arquivo não contém uma faixa de áudio.")
    stream = streams[0]
    duration = float(stream.get("duration") or data["format"].get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Duração de áudio inválida.")
    return {"duration": duration, "sample_rate": int(stream["sample_rate"]),
            "channels": int(stream["channels"]), "codec": stream["codec_name"],
            "path": str(path)}


def detect_silence(audio_path: str | Path, duration: float, threshold_db: float = -36,
                   min_duration: float = .35) -> list[dict[str, float]]:
    result = _run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(Path(audio_path).resolve()),
                   "-vn", "-af", f"silencedetect=noise={threshold_db}dB:d={min_duration}",
                   "-f", "null", "-"])
    pauses, pending = [], None
    for match in re.finditer(r"silence_(start|end):\s*([\d.eE+\-]+)", result.stderr):
        kind, value = match.group(1), min(duration, max(0., float(match.group(2))))
        if kind == "start":
            pending = value
        elif pending is not None:
            pauses.append({"start": round(pending, 4), "end": round(value, 4)})
            pending = None
    if pending is not None:
        pauses.append({"start": round(pending, 4), "end": round(duration, 4)})
    return pauses


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refine_silence_boundaries(words: list[dict[str, Any]], pauses: list[dict[str, float]]) -> int:
    """Clip model estimates to measured non-silent audio, retaining raw evidence.

    This is acoustic boundary refinement, not forced alignment. Entirely silent
    word estimates are flagged for review rather than assigned invented times.
    """
    adjusted = 0
    for word in words:
        original = float(word["start"]), float(word["end"])
        start, end = original
        for pause in pauses:
            left, right = pause["start"], pause["end"]
            if end <= left or start >= right:
                continue
            if left <= start and end <= right:
                word["silence_overlap_warning"] = True
                continue
            if start < left and end <= right:
                end = left
            elif left <= start and end > right:
                start = right
            elif start < left and end > right:
                if left - start >= end - right:
                    end = left
                else:
                    start = right
        if (start, end) != original and end > start:
            word["raw_start"], word["raw_end"] = original
            word["start"], word["end"] = round(start, 4), round(end, 4)
            word["alignment_refinement"] = "clipped-to-measured-silence-boundary"
            adjusted += 1
    return adjusted


def validate_transcript(data: dict[str, Any]) -> None:
    duration = float(data["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Transcrição com duração inválida")
    previous = -1.
    for item in data["words"]:
        start, end = float(item["start"]), float(item["end"])
        if not item["word"].strip() or not (0 <= start <= end <= duration + .025):
            raise ValueError(f"Timestamp de palavra inválido: {item}")
        if start + .025 < previous:
            raise ValueError("Palavras fora da ordem temporal")
        previous = start
    if not data["words"]:
        raise ValueError("Nenhuma palavra reconhecida. Verifique se o arquivo contém fala audível.")


def analyze(audio_path: str | Path, cache_dir: str | Path, model: str = "large-v3-turbo",
            language: str = "pt", cpu_threads: int | None = None,
            beam_size: int = 5, force: bool = False, **kwargs: Any) -> dict[str, Any]:
    """Return real Whisper word timestamps. Download model once; cache by audio+settings.

    Whisper's timestamps are model estimates, not independently verified forced
    alignment. The report explicitly records that limitation. All original audio
    samples and timing are kept by the subsequent muxing step.
    """
    from faster_whisper import WhisperModel

    path = Path(audio_path).resolve()
    probe = probe_audio(path)
    cache = Path(cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    version = importlib.metadata.version("faster-whisper")
    settings = {"schema": SCHEMA_VERSION, "backend": f"faster-whisper-{version}",
                "model": model, "language": language, "beam_size": beam_size}
    source_hash = _hash_file(path)
    key = hashlib.sha256((source_hash + json.dumps(settings, sort_keys=True)).encode()).hexdigest()
    cached = cache / f"transcript-{key}.json"
    if cached.exists() and not force:
        result = json.loads(cached.read_text(encoding="utf-8"))
        validate_transcript(result)
        result["cache_hit"] = True
        result["source"] = str(path)
        return result
    started = time.monotonic()
    threads = cpu_threads or max(1, min(4, (os.cpu_count() or 2) - 1))
    LOG.info("Transcrevendo PT-BR com Whisper %s, CPU int8 (%s threads)", model, threads)
    # Local files supplied as model are supported. Hugging Face cache is kept in
    # the project library, and no paid service or remote inference is used.
    engine = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads,
                          num_workers=1, download_root=str(cache / "models"))
    segments, info = engine.transcribe(str(path), language=language, beam_size=beam_size,
                                       word_timestamps=True, vad_filter=True,
                                       vad_parameters={"min_silence_duration_ms": 400},
                                       condition_on_previous_text=False,
                                       hallucination_silence_threshold=1.5)
    words, text_segments = [], []
    duration = probe["duration"]
    for segment in segments:
        actual_words = []
        for word in segment.words or []:
            token = word.word.strip()
            if not token:
                continue
            # Clamping corrects numerical boundary overshoot only. No invented
            # timings, duration weighting or text-to-speech alignment fallback.
            start = max(0., min(duration, float(word.start)))
            end = max(start, min(duration, float(word.end)))
            item = {"word": token, "start": round(start, 4), "end": round(end, 4),
                    "probability": round(float(word.probability), 5)}
            words.append(item)
            actual_words.append(token)
        if actual_words:
            text_segments.append({"text": " ".join(actual_words),
                                  "start": round(max(0., float(segment.start)), 4),
                                  "end": round(min(duration, float(segment.end)), 4),
                                  "avg_logprob": round(float(segment.avg_logprob), 5)})
    pauses = detect_silence(path, duration)
    refined_words = refine_silence_boundaries(words, pauses)
    result = {"schema_version": SCHEMA_VERSION, "source": str(path), "audio_sha256": source_hash,
              "language": "pt-BR" if language == "pt" else language, "duration": duration,
              "text": " ".join(w["word"] for w in words), "words": words,
              "segments": text_segments,
              "pauses": pauses, "audio": probe,
              "transcription": {**settings, "compute_type": "int8", "cpu_threads": threads,
                  "alignment": "whisper-word-timestamps+acoustic-silence-clipping", "forced_alignment": False,
                  "silence_refined_words": refined_words,
                  "language_probability": float(info.language_probability),
                  "elapsed_seconds": round(time.monotonic() - started, 3)},
              "cache_hit": False,
              "warnings": ["Timestamps estimados pelo Whisper; não são forced alignment independente."]}
    if duration < 60:
        result["warnings"].append("Áudio com menos de 60 segundos: pode não cumprir a duração exigida pelo Programa de Recompensas do TikTok. A narração foi preservada.")
    low_confidence = sum(w["probability"] < .5 for w in words)
    if words and low_confidence / len(words) > .15:
        result["warnings"].append("Mais de 15% das palavras têm baixa confiança; confira a transcrição antes de publicar.")
    validate_transcript(result)
    temporary = cached.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(cached)
    return result
