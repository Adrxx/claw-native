"""Finite original/native TownGuard2 allocation and lifecycle comparison."""
import ctypes as C
import importlib.util
import json
import hashlib
import re
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'Tests')]
_spec=importlib.util.spec_from_file_location('cut_transport',ROOT/'Tests/NativeObjectConnections/cut_throat_transport.py')
cut=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(cut)
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS
BASE,SIZE,ALLOC=cut.BASE,cut.SIZE,cut.ALLOC
OBSERVE=tuple(a for a in cut.OBSERVE if a not in (0x437a90,0x4384f0))+(0x496990,0x497970,0x44f1b0,0x44cfd0,0x4c96b0,0x4dc870,0x497510,0x497130,0x44d000,0x44d3c0,0x43dfa0,0x4979b0,0x497040,0x4f6584,0x4f6428,0x497a50,0x43e420,0x4cbb60)
class Reference(cut.Reference):
 def __init__(self,status=0,live=False,control=0x23f):
  super().__init__(status,live,control)
  self.contexts=[];self.commands=[0];self.freed=[];self.source_returns=[];self.source_entry=None;self.source_fs={};self.fs_transport=[]
  self.m.intercept(0x4a49b0)
  self.put(self.tokens['state']+0x10,0x4968d0)
  sprite=self.lookup(self.tokens['managers']['sprites']+16,'LEVEL_CUTTHROAT')
  animation=self.lookup(self.tokens['managers']['animations']+16,'LEVEL_CUTTHROAT_WALK')
  self.bind('sprites',0x52d450,sprite)
  for key in (0x52d434,0x52d394,0x52d3f8,0x52d1ac,0x52d47c):self.bind('animations',key,animation)
  for key in (0x52d090,0x52d074,0x52d2dc,0x52d040,0x52d2c0,0x52d2a4,0x52d288,0x52d26c,0x52d250,0x52cf98,0x52d234,0x52cf60,0x52cf44,0x52cf2c,0x52cf14):
   self.bind('sounds',key,self.object(0x20,fill=0))
  for a in OBSERVE:
   if a not in cut.OBSERVE:self.m.observe(a,self.entry)
  for pc,function in ((0x4971f9,0x497a50),(0x4dc946,0x497130)):
   self.m.observe(pc,lambda machine,address,function=function:self.source_return(machine,function))
  self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
 def source_return(self,m,function):
  cpu={name:m.register(reg) for name,reg in REGISTERS.items() if name!='eflags'}
  cpu['esp']-=self.source_entry
  incoming=self.source_fs[function];assert m.fs_head==incoming
  self.fs_transport.append(dict(function=function,entry=incoming,returned=m.fs_head,preserved=True))
  cpu['fs_head']='entry-fs-chain'
  self.source_returns.append(dict(function=function,cpu=cpu))
 def lifecycle(self):
  self.commands=[0,1000,29,30,6]
  player=self.object(0x200,fill=0);state=self.object(0x180,fill=0);inputs=self.object(0x80,fill=0)
  self.put(0x537e88,player);self.put(player+0x6c,state);self.put(state+0x14,inputs);self.put(player+0x4c,100)
  name=self.object(16,data=b'LS_IDLE2\0',fill=0);table=self.object(4,words=[name]);self.put(0x5376a0,6,6,table);self.put(0x5376b0,4)
  callbacks=self.object(4,words=[0x497a50]);self.put(0x53ca78,6,6,callbacks);self.put(0x53ca88,4)
  tilemap=self.object(0xa0,fill=0);cells=self.object(4,words=[0xffffffff]);rows=self.object(4,words=[0])
  self.put(tilemap+0x20,cells,rows);self.put(tilemap+0x30,1024,1024);self.put(tilemap+0x8c,10,10);self.put(self.tokens['collision']+0x5c,tilemap)
  self.initial=[dict(address=a,data=self.read(a,n).hex()) for a,n in self.blocks]
 def external(self,m,a):
  slot=next((k for k,v in m.import_stub.items() if v==a),a)
  sp=m.register(UC_X86_REG_ESP)
  if slot==0x546cd4:
   rectangle,x,y=m.words(sp+4,3);x,y=struct.unpack('<ii',struct.pack('<II',x,y));left,top,right,bottom=struct.unpack('<iiii',self.read(rectangle,16))
   result=int(left<=x<right and top<=y<bottom);self.events.append(['point-in-rectangle',rectangle,x,y,result]);m.return_from_external(result,12)
  elif a==0x4a49b0:
   token=self.get(sp+4);assert token in [v[0] for v in self.allocations] and token not in self.freed
   self.freed.append(token);self.events.append(['free',token]);m.return_from_external(0,0)
  else:super().external(m,a)
 def bind(self,kind,key,value):
  receiver=self.tokens['managers'][kind]+16;buckets=self.get(receiver+4)
  if not buckets:buckets=self.object(4,fill=0);self.put(receiver+4,buckets)
  node=self.object(16,words=[self.get(buckets),0,key,value]);self.put(buckets,node);self.put(receiver+12,self.get(receiver+12)+1)
 def entry(self,m,a):
  if a in (0x497130,0x497a50):self.source_fs[a]=m.fs_head
  if a in cut.OBSERVE:super().entry(m,a)
  else:
   arity={0x496990:1,0x4dc870:1,0x497510:1,0x497130:1,0x44d000:1,0x44d3c0:1,0x497040:1,0x4f6428:1,0x4cbb60:4}.get(a,0)
   receiver=0 if a in (0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)
   self.entries.append([a,receiver,list(m.words(m.register(UC_X86_REG_ESP)+4,arity))])
  if a==0x496990:self.continuations.append([a,self.get(m.register(UC_X86_REG_ESP))])
  if a==0x497130:
   sp=m.register(UC_X86_REG_ESP);self.source_entry=sp
   self.contexts.append([a,m.register(UC_X86_REG_ECX),self.get(sp),m.register(UC_X86_REG_EBX),m.register(UC_X86_REG_EBP),m.register(UC_X86_REG_EAX),m.register(UC_X86_REG_ESI),m.register(UC_X86_REG_EDI),self.get(sp+4)])
 def run(self,label):
  self.m.reset_x87();self.m.set_x87_state(*self.incoming);snapshots=[];results=[];x87_snapshots=[]
  for command in self.commands:
   self.put(self.tokens['state']+0x1c,command)
   if command==6:
    # Inputs to this finite lifecycle boundary: an unexpired idle timer and
    # motion state 7 use the original collision owner's direct publication.
    self.put(0x537210,100);self.put(ALLOC+0x488,90,20);self.put(self.tokens['owner']+0xcc,7)
   r=self.m.call(0x4968d0,arguments=(self.tokens['owner'],),timeout_seconds=5)
   if not r.completed:raise RuntimeError((label,command,r))
   results.append(self.m.register(UC_X86_REG_EAX));x87_snapshots.append(self.m.x87_state())
   spans=[(self.tokens['owner'],0x200),(self.tokens['state'],0x180)]+self.allocations
   snapshots.append([dict(address=a,data=self.read(a,n).hex()) for a,n in spans])
  retired=None
  if len(self.commands)>1:
   self.retirement_entries=len(self.entries)
   r=self.m.call(0x497040,ecx=ALLOC,arguments=(1,),timeout_seconds=5)
   if not r.completed:raise RuntimeError(('retirement',label,r))
   retired=dict(bytes=self.read(ALLOC,0x498).hex(),freed=self.freed,entries=self.entries[self.retirement_entries:])
  return dict(retired=retired,label=label,actor=self.tokens['owner'],state=self.tokens['state'],initial=self.initial,commands=self.commands,continuations=self.continuations,incoming=self.incoming,outgoing=self.m.x87_state(),allocations=self.allocations,events=self.events,entries=self.entries,contexts=self.contexts,source_returns=self.source_returns,fs_transport=self.fs_transport,results=results,snapshots=snapshots,x87_snapshots=x87_snapshots,final=snapshots[-1])
def boundary_metadata():
 # Decode only the finite ABI boundary against the pinned executable. Instruction
 # text stays out of source control; the evidence records typed CALL metadata.
 from capstone import Cs, CS_ARCH_X86, CS_MODE_32
 from capstone.x86_const import X86_INS_CALL,X86_OP_MEM,X86_REG_EAX,X86_REG_EDX,X86_REG_ESI
 program=claw();decoder=Cs(CS_ARCH_X86,CS_MODE_32);decoder.detail=True
 def read(address,count):
  section=next(s for s in program.sections if s.address<=address and address+count<=s.address+len(s.data))
  return section.data[address-section.address:address-section.address+count]
 metadata=[]
 for pc,target,continuation in ((0x496908,0x4f63ec,0x49690d),(0x496923,0x496990,0x496928),(0x4969b5,0x44c000,0x4969ba)):
  code=read(pc,5);assert code[0]==0xe8 and ((pc+5+struct.unpack('<i',code[1:])[0])&0xffffffff)==target and pc+5==continuation
  metadata.append(dict(call=pc,target=target,continuation=continuation))
 for pc,continuation,base,offset in ((0x49693a,0x49693d,X86_REG_EAX,0x10),(0x496947,0x49694a,X86_REG_EDX,0x20),(0x49696b,0x49696e,X86_REG_EDX,0x1c),(0x4dc943,0x4dc946,X86_REG_EDX,8),(0x4971f7,0x4971f9,X86_REG_ESI,0)):
  instruction=next(decoder.disasm(read(pc,8),pc));assert instruction.id==X86_INS_CALL and instruction.address+instruction.size==continuation
  assert len(instruction.operands)==1 and instruction.operands[0].type==X86_OP_MEM
  operand=instruction.operands[0];assert operand.size==4 and operand.mem.base==base and operand.mem.index==0 and operand.mem.disp==offset
  metadata.append(dict(call=pc,continuation=continuation,receiver_register=decoder.reg_name(base),slot=offset))
 slots={offset:struct.unpack('<I',read(0x50fb6c+offset,4))[0] for offset in (0,4,8,12,16,28,32,36)}
 assert slots=={0:0x497040,4:0x497510,8:0x497130,12:0x44d3c0,16:0x405000,28:0x4c96b0,32:0x44cfd0,36:0x43dfa0}
 return dict(call_metadata=metadata,vtable=dict(address=0x50fb6c,slots=slots))
def string_retirement_references():
 rows=[]
 for name,references,members in (('owned-string-free',1,[0x1a4]),('owned-string-retained',2,[0x1a4]),('owned-string-shared',2,[0x1a8,0x1a4])):
  r=Reference();r.run(name)
  allocated=r.m.call(0x4a48e0,arguments=(16,),timeout_seconds=5);assert allocated.completed
  token=r.m.register(UC_X86_REG_EAX);r.put(token,references,3,3);r.write(token+12,b'abc\0')
  for offset in members:r.put(ALLOC+offset,token+12)
  result=r.m.call(0x497040,ecx=ALLOC,arguments=(1,),timeout_seconds=5);assert result.completed
  rows.append(dict(name=name,references=references,members=members,token=token,bytes=r.read(token,16).hex(),freed=token in r.freed,helper_freed=ALLOC in r.freed,helper_bytes=r.read(ALLOC,0x498).hex()))
 return rows
def fallback_reference():
 # Stop before the unelected inherited descendant, without replacing any game
 # instruction or manufacturing a successful return from it.
 r=Reference();r.lifecycle();r.commands=[0];r.run('fallback-boundary')
 table=r.get(0x53ca80);r.put(table,0);r.put(0x537880,6,6,table,0,4)
 r.put(r.tokens['state']+0x1c,6);r.put(0x537210,100);r.put(ALLOC+0x488,90,20);r.put(r.tokens['owner']+0xcc,7)
 seen={}
 def entry(m,address):
  cpu={name:m.register(reg) for name,reg in REGISTERS.items() if name!='eflags'}
  cpu['esp']-=r.source_entry;assert m.fs_head==r.source_fs[0x497130];cpu['fs_head']='entry-fs-chain'
  seen['cpu']=cpu;seen['continuation']=m.words(m.register(UC_X86_REG_ESP),1)[0]
 def stop(m,address):
  seen['missing_target']=address;m.uc.emu_stop()
 r.m.observe(0x44c840,entry);r.m.observe(0x43d490,stop)
 r.m.call(0x4968d0,arguments=(r.tokens['owner'],),timeout_seconds=5)
 assert seen['continuation']==0x49723a and seen['missing_target']==0x43d490
 return seen
def fs_boundary(out):
 # The original callback owns an SEH record while the native caller supplies
 # its platform sentinel. Verify the executed source scopes never consume the
 # chain and preserve it; keep both raw identities in the comparison evidence.
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32
 from capstone.x86_const import X86_OP_MEM,X86_REG_FS
 from unicorn import UC_HOOK_CODE
 r=Reference();r.lifecycle();active=[];accesses=[];executed=set()
 for address in (0x497130,0x497a50):
  r.m.observe(address,lambda m,a:active.append(a))
 for address,function in ((0x4971f9,0x497a50),(0x4dc946,0x497130)):
  def returned(m,a,function=function):
   assert active.pop()==function
  r.m.observe(address,returned)
 decoder=Cs(CS_ARCH_X86,CS_MODE_32);decoder.detail=True
 def hook(uc,address,size,_):
  if not active:return
  instruction=next(decoder.disasm(bytes(uc.mem_read(address,size)),address));executed.add(address)
  for operand in instruction.operands:
   if operand.type==X86_OP_MEM and operand.mem.segment==X86_REG_FS:accesses.append(dict(address=address,function=active[-1]))
 r.m.uc.hook_add(UC_HOOK_CODE,hook);r.run('fs-boundary')
 result=dict(original_sha256=claw().sha256,entries=r.fs_transport,source_instructions=len(executed),fs_accesses=accesses)
 assert not active and not accesses and len(executed)>0 and all(row['preserved'] for row in r.fs_transport)
 (out/'fs-boundary.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
def prepare(out):
 out.mkdir(parents=True,exist_ok=True)
 profiles=[]
 for live in (False,True):
  for fractional in (False,True):
   r=Reference(live=live);r.lifecycle()
   if fractional:
    for address,value in ((0x5262b8,1.3333333730697632),(0x5262b4,1.1777777671813965),(0x5262b0,0.9133333563804626)):
     r.write(address,struct.pack('<f',value))
   r.initial=[dict(address=a,data=r.read(a,n).hex()) for a,n in r.blocks]
   profile=r.run(f'live-{int(live)}-fractional-{int(fractional)}');profiles.append(profile)
   assert profile['allocations']==[[ALLOC,0x498]]
   assert profile['continuations']==[[0x4f63ec,0x49690d],[0x496990,0x496928]]
   for name in ('LEVEL_TOWNGUARD2','LEVEL_TOWNGUARD2_ADVANCE','LEVEL_TOWNGUARD2_STRIKE1'):
    assert any(event[0]=='lookup' and event[2]==name and event[3]!=0 for event in profile['events']),name
   assert {0x497130,0x497a50,0x43dfa0}.issubset({row[0] for row in profile['entries']})
 (out/'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,**boundary_metadata(),profiles=profiles,string_retirements=string_retirement_references(),fallback=fallback_reference(),fs_boundary=fs_boundary(out)),indent=2)+'\n')
 print(json.dumps(dict(status='pass',original_profiles=len(profiles))))
def preflight(out):
 registry=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
 required=(0x4968d0,0x496990,0x44c000,0x44d000,0x44d3c0,0x44c840,0x497130,0x497510,0x497a50,0x43dfa0,0x497040)
 missing=[hex(a) for a in required if not re.search(r'\{0x%08xu,' % a,registry)]
 result=dict(status='pending-admission' if missing else 'pass',missing_canonical_entries=missing,native_comparison=False,host_wired=False)
 (out/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 3 if missing else 0
def compare(out):
 ref=json.loads((out/'reference.json').read_text());native=json.loads((out/'native.json').read_text());fail=[]
 if len(ref['profiles'])!=4 or len(native['profiles'])!=4:fail.append('profile count')
 if ref.get('fs_boundary',{}).get('fs_accesses')!=[] or ref.get('fs_boundary',{}).get('source_instructions',0)<=0:fail.append('missing original FS preservation trace')

 required={'provider required','foreign provider rejected','wrong callback rejected','missing registry fails','allocation exhaustion preserved','actor identity replacement rejected','allocation identity replacement rejected','physical service reentry rejected','stale live helper rejected','same-owner retirement','double retirement rejected','recreation uses fresh helper','stale helper after recreation rejected'}
 controls=native['controls'];names=[c['name'] for c in controls]
 if not required.issubset(names) or len(set(names))!=len(names):fail.append('required controls missing or duplicated')
 for expected,actual in zip(ref['profiles'],native['profiles']):
  for field in ('label','outgoing','events','snapshots','x87_snapshots','source_returns'):
   if expected[field]!=actual[field]:fail.append(dict(label=expected['label'],field=field))
  if not actual['completed']:fail.append(dict(label=expected['label'],fault=actual['fault']))
  if not actual['allocation_witness']:fail.append('allocation continuation witness')
  for environment,row in (('original',expected),('native',actual)):
   fs=row.get('fs_transport',[])
   if [v['function'] for v in fs]!=[0x497a50,0x497130] or not all(v['entry']==v['returned'] and v['preserved'] for v in fs):fail.append(dict(environment=environment,field='FS chain preservation'))
  if not actual['retired']:fail.append('retirement incomplete')
  if actual['retired_bytes']!=expected['retired']['bytes']:fail.append(dict(label=expected['label'],field='destructor bytes'))
  # The admitted enemy owner implements 43dfa0 as motion()->integrate(),
  # sharing the 4dca10 body in C++. Keep its real producer and collision calls.
  # Require the original 4dca10 entry and both source/native descendants before
  # removing this instrumentation-only extra entry from the ordered comparison.
  original_motion=[v[0] for v in expected['entries'] if v[0] in (0x43dfa0,0x4dca10,0x403b40,0x4cbb60)][-4:]
  native_motion=[v[0] for v in actual['calls'] if v[0] in (0x43dfa0,0x4dca10,0x403b40,0x4cbb60)][-3:]
  if original_motion!=[0x43dfa0,0x4dca10,0x403b40,0x4cbb60] or native_motion!=[0x43dfa0,0x403b40,0x4cbb60]:fail.append('inlined integration witness')
  # 44bc60 is likewise embedded in the base constructor; lookups have separate
  # ordered physical events, and the retirement root is directly invoked.
  selected=set(OBSERVE)-{0x44bc60,0x4f6286,0x497040,0x4dca10}
  e=cut.normalize_calls([v for v in expected['entries'] if v[0] in selected]);a=cut.normalize_calls([v for v in actual['calls'] if v[0] in selected])
  if e!=a:fail.append(dict(label=expected['label'],field='ordered calls',expected_count=len(e),actual_count=len(a),first_difference=next(((x,y) for x,y in zip(e,a) if x!=y),None)))
  contexts=actual['contexts']
  if len(contexts)!=1 or contexts[0]!=expected['contexts'][0]:fail.append(dict(label=expected['label'],field='lifecycle source context',expected=expected['contexts'],actual=contexts))
 if native.get('fallback')!=ref.get('fallback'):fail.append(dict(field='fallback source boundary',expected=ref.get('fallback'),actual=native.get('fallback')))
 if native.get('string_retirements')!=ref.get('string_retirements') or len(ref.get('string_retirements',[]))!=3:fail.append('owned CString retirement comparison')
 for c in controls:
  if not c['passed']:fail.append(dict(control=c['name']))
 result=dict(status='fail' if fail else 'pass',profiles=4,controls=len(controls),string_retirements=3,failures=fail,host_wired=False)
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(fail)


STATE_TARGETS = (0x497750, 0x4979B0, 0x497A50, 0x483DC0, 0x44C840)
REGISTRATIONS = ((0x49730F, 0x497750), (0x497396, 0x4979B0),
                 (0x49741D, 0x497A50), (0x497504, 0x483DC0))
REGISTERS = dict(zip(
    ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip", "eflags"),
    (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
     UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
     UC_X86_REG_EIP, UC_X86_REG_EFLAGS)))


def signature(address):
    header = (ROOT / "Sources/ClawCanonicalDispatch.h").read_text()
    row = re.search(r"\{0x%08xu,\s*([^\n]+)\}," % address, header)
    if row is None:
        raise RuntimeError(f"missing canonical entry {address:#x}")
    fields = [part.strip() for part in row[1].split(",")]
    number = lambda i: int(fields[i].removesuffix("u"), 0)
    return dict(function=hex(address), convention=fields[0], arguments=number(1),
                result=fields[2], family=fields[4].strip('"'),
                source_capability=number(5), input_mask=number(6),
                output_mask=number(7), preserve_mask=number(8))


def original_witness(native_entry=None):
    program = claw()  # Required v1.0 executable hash check.
    machine = Machine(program, 0x03000000, 0x10000)
    # Keep the comparison host's reserved leading heap guard intact.
    helper, table, index = 0x03000040, 0x03001000, 7

    def put(address, *values):
        machine.write(address, struct.pack("<" + "I" * len(values), *values))

    # Legal in-range LS_IDLE2 input; the original early return has no child
    # calls. No instructions or imports are patched or intercepted.
    put(helper + 0x488, 90, 20)
    put(0x537210, 100)
    put(0x53CA78, index, index, table, 0, 4)
    put(table, 0x497A50)
    observed = []
    native_calls = []

    def capture():
        return {name: machine.register(reg) for name, reg in REGISTERS.items()}

    if native_entry is not None:
        # Only this elected native owner replaces original instructions. The
        # original dispatcher supplies the real CALL frame and executes its
        # suffix. This bounded comparison is not a shipping ownership adapter.
        from Tests.clawparity.env import Env, NativeSourceContext

        def native_state(active, target):
            assert target == 0x497A50
            observed.append(dict(at=hex(target), cpu=capture()))
            assert active.words(active.register(UC_X86_REG_ESP), 1)[0] == 0x4971F9
            env = Env(program, heap_bytes=0x20000)
            assert env.object(0xFFC0, "actual helper and dispatch table") == helper
            env.write(helper, active.read(helper, 0xFFC0))
            env.write(program.data_start, active.read(program.data_start,
                      program.base + program.size - program.data_start))
            stack_base, stack_size = 0x01FF0000, 0x20000
            env.write(stack_base, active.read(stack_base, stack_size))
            cpu = NativeSourceContext(size=C.sizeof(NativeSourceContext), version=1,
                                      inputMask=0x7FF, outputMask=0x5FF,
                                      preserveMask=0x472, fsHead=active.fs_head)
            for name, value in capture().items():
                setattr(cpu, name, value)
            env._freeze()
            result = env.run_native(native_entry, target, helper, (),
                                    source_context=cpu, source_return_pc=0x4971F9,
                                    source_convention="thiscall")
            assert result.completed, (result.fault, result.errors)
            assert cpu.eip == 0x4971F9, "native owner changed its real continuation"
            active.write(0x03000000, result.heap[:0x10000])
            active.write(program.data_start, result.image)
            active.write(stack_base, bytes(env._stack))
            for bit, (name, reg) in enumerate(REGISTERS.items()):
                if cpu.outputMask & (1 << bit):
                    active.uc.reg_write(reg, getattr(cpu, name))
            active.fs_head = cpu.fsHead
            native_calls.append(dict(target=hex(target), continuation=hex(cpu.eip),
                                     eax=cpu.eax, ecx=cpu.ecx, edx=cpu.edx))

        machine.intercept(0x497A50)
        machine.on_external = native_state

    for address in (0x497130, 0x497A50, 0x4971F9):
        if native_entry is not None and address == 0x497A50:
            continue
        machine.observe(address, lambda _, pc: observed.append(
            dict(at=hex(pc), cpu=capture())))
    result = machine.call(0x497130, ecx=helper, edx=0x12345678, arguments=(index,))
    if not result.completed:
        raise RuntimeError(f"original witness failed: {result}")
    child = next(row["cpu"] for row in observed if row["at"] == "0x497a50")
    returned = next(row["cpu"] for row in observed if row["at"] == "0x4971f9")
    assert returned["eax"] == 0 and returned["ecx"] == 20 and returned["edx"] == 90
    assert (child["ecx"], child["edx"]) != (20, 90)
    final_cpu = capture()
    assert final_cpu["eax"] == 0 and final_cpu["ecx"] == 20 and final_cpu["edx"] == 90
    registration = []
    for store, target in REGISTRATIONS:
        code = machine.read(store, 6)
        assert code[:2] == b"\xc7\x00" and struct.unpack("<I", code[2:])[0] == target
        registration.append(dict(store=hex(store), target=hex(target)))
    code = machine.read(0x497235, 5)
    assert code[0] == 0xE8 and 0x49723A + struct.unpack("<i", code[1:])[0] == 0x44C840
    for call, continuation in ((0x4971F7, 0x4971F9), (0x49722A, 0x49722C)):
        assert machine.read(call, 2) == b"\xff\x16" and continuation == call + 2
    name = machine.read(0x52D464, 16).split(b"\0")[0].decode("ascii")
    assert name == "LS_IDLE2"
    return dict(original_sha256=program.sha256, original_completed=True,
                root="0x497130", target="0x497a50", continuation="0x4971f9",
                state_name=name, state_index=index,
                index_note="Registry-assigned input, not a fixed startup ordinal",
                now=100, timer=90, interval=20, observed=observed,
                final_cpu=final_cpu, original_registrations=registration,
                fallback=dict(call="0x497235", target="0x44c840", continuation="0x49723a"),
                stack_sha256=hashlib.sha256(machine.read(0x01FF0000, 0x20000)).hexdigest(),
                fs_head=machine.fs_head,
                helper=hex(helper), table=hex(table),
                native_state_calls=native_calls, native_comparison=native_entry is not None)


def source_contract_check():
    from Tests.clawparity.env import Env, NativeSourceContext, NativeHost, U32, build, ContextFault
    contracts = []
    for family in ("level_five_town_guard_states_switch", "level_one_object_actions_01"):
        spec = json.loads((ROOT / f"Tests/families/{family}.json").read_text())
        assert spec["evidence"]["gate"]["status"] == "admitted", family
        for owned in spec["owned"]:
            if int(owned["address"], 16) in STATE_TARGETS:
                assert owned["source_context"] == dict(input_mask=0x7FF,
                    output_mask=0x5FF, preserve_mask=0x472, optional=True)
                contracts.append(dict(family=family, function=owned["address"],
                                      contract=owned["source_context"]))
    assert len(contracts) == 5
    library = C.CDLL(str(build.library("town-guard-state-source-witness",
                         [ROOT / "Sources/LevelFiveTownGuardStatesSwitchRuntime.cpp"])))
    entry = library.claw_level_five_town_guard_states_switch_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = C.c_int
    original = original_witness()
    native = original_witness(entry)
    # Return flags are dead at this consumer. All selected integer CPU fields
    # and every stack byte must agree at the child and dispatcher returns.
    selected = tuple(name for name in REGISTERS if name != "eflags")
    left = next(row["cpu"] for row in original["observed"] if row["at"] == "0x4971f9")
    right = next(row["cpu"] for row in native["observed"] if row["at"] == "0x4971f9")
    assert all(left[name] == right[name] for name in selected), (left, right)
    assert all(original["final_cpu"][name] == native["final_cpu"][name] for name in selected)
    assert original["stack_sha256"] == native["stack_sha256"]
    assert original["fs_head"] == native["fs_head"]
    # Independent publication mutations prove this witness rejects stale or
    # corrupted CPU outputs after the actual translated owner executes.
    publication_controls = []
    for field in ("eax", "ecx", "edx", "eip"):
        def corrupt(function, receiver, arguments, count, host, output, field=field):
            completed = entry(function, receiver, arguments, count, host, output)
            cpu = C.cast(host, C.POINTER(NativeHost)).contents.sourceContext.contents
            setattr(cpu, field, getattr(cpu, field) ^ 1)
            return completed
        try:
            original_witness(corrupt)
        except AssertionError:
            publication_controls.append(dict(field=field, rejected=True))
        else:
            raise AssertionError(f"undetected source publication mutation: {field}")
    negative = []
    for label, masks, return_pc in (
            ("wrong-output-mask", (0x7FF, 0x5F3, 0x472), 0x4971F9),
            ("wrong-preserve-mask", (0x7FF, 0x5FF, 0), 0x4971F9),
            ("missing-return-pc", (0x7FF, 0x5FF, 0x472), 0)):
        env = Env(claw())
        helper = env.object(0x500, "negative helper")
        env.put(helper + 0x488, 90, 20)
        env.put(0x537210, 100)
        cpu = NativeSourceContext(size=C.sizeof(NativeSourceContext), version=1,
            inputMask=masks[0], outputMask=masks[1], preserveMask=masks[2],
            ecx=helper, esp=0x02007FF0, eip=0x497A50, eflags=2, fsHead=0xFFFFFFFF)
        env._freeze()
        try:
            result = env.run_native(entry, 0x497A50, helper, (), source_context=cpu,
                                    source_return_pc=return_pc, source_convention="thiscall")
        except ContextFault as error:
            negative.append(dict(control=label, rejected=True, reason=type(error).__name__))
        else:
            assert not result.completed and result.fault == 5, label
            negative.append(dict(control=label, rejected=True, fault=result.fault))
    result = dict(status="pass", scope="native-state-owner-with-original-dispatch-frame-and-suffix",
        host_wired=False, contracts=contracts, original=original, native=native,
        negative_context=negative, publication_controls=publication_controls)
    out = ROOT / "work/native-object-connections/town_guard2/source_contracts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="pass", contracts=5, eax=0, ecx=20, edx=90,
                         negative_context=len(negative),
                         rejected_publication_mutations=len(publication_controls),
                         host_wired=False, evidence=str(out))))
    return 0


if __name__=='__main__':
 if '--source-contracts' in sys.argv:raise SystemExit(source_contract_check())
 command=sys.argv[1] if len(sys.argv)>1 else 'prepare'
 out=Path(sys.argv[2] if len(sys.argv)>2 else ROOT/'work/native-object-connections/town_guard2/transport').resolve()
 if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence belongs under work/')
 if command=='prepare':prepare(out)
 elif command=='compare':raise SystemExit(compare(out))
 elif command=='preflight':raise SystemExit(preflight(out))
 else:raise ValueError('unknown comparison command')
