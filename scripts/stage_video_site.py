#!/usr/bin/env python3
"""Stage one private Site video without lowering quality to meet asset limits.

For files larger than an individual Site asset, parts are reassembled in the
visitor's browser into one byte-identical MP4. No second video is created.
"""
from __future__ import annotations
import argparse,hashlib,json,math,subprocess
from pathlib import Path


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def stage(source:Path,destination:Path,chunk_bytes=20*1024*1024):
    source=source.resolve(strict=True);destination=destination.resolve()
    if destination.exists():raise FileExistsError('Site staging directory already exists')
    if source.suffix.lower()!='.mp4' or chunk_bytes<1024:raise ValueError('Expected MP4 and a valid chunk size')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'stream=codec_type,codec_name:format=duration','-of','json',str(source)]))
    codecs={(s.get('codec_type'),s.get('codec_name')) for s in probe.get('streams',[])}
    if ('video','h264') not in codecs or ('audio','aac') not in codecs:
        raise ValueError('Expected an MP4 with H.264 video and AAC audio')
    duration=float(probe['format']['duration'])
    if not math.isfinite(duration) or duration<=0:raise ValueError('Invalid video duration')
    size=source.stat().st_size
    if not size:raise ValueError('Empty video')
    destination.mkdir(parents=True,exist_ok=False)
    chunks=[];actual=hashlib.sha256()
    with source.open('rb') as inp:
        if size<=chunk_bytes:
            name='video.mp4'
            with (destination/name).open('xb') as out:
                while data:=inp.read(1024*1024):actual.update(data);out.write(data)
            chunks=[{'path':name,'bytes':size}]
        else:
            index=1
            while True:
                data=inp.read(chunk_bytes)
                if not data:break
                name=f'video.part{index:03}.bin'
                with (destination/name).open('xb') as out:out.write(data)
                actual.update(data);chunks.append({'path':name,'bytes':len(data)});index+=1
    if actual.hexdigest()!=digest(source):raise RuntimeError('Staged MP4 checksum differs from original')
    chunks_json=json.dumps(chunks,separators=(',',':'))
    if len(chunks)==1:
        media='<video controls playsinline preload="metadata" src="video.mp4"></video><br><a href="video.mp4" download="video_final.mp4">Baixar vídeo</a>'
        script=''
    else:
        media='<p id="status" role="status">Carregando vídeo…</p><video id="video" controls playsinline hidden></video><br><a id="download" download="video_final.mp4" hidden>Baixar vídeo</a><button id="retry" hidden>Tentar novamente</button>'
        script='''<script>
const parts=CHUNKS;const status=document.getElementById('status');const player=document.getElementById('video');const download=document.getElementById('download');const retry=document.getElementById('retry');let objectUrl;
async function loadVideo(){retry.hidden=true;player.hidden=true;download.hidden=true;status.textContent='Carregando vídeo…';try{const buffers=[];for(let i=0;i<parts.length;i++){const response=await fetch(parts[i].path);if(!response.ok)throw Error('download');const data=await response.arrayBuffer();if(data.byteLength!==parts[i].bytes)throw Error('incomplete');buffers.push(data);status.textContent='Carregando vídeo… '+Math.round((i+1)/parts.length*100)+'%';}if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(new Blob(buffers,{type:'video/mp4'}));player.src=objectUrl;download.href=objectUrl;player.hidden=false;download.hidden=false;status.textContent='';}catch(error){status.textContent='Não foi possível carregar o vídeo.';retry.hidden=false;}}
retry.addEventListener('click',loadVideo);loadVideo();
</script>'''.replace('CHUNKS',chunks_json)
    html='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MineStory — vídeo</title><style>body{margin:0;background:#101923;color:#f4f7f3;font:16px system-ui,sans-serif}main{max-width:440px;margin:0 auto;padding:32px 20px;text-align:center}h1{font-size:1.5rem}p{color:#c0cec2;line-height:1.5}video{width:100%;max-height:70vh;background:#050807;border-radius:10px}a,button{display:inline-block;margin:20px auto;padding:12px 20px;border:0;border-radius:8px;background:#87b95e;color:#101923;text-decoration:none;font:700 1rem system-ui,sans-serif;cursor:pointer}[hidden]{display:none}</style></head><body><main><h1>Seu vídeo</h1>MEDIA</main>SCRIPT</body></html>'''.replace('MEDIA',media).replace('SCRIPT',script)
    (destination/'index.html').write_text(html,encoding='utf8')
    return {'source_sha256':actual.hexdigest(),'bytes':size,'parts':len(chunks),
            'max_part_bytes':max(c['bytes'] for c in chunks),'duration':duration,'destination':str(destination)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--chunk-mib',type=float,default=20)
    a=p.parse_args()
    if not math.isfinite(a.chunk_mib) or not 1<=a.chunk_mib<=24:raise ValueError('Chunk size must be 1–24 MiB')
    print(json.dumps(stage(a.video,a.output,int(a.chunk_mib*1024*1024)),indent=2))

if __name__=='__main__':main()
