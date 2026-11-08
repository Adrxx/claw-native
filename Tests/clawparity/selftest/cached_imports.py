"""Cached IAT targets: real native calls against independent synthetic x86."""
import ctypes as C
import json
from pathlib import Path
import subprocess
import sys
from .. import build
from ..env import Env, NativeHost, U32
from ..kernel import STACK_TOP
from ..program import Program, Section


def checks(flavor='O2'):
    # mov eax,[IAT]; push incoming argument; call eax; ret
    code = bytes.fromhex('a1 00204000 ff742404 ffd0 c3')
    program = Program('cached-import-synthetic', '', 0x400000, 0x3000,
        [Section('.text',0x401000,0x100,code.ljust(0x100,b'\xcc')),
         Section('.data',0x402000,0x1000,bytes(0x1000))],(0x401000,0x401100),
        {0x402000:'SYNTH.dll!declared',0x402004:'SYNTH.dll!undeclared'})
    env = Env(program)
    def physical(state, call):
        state.put(0x402020,call.arguments[0],call.stack_pointer)
        return call.arguments[0] ^ 0xa55aa55a
    env.fixture(0x402000, 'stdcall', 1, physical)
    library = C.CDLL(str(build.library('cached-import-selftest', [Path(__file__).with_name('CachedImportModule.cpp')],flavor)))
    entry = library.claw_cached_import_selftest_entry
    entry.argtypes = [U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)]
    entry.restype = U32
    found = {}
    for frame in (STACK_TOP,STACK_TOP-0x100):
        for value in (0,1,0xdeadbeef,0xffffffff):
            env._begin_case(None);env._freeze()
            native = env.run_native(entry,0x401000,0,(value,),entry_stack_pointer=frame)
            original = env.run_original(0x401000,0,(value,),stack_pointer=frame)
            found[f'{frame:x}_{value:x}_comparison'] = env.compare(native,original,True,frame+4) is None
            found[f'{frame:x}_{value:x}_completed'] = native.completed and not native.errors and not native.bridged and len(native.events)==1
    for function,label in ((0x401010,'wrong_arity'),(0x401020,'wrong_receiver'),(0x401030,'undeclared')):
        env._begin_case(None);env._freeze()
        result = env.run_native(entry,function,0,(7,))
        found[label+'_rejected'] = bool(result.errors) and not result.completed and not result.events
    return found


def sanitized_checks():
    command,environment = build.sanitized_python()
    if command is None: return {'available':False}
    child = subprocess.run(command+['-m','clawparity.selftest.cached_imports','--sanitize'],env=environment,capture_output=True,text=True,timeout=120)
    if child.returncode: return {'passed':False,'detail':child.stderr[-2000:] or child.stdout[-2000:]}
    result=json.loads(child.stdout)
    return {'passed':not result['failed'],**result}


if __name__=='__main__':
    values=checks('sanitize' if '--sanitize' in sys.argv else 'O2')
    print(json.dumps({'checked':len(values),'failed':[k for k,v in values.items() if not v]}))
    raise SystemExit(not all(values.values()))
