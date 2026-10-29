"""Resumable audio → scene graph → Blender frames → captioned H.264."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from . import __version__
from .util import ROOT, content_hash, event, file_hash, read_json, run, write_json
from .library import Library

PROFILES = {"preview": {"width":360,"height":640,"fps":30,"crf":21},
            "final": {"width":1080,"height":1920,"fps":30,"crf":18}}

def _profile_gate(qc,profile):
    media=qc.get("media",{})
    if any(media.get(k)!=profile[k] for k in ("width","height","fps")):
        qc.setdefault("issues",[]).append({"severity":"error","code":"profile_dimensions","detail":"A resolução/FPS real não coincide com o perfil solicitado"})
        qc["technical_gates_passed"]=False
        qc["status"]="needs_review"
    return qc

def doctor():
    tools = {}
    for name, args in {"blender":["--version"], "ffmpeg":["-version"], "ffprobe":["-version"], "codex":["--version"]}.items():
        path = shutil.which(name)
        item = {"path":path, "available":bool(path)}
        if path:
            try:
                item["version"] = run([path,*args], timeout=20).stdout.splitlines()[0]
            except Exception as exc:
                item["error"] = str(exc)
        tools[name] = item
    return {"engine":__version__, "cpu_count":os.cpu_count(), "tools":tools,
            "model_present":(ROOT / ".models/qwen2.5-1.5b-instruct-q4_k_m.gguf").is_file(),
            "note":"Status de login Codex não comprova autorização de uma chamada; execução é validada pelo diretor."}

def _check_tools():
    for name in ("blender", "ffmpeg", "ffprobe"):
        if not shutil.which(name):
            raise RuntimeError(f"Ferramenta obrigatória ausente: {name}. Consulte docs/OPERATIONS.md")

def _scene_clip(scene, profile, cache, log, *, reuse=True):
    sources = [ROOT / "minestory" / name for name in ("blender_scene.py", "assets.py")]
    key = content_hash({"scene":scene,"profile":profile,"renderer":[file_hash(p) for p in sources],
                        "blender":run(["blender","--version"],timeout=15).stdout.splitlines()[0]})
    folder = Path(cache) / "scenes" / key
    folder.mkdir(parents=True, exist_ok=True)
    from filelock import FileLock
    with FileLock(str(folder/".render.lock"),timeout=3600):
        return _realize_scene(scene,profile,folder,key,log,reuse=reuse)

def _realize_scene(scene,profile,folder,key,log,*,reuse=True):
    """Only one process may write a content-addressed scene at a time."""
    marker = folder / "complete.json"
    clip = folder / "scene.mp4"
    frames = round(scene["end"] * profile["fps"]) - round(scene["start"] * profile["fps"])
    if frames < 1:
        raise ValueError(f"Cena {scene['id']} tem menos de um quadro")
    if reuse and marker.exists() and clip.exists():
        manifest = read_json(marker)
        if manifest.get("clip_sha256") == file_hash(clip):
            return {"id":scene["id"],"key":key,"path":str(clip),"cached":True,"frames":frames,"seconds":0}
    started = time.monotonic()
    write_json(folder / "scene.json", scene)
    frame_dir = folder / "frames"
    frame_dir.mkdir(exist_ok=True)
    if reuse:
        from PIL import Image
        for existing in frame_dir.glob("frame_*.png"):
            try:
                with Image.open(existing) as decoded:
                    decoded.verify()
            except (OSError,ValueError,SyntaxError):
                # A render interrupted during PNG write must not poison resume.
                existing.unlink()
    command = ["blender", "-b", "--threads", "2", "--python", ROOT / "minestory/blender_scene.py", "--",
               "--scene", folder / "scene.json", "--output", frame_dir,
               "--width", profile["width"], "--height", profile["height"], "--fps",profile["fps"], "--frames",frames,"--save-blend"]
    if reuse:
        command.append("--resume")
    run(command, log=log, timeout=max(300, frames * 6))
    pngs = sorted(frame_dir.glob("*.png"))
    if len(pngs) < frames:
        raise RuntimeError(f"Cena {scene['id']}: render retornou {len(pngs)} de {frames} PNGs")
    # Blender's default frame numbering uses four digits starting at one.
    temporary = folder / "scene.pending.mp4"
    run(["ffmpeg","-y","-v","warning","-framerate",profile["fps"],"-start_number","1",
         "-i",frame_dir / "frame_%04d.png","-frames:v",frames,"-an","-c:v","libx264",
         "-preset","veryfast","-crf",profile["crf"],"-pix_fmt","yuv420p","-threads","2",
         "-movflags","+faststart",temporary],log=log,timeout=max(180,frames))
    temporary.replace(clip)
    info = {"id":scene["id"],"key":key,"path":str(clip),"cached":False,"frames":frames,
            "seconds":round(time.monotonic()-started,3),"clip_sha256":file_hash(clip)}
    write_json(marker,info)
    from .cache import compact_scene
    info["frame_compaction"]=compact_scene(folder)
    return info

def render_storyboard(storyboard, audio, output, *, quality="preview", captions=True, reuse_assets=True,
                      jobs=1, transcript=None, library=None, music=False, _allow_job_files=False):
    from .scene_schema import validate_storyboard
    from .captions import write_captions
    from .sound import build_soundtrack, mix_audio
    from .qc import inspect_video
    from .audio import probe_audio, validate_transcript
    _check_tools()
    if music:
        raise ValueError("Música automática não configurada. O padrão é off; efeitos originais são gerados localmente.")
    profile = PROFILES[quality].copy()
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()) and not _allow_job_files:
        raise FileExistsError(f"Diretório existente preservado: {output}. Use um diretório novo para renderizar outra versão.")
    output.mkdir(parents=True,exist_ok=True)
    target = output / ("video_preview.mp4" if quality == "preview" else "video_final.mp4")
    if transcript is None and (output / "transcript.json").exists():
        transcript = read_json(output / "transcript.json")
    if transcript is None:
        raise ValueError("Render exige transcript.json com tempos reais para gerar legendas e validar sincronização")
    validate_transcript(transcript)
    source_hash = file_hash(audio)
    audio_duration = probe_audio(audio)["duration"]
    validate_storyboard(storyboard,expected_duration=audio_duration)
    if abs(float(transcript["duration"])-audio_duration) > .04:
        raise ValueError("Duração da transcrição difere do áudio fornecido")
    if transcript.get("audio_sha256") and transcript["audio_sha256"] != source_hash:
        raise ValueError("A transcrição pertence a outro áudio; render recusado")
    inputs = {"storyboard":content_hash(storyboard),"transcript":content_hash(transcript),"audio":source_hash,"profile":profile,"captions":captions}
    marker = output / f"render-inputs-{quality}.json"
    if marker.exists() and read_json(marker) != inputs:
        raise ValueError("Entradas do job foram modificadas. Crie outra produção; este diretório foi preservado")
    if target.exists():
        if not (_allow_job_files and marker.exists()):
            raise FileExistsError(f"Vídeo existente preservado: {target}")
        qc = inspect_video(target,transcript=transcript,storyboard=storyboard,output_dir=output/"qc")
        _profile_gate(qc,profile)
        write_json(output/"qc/qc_report.json",qc)
        if not qc.get("technical_gates_passed"):
            raise RuntimeError("QC técnico da retomada falhou. Consulte qc/qc_report.json")
        return {"video":str(target),"quality":quality,"profile":profile,"qc":qc,"resumed_existing_video":True}
    write_json(marker,inputs)
    write_json(output/"storyboard_input.json",storyboard)
    from .preflight import inspect_framing
    event(output,"preflight",message="Medindo atores e objetos em poses animadas; corrigindo enquadramentos simples")
    storyboard,preflight_info=inspect_framing(storyboard,output/"preflight")
    write_json(output / "storyboard.json",storyboard)
    write_json(output / "transcript.json",transcript)
    caption_info = write_captions(transcript,output,width=profile["width"],height=profile["height"],font="Pixelify Sans",
                                  font_path=ROOT/"assets/fonts/PixelifySans.ttf")
    lib = library or Library()
    hashes = lib.remember(storyboard,output)
    tasks = []
    max_jobs = min(max(int(jobs),1),max(1,(os.cpu_count() or 2)//2),4)
    scene_cache = ROOT / ".cache"
    # Scene jobs are deterministic and isolated; on this 3-CPU host default to one.
    with ThreadPoolExecutor(max_workers=max_jobs) as pool:
        futures = {pool.submit(_scene_clip,scene,profile,scene_cache,output/f"render-{i:03d}.log",reuse=reuse_assets):i
                   for i,scene in enumerate(storyboard["scenes"])}
        for future in as_completed(futures):
            clip = future.result()
            tasks.append((futures[future],clip))
            event(output,"render",message=f"{clip['id']} ({'cache' if clip['cached'] else str(clip['seconds'])+'s'})")
    clips = [x[1] for x in sorted(tasks)]
    write_json(output/"scene_cache.json",clips)
    # Paths are generated hashes, with no caller-controlled quote characters.
    (output/"concat.txt").write_text("".join(f"file '{c['path']}'\n" for c in clips),encoding="utf-8")
    raw = output/"animation.mp4"
    run(["ffmpeg","-y","-v","warning","-f","concat","-safe","0","-i",output/"concat.txt",
         "-c","copy","-an",raw],log=output/"assemble.log",timeout=300)
    effects = output/"effects.wav"
    sounds = build_soundtrack(storyboard,float(transcript["duration"]),effects)
    mixed = output/"mixed.wav"
    mix_info = mix_audio(Path(audio).resolve(),effects,mixed,float(transcript["duration"]))
    partial = output/(target.stem+".pending.mp4")
    args = ["ffmpeg","-y","-v","warning","-i",raw,"-i",mixed,"-map","0:v:0","-map","1:a:0"]
    if captions:
        # Font path is a controlled copy: filter text never contains the user filename.
        fontdir = output / "fonts"
        fontdir.mkdir(exist_ok=True)
        for file in (ROOT/"assets/fonts").glob("*.ttf"):
            shutil.copy2(file,fontdir/file.name)
        args.extend(["-vf","ass=legendas.ass:fontsdir=fonts","-c:v","libx264","-preset","fast","-crf",profile["crf"],"-threads","2"])
    else:
        args.extend(["-c:v","copy"])
    args.extend(["-c:a","aac","-b:a","192k","-ar","48000","-pix_fmt","yuv420p",
                 "-t",str(transcript["duration"]),"-movflags","+faststart",partial.name])
    run(args,cwd=output,log=output/"assemble.log",timeout=max(300,float(transcript["duration"])*10))
    event(output,"qc",message="Inspeção de frames, duração e streams")
    qc = inspect_video(partial,transcript=transcript,storyboard=storyboard,output_dir=output/"qc")
    _profile_gate(qc,profile)
    write_json(output/"qc/qc_report.json",qc)
    if not qc.get("technical_gates_passed"):
        raise RuntimeError("QC técnico recusou a exportação. Artefato pendente preservado; consulte qc/qc_report.json")
    partial.replace(target)
    qc["video"]=str(target)
    write_json(output/"qc/qc_report.json",qc)
    return {"video":str(target),"quality":quality,"profile":profile,"scenes":clips,"assets":hashes,
            "captions":caption_info,"sounds":sounds,"mix":mix_info,"qc":qc,"preflight":preflight_info}

def produce(audio, *, quality="final", director="auto", model="large-v3-turbo", output=None,
            resume=None, captions=True, reuse_assets=True, jobs=1, music=False):
    from .audio import analyze
    from .director import generate
    audio = Path(audio).expanduser().resolve()
    if not audio.is_file():
        raise FileNotFoundError(audio)
    _check_tools()
    digest = file_hash(audio)
    if resume:
        job = Path(resume).resolve()
        previous = read_json(job/"production_report.json")
        if previous.get("input_sha256") != digest:
            raise ValueError("O áudio difere do job interrompido; a retomada foi recusada")
        if previous.get("status") == "completed":
            raise ValueError("Job já concluído e preservado. Crie outra produção para nova versão")
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        job = Path(output).resolve() if output else ROOT/"productions"/f"{stamp}-{digest[:8]}-{uuid.uuid4().hex[:6]}"
        if job.exists() and any(job.iterdir()):
            raise FileExistsError(f"Diretório existente preservado: {job}")
        job.mkdir(parents=True,exist_ok=True)
        shutil.copy2(audio,job/("narration"+audio.suffix.lower()))
    started = time.monotonic()
    report = {"version":__version__,"job":str(job),"input":str(audio),"input_sha256":digest,
              "quality":quality,"status":"running","tools":doctor(),"errors":[],"warnings":[]}
    write_json(job/"production_report.json",report)
    try:
        event(job,"transcription",message="Português, áudio original e timestamps por palavra")
        transcript_path = job/"transcript.json"
        if transcript_path.exists():
            transcript = read_json(transcript_path)
        else:
            transcript = analyze(audio,ROOT/".cache"/"audio",model=model,language="pt")
            write_json(transcript_path,transcript)
        if float(transcript["duration"]) < 60:
            warning = "Áudio com menos de 60 segundos: pode não cumprir a duração exigida pelo Programa de Recompensas do TikTok. Narração mantida intacta."
            report["warnings"].append(warning)
            event(job,"notice",message=warning)
        event(job,"direction",message="Gerando cenas a partir da narração transcrita")
        storyboard_path = job/"storyboard_input.json"
        lib = Library()
        if storyboard_path.exists():
            storyboard = read_json(storyboard_path)
        else:
            from .llm_runtime import local_director
            with local_director(director):
                storyboard = generate(transcript,library=lib.list(),backend=director)
            write_json(storyboard_path,storyboard)
        report["director"] = storyboard.get("director",storyboard.get("metadata",{}))
        result = render_storyboard(storyboard,audio,job,quality=quality,captions=captions,
                                   reuse_assets=reuse_assets,jobs=jobs,transcript=transcript,library=lib,music=music,_allow_job_files=True)
        report.update(result)
        report["status"] = "completed"
        report["quality_status"] = result["qc"].get("status","needs_review")
        event(job,"completed",message=result["video"])
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"type":type(exc).__name__,"message":str(exc)})
        event(job,"failed",message=str(exc))
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic()-started,3)
        write_json(job/"production_report.json",report)
    return report
