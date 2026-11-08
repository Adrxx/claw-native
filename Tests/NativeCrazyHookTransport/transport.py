"""Finite original/native CrazyHook shared-owner transport comparison."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
spec=importlib.util.spec_from_file_location('cut_transport',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(spec);spec.loader.exec_module(cut)
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE=tuple(a for a in cut.OBSERVE if a not in (0x437a90,0x4384f0))+(0x434250,0x44f1b0,0x44cfd0,0x4c96b0,0x4dc870,0x434d30,0x434950,0x44d000,0x44d3c0,0x43dfa0,0x435600,0x434860,0x4f6584,0x4f6428,0x43e420,0x4cbb60,0x4c82a0,0x4c7f20,0x4c7fe0,0x4c81b0,0x4c8160,0x4c80c0,0x4c80e0)
class Reference(cut.Reference):
 def __init__(self,live=False,fractional=False):
  super().__init__(0,live,0x23f)
  self.commands=[0,0,1000,29,30,6];self.freed=[];self.contexts=[];self.secondary_retired=[];self.member_source=[];self.member_entries=[];self.frame_error_reads=0
  self.put(self.tokens['state']+0x10,0x434190)
  for key,kind,callback in ((0x522d54,21,0x4dc830),(0x522d48,22,0x4dc850)):
   self.bind('logic',key,self.object(0x14,words=[key,kind,2,0,callback]))
  self.m.intercept(0x4a49b0)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x526a1c,sprite)
  for key in (0x526a04,0x5269e8,0x5269d0,0x5269b8,0x5269a0,0x526988,0x52696c,0x526954,0x52693c,0x526924,0x52690c,0x5268f4,0x5268dc):self.bind('animations',key,animation)
  for key in (0x5268c0,0x5268a4,0x526888,0x52686c,0x526850,0x526834,0x526818,0x5267fc,0x5267e0,0x5267c4,0x5267ac,0x526794,0x526778,0x52675c):self.bind('sounds',key,self.object(0x20,fill=0))
  player=self.object(0x200,fill=0);state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,state);self.put(state+0x14,inputs);self.put(player+0x4c,100)
  name=self.object(16,data=b'LS_BLOCK\0',fill=0);table=self.object(4,words=[name]);self.put(0x5376a0,6,6,table);self.put(0x5376b0,4)
  callbacks=self.object(4,words=[0x435600]);self.put(0x537340,6,6,callbacks);self.put(0x537350,4)
  tilemap=self.object(0xa0,fill=0);cells=self.object(4,words=[0xffffffff]);rows=self.object(4,words=[0])
  self.put(tilemap+0x20,cells,rows);self.put(tilemap+0x30,1024,1024);self.put(tilemap+0x8c,10,10);self.put(self.tokens['collision']+0x5c,tilemap)
  self.put(0x53774c,0);self.put(0x541334,1)
  if fractional:
   for a,v in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):self.write(a,struct.pack('<f',v))
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  for pc in (0x44c04e,0x44c05e,0x4dc1a7,0x4dbe3c):self.m.observe(pc,self.member_return)
  self.m.observe(0x4dc680,self.frame_error)
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def frame_error(self,m,a):self.frame_error_reads+=1
 def member_return(self,m,a):
  from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP
  function,receiver,sp,regs=self.member_entries.pop()
  returned=[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]
  self.member_source.append(dict(function=function,receiver=receiver,return_pc=a,eax=m.register(UC_X86_REG_EAX),stack_delta=m.register(UC_X86_REG_ESP)-sp,preserved=returned==regs))
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a in (0x4f6439,0x4db620):
   from unicorn.x86_const import UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP
   self.member_entries.append((a,m.register(UC_X86_REG_ECX),m.register(UC_X86_REG_ESP),[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]))
  if a in cut.OBSERVE:super().entry(m,a)
  else:
   arity={0x434250:1,0x4dc870:1,0x434d30:1,0x434950:1,0x44d000:1,0x44d3c0:1,0x434860:1,0x4f6428:1,0x4cbb60:4,0x4c82a0:1,0x4c7f20:1,0x4c7fe0:1,0x4c8160:2,0x4c80c0:1}.get(a,0)
   receiver=0 if a in (0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
   self.entries.append([a,receiver,list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a==0x434250:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a in (0x4dbd60,0x4dbe10):
   from unicorn.x86_const import UC_X86_REG_EBP
   self.contexts.append([a,m.register(UC_X86_REG_EBP)])
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a)
  if slot==0x546cd4:
   rectangle,x,y=m.words(m.register(UC_X86_REG_ESP)+4,3);x,y=struct.unpack('<ii',struct.pack('<II',x,y));left,top,right,bottom=struct.unpack('<iiii',self.read(rectangle,16))
   result=int(left<=x<right and top<=y<bottom);self.events.append(['point-in-rectangle',rectangle,x,y,result]);m.return_from_external(result,12)
  elif a==0x4a49b0:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [x[0] for x in self.allocations] and token not in self.freed
   if [token,0x174] in self.allocations:self.secondary_retired.append(dict(address=token,data=self.read(token,0x174).hex()))
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  else:super().external(m,a)
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];x87=[]
  for index,command in enumerate(self.commands):
   if index==1:
    helper=self.get(self.tokens['state']+0x18);retired=self.m.call(0x434860,ecx=helper,arguments=(1,),timeout_seconds=5);assert retired.completed
    self.put(self.tokens['state']+0x18,0)
   self.put(self.tokens['state']+0x1c,command)
   if command==6:self.put(0x537210,100);self.put(0x5430c4,0);self.put(self.tokens['owner']+0xcc,7);self.put(self.get(self.tokens['state']+0x18)+0x490,1000)
   result=self.m.call(0x434190,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not result.completed:raise RuntimeError((label,command,result))
   spans=[(BASE,SIZE),(0x537668,0x54),(0x537338,0x28),(0x537210,4),(0x5430c4,4)]+[v for v in self.allocations if v[0] not in self.freed]
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans]);x87.append(self.m.x87_state())
  helper=self.get(self.tokens['state']+0x18)
  result=self.m.call(0x434860,ecx=helper,arguments=(1,),timeout_seconds=5)
  if not result.completed:raise RuntimeError(('retirement',label,result))
  retired_bytes=self.read(helper,0x498).hex()
  for offset in (0x70,0x78):
   result=self.m.call(0x4c80c0,ecx=self.get(self.tokens['owner']+offset),arguments=(1,),timeout_seconds=5);assert result.completed
   self.put(self.tokens['owner']+offset,0)
  return dict(member_source=self.member_source,frame_error_reads=self.frame_error_reads,secondary_retired=self.secondary_retired,label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,contexts=self.contexts,snapshots=snapshots,x87_snapshots=x87,retired_bytes=retired_bytes)
def metadata():
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32
 from capstone.x86_const import X86_INS_CALL,X86_OP_MEM
 m=Machine(claw(),BASE,SIZE);decoder=Cs(CS_ARCH_X86,CS_MODE_32);decoder.detail=True;rows=[]
 for pc,target,continuation in ((0x4341c8,0x4f63ec,0x4341cd),(0x4341e3,0x434250,0x4341e8)):
  code=m.read(pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target and pc+5==continuation
  rows.append(dict(call=pc,target=target,continuation=continuation))
 slots={offset:m.words(0x50c85c+offset,1)[0] for offset in (0,4,8,12,16,28,32,36)}
 assert slots=={0:0x434860,4:0x434d30,8:0x434950,12:0x44d3c0,16:0x405000,28:0x4c96b0,32:0x44cfd0,36:0x43dfa0}
 return dict(call_metadata=rows,vtable=dict(address=0x50c85c,slots=slots))
def allocation_failure_reference():
 # Allocation failure follows source operator new to its actual handler lookup.
 # Stop at the dependency without manufacturing an exception result.
 r=Reference();seen={}
 def failure(m,address):
  if address==0x4a48e0:
   sp=m.register(UC_X86_REG_ESP);seen['requested']=m.words(sp+4,1)[0];m.return_from_external(0,0)
  else:r.external(m,address)
 def lookup(m,address):
  seen.update(target=address,return_pc=m.words(m.register(UC_X86_REG_ESP),1)[0],event=r.get(r.tokens['state']+0x1c),helper=r.get(r.tokens['state']+0x18))
  m.uc.emu_stop()
 r.m.on_external=failure;r.m.observe(0x5022b5,lookup)
 result=r.m.call(0x434190,arguments=(r.tokens['owner'],),timeout_seconds=5)
 assert not result.completed and seen==dict(requested=0x498,target=0x5022b5,return_pc=0x4f6413,event=1000,helper=0)
 return seen
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 rows=[Reference(live,fractional).run(f'live-{int(live)}-fractional-{int(fractional)}') for live in (False,True) for fractional in (False,True)]
 for r in rows:
  assert [v for v in r['continuations'] if v[0]==0x434250]==[[0x434250,0x4341e8]]*2
  assert [v for v in r['continuations'] if v[0]==0x4f63ec].count([0x4f63ec,0x4341cd])==2
  assert [v[1] for v in r['allocations']]==[0x498,0x174,0x174,0x498]
  assert {0x434950,0x435600,0x4dc870,0x434d30,0x44d3c0}.issubset({x[0] for x in r['entries']})
  assert len(r['contexts'])==4
  assert not r['frame_error_reads'] and len(r['member_source'])==8 and not r.get('member_entries',[])
  assert all(v['eax']==v['receiver'] and v['preserved'] for v in r['member_source'])
  assert all(v[1]==r['allocations'][i//2*3][0]+0x230 for i,v in enumerate(r['contexts']))
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,**metadata(),profiles=rows,allocation_failure=allocation_failure_reference()),indent=2)+'\n')
 print(json.dumps(dict(status='pass',profiles=len(rows))))
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 required={'provider required','foreign provider rejected','wrong callback rejected','missing registry fails','allocation exhaustion preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected','foreign retirement provider rejected','double physical free rejected','wrong actor state rejected','vtable slot 8 replacement rejected','reentrant wrong size request rejected','reentrant wrong receiver request rejected','reentrant wrong actor request rejected','reentrant wrong continuation request rejected','source allocation stack word 20 tampering rejected before allocation','foreign state callback rejected','missing CString service rejected','live vtable replacement rejected'}
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append('required controls missing or duplicated')
 for e,a in zip(ref['profiles'],native['profiles']):
  for key in ('label','outgoing','events','snapshots','x87_snapshots','retired_bytes','secondary_retired'):
   if e[key]!=a[key]:
    difference=dict(label=e['label'],field=key)
    if key=='x87_snapshots':difference['commands']=[dict(index=i,command=e['commands'][i],expected=x,actual=y) for i,(x,y) in enumerate(zip(e[key],a[key])) if x!=y]
    fail.append(difference)
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  if not a['allocation_witness']:fail.append('allocation continuation witness')
  if not a['retired']:fail.append('retirement incomplete')
  # The constructor and secondary binders embed their admitted bases.
  # Their native service calls and all resulting bytes remain compared.
  selected=set(OBSERVE)-{0x44bc60,0x4f6286,0x4dca10,0x4c7f20,0x4c7fe0,0x4c80e0}
  expected=cut.normalize_calls([r for r in e['entries'] if r[0] in selected]);actual=cut.normalize_calls([r for r in a['calls'] if r[0] in selected])
  if expected!=actual:fail.append(dict(label=e['label'],field='ordered calls',expected_count=len(expected),actual_count=len(actual),first_difference=next(((x,y) for x,y in zip(expected,actual) if x!=y),None)))
 if native.get('allocation_failure')!={k:v for k,v in ref.get('allocation_failure',{}).items() if k!='return_pc'}:fail.append(dict(field='allocation failure handler boundary',expected=ref.get('allocation_failure'),actual=native.get('allocation_failure')))
 for c in controls:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=4,controls=len(controls),failures=fail,host_wired=False)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
