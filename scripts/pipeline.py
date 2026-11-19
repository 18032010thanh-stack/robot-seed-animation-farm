"""CPU-oriented chunk renderer, resumable JPEG frames -> H.264 -> concat."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"project.json"
SCRIPT=ROOT/"scripts"/"scene_robot_seed.py"
OUT=ROOT/"outputs"

def config(): return json.loads(CFG.read_text(encoding="utf-8"))
def shell(args):
    print("$", " ".join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True)

def sha():
    d=hashlib.sha256()
    for file in (CFG,SCRIPT):
        d.update(file.read_bytes())
    return d.hexdigest()

def bounds(c,num,test_frames=None):
    total=c["duration_seconds"]*c["fps"]
    per=c["chunk_seconds"]*c["fps"]
    count=(total+per-1)//per
    if num<1 or num>count: raise ValueError(f"Chunk must be 1..{count}")
    start=1+(num-1)*per
    end=min(total,start+per-1)
    if test_frames: end=min(end,start+test_frames-1)
    return start,end

def probe(file):
    raw=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
       "-show_entries","stream=codec_name,width,height,avg_frame_rate,nb_frames",
       "-of","json",str(file)],text=True)
    streams=json.loads(raw).get("streams",[])
    if not streams: raise ValueError("No video stream")
    return streams[0]

def check_video(file,c,frames):
    if not file.exists() or file.stat().st_size<1024: return False
    try:
        v=probe(file)
        nom,den=map(int,v["avg_frame_rate"].split("/"))
        return (v["codec_name"]=="h264" and v["width"]==c["width"]
             and v["height"]==c["height"] and nom==c["fps"]*den
             and int(v.get("nb_frames",0))==frames)
    except (KeyError,ValueError,FileNotFoundError,subprocess.CalledProcessError): return False

def do_doctor(c):
    print("Project:",c["title"],c["width"],"x",c["height"],c["fps"],"FPS")
    for program in ("blender","ffmpeg","ffprobe"):
        p=shutil.which(program)
        print(program,p or "NOT FOUND")
    print("Expected:",(c["duration_seconds"]+c["chunk_seconds"]-1)//c["chunk_seconds"],"chunks")
    return all(shutil.which(p) for p in ("blender","ffmpeg","ffprobe"))

def do_render(c,num,threads,test_frames):
    if not do_doctor(c): raise RuntimeError("Install Blender and FFmpeg first")
    start,end=bounds(c,num,test_frames)
    is_test=test_frames is not None
    base=OUT/"test" if is_test else OUT
    base.mkdir(parents=True,exist_ok=True)
    output=base/f"part_{num:03d}.mp4"
    if check_video(output,c,end-start+1):
        print("ALREADY DONE",output)
        return
    frames=base/"frames"/f"part_{num:03d}"
    frames.mkdir(parents=True,exist_ok=True)
    source=frames/".source_sha256"
    # Invalidate partial JPEGs if source or config changed.
    fingerprint=sha()
    if source.exists() and source.read_text().strip()!=fingerprint:
        for old in frames.glob("f_*.jpg"): old.unlink()
    source.write_text(fingerprint)
    t0=time.time()
    shell(["blender","--background","--threads",str(threads),"--python",SCRIPT,
          "--","--config",CFG,"--start",start,"--end",end,"--frames",frames])
    missing=[n for n in range(start,end+1) if not (frames/f"f_{n:06d}.jpg").exists()]
    if missing: raise RuntimeError(f"Missing frames: {missing[:10]}")
    tmp=output.with_suffix(".tmp.mp4")
    shell(["ffmpeg","-hide_banner","-loglevel","error","-y",
          "-framerate",c["fps"],"-start_number",start,
          "-i",frames/"f_%06d.jpg","-frames:v",end-start+1,
          "-c:v","libx264","-crf",c["crf"],"-preset","veryfast",
          "-pix_fmt","yuv420p","-movflags","+faststart",tmp])
    if not check_video(tmp,c,end-start+1):
        raise RuntimeError("Video verification failed; left JPEGs for retry")
    tmp.replace(output)
    (base/f"part_{num:03d}.sha256").write_text(
       hashlib.sha256(output.read_bytes()).hexdigest()+"  "+output.name+"\n")
    print("COMPLETE",output,output.stat().st_size,"bytes",round(time.time()-t0,1),"sec")
    # Keep verified frame JPEGs for resumability; users may delete frames manually.

def do_status(c):
    count=(c["duration_seconds"]+c["chunk_seconds"]-1)//c["chunk_seconds"]
    for n in range(1,count+1):
        start,end=bounds(c,n)
        path=OUT/f"part_{n:03d}.mp4"
        print(f"{n:02d}: {'OK' if check_video(path,c,end-start+1) else 'MISSING'} {path.name}")

def do_merge(c):
    count=(c["duration_seconds"]+c["chunk_seconds"]-1)//c["chunk_seconds"]
    paths=[]
    for n in range(1,count+1):
        start,end=bounds(c,n)
        path=OUT/f"part_{n:03d}.mp4"
        if not check_video(path,c,end-start+1): raise RuntimeError(f"Missing/bad chunk {n}")
        paths.append(path)
    manifest=OUT/"concat.txt"
    manifest.write_text("".join("file '"+str(p.resolve()).replace("'","'\\''")+"'\n" for p in paths))
    result=OUT/"final_film.mp4"
    shell(["ffmpeg","-hide_banner","-loglevel","error","-y",
           "-f","concat","-safe","0","-i",manifest,"-c","copy",result])
    if not check_video(result,c,c["duration_seconds"]*c["fps"]):
        raise RuntimeError("Merged file verification failed")
    print("FINAL",result)

def main():
    p=argparse.ArgumentParser()
    commands=p.add_subparsers(dest="cmd",required=True)
    commands.add_parser("doctor")
    commands.add_parser("status")
    commands.add_parser("merge")
    run=commands.add_parser("run")
    run.add_argument("--chunk",type=int,required=True)
    run.add_argument("--threads",type=int,default=2)
    run.add_argument("--test-frames",type=int,default=None)
    run.add_argument("--preview",action="store_true")
    a=p.parse_args()
    c=config()
    if a.cmd=="doctor":
        if not do_doctor(c): sys.exit(1)
    elif a.cmd=="run":
        if a.threads<1: p.error("threads must be >=1")
        if a.test_frames is not None and a.test_frames<1: p.error("test-frames must be >=1")
        do_render(c,a.chunk,a.threads,a.test_frames or (30 if a.preview else None))
    elif a.cmd=="status": do_status(c)
    else: do_merge(c)

if __name__=="__main__": main()
