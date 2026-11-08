"""Original-only grid controls; run with python -m unittest and this module.

Uses the repository's work/test-env/bin/python. No app or translations run.
"""
from collections import Counter, deque
import hashlib
import struct
import unittest
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDI,
    UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_FPCW,
    UC_X86_REG_FPSW, UC_X86_REG_FPTAG,
)
from Tests.clawparity.program import claw
from Tests.NativeMenuBase.trace import MenuTrace, Blocked, ARRAY_RETURN
from Tests.NativeLevels.grid_fixture import LargeGridFixture

STACK = 0x2000000
STOP = 0x70000000
BASE = 0x61000008
CONSTRUCT, DESTRUCT = 0x4a4590, 0x4a4450
CTOR, DTOR = 0x4f4a90, 0x4c96b0
PRESERVED = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)


class GridProbe(LargeGridFixture, MenuTrace):
    """Map the hash-checked original without startup, route input or assets."""

    def __init__(self, program, count=73728):
        self.machine = Uc(UC_ARCH_X86, UC_MODE_32)
        self.machine.mem_map(program.base, program.size)
        for section in program.sections:
            self.machine.mem_write(section.address, section.data)
        for base, size in ((0, 4096), (STACK-0x10000, 0x20000),
                           (0x61000000, 0x900000), (STOP, 0x10000)):
            self.machine.mem_map(base, size)
        self.put(0, 0xffffffff)
        for register, value in ((UC_X86_REG_FPCW, 0x027f), (UC_X86_REG_FPSW, 0),
                                (UC_X86_REG_FPTAG, 0xffff)):
            self.machine.reg_write(register, value)
        self.allocations = {BASE: count*8}
        self.machine.mem_write(BASE-8, b'leftedge')
        self.machine.mem_write(BASE, b'\xa5\x19\xc3\x72\x53\xe6\x81\x2f'*count)
        self.machine.mem_write(BASE+count*8, b'rightend')
        self.physical_events, self.array_callbacks = [], []
        self.platform, self.platform_names = Counter(), {}
        self.deny_platform = None
        self.phase = 'large-grid-control'
        self.instructions, self.instruction_limit = 0, 3_000_000
        self.recent = deque(maxlen=32)
        self.pending, self.last_transfer, self.boundary = None, None, None
        self.edges, self.branch_targets, self.entries = Counter(), Counter(), set()
        self.calls, self.order = 0, hashlib.sha256()
        self.first, self.last, self.corrupt = None, None, None
        for register, value in zip(PRESERVED, (0x13579bdf, 0x2468ace0, 0x31415926, 0x27182818)):
            self.machine.reg_write(register, value)
        self.preserved = tuple(self.machine.reg_read(r) for r in PRESERVED)
        self.machine.hook_add(UC_HOOK_CODE, self.observe, begin=CTOR, end=CTOR)
        self.machine.hook_add(UC_HOOK_CODE, self.observe, begin=DTOR, end=DTOR)
        self.machine.hook_add(UC_HOOK_CODE, self.callback_return, begin=ARRAY_RETURN, end=ARRAY_RETURN)

    def observe(self, machine, address, size, user):
        receiver = machine.reg_read(UC_X86_REG_ECX)
        self.calls += 1
        self.order.update(struct.pack('<I', receiver))
        if self.first is None:
            self.first = receiver
        self.last = receiver

    def callback_return(self, machine, address, size, user):
        if self.corrupt == 'fs':
            self.put(0, 0x12345678)
        elif self.corrupt is not None:
            machine.reg_write(self.corrupt, machine.reg_read(self.corrupt) ^ 4)
        MenuTrace.hook(self, machine, address, size, user)

    def prepare(self, construct=True, count=73728, base=BASE, stride=8,
                callback=None, destructor=DTOR):
        address = CONSTRUCT if construct else DESTRUCT
        callback = callback if callback is not None else (CTOR if construct else DTOR)
        arguments = (base, stride, count, callback) + ((destructor,) if construct else ())
        for index, value in enumerate((STOP, *arguments)):
            self.put(STACK+index*4, value)
        self.machine.reg_write(UC_X86_REG_ESP, STACK)
        self.machine.reg_write(UC_X86_REG_EIP, address)
        return address, len(arguments)

    def run(self, address, fixture):
        if fixture:
            self.fixture(address)
        self.machine.emu_start(self.machine.reg_read(UC_X86_REG_EIP), STOP, count=10_000_000)
        if self.machine.reg_read(UC_X86_REG_EIP) != STOP:
            raise AssertionError('Bounded grid control did not return')


class LargeGridFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program = claw()

    def test_original_constructor_and_destructor_match_adapter(self):
        count = 73728  # Original Level 3 grid, above the inherited 65536 bound.
        for construct in (True, False):
            observed = []
            for fixture in (False, True):
                with self.subTest(construct=construct, fixture=fixture):
                    probe = GridProbe(self.program, count)
                    before = bytes(probe.machine.mem_read(BASE, count*8))
                    address, argc = probe.prepare(construct, count)
                    probe.run(address, fixture)
                    expected_order = hashlib.sha256()
                    indices = range(count) if construct else range(count-1, -1, -1)
                    for index in indices:
                        expected_order.update(struct.pack('<I', BASE+8*index))
                    self.assertEqual(probe.calls, count)
                    self.assertEqual(probe.order.digest(), expected_order.digest())
                    self.assertEqual((probe.first, probe.last),
                                     (BASE, BASE+8*(count-1)) if construct else (BASE+8*(count-1), BASE))
                    self.assertEqual(tuple(probe.machine.reg_read(r) for r in PRESERVED), probe.preserved)
                    self.assertEqual(probe.machine.reg_read(UC_X86_REG_ESP), STACK+4*(argc+1))
                    self.assertEqual(probe.word(0), 0xffffffff)
                    for register, value in ((UC_X86_REG_FPCW, 0x027f), (UC_X86_REG_FPSW, 0),
                                            (UC_X86_REG_FPTAG, 0xffff)):
                        self.assertEqual(probe.machine.reg_read(register), value)
                    after = bytes(probe.machine.mem_read(BASE, count*8))
                    self.assertEqual(after, bytes(count*8) if construct else before)
                    self.assertEqual(bytes(probe.machine.mem_read(BASE-8, 8)), b'leftedge')
                    self.assertEqual(bytes(probe.machine.mem_read(BASE+count*8, 8)), b'rightend')
                    if fixture:
                        self.assertEqual(len(probe.physical_events), 1)
                        self.assertEqual(probe.physical_events[0]['completed'], count)
                        self.assertEqual(probe.physical_events[0]['phase'], 'large-grid-control')
                        self.assertFalse(probe.array_callbacks)
                    observed.append((after, probe.order.digest(), probe.calls))
            self.assertEqual(observed[0], observed[1])

    def test_upper_bound_is_accepted_without_running_million_callbacks(self):
        for count in (65537, 0x100000):
            for construct in (True, False):
                with self.subTest(construct=construct, count=count):
                    probe = GridProbe(self.program, count)
                    address, _ = probe.prepare(construct, count)
                    probe.fixture(address)
                    self.assertEqual(probe.calls, 0)
                    self.assertEqual(probe.physical_events[0]['count'], count)
                    frame = probe.array_callbacks[0]
                    self.assertEqual(frame['count'], count)
                    self.assertEqual(frame['stride'], 8 if construct else -8)
                    self.assertEqual(probe.machine.reg_read(UC_X86_REG_ECX),
                                     BASE if construct else BASE+8*(count-1))
                    self.assertEqual(probe.machine.reg_read(UC_X86_REG_EIP), CTOR if construct else DTOR)

    def test_interior_allocation_window_is_accepted(self):
        for construct in (True, False):
            with self.subTest(construct=construct):
                probe = GridProbe(self.program)
                probe.allocations = {BASE-8: 73728*8+16}
                address, _ = probe.prepare(construct)
                probe.fixture(address)
                self.assertEqual(len(probe.array_callbacks), 1)
                self.assertEqual(probe.physical_events[0]['base'], hex(BASE))
                self.assertEqual(probe.physical_events[0]['count'], 73728)

    def test_invalid_profiles_fail_before_callback_or_publication(self):
        cases = [dict(stride=0), dict(stride=4), dict(stride=16),
                 dict(callback=DTOR), dict(callback=CTOR+2), dict(destructor=CTOR),
                 dict(count=0x100001), dict(count=0xffffffff), dict(stride=0xffffffff),
                 dict(base=BASE-8), dict(base=BASE+8), dict(base=0xfffffff8), dict(base=0),
                 dict(construct=False, callback=CTOR), dict(construct=False, stride=4),
                 dict(construct=False, count=0x100001), dict(construct=False, base=BASE+8)]
        for changes in cases:
            with self.subTest(changes=changes):
                probe = GridProbe(self.program)
                address, _ = probe.prepare(**changes)
                before = bytes(probe.machine.mem_read(BASE-8, 73728*8+16))
                cpu = probe.cpu_state()
                with self.assertRaises(Blocked):
                    probe.fixture(address)
                self.assertEqual(probe.cpu_state(), cpu)
                self.assertEqual(probe.calls, 0)
                self.assertFalse(probe.platform)
                self.assertFalse(probe.physical_events)
                self.assertFalse(probe.array_callbacks)
                self.assertEqual(bytes(probe.machine.mem_read(BASE-8, 73728*8+16)), before)

    def test_mapped_but_unallocated_and_cross_allocation_ranges_fail(self):
        for allocations in ({}, {BASE: 73728*8-1},
                            {BASE: 73728*4, BASE+73728*4: 73728*4},
                            {0xfffffff8: 73728*8}):
            with self.subTest(allocations=allocations):
                probe = GridProbe(self.program)
                probe.allocations = allocations
                address, _ = probe.prepare(base=0xfffffff8 if 0xfffffff8 in allocations else BASE)
                with self.assertRaises(Blocked):
                    probe.fixture(address)
                self.assertFalse(probe.physical_events)
                self.assertFalse(probe.array_callbacks)

    def test_callback_return_rejects_preserved_state_corruption(self):
        for corrupt in (*PRESERVED, UC_X86_REG_ESP, UC_X86_REG_FPCW, 'fs'):
            with self.subTest(corrupt=corrupt):
                probe = GridProbe(self.program, 65537)
                probe.corrupt = corrupt
                address, _ = probe.prepare(count=65537)
                with self.assertRaisesRegex(Blocked, 'preserved CPU/stack/exception state'):
                    probe.run(address, True)
                self.assertEqual(probe.calls, 1)
                self.assertEqual(probe.physical_events[0]['completed'], 0)

    def test_small_counts_and_other_services_delegate(self):
        class Parent:
            def fixture(self, address):
                return ('delegated', address)

        class Dispatch(LargeGridFixture, Parent):
            machine = type('Stack', (), {'reg_read': lambda self, reg: STACK})()

            def word(self, address):
                return self.count

        dispatch = Dispatch()
        for count in (0, 1, 4096, 65536):
            dispatch.count = count
            for address in (CONSTRUCT, DESTRUCT, 0x4a3810):
                self.assertEqual(dispatch.fixture(address), ('delegated', address))


if __name__ == '__main__':
    unittest.main()
