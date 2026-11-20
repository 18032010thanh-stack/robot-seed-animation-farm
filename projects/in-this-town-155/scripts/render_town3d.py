"""Render 3D town in resumable chunks; verify and assemble 155s Vietsub H.264."""
import argparse, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
STORY_FILE=HERE/"stories"/"town_last_awake_155.json"
STORY=json.loads(STORY_FILE.read_text(encoding="utf-8"))
SCRIPT=HERE/"scripts"/"scene_town3d.py"
OUT=HERE/"output3d"
FPS=int(STORY["fps"])
SHOT_FRAMES=int(STORY["shot_seconds"])*FPS
TOTAL_FRAMES=int(STORY["seconds"])*FPS
CHUNK_FRAMES=10*FPS
NUM_CHUNKS=(TOTAL_FRAMES+CHUNK_FRAMES-1)//CHUNK_FRAMES

def call(*args):
    print("$"," ".join(map(str,args)),flush=True)
    subprocess.run([str(a) for a in args],check=True)

def checksum():
    h=hashlib.sha256()
    for p in (SCRIPT,STORY_FILE,Path(__file__).resolve()):
        h.update(p.read_bytes())
    return h.hexdigest()

def interval(chunk,limit=None):
    if not 1<=chunk<=NUM_CHUNKS:raise ValueError(f"chunk must be 1..{NUM_CHUNKS}")
    start=(chunk-1)*CHUNK_FRAMES+1
    end=min(chunk*CHUNK_FRAMES,TOTAL_FRAMES)
    if limit is not None:
        if limit<1:raise ValueError("test frames must be positive")
        end=min(end,start+limit-1)
    return start,end

def stats(p):
    raw=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,width,height,avg_frame_rate,nb_frames",
        "-of","json",str(p)],text=True)
    items=json.loads(raw).get("streams",[])
    if not items:raise ValueError("No video stream")
    return items[0]

def check(p,n):
    if not p.exists() or p.stat().st_size<1024:raise ValueError("Video missing or empty")
    s=stats(p)
    num,den=map(int,s["avg_frame_rate"].split("/"))
    if s["codec_name"]!="h264" or s["width"]!=STORY["width"] or s["height"]!=STORY["height"]:
        raise ValueError(f"Codec/resolution mismatch: {s}")
    if num!=FPS*den or int(s.get("nb_frames") or 0)!=n:
        raise ValueError(f"Frame rate/count mismatch: {s}; expected {FPS}fps, {n} frames")
    print("VERIFIED",p.name,n,"frames",flush=True)

def story_check():
    shots=STORY["shots"]
    assert len(shots)*SHOT_FRAMES==TOTAL_FRAMES, "Story must cover exact runtime"
    assert STORY["width"]>0 and STORY["height"]>0
    assert all("scene" in s and "line" in s and "id" in s for s in shots)
    print("STORY OK",len(shots),"shots",NUM_CHUNKS,"chunks",TOTAL_FRAMES,"frames",flush=True)

def render(chunk,threads,quality,limit):
    story_check()
    if not (shutil.which("blender") and shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise RuntimeError("Missing Blender or FFmpeg/ffprobe")
    start,end=interval(chunk,limit)
    root=OUT/("test" if limit is not None else "")
    root.mkdir(parents=True,exist_ok=True)
    video=root/f"part_{chunk:03d}.mp4"
    fingerprint=checksum()+":"+quality
    flag=root/f"part_{chunk:03d}.source"
    if video.exists() and flag.exists() and flag.read_text().strip()==fingerprint:
        try:
            check(video,end-start+1)
            print("ALREADY DONE",video,flush=True)
            return
        except (ValueError,KeyError,FileNotFoundError,subprocess.CalledProcessError):
            pass
    frames=root/"frames"/f"part_{chunk:03d}"
    frames.mkdir(parents=True,exist_ok=True)
    source=frames/".source"
    if not source.exists() or source.read_text().strip()!=fingerprint:
        for f in frames.glob("f_*.jpg"):f.unlink()
        source.write_text(fingerprint,encoding="utf-8")
    t0=time.perf_counter()
    first_shot=(start-1)//SHOT_FRAMES
    last_shot=(end-1)//SHOT_FRAMES
    for shot in range(first_shot,last_shot+1):
        lo=max(1,start-shot*SHOT_FRAMES)
        hi=min(SHOT_FRAMES,end-shot*SHOT_FRAMES)
        call("blender","--background","--threads",threads,"--python",SCRIPT,
            "--","--shot",shot,"--start",lo,"--end",hi,"--output",frames,"--quality",quality)
    absent=[f for f in range(start,end+1)
            if not (frames/f"f_{f:06d}.jpg").exists()]
    if absent:raise RuntimeError(f"Missing frames: {absent[:10]}")
    tmp=video.with_name(video.stem+".temp.mp4")
    call("ffmpeg","-hide_banner","-loglevel","error","-y",
         "-framerate",FPS,"-start_number",start,
         "-i",frames/"f_%06d.jpg","-frames:v",end-start+1,
         "-c:v","libx264","-preset","veryfast","-crf","23",
         "-pix_fmt","yuv420p","-movflags","+faststart",tmp)
    check(tmp,end-start+1)
    tmp.replace(video)
    flag.write_text(fingerprint,encoding="utf-8")
    print("COMPLETE",video,video.stat().st_size,"bytes",
        round(time.perf_counter()-t0,2),"seconds",flush=True)

def assemble():
    story_check()
    OUT.mkdir(parents=True,exist_ok=True)
    paths=[]
    for i in range(1,NUM_CHUNKS+1):
        p=OUT/f"part_{i:03d}.mp4"
        a,b=interval(i)
        check(p,b-a+1)
        paths.append(p.resolve())
    manifest=OUT/"concat.txt"
    manifest.write_text("".join("file '"+str(p)+"'\n" for p in paths),encoding="utf-8")
    silent=OUT/"joined_silent.mp4"
    call("ffmpeg","-hide_banner","-loglevel","error","-y",
         "-f","concat","-safe","0","-i",manifest,"-c","copy",silent)
    check(silent,TOTAL_FRAMES)
    # Subtitle and narration generator from the previously validated original 2D project.
    import make_animatic
    make_animatic.OUT=OUT
    make_animatic.OUT.mkdir(parents=True,exist_ok=True)
    make_animatic.make_srt()
    voice=make_animatic.synth_voice()
    if voice is None:raise RuntimeError("Install espeak-ng for Vietnamese narration")
    srt=(OUT/"vietsub.srt").resolve().as_posix()
    # libass supports Unicode Vietnamese text; fonts-noto-core supplies the glyphs.
    subfilter=("subtitles=filename="+srt+
      ":force_style='FontName=Noto Sans,FontSize=19,Alignment=2,MarginV=75,"
      "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1'")
    final=OUT/"in_this_town_155s_3d_vietsub.mp4"
    call("ffmpeg","-hide_banner","-loglevel","error","-y",
         "-i",silent,"-i",voice,"-vf",subfilter,
         "-c:v","libx264","-preset","veryfast","-crf","22",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","96k",
         "-frames:v",TOTAL_FRAMES,"-t",STORY["seconds"],
         "-movflags","+faststart",final)
    check(final,TOTAL_FRAMES)
    print("FINAL",final,final.stat().st_size,"bytes",flush=True)

def main():
    parser=argparse.ArgumentParser()
    modes=parser.add_subparsers(dest="command",required=True)
    modes.add_parser("doctor")
    modes.add_parser("assemble")
    r=modes.add_parser("render")
    r.add_argument("--chunk",type=int,required=True)
    r.add_argument("--threads",type=int,default=2)
    r.add_argument("--quality",choices=("workbench","fast","cycles"),default="fast")
    r.add_argument("--test-frames",type=int,default=None)
    args=parser.parse_args()
    if args.command=="doctor":
        story_check()
        for bin in ("blender","ffmpeg","ffprobe","espeak-ng"):
            print(bin,shutil.which(bin),flush=True)
    elif args.command=="render":render(args.chunk,args.threads,args.quality,args.test_frames)
    else:assemble()

if __name__=="__main__":main()
