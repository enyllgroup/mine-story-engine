import importlib.util,shutil,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage_video_site',ROOT/'scripts/stage_video_site.py')
site=importlib.util.module_from_spec(spec);spec.loader.exec_module(site)


def test_one_video_is_reassembled_byte_for_byte_without_reencoding(tmp_path):
    video=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=64x96:r=30:d=0.2',
                    '-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','0.2',
                    '-c:v','libx264','-c:a','aac','-pix_fmt','yuv420p',str(video)],check=True)
    # Padding is used only to exercise the chunk boundary; ffprobe still opens it.
    with video.open('ab') as f:f.write(b'\x00'*(1024*1024+17))
    dest=tmp_path/'dist';report=site.stage(video,dest,1024*1024)
    parts=sorted(dest.glob('video.part*.bin'))
    assert report['parts']==2 and b''.join(p.read_bytes() for p in parts)==video.read_bytes()
    html=(dest/'index.html').read_text()
    assert html.count('<video ')==1 and 'Baixar vídeo' in html and 'new Blob(buffers' in html
    if shutil.which('node'):
        # Execute the actual client script with a minimal same-origin fetch stub.
        runner=tmp_path/'run-client.cjs'
        runner.write_text('''const fs=require("fs"),vm=require("vm"),path=require("path");
const root=process.argv[2],original=process.argv[3],html=fs.readFileSync(path.join(root,"index.html"),"utf8");
const script=html.match(/<script>([\\s\\S]*?)<\\/script>/)[1];let result;
const nodes={status:{},video:{},download:{},retry:{addEventListener(){}}};
const ctx={Blob,document:{getElementById:id=>nodes[id]},URL:{createObjectURL:b=>(result=b,"blob:test"),revokeObjectURL(){}},
  fetch:async name=>({ok:true,arrayBuffer:async()=>{const b=fs.readFileSync(path.join(root,name));return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)}})};
vm.runInNewContext(script,ctx);(async()=>{for(let i=0;i<100&&!result;i++)await new Promise(r=>setTimeout(r,10));
 if(!result||!Buffer.from(await result.arrayBuffer()).equals(fs.readFileSync(original)))process.exit(1);
 if(nodes.video.hidden||nodes.download.hidden||nodes.download.href!=="blob:test")process.exit(2);})();''')
        subprocess.run(['node',str(runner),str(dest),str(video)],check=True)
    with pytest.raises(FileExistsError):site.stage(video,dest,1024*1024)
    small_dest=tmp_path/'small-dist';small=site.stage(video,small_dest,4*1024*1024)
    assert small['parts']==1 and (small_dest/'video.mp4').read_bytes()==video.read_bytes()
    assert 'src="video.mp4"' in (small_dest/'index.html').read_text()
