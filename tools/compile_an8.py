#!/usr/bin/env python3
"""Anim8or .an8 -> Baldi Anim Studio compiler.

v3 compiles the actual FIGURE bind pose instead of blindly stacking the
standalone Object-editor parts.  That matters for this Baldi source because:
  * the saved standalone arm objects are vertical;
  * the Figure rotates them into the horizontal bind pose;
  * RArm2/LArm2 standalone objects are leftovers and are NOT referenced by the
    Baldi figure;
  * the real arm object is skinned to Arm1/Arm2.  We split its components by
    dominant weight so the elbow stays independently animatable.

The result is a clean bind-pose mesh per editable control, with pivots taken
from the actual Anim8or bone joints.
"""
import re, json, math, argparse, os, collections

NUM=r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'

def strip_comments(s):
    return re.sub(r'/\*.*?\*/','',s,flags=re.S)

def extract_top_blocks(s):
    out=[]; i=0; n=len(s); pat=re.compile(r'([A-Za-z_][\w]*)\s*\{')
    while i<n:
        m=pat.search(s,i)
        if not m: break
        kw=m.group(1); brace=s.find('{',m.start()); d=1; j=brace+1; ins=False; esc=False
        while j<n and d:
            c=s[j]
            if ins:
                if esc: esc=False
                elif c=='\\': esc=True
                elif c=='"': ins=False
            else:
                if c=='"': ins=True
                elif c=='{': d+=1
                elif c=='}': d-=1
            j+=1
        out.append((kw,s[m.start():j])); i=j
    return out

def inner(block):
    a=block.find('{'); return block[a+1:-1] if a>=0 else ''

def direct_chunks(s):
    out=[]; i=0; n=len(s)
    while i<n:
        if s[i]=='"':
            i+=1
            while i<n:
                if s[i]=='\\': i+=2; continue
                if s[i]=='"': i+=1; break
                i+=1
            continue
        c=s[i]
        if c.isalpha() or c=='_':
            j=i+1
            while j<n and (s[j].isalnum() or s[j]=='_'): j+=1
            k=j
            while k<n and s[k].isspace(): k+=1
            if k<n and s[k]=='{':
                kw=s[i:j]; d=1; p=k+1; ins=False; esc=False
                while p<n and d:
                    cc=s[p]
                    if ins:
                        if esc: esc=False
                        elif cc=='\\': esc=True
                        elif cc=='"': ins=False
                    else:
                        if cc=='"': ins=True
                        elif cc=='{': d+=1
                        elif cc=='}': d-=1
                    p+=1
                out.append((kw,s[i:p])); i=p; continue
        i+=1
    return out

def children(block, kw=None):
    arr=direct_chunks(inner(block))
    return [b for k,b in arr if kw is None or k==kw]

def child(block, kw):
    for k,b in direct_chunks(inner(block)):
        if k==kw:return b
    return None

def first_string(block, default=''):
    m=re.search(r'\{\s*"([^"]*)"',block or '')
    return m.group(1) if m else default

def component_name(block, default=''):
    nb=child(block,'name')
    return first_string(nb,default) if nb else default

def scalar(block, kw, default=0.0):
    b=child(block,kw)
    if not b:return default
    m=re.search(NUM,inner(b)); return float(m.group()) if m else default

def ints(block, kw, default=(12,8)):
    b=child(block,kw)
    if not b:return default
    vals=re.findall(r'-?\d+',inner(b))
    return tuple(map(int,vals[:len(default)])) if vals else default

def vec3(block, kw='origin', default=(0,0,0)):
    b=child(block,kw)
    if not b:return default
    m=re.search(r'\(\s*('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s*\)',inner(b))
    return tuple(map(float,m.groups())) if m else default

def quat(block, kw='orientation', default=(0,0,0,1)):
    b=child(block,kw)
    if not b:return default
    m=re.search(r'\(\s*('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s*\)',inner(b))
    return tuple(map(float,m.groups())) if m else default

def qnorm(q):
    l=math.sqrt(sum(x*x for x in q)) or 1
    return tuple(x/l for x in q)

def qmul(a,b):
    ax,ay,az,aw=a; bx,by,bz,bw=b
    return qnorm((aw*bx+ax*bw+ay*bz-az*by,
                  aw*by-ax*bz+ay*bw+az*bx,
                  aw*bz+ax*by-ay*bx+az*bw,
                  aw*bw-ax*bx-ay*by-az*bz))

def qrot(q,v):
    x,y,z,w=qnorm(q); vx,vy,vz=v
    tx=2*(y*vz-z*vy); ty=2*(z*vx-x*vz); tz=2*(x*vy-y*vx)
    return (vx+w*tx+(y*tz-z*ty), vy+w*ty+(z*tx-x*tz), vz+w*tz+(x*ty-y*tx))

def compose(a,b):
    ap,aq=a; bp,bq=b; r=qrot(aq,bp)
    return ((ap[0]+r[0],ap[1]+r[1],ap[2]+r[2]), qmul(aq,bq))

def base_tf(block):
    b=child(block,'base')
    if not b:return ((0,0,0),(0,0,0,1))
    return (vec3(b,'origin'), quat(b,'orientation'))

def tf_point(tf,p):
    r=qrot(tf[1],p); return (r[0]+tf[0][0],r[1]+tf[0][1],r[2]+tf[0][2])

def norm(v):
    l=math.sqrt(sum(x*x for x in v)); return tuple(x/l for x in v) if l>1e-12 else (0,0,1)
def sub(a,b): return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def material_from_block(b):
    name=first_string(b,'material'); surf=child(b,'surface') or b
    def color_component(kind, fallback):
        c=child(surf,kind)
        if not c:return fallback
        rgb=child(c,'rgb')
        if rgb:
            vals=re.findall(r'-?\d+',inner(rgb))[:3]
            if len(vals)==3:return [int(v)/255 for v in vals]
        return fallback
    rgb=child(surf,'rgb'); base=[0.75,0.75,0.75]
    if rgb:
        vals=re.findall(r'-?\d+',inner(rgb))[:3]
        if len(vals)==3:base=[int(v)/255 for v in vals]
    diffuse=color_component('diffuse',base); ambient=color_component('ambient',diffuse); specular=color_component('specular',[1,1,1])
    def factor(kind,default):
        c=child(surf,kind); return scalar(c,'factor',default) if c else default
    return {'name':name,'diffuse':diffuse,'ambient':ambient,'specular':specular,
            'ka':factor('ambient',0.3),'kd':factor('diffuse',0.7),'ks':factor('specular',0.2),
            'shininess':scalar(surf,'phongsize',32.0),'alpha':scalar(surf,'alpha',1.0)}

def polygon_normal(pts, idx):
    # Newell normal is stable for arbitrary planar n-gons.
    nx=ny=nz=0.0
    for i,aidx in enumerate(idx):
        bidx=idx[(i+1)%len(idx)]; a=pts[aidx]; b=pts[bidx]
        nx+=(a[1]-b[1])*(a[2]+b[2])
        ny+=(a[2]-b[2])*(a[0]+b[0])
        nz+=(a[0]-b[0])*(a[1]+b[1])
    return norm((nx,ny,nz))

def project_polygon_2d(pts, idx):
    n=polygon_normal(pts,idx); ax=max(range(3), key=lambda i:abs(n[i]))
    if ax==0:return [(pts[i][1],pts[i][2]) for i in idx]
    if ax==1:return [(pts[i][0],pts[i][2]) for i in idx]
    return [(pts[i][0],pts[i][1]) for i in idx]

def signed_area2(poly):
    return sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))

def point_in_tri2(p,a,b,c,eps=1e-10):
    def cr(u,v,w):return (v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0])
    c1,c2,c3=cr(a,b,p),cr(b,c,p),cr(c,a,p)
    return (c1>=-eps and c2>=-eps and c3>=-eps) or (c1<=eps and c2<=eps and c3<=eps)

def triangulate_polygon(pts, idx):
    """Ear-clip an Anim8or n-gon instead of fan-triangulating it.

    Fan triangulation was the cause of the long triangular shard through
    Baldi's lip: concave mouth polygons were connected to vertex 0 across the
    face.  Ear clipping keeps triangles inside the original polygon.
    """
    idx=[i for i in idx if 0<=i<len(pts)]
    if len(idx)<3:return []
    if len(idx)==3:return [tuple(idx)]
    poly=project_polygon_2d(pts,idx)
    orientation=1 if signed_area2(poly)>=0 else -1
    remaining=list(range(len(idx))); out=[]; guard=0
    while len(remaining)>3 and guard<len(idx)*len(idx)*4:
        guard+=1; found=False
        for q in range(len(remaining)):
            ia=remaining[(q-1)%len(remaining)]; ib=remaining[q]; ic=remaining[(q+1)%len(remaining)]
            a,b,c=poly[ia],poly[ib],poly[ic]
            cross2=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
            if orientation*cross2<=1e-10:continue
            if any(point_in_tri2(poly[j],a,b,c) for j in remaining if j not in (ia,ib,ic)):continue
            out.append((idx[ia],idx[ib],idx[ic])); remaining.pop(q); found=True; break
        if not found:break
    if len(remaining)==3:out.append(tuple(idx[i] for i in remaining))
    if len(out)!=len(idx)-2:
        # Degenerate/self-intersecting source face fallback.  This is rare and
        # safer than silently deleting geometry.
        return [(idx[0],idx[k],idx[k+1]) for k in range(1,len(idx)-1)]
    return out

def catmull_clark_once(pts, faces):
    """One Catmull-Clark step. faces = [(vertex_indices, material_index), ...]."""
    if not faces:return pts,faces
    face_points=[]
    for idx,_ in faces:
        face_points.append(tuple(sum(pts[v][a] for v in idx)/len(idx) for a in range(3)))
    edge_faces=collections.defaultdict(list); vertex_faces=collections.defaultdict(list); vertex_edges=collections.defaultdict(set)
    for fi,(idx,_) in enumerate(faces):
        for v in idx:vertex_faces[v].append(fi)
        for j,v in enumerate(idx):
            w=idx[(j+1)%len(idx)]; e=tuple(sorted((v,w))); edge_faces[e].append(fi); vertex_edges[v].add(e); vertex_edges[w].add(e)
    new_vertex=[]
    for vi,p in enumerate(pts):
        edges=list(vertex_edges.get(vi,()))
        if not edges:new_vertex.append(p);continue
        boundary=[e for e in edges if len(edge_faces[e])==1]
        if boundary:
            neigh=[]
            for e in boundary:
                neigh.append(e[1] if e[0]==vi else e[0])
            # Standard cubic B-spline boundary rule. Corners with only one
            # boundary neighbor remain stable instead of exploding.
            if len(neigh)>=2:
                a,b=pts[neigh[0]],pts[neigh[1]]
                new_vertex.append(tuple((6*p[k]+a[k]+b[k])/8 for k in range(3)))
            else:new_vertex.append(p)
        else:
            fids=vertex_faces[vi]; n=len(fids)
            F=tuple(sum(face_points[f][k] for f in fids)/n for k in range(3))
            mids=[]
            for e in edges:
                a,b=pts[e[0]],pts[e[1]];mids.append(tuple((a[k]+b[k])/2 for k in range(3)))
            R=tuple(sum(m[k] for m in mids)/len(mids) for k in range(3))
            new_vertex.append(tuple((F[k]+2*R[k]+(n-3)*p[k])/n for k in range(3)))
    out_pts=list(new_vertex)
    edge_idx={}
    for e,fids in edge_faces.items():
        a,b=pts[e[0]],pts[e[1]]
        if len(fids)>=2:
            fp1,fp2=face_points[fids[0]],face_points[fids[1]]
            ep=tuple((a[k]+b[k]+fp1[k]+fp2[k])/4 for k in range(3))
        else:ep=tuple((a[k]+b[k])/2 for k in range(3))
        edge_idx[e]=len(out_pts);out_pts.append(ep)
    face_idx=[]
    for fp in face_points:face_idx.append(len(out_pts));out_pts.append(fp)
    out_faces=[]
    for fi,(idx,mi) in enumerate(faces):
        n=len(idx)
        for j,v in enumerate(idx):
            prev=idx[(j-1)%n];nxt=idx[(j+1)%n]
            out_faces.append(([v,edge_idx[tuple(sorted((v,nxt)))],face_idx[fi],edge_idx[tuple(sorted((prev,v)))]],mi))
    return out_pts,out_faces

def mesh_data(block, tf, fallback_mat, subdiv_levels=0):
    pb=child(block,'points'); fb=child(block,'faces')
    if not pb or not fb:return None
    pts=[tuple(map(float,m)) for m in re.findall(r'\(\s*('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s*\)',inner(pb))]
    pts=[tf_point(tf,p) for p in pts]
    matlist=[]; ml=child(block,'materiallist')
    if ml:
        for mb in children(ml,'materialname'):matlist.append(first_string(mb,''))
    if not matlist: matlist=[fallback_mat]
    faces=[]
    face_re=r'(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\(\s*((?:\(\s*-?\d+(?:\s+-?\d+){0,2}\s*\)\s*)+)\)'
    for m in re.finditer(face_re,inner(fb)):
        n=int(m.group(1)); mi=int(m.group(3)); vids=re.findall(r'\(\s*(-?\d+)',m.group(5)); idx=[int(x) for x in vids[:n]]
        if len(idx)>=3 and max(idx)<len(pts) and min(idx)>=0:faces.append((idx,mi))
    # Anim8or stores Subdivision objects as their control cage.  The old web
    # parser rendered that cage directly, which made the lips look torn/spiky.
    # Use the saved Working level (capped at 2 for interactive size).
    for _ in range(max(0,min(2,int(subdiv_levels or 0)))):
        pts,faces=catmull_clark_once(pts,faces)
    acc=[[0.0,0.0,0.0] for _ in pts]; tris_by_mat={}
    for idx,mi in faces:
        for tri in triangulate_polygon(pts,idx):
            a,b,c=[pts[x] for x in tri]; fn=norm(cross(sub(b,a),sub(c,a)))
            for vi in tri:
                acc[vi][0]+=fn[0];acc[vi][1]+=fn[1];acc[vi][2]+=fn[2]
            mn=matlist[mi] if 0<=mi<len(matlist) else fallback_mat
            tris_by_mat.setdefault(mn,[]).extend(tri)
    return {'component':component_name(block,'mesh'),'positions':pts,'normals':[norm(v) for v in acc],'groups':tris_by_mat}

def sphere_data(block, tf, fallback_mat):
    d=scalar(block,'diameter',10.0); lon,lat=ints(block,'longlat',(12,8)); lon=max(3,lon);lat=max(2,lat); r=d/2; pts=[]
    for j in range(lat+1):
        th=math.pi*j/lat; y=math.cos(th)*r; rr=math.sin(th)*r
        for i in range(lon):
            ph=2*math.pi*i/lon; pts.append(tf_point(tf,(rr*math.cos(ph),y,rr*math.sin(ph))))
    idx=[]
    for j in range(lat):
        for i in range(lon):
            ni=(i+1)%lon; a=j*lon+i;b=j*lon+ni;c=(j+1)*lon+i;d2=(j+1)*lon+ni
            if j>0:idx += [a,c,b]
            if j<lat-1:idx += [b,c,d2]
    acc=[[0,0,0] for _ in pts]
    for k in range(0,len(idx),3):
        a,b,c=[pts[x] for x in idx[k:k+3]];fn=norm(cross(sub(b,a),sub(c,a)))
        for vi in idx[k:k+3]:acc[vi][0]+=fn[0];acc[vi][1]+=fn[1];acc[vi][2]+=fn[2]
    return {'component':component_name(block,'sphere'),'positions':pts,'normals':[norm(v) for v in acc],'groups':{fallback_mat:idx}}

def cylinder_data(block, tf, fallback_mat):
    length=scalar(block,'length',10); d1=scalar(block,'diameter',5)/2; d2=scalar(block,'topdiameter',d1*2)/2; lon,_=ints(block,'longlat',(12,8));lon=max(3,lon);pts=[]
    for y,r in [(-length/2,d1),(length/2,d2)]:
        for i in range(lon):
            ph=2*math.pi*i/lon;pts.append(tf_point(tf,(r*math.cos(ph),y,r*math.sin(ph))))
    idx=[]
    for i in range(lon):
        ni=(i+1)%lon;a=i;b=ni;c=lon+i;d=lon+ni;idx += [a,c,b,b,c,d]
    if child(block,'capstart'):
        ci=len(pts);pts.append(tf_point(tf,(0,-length/2,0)))
        for i in range(lon):idx += [ci,(i+1)%lon,i]
    if child(block,'capend'):
        ci=len(pts);pts.append(tf_point(tf,(0,length/2,0)))
        for i in range(lon):idx += [ci,lon+i,lon+(i+1)%lon]
    acc=[[0,0,0] for _ in pts]
    for k in range(0,len(idx),3):
        tri=idx[k:k+3];a,b,c=[pts[x] for x in tri];fn=norm(cross(sub(b,a),sub(c,a)))
        for vi in tri:acc[vi][0]+=fn[0];acc[vi][1]+=fn[1];acc[vi][2]+=fn[2]
    return {'component':component_name(block,'cylinder'),'positions':pts,'normals':[norm(v) for v in acc],'groups':{fallback_mat:idx}}

def walk_geometry(block, tf, fallback='___default___', root_object=''):
    out=[]
    for kw,b in direct_chunks(inner(block)):
        if kw=='group':out += walk_geometry(b,compose(tf,base_tf(b)),fallback,root_object)
        elif kw in ('mesh','subdivision'):
            local=compose(tf,base_tf(b));matb=child(b,'material');mat=first_string(matb,fallback) if matb else fallback
            levels=(min(2,int(scalar(b,'working',0))) if root_object in ('Mouth1','Mouth2') else 0) if kw=='subdivision' else 0
            md=mesh_data(b,local,mat,levels)
            if md:out.append(md)
        elif kw=='sphere':
            local=compose(tf,base_tf(b));matb=child(b,'material');mat=first_string(matb,fallback) if matb else fallback;out.append(sphere_data(b,local,mat))
        elif kw=='cylinder':
            local=compose(tf,base_tf(b));matb=child(b,'material');mat=first_string(matb,fallback) if matb else fallback;out.append(cylinder_data(b,local,mat))
    return out

def transform_mesh(md,tf):
    return {'component':md['component'],
            'positions':[tf_point(tf,p) for p in md['positions']],
            'normals':[norm(qrot(tf[1],n)) for n in md['normals']],
            'groups':{k:list(v) for k,v in md['groups'].items()}}

def r4(x):return round(float(x),5)
def compact_mesh(m):
    return {'p':[r4(v) for p in m['positions'] for v in p],
            'n':[r4(v) for p in m['normals'] for v in p],
            'g':[{'m':name,'i':idx} for name,idx in m['groups'].items() if idx],
            'c':m.get('component','')}

def bbox_of(meshes):
    pts=[]
    for m in meshes:
        p=m['p'];pts.extend(zip(p[0::3],p[1::3],p[2::3]))
    if not pts:return [[0,0,0],[0,0,0]]
    return [[r4(min(p[i] for p in pts)) for i in range(3)],[r4(max(p[i] for p in pts)) for i in range(3)]]

def shift_compact_meshes(meshes, delta):
    for m in meshes:
        p=m['p']
        for i in range(0,len(p),3):
            p[i]=r4(p[i]+delta[0]);p[i+1]=r4(p[i+1]+delta[1]);p[i+2]=r4(p[i+2]+delta[2])

def snap_finger_to_joint(name, meshes, pivot):
    """Anim8or fan models sometimes keep finger primitive bases a few units
    away from the actual Figure joint. Figure mode visually treats the bone
    joint as the attachment point; bake that attachment so the web bind pose
    does not show floating fingers. This is a bind-pose correction only; the
    real joint pivot remains untouched."""
    if not re.match(r'^[RL](Thumb|Index|Middle|Ring|Pinky)[12]$', name):
        return [0.0,0.0,0.0]
    bb=bbox_of(meshes)
    dims=[bb[1][i]-bb[0][i] for i in range(3)]
    axis=max(range(3), key=lambda i:dims[i])
    center=[(bb[0][i]+bb[1][i])*0.5 for i in range(3)]
    candidates=[]
    for side in (0,1):
        q=center[:];q[axis]=bb[side][axis]
        candidates.append(q)
    endpoint=min(candidates,key=lambda q:sum((q[i]-pivot[i])**2 for i in range(3)))
    delta=[pivot[i]-endpoint[i] for i in range(3)]
    # Only correct small attachment offsets. A giant shift means the source
    # uses a different modeling convention and should not be guessed at.
    if math.sqrt(sum(x*x for x in delta))>20:
        return [0.0,0.0,0.0]
    shift_compact_meshes(meshes,delta)
    return [r4(x) for x in delta]

def hierarchy(parts):
    parent={n:'Root' for n in parts}
    for n in ['Head','RArm1','LArm1','RLeg1','LLeg1']:
        if n in parent:parent[n]='Body'
    for n in ['REye','LEye','REyeBrow','LEyeBrow','Mouth1','Mouth2']:
        if n in parent:parent[n]='Head'
    for a,b in [('RArm2','RArm1'),('RHand','RArm2'),('LArm2','LArm1'),('LHand','LArm2'),('RLeg2','RLeg1'),('RShoe','RLeg2'),('LLeg2','LLeg1'),('LShoe','LLeg2'),('Ruler','RHand')]:
        if a in parent and b in parts:parent[a]=b
    for s in 'RL':
        hand=s+'Hand'
        for f in ['Thumb','Index','Middle','Ring','Pinky']:
            a=s+f+'1';b=s+f+'2'
            if a in parent and hand in parts:parent[a]=hand
            if b in parent and a in parts:parent[b]=a
    return parent

def dominant_weight_map(named):
    weighted=[first_string(x) for x in children(named,'weightedby')]
    out={}
    if not weighted:return weighted,out
    for wb in children(named,'weights'):
        comp=first_string(wb,''); sums=collections.defaultdict(float)
        for bi,w in re.findall(r'\(\s*(\d+)\s+('+NUM+r')\s*\)',inner(wb)):
            bi=int(bi)
            if 0<=bi<len(weighted):sums[bi]+=float(w)
        if sums:out[comp]=weighted[max(sums,key=sums.get)]
    return weighted,out

def part_from_control_bone(bone,ref):
    mp={'RightArm1':'RArm1','RightArm2':'RArm2','LeftArm1':'LArm1','LeftArm2':'LArm2','LLeg':'LShoe'}
    if bone in mp:return mp[bone]
    if re.match(r'^[RL](Thumb|Index|Middle|Ring|Pinky)[12]$',bone):return bone
    if bone in ('Body','Head','REye','LEye','REyeBrow','LEyeBrow','Mouth1','Mouth2','RLeg1','RLeg2','RShoe','LLeg1','LLeg2','LShoe'):return bone
    return ref

def compile_file(src):
    text=strip_comments(open(src,encoding='utf-8',errors='ignore').read())
    tops=extract_top_blocks(text);objects={};global_mats={}
    for kw,b in tops:
        if kw!='object':continue
        name=first_string(b,'');mats={}
        for mb in children(b,'material'):
            m=material_from_block(mb);mats[m['name']]=m
        if '___default___' not in mats:
            mats['___default___']={'name':'___default___','diffuse':[.75,.75,.75],'ambient':[.75,.75,.75],'specular':[1,1,1],'ka':.3,'kd':.7,'ks':.2,'shininess':32,'alpha':1}
        # Anim8or materials are object-local. Previous compilers merged equal
        # names globally which could make a face inherit another object's
        # "-- default --" material. Scope IDs by object to preserve source.
        scoped={}
        for mn,mat in mats.items():
            mid=f'{name}::{mn}'; scoped[mn]=mid; global_mats[mid]=dict(mat)
        meshes=walk_geometry(b,((0,0,0),(0,0,0,1)),root_object=name)
        for md in meshes:
            ng={}
            for mn,idx in md['groups'].items():
                # Mouth2 contains a tiny orphan/default cap in this source.
                # Anim8or does not show it as part of the red lip surface; it
                # is the little spike visible in the old web parser.
                if name=='Mouth2' and mn.strip() in ('-- default --','___default___') and len(idx)<=18:
                    continue
                ng[scoped.get(mn,f'{name}::{mn}')]=idx
            md['groups']=ng
        objects[name]={'block':b,'meshes':meshes,'materials':mats,'scoped':scoped}
    fig=None
    for kw,b in tops:
        if kw=='figure' and first_string(b,'')=='Baldi':fig=b;break
    if not fig:raise RuntimeError('Baldi figure bulunamadı; bu derleyici gerçek figure bind pose ister.')

    bone_info={};attachments=[]
    def walk_bone(b,parent_tf=((0,0,0),(0,0,0,1)),parent_len=0,parent_name=None,path=''):
        name=first_string(b,'bone');start_tf=compose(parent_tf,((0,parent_len,0),(0,0,0,1)));world_tf=compose(start_tf,((0,0,0),quat(b,'orientation',(0,0,0,1))));length=scalar(b,'length',0)
        bone_info[name]={'name':name,'tf':world_tf,'start':world_tf[0],'end':tf_point(world_tf,(0,length,0)),'length':length,'parent':parent_name,'path':path+'/'+name}
        for kw,ch in direct_chunks(inner(b)):
            if kw=='namedobject':attachments.append((name,ch))
            elif kw=='bone':walk_bone(ch,world_tf,length,name,path+'/'+name)
    walk_bone(child(fig,'bone'))

    part_meshes=collections.defaultdict(list);pivots={};source_controls={}
    for base_bone,named in attachments:
        ref=first_string(named,'')
        if ref not in objects:continue
        bind_tf=compose(bone_info[base_bone]['tf'],base_tf(named))
        weighted,dom=dominant_weight_map(named)
        for md in objects[ref]['meshes']:
            # Only the full arm namedobjects are intentionally split into Arm1/Arm2
            # controls.  Other namedobjects may contain a weightedby list even when
            # every vertex belongs to the base bone (RHand/LHand do this), and
            # treating those as the forearm would swallow the hand mesh.
            split_skin = ref in ('RArm1','LArm1') and bool(weighted)
            target_bone=dom.get(md['component'],base_bone) if split_skin else base_bone
            if split_skin:
                part=part_from_control_bone(target_bone,ref)
            else:
                # Left fingers reuse right-hand source Objects; name them after the
                # actual left-side figure bone instead of the referenced Object.
                if ref.startswith('R') and re.match(r'^L(Thumb|Index|Middle|Ring|Pinky)[12]$',base_bone):part=base_bone
                else:part=ref
            part_meshes[part].append(compact_mesh(transform_mesh(md,bind_tf)))
            source_controls.setdefault(part,target_bone if weighted else base_bone)
        # pivot for rigid attachment controls
        if ref in part_meshes and ref not in pivots:
            pivots[ref]=list(bone_info[base_bone]['start'])

    # Exact joint pivots from the real figure skeleton.
    control_bones={'Body':'Body','Head':'Head','RArm1':'RightArm1','RArm2':'RightArm2','LArm1':'LeftArm1','LArm2':'LeftArm2',
                   'RLeg1':'RLeg1','RLeg2':'RLeg2','RShoe':'RShoe','LLeg1':'LLeg1','LLeg2':'LLeg2','LShoe':'LLeg'}
    for s in 'RL':
        for f in ['Thumb','Index','Middle','Ring','Pinky']:
            control_bones[s+f+'1']=s+f+'1';control_bones[s+f+'2']=s+f+'2'
    for p,bn in control_bones.items():
        if p in part_meshes and bn in bone_info:pivots[p]=list(bone_info[bn]['start'])
    # Hand rotation is more useful at the wrist, the end of forearm bone.
    if 'RHand' in part_meshes:pivots['RHand']=list(bone_info['RightArm2']['end'])
    if 'LHand' in part_meshes:pivots['LHand']=list(bone_info['LeftArm2']['end'])
    # Facial pieces: use their own attachment joint when available, otherwise center.

    parts={};corrections={}
    for n,meshes in part_meshes.items():
        if not meshes:continue
        bb=bbox_of(meshes)
        pv=pivots.get(n,[(bb[0][i]+bb[1][i])/2 for i in range(3)])
        delta=snap_finger_to_joint(n,meshes,pv)
        if any(abs(x)>1e-6 for x in delta):corrections[n]={'bindSnap':delta}
        bb=bbox_of(meshes)
        parts[n]={'name':n,'meshes':meshes,'bbox':bb,'pivot':[r4(x) for x in pv],'sourceBone':source_controls.get(n,'')}
    par=hierarchy(parts)
    for n in parts:parts[n]['parent']=par.get(n,'Root')

    env={}
    m=re.search(r'framerate\s*\{\s*(\d+)',text);env['fps']=int(m.group(1)) if m else 24
    m=re.search(r'film\s*\{.*?size\s*\{\s*(\d+)\s+(\d+)',text,re.S);env['filmSize']=[int(m.group(1)),int(m.group(2))] if m else [640,480]
    m=re.search(r'scene\s*\{\s*"[^"]+".*?frames\s*\{\s*(\d+)',text,re.S);env['frames']=int(m.group(1)) if m else 72
    allpts=[p for name,part in parts.items() if name!='Ruler' for mesh in part['meshes'] for p in zip(mesh['p'][0::3],mesh['p'][1::3],mesh['p'][2::3])]
    if allpts:env['bindBounds']=[[r4(min(p[i] for p in allpts)) for i in range(3)],[r4(max(p[i] for p in allpts)) for i in range(3)]]
    return {'format':'BaldiAnimStudioModel','version':5,'source':os.path.basename(src),'environment':env,'materials':global_mats,'parts':parts,
            'compiler':{'mode':'anim8or-figure-bind-v5','figure':'Baldi','bones':len(bone_info),'attachments':len(attachments),
                        'corrections':corrections,'notes':['object-local material scoping','finger joint bind snap','ear-clipped n-gons','Anim8or subdivision working levels','Mouth2 orphan default cap removed']}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('src');ap.add_argument('out');a=ap.parse_args();model=compile_file(a.src)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)),exist_ok=True);payload=json.dumps(model,separators=(',',':'))
    if a.out.lower().endswith('.js'):open(a.out,'w',encoding='utf-8').write('window.BALDI_MODEL='+payload+';\n')
    else:open(a.out,'w',encoding='utf-8').write(payload)
    print('parts',len(model['parts']),'bytes',len(payload),'mode',model['compiler']['mode'])
    for n,p in model['parts'].items():print(n,'parent=',p['parent'],'pivot=',p['pivot'],'bbox=',p['bbox'],'meshes=',len(p['meshes']))
if __name__=='__main__':main()
