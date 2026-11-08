"""Finite original/native TownGuard1 allocation and lifecycle comparison."""
import importlib.util
import json
import hashlib
import re
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
_spec=importlib.util.spec_from_file_location('cut_transport',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(cut)
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE=tuple(a for a in cut.OBSERVE if a not in (0x437a90,0x4384f0))+(0x496110,0x497970,0x44f1b0,0x44cfd0,0x4c96b0,0x4dc870,0x497510,0x497130,0x44d000,0x44d3c0,0x43dfa0,0x4979b0,0x496840,0x4f6584,0x4f6428,0x497a50,0x43e420,0x4cbb60)
SECONDARY_OBSERVE=(0x4c7f20,0x4c7fe0,0x4c81b0,0x4c8160,0x4c80c0,0x4c80e0)
class Reference(cut.Reference):
 def __init__(self,status=0,live=False,control=0x23f):
  super().__init__(status,live,control)
  self.contexts=[];self.commands=[0];self.freed=[];self.secondary=False;self.secondary_retired=[]
  self.m.intercept(0x4a49b0)
  self.put(self.tokens['state']+0x10,0x496050)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x52d204,sprite)
  for key in (0x52d1e8,0x52d148,0x52d1ac,0x52d47c):self.bind('animations',key,animation)
  for key in (0x52d090,0x52d074,0x52d058,0x52d040,0x52d024,0x52d008,0x52cfec,0x52cfd0,0x52cfb4,0x52cf98,0x52cf7c,0x52cf60,0x52cf44,0x52cf2c,0x52cf14):
   self.bind('sounds',key,self.object(0x20,fill=0))
  for a in OBSERVE+SECONDARY_OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
 def fresh_secondary(self):
  self.secondary=True;self.commands=[0,0]
  # These are the actual registry identities and callbacks in the retained WWD
  # actor witness, projected into this independent constructor fixture.
  for key,kind,callback in ((0x522d54,21,0x4dc830),(0x522d48,22,0x4dc850)):
   self.bind('logic',key,self.object(0x14,words=[key,kind,2,0,callback]))
  assert self.get(self.tokens['owner']+0x70)==self.get(self.tokens['owner']+0x78)==0
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def lifecycle(self):
  self.commands=[0,1000,29,30,6]
  player=self.object(0x200,fill=0);state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,state);self.put(state+0x14,inputs);self.put(player+0x4c,100)
  name=self.object(16,data=b'LS_IDLE2\0',fill=0);table=self.object(4,words=[name]);self.put(0x5376a0,6,6,table);self.put(0x5376b0,4)
  callbacks=self.object(4,words=[0x497a50]);self.put(0x53ca78,6,6,callbacks);self.put(0x53ca88,4)
  tilemap=self.object(0xa0,fill=0);cells=self.object(4,words=[0xffffffff]);rows=self.object(4,words=[0])
  self.put(tilemap+0x20,cells,rows);self.put(tilemap+0x30,1024,1024);self.put(tilemap+0x8c,10,10);self.put(self.tokens['collision']+0x5c,tilemap)
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a)
  sp=m.register(UC_X86_REG_ESP)
  if slot==0x546cd4:
   rectangle,x,y=m.words(sp+4,3);x,y=struct.unpack('<ii',struct.pack('<II',x,y));left,top,right,bottom=struct.unpack('<iiii',self.read(rectangle,16))
   result=int(left<=x<right and top<=y<bottom);self.events.append(['point-in-rectangle',rectangle,x,y,result]);m.return_from_external(result,12)
  elif a==0x4a49b0:
   token=self.get(sp+4);assert token in [v[0] for v in self.allocations] and token not in self.freed
   if [token,0x174] in self.allocations:self.secondary_retired.append(dict(address=token,data=self.read(token,0x174).hex()))
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  else:super().external(m,a)
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a in cut.OBSERVE:super().entry(m,a)
  else:
   arity={0x496110:1,0x4dc870:1,0x497510:1,0x497130:1,0x44d000:1,0x44d3c0:1,0x496840:1,0x4f6428:1,0x4cbb60:4,0x4c7f20:1,0x4c7fe0:1,0x4c8160:2,0x4c80c0:1}.get(a,0)
   receiver=0 if a in (0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
   self.entries.append([a,receiver,list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a==0x496110:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x497130:
   sp=m.register(UC_X86_REG_ESP)
   self.contexts.append([a,m.register(UC_X86_REG_ECX),self.get(sp),m.register(UC_X86_REG_EBX),m.register(UC_X86_REG_EBP),m.register(UC_X86_REG_EAX),m.register(UC_X86_REG_ESI),m.register(UC_X86_REG_EDI),self.get(sp+4)])
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];results=[];x87_snapshots=[]
  for index,command in enumerate(self.commands):
   if self.secondary and index:
    old=self.get(self.tokens['state']+0x18)
    retired=self.m.call(0x496840,ecx=old,arguments=(1,),timeout_seconds=5);assert retired.completed
    self.put(self.tokens['state']+0x18,0)
   self.put(self.tokens['state']+0x1c,command)
   if command==6:
    # Inputs to this finite lifecycle boundary: an unexpired idle timer and
    # motion state 7 use the original collision owner's direct publication.
    self.put(0x537210,100);self.put(ALLOC+0x488,90,20);self.put(self.tokens['owner']+0xcc,7)
   r=self.m.call(0x496050,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not r.completed:raise RuntimeError((label,command,r))
   results.append(self.m.register(UC_X86_REG_EAX));x87_snapshots.append(self.m.x87_state())
   spans=[(self.tokens['owner'],0x200),(self.tokens['state'],0x180)]+[a for a in self.allocations if a[0] not in self.freed]
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
  retired=None
  if len(self.commands)>1:
   self.retirement_entries=len(self.entries)
   helper=self.get(self.tokens['state']+0x18)
   r=self.m.call(0x496840,ecx=helper,arguments=(1,),timeout_seconds=5)
   if not r.completed:raise RuntimeError(('retirement',label,r))
   retired=dict(bytes=self.read(helper,0x498).hex(),freed=self.freed,entries=self.entries[self.retirement_entries:])
   if self.secondary:
    for offset in (0x70,0x78):
     result=self.m.call(0x4c80c0,ecx=self.get(self.tokens['owner']+offset),arguments=(1,),timeout_seconds=5);assert result.completed
     self.put(self.tokens['owner']+offset,0)
  return dict(secondary=self.secondary,secondary_retired=self.secondary_retired,retired=retired,label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,contexts=self.contexts,results=results,snapshots=snapshots,x87_snapshots=x87_snapshots,final=snapshots[-1])
DERIVED_RETURNS=(0x496725,0x49676b,0x49678e)
def diagnostic(out):
 out.mkdir(parents=True,exist_ok=True)
 profiles=[]
 for live in (False,True):
  for fractional in (False,True):
   r=Reference(live=live);calls=[];base=[]
   if fractional:
    for address,value in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):
     r.write(address,struct.pack('<f',value))
   r.initial=[dict(address=a,data=r.read(a,n).hex()) for a,n in r.blocks]
   r.m.observe(0x49613a,lambda machine,address:base.append(machine.x87_state()))
   r.m.observe(0x4a30e0,lambda machine,address:calls.append(dict(function=address,return_pc=r.get(machine.register(UC_X86_REG_ESP)),x87=machine.x87_state())))
   profile=r.run(f'live-{int(live)}-fractional-{int(fractional)}')
   profile.update(live=live,fractional=fractional,base_return_x87=base,conversion_calls=calls)
   derived=[c for c in calls if c['return_pc'] in DERIVED_RETURNS]
   assert [c['return_pc'] for c in derived]==list(DERIVED_RETURNS)
   assert all(len(c['x87'][2])==(2 if live else 1) for c in derived)
   assert all(c['x87'][0]==0x23f for c in derived)
   assert profile['outgoing']==base[0], 'sampled final x87 changed; inspect exact evidence'
   assert profile['allocations']==[[ALLOC,0x498]]
   assert profile['continuations']==[[0x4f63ec,0x49608d],[0x496110,0x4960a8]]
   assert any(e[0]=='lookup' and e[2]=='LEVEL_TOWNGUARD1' and e[3]!=0 for e in profile['events'])
   assert any(e[0]=='lookup' and e[2]=='LEVEL_TOWNGUARD1_STRIKE1' and e[3]!=0 for e in profile['events'])
   profiles.append(profile)
 program=claw();metadata=[]
 for pc,target,continuation in ((0x496088,0x4f63ec,0x49608d),(0x4960a3,0x496110,0x4960a8),(0x496135,0x44c000,0x49613a),(0x496720,0x4a30e0,0x496725),(0x496766,0x4a30e0,0x49676b),(0x496789,0x4a30e0,0x49678e)):
  code=r.read(pc,5)
  assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 registry=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
 row=next(line.strip() for line in registry.splitlines() if line.strip().startswith('{0x00496110u,'))
 fields=[part.strip() for part in row.strip('{}, ').split(',')]
 environment=int(fields[-1].rstrip('u'),0)
 source=(ROOT/'Sources/LevelFiveTownGuardCoreRuntime.cpp').read_text()
 constructor=source[source.index('uint32_t construct('):source.index('uint32_t destruct(')]
 scalar_calls=len(re.findall(r'run\.call_x87\(0x4a30e0',constructor))
 missing=environment==0 and scalar_calls==3
 hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('Sources/LevelFiveTownGuardCoreRuntime.cpp','Sources/ClawCanonicalDispatch.h','Sources/ClawRuntime.hpp')}
 evidence=dict(original_sha256=program.sha256,call_metadata=metadata,profiles=profiles,source_hashes=hashes,constructor_x87_environment=environment,constructor_scalar_conversion_calls=scalar_calls,native_comparison=False,host_wired=False)
 (out/'reference.json').write_text(json.dumps(evidence,indent=2)+'\n')
 result=dict(status='missing-owner-contract' if missing else 'transport-not-implemented',original_profiles=len(profiles),original_complete=True,native_comparison=False,host_wired=False,evidence=str(out/'reference.json'),reason='Constructor 0x496110 has no x87 environment contract and uses three scalar conversion calls; original inherited live stack supplies two slots plus CW/SW at each derived conversion.' if missing else 'The constructor contract changed; native transport comparisons and ownership controls are still required.',sampled_final_x87='equals base-return state; no final-state mismatch claimed')
 (out/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 3
def boundary_metadata():
 # Decode only the finite ABI boundary against the pinned executable. Instruction
 # text stays out of source control; the evidence records typed CALL metadata.
 from capstone import Cs, CS_ARCH_X86, CS_MODE_32
 from capstone.x86_const import X86_INS_CALL,X86_OP_MEM,X86_REG_EAX,X86_REG_EDX,X86_REG_ESI
 program=claw();decoder=Cs(CS_ARCH_X86,CS_MODE_32);decoder.detail=True
 def read(address,count):
  section=next(s for s in program.sections if s.address<=address and address+count<=s.address+len(s.data))
  return section.data[address-section.address:address-section.address+count]
 metadata=[]
 for pc,target,continuation in ((0x496088,0x4f63ec,0x49608d),(0x4960a3,0x496110,0x4960a8),(0x496135,0x44c000,0x49613a),(0x4c7f4a,0x4f63ec,0x4c7f4f),(0x4c800a,0x4f63ec,0x4c800f),(0x4c7fcb,0x4c7f20,0x4c7fd0),(0x4c808b,0x4c7fe0,0x4c8090)):
  code=read(pc,5);assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 for pc,continuation,base,offset in ((0x4960ba,0x4960bd,X86_REG_EAX,0x10),(0x4960c7,0x4960ca,X86_REG_EDX,0x20),(0x4960eb,0x4960ee,X86_REG_EDX,0x1c),(0x4dc943,0x4dc946,X86_REG_EDX,8),(0x4971f7,0x4971f9,X86_REG_ESI,0)):
  instruction=next(decoder.disasm(read(pc,8),pc));assert instruction.id==X86_INS_CALL and instruction.address+instruction.size==continuation
  assert len(instruction.operands)==1 and instruction.operands[0].type==X86_OP_MEM
  operand=instruction.operands[0];assert operand.size==4 and operand.mem.base==base and operand.mem.index==0 and operand.mem.disp==offset
  metadata.append(dict(call=pc,continuation=continuation,receiver_register=decoder.reg_name(base),slot=offset))
 slots={offset:struct.unpack('<I',read(0x50fabc+offset,4))[0] for offset in (0,4,8,12,16,28,32,36)}
 assert slots=={0:0x496840,4:0x497510,8:0x497130,12:0x44d3c0,16:0x405000,28:0x4c96b0,32:0x44cfd0,36:0x43dfa0}
 return dict(call_metadata=metadata,vtable=dict(address=0x50fabc,slots=slots))
def string_retirement_references():
 rows=[]
 for name,references,members in (('owned-string-free',1,[0x1a4]),('owned-string-retained',2,[0x1a4]),('owned-string-shared',2,[0x1a8,0x1a4])):
  r=Reference();r.run(name)
  allocated=r.m.call(0x4a48e0,arguments=(16,),timeout_seconds=5);assert allocated.completed
  token=r.m.register(UC_X86_REG_EAX);r.put(token,references,3,3);r.write(token+12,b'abc\0')
  for offset in members:r.put(ALLOC+offset,token+12)
  result=r.m.call(0x496840,ecx=ALLOC,arguments=(1,),timeout_seconds=5);assert result.completed
  rows.append(dict(name=name,references=references,members=members,token=token,bytes=r.read(token,16).hex(),freed=token in r.freed,helper_freed=ALLOC in r.freed,helper_bytes=r.read(ALLOC,0x498).hex()))
 return rows
def wwd_secondary_prefix():
 source=ROOT/'work/native-object-connections/town_guard1'
 p=json.loads((source/'town-active-input.json').read_text());failed=json.loads((source/'town-failed-callback.json').read_text())
 m=cut.Machine(claw(),BASE,4096)
 imports={a:m.read(a,4) for a in m.import_stub}
 def map_span(a,n):
  for page in range(a&~4095,(a+n+4095)&~4095,4096):
   if not any(lo<=page<=hi for lo,hi,_ in m.uc.mem_regions()):m.uc.mem_map(page,4096)
 for b in p['segments']:
  data=bytes.fromhex(b['hex']);map_span(b['address'],len(data));m.write(b['address'],data)
 for a,data in imports.items():m.write(a,data)
 next_token=failed['allocations'][0]['token'];base=next_token;calls=[];events=[];binds=[];done=[]
 bindings={'LogicHit':0x61f50c40,'LogicAttack':0x61f50c60}
 assert m.words(p['actor']+0x70,1)==m.words(p['actor']+0x78,1)==(0,)
 for name,token in bindings.items():
  assert m.read(m.words(token,1)[0],len(name)+1)==name.encode()+bytes([0])
 def observed(machine,a):
  sp=machine.register(UC_X86_REG_ESP);receiver=machine.register(UC_X86_REG_ECX)
  arity=2 if a==0x4c8160 else 1
  calls.append([a,receiver,list(machine.words(sp+4,arity))])
  if a==0x4c8160:
   binds.append(a)
   if len(binds)==2:
    def stop(machine,a):done.append(True);machine.uc.emu_stop()
    machine.observe(machine.words(sp,1)[0],stop)
 for a in (0x4c7fa0,0x4c8060,0x4c8160):m.observe(a,observed)
 for a in (0x4a48e0,0x4f6286):m.intercept(a)
 def external(machine,a):
  nonlocal next_token
  sp=machine.register(UC_X86_REG_ESP)
  if a==0x4a48e0:
   n=machine.words(sp+4,1)[0];token=next_token;next_token=(token+n+15)&~15;map_span(token,n);machine.write(token,bytes([204])*n)
   events.append(['malloc',token,n]);machine.return_from_external(token,0)
  elif a==0x4f6286:
   key,out=machine.words(sp+4,2);name=machine.read(key,32).split(bytes([0]))[0].decode();value=bindings[name]
   machine.write(out,struct.pack('<I',value));events.append(['lookup',machine.register(UC_X86_REG_ECX),name,value]);machine.return_from_external(1,8)
  else:raise AssertionError(('unexpected WWD prefix service',hex(a)))
 m.on_external=external;m.reset_x87();m.set_x87_state(0x23f,0,[])
 m.call(0x496050,arguments=(p['actor'],),timeout_seconds=5);assert done
 return dict(actor=p['actor'],state=p['state'],allocation_base=base,wwd=True,incoming=[0x23f,0,[]],initial=[dict(address=b['address'],data=b['hex']) for b in p['segments']],bindings=bindings,events=events,calls=calls,secondary_bytes=[dict(address=m.words(p['actor']+off,1)[0],data=m.read(m.words(p['actor']+off,1)[0],0x174).hex()) for off in (0x70,0x78)])
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 profiles=[]
 for live in (False,True):
  for fractional in (False,True):
   r=Reference(live=live);r.lifecycle()
   if fractional:
    for address,value in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):
     r.write(address,struct.pack('<f',value))
   r.initial=[dict(address=a,data=r.read(a,n).hex()) for a,n in r.blocks]
   profile=r.run(f'live-{int(live)}-fractional-{int(fractional)}');profiles.append(profile)
   assert profile['allocations']==[[ALLOC,0x498]]
   assert profile['continuations']==[[0x4f63ec,0x49608d],[0x496110,0x4960a8]]
   assert {0x497130,0x497a50,0x43dfa0}.issubset({row[0] for row in profile['entries']})
 for live in (False,True):
  r=Reference(live=live);r.fresh_secondary();profile=r.run(f'fresh-secondary-rebind-live-{int(live)}');profiles.append(profile)
  assert profile['allocations']==[[ALLOC,0x498],[ALLOC+0x4a0,0x174],[ALLOC+0x620,0x174],[ALLOC+0x7a0,0x498]]
  assert profile['continuations']==[[0x4f63ec,0x49608d],[0x496110,0x4960a8],[0x4f63ec,0x4c7f4f],[0x4f63ec,0x4c800f],[0x4f63ec,0x49608d],[0x496110,0x4960a8]]
  assert [v[0] for v in profile['entries'] if v[0] in (0x4c81b0,0x4c8160)]==[0x4c8160,0x4c8160,0x4c81b0,0x4c8160,0x4c81b0,0x4c8160]
  assert all(any(e[:3]==['lookup',r.tokens['managers']['logic']+16,name] and e[3] for e in profile['events']) for name in ('LogicHit','LogicAttack'))
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,**boundary_metadata(),profiles=profiles,string_retirements=string_retirement_references(),wwd=wwd_secondary_prefix()),indent=2)+'\n')
 print(json.dumps(dict(status='pass',original_profiles=len(profiles))))
def preflight(out):
 registry=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
 required=(0x496050,0x496110,0x44c000,0x44d000,0x44d3c0,0x44c840,0x497130,0x497510,0x497a50,0x43dfa0,0x496840)
 missing=[hex(a) for a in required if not re.search(r'\{0x%08xu,' % a,registry)]
 result=dict(status='pending-admission' if missing else 'pass',missing_canonical_entries=missing,native_comparison=False,host_wired=False)
 (out/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 3 if missing else 0
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=6 or len(native['profiles'])!=6:fail.append('profile count')
 required={'provider required','foreign provider rejected','wrong callback rejected','missing registry fails','allocation exhaustion preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected'}
 required.update({'fresh secondaries require scene owner','fresh secondary ledger ownership','same owner retires all three allocations','secondary allocation source stack tampering rejected','secondary allocation exhaustion preserved','stale LogicHit metadata allocation rejected','stale LogicAttack metadata allocation rejected','LogicHit callback mutation rejected','LogicAttack callback mutation rejected','secondary rebind rejects redirected scene owner','secondary rebind rejects replaced registry identity','secondary teardown observer reentry rejected'})
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append('required controls missing or duplicated')
 for expected,actual in zip(ref['profiles'],native['profiles']):
  for field in ('label','outgoing','events','snapshots','x87_snapshots','secondary_retired'):
   if expected[field]!=actual[field]:fail.append(dict(label=expected['label'],field=field))
  if not actual['completed']:fail.append(dict(label=expected['label'],fault=actual['fault']))
  if not actual['allocation_witness']:fail.append('allocation continuation witness')
  if not actual['retired']:fail.append('retirement incomplete')
  if expected['secondary'] and actual['secondary_witnesses']!=[[0x4c7fa0,0x174,0x4f63ff,0x4c7f4f],[0x4c8060,0x174,0x4f63ff,0x4c800f]]:fail.append(dict(profile=expected['label'],field='secondary allocation source witness',actual=actual['secondary_witnesses']))
  if actual['retired_bytes']!=expected['retired']['bytes']:fail.append(dict(label=expected['label'],field='destructor bytes'))
  # The admitted enemy owner implements 43dfa0 as motion()->integrate(),
  # sharing the 4dca10 body in C++. Keep its real producer and collision calls.
  # Require the original 4dca10 entry and both source/native descendants before
  # removing this instrumentation-only extra entry from the ordered comparison.
  original_motion=[v[0] for v in expected['entries'] if v[0] in (0x43dfa0,0x4dca10,0x403b40,0x4cbb60)][-4:]
  native_motion=[v[0] for v in actual['calls'] if v[0] in (0x43dfa0,0x4dca10,0x403b40,0x4cbb60)][-3:]
  if not expected['secondary'] and (original_motion!=[0x43dfa0,0x4dca10,0x403b40,0x4cbb60] or native_motion!=[0x43dfa0,0x403b40,0x4cbb60]):fail.append('inlined integration witness')
  # 44bc60 is likewise embedded in the base constructor; lookups have separate
  # ordered physical events, and the retirement root is directly invoked.
  selected=(set(OBSERVE)|set(SECONDARY_OBSERVE))-{0x44bc60,0x4f6286,0x496840,0x4dca10,0x4c7f20,0x4c7fe0,0x4c80e0}
  if expected['secondary']:
   if len([v for v in expected['entries'] if v[0]==0x4c80e0])!=2 or any(v[0]==0x4c80e0 for v in actual['calls']):fail.append('inlined secondary destructor witness')
  e=cut.normalize_calls([v for v in expected['entries'] if v[0] in selected]);a=cut.normalize_calls([v for v in actual['calls'] if v[0] in selected])
  if e!=a:fail.append(dict(label=expected['label'],field='ordered calls',expected_count=len(e),actual_count=len(a),first_difference=next(((x,y) for x,y in zip(e,a) if x!=y),None)))
  contexts=actual['contexts']
  if contexts!=expected['contexts']:fail.append(dict(label=expected['label'],field='lifecycle source context',expected=expected['contexts'],actual=contexts))
 wwd=ref['wwd'];actual_wwd=native['wwd']
 for field in ('events','calls','secondary_bytes'):
  if actual_wwd[field]!=wwd[field]:fail.append(dict(profile='retained WWD prefix',field=field))
 if not actual_wwd['owned']:fail.append('retained WWD secondary ownership')
 if actual_wwd['completed']:fail.append('WWD prefix unexpectedly claimed complete callback')
 if native.get('string_retirements')!=ref.get('string_retirements') or len(ref.get('string_retirements',[]))!=3:fail.append('owned CString retirement comparison')
 for c in controls:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=6,controls=len(controls),string_retirements=3,failures=fail,host_wired=False)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>2 else 'diagnostic'
 out=Path(sys.argv[2] if len(sys.argv)>2 else sys.argv[1] if len(sys.argv)>1 else ROOT/'work/native-object-connections/town_guard1/transport').resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence belongs under work/')
 if command=='prepare':prepare(out)
 elif command=='compare':raise SystemExit(compare(out))
 elif command=='preflight':raise SystemExit(preflight(out))
 else:raise SystemExit(diagnostic(out))
