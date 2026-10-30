#!/usr/bin/env python3
"""Download and extract pinned Debian 13 X11 utilities into .tools, without root.

This is not a dependency resolver. It uses the host's Debian 13 shared libraries.
No Debian maintainer scripts are executed; only dpkg-deb extraction is used.
"""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = Path(__file__).with_name("debian_x11_packages.json")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / ".tools/x11")
    parser.add_argument("--verify-only", action="store_true",
                        help="verify cached package hashes; do not download or extract")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise SystemExit("These pinned packages require Linux x86-64 with Debian 13 libraries")
    target = args.directory.resolve()
    debs = target / "debs"
    if not args.verify_only:
        if not shutil.which("dpkg-deb"):
            raise SystemExit("dpkg-deb is required for local extraction")
        debs.mkdir(parents=True, exist_ok=True)
    checked = []
    for package in lock["packages"]:
        archive = debs / Path(package["Filename"]).name
        valid = archive.is_file() and digest(archive) == package["SHA256"]
        if not valid:
            if args.verify_only:
                raise SystemExit(f"Missing or invalid cached package: {archive.name}")
            partial = archive.with_suffix(".partial")
            with urllib.request.urlopen(lock["mirror"] + package["Filename"], timeout=60) as response:
                with partial.open("wb") as handle:
                    shutil.copyfileobj(response, handle)
            if digest(partial) != package["SHA256"]:
                partial.unlink()
                raise SystemExit(f"Checksum mismatch: {archive.name}")
            partial.replace(archive)
        if not args.verify_only:
            subprocess.run(["dpkg-deb", "-x", str(archive), str(target / "root")], check=True)
        checked.append({"package": package["Package"], "version": package["Version"],
                        "sha256": package["SHA256"]})
    result = {"distribution": lock["distribution"], "packages": checked,
              "root": str(target / "root"), "verified_only": args.verify_only}
    if not args.verify_only:
        (target / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
