"""Original-backed finite AquatisStalactite provider transport comparison."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
spec=importlib.util.spec_from_file_location('stalactite_physical_world',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(spec);spec.loader.exec_module(cut)
ALLOC=cut.ALLOC
ARITIES={0x42a680:0,0x4f63ec:1,0x4078b0:1,0x4c96b0:0,0x4dc870:1,0x407c10:1,0x407500:1,0x4063b0:1,0x4dca10:0,0x4f6428:1,0x407bd0:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4c8220:1,0x4c82a0:1,0x4f6286:2,0x4f6974:1,0x4dba00:1,0x4082f0:1,0x4080a0:0,0x408220:22,0x4082d0:2,0x408370:1,0x406290:0,0x406240:0,0x408050:0}
# Internal state bodies are inlined by the admitted owner; observe canonical joins.
SELECTED=set(ARITIES)-{0x4082f0,0x4080a0,0x408220,0x4082d0,0x408370}
class Reference(cut.Reference):
 def __init__(self,status=0,live=False):
  super().__init__(status,live)
  self.entries=[];self.events=[];self.freed=[];self.exact=[]
  self.put(self.tokens['state']+0x10,0x4073e0)
  self.put(self.tokens['owner']+0x108,1)
  self.put(self.tokens['owner']+0x148,0,0)
  self.put(0x537210,1234);self.put(0x5430c4,16)
  collision=self.get(self.tokens['world']+0x24) if 'world' in self.tokens else self.get(self.get(self.tokens['owner']+0xc)+0x24)
  plane=self.object(0x100,fill=0);tiles=self.object(64*4,words=[0xffffffff]*64);rows=self.object(8*4,words=[i*8 for i in range(8)])
  self.put(collision+0x5c,plane);self.put(plane+0x20,tiles,rows);self.put(plane+0x30,512,512);self.put(plane+0x8c,6,6)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  sequence=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x523698,sprite)
  for key,callback in ((0x522d54,0x4dc830),(0x522d48,0x4dc850)):
   metadata=self.object(0x14,fill=0);self.put(metadata+0x10,callback);self.bind('logic',key,metadata)
  self.bind('animations',0x523680,sequence);self.bind('animations',0x523664,sequence)
  for key in (0x52364c,0x523634):
   record=self.object(0x14,fill=0);sound=self.object(0x14,fill=0);source=self.object(0x7c,fill=0)
   self.put(record+0x10,sound);self.put(sound+0x10,source);self.bind('sounds',key,record)
  self.put(0x532c0c,0);self.put(0x532c10,100)
  boss=self.object(0x500,fill=0);self.tokens['boss']=boss
  self.put(0x534874,boss);self.put(boss+0xc,0x12340000);self.put(0x5349dc,0x12340000)
  self.put(boss+0x4b0,100000);self.put(boss+0x4b8,1,0)
  self.put(0x53490c,0);self.put(0x5231f4,5);self.put(0x5231e0,1,2,4,8,16);self.put(0x5235e0,1)
  self.registry([(0x523604,1001),(0x5235f8,1002),(0x5235f0,1003),(0x5235e4,1004)])
  name_table=self.object(1105*4,fill=0);dispatch=self.object(1105*4,fill=0)
  for i,(key,target) in enumerate(((0x523604,0x407cc0),(0x5235f8,0x407e40),(0x5235f0,0x407f20),(0x5235e4,0x42a680))):
   n=self.text(key).encode();record=self.object(13+len(n),data=struct.pack('<III',1,len(n),len(n))+n+b'\0')
   self.put(name_table+(1001+i)*4,record+12);self.put(dispatch+(1001+i)*4,target)
  self.put(0x5376a0,0,1104,name_table,name_table,4,0,0)
  self.put(0x5348f0,0,1104,dispatch,dispatch,4,0,0)
  for a in ARITIES:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  self.m.intercept(0x4f6428)
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def bind(self,kind,key,value):
  r=self.tokens['managers'][kind]+16;buckets=self.get(r+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(r+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(r+12,self.get(r+12)+1)
 def registry(self,entries):
  # A complete valid physical Patricia tree, preserving the real lookup body.
  def bit(key,i):
   b=self.text(key).encode()+b'\0';return (b[i//8]>>(i%8))&1 if i//8<len(b) else 0
  def node(rows,start=0):
   if len(rows)==1:
    key,value=rows[0];n=self.object(20,fill=0);self.put(n,n,n,0,key,value);return n
   index=next(i for i in range(start,1024) if len({bit(k,i) for k,v in rows})>1)
   n=self.object(20,fill=0);left=node([(k,v) for k,v in rows if not bit(k,index)],index+1);right=node([(k,v) for k,v in rows if bit(k,index)],index+1)
   self.put(n,left,right,index,rows[0][0],rows[0][1]);return n
  self.put(0x537680,node(entries))
 def entry(self,m,a):
  if a not in SELECTED:return
  receiver=0 if a in (0x4f63ec,0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
  args=list(m.words(m.register(UC_X86_REG_ESP)+4,ARITIES[a]))
  self.entries.append([a,receiver,args])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  if a==0x4f6428:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [a for a,n in self.allocations] and token not in self.freed
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  elif a==0x4f6974:m.return_from_external(self.get(m.register(UC_X86_REG_ECX)),4)
  elif next((k for k,v in m.import_stub.items() if v==a),a)==0x546a40:
   sp=m.register(UC_X86_REG_ESP);self.read(self.get(sp+4),self.get(sp+8));m.return_from_external(0,8)
  else:super().external(m,a)
 def snapshot(self,label):
  spans=[(cut.BASE,cut.SIZE),(0x537668,0x60),(0x5348e8,0x28),(0x5235e0,4)]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(label=label,outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),retired={str(a):self.read(a,n).hex() for a,n in self.allocations if a in self.freed},final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
 def run(self):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);phases=[]
  for i,command in enumerate((0,1000,29,30,1001,1001,1002,1003,1004,1001)):
   helper=self.get(self.tokens['state']+0x18)
   if i==5:self.put(self.tokens['boss']+0x4bc,1)
   if i==6:self.put(self.tokens['boss']+0x4b0,0)
   if i==7:self.put(self.tokens['owner']+0x1a4,1)
   if i==9:self.put(self.tokens['boss']+0x4ec,1)
   self.put(self.tokens['state']+0x1c,command)
   r=self.m.call(0x4073e0,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not r.completed:raise RuntimeError((i,command,r,self.entries[-10:]))
   if i in (0,5,6,7,8,9):
    expected={0:1001,5:1002,6:1003,7:1004,8:1004,9:1001}[i]
    assert self.get(self.tokens['state']+0x1c)==expected,(i,expected)
   phases.append(self.snapshot(command))
  helper=self.get(self.tokens['state']+0x18)
  r=self.m.call(0x407bd0,ecx=helper,arguments=(1,));assert r.completed,r
  self.put(self.tokens['state']+0x18,0);phases.append(self.snapshot('retire'))
  self.put(self.tokens['state']+0x1c,0);r=self.m.call(0x4073e0,arguments=(self.tokens['owner'],));assert r.completed,r
  phases.append(self.snapshot('recreate'))
  return dict(actor=self.tokens['owner'],state=self.tokens['state'],boss=self.tokens['boss'],initial=self.initial,incoming=self.incoming,phases=phases)
def prepare(out):
 # Allocation failure must enter the original new-handler lookup, with no
 # helper construction or allocation. This remains separate from native faults.
 class ExhaustionReached(Exception):pass
 r=Reference();attempted=[];r.m.intercept(0x5022b5)
 def fail_malloc(m,a):
  if a==0x4a48e0:
   attempted.append(r.get(m.register(UC_X86_REG_ESP)+4));m.return_from_external(0,0)
  elif a==0x5022b5:raise ExhaustionReached()
  else:r.external(m,a)
 r.m.on_external=fail_malloc
 try:r.m.call(0x4073e0,arguments=(r.tokens['owner'],));raise AssertionError('original exhaustion returned')
 except ExhaustionReached:pass
 assert attempted==[0x1b8] and not r.allocations
 p=claw();image=bytearray(p.size)
 for section in p.sections:image[section.address-p.base:section.address-p.base+len(section.data)]=section.data
 # Hash-verified original 407620 state registration. Each literal lookup
 # feeds the 5348e8 indexed-table cell that receives this exact callback.
 for lookup,key,index_owner,store,target in ((0x407624,0x523604,0x40769b,0x4076af,0x407cc0),(0x4076a5,0x5235f8,0x407722,0x407736,0x407e40),(0x40772c,0x5235f0,0x4077a9,0x4077bd,0x407f20),(0x4077b3,0x5235e4,0x407897,0x4078a4,0x42a680)):
  assert image[lookup-p.base]==0x68 and struct.unpack_from('<I',image,lookup-p.base+1)[0]==key
  assert image[index_owner-p.base]==0xb9 and struct.unpack_from('<I',image,index_owner-p.base+1)[0]==0x5348e8
  assert image[store-p.base:store-p.base+2]==bytes([0xc7,0x00]) and struct.unpack_from('<I',image,store-p.base+2)[0]==target
 for site,target,continuation in ((0x407418,0x4f63ec,0x40741d),(0x407433,0x4078b0,0x407438),(0x40746c,0x4dc870,0x407471)):
  assert image[site-p.base]==0xe8 and site+5==continuation and continuation+struct.unpack_from('<i',image,site-p.base+1)[0]==target
 assert struct.unpack_from('<10I',image,0x50b26c-p.base)==(0x407bd0,0x407c10,0x407500,0x4063b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0,0x4dca10)
 for site,modrm,slot,continuation in ((0x40744a,0x50,0x10,0x40744d),(0x407457,0x52,0x20,0x40745a),(0x40747b,0x52,0x1c,0x40747e)):
  assert image[site-p.base:site-p.base+3]==bytes([0xff,modrm,slot]) and site+3==continuation
 rows=[Reference(status,live).run() for status,live in ((0,False),(0x21,True))]
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='original-captured',profiles=len(rows))))
def canonical_entries(rows):
 # 4063b0 and its virtual target 4dca10 share one admitted C++ owner.
 # The native module executes that owned body internally, without reentering
 # the host observer. Keep the constructor's separate 4dca10 join visible.
 result=[]
 for row in rows:
  if row[0]==0x4dca10 and result and result[-1][0]==0x4063b0:continue
  if row[0] in SELECTED:result.append(row)
 return cut.normalize_calls(result)
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 for pi,(ep,ap) in enumerate(zip(ref['profiles'],native['profiles'])):
  if not ap['completed']:fail.append(dict(profile=pi,fault=ap['fault'],calls=ap['calls'][-8:]))
  for i,(e,a) in enumerate(zip(ep['phases'],ap['phases'])):
   for key in ('label','outgoing','events','retired','final'):
    if e[key]!=a[key]:fail.append(dict(profile=pi,phase=i,field=key))
   ec=canonical_entries(e['entries']);ac=canonical_entries(a['entries'])
   if ec!=ac:fail.append(dict(profile=pi,phase=i,field='ordered calls',expected=len(ec),actual=len(ac),first=next(((x,y) for x,y in zip(ec,ac) if x!=y),None)))
  if len(ep['phases'])!=len(ap['phases']):fail.append('phase count')
 if len(ref['profiles'])!=len(native['profiles']):fail.append('profile count')
 required={'allocation continuation witness 0','allocation continuation witness 1','provider required','foreign provider','wrong root','wrong actor','missing service','allocation exhaustion','occupied allocation','reentry','wrong continuation','reentrant wrong size','reentrant wrong receiver','reentrant wrong continuation','stale actor identity','stale helper identity','stale logic identity','wrong vtable','wrong slot','unauthorized free','foreign free','same owner retirement','double free','double retirement','shared scene cursor cooperation','unbound entry 5202924','unbound entry 4225200'}
 names=[c['name'] for c in native['controls']]
 if not required.issubset(names) or len(names)!=len(set(names)):fail.append('missing or duplicated native controls')
 for c in native['controls']:
  if not c['passed']:fail.append(c)
 result=dict(status='fail' if fail else 'pass',profiles=len(ref['profiles']),comparisons=sum(len(r['phases']) for r in ref['profiles']),controls=native['controls'],failures=fail)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not fail
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','compare']);p.add_argument('--out',default='work/native-object-connections/aquatis_stalactite/transport');a=p.parse_args();(prepare if a.mode=='prepare' else compare)(ROOT/a.out)
