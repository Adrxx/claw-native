"""Guest comparison rejects mismatches and keeps unhandled separate from RET."""
import copy
from dataclasses import replace
import unittest
from Tests import test_guest_reference as reference_tests
from Tests.clawparity.guest_compare import compare_guest_outcomes
from Tests.clawparity.guest_exception import CPU

class GuestCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference_tests.GuestReferenceTests.setUpClass()
        helper=reference_tests.GuestReferenceTests()
        env,owner,crt,depths,physical,cpu=helper.fixture()
        cls.env=env
        cls.original=helper.run_reference(env,owner,cpu)
        assert cls.original.kind=='unhandled'

    def compare(self,native,expected='unhandled',return_sp=1):
        return compare_guest_outcomes(self.env,native,self.original,
            expected=expected,expected_return_sp=return_sp)

    def test_unhandled_does_not_require_ordinary_return_stack(self):
        self.assertIsNone(self.compare(self.original,return_sp=1))

    def test_fault_cannot_count_as_matching_unhandled(self):
        self.assertEqual(self.compare(replace(self.original,kind='fault'))['kind'],'guest-outcome')

    def test_missing_terminal_state_rejected(self):
        self.assertEqual(self.compare(replace(self.original,terminal_cpu=None))['kind'],'guest-state')

    def test_each_snapshot_field_is_compared(self):
        first=self.original.transfers[0]
        changes={'event':None,'cpu':CPU((0,)*10,0),'stack':b'changed','heap':b'changed',
            'image_data':b'changed','spans':(),'freed':(123,), 'allocator_cursor':0,
            'names':(),'events':()}
        for field,value in changes.items():
            with self.subTest(field=field):
                self.assertNotEqual(getattr(first,field),value)
                transfer=replace(first,**{field:value})
                outcome=replace(self.original,transfers=(transfer,*self.original.transfers[1:]))
                self.assertEqual(self.compare(outcome)['kind'],'guest-state')

    def test_terminal_memory_and_exception_record_are_compared(self):
        side=copy.copy(self.original.side);side.heap=b'changed'
        self.assertEqual(self.compare(replace(self.original,side=side))['kind'],'guest-state')
        result=replace(self.original.result,exception=None)
        self.assertEqual(self.compare(replace(self.original,result=result))['kind'],'guest-state')

    def test_normal_return_compares_final_allocation_identity_and_result(self):
        helper=reference_tests.GuestReferenceTests()
        env,owner,crt,depths,physical,cpu=helper.fixture()
        env.backend='initial';env.put(owner,crt);env._freeze()
        original=helper.run_reference(env,owner,cpu)
        changes=[replace(original,terminal_state=replace(original.terminal_state,allocator_cursor=0)),
            replace(original,terminal_state=replace(original.terminal_state,names=())),
            replace(original,result=replace(original.result,eax=0))]
        for native in changes:
            self.assertIsNotNone(compare_guest_outcomes(env,native,original,
                expected='returned',expected_return_sp=cpu.esp+8))

    def test_physical_halt_compares_fault_address(self):
        from Tests.clawparity.env import Halt
        helper=reference_tests.GuestReferenceTests()
        env,owner,crt,depths,physical,cpu=helper.fixture()
        def stop(e,c): raise Halt('stop')
        env.override(0x546aa8,stop)
        original=helper.run_reference(env,owner,cpu)
        side=copy.copy(original.side);side.fault_address^=4
        self.assertIsNotNone(compare_guest_outcomes(env,replace(original,side=side),original,
            expected='halt',expected_return_sp=cpu.esp+8))

if __name__=='__main__':unittest.main()
