"""Hash-verified original execution for the finite LavaMouth native join."""
import base64,json,struct,sys
from pathlib import Path
from Tests.clawparity.program import claw
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_FPCW
OUT=Path('work/native-object-connections/lava_mouth_transport')
A,L,W=0x3000000,0x3001000,0x3002000
ROOT,IDLE,ERUPT=0x3003000,0x3003040,0x3003080
CA,CL,CLOCK=0x3004000,0x3005000,0x3006000
IM,AN,BIND=0x3007000,0x3007100,0x3007200
IMAGE,TABLE,FRAME,SEQ,HIT,ATTACK=0x3007300,0x3007400,0x3007500,0x3007600,0x3007700,0x3007800
ST,LT,CS=0x3008000,0x3008100,0x3008200
STOP,STACK,ALLOC=0x7000000,0x7008000,0x62000000

def initial():
 p=claw();regions=[[s.address,bytearray(s.data.ljust(s.size,b'\0'))] for s in p.sections if s.address>=0x500000];regions.extend([A+offset,bytearray(0x1000)] for offset in range(0,0x9000,0x1000))
 def put(a,v):
  for b,d in regions:
   if b<=a and a+4<=b+len(d):struct.pack_into('<I',d,a-b,v&0xffffffff);return
  raise ValueError(hex(a))
 values={A+12:W,A+0x6c:L,A+0x18c:A,0x532c0c:0,L+0x10:0x457620,L+0xbc:20,W+0x10:IM,W+0x14:BIND,W+0x28:0x3007900,W+0x2c:AN,0x537e88:CA,CA+0x6c:CL,CL+0x14:CLOCK,CLOCK+0x80:7,0x537210:100,0x5430c4:0,0x5262b0:0x3fc00000,0x537680:ROOT,ROOT:IDLE,ROOT+4:ERUPT,ROOT+8:26,IDLE:IDLE,IDLE+4:IDLE,IDLE+8:0,IDLE+12:0x523604,IDLE+16:1,ERUPT:ERUPT,ERUPT+4:ERUPT,ERUPT+8:0,ERUPT+12:0x5235f8,ERUPT+16:2,SEQ+0xc:0x3008300,SEQ+0x10:1,0x3008300:0x3008340,0x3008348:1,0x3008358:100,IMAGE+0x14:TABLE,IMAGE+0x64:1,IMAGE+0x68:1,TABLE+4:FRAME,HIT+16:0x4dc830,ATTACK+16:0x4dc850,0x5376a0:1,0x5376a4:2,0x5376a8:LT,0x5376b0:4,LT:CS+12,LT+4:CS+12,CS:1,CS+4:1,CS+8:0,0x537a98:1,0x537a9c:2,0x537aa0:ST,0x537aa8:4,ST:0x457d60,ST+4:0x457de0}
 for a,v in values.items():put(a,v)
 slots=[0x546a90,0x546a7c,0x546a84,0x546aa4,0x546aac,0x546a9c,0x546aa0,0x546b1c,0x546a8c,0x5469c8,0x546a88,0x5469c4,0x546ac0,0x546aa8,0x546a80,0x5469d8]
 imports={s:0x710000+i*4 for i,s in enumerate(sorted(slots))}
 for s,t in imports.items():put(s,t)
 return p,regions,imports

class Original:
 def __init__(self):
  self.p,self.regions,self.imports=initial();self.u=Uc(UC_ARCH_X86,UC_MODE_32);self.u.mem_map(0x400000,0x200000)
  for s in self.p.sections:self.u.mem_write(s.address,s.data)
  self.u.mem_map(0,0x1000);self.u.mem_map(A,0x10000);self.u.mem_map(ALLOC,0x10000);self.u.mem_map(STOP,0x10000)
  for b,d in self.regions:self.u.mem_write(b,bytes(d))
  self.put(0,0xffffffff);self.u.reg_write(UC_X86_REG_FPCW,0x023f);self.failAllocation=False;self.missing=None;self.fallback=False;self.nullSounds=False;self.next=ALLOC;self.allocations={};self.services=[];self.reached=set();self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_READ,self.read)
 def read(self,u,access,a,size,value,user):
  if a<0x1000 and (a!=0 or size!=4):raise AssertionError(("null-read",hex(a),size,hex(u.reg_read(UC_X86_REG_EIP))))
 def word(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def put(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def ret(self,v,n=0):
  sp=self.u.reg_read(UC_X86_REG_ESP);self.u.reg_write(UC_X86_REG_EAX,v);self.u.reg_write(UC_X86_REG_ESP,sp+4+n*4);self.u.reg_write(UC_X86_REG_EIP,self.word(sp))
 def code(self,u,a,size,user):
  if a==STOP:u.emu_stop();return
  self.reached.add(a)
  if a==0x5022b5 and self.failAllocation:self.missing=a;u.emu_stop();return
  if a==0x4a48e0:
   if self.failAllocation:self.ret(0);return
   n=self.word(u.reg_read(UC_X86_REG_ESP)+4);token=self.next;self.next=(token+n+15)&~15;self.allocations[token]=n;u.mem_write(token,b'\xcc'*n);self.services.append(['allocate',n,token]);self.ret(token)
  elif a==0x4a49b0:
   token=self.word(u.reg_read(UC_X86_REG_ESP)+4);assert token in self.allocations;self.services.append(['free',token]);del self.allocations[token];self.ret(0)
  elif a in (0x4a7bc0,0x4a7c40):self.ret(0)
  elif a==0x4f6974:self.services.append(['table',u.reg_read(UC_X86_REG_ECX),self.word(u.reg_read(UC_X86_REG_ECX))])
  elif a==0x4f6286:
   sp=u.reg_read(UC_X86_REG_ESP);name=self.word(sp+4);output=self.word(sp+8);r=u.reg_read(UC_X86_REG_ECX);v={0x522d54:HIT,0x522d48:ATTACK,0x5286a4:IMAGE,0x52417c:0 if self.fallback else SEQ,0x5234b4:SEQ,0x528690:0 if self.nullSounds else 0x3007a00,0x52867c:0 if self.nullSounds else 0x3007b00}.get(name);assert v is not None,hex(name);self.put(output,v);self.services.append(['lookup',r,name,v]);self.ret(1,2)
 def call(self,f,r=0,args=()):
  self.u.reg_write(UC_X86_REG_ECX,r);self.u.reg_write(UC_X86_REG_ESP,STACK);self.put(STACK,STOP)
  for i,a in enumerate(args):self.put(STACK+4+i*4,a)
  self.u.emu_start(f,STOP+1,count=200000);assert (self.u.reg_read(UC_X86_REG_EIP)==STOP or self.missing is not None),(hex(f),hex(self.u.reg_read(UC_X86_REG_EIP)))
 def snapshot(self,label,h):
  return {'label':label,'helper':h,'actor':list(self.u.mem_read(A,0x1b4)),'logic':list(self.u.mem_read(L,0x174)),'helperBytes':list(self.u.mem_read(h,0xb8)) if h else [],'globals':{str(a):list(self.u.mem_read(a,n)) for a,n in [(0x537668,0x2c),(0x537698,0x24),(0x537a90,0x24),(0x537210,4),(0x5430c4,4),(0x532c0c,8),(0x5262b0,4),(0x537e88,4),(CA,0x1b4),(CL,0x174),(CLOCK,0x84)]},'sounds':{str(self.word(h+offset)):list(self.u.mem_read(self.word(h+offset),0x14)) for offset in [0xb0,0xb4] if h and self.word(h+offset)},'services':list(self.services),'allocations':{str(a):n for a,n in self.allocations.items()},'secondaries':{str(self.word(A+off)):list(self.u.mem_read(self.word(A+off),0x174)) for off in [0x70,0x78] if self.word(A+off)}}

def prepare():
 OUT.mkdir(parents=True,exist_ok=True);p,regions,imports=initial();(OUT/'input.json').write_text(json.dumps({'allocationBase':ALLOC,'sha256':p.sha256,'regions':[{'address':b,'bytes':base64.b64encode(d).decode()} for b,d in regions],'imports':{str(k):v for k,v in imports.items()}}));o=Original();snapshots=[]
 for label,command,clock in [('construct',0,100),('no-op',1000,100),('command29',29,100),('command30',30,100),('idle',1,100),('eruption',1,121),('erupting',2,121)]:
  o.put(L+0x1c,command);o.put(0x537210,clock);o.call(0x457620,args=[A]);snapshots.append(o.snapshot(label,o.word(L+0x18)))
 o.put(CLOCK+0x80,8);o.put(L+0x1c,2);o.call(0x457620,args=[A]);snapshots.append(o.snapshot('clock-idle',o.word(L+0x18)))
 h=o.word(L+0x18);o.call(0x484d90,h,[1]);o.put(L+0x18,0);snapshots.append(o.snapshot('retired',0));o.put(L+0x1c,0);o.call(0x457620,args=[A]);snapshots.append(o.snapshot('recreated',o.word(L+0x18)))
 fallback=Original();fallback.fallback=True;fallback.call(0x457620,args=[A]);snapshots.append(fallback.snapshot('fallback',fallback.word(L+0x18)))
 null_sounds=Original();null_sounds.nullSounds=True;null_sounds.call(0x457620,args=[A]);snapshots.append(null_sounds.snapshot('null-sounds',null_sounds.word(L+0x18)))
 required=[0x457658,0x45765d,0x457673,0x457678,0x45768a,0x45768d,0x457697,0x45769a,0x4576bb,0x4576be,0x4576ac,0x4576b1,0x457620,0x457b10,0x408370,0x4c7fa0,0x4c8060,0x4c7970,0x4f6286,0x4dba00,0x4a30e0,0x4c96b0,0x4dc870,0x4c9e30,0x457740,0x4041b0,0x457cd0,0x457d60,0x457d80,0x457de0,0x484d90];assert all(a in o.reached for a in required),[hex(a) for a in required if a not in o.reached];failure=Original();failure.failAllocation=True;failure.call(0x457620,args=[A]);assert failure.missing==0x5022b5 and failure.word(L+0x1c)==1000 and failure.word(L+0x18)==0;(OUT/'original.json').write_text(json.dumps({'snapshots':snapshots,'edges':[hex(a) for a in required],'sha256':p.sha256,'allocationFailure':{'address':failure.missing,'command':failure.word(L+0x1c),'helper':failure.word(L+0x18)}}));print(json.dumps({'original':'pass','snapshots':len(snapshots)}))

def compare():
 o=json.loads((OUT/'original.json').read_text());n=json.loads((OUT/'native.json').read_text())
 for a,b in zip(o['snapshots'],n['snapshots']):
  for k in a:
   if a[k]!=b[k]:
    differences=[(i,x,y) for i,(x,y) in enumerate(zip(a[k],b[k])) if x!=y][:10] if isinstance(a[k],list) else (a[k],b[k])
    raise AssertionError((a['label'],k,differences))
 assert len(o['snapshots'])==len(n['snapshots']);assert o['allocationFailure']==n['allocationFailure'];assert n['controls'] and all(n['controls'].values()),n['controls'];result={'command':'lava-mouth-transport','status':'pass','comparisons':len(o['snapshots']),'edges':o['edges'],'controls':n['controls'],'unresolved_dependencies':[]};(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':globals()[sys.argv[1]]()
