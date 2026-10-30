import hashlib,json,subprocess
from fractions import Fraction
import numpy as np
import pytest
from minestory.native_retake import prepare_region,validate_retakes,filter_graph


def probe(path):
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=codec_name,width,height,avg_frame_rate,nb_frames,duration',
        '-of','json',str(path)]))['streams'][0]
    return {'stream':data,'width':data['width'],'height':data['height'],
            'fps':float(Fraction(data['avg_frame_rate'])),'duration':float(data['duration'])}


def create_video(path,color,frames):
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color={color}:s=64x96:r=30',
                    '-frames:v',str(frames),'-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)


def test_region_preserves_source_and_requires_local_assets(tmp_path):
    src=tmp_path/'story.miproject';out=tmp_path/'retake.miproject'
    original={'format':34,'created_in':'2.0.2','project':{'timeline':{'region_start':0,'region_end':89}}}
    src.write_text(json.dumps(original))
    assert prepare_region(src,out,30,60)['frames']==30
    assert json.loads(out.read_text())['project']['timeline']['region_end']==59
    assert json.loads(src.read_text())==original
    with pytest.raises(FileExistsError):prepare_region(src,out,30,60)
    with pytest.raises(ValueError):prepare_region(src,tmp_path/'outside'/'new.miproject',30,60)


def test_retake_replaces_exact_frames_and_rejects_overlap(tmp_path):
    base=tmp_path/'base.mp4';red=tmp_path/'red.mp4';blue=tmp_path/'blue.mp4'
    create_video(base,'black',90);create_video(red,'red',30);create_video(blue,'blue',15)
    for video,start,end in [(red,15,45),(blue,60,75)]:
        project=tmp_path/(video.stem+'.miproject')
        project.write_text(json.dumps({'project':{'timeline':{'region_start':start,'region_end':end-1}}}))
        digest=hashlib.sha256(video.read_bytes()).hexdigest()
        (tmp_path/(video.stem+'.export.json')).write_text(json.dumps({'native_export_confirmed':True,
            'sha256':digest,'output':str(video),'project':str(project)}))
    manifest=tmp_path/'retakes.json';manifest.write_text(json.dumps({'retakes':[
        {'video':'red.mp4','export_report':'red.export.json','start_frame':15,'end_frame_exclusive':45},
        {'video':'blue.mp4','export_report':'blue.export.json','start_frame':60,'end_frame_exclusive':75}]}))
    retakes=validate_retakes(manifest,probe(base),probe)
    output=tmp_path/'merged.mp4';graph=filter_graph(90,retakes,captions=False)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(base),'-i',str(red),'-i',str(blue),
        '-filter_complex',graph,'-map','[vout]','-c:v','libx264','-pix_fmt','yuv420p',str(output)],check=True)
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-pix_fmt','rgb24','-f','rawvideo','-'])
    frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,96,64,3)
    assert len(frames)==90
    means=frames.mean(axis=(1,2))
    assert means[14].max()<15 and means[15,0]>200 and means[44,0]>200 and means[45].max()<15
    assert means[59].max()<15 and means[60,2]>200 and means[74,2]>200 and means[75].max()<15
    evidence_path=tmp_path/'red.export.json';saved=evidence_path.read_text()
    invalid_report=json.loads(saved);invalid_report['sha256']='0'*64
    evidence_path.write_text(json.dumps(invalid_report))
    with pytest.raises(ValueError,match='hash'):validate_retakes(manifest,probe(base),probe)
    evidence_path.write_text(saved)
    invalid=json.loads(manifest.read_text());invalid['retakes'][1]['start_frame']=40
    manifest.write_text(json.dumps(invalid))
    with pytest.raises(ValueError,match='disjoint'):validate_retakes(manifest,probe(base),probe)
