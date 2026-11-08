"""Host-scope regression for the TLS getter's locally owned setter.

Reuses frozen independent original cases; adds transport checks invisible to
CPU/stack parity, including restoration after genuine missing-throw halts.
"""
import ctypes as C
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clawparity import runner
from clawparity.env import Env, ContextFault

SPEC = Path(__file__).resolve().parent / 'families/mfc_tls_values.json'
SETTER_RETURNS = {0x503173, 0x50319c, 0x5031be, 0x5031c7, 0x5031d1,
                  0x5031e7, 0x5031f9, 0x503205, 0x503225, 0x503237}


class OwnedScopeTests(unittest.TestCase):
    def test_local_setter_scope_and_restore_on_return_and_halt(self):
        observed = dict(nested=0, restored_return=0, restored_halt=0)

        class ObservedEnv(Env):
            def run_native(self, entry, function, receiver, arguments, **options):
                self.root_function = function
                self.root_frame = options.get('source_context').esp if options.get('source_context') else None
                def checked_entry(*args):
                    host = self._host
                    before = (C.cast(host.sourceContext, C.c_void_p).value,
                              host.entryStackPointer, host.sourceReturnPC)
                    completed = entry(*args)
                    after = (C.cast(host.sourceContext, C.c_void_p).value,
                             host.entryStackPointer, host.sourceReturnPC)
                    if before != after:
                        raise AssertionError('owned entry failed to restore borrowed host scope')
                    if self.root_function == 0x50335e and self.root_frame is not None:
                        observed['restored_return' if completed else 'restored_halt'] += 1
                    return completed
                return super().run_native(checked_entry, function, receiver, arguments, **options)

            def _native_source_call(self, raw):
                if self.root_function == 0x50335e and raw.sourceReturnPC in SETTER_RETURNS:
                    host = self._host
                    if (host.entryStackPointer != self.root_frame - 20 or
                            host.sourceReturnPC != 0x5033ce or not host.sourceContext):
                        raise ContextFault('owned setter lacks its actual frame/return scope')
                    active = host.sourceContext.contents
                    outgoing = raw.sourceContext.contents
                    if active.preserveMask != 0x442 or outgoing.esp != active.esp - 4:
                        raise ContextFault('owned setter callback uses suspended parent CPU')
                    if C.cast(host.sourceContext, C.c_void_p).value == C.cast(raw.sourceContext, C.c_void_p).value:
                        raise ContextFault('outgoing context aliases active owned CPU')
                    observed['nested'] += 1
                return super()._native_source_call(raw)

        with patch.object(runner, 'Env', ObservedEnv):
            result = runner.run(SPEC)
        self.assertEqual(result['status'], 'pass', result)
        self.assertGreater(observed['nested'], 0)
        self.assertGreater(observed['restored_return'], 0)
        self.assertGreater(observed['restored_halt'], 0)


if __name__ == '__main__':
    unittest.main()
