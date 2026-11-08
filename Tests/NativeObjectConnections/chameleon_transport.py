"""Original-backed Chameleon transport. Derived bytes stay under work/."""
import json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
import unicorn.x86_const as xr
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_FPCW,UC_X86_REG_FPSW
BASE,SIZE,ALLOC=0x10000000,0x20000,0x61000000
ACTOR,LOGIC,WORLD,REGISTRY,COLLISION,ANIMATIONS,IMAGES,SOUNDS,HIT,ATTACK=[BASE+i*0x1000 for i in range(1,11)]
ACTION,ANIMATION,LIST,IMAGE,FRAME,SURFACE,STAGE,ROOTMAN,NAMES,METHODS=[BASE+0xb000+i*0x1000 for i in range(10)]
SETRECT,EMPTY,DEC,POINT=0x68001000,0x68001010,0x68001020,0x68001030
OBSERVE=(0x421200,0x421710,0x44c000,0x405000,0x44cfd0,0x4c96b0,0x4dc870,0x421bf0,0x421320,0x44d3c0,0x43dfa0,0x421e00,0x421b60,0x421b80,0x4f63ec,0x4c7fa0,0x4c8060,0x4f6439,0x4dc180,0x4dbe10,0x4dbd60,0x4db620)
class Reference:
 def __init__(self):
  self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x20000);self.m.uc.mem_map(0x68001000,0x1000)
  self.next_alloc=ALLOC;self.allocations=[];self.events=[];self.entries=[];self.retired={}
  self.m.write(BASE,bytes(SIZE));self.w(ACTOR+0xc,WORLD);self.w(ACTOR+0x6c,LOGIC);self.w(LOGIC+0x10,0x421200);self.w(LOGIC+0x168,100)
  self.w(ACTOR+0x18c,ACTOR);self.w(ACTOR+0x4c,128,512);self.w(ACTOR+0x118,0x80000000);self.w(LOGIC+0x2c,120,140,3,7)
  self.w(WORLD+0x10,IMAGES,HIT,ATTACK);self.w(WORLD+0x24,COLLISION,SOUNDS,ANIMATIONS)
  self.w(COLLISION+0x5c,BASE+0x15000);self.w(BASE+0x15000+0x20,BASE+0x19000,BASE+0x16000);self.w(BASE+0x15000+0x30,1024,1024);self.w(BASE+0x15000+0x8c,10,10);self.w(BASE+0x19000,0xffffffff)
  
  for i in range(7):self.w(BASE+0x1c000+i*0x20+0xc,LIST,1)
  self.w(ANIMATION+0xc,LIST,1);self.w(LIST,ACTION);self.w(ACTION+0x1c,1)
  self.w(IMAGE+0x14,BASE+0x18000);self.w(IMAGE+0x64,900,902);self.w(FRAME+0x18,-3,-7,31,41);self.w(FRAME+0x30,SURFACE)
  for i in range(900,905):self.w(BASE+0x18000+i*4,FRAME)
  self.w(BASE+0x1d010,0x4dc830);self.w(BASE+0x1d110,0x4dc850);self.w(0x5371fc,ROOTMAN);self.w(ROOTMAN+0x2c,STAGE);self.w(STAGE+0x770,0x12345678)
  self.w(0x537e88,BASE+0x1f000);self.w(BASE+0x1f000+0x4c,300,512);self.w(0x537680,0);self.w(0x5376a0,0,1,NAMES,NAMES,4,0,0);self.m.write(BASE+0x1e000,b'LS_HOME\0');self.w(NAMES,BASE+0x1e000,BASE+0x1e000)
  self.w(0x534ed8,0,1,METHODS,METHODS,4);self.w(METHODS,0x421e00,0x421e00)
  for a,v in ((0x537964,13),(0x537210,10000),(0x532c0c,0),(0x544d18,0),(0x52f01c,1)):self.w(a,v)
  self.m.write(0x5262b0,struct.pack('<f',1.25));self.m.write(0x5262b4,struct.pack('<f',0.75));self.m.write(0x5262b8,struct.pack('<d',2.5))
  for slot,target in ((0x546d5c,SETRECT),(0x546cdc,EMPTY),(0x5469e8,DEC),(0x546cd4,POINT)):self.w(slot,target)
  for a in OBSERVE:self.m.observe(a,self.entry)
  for a in (0x4a48e0,0x4a49b0,0x4f6286,0x4f6974,0x4a3050,SETRECT,EMPTY,DEC,POINT):self.m.intercept(a)
  self.m.on_external=self.external
  self.m.uc.reg_write(xr.UC_X86_REG_FPSW,6<<11);self.m.uc.reg_write(xr.UC_X86_REG_FPTAG,0x0fff)
  self.m.uc.reg_write(xr.UC_X86_REG_FP6,(0xa000000000000000,0x3fff));self.m.uc.reg_write(xr.UC_X86_REG_FP7,(0xc000000000000000,0xc000))
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in ((BASE,SIZE),(0x500000,0x48000))]
 def w(self,a,*v):self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
 def get(self,a):return self.m.words(a,1)[0]
 def text(self,a):return self.m.read(a,128).split(b'\0')[0].decode('ascii')
 def entry(self,m,a):
  self.entries.append([a,m.register(UC_X86_REG_ECX) if a not in (0x421200,0x4dc870,0x4f63ec) else 0])
  if a in (0x4f6439,0x4db620):self.member_sources.append([a,self.get(m.register(UC_X86_REG_ESP)),m.register(UC_X86_REG_ECX)])
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i);receiver=m.register(UC_X86_REG_ECX)
  if a==0x4a48e0:
   n=arg(0);token=self.next_alloc;self.next_alloc=(token+n+15)&~15;self.m.write(token,bytes([204])*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
  elif a==0x4a49b0:
   token=arg(0);self.retired[token]=self.m.read(token,next(n for t,n in self.allocations if t==token)).hex();self.events.append(['free',token]);m.return_from_external(0,0)
  elif a==0x4f6286:
   key=self.text(arg(0));value=0
   if receiver==ANIMATIONS+0x10:
    name=key.removeprefix('LEVEL_CHAMELEON_');index=('IDLE','FASTADVANCE','HIT','JUMP','KILLFALL','STRIKE1','GAME_NULL').index(name);value=BASE+0x1c000+index*0x20
   elif receiver==IMAGES+0x10 and key=='LEVEL_CHAMELEON':value=IMAGE
   elif receiver==SOUNDS+0x10:value=BASE+0x17000+(sum(key.encode())%32)*0x20
   elif receiver==HIT+0x10:value=BASE+0x1d100 if key=='LogicAttack' else BASE+0x1d000
   elif receiver==ATTACK+0x10:value=BASE+0x1d100
   else:raise RuntimeError(('registry',hex(receiver),key))
   self.events.append(['registry',receiver,key,value]);self.w(arg(1),value);m.return_from_external(int(value!=0),8)
  elif a==0x4f6974:
   value=self.get(receiver);self.events.append(['state-name',receiver,value]);m.return_from_external(value,4)
  elif a==0x4a3050:self.events.append(['rand',95]);m.return_from_external(95,0)
  elif a in (SETRECT,EMPTY):
   values=[arg(i) for i in range(1,5)] if a==SETRECT else [0]*4;self.w(arg(0),*values);self.events.append(['rectangle',arg(0),*values]);m.return_from_external(1,20 if a==SETRECT else 4)
  elif a==DEC:
   v=(self.get(arg(0))-1)&0xffffffff;self.w(arg(0),v);self.events.append(['decrement',arg(0),v]);m.return_from_external(v,4)
  elif a==POINT:
   left,top,right,bottom=self.m.words(arg(0),4);signed=lambda x:struct.unpack('<i',struct.pack('<I',x))[0];x,y=signed(arg(1)),signed(arg(2));value=int(signed(left)<=x<signed(right) and signed(top)<=y<signed(bottom));self.events.append(['point',arg(0),arg(1),arg(2),value]);m.return_from_external(value,12)
  else:raise RuntimeError(('service',hex(a)))
 def snapshot(self):
  spans=[(ACTOR,0x1b4),(LOGIC,0x174),(0x534ed0,0x28),(0x537668,0x58)]+[(a,n) for a,n in self.allocations if a not in self.retired]
  return [dict(address=a,data=self.m.read(a,n).hex()) for a,n in spans]
 def fp(self):
  status=self.m.register(UC_X86_REG_FPSW);top=(status>>11)&7;tags=self.m.register(xr.UC_X86_REG_FPTAG);slots=[]
  for i in range(8):
   index=(top+i)&7
   if (tags>>(index*2))&3==3:break
   sig,exp=self.m.uc.reg_read(getattr(xr,"UC_X86_REG_FP"+str(index)));slots.append([str(sig),exp])
  return dict(control=self.m.register(UC_X86_REG_FPCW),status=status,count=len(slots),slots=slots)
 def run(self):
  steps=[]
  for command in (0,1000,29,30,1,'destroy',0,1000,'destroy'):
   self.events=[];self.entries=[];self.member_sources=[];incoming=self.fp()
   if command=='destroy':
    helper=self.get(LOGIC+0x18);done=self.m.call(0x421b60,ecx=helper,arguments=(1,));scalar_result=self.m.register(UC_X86_REG_EAX);
    for offset in (0x70,0x78):
     token=self.get(ACTOR+offset)
     if token:self.m.call(0x4c80c0,ecx=token,arguments=(1,));self.w(ACTOR+offset,0)
    self.w(LOGIC+0x18,0)
   else:self.w(LOGIC+0x1c,command);done=self.m.call(0x421200,arguments=(ACTOR,))
   if not done.completed:raise RuntimeError((command,done))
   steps.append(dict(command=command,result=scalar_result if command=='destroy' else self.m.register(UC_X86_REG_EAX),events=self.events,entries=self.entries,final=self.snapshot(),member_sources=self.member_sources,incoming_x87=incoming,x87=self.fp(),retired={str(k):v for k,v in self.retired.items()}))
  return dict(label='complete-lifecycle',initial=self.initial,steps=steps)
def prepare(out):
 profiles=[Reference().run()];out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(version=1,executable_sha256=claw().sha256,profiles=profiles),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(profiles))))
def compare(out):
 reference=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());failures=[]
 if not reference['profiles'] or len(reference['profiles'])!=len(native['profiles']):failures.append('profile count')
 for p,n in zip(reference['profiles'],native['profiles']):
  if len(p['steps'])!=len(n['steps']):failures.append('step count')
  for e,a in zip(p['steps'],n['steps']):
   for field in ('command','events','final','x87','retired'):
    if e[field]!=a.get(field):failures.append(dict(command=e['command'],field=field))
   if e['result']!=a.get('result'):failures.append(dict(command=e['command'],field='callback result'))
   # The ordinary host relocates its bounded temporary frame. This local
   # receiver never escapes; persistent helper receivers remain exact tokens.
   def members(rows):
    return [[f,pc,'caller-local' if f==0x4db620 and pc==0x4dbe3c and 0x2000000<=receiver<0x2008000 and receiver%4==0 else receiver] for f,pc,receiver in rows]
   if members(e['member_sources'])!=members(a.get('member_sources',[])):failures.append(dict(command=e['command'],field='source member joins'))
   projected={0x421710,0x44c000,0x405000,0x44cfd0,0x4c96b0,0x4dc870,0x421bf0,0x421320,0x44d3c0,0x43dfa0,0x421e00,0x421b60}
   if [r for r in e['entries'] if r[0] in projected]!=[r for r in a['calls'] if r[0] in projected]:failures.append(dict(command=e['command'],field='elected entries'))
   if not a['completed']:failures.append(dict(command=e['command'],fault=a.get('fault')))
 if {c['name'] for c in native['controls']} != {'missing service','wrong provider','wrong actor','reentrant service','replaced helper','stale helper','same heap wrong provider'}:failures.append('required controls')
 for c in native['controls']:
  if not c['passed']:failures.append(dict(control=c['name']))
 result=dict(status='fail' if failures else 'pass',steps=sum(len(p['steps']) for p in reference['profiles']),controls=len(native['controls']),failures=failures,source_member_edges=sorted({(hex(f),hex(pc)) for p in native['profiles'] for s in p['steps'] for f,pc,_ in s['member_sources']}),exercised_edges=sorted({hex(a) for p in native["profiles"] for s in p["steps"] for a,_ in s["calls"] if a in OBSERVE}));(out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)
def main():
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence stays in work')
 return prepare(out) if sys.argv[1]=='prepare' else compare(out)
if __name__=='__main__':raise SystemExit(main())
