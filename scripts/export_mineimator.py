#!/usr/bin/env python3
"""Guarded native GUI export for Mine-imator 2.0.2 Linux, English light UI.

Fixed profile: maximized editor on a 1600x1000 X11 display, default UI scale,
Custom video size, MP4/30FPS, audio off, hidden off, high quality on, watermark
off through the application's legitimate Full configuration. Does not activate
licenses, patch the binary, remove watermarks, or operate another renderer.

--editor-ready and --profile-confirmed attest an agent/operator has inspected
that state. Runtime checks still require native load logs, exact display/window
size, OCR, checkbox pixels, new export logs, completion toast and ffprobe.
--monitor only reads an export already started by the real application.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GUI_SCRIPT = ROOT / 'scripts/mineimator_gui.py'
PROFILE = 'mineimator-2.0.2-linux-en-light-1600x1000'
COMPLETE = 'New toast: Movie exporting finished!, positive'
SPEC = importlib.util.spec_from_file_location('mineimator_gui_export_helpers', GUI_SCRIPT)
GUI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUI)


def inspect_project(path: Path, max_seconds: float = 20) -> dict:
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError('Maximum duration must be finite and positive')
    doc = json.loads(path.read_text())
    if doc.get('format') != 34 or doc.get('created_in') != '2.0.2':
        raise ValueError('Only native Mine-imator 2.0.2 format 34 is supported')
    project = doc['project']
    width, height = project['video_width'], project['video_height']
    if (width, height) not in ((540,960), (1080,1920)):
        raise ValueError('This tested profile supports only 540x960 or 1080x1920')
    fps = float(project['tempo'])
    if fps != 30:
        raise ValueError('This tested GUI profile requires 30FPS project tempo')
    timeline = project.get('timeline', {})
    start, end = timeline.get('region_start'), timeline.get('region_end')
    if not isinstance(start, (int,float)) or not isinstance(end, (int,float)):
        raise ValueError('Project needs an explicit numeric export region')
    if start < 0 or end < start:
        raise ValueError('Invalid export region')
    frames = math.floor((end-start)/fps*30) + 1
    if frames < 2 or frames/30 > max_seconds:
        raise ValueError(f'This validation controller allows a project of at most {max_seconds:g} seconds; use --max-seconds for a longer requested narration')
    if not any(t.get('type') == 'camera' for t in doc.get('timelines', [])):
        raise ValueError('Native project has no camera timeline')
    return {'project':str(path.resolve()), 'width':width, 'height':height,
            'fps':30, 'expected_frames':frames, 'expected_duration':frames/30,
            'profile':PROFILE}


def last_project_loaded(log: str, project: Path) -> bool:
    opened, complete = None, False
    for line in log.splitlines():
        if 'Opening project: ' in line:
            opened = line.split('Opening project: ',1)[1].strip()
            complete = False
        elif opened is not None and line.endswith('Project loaded'):
            complete = True
    return opened == str(project.resolve()) and complete


def export_block(log: str, output: Path) -> str | None:
    """Scope completion/settings to the latest matching native export event."""
    blocks = re.split(r'(?m)^.*?Export movie: ', log)
    selected = None
    for block in blocks[1:]:
        first, _, rest = block.partition('\n')
        if first.strip() == str(output.resolve()):
            selected = rest
    return selected


def has_pending_export(log: str) -> bool:
    # Reopening a project establishes a new idle editor after a cancellation.
    latest = log.rsplit('Opening project: ',1)[-1]
    blocks = re.split(r'(?m)^.*?Export movie: ', latest)
    if len(blocks) == 1:
        return False
    tail = blocks[-1]
    return COMPLETE not in tail and 'Error when exporting' not in tail and 'Movie export error' not in tail


def validate_native_settings(block: str, expected: dict) -> None:
    values = {}
    for field in ('Format','Bitrate','Framerate','Audio','High Quality','Size','Encoder'):
        match = re.search(r'(?m)^.*?\b'+re.escape(field)+r': (.+)$',block)
        if match:
            values[field] = match.group(1).strip()
    required = {'Format':'mp4','Bitrate':'5000000','Framerate':'30','Audio':'no',
                'High Quality':'yes','Size':f"{expected['width']}, {expected['height']}"}
    for key,value in required.items():
        if values.get(key) != value:
            raise ValueError(f'Native export setting {key}: expected {value!r}, got {values.get(key)!r}')
    if not values.get('Encoder','').startswith('libx264 '):
        raise ValueError('Native log did not confirm the libx264 encoder')


def checkbox_checked(image: Image.Image, x: int, y: int) -> bool:
    image = image.convert('RGB')
    pixels = [image.getpixel((xx,yy)) for xx in range(x-4,x+5) for yy in range(y-4,y+5)]
    return sum(sum(p) < 450 for p in pixels)/len(pixels) > .35


def verify_popup(image_path: Path, expected: dict, *, best: bool) -> str:
    image = Image.open(image_path)
    if image.size != (1600,1000):
        raise ValueError('Screenshot size differs from the fixed 1600x1000 profile')
    crop = image.crop((625,256,975,744))
    buf = io.BytesIO(); crop.resize((1050,1464)).save(buf,'PNG')
    proc = subprocess.run(['tesseract','stdin','stdout','--psm','6'],input=buf.getvalue(),
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    ocr = proc.stdout.decode('utf-8',errors='replace')
    if 'Export movie' not in ocr or 'MP4' not in ocr:
        raise ValueError('OCR did not confirm the native MP4 export popup')
    if not re.search(r'\bW\w*\s+'+str(expected['width'])+r'\s+H\s+'+str(expected['height'])+r'\b',ocr,re.I):
        raise ValueError('OCR did not confirm project dimensions in the popup')
    if not re.search(r'Framerate\s+30\b',ocr,re.I):
        raise ValueError('OCR did not confirm 30 FPS')
    if best and not re.search(r'Video quality\s+Best\b',ocr,re.I):
        raise ValueError('OCR did not confirm the Best bitrate preset')
    for name,y,wanted in [('audio',583,False),('hidden objects',615,False),
                           ('high quality',647,True),('watermark',679,False)]:
        if checkbox_checked(image,644,y) != wanted:
            raise ValueError(f'Native checkbox {name} differs from the tested profile; inspect the screenshot')
    return ocr


def probe_finished(output: Path, expected: dict) -> dict:
    proc = subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format',
                           '-of','json',str(output)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    data = json.loads(proc.stdout)
    streams = data.get('streams',[])
    videos = [s for s in streams if s.get('codec_type') == 'video']
    if len(videos) != 1:
        raise ValueError('Expected exactly one native video stream')
    video = videos[0]
    if video.get('codec_name') != 'h264' or (video.get('width'),video.get('height')) != (expected['width'],expected['height']):
        raise ValueError('ffprobe rejected native codec or dimensions')
    if Fraction(video['avg_frame_rate']) != 30:
        raise ValueError('ffprobe rejected frame rate')
    if int(video.get('nb_read_frames',video.get('nb_frames',0))) != expected['expected_frames']:
        raise ValueError('Native video frame count is incomplete or differs from the project region')
    duration = float(data['format']['duration'])
    if abs(duration-expected['expected_duration']) > 1/30+.002:
        raise ValueError('Native video duration differs from the project region')
    if any(s.get('codec_type') == 'audio' for s in streams):
        raise ValueError('This profile expects a silent native master; narration is mixed afterward')
    return data


def monitor(log_path: Path, output: Path, expected: dict, timeout: float, checkpoint=None) -> dict:
    deadline = time.monotonic()+timeout
    next_status = 0
    while time.monotonic() < deadline:
        log = (GUI.new_log_segment(log_path,checkpoint) if checkpoint else log_path.read_text(errors='replace'))
        block = export_block(log,output)
        if block is not None:
            if 'Error when exporting' in block or 'Error when adding frame' in block or 'Movie export error' in block:
                raise RuntimeError('Native application reported export failure; inspect its log')
            if COMPLETE in block:
                validate_native_settings(block,expected)
                if not output.is_file():
                    raise RuntimeError('Completion toast exists but output file is missing')
                probe = probe_finished(output,expected)
                with output.open('rb') as handle:
                    checksum = hashlib.file_digest(handle,'sha256').hexdigest()
                return {**expected,'output':str(output.resolve()),'native_export_confirmed':True,
                        'native_log':str(log_path.resolve()), 'native_evidence':block,
                        'sha256':checksum,
                        'bytes':output.stat().st_size,'ffprobe':probe,
                        'semantic_visual_qc':'pending separate frame inspection'}
        if time.monotonic() >= next_status:
            print(json.dumps({'status':'waiting for native completion','output_bytes':output.stat().st_size if output.exists() else 0}),flush=True)
            next_status = time.monotonic()+15
        time.sleep(1)
    raise TimeoutError('Native completion was not confirmed before timeout; output was preserved and is not approved')


def gui_env(display: str) -> dict:
    env = dict(os.environ, DISPLAY=display)
    lib = str(GUI.XROOT/'usr/lib/x86_64-linux-gnu')
    env['LD_LIBRARY_PATH'] = lib + (':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    return env


def assert_editor_geometry(display: str) -> None:
    env = gui_env(display)
    info = subprocess.check_output(['xdpyinfo'],env=env,text=True)
    if not re.search(r'dimensions:\s+1600x1000\s+pixels',info):
        raise ValueError('Display must be exactly 1600x1000')
    xdo = str(GUI.XROOT/'usr/bin/xdotool')
    focused = subprocess.check_output([xdo,'getwindowfocus'],env=env,text=True).strip()
    title = subprocess.check_output([xdo,'getwindowname',focused],env=env,text=True).strip()
    geometry = subprocess.check_output([xdo,'getwindowgeometry','--shell',focused],env=env,text=True)
    values = dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
    native_title = title == 'Mine-imator' or title.endswith(' - Mine-imator')
    if not native_title or any(values.get(k) != v for k,v in {'X':'0','Y':'0','WIDTH':'1600','HEIGHT':'1000'}.items()):
        raise ValueError('Focused Mine-imator editor must fill the display at 0,0')


def perform_export(args, expected: dict) -> dict:
    if not args.editor_ready or not args.profile_confirmed:
        raise ValueError('GUI export requires --editor-ready and --profile-confirmed after inspection of the documented profile')
    if args.output.exists():
        raise FileExistsError('Destination already exists; choose a new path')
    text = args.log.read_text(errors='replace')
    if not last_project_loaded(text,args.project):
        raise ValueError('The last completed native project load is not the requested project')
    if has_pending_export(text):
        raise ValueError('Native log indicates an unfinished export; no GUI actions were sent')
    if args.check:
        return {**expected,'preflight':'passed file/log guards; no GUI actions sent','gui_profile_checks':'not run in --check mode'}
    assert_editor_geometry(args.display)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    checkpoint = GUI.log_checkpoint(args.log)
    prefix = args.output.with_suffix('')
    before = Path(str(prefix)+'.editor.png'); popup = Path(str(prefix)+'.settings.png'); best = Path(str(prefix)+'.best.png')
    for path in (before,popup,best):
        if path.exists():
            raise FileExistsError(f'Evidence path already exists: {path}')
    def call(*tokens, input=None):
        subprocess.run([sys.executable,str(GUI_SCRIPT),'--display',args.display,*map(str,tokens)],
                       input=input,check=True)
    call('screenshot',before)
    call('click',110,14)
    call('click',161,68)
    time.sleep(.7)
    call('screenshot',popup)
    verify_popup(popup,expected,best=False)
    call('click',800,503)
    call('click',662,528)
    time.sleep(.7)
    call('screenshot',best)
    ocr = verify_popup(best,expected,best=True)
    call('click',921,716)
    time.sleep(.5)
    env = gui_env(args.display); xdo = str(GUI.XROOT/'usr/bin/xdotool')
    focused = subprocess.check_output([xdo,'getwindowfocus'],env=env,text=True).strip()
    title = subprocess.check_output([xdo,'getwindowname',focused],env=env,text=True).strip()
    if title != args.save_dialog_title:
        raise ValueError(f'Expected native file picker {args.save_dialog_title!r}, got {title!r}; no destination pasted')
    if args.output.exists():
        raise FileExistsError('Destination appeared during GUI preparation; export refused')
    call('text',input=str(args.output.resolve()).encode())
    call('key','Return','--hold','.03')
    report = monitor(args.log,args.output,expected,args.timeout,checkpoint)
    report['profile_ocr'] = ocr
    report['screenshots'] = [str(p) for p in (before,popup,best)]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--log',type=Path,default=Path.home()/'Mine-imator/log.txt')
    parser.add_argument('--display',default=':100')
    parser.add_argument('--editor-ready',action='store_true')
    parser.add_argument('--profile-confirmed',action='store_true')
    parser.add_argument('--save-dialog-title',default='Save movie')
    parser.add_argument('--timeout',type=float,default=3600)
    parser.add_argument('--max-seconds',type=float,default=20,
                        help='Allowed narration length; default retains earlier short-test limit')
    parser.add_argument('--check',action='store_true',help='validate file/log guards without GUI interaction')
    parser.add_argument('--monitor',action='store_true',help='only monitor an already started native export, never operate GUI')
    parser.add_argument('--report',type=Path,help='new JSON evidence report path; existing reports are never overwritten')
    args = parser.parse_args()
    try:
        args.project = args.project.resolve(strict=True)
        args.log = args.log.resolve(strict=True)
        args.output = args.output.resolve()
        if args.output.suffix.lower() != '.mp4':
            raise ValueError('Destination must be MP4')
        if not re.fullmatch(r':\d+',args.display):
            raise ValueError('Display must be local, such as :100')
        if args.timeout <= 0:
            raise ValueError('Timeout must be positive')
        report_path = args.report or args.output.with_suffix('.export.json')
        if report_path.resolve() == args.output.resolve():
            raise ValueError('Report path must differ from the video destination')
        if not args.check and report_path.exists():
            raise FileExistsError('Report exists; choose a new report path')
        expected = inspect_project(args.project,args.max_seconds)
        if args.monitor:
            if args.check:
                raise ValueError('--check and --monitor are separate modes')
            if export_block(args.log.read_text(errors='replace'),args.output) is None:
                raise ValueError('No native export event for that destination exists in the log')
            report = monitor(args.log,args.output,expected,args.timeout)
            report['mode'] = 'monitor only; no GUI actions'
        else:
            report = perform_export(args,expected)
        if not args.check:
            report_path.parent.mkdir(parents=True,exist_ok=True)
            with report_path.open('x') as handle:
                json.dump(report,handle,ensure_ascii=False,indent=2); handle.write('\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('native_evidence','ffprobe','profile_ocr')},ensure_ascii=False,indent=2))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        parser.exit(1,f'Export not confirmed: {error}\n')

if __name__ == '__main__':
    main()
