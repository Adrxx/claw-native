"""Finite Siren host transport. Execute the hash-verified original, never stubs for game bodies."""
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Tests.NativeObjectConnections import bear_sailor_transport as base
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
BASE,SIZE,ALLOC=base.BASE,base.SIZE,base.ALLOC
OBSERVE=tuple(a for a in base.OBSERVE if a not in (0x409920,0x40a440,0x40a490,0x409ee0,0x409f70,0x40a040))+(0x489c50,0x48a0d0,0x48a0f0,0x489850,0x48a160,0x48a240,0x48a2e0,0x44d9f0,0x4a30e0)
class Reference(base.Reference):
 def __init__(self,status=0,live=False):
  super().__init__(status,live)
  # Reuse the physical resource-map fixture layout, elect Siren resource names.
  old=self.tokens['managers']['sprites']
  sprite=self.lookup(old+0x10,'LEVEL_BEARSAILOR')
  manager=base.cases.world.__globals__['resource_manager'](self,{'LEVEL_SIREN':sprite},1,'Siren sprites')
  world=self.tokens['world']
  for offset in range(0,0x40,4):
   if self.get(world+offset)==old:self.put(world+offset,manager)
  oldAnimations=self.tokens['managers']['animations']
  entries={}
  buckets,count=self.get(oldAnimations+0x14),self.get(oldAnimations+0x18)
  for index in range(count):
   node=self.get(buckets+4*index)
   while node:
    entries[self.text(self.get(node+8)).replace('BEARSAILOR','SIREN')]=self.get(node+12)
    node=self.get(node)
  animations=base.cases.world.__globals__['resource_manager'](self,entries,1,'Siren animations')
  for offset in range(0,0x40,4):
   if self.get(world+offset)==oldAnimations:self.put(world+offset,animations)
  self.put(self.tokens['state']+0x10,0x489730)
  row=self.object(4,words=[0x48a2e0]);self.put(0x53c300,17,17,row,row,4)
  self.put(self.tokens['owner']+0x18c,self.tokens['owner'])
  self.put(0x537964,0) # notify still executes the real base, then its non-Level-12 return.
  self.entries=[];self.events=[];self.continuations=[]
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
  for address in OBSERVE:
   if address not in base.OBSERVE:self.m.observe(address,self.entry)
 def entry(self,m,a):
  if a not in OBSERVE:return
  receiver=m.register(UC_X86_REG_ECX) if a not in (0x4f63ec,0x4dc870,0x4f6428,0x4a30e0) else 0
  arities={0x489c50:1,0x48a0d0:1,0x489850:1,0x48a160:1}
  if a not in arities:return super().entry(m,a)
  arguments=m.words(m.register(UC_X86_REG_ESP)+4,arities[a]);self.entries.append([a,receiver,list(arguments)])
  if a==0x489c50:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
 def external(self,m,address):
  if address==0x4a49b0:
   token=self.get(m.register(UC_X86_REG_ESP)+4);count=dict(self.allocations)[token]
   self.events.append(['free',token,self.read(token,count).hex()]);self.released.add(token);m.return_from_external(0,0)
  else:super().external(m,address)
 def snapshot(self):
  spans=[(BASE,SIZE),(0x53c2f8,0x28),(0x537698,0x28),(0x537668,0x20),(0x510020,4)]+self.allocations
  return [dict(address=a,data='released' if a in self.released else self.read(a,n).hex()) for a,n in spans]
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming)
  stages=[]
  plan=[dict(label='construct',command=0),dict(label='park',command=1000),dict(label='detach',command=29),dict(label='no-op',command=30),dict(label='home',command=17,writes=[[self.tokens['owner']+0x19c,100],[self.tokens['owner']+0x1a0,1]]),dict(label='delete',retire=True),dict(label='recreate',command=0)]
  for stage in plan:
   for address,value in stage.get('writes',[]):self.put(address,value)
   if stage.get('retire'):
    r=self.m.call(0x48a0d0,ecx=self.get(self.tokens['state']+0x18),arguments=(1,));self.put(self.tokens['state']+0x18,0)
   else:
    self.put(self.tokens['state']+0x1c,stage['command']);r=self.m.call(0x489730,arguments=(self.tokens['owner'],))
   if not r.completed:raise RuntimeError((stage['label'],r,hex(self.m.register(UC_X86_REG_EIP))))
   stage.update(outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),final=self.snapshot());stages.append(stage)
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,continuations=self.continuations,incoming=self.incoming,allocations=self.allocations,stages=stages)
def prepare(out):
 rows=[Reference(status,live).run(f'sw-{status:x}-live-{int(live)}') for status,live in ((0,False),(0x20,False),(0x20,True))]
 m=Machine(claw(),BASE,SIZE);metadata=[]
 for pc,target,continuation in ((0x489768,0x4f63ec,0x48976d),(0x489783,0x489c50,0x489788),(0x4897bc,0x4dc870,0x4897c1),(0x489c74,0x44c000,0x489c79)):
  code=m.read(pc,5);assert code[0]==0xe8 and (pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 for pc,code,continuation in ((0x48979a,b'\xff\x50\x10',0x48979d),(0x4897a7,b'\xff\x52\x20',0x4897aa),(0x4897cb,b'\xff\x52\x1c',0x4897ce)):
  assert m.read(pc,len(code))==code and pc+len(code)==continuation;metadata.append(dict(call=pc,continuation=continuation))
 slots=((0,0x48a0d0),(4,0x48a160),(8,0x489850),(12,0x44d3c0),(16,0x405000),(20,0x44df60),(24,0x4bb030),(28,0x4c96b0),(32,0x44cfd0),(36,0x43dfa0))
 for offset,target in slots:assert m.words(0x50f694+offset,1)[0]==target
 # Original Siren registration pairs LS_HOME with the actual update body.
 assert m.words(0x489a60,1)[0]==0x5234ec and m.words(0x489ae9,1)[0]==0x48a2e0
 # Stop at the unavailable new-handler boundary after real operator new has
 # observed physical malloc exhaustion. No helper or successful return is supplied.
 class ExhaustedBoundary(Exception):pass
 exhausted=Reference()
 def new_handler(machine,address):raise ExhaustedBoundary(address)
 exhausted.m.observe(0x5022b5,new_handler)
 def exhausted_service(machine,address):
  if address==0x4a48e0:machine.return_from_external(0,0)
  else:exhausted.external(machine,address)
 exhausted.m.on_external=exhausted_service
 try:exhausted.m.call(0x489730,arguments=(exhausted.tokens['owner'],))
 except ExhaustedBoundary as error:assert error.args==(0x5022b5,)
 else:raise AssertionError('original allocation exhaustion returned')
 assert not exhausted.allocations and exhausted.get(exhausted.tokens['state']+0x1c)==1000
 for p in rows:
  assert [r for r in p['continuations'] if r[0]==0x489c50]==[[0x489c50,0x489788]]*2
  assert [r for r in p['continuations'] if r[0]==0x44c000]==[[0x44c000,0x489c79]]*2
  assert [r for r in p['continuations'] if r==[0x4f63ec,0x48976d]]==[[0x4f63ec,0x48976d]]*2
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,call_metadata=metadata,vtable=slots,state_registration=dict(name='LS_HOME',target=0x48a2e0),exhaustion_boundary=0x5022b5,profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 assert len(ref['profiles'])==3 and len(native['profiles'])==3
 # Embedded base/destructor/helper calls are checked through bytes and physical events.
 selected=set(OBSERVE)-{0x44bc60,0x48a0f0,0x4f6286,0x4f6428,0x48a240,0x4a30e0}
 for e,a in zip(ref['profiles'],native['profiles']):
  if not a['completed'] or not a['allocation_witness']:fail.append(dict(label=e['label'],fault=a['fault']))
  if len(e['stages'])!=len(a['stages']):fail.append('stage count')
  for es,ns in zip(e['stages'],a['stages']):
   for field in ('label','outgoing','events','final'):
    if es[field]!=ns[field]:fail.append(dict(label=e['label'],stage=es['label'],field=field))
   visible=[r for i,r in enumerate(es['entries']) if not (r[0]==0x4dca10 and i>0 and es['entries'][i-1]==[0x43dfa0,r[1],[]])]
   expected=base.normalize_calls([r for r in visible if r[0] in selected]);actual=base.normalize_calls([r for r in ns['calls'] if r[0] in selected])
   if expected!=actual:fail.append(dict(label=e['label'],stage=es['label'],field='call order',expected_count=len(expected),actual_count=len(actual),first_difference=next(((x,y) for x,y in zip(expected,actual) if x!=y),None)))
 required={'provider required','wrong callback rejected','allocation exhaustion preserved','owner routed release','fresh allocation after release','double retirement rejected','live helper cannot be freed directly','stale actor and state storage rejected','registered handler replacement rejected','physical service reentry rejected'}
 names=[c['name'] for c in native['controls']]
 if len(names)!=72 or len(set(names))!=72 or not required.issubset(names):fail.append('missing or duplicated ownership controls')
 for control in native['controls']:
  if not control['passed']:fail.append(control)
 result=dict(status='fail' if fail else 'pass',profiles=3,stages=21,controls=len(native['controls']),failures=fail,host_wired=False)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve();assert (base.ROOT/'work').resolve() in out.parents
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
