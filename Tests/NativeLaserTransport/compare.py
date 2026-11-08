"""Laser's finite shared-owner join, executed against hash-checked original code."""
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.kernel import Machine,STACK_BASE,STACK_SIZE
from Tests.clawparity.program import claw
from Tests.clawparity.world import idle_registry
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
BASE,SIZE,ALLOC=0x10000000,0x10000,0x61000000
OBSERVE={0x455490:1,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4c8220:1,0x4c82a0:1,0x4f6286:2,0x4dba00:1,0x4c96b0:0,0x4dc870:1,0x4c9e30:1,0x455600:1,0x4041b0:1,0x4f6974:1,0x484d90:1,0x4f6428:1}
class Reference:
 def __init__(self,handler=0x455960,elapsed=0):
  self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
  self.next=BASE;self.next_alloc=ALLOC;self.allocations=[];self.entries=[];self.events=[];self.continuations=[]
  self.freed=[];self.handler=handler;self.elapsed=elapsed
  actor=self.object(0x200);state=self.object(0x180);world=self.object(0x50)
  managers={kind:self.object(0x30) for kind in ('sprites','logic','animations')}
  self.tokens=dict(owner=actor,state=state,world=world,managers=managers)
  self.put(actor+0xc,world);self.put(actor+0x6c,state);self.put(actor+0x18c,actor)
  self.put(state+0x10,0x4553d0);self.put(0x510020,0xffffffff)
  self.put(world+0x10,managers['sprites'],managers['logic']);self.put(world+0x2c,managers['animations'])
  for manager in managers.values():self.put(manager+0x18,1)
  frames=self.object(8,words=[self.object(0x28),self.object(0x28)])
  sprite=self.object(0x6c);self.put(sprite+0x14,frames);self.put(sprite+0x64,0,1)
  record=self.object(0x30);self.put(record+0xc,9);self.put(record+0x18,0 if elapsed==100 else 17)
  records=self.object(4,words=[record]);animation=self.object(0x14);self.put(animation+0xc,records,1)
  self.bind('sprites',0x528584,sprite);self.bind('animations',0x528570,animation)
  self.bind('logic',0x522d54,self.object(0x14,words=[0,0,0,0,0x4dc830]))
  self.bind('logic',0x522d48,self.object(0x14,words=[0,0,0,0,0x4dc850]))
  self.put(self.tokens['state']+0xb8,37);self.put(0x537210,0xfffffff0);self.put(0x5430c4,17)
  idle_registry(self,5)
  name=self.text(0x523148).encode();text=self.object(13+len(name),data=struct.pack('<III',1,len(name),len(name))+name+b'\0')+12
  names=self.object(4,words=[text]);self.put(0x5376a0,5,5,names,names,4,0,0)
  handlers=self.object(4,words=[handler]);self.put(0x5379d8,5,5,handlers,handlers,4,0,0)
  self.handler_entries=[]
  for a in OBSERVE:self.m.observe(a,self.entry)
  for a in (0x4558b0,0x455960):self.m.observe(a,lambda m,a:self.handler_entries.append(a))
  for a in (0x4f6428,0x4a48e0):self.m.intercept(a)
  self.m.on_external=self.external
  self.blocks=[(BASE,SIZE),(0x50a000,claw().base+claw().size-0x50a000)]
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def object(self,n,name='',fill=0,data=None,words=None):
  a=self.next;self.next=(a+n+15)&~15;assert self.next<BASE+SIZE
  self.write(a,bytes([fill])*n)
  if data is not None:self.write(a,data)
  if words is not None:self.put(a,*words)
  return a
 def override(self,*_):pass
 def put(self,a,*v):self.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
 def get(self,a):return self.m.words(a,1)[0]
 def read(self,a,n):return self.m.read(a,n)
 def write(self,a,d):self.m.write(a,d)
 def text(self,a):return self.read(a,256).split(b'\0')[0].decode('ascii')
 def lookup(self,receiver,key):
  buckets,count=self.get(receiver+4),self.get(receiver+8)
  for i in range(count if buckets else 0):
   node=self.get(buckets+4*i)
   while node:
    if self.text(self.get(node+8))==key:return self.get(node+12)
    node=self.get(node)
  return 0
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a not in OBSERVE:return
  args=list(m.words(m.register(UC_X86_REG_ESP)+4,OBSERVE[a]));receiver=0 if a in (0x4f63ec,0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
  self.entries.append([a,receiver,args])
  if a in (0x4f63ec,0x455490):self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  if a==0x4f6428:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [a for a,n in self.allocations] and token not in self.freed
   self.freed.append(token);m.return_from_external(0,0)
  elif a==0x4a48e0:
   n=self.get(m.register(UC_X86_REG_ESP)+4);token=self.next_alloc;self.next_alloc=(token+n+15)&~15
   self.write(token,bytes([204])*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
  else:raise RuntimeError(('unexpected physical service',hex(a)))
 def snapshot(self,command):
  spans=[(BASE,SIZE),(0x537210,4),(0x5430c4,4),(0x5379d0,0x24),(0x53769c,0x24)]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(command=command,helper=self.get(self.tokens['state']+0x18),events=list(self.events),entries=list(self.entries),retired={str(a):self.read(a,n).hex() for a,n in self.allocations if a in self.freed},final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
 def run(self,label):
  phases=[]
  for command in (0,1000,29,30,5):
   self.put(self.tokens['state']+0x1c,command)
   if command==5:self.put(0x537210,(0xfffffff0+self.elapsed)&0xffffffff)
   r=self.m.call(0x4553d0,arguments=(self.tokens['owner'],));assert r.completed,(command,r)
   if command==5:
    left=self.get(self.tokens['owner']+0x138)
    assert left==(0xffffffec if self.handler==0x455960 and self.elapsed==37 else 0x80000000)
    if self.handler==0x455960 and self.elapsed==100:assert self.get(ALLOC+0x50)==84
   phases.append(self.snapshot(command))
  helper=self.get(self.tokens['state']+0x18);r=self.m.call(0x484d90,ecx=helper,arguments=(1,));assert r.completed and r.eax==helper,r
  self.put(self.tokens['state']+0x18,0);phases.append(self.snapshot('retire'))
  self.put(self.tokens['state']+0x1c,0);r=self.m.call(0x4553d0,arguments=(self.tokens['owner'],));assert r.completed,r
  phases.append(self.snapshot('recreate'))
  assert self.handler in self.handler_entries and 0x4558b0 in self.handler_entries
  return dict(handler_entries=self.handler_entries,label=label,actor=self.tokens['owner'],state=self.tokens['state'],elapsed=self.elapsed,initial=self.initial,continuations=self.continuations,phases=phases)
def prepare(out):
 rows=[Reference(handler,elapsed).run(f'{handler:x}-{elapsed}') for handler,elapsed in ((0x4558b0,0),(0x455960,0),(0x455960,37),(0x455960,100))]
 r=Reference();slots={off:r.get(0x50e35c+off) for off in (0,4,8,12,16,28,32)}
 assert slots=={0:0x484d90,4:0x4c9e30,8:0x455600,12:0x4041b0,16:0x4c96b0,28:0x4c96b0,32:0x4c96b0}
 metadata=[]
 for pc,target in ((0x455405,0x4f63ec),(0x455420,0x455490)):
  code=r.read(pc,5);assert code[0]==0xe8 and pc+5+struct.unpack('<i',code[1:])[0]==target,(hex(pc),code.hex())
  metadata.append(dict(call=pc,target=target,continuation=pc+5))
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=rows,call_metadata=metadata,vtable=slots),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
def normalize_calls(rows):
 # Scratch frames have native reservations. Preserve output-cell aliasing and
 # service order, while comparing every non-stack token exactly.
 locals={}
 def token(value):
  if STACK_BASE<=value<STACK_BASE+STACK_SIZE:
   if value not in locals:locals[value]=f'stack-local-{len(locals)}'
   return locals[value]
  return value
 return [[function,token(receiver),[token(v) for v in args]] for function,receiver,args in rows]
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 for e,a in zip(ref['profiles'],native['profiles']):
  if e['label']!=a['label'] or not a['allocation_witness']:fail.append('profile/allocation witness')
  if len(e['phases'])!=7 or len(a['phases'])!=7:fail.append('phase count')
  for ep,ap in zip(e['phases'],a['phases']):
   for key in ('command','helper','events','final','retired'):
    if ep[key]!=ap[key]:fail.append(dict(label=e['label'],command=ep['command'],field=key))
   expected=normalize_calls([r for r in ep['entries'] if r[0]!=0x4f6286]);actual=normalize_calls([r for r in ap['calls'] if r[0] in OBSERVE and r[0]!=0x4f6286])
   if expected!=actual:fail.append(dict(label=e['label'],command=ep['command'],field='ordered calls',first_difference=next(((x,y) for x,y in zip(expected,actual) if x!=y),None),counts=[len(expected),len(actual)]))
   if not ap['completed']:fail.append(dict(label=e['label'],command=ep['command'],fault=ap['fault']))
 required={'provider required','foreign provider rejected','wrong callback rejected','wrong actor state rejected','missing registry fails','allocation exhaustion preserved','occupied allocation preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','owner routed release','fresh allocation after release','retirement recreation rejects stale helper','double retirement rejected','shared scene cursor advanced by exact extent','allocation lease expires','allocation owner retained','foreign provider on same host rejected','foreign helper allocation rejected'}
 required.update({'missing lifecycle string service rejected','unelected state table target rejected'})
 required.update('direct Laser entry '+str(a)+' rejected' for a in (0x455490,0x455600,0x4558b0,0x455960))
 required.update('direct retirement '+mode+' rejected' for mode in ('wrong actor','foreign provider','replaced helper','foreign helper'))
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append(dict(field='required controls',missing=sorted(required-set(names))))
 fail += [dict(control=c['name']) for c in controls if not c['passed']]
 result=dict(status='fail' if fail else 'pass',profiles=4,controls=len(controls),failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve();assert (ROOT/'work').resolve() in out.parents
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
