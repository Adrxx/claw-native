"""Compare the finite shared-owner PathElevator boundary with the original."""
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP
BASE,SIZE=0x10000000,0x10000
ACTOR,STATE,RECT,MANAGER,LEVEL,PALETTE,OWNER,REGISTRY=[BASE+i*0x1000 for i in range(8)]
ALLOC=0x61000000
OBSERVE=(0x4f63ec,0x4683a0,0x468540,0x468890,0x4688f0,0x4f6286,0x4f6428)
class Reference:
 def __init__(self,label,pattern=1,level=1,key=17,lookup=17,pairs=False,missing=False):
  self.label=label;self.lookup=lookup;self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
  self.allocations=[];self.events=[];self.calls=[];self.stages=[];self.next=ALLOC
  self.blocks=[(BASE,SIZE),(0x510020,4),(0x5371fc,4),(0x537960,4),(0x537210,4),(0x528a4c,32)]
  self.w(ACTOR+0x6c,STATE);self.w(STATE+0x10,0x49ee30);self.w(STATE+0x18,0,0);self.w(STATE+0xbc,125)
  self.w(ACTOR+8,0x200);self.w(ACTOR+0xc,OWNER);self.w(OWNER+0x10,REGISTRY)
  self.w(ACTOR+0x100,pattern);self.w(ACTOR+0x110,75);self.w(ACTOR+0x170,key);self.w(ACTOR+0x174,RECT)
  self.w(ACTOR+0x4c,320,240);self.w(ACTOR+0xe8,320,240)
  self.w(RECT+0x18,3,5,45,29)
  if pairs:self.w(ACTOR+0x118,6,150,2,80,0,0)
  if missing:self.w(ACTOR+0x118,0x80000000)
  self.w(0x5371fc,MANAGER);self.w(MANAGER+0x2c,LEVEL);self.w(LEVEL+0x14,level)
  self.w(0x537960,PALETTE);self.w(PALETTE+0x68,1,2,3,4);self.w(PALETTE+0x98,11,22,33,44)
  self.w(0x537210,375);self.w(0x510020,0xffffffff)
  for address in OBSERVE:self.m.observe(address,self.observe)
  for address in (0x4a48e0,0x4f6428,0x4f6286):self.m.intercept(address)
  self.m.on_external=self.external
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
 def w(self,a,*v):self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
 def get(self,a):return self.m.words(a,1)[0]
 def observe(self,m,address):
  sp=m.register(UC_X86_REG_ESP);argc={0x4f63ec:1,0x4683a0:1,0x468540:1,0x468890:4,0x4688f0:1,0x4f6286:2,0x4f6428:1}[address]
  args=[self.get(sp+4+i*4) for i in range(argc)]
  if address==0x4f6286:args[1]=0 # Stack layout belongs to each runtime; bytes and value are compared.
  self.calls.append([address,0 if address in (0x4f63ec,0x4f6428) else m.register(UC_X86_REG_ECX),args])
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i)
  if a==0x4a48e0:
   n=arg(0);token=self.next;self.next=(token+n+15)&~15;self.m.write(token,b'\xcc'*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
  elif a==0x4f6428:self.events.append(['free',arg(0)]);m.return_from_external(0,0)
  elif a==0x4f6286:
   receiver=m.register(UC_X86_REG_ECX);name=m.read(arg(0),32).split(b'\0')[0].decode('ascii');self.w(arg(1),self.lookup);self.events.append(['lookup',receiver,name,self.lookup]);m.return_from_external(self.lookup!=0,8)
  else:raise RuntimeError(hex(a))
 def snapshot(self,name,allocated=True,helper_only=False):
  spans=[(BASE,SIZE)]+[(a,n) for a,n in self.allocations] if allocated else [(BASE,SIZE)]
  if helper_only:spans=[(BASE,SIZE),self.allocations[1]]
  self.stages.append(dict(name=name,bytes=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in spans]))
 def call(self,root,receiver=0,args=()):
  result=self.m.call(root,ecx=receiver,arguments=args)
  if not result.completed:raise RuntimeError((self.label,hex(root),result))
 def run(self):
  self.call(0x49ee30,args=(ACTOR,));self.snapshot('initialized')
  self.call(0x49ee30,args=(ACTOR,));self.snapshot('tick')
  helper=self.get(STATE+0x18)
  if self.label=='destructor-body-then-scalar':self.call(0x49f040,helper);self.snapshot('body-released-path',helper_only=True)
  self.call(0x49f020,helper,(1,));self.snapshot('released',False)
  return dict(label=self.label,actor=ACTOR,state=STATE,initial=self.initial,allocations=self.allocations,stages=self.stages,events=self.events,calls=self.calls)
def prepare(out):
 profiles=[Reference('preset-one').run(),Reference('preset-two',pattern=2).run(),Reference('object-pairs',pattern=0,pairs=True).run(),Reference('missing-path',pattern=0,missing=True).run(),Reference('level-ten-match',level=10).run(),Reference('level-ten-miss',level=10,lookup=99).run(),Reference('destructor-body-then-scalar').run()]
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=profiles),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(profiles))))
def compare(out):
 reference=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());failures=[]
 if len(reference['profiles'])!=len(native['profiles']):failures.append('profile count')
 for expected,actual in zip(reference['profiles'],native['profiles']):
  for key in ('label','stages','events','calls'):
   if expected[key]!=actual[key]:failures.append(dict(profile=expected['label'],field=key))
  if not actual['completed']:failures.append(dict(profile=expected['label'],fault=actual['fault']))
  if actual['allocation_witnesses']!=[True,True]:failures.append(dict(profile=expected['label'],field='source allocation continuations'))
  if expected['label'].startswith('level-ten') and not actual['palette_stack_output']:failures.append(dict(profile=expected['label'],field='palette stack output'))
  if not actual['retired']:failures.append(dict(profile=expected['label'],field='owned release'))
 for control in native['controls']:
  if not control['passed']:failures.append(dict(control=control['name']))
 result=dict(status='fail' if failures else 'pass',profiles=len(reference['profiles']),controls=len(native['controls']),failures=failures)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('derived evidence stays under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
 else:raise ValueError(sys.argv[1])
