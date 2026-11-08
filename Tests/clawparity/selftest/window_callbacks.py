"""Synthetic source-built registration and original creation callback tests."""
import ctypes as C
from dataclasses import replace
import hashlib,json,struct,subprocess,sys
from pathlib import Path
from .. import build
from ..env import Env,Halt,WindowCallbackContract,NativeSourceContext,NativeHost,U32,Signature
from ..kernel import STACK_BASE,STACK_SIZE,STACK_TOP,ContextFault
from ..program import Program,Section
from .source_context import context
from .stack import relative_call
REG=0x402000;CREATE=0x402004;NESTED=0x402008;DESC=0x402100;NAME=0x402200;TARGET=0x401400
WORDS=(8,TARGET,0,0,0x51,0x111,0x222,0x333,0,NAME)
ARGS=(0x40008,NAME,NAME+32,0x80080000,0,0,640,480,0,0,0x51,0)
CALLBACK=bytes.fromhex('55 89e5 8b450c a340204000 ff0544204000 ff7514 50 ff1508204000 89ec 5d c21000')
def source(callback=CALLBACK):
    code=bytearray(b'\xcc'*0x800);b=bytearray()
    for i,value in enumerate(WORDS):b+=b'\xc7\x05'+struct.pack('<II',DESC+4*i,value)
    b+=b'\x68'+struct.pack('<I',DESC);regpc=0x401000+len(b);b+=b'\xff\x15'+struct.pack('<I',REG)
    for value in reversed(ARGS):b+=b'\x68'+struct.pack('<I',value)
    createpc=0x401000+len(b);b+=b'\xff\x15'+struct.pack('<I',CREATE)+b'\xa3'+struct.pack('<I',0x402050)+b'\xc3'
    code[:len(b)]=b;code[0x300:0x306]=relative_call(0x401300,0x401000)+b'\xc3';code[0x400:0x400+len(callback)]=callback
    data=bytearray(0x1000);data[0x200:0x20a]=b'TestClass\0';data[0x220:0x225]=b'Test\0'
    program=Program('window-synthetic','window-original-v1',0x400000,0x3000,[Section('.text',0x401000,len(code),bytes(code)),Section('.data',0x402000,0x1000,bytes(data))],(0x401000,0x401800),{REG:'USER32.dll!RegisterClassA',CREATE:'USER32.dll!CreateWindowExA',NESTED:'SYNTH!physical'})
    return program,WindowCallbackContract(program.sha256,TARGET,TARGET+len(callback),hashlib.sha256(callback).hexdigest(),(REG,regpc,regpc+6),(CREATE,createpc,createpc+6))
def environment(change=None,register_change=None,halt=0,callback=CALLBACK,reject=0):
    program,contract=source(callback);e=Env(program);retained=[]
    def registration(env,call):
        if register_change:return register_change(env,call)
        assert env.read(DESC,40)==struct.pack('<10I',*WORDS)
        return env.register_window_class(call,0x1234)
    def nested(env,call):
        msg,pointer=call.arguments
        if halt==msg:raise Halt('window physical child')
        return 0 if reject==0x81 and msg==0x81 else 0xffffffff if reject==1 and msg==1 else int(msg==0x81)
    def creation(env,call):
        if change:return change(env,call,retained)
        with env.window_operation(call,0x99) as lease:
            retained.append((call,lease))
            for msg,p in ((0x24,lease.minmax_info),(0x81,lease.create_struct),(0x83,lease.window_rect),(1,lease.create_struct)):
                value=env.invoke_window_callback(call,lease,msg,0,p)
                if (msg==0x81 and value==0) or (msg==1 and value==0xffffffff):return 0
        return 0x99
    e.fixture(REG,'stdcall',1,registration);e.fixture(CREATE,'stdcall',12,creation);e.fixture(NESTED,'stdcall',2,nested);e.window_callback(contract)
    e.source_callees[0x401000]=dict(kind='whole',convention='cdecl',argc=0,returns='u32',source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
    e._initial['stack'][:]=bytes(range(256))*(STACK_SIZE//256);e._freeze();return e,retained
def entry(flavor):
    lib=C.CDLL(str(build.library('window-callbacks-selftest',[Path(__file__).with_name('window_callbacks_module.cpp')],flavor)))
    f=lib.claw_window_callbacks_entry;f.argtypes=[U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)];f.restype=U32;return f
def run(e,f,route,ctx=None):
    function=0x401300 if route=='bridge' else 0x401000;ctx=ctx or context(function,head=STACK_TOP+0x100)
    return e.run_original_context(function,ctx,source_return_pc=0x401700) if route=='original' else e.run_native(f,function,0,(),source_context=ctx,source_return_pc=0x401700)
def checks(flavor='O2'):
    f=entry(flavor);found={}
    for function in (0x401000,0x401300):
      for halt in (0,0x24,0x81,0x83,1):
       for frame in (STACK_BASE+256,STACK_TOP,STACK_BASE+STACK_SIZE-4):
        e,retained=environment(halt=halt);initial=context(function,frame,0xffffffff,STACK_TOP+0x100)
        n=NativeSourceContext.from_buffer_copy(initial);o=NativeSourceContext.from_buffer_copy(initial)
        a=run(e,f,'bridge' if function==0x401300 else 'native',n);stack=bytes(e._stack);history=list(e.window_history);records=list(e.callback_executions)
        b=e.run_original_context(function,o,source_return_pc=0x401700);key=f'{function:x}_{halt:x}_{frame:x}'
        found[key+'_memory']=not a.errors and not b.errors and a.heap==b.heap and a.image==b.image and a.spans==b.spans and a.freed==b.freed and stack==e.machine.read(STACK_BASE,STACK_SIZE)
        found[key+'_events']=a.events==b.events and records==e.callback_executions and history==e.window_history
        found[key+'_cpu']=(a.halted and b.halted and a.source_stop==b.source_stop and a.source_stop['function']==NESTED) if halt else a.completed and b.completed and bytes(n)==bytes(o) and a.eax==0x99 and e.get(0x402050)==0x99
        found[key+'_executed']=all(r['entered'] for r in records) and len(records)==((0x24,0x81,0x83,1).index(halt)+1 if halt else 4)
        found[key+'_retired']=not e._window_sessions and not e._window_classes and not e._window_pending and not e._window_handles and not e.machine._physical_pump and e.machine.maximum_active_emulations==1
        try:e.invoke_window_callback(*retained[-1],1,0,retained[-1][1].create_struct);ok=False
        except ContextFault:ok=True
        found[key+'_lease_retired']=ok
        if not all(v for k,v in found.items() if k.startswith(key)):print(key,[str(x) for x in a.errors],[str(x) for x in b.errors],file=sys.stderr)
    for rejection in (0x81,1):
      for route in ('original','native','bridge'):
        e,_=environment(reject=rejection);out=run(e,f,route);found[f'reject_{rejection}_{route}']=out.completed and not out.errors and out.eax==0 and e.window_history[-1]==('failed',0x99)
    found.update(negatives(f));return found

def negatives(f):
    found={}
    def invoke(e,c,l):return e.invoke_window_callback(c,l,0x24,0,l.minmax_info)
    attacks={
      'copy_request':lambda e,c,l:invoke(e,replace(c),l),'copy_lease':lambda e,c,l:invoke(e,c,replace(l)),
      'generation':lambda e,c,l:(setattr(e,'_callback_generation',object()),invoke(e,c,l))[1],
      'hwnd':lambda e,c,l:invoke(e,c,replace(l,hwnd=0x98)),
      'active_code':lambda e,c,l:(e.write(TARGET,b'\x90'),invoke(e,c,l))[1],
      'machine_code':lambda e,c,l:(e.machine.write(TARGET,b'\x90'),invoke(e,c,l))[1],
      'call_code':lambda e,c,l:(e.write(source()[1].create_site[1],b'\x90'),invoke(e,c,l))[1],
      'frame':lambda e,c,l:(e.put(c.stack_pointer+4,1),invoke(e,c,l))[1],
      'cpu':lambda e,c,l:(setattr(c.source_context,'ebp',1),invoke(e,c,l))[1],
      'message':lambda e,c,l:e.invoke_window_callback(c,l,0x82,0,l.minmax_info),
      'pointer':lambda e,c,l:e.invoke_window_callback(c,l,0x24,0,l.create_struct),
      'wparam':lambda e,c,l:e.invoke_window_callback(c,l,0x24,1,l.minmax_info),
      'signed':lambda e,c,l:e.invoke_window_callback(c,l,-1,0,l.minmax_info),
      'create_struct':lambda e,c,l:(e.put(l.create_struct,0x123),invoke(e,c,l))[1],
      'retired_storage':lambda e,c,l:(e.release(l.minmax_info),invoke(e,c,l))[1],
      'program':lambda e,c,l:(setattr(e,'program',replace(e.program)),invoke(e,c,l))[1],
      'override':lambda e,c,l:(e._case_fixtures.__setitem__(TARGET,(Signature(TARGET,'bad','stdcall',4),0)),invoke(e,c,l))[1]}
    for name,attack in attacks.items():
      for route in ('original','native','bridge'):
        def effect(e,c,r,attack=attack):
            with e.window_operation(c,0x99) as l:return attack(e,c,l)
        e,_=environment(change=effect);out=run(e,f,route);found[name+'_'+route]=bool(out.errors) and not out.completed and not out.halted and not e.callback_executions
    for name,effect in {'fake_success':lambda e,c,r:0x99,'empty_success':lambda e,c,r:empty(e,c,0x99),'lifecycle':lambda e,c,r:e.invoke_window_callback(c,None,2,0,0)}.items():
      for route in ('original','native','bridge'):
        e,_=environment(change=effect);out=run(e,f,route);found[name+'_'+route]=bool(out.errors) and not out.completed
    for name,effect in {'fake_atom':lambda e,c:0x1234,'atom_mismatch':lambda e,c:(e.register_window_class(c,0x1234),0x4321)[1],
      'zero_atom':lambda e,c:e.register_window_class(c,0),'high_atom':lambda e,c:e.register_window_class(c,0x10000),
      'target':lambda e,c:(e.put(DESC+4,TARGET+1),e.register_window_class(c,0x1234))[1],
      'copy_register':lambda e,c:e.register_window_class(replace(c),0x1234)}.items():
      for route in ('original','native','bridge'):
        e,_=environment(register_change=effect);out=run(e,f,route);found[name+'_'+route]=bool(out.errors) and not out.completed and not e.callback_executions
    for name,code in {'bad_ret':CALLBACK[:-3]+bytes.fromhex('c21400'),'nonvolatile':bytes.fromhex('43c21000'),'fs':bytes.fromhex('64c70500000000 ffffffff c21000'),'jmp_token':bytes.fromhex('83c414 b800007200 ffe0'),'bad_read':bytes.fromhex('a100000000c21000'),'loop':bytes.fromhex('ebfe')}.items():
      for route in ('original','native','bridge'):
        e,_=environment(callback=code);e.maximum_operations=1000;out=run(e,f,route);found[name+'_'+route]=bool(out.errors) and not out.completed and not out.halted and not e.machine._physical_pump
    for action in ('swallow','write','release','finish'):
      for route in ('original','native','bridge'):
        def effect(e,c,r,action=action):
            with e.window_operation(c,0x99) as l:
                try:invoke(e,c,l)
                except Halt:
                    if action=='write':e.put(0x402050,0xbeef)
                    if action=='release':e.release(l.minmax_info)
                    if action=='finish':return 0x99
            return 0x99
        e,_=environment(change=effect,halt=0x24);out=run(e,f,route);found['deep_'+action+'_'+route]=out.halted and not out.errors and not out.completed and out.source_stop['function']==NESTED and e.get(0x402050)==0 and len(out.spans)==3 and not out.freed
    e,ret=environment();run(e,f,'original');stale=ret[-1];e.override(CREATE,lambda state,call:state.invoke_window_callback(stale[0],stale[1],0x24,0,stale[1].minmax_info));out=run(e,f,'original');found['cross_run']=bool(out.errors) and not e.callback_executions
    e,_=environment(callback=bytes.fromhex('ebfe'));e.callback_timeout_seconds=0.01;out=run(e,f,'original');found['deadline']=bool(out.errors) and 'deadline' in str(out.errors[0])
    e,_=environment(callback=bytes.fromhex('8b442408 3d81000000 0f94c0 0fb6c0 c21000'));out=run(e,f,'original');found['fake_effect_control']=out.completed and e.get(0x402044)==0 and len(out.events)==2
    found.update(extra_checks(f))
    return found

def empty(e,c,result):
    with e.window_operation(c,0x99):pass
    return result

def extra_checks(f):
    found={}
    def sequence(e,c,l):
        for msg,p in ((0x24,l.minmax_info),(0x81,l.create_struct),(0x83,l.window_rect),(1,l.create_struct)):
            value=e.invoke_window_callback(c,l,msg,0,p)
            if (msg==0x81 and value==0) or (msg==1 and value==0xffffffff):return 0
        return l.hwnd
    for route in ('original','native','bridge'):
      for kind in ('class_name','repeated_lease','native_root','cross_VM','retired_lease','wrong_result','mutated_descriptor_snapshot','source_call_code','retired_registration'):
        other,other_ret=environment();run(other,f,'original');old=other_ret[-1]
        def effect(e,c,r,kind=kind):
            if kind=='class_name':e.write(NAME,b'Other\0')
            if kind=='native_root':e._native_source_entry=TARGET
            if kind=='source_call_code':e.machine.write(source()[1].register_site[1],b'\x90')
            if kind=='mutated_descriptor_snapshot':e.put(DESC+4,0)
            with e.window_operation(c,0x99) as l:
                if kind=='repeated_lease':
                    with e.window_operation(c,0x99):pass
                if kind=='cross_VM':return e.invoke_window_callback(c,old[1],0x24,0,old[1].minmax_info)
                if kind=='retired_registration':e._window_classes.clear()
                result=sequence(e,c,l)
            if kind=='retired_lease':return e.invoke_window_callback(c,l,0x24,0,l.minmax_info)
            return 0x88 if kind=='wrong_result' else result
        e,_=environment(change=effect);out=run(e,f,route)
        # Class registration stores a snapshot, not authority to the old descriptor memory.
        # Its original CALL must remain unchanged even across the intervening API lifetime.
        positive=kind=='mutated_descriptor_snapshot' or (kind=='native_root' and route=='original')
        found[kind+'_'+route]=out.completed and not out.errors if positive else bool(out.errors) and not out.completed
      e,_=environment()
      def poison(machine,pc):raise RuntimeError('window hook exception')
      e.machine.observe(TARGET,poison)
      try:out=run(e,f,route);ok=bool(out.errors) and not out.halted
      except RuntimeError as x:ok=str(x)=='window hook exception'
      found['hook_'+route]=ok and not e.machine._physical_pump and not e._window_sessions
      e,_=environment();out=run(e,f,route,context(0x401300 if route=='bridge' else 0x401000,frame=STACK_BASE+96))
      found['frame_lower_bound_'+route]=bool(out.errors) and not out.completed
      e,_=environment(callback=bytes.fromhex('c7442454 efbeadde c21000'));out=run(e,f,route)
      found['parent_frame_'+route]=bool(out.errors) and not out.completed
      e,_=environment(callback=bytes.fromhex('64a100000000 c70000000000 c21000'));out=run(e,f,route)
      found['parent_FS_'+route]=bool(out.errors) and not out.completed
    for name,change in {'hash':dict(program_sha256='wrong'),'body':dict(body_sha256='0'*64),'abi_site':dict(register_site=(REG,0x401000,0x401006)),
                         'list_site':dict(create_site=list(source()[1].create_site)),'body_bounds':dict(body_end=TARGET+4097),'noninteger':dict(target=True)}.items():
        p,c=source();e=Env(p);e.fixture(REG,'stdcall',1,0);e.fixture(CREATE,'stdcall',12,0)
        try:e.window_callback(replace(c,**change));ok=False
        except ContextFault:ok=True
        found['declare_'+name]=ok
    p,c=source();e=Env(p);e.fixture(REG,'cdecl',1,0);e.fixture(CREATE,'stdcall',12,0)
    try:e.window_callback(c);ok=False
    except ContextFault:ok=True
    found['declare_wrong_stdcall']=ok
    e,_=environment()
    try:e.fixture(TARGET,'stdcall',4,0);ok=False
    except ContextFault:ok=True
    found['fixture_target']=ok
    found['no_generic_authority']=TARGET not in e.source_callees
    # Two real source CALLs at the same creation site, with first NCCREATE rejection.
    # The second call reuses numeric HWND with a new lease; registration survives.
    # This is an original-only synthetic control, not an arbitrary callback jump.
    def loop_environment(stale=False):
        e,ret=environment();program=e.program
        sec=program.sections[0];code=bytearray(sec.data)
        end=source()[1].create_site[2]+5
        tail=b'\xff\x05'+struct.pack('<I',0x402060)+b'\x83\x3d'+struct.pack('<I',0x402060)+b'\x01'
        jump=0x401000+0x6f
        tail+=b'\x0f\x84'+struct.pack('<i',jump-(end+len(tail)+6))+b'\xc3'
        code[end-sec.address:end-sec.address+len(tail)]=tail
        changed=replace(program,sections=[replace(sec,data=bytes(code)),program.sections[1]])
        # New independent source program is declared before any execution.
        e=Env(changed);saved=[];attempt=[0]
        e.fixture(REG,'stdcall',1,lambda state,call:state.register_window_class(call,0x1234))
        e.fixture(NESTED,'stdcall',2,lambda state,call:0 if call.arguments[0]!=0x81 or attempt[0]==1 else 1)
        def create(state,call):
            attempt[0]+=1
            with state.window_operation(call,0x99) as lease:
                if saved and stale:return state.invoke_window_callback(call,saved[0],0x24,0,saved[0].minmax_info)
                saved.append(lease);return sequence(state,call,lease)
        e.fixture(CREATE,'stdcall',12,create);e.window_callback(source()[1]);e._freeze()
        out=run(e,f,'original');return e,out,saved
    e,out,leases=loop_environment()
    found['failure_handle_reuse']=out.completed and out.eax==0x99 and len(leases)==2 and leases[0] is not leases[1] and [x[0] for x in e.window_history].count('registered')==1
    e,out,leases=loop_environment(True);found['old_handle_incarnation_rejected']=bool(out.errors) and not out.completed
    # Genuine synthetic callback instructions re-enter the same CreateWindow CALL.
    # Every nested lease has a different handle; the shared callback bound wins.
    recursive=b'\xe9'+struct.pack('<i',0x40106f-(TARGET+5))
    for route in ('original','native','bridge'):
        def recurse(state,call,retained):
            with state.window_operation(call,0x99+len(state._window_handles)) as lease:
                return state.invoke_window_callback(call,lease,0x24,0,lease.minmax_info)
        e,_=environment(callback=recursive,change=recurse);out=run(e,f,route)
        found['shared_callback_depth_'+route]=bool(out.errors) and 'depth exceeded' in str(out.errors[0]) and sum(x['entered'] for x in e.callback_executions)==16 and not e.machine._callback_returns and not e._window_sessions
    return found

def sanitized_checks():
    command,env=build.sanitized_python()
    if command is None:return {'passed':False,'detail':'sanitizer unavailable'}
    child=subprocess.run(command+['-m',__name__,'--sanitize'],env=env,capture_output=True,text=True,timeout=180)
    try:result=json.loads(child.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):result={}
    return dict(result,passed=child.returncode==0 and result.get('failed')==[],returncode=child.returncode,stderr=child.stderr[-4000:])
if __name__=='__main__':
    result=checks('sanitize' if '--sanitize' in sys.argv else 'O0' if '--O0' in sys.argv else 'O2');print(json.dumps({'checked':len(result),'failed':[k for k,v in result.items() if not v]}));raise SystemExit(not all(result.values()))
