"""Two individually directed TEST productions authored by Codex in this session.

These are reproducible fixtures, not the engine's general director or a template
for new narration. New uploads must be interpreted by the active Codex model.
"""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from minestory.director import compile_plan
from minestory.util import read_json,write_json

def act(kind,start,end,target=None,obj=None):
    a={"type":kind,"start":round(start,3),"end":round(end,3)}
    if target is not None:a["target"]=target
    if obj:a["object"]=obj
    return a
def anim(kind,start,end,to=None):
    a={"type":kind,"start":round(start,3),"end":round(end,3)}
    if to is not None:a["to"]=to
    return a
def actor(name,pos,actions,color="teal"):
    return {"id":name,"position":pos,"actions":actions,"color":color}
def prop(name,kind,pos,scale=1,material="gold",animations=None,voxels=None):
    p={"id":name,"kind":kind,"position":pos,"scale":scale,"material":material,"animations":animations or []}
    if voxels:p["voxels"]=voxels
    return p
def voxel(pos,size,material):return {"position":pos,"size":size,"material":material}
def paper(name,pos,scale=.6,material="white",damaged=False):
    vox=[voxel([0,0,0],[.68,.045,.96],"planks"),voxel([0,-.03,0],[.59,.012,.85],material),voxel([0,-.045,.15],[.43,.012,.4],"blue")]
    if damaged:
        for j in range(4):vox.append(voxel([-.2+j*.11,-.06,-.31+j*.13],[.16,.014,.045],"dark"))
        vox.append(voxel([.27,-.052,.35],[.11,.02,.19],"dirt"))
    return prop(name,"custom",pos,scale,"white",voxels=vox)
def custom(name,pos,voxels,scale=1,animations=None):return prop(name,"custom",pos,scale,"stone",animations,voxels)
def cue(beat,word,default=.5):
    for w in beat["words"]:
        if word in w["word"].lower():return max(.05,min(beat["end"]-beat["start"]-.15,w["start"]-beat["start"]-.1))
    return default
def scene(i,obj,env,actors,props,tags=None,camera=None,blocks=None):
    return {"beat_index":i,"objective":obj,"environment":env,"actors":actors,"props":props,"blocks":blocks or [],"semantic_tags":tags or [],
            "camera":camera or {"position":[4.5,-10,5.2],"target":[0,0,1.15],"scale":7.2,"end_position":[4.35,-9.85,5.16]}}

def cards(beats):
    scenes=[]
    for b in beats:
        i=b["index"];d=b["end"]-b["start"]
        hero=prop("rare","card",[0,-.15,1.2],.72,animations=[anim("rotate",0,d,[0,0,.45])])
        if i==0:
            props=[prop("chest","chest",[-.7,.7,0]),hero]
            for j in range(4):
                p=paper(f"ordinary{j}",[.4+j*.17,.6,.35],.34)
                p["animations"]=[anim("appear",1+j*.25,1.2+j*.25),anim("move",1.3+j*.25,2.3+j*.25,[.45+j*.2,.4,.9])]
                props.append(p)
            actors=[actor("Lia",[-1.3,-.35,0],[act("walk",0,1.5,[-.6,-.35,0]),act("look",1.5,2.4,[-.7,.7,.7]),act("hold",2.5,d,obj="rare")])]
            obj="Um explorador abre a investigação diante de um baú, retira cartas comuns e ergue um item pequeno; casas de blocos no fundo estabelecem a comparação de valor."
        elif i==1:
            props=[paper(f"ordinary{j}",[-1.05+(j%2)*.25,.2+(j//2)*.13,1.05],.35) for j in range(6)]+[hero,prop("stand","cube",[.65,.15,0],.7,"planks")]
            hero["position"]=[.65,0,1.25];hero["animations"]=[anim("grow",cue(b,"rara"),min(d,cue(b,"rara")+.6),[1,1,1]),anim("rotate",0,d,[0,0,.5])]
            actors=[actor("Lia",[-.25,-.7,0],[act("point",.1,min(d,2.1),[-1,.2,1]),act("surprise",max(.1,d-2),d)])]
            obj="A câmera compara uma pilha de exemplares simples com uma única carta dourada que se destaca; a reação marca a descoberta e a escassez."
        elif i==2:
            props=[hero,prop("stand","cube",[0,.1,.2],.55,"planks")]
            actors=[actor("Lia",[-1.4,-.5,0],[act("walk",.1,1.8,[-.85,-.4,0]),act("point",2,d,[0,-.15,1.2])]),
                    actor("Noa",[1.4,-.1,0],[act("run",.3,1.8,[.75,-.2,0]),act("point",1.9,d,[0,-.15,1.2])],"amber"),
                    actor("Ivo",[.45,1,0],[act("walk",.6,2.1,[.45,.55,0]),act("surprise",2.2,min(d,3.4)),act("look",min(d,3.4),d,[0,0,1.2])],"blue")]
            obj="Três interessados se aproximam do mesmo exemplar e levantam os braços; a oferta permanece em uma unidade enquanto a procura aumenta."
        elif i==3:
            props=[hero]
            actors=[actor("Lia",[-.85,-.3,0],[act("hold",0,d,obj="rare"),act("look",.2,d,[.95,0,1.7])]),actor("Noa",[1.25,.4,0],[act("walk",.1,d,[.4,1.4,0]),act("look",.2,d,[1,4,2])],"amber")]
            obj="A dona exibe a carta rara, mas um visitante passa e olha para outra direção: raridade sem interesse não produz uma compra."
        elif i==4:
            trophy=[voxel([0,0,.15],[.65,.45,.25],"stone"),voxel([0,0,.6],[.18,.18,.75],"gold"),voxel([0,0,1.1],[.7,.45,.45],"gold"),voxel([-.48,0,1.1],[.2,.22,.3],"gold"),voxel([.48,0,1.1],[.2,.22,.3],"gold")]
            props=[hero,custom("trophy",[.8,.8,0],trophy,.75),custom("archive",[-1,.75,.45],[voxel([0,0,0],[.6,.18,.8],"red"),voxel([0,-.12,0],[.5,.08,.68],"white")],.8)]
            props[1]["animations"]=[anim("appear",2,2.3)];props[2]["animations"]=[anim("appear",.4,.7)]
            actors=[actor("Noa",[-.7,-.6,0],[act("point",.1,2,[-1,.75,.8]),act("point",2.2,4,[.8,.8,1]),act("joy",4.1,min(d,5.3)),act("look",min(d,5.4),d,[0,0,1.2])],"amber")]
            obj="Um arquivo de memórias e um troféu de competição surgem junto da carta; o colecionador liga valor a história e conquista, sem usar marcas reais."
        elif i==5:
            damaged=paper("worn",[0,-.1,1.25],.85,damaged=True)
            props=[damaged]+[prop(f"offer{j}","coin",[.65+j*.12,-.1,.85],.45,animations=[anim("move",1.5+j*.25,2.5+j*.25,[.2+j*.12,-.1,.85])]) for j in range(3)]
            actors=[actor("Lia",[-1,-.3,0],[act("hold",.2,d,obj="worn")]),actor("Noa",[1,-.2,0],[act("point",.5,2,[0,0,1.2]),act("look",2.2,d,[0,0,1.2])],"amber")]
            obj="Em uma feira, a carta arranhada é apresentada e uma oferta pequena de moedas desliza até a vendedora. Marcas escuras são visíveis no papel."
        elif i==6:
            case=[voxel([0,0,0],[.9,.12,1.25],"blue"),voxel([0,-.08,0],[.78,.06,1.1],"white")]
            props=[hero,custom("protective_case",[.65,.1,1.1],case,.85)]
            hero["position"]=[.65,-.08,1.1];hero["scale"]=.7
            for j in range(5):props.append(prop(f"offer{j}","coin",[-.6+j*.1,-.15,.65+j*.1],.48,animations=[anim("appear",1+j*.3,1.2+j*.3)]))
            actors=[actor("Noa",[-.8,-.55,0],[act("point",.1,min(d,2.5),[.65,0,1.1]),act("surprise",min(d,3),min(d,4.1)),act("look",min(d,4.2),d,[.65,0,1.1])],"amber")]
            obj="A cópia bem preservada aparece num suporte com moldura protetora e recebe uma oferta maior, em continuidade com a negociação anterior."
        elif i==7:
            props=[paper("worn",[-.3,0,1.3],1.2,damaged=True)]
            for j in range(4):props.append(prop(f"price{j}","coin",[.8,0,.3+j*.24],.45,animations=[anim("move",1+j*.3,2.5+j*.3,[1.0,0,-.3]),anim("disappear",2.5+j*.3,2.7+j*.3)]))
            actors=[actor("Noa",[-1.1,-.25,0],[act("point",.1,2.1,[-.3,0,1.3]),act("fear",2.2,min(d,3.4)),act("look",min(d,3.5),d,[.8,0,.7])],"amber")]
            obj="Plano próximo das bordas gastas e riscos. Moedas descem e somem uma a uma para mostrar a redução da oferta."
        elif i==8:
            glass=[voxel([0,0,.2],[.12,.12,.6],"dark"),voxel([0,0,.7],[.65,.12,.65],"blue"),voxel([0,-.08,.7],[.45,.03,.45],"white")]
            props=[paper("sampleA",[-.7,.1,1.1],.75),paper("sampleB",[.7,.1,1.1],.75,material="sand"),custom("magnifier",[0,-.5,.7],glass,.6,animations=[anim("move",.4,2,[-.5,-.5,.7]),anim("move",2,3.8,[.55,-.5,.7])])]
            props.append(custom("verified",[.75,-.1,1.75],[voxel([-.1,0,0],[.12,.1,.35],"grass_top"),voxel([.1,0,.12],[.35,.1,.12],"grass_top")],.8,animations=[anim("appear",max(.5,d-2),max(.7,d-1.8))]))
            actors=[actor("Ivo",[0,.85,0],[act("point",.3,3,[-.7,.1,1.1]),act("point",3.1,d,[.7,.1,1.1])],"blue")]
            obj="Na bancada, duas impressões são comparadas com uma lupa de cuboides. Uma confirmação visual só surge após a inspeção, comunicando risco e verificação."
        elif i==9:
            props=[hero]
            for j in range(4):
                p=prop(f"bid{j}","cube",[.75,0,.2+j*.35],[.32,.32,.32],"gold",[anim("appear",.3+j*.35,.5+j*.35)])
                p["animations"].append(anim("move",max(2,d-1.3)+j*.08,d,[.75,0,.1+j*.16]));props.append(p)
            actors=[actor("Lia",[-1,-.3,0],[act("point",.1,1.2,[0,0,1.2]),act("jump",1.3,2.1),act("surprise",max(2.2,d-1.4),d)]),actor("Noa",[1,.75,0],[act("point",.8,2,[0,0,1.2]),act("look",2,d,[.75,0,1])],"amber")]
            obj="Compradores levantam os braços; a pilha de lances cresce e depois encolhe no aviso de queda. O movimento acompanha as duas direções do preço."
        elif i==10:
            props=[hero,prop("chest","chest",[-1,.6,0],.65)]
            for j in range(4):props.append(prop(f"foundation{j}","cube",[-.8+j*.5,0,.15],[.4,.4,.3],"planks",[anim("grow",1+j*.6,1.5+j*.6,[.4,.4,.65])]))
            hero["position"]=[0,-.1,1.35]
            actors=[actor("Lia",[-1.2,-.5,0],[act("point",.2,2,[-1,.6,.5]),act("point",2.2,d,[0,0,.8])])]
            obj="Um baú de moedas para de crescer. Quatro apoios de madeira se completam sob o item para representar a combinação de oferta, procura, confiança e memória."
        else:
            memory=paper("keepsake",[0,-.15,1.25],.7,material="sand")
            props=[memory,prop("coins","chest",[1,1,0],.55)]
            actors=[actor("Lia",[-.6,-.25,0],[act("hold",.1,1.8,obj="keepsake"),act("give",1.85,2.7,[.4,-.5,1.3],"keepsake"),act("joy",2.8,min(d,4))]),actor("Noa",[.8,-.15,0],[act("look",.1,2,[0,-.15,1.25]),act("receive",2.75,d,obj="keepsake"),act("joy",3.2,min(d,4.3))],"amber")]
            obj="Uma carta simples passa de uma pessoa para outra e ambas reagem com alegria; o baú de moedas fica no fundo para separar lembrança pessoal e preço."
        scenes.append(scene(i,obj,"laboratory" if i==8 else "market",actors,props,["value","cause_effect","comparison" if i in [1,6,7,8] else "acting"]))
    return {"title":"Por que uma carta pode valer tanto? — TESTE SINTÉTICO", "scenes":scenes}

def solar(beats):
    scenes=[]
    for b in beats:
        i=b["index"];d=b["end"]-b["start"]
        earth=prop("earth","earth",[.75,.2,1.5],.8,"blue",[anim("rotate",0,d,[0,0,.6])])
        sun=prop("sun","sun",[-1.15,.1,2.3],.7,"sun")
        actors=[];props=[earth];env="space"
        if i==0:
            t=cue(b,"desapare",1.5);sun["animations"]=[anim("disappear",t,t+.2)];props.append(sun)
            for j in range(5):
                p=prop(f"light{j}","cube",[-.7+j*.2,-.2,2.0-j*.07],.09,"gold",[anim("move",max(0,t-.1),d,[.65,.1,1.5]),anim("disappear",max(t+.3,d-.3),d)])
                props.append(p)
            actors=[actor("observer",[-.65,-.8,0],[act("point",.1,t,[-1.15,0,2.3]),act("surprise",t,min(d,t+1.2)),act("look",min(d,t+1.3),d,[.75,.2,1.5])])]
            obj="O Sol desaparece na hipótese, mas os pulsos luminosos que já estavam a caminho continuam viajando em direção à Terra."
        elif i==1:
            props.append(prop("lit_shell","earth",[.75,.2,1.5],.81,"blue",[anim("disappear",cue(b,"depois",2),min(d,cue(b,"depois",2)+.3))]));earth["material"]="dark"
            actors=[actor("observer",[-.7,-.8,0],[act("look",.1,2,[.75,.2,1.5]),act("fear",2.2,min(d,3.6))])]
            obj="A camada iluminada permanece um instante e some; a Terra escura revela a chegada do apagão e o observador reage."
        elif i==2:
            earth["position"]=[-1,.1,1.5];earth["animations"]=[anim("move",.2,d,[1.15,.1,1.5]),anim("rotate",0,d,[0,0,.4])]
            for j in range(7):props.append(prop(f"trajectory{j}","cube",[-1.2+j*.38,.15,.75],.07,"white"))
            obj="Sem o Sol, a Terra atravessa uma linha pontilhada reta de blocos. A trajetória explica a consequência gravitacional sem inventar uma explosão."
        elif i==3:
            props.append(prop("moon","moon",[1.45,.2,1.6],.25,"stone",[anim("orbit",0,d,[.75,.2,1.5])]))
            for j in range(3):props.append(prop(f"heat{j}","cube",[-.65+j*.25,.2,1.7],.12,"red",[anim("grow",.1,d,[.10,.10,.10])]))
            obj="A Lua segue junto da Terra em órbita curta; pequenos blocos de calor encolhem lentamente para mostrar que a temperatura não cai instantaneamente."
        elif i==4:
            env="night";props=[]
            ocean=custom("ocean",[.6,.2,0],[voxel([0,0,.2],[1.2,.8,.4],"water"),voxel([0,0,.48],[1.2,.8,.12],"white")],1)
            ocean["animations"]=[anim("grow",.5,d,[1,1,1.15])]
            plant=custom("plant",[-.7,-.1,0],[voxel([0,0,.6],[.12,.12,1.2],"log"),voxel([-.22,0,.8],[.5,.15,.3],"grass_top"),voxel([.22,0,1.05],[.5,.15,.3],"grass_top")],1,[anim("grow",cue(b,"plant",d*.55),d,[.8,.8,.45])])
            props=[ocean,plant];actors=[actor("observer",[.0,-.8,0],[act("point",.1,2,[.6,.2,.8]),act("look",2,d,[-.7,0,.7])])]
            obj="Um corte para a superfície mostra água acumulando uma camada de gelo e uma planta perdendo vigor. Reservas térmicas e dependência da luz são mostradas separadamente."
        elif i==5:
            env="underground"
            props=[custom("vent",[.6,.3,0],[voxel([0,0,.3],[1,.8,.6],"stone"),voxel([0,0,.7],[.4,.4,.3],"red"),voxel([0,0,1],[.16,.16,.3],"gold")],1),custom("organism",[-.5,.1,.5],[voxel([0,0,0],[.45,.25,.3],"white"),voxel([.2,-.1,.08],[.1,.08,.1],"dark")],1,[anim("move",.3,d,[.25,.2,.6])])]
            obj="Sob a superfície, um organismo se aproxima de uma fonte geotérmica feita de pedra e blocos quentes: um possível abrigo para algumas formas de vida."
        else:
            props=[earth,sun]
            sun["animations"]=[anim("appear",.2,.4),anim("rotate",.4,d,[0,0,.5])]
            actors=[actor("observer",[-.6,-.8,0],[act("point",.3,2,[-1.15,.1,2.3]),act("look",2,d,[.75,.2,1.5])])]
            obj="A representação retorna ao sistema com o Sol presente, encerrando a experiência mental e marcando que desaparecimento espontâneo não é um evento físico real."
        cam={"position":[3.5,-11,5.6],"target":[0,.1,1.35],"scale":8.2,"end_position":[3.4,-10.9,5.58]}
        scenes.append(scene(i,obj,env,actors,props,["hypothesis","cause_effect","science"],cam))
    return {"title":"E se o Sol desaparecesse? — TESTE SINTÉTICO", "scenes":scenes}

if __name__=="__main__":
    for name,build in [("cartas",cards),("sol",solar)]:
        job=ROOT/"productions"/f"{name}_preview"
        request=read_json(job/"director_request.json")
        plan=build(request["beats"])
        compile_plan(plan,request["beats"],request["beats"][-1]["end"],"codex-session")
        destination=job/"direction_plan.json"
        if destination.exists():raise FileExistsError(destination)
        write_json(destination,plan)
        write_json(ROOT/"examples"/f"direction_{name}.json",plan)
        print(destination)
