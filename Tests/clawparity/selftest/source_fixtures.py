"""Case-scoped dynamic source fixtures, with genuine synthetic indirect CALLs."""
import ctypes as C
from dataclasses import replace
import json
from pathlib import Path
import struct
import subprocess
import sys

from .. import build
from ..env import Env, Halt, NativeCall, NativeHost, NativeSourceContext, U32
from ..kernel import (CONTEXT_FIELDS, STACK_BASE, STACK_SIZE, STACK_TOP, STOP, ContextFault,
                      validate_source, validate_source_fixture)
from ..program import Program, Section
from .source_context import context
from .stack import relative_call

HEADER = ('size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1')


def program():
    code = bytearray(b'\xcc' * 0x200)
    # mov eax,[callback]; push [pointer]; push 33; call eax; lea esp,[esp+8]; ret
    caller = bytes.fromhex('a1 00204000 ff35 04204000 6a33 ffd0 8d642408 c3')
    code[:len(caller)] = caller
    code[0x100:0x100+len(caller)] = caller
    code[0x40:0x46] = relative_call(0x401040, 0x401100) + b'\xc3'
    return Program('dynamic-source-fixture-synthetic', '', 0x400000, 0x3000,
        [Section('.text', 0x401000, len(code), bytes(code)),
         Section('.data', 0x402000, 0x1000, bytes(0x1000))], (0x401000, 0x401200), {})


def environment(halt=False):
    env = Env(program())
    observed = []
    def callback(state, call):
        observed.append((state.side, call.function, call.arguments, call.stack_pointer, call.source_return_pc,
            state.read(call.stack_pointer, 12), tuple(getattr(call.source_context,n) for n in CONTEXT_FIELDS)))
        state.put(call.arguments[1], call.arguments[0])
        if halt: raise Halt('synthetic dynamic source callback stop')
        return 0xaabbccdd
    pointer = env.object(4)
    target = env.stub('dynamic', 'cdecl', 2, callback, arguments=('u32','ptr:4'))
    env.put(0x402000, target, pointer)
    env.source_callees[0x401100] = dict(kind='whole', convention='cdecl', argc=0, returns='u32',
        source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
    env._freeze()
    return env, target, pointer, observed


def checks(flavor='O2'):
    lib = C.CDLL(str(build.library('source-fixtures-selftest', [Path(__file__).with_name('source_fixtures_module.cpp')], flavor)))
    entry = lib.claw_source_fixtures_entry
    entry.argtypes = [U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)]
    entry.restype = U32
    found = {}
    for function in (0x401000, 0x401040):
        for halt in (False, True):
            for frame in (STACK_BASE+32,STACK_TOP,STACK_BASE+STACK_SIZE-4):
                env,target,pointer,observed = environment(halt)
                env._initial['stack'][:] = bytes(range(256))*(STACK_SIZE//256)
                n = context(function,frame,0xffffffff,STACK_TOP+0x100)
                o = NativeSourceContext.from_buffer_copy(n)
                native = env.run_native(entry,function,0,(),source_context=n,source_return_pc=0x401180)
                stack = bytes(env._stack)
                original = env.run_original_context(function,o,source_return_pc=0x401180)
                key = f'{function:x}_{halt}_{frame:x}'
                found[key+'_effects'] = (not native.errors and not original.errors and native.events == original.events and
                    native.heap == original.heap and native.image == original.image and native.spans == original.spans and native.freed == original.freed)
                found[key+'_stack'] = stack == env.machine.read(STACK_BASE,STACK_SIZE)
                found[key+'_cpu'] = (native.halted and original.halted and native.source_stop == original.source_stop) if halt else (
                    native.completed and original.completed and bytes(n) == bytes(o))
                found[key+'_callback'] = (len(observed) == 2 and observed[0][1:] == observed[1][1:] and
                    observed[0][1] == target and observed[0][-1][8] == target and
                    struct.unpack('<3I',observed[0][-2]) == (observed[0][4],0x33,pointer))
                found[key+'_original_bridge'] = native.bridged == ([0x401100] if function == 0x401040 else [])
                found[key+'_metadata_unchanged'] = env.program.imports == {} and env.program.text == (0x401000,0x401200)
    def probe(change=None, active=True, corrupt_effect=None):
        env,target,pointer,observed = environment()
        raw = NativeCall(); child = context(target,STACK_TOP-12)
        raw.function=target; raw.argumentCount=2; raw.arguments[0]=0x33; raw.arguments[1]=pointer
        raw.stackPointer=child.esp; raw.sourceContext=C.pointer(child); raw.sourceReturnPC=0x40100f
        if corrupt_effect:
            signature,effect = env._case_fixtures[target]
            # Register normally: capability is bound to this exact effect too.
            env._begin_case(None)
            pointer=env.object(4)
            def corrupt(state,call):
                value=effect(state,call)
                corrupt_effect(state,call)
                return value
            assert env.stub('dynamic','cdecl',2,corrupt,arguments=('u32','ptr:4')) == target
            env._freeze()
        if change: change(env,raw,child)
        before=bytes(child)
        def call_host(*args):
            env.put(STACK_TOP-12,0x40100f,0x33,pointer)
            env._native_call(None,C.pointer(raw))
            return int(not env._host.fault)
        root=context(0x401000) if active else None
        result=env.run_native(call_host,0x401000,0,(),source_context=root,source_return_pc=0x401180 if active else 0)
        return result,observed,before,bytes(child)
    def bad_pointer(e,r,s): r.arguments[1] += 4
    invalid={
        'unknown':lambda e,r,s:(setattr(r,'function',r.function+1),setattr(s,'eip',r.function)),
        'mismatched_eip':lambda e,r,s:setattr(s,'eip',r.function+1),
        'arity':lambda e,r,s:setattr(r,'argumentCount',1),
        'receiver':lambda e,r,s:setattr(r,'receiver',1),
        'receiver2':lambda e,r,s:setattr(r,'receiver2',1),
        'stack':lambda e,r,s:setattr(r,'stackPointer',s.esp+4),
        'unaligned_frame':lambda e,r,s:(setattr(s,'esp',s.esp+1),setattr(r,'stackPointer',s.esp)),
        'unbounded_frame':lambda e,r,s:(setattr(s,'esp',STACK_BASE-4),setattr(r,'stackPointer',s.esp)),
        'return_pc':lambda e,r,s:setattr(r,'sourceReturnPC',STOP),
        'physical_return_pc':lambda e,r,s:setattr(r,'sourceReturnPC',0x401020),
        'physical_pointer_argument':bad_pointer,
        'mask':lambda e,r,s:setattr(s,'inputMask',0),
        'output_mask':lambda e,r,s:setattr(s,'outputMask',0),
        'preserve_mask':lambda e,r,s:setattr(s,'preserveMask',0x7ff),
        'flags':lambda e,r,s:setattr(s,'eflags',0x202),
        'fs':lambda e,r,s:setattr(s,'fsHead',0),
        'reserved':lambda e,r,s:setattr(s,'reserved0',1),
        'x87':lambda e,r,s:setattr(r,'x87ArgumentCount',1),
        'retired':lambda e,r,s:e._case_fixtures.clear(),
        'substituted_signature':lambda e,r,s:e._case_fixtures.__setitem__(r.function,
            (replace(e._case_fixtures[r.function][0],argc=1),e._case_fixtures[r.function][1])),
        'substituted_convention':lambda e,r,s:e._case_fixtures.__setitem__(r.function,
            (replace(e._case_fixtures[r.function][0],convention='stdcall'),e._case_fixtures[r.function][1])),
        'substituted_effect':lambda e,r,s:e._case_fixtures.__setitem__(r.function,
            (e._case_fixtures[r.function][0],123)),
        'unregistered':lambda e,r,s:e._source_fixture_capabilities.clear(),
    }
    for label,change in invalid.items():
        result,observed,before,after=probe(change)
        found['reject_'+label]=result.fault == 5 and not observed and before == after
    result,observed,before,after=probe(active=False)
    found['reject_inactive_graph']=result.fault == 5 and not observed and before == after
    for label,corrupt in {
        'preserved':lambda e,c:setattr(c.source_context,'ebx',42),
        'output_flags':lambda e,c:setattr(c.source_context,'eflags',0x202),
        'output_fs':lambda e,c:setattr(c.source_context,'fsHead',0),
        'retired_during_effect':lambda e,c:e._case_fixtures.clear(),
    }.items():
        result,observed,_,_=probe(corrupt_effect=corrupt)
        found['reject_'+label]=result.fault == 5 and len(observed) == 1
    env,target,pointer,observed=environment()
    signature=env._case_fixtures[target][0]; capability=env._source_fixture_capabilities[target]
    def rejected(action):
        try: action()
        except ContextFault: return True
        return False
    found['generic_rejects_registered']=rejected(lambda:validate_source(context(target),target,0x40100f,env.program))
    env._begin_case(None)
    env.stub('replacement','cdecl',2,0)
    found['reject_previous_case_capability']=rejected(lambda:validate_source_fixture(
        context(target),target,0x40100f,env.program,capability,signature))
    return found


def sanitized_checks():
    command,environment=build.sanitized_python()
    if command is None: return {'passed':False,'detail':'sanitizer unavailable'}
    child=subprocess.run(command+['-m',__name__,'--sanitize'],env=environment,capture_output=True,text=True,timeout=180)
    try: result=json.loads(child.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError): result={}
    return dict(result,passed=child.returncode == 0 and result.get('failed') == [],returncode=child.returncode,stderr=child.stderr[-2000:])


if __name__ == '__main__':
    values=checks('sanitize' if '--sanitize' in sys.argv else 'O2')
    print(json.dumps({'checked':len(values),'failed':[k for k,v in values.items() if not v]}))
    raise SystemExit(not all(values.values()))
