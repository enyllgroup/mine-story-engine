"""Sound provenance, explicit event timing, and non-destructive production IO."""
import hashlib
import json
from pathlib import Path
import subprocess
import wave
import numpy as np
import pytest

from minestory import native_sound as sound


def test_vanilla_catalog_preserves_rights_and_pinned_hashes():
    data=sound.catalog()
    assert 'all rights reserved' in data['license']['id']
    assert data['license']['music_included'] is False
    assert data['asset_base']=='https://resources.download.minecraft.net'
    assert 'Mojang' in data['license']['owner']
    assert all(x['asset'].startswith('minecraft/sounds/') and x['bytes']>0
               for variants in data['events'].values() for x in variants)


def test_invalid_or_unknown_event_is_not_silently_substituted():
    for cue in ({'event':'nintendo:catch','at':0},
                {'event':'minecraft:item_pickup','at':float('nan')},
                {'event':'minecraft:item_pickup','at':5},
                {'event':'minecraft:item_pickup','at':0,'gain':2},
                {'event':'minecraft:portal_ambient','at':1,'duration':7}):
        with pytest.raises(ValueError):sound.validate_cues({'duration':3,'events':[cue]})


def test_corrupt_official_asset_is_rejected_instead_of_used(tmp_path):
    record=sound.catalog()['events']['minecraft:item_pickup'][0]
    path=sound.asset_path(tmp_path,record);path.parent.mkdir(parents=True)
    path.write_bytes(b'not official audio')
    assert not sound.verify_asset(path,record)
    with pytest.raises(ValueError,match='missing/damaged'):
        sound.build_timeline({'duration':1,'events':[{'event':'minecraft:item_pickup','at':0}]},
                             tmp_path/'effects.wav',library=tmp_path)


def test_existing_production_sound_is_preserved(tmp_path):
    out=tmp_path/'fx.wav';out.write_bytes(b'previous production')
    with pytest.raises(FileExistsError):sound.build_timeline({'duration':1,'events':[]},out)
    assert out.read_bytes()==b'previous production'
    with pytest.raises(FileExistsError):sound.mix_narration(tmp_path/'voice.wav',out,out,1)


def test_original_timeline_has_timed_silence_and_honest_cc0_provenance(tmp_path):
    out=tmp_path/'fx.wav'
    report=sound.build_timeline({'duration':2,'events':[{'event':'original:digitalize','at':1,'gain':.5}]},out)
    assert report['events'][0]['license']=='CC0-1.0'
    assert 'not CC0' in report['license_note']
    with wave.open(str(out),'rb') as wav:
        assert wav.getframerate()==48000 and wav.getnchannels()==2
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').reshape(-1,2)
    assert not samples[:48000].any()
    assert samples[48000:].any()
    assert len(samples)==96000


def test_empty_effect_mix_does_not_retime_narration(tmp_path):
    voice=tmp_path/'voice.wav';fx=tmp_path/'fx.wav';mixed=tmp_path/'mix.wav'
    t=np.arange(48000)/48000
    original=(.12*np.sin(2*np.pi*440*t)*32767).astype('<i2')
    with wave.open(str(voice),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(48000);wav.writeframes(original.tobytes())
    sound.build_timeline({'duration':1,'events':[]},fx)
    report=sound.mix_narration(voice,fx,mixed,1)
    with wave.open(str(mixed),'rb') as wav:
        assert wav.getnframes()==48000 and wav.getframerate()==48000
        result=np.frombuffer(wav.readframes(48000),dtype='<i2').reshape(-1,2)
    # FFmpeg duplicates mono into stereo with its normal -3dB channel mapping.
    # Timing/correlation, rather than container hash, checks voice preservation.
    assert np.corrcoef(result[:,0],original)[0,1]>.9999
    assert report['narration_speed']==report['narration_pitch']==1
    assert report['narration_sha256']==hashlib.sha256(voice.read_bytes()).hexdigest()
