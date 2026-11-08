"""Finite original-backed RobberThief constructor transport; evidence stays local."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.kernel import Machine,STACK_BASE,STACK_SIZE
from Tests.clawparity.program import claw
from clawparity.world import resource_manager
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EBP,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBX,UC_X86_REG_EFLAGS
BASE,SIZE,ALLOC=0x10000000,0x10000,0x61000000
OBSERVE=(0x485330,0x44c000,0x44bc60,0x4dca10,0x403b40,0x405000,0x4f63ec,0x4c7fa0,0x4c8060,0x4c7970,0x4062e0,0x4061b0,0x485d60,0x4c8220,0x4f6286,0x4f6439,0x4dc180,0x4db620,0x4dbe10,0x4dbd60,0x4dbcd0,0x420fc0,0x4dbd20,0x44f1b0,0x40f6c0,0x40ab80,0x40abf0,0x4c81b0,0x4c8160,0x4a30e0)
LIFECYCLE=(0x4dc870,0x44d000,0x485960,0x44c840,0x44f290,0x44f840,0x4c82a0,0x44d3c0,0x43e420,0x43dfa0,0x44cfd0,0x4c96b0,0x43e9b0,0x485870,0x4f6584,0x4f6428,0x4c80c0,0x4c80e0,0x4f6974)
OBSERVE+=LIFECYCLE
spec=importlib.util.spec_from_file_location('robber_thief_cases',ROOT/'Tests/families/robber_thief.cases.py')
cases=importlib.util.module_from_spec(spec);spec.loader.exec_module(cases)
class Reference:
 def __init__(self,status=0,live=False,control=0x23f,lifecycle=False):
  self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
  self.next=BASE;self.next_alloc=ALLOC;self.allocations=[];self.entries=[];self.events=[];self.continuations=[];self.lifecycle=lifecycle;self.retirement_bytes=None;self.freed=[]
  values=[99,37,64,48,1,-31,77,0,3]
  self.tokens=cases.constructor('hit',values)(self)
  logic={name:self.object(20,name,words=[key,index,2,0,callback]) for name,key,index,callback in [('LogicHit',0x522d54,21,0x4dc830),('LogicAttack',0x522d48,22,0x4dc850)]}
  manager=resource_manager(self,logic,1,'constructor-logic')
  self.put(self.tokens['world']+0x14,manager)
  self.put(self.tokens['state']+0x10,0x485270);self.put(0x510020,0xffffffff)
  if lifecycle:
   # A finite projection of the actual registered LS_IDLE row. The original
   # image's registration and dispatch instructions are checked in prepare.
   self.put(self.tokens['idle_registry']+16,2000)
   name=self.object(20,'idle-cstring',words=[0xffffffff,7,7],data=None);self.write(name+12,b'LS_IDLE\0')
   for table,vtable,target in ((0x537698,0x50dbf4,name+12),(0x537878,0x50b0ac,0x44f290),(0x53c238,0x50b0ac,0)):
    row=self.object(4,'idle-row',words=[target]);self.put(table,vtable,0x544b50,2000,2000,row,1,4,row,0)
   self.put(self.tokens['owner']+0x18c,self.tokens['owner'])
   player=self.object(0x1b4,'physical-player');self.put(player+0x4c,120,77);self.put(0x537e88,player)
   self.put(0x532c0c,0);self.put(0x534eac,0x26b7);self.put(0x541334,1);self.put(self.tokens['owner']+0xcc,7);self.put(0x5430c4,17);self.put(0x537210,100)
  self.incoming=[control,status | (3<<11 if live else 0),[[0xc000000000000000,0x3fff]] if live else []]
  self.blocks=[(BASE,SIZE),(0x50a000,claw().base+claw().size-0x50a000)]
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
  for a in OBSERVE:self.m.observe(a,self.entry)
  for a in (0x4a48e0,0x4a49b0,0x4a3050):self.m.intercept(a)
  self.m.on_external=self.external
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
 def entry(self,m,a):
  receiver=m.register(UC_X86_REG_ECX) if a not in (0x4f63ec,0x4a30e0,0x4dc870,0x4f6428) else 0
  arity={0x40f6c0:4,0x40ab80:4,0x4c8160:2,0x4c8220:1,0x4db620:1,0x4dbe10:2,0x4dbd60:1,0x420fc0:1,0x4dbd20:1,0x403b40:2,0x4dc870:1,0x44d000:1,0x485960:1,0x44c840:1,0x44d3c0:1,0x485870:1,0x4c80c0:1,0x4f6428:1,0x4f6974:1,0x4c82a0:1,0x485330:1,0x44c000:1,0x44bc60:1,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4f6286:2}.get(a,0)
  args=m.words(m.register(UC_X86_REG_ESP)+4,arity)
  self.entries.append([a,receiver,list(args)])
  if a in (0x4f63ec,0x485330):self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x4f6428 and args[0]==self.get(self.tokens['state']+0x18):self.retirement_bytes=self.read(args[0],0x478).hex()
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i)
  if a==0x4a48e0:
   n=arg(0);token=self.next_alloc;self.next_alloc=(token+n+15)&~15
   self.write(token,bytes([204])*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
  elif a==0x4a49b0:
   token=arg(0);assert token not in self.freed;self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  elif a==0x4a3050:self.events.append(['rand',99]);m.return_from_external(99,0)
  else:
   slot=next((k for k,v in m.import_stub.items() if v==a),a)
   if slot==0x546d5c:
    values=[arg(i) for i in range(1,5)];self.put(arg(0),*values);self.events.append(['rectangle',arg(0),*values]);m.return_from_external(1,20)
   elif slot==0x546cdc:self.put(arg(0),0,0,0,0);self.events.append(['empty-rectangle',arg(0)]);m.return_from_external(1,4)
   elif slot==0x5469e8:
    value=(self.get(arg(0))-1)&0xffffffff;self.put(arg(0),value);m.return_from_external(value,4)
   else:raise RuntimeError(('unexpected service',hex(a),hex(slot)))
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming)
  steps=[]
  for command in ([0,1000,29,30,2000] if self.lifecycle else [0]):
   self.put(self.tokens['state']+0x1c,command)
   if command==2000:
    self.put(self.tokens['owner']+0xcc,7);self.put(self.tokens['owner']+8,self.get(self.tokens['owner']+8)|0x10)
   start=(len(self.events),len(self.entries))
   try:r=self.m.call(0x485270,arguments=(self.tokens['owner'],))
   except Exception as exc:raise RuntimeError((label,command,self.entries[-12:])) from exc
   if not r.completed:raise RuntimeError((label,command,r))
   spans=self.blocks+self.allocations
   steps.append(dict(command=command,outgoing=self.m.x87_state(),events=self.events[start[0]:],calls=self.entries[start[1]:],final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans]))
  retirement=None;members=[]
  if self.lifecycle:
   helper=self.get(self.tokens['state']+0x18);hit=self.get(self.tokens['owner']+0x70);attack=self.get(self.tokens['owner']+0x78)
   # Physical owned members are live retirement inputs, not game stand-ins.
   for data in (struct.pack('<III',1,3,3)+b'one\0',struct.pack('<III',1,3,3)+b'two\0',struct.pack('<II',0x12ab34cd,0x55aa55aa)):
    token=self.next_alloc;self.next_alloc=(token+len(data)+15)&~15;self.write(token,data);members.append(dict(address=token,data=data.hex()))
   self.put(helper+0x1a4,members[0]['address']+12);self.put(helper+0x1a8,members[1]['address']+12)
   self.put(helper+0x2fc,64,members[2]['address'])
   start=(len(self.events),len(self.entries))
   for function,receiver,arguments in ((0x485870,helper,(1,)),(0x4c80c0,hit,(1,)),(0x4c80c0,attack,(1,))):
    r=self.m.call(function,ecx=receiver,arguments=arguments)
    if not r.completed:raise RuntimeError(('retirement',r))
   sizes=dict(self.allocations);sizes.update((b['address'],len(b['data'])//2) for b in members)
   retirement=dict(helper=helper,bytes=self.retirement_bytes,freedBytes=[dict(address=a,data=self.read(a,sizes[a]).hex()) for a in self.freed],events=self.events[start[0]:],calls=self.entries[start[1]:],freed=self.freed)
  return dict(label=label,lifecycle=self.lifecycle,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,continuations=self.continuations,incoming=self.incoming,outgoing=steps[-1]['outgoing'],allocations=self.allocations,events=steps[0]['events'] if not self.lifecycle else self.events,entries=steps[0]['calls'] if not self.lifecycle else self.entries,final=steps[-1]['final'],steps=steps,retirement=retirement,members=members)

def prepare(out):
 rows=[Reference(status,live,control).run(f'cw-{control:x}-sw-{status:x}-live-{int(live)}') for status,live,control in ((0,False,0x23f),(0x20,False,0x23f),(0x21,False,0x23f),(0x20,True,0x23f),(0x4500,True,0x23f),(0x21,True,0x23f))]
 for row in list(rows):
  scene=dict(row);scene['scene']=True;scene['label']+='-scene';rows.append(scene)
 for status,live,control in ((0,False,0x23f),(0x20,False,0x23f),(0x21,False,0x23f),(0x20,True,0x23f),(0x4500,True,0x23f),(0x21,True,0x23f)):
  row=Reference(status,live,control,True).run(f'lifecycle-cw-{control:x}-sw-{status:x}-live-{int(live)}');row['scene']=True;rows.append(row)
 metadata=[]
 m=Machine(claw(),BASE,SIZE)
 for pc,target,continuation in ((0x4852a8,0x4f63ec,0x4852ad),(0x4852c3,0x485330,0x4852c8),(0x4dc1a2,0x4db620,0x4dc1a7),(0x4dbe37,0x4db620,0x4dbe3c),(0x485355,0x44c000,0x48535a),(0x485a65,0x44c840,0x485a6a)):
  code=m.read(pc,5)
  assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 assert m.read(0x44cda9,5)==b'\x68'+struct.pack('<I',0x523148)
 assert m.read(0x44cdd0,6)==b'\xc7\x00'+struct.pack('<I',0x44f290)
 for row in rows:
  assert row['continuations']==[[0x4f63ec,0x4852ad],[0x485330,0x4852c8],[0x4f63ec,0x4c7f4f],[0x4f63ec,0x4c800f]]
  assert [n for _,n in row['allocations']]==[0x478,0x174,0x174]
  assert all(any(e[0]=='lookup' and e[2]==name and e[3] for e in row['events']) for name in ('LogicHit','LogicAttack','LEVEL_ROBBERTHIEF','LEVEL_ROBBERTHIEF_FASTADVANCE'))
 for offset,target in ((0,0x485870),(4,0x44d000),(8,0x485960),(12,0x44d3c0),(16,0x405000),(28,0x4c96b0),(32,0x44cfd0),(0x48,0x485d60)):
  assert m.words(0x50f49c+offset,1)[0]==target
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,call_metadata=metadata,profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
def normalize_calls(rows):
 # Ordinary native frames reserve bounded scratch space independently of the
 # original register allocator. Keep each local's identity across calls.
 locals={}
 def token(value):
  if STACK_BASE<=value<STACK_BASE+STACK_SIZE:
   if value not in locals:locals[value]=f'stack-local-{len(locals)}'
   return locals[value]
  return value
 return [[function,token(receiver),[token(v) for v in args]] for function,receiver,args in rows]
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=18 or len(native['profiles'])!=len(ref['profiles']):fail.append('profile count')
 if [p['label'] for p in native['profiles']] != [p['label'] for p in ref['profiles']]:fail.append('profile labels')
 required_controls={'provider required','wrong callback rejected','missing registry fails','allocation exhaustion preserved','stale live helper rejected','owner routed release','fresh allocation after release','unsupported x87 CW rejected','scene heap helper allocation retained','scene owner routed release','scene owner routed reallocation','foreign existing helper rejected before allocation','cross-owner or malformed cut-size rejected','cross-owner or malformed cut-constructor rejected','cross-owner or malformed cut-vtable rejected','cross-owner or malformed base-x87 rejected'}
 required_controls |= {'lifecycle source eax rejected','lifecycle source frame rejected','lifecycle source continuation rejected','lifecycle x87 rejected','retirement rejects foreign provider','retirement cstring-link substitution rejected','retirement bitset-link substitution rejected','retirement provider-reentry substitution rejected','persistent helper raw free rejected','persistent helper raw resize rejected','wrong vtable slot 72 rejected before allocation'}
 names=[c['name'] for c in native['controls']]
 if not required_controls.issubset(names) or len(names)!=len(set(names)):fail.append('required controls missing or duplicated')
 for e,a in zip(ref['profiles'],native['profiles']):
  for f in (('label','outgoing','final') if e['lifecycle'] else ('label','outgoing','events','final')):
   if e[f]!=a[f]:fail.append(dict(label=e['label'],field=f))
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  if not a['allocation_witness']:fail.append(dict(label=e['label'],field='original allocation continuation'))
  # Canonical44c000 embeds44bc60 and485330 embeds485d60; motion43dfa0
  # embeds4dca10, and secondary4c80c0 embeds4c80e0. Their physical
  # descendants, full bytes and release order remain independently compared.
  if not {0x44bc60,0x485d60}.issubset({row[0] for row in e['entries']}):fail.append('original inherited/idle witness')
  if e['lifecycle']:
   for expected,actual in zip(e['steps'],a['steps']):
    for f in ('command','outgoing','events','final'):
     if expected[f]!=actual[f]:fail.append(dict(label=e['label'],command=expected['command'],field=f))
   if len(a['steps'])!=5:fail.append(dict(label=e['label'],field='lifecycle completion'))
   if any(e['retirement'][key]!=a['retirement'].get(key) for key in ('bytes','freed','freedBytes')):fail.append(dict(label=e['label'],field='scalar and secondary retirement'))
  selected=tuple(a for a in OBSERVE if a not in (0x44bc60,0x485d60,0x4f6286,0x4dca10,0x4c80e0) and not (e["lifecycle"] and a==0x4f6428))
  required=normalize_calls([r for r in e['entries'] if r[0] in selected]);found=normalize_calls([r for r in a['calls'] if r[0] in selected])
  if required!=found:fail.append(dict(label=e['label'],field='ordered calls',expected_count=len(required),actual_count=len(found),first_difference=next(((x,y) for x,y in zip(required,found) if x!=y),None)))
 for c in native['controls']:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),controls=len(native['controls']),failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
