"""Original-audio and reviewed-artifact preservation in native analysis."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import wave

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_narration', ROOT/'scripts/analyze_native_narration.py')
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


@pytest.fixture
def prepared(monkeypatch, tmp_path):
    source = tmp_path/'supplied.wav'
    with wave.open(str(source), 'wb') as handle:
        handle.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        handle.writeframes(b'\0\0'*1600)
    model = tmp_path/'cached-model'; model.mkdir()
    monkeypatch.setattr('faster_whisper.utils.download_model', lambda *a, **kw: str(model))
    calls = []
    def analyze(path, cache, **kwargs):
        calls.append((path, cache, kwargs))
        return {'duration':.1, 'audio_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                'words':[{'word':'Teste.', 'start':0, 'end':.1, 'probability':1}],
                'segments':[{'text':'Teste.', 'start':0, 'end':.1}], 'pauses':[],
                'transcription':{'forced_alignment':False}}
    monkeypatch.setattr(ANALYZER, 'analyze', analyze)
    job = tmp_path/'new-job'
    monkeypatch.setattr(sys, 'argv', ['analyze_native_narration.py', str(source), '--output', str(job)])
    return source, job, calls


def test_original_and_raw_evidence_are_preserved_in_production(prepared):
    source, job, calls = prepared
    ANALYZER.main()
    assert (job/'input/narracao.wav').read_bytes() == source.read_bytes()
    raw = json.loads((job/'transcript.raw-asr.json').read_text())
    current = json.loads((job/'transcript.json').read_text())
    assert raw == current and raw['transcription']['forced_alignment'] is False
    assert calls[0][1] == job/'analysis_cache'
    assert (job/'legendas.ass').is_file() and (job/'legendas.srt').is_file()


def test_existing_review_and_captions_are_not_overwritten(prepared):
    source, job, calls = prepared
    ANALYZER.main()
    captions = job/'legendas.srt'
    captions.write_text('Reviewed captions')
    ANALYZER.main()
    assert len(calls) == 1
    assert captions.read_text() == 'Reviewed captions'


def test_different_audio_cannot_replace_prior_production(prepared):
    source, job, calls = prepared
    ANALYZER.main()
    before = (job/'input/narracao.wav').read_bytes()
    source.write_bytes(b'different audio, not even a WAV')
    with pytest.raises(SystemExit, match='different narration'):
        ANALYZER.main()
    assert len(calls) == 1
    assert (job/'input/narracao.wav').read_bytes() == before
