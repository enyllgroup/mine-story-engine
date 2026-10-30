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
