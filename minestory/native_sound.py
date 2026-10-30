"""Versioned Minecraft SFX provenance and non-destructive scene soundtracks.

Minecraft audio remains owned by Mojang/Microsoft under their Usage Guidelines.
Only locally downloaded assets live in the ignored library. Original scientific
effects are generated separately and explicitly identified as MineStory CC0.
No voice synthesis or playback speed changes are performed by this module.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import urllib.request
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / 'assets/audio/minecraft-sfx-1.20.2.json'
DEFAULT_LIBRARY = ROOT / 'library/audio/minecraft/1.20.2'
RATE = 48000
ORIGINAL_EVENTS = {'original:digitalize', 'original:squeeze', 'original:scan', 'original:whoosh'}


def catalog(path: Path = CATALOG_PATH) -> dict:
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or not data.get('license', {}).get('owner'):
        raise ValueError('Missing versioned sound catalog/provenance')
    for name, variants in data['events'].items():
        if not name.startswith('minecraft:') or not variants:
            raise ValueError('Minecraft event requires at least one cataloged variant')
        for record in variants:
            digest = record['sha1']
            if len(digest) != 40 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('Invalid official asset SHA1')
    return data


def asset_path(library: Path, record: dict) -> Path:
    return library / 'objects' / record['sha1'][:2] / (record['sha1'] + '.ogg')


def verify_asset(path: Path, record: dict) -> bool:
    return (path.is_file() and path.stat().st_size == record['bytes']
            and hashlib.sha1(path.read_bytes()).hexdigest() == record['sha1'])


def install(library: Path = DEFAULT_LIBRARY, *, verify_only: bool = False) -> dict:
    """Fetch the pinned small subset from official URLs; never a game client."""
    data = catalog()
    records = {x['sha1']: x for variants in data['events'].values() for x in variants}
    manifest = {'schema': 1, 'version': data['minecraft_version'], 'license': data['license'],
                'events': data['events'], 'assets': [], 'verify_only': verify_only}
    for record in records.values():
        path = asset_path(library, record)
        url = data['asset_base'] + '/' + record['sha1'][:2] + '/' + record['sha1']
        if not verify_asset(path, record):
            if verify_only:
                raise ValueError(f'Missing or damaged official sound: {record["asset"]}')
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.partial')
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = response.read(record['bytes'] + 1)
            if len(payload) != record['bytes'] or hashlib.sha1(payload).hexdigest() != record['sha1']:
                raise ValueError(f'Official sound checksum mismatch: {record["asset"]}')
            temporary.write_bytes(payload)
            temporary.replace(path)
        manifest['assets'].append({**record, 'url': url, 'local': str(path.resolve())})
    if not verify_only:
        library.mkdir(parents=True, exist_ok=True)
        # This cache manifest may be refreshed; production outputs never are.
        (library / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def _original(event: str) -> np.ndarray:
    """Original block-world compatible effects; not copyrighted game samples."""
    if event not in ORIGINAL_EVENTS:
        raise ValueError(f'Unknown original sound event: {event}')
    length = {'original:digitalize': .85, 'original:squeeze': .5,
              'original:scan': .7, 'original:whoosh': .35}[event]
    t = np.arange(round(RATE * length)) / RATE
    seed = int(hashlib.sha256(event.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    if event == 'original:digitalize':
        frequencies = np.round(np.linspace(350, 1500, 12) / 50) * 50
        f = frequencies[np.minimum((t / length * len(frequencies)).astype(int), len(frequencies)-1)]
        signal = .7 * np.sin(2*np.pi*np.cumsum(f)/RATE) + .08*rng.normal(size=len(t))
        signal *= (np.sin(2*np.pi*18*t) > -.2)
    elif event == 'original:squeeze':
        phase = 2*np.pi*np.cumsum(260 + 950*(t/length)**2)/RATE
        signal = np.sin(phase) + .2*np.sin(phase*2)
    elif event == 'original:scan':
        phase = 2*np.pi*np.cumsum(700 + 400*np.sin(2*np.pi*t/length))/RATE
        signal = .7*np.sin(phase) * (.6+.4*np.sin(2*np.pi*12*t))
    else:
        signal = np.convolve(rng.normal(size=len(t)), np.ones(16)/16, 'same')
    signal *= np.sin(np.pi*t/length)**2
    return (signal / max(1e-9, np.max(np.abs(signal))) * .22).astype(np.float32)


def _decode(path: Path) -> np.ndarray:
    p = subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(path),'-ac','1','-ar',str(RATE),
                        '-f','f32le','pipe:1'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    samples = np.frombuffer(p.stdout, dtype='<f4').copy()
    if not len(samples) or not np.isfinite(samples).all():
        raise ValueError(f'Invalid decoded sound: {path}')
    return samples


def validate_cues(cues: dict) -> float:
    duration = float(cues['duration'])
    if not math.isfinite(duration) or duration <= 0 or duration > 600:
        raise ValueError('Cue duration must be finite, positive and at most 600 seconds')
    known = set(catalog()['events']) | ORIGINAL_EVENTS
    for event in cues.get('events', []):
        if event['event'] not in known:
            raise ValueError(f'Unknown catalog sound event: {event["event"]}')
        at, gain, pan = float(event['at']), float(event.get('gain', .35)), float(event.get('pan', 0))
        if not all(math.isfinite(v) for v in (at,gain,pan)) or not 0 <= at < duration:
            raise ValueError('Sound cue time/value is not finite or lies outside narration')
        if not 0 <= gain <= 1 or not -1 <= pan <= 1:
            raise ValueError('Gain/pan outside allowed range')
        if 'duration' in event:
            length = float(event['duration'])
            if not math.isfinite(length) or not 0 < length <= duration-at+.00001:
                raise ValueError('Loop duration must stay inside narration')
    return duration


def build_timeline(cues: dict, output: Path, *, library: Path = DEFAULT_LIBRARY) -> dict:
    """Mix explicit action-synchronized cues; save this timeline only in its job."""
    duration = validate_cues(cues)
    if output.exists():
        raise FileExistsError(f'Production sound preserved: {output}')
    data = catalog()
    timeline = np.zeros((math.ceil(duration*RATE),2),dtype=np.float32)
    decoded, events = {}, []
    for index, cue in enumerate(cues.get('events', [])):
        name = cue['event']
        provenance = {'event':name, 'time':float(cue['at']), 'gain':float(cue.get('gain',.35)),
                      'pan':float(cue.get('pan',0))}
        if name.startswith('original:'):
            samples = decoded.setdefault(name, _original(name))
            provenance.update(source='MineStory original synthesized waveform', license='CC0-1.0')
        else:
            variants = data['events'][name]
            record = variants[int(cue.get('variant',index)) % len(variants)]
            path = asset_path(library, record)
            if not verify_asset(path,record):
                raise ValueError(f'Official SFX missing/damaged; install catalog first: {name}')
            if record['sha1'] not in decoded:
                decoded[record['sha1']] = _decode(path)
            samples = decoded[record['sha1']]
            provenance.update(source=record['asset'],sha1=record['sha1'],license=data['license']['id'],
                              url=data['asset_base']+'/'+record['sha1'][:2]+'/'+record['sha1'])
        if 'duration' in cue:
            count = round(float(cue['duration'])*RATE)
            samples = np.tile(samples, math.ceil(count/len(samples)))[:count]
        at = round(float(cue['at'])*RATE)
        n = min(len(samples),len(timeline)-at)
        values = samples[:n].copy() * provenance['gain']
        fade = min(round(.006*RATE),n//2)
        if fade:
            values[:fade] *= np.linspace(0,1,fade)
            values[-fade:] *= np.linspace(1,0,fade)
        pan = provenance['pan']
        timeline[at:at+n,0] += values * math.cos((pan+1)*math.pi/4)
        timeline[at:at+n,1] += values * math.sin((pan+1)*math.pi/4)
        events.append({**provenance,'length_seconds':n/RATE})
    peak = float(np.abs(timeline).max()) if len(timeline) else 0
    if peak > .95:
        timeline *= .95/peak
    output.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation protects an earlier production from accidental reruns.
    with output.open('xb') as handle:
        with wave.open(handle,'wb') as wav:
            wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(RATE)
            wav.writeframes((np.clip(timeline,-1,1)*32767).astype('<i2').tobytes())
    return {'output':str(output.resolve()),'duration':duration,'sample_rate':RATE,'channels':2,
            'events':events,'events_count':len(events),'music':False,'peak_before_limiter':peak,
            'license_note':'Mixed sources retain separate rights; Minecraft samples are not CC0.',
            'timeline_scope':'production only; not a permanent story template'}


def mix_narration(narration: Path, effects: Path, output: Path, duration: float) -> dict:
    """Unity narration plus speech-ducked low SFX, with no time/pitch changes."""
    if output.exists():
        raise FileExistsError(f'Production mix preserved: {output}')
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid narration duration')
    output.parent.mkdir(parents=True,exist_ok=True)
    graph = ('[0:a]aresample=48000,asplit=2[voice][detector];'
             '[1:a]aresample=48000,volume=0.35[fx];'
             '[fx][detector]sidechaincompress=threshold=0.025:ratio=10:attack=8:release=180[ducked];'
             '[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,'
             'alimiter=limit=0.98:level=false:latency=true[out]')
    p = subprocess.run(['ffmpeg','-v','error','-n','-nostdin','-i',str(narration),'-i',str(effects),
                        '-filter_complex',graph,'-map','[out]','-t',str(duration),'-ac','2',
                        '-c:a','pcm_s16le',str(output)],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError('Native sound mix failed: '+p.stderr[-1500:])
    return {'path':str(output.resolve()),'narration_gain':1,'narration_speed':1,
            'narration_pitch':1,'effects_gain':.35,'sidechain_ducking':True,'music':False,
            'narration_sha256':hashlib.file_digest(narration.open('rb'),'sha256').hexdigest(),
            'effects_sha256':hashlib.file_digest(effects.open('rb'),'sha256').hexdigest()}
