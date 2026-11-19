"""Standalone low-poly film generator for Blender 3.x/4.x, no external assets."""
import argparse, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector

def material(name, rgb, metal=0.0, glow=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    node = m.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*rgb, 1)
    node.inputs["Metallic"].default_value = metal
    node.inputs["Roughness"].default_value = .62
    if glow:
        for k,v in (("Emission Color", (*rgb,1)), ("Emission Strength",glow)):
            if k in node.inputs: node.inputs[k].default_value = v
    return m

def shape(kind, name, loc, scale, mat, parent=None, segments=12):
    if kind == "cube": bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    elif kind == "cyl": bpy.ops.mesh.primitive_cylinder_add(vertices=max(12,segments),radius=1,depth=1,location=loc)
    else: bpy.ops.mesh.primitive_uv_sphere_add(segments=max(12,segments),ring_count=8,location=loc)
    o = bpy.context.object
    o.name=name
    o.scale=scale
    o.data.materials.append(mat)
    if parent is not None: o.parent=parent
    return o

REFERENCE_FPS = 15
TIMELINE_SCALE = 1.0

def scaled_frame(f):
    # The storyboard uses 15-fps key positions. Keep the SAME seconds at any output FPS.
    return 1.0 + (f - 1.0) * TIMELINE_SCALE

def key(o,path,f,val):
    setattr(o,path,val)
    o.keyframe_insert(data_path=path,frame=scaled_frame(f))

def key_component(o,path,index,f,val):
    getattr(o,path)[index]=val
    o.keyframe_insert(data_path=path,index=index,frame=scaled_frame(f))

def build(cfg):
    global TIMELINE_SCALE
    TIMELINE_SCALE = float(cfg['fps']) / REFERENCE_FPS
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.frame_start=1
    scene.frame_end=cfg["duration_seconds"]*cfg["fps"]
    scene.render.fps=cfg["fps"]
    scene.render.resolution_x=cfg["width"]
    scene.render.resolution_y=cfg["height"]
    scene.render.resolution_percentage=100
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=int(cfg.get("samples",8))
    if hasattr(scene.cycles,"use_denoising"): scene.cycles.use_denoising=True
    scene.view_settings.view_transform="Standard"
    world=bpy.data.worlds.new("Lavender dusk") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world=world
    world.use_nodes=True
    bg=world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value=(.15,.14,.25,1)
    bg.inputs["Strength"].default_value=.65

    soil=material("Planet lavender",(.27,.25,.35))
    stone=material("Stones",(.39,.37,.45))
    earth=material("Soil",(.44,.29,.20))
    white=material("Robot white",(.80,.86,.88),.18)
    blue=material("Robot panels",(.19,.44,.57),.18)
    eye=material("Eye cyan",(.02,.79,.75),.0,.45)
    seedmat=material("Seed",(.27,.14,.08))
    green=material("Green stem",(.20,.66,.32))
    leafmat=material("Leaves",(.36,.78,.30))
    petal=material("Pink petals",(.98,.53,.50))
    yellow=material("Flower yellow",(.99,.77,.24),0,.4)

    shape("cyl","Floating planet",(0,0,-.24),(6.2,6.2,.55),soil,segments=48)
    shape("cyl","Soil patch",(1.62,0,.06),(.88,.88,.11),earth,segments=24)
    random.seed(20261119)
    for i in range(22):
        a=random.random()*math.tau
        r=random.uniform(2.2,5.4)
        x,y=math.cos(a)*r,math.sin(a)*r
        if abs(x-1.62)<1.3 and abs(y)<1.1: continue
        s=random.uniform(.08,.26)
        shape("sphere",f"Rock {i}",(x,y,.10),(s,s*.85,s*.48),stone)

    robot=bpy.data.objects.new("Robot master",None)
    bpy.context.collection.objects.link(robot)
    robot.location=(-3.45,0,.04)
    shape("cube","Body",(0,0,1.02),(.86,.67,1.0),white,robot)
    shape("cube","Chest light",(0,-.35,1.07),(.30,.06,.18),blue,robot)
    head=shape("cube","Head",(0,-.04,1.82),(1.05,.78,.70),white,robot)
    shape("cube","Face visor",(0,-.445,1.84),(.81,.05,.40),blue,robot)
    for sign in (-1,1):
        shape("sphere",f"Eye {sign}",(.22*sign,-.48,1.89),(.105,.04,.09),eye,robot)
        shape("cube",f"Foot {sign}",(.25*sign,-.02,.20),(.30,.52,.30),blue,robot)
        arm=shape("cube",f"Arm {sign}",(.63*sign,0,.99),(.23,.32,.62),white,robot)
        for f,ang in ((1,0),(650,.1*sign),(1150,-.2*sign),(1490,.65*sign),(2120,.06*sign),(2600,.5*sign),(2700,.1*sign)):
            key_component(arm,"rotation_euler",1,f,ang)
    shape("cyl","Antenna",(0,0,2.28),(.05,.05,.30),blue,robot)
    shape("sphere","Antenna glow",(0,0,2.47),(.11,.11,.11),eye,robot)
    # The same global frame positions are used independently in every chunk.
    for f,x in ((1,-3.45),(300,-2.7),(600,-1.5),(900,-.18),(1110,.60),(2700,.60)):
        key_component(robot,"location",0,f,x)
    for f in range(1,1150,60):
        key_component(robot,"location",2,f,.04+(.08 if f//60%2 else 0))
    key_component(robot,"location",2,1200,.04)
    key_component(robot,"location",2,2700,.04)
    for f,tilt in ((1,0),(850,.1),(1120,-.19),(1530,-.11),(1950,.07),(2450,.16),(2700,0)):
        key_component(robot,"rotation_euler",1,f,tilt)

    seed=shape("sphere","Last seed",(1.62,-.03,.19),(.13,.12,.18),seedmat)
    for f,s in ((1,1),(1300,1),(1600,.01),(2700,.01)):
        key(seed,"scale",f,(.13*s,.12*s,.18*s))

    # Water droplets, keyframed, without costly particle or fluid simulations.
    for i in range(5):
        d=shape("sphere",f"Water drop {i}",(1.25+i*.12,-.10,1.4),(.055,.055,.09),eye)
        t=1430+i*36
        for f,s in ((1,.001),(t-1,.001),(t+1,1),(t+24,1),(t+40,.001),(2700,.001)):
            key(d,"scale",f,(.055*s,.055*s,.09*s))
        for f,z in ((1,1.4),(t,1.4),(t+40,.15),(2700,.15)):
            key_component(d,"location",2,f,z)

    stem=shape("cyl","Growing stem",(1.62,0,.07),(.07,.07,.001),green)
    for f,h in ((1,.001),(1750,.001),(1910,.26),(2050,.66),(2270,1.2),(2570,1.5),(2700,1.5)):
        key(stem,"scale",f,(.07,.07,h))
        key_component(stem,"location",2,f,.07+h/2)
    for side in (-1,1):
        leaf=shape("sphere",f"Leaf {side}",(1.62+side*.25,0,.67),(.30,.12,.13),leafmat)
        for f,s in ((1,.001),(1970,.001),(2170,.6),(2340,1),(2700,1)):
            key(leaf,"scale",f,(.30*s,.12*s,.13*s))
    bloom=bpy.data.objects.new("Flower bloom root",None)
    bpy.context.collection.objects.link(bloom)
    for f,z in ((1,.08),(2240,.08),(2400,1.19),(2600,1.58),(2700,1.58)):
        key(bloom,"location",f,(1.62,-.03,z))
    core=shape("sphere","Flower center",(0,-.06,0),(.22,.12,.22),yellow,bloom)
    for f,s in ((1,.001),(2320,.001),(2450,.35),(2630,1),(2700,1)):
        key(core,"scale",f,(.22*s,.12*s,.22*s))
    for i in range(7):
        a=math.tau*i/7
        p=shape("sphere",f"Petal {i}",(.34*math.sin(a),0,.34*math.cos(a)),(.18,.08,.34),petal,bloom)
        p.rotation_euler[1]=a
        for f,s in ((1,.001),(2360,.001),(2480,.25),(2630,1),(2700,1)):
            key(p,"scale",f,(.18*s,.08*s,.34*s))

    # Fixed camera and soft lighting to avoid discontinuities between chunks.
    bpy.ops.object.camera_add(location=(0,-13.5,6.2))
    cam=bpy.context.object
    target=Vector((0,0,.88))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO"
    cam.data.ortho_scale=12.6
    scene.camera=cam
    bpy.ops.object.light_add(type="AREA",location=(-4,-5,9))
    bpy.context.object.data.energy=1100
    bpy.context.object.data.shape="DISK"
    bpy.context.object.data.size=10
    bpy.ops.object.light_add(type="AREA",location=(4,4,7))
    bpy.context.object.data.energy=650
    bpy.context.object.data.size=7

def main():
    import json
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",default="project.json")
    parser.add_argument("--start",type=int,required=True)
    parser.add_argument("--end",type=int,required=True)
    parser.add_argument("--frames",required=True)
    a=parser.parse_args(args)
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8"))
    build(cfg)
    scene=bpy.context.scene
    scene.render.image_settings.file_format="JPEG"
    scene.render.image_settings.quality=82
    out=Path(a.frames)
    out.mkdir(parents=True,exist_ok=True)
    for f in range(a.start,a.end+1):
        file=out/f"f_{f:06d}.jpg"
        if file.exists() and file.stat().st_size>1024: continue
        scene.frame_set(f)
        scene.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED {f}/{a.end} {file}",flush=True)
if __name__=="__main__": main()
