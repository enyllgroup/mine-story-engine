#!/usr/bin/env python3
"""Neural PT-BR synthetic fixtures ONLY; never used in the production pipeline.

Install optional test dependency: uv pip install --python .venv/bin/python piper-tts==1.8.0
Voice dataset CC0; engine GPL-3.0: https://github.com/OHF-Voice/piper1-gpl
https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/faber/medium/MODEL_CARD
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/"
FILES = {
    "pt_BR-faber-medium.onnx": "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7",
    "pt_BR-faber-medium.onnx.json": "7e694de195ae3fc36dd732c445eb04fb49b649854893cb5506b978f0d50a1d6f",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "examples/audio")
    parser.add_argument("--length-scale", type=float, default=1.05)
    args = parser.parse_args()
    model_dir = ROOT / ".tools/piper"
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, expected_hash in FILES.items():
        path = model_dir / name
        if not path.exists():
            urllib.request.urlretrieve(BASE + name, path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise SystemExit(f"Checksum divergente para {path}; não carregar modelo")
    from piper import PiperVoice, SynthesisConfig
    started = time.monotonic()
    voice = PiperVoice.load(model_dir / "pt_BR-faber-medium.onnx")
    config = SynthesisConfig(length_scale=args.length_scale, noise_scale=.667, noise_w_scale=.8)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"synthetic_test_only": True, "not_user_narration": True,
       "engine": "Piper 1.8.0", "voice": "pt_BR-faber-medium", "dataset_license": "CC0",
       "model_sha256": FILES["pt_BR-faber-medium.onnx"], "audio": []}
    for name in ["cartas", "sol"]:
        text = (ROOT / f"examples/demo_{name}.txt").read_text(encoding="utf-8")
        path = output / f"demo_{name}_PIPER_SINTETICO.wav"
        if path.exists():
            print(f"Preservado fixture existente: {path}")
        else:
            with wave.open(str(path), "wb") as handle:
                voice.synthesize_wav(text, handle, config)
        with wave.open(str(path), "rb") as handle:
            manifest["audio"].append({"path": str(path), "duration": handle.getnframes()/handle.getframerate(),
                  "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                  "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    phrases = ["Um bloco caiu no chão.", "Agora o explorador encontrou uma carta.", "O Sol desapareceu e o céu ficou escuro."]
    destination = output / "sincronia_PIPER_SINTETICO.wav"
    windows, count = [], 0
    if not destination.exists():
        with wave.open(str(destination), "wb") as out:
            for i, phrase in enumerate(phrases):
                buffer = io.BytesIO()
                with wave.open(buffer, "wb") as handle:
                    voice.synthesize_wav(phrase, handle, config)
                buffer.seek(0)
                with wave.open(buffer, "rb") as inp:
                    if i == 0:
                        out.setparams(inp.getparams())
                    rate, channels, width = inp.getframerate(), inp.getnchannels(), inp.getsampwidth()
                    frames = inp.readframes(inp.getnframes())
                    nframes = len(frames) // (channels * width)
                    windows.append({"text": phrase, "start": count/rate, "end": (count+nframes)/rate})
                    out.writeframes(frames)
                    pause = round(.8 * rate)
                    out.writeframes(bytes(pause * channels * width))
                    count += nframes + pause
        (output / "sincronia_piper_ground_truth.json").write_text(json.dumps({
            "synthetic_test_only": True, "generator": "Piper 1.8.0 pt_BR-faber-medium CC0",
            "method": "separate phrase synthesis + exact 0.8-second inserted pauses",
            "phrases": windows, "duration": count/rate}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["generation_elapsed_seconds"] = time.monotonic()-started
    (output / "piper_test_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "README.txt").write_text("ÁUDIOS SINTÉTICOS DE TESTE — eSpeak NG ou Piper CC0 pt-br. Não são a narração do usuário.\n"
       "Textos originais gerados exclusivamente para validar a engine. A produção nunca usa TTS.\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
