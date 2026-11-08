"""Finite original/native PegLeg shared-owner transport; no scene promotion."""
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
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE=tuple(a for a in cut.OBSERVE if a not in (0x437a90,0x4384f0))+(0x468eb0,0x44d9f0,0x46a000,0x44cfd0,0x4c96b0,0x4dc870,0x468ad0,0x44d000,0x44d3c0,0x43dfa0,0x469a40,0x469480,0x4f6584,0x4f6428,0x43e420,0x4cbb60,0x4c82a0,0x4c80c0,0x4c8160,0x4c81b0)
# Exact fields assigned by the real constructor; sparse zero fields are valid.
RESOURCE_FIELDS=(0x12c,0x308,0x30c,0x310,0x32c,0x334,0x338,0x33c,0x344,0x34c,0x350,0x36c,0x374,0x378,0x37c,0x380,0x3a4,0x414,0x450,0x454,0x458,0x45c,0x460,0x464,0x468,0x46c,0x470,0x474,0x478,0x47c,0x480,0x484,0x488,0x48c,0x490)
class Reference(cut.Reference):
 def __init__(self,status=0,live=False,fractional=False):
  super().__init__(status,live,0x23f)
  self.commands=[0,0,1000,29,30,6];self.freed=[];self.member_source=[];self.member_entries=[]
  self.put(self.tokens['state']+0x10,0x4689b0)
  self.m.intercept(0x4a49b0)
  # Physical registry records select the original LogicHit/LogicAttack callbacks.
  # No secondary actor record exists until the original binder allocates it.
  assert self.get(self.tokens['owner']+0x70)==self.get(self.tokens['owner']+0x78)==0
  self.secondary_metadata=[]
  for offset,name,callback in ((0x70,0x522d54,0x4dc830),(0x78,0x522d48,0x4dc850)):
   metadata=self.object(0x14,words=[0,0,0,0,callback])
   self.bind('logic',name,metadata)
   self.secondary_metadata.append(dict(offset=offset,name=name,token=metadata,callback=callback))
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x529f90,sprite)
  for key in (0x529f7c,0x529f64,0x529f48,0x529f30,0x529f1c,0x529f08,0x529ef4,0x529edc,0x529ec4,0x529eac,0x529e94,0x529e7c,0x529e68,0x529e4c,0x529e30):self.bind('animations',key,animation)
  for key in (0x529e14,0x529dfc,0x529de4,0x529dcc,0x529db4,0x529d9c,0x529d84,0x529d6c,0x529d54,0x529d3c,0x529d24,0x529d0c,0x529cf4,0x529cdc,0x529cc4,0x529cb0):self.bind('sounds',key,self.object(0x20,fill=0))
  # The original name registry is a Patricia tree. Supply its physical HOME
  # leaf and actual state-registration target, without replacing either owner.
  node=self.object(20,fill=0);self.put(node,node,node,0,0x5234ec,5);self.put(0x537680,node)
  home=self.object(32,data=self.text(0x5234ec).encode()+b'\0');fire=self.object(32,data=self.text(0x524548).encode()+b'\0')
  names=self.object(8,words=[home,fire]);self.put(0x5376a0,5,6,names);self.put(0x5376b0,4)
  callbacks=self.object(8,words=[0x469570,0x469a40]);self.put(0x537c68,5,6,callbacks);self.put(0x537c78,4)
  player=self.object(0x200,fill=0);state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,state);self.put(state+0x14,inputs);self.put(player+0x4c,100)
  tilemap=self.object(0xa0,fill=0);cells=self.object(4,words=[0xffffffff]);rows=self.object(4,words=[0])
  self.put(tilemap+0x20,cells,rows);self.put(tilemap+0x30,1024,1024);self.put(tilemap+0x8c,10,10);self.put(self.tokens['collision']+0x5c,tilemap)
  self.put(0x53774c,0);self.put(0x541334,1)
  if fractional:
   for a,v in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):self.write(a,struct.pack('<f',v))
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  for pc in (0x44c04e,0x44c05e,0x4dc1a7,0x4dbe3c):self.m.observe(pc,self.member_return)
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def member_return(self,m,a):
  function,receiver,sp,regs=self.member_entries.pop()
  returned=[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]
  self.member_source.append(dict(function=function,receiver=receiver,return_pc=a,eax=m.register(UC_X86_REG_EAX),stack_delta=m.register(UC_X86_REG_ESP)-sp,preserved=returned==regs))
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a in (0x4f6439,0x4db620):self.member_entries.append((a,m.register(UC_X86_REG_ECX),m.register(UC_X86_REG_ESP),[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]))
  if a in cut.OBSERVE:super().entry(m,a)
  else:
   arity={0x468eb0:1,0x4dc870:1,0x468ad0:1,0x44d000:1,0x44d3c0:1,0x469480:1,0x4f6428:1,0x4cbb60:4,0x4c82a0:1,0x4c80c0:1,0x4c8160:2}.get(a,0)
   receiver=0 if a in (0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
   self.entries.append([a,receiver,list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a==0x468eb0:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a)
  if slot==0x546cd4:
   rectangle,x,y=m.words(m.register(UC_X86_REG_ESP)+4,3);x,y=struct.unpack('<ii',struct.pack('<II',x,y));left,top,right,bottom=struct.unpack('<iiii',self.read(rectangle,16))
   result=int(left<=x<right and top<=y<bottom);self.events.append(['point-in-rectangle',rectangle,x,y,result]);m.return_from_external(result,12)
  elif a==0x4a49b0:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [x[0] for x in self.allocations] and token not in self.freed
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  else:super().external(m,a)
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];x87=[]
  for index,command in enumerate(self.commands):
   if index==1:
    helper=self.get(self.tokens['state']+0x18);retired=self.m.call(0x469480,ecx=helper,arguments=(1,),timeout_seconds=5);assert retired.completed
    self.put(self.tokens['state']+0x18,0)
   self.put(self.tokens['state']+0x1c,command)
   if command==6:
    self.put(0x537210,100);self.put(0x5430c4,0);self.put(self.tokens['owner']+0xcc,7)
    self.put(self.get(self.tokens['state']+0x18)+0x4cc,1)
   result=self.m.call(0x4689b0,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not result.completed:raise RuntimeError((label,command,result))
   if command==0:
    helper=self.get(self.tokens['state']+0x18)
    assert helper==self.allocations[0 if index==0 else 3][0] and self.get(self.tokens['state']+0x1c)==5
    for binding in self.secondary_metadata:
     secondary=self.get(self.tokens['owner']+binding['offset'])
     assert secondary!=0 and self.get(secondary+0x10)==binding['callback']
     if index==1:assert secondary==self.allocations[1 if binding['offset']==0x70 else 2][0]
    assert all(self.get(helper+offset)!=0 for offset in RESOURCE_FIELDS)
   spans=[(BASE,SIZE),(0x537668,0x54),(0x537c60,0x28),(0x537210,4),(0x5430c4,4)]+[v for v in self.allocations if v[0] not in self.freed]
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans]);x87.append(self.m.x87_state())
  helper=self.get(self.tokens['state']+0x18)
  result=self.m.call(0x469480,ecx=helper,arguments=(1,),timeout_seconds=5)
  if not result.completed:raise RuntimeError(('retirement',label,result))
  retired_secondary=[]
  for binding in self.secondary_metadata:
   secondary=self.get(self.tokens['owner']+binding['offset'])
   result=self.m.call(0x4c80c0,ecx=secondary,arguments=(1,),timeout_seconds=5)
   if not result.completed:raise RuntimeError(('secondary retirement',label,binding,result))
   retired_secondary.append(dict(address=secondary,data=self.read(secondary,0x174).hex()))
   self.put(self.tokens['owner']+binding['offset'],0)
  self.put(self.tokens['state']+0x18,0)
  final_spans=[(BASE,SIZE),(0x537668,0x54),(0x537c60,0x28),(0x537210,4),(0x5430c4,4)]
  final_snapshots=[dict(address=a,data=self.read(a,n).hex()) for a,n in final_spans]
  assert set(self.freed)=={a for a,n in self.allocations}
  return dict(secondary_metadata=self.secondary_metadata,final_snapshots=final_snapshots,retired_secondary_bytes=retired_secondary,member_source=self.member_source,label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,snapshots=snapshots,x87_snapshots=x87,retired_bytes=self.read(helper,0x4e8).hex())
def metadata():
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32
 from capstone.x86_const import X86_INS_CALL,X86_OP_MEM
 m=Machine(claw(),BASE,SIZE);decoder=Cs(CS_ARCH_X86,CS_MODE_32);decoder.detail=True;rows=[]
 for pc,target,continuation in ((0x4689e8,0x4f63ec,0x4689ed),(0x468a03,0x468eb0,0x468a08),(0x468a3c,0x4dc870,0x468a41),(0x468ed4,0x44c000,0x468ed9),(0x4c7f4a,0x4f63ec,0x4c7f4f),(0x4c800a,0x4f63ec,0x4c800f)):
  code=m.read(pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target and pc+5==continuation
  rows.append(dict(call=pc,target=target,continuation=continuation))
 for pc,continuation,slot in ((0x468a1a,0x468a1d,16),(0x468a27,0x468a2a,32),(0x468a4b,0x468a4e,28),(0x4c7f40,0x4c7f43,0x1c),(0x4c7f94,0x4c7f97,0x24),(0x4c8000,0x4c8003,0x1c),(0x4c8054,0x4c8057,0x24)):
  i=next(decoder.disasm(m.read(pc,8),pc));assert i.id==X86_INS_CALL and i.address+i.size==continuation and i.operands[0].type==X86_OP_MEM and i.operands[0].mem.disp==slot
  rows.append(dict(call=pc,continuation=continuation,slot=slot))
 slots={offset:m.words(0x50ed1c+offset,1)[0] for offset in (0,4,8,12,16,28,32,36)}
 assert slots=={0:0x469480,4:0x44d000,8:0x468ad0,12:0x44d3c0,16:0x405000,28:0x4c96b0,32:0x44cfd0,36:0x43dfa0}
 # Registration instructions retain the selected FIRE name and actual callback.
 code=m.read(0x468be0,0x2d0)
 assert struct.pack('<I',0x469a40) in code and struct.pack('<I',0x524548) in code
 # Original startup registration selects these exact named logic callbacks.
 for pc,name,callback in ((0x4011e3,0x522d54,0x4dc830),(0x4011f7,0x522d48,0x4dc850)):
  assert m.read(pc,12)==b'\x6a\x02\x68'+struct.pack('<I',name)+b'\x68'+struct.pack('<I',callback)
 return dict(call_metadata=rows,vtable=dict(address=0x50ed1c,slots=slots))
def allocation_failure_reference():
 r=Reference();seen={}
 def failure(m,address):
  if address==0x4a48e0:
   sp=m.register(UC_X86_REG_ESP);seen['requested']=m.words(sp+4,1)[0];m.return_from_external(0,0)
  else:r.external(m,address)
 def lookup(m,address):
  seen.update(target=address,return_pc=m.words(m.register(UC_X86_REG_ESP),1)[0],event=r.get(r.tokens['state']+0x1c),helper=r.get(r.tokens['state']+0x18));m.uc.emu_stop()
 r.m.on_external=failure;r.m.observe(0x5022b5,lookup)
 result=r.m.call(0x4689b0,arguments=(r.tokens['owner'],),timeout_seconds=5)
 assert not result.completed and seen==dict(requested=0x4e8,target=0x5022b5,return_pc=0x4f6413,event=1000,helper=0)
 return seen
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 rows=[Reference(status,live,fractional).run(f'sw-{status:x}-live-{int(live)}-fractional-{int(fractional)}') for status,live,fractional in ((0,False,False),(0x20,False,True),(0x21,False,False),(0x21,True,True))]
 for r in rows:
  assert [v for v in r['continuations'] if v[0]==0x468eb0]==[[0x468eb0,0x468a08]]*2
  assert [v for v in r['continuations'] if v[0]==0x4f63ec]==[[0x4f63ec,0x4689ed],[0x4f63ec,0x4c7f4f],[0x4f63ec,0x4c800f],[0x4f63ec,0x4689ed]]
  assert [v[1] for v in r['allocations']]==[0x4e8,0x174,0x174,0x4e8]
  assert {0x468ad0,0x469a40,0x43dfa0}.issubset({x[0] for x in r['entries']})
  assert len(r['member_source'])==8
  assert all(v['eax']==v['receiver'] and v['preserved'] for v in r['member_source'])
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,**metadata(),profiles=rows,allocation_failure=allocation_failure_reference()),indent=2)+'\n')
 print(json.dumps(dict(status='pass',profiles=len(rows))))
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 required={'provider required','foreign provider rejected','wrong callback rejected','missing registry fails','allocation exhaustion preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected','foreign retirement provider rejected','double physical free rejected','wrong actor state rejected','vtable slot 8 replacement rejected','reentrant wrong size request rejected','reentrant wrong receiver request rejected','reentrant wrong actor request rejected','reentrant wrong continuation request rejected','source allocation stack word 20 tampering rejected before allocation','foreign state callback rejected','missing CString service rejected','live vtable replacement rejected','duplicate allocation request rejected'}
 required.update({'helper-only retirement retains secondaries','final retirement frees all owned allocations','stale secondary after final retirement rejected'})
 for offset in ('70','78'):
  required.update(f'{name} {offset}' for name in ('secondary metadata callback replacement rejected','retained secondary identity replacement rejected','foreign secondary slot rejected','secondary allocation size rejected','secondary allocation continuation rejected','secondary allocation reentry rejected','secondary allocation duplicate rejected','secondary duplicate free rejected','secondary physical free bypass rejected','secondary physical free after helper retirement rejected','retained secondary metadata replacement rejected'))
 required.update({f'malformed source {mode} rejected' for mode in ('size','version','mask','return')})
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append('required controls missing or duplicated')
 for e,a in zip(ref['profiles'],native['profiles']):
  initial=bytes.fromhex(next(b['data'] for b in e['initial'] if b['address']==BASE))
  if any(struct.unpack_from('<I',initial,e['actor']-BASE+offset)[0] for offset in (0x70,0x78)):
   fail.append(dict(label=e['label'],field='empty initial secondary slots'))
  for index in (0,1):
   helper=e['allocations'][0 if index==0 else 3][0]
   data=bytes.fromhex(next(b['data'] for b in e['snapshots'][index] if b['address']==helper))
   actor_data=bytes.fromhex(next(b['data'] for b in e['snapshots'][index] if b['address']==BASE))
   if any(struct.unpack_from('<I',data,offset)[0]==0 for offset in RESOURCE_FIELDS):fail.append(dict(label=e['label'],field='nonzero constructor resource witnesses'))
   if struct.unpack_from('<II',actor_data,e['state']-BASE+0x18)!=(helper,5):fail.append(dict(label=e['label'],field='constructor helper and HOME state outputs'))
   for binding in e['secondary_metadata']:
    token=struct.unpack_from('<I',actor_data,e['actor']-BASE+binding['offset'])[0]
    allocation=e['allocations'][1 if binding['offset']==0x70 else 2]
    if [token,0x174]!=allocation:fail.append(dict(label=e['label'],field='secondary allocation identity'))
    secondary=bytes.fromhex(next(b['data'] for b in e['snapshots'][index] if b['address']==token))
    if struct.unpack_from('<I',secondary,0x10)[0]!=binding['callback']:
     fail.append(dict(label=e['label'],field='metadata-selected secondary callback'))
  for key in ('label','outgoing','events','snapshots','x87_snapshots','retired_bytes','final_snapshots','retired_secondary_bytes'):
   if e[key]!=a[key]:
    difference=dict(label=e['label'],field=key)
    if key=='x87_snapshots':difference['commands']=[dict(index=i,command=e['commands'][i],expected=x,actual=y) for i,(x,y) in enumerate(zip(e[key],a[key])) if x!=y]
    fail.append(difference)
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  if not a['allocation_witness']:fail.append('allocation continuation witness')
  if a.get('secondary_witnesses')!=[0x4c7f4f,0x4c800f]:fail.append('secondary allocation continuation witnesses')
  if not a['retired']:fail.append('retirement incomplete')
  def source_records(rows):return cut.normalize_calls([[v['function'],v['receiver'],[v['eax'],v['return_pc'],v['stack_delta'],int(v['preserved'])]] for v in rows])
  if not e['member_source'] or source_records(e['member_source'])!=source_records(a.get('member_source',[])):fail.append(dict(label=e['label'],field='member source CALL/RET observations'))
  # Original 44bc60, 469510 and motion integrator 4dca10 are embedded by
  # recovered owners; all outward resource, memory and collision calls remain.
  selected=set(OBSERVE)-{0x44bc60,0x4f6286,0x4dca10}
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
