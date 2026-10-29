#!/usr/bin/env python3
"""Generate explicitly synthetic validation fixtures, never a user's narration.

Only this optional test utility uses TTS. Production audio.py transcribes supplied
speech and never generates or replaces a voice. eSpeak NG GPL-3.0+ binaries are
kept outside the repository, downloaded from official Debian archive with hashes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = [
    ("e/espeak-ng/", "espeak-ng_1.52.0+dfsg-5_amd64.deb"),
    ("e/espeak-ng/", "espeak-ng-data_1.52.0+dfsg-5_amd64.deb"),
    ("e/espeak-ng/", "libespeak-ng1_1.52.0+dfsg-5_amd64.deb"),
    ("p/pcaudiolib/", "libpcaudio0_1.3-1_amd64.deb"),
    ("s/sonic/", "libsonic0_0.2.0-13+b1_amd64.deb"),
]


def get_espeak(install: bool = False):
    binary = shutil.which("espeak-ng")
    if binary:
        return [binary], os.environ.copy()
    prefix = ROOT / ".tools/espeak/root"
    binary = prefix / "usr/bin/espeak-ng"
    if not binary.exists() and install:
        packages = ROOT / ".tools/espeak/packages"
        packages.mkdir(parents=True, exist_ok=True)
        manifest = []
        for part, name in PACKAGES:
            path = packages / name
            url = "https://deb.debian.org/debian/pool/main/" + part + name
            if not path.exists():
                urllib.request.urlretrieve(url, path)
            manifest.append({"url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            subprocess.run(["dpkg-deb", "-x", str(path), str(prefix)], check=True)
        (packages / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if not binary.exists():
        raise SystemExit("Instale espeak-ng no sistema ou execute este script com --install-espeak (Debian x86_64).")
    libs = prefix / "usr/lib/x86_64-linux-gnu"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(libs) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    env["ESPEAK_DATA_PATH"] = str(libs / "espeak-ng-data")
    return [str(binary), f"--path={libs}"], env


def synthesize(command, env, text: str, path: Path, speed: int = 155):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([*command, "-v", "pt-br", "-s", str(speed), "-p", "47", "-a", "110",
                    "-b", "1", "-w", str(path), "--stdin"], input=text, env=env, text=True, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-espeak", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "examples/audio")
    args = parser.parse_args()
    command, env = get_espeak(args.install_espeak)
    output = args.output.resolve()
    for name in ["cartas", "sol"]:
        synthesize(command, env, (ROOT / f"examples/demo_{name}.txt").read_text(), output / f"demo_{name}_SINTETICO.wav")
    phrases = ["Um bloco caiu no chão.", "Agora o explorador encontrou uma carta.", "O Sol desapareceu e o céu ficou escuro."]
    phrase_paths = []
    for i, phrase in enumerate(phrases):
        part = output / f".sync_{i}.wav"
        synthesize(command, env, phrase, part)
        phrase_paths.append(part)
    windows = []
    count = 0
    destination = output / "sincronia_SINTETICO.wav"
    with wave.open(str(destination), "wb") as out:
        for i, (phrase, part) in enumerate(zip(phrases, phrase_paths)):
            with wave.open(str(part), "rb") as inp:
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
            part.unlink()
    (output / "sincronia_ground_truth.json").write_text(json.dumps({"synthetic_test_only": True,
       "generator": "eSpeak NG 1.52.0 pt-br", "method": "separate phrase synthesis + exact 0.8-second inserted pauses",
       "phrases": windows, "duration": count/rate}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "README.txt").write_text("ÁUDIOS SINTÉTICOS DE TESTE — eSpeak NG pt-br. Não são a narração do usuário.\n"
      "Textos originais gerados exclusivamente para testar a engine. Pipeline de produção nunca usa TTS.\n")
    print(json.dumps({"synthetic_test_only": True, "output": str(output), "ground_truth": windows}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
