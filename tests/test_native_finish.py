"""Native finishing guards; generated decoder fixtures are not Minecraft demos."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('native_finish',ROOT/'scripts/finish_mineimator.py')
FINISH=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FINISH)


def wav(path, seconds=.3, frequency=430):
    t=np.arange(round(48000*seconds))/48000
    values=(.08*np.sin(2*np.pi*frequency*t)*32767).astype('<i2')
    with wave.open(str(path),'wb') as handle:
        handle.setnchannels(1);handle.setsampwidth(2);handle.setframerate(48000)
        handle.writeframes(values.tobytes())
    return path


@pytest.fixture
def job(tmp_path):
    voice=wav(tmp_path/'original.wav')
    effects=wav(tmp_path/'effects.wav',frequency=800)
    (tmp_path/'transcript.json').write_text(json.dumps({'duration':.3,'audio_sha256':FINISH.file_hash(voice),
        'words':[{'word':'teste','start':0,'end':.25}]}))
    return tmp_path,voice,effects


def native_metadata(width=1080,height=1920):
    return {'width':width,'height':height,'fps':30.,'duration':.3}


def test_preview_requires_matching_native_resolution_and_does_not_upscale(monkeypatch,job):
    folder,voice,effects=job
    monkeypatch.setattr(FINISH,'media_video',lambda path:native_metadata(540,960))
    info=FINISH.check_inputs(folder/'native.mp4',voice,folder,False,quality='preview',effects=effects)
    assert info['native']['width']==540 and info['quality']=='preview'
    assert info['narration_sha256']==FINISH.file_hash(voice)
    assert info['effects']['sha256']==FINISH.file_hash(effects)
    with pytest.raises(ValueError,match='no upscale'):
        FINISH.check_inputs(folder/'native.mp4',voice,folder,False)


def test_mixed_audio_cannot_replace_original_transcript_binding(monkeypatch,job):
    folder,voice,effects=job
    monkeypatch.setattr(FINISH,'media_video',lambda path:native_metadata())
    from minestory.native_sound import mix_narration
    mixed=folder/'mix.wav'
    mix_narration(voice,effects,mixed,.3)
    with pytest.raises(ValueError,match='SHA256'):
        FINISH.check_inputs(folder/'native.mp4',mixed,folder,False)
    # The same mix succeeds only when the unchanged source remains --audio.
    info=FINISH.check_inputs(folder/'native.mp4',voice,folder,False,effects=effects)
    assert info['narration_sha256']==FINISH.file_hash(voice)


def test_wrong_effect_duration_and_double_narration_are_rejected(monkeypatch,job):
    folder,voice,effects=job
    monkeypatch.setattr(FINISH,'media_video',lambda path:native_metadata())
    long_effect=wav(folder/'long-effects.wav',seconds=.5)
    with pytest.raises(ValueError,match='duration differs'):
        FINISH.check_inputs(folder/'native.mp4',voice,folder,False,effects=long_effect)
    with pytest.raises(ValueError,match='duplicated'):
        FINISH.check_inputs(folder/'native.mp4',voice,folder,False,effects=voice)


def test_real_preview_finish_with_effects_preserves_original_and_names(job):
    folder,voice,effects=job
    original_hash=FINISH.file_hash(voice)
    native=folder/'decoder-fixture.mp4'
    # Small generated unit-test fixture, not presented as a Mine-imator render.
    subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i',
                    'color=c=0x334455:s=540x960:r=30:d=0.3','-an','-c:v','libx264',
                    '-threads','1','-pix_fmt','yuv420p',str(native)],check=True)
    result=subprocess.run([sys.executable,str(ROOT/'scripts/finish_mineimator.py'),
        '--video',str(native),'--audio',str(voice),'--effects',str(effects),
        '--job',str(folder),'--quality','preview','--captions','off'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (folder/'video_preview.mp4').is_file()
    assert not (folder/'video_final.mp4').exists()
    report=json.loads((folder/'finish_preview_report.json').read_text())
    qc=json.loads((folder/'qc_preview_report.json').read_text())
    assert report['input']['narration_sha256']==original_hash==FINISH.file_hash(voice)
    assert report['effects_mix']['narration_sha256']==original_hash
    assert report['effects_mix']['narration_speed']==1
    assert report['effects_mix']['narration_pitch']==1
    assert qc['media']['width']==540 and qc['media']['height']==960
    assert qc['technical_gates_passed'] and qc['decoded_frames']==9
    assert (folder/'preview_contact_sheet.jpg').is_file()
    # The guarded output prevents a rerun from replacing the reviewed version.
    second=subprocess.run(result.args,capture_output=True,text=True)
    assert second.returncode!=0 and 'Preserving existing' in second.stderr


def test_finish_inserts_verified_retake_without_retiming_voice(job):
    folder,voice,_=job
    native=folder/'native-fixture.mp4';patch=folder/'retake-fixture.mp4'
    for target,color,frames in [(native,'0x334455',9),(patch,'red',3)]:
        subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i',
            f'color=c={color}:s=540x960:r=30','-frames:v',str(frames),'-an',
            '-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(target)],check=True)
    project=folder/'retake.miproject'
    project.write_text(json.dumps({'project':{'timeline':{'region_start':3,'region_end':5}}}))
    evidence=folder/'retake.export.json'
    evidence.write_text(json.dumps({'native_export_confirmed':True,'sha256':FINISH.file_hash(patch),
                                    'output':str(patch),'project':str(project)}))
    manifest=folder/'retakes.json'
    manifest.write_text(json.dumps({'retakes':[{'video':patch.name,'export_report':evidence.name,
                                                'start_frame':3,'end_frame_exclusive':6}]}))
    (folder/'legendas.ass').write_text('''[Script Info]\nScriptType: v4.00+\nPlayResX: 540\nPlayResY: 960\n
[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Pixelify Sans,40,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,30,1\n
[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.00,0:00:00.25,Default,,0,0,0,,teste\n''')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/finish_mineimator.py'),
        '--video',str(native),'--audio',str(voice),'--job',str(folder),'--quality','preview',
        '--captions','on','--retakes',str(manifest)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads((folder/'finish_preview_report.json').read_text())
    assert report['retakes'][0]['frames']==3
    assert report['narration_speed']==1 and report['input']['narration_sha256']==FINISH.file_hash(voice)
    qc=json.loads((folder/'qc_preview_report.json').read_text())
    assert qc['decoded_frames']==9 and qc['technical_gates_passed']
