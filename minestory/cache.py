"""Compact only completed, verified scene caches; preserve interrupted frames."""
from pathlib import Path
import re
from filelock import FileLock,Timeout
from .util import ROOT,file_hash,read_json

def compact_scene(folder, *, dry_run=False):
    folder=Path(folder)
    marker=folder/"complete.json"
    clip=folder/"scene.mp4"
    if not marker.is_file() or not clip.is_file():
        return {"files":0,"bytes":0,"reason":"incomplete"}
    manifest=read_json(marker)
    if manifest.get("clip_sha256")!=file_hash(clip):
        return {"files":0,"bytes":0,"reason":"unverified"}
    frames=sorted(p for p in (folder/"frames").glob("frame_*.png") if re.fullmatch(r"frame_[0-9]+\.png",p.name))
    keep={frames[i] for i in {0,len(frames)//2,len(frames)-1}} if frames else set()
    remove=[p for p in frames if p not in keep]
    size=sum(p.stat().st_size for p in remove)
    if not dry_run:
        for path in remove:
            path.unlink()
    return {"files":len(remove),"bytes":size,"kept":len(keep),"dry_run":dry_run}

def compact_cache(directory=None, *, dry_run=False):
    root=Path(directory or ROOT/".cache/scenes")
    report={"scenes":0,"files":0,"bytes":0,"skipped_active":0,"dry_run":dry_run}
    for folder in root.iterdir() if root.exists() else []:
        if folder.is_symlink() or not folder.is_dir() or not re.fullmatch(r"[a-f0-9]{64}",folder.name):continue
        try:
            with FileLock(str(folder/".render.lock"),timeout=0):
                item=compact_scene(folder,dry_run=dry_run)
                report["scenes"]+=bool(item.get("files"))
                report["files"]+=item.get("files",0);report["bytes"]+=item.get("bytes",0)
        except Timeout:
            report["skipped_active"]+=1
    return report
