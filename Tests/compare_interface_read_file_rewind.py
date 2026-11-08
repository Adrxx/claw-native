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
 for fragment in(4096,):
  n=h.fresh(fragment,name);h.write(h.DATA+n,bytes(range(84)));h.put(h.VT+32,[0x4fc139]);h.put(h.VT+48,[0x710108]);h.put(h.VT+60,[0x710104]);h.put(h.VT+88,[0x710100])
  h.put(h.FILE,[h.VT,0xffffffff,0,0x52e1c4,0,0,n+84,n+84,h.DATA,0])
  h.compare(0x4dcc40,h.MENU,[640,480],'ordinary file ctor')
  h.compare(0x4dcd10,h.MENU,[h.GRAPHICS,h.FILE,0x710000,0,0,0],'ordinary physical read')
  assert len(list(tree(h.MENU+72)))==count
  assert h.get(h.FILE+20)==n
  assert any(e[0]==0x710108 and C.c_int32(e[2][0]).value<0 for e in h.events),'source close rewind must be elected'
  h.compare(0x4dccb0,h.MENU,[],'ordinary file teardown',void=True)
  print('retail physical',name,'fragment',fragment,flush=True)

print('PASS',h.calls,'whole retained original calls /',h.snapshots,'full snapshots; both retail files rewound across84-byte unread trailer',flush=True)
