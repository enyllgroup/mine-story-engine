"""Native Mine-imator stages and explicitly opted-in legacy diagnostics."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from .util import ROOT, read_json, write_json

LEGACY_VISUAL_COMMANDS = {"produce", "prepare", "finish", "render", "launcher"}
NATIVE_SCRIPTS = {
    "narration": "analyze_native_narration.py",
    "align": "align_native_narration.py",
    "retake": "prepare_native_retake.py",
    "character": "build_native_character.py",
    "sound": "native_sound_design.py",
    "project": "create_mineimator_test_project.py",
    "gui": "mineimator_gui.py",
    "export": "export_mineimator.py",
    "finish": "finish_mineimator.py",
}

def boolean(value):
    return value == "on"

def main(argv=None):
    parser = argparse.ArgumentParser(prog="minestory",description="Etapas Mine-imator nativas. Direção pelo Codex nesta conversa, sem API paga; integração áudio → vídeo em andamento.")
    parser.add_argument("--legacy-blender", action="store_true",
                        help="Habilitar somente diagnóstico explicitamente autorizado do pipeline Blender legado")
    sub = parser.add_subparsers(dest="command",required=True)
    p = sub.add_parser("produce",help="LEGADO Blender: diagnóstico a partir de áudio; exige --legacy-blender")
    p.add_argument("audio",type=Path)
    p.add_argument("--quality",choices=["preview","final"],default="final")
    p.add_argument("--director",choices=["auto","session","codex","llama","procedural"],default="auto")
    p.add_argument("--model",default="large-v3-turbo",help="Modelo Whisper local; large-v3-turbo é o padrão")
    p.add_argument("--captions",choices=["on","off"],default="on")
    p.add_argument("--music",choices=["on","off"],default="off")
    p.add_argument("--reuse-assets",choices=["on","off"],default="on")
    p.add_argument("--output",type=Path)
    p.add_argument("--resume",type=Path)
    p.add_argument("--jobs",type=int,default=1)
    p = sub.add_parser("prepare",help="LEGADO Blender: preparar pacote de direção; exige --legacy-blender")
    p.add_argument("audio",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--model",default="large-v3-turbo")
    p = sub.add_parser("finish",help="LEGADO Blender: renderizar direção; exige --legacy-blender")
    p.add_argument("job",type=Path)
    p.add_argument("--plan",type=Path)
    p.add_argument("--quality",choices=["preview","final"],default="preview")
    p.add_argument("--jobs",type=int,default=1)
    p.add_argument("--captions",choices=["on","off"],default="on")
    p = sub.add_parser("version",help="Criar outra versão de sessão preservando a anterior")
    p.add_argument("job",type=Path)
    p.add_argument("--output",type=Path)
    sub.add_parser("doctor",help="Diagnóstico de ferramentas e hardware")
    p = sub.add_parser("analyze",help="Transcrever narração e estimar tempos de palavras")
    p.add_argument("audio",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--model",default="large-v3-turbo")
    p = sub.add_parser("plan",help="Gerar storyboard no schema legado a partir de transcript.json")
    p.add_argument("transcript",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--director",choices=["auto","codex","llama","procedural"],default="auto")
    p = sub.add_parser("validate",help="Validar grafo de cenas")
    p.add_argument("storyboard",type=Path)
    p = sub.add_parser("render",help="LEGADO Blender: renderizar storyboard; exige --legacy-blender")
    p.add_argument("storyboard",type=Path)
    p.add_argument("--audio",type=Path,required=True)
    p.add_argument("--transcript",type=Path)
    p.add_argument("--quality",choices=["preview","final"],default="preview")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--jobs",type=int,default=1)
    p.add_argument("--captions",choices=["on","off"],default="on")
    p = sub.add_parser("qc",help="Inspecionar vídeo existente")
    p.add_argument("video",type=Path)
    p.add_argument("--storyboard",type=Path)
    p.add_argument("--transcript",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p = sub.add_parser("assets",help="Biblioteca persistente com hashes")
    ap = p.add_subparsers(dest="action",required=True)
    ap.add_parser("list")
    add = ap.add_parser("add")
    add.add_argument("path",type=Path)
    add.add_argument("--kind",default="custom")
    add.add_argument("--license",default="user-provided")
    sub.add_parser("launcher",help="LEGADO Blender: seletor de diagnóstico; exige --legacy-blender")
    p=sub.add_parser("cache",help="Compactar apenas frames de cenas já exportadas e verificadas")
    p.add_argument("action",choices=["compact"])
    p.add_argument("--dry-run",action="store_true")
    native = sub.add_parser("native",help="Executar uma etapa real Mine-imator: project, gui, export ou finish")
    native.add_argument("action", choices=sorted(NATIVE_SCRIPTS))
    native.add_argument("arguments", nargs=argparse.REMAINDER,
                        help="Argumentos da etapa, encaminhados sem shell; use ETAPA --help")
    # Accept the explicit diagnostic opt-in both before and after the command.
    # SUPPRESS preserves a global True when no subcommand-local flag is given.
    for command in LEGACY_VISUAL_COMMANDS:
        sub.choices[command].add_argument(
            "--legacy-blender", action="store_true", default=argparse.SUPPRESS,
            help="Executar somente o diagnóstico Blender legado explicitamente autorizado",
        )
    args = parser.parse_args(argv)
    if args.command in LEGACY_VISUAL_COMMANDS and not args.legacy_blender:
        print(
            f"MineStory: '{args.command}' pertence ao pipeline Blender legado e foi bloqueado. "
            "A rota atual é Mine-imator; envie a narração nesta conversa do Codex. "
            "Para transcrição isolada, use 'analyze AUDIO --output DIRETORIO'; "
            "para as etapas nativas, use 'native --help' e a skill mineimator-native. "
            "A integração completa áudio → Mine-imator ainda está em andamento. "
            "--legacy-blender habilita apenas diagnóstico legado explicitamente autorizado.",
            file=sys.stderr,
        )
        return 2
    try:
        if args.command == "native":
            script = ROOT / "scripts" / NATIVE_SCRIPTS[args.action]
            if not script.is_file():
                raise RuntimeError(f"Etapa nativa ainda indisponível: {args.action}. Integração em andamento; nenhum renderer substituto foi acionado.")
            print(
                "MineStory: etapa Mine-imator nativa. A direção usa o Codex nesta conversa, "
                "sem API paga. O fluxo completo a partir de áudio ainda está em integração.",
                file=sys.stderr,
            )
            return subprocess.run([sys.executable, str(script), *args.arguments], cwd=ROOT).returncode
        elif args.command == "produce":
            if args.director == "session":
                from .session import prepare
                result = prepare(args.audio,output=args.output,model=args.model)
                print(json.dumps(result,ensure_ascii=False,indent=2))
                return 0
            from .pipeline import produce
            result = produce(args.audio,quality=args.quality,director=args.director,model=args.model,
                             captions=boolean(args.captions),music=boolean(args.music),reuse_assets=boolean(args.reuse_assets),
                             output=args.output,resume=args.resume,jobs=args.jobs)
            print(json.dumps({"status":result["status"],"video":result["video"],"report":str(Path(result["job"])/"production_report.json")},ensure_ascii=False,indent=2))
        elif args.command == "prepare":
            from .session import prepare
            result = prepare(args.audio,output=args.output,model=args.model)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        elif args.command == "finish":
            from .session import finish
            result = finish(args.job,plan=args.plan,quality=args.quality,jobs=args.jobs,captions=boolean(args.captions))
            print(json.dumps({"video":result["video"],"quality_status":result["quality_status"]},ensure_ascii=False,indent=2))
        elif args.command == "version":
            from .session import new_version
            print(json.dumps(new_version(args.job,output=args.output),ensure_ascii=False,indent=2))
        elif args.command == "doctor":
            from .pipeline import doctor
            print(json.dumps(doctor(),ensure_ascii=False,indent=2))
        elif args.command == "analyze":
            from .audio import analyze
            result = analyze(args.audio,ROOT/".cache/audio",model=args.model,language="pt")
            destination = args.output if args.output.suffix == ".json" else args.output/"transcript.json"
            write_json(destination,result)
            print(destination)
        elif args.command == "plan":
            from .director import generate
            from .library import Library
            if args.output.exists():
                raise FileExistsError(f"Storyboard existente preservado: {args.output}")
            from .llm_runtime import local_director
            with local_director(args.director):
                result = generate(read_json(args.transcript),library=Library().list(),backend=args.director)
            write_json(args.output,result)
            print(args.output)
        elif args.command == "validate":
            from .scene_schema import validate_storyboard
            result = validate_storyboard(read_json(args.storyboard))
            print(json.dumps({"valid":True,"details":result},ensure_ascii=False,default=str))
        elif args.command == "render":
            from .pipeline import render_storyboard
            source = args.transcript or args.storyboard.parent/"transcript.json"
            result = render_storyboard(read_json(args.storyboard),args.audio,args.output,quality=args.quality,
                                      jobs=args.jobs,captions=boolean(args.captions),transcript=read_json(source))
            write_json(args.output/"render_report.json",result)
            print(result["video"])
        elif args.command == "qc":
            from .qc import inspect_video
            result = inspect_video(args.video,transcript=read_json(args.transcript) if args.transcript else None,
                                   storyboard=read_json(args.storyboard) if args.storyboard else None,output_dir=args.output)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        elif args.command == "assets":
            from .library import Library
            library = Library()
            result = library.list() if args.action == "list" else library.add(args.path,kind=args.kind,license=args.license)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        elif args.command == "launcher":
            from .launcher import launch
            launch()
        elif args.command == "cache":
            from .cache import compact_cache
            print(json.dumps(compact_cache(dry_run=args.dry_run),ensure_ascii=False,indent=2))
        return 0
    except KeyboardInterrupt:
        print("Interrompido. Os frames e caches concluídos foram preservados para --resume.",file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"MineStory: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
