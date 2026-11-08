"""Finite ConveyorBelt transport against the hash-verified original."""
import json, struct, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESP
BASE,SIZE,ALLOC=0x10000000,0x30000,0x61000000
ACTOR,STATE,WORLD,REGISTRY,IMAGES,ANIMATIONS,TABLE,STRING,HIT,ATTACK,PLAYER,PLAYERSTATE,CONTROLLER,STATEHANDLERS,TRIEROOT,IDLENODE,MOVENODE,IMAGESET,IMAGE,IMAGETABLE,FRAMETABLE,FRAME=[BASE+i*0x1000 for i in range(1,23)]
CYCLES=[BASE+i*0x1000 for i in range(23,31)]
OBSERVE=(0x431320,0x484d90,0x4f6428,0x431810,0x4f63ec,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4061b0,0x406290,0x4f65f2,0x4f6584,0x4dba00,0x4c8220,0x4c82a0,0x40f680,0x4dc870,0x4c9e30,0x431440,0x4041b0,0x431a70,0x431b10,0x431b40,0x431b70,0x431bd0,0x431c90)
BOUNDARIES=(0x431355,0x43135a,0x431370,0x431375,0x431387,0x43138a,0x431394,0x431397,0x4313a9,0x4313ae,0x4313b8,0x4313bb,0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd)
class Reference:
 def __init__(self,speed=100,exhausted=False,multi_image=False):
  self.speed,self.exhausted,self.multi_image=speed,exhausted,multi_image;self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x20000)
  self.images=[];self.events=[];self.calls=[];self.requests=[];self.allocations=[];self.boundaries=[];self.frontier=None;self.cursor=ALLOC
  self.blocks=[(a,0x400) for a in [ACTOR,STATE,WORLD,REGISTRY,IMAGES,ANIMATIONS,TABLE,STRING,HIT,ATTACK,PLAYER,PLAYERSTATE,CONTROLLER,STATEHANDLERS,TRIEROOT,IDLENODE,MOVENODE,IMAGESET,IMAGE,IMAGETABLE,FRAMETABLE,FRAME]+CYCLES]
  self.blocks += [(a,n) for a,n in [(0x50c6bc,0x24),(0x513740,0x28),(0x510020,4),(0x537668,0x60),(0x537278,0x24),(0x537e88,4),(0x5430c4,4),(0x537210,4),(0x522d48,0x20),(0x523604,0x20),(0x52417c,0x20),(0x5240d8,0x20),(0x526540,0xcc),(0x5469e4,8)]]
  assert [self.get(0x50c6bc+i) for i in [0,4,8,12,16,28,32]]==[0x484d90,0x4c9e30,0x431440,0x4041b0,0x4c96b0,0x4c96b0,0x4c96b0]
  self.w(ACTOR+4,91);self.w(ACTOR+0xc,WORLD);self.w(ACTOR+0x4c,32,64);self.w(ACTOR+0x64,3);self.w(ACTOR+0x6c,STATE)
  self.w(STATE+0xc,WORLD);self.w(STATE+0x10,0x431320);self.w(STATE+0xbc,speed)
  self.w(WORLD+0x10,IMAGES,REGISTRY);self.w(WORLD+0x2c,ANIMATIONS)
  self.w(HIT+0x10,0x4dc830);self.w(ATTACK+0x10,0x4dc850)
  self.w(ACTOR+0x170,IMAGESET,IMAGE);self.w(ACTOR+0x18c,ACTOR)
  self.w(IMAGESET+0x14,IMAGETABLE,1);self.m.write(IMAGESET+0x24,b'LEVEL_CONVEYORBELT\0');self.w(IMAGESET+0x64,0,0);self.w(IMAGETABLE,IMAGE)
  self.w(IMAGE+0x18,32,12,32,12)
  for cycle in CYCLES:self.w(cycle+0xc,FRAMETABLE,1)
  self.w(FRAMETABLE,FRAME);self.w(FRAME,0,0,0,0,0,0,100,19,0,0,0,0)
  if multi_image:
   self.blocks += [(BASE+0x1f000,0x400),(BASE+0x20000,0x400),(BASE+0x21000,0x400)]
   self.w(IMAGESET+0x18,3);self.w(IMAGESET+0x64,0,2);self.w(IMAGETABLE,IMAGE,BASE+0x1f000,BASE+0x20000)
   self.w(BASE+0x1f000+0x18,33,13,33,13);self.w(BASE+0x20000+0x18,34,14,34,14)
   # Both backed records select genuine table images through the animation owner.
   for cycle in CYCLES:self.w(cycle+0x10,2)
   self.w(FRAMETABLE,FRAME,BASE+0x21000)
   self.w(FRAME,0,0,1,2,0,0,40,19,0,0,0,0)
   self.w(BASE+0x21000,0,0,2,2,0,0,40,23,0,0,0,0)
  self.w(PLAYER+0x4c,40,40);self.w(PLAYER+0x118,0,0,8,30);self.w(PLAYER+0x6c,PLAYERSTATE);self.w(PLAYERSTATE+0x14,CONTROLLER);self.w(CONTROLLER+0x84,901)
  self.w(0x537e88,PLAYER);self.w(0x5430c4,17);self.w(0x537210,113)
  self.w(0x537668,*([0]*12));self.w(0x537680,TRIEROOT)
  self.w(TRIEROOT,IDLENODE,MOVENODE,26,0,0);self.w(IDLENODE,IDLENODE,IDLENODE,26,0x523604,7);self.w(MOVENODE,MOVENODE,MOVENODE,26,0x526544,8)
  self.w(0x537698,0,0,0,63,TABLE,0,4,0,0,0,0,0);self.w(STRING,1,0,0,0)
  self.w(0x537278,0,0,0,63,STATEHANDLERS,0,4,0,0)
  for i in range(64):self.w(TABLE+i*4,STRING+12)
  self.w(STATEHANDLERS+7*4,0x431b10,0x431b70)
  for a in OBSERVE:self.m.observe(a,self.observe_call)
  for a in BOUNDARIES:self.m.observe(a,lambda m,a:self.boundaries.append(a))
  self.imports={self.get(0x5469e4):'strlen',self.get(0x5469e8):'decrement',self.get(0x546ce0):'intersect'};self.blocks.append((0x546ce0,4))
  for a in (0x4a48e0,0x4a49b0,0x4f6286,0x5022b5):self.m.intercept(a)
  self.m.observe(0x4f6974,self.buffer);self.m.on_external=self.external;self.blocks += [(0x52e1cc,4),(self.get(0x52e1cc)-12,13)];self.initial=self.snapshot(self.blocks)
 def observe_call(self,m,a):
  self.calls.append([a,m.register(UC_X86_REG_ECX) if a not in (0x431320,0x4f63ec,0x4dc870,0x4f6428) else 0])
  if a in [0x406290,0x4c8220,0x4c82a0,0x4f6584]:self.images.append([a,self.get(ACTOR+0x174)])
 def w(self,a,*v):self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
 def get(self,a):return self.m.words(a,1)[0]
 def snapshot(self,blocks):return [dict(address=a,data=self.m.read(a,n).hex()) for a,n in blocks]
 def cstr(self,a):return self.m.read(a,128).split(b'\0')[0].decode('ascii')
 def buffer(self,m,a):self.events.append(['buffer',m.register(UC_X86_REG_ECX),self.get(m.register(UC_X86_REG_ECX))])
 def lookup(self,receiver,key):
  if receiver==REGISTRY+16:return {'LogicHit':HIT,'LogicAttack':ATTACK}.get(key,0)
  if receiver==ANIMATIONS+16:return dict(zip([self.cstr(a) for a in [0x52417c,0x5240d8,0x5265ec,0x5265dc,0x5265c8,0x5265b0,0x526598,0x526580]],CYCLES)).get(key,0)
  raise AssertionError(('map',hex(receiver),key))
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+i*4)
  if a==0x4a48e0:
   count=arg(0);value=0 if count==self.exhausted else self.cursor
   self.requests.append([a,self.get(sp),self.get(sp+20),count,m.register(UC_X86_REG_EBX)])
   if value:self.cursor+=(count+15)&~15;self.allocations.append((value,count));m.write(value,bytes([204])*count)
   self.events.append(['malloc',value,count]);m.return_from_external(value,0)
  elif a==0x4a49b0:self.events.append(['free',arg(0)]);m.return_from_external(0,0)
  elif a==0x4f6286:
   key=self.cstr(arg(0));receiver=m.register(UC_X86_REG_ECX);value=self.lookup(receiver,key);self.w(arg(1),value);self.events.append(['registry',receiver,key,value]);m.return_from_external(int(value!=0),8)
  elif a==0x5022b5:self.frontier=a;m.uc.emu_stop()
  elif self.imports.get(a)=='strlen':m.return_from_external(len(self.cstr(arg(0))),4)
  elif self.imports.get(a)=='decrement':value=(self.get(arg(0))-1)&0xffffffff;self.w(arg(0),value);m.return_from_external(value,4)
  elif self.imports.get(a)=='intersect':
   first=self.m.words(arg(1),4);second=self.m.words(arg(2),4);rect=[max(first[0],second[0]),max(first[1],second[1]),min(first[2],second[2]),min(first[3],second[3])];ok=rect[0]<rect[2] and rect[1]<rect[3]
   self.w(arg(0),*(rect if ok else [0]*4));self.events.append(['intersect',first,second,rect if ok else [0]*4]);m.return_from_external(int(ok),12)
  else:raise AssertionError(hex(a))
 def run(self):
  steps=[dict(command=c,x=x,playerMode=mode) for c,x,mode in [(0,40,0),(1000,40,0),(29,40,0),(30,40,0),(7,40,0),(8,40,0),(8,400,0),(7,40,3),(8,40,3)]];snapshots=[];results=[]
  for s in steps:
   self.w(STATE+0x1c,s['command']);self.w(PLAYER+0x4c,s['x']);self.w(PLAYER+0xcc,s['playerMode']);done=self.m.call(0x431320,arguments=[ACTOR])
   if not done.completed:
    if self.frontier is None:raise RuntimeError((self.speed,s,done,self.calls[-8:],self.events[-8:]))
    break
   results.append(self.m.register(UC_X86_REG_EAX));snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174),(PLAYER,0x174),(CONTROLLER,0x88),(0x537668,0x60),(0x537278,0x24),(0x537e88,4),(0x5430c4,4)]+([(a,0x400) for a in [IMAGESET,IMAGETABLE,IMAGE,BASE+0x1f000,BASE+0x20000,FRAMETABLE,FRAME,BASE+0x21000]] if self.multi_image else [])+self.allocations))
  roundtrip=[]
  if (self.speed==-451 or self.multi_image) and not self.exhausted:
   helper=self.get(STATE+0x18)
   done=self.m.call(0x484d90,ecx=helper,arguments=[1]);assert done.completed
   self.w(STATE+0x18,0);self.w(STATE+0x1c,0)
   done=self.m.call(0x431320,arguments=[ACTOR]);assert done.completed
   roundtrip=self.snapshot([(ACTOR,0x1b4),(STATE,0x174),(PLAYER,0x174),(CONTROLLER,0x88),(0x537668,0x60),(0x537278,0x24),(0x537e88,4),(0x5430c4,4)]+([(a,0x400) for a in [IMAGESET,IMAGETABLE,IMAGE,BASE+0x1f000,BASE+0x20000,FRAMETABLE,FRAME,BASE+0x21000]] if self.multi_image else [])+self.allocations)
  return dict(images=self.images,multi_image=self.multi_image,roundtrip=roundtrip,label=str(self.speed)+("-multi-image" if self.multi_image else "")+(f"-exhaustion-{self.exhausted}" if self.exhausted else ""),speed=self.speed,exhausted=self.exhausted,initial=self.initial,imports=self.imports,steps=steps,results=results,snapshots=snapshots,events=self.events,requests=self.requests,calls=self.calls,boundaries=self.boundaries,frontier=self.frontier,allocations=self.allocations)
def prepare(out):
 probe=Reference();metadata=[]
 for site,continuation,target in [(0x431355,0x43135a,0x4f63ec),(0x431370,0x431375,0x431810),(0x4313a9,0x4313ae,0x4dc870),(0x4f6499,0x4f649e,0x4f63ec),(0x4f65f7,0x4f65fc,0x4f6433)]:
  body=probe.m.read(site,5);assert body[0]==0xe8
  assert (site+5+struct.unpack('<i',body[1:])[0])&0xffffffff==target and site+5==continuation
  metadata.append(dict(call=site,continuation=continuation,target=target))
 for site,continuation in [(0x431387,0x43138a),(0x431394,0x431397),(0x4313b8,0x4313bb)]:
  body=probe.m.read(site,3);assert body=={0x431387:bytes.fromhex("ff5010"),0x431394:bytes.fromhex("ff5220"),0x4313b8:bytes.fromhex("ff521c")}[site] and continuation-site==3
  metadata.append(dict(call=site,continuation=continuation,target=0x4c96b0))
 profiles=[Reference(n).run() for n in [-451,-300,-225,-150,-75,-1,0,74,75,150,225,300,451]]
 profiles += [Reference(n,multi_image=True).run() for n in [-451,150]]
 expected=[0x431355,0x43135a,0x431370,0x431375,0x431387,0x43138a,0x431394,0x431397,0x4313b8,0x4313bb]
 expected += [0x4313a9,0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd,0x4313ae]*5
 assert all([a for a in p['boundaries'][:len(expected)+8] if a!=0x4313bb]==[a for a in expected if a!=0x4313bb] and p['boundaries'][:len(expected)+8].count(0x4313bb)==9 for p in profiles),profiles[0]['boundaries']
 for p in profiles:
  if p['multi_image']:
   teardown=[image for function,image in p['images'] if function==0x4f6584]
   assert teardown and all(image!=IMAGE for image in teardown),p['images']
   selected=[struct.unpack_from('<I',bytes.fromhex(s[0]['data']),0x174)[0] for s in p['snapshots']]
   assert len(set(selected))>1,selected
   assert p['roundtrip'] and p['frontier'] is None
 (out/'reference.json').write_text(json.dumps(dict(version=1,executable_sha256=claw().sha256,call_metadata=metadata,profiles=profiles,exhaustions=[Reference(100,88).run(),Reference(100,31).run()]),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(profiles))))
def compare(out):
 ref,actual=[json.loads((out/n).read_text()) for n in ['reference.json','native.json']];failures=[]
 for group in ['profiles','exhaustions']:
  if len(ref[group])!=len(actual[group]):failures.append(group+' count')
  for r,n in zip(ref[group],actual[group]):
   for key in ['label','results','snapshots','roundtrip','events','frontier','images']:
    if r[key]!=n[key]:failures.append(dict(label=r['label'],field=key))
   if n.get('shadowOffered'):failures.append(dict(label=r['label'],field='canonical shadow'))
   if r['requests']!=n['requests']:failures.append(dict(label=r['label'],field='allocation CALL context'))
   if not n['physicalIntegrity']:failures.append(dict(label=r['label'],field='allocation identity'))
   if not r['exhausted']:
    def visible(calls):
     result=[];temporary=False;previous=0
     for f,receiver in calls:
      # Physical CString teardown releases its exact Memory lease directly.
      if f==0x4f6428 and previous==0x4f6584:continue
      previous=f
      if f==0x4f65f2:temporary=True
      if f in [0x4f65f2,0x4f6584]:receiver=0
      if f==0x4f6584:temporary=False
      if f not in [0x431320,0x431a70,0x431b40,0x431bd0,0x431c90]:result.append([f,receiver])
     return result
    if visible(r['calls']) != visible(n['calls']):failures.append(dict(label=r['label'],field='ordered canonical calls'))
    if n['completed']!=[True]*len(r['steps']):failures.append(dict(label=r['label'],field='completion'))
 if not actual.get('controls'):failures.append('missing controls')
 for c in actual['controls']:
  if not c['passed']:failures.append(dict(control=c['name']))
 result=dict(status='fail' if failures else 'pass',profiles=len(ref['profiles']),multi_image_profiles=sum(p['multi_image'] for p in ref['profiles']),commands=[0,1000,29,30,7,8],call_metadata=ref['call_metadata'],controls=len(actual['controls']),unresolved_dependencies=[] if not failures else None,command='scripts/check-conveyor-belt-transport.sh',failures=failures)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve();assert (ROOT/'work').resolve() in out.parents;out.mkdir(parents=True,exist_ok=True)
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
 else:raise ValueError(sys.argv[1])
