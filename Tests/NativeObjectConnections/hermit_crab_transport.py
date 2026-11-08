"""Finite HermitCrab shared-heap transport against the pinned original."""
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
_spec=importlib.util.spec_from_file_location('cut_transport',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(cut)
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EBP
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE=tuple(a for a in cut.OBSERVE if a not in (0x437a90,0x4384f0,0x44c000))+(0x43dfa0,0x44a380,0x44aaf0,0x449d60,0x404fc0,0x4063b0,0x43e9b0,0x4c96b0,0x4dc870,0x44ac40,0x44ac60,0x44ae30,0x44ade0,0x4f6584,0x4f6428,0x4dba00,0x4c7f20,0x4c7fe0,0x4c81b0,0x4c8160,0x4c80c0,0x4c80e0)
class Reference(cut.Reference):
 def __init__(self,live=False,fractional=False):
  super().__init__(live=live)
  self.commands=[0,1000,29,30,6];self.freed=[];self.frames=[];self.x87_calls=[];self.source_observations=[];self.pending_sources={}
  self.put(self.tokens['state']+0x10,0x449c40)
  self.m.intercept(0x4a49b0)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  for key in (0x527d20,0x527d0c):self.bind('sprites',key,sprite)
  for key in (0x527cec,0x527cd0,0x527cb8,0x527c9c,0x527c80,0x527c68,0x527c50,0x527c38):self.bind('animations',key,animation)
  for key in (0x5266ec,0x524870,0x524864,0x524858,0x52484c,0x5266dc,0x527c28,0x527c0c,0x527bf0,0x527bd4,0x527bc4):self.bind('sounds',key,self.object(0x20,fill=0))
  for key,kind,callback in ((0x522d54,21,0x4dc830),(0x522d48,22,0x4dc850)):
   self.bind('logic',key,self.object(0x14,words=[key,kind,2,0,callback]))
  # Native owners consume the actual tree and table representations.
  node=self.object(0x14,fill=0);name=self.object(16,data=b'ES_HOME\0',fill=0)
  self.put(node,node,node,0,name,5);self.put(0x537680,node)
  state_header=self.object(32,fill=0);self.put(state_header,1,7,7);state_name=state_header+12;self.write(state_name,b'ES_HIDE\0');names=self.object(4,words=[state_name]);self.state_string_spans=[(state_header,32),(names,4)];self.put(0x5376a0,6,6,names);self.put(0x5376b0,4)
  callbacks=self.object(4,words=[0x44ade0]);self.put(0x537850,6,6,callbacks,0,4)
  player=self.object(0x200,fill=0);player_state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,player_state);self.put(player_state+0x14,inputs);self.put(player+0x4c,100)
  self.put(self.tokens['owner']+0xcc,7)
  self.put(0x537210,100);self.put(0x532c0c,0)
  if fractional:
   for address,value in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):self.write(address,struct.pack('<f',value))
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  self.m.observe(0x4a30e0,lambda m,a:self.x87_calls.append(dict(function=a,continuation=self.get(m.register(UC_X86_REG_ESP)),x87=m.x87_state())))
  for pc,function in ((0x44a3d0,0x4f6439),(0x44a3e0,0x4f6439),(0x4dc1a7,0x4db620),(0x4dbe3c,0x4db620)):
   self.m.observe(pc,lambda m,a,function=function:self.source_return(m,function))
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def source_return(self,m,function):
  incoming=self.pending_sources.pop(function)
  self.source_observations.append(dict(function=function,input_receiver=incoming['receiver'],return_pc=incoming['return_pc'],output_eax=m.register(UC_X86_REG_EAX),stack_delta=m.register(UC_X86_REG_ESP)-incoming['sp'],fs_preserved=m.fs_head==incoming['fs']))
 def entry(self,m,a):
  if a in (0x4f6439,0x4db620):
   sp=m.register(UC_X86_REG_ESP);self.pending_sources[a]=dict(receiver=m.register(UC_X86_REG_ECX),sp=sp,return_pc=self.get(sp),fs=m.fs_head)
  if a in cut.OBSERVE:super().entry(m,a)
  else:
   arity={0x44a380:1,0x44aaf0:1,0x449d60:1,0x404fc0:1,0x4063b0:1,0x4dc870:1,0x44ac40:1,0x4f6428:1,0x4dba00:1,0x4c7f20:1,0x4c7fe0:1,0x4c8160:2,0x4c80c0:1}.get(a,0)
   receiver=0 if a in (0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
   self.entries.append([a,receiver,list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a==0x44a380:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a in (0x4dbe10,0x4dbd60):self.frames.append(dict(function=a,receiver=m.register(UC_X86_REG_ECX),caller_frame=m.register(UC_X86_REG_EBP),continuation=self.get(m.register(UC_X86_REG_ESP))))
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a);sp=m.register(UC_X86_REG_ESP)
  if a==0x4a49b0:
   token=self.get(sp+4);assert token in [v[0] for v in self.allocations] and token not in self.freed
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  elif slot==0x546cd4:
   rectangle,x,y=m.words(sp+4,3);x,y=struct.unpack('<ii',struct.pack('<II',x,y));l,t,r,b=struct.unpack('<iiii',self.read(rectangle,16));value=int(l<=x<r and t<=y<b);self.events.append(['point-in-rectangle',rectangle,x,y,value]);m.return_from_external(value,12)
  elif slot==0x546d24:
   rectangle,x,y=m.words(sp+4,3);x,y=struct.unpack('<ii',struct.pack('<II',x,y));l,t,r,b=struct.unpack('<iiii',self.read(rectangle,16));self.put(rectangle,l-x,t-y,r+x,b+y);self.events.append(['inflate-rectangle',rectangle,x,y]);m.return_from_external(1,12)
  else:super().external(m,a)
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];x87=[];results=[]
  for command in self.commands:
   self.put(self.tokens['state']+0x1c,command)
   if command==6:self.put(ALLOC+0x410,99,1000)
   result=self.m.call(0x449c40,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not result.completed:raise RuntimeError((label,command,result))
   results.append(self.m.register(UC_X86_REG_EAX));x87.append(self.m.x87_state())
   spans=[(self.tokens['owner'],0x200),(self.tokens['state'],0x180),(0x537848,0x24)]+self.state_string_spans+self.allocations
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
  result=self.m.call(0x44ac40,ecx=ALLOC,arguments=(1,),timeout_seconds=5)
  if not result.completed:raise RuntimeError(('retirement',label,result))
  retired=self.read(ALLOC,0x438).hex()
  for offset in (0x70,0x78):
   helper=self.get(self.tokens['owner']+offset);result=self.m.call(0x4c80c0,ecx=helper,arguments=(1,),timeout_seconds=5);assert result.completed;self.put(self.tokens['owner']+offset,0)
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,frames=self.frames,x87_calls=self.x87_calls,results=results,snapshots=snapshots,x87_snapshots=x87,retired_bytes=retired,freed=self.freed,source_observations=self.source_observations)
def string_retirement_references():
 rows=[]
 for name,references,members in (('owned-string-free',1,[0x1a4]),('owned-string-retained',2,[0x1a4]),('owned-string-shared',2,[0x1a8,0x1a4])):
  r=Reference();r.m.reset_x87();r.m.set_x87_state(*r.incoming)
  result=r.m.call(0x449c40,arguments=(r.tokens['owner'],),timeout_seconds=5);assert result.completed
  result=r.m.call(0x4a48e0,arguments=(16,),timeout_seconds=5);assert result.completed
  token=r.m.register(UC_X86_REG_EAX);r.put(token,references,3,3);r.write(token+12,b'abc\0')
  for offset in members:r.put(ALLOC+offset,token+12)
  result=r.m.call(0x44ac40,ecx=ALLOC,arguments=(1,),timeout_seconds=5);assert result.completed
  rows.append(dict(name=name,references=references,members=members,token=token,bytes=r.read(token,16).hex(),freed=token in r.freed,helper_freed=ALLOC in r.freed,helper_bytes=r.read(ALLOC,0x438).hex()))
 return rows
def allocation_failure_reference():
 r=Reference();seen=[];original_external=r.external
 def external(m,address):
  if address==0x4a48e0:seen.append(dict(function=address,result=0));m.return_from_external(0,0)
  else:original_external(m,address)
 def stop(m,address):seen.append(dict(function=address));m.uc.emu_stop()
 r.m.on_external=external;r.m.observe(0x5022b5,stop)
 result=r.m.call(0x449c40,arguments=(r.tokens['owner'],),timeout_seconds=1)
 assert not result.completed and seen==[dict(function=0x4a48e0,result=0),dict(function=0x5022b5)] and r.allocations==[]
 return seen
def prepare(out):
 out.mkdir(parents=True,exist_ok=True);profiles=[]
 for live in (False,True):
  for fractional in (False,True):profiles.append(Reference(live,fractional).run(f'live-{int(live)}-fractional-{int(fractional)}'))
 r=Reference();metadata=[]
 for pc,target,continuation in ((0x449c78,0x4f63ec,0x449c7d),(0x449c93,0x44a380,0x449c98)):
  code=r.read(pc,5);assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation;metadata.append(dict(call=pc,target=target,continuation=continuation))
 slots={offset:r.get(0x50e014+offset) for offset in (0,4,8,12,16,28,32,36)}
 assert slots=={0:0x44ac40,4:0x404fc0,8:0x449d60,12:0x4063b0,16:0x405000,28:0x4c96b0,32:0x43e9b0,36:0x43dfa0}
 for row in profiles:
  assert row['allocations']==[[ALLOC,0x438],[ALLOC+0x440,0x174],[ALLOC+0x5c0,0x174]],row['allocations']
  assert row['continuations'][0]==[0x4f63ec,0x449c7d] and row['continuations'][1]==[0x44a380,0x449c98]
  assert {0x44bc60,0x44aaf0,0x4dbe10,0x4dbd60,0x4f6439,0x449d60,0x44ade0,0x43e9b0,0x4c96b0,0x44ac40,0x4f6584}.issubset({r[0] for r in row['entries']})
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,call_metadata=metadata,vtable=slots,profiles=profiles,string_retirements=string_retirement_references(),allocation_failure=allocation_failure_reference()),indent=2)+'\n');print(json.dumps(dict(status='pass',original_profiles=len(profiles))))
def preflight(out):
 registry=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text();required=(0x449c40,0x44a380,0x44bc60,0x44aaf0,0x449d60,0x44ade0,0x44ac40)
 missing=[hex(a) for a in required if not re.search(r'\{0x%08xu,' % a,registry)]
 print(json.dumps(dict(status='pending-admission' if missing else 'pass',missing=missing)));return bool(missing)
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 required={'provider required','foreign provider rejected','wrong callback rejected','missing registry fails','allocation exhaustion preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected','foreign retirement provider rejected','double physical free rejected','vtable slot 36 replacement rejected'}
 names=[c['name'] for c in native['controls']]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append('required controls missing or duplicated')
 for e,a in zip(ref['profiles'],native['profiles']):
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  if not a['allocation_witness']:fail.append('allocation continuation witness')
  if not a['retired']:fail.append('owner-routed retirement')
  for field in ('label','outgoing','snapshots','x87_snapshots','retired_bytes'):
   if e[field]!=a[field]:fail.append(dict(label=e['label'],field=field))
  # Native scratch frame addresses differ, while each local identity and its
  # use must agree within an ordered observation sequence.
  def events(rows):
   local={}
   def value(v):
    if isinstance(v,int) and cut.STACK_BASE<=v<cut.STACK_BASE+cut.STACK_SIZE:
     if v not in local:local[v]='stack-local-'+str(len(local))
     return local[v]
    return v
   return [[value(v) for v in row] for row in rows]
  if events(e['events'])!=events(a['events']):fail.append(dict(label=e['label'],field='ordered physical events',expected_count=len(e['events']),actual_count=len(a['events']),first_difference=next(((x,y) for x,y in zip(events(e['events']),events(a['events'])) if x!=y),None)))
  # Internal 44ac60/44ae30 are inlined by the admitted Hermit owner.
  # Dictionary lookups are compared independently as ordered physical events.
  # Actor-storage 4c7fa0/4c8060 directly own 4c7f20/4c7fe0; scalar
  # ActorDestructionCanonical 4c80c0 directly owns 4c80e0. Retain their
  # registered roots, descendants, effects and complete allocation bytes.
  selected=set(OBSERVE)-{0x4f6286,0x44ac60,0x44ae30,0x4c7f20,0x4c7fe0,0x4c80e0}
  original_calls=[r for r in e['entries'] if r[0] in selected];native_calls=[r for r in a['calls'] if r[0] in selected]
  assert sum(r[0]==0x4dca10 for r in original_calls)==2
  assert sum(r[0]==0x4dca10 for r in native_calls)==1
  descendant=next(i for i,r in enumerate(original_calls) if r[0]==0x4063b0)+1
  # 4063b0 resolves actual +0x24=43dfa0 through dynamicCall, whose owned
  # branch calls ownedBody directly. Its motion body embeds integrate(4dca10);
  # the base constructor separately calls the registered 4dca10 root.
  assert [r[0] for r in original_calls[descendant:descendant+3]]==[0x43dfa0,0x4dca10,0x403b40]
  native_descendant=next(i for i,r in enumerate(native_calls) if r[0]==0x4063b0)+1
  assert native_calls[native_descendant][0]==0x403b40
  original_calls.pop(descendant+1);original_calls.pop(descendant)
  ec=cut.normalize_calls(original_calls);ac=cut.normalize_calls(native_calls)
  if ec!=ac:fail.append(dict(label=e['label'],field='ordered source calls',expected_count=len(ec),actual_count=len(ac),first_difference=next(((x,y) for x,y in zip(ec,ac) if x!=y),None)))
  expected_frames=[[r['function'],r['caller_frame'],r['continuation']] for r in e['frames']]
  actual_frames=[[r['function'],r['caller_frame'],r['continuation']] for r in a['frames']]
  if expected_frames!=[[0x4dbe10,ALLOC+0x128,0x44a556],[0x4dbd60,ALLOC+0x128,0x44a56d]] or actual_frames!=[[0x4dbe10,0,0],[0x4dbd60,0,0]]:fail.append(dict(label=e['label'],field='ordinary bitset and original caller-frame observations',expected=expected_frames,actual=actual_frames))
  def source_rows(rows):return cut.normalize_calls([[r['function'],r['input_receiver'],[r['return_pc'],r['output_eax'],r['stack_delta'],r['fs_preserved']]] for r in rows])
  if source_rows(e['source_observations'])!=source_rows(a['source_observations']):fail.append(dict(label=e['label'],field='source member observations'))
  requests=a['allocation_requests']
  if [r[1:] for r in requests]!=[[0x438,0x4f63ff,0x449c7d],[0x174,0x4f63ff,0x4c7f4f],[0x174,0x4f63ff,0x4c800f]]:fail.append(dict(label=e['label'],field='allocation source contexts',actual=requests))
 if ref['string_retirements']!=native['string_retirements']:fail.append('member string destructor ownership')
 for control in native['controls']:
  if not control['passed']:fail.append(dict(control=control['name']))
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),controls=len(native['controls']),failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='preflight':raise SystemExit(preflight(out))
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
