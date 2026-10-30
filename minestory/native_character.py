"""Original articulated Minecraft-proportion characters for native Mine-imator.

The reusable builder accepts a private profile. It does not embed a user's photo
or identity, call a paid service, or copy any official model/texture. Coordinates
in .mimodel use Y up; project keyframes use Z up (the native loader swaps axes).
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def box(start, end, color, description='', **kw):
    return {'type':'block','from':list(start),'to':list(end),'uv':[20,20],
            'color_blend':color,'description':description, **kw}


def part(name, position=(0,0,0), shapes=None, children=None, **kw):
    return {'name':name,'position':list(position),'shapes':shapes or [],
            'parts':children or [],**kw}


def flatten_parts(model):
    result=[]
    def visit(parts, parent=None):
        for item in parts:
            result.append((item,parent)); visit(item.get('parts',[]),item['name'])
    visit(model['parts']); return result


def validate_model(model):
    names=[p['name'] for p,_ in flatten_parts(model)]
    if len(names)!=len(set(names)): raise ValueError('Duplicate rig part')
    if not model.get('texture') or len(model.get('texture_size',[]))!=2:
        raise ValueError('Model texture metadata missing')
    for p,_ in flatten_parts(model):
        if len(p.get('position',[]))!=3: raise ValueError('Invalid part pivot')
        for s in p.get('shapes',[]):
            if s.get('type')!='block' or len(s.get('uv',[]))!=2:
                raise ValueError('Only explicit native block shapes are emitted')
            if any(a>=b for a,b in zip(s['from'],s['to'])):
                raise ValueError('Degenerate or inverted shape')
    return {'parts':len(names),'shapes':sum(len(p['shapes']) for p,_ in flatten_parts(model))}


def model_from_profile(profile):
    """Build articulated features, not just a flat player skin."""
    c=profile['palette'];skin=c['skin'];dark=c['hair'];cloth=c['sweatshirt'];pants=c['trousers']
    dark2=c.get('hair_highlight','#20252E');skin2=c.get('skin_shadow','#AD765D')
    silver=c.get('frame','#B3BDC4');lens=c.get('lens','#263D3E')
    # A standard block head plus separate facial surfaces, ears and extruded nose.
    face=[box((-4,0,-4),(4,8,4),skin,'head base'),
          box((-4.28,2.5,-.1),(-4,5,1.9),skin2,'left ear'),
          box((4,2.5,-.1),(4.28,5,1.9),skin2,'right ear'),
          box((-.6,2.05,4.01),(.6,3.8,4.48),skin2,'nose bridge'),
          box((-.75,2.05,4.1),(.75,2.65,4.7),skin,'nose tip'),
          box((-3.4,.1,4.01),(3.4,.75,4.12),c.get('beard','#343036'),'jaw stubble'),
          box((-1.7,-.1,4.01),(1.7,.65,4.18),dark,'goatee chin'),
          box((-.65,.4,4.1),(.65,.95,4.2),dark,'soul patch')]
    for x0,x1,yy in [(-2.05,-.25,2.13),(.25,2.05,2.13),(-1.55,-.15,2.38),(.15,1.55,2.38)]:
        face.append(box((x0,yy,4.05),(x1,yy+.22,4.27),dark,'moustache'))
    # Swept-back sculpted stepped silhouette: sides, layered crown and comb lines.
    hair=[box((-4.15,5.8,-4.15),(4.15,8.25,2.4),dark,'hair back and crown'),
          box((-4.15,4.9,-3.9),(-3.8,7.4,2.7),dark,'side fade left'),
          box((3.8,4.9,-3.9),(4.15,7.4,2.7),dark,'side fade right'),
          box((-3.85,7.55,1.5),(3.7,8.55,4.04),dark,'swept front fringe')]
    for i in range(9):
        x=-3.72+i*.83; z=-3.5+(i%3)*.22; height=8.45+.35*math.sin((i+.6)/9*math.pi)
        hair.append(box((x,8.05,z),(x+.66,height,3.35-(i%2)*.4),dark2 if i%3==0 else dark,'comb ridge'))
    hair += [box((-4.05,5.1,2.4),(-3.65,6.9,3.7),dark,'temple left'),
             box((3.65,5.1,2.4),(4.05,6.9,3.7),dark,'temple right')]
    # Eyes and eyebrows are genuinely separate animated parts below liftable visor.
    eyes=[]
    for side,x in [('right',-1.75),('left',1.75)]:
        eyes.append(part('eye_'+side,(x,4.85,4.025),[
            box((-.96,-.65,0),(.96,.65,.1),'#EAE8DD','eye white'),
            box((-.38,-.57,.11),(.38,.56,.19),c.get('eye','#503B31'),'iris'),
            box((-.16,-.48,.2),(.16,.46,.23),'#19252B','pupil'),
            box((-.23,.22,.24),(-.06,.43,.26),'#FAF4DD','eye glint')]))
        eyes.append(part('brow_'+side,(x,5.85,4.07),[
            box((-1.04,-.15,0),(1.04,.15,.16),dark,'brow')]))
        eyes.append(part('lid_'+side,(x,5.48,4.3),[
            box((-.99,-1.35,0),(.99,0,.12),skin,'eyelid')]))
    mouth=part('mouth',(0,1.35,4.1),[
        box((-1.05,-.14,0),(1.05,.14,.11),'#734347','mouth line'),
        box((-.85,-.26,.02),(.85,-.12,.15),'#BF7B79','lower lip')])
    visor=[]
    for x0,x1 in [(-4.05,-.55),(.55,4.05)]:
        visor.append(box((x0,-1.05,0),(x1,.85,.28),lens,'mirrored visor lens'))
        visor.append(box((x0,.85,-.03),(x1,1.04,.38),silver,'silver upper rim'))
        visor.append(box((x0,-1.19,-.03),(x1,-1.02,.34),silver,'silver lower rim'))
        for j in range(5):
            xx=x0+.24+j*.58
            if xx+.12<x1:
                visor.append(box((xx,-.8,.29),(xx+.12,.68,.31), '#5A7472' if j%2 else '#80918C','pixel reflection'))
    visor += [box((-.7,.52,-.03),(.7,.77,.35),silver,'nasal bridge'),
              box((-.76,-.08,-.05),(-.52,.65,.34),silver,'bridge left'),
              box((.52,-.08,-.05),(.76,.65,.34),silver,'bridge right'),
              box((-4.34,-.17,-5.8),(-4.07,.71,.32),silver,'left temple arm'),
              box((4.07,-.17,-5.8),(4.34,.71,.32),silver,'right temple arm')]
    glasses=part('glasses',(0,5.15,4.28),visor)
    head=part('head',(0,12,0),face,[part('hair',shapes=hair),*eyes,mouth,glasses])
    # Body has layered collar/hem/cuffs, embroidered pixel motif, segmented limbs.
    torso=[box((-4.06,0,-2.08),(4.06,11.8,2.08),cloth,'sweatshirt'),
           box((-2.45,11.45,-2.15),(2.45,12.05,2.16),c.get('cuff','#141D2C'),'ribbed collar'),
           box((-1.7,11.85,-1.7),(1.7,12.05,1.7),skin,'neck'),
           box((-4.13,-.18,-2.16),(4.13,.8,2.16),c.get('cuff','#141D2C'),'ribbed hem')]
    # Pixel embroidery is a clothing detail, no borrowed brand artwork.
    pink=c.get('chest_accent','#C69CBD')
    for i in range(9):
        x=-2.7+i*.63
        torso.append(box((x,6.8,2.1),(x+.4,7.15+(i%2)*.2,2.2),pink,'embroidered pixel accent'))
    torso.append(box((-3.45,2.2,2.09),(-.55,4.2,2.16),c.get('cloth_shadow','#182333'),'seam pocket'))
    body=part('body',(0,12,0),torso,[head])
    for side,sign in [('right',-1),('left',1)]:
        forearm=part(side+'_forearm',(0,-4,0),[
            box((-2,-4.8,-2),(2,0,2),cloth,'sleeve forearm'),
            box((-2.07,-5.4,-2.07),(2.07,-4.5,2.07),c.get('cuff','#141D2C'),'cuff'),
            box((-1.92,-6.05,-1.92),(1.92,-5.35,1.92),skin,'hand')])
        arm=part(side+'_arm',(sign*6,10,0),[
            box((-2,-4,-2),(2,2,2),cloth,'upper sleeve')],[forearm])
        # Grip locator is an empty native part, parenting props does not depend on skin.
        forearm['parts']=[part(side+'_grip',(0,-5.9,1.1))]
        body['parts'].append(arm)
    legs=[]
    for side,sign in [('right',-1),('left',1)]:
        shin=part(side+'_shin',(0,-6,0),[
            box((-1.96,-5.4,-1.98),(1.96,0,1.98),pants,'trouser shin'),
            box((-2.07,-6.1,-2.08),(2.07,-4.55,2.55),c.get('shoe','#222932'),'shoe'),
            box((-2.1,-6.15,-2.1),(2.1,-5.8,2.6),c.get('sole','#8D9091'),'sole')])
        legs.append(part(side+'_leg',(sign*2,12,0),[
            box((-1.98,-6,-1.99),(1.98,0,1.99),pants,'trouser thigh')],[shin]))
    model={'name':profile.get('model_name','channel_host'), 'texture':'host_atlas.png',
           'texture_size':[64,64], 'description':'Original private channel host, articulated native .mimodel',
           'parts':[body,*legs]}
    validate_model(model); return model


def default_pose():
    return {'lid_left':{'SCA_Z':.02},'lid_right':{'SCA_Z':.02}}


def animation_library(profile=None):
    """Explicit native-frame curves. At30FPS; clips compose onto a root/rig."""
    neutral=default_pose()
    clips={}
    def add(name,duration,curves,loop=False):
        clips[name]={'fps':30,'frames':duration,'loop':loop,'curves':curves}
    walk={}
    for part_name,sign in [('right_leg',1),('left_leg',-1),('right_arm',-1),('left_arm',1)]:
        walk[part_name]={str(f):{'ROT_X':sign*a} for f,a in [(0,-22),(4,0),(8,22),(12,0),(16,-22)]}
    for side,phase in [('right',0),('left',8)]:
        walk[side+'_shin']={str(f):{'ROT_X':max(0,math.sin((f+phase)/16*2*math.pi))*24} for f in range(0,17,2)}
        walk[side+'_forearm']={'0':{'ROT_X':12},'16':{'ROT_X':12}}
    walk['body']={'0':{'POS_Z':0},'4':{'POS_Z':.38},'8':{'POS_Z':0},'12':{'POS_Z':.38},'16':{'POS_Z':0}}
    add('walk',16,walk,True)
    run=copy.deepcopy(walk)
    for curve in run.values():
        for values in curve.values():
            for field in values:
                values[field]*=1.65
    add('run',16,run,True)
    add('look_left',30,{'head':{'0':{'ROT_Z':0},'15':{'ROT_Z':-28},'30':{'ROT_Z':0}}})
    add('point',45,{'right_arm':{'0':{'ROT_X':0},'15':{'ROT_X':-78,'ROT_Y':-10},'35':{'ROT_X':-78,'ROT_Y':-10},'45':{'ROT_X':0}},'right_forearm':{'0':{'ROT_X':0},'15':{'ROT_X':-5},'45':{'ROT_X':0}}})
    add('hold',60,{'right_arm':{'0':{'ROT_X':-45},'60':{'ROT_X':-45}},'right_forearm':{'0':{'ROT_X':-50},'60':{'ROT_X':-50}}},True)
    add('give',50,{'right_arm':{'0':{'ROT_X':-45},'25':{'ROT_X':-75},'50':{'ROT_X':-30}},'right_forearm':{'0':{'ROT_X':-50},'25':{'ROT_X':-10},'50':{'ROT_X':-35}}})
    add('receive',50,{'left_arm':{'0':{'ROT_X':-10},'25':{'ROT_X':-68},'50':{'ROT_X':-40}},'left_forearm':{'0':{'ROT_X':-5},'25':{'ROT_X':-15},'50':{'ROT_X':-45}}})
    add('surprise',45,{'body':{'0':{'ROT_X':0},'9':{'ROT_X':-9},'22':{'ROT_X':3},'45':{'ROT_X':0}},'head':{'0':{},'9':{'ROT_X':-14},'45':{}},'mouth':{'0':{},'9':{'SCA_Z':2.8,'SCA_X':.7},'35':{'SCA_Z':1.8},'45':{}},'right_arm':{'0':{},'9':{'ROT_X':-80,'ROT_Y':-22},'45':{}},'left_arm':{'0':{},'9':{'ROT_X':-65,'ROT_Y':22},'45':{}}})
    add('joy',60,{'right_arm':{'0':{},'15':{'ROT_X':-145,'ROT_Y':-20},'45':{'ROT_X':-135,'ROT_Y':-20},'60':{}},'left_arm':{'0':{},'15':{'ROT_X':-145,'ROT_Y':20},'45':{'ROT_X':-135,'ROT_Y':20},'60':{}},'mouth':{'0':{},'15':{'SCA_X':1.35,'SCA_Z':1.8},'60':{}}})
    add('fear',45,{'body':{'0':{},'15':{'ROT_X':-12},'45':{}},'head':{'0':{},'15':{'ROT_X':-10,'ROT_Z':10},'45':{}},'brow_left':{'0':{},'15':{'ROT_Y':-16},'45':{}},'brow_right':{'0':{},'15':{'ROT_Y':16},'45':{}}})
    add('jump',30,{'__root__':{'0':{'POS_Z':0},'6':{'POS_Z':-1},'14':{'POS_Z':6},'22':{'POS_Z':0},'30':{'POS_Z':0}},'right_leg':{'0':{},'6':{'ROT_X':-15},'14':{'ROT_X':10},'30':{}},'left_leg':{'0':{},'6':{'ROT_X':15},'14':{'ROT_X':-10},'30':{}}})
    add('sit',45,{'right_leg':{'0':{},'20':{'ROT_X':-88},'45':{'ROT_X':-88}},'left_leg':{'0':{},'20':{'ROT_X':-88},'45':{'ROT_X':-88}},'right_shin':{'0':{},'20':{'ROT_X':88},'45':{'ROT_X':88}},'left_shin':{'0':{},'20':{'ROT_X':88},'45':{'ROT_X':88}}})
    add('fall',40,{'__root__':{'0':{},'16':{'ROT_X':25},'30':{'ROT_X':90,'POS_Z':3},'40':{'ROT_X':90,'POS_Z':3}},'right_arm':{'0':{},'12':{'ROT_X':-85},'40':{'ROT_X':-70}}})
    add('glasses_lift',45,{'glasses':{'0':{},'15':{'POS_Z':1.5,'ROT_X':-28},'30':{'POS_Z':1.5,'ROT_X':-28},'45':{}}})
    add('blink',8,{'lid_left':{'0':{'SCA_Z':.02},'3':{'SCA_Z':1},'5':{'SCA_Z':1},'8':{'SCA_Z':.02}},'lid_right':{'0':{'SCA_Z':.02},'3':{'SCA_Z':1},'5':{'SCA_Z':1},'8':{'SCA_Z':.02}}})
    policy=(profile or {}).get('appearance_policy',{})
    if policy.get('glasses_always_on'):
        clips.pop('glasses_lift',None)
    return {'schema':1,'native_coordinate_system':'XYZ with Z up','default_pose':neutral,
            'appearance_policy':copy.deepcopy(policy),'clips':clips}


def build_character(profile: dict, destination: Path):
    if destination.exists(): raise FileExistsError('Character version already exists; choose a new version')
    destination.mkdir(parents=True,exist_ok=False)
    model=model_from_profile(profile); stats=validate_model(model)
    write_new(destination/'profile.json',profile)
    write_new(destination/'host.mimodel',model)
    animations=animation_library(profile)
    write_new(destination/'animations.json',animations)
    # White lightly dithered atlas modulates the explicit original shape palette.
    im=Image.new('RGBA',(64,64),'white'); px=im.load()
    for y in range(64):
        for x in range(64):
            n=255-((x*17+y*31+(x*y)%7)%5)*2
            px[x,y]=(n,n,n,255)
    im.save(destination/'host_atlas.png')
    hashes={p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in destination.iterdir() if p.is_file()}
    write_new(destination/'manifest.json',{'id':profile['id'],'version':profile['version'],
        'status':'awaiting_user_review','native_validation':'pending native load/render by owner',
        'source':'appearance interpreted from user-supplied photo; original geometry and texture',
        'private_likeness':True,'model':stats,'files':hashes,'animation_clips':list(animations['clips']),'appearance_policy':copy.deepcopy(profile.get('appearance_policy',{})),
        'unseen_lower_body':'Original navy trousers and gray-soled shoes; not inferred as photo fact'})
    return destination


def add_character(doc, directory: Path, job: Path, actor_id='host', root_keys=None):
    """Copy immutable character version into a new job and create native timelines."""
    assets=job/'assets'/actor_id
    if assets.exists(): raise FileExistsError('Actor job assets already exist')
    assets.mkdir(parents=True,exist_ok=False)
    model=json.loads((directory/'host.mimodel').read_text())
    texture=(assets/'host_atlas.png').relative_to(job).as_posix()
    model['texture']=texture
    shutil.copy2(directory/'host_atlas.png',assets/'host_atlas.png')
    write_new(assets/'host.mimodel',model)
    res_id=actor_id+'_model_res';temp_id=actor_id+'_rig'
    doc.setdefault('resources',[]).append({'id':res_id,'type':'model','filename':(assets/'host.mimodel').relative_to(job).as_posix()})
    doc.setdefault('templates',[]).append({'id':temp_id,'type':'model','name':actor_id,'model':res_id,'model_tex':'null','model_tex_material':'null','model_tex_normal':'null'})
    def tl(tid,typ,parent,temp=temp_id,**kw):
        value={'id':tid,'name':tid,'type':typ,'parent':parent,'temp':temp,'parent_tree_index':-1,
               'keyframes':{'0':{}},'default_values':{},'texture_filtering':False,**kw}
        doc.setdefault('timelines',[]).append(value);return value
    roots=[p['name'] for p,_ in flatten_parts(model)]
    tl(actor_id,'model','root',parts=[actor_id+'_'+p for p in roots],keyframes={str(f):v for f,v in (root_keys or {0:{'ROT_Z':180},359:{'ROT_Z':180}}).items()})
    neutral=default_pose()
    for p,parent in flatten_parts(model):
        name=p['name']
        value=tl(actor_id+'_'+name,'bodypart',actor_id+'_'+parent if parent else actor_id,
                 part_of=actor_id,model_part_name=name,
                 inherit={'alpha':True,'color':True,'texture':True,'surface':True,'subsurface':True,'rot_point':True})
        if name in neutral:value['keyframes']={'0':neutral[name]}
    return model


def _field_default(field, values):
    return values.get(field, 1 if field.startswith('SCA_') else (True if field == 'VISIBLE' else 0))


def _sample_curve(curve, frame, fields, defaults):
    keys=sorted((int(k),v) for k,v in curve.items())
    if not keys:return {f:_field_default(f,defaults) for f in fields}
    left=max((item for item in keys if item[0]<=frame),default=keys[0],key=lambda item:item[0])
    right=min((item for item in keys if item[0]>=frame),default=keys[-1],key=lambda item:item[0])
    amount=0 if right[0]==left[0] else (frame-left[0])/(right[0]-left[0])
    result={}
    for field in fields:
        a=left[1].get(field,_field_default(field,defaults));b=right[1].get(field,_field_default(field,defaults))
        result[field]=(a+(b-a)*amount) if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) else a
    return result


def apply_clip(doc, directory, actor_id, name, start, end=None, repeat=False, amplitude=1):
    """Compose independent native channels without resetting existing trajectories.

    Native omitted fields reset to timeline defaults, rather than inheriting the
    previous keyframe. Materialize complete channels at inserted times. Root
    animation curves are offsets on the already authored root trajectory.
    """
    library=json.loads((Path(directory)/'animations.json').read_text())
    profile_path=Path(directory)/'profile.json'
    profile=json.loads(profile_path.read_text()) if profile_path.is_file() else {}
    always_on=profile.get('appearance_policy',{}).get('glasses_always_on',False)
    if always_on and name=='glasses_lift':
        raise ValueError('Character policy requires glasses always on; lifting/removal is disabled')
    clip=library['clips'][name]
    if always_on:
        for pose in clip['curves'].get('glasses',{}).values():
            for field,value in pose.items():
                expected=1 if field.startswith('SCA_') or field in ('ALPHA','VISIBLE') else 0
                if value!=expected:
                    raise ValueError('Character policy requires glasses always on; eyewear transformation refused')
    duration=clip['frames'];end=end if end is not None else start+duration
    by_id={t['id']:t for t in doc['timelines']}
    for p,curve in clip['curves'].items():
        target=by_id[actor_id if p=='__root__' else actor_id+'_'+p]
        existing=copy.deepcopy(target['keyframes']);defaults=target.get('default_values',{})
        channels={field for values in curve.values() for field in values}
        all_fields=channels|set(defaults)|{field for values in existing.values() for field in values}
        times={int(f) for f in existing}
        offsets=range(start,end+1,duration) if repeat else [start]
        spans=[]
        for offset in offsets:
            stop=min(end,offset+duration);spans.append((offset,stop))
            times.update(offset+int(f) for f in curve if offset+int(f)<=stop)
            times.add(stop)
        materialized={}
        for at in sorted(times):
            values=_sample_curve(existing,at,all_fields,defaults)
            spans_at=[span for span in spans if span[0]<=at<=span[1]]
            if spans_at:
                offset,stop=spans_at[-1]
                pose=_sample_curve(curve,at-offset,channels,defaults)
                for field,value in pose.items():
                    if field.startswith('SCA_'):
                        values[field]=1+(value-1)*amplitude
                    else:
                        values[field]=(values[field] if p=='__root__' else 0)+value*amplitude
            materialized[str(at)]=values
        target['keyframes']=materialized
    return doc


def preview_project(directory: Path, output: Path, quality='preview'):
    if output.exists():raise FileExistsError('Preview project exists; choose a new job')
    doc=json.loads((ROOT/'templates/mineimator/base-2.0.2.miproject').read_text())
    width,height=(540,960) if quality=='preview' else (1080,1920)
    doc['project'].update(name='Permanent host — review v001',video_width=width,video_height=height,
                          tempo=30,view_main_camera='camera',view_second_camera=-4,render_settings='')
    doc['project']['timeline'].update(region_start=0,region_end=359,marker=0,zoom=2)
    doc['background'].update(sky_time=-35,ground_show=True,fog_show=False,wind=False)
    doc['render'].update(render_samples=1,render_ssao=False,render_indirect=False,render_reflections=False,
                         render_glow=False,texture_filtering=False,material_maps=False)
    doc['templates']=[];doc['timelines']=[];doc['resources']=[]
    add_character(doc,directory,output.parent,root_keys={0:{'POS_X':-3,'ROT_Z':155},75:{'POS_X':0,'ROT_Z':180},150:{'ROT_Z':205},195:{'ROT_Z':180},359:{'ROT_Z':180}})
    apply_clip(doc,directory,'host','walk',0,64,True)
    profile=json.loads((directory/'profile.json').read_text())
    if profile.get('appearance_policy',{}).get('glasses_always_on'):
        apply_clip(doc,directory,'host','look_left',100,130)
    else:
        apply_clip(doc,directory,'host','glasses_lift',100,145)
    apply_clip(doc,directory,'host','blink',120,128)
    apply_clip(doc,directory,'host','point',170,215)
    apply_clip(doc,directory,'host','hold',218,275)
    apply_clip(doc,directory,'host','surprise',280,325)
    camera={'id':'camera','name':'Portrait review camera','type':'camera','temp':'null','parent':'root',
            'parent_tree_index':-1,'default_values':{},'keyframes':{
                '0':{'POS_X':0,'POS_Y':-66,'POS_Z':23,'ROT_X':5,'CAM_FOV':37},
                '75':{'POS_X':0,'POS_Y':-66,'POS_Z':23,'ROT_X':5,'CAM_FOV':37},
                '150':{'POS_X':0,'POS_Y':-57,'POS_Z':25,'ROT_X':7,'CAM_FOV':37},
                '359':{'POS_X':0,'POS_Y':-62,'POS_Z':24,'ROT_X':6,'CAM_FOV':37}}}
    doc['timelines'].append(camera)
    write_new(output,doc)
    return output
