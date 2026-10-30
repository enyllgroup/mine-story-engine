"""Frame-exact native Mine-imator scene retakes; no renderer substitution."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path


def prepare_region(source: Path, destination: Path, start: int, end_exclusive: int):
    source=source.resolve(strict=True);destination=destination.resolve()
    if source.parent!=destination.parent:
        raise ValueError('Retake project must share its source folder so assets resolve')
    if destination.exists():raise FileExistsError('Retake project already exists')
    doc=json.loads(source.read_text())
    if doc.get('format')!=34 or doc.get('created_in')!='2.0.2':raise ValueError('Expected native Mine-imator 2.0.2 project')
    original=doc['project']['timeline'];lo=original.get('region_start');hi=original.get('region_end')
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (start,end_exclusive,lo,hi)):
        raise ValueError('Frame boundaries must be integers')
    if not lo<=start<end_exclusive<=hi+1:raise ValueError('Retake range must fit in original region')
    result=copy.deepcopy(doc);result['project']['timeline']['region_start']=start
    result['project']['timeline']['region_end']=end_exclusive-1
    with destination.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    return {'project':str(destination),'start_frame':start,'end_frame_exclusive':end_exclusive,
            'frames':end_exclusive-start,'original_preserved':str(source)}


def validate_retakes(manifest:Path, base:dict, probe):
    """Validate silent native clips; frames use an exclusive end boundary."""
    data=json.loads(manifest.read_text()); entries=data.get('retakes')
    if not isinstance(entries,list) or not entries:raise ValueError('Retake manifest needs a nonempty retakes list')
    base_stream=base['stream'];base_frames=int(base_stream.get('nb_frames') or round(base['duration']*base['fps']))
    result=[];last=0
    for entry in entries:
        start=entry.get('start_frame');end=entry.get('end_frame_exclusive')
        if any(not isinstance(x,int) or isinstance(x,bool) for x in (start,end)):
            raise ValueError('Retake frame bounds must be integers')
        if not 0<=start<end<=base_frames or start<last:raise ValueError('Retakes must be ordered, disjoint, and inside the original')
        if not isinstance(entry.get('video'),str) or not isinstance(entry.get('export_report'),str):
            raise ValueError('Retake needs a video and its native export_report')
        file=(manifest.parent/entry['video']).resolve(strict=True);p=probe(file)
        evidence_path=(manifest.parent/entry['export_report']).resolve(strict=True)
        evidence=json.loads(evidence_path.read_text())
        with file.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if (evidence.get('native_export_confirmed') is not True
            or evidence.get('sha256')!=digest
            or Path(evidence.get('output','')).resolve()!=file):
            raise ValueError('Retake requires its matching verified native export report and hash')
        project=Path(evidence.get('project','')).resolve(strict=True)
        region=json.loads(project.read_text())['project']['timeline']
        if region.get('region_start')!=start or region.get('region_end')!=end-1:
            raise ValueError('Retake native project region does not match its intended frame range')
        count=int(p['stream'].get('nb_frames') or round(p['duration']*p['fps']))
        if (p['width'],p['height'])!=(base['width'],base['height']) or abs(p['fps']-base['fps'])>.001:
            raise ValueError('Retake dimensions and frame rate must match the native master')
        if p['stream'].get('codec_name')!='h264' or count!=end-start:
            raise ValueError('Retake must be H.264 with exactly the requested frames')
        if abs(p['duration']-(end-start)/base['fps'])>1/base['fps']+.002:
            raise ValueError('Retake duration does not match the requested frames')
        result.append({'video':str(file),'start_frame':start,'end_frame_exclusive':end,'frames':count,
                       'export_report':str(evidence_path),'sha256':digest})
        last=end
    return result


def filter_graph(base_frames:int,retakes:list,*,captions:bool):
    """Compose already-validated retakes and optional ASS in one final encode."""
    if not retakes:
        return ('[0:v]ass=captions.ass:fontsdir=fonts[vout]' if captions else '[0:v]null[vout]')
    pieces=[];cursor=0
    for i,r in enumerate(retakes):
        if cursor<r['start_frame']:pieces.append(('base',cursor,r['start_frame']))
        pieces.append((i+1,0,r['frames']));cursor=r['end_frame_exclusive']
    if cursor<base_frames:pieces.append(('base',cursor,base_frames))
    base_count=sum(p[0]=='base' for p in pieces);parts=[]
    if base_count>1:parts.append('[0:v]split='+str(base_count)+''.join(f'[base{i}]' for i in range(base_count)))
    pos=0;outs=[]
    for n,(kind,start,end) in enumerate(pieces):
        if kind=='base':
            inp='[0:v]' if base_count==1 else f'[base{pos}]';pos+=1
        else:inp=f'[{kind}:v]'
        out=f'[piece{n}]';outs.append(out)
        parts.append(f'{inp}trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS{out}')
    chain=''.join(outs)+f'concat=n={len(outs)}:v=1:a=0'
    chain+=',ass=captions.ass:fontsdir=fonts[vout]' if captions else '[vout]'
    parts.append(chain)
    return ';'.join(parts)
