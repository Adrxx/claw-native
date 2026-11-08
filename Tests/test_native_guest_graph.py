"""Original-root/native-catch transport proof, not whole-singleton admission."""
import ctypes as C
import os
from pathlib import Path
import unittest
from Tests.clawparity import build
from Tests.clawparity.env import Env, HEAP_BASE
from Tests.clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_REGISTERS
from Tests.clawparity.program import claw
from Tests.clawparity.guest_exception import CPU, GuestExceptionRunner

ROOT = Path(__file__).resolve().parents[1]
HANDLERS = frozenset((0x508539,0x508bf8,0x4a3260,0x4a9348,0x4a3490))

class NativeGuestGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flavor = os.environ.get('CLAW_GUEST_TEST_FLAVOR','O2')
        cls.program = claw()
        cls.library = C.CDLL(str(build.library('native-guest-funclet-independent',
            [ROOT/'Tests/NativeGuestTransfer/funclet.cpp'],flavor=cls.flavor,guest_transfer=True)))

    def fixture(self):
        env = Env(self.program,strict=False)
        env._begin_case(None)
        owner = env.object(4,'singleton publication',fill=0)
        crt = env.object(0x74,'initialized CRT thread',fill=0)
        env.put(0x52edd8,17)
        depths,physical = {},[]
        arities = {'GetLastError':0,'SetLastError':1,'TlsGetValue':1,'GetVersion':0,
            'InitializeCriticalSection':1,'EnterCriticalSection':1,'LeaveCriticalSection':1,
            'LocalAlloc':2,'RaiseException':4,'RtlUnwind':4,'IsBadReadPtr':2,'IsBadWritePtr':2}
        def effect(label):
            def serve(e,c):
                physical.append((label,tuple(c.arguments)))
                if label == 'GetVersion': return 10
                if label == 'TlsGetValue':
                    self.assertEqual(c.arguments,(17,))
                    return crt
                if label == 'InitializeCriticalSection': depths[c.arguments[0]]=0
                elif label == 'EnterCriticalSection': depths[c.arguments[0]]+=1
                elif label == 'LeaveCriticalSection': depths[c.arguments[0]]-=1
                elif label in ('RaiseException','RtlUnwind'):
                    raise AssertionError('physical transfer must not return through a fixture')
                return 0
            return serve
        for slot,label in env.program.imports.items():
            name=label.split('!')[-1]
            if name in arities: env.fixture(slot,'stdcall',arities[name],effect(name))
        self.prepare(env)
        self.assertTrue(env.machine.call(0x4a7da0,arguments=(crt,),stack_pointer=STACK_TOP-0x4000).completed)
        env._initial['heap'][:]=env.machine.read(HEAP_BASE,env.heap_bytes)
        env._initial['image'][env.data_offset:]=env.machine.read(env.program.data_start,env.program.size-env.data_offset)
        env._initial['stack'][:]=env.machine.read(STACK_BASE,STACK_SIZE)
        env._freeze()
        physical.clear()
        for function,argc in ((0x502f05,1),(0x4a5690,2)):
            env.source_callees[function]={'kind':'whole','convention':'stdcall','argc':argc,
                'source_context':{'input_mask':0x7ff,'output_mask':0x7ff,'preserve_mask':0}}
        return env,owner,crt,depths,physical

    @staticmethod
    def prepare(env):
        env.machine.write(HEAP_BASE,bytes(env._initial['heap']))
        env.machine.write(env.program.data_start,bytes(env._initial['image'])[env.data_offset:])
        env.machine.write(STACK_BASE,bytes(env._initial['stack']))
        env.backend,env.side='machine','original'
        if hasattr(env,'_frozen'): env._reset_run()

    def original(self):
        env,owner,crt,depths,physical=self.fixture()
        self.prepare(env)
        runner=GuestExceptionRunner(env.machine,allowed_handlers=HANDLERS)
        snapshots=[]
        def capture(event):
            snapshots.append((event,env.machine.read(STACK_BASE,STACK_SIZE),
                env.machine.read(HEAP_BASE,env.heap_bytes),
                env.machine.read(env.program.data_start,env.program.size-env.data_offset),
                tuple(sorted(env.spans.items())),tuple(env.freed),env._bump,
                tuple(sorted(env.names.items()))))
        runner.on_physical=capture
        result=runner.call(0x503420,ecx=owner,arguments=(0x502369,))
        return dict(result=result,snapshots=snapshots,cpu=CPU(tuple(env.machine.register(r) for r in CONTEXT_REGISTERS),env.machine.fs_head),
            stack=env.machine.read(STACK_BASE,STACK_SIZE),heap=env.machine.read(HEAP_BASE,env.heap_bytes),
            image=env.machine.read(env.program.data_start,env.program.size-env.data_offset),
            depths=depths,physical=physical,owner=env.machine.words(owner,1)[0],crt=env.machine.words(crt+0x6c,2))

    def graph(self,entry):
        from Tests.clawparity.guest_adapter import GuestFuncletRoute,GuestGraph
        route=GuestFuncletRoute(owner_entry=0x503420,entry_pc=0x503454,handler=0x508bf8,
            func_info=0x51ebc0,handler_table=0x51ec08,call_site=0x4a8f25,return_pc=0x4a8f27,native_entry=entry)
        return GuestGraph(allowed_handlers=HANDLERS,owned_ranges=((0x503454,0x503464),),funclet=route)

    def test_genuine_dispatch_calls_native_catch_then_both_unwinds(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        expected=self.original()
        env,owner,crt,depths,physical=self.fixture()
        self.library.catch_reset()
        outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
            graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        self.assertEqual(outcome.kind,'unhandled',outcome.side.errors)
        self.assertEqual([type(e).__name__ for e in outcome.result.transitions],['Raise','Unwind','Raise','Unwind'])
        self.assertEqual(outcome.result.transitions,expected['result'].transitions)
        self.assertEqual([(s.event,s.stack,s.heap,s.image_data,s.spans,s.freed,
            s.allocator_cursor,s.names) for s in outcome.transfers],expected['snapshots'])
        self.assertEqual(outcome.result.exception.words,expected['result'].exception.words)
        self.assertEqual(outcome.terminal_cpu,expected['cpu'])
        self.assertEqual(outcome.terminal_stack,expected['stack'])
        self.assertEqual(env.machine.read(HEAP_BASE,env.heap_bytes),expected['heap'])
        self.assertEqual(env.machine.read(env.program.data_start,env.program.size-env.data_offset),expected['image'])
        self.assertEqual(depths,expected['depths'])
        self.assertEqual(physical,expected['physical'])
        self.assertEqual(env.machine.words(owner,1),(0,))
        self.assertEqual(env.machine.words(crt+0x6c,2),(0,0))
        self.assertEqual(self.library.catch_entered(),1)
        self.assertEqual(self.library.catch_continued(),0)
        self.assertEqual(self.library.catch_destroyed(),1)
        self.assertEqual(len(outcome.invocations),1)

    def test_returning_catch_is_fault_not_fabricated_continuation(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        env,owner,crt,depths,physical=self.fixture()
        self.library.catch_reset()
        outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
            graph=self.graph(self.library.transport_returning_catch),flavor=self.flavor)
        self.assertEqual(outcome.kind,'fault')
        self.assertNotEqual(outcome.side.fault,0)
        self.assertIsNone(outcome.terminal_cpu)
        self.assertIsNone(outcome.terminal_stack)
        self.assertEqual(outcome.terminal_provenance,'unavailable-native-funclet-fault')

    def test_owned_root_cannot_fall_back_to_original_execution(self):
        from dataclasses import replace
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        env,owner,crt,depths,physical=self.fixture()
        self.library.catch_reset()
        graph=replace(self.graph(self.library.transport_catch),
            owned_ranges=((0x503420,0x50348b),))
        outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
            graph=graph,flavor=self.flavor)
        self.assertEqual(outcome.kind,'fault')
        self.assertNotEqual(outcome.side.fault,0)
        self.assertEqual(physical,[])
        self.assertEqual(self.library.catch_entered(),0)
        self.assertEqual(outcome.invocations,())

    def test_unattached_handler_table_is_rejected(self):
        from dataclasses import replace
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        from Tests.clawparity.kernel import ContextFault
        env,owner,crt,depths,physical=self.fixture()
        self.library.catch_reset()
        graph=self.graph(self.library.transport_catch)
        graph=replace(graph,funclet=replace(graph.funclet,handler_table=0x51ec0c))
        with self.assertRaises(ContextFault):
            run_original_guest_graph(env,0x503420,owner,(0x502369,),
                graph=graph,flavor=self.flavor)
        self.assertEqual(physical,[])
        self.assertEqual(self.library.catch_entered(),0)
        self.assertIsNone(getattr(env,'_guest_adapter',None))

    def test_native_normal_return_publishes_native_terminal_state(self):
        from Tests.test_native_guest_adapter import NativeGuestAdapterTests
        from Tests.clawparity.guest_adapter import run_native_guest_graph
        helper=NativeGuestAdapterTests()
        helper.program=self.program
        env,cpu,marker,effects=helper.fixture()
        allocated=[]
        def allocate(e,call):
            token=e.object(call.arguments[1],'normal graph allocation',fill=0)
            allocated.append(token)
            return token
        env.override(0x546aa8,allocate)
        library=C.CDLL(str(build.library('native-guest-independent',
            [ROOT/'Tests/NativeGuestTransfer/transport.cpp'],flavor=self.flavor,guest_transfer=True)))
        outcome=run_native_guest_graph(env,library.transport_entry,0x503420,0,(),
            graph=self.graph(self.library.transport_catch),source_context=cpu,
            source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(outcome.kind,'returned',outcome.side.errors)
        self.assertEqual(outcome.side.eax,allocated[0])
        self.assertEqual(outcome.terminal_cpu,CPU(tuple(getattr(cpu,name) for name in
            ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags')),cpu.fsHead))
        self.assertEqual(outcome.terminal_stack,bytes(env._stack))
        self.assertEqual(outcome.transfers,())
        self.assertEqual(outcome.invocations,())
        self.assertEqual(outcome.terminal_state.allocator_cursor,env._bump)
        self.assertEqual(outcome.terminal_state.names,tuple(sorted(env.names.items())))
        self.assertEqual(outcome.terminal_state.spans,tuple(sorted(outcome.side.spans.items())))
        self.assertEqual(outcome.terminal_state.freed,tuple(outcome.side.freed))
        retained=outcome.terminal_state
        env.names.clear()
        env._bump=0
        self.assertEqual(outcome.terminal_state,retained)
        self.assertTrue(outcome.terminal_state.names)

    def test_synthetic_parent_headers_survive_module_factory_contract(self):
        from Tests.test_native_guest_adapter import NativeGuestAdapterTests
        from Tests.test_guest_contract import specification
        from Tests.clawparity.guest_contract import normalize_guest_contract
        from Tests.clawparity.guest_adapter import run_native_guest_graph
        from dataclasses import replace
        helper=NativeGuestAdapterTests();helper.program=self.program
        library=C.CDLL(str(build.library('native-guest-header-independent',
            [ROOT/'Tests/NativeGuestTransfer/transport.cpp',ROOT/'Tests/NativeGuestTransfer/funclet.cpp'],
            flavor=self.flavor,guest_transfer=True)))
        for mask,entry in ((0,library.transport_zero_header_entry),(0x400,library.transport_nonzero_header_entry)):
            with self.subTest(parent_mask=mask):
                env,cpu,marker,effects=helper.fixture();cpu.preserveMask=mask
                env.source_callees[0x502369]['returns']='u32'
                env.override(0x546aa8,lambda e,c:e.object(c.arguments[1],'header crossing allocation',fill=0))
                fields=('size','version','inputMask','outputMask','preserveMask','reserved0','reserved1')
                header=tuple(getattr(cpu,name) for name in fields)
                spec=specification();spec['owned'][0]['attached_entries'][0]['native_entry']='transport_catch'
                plan=normalize_guest_contract(spec)
                graph=replace(self.graph(library.transport_catch),allowed_handlers=plan.allowed_handlers,
                    owned_ranges=plan.owned_ranges,contract=plan if mask==0 else None)
                outcome=run_native_guest_graph(env,entry,0x503420,0,(0x502369,),
                    graph=graph,source_context=cpu,source_return_pc=0x5022b4,source_convention='thiscall',flavor=self.flavor)
                self.assertEqual(outcome.kind,'returned',outcome.side.errors)
                self.assertEqual(outcome.side.errors,[])
                self.assertEqual(tuple(getattr(cpu,name) for name in fields),header)
                self.assertEqual(cpu.esp,STACK_TOP+8)
                self.assertEqual(cpu.eip,0x5022b4)
                self.assertEqual(cpu.eax,outcome.side.eax)
                self.assertGreater(cpu.eax,HEAP_BASE)

    def test_native_budget_fault_does_not_publish_stale_machine_state(self):
        from Tests.test_native_guest_adapter import NativeGuestAdapterTests
        from Tests.clawparity.guest_adapter import run_native_guest_graph
        helper=NativeGuestAdapterTests()
        helper.program=self.program
        env,cpu,marker,effects=helper.fixture()
        env.maximum_operations=1
        library=C.CDLL(str(build.library('native-guest-independent',
            [ROOT/'Tests/NativeGuestTransfer/transport.cpp'],flavor=self.flavor,guest_transfer=True)))
        outcome=run_native_guest_graph(env,library.transport_entry,0x503420,0,(),
            graph=self.graph(self.library.transport_catch),source_context=cpu,
            source_return_pc=0x5022b4,flavor=self.flavor)
        self.assertEqual(outcome.kind,'fault')
        self.assertEqual(outcome.side.fault,3)
        self.assertEqual(outcome.terminal_cpu,CPU(tuple(getattr(cpu,name) for name in
            ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags')),cpu.fsHead))
        self.assertEqual(outcome.terminal_stack,bytes(env._stack))

    def test_original_callback_cannot_replace_shared_budget(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        env,owner,crt,depths,physical=self.fixture()
        replacement=C.c_uint64(100000000)
        slot=next(s for s,name in env.program.imports.items() if name.split('!')[-1]=='GetVersion')
        def mutate(e,call):
            e._host.remainingOperations=C.pointer(replacement)
            return 10
        env.override(slot,mutate)
        self.library.catch_reset()
        outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
            graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        self.assertEqual(outcome.kind,'fault')
        self.assertNotEqual(outcome.side.fault,0)
        self.assertEqual(self.library.catch_entered(),0)
        self.assertEqual(replacement.value,100000000)

    def test_original_callback_cannot_refill_shared_budget(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        env,owner,crt,depths,physical=self.fixture()
        slot=next(s for s,name in env.program.imports.items() if name.split('!')[-1]=='GetVersion')
        def refill(e,call):
            e._source_budget.value+=1000000
            return 10
        env.override(slot,refill)
        self.library.catch_reset()
        outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
            graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        self.assertEqual(outcome.kind,'fault')
        self.assertNotEqual(outcome.side.fault,0)
        self.assertEqual(self.library.catch_entered(),0)

    def test_owned_catch_fixture_is_rejected_before_effect(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        from Tests.clawparity.kernel import ContextFault
        env,owner,crt,depths,physical=self.fixture()
        intercepted=[]
        env.fixture(0x503454,'cdecl',0,lambda e,c: intercepted.append(c) or 0)
        self.library.catch_reset()
        try:
            outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
                graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        except ContextFault:
            pass
        else:
            self.assertEqual(outcome.kind,'fault')
            self.assertNotEqual(outcome.side.fault,0)
        self.assertEqual(intercepted,[])
        self.assertEqual(self.library.catch_entered(),0)

    def test_original_callback_fault_stops_further_effects(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        env,owner,crt,depths,physical=self.fixture()
        slot=next(s for s,name in env.program.imports.items() if name.split('!')[-1]=='GetVersion')
        boundary=[]
        def fail(e,call):
            boundary.append(tuple(physical))
            e._host.fault=3
            return 10
        env.override(slot,fail)
        self.library.catch_reset()
        outcome=run_original_guest_graph(env,0x503420,owner,(0x502369,),
            graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        self.assertEqual(outcome.kind,'fault')
        self.assertEqual(outcome.side.fault,3)
        self.assertEqual(len(boundary),1)
        self.assertEqual(tuple(physical),boundary[0])
        self.assertEqual(outcome.transfers,())
        self.assertEqual(self.library.catch_entered(),0)

    def test_borrowed_original_cannot_execute_heap_factory(self):
        import struct
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        env,owner,crt,depths,physical=self.fixture()
        env.backend='initial'
        factory=env.object(6,'synthetic code',fill=0)
        env.write(factory,b'\xb8'+struct.pack('<I',crt)+b'\xc3')
        env._freeze()
        self.library.catch_reset()
        out=run_original_guest_graph(env,0x503420,owner,(factory,),
            graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        self.assertEqual(out.kind,'fault')
        self.assertEqual(out.side.fault,5)
        self.assertEqual(env.machine.words(owner,1),(0,))

    def test_synthetic_external_factory_rejected_before_effect(self):
        from Tests.clawparity.guest_adapter import run_original_guest_graph
        from Tests.clawparity.kernel import ContextFault
        env,owner,crt,depths,physical=self.fixture()
        effects=[]
        factory=env.stub('synthetic factory','cdecl',0,lambda e,c:effects.append(c) or crt)
        with self.assertRaises(ContextFault):
            run_original_guest_graph(env,0x503420,owner,(factory,),
                graph=self.graph(self.library.transport_catch),flavor=self.flavor)
        self.assertEqual(effects,[])

if __name__ == '__main__': unittest.main()
