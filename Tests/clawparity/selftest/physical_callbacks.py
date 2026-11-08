"""Independent original/native tests for synchronous physical-to-original callbacks."""
import ctypes as C
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from .. import build
from ..env import Env, Halt, DialogCallbackContract, NativeSourceContext, NativeHost, U32
from ..kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_FIELDS, PHYSICAL_CALLBACK_RETURN, ContextFault, CONTEXT_REGISTERS
from ..program import Program, Section
from .source_context import context
from .stack import relative_call

CALLBACK=bytes.fromhex('55 89e5 8b4510 a344204000 ff0548204000 648b1500000000 89154c204000 8b4d14 8901 50 ff1504204000 89ec 5d c21000')
def program(callback=CALLBACK):
    code=bytearray(b'\xcc'*0x400)
    caller=bytes.fromhex('6a00 6800114000 6a00 6880204000 6a51 ff1500204000 c3')
    code[:len(caller)]=caller
    code[0x40:0x46]=relative_call(0x401040,0x401000)+b'\xc3'
    code[0x100:0x100+len(callback)]=callback
    return Program('dialog-callback-synthetic','synthetic-original-v1',0x400000,0x3000,
        [Section('.text',0x401000,len(code),bytes(code)),Section('.data',0x402000,0x1000,bytes(0x1000))],
        (0x401000,0x401400),{0x402000:'USER32.dll!DialogBoxParamA',0x402004:'SYNTH!nested'})
def contract(callback=CALLBACK):
    return DialogCallbackContract('synthetic-original-v1',0x402000,0x401010,0x401016,0x401100,
                                  0x401100+len(callback),hashlib.sha256(callback).hexdigest())
def environment(halt=False,callback=CALLBACK,effect_change=None):
    e=Env(program(callback)); observations=[]; retained=[]
    pointer=e.object(4)
    def nested(env,call):
        observations.append((env.side,'nested',call.arguments,call.stack_pointer,
                             tuple(getattr(call.source_context,n) for n in CONTEXT_FIELDS)))
        if halt and env.calls_so_far(0x402004)==2: raise Halt('deep callback service')
        return 0xabcd
    def dialog(env,call):
        retained.append(call)
        if effect_change:return effect_change(env,call,pointer)
        env.put(0x402040,0xdeadbeef)
        values=[]
        for value in (0x33,0x44):
            values.append(env.invoke_dialog_callback(call,(0x55,0x111,value,pointer)))
        observations.append((env.side,'returned',tuple(values)))
        return 0x99
    e.fixture(0x402000,'stdcall',5,dialog)
    e.fixture(0x402004,'stdcall',1,nested)
    e.dialog_callback(contract(callback))
    e.source_callees[0x401000]=dict(kind='whole',convention='cdecl',argc=0,returns='u32',
        source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
    e._initial['stack'][:]=bytes(range(256))*(STACK_SIZE//256)
    e._freeze()
    return e,pointer,observations,retained
def entry(flavor, symbol='claw_physical_callbacks_entry'):
    lib=C.CDLL(str(build.library('physical-callbacks-selftest',[Path(__file__).with_name('physical_callbacks_module.cpp')],flavor)))
    f=getattr(lib,symbol)
    f.argtypes=[U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)];f.restype=U32
    return f
def checks(flavor='O2'):
    f=entry(flavor);found={}
    for function in (0x401000,0x401040):
      for halt in (False,True):
       for frame in (STACK_BASE+256,STACK_TOP,STACK_BASE+STACK_SIZE-4):
        for ebp in (0,0xffffffff):
            e,pointer,observed,retained=environment(halt)
            initial=context(function,frame,ebp,STACK_TOP+0x100)
            n,o=NativeSourceContext.from_buffer_copy(initial),NativeSourceContext.from_buffer_copy(initial)
            native=e.run_native(f,function,0,(),source_context=n,source_return_pc=0x401380)
            stack=bytes(e._stack);records=list(e.callback_executions)
            from unicorn.x86_const import UC_X86_REG_ESP
            deepest_native_esp=e.machine.register(UC_X86_REG_ESP)
            original=e.run_original_context(function,o,source_return_pc=0x401380)
            key=f'{function:x}_{halt}_{frame:x}_{ebp:x}'
            found[key+'_effects']=(not native.errors and not original.errors and native.events==original.events and native.heap==original.heap and native.image==original.image)
            found[key+'_stack']=stack==e.machine.read(STACK_BASE,STACK_SIZE)
            found[key+'_cpu']=(native.halted and original.halted and native.source_stop==original.source_stop and native.source_stop['function']==0x402004) if halt else (native.completed and original.completed and bytes(n)==bytes(o) and native.eax==0x99)
            found[key+'_actual_callbacks']=len(records)==2 and records==e.callback_executions and e.get(pointer)==0x44 and e.get(0x402048)==2 and e.get(0x402040)==0xdeadbeef and all(x['entered'] for x in records)
            if halt: found[key+'_no_parent_restore']=deepest_native_esp==native.source_stop['registers']['esp']
            found[key+'_single_emulation']=e.machine.maximum_active_emulations==1
            found[key+'_retirement']=not e._physical_requests and not e.machine._physical_pump and not e.machine._callback_returns and all(not lo <= PHYSICAL_CALLBACK_RETURN <= hi for lo,hi,permissions in e.machine.uc.mem_regions())
            try:e.invoke_dialog_callback(retained[-1],(0,0,0,pointer));rejected=False
            except ContextFault:rejected=True
            found[key+'_retired_request']=rejected
            if not all(v for k,v in found.items() if k.startswith(key)):
                print(json.dumps({'failed_case':key,'native_errors':[str(x) for x in native.errors],'original_errors':[str(x) for x in original.errors],'native_fault':native.fault,'native_stop':native.source_stop,'original_stop':original.source_stop}),file=sys.stderr)
    found.update(negative_checks(f))
    found.update(owned_checks(flavor))
    found.update(modal_owned_checks(flavor))
    found.update(cpu_owned_checks(flavor))
    found.update(claw_checks(flavor))
    return found

def negative_checks(f):
    from ..env import Signature, Call, SourceBudgetFault
    from unicorn.x86_const import UC_X86_REG_ESP
    found={}
    def invoke(e,c,p):return e.invoke_dialog_callback(c,(0x55,0x111,0x33,p))
    def altered_request(field,value):
        return lambda e,c,p:invoke(e,replace(c,**{field:value}),p)
    effects={
      'copy':lambda e,c,p:invoke(e,replace(c),p),
      'wrong_iat':altered_request('function',0x402004),
      'wrong_return_pc':altered_request('source_return_pc',0x401017),
      'wrong_callback_operand':lambda e,c,p:invoke(e,replace(c,arguments=c.arguments[:3]+(0x401101,0)),p),
      'wrong_argument_arity':lambda e,c,p:e.invoke_dialog_callback(c,(1,2,3)),
      'signed_argument':lambda e,c,p:e.invoke_dialog_callback(c,(1,2,-1,p)),
      'boolean_argument':lambda e,c,p:e.invoke_dialog_callback(c,(1,2,True,p)),
      'argument_container':lambda e,c,p:e.invoke_dialog_callback(c,[1,2,3,p]),
      'changed_source_cpu':lambda e,c,p:(setattr(c.source_context,'ebx',42),invoke(e,c,p))[1],
      'changed_source_mask':lambda e,c,p:(setattr(c.source_context,'inputMask',0x5c0),invoke(e,c,p))[1],
      'changed_physical_frame':lambda e,c,p:(e.put(c.stack_pointer+4,42),invoke(e,c,p))[1],
      'changed_callback_code':lambda e,c,p:(e.machine.write(0x401100,b'\x90'),invoke(e,c,p))[1],
      'changed_CALL_code':lambda e,c,p:(e.machine.write(0x401010,b'\x90'),invoke(e,c,p))[1],
      'changed_active_callback_code':lambda e,c,p:(e.write(0x401100,b'\x90'),invoke(e,c,p))[1],
      'changed_active_CALL_code':lambda e,c,p:(e.write(0x401010,b'\x90'),invoke(e,c,p))[1],
      'native_owned_callback':lambda e,c,p:(setattr(e,'_native_source_entry',0x401100),invoke(e,c,p))[1],
      'original_override':lambda e,c,p:(e._case_fixtures.__setitem__(0x401100,(Signature(0x401100,'bad','stdcall',4),0)),invoke(e,c,p))[1],
      'changed_program_owner':lambda e,c,p:(setattr(e,'program',replace(e.program)),invoke(e,c,p))[1],
      'retired_generation':lambda e,c,p:(setattr(e,'_callback_generation',object()),invoke(e,c,p))[1],
    }
    for name,effect in effects.items():
      for route in ('original','native','bridge'):
        if name=='native_owned_callback' and route=='original':continue
        e,p,obs,ret=environment(effect_change=effect)
        function=0x401040 if route=='bridge' else 0x401000
        ctx=context(function)
        out=(e.run_original_context(function,ctx,source_return_pc=0x401380) if route=='original' else
             e.run_native(f,function,0,(),source_context=ctx,source_return_pc=0x401380))
        found['reject_'+name+'_'+route]=bool(out.errors) and not out.completed and not out.halted and not e.callback_executions and not e.machine._physical_pump and not e._physical_requests
    # A stale prior native-root marker never owns a later original-only graph.
    e,p,obs,ret=environment();e._native_source_entry=0x401100
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['stale_native_root_does_not_own_original_graph']=out.completed and not out.errors and len(e.callback_executions)==2
    # Typed declarations are rejected before source execution.
    for name,change in {
       'program_hash':dict(program_sha256='wrong'), 'iat':dict(service=0x402004),
       'callsite':dict(call_pc=0x401011), 'return_pc':dict(return_pc=0x401017),
       'body_hash':dict(body_sha256='0'*64), 'shifted_body':dict(target=0x401101),
       'body_bounds':dict(body_end=0x402000), 'noninteger':dict(target=True),
    }.items():
        e=Env(program());e.fixture(0x402000,'stdcall',5,0)
        try:e.dialog_callback(replace(contract(),**change));rejected=False
        except ContextFault:rejected=True
        found['declaration_'+name]=rejected
    # The exact final opcode/pop and nonvolatile/FS state are checked after real execution.
    bad_code={
       'wrong_ret':CALLBACK[:-3]+bytes.fromhex('c21400'),
       'no_ret':bytes.fromhex('83c414 b800007200 ffe0'),
       'nonvolatile':bytes.fromhex('43 c21000'),
       'fs':bytes.fromhex('64 c70500000000 ffffffff c21000'),
       'invalid_memory':bytes.fromhex('a100000000 c21000'),
       'parent_frame':bytes.fromhex('c7442454 efbeadde c21000'),
       'parent_fs_record':bytes.fromhex('64a100000000 c70000000000 c21000'),
       'infinite_loop':bytes.fromhex('ebfe'),
    }
    for name,code in bad_code.items():
      for route in ('original','native','bridge'):
        e,p,obs,ret=environment(callback=code)
        if name=='infinite_loop':e.maximum_operations=200
        function=0x401040 if route=='bridge' else 0x401000
        ctx=context(function,head=STACK_TOP+0x100)
        out=(e.run_original_context(function,ctx,source_return_pc=0x401380) if route=='original' else
             e.run_native(f,function,0,(),source_context=ctx,source_return_pc=0x401380))
        found['execution_reject_'+name+'_'+route]=bool(out.errors) and not out.completed and not out.halted and len(e.callback_executions)==1 and not e.callback_executions[0]['returned'] and not e.machine._physical_pump
    # Borrowed source backing stays shared, including the OS dispatcher's live stack scratch.
    def stack_alias(e,c,p):
        scratch=c.stack_pointer-32;e.put(scratch,0xabcdef)
        result=e.invoke_dialog_callback(c,(0x55,0x111,0x42,scratch))
        if e.get(scratch)!=0x42:raise AssertionError('callback did not update live stack alias')
        return result
    e,p,obs,ret=environment(effect_change=stack_alias)
    n=context();o=context()
    a=e.run_native(f,0x401000,0,(),source_context=n,source_return_pc=0x401380);stack=bytes(e._stack)
    b=e.run_original_context(0x401000,o,source_return_pc=0x401380)
    found['live_parent_stack_alias']=a.completed and b.completed and a.events==b.events and stack==e.machine.read(STACK_BASE,STACK_SIZE)
    # The same numeric frame/site cannot renew an old request in a later run.
    e,p,obs,ret=environment();e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    stale=ret[0]
    e.override(0x402000,lambda state,request:state.invoke_dialog_callback(stale,(0,0,0,p)))
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['cross_run_stale_request']=bool(out.errors) and not e.callback_executions
    # A hook exception remains a failure and retires the pump, never a fabricated Halt.
    for route in ('original','native','bridge'):
        e,p,obs,ret=environment()
        def poison(machine,pc):raise RuntimeError('synthetic callback hook failure')
        e.machine.observe(0x401100,poison)
        function=0x401040 if route=='bridge' else 0x401000
        try:
            out=(e.run_original_context(function,context(function),source_return_pc=0x401380) if route=='original' else
                 e.run_native(f,function,0,(),source_context=context(function),source_return_pc=0x401380))
            rejected=bool(out.errors) and not out.halted
        except RuntimeError as error:rejected=str(error)=='synthetic callback hook failure'
        found['hook_exception_'+route]=rejected and not e.machine._physical_pump and not e._physical_requests
    # Graph deadline is shared with callback loops and must terminate without a nested timer.
    e,p,obs,ret=environment(callback=bytes.fromhex('ebfe'))
    e.callback_timeout_seconds=0.01
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['shared_deadline']=bool(out.errors) and 'deadline' in str(out.errors[0]) and not out.halted
    # A shallow physical frame cannot allocate the declared dispatcher frame.
    e,p,obs,ret=environment()
    out=e.run_original_context(0x401000,context(frame=STACK_BASE+32),source_return_pc=0x401380)
    found['dispatcher_lower_bound']=bool(out.errors) and 'dispatcher frame' in str(out.errors[0])
    # Malformed callbacks cannot swallow a terminal result and resume their parents.
    for poison in ('halt','fault','stop_tamper'):
      for route in ('original','native','bridge'):
        def swallow(e,c,p,poison=poison):
            try:
                e.invoke_dialog_callback(c,(0x55,0x111,0x33,p))
                e.invoke_dialog_callback(c,(0x55,0x111,0x44,p))
            except (Halt,ContextFault):
                if poison=='stop_tamper':e._source_stop['registers']['eax']^=1
                return 123
        e,p,obs,ret=environment(halt=poison!='fault',callback=bytes.fromhex('43c21000') if poison=='fault' else CALLBACK,effect_change=swallow)
        function=0x401040 if route=='bridge' else 0x401000
        out=(e.run_original_context(function,context(function),source_return_pc=0x401380) if route=='original' else
             e.run_native(f,function,0,(),source_context=context(function),source_return_pc=0x401380))
        found['cannot_swallow_'+poison+'_'+route]=(out.halted and not out.errors if poison=='halt' else bool(out.errors) and not out.halted) and not out.completed
    for operation in ('write','release','allocate'):
        def mutate_after_halt(e,c,p,operation=operation):
            try:
                e.invoke_dialog_callback(c,(0x55,0x111,0x33,p))
                e.invoke_dialog_callback(c,(0x55,0x111,0x44,p))
            except Halt:
                if operation=='write':e.put(0x402040,0xfeed)
                elif operation=='release':e.release(p)
                else:e.object(4)
            return 123
        e,p,obs,ret=environment(halt=True,effect_change=mutate_after_halt)
        before=dict(e.spans)
        out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
        found['terminal_prefix_blocks_'+operation]=out.halted and not out.errors and e.spans==before and not e.freed and e.get(0x402040)==0
    # Recursive physical DialogBox requests execute the same genuine synthetic CALL,
    # and consume one bounded graph rather than renewing operation/depth limits.
    prefix=bytes.fromhex('6a00 6800114000 6a00 6880204000 6a51')
    recursive=prefix+b'\xe9'+struct.pack('<i',0x401010-(0x401100+len(prefix)+5))
    e,p,obs,ret=environment(callback=recursive)
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['shared_callback_depth']=bool(out.errors) and 'depth exceeded' in str(out.errors[0]) and sum(x['entered'] for x in e.callback_executions)==16 and not e.machine._callback_returns
    e,p,obs,ret=environment()
    out=e.run_original_context(0x401000,context(head=STACK_TOP-104),source_return_pc=0x401380)
    found['dispatcher_rejects_fs_overlap']=bool(out.errors) and 'overlaps parent FS' in str(out.errors[0]) and not any(x['entered'] for x in e.callback_executions)
    e,p,obs,ret=environment()
    found['no_generic_source_callee_authority']=0x401100 not in e.source_callees
    try:e.fixture(0x401100,'stdcall',4,0);rejected=False
    except ContextFault:rejected=True
    found['public_fixture_override_rejected']=rejected
    # A copied request from another live-compatible VM never gains authority.
    other,p2,obs2,ret2=environment()
    other.run_original_context(0x401000,context(),source_return_pc=0x401380)
    e,p,obs,ret=environment(effect_change=lambda state,request,pointer:state.invoke_dialog_callback(ret2[0],(0,0,0,pointer)))
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['cross_VM_request_rejected']=bool(out.errors) and not e.callback_executions
    # Explicit negative controls: a Python constant or a guest return alone cannot
    # satisfy the independent expectation of two callback stores and nested events.
    e,p,obs,ret=environment(effect_change=lambda state,request,pointer:0x99)
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['control_fake_callback_detected']=out.completed and not e.callback_executions and e.get(0x402048)!=2
    e,p,obs,ret=environment(callback=bytes.fromhex('b8cdab0000 c21000'))
    out=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['control_omitted_callback_effects_detected']=out.completed and len(e.callback_executions)==2 and e.get(0x402048)!=2 and len(out.events)!=3
    return found

def owned_checks(flavor):
    # Independent ordinary native callback: the OS owns its frame/pop, while
    # game stores must come from the selected module (including the mutant).
    code=bytes.fromhex('8b44240c a344204000 8b4c2410 8901 b8cdab0000 c21000')
    found={}
    for route in ('native','bridge'):
      for mutant in (False,True):
        e,p,obs,ret=environment(callback=code)
        # Rebuild the setup declaration rather than change live authority.
        e._dialog_contracts.clear();e._dialog_owners.clear();e.backend='initial'
        e.dialog_callback(replace(contract(code),native_owned=True));e._freeze()
        f=entry(flavor,'claw_physical_callbacks_mutant' if mutant else 'claw_physical_callbacks_selected')
        function=0x401040 if route=='bridge' else 0x401000
        a=e.run_native(f,function,0,(),source_context=context(function),source_return_pc=0x401380)
        b=e.run_original_context(function,context(function),source_return_pc=0x401380)
        matches=a.heap==b.heap and a.image==b.image and a.events==b.events
        found[f'owned_{route}_{mutant}']=a.completed and b.completed and not a.errors and not b.errors and matches != mutant
    # A later case can elect the same address as original-backed. Persistent
    # VM observers must consult the new case's declaration, not stale ownership.
    e._begin_case(None)
    p=e.object(4)
    e.fixture(0x402000,'stdcall',5,lambda env,call:env.invoke_dialog_callback(call,(0x55,0x111,0x33,p)))
    e.dialog_callback(contract(code));e._freeze()
    out=e.run_native(entry(flavor),0x401000,0,(),source_context=context(),source_return_pc=0x401380)
    found['owned_observer_retires_between_cases']=out.completed and not out.errors and e.get(p)==0x33
    return found


def modal_owned_checks(flavor):
    # This independently authored modal callback has both lifecycle branches,
    # one ordinary original dependency, and a physical EndDialog descendant.
    init=bytes.fromhex('c7054420400034120000 b801000000 c21000')
    prefix=bytes.fromhex('817c240810010000 7500')
    prefix=prefix[:-1]+bytes([len(init)])
    start=0x401100+len(prefix)+len(init)
    command=bytes.fromhex('8b44240c a344204000')
    command+=relative_call(start+len(command),0x401200)
    command+=bytes.fromhex('ff74240c ff742408 ff1508204000 b801000000 c21000')
    code=prefix+init+command
    found={}
    for route in ('original','native','bridge'):
      for attack in (None,'reentrant','failed_end','swallowed_halt','changed_contract','changed_end_owner','end_twice'):
        p=program(code)
        text=bytearray(p.sections[0].data)
        text[0x200:0x20b]=bytes.fromhex('c7054820400078560000 c3')
        p=replace(p,sections=[replace(p.sections[0],data=bytes(text)),p.sections[1]],
                  imports={**p.imports,0x402008:'USER32.dll!EndDialog'})
        e=Env(p);ending=[];requests=[]
        def end(env,call):
            if attack=='reentrant':env.invoke_dialog_callback(requests[-1],(0x55,0x111,1,0))
            if attack=='swallowed_halt':raise Halt('owned callback descendant')
            ending.append(call.arguments[1]);return 0 if attack=='failed_end' else 1
        def dialog(env,call):
            requests.append(call)
            env.invoke_dialog_callback(call,(0x55,0x110,0,0))
            if attack=='changed_contract':
                key=next(iter(env._dialog_contracts))
                env._dialog_contracts[key]=replace(env._dialog_contracts[key],native_owned=False)
            if attack=='changed_end_owner':
                from ..env import Signature
                env._case_fixtures[0x402008]=(Signature(0x402008,'changed','stdcall',2),end)
            try:env.invoke_dialog_callback(call,(0x55,0x111,1,0))
            except (Halt,ContextFault):
                if attack!='swallowed_halt':raise
            if attack=='end_twice':env.invoke_dialog_callback(call,(0x55,0x111,1,0))
            return ending[-1] if ending else 1
        e.fixture(0x402000,'stdcall',5,dialog);e.fixture(0x402008,'stdcall',2,end)
        e.dialog_callback(replace(contract(code),native_owned=True,end_service=0x402008))
        e.source_callees[0x401000]=dict(kind='whole',convention='cdecl',argc=0,returns='u32',
            source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
        e._freeze()
        function=0x401040 if route=='bridge' else 0x401000
        out=(e.run_original_context(function,context(function),source_return_pc=0x401380) if route=='original' else
             e.run_native(entry(flavor,'claw_physical_callbacks_selected'),function,0,(),source_context=context(function),source_return_pc=0x401380))
        if attack is None:
            passed=out.completed and not out.errors and e.get(0x402044)==1 and e.get(0x402048)==0x5678 and ending==[1]
        else:passed=not out.completed and (bool(out.errors) or out.halted)
        found[f'modal_owned_{route}_{attack}']=passed and not e._dialog_sessions and not e._physical_requests and not e.machine._physical_pump
        if not passed:print('owned modal',route,attack,out.completed,[str(x) for x in out.errors],file=sys.stderr)
    return found


def cpu_owned_checks(flavor):
    # MOV/PUSH/POP-only CPU witnesses keep flags independently specified. The
    # unchanged dependency spills the callback's live ESI/EDI, not its parent's.
    code=bytes.fromhex('56 57 be10325476 bf78563412 b899000000 ff742414')
    code+=relative_call(0x401100+len(code),0x401200)
    assert 0x401100+len(code)==0x40111a
    code+=bytes.fromhex('ff742414 ff1504204000')
    assert 0x401100+len(code)==0x401124
    code+=bytes.fromhex('5f 5e b8cdab0000 c21000')
    dependency=bytes.fromhex('56 57 893544204000 893d48204000 ff74240c ff1504204000 5f 5e c20400')
    found={};f=entry(flavor,'claw_physical_callbacks_cpu')
    def setup(halt_at=0,attack=0,swallow=False,dependency_code=dependency,change_live=False):
        e,p,obs,ret=environment(callback=code)
        original=e.program
        text=bytearray(original.sections[0].data);text[0x200:0x200+len(dependency_code)]=dependency_code
        original=replace(original,sections=[replace(original.sections[0],data=bytes(text)),original.sections[1]])
        e=Env(original);saved=[]
        def nested(env,call):
            if change_live and env.side=='native':env._host.callbackCPU.contents.cpu.esi^=1
            if env.calls_so_far(0x402004)==halt_at:raise Halt('live owned CPU stop')
            return 0x5678
        def dialog(env,call):
            saved.append(call)
            try:
                for v in (0x33,0x44):env.invoke_dialog_callback(call,(0x55,0x111,v,0))
            except (Halt,ContextFault):
                if not swallow:raise
                env.put(0x402074,1) # poison must prevent post-failure effects
            return 0x99
        e.fixture(0x402000,'stdcall',5,dialog);e.fixture(0x402004,'stdcall',1,nested)
        e.dialog_callback(replace(contract(code),native_owned=True))
        e.source_callees[0x401200]=dict(kind='whole',convention='stdcall',argc=1,returns='u32',
            source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472,optional=True))
        e.source_callees[0x401000]=dict(kind='whole',convention='cdecl',argc=0,returns='u32',
            source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
        e.put(0x402070,attack)
        e._initial['stack'][:]=bytes(range(256))*(STACK_SIZE//256)
        e._freeze()
        return e,saved
    for function in (0x401000,0x401040):
      for halt_at in (0,1,2,3,4):
       for swallow in (False,True) if halt_at else (False,):
        e,saved=setup(halt_at,swallow=swallow)
        n=context(function,head=STACK_TOP+0x100);o=NativeSourceContext.from_buffer_copy(n)
        a=e.run_native(f,function,0,(),source_context=n,source_return_pc=0x401380)
        stack=bytes(e._stack);records=list(e.callback_executions)
        deepest=tuple(e.machine.register(r) for r in CONTEXT_REGISTERS)
        bridged=list(e.bridged);spills=(e.get(0x402044),e.get(0x402048))
        b=e.run_original_context(function,o,source_return_pc=0x401380)
        key=f'owned_cpu_{function:x}_{halt_at}_{swallow}'
        found[key+'_effects']=not a.errors and not b.errors and a.events==b.events and a.heap==b.heap and a.image==b.image
        found[key+'_stack']=stack==e.machine.read(STACK_BASE,STACK_SIZE)
        found[key+'_cpu']=(a.halted and b.halted and a.source_stop==b.source_stop and
            deepest==tuple(a.source_stop['registers'][n] for n in CONTEXT_FIELDS[:-1])) if halt_at else (a.completed and b.completed and bytes(n)==bytes(o))
        found[key+'_retirement']=not e._dialog_cpu_scope and not e._host.callbackCPU and not e._physical_requests and not e.machine._physical_pump
        found[key+'_original_dependency']=0x401200 in bridged and spills==(0x76543210,0x12345678)
        if not all(v for k,v in found.items() if k.startswith(key)):
            print(key,[str(x) for x in a.errors],[str(x) for x in b.errors],a.source_stop,b.source_stop,file=sys.stderr)
    for attack in range(1,15):
        e,saved=setup(attack=attack)
        out=e.run_native(f,0x401000,0,(),source_context=context(),source_return_pc=0x401380)
        found[f'owned_cpu_reject_{attack}']=bool(out.errors) and not out.completed and not out.halted and not e._host.callbackCPU and not e._dialog_cpu_scope
    for attack in ('vm','program','generation','contract','service','retired'):
        e,saved=setup()
        def selected(function,receiver,arguments,count,host,result):
            if function==0x401100:
                scope=list(e._dialog_cpu_scope)
                if attack=='vm':scope[2]=object()
                if attack=='program':scope[3]=object()
                if attack=='service':
                    signature,effect=e._case_fixtures[0x402000]
                    e._case_fixtures[0x402000]=(replace(signature),effect)
                if attack=='generation':scope[4]=object()
                if attack=='contract':scope[5]=replace(scope[5])
                if attack=='retired':scope=None
                e._dialog_cpu_scope=tuple(scope) if scope else None
            return f(function,receiver,arguments,count,host,result)
        out=e.run_native(selected,0x401000,0,(),source_context=context(),source_return_pc=0x401380)
        found['owned_cpu_reject_'+attack]=bool(out.errors) and not out.completed and not e._host.callbackCPU and not e._dialog_cpu_scope
    e,saved=setup(change_live=True)
    out=e.run_native(f,0x401000,0,(),source_context=context(),source_return_pc=0x401380)
    found['owned_cpu_reject_mutation_during_borrow']=bool(out.errors) and not out.completed and len(e.callback_executions)==1
    # Neither a C++ entry fault nor a deeper original memory fault restores the
    # suspended parent. Compare the actual failure prefix on both backends.
    e,saved=setup(dependency_code=bytes.fromhex('56 57 a100000000'))
    a=e.run_native(f,0x401000,0,(),source_context=context(),source_return_pc=0x401380)
    stack=bytes(e._stack);cpu=tuple(e.machine.register(r) for r in CONTEXT_REGISTERS)
    b=e.run_original_context(0x401000,context(),source_return_pc=0x401380)
    found['owned_cpu_original_fault_prefix']=(bool(a.errors) and bool(b.errors) and not a.completed and not b.completed
        and a.events==b.events and a.heap==b.heap and a.image==b.image and stack==e.machine.read(STACK_BASE,STACK_SIZE)
        and cpu==tuple(e.machine.register(r) for r in CONTEXT_REGISTERS))
    # A retained lease and matching numeric frame cannot revive a retired owner.
    from ..env import NativeCallbackCPU, NativeCall
    e,saved=setup();retained=[]
    def retain(function,receiver,arguments,count,host,result):
        if function==0x401100:retained.append(NativeCallbackCPU.from_buffer_copy(e._host.callbackCPU.contents))
        return f(function,receiver,arguments,count,host,result)
    out=e.run_native(retain,0x401000,0,(),source_context=context(),source_return_pc=0x401380)
    raw=NativeCall();raw.function=0x401200;raw.callbackCPU=C.pointer(retained[-1]);raw.callbackActivation=retained[-1].activation
    prior=list(e.events);e._native_call(None,C.pointer(raw))
    found['owned_cpu_reject_retired_lease']=out.completed and e._host.fault==5 and e.events==prior and 'no live owner' in str(e.errors[-1])
    return found


def claw_environment(target=0x49b630, attack=None):
    from ..program import claw
    e=Env(claw());physical={};endings=[];retained=[];reached=[]
    app=e.object(0x68);window=e.object(8);module=e.object(0x10);manager=e.object(0x10)
    players=[e.object(0x2640) for _ in range(3)]
    nodes=[e.object(12) for _ in players]
    for i,(player,name) in enumerate(zip(players,(b'Player',b'Claw',b'Swash'))):
        e.write(player+0x14,name+b'\0');e.write(player+0x36,b'Home\0');e.write(player+0x88,b'Info\0')
        e.put(nodes[i],nodes[i+1] if i+1<len(nodes) else 0,0,player)
    e.put(manager+4,nodes[0]);e.put(manager+12,len(nodes))
    e.put(app+4,window,module);e.put(window+4,0x9090);e.put(module+12,0x5151)
    e.put(app+0x60,manager,players[1]);e.put(0x5371fc,app);e.put(0x537204,0)
    e.put(0x537e88,0);e.put(0x540e88,0)
    def get_item(env,call):return 0x10000+call.arguments[1]
    def text(env,call):return 1
    def send(env,call):
        hwnd,msg,w,l=call.arguments
        state=physical.setdefault(hwnd,dict(items=[],selected=-1))
        if msg==0x184:state.update(items=[],selected=-1);return 0
        if msg==0x180:state['items'].append(env.cstr(l));return len(state['items'])-1
        if msg==0x18f:
            needle=env.cstr(l)
            return next((i for i,x in enumerate(state['items']) if x==needle),0xffffffff)
        if msg==0x186:state['selected']=w;return w
        if msg==0x188:return state['selected'] & 0xffffffff
        if msg==0x189:
            if w>=len(state['items']):return 0xffffffff
            value=state['items'][w]
            if isinstance(value,str):value=value.encode()
            env.write(l,value+b'\0');return len(value)
        raise AssertionError(f'unsupported physical message {msg:#x}')
    def end(env,call):
        endings.append((call.arguments,env.get(0x53ebe0)))
        return 1
    def dialog(env,call):
        physical.clear();endings.clear();retained.append(call)
        if attack=='fabricated_positive':return 1
        if attack=='creation_failure':return 0xffffffff
        hwnd=0x7777
        env.invoke_dialog_callback(call,(hwnd,0x110,0,call.arguments[4]))
        if attack=='repeat_init':return env.invoke_dialog_callback(call,(hwnd,0x110,0,call.arguments[4]))
        if attack=='wrong_hwnd':return env.invoke_dialog_callback(call,(hwnd+1,0x111,1,0))
        if attack=='copied_request':return env.invoke_dialog_callback(replace(call),(hwnd,0x111,1,0))
        if not endings:
            state=physical.get(0x1043b)
            if state is not None:
                state['selected']=next((i for i,x in enumerate(state['items']) if x in ('Swash',b'Swash')),-1)
                if attack=='no_selection':state['selected']=-1
            env.invoke_dialog_callback(call,(hwnd,0x111,2 if attack=='cancel' else 1,0))
        if attack=='after_end':return env.invoke_dialog_callback(call,(hwnd,0x111,1,0))
        if attack=='wrong_result':return (endings[-1][0][1]+1)&0xffffffff
        return endings[-1][0][1] if endings else 0
    for addr,argc,effect in ((0x546d2c,5,dialog),(0x546d34,2,end),(0x546d40,2,get_item),
        (0x546d3c,3,text),(0x546d44,4,send),(0x546d54,1,1),(0x546df0,0,100),(0x546d50,4,1),
        (0x546d18,2,0),(0x546ca0,2,0),(0x546ca4,1,0)):
        e.fixture(addr,'stdcall',argc,effect)
    identities=((0x49b730,0x49b83d,'253fb62a4a33e89b2b6e3ac0ec33fbbf7f7ca536159e99bd4db6a61d22fc71e3'),
                (0x49b160,0x49b393,'e9c3e3f6220163984476c7b77733d431504b22d871fc674565c7ff2016d4153e'),
                (0x49b630,0x49b72b,'d8d4f3f1cf5f6ec2f6becf08c4f3fe2830cffe71da5e10116db49105bf88ad6d'))
    for address,stop,digest in identities:
        e.dialog_callback(DialogCallbackContract(e.program.sha256,0x546d2c,0x42bb7b,0x42bb81,
            address,stop,digest,native_owned=address==0x49b730))
    e.dialog_callback(DialogCallbackContract(e.program.sha256,0x546d2c,0x453989,0x45398f,
        0x453a10,0x453b0f,'a5b7da2f873d90e9678dbb766107776d4c76a3ce05f4eea3835dac10d1832c16'))
    for pc in (0x42bb7b,0x49afd0,0x49bee0,0x49b661,0x49b67e):
        e.machine.observe(pc,lambda machine,address:reached.append(address))
    # Also expose this physical import as an isolated root for native-buffer
    # parity. Full wrapper probes above still execute the real indirect CALL.
    e.machine.intercept(0x546d2c)
    e._freeze()
    return e,app,players,endings,reached


def claw_checks(flavor):
    found={};f=entry(flavor)
    # Real original wrappers reach the real CALL instruction, all three bodies,
    # and the removal lookup/store/EndDialog(1) without any game fixtures.
    for target,template in ((0x49b730,0x525f30),(0x49b160,0x525f3c),(0x49b630,0x525f48)):
        e,app,players,endings,reached=claw_environment(target)
        ctx=context(0x42bb00);ctx.ecx=app
        out=e.run_original_context(0x42bb00,ctx,source_return_pc=0x42bbdf,
                                  source_convention='thiscall',receiver=app,arguments=(template,target))
        prefix=f'claw_{target:x}'
        found[prefix+'_actual_callsite']=out.completed and not out.errors and 0x42bb7b in reached
        found[prefix+'_body']=len(e.callback_executions)==2 and all(x['target']==target and x['entered'] and x['returned'] for x in e.callback_executions)
        found[prefix+'_end']=bool(endings) and endings[-1][0]==(0x7777,1 if target==0x49b630 else 0)
        if target==0x49b730:found[prefix+'_selected']=e.get(app+0x64)==players[2]
        if target==0x49b160:found[prefix+'_initialized']=e.get(0x53ebe4)==0x10443 and e.get(0x53ebe8)==0x10446
        if target==0x49b630:
            found[prefix+'_real_removal']=all(pc in reached for pc in (0x49afd0,0x49bee0,0x49b661,0x49b67e)) and endings[-1][1]==players[2] and out.eax==1
        if out.errors:print(prefix,[str(x) for x in out.errors],file=sys.stderr)
    # A native-backed physical boundary shares the same callback heap/globals
    # and stack as the original boundary. The body identities are not copied.
    for target in (0x49b160,0x49b630):
      for attack in (None,'cancel','no_selection','creation_failure'):
        e,app,players,endings,reached=claw_environment(target,attack)
        args=(0x5151,0x525f3c if target==0x49b160 else 0x525f48,0x9090,target,0)
        a=e.run_native(f,0x546d2c,0,args,source_context=context(0x546d2c),source_return_pc=0x42bb81,source_convention='stdcall')
        stack=bytes(e._stack)
        b=e.run_original_context(0x546d2c,context(0x546d2c),source_return_pc=0x42bb81,source_convention='stdcall',arguments=args)
        expected=0xffffffff if attack=='creation_failure' else int(target==0x49b630 and attack is None)
        found[f'claw_native_{target:x}_{attack}']=a.completed and b.completed and not a.errors and not b.errors and a.eax==b.eax==expected and a.events==b.events and a.heap==b.heap and a.image==b.image and stack==e.machine.read(STACK_BASE,STACK_SIZE)
        if a.errors or b.errors:print('native real',target,attack,[str(x) for x in a.errors+b.errors],file=sys.stderr)
    for attack in ('fabricated_positive','repeat_init','wrong_hwnd','copied_request','after_end','wrong_result'):
      for native in (False,True):
        e,app,players,endings,reached=claw_environment(attack=attack)
        args=(0x5151,0x525f48,0x9090,0x49b630,0)
        out=(e.run_native(f,0x546d2c,0,args,source_context=context(0x546d2c),source_return_pc=0x42bb81,source_convention='stdcall') if native else
             e.run_original_context(0x546d2c,context(0x546d2c),source_return_pc=0x42bb81,source_convention='stdcall',arguments=args))
        found[f'claw_reject_{attack}_{native}']=bool(out.errors) and not out.completed and not e._dialog_sessions and not e._physical_requests and not e.machine._physical_pump
    e,app,players,endings,reached=claw_environment()
    out=e.run_original_context(0x546d2c,context(0x546d2c),source_return_pc=0x45398f,source_convention='stdcall',arguments=(0x5151,0x528228,0x9090,0x453a10,0))
    found['claw_existing_callsite']=out.completed and not out.errors and e.get(0x53796c)==2 and len(e.callback_executions)==2
    # The real owned callback must use the selected mutant; no original replay
    # may rescue its missing EndDialog or selection writes.
    e,app,players,endings,reached=claw_environment(0x49b730)
    out=e.run_native(entry(flavor,'claw_physical_callbacks_mutant'),0x546d2c,0,
        (0x5151,0x525f30,0x9090,0x49b730,0),source_context=context(0x546d2c),
        source_return_pc=0x42bb81,source_convention='stdcall')
    found['claw_owned_mutant_detected']=(any('modal result' in str(x) for x in out.errors) and
        not out.completed and e.get(app+0x64)==players[1] and not endings and
        len(e.callback_executions)==2 and all(x['entered'] and x['returned'] for x in e.callback_executions))
    # Hash-pinned bodies cannot be paired with another reviewed callsite, nor
    # can an external callback be silently elected as a native implementation.
    for change in (dict(call_pc=0x453989,return_pc=0x45398f),dict(body_sha256='0'*64),
                   dict(native_owned=True),dict(target=0x49b631),dict(end_service=0x546d40)):
        e,app,players,endings,reached=claw_environment()
        c=e._dialog_contracts[(0x546d2c,0x42bb81,0x49b630)]
        try:e.dialog_callback(replace(c,**change));rejected=False
        except ContextFault:rejected=True
        found['claw_pinned_'+next(iter(change))]=rejected
    return found


def sanitized_checks():
    command,environment=build.sanitized_python()
    if command is None:return {'passed':False,'detail':'sanitizer unavailable'}
    child=subprocess.run(command+['-m',__name__,'--sanitize'],env=environment,capture_output=True,text=True,timeout=180)
    try:result=json.loads(child.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):result={}
    return dict(result,passed=child.returncode==0 and result.get('failed')==[],returncode=child.returncode,stderr=child.stderr[-4000:])
if __name__=='__main__':
    values=checks('sanitize' if '--sanitize' in sys.argv else 'O0' if '--O0' in sys.argv else 'O2')
    print(json.dumps({'checked':len(values),'failed':[k for k,v in values.items() if not v]}))
    raise SystemExit(not all(values.values()))
