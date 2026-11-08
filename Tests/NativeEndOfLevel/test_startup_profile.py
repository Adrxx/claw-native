"""Checkpoint profile guards must reject mismatches before guest memory restore."""
import unittest
from unittest.mock import patch

from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, Blocked
from Tests.NativeLevelTwo.trace import LevelTwoTrace
from Tests.NativeLevels.trace import LevelTrace


class StartupProfileTests(unittest.TestCase):
    def tracer(self, kind, paper):
        trace = kind.__new__(kind)
        trace.startup_paper = paper
        trace.startup_profile = dict(paper=paper, query_ms=int(paper))
        return trace

    def test_all_loaders_reject_opposite_profile_before_restore(self):
        for kind, method, module in (
                (EndOfLevelTrace, 'resume_level_checkpoint', 'Tests.NativeEndOfLevel.trace'),
                (LevelTwoTrace, 'resume_two_checkpoint', 'Tests.NativeLevelTwo.trace'),
                (LevelTrace, 'resume_target', 'Tests.NativeLevels.trace')):
            for paper in (False, True):
                with self.subTest(kind=kind, paper=paper):
                    trace = self.tracer(kind, paper)
                    with patch(module+'.load_checkpoint', return_value={'state': {'startup_paper': not paper}}), \
                            patch(module+'.restore_memory') as restore:
                        with self.assertRaisesRegex(Blocked, 'profile mismatch'):
                            getattr(trace, method)('unused')
                        restore.assert_not_called()

    def test_paper_requires_actual_startup_objects_and_queries(self):
        trace = self.tracer(EndOfLevelTrace, True)
        state = dict(startup_paper=True, startup_profile=trace.startup_profile,
            startup_queries=dict(count=2, increments={1: 2}),
            startup_objects={'0x44': '0x60000000', '0x58': '0x60000040'},
            startup_evidence=[dict(binding='application+0x44'), dict(binding='application+0x58')])
        trace.validate_checkpoint_profile(state)
        for key in ('startup_profile', 'startup_queries', 'startup_objects', 'startup_evidence'):
            with self.subTest(missing=key), self.assertRaisesRegex(Blocked, 'lacks original'):
                trace.validate_checkpoint_profile({k: v for k, v in state.items() if k != key})
        state['startup_queries']['increments'] = {0: 2}
        with self.assertRaisesRegex(Blocked, 'lacks original'):
            trace.validate_checkpoint_profile(state)

    def test_legacy_default_remains_compatible(self):
        self.tracer(EndOfLevelTrace, False).validate_checkpoint_profile({})


if __name__ == '__main__':
    unittest.main()
