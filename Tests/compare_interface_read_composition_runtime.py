"""Joined frozen IFC/CArchive readers; physical file/image services explicit."""
import ctypes as C,gzip,struct,json
import interface_read_composition_helpers as h
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
from unicorn import UC_HOOK_CODE
class MemoryLoad(C.Structure):_fields_=[(n,h.U)for n in('graphics','bytes','length','resolver')]+[('trailing',h.U*3)]
class FileLoad(C.Structure):_fields_=[(n,h.U)for n in('graphics','file','resolver')]+[('trailing',h.U*3)]
for fn,typ in(('claw_interface_read_memory',MemoryLoad),('claw_interface_read_file',FileLoad)):
 getattr(h.lib,fn).argtypes=[h.U,C.POINTER(typ),C.POINTER(h.Context),h.Dep,C.c_void_p,C.POINTER(h.U)]
rawEntry=h.lib.claw_interface_read_composition_entry
def entry(f,t,a,n,c,d,u,out):
 if f==0x4dcdf0 and n==7:
  p=MemoryLoad(*a[:4],(h.U*3)(*a[4:7]));return h.lib.claw_interface_read_memory(t,C.byref(p),c,d,u,out)
 if f==0x4dcd10 and n==6:
  p=FileLoad(*a[:3],(h.U*3)(*a[3:6]));return h.lib.claw_interface_read_file(t,C.byref(p),c,d,u,out)
 return rawEntry(f,t,a,n,c,d,u,out)
h.lib.claw_interface_read_composition_entry=entry

def tree(t):
 yield t
 for i in range(h.get(t+32)):yield from tree(h.get(h.get(t+28)+i*4))
# Borrowed memory: actual source parser and all ctor/tree/dtor bodies run.
for seed,name,count in((0,'CLAW.IFC',133),(1,'CLAWWITHLOBBY.IFC',138)):
 h.capture=True;n=h.fresh(seed,name)
 h.compare(0x4dcc40,h.MENU,[640,480],'typed ctor')
 h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,n,0x710000,0,0,0],name)
 assert len(list(tree(h.MENU+72)))==count
 assert len(h.nativeNames)==count*8 and h.nativeNames==h.sourceNames
 assert h.get(h.MENU+68)==1
 h.compare(0x4dccb0,h.MENU,[],'typed teardown',void=True);h.capture=False
 print('retail borrowed',name,count,'nodes',flush=True)
# Real data truncations and mandatory resource failure retain source prefixes.
for name in('CLAW.IFC','CLAWWITHLOBBY.IFC'):
 for length in(0,1,4,4095):
  h.fresh(2,name);h.compare(0x4dcc40,h.MENU,[640,480],'EOF ctor')
  h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,length,0x710000,0,0,0],'typed EOF',unsafe=True)
 for failure in(1,8,32):
  n=h.fresh(3,name);h.compare(0x4dcc40,h.MENU,[640,480],'failed image ctor')
  h.resolverFailAt=failure
  h.compare(0x4dcdf0,h.MENU,[h.GRAPHICS,h.DATA,n,0x710000,0,0,0],'failed image result')
  h.compare(0x4dccb0,h.MENU,[],'failed image cleanup',void=True)
# Ordinary physical non-direct FILE transport: no independent IFC parser.
# File Read/Seek/GetBufferPtr packets remain exact addressed services. Partial
# reads expose real CArchive fill and close rewind behavior in source and native.
physicalFunctions={0x710100:4,0x710104:2,0x710108:2};fragment=500
oldEffect=h.effect
def effect(f,t,a,b):
 if f not in physicalFunctions:return oldEffect(f,t,a,b)
 if f==0x710100:return 0 # no direct buffer
 if f==0x710104:
  position=h.get(h.FILE+20);size=h.get(h.FILE+28);amount=min(a[1],fragment,max(0,size-position))
  h.write(a[0],h.read(h.get(h.FILE+32)+position,amount));h.put(h.FILE+20,[position+amount]);return amount
 off=C.c_int32(a[0]).value;origin=0 if a[1]==0 else h.get(h.FILE+20)if a[1]==1 else h.get(h.FILE+28)
 position=origin+off;assert position>=0;h.put(h.FILE+20,[position]);return position
h.effect=effect
def physicalHook(u,f,size,user):
 if f==0x4fda33 and h.currentFunction==0x4dcd10:h.fileAlias=h.FILE
 if f not in physicalFunctions:return
 sp=u.reg_read(UC_X86_REG_ESP);t=u.reg_read(UC_X86_REG_ECX);assert t==h.FILE
 a=list(h.m.read_words(sp+4,physicalFunctions[f]));b=[t]
 h.oevents.append((f,0,tuple(a),256,(bytes(u.mem_read(t,40)),),h.snap(),h.automatic()))
 value=effect(f,0,a,b);h.ret(len(a)*4,value)
h.m.u.hook_add(UC_HOOK_CODE,physicalHook)
for name,count in(('CLAW.IFC',133),('CLAWWITHLOBBY.IFC',138)):
 for fragment in(31,500,4096):
  n=h.fresh(fragment,name);h.put(h.VT+32,[0x4fc139]);h.put(h.VT+48,[0x710108]);h.put(h.VT+60,[0x710104]);h.put(h.VT+88,[0x710100])
  h.put(h.FILE,[h.VT,0xffffffff,0,0x52e1c4,0,0,n,n,h.DATA,0])
  h.compare(0x4dcc40,h.MENU,[640,480],'ordinary file ctor')
  h.compare(0x4dcd10,h.MENU,[h.GRAPHICS,h.FILE,0x710000,0,0,0],'ordinary physical read')
  assert len(list(tree(h.MENU+72)))==count
  assert h.get(h.FILE+20)==n
  h.compare(0x4dccb0,h.MENU,[],'ordinary file teardown',void=True)
  print('retail physical',name,'fragment',fragment,flush=True)
# Standalone owned memory-file bodies: compare every file word as well as bytes.
for seed in range(16):
 n=h.fresh(seed);h.put(h.FILE,[0x5142f4,0xffffffff,0,0x52e1c4,0,seed,n,n,h.DATA,0])
 for requested in(0,1,3,19,n+1):
  h.compare(0x4ff79f,h.FILE,[h.BASE+0x9000,requested],'memory read')
 h.compare(0x4ff822,h.FILE,[0,0],'memory seek begin')
 h.compare(0x4ff822,h.FILE,[0xfffffff9,2],'memory seek end')
 h.compare(0x4ff8a8,h.FILE,[0,3,h.BASE+0x9200,h.BASE+0x9204],'memory direct buffer')
 h.compare(0x4ff8a8,h.FILE,[0,0xffffffff,h.BASE+0x9200,h.BASE+0x9204],'memory remaining')
# Freeze exact-span borrowed retail and lifecycle replay corpus.
p=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
with gzip.open(h.WORK/'sanitizer-replay.bin.gz','wb')as out:
 out.write(b'IFCR'+p(h.iBase,len(h.seedImage),h.SIZE,len(h.corpus))+h.seedImage)
 for f,t,a,label,value,meaningful,before,globals,expected,objects,events,file,archive in h.corpus:
  out.write(p(f,t,len(a),value,meaningful,len(objects),len(events))+p(*a)+before+globals)
  for token,n in objects.items():out.write(p(token,n))
  for f,t,a,mask,outputs,buffers,digest,value,patches in events:
   out.write(p(f,t,len(a),mask,value,len(patches),len(buffers))+p(*a)+digest)
   for i,b in patches:out.write(p(i,b))
   for b,v in zip(buffers,outputs):out.write(p(len(b))+b+v)
  out.write(expected+file+archive)
text=sum(0x401000<=a<0x50adb5 for a in h.m.executed)
print('PASS',h.calls,'whole original compositions /',h.snapshots,'ordered full snapshots /',len(h.unsafeCases),'stopped prefixes /',text,'text /',len(h.m.executed),'total addresses /',len(h.corpus),'exact replay cases',flush=True)
(h.WORK/'prefixes.json').write_text(json.dumps(h.unsafeCases,indent=2))
