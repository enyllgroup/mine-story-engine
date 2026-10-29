import json
from minestory.library import Library

def test_content_addressed_library_preserves_assets_and_records_reusable_types(tmp_path):
    library=Library(tmp_path/"library")
    board={"scenes":[{"id":"scene_001","start":0,"end":2,"environment":"village","camera":{"position":[3,-6,5],"target":[0,0,1],"scale":7},
                      "actors":[{"id":"Lia","color":"teal","position":[0,0,0],"actions":[{"type":"jump","start":0,"end":1}]}],
                      "props":[{"id":"item","kind":"card","position":[0,0,1],"scale":1,"animations":[]}],"sound_events":[{"type":"whoosh","time":0,"gain":.1}]}]}
    first=library.remember(board,"first-production")
    rows=library.list();before={r["hash"]:(library.root/r["path"]).read_bytes() for r in rows}
    second=library.remember(board,"second-production")
    assert first==second
    kinds={r["kind"] for r in rows}
    assert {"pixel_texture","blockbench_model","rig-definition","animation-definition","camera-definition","environment-definition","lighting-definition","sound-effect","scene-definition"}<=kinds
    assert len(rows)==len(library.list())
    assert all((library.root/r["path"]).read_bytes()==before[r["hash"]] for r in library.list())
