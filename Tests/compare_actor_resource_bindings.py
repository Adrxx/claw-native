#!/usr/bin/env python3
"""Real lookup/binder/reset/constructor/initializer versus portable state."""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
import subprocess
from actor_resource_binding_helpers import ActorBindingHarness,packed

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');a=p.parse_args()
library=ROOT/'work/actor-bindings-agent/libActorResourceBindings.dylib'
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/ActorResourceBindings.cpp'),'-o',str(library)],check=True)
class State(C.Structure):_fields_=[('actor',C.c_uint32*128),('secondary',C.c_uint32*93)]
class Image(C.Structure):_fields_=[('token',C.c_uint32),('minimum',C.c_int32),('maximum',C.c_int32),('firstImageIndex',C.c_int32),('images',C.POINTER(C.c_uint32)),('imageCount',C.c_size_t)]
class Context(C.Structure):_fields_=[('imageRegistryToken',C.c_uint32),('logicRegistryToken',C.c_uint32),('image',Image)]+[(x,C.c_uint32)for x in('metadataToken','metadataCallback','metadataFlags','associatedDestructor')]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argument',C.c_uint32),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(library))
lib.claw_actor_bind_indexed_image.argtypes=[C.POINTER(State),C.POINTER(Context),C.c_char_p,C.c_int32,Dependency,C.c_void_p];lib.claw_actor_bind_indexed_image.restype=C.c_uint32
for name in('claw_actor_bind_default_image','claw_actor_bind_secondary_logic_name','claw_actor_bind_contact_logic_name'):
    getattr(lib,name).argtypes=[C.POINTER(State),C.POINTER(Context),C.c_char_p,Dependency,C.c_void_p];getattr(lib,name).restype=C.c_uint32
lib.claw_actor_bind_secondary_logic.argtypes=[C.POINTER(State),C.POINTER(Context),Dependency,C.c_void_p];lib.claw_actor_bind_secondary_logic.restype=C.c_uint32
lib.claw_actor_bind_contact_logic.argtypes=[C.POINTER(State),C.POINTER(Context),Dependency,C.c_void_p];lib.claw_actor_bind_contact_logic.restype=C.c_uint32
lib.claw_actor_reset_secondary_logic.argtypes=[C.POINTER(State),C.POINTER(Context),Dependency,C.c_void_p]
r=ActorBindingHarness(a.exe);m=r.machine;u=r.u;m.executed.clear();rng=random.Random(1997);config={};events=[];calls=0
@Dependency
def dependency(state,context,event,user):
    e=event.contents;c=context.contents;text=e.name if e.name is not None else None
    events.append((e.function,e.receiver,e.argument,text))
    if e.function==0x4f6286:
        return r.lookup(e.receiver,text)
    r.mutate(state.contents.actor,state.contents.secondary,e.function)
    if e.function==0x4f63ec:return r.secondary if config['allocation'] else 0
    return 0
def prepare(existing=False,private=False,associated=False,callback=0x41ce80,flags=0,allocation=True,minimum=-16,maximum=47,images=None):
    aw=[rng.getrandbits(32)for _ in range(128)];sw=[rng.getrandbits(32)for _ in range(93)]
    aw[3]=r.actor_scene;aw[0x70//4]=r.secondary if existing else 0
    sw[0]=0x513740;sw[0x14//4]=0x55667788 if private else 0;sw[0x18//4]=r.associated if associated else 0
    state=State((C.c_uint32*128)(*aw),(C.c_uint32*93)(*sw))
    values=images if images is not None else [rng.getrandbits(32)if rng.randrange(5)else 0 for _ in range(64)]
    table=(C.c_uint32*len(values))(*values)
    c=Context(r.image_manager+16,r.registry+16,Image(r.image_resource,minimum,maximum,-16,table,len(values)),r.metadata,callback,flags,r.destructor)
    m.write_words(r.image_resource+0x14,[r.image_table+64]);m.write_words(r.image_resource+0x64,[minimum,maximum]);m.write_words(r.image_table,values)
    m.write_words(r.metadata+8,[flags,0,callback]);config.update(allocation=allocation)
    return state,c,table
def invoke(state,c,operation,name=b'Handler',index=0):
    global calls
    before_a=list(state.actor);before_s=list(state.secondary);events.clear()
    if operation=='indexed':result=lib.claw_actor_bind_indexed_image(C.byref(state),C.byref(c),name,index,dependency,None);address=0x4c7900;args=packed(r.query,index)
    elif operation=='default':result=lib.claw_actor_bind_default_image(C.byref(state),C.byref(c),name,dependency,None);address=0x4c7970;args=packed(r.query)
    elif operation=='named':result=lib.claw_actor_bind_secondary_logic_name(C.byref(state),C.byref(c),name,dependency,None);address=0x4c7fa0;args=packed(r.query)
    elif operation=='resolved':result=lib.claw_actor_bind_secondary_logic(C.byref(state),C.byref(c),dependency,None);address=0x4c7f20;args=packed(c.metadataToken)
    elif operation=='contact-named':result=lib.claw_actor_bind_contact_logic_name(C.byref(state),C.byref(c),name,dependency,None);address=0x4c8060;args=packed(r.query)
    elif operation=='contact-resolved':result=lib.claw_actor_bind_contact_logic(C.byref(state),C.byref(c),dependency,None);address=0x4c7fe0;args=packed(c.metadataToken)
    elif operation=='reset':lib.claw_actor_reset_secondary_logic(C.byref(state),C.byref(c),dependency,None);result=None;address=0x4c81b0;args=b''
    expected=list(events)
    m.write_words(r.actor,before_a);m.write_words(r.secondary,before_s);u.mem_write(r.query,name+b'\0');r.events.clear();r.capture=True;r.allocation=config['allocation']
    original=m.call(address,r.secondary if operation=='reset'else r.actor,args);r.capture=False
    assert expected==r.events,(operation,'events',expected,r.events)
    if operation in('named','resolved','contact-named','contact-resolved'):assert result==original,(operation,'result',result,original)
    elif operation in('indexed','default'):assert result==1
    assert m.read_words(r.actor,128)==list(state.actor),(operation,'actor',[(i*4,hex(x),hex(y))for i,(x,y)in enumerate(zip(m.read_words(r.actor,128),state.actor))if x!=y])
    assert m.read_words(r.secondary,93)==list(state.secondary),(operation,'secondary',[(i*4,hex(x),hex(y))for i,(x,y)in enumerate(zip(m.read_words(r.secondary,93),state.secondary))if x!=y])
    calls+=1

for i in range(2000):
    minimum=rng.randrange(-16,40);maximum=rng.randrange(minimum,48)
    state,c,table=prepare(minimum=minimum,maximum=maximum)
    invoke(state,c,'indexed',b'Images'if i%3 else b'Missing',rng.choice([minimum-1,minimum,maximum,maximum+1,rng.randrange(-20,52),-2147483648,2147483647]))
    invoke(state,c,'default',b'Images'if i%5 else b'Missing')
    invoke(state,c,'indexed',b'Images',minimum)
print('PASS2000 image histories: indexed/default/missing/rebinding, signed IDs, edge ranges and zero image tokens; original lookup executes',flush=True)
# Inverted resource bounds are an original no-image condition, not repaired.
state,c,table=prepare(minimum=5,maximum=4);invoke(state,c,'default',b'Images');invoke(state,c,'indexed',b'Images',5)
for i in range(2000):
    callback=0 if i%7==0 else rng.getrandbits(32)or 1
    state,c,table=prepare(existing=i%2==0,private=i%3==0,associated=i%5==0,callback=callback,flags=rng.getrandbits(32),allocation=i%11!=0)
    invoke(state,c,'named',b'Handler'if i%4 else b'Missing')
    c.metadataToken=r.metadata
    invoke(state,c,'resolved')
    invoke(state,c,'reset')
print('PASS2000 secondary histories: allocation/failure, existing reset/private free/associated destroy, missing metadata/zero callbacks, flag independence and rebind',flush=True)
for i in range(2000):
    state,c,table=prepare(existing=i%2==0,private=i%3==0,associated=i%5==0,
        callback=0 if i%7==0 else rng.getrandbits(32)or 1,flags=rng.getrandbits(32),allocation=i%11!=0)
    # The contact call uses the93-word supplied buffer at actor78; preserve
    # actor70 as unrelated random storage, including across callback mutation.
    state.actor[0x78//4]=state.actor[0x70//4];state.actor[0x70//4]=rng.getrandbits(32)
    invoke(state,c,'contact-named',b'Handler'if i%4 else b'Missing')
    c.metadataToken=r.metadata;invoke(state,c,'contact-resolved')
print('PASS2000 contact histories: named/resolved allocation/reset, missing metadata, zero callbacks, and independent actor70/78',flush=True)
state,c,table=prepare(existing=True,private=True,associated=True);c.metadataToken=0;invoke(state,c,'resolved')
for entry in r.entries[:212]:
    state,c,table=prepare(callback=entry['callback'],flags=entry['flags'])
    invoke(state,c,'named',entry['name'].encode())
    assert state.secondary[2]==0 and state.secondary[4]==entry['callback']
print('PASS all212 actual original registered handler identities bind as secondary logic with flagszero',flush=True)
files=sorted((ROOT/'App/GameData/IMAGES').glob('*.PID'))
ids=[int(path.stem.removeprefix('FRAME'))for path in files];assert ids and len(ids)==len(set(ids))
values=[0]*(max(ids)+17)
for image_id in ids:values[image_id+16]=0x1200000+image_id*64
state,c,table=prepare(minimum=min(ids),maximum=max(ids),images=values)
invoke(state,c,'default',b'Images')
for image_id in [min(ids)-1,*ids,max(ids)+1]:invoke(state,c,'indexed',b'Images',image_id)
print(f'PASS actual{len(ids)}CLAW PID image IDs plus default and out-of-range selections; decoded pixel/image storage remains separate',flush=True)
# Native pointer/table safety rejects before recovered field writes; lookup may
# still occur and adapter side effects are outside an atomicity claim.
state,c,table=prepare();before=bytes(state);c.image.imageCount=1;events.clear()
assert lib.claw_actor_bind_indexed_image(C.byref(state),C.byref(c),b'Images',47,dependency,None)==0 and bytes(state)==before
required={0x4c7900,0x4c7970,0x4c7f20,0x4c7fa0,0x4c7fe0,0x4c8060,0x4c81b0,0x4c8160,0x4f6286,0x4f5d5c,0x4a3810}
assert required<=m.executed
addresses=m.executed-r.side_entries-{0x4f63ec,0x4f6428,0x4f66cc,0x4c80c0,r.destructor,m.stop}
print(f'PASS{calls} complete original binder/reset calls; full128actor+93secondary words and ordered dependencies;{len(addresses)} original binding-phase addresses. Only allocation/free/associated destructor adapted in binding phase; binder/reset/init/lookup execute. Original registry initialization uses separate documented harness adapters.',flush=True)
