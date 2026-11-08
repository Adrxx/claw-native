"""Coverage must describe only the original side, regardless of cache history.

Run: PYTHONPATH=.:Tests work/test-env/bin/python -m unittest \
    Tests.clawparity.selftest.coverage_cache

The tiny x86 program is hand-written, independent of the reference binary.
Its native entry bridges to an original helper which reenters an owned leaf.
"""
import ctypes as C
import struct
import unittest
from types import SimpleNamespace

from ..env import Call, Env, U32
from ..kernel import Machine, STACK_TOP
from ..runner import coverage_report


ROOT, HELPER, OWNED, NATIVE_ONLY, FAULT = (0x401000 + n * 0x100 for n in range(5))


def program():
    def call_ret(address, target):
        return b'\xe8' + struct.pack('<i', target - address - 5) + b'\xc3'

    bodies = {
        ROOT: call_ret(ROOT, HELPER),
        HELPER: call_ret(HELPER, OWNED),
        OWNED: b'\xb8\x07\x00\x00\x00\xc3',  # return 7
        NATIVE_ONLY: b'\xb8\x63\x00\x00\x00\xc3',  # return 99
        FAULT: b'\x0f\x0b',  # UD2
    }
    return SimpleNamespace(
        base=0x400000, size=0x3000, data_start=0x402000,
        text=(0x401000, 0x402000), imports={}, startup_calls=(), control_word=None,
        sections=[SimpleNamespace(address=a, data=b) for a, b in bodies.items()],
        in_text=lambda a: 0x401000 <= a < 0x402000,
    )


def covered_bytes(blocks):
    return {byte for address, size in blocks for byte in range(address, address + size)}


def native_entry(env, helper=HELPER):
    def entry(function, receiver, arguments, count, host, result):
        value = env._bridge(Call(helper, 0, 0, (), 0))
        C.cast(result, C.POINTER(U32))[0] = value
        return 1
    return entry


class CoverageCacheTests(unittest.TestCase):
    def environment(self):
        env = Env(program(), heap_bytes=0x1000)
        env._freeze()
        return env

    def test_native_first_helper_reentry_matches_original_only(self):
        reports = []
        expected = {b for a in (ROOT, HELPER, OWNED) for b in range(a, a + 6)}
        spec = {'owned': [{'address': hex(a), 'interval_end': hex(a + 6)}
                          for a in (ROOT, OWNED)], 'oracle': {}}
        for native_first in (False, True):
            with self.subTest(native_first=native_first):
                env = self.environment()
                for function in (ROOT, OWNED):
                    if native_first:
                        entry = native_entry(env) if function == ROOT else native_entry(env, OWNED)
                        native = env.run_native(entry, function, 0, ())
                        self.assertTrue(native.completed)
                        self.assertFalse(native.errors)
                        self.assertEqual(native.bridged, [HELPER if function == ROOT else OWNED])
                    original = env.run_original(function, 0, (), trace=True)
                    self.assertTrue(original.completed)
                    self.assertFalse(original.errors)
                    self.assertEqual(original.eax, 7)
                    if native_first:
                        self.assertIsNone(env.compare(native, original, True, STACK_TOP + 4))
                self.assertEqual(covered_bytes(env.coverage), expected)
                reports.append(coverage_report(spec, env.coverage, {ROOT: 1, OWNED: 1}))
        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0], reports[1])
        self.assertEqual(reports[1][hex(OWNED)]['executed'], 6)

    def test_native_helper_between_original_runs_cannot_add_coverage(self):
        env = self.environment()
        self.assertTrue(env.run_original(ROOT, 0, (), trace=True).completed)
        before = set(env.coverage)
        native = env.run_native(native_entry(env, NATIVE_ONLY), ROOT, 0, ())
        self.assertTrue(native.completed)
        self.assertEqual(native.eax, 99)
        self.assertTrue(env.run_original(OWNED, 0, (), trace=True).completed)
        self.assertEqual(env.coverage, before)
        self.assertNotIn(NATIVE_ONLY, covered_bytes(env.coverage))

    def test_hook_transitions_retranslate_warmed_blocks(self):
        machine = Machine(program(), 0x1000000, 0x1000)
        for _ in range(3):
            machine.trace_blocks(False)
            self.assertTrue(machine.call(HELPER).completed)
            machine.trace_blocks(True)
            self.assertTrue(machine.call(ROOT).completed)
            expected = {b for a in (ROOT, HELPER, OWNED) for b in range(a, a + 6)}
            self.assertEqual(covered_bytes(machine.blocks), expected)
            machine.trace_blocks(True)  # An unchanged mode retains accumulated coverage.
            self.assertEqual(covered_bytes(machine.blocks), expected)
            machine.trace_blocks(False)
            machine.trace_blocks(False)
            self.assertTrue(machine.call(NATIVE_ONLY).completed)
            self.assertEqual(covered_bytes(machine.blocks), expected)

    def test_fault_and_untraced_runs_do_not_leave_coverage_enabled(self):
        env = self.environment()
        failed = env.run_original(FAULT, 0, (), trace=True)
        self.assertFalse(failed.completed)
        self.assertTrue(failed.errors)
        self.assertIsNone(env.machine._block_hook)
        before = set(env.coverage)
        self.assertTrue(env.run_original(ROOT, 0, (), trace=False).completed)
        self.assertEqual(env.coverage, before)
        self.assertIsNone(env.machine._block_hook)


if __name__ == '__main__':
    unittest.main()
