#!/usr/bin/env python3
"""Install only into this checkout. Downloads are pinned and checksummed."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv

ROOT = Path(__file__).resolve().parents[1]
LLAMA_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b11982/llama-b11982-bin-ubuntu-x64.tar.gz"
LLAMA_SHA = "a7e6cc16d423fc88c204a8d8e646c1d11b1d0de9ec4a56942f6c02936e9bf09c"
MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_SHA = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"

def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024),b""):
            result.update(block)
    return result.hexdigest()

def download(url, destination, expected):
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists() and sha(destination) == expected:
        print(f"Cache verificado: {destination.name}",flush=True)
        return
    partial = destination.with_suffix(destination.suffix+".partial")
    print(f"Baixando {destination.name} da fonte oficial…",flush=True)
    with urllib.request.urlopen(url,timeout=60) as response,partial.open("wb") as stream:
        shutil.copyfileobj(response,stream,1024*1024)
    actual = sha(partial)
    if actual != expected:
        partial.unlink()
        raise RuntimeError(f"SHA256 incorreto para {destination.name}: {actual}")
    partial.replace(destination)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-director",action="store_true",help="Instalar llama.cpp CPU e Qwen1.5B quantizado (~1.1GB)")
    parser.add_argument("--skip-python",action="store_true")
    args = parser.parse_args()
    if not args.skip_python:
        target = ROOT/".venv"
        python = target/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        if not python.exists():
            if shutil.which("uv"):
                subprocess.run(["uv","venv",str(target)],check=True)
            else:
                venv.EnvBuilder(with_pip=True).create(target)
        if shutil.which("uv"):
            command=["uv","pip","install","--python",str(python),"-e",str(ROOT)+"[dev]"]
        else:
            command=[str(python),"-m","pip","install","-e",str(ROOT)+"[dev]"]
        subprocess.run(command,check=True,cwd=ROOT)
    missing = [name for name in ("blender","ffmpeg","ffprobe") if not shutil.which(name)]
    if missing:
        print("Ferramentas do sistema ausentes: "+", ".join(missing))
        print("Instale Blender4.3+ e FFmpeg com libass/libx264 por seus distribuidores oficiais. Consulte docs/OPERATIONS.md.")
    if args.local_director:
        if platform.system()!="Linux" or platform.machine() not in {"x86_64","AMD64"}:
            raise RuntimeError("Download automático testado em Linuxx86-64. Outras plataformas: instale llama.cpp oficial e configure MINESTORY_LLM_URL.")
        archive = ROOT/".tools/llama.tar.gz"
        download(LLAMA_URL,archive,LLAMA_SHA)
        extracted=ROOT/".tools/llama"
        extracted.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,"r:gz") as stream:
            # data filter rejects escaping links, absolute paths and special files.
            stream.extractall(extracted,filter="data")
        download(MODEL_URL,ROOT/".models/qwen2.5-1.5b-instruct-q4_k_m.gguf",MODEL_SHA)
        subprocess.run([str(extracted/"llama-b11982/llama-server"),"--version"],check=True)
    print("Configuração local concluída. Execute .venv/bin/python -m minestory doctor")
    return bool(missing)

if __name__=="__main__":
    raise SystemExit(main())
