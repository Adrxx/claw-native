"""Direct-JMP original bridging, inherited frames and single-RET outputs."""
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys

from .. import build
from ..env import Env, Halt, NativeCall, NativeHost, U32, NativeSourceContext
from ..kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_ALL, ContextFault
from ..program import Program, Section
from .source_context import context
from .stack import relative_call


def program():
    code = bytearray(b'\xcc' * 0x400)
    roots = [(0x401000, b'', 0x401100),
             (0x401020, b'\xb9' + struct.pack('<I', 0x12345678), 0x401140),
             (0x401040, b'\xb8' + struct.pack('<I', 0x87654321), 0x401180),
             (0x401060, b'', 0x4011c0), (0x401080, b'', 0x401240),
             (0x4010a0, relative_call(0x4010a0,0x401280),0x4012a0)]
    for root, prefix, target in roots:
        site = root + len(prefix)
        body = prefix + b'\xe9' + struct.pack('<i', target-site-5)
        code[root-0x401000:root-0x401000+len(body)] = body
    # Targets witness the inherited return word, ECX, and caller-owned slots.
    for target, body in ((0x401100, bytes.fromhex('8b0424 a300204000 c3')),
                         (0x401140, bytes.fromhex('890d00204000 8b0424 c3')),
                         (0x401180, bytes.fromhex('89442404 8b0424 c3')),
                         (0x4011c0, relative_call(0x4011c0, 0x401200) + b'\xc3')):
        code[target-0x401000:target-0x401000+len(body)] = body
    code[0x300] = 0x90
    code[0x240:0x242] = b'\xeb\xfe'
    code[0x280] = 0xc3
    code[0x2a0:0x2a6] = bytes.fromhex('6a77 59 8b0424')
    code[0x2a6] = 0xc3
    return Program('source-tail-synthetic', '', 0x400000, 0x3000,
        [Section('.text', 0x401000, len(code), bytes(code)),
         Section('.data', 0x402000, 0x1000, bytes(0x1000))], (0x401000, 0x401400), {})


def environment():
    env = Env(program())
    for target in (0x401100, 0x401140, 0x401180, 0x4011c0, 0x401240, 0x401280, 0x4012a0):
        env.source_callees[target] = {'kind': 'whole', 'argc': 0, 'returns': 'u32',
            'convention': 'thiscall' if target == 0x401140 else 'cdecl',
            'source_context': {'input_mask': CONTEXT_ALL, 'output_mask': CONTEXT_ALL, 'preserve_mask': 0x400}}
    return env


def checks(flavor='O2'):
    lib = C.CDLL(str(build.library('source-tail-selftest', [Path(__file__).with_name('source_tail_module.cpp')], flavor)))
    entry = lib.claw_source_tail_selftest_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    results = {}
    for function, target, offset in ((0x401000,0x401100,0), (0x401020,0x401140,5), (0x401040,0x401180,5), (0x4010a0,0x4012a0,5)):
        for frame in (STACK_BASE+32, STACK_TOP, STACK_BASE+STACK_SIZE-8):
            env = environment()
            env.source_tail_edge(function, function+offset, target)
            env.put(frame+4, 0xfeedface)
            env._freeze()
            n = context(function, frame); o = NativeSourceContext.from_buffer_copy(n)
            native = env.run_native(entry,function,0,(),source_context=n,source_return_pc=0x401300)
            stack = bytes(env._stack)
            original = env.run_original_context(function,o,source_return_pc=0x401300)
            label = f'{function:x}_{frame:x}'
            results[label+'_completion'] = native.completed and original.completed and not native.errors and not original.errors
            results[label+'_cpu'] = bytes(n) == bytes(o) and n.esp == frame+4 and n.eip == 0x401300
            results[label+'_memory'] = native.image == original.image and native.heap == original.heap
            results[label+'_stack'] = stack == env.machine.read(STACK_BASE,STACK_SIZE)
            results[label+'_observations'] = native.source_boundaries == original.source_boundaries and len(native.source_boundaries) == 2
            results[label+'_headers'] = n.preserveMask == 0x472 and n.inputMask == CONTEXT_ALL and n.outputMask == CONTEXT_ALL
    mutant_lib=C.CDLL(str(build.library('source-tail-skip-call-selftest', [Path(__file__).with_name('source_tail_module.cpp')], flavor,
        defines=('CLAW_SELFTEST_SKIP_EMPTY_CALL=1',))))
    mutant=mutant_lib.claw_source_tail_selftest_entry
    mutant.argtypes,mutant.restype=entry.argtypes,entry.restype
    env=environment();env.source_tail_edge(0x4010a0,0x4010a5,0x4012a0);env._freeze()
    n=context(0x4010a0);o=NativeSourceContext.from_buffer_copy(n)
    native=env.run_native(mutant,0x4010a0,0,(),source_context=n,source_return_pc=0x401300);stack=bytes(env._stack)
    original=env.run_original_context(0x4010a0,o,source_return_pc=0x401300)
    results['empty_call_skip_final_states_equal']=native.completed and original.completed and bytes(n)==bytes(o) and native.image==original.image and stack==env.machine.read(STACK_BASE,STACK_SIZE)
    results['empty_call_skip_jmp_stack_detects']=native.source_boundaries[0][:4]==original.source_boundaries[0][:4] and native.source_boundaries[0][4]!=original.source_boundaries[0][4]
    results['empty_call_skip_return_stack_equal']=native.source_boundaries[1]==original.source_boundaries[1]
    for wrong in ('site', 'target', 'undeclared', 'fixture'):
        env = environment()
        env.source_tail_edge(0x401000,0x401000,0x401100)
        if wrong == 'site': env._tail_specs = {(0x401000,0x401001):0x401100}
        if wrong == 'target': env._tail_specs[(0x401000,0x401000)] = 0x401140
        if wrong == 'undeclared': del env.source_callees[0x401100]
        if wrong == 'fixture': env.fixtures[0x401100] = (None,None)
        env._freeze(); n = context()
        native = env.run_native(entry,0x401000,0,(),source_context=n,source_return_pc=0x401300)
        results['reject_'+wrong] = not native.completed and native.fault == 5 and not env.bridged and not env.source_boundaries
    for caller,site,target in ((0x401000,0x401001,0x401100),(0x401000,0x401000,0x401140)):
        env = environment()
        try: env.source_tail_edge(caller,site,target)
        except ContextFault: results[f'reject_original_metadata_{site:x}_{target:x}'] = True
        else: results[f'reject_original_metadata_{site:x}_{target:x}'] = False
    # Poison each borrowed request before bridge execution. No target effects
    # or completed tail observation may occur for a rejected request.
    mutations = {
        'version': lambda e,r: setattr(r,'sourceTransferVersion',2),
        'kind': lambda e,r: setattr(r,'sourceTransferKind',2),
        'caller': lambda e,r: setattr(r,'sourceCallerFunction',0x401020),
        'site': lambda e,r: setattr(r,'sourceTransferSite',0x401001),
        'target': lambda e,r: setattr(r,'function',0x401140),
        'args': lambda e,r: setattr(r,'argumentCount',1),
        'return': lambda e,r: setattr(r,'sourceReturnPC',0x401301),
        'frame': lambda e,r: setattr(r.sourceContext.contents,'esp',STACK_TOP-4),
        'copied_frame': lambda e,r: setattr(r,'stackPointer',STACK_TOP-4),
        'receiver': lambda e,r: setattr(r,'receiver',1),
        'ecx': lambda e,r: setattr(r.sourceContext.contents,'ecx',1),
        'header': lambda e,r: setattr(r.sourceContext.contents,'reserved0',1),
        'parent_header': lambda e,r: setattr(e._host.sourceContext.contents,'reserved0',1),
        'parent_preserve': lambda e,r: setattr(e._host.sourceContext.contents,'preserveMask',0),
        'mask': lambda e,r: setattr(r.sourceContext.contents,'inputMask',0x472),
        'aliased_context': lambda e,r: setattr(r,'sourceContext',e._host.sourceContext),
        'receipt': lambda e,r: setattr(r.sourceDisposition.contents,'disposition',1),
        'guest': lambda e,r: setattr(e._host,'guestSession',1),
    }
    for label,mutate in mutations.items():
        env = environment(); env.source_tail_edge(0x401000,0x401000,0x401100); env._freeze()
        serve = env._native_source_tail
        def poisoned(raw, mutate=mutate, serve=serve, env=env):
            mutate(env,raw)
            return serve(raw)
        env._native_source_tail = poisoned
        n = context()
        native = env.run_native(entry,0x401000,0,(),source_context=n,source_return_pc=0x401300)
        results['reject_request_'+label] = not native.completed and native.fault == 5 and not env.bridged and not env.source_boundaries
    def stop(e,call):
        e.put(0x402000,0x543210)
        raise Halt('actual nonreturning physical stop')
    env=environment(); env.fixture(0x401200,'cdecl',0,stop)
    env.source_tail_edge(0x401060,0x401060,0x4011c0); env._freeze()
    n=context(0x401060); o=NativeSourceContext.from_buffer_copy(n)
    native=env.run_native(entry,0x401060,0,(),source_context=n,source_return_pc=0x401300)
    stack=bytes(env._stack)
    original=env.run_original_context(0x401060,o,source_return_pc=0x401300)
    results['physical_stop_no_return']=not native.completed and native.fault==2 and original.halted and len(native.source_boundaries)==1
    results['physical_stop_prefix']=native.source_stop==original.source_stop and all(getattr(n,k)==v for k,v in native.source_stop['registers'].items())
    results['physical_stop_effects']=native.image==original.image and stack==env.machine.read(STACK_BASE,STACK_SIZE) and native.events==original.events
    env=environment(); env.maximum_operations=512
    env.source_tail_edge(0x401080,0x401080,0x401240); env._freeze(); n=context(0x401080)
    native=env.run_native(entry,0x401080,0,(),source_context=n,source_return_pc=0x401300)
    results['tail_cycle_budget']=not native.completed and native.fault==3 and n.eip==0x401240 and n.esp==STACK_TOP and len(native.source_boundaries)==1
    for poison in ('parent_header','receipt','reentry','ordinary_callback_reentry'):
        env=environment(); env.source_tail_edge(0x401060,0x401060,0x4011c0)
        serve=env._native_source_tail
        retained=[]
        def save(raw,serve=serve,retained=retained):
            retained.append(raw)
            return serve(raw)
        env._native_source_tail=save
        def effect(e,call,poison=poison,retained=retained):
            if poison=='parent_header': e._host.sourceContext.contents.reserved0=1
            elif poison=='receipt': retained[0].sourceDisposition.contents.disposition=1
            elif poison=='reentry': e._native_source_tail(retained[0])
            else:
                forged=NativeCall.from_buffer_copy(retained[0])
                forged.sourceTransferVersion=forged.sourceTransferKind=forged.sourceTransferSite=forged.sourceCallerFunction=0
                forged.sourceDisposition=None
                e._native_call(None,C.pointer(forged))
            return 7
        env.fixture(0x401200,'cdecl',0,effect); env._freeze(); n=context(0x401060)
        native=env.run_native(entry,0x401060,0,(),source_context=n,source_return_pc=0x401300)
        results['post_bridge_'+poison]=not native.completed and native.fault==5 and len(native.source_boundaries)==1 and len(env.bridged)==1
    return results


def sanitized_checks():
    command, environ = build.sanitized_python()
    if command is None: return {'passed': False, 'error': 'sanitizer unavailable'}
    result = subprocess.run(command + ['-m', __name__, 'sanitize'], env=environ, capture_output=True, text=True, timeout=120)
    try: report = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError): report = {'status': 'fail'}
    return {**report, 'returncode': result.returncode, 'stderr': result.stderr[-2000:],
            'passed': result.returncode == 0 and report.get('status') == 'pass'}


def main():
    results = checks(sys.argv[1] if len(sys.argv)>1 else 'O2')
    bad = [k for k,v in results.items() if not v]
    print(json.dumps({'command':'source-tail-selftest','checks':len(results),'failures':bad,'status':'fail' if bad else 'pass'}))
    return bool(bad)


if __name__ == '__main__': sys.exit(main())
