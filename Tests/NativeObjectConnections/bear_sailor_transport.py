"""Finite original-backed BearSailor constructor transport; evidence stays local."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import random
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.kernel import Machine,STACK_BASE,STACK_SIZE
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
BASE,SIZE,ALLOC=0x10000000,0x10000,0x61000000
OBSERVE=(0x409920,0x44c000,0x44bc60,0x4dca10,0x403b40,0x405000,0x4f63ec,0x4c7fa0,0x4c8060,0x4c7970,0x4062e0,0x4061b0,0x40a440,0x40a490,0x409ee0,0x409f70,0x40a040,0x44d000,0x44d3c0,0x43dfa0,0x4dc870,0x44cfd0,0x43e9b0,0x4c96b0,0x4c8160,0x4c81b0,0x4f6428,0x4c8220,0x4f6286,0x4f6439,0x4dc180,0x4db620,0x4dbe10,0x4dbd60,0x4dbcd0,0x420fc0,0x4dbd20)
spec=importlib.util.spec_from_file_location('bear_sailor_cases',ROOT/'Tests/families/bear_sailor.cases.py')
cases=importlib.util.module_from_spec(spec);spec.loader.exec_module(cases)
class Reference:
 def __init__(self,status=0,live=False,control=0x23f):
  self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
  self.next=BASE;self.next_alloc=ALLOC;self.allocations=[];self.entries=[];self.events=[];self.continuations=[];self.released=set()
  self.tokens=list(cases.cases(random.Random(1234)))[8].setup(self)
  self.put(self.tokens['state']+0x10,0x409860);self.put(0x510020,0xffffffff)
  hit=self.object(0x20,fill=0);attack=self.object(0x20,fill=0)
  self.put(hit+0x10,0x4dc830);self.put(attack+0x10,0x4dc850)
  registry=cases.world.__globals__['resource_manager'](self,{'LogicHit':hit,'LogicAttack':attack},1,'secondary registry')
  self.put(self.tokens['world']+0x14,registry)
  home=cases.cstring(self,b'LS_HOME');names=self.object(4,words=[home]);self.put(0x5376a0,17,17,names,names,4)
  row=self.object(4,words=[0x40a490]);self.put(0x534980,17,17,row,row,4)
  self.put(0x541334,1);self.put(0x534eac,0x26b7);self.put(0x537210,0);self.put(0x5430c4,0)
  self.put(0x537e88,self.tokens['owner'])
  actor=self.tokens['owner'];self.put(actor+8,0);self.put(actor+0x40,0);self.put(actor+0x4c,200,300);self.put(actor+0xcc,7)
  self.put(actor+0xdc,16,16)
  plane=self.object(0xa0,fill=0);tiles=self.object(4,words=[0xffffffff]);rows=self.object(4,words=[0])
  self.put(self.tokens['collision']+0x5c,plane);self.put(plane+0x20,tiles,rows)
  self.put(plane+0x30,4096,4096);self.put(plane+0x8c,12,12)
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
 def stub(self,*_):raise RuntimeError('unexpected executable stub')
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
  receiver=m.register(UC_X86_REG_ECX) if a not in (0x4f63ec,0x4dc870,0x4f6428) else 0
  arity={0x4c8220:1,0x4db620:1,0x4dbe10:2,0x4dbd60:1,0x420fc0:1,0x4dbd20:1,0x403b40:2,0x409920:1,0x44c000:1,0x44bc60:1,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4c8160:2,0x4dc870:1,0x409ee0:1,0x44d000:1,0x40a040:1,0x44d3c0:1,0x4f6428:1,0x4f6286:2}.get(a,0)
  args=m.words(m.register(UC_X86_REG_ESP)+4,arity)
  self.entries.append([a,receiver,list(args)])
  if a in (0x4f63ec,0x409920,0x44c000):self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i)
  if a==0x4a48e0:
   n=arg(0);token=self.next_alloc;self.next_alloc=(token+n+15)&~15
   self.write(token,bytes([204])*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
  elif a==0x4a49b0:self.events.append(['free',arg(0)]);self.released.add(arg(0));m.return_from_external(0,0)
  elif a==0x4a3050:self.events.append(['rand',99]);m.return_from_external(99,0)
  else:
   slot=next((k for k,v in m.import_stub.items() if v==a),a)
   if slot==0x546d5c:
    values=[arg(i) for i in range(1,5)];self.put(arg(0),*values);self.events.append(['rectangle',arg(0),*values]);m.return_from_external(1,20)
   elif slot==0x546cdc:self.put(arg(0),0,0,0,0);self.events.append(['empty-rectangle',arg(0)]);m.return_from_external(1,4)
   elif slot==0x5469e8:
    value=(self.get(arg(0))-1)&0xffffffff;self.put(arg(0),value);m.return_from_external(value,4)
   else:raise RuntimeError(('unexpected service',hex(a),hex(slot)))
 def snapshot(self):
  spans=[(BASE,SIZE),(0x534978,0x28),(0x537698,0x28),(0x537668,0x20),(0x510020,4)]+self.allocations
  return [dict(address=a,data='released' if a in self.released else self.read(a,n).hex()) for a,n in spans]
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming)
  stages=[];helper=ALLOC
  plan=[dict(label='construct',command=0),dict(label='park',command=1000),dict(label='detach',command=29),dict(label='no-op',command=30),dict(label='home',command=17,writes=[[helper+0x498,1]]),dict(label='delete',retire=True),dict(label='recreate',command=0)]
  for stage in plan:
   for a,v in stage.get('writes',[]):self.put(a,v)
   if stage.get('retire'):
    r=self.m.call(0x409ee0,ecx=self.get(self.tokens['state']+0x18),arguments=(1,))
    self.put(self.tokens['state']+0x18,0)
   else:
    self.put(self.tokens['state']+0x1c,stage['command'])
    r=self.m.call(0x409860,arguments=(self.tokens['owner'],))
   if not r.completed:raise RuntimeError((stage['label'],r,hex(self.m.register(UC_X86_REG_EIP))))
   stage.update(outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),final=self.snapshot());stages.append(stage)
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,continuations=self.continuations,incoming=self.incoming,allocations=self.allocations,stages=stages)
def prepare(out):
 rows=[Reference(status,live).run(f'sw-{status:x}-live-{int(live)}') for status,live in ((0,False),(0x20,False),(0x20,True))]
 metadata=[];m=Machine(claw(),BASE,SIZE)
 for pc,target,continuation in ((0x409898,0x4f63ec,0x40989d),(0x4098b3,0x409920,0x4098b8),(0x4098ec,0x4dc870,0x4098f1),(0x409945,0x44c000,0x40994a)):
  code=m.read(pc,5);assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 for pc,continuation in ((0x4098ca,0x4098cd),(0x4098d7,0x4098da),(0x4098fb,0x4098fe)):
  assert m.read(pc,1)==b'\xff';metadata.append(dict(call=pc,continuation=continuation))
 for pc,code,continuation,slot in ((0x40a107,b'\xff\x16',0x40a109,dict(base_register='esi',displacement=0)),(0x4dc943,b'\xff\x52\x08',0x4dc946,dict(base_register='edx',displacement=8))):
  assert m.read(pc,len(code))==code and pc+len(code)==continuation
  metadata.append(dict(call=pc,continuation=continuation,opcode='indirect-memory-call',length=len(code),slot=slot))
 for profile in rows:
  continuations=profile['continuations']
  assert [row for row in continuations if row[0]==0x409920]==[[0x409920,0x4098b8]]*2
  assert [row for row in continuations if row[0]==0x44c000]==[[0x44c000,0x40994a]]*2
  # Secondary LogicHit/LogicAttack new calls keep their own original sites.
  assert [row for row in continuations if row==[0x4f63ec,0x40989d]]==[[0x4f63ec,0x40989d]]*2
 vtable=[]
 for offset,target in ((0,0x409ee0),(4,0x44d000),(8,0x40a040),(12,0x44d3c0),(16,0x405000),(28,0x4c96b0),(32,0x44cfd0),(36,0x43dfa0)):
  assert m.words(0x50b38c+offset,1)[0]==target;vtable.append(dict(offset=offset,target=target))
 assert m.words(0x40a2a8,1)[0]==0x40a490
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,call_metadata=metadata,vtable=vtable,state_registration=dict(store=0x40a2a6,target=0x40a490,name='LS_HOME'),profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
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
def source_visible_calls(rows):
 # motion(43dfa0) directly embeds integrate(4dca10) in its canonical owner.
 # Remove only that verified original nested entry, retaining constructor and
 # all other independently dispatched integrate observations.
 result=[]
 for i,row in enumerate(rows):
  if row[0]==0x4dca10 and i>0 and i+1<len(rows):
   parent,child=rows[i-1],rows[i+1]
   if parent==[0x43dfa0,row[1],[]] and child[0]==0x403b40 and child[1]==row[1]+0x28:
    continue
  result.append(row)
 return result
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=3 or len(native['profiles'])!=len(ref['profiles']):fail.append('profile count')
 if [p['label'] for p in native['profiles']] != [p['label'] for p in ref['profiles']]:fail.append('profile labels')
 required_controls={'provider required','wrong callback rejected','missing registry fails','allocation exhaustion preserved','stale live helper rejected','owner routed release','fresh allocation after release','unsupported x87 CW rejected'}
 names=[c['name'] for c in native['controls']]
 if not required_controls.issubset(names) or len(names)!=len(set(names)):fail.append('required controls missing or duplicated')
 # Embedded base, destructor and operator delete bodies preserve their physical
 # dependencies and bytes; native ordinary dispatch need not emit their inlining.
 selected=tuple(a for a in OBSERVE if a not in (0x44bc60,0x409f70,0x4f6286,0x4f6428))
 for e,a in zip(ref['profiles'],native['profiles']):
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  if not a['allocation_witness']:fail.append(dict(label=e['label'],field='original allocation continuation'))
  if len(e['stages'])!=len(a['stages']):fail.append(dict(label=e['label'],field='stage count'))
  if not {0x44bc60,0x40a440,0x40a490,0x40a040,0x43dfa0,0x409ee0}.issubset({row[0] for row in e['stages'][-1]['entries']}):fail.append('original constructor/lifecycle/retirement witness')
  for es,ns in zip(e['stages'],a['stages']):
   for f in ('label','outgoing','events','final'):
    if es[f]!=ns[f]:fail.append(dict(label=e['label'],stage=es['label'],field=f))
   if not ns['completed']:fail.append(dict(label=e['label'],stage=es['label'],fault=ns['fault']))
   required=normalize_calls([r for r in source_visible_calls(es['entries']) if r[0] in selected]);found=normalize_calls([r for r in ns['calls'] if r[0] in selected])
   if required!=found:fail.append(dict(label=e['label'],stage=es['label'],field='ordered calls',expected_count=len(required),actual_count=len(found),first_difference=next(((x,y) for x,y in zip(required,found) if x!=y),None)))
 for c in native['controls']:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),stages=sum(len(p['stages']) for p in ref['profiles']),controls=len(native['controls']),failures=fail)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
