"""Independent source-frame reference checks; no native library is loaded."""
import ctypes as C
import unittest
from Tests import test_native_guest_graph as graph_tests
HANDLERS=graph_tests.HANDLERS
from Tests.clawparity.env import NativeSourceContext, HEAP_BASE, Halt
from Tests.clawparity.kernel import CONTEXT_REGISTERS, STACK_BASE, STACK_SIZE, STACK_TOP
from Tests.clawparity.guest_exception import CPU, GuestExceptionRunner, PhysicalTransfer
from Tests.clawparity.program import claw

class GuestReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.program=claw()

    def fixture(self):
        helper=graph_tests.NativeGuestGraphTests()
        helper.program=self.program
        env,owner,crt,depths,physical=helper.fixture()
        helper.prepare(env)
        values=[env.machine.register(r) for r in CONTEXT_REGISTERS]
        values[2],values[7],values[8]=owner,STACK_TOP,0x503420
        cpu=NativeSourceContext(72,1,0x7ff,0x7ff,*values,0xffffffff,0,0,0)
        return env,owner,crt,depths,physical,cpu

    def run_reference(self,env,owner,cpu,**options):
        from Tests.clawparity.guest_reference import run_original_guest_source
        return run_original_guest_source(env,0x503420,owner,(0x502369,),
            allowed_handlers=HANDLERS,source_context=cpu,source_return_pc=0x5022b4,
            source_convention='thiscall',**options)

    def direct(self,success=False):
        env,owner,crt,depths,physical,cpu=self.fixture()
        if success:
            env.backend='initial'
            env.put(owner,crt); env._freeze(); graph_tests.NativeGuestGraphTests.prepare(env)
        snapshots=[]
        runner=GuestExceptionRunner(env.machine,allowed_handlers=HANDLERS)
        def capture(event):
            snapshots.append((event,env.machine.read(STACK_BASE,STACK_SIZE),
                env.machine.read(HEAP_BASE,env.heap_bytes),
                env.machine.read(env.program.data_start,env.program.size-env.data_offset)))
        runner.on_physical=capture
        with runner.capture_scope():
            try:
                returned=env.machine.call_source(0x503420,cpu,0x5022b4,'thiscall',owner,0,(0x502369,))
                result=None
            except PhysicalTransfer as stop:
                result=runner.resume_raise(stop.event)
        return {'result':result,'snapshots':snapshots,'cpu':CPU(tuple(env.machine.register(r) for r in CONTEXT_REGISTERS),env.machine.fs_head),
            'stack':env.machine.read(STACK_BASE,STACK_SIZE),'heap':env.machine.read(HEAP_BASE,env.heap_bytes),
            'image':env.machine.read(env.program.data_start,env.program.size-env.data_offset),'physical':physical}

    def test_unhandled_matches_direct_original_full_source_run(self):
        expected=self.direct()
        env,owner,crt,depths,physical,cpu=self.fixture()
        before=bytes(cpu); host=bytes(env._host)
        out=self.run_reference(env,owner,cpu)
        self.assertEqual(out.kind,'unhandled',out.side.errors)
        self.assertEqual(out.result.transitions,expected['result'].transitions)
        self.assertEqual(out.result.exception.words,expected['result'].exception.words)
        self.assertEqual(out.terminal_cpu,expected['cpu'])
        self.assertEqual(out.terminal_stack,expected['stack'])
        self.assertEqual(out.side.heap,expected['heap'])
        self.assertEqual(out.side.image,expected['image'])
        self.assertEqual([(s.event,s.stack,s.heap,s.image_data) for s in out.transfers],expected['snapshots'])
        self.assertEqual(physical,expected['physical'])
        self.assertEqual(bytes(cpu),before)
        self.assertEqual(bytes(env._host),host)
        self.assertIsNone(env.machine.guest_exceptions)
        self.assertTrue(any(0x503454<=a<0x503464 for a,size in out.coverage))
        self.assertGreater(out.operations,0)
        self.assertGreater(out.remaining_operations,0)

    def test_existing_singleton_returns_at_genuine_source_continuation(self):
        expected=self.direct(success=True)
        env,owner,crt,depths,physical,cpu=self.fixture()
        env.backend='initial'
        env.put(owner,crt);env._freeze()
        out=self.run_reference(env,owner,cpu)
        self.assertEqual(out.kind,'returned',out.side.errors)
        self.assertEqual(out.side.eax,crt)
        self.assertEqual(out.terminal_cpu,expected['cpu'])
        self.assertEqual(out.terminal_stack,expected['stack'])
        self.assertEqual(out.transfers,())
        self.assertFalse(any(0x503454<=a<0x503464 for a,size in out.coverage))

    def test_internal_source_continuation_is_still_traced_and_charged(self):
        from Tests.clawparity.guest_reference import run_original_guest_source
        env, owner, crt, depths, physical, cpu = self.fixture()
        env.backend = 'initial'
        env.put(owner, crt)
        env._freeze()
        options = dict(allowed_handlers=HANDLERS, source_context=cpu,
                       source_return_pc=0x503478, source_convention='thiscall')
        out = run_original_guest_source(env, 0x503420, owner, (0x502369,), **options)
        self.assertEqual(out.kind, 'returned', out.side.errors)
        self.assertIn((0x503478, 2), out.coverage)
        self.assertEqual(out.operations, len(out.coverage))
        limited = run_original_guest_source(env, 0x503420, owner, (0x502369,),
                                           max_operations=out.operations - 1, **options)
        self.assertEqual(limited.kind, 'fault')
        self.assertEqual(limited.remaining_operations, 0)

    def test_physical_halt_does_not_become_unhandled(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        def stop(e,c): raise Halt('physical stop')
        env.override(0x546aa8,stop)
        out=self.run_reference(env,owner,cpu)
        self.assertEqual(out.kind,'halt')
        self.assertTrue(out.side.halted)
        self.assertFalse(out.side.completed)
        self.assertEqual(out.transfers,())
        self.assertIsNone(env.machine.guest_exceptions)

    def test_exhausted_budget_is_fault_and_restores_scope(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        before=bytes(cpu);host=bytes(env._host)
        out=self.run_reference(env,owner,cpu,max_operations=1)
        self.assertEqual(out.kind,'fault')
        self.assertEqual(out.side.fault,3)
        self.assertEqual(bytes(cpu),before)
        self.assertEqual(bytes(env._host),host)
        self.assertIsNone(env.machine.guest_exceptions)
        self.assertEqual(physical,[])

    def test_frozen_original_code_cannot_be_replaced_by_case(self):
        from Tests.clawparity.kernel import ContextFault
        env,owner,crt,depths,physical,cpu=self.fixture()
        env.backend='initial'
        env.write(0x503454,b'\x90')
        env._freeze()
        with self.assertRaises(ContextFault): self.run_reference(env,owner,cpu)
        self.assertEqual(physical,[])

    def test_callback_cannot_modify_original_catch_code(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        slot=next(s for s,name in env.program.imports.items() if name.split('!')[-1]=='GetVersion')
        boundary=[]
        def mutate(e,c):
            boundary.append(tuple(physical))
            e.write(0x503454,b'\x90')
            return 10
        env.override(slot,mutate)
        out=self.run_reference(env,owner,cpu)
        self.assertEqual(out.kind,'fault')
        self.assertEqual(out.side.fault,5)
        self.assertEqual(tuple(physical),boundary[0])
        self.assertEqual(out.transfers,())

    def test_callback_fault_preserves_priority_and_stops(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        slot=next(s for s,name in env.program.imports.items() if name.split('!')[-1]=='GetVersion')
        boundary=[]
        def fail(e,c):
            boundary.append(tuple(physical))
            e._host.fault=3
            return 10
        env.override(slot,fail)
        out=self.run_reference(env,owner,cpu)
        self.assertEqual(out.kind,'fault')
        self.assertEqual(out.side.fault,3)
        self.assertEqual(tuple(physical),boundary[0])
        self.assertEqual(out.transfers,())

    def test_synthetic_factory_cannot_replace_original_execution(self):
        from Tests.clawparity.guest_reference import run_original_guest_source
        from Tests.clawparity.kernel import ContextFault
        env,owner,crt,depths,physical,cpu=self.fixture()
        effects=[]
        factory=env.stub('synthetic factory','cdecl',0,lambda e,c:effects.append(c) or crt)
        with self.assertRaises(ContextFault):
            run_original_guest_source(env,0x503420,owner,(factory,),
                allowed_handlers=HANDLERS,source_context=cpu,source_return_pc=0x5022b4,
                source_convention='thiscall')
        self.assertEqual(effects,[])

    def test_executable_heap_is_not_original_code(self):
        import struct
        from Tests.clawparity.guest_reference import run_original_guest_source
        env,owner,crt,depths,physical,cpu=self.fixture()
        env.backend='initial'
        factory=env.object(6,'synthetic executable bytes',fill=0)
        env.write(factory,b'\xb8'+struct.pack('<I',crt)+b'\xc3')
        env._freeze()
        out=run_original_guest_source(env,0x503420,owner,(factory,),
            allowed_handlers=HANDLERS,source_context=cpu,source_return_pc=0x5022b4,
            source_convention='thiscall')
        self.assertEqual(out.kind,'fault')
        self.assertEqual(out.side.fault,5)
        self.assertFalse(any(factory<=address<factory+6 for address,size in out.coverage))

if __name__=='__main__': unittest.main()
