"""Finite original/native PunkRat and GroundCannon owner transport; no scene promotion."""
import importlib.util
import hashlib
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.program import claw
from Tests.clawparity.world import idle_registry
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP
spec=importlib.util.spec_from_file_location('punk_rat_transport_services',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(spec);spec.loader.exec_module(cut)
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE={a:0 for a in cut.OBSERVE if a not in (0x437a90,0x44c000,0x44bc60,0x4384f0)}
OBSERVE.update({0x4743f0:1,0x4332f0:1,0x4dca10:0,0x403b40:2,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4c8220:1,0x4f6286:2,0x4db620:1,0x4dbe10:2,0x4dbd60:1,0x420fc0:1,0x4dbd20:1,0x43e9b0:0,0x4c96b0:0,0x4dc870:1,0x404fc0:1,0x4747e0:1,0x4a36f0:1,0x43d490:1,0x4063b0:1,0x43dfa0:0,0x4746f0:1,0x4f6428:1,0x4f6584:0})
OBSERVE.update({0x474bc0:0,0x4c8da0:6,0x4c8be0:6,0x4c9780:3,0x4c9830:3,0x4c9d40:4,0x4c7df0:2,0x4493c0:1,0x449480:1,0x414030:1,0x4f51c5:1,0x4f6428:1,0x484d90:1,0x456030:0,0x4c80c0:1,0x4c80e0:0})
class Reference(cut.Reference):
 def __init__(self,status=0,live=False,mirrored=False,fractional=False):
  super().__init__(status,live)
  self.freed=[];self.exact=[];self.member_entries=[];self.member_source=[]
  self.put(self.tokens['state']+0x10,0x474330)
  self.put(self.tokens['owner']+0x40,2 if mirrored else 0)
  if fractional:
   for address,value in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):self.write(address,struct.pack('<f',value))
  self.put(self.tokens['owner']+0x38,0xffffffff);self.put(self.tokens['owner']+0xdc,1,1)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x52a784,sprite)
  self.bind('sprites',0x527b14,sprite)
  for key in (0x52a770,0x52a75c,0x52a748,0x52a730,0x52a71c,0x52a704,0x527b00,0x527aec):self.bind('animations',key,animation)
  for key in (0x52a6f8,0x52a6e8):self.bind('sounds',key,self.object(0x20,fill=0))
  for key,kind,callback in ((0x522d54,21,0x4dc830),(0x522d48,22,0x4dc850),(0x522d0c,23,0x4493c0)):
   self.bind('logic',key,self.object(0x14,words=[key,kind,2,0,callback]))
  context=self.get(self.tokens['owner']+0x0c);self.put(self.tokens['state']+0x0c,context)
  container=self.object(0x40,fill=0);self.put(container+0x0c,context);self.put(context+8,container)
  self.put(container+0x28,1)
  self.scene_container=container
  player=self.object(0x200,fill=0);player_state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,player_state);self.put(player_state+0x14,inputs);self.put(player+0x4c,100)
  tilemap=self.object(0xa0,fill=0);cells=self.object(4,words=[0xffffffff]);rows=self.object(4,words=[0])
  self.put(tilemap+0x20,cells,rows);self.put(tilemap+0x30,1024,1024);self.put(tilemap+0x8c,10,10);self.put(self.tokens['collision']+0x5c,tilemap)
  idle_registry(self,5)
  text=self.text(0x523604).encode();name=self.object(13+len(text),data=struct.pack("<III",1,len(text),len(text))+text+b"\0")+12
  names=self.object(4,words=[name]);self.put(0x5376a0,5,5,names,names,4,0,0)
  # PunkRat state index 5 selects the real inherited fallback in this fixture;
  # the actual inherited fallback dispatcher remains real.
  callbacks=self.object(24,words=[0]*6)
  self.put(0x538460,0,5,callbacks,0,4)
  fallback=self.object(24,words=[0]*6)
  self.put(0x537640,0,5,fallback,0,4)
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  for a in (0x4a49b0,):self.m.intercept(a)
  for a in (0x4332f0,0x404fc0,0x4063b0):self.m.observe(a,lambda m,a:self.exact.append(dict(function=a,state=m.x87_state())))
  for a in (0x4f6439,0x4db620):self.m.observe(a,self.member_entry)
  for a in (0x4334d3,0x4334e3,0x4dc1a7,0x4dbe3c):self.m.observe(a,self.member_return)
  self.m.intercept(0x4f51c5)
  self.initial_next=self.next
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def member_entry(self,m,a):
  self.member_entries.append((a,m.register(UC_X86_REG_ECX),m.register(UC_X86_REG_ESP),[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]))
 def member_return(self,m,a):
  function,receiver,sp,regs=self.member_entries.pop();returned=[m.register(r) for r in (UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)]
  self.member_source.append(dict(function=function,receiver=receiver,return_pc=a,eax=m.register(UC_X86_REG_EAX),stack_delta=m.register(UC_X86_REG_ESP)-sp,preserved=returned==regs))
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a not in OBSERVE:return
  receiver=0 if a in (0x4f63ec,0x4dc870,0x4f6428,0x4a36f0,0x4493c0) else m.register(UC_X86_REG_ECX)
  args=list(m.words(m.register(UC_X86_REG_ESP)+4,OBSERVE[a]));self.entries.append([a,receiver,args])
  if a in (0x4f63ec,0x4743f0):self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a)
  if a==0x4f51c5:
   receiver=m.register(UC_X86_REG_ECX);actor=self.get(m.register(UC_X86_REG_ESP)+4)
   node=self.object(12,fill=0);last=self.get(receiver+8);self.put(node,0,last,actor)
   if last:self.put(last,node)
   else:self.put(receiver+4,node)
   self.put(receiver+8,node);self.put(receiver+12,self.get(receiver+12)+1)
   self.events.append(['append',receiver,actor,node]);m.return_from_external(node,4)
  elif slot==0x546cd4:
   rectangle,x,y=m.words(m.register(UC_X86_REG_ESP)+4,3);left,top,right,bottom=struct.unpack("<iiii",self.read(rectangle,16));x,y=struct.unpack("<ii",struct.pack("<II",x,y));result=int(left<=x<right and top<=y<bottom);self.events.append(["contains",rectangle,x,y,result]);m.return_from_external(result,12)
  elif slot==0x546a40:
   pointer,size=m.words(m.register(UC_X86_REG_ESP)+4,2);self.read(pointer,size);self.events.append(["readable",pointer,size,0]);m.return_from_external(0,8)
  elif a==0x4a49b0:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [a for a,n in self.allocations] and token not in self.freed
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  else:super().external(m,a)
 def snapshot(self,command):
  spans=[(BASE,SIZE),(0x537638,0x88),(0x538458,0x24),(0x5430c4,4)]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(command=command,helper=self.get(self.tokens['state']+0x18),outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),retired={str(a):self.read(a,n).hex() for a,n in self.allocations if a in self.freed},exact=list(self.exact),member_source=list(self.member_source),final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);phases=[]
  for command in (0,1000,29,30,5):
   self.put(self.tokens['state']+0x1c,command);r=self.m.call(0x474330,arguments=(self.tokens['owner'],),timeout_seconds=5)
   assert r.completed,(command,r)
   phases.append(self.snapshot(command))
  helper=self.get(self.tokens['state']+0x18)
  assert helper==ALLOC and self.get(self.tokens['state']+0x1c)==5
  child=self.get(helper+0x408)
  r=self.m.call(0x4746f0,ecx=helper,arguments=(1,));assert r.completed and r.eax==helper,r
  self.put(self.tokens['state']+0x18,0);phases.append(self.snapshot('retire'))
  child_state=self.get(child+0x6c);child_helper=self.get(child_state+0x18)
  r=self.m.call(0x484d90,ecx=child_helper,arguments=(1,));assert r.completed and r.eax==child_helper,r
  for offset in (0x70,0x78):
   token=self.get(child+offset);r=self.m.call(0x4c80c0,ecx=token,arguments=(1,));assert r.completed;self.put(child+offset,0)
  self.put(child_state+0x18,0);phases.append(self.snapshot('child-retire'))
  self.put(self.tokens['state']+0x1c,0);r=self.m.call(0x474330,arguments=(self.tokens['owner'],));assert r.completed,r
  phases.append(self.snapshot('recreate'))
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,incoming=self.incoming,continuations=self.continuations,platform_next=self.initial_next,phases=phases)
def prepare(out):
 rows=[Reference(status,live,mirrored,fractional).run(f'sw-{status:x}-live-{int(live)}-mirror-{int(mirrored)}-fractional-{int(fractional)}') for status,live,mirrored,fractional in ((0,False,False,False),(0x21,False,True,True),(0x21,True,False,True),(0x4500,True,True,False))]
 metadata=[];r=Reference()
 assert r.read(0x4c9d7d,3)==b"\xc2\x10\x00"
 child_slots={off:r.get(0x50dfd4+off) for off in (0,4,8,12,16,28,32)}
 assert child_slots=={0:0x484d90,4:0x4c9e30,8:0x449590,12:0x4041b0,16:0x4c96b0,28:0x4c96b0,32:0x4c96b0}
 slots={off:r.get(0x50eee4+off) for off in (0,4,8,12,16,28,32)}
 assert slots=={0:0x4746f0,4:0x404fc0,8:0x4747e0,12:0x4063b0,16:0x474bc0,28:0x4c96b0,32:0x43e9b0}
 for pc,target,continuation in ((0x484d93,0x456030,0x484d98),(0x4c80c3,0x4c80e0,0x4c80c8),(0x4c9d76,0x4c7df0,0x4c9d7b),(0x4c8ded,0x4c8be0,0x4c8df2),(0x474496,0x4a30e0,0x47449b),(0x474368,0x4f63ec,0x47436d),(0x474383,0x4743f0,0x474388),(0x474414,0x4332f0,0x474419),(0x4493f5,0x4f63ec,0x4493fa),(0x449410,0x449480,0x449415),(0x4494a2,0x414030,0x4494a7),(0x474c1c,0x4c8da0,0x474c21)):
  code=r.read(pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target and continuation==pc+5
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=rows,call_metadata=metadata,child_vtable=dict(address=0x50dfd4,slots=child_slots),vtable=dict(address=0x50eee4,slots=slots,locator=r.get(0x50eee0),descriptor=r.get(r.get(0x50eee0)+12))),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 # These original bodies are inlined within the admitted callbacks. Their
 # CALL sites remain hash-checked below; dependent observations and all bytes compare.
 selected=set(OBSERVE)-{0x4f6286,0x43dfa0,0x4dca10,0x4743f0,0x474bc0,0x449480,0x4c8be0,0x4c7df0,0x456030,0x4c80e0}
 for e,a in zip(ref['profiles'],native['profiles']):
  if e['label']!=a['label'] or not a['allocation_witness']:fail.append('profile or allocation witness')
  if [r[1] for r in e['continuations'] if r[0]==0x4f63ec]!=a.get('allocation_continuations'):fail.append(dict(label=e['label'],field='all allocation CALL continuations'))
  if len(e['phases'])!=8 or len(a['phases'])!=8:fail.append('phase count')
  for ep,ap in zip(e['phases'],a['phases']):
   for key in ('command','helper','outgoing','events','final','retired'):
    if ep[key]!=ap[key]:fail.append(dict(label=e['label'],command=ep['command'],field=key))
   expected=cut.normalize_calls([r for r in ep['entries'] if r[0] in selected]);actual=cut.normalize_calls([r for r in ap['calls'] if r[0] in selected])
   if expected!=actual:fail.append(dict(label=e['label'],command=ep['command'],field='ordered calls',first_difference=next(((x,y) for x,y in zip(expected,actual) if x!=y),None),counts=[len(expected),len(actual)]))
   def member_records(rows):return cut.normalize_calls([[v['function'],v['receiver'],[v['eax'],v['return_pc'],v['stack_delta'],int(v['preserved'])]] for v in rows])
   if member_records(ep['member_source'])!=member_records(ap.get('member_source',[])):fail.append(dict(label=e['label'],command=ep['command'],field='member source CALL/RET'))
   if not ap['completed'] or ap.get('fault')!='none':fail.append(dict(label=e['label'],command=ep['command'],fault=ap['fault']))
   if [x['state'] for x in ep['exact']]!=[x['state'] for x in ap['exact']]:fail.append(dict(label=e['label'],command=ep['command'],field='inherited exact x87'))
 required={'provider required','foreign provider rejected','wrong callback rejected','wrong actor state rejected','missing registry fails','missing rectangle fails','allocation exhaustion preserved','occupied allocation preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','owner routed release','fresh allocation after release','retirement recreation rejects stale helper','double retirement rejected','shared scene cursor advanced by exact extent','allocation lease expires','allocation owner retained','foreign provider on same host rejected','foreign helper allocation rejected'}
 required.add('missing RTTI readability rejected');required.add('consumer callback API')
 required.update({'state identity replacement rejected','parent child link replacement rejected','child survives parent retirement','same-owner independent child retirement','double child retirement rejected','foreign child retirement provider rejected'})
 required.update(f'child {mode} identity replacement rejected' for mode in ('actor','state','private'))
 required.update(f'live parent {mode} physical retirement rejected' for mode in ('actor','state','private'))
 required.update(f'linked child {mode} physical retirement rejected' for mode in ('actor','state','private'))
 required.update(f'parent vtable slot {offset} replacement rejected' for offset in (0,4,8,12,16,28,32,36))
 required.update(f'child vtable slot {offset} replacement rejected' for offset in (0,4,8,12,16,28,32))
 required.update(f'wrong request {field} rejected' for field in ('root','size'))
 required.update(f'missing child resource {name} rejected' for name in ('LEVEL_CANNON','LEVEL_CANNON_FIRING'))
 required.update(f'child allocation {nth} exhaustion rejected' for nth in range(4,9))
 required.update(f'direct destructor {target:x} bypass rejected' for target in (0x4746f0,0x474710,0x484d90,0x456030))
 required.update('direct retirement '+mode+' rejected' for mode in ('wrong actor','foreign provider','replaced helper','foreign helper'))
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append(dict(field='required controls',missing=sorted(required-set(names))))
 fail += [dict(control=c['name']) for c in controls if not c['passed']]
 unresolved=sum(profile.get('unresolved_calls',1) for profile in native['profiles'])
 faults=sum(phase.get('fault')!='none' for profile in native['profiles'] for phase in profile['phases'])
 captured=json.loads((out/'swift-inputs.json').read_text())
 current=all(hashlib.sha256((ROOT/'Sources'/name).read_bytes()).hexdigest()==digest for name,digest in captured.items())
 if unresolved:fail.append('unresolved dependency')
 if not current:fail.append('shared source inputs changed during check')
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),phases=sum(len(p['phases']) for p in native['profiles']),controls=len(controls),faults=faults,unresolved_dependencies=unresolved,source_inputs_current=current,failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
