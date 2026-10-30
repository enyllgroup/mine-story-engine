#!/usr/bin/env python3
"""Package an authored native project and its job-local assets without overwrites.

Does not download or bundle an installed Minecraft texture pack, application,
permanent library, authentication material, or unrelated production files.
Source rights remain the author's responsibility. This project packages only
its original models/textures, personal narration and derived narrated SFX mix.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def contained(root: Path, relative: str) -> Path:
    path=(root/relative).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Project resource escapes its production directory')
    return path


def package(job: Path, project: Path, output: Path) -> dict:
    job=job.resolve(strict=True);project=project.resolve(strict=True)
    if not project.is_relative_to(job):raise ValueError('Native project must belong to the supplied job')
    if output.exists():raise FileExistsError('Existing downloadable project preserved')
    doc=json.loads(project.read_text())
    if doc.get('format')!=34:raise ValueError('Only the authored native format34 is supported')
    files={project}
    for resource in doc.get('resources',[]):
        resource_file=contained(project.parent,resource['filename'])
        files.add(resource_file)
        if resource.get('type')=='model':
            model=json.loads(resource_file.read_text())
            texture=model.get('texture')
            if isinstance(texture,str) and texture.lower().endswith('.png'):
                files.add(contained(project.parent,texture))
    for name in ('storyboard.json','storyboard.md','legendas.srt','legendas.ass','transcript.json',
                 'narration_manifest.json','sound_cues.json','audio_mix.sound.json'):
        if (job/name).is_file():files.add(job/name)
    if (job/'input/narracao.wav').is_file():files.add(job/'input/narracao.wav')
    for path in files:
        if not path.is_relative_to(job):raise ValueError('A packaged file is outside the production')
        if path.suffix.lower()=='.ogg':
            raise ValueError('Standalone source OGG assets are not included; package the narrated derived mix')
    manifest={'schema':1,'entrypoint':project.relative_to(job).as_posix(),
        'files':{path.relative_to(job).as_posix():{'bytes':path.stat().st_size,
            'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest()} for path in sorted(files)},
        'native_validation':'Consult the production report; packaging does not prove GUI execution',
        'minecraft_resources':'Vanilla blocks/textures are supplied by a legitimate local Mine-imator installation, not bundled',
        'privacy':'Contains a personal character and user narration; retain the intended private audience',
        'audio_rights':'Minecraft sounds remain Mojang/Microsoft property under Usage Guidelines. Only the derived narrated mix is bundled; original scientific effects are MineStory CC0.',
        'minecraft_guidelines':'https://www.minecraft.net/en-us/usage-guidelines'}
    readme=('MineStory — projeto nativo editável\n\n'
        'Extraia o ZIP inteiro para uma pasta própria e abra '+manifest['entrypoint']+' no Mine-imator2.0.2.\n'
        'Mantenha a pasta assets junto ao projeto. Modelos, texturas originais e o mix de narração/efeitos estão incluídos.\n'
        'Os recursos vanilla vêm da instalação legítima do Mine-imator e não estão redistribuídos neste pacote.\n'
        'O personagem é uma versão para avaliação; a produção pode ser um rascunho. Consulte storyboard.md.\n'
        'A narração original fica em input/narracao.wav. A timeline nativa usa a mixagem derivada; não aplique ambos simultaneamente.\n'
        'Não redistribua os efeitos Minecraft isoladamente. Mantenha o acesso privado aos recursos pessoais.\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):archive.write(path,path.relative_to(job).as_posix())
        archive.writestr('MINESTORY_BUNDLE.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        archive.writestr('LEIA-ME.txt',readme)
    with zipfile.ZipFile(output) as archive:
        damaged=archive.testzip()
        if damaged:raise ValueError('ZIP validation failed: '+damaged)
    return {'archive':str(output.resolve()),'bytes':output.stat().st_size,'entrypoint':manifest['entrypoint'],
        'files':len(files)+2,'sha256':hashlib.file_digest(output.open('rb'),'sha256').hexdigest()}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job',type=Path,required=True)
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();print(json.dumps(package(args.job,args.project,args.output),ensure_ascii=False,indent=2))
