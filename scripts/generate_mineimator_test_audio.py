#!/usr/bin/env python3
"""Generate an explicitly synthetic, free PT-BR fixture; never a user narration.

Run with .venv/bin/python. Uses the existing Piper installation and cached
Whisper weights, without retiming the generated waveform. Existing audio is
preserved. Whisper word boundaries are estimates, not forced alignment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEXT = (
    "Uma carta comum pode existir aos milhares. Por isso, é fácil encontrar outra igual. "
    "Mas uma cópia rara muda a história. Um colecionador encontra a carta e percebe o brilho diferente. "
    "Outro se aproxima, curioso. Quando todos querem o mesmo objeto, mas existe apenas um, "
    "começa a disputa. O pequeno pedaço de papel vira um verdadeiro tesouro."
)
VOICE_SHA256 = "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "productions/mineimator-validation")
    parser.add_argument("--model", default="small", help="Whisper model; small is already cached on this host")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    path = output / "narracao_teste.wav"
    model = ROOT / ".tools/piper/pt_BR-faber-medium.onnx"
    if hashlib.file_digest(model.open("rb"), "sha256").hexdigest() != VOICE_SHA256:
        raise SystemExit("Piper voice hash differs from the pinned official model")
    if not path.exists():
        from piper import PiperVoice, SynthesisConfig
        voice = PiperVoice.load(model)
        with wave.open(str(path), "wb") as handle:
            voice.synthesize_wav(TEXT, handle, SynthesisConfig())
    with wave.open(str(path), "rb") as handle:
        duration = handle.getnframes() / handle.getframerate()
    if duration > 20:
        raise SystemExit(f"Fixture exceeds 20 seconds ({duration:.3f}); audio preserved without retiming")
    manifest = {
        "synthetic_test_only": True, "not_user_narration": True,
        "text": TEXT, "duration": duration, "engine": "Piper 1.8.0",
        "voice": "pt_BR-faber-medium", "voice_dataset_license": "CC0",
        "voice_dataset_model_card": "https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/faber/medium/MODEL_CARD",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "voice_speed_adjustment_after_generation": False,
    }
    manifest_path = output / "narracao_teste_manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    from minestory.audio import analyze
    from minestory.captions import write_captions
    transcript_path = output / "transcript.json"
    if transcript_path.exists():
        transcript = json.loads(transcript_path.read_text())
        if transcript["audio_sha256"] != manifest["sha256"]:
            raise SystemExit("Existing transcript belongs to a different audio; use a new output directory")
    else:
        transcript = analyze(path, ROOT / "library/cache", model=args.model, cpu_threads=1)
        transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
    # Do not replace a reviewed caption artifact or silently correct ASR words.
    if not (output / "legendas.ass").exists() and not (output / "legendas.srt").exists():
        report = write_captions(transcript, output, font_path=ROOT / "assets/fonts/PixelifySans.ttf")
        (output / "captions_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"audio": str(path), "duration": duration,
                      "transcript": str(transcript_path), "synthetic_test_only": True}, indent=2))


if __name__ == "__main__":
    main()
