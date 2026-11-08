"""Shared-owner comparison using retained WWD heap and disc-authenticated resources."""
import importlib.util,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from Tests.NativeObjectConnections.rez import entries,verify_assets
from unicorn.x86_const import *
from unicorn import UC_HOOK_MEM_WRITE
s=importlib.util.spec_from_file_location('constructor',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
OBSERVE=base.OBSERVE+(0x44cfd0,0x4c96b0,0x4dc870,0x44d000,0x438100,0x44d3c0,0x43e420,0x43dfa0,0x4c82a0,0x438010,0x4f6584,0x4f6428,0x4dc830,0x4dc850,0x4c80c0,0x438030,0x4385b0,0x4386d0,0x4388a0,0x438900,0x438a90)
ARITY={0x4c8220:1,0x4db620:1,0x4dbe10:2,0x4dbd60:1,0x420fc0:1,0x4dbd20:1,0x403b40:2,0x437a90:1,0x44c000:1,0x44bc60:1,0x4f63ec:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x4062e0:1,0x4061b0:1,0x4f6286:2,0x44d000:1,0x44d3c0:1,0x4dc870:1,0x438100:1,0x4c82a0:1,0x438010:1,0x4f6428:1,0x4c80c0:1}
def fixture():
 d=ROOT/'work/native-object-connections/cut_throat';p=json.loads((d/'cut-throat-fault.json').read_text());spans={s['address']:bytes.fromhex(s['hex']) for s in p['segments']};boundary=json.loads((d/'original-secondary-allocation-boundary.json').read_text());assert boundary['executable_sha256']==claw().sha256
 def get(a):
  for t,b in spans.items():
   if t<=a and a+4<=t+len(b):return struct.unpack_from('<I',b,a-t)[0]
  raise KeyError(hex(a))
 actor,state=boundary['actor'],boundary['state'];world=get(actor+12)
 logic={}
 for a,b in spans.items():
  if len(b)==20 and get(a) in (0x522d48,0x522d54):logic['LogicAttack' if get(a)==0x522d48 else 'LogicHit']=a
 assert set(logic)=={'LogicHit','LogicAttack'} and get(logic['LogicHit']+16)==0x4dc830 and get(logic['LogicAttack']+16)==0x4dc850
 disc=dict(entries());verify_assets();images=[]
 # Authenticate all actual image frame bodies against the hash-checked disc.
 pids={int(Path(n).stem.removeprefix('FRAME')):b[32:] for n,b in disc.items() if n.startswith('LEVEL3/IMAGES/CUTTHROAT/') and n.endswith('.PID')}
 for a,b in spans.items():
  if len(b)!=108:continue
  table,count=struct.unpack_from('<II',b,20)
  if count!=max(pids)+1 or table not in spans or len(spans[table])!=count*4:continue
  ptrs=struct.unpack('<'+'I'*count,spans[table]);valid=True
  for index,payload in pids.items():
   frame=ptrs[index]
   if frame not in spans or len(spans[frame])!=64:valid=False;break
   bitmap=get(frame+48);raw=get(bitmap+12)
   if spans.get(raw)!=payload:valid=False;break
  if valid:images.append(a)
 assert len(images)==1,images
 sequences={}
 for n,b in disc.items():
  if not n.startswith('LEVEL3/ANIS/CUTTHROAT/') or not n.endswith('.ANI'):continue
  count,namelen=struct.unpack_from('<II',b,12);rows=[struct.unpack_from('<10H',b,32+namelen+i*20) for i in range(count)];matches=[]
  for token,v in spans.items():
   if len(v)!=20 or token<max(logic.values()):continue
   ptr,num=struct.unpack_from('<II',v,12)
   if num!=count or ptr not in spans or len(spans[ptr])!=num*4:continue
   frames=[spans.get(x) for x in struct.unpack('<'+'I'*num,spans[ptr])]
   if all(f is not None and len(f)==48 for f in frames) and all(tuple(struct.unpack_from('<I',f,i)[0] for i in (8,12,20,24))==(r[1],r[2],r[4],r[5]) for r,f in zip(rows,frames)):matches.append(token)
  if len(matches)==1:sequences['LEVEL_CUTTHROAT_'+Path(n).stem]=matches[0]
 assert {'LEVEL_CUTTHROAT_'+n for n in ['WALK','STRIKE1','STRIKE2','FALL','HITLOW','HITHIGH','HOME','LIFTED','LIFTED2','STAND1','STAND2','STAND3','STAND4','JUMP','THROWN']}<=sequences.keys()
 lower,upper,data,stride=[get(a) for a in [0x5375a0,0x5375a4,0x5375a8,0x5375b0]]
 home_states=[state for state in range(lower,upper+1) if get(data+(state-lower)*stride)==0x4386d0];assert len(home_states)==1
 bindings=[[get(world+0x14)+16,n,t] for n,t in logic.items()]+[[get(world+0x10)+16,'LEVEL_CUTTHROAT',images[0]]]+[[get(world+0x2c)+16,n,t] for n,t in sequences.items()]
 audio=get(world+0x28)+16;assert get(audio)==0
 program=claw();m=Machine(program,0x10000000,0x1000)
 for address,count in [(0x50c934,40),(0x513740,40),(0x50c928,4),(0x5262b0,12),(0x50b090,24),(0x50e008,8),(0x513e10,16),(0x513e40,4),(0x513e48,16)]:
  expected=m.read(address,count);actual=b''.join(struct.pack('<I',get(address+i)) for i in range(0,count,4));assert actual==expected,hex(address)
 for name,id,callback in [('LogicHit',21,0x4dc830),('LogicAttack',22,0x4dc850)]:
  token=logic[name];assert tuple(get(token+i) for i in (4,8,12,16))==(id,2,0,callback)
 lo,hi=0x50a000,program.base+program.size;occupied=sorted((a,a+len(b)) for a,b in spans.items() if a<hi and a+len(b)>lo);cursor=lo
 for a,end in occupied+[(hi,hi)]:
  cursor=(cursor+3)&~3;end_gap=a&~3
  if cursor<end_gap:spans[cursor]=m.read(cursor,end_gap-cursor)
  cursor=max(cursor,end)
 return dict(home_state=home_states[0],actor=actor,state=state,allocation_base=0x69d00000,bindings=bindings,audio_dictionary=audio,initial=[dict(address=a,data=b.hex()) for a,b in sorted(spans.items())],resource_proof=dict(asset_sha256=verify_assets(),pid_count=len(pids),animations=sequences,image_token=images[0],logic=logic))
class Reference:
 def __init__(self,p):
  self.p=p;self.m=Machine(claw(),0x10000000,0x1000);self.next=p['allocation_base'];self.allocations=[];self.calls=[];self.events=[];self.continuations=[];self.source=[];self.retirements=[];self.live={}
  mapped={page for begin,end,_ in self.m.uc.mem_regions() for page in range(begin,end+1,4096)}
  def map_span(a,n):
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in mapped:self.m.uc.mem_map(page,4096);mapped.add(page)
  self.map=map_span;imports={k:self.m.read(k,4) for k in self.m.import_stub}
  for b in p['initial']:
   data=bytes.fromhex(b['data']);map_span(b['address'],len(data));self.m.write(b['address'],data)
  for k,v in imports.items():self.m.write(k,v)
  for a in OBSERVE:self.m.observe(a,self.entry)
  self.m.observe(0x4dc946,self.return_source)
  for a in (0x4a48e0,0x4f6286,0x4a3050,0x4a49b0):self.m.intercept(a)
  self.m.on_external=self.external
  self.global_writes=[]
  self.m.uc.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,address,size,value,user:self.global_writes.append((address,size)) if 0x500000<=address<0x600000 else None)
 def get(self,a):return self.m.words(a,1)[0]
 def put(self,a,v):self.m.write(a,struct.pack('<I',v&0xffffffff))
 def text(self,a):
  result=b''
  for i in range(256):
   c=self.m.read(a+i,1)
   if c==b'\0':return result.decode('ascii')
   result+=c
  raise AssertionError(hex(a))
 def entry(self,m,a):
  sp=m.register(UC_X86_REG_ESP);receiver=0 if a in (0x4f63ec,0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX);self.calls.append([a,receiver,list(m.words(sp+4,ARITY.get(a,0)))])
  if a==0x4f63ec:self.continuations.append([a,self.get(sp)])
  if a==0x438100:self.source.append(dict(function=a,eax=m.register(UC_X86_REG_EAX),edx=m.register(UC_X86_REG_EDX),ebx=m.register(UC_X86_REG_EBX),esi=m.register(UC_X86_REG_ESI),edi=m.register(UC_X86_REG_EDI),ebp=m.register(UC_X86_REG_EBP),esp=sp,ecx=m.register(UC_X86_REG_ECX),eflags=m.register(UC_X86_REG_EFLAGS),frame=list(m.words(sp,6))))
 def return_source(self,m,a):
  if self.source:self.source[-1]['output']={n:m.register(r) for n,r in [('eax',UC_X86_REG_EAX),('ebx',UC_X86_REG_EBX),('esi',UC_X86_REG_ESI),('edi',UC_X86_REG_EDI),('ebp',UC_X86_REG_EBP),('eflags',UC_X86_REG_EFLAGS)]}
 def external(self,m,a):
  sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+i*4)
  if a==0x4a48e0:
   n=arg(0);t=self.next;self.next=(t+n+15)&~15;self.map(t,n);m.write(t,b'\xcc'*n);self.allocations.append([t,n]);self.live[t]=n;self.events.append(['malloc',t,n]);m.return_from_external(t,0)
  elif a==0x4a49b0:
   t=arg(0);n=self.live.pop(t);self.retirements.append(dict(address=t,data=m.read(t,n).hex()));m.return_from_external(0,0)
  elif a==0x4f6286:
   receiver=m.register(UC_X86_REG_ECX);name=self.text(arg(0));found=[t for r,n,t in self.p['bindings'] if r==receiver and n==name]
   if not found:assert receiver==self.p['audio_dictionary'],(hex(receiver),name)
   value=found[0] if found else 0;self.put(arg(1),value);self.events.append(['lookup',receiver,name,value]);m.return_from_external(int(value!=0),8)
  elif a==0x4a3050:self.events.append(['rand',99]);m.return_from_external(99,0)
  else:
   slot=next((k for k,v in m.import_stub.items() if v==a),a)
   if slot==0x546d5c:
    v=[arg(i) for i in range(1,5)];m.write(arg(0),struct.pack('<4I',*v));self.events.append(['rectangle',arg(0),*v]);m.return_from_external(1,20)
   elif slot==0x546cdc:m.write(arg(0),bytes(16));self.events.append(['empty-rectangle',arg(0)]);m.return_from_external(1,4)
   elif slot==0x5469e8:v=(self.get(arg(0))-1)&0xffffffff;self.put(arg(0),v);m.return_from_external(v,4)
   elif slot==0x546cd4:
    l,t,r,b=struct.unpack('<4i',m.read(arg(0),16));x,y=struct.unpack('<2i',struct.pack('<2I',arg(1),arg(2)));m.return_from_external(int(l<=x<r and t<=y<b),12)
   else:raise RuntimeError(('service',hex(a),hex(slot)))
 def run(self,label,incoming):
  self.m.reset_x87();self.m.set_x87_state(*incoming);outputs=[];home=0
  for command in [0,1000,29,30,None,self.p["home_state"],"retire",0]:
   command=home if command is None else command;self.put(self.p['state']+0x1c,0 if command=='retire' else command);self.put(0x5430c4,17);self.put(0x537210,1000);self.calls=[];self.events=[];self.source=[];self.global_writes=[]
   print('original command',command,flush=True);before=self.m.x87_state()
   if command=='retire':
    helper=self.get(self.p['state']+0x18);result=self.m.call(0x438010,ecx=helper,arguments=[1]);assert result.completed,result
    for offset in [0x70,0x78]:
     token=self.get(self.p['actor']+offset);result=self.m.call(0x4c80c0,ecx=token,arguments=[1]);assert result.completed,result
     self.put(self.p['actor']+offset,0)
    self.put(self.p['state']+0x18,0)
   else:
    result=self.m.call(0x4379d0,arguments=[self.p['actor']]);assert result.completed,(command,result,self.calls[-10:])
   if command==0:home=self.get(self.p['state']+0x1c)
   spans=[(self.p['actor'],0x1b4),(self.p['state'],0x174)]+list(self.live.items())+[(0x537598,36),(0x537668,44),(0x537698,36),(0x537638,36),(0x537878,36),(0x544b14,60),(0x5430c4,4),(0x537210,4)]
   assert all(any(a<=address and address+size<=a+n for a,n in spans) for address,size in self.global_writes),[(hex(a),n) for a,n in self.global_writes if not any(t<=a and a+n<=t+count for t,count in spans)]
   outputs.append(dict(global_writes=sorted(set(self.global_writes)),command=command,incoming=before,outgoing=self.m.x87_state(),calls=list(self.calls),events=list(self.events),source=list(self.source),retirements=list(self.retirements),final=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in spans]))
  return dict(label=label,incoming=incoming,steps=outputs,allocations=self.allocations,continuations=self.continuations)
def prepare(out):
 p=fixture();rows=[Reference(p).run('empty',[0x23f,0,[]]),Reference(p).run('live-status',[0x23f,0x1821,[[0xc000000000000000,0x3fff]]])];out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,fixture=p,profiles=rows),indent=2)+'\n');print(json.dumps(dict(status='pass',profiles=len(rows))))
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[];selected=set(OBSERVE)-{0x44bc60,0x438030,0x4f6286}
 assert len(ref['profiles'])==len(native['profiles'])==2
 assert len(native['controls'])>=48 and len({c['name'] for c in native['controls']})==len(native['controls'])
 required={'provider required','foreign provider rejected','wrong callback rejected','wrong actor rejected','allocation exhaustion preserved','secondary allocation exhaustion 2 preserves earlier owners','secondary allocation exhaustion 3 preserves earlier owners','wrong source frame rejected','foreign retirement owner rejected','unbound destructor rejected','retained live helper rejects second construction','replacement actor identity rejected','replacement helper rejected','foreign helper rejected'}
 assert required<={c['name'] for c in native['controls']}
 for expected,actual in zip(ref['profiles'],native['profiles'],strict=True):
  assert len(expected['steps'])==8
  assert [n for _,n in expected['allocations']]==[0x480,0x174,0x174]*2
  assert len({a for a,_ in expected['allocations']})==6
  assert len(expected['steps'][6]['retirements'])==3
  assert {0x4385b0,0x4386d0}<={call[0] for step in expected['steps'] for call in step['calls']}
  expected_requests=[[{0x437a0d:0x4379d0,0x4c7f4f:0x4c7fa0,0x4c800f:0x4c8060}[pc],size,0x4f63ff,pc] for (_,pc),(_,size) in zip(expected['continuations'],expected['allocations'],strict=True)]
  if actual['requests']!=expected_requests:fail.append(dict(label=expected['label'],field='allocation request roots sizes and continuations'))
  if len(expected['steps'])!=len(actual['steps']):fail.append(dict(label=expected['label'],field='step count'))
  for e,a in zip(expected['steps'],actual['steps']):
   for k in ['command','incoming','outgoing','events','final','retirements']:
    if e[k]!=a[k]:fail.append(dict(label=expected['label'],command=e['command'],field=k))
   def calls(rows):
    selected_rows=[r for r in rows if r[0] in selected and not(e['command']==0 and r[0]==0x4384f0)]
    # The admitted43dfa0 body directly embeds its private4dca10 integrate
    # helper. Keep the independent constructor4dca10 owner observations.
    return base.normalize_calls([r for i,r in enumerate(selected_rows) if not(r[0]==0x4dca10 and i>0 and selected_rows[i-1][0]==0x43dfa0)])
   if calls(e['calls'])!=calls(a['calls']):fail.append(dict(command=e['command'],field='ordered calls',expected=calls(e['calls']),actual=calls(a['calls'])))
   if not a['completed']:fail.append(dict(command=e['command'],fault=a['fault']))
   original_inputs=[{k:v for k,v in row.items() if k in ['eax','edx','ebx','esi','edi','ebp','ecx','eflags','frame']} for row in e['source']]
   for row in original_inputs:row['frame']=row['frame'][:4]
   if original_inputs!=a['source']:fail.append(dict(command=e['command'],field='source entry',expected=original_inputs,actual=a['source']))
   outputs=[{k:v for k,v in row['output'].items() if k!='eflags'} for row in e['source']]
   if outputs!=a['source_outputs']:fail.append(dict(command=e['command'],field='source return',expected=outputs,actual=a['source_outputs']))
 for c in native['controls']:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=len(native['profiles']),controls=len(native['controls']),failures=fail);(out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)
if __name__=='__main__':
 out=Path(sys.argv[2]).resolve();assert (ROOT/'work').resolve() in out.parents
 if sys.argv[1]=='prepare':prepare(out)
 elif sys.argv[1]=='compare':raise SystemExit(compare(out))
