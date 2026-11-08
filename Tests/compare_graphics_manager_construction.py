#!/usr/bin/env python3
"""Whole original constructors; no source callee or physical-service stubs."""
from pathlib import Path
import ctypes as C,random,subprocess,json
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/graphics-manager-construction';WORK.mkdir(exist_ok=True)
names=['GraphicsManagerConstructionRuntime','SoundTriggerLogicRuntime','EnemySpeechRuntime','SpeechActor','AudioEvents','ActorResourceBindings','ActorDestruction','SceneActorRuntime','WorldObjectRuntime','GameTiming','ActorAnimationRuntime','AnimationEngine','AnimationOperations']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(ROOT/'Sources'/f'{n}.cpp')for n in names],'-o',str(WORK/'libGraphicsCtor.dylib')],check=True)
U=C.c_uint32
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,Call);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('clock',Clock)]
base,size=0x1000000,65536;heap=(C.c_uint8*size)()
@Lookup
def lookup(_,t,n):return C.addressof(heap)+t-base if base<=t and t+n*4<=base+size else None
host=Host(None,lookup,Allocate(),Free(),Invoke(),Clock());lib=C.CDLL(str(WORK/'libGraphicsCtor.dylib'))
for name in ['claw_graphics_manager_construct','claw_graphics_string_array_construct']:
 getattr(lib,name).argtypes=[U,Host,C.POINTER(U),C.POINTER(U)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(0,4096);r=random.Random(0x4bc120);fixtures=[]
for i in range(512):
 raw=r.randbytes(size);t=base+128+(i%11)*64
 for entry,name,n in [(0x4bc120,'claw_graphics_manager_construct',2180),(0x4f54ea,'claw_graphics_string_array_construct',20)]:
  C.memmove(heap,raw,size);m.u.mem_write(base,raw);beforeGlobals=bytes(m.u.mem_read(0x500000,0x50000))
  value=m.call(entry,t,b'');expected=bytes(m.u.mem_read(base,size));fault=U(0);result=U(0)
  assert getattr(lib,name)(t,host,C.byref(fault),C.byref(result))==1 and fault.value==0 and result.value==value==t
  assert bytes(heap)==expected and bytes(m.u.mem_read(0x500000,0x50000))==beforeGlobals
  if i<32:fixtures.append({'entry':entry,'before':raw[t-base:t-base+n].hex(),'after':expected[t-base:t-base+n].hex()})
(WORK/'fixtures.json').write_text(json.dumps(fixtures))
print('PASS1024 whole original constructor calls: full64KiB heap +320KiB globals, meaningful EAX, two actual original list callees, seeded untouched bytes; physical startup/teardown separate')
