"""Focused original/native Omar comparison; derived data stays in work/."""
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from Tests.clawparity.program import claw
from Tests.clawparity.kernel import Machine
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP
BASE,SIZE,ALLOC=0x10000000,0x10000,0x62000000
ACTOR,STATE,LEVEL,REGISTRY,PLAYER=[BASE+i*0x1000 for i in range(1,6)]
CALLBACK=0x4633a0
OBSERVE=(CALLBACK,0x463460,0x40e0d0,0x44c000,0x40e1b0,0x40e5b0,0x4c96b0,0x4dc870,0x464010,0x463b40,0x44d3c0,0x463a30,0x4f6439,0x4db620,0x4dbd60,0x4dbe10,0x4dbcd0,0x4f6584,0x464770,0x4640b0,0x464f20,0x464fe0,0x465480,0x484d90,0x4c8da0,0x4080a0,0x463a30,0x4c80c0)
OBSERVE=tuple(dict.fromkeys(OBSERVE))

def audit_original():
 p=claw()
 def read(a,n):
  for section in p.sections:
   if section.address<=a and a+n<=section.address+len(section.data):return section.data[a-section.address:a-section.address+n]
  raise ValueError(hex(a))
 for site,target,ret in ((0x4633d8,0x4f63ec,0x4633dd),(0x4633f3,0x463460,0x4633f8),(0x46342c,0x4dc870,0x463431)):
  raw=read(site,5);assert raw[0]==0xe8 and site+5+struct.unpack('<i',raw[1:])[0]==target and ret==site+5
 expected={0:0x463a30,4:0x464010,8:0x463b40,12:0x4640b0,16:0x40e1b0,28:0x4c96b0,32:0x40e5b0,72:0x4646f0}
 for offset,target in expected.items():assert struct.unpack('<I',read(0x50eafc+offset,4))[0]==target
 assert struct.unpack('<I',read(0x50ebb4,4))[0]==0x484d90
 return p.sha256

class AllocationFailureBoundary(Exception):pass

class Reference:
 def __init__(self,out,bindings=False):
  self.bindings=bindings
  self.resource_inputs=json.loads((out/"resource-inputs.json").read_text());self.resources=json.loads((out/"resources.json").read_text())
  self.program=claw();self.m=Machine(self.program,BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000);self.m.uc.mem_map(0x61000000,0x1000000)
  for b in self.resources["spans"]:self.m.write(b["address"],bytes.fromhex(b["data"]))
  self.events=[];self.entries=[];self.allocations=[];self.next=ALLOC;self.source_pending=[];self.sources=[];self.freed=set();self.fail_allocation=False;self.base_frame=None;self.temporary=None;self.temporary_frames=[]
  self.w(ACTOR+0x18c,ACTOR);self.w(ACTOR+0xdc,32,32);self.w(ACTOR+0xc,LEVEL);self.w(ACTOR+0x6c,STATE);self.w(ACTOR+0x4c,100,200)
  self.w(STATE+0xc,LEVEL);self.w(LEVEL+8,BASE+0x9000);self.w(BASE+0x900c,LEVEL);self.w(BASE+0x9028,1);self.w(BASE+0x9010,0,0,0,0);self.w(BASE+0xa010,0x464f20);self.w(BASE+0xa110,0x4dc830);self.w(BASE+0xa210,0x4dc850);self.w(STATE+0x10,CALLBACK);self.w(LEVEL+0x10,REGISTRY);self.w(LEVEL+0x24,REGISTRY,REGISTRY);self.w(LEVEL+0x14,REGISTRY);self.w(LEVEL+0x1c,REGISTRY+0x100);self.w(LEVEL+0x2c,REGISTRY+0x200)
  self.w(0x537e88,PLAYER);self.w(0x510020,0xffffffff)
  plane,rows,cells=BASE+0x7000,BASE+0x8000,BASE+0x8100
  self.w(REGISTRY+0x5c,plane);self.w(REGISTRY+0x64,32,32)
  self.w(plane+0x20,cells,rows);self.w(plane+0x30,65536,65536)
  self.w(plane+0x8c,16,16);self.w(rows,0);self.w(cells,0xeeeeeeee)
  node=BASE+0x6000;self.w(node,node,node,0,0x523148,7);self.w(0x537668+0x18,node)
  self.w(0x537bd8,7,7,BASE+0x6100,0,4);self.w(BASE+0x6100,0x464770,0x4640b0,0x464f20,0x464fe0,0x465480,0x484d90,0x4c8da0,0x4080a0,0x463a30,0x4c80c0)
  self.w(0x537698+8,7,7,BASE+0x6200,0,4);self.w(BASE+0x6200,0x523148)
  self.w(0x52e1c8,0x52e1b8);self.w(0x52e1b8,0xffffffff,0,0);self.m.write(0x52e1c4,b'\0')
  self.w(0x546d5c,0x710c00);self.w(0x546cdc,0x710c10);self.w(0x546a40,0x710c20);self.w(0x546cd4,0x710c30)
  for a in OBSERVE:self.m.observe(a,self.entry)
  for a in (0x44c04e,0x44c05e,0x4dc1a7,0x4dbe3c):self.m.observe(a,self.source_return)
  for a in (0x4a48e0,0x4a49b0,0x4f6286,0x4f6974,0x4a3050,0x4f51c5):self.m.intercept(a)
  self.m.on_external=self.external
  self.initial=[dict(address=s.address,data=self.m.read(s.address,s.size).hex()) for s in self.program.sections]
  self.initial.append(dict(address=BASE,data=self.m.read(BASE,SIZE).hex()))
 def w(self,a,*v):self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
 def get(self,a):return self.m.words(a,1)[0]
 def entry(self,m,a):
  self.entries.append([a,0 if a==0x464f20 else m.register(UC_X86_REG_ECX)])
  if a==0x44c000:self.base_frame=m.register(UC_X86_REG_ESP)
  if a==0x4dbe10:
   self.temporary=m.register(UC_X86_REG_ECX);assert self.temporary==self.base_frame-28
   self.temporary_frames.append(dict(receiver=self.temporary,callerFrame=self.base_frame))
  if a in (0x4f6439,0x4db620):
   sp=m.register(UC_X86_REG_ESP);self.source_pending.append((a,m.register(UC_X86_REG_ECX),sp,self.get(sp),[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)],m.fs_head))
 def source_return(self,m,pc):
  a,receiver,sp,expected,preserved,fs=self.source_pending.pop();assert pc==expected
  self.sources.append(dict(function=a,receiver=receiver,returnPC=pc,eax=m.register(UC_X86_REG_EAX),stackDelta=m.register(UC_X86_REG_ESP)-sp,preserved=preserved==[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)] and fs==m.fs_head))
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i);receiver=m.register(UC_X86_REG_ECX)
  if a==0x5022b5:raise AllocationFailureBoundary()
  if a==0x4a48e0:
   n=arg(0);t=0 if self.fail_allocation else self.next;
   if self.fail_allocation:self.events.append(['malloc',0,n]);m.return_from_external(0,0);return
   self.next=(t+(512 if n==0x1b4 else n)+15)&~15;self.m.write(t,bytes([0xcc])*n);self.allocations.append([t,n]);self.events.append(['malloc',t,n]);m.return_from_external(t,0)
  elif a==0x4a49b0:
   token=arg(0);assert token in dict(self.allocations) and token not in self.freed,('invalid or duplicate original free',hex(token));extent=dict(self.allocations)[token];self.events.append(['free',token,self.m.read(token,extent).hex()]);self.freed.add(token);m.return_from_external(0,0)
  elif a==0x4f51c5:
   actor=arg(0);node=BASE+0xb000+self.get(receiver+0xc)*16;tail=self.get(receiver+8);self.w(node,0,tail,actor)
   if tail:self.w(tail,node)
   else:self.w(receiver+4,node)
   self.w(receiver+8,node);self.w(receiver+0xc,self.get(receiver+0xc)+1);self.events.append(['append',receiver,actor,node]);m.return_from_external(node,4)
  elif a==0x4a3050:m.return_from_external(17,0)
  elif a==0x4f6974:m.return_from_external(self.get(receiver),4)
  elif a==0x4f6286:
   name=m.read(arg(0),128).split(b'\0')[0].decode('ascii');value=BASE+0xa000 if name=='OmarShield' else BASE+0xa100 if self.bindings and name=='LogicHit' else BASE+0xa200 if self.bindings and name=='LogicAttack' else (self.resources['images'] if receiver==REGISTRY+0x10 else self.resources['sequences']).get(name,0);self.events.append(['registry',receiver,name,value]);self.w(arg(1),value);m.return_from_external(bool(value),8)
  elif a in (0x710c00,0x710c10):
   values=[arg(i) for i in range(1,5)] if a==0x710c00 else [0]*4
   self.w(arg(0),*values);self.events.append(['rectangle',*values]);m.return_from_external(1,20 if a==0x710c00 else 4)
  elif a==0x710c20:m.return_from_external(0,8)
  elif a==0x710c30:
   l,t,r,b=self.m.words(arg(0),4);x,y=arg(1),arg(2);signed=lambda n:n if n<0x80000000 else n-0x100000000;m.return_from_external(int(signed(l)<=signed(x)<signed(r) and signed(t)<=signed(y)<signed(b)),12)
  else:raise RuntimeError(hex(a))
 def snapshot(self,command):
  spans=[(s.address,s.size) for s in self.program.sections if s.name=='.data']+[(ACTOR,0x1b4),(STATE,0x174),(LEVEL,0x1000),(REGISTRY,0x1000),(BASE+0x9000,0x3000),(0x53c19c,4),(0x5349dc,4)]+[(b["address"],len(b["data"])//2) for b in self.resources["spans"]]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(command=command,entries=list(self.entries),events=list(self.events),allocations=list(self.allocations),final=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in spans],x87=self.m.x87_state(),sources=list(self.sources),temporary_frames=list(self.temporary_frames))
 def run_failure(self):
  self.fail_allocation=True;self.m.intercept(0x5022b5);self.w(STATE+0x1c,0)
  try:self.m.call(CALLBACK,arguments=(ACTOR,))
  except AllocationFailureBoundary:return dict(boundary=0x5022b5,command=self.get(STATE+0x1c),helper=self.get(STATE+0x18),events=self.events)
  raise AssertionError('allocation failure unexpectedly returned')
 def run(self):
  snapshots=[]
  for command in (0,1000,7,29,30):
   self.w(STATE+0x1c,command);done=self.m.call(CALLBACK,arguments=(ACTOR,))
   if not done.completed:raise RuntimeError((command,done))
   snapshots.append(self.snapshot(command))
  helper=self.get(STATE+0x18)
  for i in range(9):
   child=self.get(helper+0x484+i*4);logic=self.get(child+0x6c)
   # The real logic scalar owner destroys its behavior through vtable slot zero.
   done=self.m.call(0x4c80c0,ecx=logic,arguments=(1,));assert done.completed,done
   for offset in (0x70,0x78):
    secondary=self.get(child+offset)
    if secondary:
     done=self.m.call(0x4c80c0,ecx=secondary,arguments=(1,));assert done.completed,done
     self.w(child+offset,0)
   factory=BASE+0x9000;node=self.get(child+0x68);following=self.get(node);previous=self.get(node+4)
   if previous:self.w(previous,following)
   else:self.w(factory+0x14,following)
   if following:self.w(following+4,previous)
   else:self.w(factory+0x18,previous)
   self.w(factory+0x1c,self.get(factory+0x1c)-1)
   self.m.call(0x4f6428,arguments=(child,))
  done=self.m.call(0x463a30,ecx=helper,arguments=(1,))
  if not done.completed:raise RuntimeError(('retire',done))
  for offset in (0x70,0x78):
   secondary=self.get(ACTOR+offset)
   if secondary:
    done=self.m.call(0x4c80c0,ecx=secondary,arguments=(1,));assert done.completed,done
    self.w(ACTOR+offset,0)
  self.w(STATE+0x18,0);snapshots.append(self.snapshot('retire'))
  self.w(STATE+0x1c,0);done=self.m.call(CALLBACK,arguments=(ACTOR,))
  if not done.completed:raise RuntimeError(('recreate',done))
  snapshots.append(self.snapshot(0))
  return dict(label='construction-lifecycle-bindings' if self.bindings else 'construction-lifecycle',resource_bindings=self.bindings,initial=self.initial,resource_inputs=self.resource_inputs,snapshots=snapshots)

def normalize_stack_temporary(snapshot):
 result=json.loads(json.dumps(snapshot))
 # The admitted shield callback owns its constructor body inline. Its original
 # CALL is retained in reference evidence and required below; native transport
 # has no separate dependency invocation at this internal implementation seam.
 # Constructor output, physical dependencies, child identities and bytes remain
 # compared in every snapshot.
 result['entries']=[row for row in result['entries'] if row[0]!=0x464fe0]
 frames=snapshot['temporary_frames']
 for witness in frames:
  receiver,frame=witness['receiver'],witness['callerFrame']
  if not (0x1ff0000<=receiver and receiver==frame-28 and frame<=0x2008000):
   raise ValueError('temporary bitset is not the declared base caller local')
 addresses={w['receiver'] for w in frames}
 for entry in result['entries']:
  if entry[0] in (0x4dbe10,0x4db620,0x4dbcd0) and entry[1] in addresses:entry[1]='base-local-28'
 for source in result['sources']:
  if source['function']==0x4db620 and source['returnPC']==0x4dbe3c:
   if source['receiver'] not in addresses or source['eax']!=source['receiver']:
    raise ValueError('temporary bitset source return lost its local identity')
   source['receiver']=source['eax']='base-local-28'
 return result

def main():
 command=sys.argv[1];out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
 if command=='resource-inputs':
  program=claw()
  def name(address):
   for section in program.sections:
    if section.address<=address<section.address+len(section.data):return section.data[address-section.address:].split(b'\0')[0].decode('ascii')
   raise ValueError(hex(address))
  addresses=(0x529a04,0x5299f0,0x5299e0,0x5299cc,0x5299b4,0x5299a0,0x52998c,0x529a8c,0x529aa0,0x5234b4)
  (out/'resource-inputs.json').write_text(json.dumps(dict(root=str(ROOT/'App/GameData'),images=[name(a) for a in (0x529a18,0x529a8c,0x529aa0)],sequences=list(dict.fromkeys(map(name,addresses))))))
 elif command=='prepare':
  audit_original();profiles=[Reference(out,bindings=b).run() for b in (False,True)]
  (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=profiles,allocation_failure=Reference(out).run_failure()))+'\n')
  print(json.dumps(dict(status='prepared',profiles=2)))
 elif command=='compare':
  ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());failures=[]
  if ref.get('allocation_failure')!=dict(boundary=0x5022b5,command=1000,helper=0,events=[['malloc',0,0xd48]]):failures.append(dict(field='original allocation failure boundary'))
  if native.get('allocation_failure')!=ref.get('allocation_failure'):failures.append(dict(field='native allocation failure boundary'))
  if len(ref['profiles'])!=len(native['profiles']):failures.append(dict(field='profile count'))
  if len(native['controls'])!=24 or len({c['name'] for c in native['controls']})!=24:failures.append(dict(field='required control count'))
  for expected,actual in zip(ref['profiles'],native['profiles']):
   if expected['label']!=actual['label']:failures.append(dict(field='profile label'))
   allocated=expected['snapshots'][-1]['allocations']
   shape=([0xd48,0x174,0x174]+[0x1b4,0x174,0x48,0x174,0x174]*9) if expected['resource_bindings'] else ([0xd48]+[0x1b4,0x174,0x48]*9)
   if [n for _,n in allocated] != shape*2 or len({a for a,_ in allocated})!=len(shape)*2:failures.append(dict(field='original recreate allocation identity'))
   required_entries={0x463460,0x40e0d0,0x44c000,0x40e1b0,0x40e5b0,0x4c96b0,0x4dc870,0x464010,0x463b40,0x464770,0x4640b0,0x464f20,0x464fe0,0x465480,0x484d90,0x4c8da0,0x4080a0,0x44d3c0,0x463a30,0x4dbcd0,0x4f6584}
   if not required_entries.issubset({a for a,_ in expected['snapshots'][-1]['entries']}):failures.append(dict(field='original exercised entries'))
   if [x['command'] for x in expected['snapshots']]!=[0,1000,7,29,30,'retire',0]:failures.append(dict(field='required original commands'))
   if len(expected['snapshots'])!=len(actual['snapshots']):failures.append(dict(field='snapshot count',actual=actual.get('completions')))
   for index,(e,a) in enumerate(zip(expected['snapshots'],actual['snapshots'])):
    if len(e.get('temporary_frames',[]))!=len(a.get('temporary_frames',[])):failures.append(dict(snapshot=index,field='temporary caller frame count'))
    try:e,a=normalize_stack_temporary(e),normalize_stack_temporary(a)
    except (KeyError,ValueError) as error:
     failures.append(dict(snapshot=index,field='temporary caller frame',detail=str(error)));continue
    for field in ('command','entries','events','allocations','final','x87','sources'):
     if e[field]!=a[field]:failures.append(dict(snapshot=index,command=e['command'],field=field))
   if not all(c['completed'] for c in actual['completions']):failures.append(dict(field='completion',actual=actual['completions']))
  failures += [c['name'] for c in native['controls'] if not c['passed']]
  resources=json.loads((out/'resources.json').read_text())
  if not all(resources[k] and all(resources[k].values()) for k in ('images','sequences')):failures.append(dict(field='loaded physical resources'))
  metadata=json.loads((ROOT/'work/native-object-connections/omar/boundary-review.json').read_text())
  result=dict(status='fail' if failures else 'pass',failures=failures,profiles=len(ref['profiles']),controls=len(native['controls']),loaded_images=len(resources['images']),loaded_sequences=len(resources['sequences']),resource_spans=len(resources['spans']),reference_sha256=ref['executable_sha256'],callback=metadata['callback'],constructor='0x463460',calls=metadata['calls'],virtual_targets=metadata['vtable'],comparison_command='scripts/check-omar-transport.sh',native_owner='ClawNativeCanonicalHost/ClawNativeMfcMemory',unresolved_dependencies=[c['fault'] for profile in native['profiles'] for c in profile['completions'] if not c['completed']])
  (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)
 else:raise ValueError(command)
if __name__=='__main__':raise SystemExit(main())
