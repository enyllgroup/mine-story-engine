"""Bridge validation, independent from the mandatory real native GUI export test."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('mineimator_project', ROOT/'scripts/create_mineimator_test_project.py')
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)

@pytest.fixture
def project(tmp_path):
    target = tmp_path/'test.miproject'
    BRIDGE.build(BRIDGE.DEFAULT_BASE, target)
    return json.loads(target.read_text())

def test_project_uses_native_group_names_and_state_maps(project):
    templates = {t['id']: t for t in project['templates']}
    assert templates['block_oak_log']['block']['name'] == 'log'
    assert templates['block_oak_log']['block']['state'] == {'variant':'oak','axis':'y'}
    assert templates['block_red_wool']['block']['state'] == {'color':'red'}
    assert templates['lia_rig']['model']['state'] == {'type':'wide','variant':'steve'}

def test_hierarchy_rejects_cycle(project):
    project['timelines'][0]['parent'] = 'lia_head'
    with pytest.raises(ValueError, match='Cycle'):
        BRIDGE.validate_project(project)

def test_hierarchy_rejects_dangling_reference(project):
    project['timelines'][0]['parent'] = 'missing_actor'
    with pytest.raises(ValueError, match='Dangling'):
        BRIDGE.validate_project(project)

def test_state_string_is_rejected_instead_of_native_variant_warnings(project):
    project['templates'][0]['model']['state'] = 'type=wide,variant=steve'
    with pytest.raises(ValueError, match='JSON object'):
        BRIDGE.validate_project(project)

def test_custom_asset_resource_paths_resolve(tmp_path):
    target = tmp_path/'test.miproject'
    BRIDGE.build(BRIDGE.DEFAULT_BASE, target)
    for resource in json.loads(target.read_text())['resources']:
        path = tmp_path/resource['filename']
        assert path.is_file()
        assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')

def test_existing_project_is_preserved_before_asset_creation(tmp_path):
    target = tmp_path/'test.miproject'
    target.write_text('previous production')
    with pytest.raises(FileExistsError, match='Existing project preserved'):
        BRIDGE.build(BRIDGE.DEFAULT_BASE, target)
    assert target.read_text() == 'previous production'
    assert not (tmp_path/'assets').exists()

def test_new_project_cannot_overwrite_an_earlier_jobs_assets(tmp_path):
    assets = tmp_path/'assets'
    assets.mkdir()
    texture = assets/'lia.png'
    texture.write_bytes(b'original texture')
    with pytest.raises(FileExistsError, match='Existing assets preserved'):
        BRIDGE.build(BRIDGE.DEFAULT_BASE, tmp_path/'another.miproject')
    assert texture.read_bytes() == b'original texture'
    assert not (tmp_path/'another.miproject').exists()

@pytest.mark.parametrize('quality,size', [('preview',(540,960)), ('final',(1080,1920))])
def test_native_resolution_is_selected_before_render(tmp_path, quality, size):
    target = tmp_path/(quality+'.miproject')
    BRIDGE.build(BRIDGE.DEFAULT_BASE, target, quality)
    doc = json.loads(target.read_text())
    assert (doc['project']['video_width'], doc['project']['video_height']) == size
    assert doc['project']['view_main_camera'] == -5
