import json
from pathlib import Path
from PIL import Image
from minestory.cache import compact_scene
from minestory.util import file_hash

def test_compaction_preserves_interrupted_frames_and_verified_video(tmp_path):
    folder=tmp_path/"scene";frames=folder/"frames";frames.mkdir(parents=True)
    for i in range(1,8):Image.new("RGB",(20,20),(i,0,0)).save(frames/f"frame_{i:04d}.png")
    assert compact_scene(folder)["reason"]=="incomplete"
    assert len(list(frames.glob("*.png")))==7
    clip=folder/"scene.mp4";clip.write_bytes(b"fixture: only integrity is under test")
    (folder/"complete.json").write_text(json.dumps({"clip_sha256":file_hash(clip)}))
    before=clip.read_bytes();report=compact_scene(folder,dry_run=True)
    assert report["files"]==4 and len(list(frames.glob("*.png")))==7
    report=compact_scene(folder)
    assert report["files"]==4
    assert {p.name for p in frames.glob("*.png")}=={"frame_0001.png","frame_0004.png","frame_0007.png"}
    assert clip.read_bytes()==before
    clip.write_bytes(b"corrupted")
    assert compact_scene(folder)["reason"]=="unverified"
