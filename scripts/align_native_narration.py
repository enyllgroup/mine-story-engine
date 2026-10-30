#!/usr/bin/env python3
"""Align an existing private transcription locally; never overwrite a job."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from minestory.audio import validate_transcript
from minestory.captions import write_captions
from minestory.ctc_alignment import MODEL_ID,MODEL_REVISION,audio_16k,align_transcript

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio',required=True,type=Path);p.add_argument('--transcript',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--model-dir',type=Path)
    p.add_argument('--threads',type=int,choices=[1,2],default=1)
    a=p.parse_args();source=a.audio.resolve(strict=True);transcript=json.loads(a.transcript.read_text())
    validate_transcript(transcript)
    with source.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=transcript.get('audio_sha256'):raise ValueError('Original narration hash does not match transcript')
    if a.output.exists():raise FileExistsError('Output already exists; choose a new version')
    if a.model_dir is None:
        from huggingface_hub import snapshot_download
        model=Path(snapshot_download(MODEL_ID,revision=MODEL_REVISION,
            allow_patterns=['onnx/model_q4.onnx','vocab.json','preprocessor_config.json','config.json','README.md'],
            cache_dir=str(ROOT/'library/cache/models')))
    else:model=a.model_dir.resolve(strict=True)
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=a.threads;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(model/'onnx/model_q4.onnx'),options,providers=['CPUExecutionProvider'])
    vocab=json.loads((model/'vocab.json').read_text())
    aligned,report=align_transcript(transcript,audio_16k(source),session,vocab)
    validate_transcript(aligned)
    a.output.mkdir(parents=True,exist_ok=False)
    with (a.output/'transcript.json').open('x') as f:json.dump(aligned,f,ensure_ascii=False,indent=2);f.write('\n')
    with (a.output/'alignment_report.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    caption=write_captions(aligned,a.output,font_path=ROOT/'assets/fonts/PixelifySans.ttf')
    with (a.output/'caption_report.json').open('x') as f:json.dump(caption,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'output':str(a.output),'aligned_words':report['aligned_words'],'words':report['words'],
                      'complete':aligned['transcription']['forced_alignment']},ensure_ascii=False))

if __name__=='__main__':main()
