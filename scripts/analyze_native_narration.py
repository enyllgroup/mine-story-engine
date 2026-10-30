#!/usr/bin/env python3
"""Prepare real narration for native production without invoking a renderer.

Preserves a byte-identical input, ASR evidence, measured pauses and word timing.
All model inference is local/free. Whisper timestamps are acoustic estimates,
not an independent forced alignment. No TTS or audio speed change is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from minestory.audio import analyze, probe_audio, validate_transcript
from minestory.captions import write_captions


def digest(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def new_json(path: Path, value: dict) -> None:
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model', default='large-v3-turbo')
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args()
    source = args.audio.resolve(strict=True)
    if args.threads not in (1, 2):
        parser.error('--threads must be 1 or 2 on this CPU-sharing production host')
    job = args.output.resolve()
    job.mkdir(parents=True, exist_ok=True)
    source_hash = digest(source)
    transcript_path = job/'transcript.json'
    if transcript_path.exists():
        data = json.loads(transcript_path.read_text())
        validate_transcript(data)
        if data.get('audio_sha256') != source_hash:
            raise SystemExit('Existing transcript preserved: different narration; choose a new job')
        print(json.dumps({'status':'existing transcription preserved', 'transcript':str(transcript_path),
                          'duration':data['duration']}))
        return
    for name in ('transcript.raw-asr.json', 'narration_manifest.json', 'legendas.ass',
                 'legendas.srt', 'caption_report.json', 'narrative_clauses.json'):
        if (job/name).exists():
            raise SystemExit(f'Existing {name} preserved; choose a new production version')
    original = job/'input'/('narracao'+source.suffix.lower())
    original.parent.mkdir(parents=True, exist_ok=True)
    if original.exists():
        if digest(original) != source_hash:
            raise SystemExit('Existing original audio preserved: SHA256 mismatch')
    else:
        with source.open('rb') as reader, original.open('xb') as writer:
            shutil.copyfileobj(reader, writer)
    probe = probe_audio(original)
    new_json(job/'narration_manifest.json', {
        'source':str(source), 'preserved_original':str(original), 'sha256':source_hash,
        'audio':probe, 'synthetic':False, 'retiming':False, 'voice_replacement':False,
        'transcription_model':args.model, 'inference':'local CPU int8', 'paid_api':False,
    })
    # Reuse only model weights globally. Narration text/cache belongs to this
    # production, never to the permanent character or creative-example library.
    from faster_whisper.utils import download_model
    local_model = Path(args.model)
    if not local_model.is_dir():
        local_model = Path(download_model(args.model, cache_dir=str(ROOT/'library/cache/models')))
    transcript = analyze(original, job/'analysis_cache', model=str(local_model.resolve()),
                         language='pt', cpu_threads=args.threads)
    transcript['transcription']['model_cache_path'] = str(local_model.resolve())
    transcript['transcription']['model'] = args.model
    validate_transcript(transcript)
    new_json(job/'transcript.raw-asr.json', transcript)
    new_json(transcript_path, transcript)
    captions = write_captions(transcript, job, font_path=ROOT/'assets/fonts/PixelifySans.ttf')
    new_json(job/'caption_report.json', captions)
    new_json(job/'narrative_clauses.json', {
        'duration':transcript['duration'], 'source_sha256':source_hash,
        'segments':transcript['segments'], 'pauses':transcript['pauses'],
        'timing':'Whisper acoustic estimates with measured silence clipping',
        'forced_alignment':False, 'corrections':[],
    })
    print(json.dumps({'status':'analyzed', 'duration':transcript['duration'],
                      'words':len(transcript['words']), 'transcript':str(transcript_path),
                      'source_sha256':source_hash, 'forced_alignment':False}, indent=2))


if __name__ == '__main__':
    main()
