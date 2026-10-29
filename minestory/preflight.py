"""Measure projected animated bounds in Blender and repair simple framing errors."""
from __future__ import annotations
import copy
import math
from pathlib import Path
from .util import ROOT,content_hash,read_json,run,write_json

def _unit(vector):
    length=math.sqrt(sum(x*x for x in vector)) or 1
    return [x/length for x in vector]

def _cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]

def inspect_framing(storyboard,output_dir, *, repair=True):
    result=copy.deepcopy(storyboard)
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    fixes=[]
    measurements=[]
    for scene in result["scenes"]:
        for attempt in range(2 if repair else 1):
            key=content_hash({"scene":scene,"renderer":(ROOT/"minestory/blender_scene.py").read_text()})
            folder=out/scene["id"]/key[:16]
            folder.mkdir(parents=True,exist_ok=True)
            write_json(folder/"scene.json",scene)
            metadata=folder/"render_metadata.json"
            if not metadata.exists():
                run(["blender","-b","--threads","2","--python",ROOT/"minestory/blender_scene.py","--",
                     "--scene",folder/"scene.json","--output",folder,"--width","270","--height","480","--fps","30","--still"],
                     log=folder/"preflight.log",timeout=120)
            data=read_json(metadata)
            rows=[p for p in data.get("projections",[]) if p.get("bounds") and p.get("kind") in {"actor","prop"}]
            if not rows:
                break
            bounds=[min(p["bounds"][0] for p in rows),min(p["bounds"][1] for p in rows),
                    max(p["bounds"][2] for p in rows),max(p["bounds"][3] for p in rows)]
            measurements.append({"scene":scene["id"],"attempt":attempt,"bounds":bounds,"metadata":str(metadata)})
            safe=bounds[0]>=.06 and bounds[1]>=.33 and bounds[2]<=.89 and bounds[3]<=.94
            if safe or not repair or attempt:
                break
            camera=scene["camera"]
            old=copy.deepcopy(camera)
            scale=float(camera.get("scale",8))
            factor=max(1,(bounds[2]-bounds[0])/.76,(bounds[3]-bounds[1])/.55)
            newscale=scale*factor*1.025
            # Orthographic coordinates scale around the camera's optical centre.
            cx=.5+((bounds[0]+bounds[2])/2-.5)/(newscale/scale)
            cy=.5+((bounds[1]+bounds[3])/2-.5)/(newscale/scale)
            direction=_unit([t-p for t,p in zip(camera["target"],camera["position"])])
            right=_unit(_cross(direction,[0,0,1]))
            up=_unit(_cross(right,direction))
            delta=[right[i]*(cx-.465)*newscale*9/16+up[i]*(cy-.64)*newscale for i in range(3)]
            for name in ("position","target","end_position","end_target"):
                if name in camera:
                    camera[name]=[round(v+d,5) for v,d in zip(camera[name],delta)]
            camera["scale"]=round(newscale,5)
            fixes.append({"scene":scene["id"],"reason":"Keep measured animated actor and prop bounds above caption band and inside portrait frame", "before":old,"after":copy.deepcopy(camera)})
    report={"measurements":measurements,"fixes":fixes,
            "limits":"Five sampled poses per scene; bounds cannot establish occlusion, editorial accuracy or all motion between samples."}
    write_json(out/"preflight_report.json",report)
    return result,report
