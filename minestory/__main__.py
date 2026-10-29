"""Command-line interface, with one required input for `produce`."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .util import ROOT, read_json, write_json

def boolean(value):
    return value == "on"

def main(argv=None):
    parser = argparse.ArgumentParser(prog="minestory",description="Narração PT-BR → animação vertical. Sem serviços pagos.")
    sub = parser.add_subparsers(dest="command",required=True)
    p = sub.add_parser("produce",help="Produzir vídeo usando somente áudio")
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
    p = sub.add_parser("prepare",help="Preparar áudio para direção pelo modelo ativo desta conversa")
    p.add_argument("audio",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--model",default="large-v3-turbo")
    p = sub.add_parser("finish",help="Renderizar direção criada pelo Codex nesta conversa")
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
    p = sub.add_parser("plan",help="Gerar storyboard a partir de transcript.json")
    p.add_argument("transcript",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--director",choices=["auto","codex","llama","procedural"],default="auto")
    p = sub.add_parser("validate",help="Validar grafo de cenas")
    p.add_argument("storyboard",type=Path)
    p = sub.add_parser("render",help="Renderizar storyboard sem alterar uma produção existente")
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
    sub.add_parser("launcher",help="Seletor local de áudio (requer ambiente gráfico)")
    p=sub.add_parser("cache",help="Compactar apenas frames de cenas já exportadas e verificadas")
    p.add_argument("action",choices=["compact"])
    p.add_argument("--dry-run",action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "produce":
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
