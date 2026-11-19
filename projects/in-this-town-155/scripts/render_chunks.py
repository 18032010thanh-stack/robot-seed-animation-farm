"""Render or assemble independent 10-second chunks of the 155s animation."""
import argparse, json, subprocess
from pathlib import Path
import make_animatic as m

OUT=m.OUT
FPS=m.FPS
PER=10*FPS
TOTAL=m.DATA["seconds"]*FPS
COUNT=(TOTAL+PER-1)//PER

def cmd(*args):
    print("$",*args,flush=True)
    subprocess.run([str(a) for a in args],check=True)

def verify(p,count):
    data=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams",
      "v:0","-show_entries","stream=codec_name,width,height,nb_frames,avg_frame_rate","-of","json",str(p)],text=True))
    v=data["streams"][0]
    assert (v["codec_name"],v["width"],v["height"],v["avg_frame_rate"],int(v["nb_frames"]))==("h264",m.W,m.H,f"{FPS}/1",count)
    print("VERIFIED",p,count,flush=True)

def render(chunk):
    assert 1<=chunk<=COUNT
    OUT.mkdir(parents=True,exist_ok=True)
    start=(chunk-1)*PER; end=min(TOTAL,start+PER)
    out=OUT/f"part_{chunk:03}.mp4"
    process=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","rawvideo","-pix_fmt","rgb24","-s",f"{m.W}x{m.H}","-r",str(FPS),
        "-i","-","-c:v","libx264","-crf","23","-preset","veryfast",
        "-pix_fmt","yuv420p","-frames:v",str(end-start),"-movflags","+faststart",str(out)],stdin=subprocess.PIPE)
    backgrounds={}
    try:
        for f in range(start,end):
            scene_idx=f//(m.SHOT_SECONDS*FPS)
            if scene_idx not in backgrounds:
                backgrounds[scene_idx]=m.background(scene_idx,m.DATA["shots"][scene_idx]["scene"])
            frame=m.make_frame(scene_idx,f%(m.SHOT_SECONDS*FPS),backgrounds[scene_idx])
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait()!=0:raise RuntimeError("FFmpeg render failed")
    except Exception:
        if process.poll() is None: process.kill()
        raise
    verify(out,end-start)

def assemble():
    OUT.mkdir(parents=True,exist_ok=True)
    parts=[OUT/f"part_{k:03}.mp4" for k in range(1,COUNT+1)]
    for k,p in enumerate(parts):
        if not p.exists():raise FileNotFoundError(str(p))
        verify(p,min(PER,TOTAL-k*PER))
    txt=OUT/"concat.txt"
    txt.write_text("".join("file '"+str(p.resolve())+"'\n" for p in parts),encoding="utf-8")
    silent=OUT/"silent.mp4"
    cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",txt,"-c","copy",silent)
    verify(silent,TOTAL)
    m.make_srt()
    voice=m.synth_voice()
    result=OUT/"in_this_town_155s_vietsub.mp4"
    if voice:
        cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-i",silent,"-i",voice,
            "-c:v","copy","-c:a","aac","-b:a","96k","-t",str(m.DATA["seconds"]),result)
    else:
        cmd("ffmpeg","-hide_banner","-loglevel","error","-y","-i",silent,"-c:v","copy",result)
    verify(result,TOTAL)
    print("FINISHED",result,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["render","assemble"])
    p.add_argument("--chunk",type=int,default=1)
    a=p.parse_args()
    if a.mode=="render":render(a.chunk)
    else:assemble()
