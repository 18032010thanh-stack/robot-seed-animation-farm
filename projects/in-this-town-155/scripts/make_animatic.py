#!/usr/bin/env python3
"""Original 155-second Vietnamese subtitled vertical animation.
Offline storyboard-grade animation from a source story, with optional offline eSpeak narration.
Does not require Blender or any third-party media, and outputs SRT plus final H.264 MP4.
"""
import argparse, json, math, os, subprocess, wave, shutil, textwrap
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE=Path(__file__).resolve().parents[1]
STORY=BASE/'stories/town_last_awake_155.json'
OUT=BASE/'output'
DATA=json.loads(STORY.read_text(encoding='utf-8'))
W,H=DATA['width'],DATA['height']
FPS=DATA['fps']
SHOT_SECONDS=DATA['shot_seconds']
FONT_BOLD='/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'
FONT_REG='/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'
FONT_FALLBACK='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(sz,bold=False):
    path=(FONT_BOLD if bold else FONT_REG)
    if not os.path.isfile(path): path=FONT_FALLBACK
    return ImageFont.truetype(path, sz)
TITLE_FONT=font(30,True); SMALL=font(18,True); CAP=font(29,True); TINY=font(13,True)

def color(c,a=255): return (*c,a)

def make_srt():
    def stamp(ms):
        hh=ms//3600000;ms%=3600000;mm=ms//60000;ms%=60000;ss=ms//1000;ms%=1000
        return f'{hh:02}:{mm:02}:{ss:02},{ms:03}'
    s=[]
    for i,sh in enumerate(DATA['shots']):
        a=i*SHOT_SECONDS*1000;b=(i+1)*SHOT_SECONDS*1000
        s.append(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{sh["line"]}\n')
    (OUT/'vietsub.srt').write_text('\n'.join(s),encoding='utf-8')

def synth_voice():
    """Original offline TTS; no cloning, no licensed songs. Keep 5-s per line."""
    ex=shutil.which('espeak-ng') or shutil.which('espeak')
    if not ex: return None
    sr=22050; total=DATA['seconds']*sr
    mix=np.zeros(total,dtype=np.float32)
    tmp=OUT/'_voice_scenes';tmp.mkdir(exist_ok=True)
    for i,sh in enumerate(DATA['shots']):
        p=tmp/f'{i:02}.wav'
        # espeak's Vietnamese voice is synthetic and may sound robotic.
        subprocess.run([ex,'-v','vi','-s','152','-a','132','-w',str(p),sh['line']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        with wave.open(str(p),'rb') as w:
            samples=w.readframes(w.getnframes()); source_rate=w.getframerate();channels=w.getnchannels(); sw=w.getsampwidth()
        if sw!=2: continue
        x=np.frombuffer(samples,dtype='<i2').astype(np.float32)/32768
        if channels>1: x=x.reshape(-1,channels).mean(axis=1)
        if source_rate != sr:
            xi=np.arange(math.ceil(len(x)*sr/source_rate))*source_rate/sr
            x=np.interp(xi,np.arange(len(x)),x).astype(np.float32)
        # Respect exact narration space with tail silence; do not break the next shot.
        maxsamples=int(4.7*sr)
        if len(x)>maxsamples:
            # Audio resampling compresses extremely long line to safe scene length.
            x=np.interp(np.linspace(0,len(x)-1,maxsamples),np.arange(len(x)),x).astype(np.float32)
        f=int(.035*sr)
        if len(x)>2*f:
            x[:f]*=np.linspace(0,1,f)
            x[-f:]*=np.linspace(1,0,f)
        t=i*SHOT_SECONDS*sr+int(.2*sr)
        mix[t:t+len(x)]+=x[:min(len(x),total-t)]
    # Peak limiter
    m=max(1.,float(np.max(np.abs(mix)))/.83)
    mix/=m
    path=OUT/'narration_vi.wav'
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr)
        w.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())
    shutil.rmtree(tmp)
    return path

# Composition helpers
NIGHT=(9,14,31); SKY=(25,34,67); GOLD=(255,205,110); ACCENT=(120,226,231)

def rect(d,xy,fill,outline=None,width=1,r=0):
    if r:d.rounded_rectangle(xy,fill=fill,outline=outline,width=width,radius=r)
    else:d.rectangle(xy,fill=fill,outline=outline,width=width)

def gradient(top,bottom):
    y=np.arange(H,dtype=np.float32)[:,None,None]
    frac=(y/(H-1)).astype(np.float32)
    a=np.array(top,dtype=np.float32).reshape(1,1,3);b=np.array(bottom,dtype=np.float32).reshape(1,1,3)
    v=(a*(1-frac)+b*frac).astype('uint8')
    return Image.fromarray(np.repeat(v,W,axis=1),'RGB')

def window(d,x,y,ww=31,hh=42,lit=True):
    rect(d,(x,y,x+ww,y+hh),(12,18,35),r=2)
    inset=(243,184,96) if lit else (28,45,67)
    rect(d,(x+3,y+3,x+ww-3,y+hh-3),inset)
    d.line((x+ww//2,y,x+ww//2,y+hh),fill=(29,40,58),width=4)
    d.line((x,y+hh//2,x+ww,y+hh//2),fill=(29,40,58),width=4)

def skyline(d,idx,show_lights=True,dawn=False):
    d.ellipse((355,70,420,135),fill=(255,241,197) if dawn else (221,228,246))
    for k in range(13):
        x=-40 + k*43
        roof=210+(k*31%85)
        col=((49,64,93) if dawn else (20+(k%2)*7,28+(k%3)*4,50+(k%2)*10))
        rect(d,(x,roof,x+46,555),col)
        for y in range(roof+21,515,62):
            if (k+y//62)%3:
                lit=show_lights and ((k+y//62+idx//3)%4!=0)
                window(d,x+8,y,24,33,lit)

def street_bg(idx,variant='town'):
    dawn=variant=='dawn'
    im=gradient((88,126,151) if dawn else (15,22,45),(205,181,140) if dawn else (34,46,77))
    d=ImageDraw.Draw(im)
    skyline(d,idx,show_lights=(idx<11 or variant=='dawn' or idx==12),dawn=dawn)
    # perspective street and pavement
    d.polygon([(120,522),(363,522),(570,854),(-90,854)],fill=(41,47,67) if not dawn else (85,91,104))
    d.polygon([(236,522),(244,522),(380,854),(320,854)],fill=(57,62,83))
    for i in range(7):
        yy=538+i*i*7
        wd=1+i*2
        d.line([(236-i*8,yy),(244+i*8,yy)],fill=(199,192,151),width=wd)
    if variant=='cafe':
        rect(d,(12,260,275,548),(42,51,76))
        rect(d,(26,279,255,335),(174,68,66),r=7)
        d.text((49,292),'MILK & SLEEP',font=SMALL,fill='white')
        rect(d,(55,361,218,530),(19,30,53))
        window(d,76,391,100,110,True)
    return im

def room_bg(idx,variant='room'):
    im=gradient((34,45,74),(62,69,88));d=ImageDraw.Draw(im)
    d.polygon([(0,592),(480,559),(480,854),(0,854)],fill=(40,47,68))
    d.polygon([(0,0),(480,0),(480,560),(0,591)],fill=(37,50,76))
    rect(d,(260,154,444,448),(14,19,39),r=6)
    rect(d,(271,165,433,436),(22,32,64))
    d.ellipse((343,189,400,249),fill=(232,233,205))
    d.line((353,165,353,435),fill=(55,60,73),width=8)
    d.line((270,304,443,304),fill=(55,60,73),width=8)
    rect(d,(0,579,275,728),(60,63,87),r=8)
    rect(d,(0,580,254,670),(93,104,125),r=8)
    rect(d,(13,562,115,610),(170,170,183),r=9)
    rect(d,(352,615,468,632),(109,72,56))
    rect(d,(365,532,392,620),(153,116,66))
    d.ellipse((337,517,420,565),fill=(255,212,146))
    d.ellipse((347,527,411,556),fill=(255,241,186))
    if variant=='window':
        # distinct blue eyes outside
        d.ellipse((312,258,349,274),fill=(102,205,238))
        d.ellipse((389,258,425,274),fill=(102,205,238))
    return im

def clock_bg(idx):
    im=gradient((27,37,66),(8,12,28));d=ImageDraw.Draw(im)
    d.ellipse((46,200,437,601),fill=(49,62,92),outline=(219,191,128),width=16)
    d.ellipse((63,215,420,580),fill=(202,211,205),outline=(26,34,48),width=8)
    for k in range(12):
        a=math.tau*k/12-math.pi/2
        x=241+math.cos(a)*140;y=401+math.sin(a)*142
        d.ellipse((x-6,y-6,x+6,y+6),fill=(31,40,57))
    d.ellipse((235,396,247,408),fill=(33,39,49))
    return im

def ghost_bg(idx):
    im=gradient((8,14,33),(26,33,61));d=ImageDraw.Draw(im)
    for r in range(270,40,-40):
        d.ellipse((240-r,365-r,240+r,365+r),outline=(32+int(r/30),42+int(r/20),74+int(r/15)),width=4)
    rect(d,(0,575,480,854),(20,26,42))
    d.polygon([(0,575),(480,575),(480,637),(0,637)],fill=(31,37,61))
    return im

def background(idx,scene):
    if scene in ('town','street','cafe','roof'):return street_bg(idx,'dawn' if idx>=28 else scene)
    if scene in ('room','window','bell'):return room_bg(idx,'window' if scene=='window' else 'room')
    if scene=='clock':return clock_bg(idx)
    return ghost_bg(idx)

def avatar(im,x,y,scale=1.0,emotion='alert',phase=0.0,shirt=(109,54,71),side=False):
    d=ImageDraw.Draw(im)
    q=lambda n:int(n*scale)
    x,y=int(x),int(y+math.sin(phase*math.tau*2)*4)
    # extruded blocky avatar: dark back faces and bright main faces
    d.ellipse((x-q(48),y+q(7),x+q(50),y+q(24)),fill=(10,17,28))
    d.polygon([(x-q(41),y-q(104)),(x+q(32),y-q(104)),(x+q(44),y-q(92)),(x-q(28),y-q(92))],fill=(44,35,51))
    rect(d,(x-q(33),y-q(112),x+q(33),y-q(42)),shirt,r=q(6))
    rect(d,(x-q(28),y-q(43),x-q(4),y+q(4)),(38,46,68),r=q(4))
    rect(d,(x+q(4),y-q(43),x+q(28),y+q(4)),(38,46,68),r=q(4))
    arm1=math.sin(phase*math.tau*1.2)*q(10)
    rect(d,(x-q(57),y-q(102)+arm1,x-q(34),y-q(44)+arm1),(229,177,143),r=q(3))
    rect(d,(x+q(34),y-q(102)-arm1,x+q(57),y-q(44)-arm1),(229,177,143),r=q(3))
    rect(d,(x-q(36),y-q(202),x+q(36),y-q(118)),(211,170,142),r=q(6))
    # hair as angular shape
    d.polygon([(x-q(40),y-q(166)),(x-q(42),y-q(210)),(x-q(24),y-q(228)),(x+q(20),y-q(227)),(x+q(45),y-q(205)),(x+q(35),y-q(169)),(x+q(23),y-q(199)),(x-q(30),y-q(199))],fill=(34,31,42))
    eyey=y-q(168)
    if emotion=='sleep':
        d.arc((x-q(25),eyey,x-q(2),eyey+q(12)),0,180,fill=(30,37,50),width=q(3))
        d.arc((x+q(6),eyey,x+q(29),eyey+q(12)),0,180,fill=(30,37,50),width=q(3))
    else:
        er=7 if emotion in ('shock','scared') else 5
        for ex in (x-q(18),x+q(18)):
            d.ellipse((ex-q(er),eyey-q(er),ex+q(er),eyey+q(er)),fill=(21,29,44))
            d.ellipse((ex-q(2),eyey-q(4),ex+q(1),eyey-q(1)),fill=(233,241,240))
    if emotion in ('shock','scared'):
        d.ellipse((x-q(5),y-q(145),x+q(5),y-q(132)),fill=(75,39,50))
    else:
        d.arc((x-q(13),y-q(153),x+q(14),y-q(136)),0,180,fill=(83,49,50),width=q(3))

def ghost(im,x,y,scale=1.0,phase=0.0):
    layer=Image.new('RGBA',(W,H));d=ImageDraw.Draw(layer)
    rx=int(x); yy=int(y+math.sin(phase*3)*8)
    q=lambda n:int(n*scale)
    d.ellipse((rx-q(77),yy-q(445),rx+q(77),yy-q(259)),fill=(15,21,40,240))
    d.polygon([(rx-q(72),yy-q(359)),(rx+q(72),yy-q(359)),(rx+q(102),yy),(rx+q(62),yy-q(38)),(rx+q(16),yy-q(2)),(rx-q(32),yy-q(41)),(rx-q(95),yy)],fill=(11,18,36,255))
    for sgn in (-1,1):
        ex=rx+sgn*q(30)
        d.ellipse((ex-q(14),yy-q(347),ex+q(14),yy-q(330)),fill=(90,224,242,255))
        d.ellipse((ex-q(5),yy-q(344),ex+q(5),yy-q(336)),fill=(221,255,255,255))
    im.paste(layer,(0,0),layer)

def props(im,scene,idx,phase):
    d=ImageDraw.Draw(im)
    if scene=='clock':
        theta=(phase*2+idx*.03)*math.tau
        d.line((241,401,241+math.cos(theta)*106,401+math.sin(theta)*106),fill=(36,40,52),width=10)
        d.line((241,401,241+math.cos(theta*.15-math.pi/3)*65,401+math.sin(theta*.15-math.pi/3)*65),fill=(45,50,56),width=13)
        d.ellipse((228,389,255,413),fill=(49,56,62))
    if scene in ('town','street','roof','cafe'):
        for s in range(5):
            x=50+s*90+int(math.sin(phase*math.tau+s)*5); y=532+s%2*10
            d.ellipse((x-4,y-4,x+4,y+4),fill=(255,200,110))
    if scene=='shadow':
        for j in range(5):
            px=40+j*96+20*math.sin(phase*math.tau*2+j)
            py=350+38*math.sin(phase*math.tau*1.6+j)
            d.arc((px-50,py-70,px+75,py+90),190,320,fill=(74,91,123),width=10)
    if scene=='bell':
        d.arc((247,310,310,390),180,360,fill=(214,224,233),width=8)
        d.polygon([(270,367),(288,367),(312,420),(249,420)],fill=(191,210,226))
        d.ellipse((275,414,291,433),fill=(249,234,168))


def make_frame(idx,local_frame,bg):
    t=local_frame/FPS; phase=t/SHOT_SECONDS
    scene=DATA['shots'][idx]['scene']; emotion=DATA['shots'][idx]['emotion']
    im=bg.copy()
    d=ImageDraw.Draw(im)
    # Hero / guardian staging; shifts for natural but inexpensive motion
    bob=t*.35
    if scene=='clock': avatar(im,225,764,.81,emotion,phase,shirt=(99,57,76))
    elif scene=='town': avatar(im,205+12*math.sin(t*.5),720,.90,emotion,phase,shirt=(108,55,72))
    elif scene=='cafe': avatar(im,315,765,.78,emotion,phase,shirt=(99,57,76))
    elif scene=='street':
        avatar(im,150,722,.96,emotion,phase)
        avatar(im,360,680,.70,'sleep',phase+.3,shirt=(51,73,95))
    elif scene=='room':avatar(im,177+5*math.sin(t),785,1.08,emotion,phase)
    elif scene=='window':
        avatar(im,125,788,1.06,emotion,phase)
        if idx>=15: ghost(im,375,730,.68,phase)
    elif scene=='ghost':
        ghost(im,270,744,1.17,phase)
        avatar(im,68,808,.67,emotion,phase)
    elif scene=='shadow':
        ghost(im,320,780,.98,phase)
        avatar(im,103,790,.83,emotion,phase)
    elif scene=='bell':avatar(im,158,770,.98,emotion,phase)
    elif scene=='roof':avatar(im,235,745,1.0,emotion,phase)
    props(im,scene,idx,phase)
    # cinematic vignette (subtle)
    overlay=Image.new('RGBA',(W,H),(0,0,0,0));od=ImageDraw.Draw(overlay)
    od.rectangle((0,0,W,117),fill=(6,11,25,160))
    im=Image.alpha_composite(im.convert('RGBA'),overlay)
    d=ImageDraw.Draw(im)
    d.text((19,22),'IN THIS TOWN',font=TITLE_FONT,fill=(246,244,226),stroke_width=1,stroke_fill=(15,19,32))
    d.text((20,65),'KHÔNG AI ĐƯỢC THỨC CUỐI CÙNG',font=TINY,fill=(160,217,231))
    tick=f'{idx+1:02}/31  •  09:00'
    d.text((W-18-d.textlength(tick,font=TINY),95),tick,font=TINY,fill=(200,211,226))
    # 5-sec, two-line Vietnamese subtitles with a single yellow keyword
    caption=DATA['shots'][idx]['line']
    words=caption.split()
    lines=[]; cur=[]
    for word in words:
        test=' '.join(cur+[word]);bbox=d.textbbox((0,0),test,font=CAP,stroke_width=2)
        if bbox[2]>W-50 and cur:
            lines.append(cur);cur=[word]
        else:cur.append(word)
    if cur:lines.append(cur)
    lineheight=43
    blockh=len(lines)*lineheight+38
    y0=H-75-blockh
    rect(d,(15,y0,W-15,y0+blockh),(8,13,29,225),r=18)
    # fixed caption per scene, dynamic highlighted word; better for vi languages than word-level forced timing
    active=min(len(words)-1,int(max(0,t)/SHOT_SECONDS*len(words)))
    for j,line in enumerate(lines):
        tot=sum(d.textlength(w,font=CAP) for w in line)+(len(line)-1)*d.textlength(' ',font=CAP)
        x=(W-tot)/2;y=y0+17+j*lineheight
        for word in line:
            overall_index=sum(len(l) for l in lines[:j])+line.index(word)
            fill=(255,224,94) if overall_index==active else (250,249,247)
            d.text((x,y),word,font=CAP,fill=fill,stroke_width=2,stroke_fill=(5,10,24))
            x+=d.textlength(word+' ',font=CAP)
    # progress bar
    d.rectangle((0,H-6,int(W*(idx+phase)/len(DATA['shots'])),H),fill=(124,231,217))
    return im.convert('RGB')

def video(args):
    make_srt();n=DATA['seconds']*FPS
    vo=None if args.silent else synth_voice()
    out=OUT/'in_this_town_155s_vietsub.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}', '-r',str(FPS),'-i','-']
    if vo:cmd+=['-i',str(vo),'-c:a','aac','-b:a','96k']
    cmd+=['-c:v','libx264','-crf','23','-preset','veryfast','-pix_fmt','yuv420p','-frames:v',str(n),'-movflags','+faststart','-t',str(DATA['seconds']),str(out)]
    print('Encoding',out,'frames=',n,'with audio=',vo is not None,flush=True)
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    bases=[background(i,sh['scene']) for i,sh in enumerate(DATA['shots'])]
    for i in range(n):
        idx=i//(SHOT_SECONDS*FPS)
        im=make_frame(idx,i%(SHOT_SECONDS*FPS),bases[idx])
        if i%(FPS*10)==0:print('time:',i//FPS,'/',DATA['seconds'],flush=True)
        process.stdin.write(im.tobytes())
    process.stdin.close();rc=process.wait()
    if rc:raise RuntimeError('ffmpeg failed '+str(rc))
    im=make_frame(0,35,bases[0]);im.save(OUT/'preview_still.jpg',quality=92)
    print('Finished:',out,round(out.stat().st_size/1e6,2),'MB',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--silent',action='store_true');args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True);video(args)