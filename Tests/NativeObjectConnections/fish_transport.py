"""Finite original/native Fish shared-owner transport; no scene promotion."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.program import claw
from Tests.clawparity.world import idle_registry
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP
spec=importlib.util.spec_from_file_location('fish_transport_services',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(spec);spec.loader.exec_module(cut)
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE={a:0 for a in cut.OBSERVE if a not in (0x437a90,0x44c000,0x44bc60,0x4384f0)}
OBSERVE.update({0x4420e0:1,0x4332f0:1,0x4dca10:0,0x403b40:2,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4c8220:1,0x4f6286:2,0x4db620:1,0x4dbe10:2,0x4dbd60:1,0x420fc0:1,0x4dbd20:1,0x43e9b0:0,0x4c96b0:0,0x4dc870:1,0x404fc0:1,0x441d00:1,0x4a36f0:1,0x43d490:1,0x4063b0:1,0x43dfa0:0,0x4423e0:1,0x4f6428:1,0x4f6584:0})
class Reference(cut.Reference):
 def __init__(self,status=0,live=False):
  super().__init__(status,live)
  self.freed=[];self.exact=[];self.member_entries=[];self.member_source=[]
  self.put(self.tokens['state']+0x10,0x441be0)
  self.put(self.tokens['owner']+0x38,0xffffffff)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x5273e0,sprite)
  for key in (0x5273d0,0x5273bc,0x5273a8,0x527398,0x527384):self.bind('animations',key,animation)
  for key in (0x527370,0x527358,0x527344,0x527330,0x52731c):self.bind('sounds',key,self.object(0x20,fill=0))
  player=self.object(0x200,fill=0);player_state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,player_state);self.put(player_state+0x14,inputs);self.put(player+0x4c,100)
  idle_registry(self,5)
  text=self.text(0x523604).encode();name=self.object(13+len(text),data=struct.pack("<III",1,len(text),len(text))+text+b"\0")+12
  names=self.object(4,words=[name]);self.put(0x5376a0,5,5,names,names,4,0,0)
  # Fish state index 5 dispatches no extra behavior in this transport fixture;
  # the actual inherited fallback dispatcher remains real.
  callbacks=self.object(24,words=[0]*6)
  self.put(0x537700,0,5,callbacks,0,4)
  fallback=self.object(24,words=[0]*6)
  self.put(0x537640,0,5,fallback,0,4)
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  for a in (0x4f6428,):self.m.intercept(a)
  for a in (0x4332f0,0x404fc0,0x4063b0):self.m.observe(a,lambda m,a:self.exact.append(dict(function=a,state=m.x87_state())))
  for a in (0x4f6439,0x4db620):self.m.observe(a,self.member_entry)
  for a in (0x4334d3,0x4334e3,0x4dc1a7,0x4dbe3c):self.m.observe(a,self.member_return)
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
  receiver=0 if a in (0x4f63ec,0x4dc870,0x4f6428,0x4a36f0) else m.register(UC_X86_REG_ECX)
  args=list(m.words(m.register(UC_X86_REG_ESP)+4,OBSERVE[a]));self.entries.append([a,receiver,args])
  if a in (0x4f63ec,0x4420e0):self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a)
  if slot==0x546cd4:
   rectangle,x,y=m.words(m.register(UC_X86_REG_ESP)+4,3);left,top,right,bottom=struct.unpack("<iiii",self.read(rectangle,16));x,y=struct.unpack("<ii",struct.pack("<II",x,y));result=int(left<=x<right and top<=y<bottom);self.events.append(["contains",rectangle,x,y,result]);m.return_from_external(result,12)
  elif slot==0x546a40:
   pointer,size=m.words(m.register(UC_X86_REG_ESP)+4,2);self.read(pointer,size);self.events.append(["readable",pointer,size,0]);m.return_from_external(0,8)
  elif a==0x4f6428:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [a for a,n in self.allocations] and token not in self.freed
   self.freed.append(token);m.return_from_external(0,0)
  else:super().external(m,a)
 def snapshot(self,command):
  spans=[(BASE,SIZE)]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(command=command,helper=self.get(self.tokens['state']+0x18),outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),retired={str(a):self.read(a,n).hex() for a,n in self.allocations if a in self.freed},exact=list(self.exact),member_source=list(self.member_source),final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);phases=[]
  for command in (0,1000,29,30,5):
   self.put(self.tokens['state']+0x1c,command);r=self.m.call(0x441be0,arguments=(self.tokens['owner'],),timeout_seconds=5)
   assert r.completed,(command,r)
   phases.append(self.snapshot(command))
  helper=self.get(self.tokens['state']+0x18)
  assert helper==ALLOC and self.get(self.tokens['state']+0x1c)==5
  assert all(self.get(helper+off) for off in (0x12c,0x400,0x404,0x408,0x310,0x374,0x364,0x3a0,0x3a4,0x40c,0x410,0x414))
  r=self.m.call(0x4423e0,ecx=helper,arguments=(1,));assert r.completed and r.eax==helper,r
  self.put(self.tokens['state']+0x18,0);phases.append(self.snapshot('retire'))
  self.put(self.tokens['state']+0x1c,0);r=self.m.call(0x441be0,arguments=(self.tokens['owner'],));assert r.completed,r
  phases.append(self.snapshot('recreate'))
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,incoming=self.incoming,continuations=self.continuations,phases=phases)
def prepare(out):
 rows=[Reference(status,live).run(f'sw-{status:x}-live-{int(live)}') for status,live in ((0,False),(0x21,False),(0x21,True),(0x4500,True))]
 metadata=[];r=Reference()
 slots={off:r.get(0x50dc84+off) for off in (0,4,8,12,16,28,32)}
 assert slots=={0:0x4423e0,4:0x404fc0,8:0x441d00,12:0x4063b0,16:0x405000,28:0x4c96b0,32:0x43e9b0}
 for pc,target,continuation in ((0x441c18,0x4f63ec,0x441c1d),(0x441c33,0x4420e0,0x441c38),(0x442104,0x4332f0,0x442109)):
  code=r.read(pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target and continuation==pc+5
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=rows,call_metadata=metadata,vtable=dict(address=0x50dc84,slots=slots,locator=r.get(0x50dc80),descriptor=r.get(r.get(0x50dc80)+12))),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 selected=set(OBSERVE)-{0x4f6286,0x43dfa0,0x4dca10}
 for e,a in zip(ref['profiles'],native['profiles']):
  if e['label']!=a['label'] or not a['allocation_witness']:fail.append('profile or allocation witness')
  if len(e['phases'])!=7 or len(a['phases'])!=7:fail.append('phase count')
  for ep,ap in zip(e['phases'],a['phases']):
   for key in ('command','helper','outgoing','events','final','retired'):
    if ep[key]!=ap[key]:fail.append(dict(label=e['label'],command=ep['command'],field=key))
   expected=cut.normalize_calls([r for r in ep['entries'] if r[0] in selected]);actual=cut.normalize_calls([r for r in ap['calls'] if r[0] in selected])
   if expected!=actual:fail.append(dict(label=e['label'],command=ep['command'],field='ordered calls',first_difference=next(((x,y) for x,y in zip(expected,actual) if x!=y),None),counts=[len(expected),len(actual)]))
   def member_records(rows):return cut.normalize_calls([[v['function'],v['receiver'],[v['eax'],v['return_pc'],v['stack_delta'],int(v['preserved'])]] for v in rows])
   if member_records(ep['member_source'])!=member_records(ap.get('member_source',[])):fail.append(dict(label=e['label'],command=ep['command'],field='member source CALL/RET'))
   if not ap['completed']:fail.append(dict(label=e['label'],command=ep['command'],fault=ap['fault']))
   if [x['state'] for x in ep['exact']]!=[x['state'] for x in ap['exact']]:fail.append(dict(label=e['label'],command=ep['command'],field='inherited exact x87'))
 required={'provider required','foreign provider rejected','wrong callback rejected','wrong actor state rejected','missing registry fails','missing rectangle fails','allocation exhaustion preserved','occupied allocation preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','owner routed release','fresh allocation after release','retirement recreation rejects stale helper','double retirement rejected','shared scene cursor advanced by exact extent','allocation lease expires','allocation owner retained','foreign provider on same host rejected','foreign helper allocation rejected'}
 required.add('missing RTTI readability rejected')
 required.update('direct retirement '+mode+' rejected' for mode in ('wrong actor','foreign provider','replaced helper','foreign helper'))
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append(dict(field='required controls',missing=sorted(required-set(names))))
 fail += [dict(control=c['name']) for c in controls if not c['passed']]
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),controls=len(controls),failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
