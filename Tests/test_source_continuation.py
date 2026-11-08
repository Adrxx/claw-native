"""Original source continuations reused by nested calls must remain executable."""
import struct
import unittest
from unicorn.x86_const import UC_X86_REG_ESP
from Tests.clawparity.env import NativeSourceContext, Halt, Env
from Tests.clawparity.kernel import Machine, STACK_BASE, STACK_SIZE, STACK_TOP, ContextFault, OwnedEntryStop
from Tests.clawparity.program import Program, Section


def machine(ret=b'\xc3', fatal=False):
    code = bytearray(b'\xcc' * 0x100)
    code[:5] = b'\xe8' + struct.pack('<i', 0x401020 - 0x401005)
    code[5:10] = b'\xb8' + struct.pack('<I', 0xabcdef01)
    code[10:10 + len(ret)] = ret
    code[0x20:0x26] = b'\xb8' + struct.pack('<I', 0x12345678) + b'\xc3'
    if fatal:
        code[10:15] = b'\xe9' + struct.pack('<i', 0x401040 - 0x40100f)
    program = Program('reused-source-continuation', '', 0x400000, 0x3000,
                      [Section('.text', 0x401000, len(code), bytes(code)),
                       Section('.data', 0x402000, 0x1000, bytes(0x1000))],
                      (0x401000, 0x401100), {})
    return Machine(program, 0x1000000, 0x1000)


def source(frame):
    return NativeSourceContext(72, 1, 0x7ff, 0x7ff,
                              1, 2, 3, 4, 5, 6, 7, frame, 0x401000,
                              0x8d7, 0xffffffff, 0x472, 0, 0)


class SourceContinuationTests(unittest.TestCase):
    def test_nested_source_frame_is_validated_without_repair(self):
        for bad_index in (0, 1, 2):
            m = machine()
            c = source(STACK_TOP)
            words = [0x401005, 0x55667788, 0x11223344]
            words[bad_index] ^= 1
            physical = struct.pack('<3I', *words)
            m.write(c.esp, physical)
            entered = []
            m.observe(0x401000, lambda m, pc: entered.append(pc))
            before = bytes(c)
            with self.assertRaisesRegex(ContextFault, 'physical frame'):
                m.call_source(0x401000, c, 0x401005, arguments=(0x55667788, 0x11223344), prepare_frame=False)
            self.assertEqual(m.read(STACK_TOP, len(physical)), physical)
            self.assertEqual(bytes(c), before)
            self.assertEqual(entered, [])

    def test_valid_nested_source_frame_executes(self):
        m = machine()
        c = source(STACK_TOP)
        m.write(c.esp, struct.pack('<3I', 0x401005, 0x55667788, 0x11223344))
        result = m.call_source(0x401000, c, 0x401005, arguments=(0x55667788, 0x11223344), prepare_frame=False)
        self.assertTrue(result.completed)
        self.assertEqual(c.eax, 0xabcdef01)
        self.assertEqual(m.words(STACK_TOP + 4, 2), (0x55667788, 0x11223344))

    def test_nested_continuation_does_not_complete_outer_call(self):
        for convention in ('cdecl', 'stdcall', 'thiscall', 'fastcall'):
            for frame in (STACK_BASE + 0x100, STACK_TOP, STACK_BASE + STACK_SIZE - 12):
                with self.subTest(convention=convention, frame=frame):
                    m = machine(b'\xc3' if convention == 'cdecl' else b'\xc2\x08\x00')
                    c = source(frame)
                    visits = []
                    m.observe(0x401005, lambda m, pc: visits.append(m.register(UC_X86_REG_ESP)))
                    r = m.call_source(0x401000, c, 0x401005, convention,
                                      ecx=c.ecx if convention in ('thiscall', 'fastcall') else 0,
                                      edx=c.edx if convention == 'fastcall' else 0,
                                      arguments=(0x55667788, 0x11223344))
                    self.assertTrue(r.completed)
                    self.assertEqual(c.eax, 0xabcdef01)
                    self.assertEqual(c.eip, 0x401005)
                    self.assertEqual(c.esp, frame + (4 if convention == 'cdecl' else 12))
                    self.assertEqual(visits, [frame, c.esp])
                    self.assertEqual((c.ebx, c.esi, c.edi, c.ebp, c.fsHead), (2, 5, 6, 7, 0xffffffff))

    def test_env_coverage_includes_executed_nested_continuation(self):
        env = Env(machine().program)
        env._begin_case(None)
        env._freeze()
        c = source(STACK_TOP)
        side = env.run_original_context(0x401000, c, trace=True, source_return_pc=0x401005)
        self.assertTrue(side.completed, side.errors)
        self.assertEqual(c.eax, 0xabcdef01)
        self.assertIn((0x401005, 5), env.coverage)

    def test_wrong_return_pop_still_rejected(self):
        for convention, ret in [('cdecl', b'\xc2\x08\x00'), ('stdcall', b'\xc3')]:
            m = machine(ret)
            c = source(STACK_TOP)
            with self.assertRaises(ContextFault):
                m.call_source(0x401000, c, 0x401005, convention, arguments=(1, 2))

    def test_return_boundary_does_not_execute_owned_or_external_continuation(self):
        for external in (False, True):
            m = machine()
            c = source(STACK_TOP)
            c.eip = 0x401020
            if external:
                m.intercept(0x401005)
                m.on_external = lambda m, pc: self.fail('return executed external continuation')
            with m.stop_owned_entries([(0x401005, 0x40100a)], lambda pc: self.fail('return executed owned continuation')):
                r = m.call_source(0x401020, c, 0x401005)
            self.assertTrue(r.completed)
            self.assertEqual(c.eax, 0x12345678)
            self.assertEqual(m._source_returns, [])

    def test_nested_visit_still_obeys_owned_instruction_guard(self):
        m = machine()
        captured = []
        def capture(pc):
            captured.append(pc)
            return pc
        with m.stop_owned_entries([(0x401005, 0x40100a)], capture):
            with self.assertRaises(OwnedEntryStop):
                m.call_source(0x401000, source(STACK_TOP), 0x401005)
        self.assertEqual(captured, [0x401005])
        self.assertEqual(m._source_returns, [])

    def test_fatal_after_nested_continuation_reaches_physical_stop(self):
        m = machine(fatal=True)
        c = source(STACK_TOP)
        observed = []
        def terminate(m, pc):
            observed.append((pc, m.words(STACK_TOP, 1)[0]))
            raise Halt('nonreturning physical termination')
        m.intercept(0x401040)
        m.on_external = terminate
        with self.assertRaises(Halt):
            m.call_source(0x401000, c, 0x401005)
        self.assertEqual(observed, [(0x401040, 0x401005)])


if __name__ == '__main__':
    unittest.main()
