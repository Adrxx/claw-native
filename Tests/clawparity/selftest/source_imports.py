"""Independent synthetic PE/IAT and optional whole-callee transport regressions."""
import copy
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys

from .. import build
from ..env import Env, Halt, NativeCall, NativeHost, NativeCompilerContext, NativeSourceContext, U32
from ..kernel import CONTEXT_FIELDS, STACK_BASE, STACK_SIZE, STACK_TOP, STOP
from ..program import Program, Section
from .source_context import context
from .stack import relative_call

HEADER = ('size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1')
CHILD = dict(kind='whole', convention='cdecl', argc=1, returns='u32',
             source_context=dict(input_mask=0x7ff, output_mask=0x7ff, preserve_mask=0x472, optional=True))


def program():
    code = bytearray(b'\xcc' * 0x200)
    # push 33; call [IAT]; ret. The physical CPU sees the Machine IAT stub.
    code[:9] = bytes.fromhex('6a33 ff15 00204000 c3')
    # mov eax,[IAT]; push 33; call eax; ret.
    code[0x20:0x2a] = bytes.fromhex('a1 00204000 6a33 ffd0 c3')
    caller = bytes.fromhex('6a33') + relative_call(0x401042, 0x401100) + bytes.fromhex('8d642404 c3')
    code[0x40:0x40+len(caller)] = caller
    # The whole child stays x86: push its argument; call [IAT]; ret.
    child = bytes.fromhex('ff742404 ff15 00204000 c3')
    code[0x100:0x100+len(child)] = child
    return Program('source-import-synthetic', '', 0x400000, 0x3000,
        [Section('.text', 0x401000, len(code), bytes(code)),
         Section('.data', 0x402000, 0x1000, bytes(0x1000))], (0x401000, 0x401200),
        {0x402000:'SYNTH.dll!physical', 0x402004:'SYNTH.dll!undeclared'})


def environment(halt=False):
    env = Env(program())
    observed = []
    def physical(state, call):
        cpu = tuple(getattr(call.source_context, n) for n in CONTEXT_FIELDS) if call.source_context else None
        observed.append((state.side, call.function, call.arguments, call.stack_pointer, call.source_return_pc,
                         state.read(call.stack_pointer, 8), cpu,
                         tuple(getattr(call.source_context,n) for n in HEADER) if call.source_context else None))
        state.put(0x402040, call.arguments[0], call.stack_pointer)
        if halt:
            raise Halt('independent synthetic physical stop')
        return 0xaabbccdd
    env.fixture(0x402000, 'stdcall', 1, physical)
    env.source_callees[0x401100] = copy.deepcopy(CHILD)
    return env, observed


def checks(flavor='O2'):
    lib = C.CDLL(str(build.library('source-imports-selftest', [Path(__file__).with_name('source_imports_module.cpp')], flavor)))
    entry = lib.claw_source_imports_entry
    entry.argtypes = [U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)]
    entry.restype = U32
    found = {}
    for function in (0x401000, 0x401020, 0x401040):
        for halt in (False, True):
            env, observed = environment(halt)
            for frame in (STACK_BASE+32, STACK_TOP, STACK_BASE+STACK_SIZE-4):
                for ebp in (0, 0xffffffff, 0x12345678):
                    env._begin_case(None)
                    # Sentinel-filled bounded stack catches writes outside exact call frames.
                    env._initial['stack'][:] = bytes(range(256)) * (STACK_SIZE//256)
                    env._freeze(); observed.clear()
                    initial = context(function, frame, ebp, STACK_TOP+0x100)
                    n, o = NativeSourceContext.from_buffer_copy(initial), NativeSourceContext.from_buffer_copy(initial)
                    native = env.run_native(entry, function, 0, (), source_context=n, source_return_pc=0x401180)
                    stack = bytes(env._stack)
                    original = env.run_original_context(function, o, source_return_pc=0x401180)
                    label = f'{function:x}_{halt}_{frame:x}_{ebp:x}'
                    found[label+'_effects'] = (not native.errors and not original.errors and native.events == original.events and
                        native.heap == original.heap and native.image == original.image and native.spans == original.spans and native.freed == original.freed)
                    found[label+'_stack'] = stack == env.machine.read(STACK_BASE, STACK_SIZE)
                    found[label+'_cpu'] = (native.halted and original.halted and native.source_stop == original.source_stop) if halt else (
                        native.completed and original.completed and bytes(n) == bytes(o))
                    found[label+'_calltime'] = (len(observed) == 2 and observed[0][1:] == observed[1][1:] and
                        observed[0][1] == 0x402000 and observed[0][-2][8] == 0x402000 and
                        struct.unpack('<II', observed[0][-3]) == (observed[0][4], 0x33))
                    found[label+'_header_scope'] = (all(getattr(n,k) == getattr(initial,k) for k in HEADER) and
                        not env._host.sourceContext and not env._host.compilerContext and not env._host.sourceReturnPC and not env._host.remainingOperations)
                    found[label+'_whole_original'] = native.bridged == ([0x401100] if function == 0x401040 else [])
    # Context-free optional dependency still executes its original complete body.
    for halt in (False, True):
        env, observed = environment(halt); env._begin_case(None); env._freeze()
        n = env.run_native(entry, 0x401040, 0, ())
        o = env.run_original(0x401040, 0, ())
        found[f'optional_ordinary_{halt}'] = (env.compare(n,o,not halt,STACK_TOP+4) is None and
            not n.errors and n.bridged == [0x401100] and len(observed) == 2 and all(x[-1] is None and x[-2] is None for x in observed))
    # Exercise host checks directly so a native front-end check cannot hide a gap.
    def probe(change=None, source=True, declaration=None, compiler=False, active=True):
        env, observed = environment()
        if declaration is not None: env.source_callees[0x401100] = declaration
        if compiler: env.compiler_callees[0x401100] = {'input_mask':0x7ff,'output_mask':0x7ff}
        env._begin_case(None); env._freeze()
        raw = NativeCall(); child = context(env.machine.import_stub[0x402000], STACK_TOP-8)
        raw.function = child.eip if source else 0x401100
        raw.stackPointer = child.esp; raw.argumentCount = 1; raw.arguments[0] = 0x33
        raw.sourceContext = C.pointer(child) if source else None
        raw.sourceReturnPC = 0x401008 if source else 0
        keep = []
        if change: change(env,raw,child,keep)
        before = bytes(child)
        def call_host(function,receiver,args,argc,host,result):
            if source:
                env.write(STACK_TOP-8, struct.pack('<2I', 0x401008, 0x33))
            env._native_call(None,C.pointer(raw))
            return int(not env._host.fault)
        root = context(0x401040) if active else None
        outcome = env.run_native(call_host,0x401040,0,(),source_context=root,source_return_pc=0x401180 if active else 0)
        return outcome, observed, before, bytes(child)
    invalid = {
        'slot_mislabeled_stub': lambda e,r,s,k:setattr(r,'function',0x402000),
        'cached_mislabeled_slot': lambda e,r,s,k:setattr(s,'eip',0x402000),
        'cached_mislabeled_other_stub': lambda e,r,s,k:setattr(s,'eip',e.machine.import_stub[0x402004]),
        'unknown_cached': lambda e,r,s,k:(setattr(r,'function',e.machine.first_free_stub),setattr(s,'eip',e.machine.first_free_stub)),
        'undeclared_cached': lambda e,r,s,k:(setattr(r,'function',e.machine.import_stub[0x402004]),setattr(s,'eip',e.machine.import_stub[0x402004])),
        'undeclared_executable': lambda e,r,s,k:(setattr(r,'function',0x401150),setattr(s,'eip',0x401150)),
        'wrong_arity': lambda e,r,s,k:setattr(r,'argumentCount',0),
        'wrong_receiver': lambda e,r,s,k:setattr(r,'receiver',1),
        'wrong_receiver2': lambda e,r,s,k:setattr(r,'receiver2',1),
        'wrong_stack': lambda e,r,s,k:setattr(r,'stackPointer',s.esp+4),
        'bad_pc': lambda e,r,s,k:setattr(r,'sourceReturnPC',STOP),
        'bad_mask': lambda e,r,s,k:setattr(s,'inputMask',0),
        'bad_reserved': lambda e,r,s,k:setattr(s,'reserved0',1),
        'bad_flags': lambda e,r,s,k:setattr(s,'eflags',0x202),
        'bad_fs': lambda e,r,s,k:setattr(s,'fsHead',0),
        'bad_frame': lambda e,r,s,k:(setattr(s,'esp',STACK_BASE-4),setattr(r,'stackPointer',STACK_BASE-4)),
        'x87_channel': lambda e,r,s,k:setattr(r,'x87ArgumentCount',1),
        'compiler_channel': lambda e,r,s,k:(k.append(NativeCompilerContext()),setattr(r,'compilerContext',C.pointer(k[-1]))),
        'missing_context': lambda e,r,s,k:setattr(r,'sourceContext',None),
        'missing_pc': lambda e,r,s,k:setattr(r,'sourceReturnPC',0),
    }
    for label,change in invalid.items():
        out,obs,before,after = probe(change)
        found['reject_'+label] = out.fault == 5 and not out.completed and not obs and before == after
    # The checked/effective view is separate from the caller's borrowed object,
    # even while a physical service observes the logical import identity.
    borrowed = []
    def inspect_borrowed(env, raw, child, keep):
        signature, effect = env.fixtures[0x402000]
        def inspect(state, call):
            borrowed.append((raw.function, child.eip, call.source_context.eip,
                             C.addressof(child) != C.addressof(call.source_context)))
            return effect(state, call)
        env.fixtures[0x402000] = signature, inspect
    out,obs,before,after = probe(inspect_borrowed)
    initial = NativeSourceContext.from_buffer_copy(before)
    returned = NativeSourceContext.from_buffer_copy(after)
    found['cached_borrowed_identity_and_output'] = (out.completed and not out.errors and len(borrowed) == 1 and
        borrowed[0][0] == borrowed[0][1] and borrowed[0][2:] == (0x402000,True) and
        returned.eip == 0x401008 and returned.esp == initial.esp+8 and returned.eax == 0xaabbccdd and
        all(getattr(initial,k) == getattr(returned,k) for k in HEADER))
    out,obs,before,after = probe(active=False)
    found['reject_no_live_source_graph'] = out.fault == 5 and not obs and before == after
    out,obs,_,_ = probe(source=False)
    found['reject_source_parent_context_free_optional'] = out.fault == 5 and not obs
    for label,decl in (
        ('required',{**CHILD,'source_context':{k:v for k,v in CHILD['source_context'].items() if k != 'optional'}}),
        ('optional_false',{**CHILD,'source_context':{**CHILD['source_context'],'optional':False}}),
        ('optional_integer',{**CHILD,'source_context':{**CHILD['source_context'],'optional':1}}),
        ('not_whole',{**CHILD,'kind':'fixture'}),
        ('fastcall',{**CHILD,'convention':'fastcall'})):
        out,obs,_,_ = probe(source=False, declaration=decl, active=False)
        found['reject_ordinary_'+label] = out.fault == 5 and not obs
    out,obs,_,_ = probe(source=False, compiler=True, active=False)
    found['reject_ordinary_compiler'] = out.fault == 5 and not obs
    for label,change in invalid.items():
        if label not in ('wrong_arity','wrong_receiver','wrong_receiver2','x87_channel'): continue
        out,obs,_,_ = probe(change,source=False,active=False)
        found['reject_optional_'+label] = out.fault == 5 and not obs
    def replace_original_with_fixture(env, raw, child, keep):
        env.fixtures[0x401100] = env.fixtures[0x402000]
    out,obs,_,_ = probe(replace_original_with_fixture,source=False,active=False)
    found['reject_optional_fixture_substitution'] = out.fault == 5 and not obs
    out,obs,_,_ = probe(lambda e,r,s,k:(replace_original_with_fixture(e,r,s,k),
        setattr(r,'function',0x401100),setattr(s,'eip',0x401100)))
    found['reject_source_fixture_substitution'] = out.fault == 5 and not obs
    return found


def sanitized_checks():
    command, environment = build.sanitized_python()
    if command is None: return {'passed':False,'detail':'sanitizer unavailable'}
    child = subprocess.run(command+['-m',__name__,'--sanitize'],env=environment,capture_output=True,text=True,timeout=180)
    try: result=json.loads(child.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError): result={}
    return dict(result,passed=child.returncode == 0 and result.get('failed') == [],returncode=child.returncode,stderr=child.stderr[-2000:])


if __name__ == '__main__':
    values = checks('sanitize' if '--sanitize' in sys.argv else 'O2')
    print(json.dumps({'checked':len(values),'failed':[k for k,v in values.items() if not v]}))
    raise SystemExit(not all(values.values()))
