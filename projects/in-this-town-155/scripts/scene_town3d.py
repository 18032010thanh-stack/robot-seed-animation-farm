"""Original low-poly 3D town animation: one deterministic five-second shot per invocation.
Blender 3.6-5.x; no imported assets, brand models, textures, or copyrighted music.
"""
import argparse, json, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parents[1]
STORY=json.loads((HERE/"stories"/"town_last_awake_155.json").read_text(encoding="utf-8"))
M={}

def material(name,color,metal=0,emission=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*color,1)
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=.72
    if emission:
        if "Emission Color" in p.inputs: p.inputs["Emission Color"].default_value=(*color,1)
        if "Emission Strength" in p.inputs: p.inputs["Emission Strength"].default_value=emission
    return m

def make_materials(day):
    global M
    M={
      "road":material("Midnight road",(0.095,.13,.21)),
      "wall":material("Ink blue building",(.16,.23,.37)),
      "wall2":material("Slate building",(.25,.31,.43)),
      "roof":material("Roof tile",(.21,.15,.27)),
      "wood":material("Dark brown wood",(.29,.17,.15)),
      "floor":material("Warm interior floor",(.23,.25,.36)),
      "light":material("Golden windows",(.95,.66,.24),emission=1.5),
      "off":material("Unlit windows",(.035,.065,.11)),
      "moon":material("Moon",(.95,.92,.72),emission=.7),
      "skin":material("Warm blocky skin",(.83,.57,.42)),
      "coat":material("Burgundy jacket",(.48,.16,.27)),
      "coat2":material("Dusk blue jacket",(.20,.38,.48)),
      "pants":material("Slate pants",(.10,.15,.26)),
      "hair":material("Dark hair",(.11,.08,.13)),
      "white":material("Soft white",(.84,.83,.78)),
      "black":material("Deep shadow",(.025,.025,.070)),
      "eyes":material("Glowing cyan eyes",(.17,.89,.96),emission=1.6),
      "red":material("Clock red",(.83,.22,.26)),
      "silver":material("Silver bell",(.65,.73,.80),metal=.75),
      "mist":material("Nightmare violet",(.22,.15,.39),emission=.06),
    }
    if day:
        M["wall"]=material("Sunlit walls",(.42,.46,.49))
        M["wall2"]=material("Sunlit slate",(.59,.57,.50))
        M["road"]=material("Sunrise road",(.31,.34,.42))

def obj(kind,name,xyz,scale,mat,segments=12,parent=None):
    if kind=="cube": bpy.ops.mesh.primitive_cube_add(size=1,location=xyz)
    elif kind=="sphere": bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=8,location=xyz)
    elif kind=="cyl": bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=1,depth=1,location=xyz)
    elif kind=="cone": bpy.ops.mesh.primitive_cone_add(vertices=segments,radius1=1,radius2=0,depth=1,location=xyz)
    else: raise ValueError(kind)
    o=bpy.context.object
    o.name=name; o.scale=scale; o.data.materials.append(mat)
    if parent:o.parent=parent
    return o

def parent_obj(name,x=0,y=0,z=0):
    o=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(o)
    o.location=(x,y,z)
    return o

def key(o,path,frame,value):
    setattr(o,path,value)
    o.keyframe_insert(data_path=path,frame=frame)

def make_actor(name,x,y,emotion="alert",color="coat",size=1.0):
    root=parent_obj(name)
    head=obj("cube",name+" head",(0,0,2.37),(.77,.69,.73),M["skin"],parent=root)
    obj("cube",name+" hair",(0,.02,2.77),(.83,.75,.21),M["hair"],parent=root)
    obj("cube",name+" torso",(0,0,1.43),(.88,.51,1.03),M[color],parent=root)
    for s in (-1,1):
        leg=obj("cube",name+f" leg{s}",(s*.22,0,.49),(.32,.48,.95),M["pants"],parent=root)
        hand=obj("cube",name+f" arm{s}",(s*.58,0,1.5),(.24,.37,.83),M["skin"],parent=root)
        for fr,angle in ((1,0),(20,.10*s),(42,-.14*s),(75,0)):
            hand.rotation_euler[1]=angle
            hand.keyframe_insert(data_path="rotation_euler",index=1,frame=fr)
        eye=obj("sphere",name+f" eye{s}",(s*.19,-.365,2.44),(.060,.040,.065),M["black"],parent=root)
        if emotion=="sleep": eye.scale.z=.018
        if emotion in ("shock","scared"): eye.scale=(.085,.045,.105)
    mouth=obj("cube",name+" mouth",(0,-.36,2.16),(.14,.042,.028 if emotion!="shock" else .11),M["hair"],parent=root)
    root.scale=(size,)*3
    for f,dz,turn in ((1,0,-.025),(22,.04,0),(42,0,.03),(62,.05,-.03),(75,0,0)):
        root.location=(x,y,dz)
        root.rotation_euler[2]=turn
        root.keyframe_insert(data_path="location",frame=f)
        root.keyframe_insert(data_path="rotation_euler",frame=f)
    return root

def make_guardian(name,x,y,size=1.0):
    root=parent_obj(name)
    obj("cone",name+" cloak",(0,0,1.72),(1.15,.97,3.15),M["black"],segments=8,parent=root)
    obj("sphere",name+" head",(0,0,3.6),(.52,.52,.77),M["black"],parent=root)
    for s in (-1,1):
        obj("sphere",name+f" glow-eye{s}",(s*.21,-.48,3.69),(.10,.048,.084),M["eyes"],parent=root)
    for s in (-1,1):
        obj("cube",name+f" limb{s}",(s*.83,0,2.10),(.22,.27,1.37),M["black"],parent=root)
    for f,dz in ((1,.02),(18,.10),(38,.22),(56,.08),(75,.02)):
        root.location=(x,y,dz)
        root.scale=(size,)*3
        root.keyframe_insert(data_path="location",frame=f)
    return root

def make_bell(x,y,z,animate=True):
    p=parent_obj("Silver bell",x,y,z)
    obj("cyl","Bell crown",(0,0,.31),(.12,.12,.07),M["silver"],parent=p)
    obj("cone","Bell body",(0,0,0),(.26,.26,.46),M["silver"],segments=12,parent=p)
    obj("sphere","Bell clapper",(0,0,-.32),(.085,.085,.085),M["silver"],parent=p)
    if animate:
        for f,v in ((1,-.15),(15,.2),(30,-.30),(45,.24),(60,-.14),(75,0)):
            p.rotation_euler[1]=v; p.keyframe_insert(data_path="rotation_euler",index=1,frame=f)

def make_town(index):
    dawn=index>=28
    obj("cube","Ground",(0,0,-.25),(18,24,.5),M["road"])
    obj("cube","Street",(0,-.6,-.005),(4,20,.05),M["floor"])
    obj("cube","Yellow line",(-.12,-.6,.025),(.025,20,.018),M["light"])
    obj("sphere","Moon or sunrise",(2,6,8.8),(.85,.85,.85),M["moon"])
    for k in range(-5,6):
        x=k*1.9
        if abs(x)<1.4:continue
        h=2.9+(k*k%3)*.68
        y=3+(abs(k)%2)*.35
        wall=M["wall"] if k%2 else M["wall2"]
        obj("cube",f"House {k}",(x,y,h/2),(1.5,1.6,h),wall)
        obj("cone",f"Roof {k}",(x,y,h+.32),(1.10,1.05,.78),M["roof"],segments=4)
        for r in range(2):
            for s in (-1,1):
                lit=(index<11 or index>=28 or (index==12 and k==2)) and ((abs(k)+r)%3!=0)
                obj("cube",f"Window {k},{r},{s}",(x+s*.37,y-.83,1.05+r*1.12),
                     (.32,.045,.53),M["light"] if lit else M["off"])
    for s in (-1,1):
        for j in range(3):
            x=s*2.0; yy=-3+j*2.8
            obj("cyl","Lamp post",(x,yy,1.1),(.055,.055,2.2),M["silver"])
            obj("sphere","Street lamp",(x,yy,2.32),(.18,.18,.18),M["light"])
    if index in (4,5):
        obj("cube","Milk cafe",(1.4,-1.1,1.1),(1.5,1.3,2.2),M["wall2"])
        obj("cube","Coffee counter",(1.25,-2.04,.75),(1.8,.40,.5),M["wood"])
        obj("cyl","Warm milk cup",(1.1,-2.06,1.12),(.14,.14,.23),M["white"])
    if index>=24 and index<=27:
        for j in range(6):
            root=parent_obj(f"Crawling nightmare {j}",(-1.4+j*.6,1.0,1.7))
            o=obj("sphere",f"Nightmare vapor {j}",(0,0,0),(.38,.27,.76),M["mist"],parent=root)
            for fr,x in ((1,0),(38,.22*math.sin(j)),(75,-.06)):
                root.location.x=(-1.4+j*.6)+x
                root.keyframe_insert(data_path="location",index=0,frame=fr)

def make_room(index,window=True):
    obj("cube","Floor",(0,0,-.27),(13,13,.55),M["floor"])
    obj("cube","Back wall",(0,3,3.15),(12,.40,6.5),M["wall"])
    obj("cube","Window glass",(1.24,2.72,3.45),(1.85,.08,2.25),M["off"])
    for s in (-1,1):
        obj("cube",f"Window frame {s}",(1.24+s*.95,2.57,3.48),(.10,.16,2.30),M["wood"])
    obj("cube","Window bar",(1.24,2.57,3.48),(.08,.17,2.30),M["wood"])
    obj("cube","Window sill",(1.24,2.51,2.34),(2.06,.27,.10),M["wood"])
    obj("cube","Bed base",(-1.5,.0,.43),(2.2,2.35,.55),M["wood"])
    obj("cube","Bed mattress",(-1.5,-.05,.75),(2.07,2.15,.23),M["white"])
    obj("cube","Pillow",(-1.50,.64,.94),(1.30,.45,.25),M["light"])
    obj("cube","Bedside lamp",(-2.25,-1.32,1.35),(.22,.22,.37),M["light"])
    if index in (14,15,25,30):
        make_guardian("Silhouette outside window",1.30,2.32,.57)
    if index in (13,14):
        for f,v in ((1,.0),(22,.16),(41,-.14),(75,.03)):
            cam=bpy.context.scene.camera
            cam.rotation_euler.z=v
            cam.keyframe_insert(data_path="rotation_euler",index=2,frame=f)

def make_clock(index):
    obj("cube","Clock background",(0,3,3.0),(10,.45,10),M["wall"])
    dial=obj("cyl","Clock dial",(0,0,3.25),(2.18,2.18,.14),M["white"],segments=48)
    dial.rotation_euler[0]=math.pi/2
    for n in range(12):
        a=2*math.pi*n/12
        x=math.sin(a)*1.7
        z=3.25+math.cos(a)*1.7
        obj("sphere",f"Clock marker {n}",(x,-.17,z),(.12,.06,.12),M["black"])
    hand1=obj("cube","Clock minute hand",(0,-.23,3.79),(.085,.07,1.19),M["black"])
    hand2=obj("cube","Clock hour hand",(-.35,-.25,3.32),(.69,.08,.092),M["red"])
    for f,v in ((1,-.2),(38,.3),(75,.7)):
        hand1.rotation_euler[1]=v
        hand1.keyframe_insert(data_path="rotation_euler",index=1,frame=f)

def make_ghost_set(index):
    obj("cube","Guardian shadows floor",(0,0,-.20),(15,15,.4),M["floor"])
    obj("cube","Dark arch",(0,3,2.65),(12,.40,5.5),M["wall"])
    for x in (-2.6,2.6):
        obj("cyl","Arch column",(x,2,2.2),(.30,.30,4.4),M["wall2"],segments=10)
    make_guardian("Guardian",.40,.90,1.0)
    if index in (17,20):
        obj("cube","Guardian sign",(1.42,-.90,2.18),(1.5,.13,.75),M["white"])
    if index in (26,27):
        make_bell(-.80,-1.15,1.72)

def setup_camera(index):
    bpy.ops.object.camera_add(location=(0,-10.7,4.4))
    c=bpy.context.object
    c.name="Portrait camera"
    c.rotation_euler=(Vector((0,.6,2.45))-c.location).to_track_quat("-Z","Y").to_euler()
    c.data.type="ORTHO"
    c.data.ortho_scale=7.8
    bpy.context.scene.camera=c
    # Subtle push-in; rebuilt using identical frame coordinates in each shot.
    for f,scale in ((1,7.85),(75,7.55)):
        c.data.ortho_scale=scale
        c.data.keyframe_insert(data_path="ortho_scale",frame=f)

def create(index,quality):
    shot=STORY["shots"][index]
    scene_name=shot["scene"]
    dawn=index>=28
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    make_materials(dawn)
    scene=bpy.context.scene
    scene.render.resolution_x=STORY["width"]
    scene.render.resolution_y=STORY["height"]
    scene.render.resolution_percentage=100
    scene.render.fps=STORY["fps"]
    scene.render.image_settings.file_format="JPEG"
    scene.render.image_settings.quality=85
    scene.render.film_transparent=False
    world=bpy.data.worlds.new("Original town night") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world=world
    world.use_nodes=True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value=(
        (.46,.39,.30,1) if dawn else (.055,.075,.17,1))
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.8
    setup_camera(index)
    if quality=="workbench":
        scene.render.engine="BLENDER_WORKBENCH"
        scene.display.shading.light="STUDIO"
        scene.display.shading.color_type="MATERIAL"
        scene.display.shading.show_shadows=True
        scene.display.shading.show_cavity=True
    else:
        scene.render.engine="CYCLES"
        scene.cycles.device="CPU"
        scene.cycles.samples=6 if quality=="cycles" else 3
        if hasattr(scene.cycles,"use_denoising"):scene.cycles.use_denoising=True
    if quality!="workbench":
        bpy.ops.object.light_add(type="AREA",location=(-3,-5,9))
        bpy.context.object.data.energy=900 if not dawn else 1550
        bpy.context.object.data.shape="DISK"
        bpy.context.object.data.size=9.0
        bpy.ops.object.light_add(type="AREA",location=(4,3,7))
        bpy.context.object.data.energy=300 if not dawn else 700
        bpy.context.object.data.size=8.0

    if scene_name in ("town","street","cafe","roof"):
        make_town(index)
        if scene_name=="street":
            make_actor("Sleepless character",-1.0,-1.4,shot["emotion"])
            make_actor("Sleepy neighbor",1.25,-.5,"sleep","coat2",.78)
        else:make_actor("The last awake",-.18,-1.85,shot["emotion"])
        if scene_name=="roof":make_bell(.8,-1.5,2.0)
    elif scene_name in ("room","window","bell"):
        make_room(index)
        make_actor("Hero",-.95,-1.25,shot["emotion"])
        if scene_name=="bell":make_bell(.7,-1.25,1.50)
    elif scene_name=="clock":
        make_clock(index)
    elif scene_name in ("ghost","shadow"):
        make_ghost_set(index)
        make_actor("Tiny human",-1.5,-1.85,shot["emotion"],size=.73)
    else:
        make_town(index);make_actor("Hero",0,-1.7,shot["emotion"])
    return scene

def main():
    raw=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--shot",type=int,required=True)
    p.add_argument("--start",type=int,default=1)
    p.add_argument("--end",type=int,default=75)
    p.add_argument("--output",required=True)
    p.add_argument("--quality",choices=("workbench","fast","cycles"),default="fast")
    a=p.parse_args(raw)
    if not (0<=a.shot<len(STORY["shots"])):p.error("Invalid shot index")
    if not (1<=a.start<=a.end<=STORY["shot_seconds"]*STORY["fps"]):p.error("Invalid shot frame interval")
    scene=create(a.shot,a.quality)
    out=Path(a.output)
    out.mkdir(parents=True,exist_ok=True)
    per=STORY["shot_seconds"]*STORY["fps"]
    for frame in range(a.start,a.end+1):
        global_frame=a.shot*per+frame
        file=out/("f_%06d.jpg"%global_frame)
        if file.exists() and file.stat().st_size>1024:continue
        scene.frame_set(frame)
        scene.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
        if frame==a.start or frame==a.end or frame%15==0:
            print("RENDERED",a.shot,frame,str(file),flush=True)

if __name__=="__main__":main()
