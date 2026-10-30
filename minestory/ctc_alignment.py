"""Optional local CTC alignment of an existing transcript to its original audio.

The model is an Apache-2.0 quantized ONNX export of Portuguese Wav2Vec2.
This aligns supplied words; it cannot establish whether those words were spoken.
Unsupported text and low-confidence segments retain their original timestamps.
"""
from __future__ import annotations
import copy
import math
import re
import subprocess
from pathlib import Path
import numpy as np

MODEL_ID = 'onnx-community/wav2vec2-large-xlsr-53-portuguese-ONNX'
MODEL_REVISION = '6f425223d83cd1ad134c007798c47f2e122744fd'
DIGITS = ('zero','um','dois','três','quatro','cinco','seis','sete','oito','nove')


def audio_16k(path: Path) -> np.ndarray:
    proc = subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(path),'-ac','1',
        '-ar','16000','-f','f32le','pipe:1'],capture_output=True,check=True)
    data=np.frombuffer(proc.stdout,dtype='<f4').copy()
    if not len(data) or not np.all(np.isfinite(data)):
        raise ValueError('Empty or invalid audio')
    return data


def make_labels(words, vocabulary):
    labels=[];owners=[]
    for index,word in enumerate(words):
        cleaned=word.lower().strip()
        cleaned=re.sub(r'^[^\w]+|[^\w]+$', '', cleaned,flags=re.UNICODE)
        if cleaned.isdecimal() and len(cleaned)==1: cleaned=DIGITS[int(cleaned)]
        if not cleaned or any(ch not in vocabulary for ch in cleaned):
            raise ValueError(f'Unsupported word for CTC alignment: {word!r}')
        if index:
            labels.append(vocabulary['|']);owners.append(None)
        labels.extend(vocabulary[ch] for ch in cleaned)
        owners.extend([index]*len(cleaned))
    return labels,owners


def ctc_viterbi(logits, labels, blank=0):
    """Return frame ranges and mean posterior for a forced label path."""
    if logits.ndim!=2 or not labels or any(not 0<=i<logits.shape[1] for i in labels):
        raise ValueError('Invalid CTC labels or logits')
    frames=logits.shape[0]; states=np.empty(len(labels)*2+1,dtype=np.int64)
    states[::2]=blank;states[1::2]=labels
    if frames < len(labels):raise ValueError('Too few frames for supplied text')
    raw=logits.astype(np.float64);mx=raw.max(axis=1,keepdims=True)
    logp=raw-mx-np.log(np.exp(raw-mx).sum(axis=1,keepdims=True))
    prev=np.full(len(states),-np.inf);prev[0]=logp[0,blank];prev[1]=logp[0,states[1]]
    back=np.zeros((frames,len(states)),dtype=np.uint8)
    allow_skip=np.zeros(len(states),dtype=bool)
    allow_skip[2:]=(states[2:]!=blank)&(states[2:]!=states[:-2])
    for t in range(1,frames):
        advance=np.r_[-np.inf,prev[:-1]]
        skip=np.r_[[-np.inf,-np.inf],prev[:-2]]
        skip[~allow_skip]=-np.inf
        options=np.stack((prev,advance,skip));best=np.argmax(options,axis=0)
        prev=options[best,np.arange(len(states))]+logp[t,states]
        back[t]=best
    state=len(states)-1 if prev[-1]>=prev[-2] else len(states)-2
    if not np.isfinite(prev[state]):raise ValueError('No CTC path for supplied text')
    path=np.empty(frames,dtype=np.int64)
    for t in range(frames-1,-1,-1):
        path[t]=state
        if t:state-=int(back[t,state])
    spans=[]
    for index,label in enumerate(labels):
        positions=np.flatnonzero(path==2*index+1)
        if not len(positions):raise ValueError('CTC omitted a supplied character')
        confidence=float(np.exp(logp[positions,label]).mean())
        spans.append((int(positions[0]),int(positions[-1])+1,confidence))
    return spans


def align_transcript(transcript, waveform, session, vocabulary, *, min_confidence=.08):
    """Align segments independently; retain Whisper times on a rejected segment."""
    out=copy.deepcopy(transcript);words=out['words'];segments=out['segments']
    assignments=[[] for _ in segments]
    for index,w in enumerate(words):
        midpoint=(w['start']+w['end'])/2
        candidates=[i for i,s in enumerate(segments) if s['start']-.02<=midpoint<=s['end']+.02]
        if len(candidates)!=1: raise ValueError(f'Word {index} does not belong to exactly one ASR segment')
        assignments[candidates[0]].append(index)
    reports=[];accepted=0
    for seg_index,(segment,indices) in enumerate(zip(segments,assignments)):
        if not indices:continue
        clip_start=max(0.0,segment['start']-.12)
        clip_end=min(len(waveform)/16000,segment['end']+.12)
        audio=waveform[round(clip_start*16000):round(clip_end*16000)].astype(np.float32)
        try:
            labels,owners=make_labels([words[i]['word'] for i in indices],vocabulary)
            if len(audio)<800:raise ValueError('Segment too short')
            audio=(audio-audio.mean())/np.sqrt(audio.var()+1e-7)
            logits=session.run(None,{'input_values':audio[None]})[0][0]
            spans=ctc_viterbi(logits,labels,blank=vocabulary['<pad>'])
            results=[]
            for local,idx in enumerate(indices):
                owned=[span for span,owner in zip(spans,owners) if owner==local]
                if not owned:raise ValueError('Word has no aligned characters')
                confidence=float(np.mean([span[2] for span in owned]))
                start=clip_start+owned[0][0]*.02+.0125
                end=clip_start+owned[-1][1]*.02+.0125
                results.append((idx,max(0,start),min(out['duration'],end),confidence))
            if min(r[3] for r in results)<min_confidence:raise ValueError('Low CTC confidence')
            if any(a>=b or b-a>3 for _,a,b,_ in results):raise ValueError('Implausible word duration')
            if any(results[i][2]>results[i+1][1]+.03 for i in range(len(results)-1)):
                raise ValueError('Overlapping aligned words')
            for idx,start,end,confidence in results:
                words[idx]['whisper_start']=words[idx]['start'];words[idx]['whisper_end']=words[idx]['end']
                words[idx]['start']=round(start,4);words[idx]['end']=round(end,4)
                words[idx]['alignment_confidence']=round(confidence,4)
                words[idx]['alignment_method']='ctc-wav2vec2-onnx'
            accepted+=len(results)
            reports.append({'segment':seg_index,'status':'aligned','words':len(results),
                            'min_confidence':round(min(r[3] for r in results),4)})
        except (ValueError,RuntimeError) as error:
            reports.append({'segment':seg_index,'status':'fallback_whisper','reason':str(error),'words':len(indices)})
    out['transcription']['forced_alignment'] = accepted==len(words)
    out['transcription']['forced_alignment_partial'] = 0<accepted<len(words)
    out['transcription']['alignment_model'] = MODEL_ID
    out['transcription']['alignment_revision'] = MODEL_REVISION
    out['transcription']['alignment_note'] = 'CTC aligns the supplied transcript; it does not verify word identity.'
    return out,{'words':len(words),'aligned_words':accepted,'segments':reports,
                'model':MODEL_ID,'revision':MODEL_REVISION,'license':'Apache-2.0',
                'audio_retimed':False,'spoken_word_identity_verified':False}
