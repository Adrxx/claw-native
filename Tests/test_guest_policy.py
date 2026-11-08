"""Execute the normalized policy against genuine original singleton paths."""
import copy
import ctypes as C
from dataclasses import replace
from types import SimpleNamespace
import unittest
from Tests import test_guest_reference as reference_tests
from Tests.test_guest_contract import specification
from Tests.clawparity.guest_contract import normalize_guest_contract,GuestDependency
from Tests.clawparity.guest_policy import GuestPolicy,_validated
from Tests.clawparity.env import NativeCall,NativeSourceContext,NativeCompilerContext
from Tests.clawparity.guest_reference import run_original_guest_source
from Tests.clawparity.kernel import ContextFault,STACK_TOP

class GuestPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference_tests.GuestReferenceTests.setUpClass()
        cls.plan=normalize_guest_contract(specification())

    def fixture(self):return reference_tests.GuestReferenceTests().fixture()

    def run_original(self,env,owner,cpu,**options):
        return run_original_guest_source(env,0x503420,owner,(0x502369,),
            allowed_handlers=self.plan.allowed_handlers,source_context=cpu,source_return_pc=0x5022b4,
            source_convention='thiscall',contract=self.plan,**options)

    def test_runtime_rejects_reduced_mutable_and_forged_dependencies(self):
        plan=self.plan
        malformed=[None,[],list(plan.dependencies),plan.dependencies[:-1],
            plan.dependencies+(plan.dependencies[0],),tuple(reversed(plan.dependencies)),
            (dict(address=plan.dependencies[0].address),)+plan.dependencies[1:],
            (SimpleNamespace(**{name:getattr(plan.dependencies[0],name)
                for name in GuestDependency.__slots__}),)+plan.dependencies[1:]]
        for records in malformed:
            with self.subTest(records=type(records)):
                with self.assertRaises(ContextFault):_validated(replace(plan,dependencies=records))
        for index,dependency in enumerate(plan.dependencies):
            mutations=dict(address=0x502335,convention='fastcall',argc=3,returns='double',
                channel='physical',input_mask=0x5c0,output_mask=0x581,
                preserve_mask=0 if dependency.preserve_mask else 0x472)
            for field,value in mutations.items():
                with self.subTest(address=dependency.address,field=field):
                    records=list(plan.dependencies);records[index]=replace(dependency,**{field:value})
                    with self.assertRaises(ContextFault):_validated(replace(plan,dependencies=tuple(records)))
            for field in GuestDependency.__slots__:
                with self.subTest(address=dependency.address,dropped=field):
                    damaged=copy.copy(dependency);object.__delattr__(damaged,field)
                    records=list(plan.dependencies);records[index]=damaged
                    with self.assertRaises(ContextFault):_validated(replace(plan,dependencies=tuple(records)))
        for field,value in (('address',True),('argc',False),('input_mask',True),
                ('output_mask',0x7ff+0.0),('preserve_mask',False)):
            dependency=next(d for d in plan.dependencies if d.address==0x502e95)
            records=tuple(replace(d,**{field:value}) if d is dependency else d for d in plan.dependencies)
            with self.assertRaises(ContextFault):_validated(replace(plan,dependencies=records))
        reduced=copy.copy(plan);object.__delattr__(reduced,'dependencies')
        with self.assertRaises(ContextFault):_validated(reduced)
        self.assertEqual(_validated(plan)[0],plan)

    def dependency_call(self,dependency):
        context_type=NativeCompilerContext if dependency.channel=='compiler_context' else NativeSourceContext
        context=context_type()
        context.size,context.version=72,1
        context.inputMask,context.outputMask=dependency.input_mask,dependency.output_mask
        context.esp,context.eip,context.eflags,context.fsHead=STACK_TOP,dependency.address,2,0xffffffff
        raw=NativeCall();raw.function=dependency.address;raw.argumentCount=dependency.argc
        if dependency.channel=='compiler_context':
            context.continuation=0x50342a;raw.compilerContext=C.pointer(context)
        else:
            context.preserveMask=dependency.preserve_mask
            raw.sourceContext=C.pointer(context);raw.stackPointer=context.esp
            raw.sourceReturnPC=0x503450 if dependency.address in self.plan.allowed_factories else 0x503444
        return raw,context

    def test_native_dependencies_check_exact_contract_before_bridge(self):
        policy=object.__new__(GuestPolicy);policy.contract=self.plan;policy._program=reference_tests.GuestReferenceTests.program
        effects=[]
        for dependency in self.plan.dependencies:
            raw,context=self.dependency_call(dependency)
            policy.native_call(raw)
            mutations=[('raw','argumentCount',dependency.argc+1),('raw','receiver',1),('raw','receiver2',1),
                ('raw','x87ArgumentCount',1),('context','size',68),('context','version',2),
                ('context','reserved0',1),('context','reserved1',1),('context','inputMask',0x5c0),
                ('context','outputMask',0x581),('context','eip',0x502335),('context','esp',STACK_TOP+1)]
            if dependency.channel=='source_context':
                mutations.extend([('context','preserveMask',0 if dependency.preserve_mask else 0x472),
                    ('raw','sourceContext',None),('raw','compilerContext',C.pointer(NativeCompilerContext())),
                    ('raw','stackPointer',STACK_TOP-4)])
            else:
                mutations.extend([('raw','compilerContext',None),('raw','sourceContext',C.pointer(NativeSourceContext())),
                    ('raw','sourceReturnPC',0x50342a),('raw','stackPointer',STACK_TOP)])
            for target,field,value in mutations:
                with self.subTest(address=dependency.address,field=field):
                    raw,context=self.dependency_call(dependency)
                    setattr(raw if target=='raw' else context,field,value)
                    with self.assertRaises(ContextFault):
                        policy.native_call(raw);effects.append(dependency.address)
        self.assertEqual(effects,[])
        dependency=next(d for d in self.plan.dependencies if d.address==0x502369)
        for field,value in (('function',0x502335),('sourceReturnPC',0x503444)):
            raw,context=self.dependency_call(dependency);setattr(raw,field,value)
            with self.assertRaises(ContextFault):policy.native_call(raw)

    def test_all_three_genuine_factories_return_and_unhandle(self):
        for factory in sorted(self.plan.allowed_factories):
            for success in (False,True):
                with self.subTest(factory=hex(factory),success=success):
                    env,owner,crt,depths,physical,cpu=self.fixture()
                    allocated=[]
                    if success:
                        def allocate(e,c):
                            value=e.object(c.arguments[1],'genuine factory allocation',fill=0)
                            allocated.append(value)
                            return value
                        env.override(0x546aa8,allocate)
                    header=bytes(cpu)
                    out=run_original_guest_source(env,0x503420,owner,(factory,),
                        allowed_handlers=self.plan.allowed_handlers,source_context=cpu,
                        source_return_pc=0x5022b4,source_convention='thiscall',contract=self.plan)
                    self.assertEqual(out.kind,'returned' if success else 'unhandled',out.side.errors)
                    self.assertEqual(out.side.errors,[])
                    self.assertTrue(any(address==factory for address,size in out.coverage))
                    self.assertEqual(bytes(cpu),header)
                    if success:
                        self.assertEqual(out.side.eax,allocated[0])
                        self.assertEqual(env.machine.words(owner,1)[0],allocated[0])
                        self.assertEqual(out.transfers,())
                    else:
                        self.assertEqual(len(out.transfers),4)
                        self.assertTrue(any(0x503454<=address<0x503464 for address,size in out.coverage))

    def test_root_keeps_its_zero_preservation_contract(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        cpu.preserveMask=0x472
        with self.assertRaises(ContextFault):self.run_original(env,owner,cpu)
        self.assertEqual(physical,[])

    def test_genuine_graph_with_allocation_bounds_passes(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        out=self.run_original(env,owner,cpu,check_objects=True)
        self.assertEqual(out.kind,'unhandled',out.side.errors)
        self.assertEqual(len(out.transfers),4)
        self.assertEqual(out.side.errors,[])

    def test_frozen_selection_metadata_must_match_original(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        env.backend='initial';env.put(0x51ebc0,0);env._freeze()
        with self.assertRaises(ContextFault):self.run_original(env,owner,cpu)
        self.assertEqual(physical,[])

    def test_callback_metadata_and_live_factory_replacement_rejected(self):
        for address,value in ((0x51ebc0,0),(STACK_TOP+4,0x4a48c0)):
            with self.subTest(address=address):
                env,owner,crt,depths,physical,cpu=self.fixture()
                slot=next(s for s,name in env.program.imports.items() if name.split('!')[-1]=='GetVersion')
                def mutate(e,c):e.put(address,value);return 10
                env.override(slot,mutate)
                out=self.run_original(env,owner,cpu)
                self.assertEqual(out.kind,'fault')
                self.assertEqual(out.side.fault,5)
                self.assertEqual(out.transfers,())

    def test_object_bounds_failure_cannot_pass_cases_check(self):
        env,owner,crt,depths,physical,cpu=self.fixture()
        heap,image,spans,bump,names=env._frozen
        spans=dict(spans);del spans[owner]
        env._frozen=(heap,image,spans,bump,names)
        out=self.run_original(env,owner,cpu,check_objects=True)
        self.assertEqual(out.kind,'fault')
        self.assertTrue(out.side.errors)

if __name__=='__main__':unittest.main()
