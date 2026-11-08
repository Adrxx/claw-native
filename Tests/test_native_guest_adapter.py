"""Independent genuine-factory capture checks; synthetic root is not game recovery."""
import ctypes as C
from pathlib import Path
import random
import os
import subprocess
import sys
import threading
import unittest

from Tests.clawparity import build
from Tests.clawparity.env import Env, NativeHost, NativeSourceContext, U32, HEAP_BASE
from Tests.clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_REGISTERS
from Tests.clawparity.program import claw

ROOT = Path(__file__).resolve().parents[1]

class NativeGuestAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flavor = os.environ.get('CLAW_GUEST_TEST_FLAVOR', 'O2')
        cls.program = claw()
        cls.library = C.CDLL(str(build.library('native-guest-independent',
            [ROOT / 'Tests/NativeGuestTransfer/transport.cpp'], flavor=cls.flavor, guest_transfer=True)))
        cls.entry = cls.library.transport_entry
        cls.entry.argtypes = [U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)]
        cls.entry.restype = U32

    def fixture(self):
        env = Env(self.program, strict=False)
        env._begin_case(random.Random(81412))
        env._initial['stack'][:] = random.Random(413).randbytes(STACK_SIZE)
        marker = env.object(32, 'capture sentinel', fill=0x35)
        effects = []
        def allocation(e, call):
            effects.append(tuple(call.arguments))
            e.write(marker, b'physical-effect-before-raise!!!!')
            return 0
        env.fixture(0x546aa8, 'stdcall', 2, allocation)
        # The adapter captures this actual import before ordinary fixture dispatch.
        def forbidden(e, call):
            raise AssertionError('RaiseException must not become an ordinary callback return')
        env.fixture(0x546958, 'stdcall', 4, forbidden)
        env.source_callees[0x502369] = {
            'kind':'whole','convention':'cdecl','argc':0,
            'source_context': {'input_mask':0x7ff,'output_mask':0x7ff,'preserve_mask':0x472}}
        cpu = NativeSourceContext(72,1,0x7ff,0x7ff,
            0x12345678,0x23456789,0,0x34567890,0x45678901,0x56789012,
            0x67890123,STACK_TOP,0x503420,0x8d7,0xffffffff,0x472,0,0)
        env.put(STACK_TOP,0x5022b4)
        env._freeze()
        return env,cpu,marker,effects

    def original_snapshot(self):
        """Independent direct original factory run, without the native adapter."""
        from Tests.clawparity.guest_exception import CPU, Raise
        from unicorn.x86_const import UC_X86_REG_ESP
        env,cpu,marker,effects = self.fixture()
        machine = env.machine
        heap,image,*_ = env._frozen
        machine.write(HEAP_BASE,heap)
        machine.write(env.program.data_start,image[env.data_offset:])
        machine.write(STACK_BASE,bytes(env._initial['stack']))
        env.backend,env.side = 'machine','original'
        env._reset_run()
        machine.reset_x87()
        captured = {}
        class Captured(Exception): pass
        def external(m,address):
            if address != m.import_stub[0x546958]:
                return env._external(m,address)
            sp = m.register(UC_X86_REG_ESP)
            pc,code,flags,count,information = m.words(sp,5)
            state = CPU(tuple(m.register(r) for r in CONTEXT_REGISTERS),m.fs_head)
            captured.update(cpu=state,event=Raise(code,flags,m.words(information,count),pc,state),
                stack=m.read(STACK_BASE,STACK_SIZE),heap=m.read(HEAP_BASE,env.heap_bytes),
                image_data=m.read(env.program.data_start,env.program.size-env.data_offset))
            raise Captured()
        machine.on_external = external
        child = NativeSourceContext.from_buffer_copy(cpu)
        child.esp -= 4
        child.eip = 0x502369
        with self.assertRaises(Captured):
            machine.call_source(0x502369,child,0x503450)
        self.assertTrue(effects)
        return captured

    def test_real_original_raise_is_owned_after_native_return(self):
        from Tests.clawparity.guest_adapter import run_native_guest
        env,cpu,marker,effects = self.fixture()
        before = bytes(cpu)
        self.library.transport_reset()
        result = run_native_guest(env,self.entry,0x503420,0,(),
            source_context=cpu,source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(result.kind,'transfer', result.side.errors)
        self.assertFalse(result.side.completed)
        self.assertEqual(result.side.fault,0)
        self.assertEqual(bytes(cpu),before)
        self.assertEqual(self.library.transport_continued(),0)
        self.assertEqual(self.library.transport_destroyed(),1)
        snap = result.snapshot
        self.assertEqual(snap.event.code,0xe06d7363)
        self.assertEqual(snap.event.flags,1)
        self.assertEqual(len(snap.event.information),3)
        self.assertEqual(snap.event.information[0],0x19930520)
        self.assertEqual(snap.event.information[2],0x51eb68)
        self.assertEqual(len(snap.stack),STACK_SIZE)
        self.assertEqual(len(snap.heap),env.heap_bytes)
        self.assertEqual(len(snap.image_data),env.program.size-env.data_offset)
        self.assertEqual(snap.heap[marker-HEAP_BASE:marker-HEAP_BASE+32],b'physical-effect-before-raise!!!!')
        self.assertTrue(effects)
        self.assertLess(snap.remaining_operations,env.maximum_operations)
        self.assertGreater(snap.remaining_operations,0)
        original = self.original_snapshot()
        for name in ('cpu','stack','heap','image_data','event'):
            self.assertEqual(getattr(snap,name),original[name],name)
        captured = (snap.cpu,snap.stack,snap.heap,snap.image_data,snap.event)
        env.machine.write(STACK_BASE,bytes(STACK_SIZE))
        env.machine.write(HEAP_BASE,bytes(env.heap_bytes))
        cpu.eax=0
        self.assertEqual((snap.cpu,snap.stack,snap.heap,snap.image_data,snap.event),captured)
        self.assertFalse(env._host.sourceContext)
        self.assertFalse(env._host.remainingOperations)
        self.assertEqual(env._host.sourceReturnPC,0)

    def test_successful_original_factory_returns_normally(self):
        from Tests.clawparity.guest_adapter import run_native_guest
        env,cpu,_,_ = self.fixture()
        allocated = []
        def allocate(e,call):
            token = e.object(call.arguments[1], 'real factory allocation', fill=0)
            allocated.append(token)
            return token
        env.override(0x546aa8,allocate)
        self.library.transport_reset()
        result = run_native_guest(env,self.entry,0x503420,0,(),
            source_context=cpu,source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(result.kind,'returned',result.side.errors)
        self.assertTrue(result.side.completed)
        self.assertEqual(result.side.fault,0)
        self.assertIsNone(result.snapshot)
        self.assertEqual(len(allocated),1)
        self.assertEqual(result.side.eax,allocated[0])
        self.assertEqual(self.library.transport_continued(),1)
        self.assertEqual(self.library.transport_destroyed(),1)

    def test_physical_callback_error_is_host_fault(self):
        from Tests.clawparity.guest_adapter import run_native_guest
        env,cpu,_,_ = self.fixture()
        def broken(e,call):
            raise ValueError('controlled physical callback failure')
        env.override(0x546aa8,broken)
        self.library.transport_reset()
        result = run_native_guest(env,self.entry,0x503420,0,(),
            source_context=cpu,source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(result.kind,'fault')
        self.assertEqual(result.side.fault,6)
        self.assertIsNone(result.snapshot)
        self.assertEqual(self.library.transport_continued(),0)
        self.assertEqual(self.library.transport_destroyed(),1)

    def test_capture_callback_cannot_publish_stale_memory(self):
        from Tests.clawparity.guest_adapter import run_native_guest
        byte_callback = C.CFUNCTYPE(C.c_void_p,C.c_void_p,U32,U32)
        for region in ('stack','heap','root-cpu','root-header-with-budget-fault'):
            with self.subTest(region=region):
                env,cpu,marker,_ = self.fixture()
                original = byte_callback(env._host.bytes)
                mutations = []
                def mutate(user,address,count):
                    pointer = original(user,address,count)
                    if address == STACK_BASE and count == STACK_SIZE:
                        if region == 'root-cpu':
                            cpu.eax ^= 1
                        elif region == 'root-header-with-budget-fault':
                            cpu.inputMask = 0
                            env._host.fault = 3
                        else:
                            target = env._stack if region == 'stack' else env._heap
                            offset = 64 if region == 'stack' else marker-HEAP_BASE
                            target[offset] ^= 0xff
                        mutations.append(region)
                    return pointer
                callback = byte_callback(mutate)
                env._host.bytes = C.cast(callback,C.c_void_p)
                self.library.transport_reset()
                result = run_native_guest(env,self.entry,0x503420,0,(),
                    source_context=cpu,source_return_pc=0x5022b4,flavor=self.flavor)
                self.assertTrue(mutations)
                self.assertEqual(result.kind,'fault')
                self.assertNotEqual(result.side.fault,0)
                if region == 'root-header-with-budget-fault':
                    self.assertEqual(result.side.fault,3)
                self.assertIsNone(result.snapshot)
                self.assertEqual(self.library.transport_continued(),0)

    def test_changed_context_pointer_is_rejected_before_read(self):
        # Contain a regression in native pointer validation in a child process.
        code = """
import ctypes as C
from Tests.test_native_guest_adapter import NativeGuestAdapterTests as T
from Tests.clawparity.env import NativeSourceContext
from Tests.clawparity.guest_adapter import run_native_guest
T.setUpClass(); t=T(); env,cpu,_,_=t.fixture()
def change(e,call):
    e._host.sourceContext=C.cast(C.c_void_p(1),C.POINTER(NativeSourceContext))
    return 0
env.override(0x546aa8,change)
r=run_native_guest(env,T.entry,0x503420,0,(),source_context=cpu,source_return_pc=0x5022b4,flavor=T.flavor)
assert r.kind=='fault' and r.side.fault and r.snapshot is None
assert T.library.transport_continued()==0
"""
        command,environment = [sys.executable],dict(os.environ)
        if self.flavor == 'sanitize':
            command,environment = build.sanitized_python()
            self.assertTrue(command)
            environment['CLAW_GUEST_TEST_FLAVOR']='sanitize'
        result = subprocess.run(command+['-c',code],cwd=ROOT,env=environment,
            capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr[-3000:])

    def test_session_lifetime_thread_and_library_ownership(self):
        from Tests.clawparity.guest_adapter import GuestConfig,GuestOutcome,support_library,run_native_guest
        lib = support_library(self.flavor)
        env,cpu,_,_ = self.fixture()
        host = env._host
        config = GuestConfig(C.sizeof(GuestConfig),1,0x503420,*env.program.text,
            0x546958,env.machine.import_stub[0x546958])
        session = lib.claw_guest_create(C.byref(host),C.byref(config))
        generation = lib.claw_guest_generation(session,C.byref(host))
        self.assertTrue(session and generation)
        foreign = NativeHost()
        self.assertEqual(lib.claw_guest_generation(session,C.byref(foreign)),0)
        self.assertEqual(lib.claw_guest_generation(1,C.byref(host)),0)
        self.assertEqual(lib.claw_guest_destroy(session,C.byref(host),generation+1),0)
        observed = []
        def foreign_thread():
            observed.extend((lib.claw_guest_generation(session,C.byref(host)),
                lib.claw_guest_destroy(session,C.byref(host),generation)))
        worker = threading.Thread(target=foreign_thread)
        worker.start(); worker.join(timeout=10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(observed,[0,0])
        self.assertEqual(host.fault,0)
        entry_type = C.CFUNCTYPE(U32,U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32))
        def complete(function,receiver,arguments,count,h,result):
            result[0]=123
            return 1
        entry = entry_type(complete)
        output,outcome = U32(),GuestOutcome()
        args = (session,C.byref(host),generation,C.cast(entry,C.c_void_p),
            0x503420,0,None,0,C.byref(output),C.byref(outcome))
        self.assertEqual(lib.claw_guest_run(*args),1)
        self.assertEqual((output.value,outcome.kind),(123,1))
        self.assertEqual(lib.claw_guest_run(*args),0)
        self.assertEqual(host.fault,5)
        self.assertEqual(lib.claw_guest_destroy(session,C.byref(host),generation),1)
        self.assertEqual(lib.claw_guest_generation(session,C.byref(host)),0)
        self.assertEqual(lib.claw_guest_destroy(session,C.byref(host),generation),0)
        host.fault=0
        fresh = lib.claw_guest_create(C.byref(host),C.byref(config))
        next_generation = lib.claw_guest_generation(fresh,C.byref(host))
        self.assertGreater(next_generation,generation)
        self.assertEqual(lib.claw_guest_destroy(fresh,C.byref(host),generation),0)
        self.assertEqual(lib.claw_guest_destroy(fresh,C.byref(host),next_generation),1)
        env,cpu,_,_ = self.fixture()
        other_flavor = 'O2' if self.flavor == 'O0' else 'O0'
        result = run_native_guest(env,self.entry,0x503420,0,(),
            source_context=cpu,source_return_pc=0x5022b4,flavor=other_flavor)
        self.assertEqual((result.kind,result.side.fault),('fault',5))
        self.assertIsNone(result.snapshot)

    def test_budget_fault_cannot_become_transfer(self):
        from Tests.clawparity.guest_adapter import run_native_guest
        env,cpu,_,effects = self.fixture()
        env.maximum_operations = 1
        self.library.transport_reset()
        result = run_native_guest(env,self.entry,0x503420,0,(),
            source_context=cpu,source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(result.kind,'fault')
        self.assertEqual(result.side.fault,3)
        self.assertIsNone(result.snapshot)
        self.assertEqual(effects,[])
        self.assertEqual(self.library.transport_continued(),0)

    def test_non_opted_in_source_entry_rejects_guest_graph(self):
        from Tests.clawparity.guest_adapter import run_native_guest
        env,cpu,_,effects = self.fixture()
        entry = self.library.transport_unsupported_entry
        entry.argtypes,entry.restype = self.entry.argtypes,self.entry.restype
        self.library.transport_reset()
        result = run_native_guest(env,entry,0x503420,0,(),
            source_context=cpu,source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(result.kind,'fault')
        self.assertEqual(result.side.fault,5)
        self.assertIsNone(result.snapshot)
        self.assertEqual(effects,[])
        self.assertEqual(self.library.transport_continued(),0)
        self.assertEqual(self.library.transport_destroyed(),0)

if __name__ == '__main__':
    unittest.main()
