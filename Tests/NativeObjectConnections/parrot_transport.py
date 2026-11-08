"""Finite Parrot shared-owner transport. Original assets and evidence stay local."""
import importlib.util,json,struct,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
spec=importlib.util.spec_from_file_location('hermit_transport',ROOT/'Tests/NativeObjectConnections/hermit_crab_transport.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
cut=h.cut
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EBP,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE=tuple(a for a in h.OBSERVE if a not in (0x44a380,0x449d60,0x44ac40,0x44ac60,0x44ae30,0x44ade0))+(0x465640,0x466730,0x465db0,0x466790,0x43e420,0x465cc0,0x465ce0,0x40f780,0x44aa90,0x406150,0x406180,0x467c90,0x441030,0x4a3810)
RESOURCE_FIELDS=(0x350,0x38c,0x390,0x394,0x398,0x39c,0x148,0x410,0x414,0x408,0x40c,0x418,0x41c,0x420,0x424,0x428)
class Reference(h.Reference):
 def __init__(self,live=False,fractional=False):
  super().__init__(live,fractional)
  self.member_registers={}
  self.commands=[0,1000,29,30,5]
  self.put(self.tokens['state']+0x10,0x465580)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  anim=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x529ba8,sprite)
  for k in (0x529b94,0x529b80,0x529b6c,0x529b54,0x529b3c):self.bind('animations',k,anim)
  for k in (0x5266ec,0x524870,0x524864,0x524858,0x52484c,0x5266dc,0x529b24,0x529b08,0x529af0,0x529adc,0x529ac8):self.bind('sounds',k,self.object(0x20,fill=0))
  node=self.get(0x537680);self.put(node+12,0x529c08);self.put(node+16,5)
  self.put(0x537b14,0)
  name_header=self.object(32,words=[1,11,11],fill=0);self.write(name_header+12,b'LS_FLYABOUT\0')
  names=self.object(4,words=[name_header+12]);self.put(0x5376a0,5,5,names);self.put(0x5376b0,4)
  callbacks=self.object(4,words=[0x466790]);self.put(0x537c38,5,5,callbacks);self.put(0x537c48,4)
  self.state_string_spans=[(name_header,32),(names,4),(callbacks,4)]
  for a in OBSERVE:
   if a not in h.OBSERVE:self.m.observe(a,self.entry)
  for pc in (0x465690,0x4656a0):self.m.observe(pc,lambda m,a:self.source_return(m,0x4f6439))
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def source_return(self,m,function):
  before=self.member_registers.pop(function)
  super().source_return(m,function)
  self.source_observations[-1].update(nonvolatiles=before,preserved=before==[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)])
 def entry(self,m,a):
  if a in (0x4f6439,0x4db620):self.member_registers[a]=[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]
  if a in h.OBSERVE:super().entry(m,a)
  else:
   arity={0x465640:1,0x466730:1,0x465db0:1,0x465cc0:1,0x40f780:1,0x44aa90:1,0x441030:1,0x4a3810:2}.get(a,0)
   self.entries.append([a,0 if a==0x4a3810 else m.register(UC_X86_REG_ECX),list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a==0x465640:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];x87=[]
  for command in self.commands:
   self.put(self.tokens['state']+0x1c,command)
   result=self.m.call(0x465580,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not result.completed:raise RuntimeError((label,command,result))
   if command==0:assert all(self.get(ALLOC+o) for o in RESOURCE_FIELDS)
   spans=[(BASE,SIZE),(0x537668,0x54),(0x537c30,0x28),(0x537210,4),(0x5430c4,4),(0x544b98,0x184)]+self.allocations
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans]);x87.append(self.m.x87_state())
  result=self.m.call(0x465cc0,ecx=ALLOC,arguments=(1,),timeout_seconds=5);assert result.completed
  retired=self.read(ALLOC,0x450).hex()
  for offset in (0x70,0x78):
   helper=self.get(self.tokens['owner']+offset);result=self.m.call(0x4c80c0,ecx=helper,arguments=(1,),timeout_seconds=5);assert result.completed;self.put(self.tokens['owner']+offset,0)
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,frames=self.frames,source_observations=self.source_observations,snapshots=snapshots,x87_snapshots=x87,retired_bytes=retired)
def string_retirements():
 rows=[]
 for name,references,members in (('owned-string-free',1,[0x1a4]),('owned-string-retained',2,[0x1a4]),('owned-string-shared',2,[0x1a8,0x1a4])):
  r=Reference();r.m.reset_x87();r.m.set_x87_state(*r.incoming)
  assert r.m.call(0x465580,arguments=(r.tokens['owner'],),timeout_seconds=5).completed
  assert r.m.call(0x4a48e0,arguments=(16,),timeout_seconds=5).completed
  token=r.m.register(UC_X86_REG_EAX);r.put(token,references,3,3);r.write(token+12,b'abc\0')
  for offset in members:r.put(ALLOC+offset,token+12)
  assert r.m.call(0x465cc0,ecx=ALLOC,arguments=(1,),timeout_seconds=5).completed
  rows.append(dict(name=name,references=references,members=members,token=token,bytes=r.read(token,16).hex(),freed=token in r.freed,helper_freed=ALLOC in r.freed,helper_bytes=r.read(ALLOC,0x450).hex()))
 return rows
def bitset_failure_reference():
 r=Reference();r.m.observe(0x4dbe10,lambda m,a:r.put(0x533470,64));seen={};external=r.external
 def fail(m,a):
  if a==0x4a48e0 and r.get(m.register(UC_X86_REG_ESP)+4)==8:m.return_from_external(0,0)
  else:external(m,a)
 def diagnostic(m,a):seen.update(ebp=m.register(UC_X86_REG_EBP),continuation=r.get(m.register(UC_X86_REG_ESP)))
 def returned(m,a):seen['eax']=m.register(UC_X86_REG_EAX);m.uc.emu_stop()
 r.m.on_external=fail;r.m.observe(0x4dc680,diagnostic);r.m.observe(0x4dbf9f,returned)
 result=r.m.call(0x465580,arguments=(r.tokens['owner'],),timeout_seconds=5)
 assert not result.completed and seen==dict(ebp=ALLOC+0x128,continuation=0x4dbf9f,eax=r.tokens['owner'])
 return seen
def allocation_failure_reference():
 r=Reference();seen=[];external=r.external
 def fail(m,a):
  if a==0x4a48e0:
   seen.append(dict(function=a,count=r.get(m.register(UC_X86_REG_ESP)+4),result=0));m.return_from_external(0,0)
  else:external(m,a)
 def stop(m,a):seen.append(dict(function=a));m.uc.emu_stop()
 r.m.on_external=fail;r.m.observe(0x5022b5,stop)
 result=r.m.call(0x465580,arguments=(r.tokens['owner'],),timeout_seconds=5)
 assert not result.completed and seen==[dict(function=0x4a48e0,count=0x450,result=0),dict(function=0x5022b5)] and r.allocations==[]
 return seen
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 profiles=[Reference(live,fractional).run(f'live-{int(live)}-fractional-{int(fractional)}') for live in (False,True) for fractional in (False,True)]
 r=Reference();metadata=[]
 for pc,target,cont in ((0x4655b8,0x4f63ec,0x4655bd),(0x4655d3,0x465640,0x4655d8),(0x465667,0x44bc60,0x46566c),(0x46568b,0x4f6439,0x465690),(0x46569b,0x4f6439,0x4656a0),(0x465811,0x4dbe10,0x465816),(0x465828,0x4dbd60,0x46582d)):
  code=r.read(pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target and pc+5==cont;metadata.append(dict(call=pc,target=target,continuation=cont))
 slots={o:r.get(0x50ec6c+o) for o in (0,4,8,12,16,28,32,36)}
 assert slots=={0:0x465cc0,4:0x466730,8:0x465db0,12:0x4063b0,16:0x405000,28:0x4c96b0,32:0x43e9b0,36:0x467c90}
 for row in profiles:
  assert row['allocations']==[[ALLOC,0x450],[ALLOC+0x450,0x174],[ALLOC+0x5d0,0x174]]
  assert row['continuations'][:2]==[[0x4f63ec,0x4655bd],[0x465640,0x4655d8]]
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=profiles,call_metadata=metadata,vtable=slots,allocation_failure=allocation_failure_reference(),bitset_failure=bitset_failure_reference(),string_retirements=string_retirements()),indent=2)+'\n')
 print(json.dumps(dict(status='pass',original_profiles=len(profiles))))
def preflight(out):
 registry=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
 required=(0x465580,0x465640,0x44bc60,0x44aaf0,0x465cc0,0x466730,0x465db0,0x466790,0x4063b0,0x467c90)
 missing=[hex(a) for a in required if not re.search(r'\{0x%08xu,' % a,registry)]
 for a in (0x465640,0x44bc60,0x466730,0x465db0,0x466790,0x4063b0):
  row=next((r for r in registry.splitlines() if '{0x%08xu,' % a in r),'')
  if not row.endswith('1u},'):missing.append(hex(a)+' x87 environment')
 print(json.dumps(dict(status='fail' if missing else 'pass',missing=missing)))
 return bool(missing)
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 required={'provider required','foreign provider rejected','wrong callback rejected','wrong actor state rejected','missing registry fails','allocation exhaustion preserved','occupied allocation preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected','foreign retirement provider rejected','double physical free rejected','duplicate allocation request rejected','foreign state callback rejected','live vtable replacement rejected','stale helper identity rejected','bitset caller frame supplies diagnostic','foreign bitset caller frame rejected','shared scene allocation cursor retained','missing lifecycle physical service rejected'}
 names=[c['name'] for c in native['controls']]
 if not required.issubset(names) or len(names)!=len(set(names)):fail.append('missing or duplicate controls')
 for e,a in zip(ref['profiles'],native['profiles']):
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  for field in ('label','outgoing','snapshots','x87_snapshots','retired_bytes'):
   if e[field]!=a[field]:fail.append(dict(label=e['label'],field=field))
  if not a['retired'] or not a['allocation_witness']:fail.append('retirement/allocation witness')
  if e['events']!=a['events']:fail.append(dict(field='events',expected=len(e['events']),actual=len(a['events']),first=next(((x,y) for x,y in zip(e['events'],a['events']) if x!=y),None)))
  selected=set(OBSERVE)-{0x4f6286,0x4c7f20,0x4c7fe0,0x4c80e0,0x465ce0}
  # Physical registry lookup owns its internal string comparisons; compare
  # lookup names/results as ordered events. The real +24 owner embeds its
  # motion integration, while its source-level 43dfa0 root is still observed.
  original=[];in_motion=False;in_release=False
  for row in e['entries']:
   if row[0]==0x43dfa0:in_motion=True
   if row[0]==0x441030:in_release=True
   if row[0]==0x4a3810 and not in_release:continue
   if row[0]==0x4dca10 and in_motion:continue
   if row[0] in selected:original.append(row)
  ec=cut.normalize_calls(original);ac=cut.normalize_calls([r for r in a['calls'] if r[0] in selected])
  if ec!=ac:fail.append(dict(field='calls',expected=len(ec),actual=len(ac),first=next(((x,y) for x,y in zip(ec,ac) if x!=y),None)))
  def sources(rows):return cut.normalize_calls([[r['function'],r['input_receiver'],[r['return_pc'],r['output_eax'],r['stack_delta'],r['fs_preserved'],*r['nonvolatiles'],r['preserved']]] for r in rows])
  if sources(e['source_observations'])!=sources(a['source_observations']):fail.append('member source contexts')
  if [[r['function'],r['caller_frame'],r['continuation']] for r in e['frames']]!=[[r['function'],r['caller_frame'],r['continuation']] for r in a['frames']]:fail.append('inherited bitset caller frames')
  if [r[1:] for r in a['allocation_requests']]!=[[0x450,0x4f63ff,0x4655bd],[0x174,0x4f63ff,0x4c7f4f],[0x174,0x4f63ff,0x4c800f]]:fail.append('source allocation requests')
 if ref['string_retirements']!=native['string_retirements']:fail.append('owned member string retirement')
 for c in native['controls']:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),controls=len(native['controls']),failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve();assert (ROOT/'work').resolve() in out.parents
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='preflight':raise SystemExit(preflight(out))
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
