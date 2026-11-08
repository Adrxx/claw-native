"""Finite original-backed CutThroat constructor transport; evidence stays local."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.kernel import Machine,STACK_BASE,STACK_SIZE
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
BASE,SIZE,ALLOC=0x10000000,0x10000,0x61000000
OBSERVE=(0x437a90,0x44c000,0x44bc60,0x4dca10,0x403b40,0x405000,0x4f63ec,0x4c7fa0,0x4c8060,0x4c7970,0x4062e0,0x4061b0,0x4384f0,0x4c8220,0x4f6286,0x4f6439,0x4dc180,0x4db620,0x4dbe10,0x4dbd60,0x4dbcd0,0x420fc0,0x4dbd20)
spec=importlib.util.spec_from_file_location('cut_throat_cases',ROOT/'Tests/families/cut_throat.cases.py')
cases=importlib.util.module_from_spec(spec);spec.loader.exec_module(cases)
class Reference:
 def __init__(self,status=0,live=False,control=0x23f):
  self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
  self.next=BASE;self.next_alloc=ALLOC;self.allocations=[];self.entries=[];self.events=[];self.continuations=[]
  values=[99,37,53,64,48,-31,77,0,3,-2,0,239,17,3]
  self.tokens=cases.construct('hit',values,False)(self)
  self.put(self.tokens['state']+0x10,0x4379d0);self.put(0x510020,0xffffffff)
  self.incoming=[control,status | (3<<11 if live else 0),[[0xc000000000000000,0x3fff]] if live else []]
  self.blocks=[(BASE,SIZE),(0x50a000,claw().base+claw().size-0x50a000)]
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
  for a in OBSERVE:self.m.observe(a,self.entry)
  for a in (0x4a48e0,0x4a3050):self.m.intercept(a)
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
  receiver=m.register(UC_X86_REG_ECX) if a!=0x4f63ec else 0
  arity={0x4c8220:1,0x4db620:1,0x4dbe10:2,0x4dbd60:1,0x420fc0:1,0x4dbd20:1,0x403b40:2,0x437a90:1,0x44c000:1,0x44bc60:1,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4f6286:2}.get(a,0)
  args=m.words(m.register(UC_X86_REG_ESP)+4,arity)
  self.entries.append([a,receiver,list(args)])
  if a in (0x4f63ec,0x437a90):self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i)
  if a==0x4a48e0:
   n=arg(0);token=self.next_alloc;self.next_alloc=(token+n+15)&~15
   self.write(token,bytes([204])*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
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
  r=self.m.call(0x4379d0,arguments=(self.tokens['owner'],))
  if not r.completed:raise RuntimeError(r)
  spans=[(self.tokens['owner'],0x200),(self.tokens['state'],0x180)]+self.allocations
  return dict(label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
def prepare(out):
 rows=[Reference(status,live,control).run(f'cw-{control:x}-sw-{status:x}-live-{int(live)}') for status,live,control in ((0,False,0x23f),(0x20,False,0x23f),(0x21,False,0x23f),(0x20,True,0x23f),(0x4500,True,0x23f),(0x21,True,0x23f))]
 metadata=[]
 m=Machine(claw(),BASE,SIZE)
 for pc,target,continuation in ((0x437a08,0x4f63ec,0x437a0d),(0x437a23,0x437a90,0x437a28),(0x4dc1a2,0x4db620,0x4dc1a7),(0x4dbe37,0x4db620,0x4dbe3c),(0x438581,0x4c8220,0x438586)):
  code=m.read(pc,5)
  assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 for row in rows:assert row['continuations']==[[0x4f63ec,0x437a0d],[0x437a90,0x437a28]]
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
 if len(ref['profiles'])!=6 or len(native['profiles'])!=len(ref['profiles']):fail.append('profile count')
 if [p['label'] for p in native['profiles']] != [p['label'] for p in ref['profiles']]:fail.append('profile labels')
 required_controls={'v1.0 callback profile selected','provider required','wrong callback rejected','missing registry fails','allocation exhaustion preserved','stale live helper rejected','owner routed release','fresh allocation after release','unsupported x87 CW rejected'}
 names=[c['name'] for c in native['controls']]
 if not required_controls.issubset(names) or len(names)!=len(set(names)):fail.append('required controls missing or duplicated')
 for e,a in zip(ref['profiles'],native['profiles']):
  for f in ('label','outgoing','events','final'):
   if e[f]!=a[f]:fail.append(dict(label=e['label'],field=f))
  if not a['completed']:fail.append(dict(label=e['label'],fault=a['fault']))
  if not a['allocation_witness']:fail.append(dict(label=e['label'],field='original allocation continuation'))
  # Canonical44c000 embeds44bc60, and437a90 embeds4384f0. Their
  # physical dependencies and final bytes remain compared in the full graph.
  if not {0x44bc60,0x4384f0}.issubset({row[0] for row in e['entries']}):fail.append('original inherited/idle witness')
  selected=tuple(a for a in OBSERVE if a not in (0x44bc60,0x4384f0,0x4f6286))
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
