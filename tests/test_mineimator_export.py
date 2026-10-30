"""Guards against overwrites and false-positive native export confirmation."""
import argparse
import importlib.util
from pathlib import Path
import json
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_export',ROOT/'scripts/export_mineimator.py')
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)

@pytest.fixture
def expected(tmp_path):
    project = tmp_path/'scene.miproject'
    project.write_text(json.dumps({'format':34,'created_in':'2.0.2',
        'project':{'video_width':1080,'video_height':1920,'tempo':30,
                   'timeline':{'region_start':0,'region_end':599}},
        'timelines':[{'type':'camera'}]}))
    return EXPORT.inspect_project(project)


def test_twenty_second_limit_is_enforced_before_gui_actions(tmp_path):
    project=tmp_path/'long.miproject'
    project.write_text(json.dumps({'format':34,'created_in':'2.0.2',
        'project':{'video_width':1080,'video_height':1920,'tempo':30,
                   'timeline':{'region_start':0,'region_end':600}},
        'timelines':[{'type':'camera'}]}))
    with pytest.raises(ValueError,match='at most 20 seconds'):
        EXPORT.inspect_project(project)


def test_old_project_completion_does_not_confirm_another_project(tmp_path):
    wanted=tmp_path/'wanted.miproject'
    log=f'00 Opening project: {wanted}\n00 Project loaded\n01 Opening project: /other.miproject\n'
    assert not EXPORT.last_project_loaded(log,wanted)


def test_other_export_completion_cannot_confirm_target(tmp_path):
    wanted=tmp_path/'wanted.mp4'
    log=(f'00 Export movie: {wanted}\n00 Format: mp4\n'
         '01 Export movie: /other.mp4\n01 '+EXPORT.COMPLETE+'\n')
    block=EXPORT.export_block(log,wanted)
    assert block is not None
    assert EXPORT.COMPLETE not in block
    assert not EXPORT.has_pending_export(log)


def test_incomplete_export_guard_does_not_use_earlier_success(tmp_path):
    log=('00 Export movie: /previous.mp4\n00 '+EXPORT.COMPLETE+'\n'
         '01 Export movie: /active.mp4\n01 Format: mp4\n')
    assert EXPORT.has_pending_export(log)
    assert not EXPORT.has_pending_export(log+'02 Opening project: /reloaded.miproject\n02 Project loaded\n')


def test_native_metadata_must_match_exact_export_profile(expected):
    block=('00 Format: mp4\n00 Bitrate: 5000000\n00 Framerate: 30\n00 Audio: no\n'
           '00 High Quality: yes\n00 Size: 1080, 1920\n00 Encoder: libx264 H.264 / AVC\n')
    EXPORT.validate_native_settings(block,expected)
    with pytest.raises(ValueError,match='Framerate'):
        EXPORT.validate_native_settings(block.replace('Framerate: 30','Framerate: 24'),expected)
    with pytest.raises(ValueError,match='Size'):
        EXPORT.validate_native_settings(block.replace('1080, 1920','540, 960'),expected)


def test_existing_video_is_refused_before_any_gui_call(tmp_path,expected):
    target=tmp_path/'previous.mp4'; target.write_bytes(b'preserve')
    args=argparse.Namespace(editor_ready=True,profile_confirmed=True,output=target)
    with pytest.raises(FileExistsError,match='already exists'):
        EXPORT.perform_export(args,expected)
    assert target.read_bytes()==b'preserve'


def test_missing_editor_inspection_refuses_before_gui(expected,tmp_path):
    args=argparse.Namespace(editor_ready=False,profile_confirmed=True,output=tmp_path/'new.mp4')
    with pytest.raises(ValueError,match='editor-ready'):
        EXPORT.perform_export(args,expected)


def test_checkbox_classifier_uses_center_interior_not_border():
    im=Image.new('RGB',(1600,1000),'white')
    assert not EXPORT.checkbox_checked(im,644,647)
    for x in range(640,649):
        for y in range(643,652): im.putpixel((x,y),(45,48,52))
    assert EXPORT.checkbox_checked(im,644,647)
