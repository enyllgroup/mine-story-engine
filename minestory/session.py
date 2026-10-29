"""Direction by the active Codex conversation, without a nested LLM API call.

The user supplies only audio. Codex runs prepare, reads the packet, creates the
visual plan as data and runs finish. Both phases are automated by the skill.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import time
import uuid
import shutil
from . import __version__
from .audio import analyze
from .director import compile_plan, direction_prompt, split_beats
from .scene_schema import MODEL_PLAN_SCHEMA
from .library import Library
from .util import ROOT, content_hash, event, file_hash, read_json, write_json

def prepare(audio, output=None, model="large-v3-turbo"):
    audio = Path(audio).expanduser().resolve()
    digest = file_hash(audio)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job = Path(output).resolve() if output else ROOT/"productions"/f"{stamp}-{digest[:8]}-{uuid.uuid4().hex[:6]}"
    if job.exists() and any(job.iterdir()):
        raise FileExistsError(f"Produção existente preservada: {job}")
    job.mkdir(parents=True,exist_ok=True)
    archived=job/("narration"+audio.suffix.lower())
    shutil.copy2(audio,archived)
    started = time.monotonic()
    event(job,"transcription",message="Preparando direção pelo Codex desta conversa")
    write_json(job/"production_report.json",{"version":__version__,"status":"transcribing","job":str(job),"input":str(audio),"input_sha256":digest,"errors":[]})
    try:
        transcript = analyze(audio,ROOT/".cache/audio",model=model,language="pt")
    except Exception as exc:
        write_json(job/"production_report.json",{"version":__version__,"status":"failed","job":str(job),"input":str(audio),"input_sha256":digest,
                                                "errors":[{"type":type(exc).__name__,"message":str(exc)}]})
        raise
    write_json(job/"transcript.json",transcript)
    beats = split_beats(transcript)
    library = Library().list()
    packet = {"version":__version__,"workflow":"codex-session","audio":str(audio),"input_sha256":digest,
              "transcript_sha256":content_hash(transcript),"beats":beats,"library":library,
              "plan_schema":MODEL_PLAN_SCHEMA,
              "instruction":"O modelo ativo da conversa deve criar direction_plan.json para estes beats, usando o significado da narração. O usuário não precisa escrever nem fornecer esse arquivo. Depois execute finish. Não chamar API paga, não substituir a fala nem alegar validação de algo não renderizado."}
    write_json(job/"director_request.json",packet)
    (job/"director_brief.txt").write_text(direction_prompt(transcript,beats,library),encoding="utf-8")
    report = {"version":__version__,"status":"awaiting_session_direction","job":str(job),"input":str(audio),
              "input_sha256":digest,"archived_input":str(archived),"transcript_sha256":content_hash(transcript),
              "director":{"backend":"codex-session","generative":True,"model":"active conversation; no separate API"},
              "errors":[],"warnings":transcript.get("warnings",[]),"prepare_seconds":round(time.monotonic()-started,3)}
    write_json(job/"production_report.json",report)
    event(job,"awaiting_session_direction",message=str(job/"director_request.json"))
    return report

def finish(job, plan=None, quality="preview", jobs=1, captions=True):
    from .pipeline import render_storyboard,doctor
    job=Path(job).resolve()
    report=read_json(job/"production_report.json")
    if report.get("status")=="completed":
        raise FileExistsError("Produção concluída preservada. Crie uma nova versão em outro diretório")
    audio=Path(report["input"])
    if not audio.exists() and report.get("archived_input"):
        audio=Path(report["archived_input"])
    if file_hash(audio)!=report["input_sha256"]:
        raise ValueError("Áudio modificado depois da transcrição")
    transcript=read_json(job/"transcript.json")
    if content_hash(transcript)!=report["transcript_sha256"]:
        raise ValueError("Transcrição modificada depois da preparação; crie outro job")
    plan_path=Path(plan) if plan else job/"direction_plan.json"
    started=time.monotonic()
    try:
        direction=read_json(plan_path)
        storyboard=compile_plan(direction,split_beats(transcript),float(transcript["duration"]),"codex-session")
        storyboard["director"]["evidence"]={"plan_sha256":content_hash(direction),"input_sha256":report["input_sha256"],
                                           "mode":"Plan authored by the active Codex conversation; no nested inference or API charge"}
        report.update(status="running",quality=quality,tools=doctor(),director=storyboard["director"])
        write_json(job/"production_report.json",report)
        result=render_storyboard(storyboard,audio,job,quality=quality,jobs=jobs,captions=captions,
                                transcript=transcript,_allow_job_files=True)
        report.update(result,status="completed",quality_status=result["qc"].get("status","needs_review"))
        event(job,"completed",message=result["video"])
    except Exception as exc:
        report["status"]="failed"
        report.setdefault("errors",[]).append({"type":type(exc).__name__,"message":str(exc)})
        event(job,"failed",message=str(exc))
        raise
    finally:
        report["finish_seconds"]=round(time.monotonic()-started,3)
        write_json(job/"production_report.json",report)
    return report

def new_version(job,output=None):
    """Create a new immutable production version, reusing the reviewed direction."""
    source=Path(job).resolve()
    previous=read_json(source/"production_report.json")
    transcript=read_json(source/"transcript.json")
    audio=Path(previous["input"])
    if not audio.exists() and previous.get("archived_input"):
        audio=Path(previous["archived_input"])
    if file_hash(audio)!=previous["input_sha256"]:
        raise ValueError("Áudio original modificado; não é possível versionar este job")
    plan=source/"direction_plan.json"
    if not plan.exists():
        raise FileNotFoundError("Versionamento de sessão requer direction_plan.json criado pelo Codex")
    result=prepare(audio,output=output,model=transcript["transcription"].get("model","large-v3-turbo"))
    destination=Path(result["job"])
    shutil.copy2(plan,destination/"direction_plan.json")
    result["parent_job"]=str(source)
    write_json(destination/"production_report.json",result)
    return result
