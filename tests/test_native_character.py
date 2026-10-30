"""Permanent avatar schema, composition and preservation contracts."""
import json
from pathlib import Path
import pytest
from minestory.native_character import (model_from_profile, validate_model, build_character,
                                        preview_project, add_character, flatten_parts, animation_library)

@pytest.fixture
def profile():
    return {'id':'test_host','version':'v001','palette':{'skin':'#BF8B70','hair':'#17202A',
        'sweatshirt':'#263044','trousers':'#293345'}}


def test_custom_avatar_has_articulated_geometry_beyond_flat_skin(profile):
    model=model_from_profile(profile)
    stats=validate_model(model)
    parts={p['name']:p for p,_ in flatten_parts(model)}
    assert stats['parts']>=20 and stats['shapes']>=70
    assert len(parts['hair']['shapes'])>=10
    assert len(parts['glasses']['shapes'])>=15
    assert {'mouth','lid_left','lid_right','brow_left','brow_right','right_forearm','left_forearm','right_grip'}<=parts.keys()


def test_permanent_character_refuses_overwrite(profile,tmp_path):
    version=tmp_path/'v001'
    build_character(profile,version)
    original=(version/'host.mimodel').read_bytes()
    with pytest.raises(FileExistsError):build_character(profile,version)
    assert (version/'host.mimodel').read_bytes()==original


def test_avatar_job_copies_resolve_model_texture_and_references(profile,tmp_path):
    version=build_character(profile,tmp_path/'library/v001')
    job=tmp_path/'job';project=job/'character.miproject'
    preview_project(version,project)
    doc=json.loads(project.read_text())
    resource=doc['resources'][0]
    assert doc['templates'][0]['model_tex']=='null'  # custom .mimodel uses its OWN atlas
    bodyparts=[t for t in doc['timelines'] if t['type']=='bodypart']
    root=next(t for t in doc['timelines'] if t['id']=='host')
    assert set(root['parts'])=={t['id'] for t in bodyparts}
    assert all('parts' not in t for t in bodyparts)  # native model root owns a flat registry
    model=json.loads((job/resource['filename']).read_text())
    assert (job/model['texture']).is_file()
    ids={t['id'] for t in doc['timelines']}
    for t in doc['timelines']:
        assert t['parent']=='root' or t['parent'] in ids
        for p in t.get('parts',[]):assert p in ids
    assert doc['project']['video_width']==540 and doc['project']['timeline']['region_end']==359
    assert json.loads((version/'manifest.json').read_text())['status']=='awaiting_user_review'


def test_composed_actor_assets_cannot_overwrite_previous_job(profile,tmp_path):
    version=build_character(profile,tmp_path/'library/v001')
    doc={'timelines':[],'templates':[],'resources':[]};job=tmp_path/'job'
    add_character(doc,version,job)
    model=(job/'assets/host/host.mimodel').read_bytes()
    with pytest.raises(FileExistsError):add_character(doc,version,job)
    assert (job/'assets/host/host.mimodel').read_bytes()==model


def test_animation_library_targets_existing_native_parts(profile):
    names={p['name'] for p,_ in flatten_parts(model_from_profile(profile))}|{'__root__'}
    clips=animation_library()['clips']
    assert {'walk','run','jump','hold','give','receive','point','surprise','fear','joy','sit','fall','blink','glasses_lift'}<=clips.keys()
    for clip in clips.values():
        assert clip['fps']==30
        for target,curve in clip['curves'].items():
            assert target in names
            assert all(0<=int(frame)<=clip['frames'] for frame in curve)


def test_jump_preserves_existing_root_trajectory_and_facing(profile,tmp_path):
    from minestory.native_character import apply_clip
    version=build_character(profile,tmp_path/'library/v001')
    doc={'templates':[],'resources':[],'timelines':[]}
    add_character(doc,version,tmp_path/'job',root_keys={0:{'POS_X':10,'POS_Y':12,'POS_Z':16,'ROT_Z':180},90:{'POS_X':100,'POS_Y':12,'POS_Z':16,'ROT_Z':180}})
    apply_clip(doc,version,'host','jump',30,60)
    root=next(t for t in doc['timelines'] if t['id']=='host')
    # Jump peak localframe14 at44: existing world pathX54 and floorZ16+height6.
    pose=root['keyframes']['44']
    assert pose['POS_X']==54 and pose['POS_Y']==12
    assert pose['ROT_Z']==180 and pose['POS_Z']==22


def test_fixed_glasses_profile_excludes_lift_but_generic_library_keeps_it(profile):
    assert 'glasses_lift' in animation_library()['clips']
    profile['appearance_policy']={'glasses_always_on':True}
    assert 'glasses_lift' not in animation_library(profile)['clips']


def test_fixed_glasses_preview_keeps_eyewear_attached_and_visible(profile,tmp_path):
    profile['appearance_policy']={'glasses_always_on':True,'automatic_glasses_lift':False}
    version=build_character(profile,tmp_path/'library/v001')
    project=tmp_path/'review/character.miproject'
    preview_project(version,project)
    doc=json.loads(project.read_text())
    eyewear=next(t for t in doc['timelines'] if t['id']=='host_glasses')
    assert eyewear['parent']=='host_head'
    assert eyewear['keyframes']=={'0':{}}
    assert json.loads((version/'manifest.json').read_text())['appearance_policy']['glasses_always_on'] is True


def test_fixed_glasses_policy_blocks_lift_and_renamed_removal_clip(profile,tmp_path):
    from minestory.native_character import apply_clip
    profile['appearance_policy']={'glasses_always_on':True}
    version=build_character(profile,tmp_path/'library/v001')
    doc={'templates':[],'resources':[],'timelines':[]}
    add_character(doc,version,tmp_path/'job')
    with pytest.raises(ValueError,match='always on'):
        apply_clip(doc,version,'host','glasses_lift',0)
    # Reject the same prohibited change even if a future clip has another name.
    animations=json.loads((version/'animations.json').read_text())
    animations['clips']['bad_removal']={'frames':10,'curves':{'glasses':{'0':{'VISIBLE':False}}}}
    (version/'animations.json').write_text(json.dumps(animations))
    before=json.dumps(doc,sort_keys=True)
    with pytest.raises(ValueError,match='always on'):
        apply_clip(doc,version,'host','bad_removal',0)
    assert json.dumps(doc,sort_keys=True)==before
