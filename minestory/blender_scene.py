"""Deterministic, headless Blender compiler for the MineStory scene format.

Run with Blender, not regular Python. Asset textures are original and generated
by ``python -m minestory.assets`` before compilation. No add-on is required.
Coordinates are metres, Z up. All action times are seconds relative to the shot.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time

import bpy
from mathutils import Vector, Matrix

VERSION = "1.0.0"
PALETTE = {
    "grass": (.34, .58, .18, 1), "grass_top": (.37,.62,.20,1),
    "grass_side": (.40,.30,.17,1), "dirt": (.45,.31,.20,1),
    "stone": (.49,.50,.50,1), "planks": (.63,.45,.24,1),
    "log": (.31,.23,.13,1), "log_side": (.31,.23,.13,1),
    "log_top": (.55,.42,.23,1), "leaves": (.24,.46,.13,1),
    "sand": (.83,.78,.54,1), "water": (.16,.40,.76,1),
    "brick": (.57,.28,.19,1), "card": (.91,.75,.24,1),
    "skin": (.72,.48,.32,1), "face": (.72,.48,.32,1),
    "hair": (.19,.12,.08,1), "cloth_teal": (.08,.60,.57,1),
    "shirt_front": (.08,.60,.57,1), "cloth_amber": (.81,.50,.10,1),
    "pants": (.23,.26,.54,1), "dark": (.14,.14,.16,1),
    "gold": (.97,.73,.13,1), "red": (.76,.14,.10,1),
    "white": (.94,.94,.89,1), "sun": (1,.79,.13,1),
    "blue": (.14,.43,.77,1), "earth": (.22,.48,.65,1),
    "moon": (.68,.69,.68,1), "purple": (.51,.24,.65,1),
    "black": (.018,.018,.026,1), "green": (.32,.68,.17,1),
    "glass": (.54,.79,.85,1), "iron": (.72,.73,.73,1),
}
MATS = {}
ASSET_ROOT = None
RNG = random.Random(0)
FPS = 30
DURATION = 5
FEND = 150


def frame(t):
    return max(1, min(FEND, 1 + round(float(t) * FPS)))


def key(obj, prop, t):
    obj.keyframe_insert(data_path=prop, frame=frame(t))


def linear(obj):
    if obj.animation_data and obj.animation_data.action:
        for curve in obj.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"


def mat(name):
    if isinstance(name, list):
        name = "#" + "".join(f"{max(0,min(255,int(c*255))):02x}" for c in name[:3])
    name = str(name or "stone")
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    color = PALETTE.get(name, (.55,.54,.50,1))
    if name.startswith("#"):
        try:
            color = tuple(int(name[i:i+2],16)/255 for i in (1,3,5)) + (1,)
        except ValueError:
            pass
    m.diffuse_color = color
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 1
    texture_name = {"grass":"grass_top", "log":"log_side", "earth":"water", "moon":"stone"}.get(name,name)
    texpath = None
    if ASSET_ROOT:
        for path in (ASSET_ROOT / "textures" / (texture_name+".png"), ASSET_ROOT / (texture_name+".png")):
            if path.exists():
                texpath = path
                break
    if texpath:
        img = bpy.data.images.load(str(texpath), check_existing=True)
    else:
        # Pure Blender fallback makes fresh scenes render without Pillow.
        # Texture generation is deterministic, never fetched from the game.
        img = bpy.data.images.new("pixel_"+name, width=16, height=16)
        rnd = random.Random(name)
        pixels = []
        for y in range(16):
            for x in range(16):
                v = rnd.choice([-.06,-.025,0,0,.025,.055])
                pixels.extend([max(0,min(1,c+v)) for c in color[:3]] + [1])
        img.pixels = pixels
    node = m.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    node.interpolation = "Closest"
    m.node_tree.nodes.active = node
    m.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
    MATS[name] = m
    return m


CUBE_MESHES = {}


def cube(name, position, size=(1,1,1), material="stone", parent=None, face_mats=None):
    # Direct datablocks avoid bpy.ops dependency-graph updates for every block.
    cache_key = (str(material), tuple(sorted((face_mats or {}).items())))
    mesh = CUBE_MESHES.get(cache_key)
    if mesh is None:
        verts = [(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),
                 (-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]
        faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        mesh = bpy.data.meshes.new("tile_"+str(material))
        mesh.from_pydata(verts,[],faces); mesh.update()
        mesh.materials.append(mat(material))
        uv = mesh.uv_layers.new(name="PixelUV")
        for poly in mesh.polygons:
            for i, loop_i in enumerate(poly.loop_indices):
                uv.data[loop_i].uv = [(0,0),(1,0),(1,1),(0,1)][i]
        if face_mats:
            for axis,mname in face_mats.items():
                mesh.materials.append(mat(mname));mi=len(mesh.materials)-1
                for poly in mesh.polygons:
                    n=poly.normal
                    if ((axis=="top" and n.z>.5) or (axis=="bottom" and n.z<-.5)
                        or (axis=="front" and n.y<-.5) or (axis=="back" and n.y>.5)
                        or (axis=="side" and abs(n.z)<.5)):
                        poly.material_index=mi
        CUBE_MESHES[cache_key]=mesh
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.location=position;obj.scale=size
    if parent:
        obj.parent=parent
    return obj


def empty(name, pos=(0,0,0), parent=None):
    obj = bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(obj)
    obj.location = pos
    obj.empty_display_size = .15
    obj.empty_display_type = "PLAIN_AXES"
    if parent:
        obj.parent = parent
    return obj


def block(pos, name="grass"):
    if name in ("grass", "grass_top"):
        return cube("grass_block",pos,material="dirt",face_mats={"side":"grass_side","top":"grass_top"})
    if name in ("log","log_side"):
        return cube("oak_log",pos,material="log_side",face_mats={"top":"log_top","bottom":"log_top"})
    return cube(name+"_block",pos,material=name)


def tree(x,y, height=3):
    for z in range(height):
        block((x,y,z+.5),"log")
    for z,rad in [(height-.3,1),(height+.7,1),(height+1.7,0)]:
        for dx in range(-rad,rad+1):
            for dy in range(-rad,rad+1):
                if rad and abs(dx)+abs(dy)==2 and RNG.random()<.25:
                    continue
                block((x+dx,y+dy,z),"leaves")


def house(x,y,w=4,d=4):
    for dx in range(w):
        for dy in range(d):
            block((x+dx,y+dy,-.05),"stone")
            if dx in (0,w-1) or dy in (0,d-1):
                for z in range(1,4):
                    if dy==0 and dx in (w//2,) and z<3:
                        continue
                    if z==2 and ((dx==w-1 and dy==d//2) or (dy==0 and dx==1)):
                        block((x+dx,y+dy,z-.05),"glass")
                    else:
                        block((x+dx,y+dy,z-.05),"log" if dx in (0,w-1) and dy in (0,d-1) else "planks")
    for row in range((w+2)//2+1):
        for dy in range(-1,d+1):
            for dx in sorted(set([-1+row,w-row])):
                block((x+dx,y+dy,3.5+row*.5),"brick")
    cube("door",(x+w//2,y-.48,.98),(.85,.11,1.9),"planks")
    cube("door_handle",(x+w//2+.22,y-.56,1.0),(.09,.08,.09),"dark")


def environment(kind, custom_blocks):
    space = kind in ("space","cosmos","solar_system","astronomy","void")
    bpy.context.scene.world.color = (.012,.018,.045) if space or kind=="night" else ((.055,.045,.04) if kind=="underground" else (.38,.66,.94))
    if kind in ("night","underground"):
        bpy.context.scene.view_settings.exposure=-.8 if kind=="night" else -.35
    if space:
        for i in range(95):
            # Fixed stars behind the action, tiny square particles.
            x,y,z=RNG.uniform(-12,12),RNG.uniform(8,13),RNG.uniform(-2,13)
            cube("star",(x,y,z),(RNG.choice([.045,.07,.10]),.025,.07),"white" if i%4 else "gold")
        # A floating observatory island keeps the original block language.
        if kind != "void":
            for x in range(-3,4):
                for y in range(-1,4):
                    if abs(x)+abs(y-1)>5:
                        continue
                    block((x,y,-.5),"stone")
                    if abs(x)<2 and abs(y-1)<2:
                        block((x,y,-1.5),"stone")
    else:
        # Distinct paths, layered terrain and buildings are generated, not plates.
        for x in range(-14,15):
            for y in range(-16,15):
                name = "grass"
                if abs(x)<1 and y<4:
                    name = "sand"
                if kind in ("laboratory","lab","museum","interior"):
                    name = "planks" if (x+y)%2 else "stone"
                elif kind=="desert":name="sand"
                elif kind=="snow":name="snow"
                elif kind=="underground":name="stone"
                elif kind=="ocean":name="water" if abs(x)>2 or abs(y)>2 else "sand"
                block((x,y,-.5),name)
        if kind in ("market","auction"):
            house(-8,9)
            for x,y,tint in [(-3.5,3,"cloth_teal"),(3.5,4,"cloth_amber")]:
                for dx in [-1,1]:
                    cube("stall_post",(x+dx,y,1.35),(.16,.16,2.7),"log")
                cube("market_counter",(x,y,.8),(2.4,.8,.18),"planks")
                for j in range(6):
                    cube("canopy",(x-1.1+j*.44,y,2.7),(.45,1.5,.15),tint if j%2 else "white")
            tree(-6,5);tree(7,9)
        elif kind in ("village","town","workshop","museum"):
            house(-6,4)
            house(3,6)
            tree(-5,0)
            tree(6,3)
            tree(-7,8)
        elif kind in ("laboratory","lab","interior"):
            # Research bench, block shelves, coloured specimen bottles.
            cube("lab_bench",(0,4,.65),(7,1.3,1.3),"planks")
            for x in (-3,-1,1,3):
                cube("cabinet",(x,5,2.3),(1.6,.5,1.8),"stone")
                cube("sample",(x,4.0,1.65),(.35,.35,.7),RNG.choice(["blue","red","green"]))
        elif kind in ("desert","history"):
            for x in range(-10,11):
                for y in range(-3,12):
                    if y>5 and abs(x)<4:
                        block((x,y,.5),"sand")
            tree(6,5)
        elif kind=="underground":
            # An open cross-section exposes the cave, without a roof hiding it.
            for x in range(-5,6):
                for z in range(3):
                    block((x,5,z+.5),"stone")
            for y in range(1,5):
                block((-4,y,.5),"stone");block((4,y,.5),"stone")
            cube("geothermal_crack",(0,3,.04),(1.7,.3,.08),"red")
        elif kind=="ocean":
            for x,y in [(-4,6),(5,8)]:
                cube("distant_islet",(x,y,.05),(2,2,.2),"sand")
        else:
            for x,y in [(-5,3),(5,5),(-7,8),(7,9)]:
                tree(x,y)
        # Vanilla style cloud geometry, with no translucent volumetric shader.
        if kind!="underground":
            for x,y,z in [(-5,10,8),(4,12,9),(-10,8,10)]:
                cube("cloud",(x,y,z),(4,.8,.4),"white")
                cube("cloud",(x+1,y,z+.2),(2,1.2,.6),"white")
    for spec in custom_blocks:
        pos = spec.get("position",spec.get("pos",[0,0,.5]))
        block(pos,spec.get("material","stone"))


def actor(spec):
    aid = str(spec.get("id","actor"))
    root = empty(aid,spec.get("position",[0,0,0]))
    root.rotation_euler[2] = math.radians(float(spec.get("rotation",0)))
    shirt = spec.get("color",spec.get("material","cloth_teal"))
    if shirt in ("teal","amber"):
        shirt = "cloth_"+shirt
    # Rigid segmented Minecraft rig at exactly 1/16 m per pixel.
    hips=empty(aid+"_hips",(0,0,.75),root)
    body=cube(aid+"_body",(0,0,.375),(.5,.25,.75),shirt,hips)
    # Clothing hem and chest pixel badge establish an original identity.
    cube(aid+"_hem",(0,-.129,.08),(.5,.012,.12),"dark",hips)
    cube(aid+"_badge",(-.11,-.138,.49),(.125,.012,.125),"gold",hips)
    head=empty(aid+"_head",(0,0,1.5),root)
    cube(aid+"_head_mesh",(0,0,.25),(.5,.5,.5),"skin",head,
         face_mats={"front":"face","top":"hair","back":"hair"})
    # Eyes sit on the true front (-Y). Useful even with the minimal fallback skin.
    for x in [-.125,.125]:
        cube(aid+"_eye",(x,-.252,.25),(.125,.012,.0625),"white",head)
        cube(aid+"_pupil",(x+.022,-.261,.25),(.0625,.012,.0625),"blue",head)
    cube(aid+"_nose",(0,-.258,.17),(.0625,.025,.0625),"skin",head)
    cube(aid+"_mouth",(0,-.259,.10),(.125,.012,.035),"hair",head)
    cube(aid+"_hair_fringe",(0,-.255,.44),(.5,.012,.125),"hair",head)
    arms={}
    hands={}
    legs={}
    for side,s in [("left",-1),("right",1)]:
        pivot=empty(aid+"_arm_"+side,(s*.375,0,1.5),root)
        cube(aid+"_sleeve_"+side,(0,0,-.14),(.25,.25,.28),shirt,pivot)
        cube(aid+"_forearm_"+side,(0,0,-.51),(.25,.25,.47),"skin",pivot)
        arms[side]=pivot
        hands[side]=empty(aid+"_hand_"+side,(0,-.05,-.70),pivot)
        leg=empty(aid+"_leg_"+side,(s*.125,0,.75),root)
        cube(aid+"_leg_mesh_"+side,(0,0,-.335),(.25,.25,.67),"pants",leg)
        cube(aid+"_boot_"+side,(0,-.02,-.69),(.25,.29,.125),"dark",leg)
        legs[side]=leg
    return {"root":root,"hips":hips,"head":head,"arms":arms,"hands":hands,"legs":legs,"spec":spec}


def voxel_ball(name,radius,material,parent,earth=False):
    # Stepped cube surface with square pixels, never smooth rounded geometry.
    step=radius/3
    for ix in range(-3,4):
        for iy in range(-3,4):
            for iz in range(-3,4):
                d=ix*ix+iy*iy+iz*iz
                if d>10 or d<3:
                    continue
                color=material
                if earth:
                    # Original deterministic continent masks.
                    if ((ix*7+iy*3+iz*11)%17)<7:
                        color="green"
                    if abs(iz)>=3:
                        color="white"
                cube(name,(ix*step,iy*step,iz*step),(step*1.02,)*3,color,parent)


def prop(spec):
    pid=str(spec.get("id","prop"))
    kind=spec.get("kind","custom")
    root=empty(pid,spec.get("position",[0,0,0]))
    size=spec.get("scale",1)
    root.scale=(size,size,size) if isinstance(size,(int,float)) else size
    if "rotation" in spec:
        rot=spec["rotation"]
        if isinstance(rot,(int,float)):
            root.rotation_euler[2]=math.radians(rot)
        else:
            root.rotation_euler=[math.radians(a) for a in rot]
    voxels=spec.get("voxels",spec.get("cuboids",[]))
    if voxels:
        for i,v in enumerate(voxels):
            cube(pid+"_"+str(i),v.get("position",v.get("pos",[0,0,0])),
                 v.get("size",[1,1,1]),v.get("material",spec.get("material","stone")),root)
    elif kind in ("card","collectible","trading_card"):
        cube(pid+"_gold_border",(0,0,0),(.68,.045,.96),"gold",root)
        cube(pid+"_paper",(0,-.027,0),(.58,.012,.84),"white",root)
        cube(pid+"_picture",(0,-.037,.15),(.47,.012,.43),"blue",root)
        # Original block creature editorial illustration, no brand/logo artwork.
        cube(pid+"_creature_body",(0,-.049,.16),(.21,.012,.23),"green",root)
        cube(pid+"_creature_head",(.05,-.052,.30),(.18,.012,.15),"green",root)
        cube(pid+"_creature_eye",(.10,-.063,.32),(.035,.008,.035),"dark",root)
        for z,w in [(-.18,.40),(-.27,.34),(-.34,.24)]:
            cube(pid+"_text_pixels",(-.04,-.04,z),(w,.012,.025),"dark",root)
        for x in [-.19,0,.19]:
            cube(pid+"_rarity",(x,-.045,-.07),(.07,.012,.07),"gold",root)
    elif kind in ("planet","earth","sun","moon","black_hole"):
        if kind=="black_hole":
            voxel_ball(pid,.72,"black",root)
            for i in range(24):
                a=i*math.tau/24
                bit=cube(pid+"_accretion",(math.cos(a)*1.08,math.sin(a)*1.08,.04),(.22,.22,.10),"gold" if i%3 else "red",root)
                bit.rotation_euler[2]=a
        else:
            material = spec.get("material",{"planet":"earth","earth":"earth","sun":"sun","moon":"moon"}.get(kind,"blue"))
            voxel_ball(pid,.8,material,root,earth=material in ("earth","water") or (kind in ("planet","earth") and material=="blue"))
    elif kind in ("coin","money"):
        for ix in range(-2,3):
            for iz in range(-2,3):
                if abs(ix)==2 and abs(iz)==2:
                    continue
                cube(pid,(ix*.1,0,iz*.1),(.1,.10,.1),"gold",root)
        cube(pid+"_stamp",(0,-.057,0),(.12,.02,.28),"sun",root)
    elif kind in ("chest","crate"):
        cube(pid+"_base",(0,0,.3),(.95,.75,.6),"planks",root)
        cube(pid+"_lid",(0,0,.65),(.98,.78,.15),"planks",root)
        for x in [-.38,.38]:
            cube(pid+"_strap",(x,-.389,.38),(.10,.018,.67),"dark",root)
        cube(pid+"_lock",(0,-.40,.42),(.16,.05,.22),"iron",root)
    elif kind in ("table","auction_table","bench"):
        cube(pid+"_top",(0,0,.83),(2.4,1.1,.18),"planks",root)
        for x in [-.95,.95]:
            for y in [-.4,.4]:
                cube(pid+"_leg",(x,y,.4),(.18,.18,.8),"log",root)
    elif kind in ("telescope","machine","microscope"):
        cube(pid+"_stand",(0,0,.6),(.25,.25,1.2),"stone",root)
        for x,y in [(-.4,-.25),(.4,-.25),(0,.4)]:
            leg=cube(pid+"_tripod",(x/2,y/2,.3),(.12,.12,.8),"dark",root)
            leg.rotation_euler=(.25,-x,0)
        barrel=cube(pid+"_barrel",(0,0,1.3),(.45,1.3,.45),"iron",root)
        barrel.rotation_euler[0]=.3
        cube(pid+"_lens",(0,-.67,1.5),(.35,.08,.35),"blue",root)
    elif kind in ("graph","bar_chart","chart"):
        values=spec.get("values",[1,2,3,5])
        for i,v in enumerate(values):
            cube(pid+"_bar",((i-(len(values)-1)/2)*.55,0,float(v)*.22),(.42,.5,max(.1,float(v)*.44)),"green" if i%2 else "gold",root)
    elif kind in ("star","spark"):
        cube(pid,(0,0,0),(.12,.12,.4),"gold",root)
        cube(pid,(0,0,0),(.4,.12,.12),"gold",root)
    elif kind in ("door",):
        cube(pid,(0,0,1),(.9,.15,2),"planks",root)
    elif kind in ("animal","cow","pig","wolf"):
        color=spec.get("material","skin" if kind=="pig" else "white")
        cube(pid+"_body",(0,0,.6),(.65,1,.55),color,root)
        cube(pid+"_head",(0,-.6,.8),(.5,.45,.45),color,root)
        for x in [-.19,.19]:
            for y in [-.32,.32]:
                cube(pid+"_leg",(x,y,.22),(.18,.18,.45),color,root)
        for x in [-.14,.14]:
            cube(pid+"_eye",(x,-.83,.87),(.09,.025,.09),"dark",root)
    else:
        cube(pid,(0,0,.5),spec.get("size",[1,1,1]),spec.get("material","stone"),root)
    return root


def animate_prop(obj,spec):
    basepos=obj.location.copy()
    basescale=obj.scale.copy()
    for a in spec.get("animations",[]):
        t0=float(a.get("start",0)); t1=float(a.get("end",DURATION))
        typ=a.get("type")
        if typ=="move":
            key(obj,"location",t0)
            obj.location=a.get("to",a.get("target",basepos))
            key(obj,"location",t1)
        elif typ=="rotate":
            key(obj,"rotation_euler",t0)
            # Contract uses radians for animation, like Blender's Python API.
            angles=a.get("to",[0,0,math.tau])
            obj.rotation_euler=[float(v) for v in angles]
            key(obj,"rotation_euler",t1)
        elif typ=="grow":
            key(obj,"scale",t0)
            target=a.get("to",a.get("scale",2))
            obj.scale=tuple(float(target)*x for x in basescale) if isinstance(target,(int,float)) else target
            key(obj,"scale",t1)
        elif typ in ("appear","disappear"):
            obj.scale=(.001,)*3 if typ=="appear" else basescale
            key(obj,"scale",max(0,t0-.10))
            obj.scale=basescale if typ=="appear" else (.001,)*3
            key(obj,"scale",t0+.15)
        elif typ=="orbit":
            center=a.get("center",a.get("to",[0,0,0])); radius=float(a.get("radius",(basepos-Vector(center)).length or 2.2))
            rounds=float(a.get("turns",1))
            for i in range(33):
                ang=i/32*math.tau*rounds
                obj.location=(center[0]+math.cos(ang)*radius,center[1]+math.sin(ang)*radius,center[2])
                key(obj,"location",t0+(t1-t0)*i/32)
        elif typ in ("pulse","float"):
            for i in range(max(2,round((t1-t0)*4)+1)):
                t=min(t1,t0+i*.25)
                if typ=="float":
                    obj.location=basepos+Vector((0,0,.08*math.sin((t-t0)*math.tau)))
                    key(obj,"location",t)
                else:
                    obj.scale=basescale*(1+.06*math.sin((t-t0)*math.tau))
                    key(obj,"scale",t)
    linear(obj)


def animate_actor(rig, props):
    root=rig["root"]; head=rig["head"]
    arms=rig["arms"]; legs=rig["legs"]
    actions=rig["spec"].get("actions",[])
    base=root.location.copy()
    # Idle acting: head tracking and breathing, never frozen between actions.
    for i in range(max(2,round(DURATION*2)+1)):
        t=min(DURATION,i*.5)
        active=[a.get("type") for a in actions if float(a.get("start",0))<=t<=float(a.get("end",DURATION))]
        if not any(a in active for a in ("look","surprise","fear","joy")):
            head.rotation_euler=(.025*math.sin(t*2.1),.015*math.sin(t*1.7),.055*math.sin(t*1.2))
            key(head,"rotation_euler",t)
        if not any(a in active for a in ("walk","run","jump","hold","give","receive","point","surprise","fear","joy")):
            for side,s in [("left",-1),("right",1)]:
                arms[side].rotation_euler=(.035*math.sin(t*2+s),s*.025,0)
                key(arms[side],"rotation_euler",t)
    for a in actions:
        typ=a.get("type","look"); t0=float(a.get("start",0)); t1=float(a.get("end",min(DURATION,t0+1)))
        if t1<=t0:
            t1=t0+.2
        if typ in ("walk","run"):
            start=root.location.copy(); target=Vector(a.get("target",a.get("to",start)))
            delta=target-start
            if delta.length>.001:
                root.rotation_euler[2]=math.atan2(delta.x,-delta.y)
                key(root,"rotation_euler",t0)
            key(root,"location",t0)
            root.location=target; key(root,"location",t1)
            cycle=.44 if typ=="run" else .65
            steps=max(2,round((t1-t0)/cycle*4))
            for i in range(steps+1):
                t=t0+(t1-t0)*i/steps
                phase=(t-t0)/cycle*math.tau
                amp=.85 if typ=="run" else .48
                for side,s in [("left",-1),("right",1)]:
                    legs[side].rotation_euler[0]=math.sin(phase)*amp*s
                    arms[side].rotation_euler[0]=-math.sin(phase)*amp*s
                    key(legs[side],"rotation_euler",t);key(arms[side],"rotation_euler",t)
            for limb in list(legs.values())+list(arms.values()):
                limb.rotation_euler=(0,0,0);key(limb,"rotation_euler",t1)
        elif typ=="jump":
            key(root,"location",t0)
            p=root.location.copy(); root.location.z+=.65;key(root,"location",(t0+t1)/2)
            root.location=p;key(root,"location",t1)
            for side,s in [("left",-1),("right",1)]:
                arms[side].rotation_euler[1]=s*-.65;key(arms[side],"rotation_euler",(t0+t1)/2)
                arms[side].rotation_euler=(0,0,0);key(arms[side],"rotation_euler",t1)
        elif typ in ("hold","give","receive","point"):
            arm=arms[a.get("hand","right")]
            # -X rotation raises arms forwards, toward the camera.
            arm.rotation_euler[0]=-.95 if typ=="hold" else -1.45
            key(arm,"rotation_euler",t0+.18)
            key(arm,"rotation_euler",t1)
            pid=a.get("object",a.get("prop"))
            if pid in props and typ in ("hold","receive"):
                ob=props[pid]
                # Child Of constraint is enabled at the precise pickup time.
                constraint=ob.constraints.new("CHILD_OF")
                constraint.target=rig["hands"][a.get("hand","right")]
                constraint.influence=0
                constraint.keyframe_insert(data_path="influence",frame=frame(max(0,t0-.01)))
                bpy.context.scene.frame_set(frame(t0))
                bpy.context.view_layer.update()
                constraint.inverse_matrix=Matrix.Translation((0,-.12,.04)) @ ob.matrix_world.inverted()
                constraint.influence=1
                constraint.keyframe_insert(data_path="influence",frame=frame(t0+.18))
                # Holding is a bounded interval: later exchanges can release it.
                constraint.keyframe_insert(data_path="influence",frame=frame(t1))
                constraint.influence=0
                constraint.keyframe_insert(data_path="influence",frame=frame(min(DURATION,t1+.035)))
            if pid in props and typ=="give":
                ob=props[pid]
                key(ob,"location",t0)
                ob.location=a.get("target",list(root.location+Vector((0,-1,1.25))))
                key(ob,"location",t1)
        elif typ in ("surprise","fear","joy"):
            for side,s in [("left",-1),("right",1)]:
                arm=arms[side]
                key(arm,"rotation_euler",t0)
                arm.rotation_euler=(-1.1 if typ=="surprise" else (-1.5 if typ=="joy" else -.5),s*(-.6 if typ=="joy" else -.2),0)
                key(arm,"rotation_euler",t0+.2)
                key(arm,"rotation_euler",max(t0+.2,t1-.15))
                arm.rotation_euler=(0,0,0);key(arm,"rotation_euler",t1)
            head.rotation_euler[0]=-.17 if typ!="fear" else .12
            key(head,"rotation_euler",t0+.2)
            if typ=="joy":
                key(root,"location",t0)
                pos=root.location.copy();root.location.z+=.18;key(root,"location",t0+.25)
                root.location=pos;key(root,"location",t0+.5)
            particle_root=empty(rig["root"].name+"_reaction",root.location+Vector((0,0,2.4)))
            if typ=="surprise":
                cube("exclamation",(0,0,.12),(.10,.10,.38),"gold",particle_root)
                cube("exclamation_dot",(0,0,-.18),(.10,.10,.10),"gold",particle_root)
            elif typ=="fear":
                cube("sweat",(.27,0,0),(.13,.10,.22),"blue",particle_root)
            else:
                for x in [-.22,.22]:
                    cube("joy",(x,0,0),(.12,.10,.12),"gold",particle_root)
            particle_root.scale=(.001,)*3;key(particle_root,"scale",max(0,t0-.01))
            particle_root.scale=(1,)*3;key(particle_root,"scale",t0+.18)
            particle_root.scale=(1,)*3;key(particle_root,"scale",max(t0+.2,t1-.10))
            particle_root.scale=(.001,)*3;key(particle_root,"scale",t1)
        elif typ=="sit":
            key(root,"location",t0)
            root.location.z-=.55;key(root,"location",t0+.35)
            for side in legs:
                legs[side].rotation_euler[0]=-math.pi/2;key(legs[side],"rotation_euler",t0+.35)
        elif typ=="fall":
            key(root,"rotation_euler",t0);key(root,"location",t0)
            root.rotation_euler[0]=math.pi/2;root.location.z+=.3
            key(root,"rotation_euler",t1);key(root,"location",t1)
        elif typ=="look":
            target=Vector(a.get("target",[0,-5,2]))
            delta=target-(root.location+Vector((0,0,1.75)))
            head.rotation_euler[2]=max(-.8,min(.8,math.atan2(delta.x,-delta.y)-root.rotation_euler[2]))
            head.rotation_euler[0]=max(-.45,min(.45,-math.atan2(delta.z,max(.01,math.hypot(delta.x,delta.y)))))
            key(head,"rotation_euler",t0+.2);key(head,"rotation_euler",t1)
    for obj in [root,head]+list(arms.values())+list(legs.values()):
        linear(obj)


def camera(spec):
    p=spec.get("position",[6,-10,5.5]); target=spec.get("target",[0,0,1.2])
    bpy.ops.object.camera_add(location=p)
    cam=bpy.context.object;cam.name="MineStory_Camera"
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type="ORTHO" if spec.get("projection","orthographic") in ("orthographic","ortho") else "PERSP"
    cam.data.ortho_scale=float(spec.get("scale",8))
    cam.data.lens=float(spec.get("lens",40))
    cam.data.clip_end=250
    bpy.context.scene.camera=cam
    key(cam,"location",0);key(cam,"rotation_euler",0)
    if "end_position" in spec:
        cam.location=spec["end_position"]
        end_target=spec.get("end_target",target)
        cam.rotation_euler=(Vector(end_target)-cam.location).to_track_quat('-Z','Y').to_euler()
    else:
        # Minimal motivated camera push, no cinematic orbit by default.
        cam.location+=Vector((-.10,.12,-.025))
    key(cam,"location",DURATION);key(cam,"rotation_euler",DURATION)
    linear(cam)
    return cam


def projection_report(rigs,props):
    from bpy_extras.object_utils import world_to_camera_view
    scene=bpy.context.scene
    result=[]
    for t in [0,DURATION*.25,DURATION*.5,DURATION*.75,max(0,DURATION-.04)]:
        scene.frame_set(frame(t));bpy.context.view_layer.update()
        entries=[(r["root"],"actor") for r in rigs]+[(o,"prop") for o in props.values()]
        for o,kind in entries:
            objects=[o]+list(o.children_recursive)
            points=[]
            for child in objects:
                if child.type!='MESH':
                    continue
                for corner in child.bound_box:
                    points.append(world_to_camera_view(scene,scene.camera,child.matrix_world@Vector(corner)))
            if not points:
                continue
            bounds=[min(p.x for p in points),min(p.y for p in points),max(p.x for p in points),max(p.y for p in points)]
            head=world_to_camera_view(scene,scene.camera,o.matrix_world@Vector((0,0,2)))
            foot=world_to_camera_view(scene,scene.camera,o.matrix_world@Vector((0,0,0)))
            result.append({"time":round(t,3),"id":o.name,"kind":kind,"head":[round(head.x,4),round(head.y,4)],"foot":[round(foot.x,4),round(foot.y,4)],"bounds":[round(v,4) for v in bounds],"in_frame":bounds[0]>=0 and bounds[1]>=0 and bounds[2]<=1 and bounds[3]<=1})
    scene.frame_set(1)
    return result


def main():
    global FPS,DURATION,FEND,ASSET_ROOT,RNG
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument('--scene',required=True);p.add_argument('--output',required=True)
    p.add_argument('--width',type=int,default=270);p.add_argument('--height',type=int,default=480)
    p.add_argument('--fps',type=int,default=30);p.add_argument('--assets')
    p.add_argument('--still',action='store_true');p.add_argument('--save-blend',action='store_true')
    p.add_argument('--start-frame',type=int,default=1);p.add_argument('--end-frame',type=int);p.add_argument('--frames',type=int);p.add_argument('--resume',action='store_true')
    args=p.parse_args(argv)
    spec=json.loads(Path(args.scene).read_text())
    if 'scene' in spec:
        spec=spec['scene']
    FPS=args.fps;DURATION=float(spec.get('end',5))-float(spec.get('start',0));FEND=max(1,args.frames if args.frames is not None else round(DURATION*FPS))
    ASSET_ROOT=Path(args.assets) if args.assets else Path(__file__).resolve().parents[1]/'library'/'assets'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from minestory.assets import generate_assets
    manifest=generate_assets(ASSET_ROOT)
    ASSET_ROOT=Path(next(iter(manifest['textures'].values()))).parent
    RNG=random.Random(str(spec.get('id','scene')))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=args.width;scene.render.resolution_y=args.height;scene.render.resolution_percentage=100
    scene.render.fps=FPS;scene.frame_start=args.start_frame;scene.frame_end=min(FEND,args.end_frame or FEND)
    scene.world=bpy.data.worlds.new('MineStory_World')
    sh=scene.display.shading
    sh.light='STUDIO';sh.studio_light='paint.sl';sh.color_type='TEXTURE'
    sh.show_shadows=False;sh.shadow_intensity=.23
    sh.show_cavity=False;sh.cavity_type='WORLD';sh.cavity_ridge_factor=.35;sh.cavity_valley_factor=.30
    sh.show_specular_highlight=False;sh.show_object_outline=False
    sh.background_type='WORLD'
    scene.display.render_aa='FXAA'
    scene.view_settings.view_transform='Standard'
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=10
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    environment(spec.get('environment','village'),spec.get('blocks',[]))
    props={str(s.get('id','prop')):prop(s) for s in spec.get('props',[])}
    rigs=[actor(s) for s in spec.get('actors',[])]
    for s in spec.get('props',[]):
        animate_prop(props[str(s.get('id','prop'))],s)
    for r in rigs:
        animate_actor(r,props)
    camera(spec.get('camera',{}))
    report={'renderer':'Blender Workbench','blender':bpy.app.version_string,'version':VERSION,'scene_id':spec.get('id'),'frames':FEND,'rendered_frame_start':scene.frame_start,'rendered_frame_end':scene.frame_end,'duration':DURATION,'resolution':[args.width,args.height],'fps':FPS,'object_count':len(bpy.data.objects),'projections':projection_report(rigs,props),'missing_textures':[m.name for m in MATS.values() if not m.use_nodes]}
    (out/'render_metadata.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (out/'frame_metadata.json').write_text(json.dumps(report['projections'],ensure_ascii=False,indent=2))
    if args.save_blend:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    tick=time.monotonic()
    if args.still:
        scene.frame_set(max(1,min(FEND,round(FEND*.45))))
        scene.render.filepath=str(out/'still.png')
        bpy.ops.render.render(write_still=True)
    else:
        scene.render.filepath=str(out/'frame_')
        if args.resume:
            for f in range(scene.frame_start,scene.frame_end+1):
                dest=out / f'frame_{f:04d}.png'
                if dest.exists() and dest.stat().st_size>100:
                    continue
                scene.frame_set(f)
                scene.render.filepath=str(dest)
                bpy.ops.render.render(write_still=True)
        else:
            bpy.ops.render.render(animation=True)
    report['render_seconds']=round(time.monotonic()-tick,3)
    (out/'render_metadata.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('MINESTORY_RENDER_COMPLETE '+json.dumps({'scene':spec.get('id'),'seconds':report['render_seconds'],'frames':1 if args.still else scene.frame_end-scene.frame_start+1}))

if __name__=='__main__':
    main()
