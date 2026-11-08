"""Original-backed finite Stalactite provider transport comparison."""
from __future__ import annotations
import argparse
import hashlib
from functools import lru_cache
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
ARITIES={0x42a680:0,0x4f63ec:1,0x48e990:1,0x4c96b0:0,0x4dc870:1,0x4c9e30:1,0x48e5c0:1,0x4063b0:1,0x4dca10:0,0x4f6428:1,0x484d90:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4c8220:1,0x4c82a0:1,0x4f6286:2,0x4f6974:1,0x4dba00:1,0x4082f0:1,0x4080a0:0,0x408220:22,0x4082d0:2,0x408370:1,0x406290:0,0x406240:0,0x408050:0}
# Internal state bodies are inlined by the admitted owner; observe canonical joins.
SELECTED=set(ARITIES)-{0x4082f0,0x4080a0,0x408220,0x4082d0,0x408370}
@lru_cache(maxsize=1)
def assets():
 from Tests.NativeObjectConnections.rez import materialize
 names=['LEVEL12/ANIS/STALACTITE/'+n+'.ANI' for n in ('HOME','CRUMBLE')]
 names+=['LEVEL12/IMAGES/PROJECTILES/STALACTITE/FRAME%03d.PID'%i for i in range(1,8)]
 names+=['LEVEL12/SOUNDS/'+n+'.WAV' for n in ('STALACTITEHIT2','STALACTITESNAP2')]
 paths={n:ROOT/'App/GameData'/n for n in names}
 materialize({n:(p,False) for n,p in paths.items()})
 return {n:p.read_bytes() for n,p in paths.items()}

class Reference(cut.Reference):
 def __init__(self,status=0,live=False,sounds=True):
  super().__init__(status,live)
  self.entries=[];self.events=[];self.freed=[];self.exact=[]
  self.put(self.tokens['state']+0x10,0x48e4a0)
  self.put(self.tokens['owner']+0x108,1)
  self.put(self.tokens['owner']+0x148,0,0)
  self.put(0x537210,1234);self.put(0x5430c4,16)
  collision=self.get(self.tokens['world']+0x24) if 'world' in self.tokens else self.get(self.get(self.tokens['owner']+0xc)+0x24)
  plane=self.object(0x100,fill=0);tiles=self.object(64*4,words=[0xffffffff]*64);rows=self.object(8*4,words=[i*8 for i in range(8)])
  self.put(collision+0x5c,plane);self.put(plane+0x20,tiles,rows);self.put(plane+0x30,512,512);self.put(plane+0x8c,6,6)
  payloads=assets()
  sprite=self.object(0x6c,fill=0);images=self.object(8*4,fill=0)
  self.put(sprite+0x14,images);self.put(sprite+0x18,8);self.put(sprite+0x64,1,7)
  for i in range(1,8):
   data=payloads['LEVEL12/IMAGES/PROJECTILES/STALACTITE/FRAME%03d.PID'%i]
   _,flags,w,h,x,y=struct.unpack_from('<6I',data)
   header=self.object(0x40,fill=0);self.put(header,0x513a70)
   self.put(header+0x10,w,h,w//2,h//2,x,y);self.put(images+i*4,header)
  self.bind('sprites',0x523698,sprite)
  for key,callback in ((0x522d54,0x4dc830),(0x522d48,0x4dc850)):
   metadata=self.object(0x14,fill=0);self.put(metadata+0x10,callback);self.bind('logic',key,metadata)
  self.bind('animations',0x523680,self.animation(payloads['LEVEL12/ANIS/STALACTITE/HOME.ANI']))
  self.bind('animations',0x523664,self.animation(payloads['LEVEL12/ANIS/STALACTITE/CRUMBLE.ANI']))
  for key,name in (((0x52364c,'STALACTITEHIT2'),(0x523634,'STALACTITESNAP2')) if sounds else ()):
   record=self.object(0x14,fill=0);sound=self.object(0x14,fill=0);source=self.object(0x7c,fill=0)
   wave=payloads['LEVEL12/SOUNDS/'+name+'.WAV'];payload=self.object(len(wave),data=wave)
   self.put(source+0x20,payload,len(wave));self.put(record+0x10,sound);self.put(sound+0x10,source);self.bind('sounds',key,record)
  self.put(0x532c0c,0);self.put(0x532c10,100)
  self.put(0x537e88,0)
  self.tokens['player']=self.object(0x200,fill=0)
  playerLogic=self.object(0x100,fill=0);playerState=self.object(0x100,fill=0)
  self.put(self.tokens['player']+0x6c,playerLogic);self.put(playerLogic+0x14,playerState);self.put(playerState+0x80,0xcccccccc)
  self.registry([(0x523604,1001),(0x527278,1002),(0x5235f8,1003),(0x5235f0,1004),(0x52726c,1005)])
  name_table=self.object(1105*4,fill=0)
  for i,key in enumerate((0x523604,0x527278,0x5235f8,0x5235f0,0x52726c)):
   n=self.text(key).encode();record=self.object(13+len(n),data=struct.pack('<III',1,len(n),len(n))+n+b'\0')
   self.put(name_table+(1001+i)*4,record+12)
  self.put(0x5376a0,0,1104,name_table,name_table,4,0,0)
  dispatch=self.object(1105*4,fill=0)
  for i,target in enumerate((0x48ed70,0x48ee10,0x48eee0,0x48ef90,0x48f040)):
   self.put(dispatch+(1001+i)*4,target)
  self.put(0x53c9d8,0,1104,dispatch,dispatch,4,0,0)
  for a in ARITIES:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  self.m.intercept(0x4f6428)
  actor=self.tokens['owner'];state=self.tokens['state']
  assert state==actor+0x200
  self.blocks=[(cut.BASE,actor-cut.BASE),(actor,0x200),(state,0x180),(state+0x180,cut.BASE+cut.SIZE-state-0x180)]+self.blocks[1:]
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def animation(self,data):
  signature,_,_,count,pathLength,_,_,_=struct.unpack_from('<8I',data)
  assert signature==32 and count>0
  cursor=32+pathLength;descriptor=self.object(0x14,fill=0);table=self.object(count*4,fill=0)
  self.put(descriptor+0xc,table,count)
  for i in range(count):
   fields=struct.unpack_from('<H9h',data,cursor);assert fields[0]&2==0
   frame=self.object(0x30,fill=0);self.put(frame,0,*fields[:9],0,0);self.put(table+i*4,frame)
   cursor+=20
  assert cursor==len(data)
  return descriptor
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
  spans=[(cut.BASE,cut.SIZE),(0x537668,0x60),(0x53c9d0,0x28),(0x537210,4),(0x537e88,4),(0x5430c4,4),(0x532c0c,8)]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(label=label,outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),retired={str(a):self.read(a,n).hex() for a,n in self.allocations if a in self.freed},final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
 def run(self):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);phases=[]
  for i,command in enumerate((0,1000,29,30,1001,1002,1003,1004,1005)):
   if command==1002:self.put(self.get(self.tokens['state']+0x18)+0x1bc,1234,0x7fffffff)
   if command==1004:self.put(self.get(self.get(self.tokens['state']+0x18)+0x12c)+0x188+0x1c,0)
   if command>=1004:self.put(0x537e88,self.tokens['player'])
   self.put(self.tokens['state']+0x1c,command)
   r=self.m.call(0x48e4a0,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not r.completed:raise RuntimeError((i,command,r,self.entries[-10:]))
   if i==0:assert self.get(self.tokens['state']+0x1c)==1001
   phases.append(self.snapshot(command))
  helper=self.get(self.tokens['state']+0x18)
  r=self.m.call(0x484d90,ecx=helper,arguments=(1,));assert r.completed,r
  self.put(self.tokens['state']+0x18,0);phases.append(self.snapshot('retire'))
  self.put(self.tokens['state']+0x1c,0);r=self.m.call(0x48e4a0,arguments=(self.tokens['owner'],));assert r.completed,r
  phases.append(self.snapshot('recreate'))
  return dict(actor=self.tokens['owner'],state=self.tokens['state'],player=self.tokens['player'],initial=self.initial,incoming=self.incoming,phases=phases)
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
 try:r.m.call(0x48e4a0,arguments=(r.tokens['owner'],));raise AssertionError('original exhaustion returned')
 except ExhaustionReached:pass
 assert attempted==[0x1c8] and not r.allocations
 p=claw();image=bytearray(p.size)
 for section in p.sections:image[section.address-p.base:section.address-p.base+len(section.data)]=section.data
 # The original state registration table is checked against its literal
 # callback stores; no game state callback is replaced by a fixture.
 for target in (0x48ed70,0x48ee10,0x48eee0,0x48ef90,0x48f040):
  assert bytes([0xc7,0x00])+struct.pack('<I',target) in image[0x48e6e0-p.base:0x48e990-p.base]
 for site,target,continuation in ((0x48e4d8,0x4f63ec,0x48e4dd),(0x48e4f3,0x48e990,0x48e4f8),(0x48e52c,0x4dc870,0x48e531)):
  assert image[site-p.base]==0xe8 and site+5==continuation and continuation+struct.unpack_from('<i',image,site-p.base+1)[0]==target
 assert struct.unpack_from('<10I',image,0x50f8a4-p.base)==(0x484d90,0x4c9e30,0x48e5c0,0x4063b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0,0x4dca10)
 for site,modrm,slot,continuation in ((0x48e50a,0x50,0x10,0x48e50d),(0x48e517,0x52,0x20,0x48e51a),(0x48e53b,0x52,0x1c,0x48e53e)):
  assert image[site-p.base:site-p.base+3]==bytes([0xff,modrm,slot]) and site+3==continuation
 rows=[Reference(status,live,sounds).run() for status,live,sounds in ((0,False,True),(0x21,True,True),(0,False,False))]
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,asset_sha256={n:hashlib.sha256(b).hexdigest() for n,b in assets().items()},profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='original-captured',profiles=len(rows))))
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
    if e[key]!=a[key]:
     detail=dict(profile=pi,phase=i,field=key)
     if key=='final':
      detail['first']=next((dict(address=x['address'],offset=(next((j for j,(v,w) in enumerate(zip(bytes.fromhex(x['data']),bytes.fromhex(y['data']))) if v!=w),None) if y['data']!='missing' else 'missing')) for x,y in zip(e[key],a[key]) if x!=y),None)
     fail.append(detail)
   ec=canonical_entries(e['entries']);ac=canonical_entries(a['entries'])
   if ec!=ac:fail.append(dict(profile=pi,phase=i,field='ordered calls',expected=len(ec),actual=len(ac),first=next(((x,y) for x,y in zip(ec,ac) if x!=y),None)))
  if len(ep['phases'])!=len(ap['phases']):fail.append('phase count')
 if len(ref['profiles'])!=len(native['profiles']):fail.append('profile count')
 required={'wrong allocation size','missing lifecycle service','unbound stdcall receiver','allocation continuation witness 2','allocation continuation witness 0','allocation continuation witness 1','provider required','foreign provider','wrong root','wrong actor','missing service','allocation exhaustion','occupied allocation','reentry','wrong continuation','reentrant wrong size','reentrant wrong receiver','reentrant wrong continuation','stale actor identity','stale helper identity','stale logic identity','wrong vtable','wrong slot','unauthorized free','foreign free','same owner retirement','double free','double retirement','shared scene cursor cooperation','unbound entry 5202924','unbound entry 4778384'}
 names=[c['name'] for c in native['controls']]
 if not required.issubset(names) or len(names)!=len(set(names)):fail.append('missing or duplicated native controls')
 for c in native['controls']:
  if not c['passed']:fail.append(c)
 result=dict(status='fail' if fail else 'pass',callback='0x48e4a0',constructor='0x48e990',lifecycle='0x4dc870',retirement='0x484d90',asset_sha256=ref['asset_sha256'],profiles=len(ref['profiles']),comparisons=sum(len(r['phases']) for r in ref['profiles']),controls=native['controls'],failures=fail)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not fail
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','compare']);p.add_argument('--out',default='work/native-object-connections/stalactite/transport');a=p.parse_args();(prepare if a.mode=='prepare' else compare)(ROOT/a.out)
