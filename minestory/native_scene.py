"""Small native Mine-imator authoring API; no renderer or subject template.

Project transforms use XYZ with Z up. MIMODEL geometry uses Minecraft XYZ
with Y up. Resources and user likeness remain in a private production folder.
The official application's actual load/render remains the integration test.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def pose(x=0, y=0, z=0, **fields):
    return {'POS_X': x, 'POS_Y': y, 'POS_Z': z, **fields}


def model_box(start, end, color='#FFFFFF', **fields):
    """Native cuboid, colored over an original white pixel atlas."""
    if any(not math.isfinite(float(v)) for v in (*start, *end)):
        raise ValueError('Model coordinates must be finite')
    if len(start) != 3 or len(end) != 3 or any(a >= b for a,b in zip(start,end)):
        raise ValueError('Cuboid bounds must be increasing XYZ triples')
    return {'type':'block', 'from':list(start), 'to':list(end), 'uv':[96,96],
            'color_blend':color, **fields}


def model_part(name, position=(0,0,0), shapes=None, children=None):
    return {'name':name, 'position':list(position), 'shapes':shapes or [], 'parts':children or []}


def flatten_model(model):
    result=[]
    def walk(parts, parent=None):
        for part in parts:
            result.append((part,parent)); walk(part.get('parts',[]),part['name'])
    walk(model['parts']); return result


BLOCKS = {
    'oak_log':('log',{'variant':'oak','axis':'y'}),
    'acacia_log':('log',{'variant':'acacia','axis':'y'}),
    'oak_leaves':('leaves',{'variant':'oak'}),
    'acacia_leaves':('leaves',{'variant':'acacia'}),
    'oak_planks':('planks',{'variant':'oak'}),
    'grass_block':('grass_block',{'snowy':'false'}),
    'poppy':('flower',{'type':'poppy'}),
    'sand':('sand',{'variant':'sand'}),
    **{name:(name,{}) for name in ('cobblestone','stone','dirt','obsidian','glass','bookshelf','crafting_table','glowstone','netherrack')},
    **{color+'_wool':('wool',{'color':color}) for color in ('white','red','blue','yellow','black','purple','cyan','green','lime')},
}


class NativeProject:
    def __init__(self, job: Path, *, duration: float, name: str, quality='preview', fps=30):
        if duration <= 0 or not math.isfinite(duration) or fps != 30:
            raise ValueError('Positive finite duration and tested30FPS are required')
        self.job=Path(job).resolve(); self.duration=duration; self.fps=fps
        self.frames=math.ceil(duration*fps); self.last=self.frames-1
        self.doc=json.loads((ROOT/'templates/mineimator/base-2.0.2.miproject').read_text())
        width,height=(540,960) if quality=='preview' else (1080,1920)
        if quality not in ('preview','final'):raise ValueError('Invalid quality')
        self.doc['project'].update(name=name, author='MineStory',video_width=width,
            video_height=height,tempo=fps,view_main_camera='camera',view_second_camera=-4,render_settings='')
        self.doc['project']['timeline'].update(marker=0,region_start=0,region_end=self.last,zoom=.5)
        self.doc['render'].update(render_samples=1,render_ssao=False,render_indirect=False,
            render_reflections=False,render_glow=False,render_shadows=True,
            texture_filtering=False,transparent_block_texture_filtering=False,material_maps=False)
        self.doc['background'].update(ground_show=True,fog_show=False,wind=False,
            sky_time=-40,sunlight_strength=1,sunlight_color='#FFFFFF',ambient_color='#8E9BAD')
        for section in ('timelines','templates','resources'):self.doc[section]=[]
        self._counter=0

    def frame(self, seconds):
        return max(0,min(self.last,round(float(seconds)*self.fps)))

    def find(self, tid):
        return next(t for t in self.doc['timelines'] if t['id']==tid)

    def template(self, tid, typ, **fields):
        self.doc['templates'].append({'id':tid,'name':tid,'type':typ,**fields}); return tid

    def timeline(self, tid, typ, template='null', parent='root', keys=None, **fields):
        timeline={'id':tid,'name':tid,'type':typ,'temp':template,'parent':parent,
            'parent_tree_index':-1,'default_values':{},'texture_filtering':False,
            'texture_blur':False,'inherit':{'visibility':True},
            'keyframes':{str(f):copy.deepcopy(v) for f,v in (keys or {0:{}}).items()},**fields}
        self.doc['timelines'].append(timeline); return tid

    def key(self, tid, seconds, **values):
        self.find(tid)['keyframes'].setdefault(str(self.frame(seconds)),{}).update(values)

    def scene(self, sid, start, end, *, origin=(0,0,0)):
        if not 0<=start<end<=self.duration+.001:raise ValueError('Scene lies outside narration')
        first=self.frame(start);last=self.frame(end)
        keys={0:{'VISIBLE':False,**pose(*origin)}}
        keys[first]={'VISIBLE':True,**pose(*origin)}
        if end<self.duration:keys[last]={'VISIBLE':False,**pose(*origin)}
        return self.timeline(sid,'folder',keys=keys)

    def block(self, block, x,y,z, *, parent='root', scale=(1,1,1), tid=None):
        if block not in BLOCKS:raise ValueError(f'Unaudited native block: {block}')
        template='block_'+block
        if not any(t['id']==template for t in self.doc['templates']):
            name,state=BLOCKS[block]
            self.template(template,'block',block={'name':name,'state':state,'tex':'default',
                'tex_material':'default','tex_normal':'default'})
        self._counter+=1; tid=tid or f'block_{self._counter}'
        return self.timeline(tid,'block',template,parent,keys={0:pose(x,y,z,
            SCA_X=scale[0],SCA_Y=scale[1],SCA_Z=scale[2])})

    def cuboid_model(self, tid, parts, *, parent='root', keys=None):
        """Write a new production-local custom model, plus articulated timelines."""
        directory=self.job/'assets'/tid
        directory.mkdir(parents=True,exist_ok=False)
        texture=directory/'atlas.png'
        im=Image.new('RGBA',(256,256),'white'); pixels=im.load()
        for yy in range(256):
            for xx in range(256):
                n=255-((xx*13+yy*29)%5)
                pixels[xx,yy]=(n,n,n,255)
        im.save(texture)
        model={'name':tid,'texture':texture.relative_to(self.job).as_posix(),
               'texture_size':[256,256],'parts':parts}
        names=[p['name'] for p,_ in flatten_model(model)]
        if len(names)!=len(set(names)):raise ValueError('Custom model has duplicate part names')
        file=directory/(tid+'.mimodel'); write_new_json(file,model)
        rid=tid+'_model_res';temp=tid+'_rig'
        self.doc['resources'].append({'id':rid,'type':'model','filename':file.relative_to(self.job).as_posix()})
        self.template(temp,'model',model=rid,model_tex='null',model_tex_material='null',model_tex_normal='null')
        self.timeline(tid,'model',temp,parent,keys=keys,parts=[tid+'_'+p['name'] for p,_ in flatten_model(model)])
        for p,p_parent in flatten_model(model):
            self.timeline(tid+'_'+p['name'],'bodypart',temp,tid+'_'+p_parent if p_parent else tid,
                part_of=tid,model_part_name=p['name'])
        return tid

    def character(self, directory: Path, tid, *, parent='root', keys=None):
        from .native_character import add_character
        add_character(self.doc,Path(directory),self.job,actor_id=tid,root_keys=keys)
        self.find(tid)['parent']=parent
        for timeline in self.doc['timelines']:
            if timeline['id']==tid or timeline.get('part_of')==tid:
                timeline.setdefault('inherit',{})['visibility']=True
                # Character-review duration must not constrain a production actor.
                if timeline['id']!=tid:timeline['keyframes'].pop('359',None)
        return tid

    def clip(self, directory, actor, name, start, end=None, repeat=False, amplitude=1):
        from .native_character import apply_clip
        library=json.loads((Path(directory)/'animations.json').read_text())
        first=self.frame(start)
        final=self.frame(end) if end is not None else min(self.last,first+library['clips'][name]['frames'])
        apply_clip(self.doc,Path(directory),actor,name,first,final,
                   repeat=repeat,amplitude=amplitude)

    def camera(self, keys):
        return self.timeline('camera','camera',keys=keys)

    def audio(self, source:Path, tid, *, at=0, end=None, volume=1):
        source=Path(source).resolve(strict=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0',
            '-show_entries','stream=duration,duration_ts,time_base','-of','json',str(source)],text=True))
        stream=probe['streams'][0]
        source_duration=(float(Fraction(stream['duration_ts'])*Fraction(stream['time_base']))
            if stream.get('duration_ts') is not None and stream.get('time_base') else float(stream['duration']))
        if end is not None and (not math.isfinite(end) or not 0<end<=source_duration+.0001):
            raise ValueError('Audio trim endpoint must remain inside its unaltered source')
        # Mine-imator SOUND_END is an OFFSET from the source end, not an
        # absolute endpoint. Zero means the complete source, not source+source.
        end_offset=float(end)-source_duration if end is not None else 0
        if abs(end_offset)<.0001:end_offset=0
        folder=self.job/'assets'/'audio';folder.mkdir(parents=True,exist_ok=True)
        dest=folder/(tid+source.suffix)
        if dest.exists():raise FileExistsError('Audio resource already exists')
        shutil.copy2(source,dest)
        rid=tid+'_sound_res'
        self.doc['resources'].append({'id':rid,'type':'sound','filename':dest.relative_to(self.job).as_posix()})
        return self.timeline(tid,'audio',keys={self.frame(at):{'SOUND_OBJ':rid,
            'SOUND_VOLUME':volume,'SOUND_PITCH':1,'SOUND_START':0,'SOUND_END':end_offset}})

    def validate(self):
        objects=[o for section in ('templates','timelines','resources') for o in self.doc[section]]
        ids=[o['id'] for o in objects]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate native ID')
        allowed=set(ids)|{'root','default','null'}
        timelines={t['id']:t for t in self.doc['timelines']}
        for t in self.doc['timelines']:
            for field in ('parent','temp','part_of'):
                if t.get(field,'null') not in allowed:raise ValueError(f'Dangling {field} in {t["id"]}')
            seen={t['id']};parent=t['parent']
            while parent!='root':
                if parent not in timelines:raise ValueError('Parent is not a timeline')
                if parent in seen:raise ValueError('Timeline cycle')
                seen.add(parent);parent=timelines[parent]['parent']
            for frame in t['keyframes']:
                if not str(frame).isdigit() or int(frame)>self.last:raise ValueError('Frame outside narration')
        for r in self.doc['resources']:
            if not (self.job/r['filename']).is_file():raise ValueError('Missing production resource')
        json.dumps(self.doc,allow_nan=False)

    def save(self, name='story.miproject'):
        # Native keyframes reset omitted channels to defaults. Sample each
        # independently authored channel at the union of event times: adding a
        # jump/expression must not freeze an unrelated travel/rotation curve.
        for t in self.doc['timelines']:
            keys=sorted(((int(frame),value) for frame,value in t['keyframes'].items()))
            fields={field for _,value in keys for field in value};expanded={}
            for frame,_ in keys:
                value={}
                for field in fields:
                    curve=[(f,v[field]) for f,v in keys if field in v]
                    before=[point for point in curve if point[0]<=frame]
                    left=before[-1] if before else curve[0]
                    after=[point for point in curve if point[0]>=frame]
                    right=after[0] if after else curve[-1]
                    result=left[1]
                    if (right[0]>left[0] and not isinstance(result,bool)
                        and isinstance(result,(int,float)) and isinstance(right[1],(int,float))):
                        factor=(frame-left[0])/(right[0]-left[0])
                        result=left[1]+factor*(right[1]-left[1])
                    value[field]=copy.deepcopy(result)
                expanded[str(frame)]=value
            t['keyframes']=expanded
        self.validate();target=self.job/name;write_new_json(target,self.doc)
        return target
