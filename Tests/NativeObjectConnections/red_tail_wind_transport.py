"""Hash-verified original comparison for the finite RedTailWind transport."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
spec=importlib.util.spec_from_file_location('red_tail_wind_world',ROOT/'Tests/NativeObjectConnections/aquatis_stalactite_transport.py')
aq=importlib.util.module_from_spec(spec);spec.loader.exec_module(aq)
cut=aq.cut
ARITIES={0x4f63ec:1,0x484ca0:1,0x4c96b0:0,0x4dc870:1,0x4c9e30:1,0x4848d0:1,0x4041b0:1,0x4f6428:1,0x484d90:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4c8220:1,0x4c82a0:1,0x4f6286:2,0x4f6974:1,0x4dba00:1,0x4c8da0:6,0x49f0a0:1,0x4c79e0:2,0x4082f0:1,0x4080a0:0,0x408220:22,0x408370:1,0x4dca10:0}
SELECTED=set(ARITIES)
class Reference(cut.Reference):
 bind=aq.Reference.bind
 registry=aq.Reference.registry
 def __init__(self,status=0,live=False,debris=False):
  super().__init__(status,live)
  self.entries=[];self.events=[];self.freed=[];self.debris=debris
  actor=self.tokens['owner'];state=self.tokens['state']
  self.put(state+0x10,0x4847b0);world=self.get(actor+0xc);self.put(state+0xc,world)
  factory=self.object(0x20,fill=0);self.put(factory+0xc,world);self.put(world+8,factory)
  if debris:
   metadata=self.object(0x14,fill=0);self.put(metadata+0x10,0x49f0a0);self.bind('logic',0x522a1c,metadata)
  for key,callback in ((0x522d54,0x4dc830),(0x522d48,0x4dc850)):
   metadata=self.object(0x14,fill=0);self.put(metadata+0x10,callback);self.bind('logic',key,metadata)
  self.put(0x532c0c,0);self.put(0x532c10,100);self.put(0x537210,1234)
  boss=self.object(0x500,fill=0);self.tokens['boss']=boss;self.put(0x53c19c,boss)
  player=self.object(0x200,fill=0);logic=self.object(0x100,fill=0);movement=self.object(0x100,fill=0)
  self.tokens['player']=player;self.put(0x537e88,player);self.put(player+0x6c,logic);self.put(logic+0x14,movement)
  self.put(player+0x4c,100,100);self.put(0x52b354,0,200,0,200);self.put(0x52b34c,35);self.put(0x52b350,1000)
  self.registry([(0x523604,1001),(0x52bb28,1002),(0x52ddbc,1003)])
  names=self.object(1105*4,fill=0);dispatch=self.object(1105*4,fill=0)
  for index,key,target in ((1001,0x523604,0x484e10),(1002,0x52bb28,0x484ea0),(1003,0x52ddbc,0x49f7e0)):
   text=self.text(key).encode();record=self.object(13+len(text),data=struct.pack('<III',1,len(text),len(text))+text+b'\0')
   self.put(names+index*4,record+12);self.put(dispatch+index*4,target)
  self.put(0x5376a0,0,1104,names,names,4,0,0)
  self.put(0x53c210,0,1104,dispatch,dispatch,4,0,0)
  for address in ARITIES:
   if address not in cut.OBSERVE:self.m.observe(address,self.entry)
  self.m.intercept(0x4f6428);self.m.intercept(0x4f51c5)
  assert state==actor+0x200
  self.blocks=[(cut.BASE,actor-cut.BASE),(actor,0x200),(state,0x180),(state+0x180,cut.BASE+cut.SIZE-state-0x180)]+self.blocks[1:]
  self.blocks=[piece for a,n in self.blocks for piece in ([(a,0x541178-a),(0x541178,404),(0x541178+404,a+n-0x541178-404)] if a<=0x541178 and a+n>=0x541178+404 else [(a,n)])]
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def entry(self,m,a):
  if a not in SELECTED:return
  receiver=0 if a in (0x4f63ec,0x4dc870,0x4f6428,0x49f0a0) else m.register(UC_X86_REG_ECX)
  args=list(m.words(m.register(UC_X86_REG_ESP)+4,ARITIES[a]));self.entries.append([a,receiver,args])
  if a==0x4f6286:
   key=self.text(args[0]);self.events.append(['lookup',receiver,key,self.lookup(receiver,key)])
 def external(self,m,a):
  if a==0x4f51c5:
   receiver=m.register(UC_X86_REG_ECX);actor=self.get(m.register(UC_X86_REG_ESP)+4)
   token=self.next_alloc;self.next_alloc=(token+12+15)&~15;tail=self.get(receiver+8)
   self.put(token,0,tail,actor)
   if tail:self.put(tail,token)
   else:self.put(receiver+4,token)
   self.put(receiver+8,token);self.put(receiver+12,self.get(receiver+12)+1)
   self.allocations.append([token,12]);self.events.append(['list-append',receiver,actor,token]);m.return_from_external(token,4)
  elif a==0x4a48e0 and self.debris:
   n=self.get(m.register(UC_X86_REG_ESP)+4);token=self.next_alloc;self.next_alloc=(token+(0x200 if n==0x1b4 else n)+15)&~15
   self.write(token,bytes([204])*n);self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
  elif a==0x4f6428:
   token=self.get(m.register(UC_X86_REG_ESP)+4);assert token in [a for a,n in self.allocations] and token not in self.freed
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  elif a==0x4f6974:m.return_from_external(self.get(m.register(UC_X86_REG_ECX)),4)
  elif next((k for k,v in m.import_stub.items() if v==a),a)==0x546cd4:
   sp=m.register(UC_X86_REG_ESP);rect,x,y=m.words(sp+4,3);left,top,right,bottom=struct.unpack('<4i',self.read(rect,16));x=x if x<0x80000000 else x-0x100000000;y=y if y<0x80000000 else y-0x100000000
   result=int(left<=x<right and top<=y<bottom);self.events.append(['point-in-rectangle',rect,x,y,result]);m.return_from_external(result,12)
  elif next((k for k,v in m.import_stub.items() if v==a),a)==0x546a40:
   sp=m.register(UC_X86_REG_ESP);self.read(self.get(sp+4),self.get(sp+8));m.return_from_external(0,8)
  else:super().external(m,a)
 def snapshot(self,label):
  spans=[(cut.BASE,cut.SIZE),(0x537668,0x60),(0x53c208,0x28),(0x53c19c,4),(0x537210,4),(0x537e88,4)]+[(a,n) for a,n in self.allocations if a not in self.freed]
  return dict(label=label,outgoing=self.m.x87_state(),events=list(self.events),entries=list(self.entries),retired={str(a):self.read(a,n).hex() for a,n in self.allocations if a in self.freed},final=[dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
 def run(self):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);phases=[]
  for i,command in enumerate((0,1000,29,30,1001,1001,1002,1002)):
   if i==5:self.put(self.tokens['boss']+0x4e4,1)
   if i==6:self.put(self.get(self.tokens['state']+0x18)+0x54,1234,100)
   if i==7:self.put(0x537210,2234)
   self.put(self.tokens['state']+0x1c,command)
   r=self.m.call(0x4847b0,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not r.completed:raise RuntimeError((i,command,r,self.entries[-10:]))
   phases.append(self.snapshot(command))
  helper=self.get(self.tokens['state']+0x18)
  r=self.m.call(0x484d90,ecx=helper,arguments=(1,));assert r.completed,r
  self.put(self.tokens['state']+0x18,0);phases.append(self.snapshot('retire'))
  self.put(self.tokens['state']+0x1c,0);r=self.m.call(0x4847b0,arguments=(self.tokens['owner'],));assert r.completed,r
  phases.append(self.snapshot('recreate'))
  return dict(actor=self.tokens['owner'],state=self.tokens['state'],player=self.tokens['player'],boss=self.tokens['boss'],initial=self.initial,incoming=self.incoming,phases=phases)
def prepare(out):
 from Tests.NativeObjectConnections.rez import materialize
 materialize({'LEVEL13/SOUNDS/REDTAIL/WINDWHISTLING.WAV':(ROOT/'App/GameData/LEVEL13/SOUNDS/REDTAIL/WINDWHISTLING.WAV',False)})
 p=claw();image=bytearray(p.size)
 for section in p.sections:image[section.address-p.base:section.address-p.base+len(section.data)]=section.data
 for site,target,continuation in ((0x4847e5,0x4f63ec,0x4847ea),(0x484800,0x484ca0,0x484805),(0x484839,0x4dc870,0x48483e),(0x4b403d,0x4f63ec,0x4b4042)):
  assert image[site-p.base]==0xe8 and site+5==continuation and continuation+struct.unpack_from('<i',image,site-p.base+1)[0]==target
 assert struct.unpack_from('<9I',image,0x50f46c-p.base)==(0x484d90,0x4c9e30,0x4848d0,0x4041b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0)
 for site,modrm,slot,continuation in ((0x484817,0x50,0x10,0x48481a),(0x484824,0x52,0x20,0x484827),(0x484848,0x52,0x1c,0x48484b)):
  assert image[site-p.base:site-p.base+3]==bytes([0xff,modrm,slot]) and site+3==continuation
 # Original registration writes these state callbacks to the wind table.
 for target in (0x484e10,0x484ea0):assert bytes([0xc7,0x07])+struct.pack('<I',target) in image[0x484a00-p.base:0x484ca0-p.base]
 rows=[Reference(status,live,debris).run() for status,live,debris in ((0,False,False),(0x21,True,False),(0,False,True))]
 out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=p.sha256,asset_sha256={'LEVEL13/SOUNDS/REDTAIL/WINDWHISTLING.WAV':hashlib.sha256((ROOT/'App/GameData/LEVEL13/SOUNDS/REDTAIL/WINDWHISTLING.WAV').read_bytes()).hexdigest()},profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='original-captured',profiles=len(rows))))
def canonical_entries(rows):
 from Tests.clawparity.kernel import STACK_BASE,STACK_SIZE
 # Resource lookups publish synchronous output cells. Different native frame
 # layouts may reuse a dead cell; only the live call's storage identity matters.
 selected=[]
 for function,receiver,args in rows:
  if function not in SELECTED:continue
  args=list(args)
  if function==0x4f6286 and STACK_BASE<=args[1]<STACK_BASE+STACK_SIZE:args[1]='synchronous-output-cell'
  selected.append([function,receiver,args])
 return selected
def normalized_events(rows):
 from Tests.clawparity.kernel import STACK_BASE,STACK_SIZE
 identities={}
 def visit(value):
  if isinstance(value,list):return [visit(v) for v in value]
  if isinstance(value,int) and STACK_BASE<=value<STACK_BASE+STACK_SIZE:
   if value not in identities:identities[value]=f'stack-local-{len(identities)}'
   return identities[value]
  return value
 return visit(rows)
def compare_enabled_audio(profile):
 """Replay the source against native-created physical audio resources and inputs."""
 from Tests.clawparity.kernel import Machine
 from unicorn.x86_const import UC_X86_REG_EAX
 assert profile['output_enabled'] is False
 m=Machine(claw(),cut.BASE,cut.SIZE);pages={page for start,end,_ in m.uc.mem_regions() for page in range(start,end+1,4096)}
 def mapped(address,count):
  for page in range(address&~4095,(address+count+4095)&~4095,4096):
   if page not in pages:m.uc.mem_map(page,4096);pages.add(page)
 def put(address,*values):m.write(address,struct.pack('<'+'I'*len(values),*values))
 for segment in profile['initial']:
  data=bytes.fromhex(segment['data']);mapped(segment['address'],len(data));m.write(segment['address'],data)
 for target in (0x4a48e0,0x4a3050,0x4f6428,0x71010008,0x71020014,0x71010018,0x7101001c,0x71010020,0x71010024,0x71010030,0x7101003c,0x71010040,0x71010044,0x71010048):
  if target>=0x70000000:mapped(target,4);m.write(target,b'\xc3')
  m.intercept(target)
 physical=[];allocations=[];frees=[]
 def external(machine,address):
  sp=machine.register(UC_X86_REG_ESP)
  if address==0x4a48e0:
   expected=allocations.pop(0);assert machine.words(sp+4,1)==(expected[2],)
   token=expected[1];mapped(token,expected[2]);machine.write(token,bytes([204])*expected[2]);machine.return_from_external(token,0);return
  if address==0x4a3050:machine.return_from_external(99,0);return
  if address==0x4f6428:
   assert machine.words(sp+4,1)==(frees.pop(0)[1],);machine.return_from_external(0,0);return
  slot=next((k for k,v in machine.import_stub.items() if v==address),address)
  if slot==0x546df0:machine.return_from_external(machine.words(0x537210,1)[0],0);return
  if slot==0x546cd4:
   rect,x,y=machine.words(sp+4,3);left,top,right,bottom=struct.unpack('<4i',machine.read(rect,16));x=x if x<0x80000000 else x-0x100000000;y=y if y<0x80000000 else y-0x100000000
   machine.return_from_external(int(left<=x<right and top<=y<bottom),12);return
  if slot in (0x546d5c,0x546cdc):
   a=machine.words(sp+4,5 if slot==0x546d5c else 1);put(a[0],*(a[1:] if slot==0x546d5c else [0]*4));machine.return_from_external(1,len(a)*4);return
  assert physical,('unexpected physical',hex(address))
  expected=physical.pop(0);assert address==expected['function'],(hex(address),expected)
  a=list(machine.words(sp+4,len(expected['arguments'])));getter=address in (0x71010018,0x7101001c,0x71010020,0x71010024,0x71020014)
  if getter:
   assert a[:-1]==expected['arguments'][:-1]
   value=expected['output']
   if address==0x71020014:mapped(value,16);put(value,machine.words(a[1],1)[0])
   put(a[-1],value)
  else:assert a==expected['arguments'],(a,expected)
  machine.return_from_external(expected['result'],len(a)*4)
 m.on_external=external;m.reset_x87();m.set_x87_state(*profile['incoming'])
 for i,step in enumerate(profile['steps']):
  assert step['completed'],('native enabled audio fault',i,step['fault'])
  if i==1:put(profile['boss']+0x4e4,1)
  helper=m.words(profile['state']+0x18,1)[0]
  if i==2:put(helper+0x54,1234,100)
  if i==3:put(0x537210,2234)
  physical=list(step['physical']);allocations=[e for e in step['events'] if e[0]=='malloc'];frees=[e for e in step['events'] if e[0]=='free']
  put(profile['state']+0x1c,step['command'])
  result=m.call(0x4847b0,arguments=(profile['actor'],),timeout_seconds=5)
  assert result.completed and not physical and not allocations and not frees,(i,result,physical,allocations)
  assert json.loads(json.dumps(m.x87_state()))==step['outgoing'],('enabled audio x87',i,m.x87_state(),step['outgoing'])
  for segment in step['final']:
   expected=bytes.fromhex(segment['data']);actual=m.read(segment['address'],len(expected))
   assert actual==expected,('enabled audio bytes',i,hex(segment['address']),next((j for j,(a,b) in enumerate(zip(actual,expected)) if a!=b),None))
 assert len(profile['steps'])==4
 return len(profile['steps'])

def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 for pi,(ep,ap) in enumerate(zip(ref['profiles'],native['profiles'])):
  if not ap['completed']:fail.append(dict(profile=pi,fault=ap['fault'],calls=ap['calls'][-8:]))
  for i,(e,a) in enumerate(zip(ep['phases'],ap['phases'])):
   for key in ('label','outgoing','events','retired','final'):
    if (normalized_events(e[key]) if key=='events' else e[key])!=(normalized_events(a[key]) if key=='events' else a[key]):
     detail=dict(profile=pi,phase=i,field=key)
     if key=='final':detail['first']=next((dict(address=x['address'],offset=next((j for j,(v,w) in enumerate(zip(bytes.fromhex(x['data']),bytes.fromhex(y['data']))) if v!=w),None)) for x,y in zip(e[key],a[key]) if x!=y and y['data']!='missing'),None)
     fail.append(detail)
   ec=canonical_entries(e['entries']);ac=canonical_entries(a['entries'])
   if ec!=ac:fail.append(dict(profile=pi,phase=i,field='ordered calls',expected=len(ec),actual=len(ac),first=next(((x,y) for x,y in zip(ec,ac) if x!=y),None)))
  if len(ep['phases'])!=len(ap['phases']):fail.append('phase count')
 if len(ref['profiles'])!=len(native['profiles']):fail.append('profile count')
 required={'replaced sound pool before registry','replaced debris helper during resumed random','missing audio physical service','wrong allocation size','missing lifecycle service','unbound stdcall receiver','allocation continuation witness 0','allocation continuation witness 1','allocation continuation witness 2','provider required','foreign provider','wrong root','wrong actor','missing service','allocation exhaustion','occupied allocation','reentry','wrong continuation','reentrant wrong size','reentrant wrong receiver','reentrant wrong continuation','stale actor identity','stale helper identity','stale logic identity','wrong vtable','wrong slot','unauthorized free','foreign free','same owner retirement','double free','double retirement','shared scene cursor cooperation','unbound entry 5202924','unbound entry 4738208'}
 names=[c['name'] for c in native['controls']]
 if not required.issubset(names) or len(names)!=len(set(names)):fail.append('missing or duplicated native controls')
 for c in native['controls']:
  if not c['passed']:fail.append(c)
 audio_comparisons=0
 try:audio_comparisons=compare_enabled_audio(native['enabled_audio'])
 except Exception as error:fail.append(dict(field='enabled audio',error=repr(error)))
 result=dict(enabled_audio_comparisons=audio_comparisons,status='fail' if fail else 'pass',callback='0x4847b0',constructor='0x484ca0',lifecycle='0x4dc870',retirement='0x484d90',profiles=len(ref['profiles']),comparisons=sum(len(r['phases']) for r in ref['profiles']),controls=native['controls'],failures=fail)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not fail
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','compare']);p.add_argument('--out',default='work/native-object-connections/red_tail_wind/transport');a=p.parse_args();(prepare if a.mode=='prepare' else compare)(ROOT/a.out)
