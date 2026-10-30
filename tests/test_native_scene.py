"""Guard actual native authoring failure modes; GUI renders remain necessary."""
import json
from pathlib import Path
import pytest
import wave
from minestory.native_scene import NativeProject,model_box,model_part,pose


def test_custom_model_uses_own_texture_and_flat_native_part_registry(tmp_path):
    p=NativeProject(tmp_path,duration=3,name='integration fixture')
    p.cuboid_model('object',[model_part('parent',children=[
        model_part('child',shapes=[model_box((0,0,0),(1,1,1))])])])
    doc=json.loads(p.save().read_text())
    template=doc['templates'][0]
    assert template['model_tex']==template['model_tex_material']==template['model_tex_normal']=='null'
    root=next(t for t in doc['timelines'] if t['id']=='object')
    assert root['parts']==['object_parent','object_child']
    child=next(t for t in doc['timelines'] if t['id']=='object_child')
    assert child['parent']=='object_parent' and 'parts' not in child


def test_visibility_handoffs_do_not_reset_staged_object_position(tmp_path):
    p=NativeProject(tmp_path,duration=3,name='visibility fixture')
    p.timeline('actor','folder',keys={0:pose(10,20,3),30:{'VISIBLE':False},60:{'VISIBLE':True}})
    keys=json.loads(p.save().read_text())['timelines'][0]['keyframes']
    assert keys['60']['POS_X']==10 and keys['60']['POS_Y']==20 and keys['60']['POS_Z']==3


def test_new_animation_channel_samples_existing_travel_curve(tmp_path):
    p=NativeProject(tmp_path,duration=4,name='travel composition fixture')
    p.timeline('actor','folder',keys={0:{'POS_X':0},60:{'POS_Z':5},120-1:{'POS_X':10}})
    keys=json.loads(p.save().read_text())['timelines'][0]['keyframes']
    assert keys['60']['POS_X']==pytest.approx(10*60/119)


def test_scenes_are_hidden_outside_their_real_narration_interval(tmp_path):
    p=NativeProject(tmp_path,duration=3,name='scene fixture')
    p.scene('scene',1,2,origin=(1000,0,0))
    keys=json.loads(p.save().read_text())['timelines'][0]['keyframes']
    assert keys['0']['VISIBLE'] is False
    assert keys['30']['VISIBLE'] is True
    assert keys['60']['VISIBLE'] is False


def test_model_cannot_overwrite_an_existing_asset_directory(tmp_path):
    p=NativeProject(tmp_path,duration=3,name='preservation fixture')
    folder=tmp_path/'assets'/'object';folder.mkdir(parents=True)
    texture=folder/'atlas.png';texture.write_bytes(b'original')
    with pytest.raises(FileExistsError):p.cuboid_model('object',[model_part('root')])
    assert texture.read_bytes()==b'original'


def test_project_cannot_overwrite_a_previous_production(tmp_path):
    target=tmp_path/'story.miproject';target.write_text('original')
    p=NativeProject(tmp_path,duration=3,name='preservation fixture')
    with pytest.raises(FileExistsError):p.save()
    assert target.read_text()=='original'


def test_parent_cycles_and_out_of_range_events_are_rejected(tmp_path):
    p=NativeProject(tmp_path,duration=3,name='hierarchy fixture')
    p.timeline('a','folder',parent='b');p.timeline('b','folder',parent='a')
    with pytest.raises(ValueError,match='cycle'):p.save()
    p.find('a')['parent']='root';p.find('b')['keyframes']['999']={}
    with pytest.raises(ValueError,match='outside'):p.save()


def test_clip_neutral_key_releases_expression_without_teleporting_root(tmp_path):
    library=tmp_path/'library';library.mkdir()
    (library/'animations.json').write_text(json.dumps({'clips':{'gesture':{
        'frames':10,'curves':{'head':{'0':{'ROT_X':25},'10':{}}}}}}))
    p=NativeProject(tmp_path/'job',duration=3,name='animation fixture')
    p.timeline('host','folder',keys={0:pose(20,30,0)})
    p.timeline('host_head','folder',parent='host')
    p.clip(library,'host','gesture',0)
    doc=json.loads(p.save().read_text())
    assert next(t for t in doc['timelines'] if t['id']=='host_head')['keyframes']['10']['ROT_X']==0
    assert next(t for t in doc['timelines'] if t['id']=='host')['keyframes']['0']['POS_X']==20


@pytest.mark.parametrize('start,end',[((0,0,0),(0,1,1)),((2,0,0),(1,1,1))])
def test_invalid_custom_geometry_is_rejected(start,end):
    with pytest.raises(ValueError):model_box(start,end)


def test_native_full_audio_end_is_zero_offset_not_double_duration(tmp_path):
    source=tmp_path/'voice.wav'
    with wave.open(str(source),'wb') as handle:
        handle.setnchannels(1);handle.setsampwidth(2);handle.setframerate(8000)
        handle.writeframes(b'\0\0'*24000)
    p=NativeProject(tmp_path/'job',duration=3,name='full sound fixture')
    p.audio(source,'voice',end=3)
    values=p.find('voice')['keyframes']['0']
    assert values['SOUND_END']==0
    assert (3+values['SOUND_END']-values['SOUND_START'])*30==90
    assert (p.job/'assets/audio/voice.wav').read_bytes()==source.read_bytes()


def test_native_audio_trim_uses_negative_end_offset(tmp_path):
    source=tmp_path/'voice.wav'
    with wave.open(str(source),'wb') as handle:
        handle.setnchannels(1);handle.setsampwidth(2);handle.setframerate(8000)
        handle.writeframes(b'\0\0'*24000)
    p=NativeProject(tmp_path/'job',duration=3,name='trim sound fixture')
    p.audio(source,'voice',end=2)
    values=p.find('voice')['keyframes']['0']
    assert values['SOUND_END']==-1
    assert (3+values['SOUND_END']-values['SOUND_START'])*30==60
