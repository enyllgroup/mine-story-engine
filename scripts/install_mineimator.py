#!/usr/bin/env python3
"""Install the unmodified official Linux Mine-imator archive locally.

Does not activate Full, remove watermarks, download Minecraft separately,
modify the application, or install any system package.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import shutil
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
URL="https://www.mineimator.com/dl/mineimator-2.0.2-tar"
SHA256="b3e3508008a201dc5daf6f42506bdbf24735a870132e028ef2e53b5bff379a09"

def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle,"sha256").hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",type=Path,default=ROOT/".tools/mineimator")
    args=parser.parse_args()
    if platform.system()!="Linux" or platform.machine() not in {"x86_64","AMD64"}:
        raise SystemExit("This pinned archive is the official Linux x86-64 build only")
    target=args.directory.resolve();target.mkdir(parents=True,exist_ok=True)
    archive=target/"mineimator-2.0.2.tar.gz"
    if not archive.is_file() or digest(archive)!=SHA256:
        partial=archive.with_suffix(".partial")
        with urllib.request.urlopen(URL,timeout=60) as response,partial.open("wb") as handle:
            shutil.copyfileobj(response,handle,1024*1024)
        if digest(partial)!=SHA256:
            partial.unlink()
            raise SystemExit("Official archive checksum changed; refusing extraction")
        partial.replace(archive)
    executable=target/"official/Mine-imator/Mine-imator"
    if not executable.is_file():
        with tarfile.open(archive,"r:gz") as handle:
            handle.extractall(target/"official",filter="data")
    print(json.dumps({"version":"2.0.2","source":URL,"archive_sha256":SHA256,
                      "executable":str(executable),"activation":"unmodified; official Trial/Full mechanism retained"},indent=2))

if __name__=="__main__":main()
