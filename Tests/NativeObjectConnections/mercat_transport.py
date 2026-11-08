"""Finite original/native Mercat allocation and lifecycle comparison."""
import importlib.util
import json
import re
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
_spec=importlib.util.spec_from_file_location('cut_transport',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(cut)
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
REGISTERS=dict(zip(('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags'),(UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS)))
OBSERVE=tuple(a for a in cut.OBSERVE if a not in (0x437a90,0x4384f0))+(0x45ffc0,0x460e20,0x460bf0,0x44d9f0,0x44f1b0,0x44cfd0,0x4c96b0,0x4dc870,0x460af0,0x460710,0x44d000,0x44d3c0,0x43dfa0,0x460ea0,0x460620,0x4f6584,0x4f6428,0x43e420,0x4cbb60)
class Reference(cut.Reference):
 def __init__(self,status=0,live=False,control=0x23f):
  super().__init__(status,live,control)
  self.frame_entries={};self.caller_frames=[];self.members=[];self.member_returns=set();self.pending_members=[];self.commands=[0];self.freed=[]
  self.m.intercept(0x4a49b0)
  self.m.observe(0x45ff00,self.entry)
  self.put(self.tokens['state']+0x10,0x45ff00);self.put(self.tokens['state']+0x18,0)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x5294c4,sprite)
  for key in (0x5294ac,0x529490,0x529478,0x529464,0x529450,0x52943c,0x529428,0x529414,0x529400,0x5293e8,0x5293d0,0x5293b8,0x5293a0,0x52938c,0x529378,0x529364):self.bind('animations',key,animation)
  for key in (0x52934c,0x529334,0x52931c,0x529304,0x5292ec,0x5292d4,0x5292bc,0x5292a4,0x52928c,0x529274,0x529260,0x52924c,0x529234,0x529220,0x529208,0x5291f0):
   self.bind('sounds',key,self.object(0x20,fill=0))
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
 def lifecycle(self):
  self.commands=[0,1000,29,30,6]
  player=self.object(0x200,fill=0);state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,state);self.put(state+0x14,inputs);self.put(player+0x4c,100)
  name=self.object(16,data=b'LS_IDLE2\0',fill=0);table=self.object(4,words=[name]);self.put(0x5376a0,6,6,table);self.put(0x5376b0,4)
  callbacks=self.object(4,words=[0x460ea0]);self.put(0x537b70,6,6,callbacks);self.put(0x537b80,4)
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
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  else:super().external(m,a)
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a in (0x45ff00,0x44c000) and a not in self.frame_entries:self.frame_entries[a]=m.register(UC_X86_REG_ESP)
  if a==0x45ff00:return
  if a in cut.OBSERVE:super().entry(m,a)
  else:
   arity={0x45ffc0:1,0x4dc870:1,0x460af0:1,0x460710:1,0x44d000:1,0x44d3c0:1,0x460620:1,0x4f6428:1,0x4cbb60:4}.get(a,0)
   receiver=0 if a in (0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
   self.entries.append([a,receiver,list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a in (0x4dbe10,0x4dbd60):
   self.caller_frames.append(dict(function=a,receiver=m.register(UC_X86_REG_ECX),caller_frame=m.register(UC_X86_REG_EBP),return_pc=self.get(m.register(UC_X86_REG_ESP))))
  if a in (0x4f6439,0x4db620):
   cpu={name:m.register(reg) for name,reg in REGISTERS.items()}
   pc=self.get(cpu['esp']);row=dict(function=a,return_pc=pc,input=cpu,caller_frame=list(m.words(cpu['ebp'],3)),stack=list(m.words(cpu['esp'],8)))
   self.members.append(row);self.pending_members.append(row)
   if pc not in self.member_returns:
    self.member_returns.add(pc)
    def returned(machine,address):
     if self.pending_members and self.pending_members[-1]['return_pc']==address:
      self.pending_members.pop()['output']={name:machine.register(reg) for name,reg in REGISTERS.items()}
    self.m.observe(pc,returned)
  if a==0x45ffc0:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];results=[];x87_snapshots=[]
  for command in self.commands:
   self.put(self.tokens['state']+0x1c,command)
   if command==6:
    # Inputs to this finite lifecycle boundary: an unexpired idle timer and
    # motion state 7 use the original collision owner's direct publication.
    self.put(0x537210,100);self.put(ALLOC+0x4a4,90,20);self.put(self.tokens['owner']+0xcc,7)
   r=self.m.call(0x45ff00,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not r.completed:raise RuntimeError((label,command,r))
   results.append(self.m.register(UC_X86_REG_EAX));x87_snapshots.append(self.m.x87_state())
   data=next(s for s in claw().sections if s.name=='.data')
   spans=[(BASE,SIZE),(data.address,len(data.data))]+self.allocations
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
  retired=None
  if len(self.commands)>1:
   self.retirement_entries=len(self.entries)
   r=self.m.call(0x460620,ecx=ALLOC,arguments=(1,),timeout_seconds=5)
   if not r.completed:raise RuntimeError(('retirement',label,r))
   retired=dict(bytes=self.read(ALLOC,0x4e0).hex(),freed=self.freed,entries=self.entries[self.retirement_entries:])
  return dict(frame_entries=self.frame_entries,caller_frames=self.caller_frames,members=self.members,retired=retired,label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,results=results,snapshots=snapshots,x87_snapshots=x87_snapshots,final=snapshots[-1])
def boundary_metadata():
 m=Machine(claw(),BASE,SIZE);metadata=[]
 for pc,target,continuation in ((0x45ff38,0x4f63ec,0x45ff3d),(0x45ff53,0x45ffc0,0x45ff58),(0x45ff8c,0x4dc870,0x45ff91),(0x45ffe4,0x44c000,0x45ffe9)):
  code=m.read(pc,5);assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 slots={o:m.words(0x50e954+o,1)[0] for o in (0,4,8,12,16,28,32,0x44,0x48)}
 assert slots=={0:0x460620,4:0x460af0,8:0x460710,12:0x44d3c0,16:0x405000,28:0x4c96b0,32:0x44cfd0,0x44:0x460bf0,0x48:0x460e20}
 return dict(call_metadata=metadata,vtable=dict(address=0x50e954,slots=slots))
def string_retirement_references():
 rows=[]
 for name,references,members in (('owned-string-free',1,[0x1a4]),('owned-string-retained',2,[0x1a4]),('owned-string-shared',2,[0x1a8,0x1a4])):
  r=Reference();r.run(name)
  allocated=r.m.call(0x4a48e0,arguments=(16,),timeout_seconds=5);assert allocated.completed
  token=r.m.register(UC_X86_REG_EAX);r.put(token,references,3,3);r.write(token+12,b'abc\0')
  for offset in members:r.put(ALLOC+offset,token+12)
  result=r.m.call(0x460620,ecx=ALLOC,arguments=(1,),timeout_seconds=5);assert result.completed
  rows.append(dict(name=name,references=references,members=members,token=token,bytes=r.read(token,16).hex(),freed=token in r.freed,helper_freed=ALLOC in r.freed,helper_bytes=r.read(ALLOC,0x4e0).hex()))
 return rows
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 profiles=[]
 for live in (False,True):
  for fractional in (False,True):
   r=Reference(status=0x21 if live else 0,live=live);r.lifecycle()
   if fractional:
    for address,value in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):
     r.write(address,struct.pack('<f',value))
   r.initial=[dict(address=a,data=r.read(a,n).hex()) for a,n in r.blocks]
   profile=r.run(f'live-{int(live)}-fractional-{int(fractional)}');profiles.append(profile)
   assert profile['members'][2]['input']['eax']==r.frame_entries[0x45ff00]-76
   assert profile['members'][3]['input']['ecx']==r.frame_entries[0x44c000]-28
   assert profile['allocations']==[[ALLOC,0x4e0]]
   assert profile['continuations']==[[0x4f63ec,0x45ff3d],[0x45ffc0,0x45ff58]]
   for name in ('LEVEL_MERCAT','LEVEL_MERCAT_IDLE2'):
    assert any(event[0]=='lookup' and event[2]==name and event[3]!=0 for event in profile['events']),name
   assert {0x460710,0x460ea0,0x460af0}.issubset({row[0] for row in profile['entries']})
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,**boundary_metadata(),profiles=profiles,string_retirements=string_retirement_references()),indent=2)+'\n')
 print(json.dumps(dict(status='pass',original_profiles=len(profiles))))
def preflight(out):
 registry=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
 required=(0x45ff00,0x45ffc0,0x44c000,0x44d000,0x44d3c0,0x44c840,0x460710,0x460af0,0x460ea0,0x43dfa0,0x460620)
 missing=[hex(a) for a in required if not re.search(r'\{0x%08xu,' % a,registry)]
 result=dict(status='pending-admission' if missing else 'pass',missing_canonical_entries=missing,native_comparison=False,host_wired=False)
 (out/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 3 if missing else 0
def normalize_members(rows):
 stack={}
 def value(v):
  if 0x02000000<=v<0x02010000:
   if v not in stack:stack[v]=f'source-stack-{len(stack)}'
   return stack[v]
  return v
 result=[]
 for row in rows:
  item=dict(function=row['function'],return_pc=row['return_pc'])
  for phase in ('input','output'):
   item[phase]={k:(row[phase][k]-row['input']['esp'] if k=='esp' else value(row[phase][k])) for k in row[phase]}
  result.append(item)
 return result
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')


 required={'provider required','foreign provider rejected','wrong callback rejected','missing registry fails','allocation exhaustion preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected'}
 required.update({'shared allocator cursor used before and after construction','live helper direct physical free rejected'})
 required.update(f'source {function:x} {mode} rejected' for function in (0x4f6439,0x4db620) for mode in ('unattached','version','input-mask','output-mask','preserve-mask','stack','continuation'))
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append('required controls missing or duplicated')
 for expected,actual in zip(ref['profiles'],native['profiles']):
  for field in ('label','outgoing','events','snapshots','x87_snapshots','results'):
   if expected[field]!=actual[field]:fail.append(dict(label=expected['label'],field=field))
  if not actual['completed']:fail.append(dict(label=expected['label'],fault=actual['fault']))
  if not actual['allocation_witness']:fail.append('allocation continuation witness')
  if not actual['retired']:fail.append('retirement incomplete')
  if actual['retired_bytes']!=expected['retired']['bytes']:fail.append(dict(label=expected['label'],field='destructor bytes'))
  if normalize_members(expected['members'])!=normalize_members(actual['members']):fail.append(dict(label=expected['label'],field='source member CPU envelopes',expected=normalize_members(expected['members']),actual=normalize_members(actual['members'])))
  expected_frames=cut.normalize_calls([[v['function'],v['receiver'],[v['caller_frame'],v['return_pc']]] for v in expected['caller_frames']]);actual_frames=cut.normalize_calls([[v['function'],v['receiver'],[v['caller_frame'],v['return_pc']]] for v in actual['caller_frames']])
  if expected_frames!=actual_frames:fail.append(dict(label=expected['label'],field='source caller frames',expected=expected_frames,actual=actual_frames))
  anchors=actual['frame_anchors'];members=actual['members']
  if len(members)!=4 or members[2]['input']['eax']!=anchors['root']-76 or members[3]['input']['ecx']!=anchors['base']-28:fail.append(dict(label=expected['label'],field='source frame relationship'))
  # The base constructor embeds 44bc60 and 4dca10. Mercat embeds only its
  # constructor's first idle call; the later virtual idle owner stays ordered.
  selected=set(OBSERVE)-{0x44bc60,0x4f6286,0x460620,0x4dca10}
  original=[];embedded_idle=False
  for row in expected['entries']:
   if row[0]==0x460e20 and not embedded_idle:embedded_idle=True;continue
   if row[0] in selected:original.append(row)
  e=cut.normalize_calls(original);a=cut.normalize_calls([v for v in actual['calls'] if v[0] in selected])
  if e!=a:fail.append(dict(label=expected['label'],field='ordered calls',expected_count=len(e),actual_count=len(a),first_difference=next(((x,y) for x,y in zip(e,a) if x!=y),None)))
 if native.get('string_retirements')!=ref.get('string_retirements') or len(ref.get('string_retirements',[]))!=3:fail.append('owned CString retirement comparison')
 for c in controls:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=4,controls=len(controls),string_retirements=3,failures=fail,host_wired=False)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)

if __name__=='__main__':
 command=sys.argv[1];out=Path(sys.argv[2]).resolve()
 assert (ROOT/'work').resolve() in out.parents
 if command=='prepare':prepare(out)
 elif command=='compare':raise SystemExit(compare(out))
 elif command=='preflight':raise SystemExit(preflight(out))
