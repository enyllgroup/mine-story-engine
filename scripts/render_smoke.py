"""Create a real test shot: walk, pick up custom card, react, look."""
import json
from pathlib import Path

SCENE = {
    "id":"model_world_object_test", "start":0,"end":4,
    "narration":"Áudio sintético de validação: personagem encontra uma carta original.",
    "objective":"Validar rig, cenário, custom prop e interação em uma cena realmente animada.",
    "environment":"market",
    "actors":[{"id":"Lia","position":[-1.3,0,0],"color":"cloth_teal","actions":[
        {"type":"walk","start":0,"end":1.3,"target":[-.35,0,0]},
        {"type":"hold","start":1.4,"end":2.5,"object":"rare_card"},
        {"type":"surprise","start":2.5,"end":3.1},
        {"type":"look","start":3.1,"end":4,"target":[0,-4,2]}]},
        {"id":"Noa","position":[1.1,.5,0],"color":"cloth_amber","rotation":-20,"actions":[
        {"type":"point","start":.2,"end":1.5},{"type":"joy","start":2,"end":3.2}]}],
    "props":[{"id":"rare_card","kind":"card","position":[.1,-.3,1.05],"scale":.6,"animations":[{"type":"float","start":0,"end":1.3}]},
             {"id":"display","kind":"table","position":[0,1.8,0]},
             {"id":"chest","kind":"chest","position":[-1.9,1.7,0]}],
    "camera":{"position":[5,-10,5.3],"target":[0,.5,1.35],"scale":7.3}
}
if __name__=='__main__':
    out=Path(__file__).resolve().parents[1]/'examples'/'render_smoke.json'
    out.write_text(json.dumps(SCENE,ensure_ascii=False,indent=2))
    print(out)
