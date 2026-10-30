#!/usr/bin/env python3
"""Build one native Mine-imator 2.0.2 animation. Never calls another renderer.

Project format audited against the upstream project_load_* / project_save_* GML.
Output resources are original pixel art. Minecraft blocks/rig come from the
unmodified installed Mine-imator distribution and are not redistributed here.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / 'templates/mineimator/base-2.0.2.miproject'


def skin(path: Path, coat: str, hair: str) -> None:
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Standard Minecraft wide player UV, original artist-authored colors.
    d.rectangle((0, 0, 31, 15), fill='#B98058')
    d.rectangle((0, 0, 31, 7), fill=hair)
    d.rectangle((0, 8, 7, 10), fill=hair)
    d.rectangle((16, 8, 31, 10), fill=hair)
    d.rectangle((8, 8, 15, 9), fill=hair)
    d.rectangle((8, 10, 8, 12), fill=hair)
    d.rectangle((15, 10, 15, 11), fill=hair)
    d.rectangle((25, 10, 28, 11), fill=hair)
    d.rectangle((9, 11, 10, 12), fill='#F2F1DA')
    d.rectangle((13, 11, 14, 12), fill='#F2F1DA')
    d.point((10, 12), fill='#243842'); d.point((13, 12), fill='#243842')
    d.rectangle((11, 14, 12, 14), fill='#6C4039')
    d.rectangle((16, 16, 39, 31), fill=coat)
    d.rectangle((40, 16, 55, 31), fill=coat)
    d.rectangle((32, 48, 47, 63), fill=coat)
    d.rectangle((40, 27, 55, 31), fill='#B98058')
    d.rectangle((32, 59, 47, 63), fill='#B98058')
    d.rectangle((0, 16, 15, 31), fill='#31425E')
    d.rectangle((16, 48, 31, 63), fill='#31425E')
    d.rectangle((0, 29, 15, 31), fill='#293039')
    d.rectangle((16, 61, 31, 63), fill='#293039')
    d.rectangle((23, 20, 24, 31), fill='#D4AB4D')
    d.rectangle((20, 24, 21, 26), fill='#294D47')
    im.save(path)


def card(path: Path) -> None:
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((3, 0, 12, 15), fill='#D8AF45')
    d.rectangle((4, 1, 11, 14), fill='#EEE4B4')
    d.rectangle((5, 3, 10, 9), fill='#244C49')
    for box, color in [((7, 3, 8, 4), '#B5EB7B'), ((6, 5, 9, 7), '#64B753'), ((7, 8, 8, 8), '#317D43')]:
        d.rectangle(box, fill=color)
    d.rectangle((5, 11, 10, 11), fill='#716644'); d.rectangle((6, 13, 9, 13), fill='#9B8B58')
    im.save(path)


def validate_project(doc: dict) -> None:
    """Validate bridge invariants only; the Mine-imator loader is still required."""
    if doc.get('format') != 34:
        raise ValueError('This bridge supports Mine-imator format 34 only')
    objects = [obj for section in ('templates', 'timelines', 'resources') for obj in doc[section]]
    ids = [obj['id'] for obj in objects]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate native object IDs')
    ids = set(ids) | {'root', 'default', 'null'}
    tls = {t['id']: t for t in doc['timelines']}
    for temp in doc['templates']:
        for field in ('model', 'block'):
            if isinstance(temp.get(field), dict) and 'state' in temp[field]:
                if not isinstance(temp[field]['state'], dict):
                    raise ValueError('Native model/block state must be a JSON object')
    for t in doc['timelines']:
        for field in ('temp', 'parent', 'part_of'):
            if field in t and t[field] not in ids:
                raise ValueError(f"Dangling {field}: {t['id']}")
        for frame in t['keyframes']:
            if int(frame) < 0 or str(int(frame)) != frame:
                raise ValueError('Keyframe must have a nonnegative integer frame number')
        seen = {t['id']}
        parent = t['parent']
        while parent != 'root':
            if parent not in tls:
                raise ValueError(f'Parent is not a timeline: {parent}')
            if parent in seen:
                raise ValueError('Cycle in native timeline hierarchy')
            seen.add(parent)
            parent = tls[parent]['parent']


def build(base: Path, output: Path, quality: str = 'final') -> dict:
    if output.exists():
        raise FileExistsError(f'Existing project preserved: {output}; choose a new --output job directory')
    assets = output.parent / 'assets'
    if assets.exists():
        raise FileExistsError(f'Existing assets preserved: {assets}; choose a new --output job directory')
    if quality not in ('preview', 'final'):
        raise ValueError('quality must be preview or final')
    width, height = (540, 960) if quality == 'preview' else (1080, 1920)
    doc = json.loads(base.read_text())
    doc['templates'] = []; doc['timelines'] = []; doc['resources'] = []
    doc['project'].update(name='MineStory-native-20s', author='MineStory',
        description='Teste técnico: caminhada, descoberta, carta original, reação e troca. Áudio de teste não é narração do usuário.',
        video_width=width, video_height=height, tempo=30, render_settings='',
        view_main_camera=-5, view_second_camera=-4)
    doc['project']['timeline'].update(marker=0, region_start=0, region_end=599, zoom=1)
    doc['project']['work_camera'].update(focus=[0, 18, 0], angle_xy=270, angle_z=8, zoom=100)
    doc['render'].update(render_samples=1, render_ssao=False, render_shadows=True,
        render_indirect=False, render_reflections=False, render_glow=False, render_aa=True,
        texture_filtering=False, transparent_block_texture_filtering=False, material_maps=False)
    doc['background'].update(ground_show=True, fog_show=False, sky_time=-45,
        wind=False, sunlight_strength=1, sunlight_color='#FFFFFF', ambient_color='#9DA6B2')
    assets.mkdir(parents=True, exist_ok=False)
    skin(assets/'lia.png', '#317C70', '#493525'); skin(assets/'rui.png', '#9A5A3B', '#28252C'); card(assets/'carta.png')
    doc['resources'] = [
        {'id':'skin_lia','type':'skin','filename':'assets/lia.png','player_skin':True},
        {'id':'skin_rui','type':'skin','filename':'assets/rui.png','player_skin':True},
        {'id':'card_tex','type':'texture','filename':'assets/carta.png'},
    ]
    def template(tid, typ, **kw):
        t={'id':tid,'type':typ,'name':tid,**kw}; doc['templates'].append(t); return tid
    def timeline(tid, typ, temp=None, parent='root', keys=None, **kw):
        t={'id':tid,'type':typ,'name':tid,'temp':temp or 'null','parent':parent,
           'parent_tree_index':-1,'default_values':{},'keyframes':{str(k):v for k,v in (keys or {0:{}}).items()},
           'glint_tex':'default','texture_blur':False,'texture_filtering':False,**kw}
        doc['timelines'].append(t); return t
    def pos(x=0,y=0,z=0,**kw): return {'POS_X':x,'POS_Y':y,'POS_Z':z,**kw}
    # Keyframe positions are Mine-imator internal XYZ: Z is vertical. Resource vectors use Minecraft XYZ.
    def actor(a, tex, x, y, keys):
        temp=template(a+'_rig','char',model_tex=tex,model_tex_material='default',model_tex_normal='default',
                      model={'name':'human','state':{'type':'wide','variant':'steve'},'model_version':1})
        parts=['body','head','hat','right_arm','left_arm','right_leg','left_leg']
        root=timeline(a,'char',temp,keys=keys,parts=[a+'_'+p for p in parts])
        parents={'body':a,'head':a+'_body','hat':a+'_head','right_arm':a+'_body','left_arm':a+'_body','right_leg':a,'left_leg':a}
        for p in parts:
            timeline(a+'_'+p,'bodypart',temp,parents[p],part_of=a,model_part_name=p,
                     inherit={'alpha':True,'color':True,'texture':True,'surface':True,'subsurface':True,'rot_point':True},
                     keys={0:{},599:{}})
        return root
    actor('lia','skin_lia',-26,0,{0:pos(-26,0,0,ROT_Z=-70),120:pos(-4,0,0,ROT_Z=-70),
        150:pos(-4,0,0,ROT_Z=0),210:pos(-4,0,0,ROT_Z=0),255:pos(-4,0,0,ROT_Z=0),
        300:pos(-4,0,0,ROT_Z=0),330:pos(-4,0,3,ROT_Z=0),345:pos(-4,0,0,ROT_Z=0),
        405:pos(-4,0,0,ROT_Z=35),465:pos(-4,0,0,ROT_Z=15),599:pos(-4,0,0,ROT_Z=0)})
    actor('rui','skin_rui',24,12,{0:pos(32,18,0,ROT_Z=70),277:pos(32,18,0,ROT_Z=70),
        323:pos(18,3,0,ROT_Z=70),420:pos(18,3,0,ROT_Z=50),599:pos(18,3,0,ROT_Z=25)})
    def get(t): return next(a for a in doc['timelines'] if a['id']==t)
    # Actual native articulated walk cycles, ending at planted feet.
    for a,start,end in [('lia',0,120),('rui',277,323)]:
        for part,sign in [('right_leg',1),('left_leg',-1),('right_arm',-1),('left_arm',1)]:
            k={0:{'ROT_X':0}}
            for f in range(start,end+1,8): k[f]={'ROT_X':sign*(27 if ((f-start)//8)%2 else -27)}
            k[end]={'ROT_X':0}; k[599]={'ROT_X':0}
            get(a+'_'+part)['keyframes']={str(f):v for f,v in sorted(k.items())}
    # Discover, bend down, lift the card, surprised recoil, offer it toward collector.
    get('lia_body')['keyframes']={str(k):v for k,v in {0:{},150:{},180:{'ROT_X':-32},210:{'ROT_X':-32},240:{'ROT_X':0},300:{},330:{'ROT_X':9},345:{},420:{'ROT_Z':-10},465:{},599:{}}.items()}
    get('lia_right_arm')['keyframes'].update({str(k):v for k,v in {150:{},180:{'ROT_X':35},210:{'ROT_X':35},240:{'ROT_X':75},300:{'ROT_X':75},330:{'ROT_X':105,'ROT_Y':-15},345:{'ROT_X':80},420:{'ROT_X':75,'ROT_Z':-35},465:{'ROT_X':75},599:{'ROT_X':75}}.items()})
    get('lia_head')['keyframes']={str(k):v for k,v in {0:{'ROT_Z':-12},120:{},150:{'ROT_X':-25},210:{'ROT_X':-25},240:{'ROT_X':-10},300:{'ROT_X':-10},330:{'ROT_X':12},345:{},405:{'ROT_Z':-25},465:{'ROT_Z':0},540:{'ROT_Z':8},599:{}}.items()}
    get('lia_left_arm')['keyframes'].update({str(k):v for k,v in {300:{},330:{'ROT_X':-25,'ROT_Y':-25},345:{'ROT_X':-15,'ROT_Y':-15},405:{},465:{'ROT_X':40},510:{'ROT_X':40},599:{}}.items()})
    get('rui_right_arm')['keyframes'].update({str(k):v for k,v in {420:{'ROT_X':65},465:{'ROT_X':65},510:{'ROT_X':85},555:{'ROT_X':65},599:{'ROT_X':65}}.items()})
    get('rui_head')['keyframes']={str(k):v for k,v in {0:{},323:{'ROT_X':-20},420:{'ROT_X':-10},450:{'ROT_X':0},465:{'ROT_X':-12},480:{'ROT_X':0},540:{'ROT_Z':15},599:{}}.items()}
    cardtemp=template('card_original','item',item={'tex':'card_tex','tex_material':'default','tex_normal':'default','slot':0,'3d':True,'face_camera':False,'bounce':False,'spin':False})
    # Native item geometry is extruded pixel art. Two instances switch visibility at pickup.
    timeline('carta_no_chao','item',cardtemp,keys={0:pos(7,-11,0.2,ROT_X=90,SCA_X=.7,SCA_Y=.7,SCA_Z=.7),209:pos(7,-11,.2,ROT_X=90,SCA_X=.7,SCA_Y=.7,SCA_Z=.7),210:{'VISIBLE':False},599:{'VISIBLE':False}})
    timeline('carta_na_mao','item',cardtemp,'lia_right_arm',keys={0:{'VISIBLE':False},209:{'VISIBLE':False},210:pos(-5,3,-11,ROT_X=65,SCA_X=.7,SCA_Y=.7,SCA_Z=.7,VISIBLE=True),599:pos(-5,3,-11,ROT_X=65,SCA_X=.7,SCA_Y=.7,SCA_Z=.7,VISIBLE=True)})
    emerald=template('emerald_vanilla','item',item={'tex':'default','tex_material':'default','tex_normal':'default','name':'item/emerald','3d':True,'face_camera':False,'bounce':False,'spin':False})
    timeline('emerald_offer','item',emerald,'rui_right_arm',keys={0:pos(-5,3,-10,SCA_X=.65,SCA_Y=.65,SCA_Z=.65),599:pos(-5,3,-10,SCA_X=.65,SCA_Y=.65,SCA_Z=.65)})
    # Procedurally assemble authentic native block models: market stall and oak trees.
    blocktypes=['oak_log','oak_leaves','oak_planks','cobblestone','red_wool','white_wool','grass_block','poppy']
    # Mine-imator groups block variants in its .midata (different from Minecraft IDs).
    native_blocks = {
        'oak_log': ('log', 'variant=oak,axis=y'),
        'oak_leaves': ('leaves', 'variant=oak'),
        'oak_planks': ('planks', 'variant=oak'),
        'red_wool': ('wool', 'color=red'),
        'white_wool': ('wool', 'color=white'),
        'grass_block': ('grass_block', 'snowy=false'),
        'poppy': ('flower', 'type=poppy'),
        'cobblestone': ('cobblestone', ''),
    }
    for b in blocktypes:
        name, state_text = native_blocks[b]
        state = dict(pair.split('=', 1) for pair in state_text.split(',') if pair)
        template('block_'+b,'block',block={'name':name,'state':state,'tex':'default','tex_material':'default','tex_normal':'default'})
    idx=0
    def block(b,x,y,z,**kw):
        nonlocal idx
        idx+=1; timeline('b%03d_%s'%(idx,b),'block','block_'+b,keys={0:pos(x,y,z,**kw)})
    for x in (-48,32):
        for z in (0,16,32): block('oak_log',x,48,z)
        for xx,yy,zz in [(x-16,48,32),(x+16,48,32),(x,32,32),(x,64,32),(x,48,48),(x-16,48,48),(x+16,48,48)]: block('oak_leaves',xx,yy,zz)
    for x in (-32,-16,0,16):
        block('oak_planks',x,70,0)
        block('white_wool' if x in(-32,0) else 'red_wool',x,70,48)
    for x in(-32,16):
        block('oak_log',x,70,16);block('oak_log',x,70,32)
    for x,y in [(-48,12),(38,16),(-28,34),(42,-18),(-42,-22)]:block('poppy',x,y,0)
    # All cameras point along local +Y with Z up. Slow motion preserves Minecraft's direct framing.
    timeline('camera','camera',keys={
        0:pos(-12,-108,42,ROT_X=14,CAM_FOV=47),
        120:pos(-5,-96,37,ROT_X=13,CAM_FOV=47),
        210:pos(-4,-90,33,ROT_X=12,CAM_FOV=47),
        277:pos(-4,-80,33,ROT_X=12,CAM_FOV=47),
        323:pos(6,-100,38,ROT_X=13,CAM_FOV=47),
        465:pos(7,-95,37,ROT_X=13,CAM_FOV=47),
        599:pos(5,-90,35,ROT_X=12,CAM_FOV=47)})
    # The bundled human's face is +Y, while this camera is on -Y. Turn roots
    # toward the camera; negative limb pitch reaches in the human's +Y front.
    for t in doc['timelines']:
        if t['id'] in ('lia', 'rui'):
            for value in t['keyframes'].values():
                if 'ROT_Z' in value:
                    value['ROT_Z'] += 180
        elif t['type'] == 'bodypart':
            for value in t['keyframes'].values():
                if 'ROT_X' in value:
                    value['ROT_X'] *= -1

    output.parent.mkdir(parents=True,exist_ok=True)
    validate_project(doc)
    with output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    return {'project':str(output),'quality':quality,'resolution':[width,height],'seconds':20,'fps':30,'frames':600,'native_validation':'pending GUI open/export','timelines':len(doc['timelines']),'templates':len(doc['templates'])}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=DEFAULT_BASE)
    p.add_argument('--output',type=Path,default=ROOT/'productions/mineimator-validation/test.miproject')
    p.add_argument('--quality', choices=('preview', 'final'), default='final')
    args=p.parse_args(); print(json.dumps(build(args.base,args.output,args.quality),ensure_ascii=False,indent=2))
