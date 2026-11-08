"""Failure controls for the coverage report contract; no game/harness execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('coverage_check', Path(__file__).with_name('check-level-object-coverage.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class CoverageCheckTests(unittest.TestCase):
    def setUp(self):
        self.report = {'schema': 1, 'complete': True, 'muted': True, 'levels': [
            {'level': n, 'placed': 1, 'instantiated': 1, 'visited': 1, 'duplicate_visits': 0,
             'skipped_count': 0, 'skipped': [], 'fault': 0, 'wwd_sha256': 'a' * 64} for n in range(1, 15)]}

    def gap(self, reason='unsupported-logic'):
        row = self.report['levels'][11]
        row.update(instantiated=0, skipped_count=1, skipped=[{
            'logic': 'MissingAquatisPiece', 'count': 1,
            'placements': [{'id': 7, 'x': 1200, 'y': 800, 'z': 100, 'plane': 1,
                            'record_offset': 4096, 'reason': reason, 'callback': '0x00000000'}]}])

    def test_complete_and_missing_level(self):
        self.assertEqual(check.assess(self.report, [], [])['status'], 'pass')
        self.report['levels'].pop()
        self.assertEqual(check.assess(self.report, [], [])['status'], 'error')

    def test_known_gap_still_fails(self):
        self.gap()
        tasks = [{'id': 'wire-object-test', 'state': 'open', 'connection': {'classes': [{'name': 'MissingAquatisPiece'}]}}]
        result = check.assess(self.report, [], tasks)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['untracked'], [])
        tasks[0]['state'] = 'done'
        self.assertEqual(check.assess(self.report, [], tasks)['untracked'], [(12, 'MissingAquatisPiece')])

    def test_no_actor_and_unvisited_are_not_success(self):
        self.gap('loader-returned-no-actor')
        self.assertEqual(check.assess(self.report, [], [])['status'], 'fail')
        self.gap('not-visited')
        self.assertEqual(check.assess(self.report, [], [])['status'], 'error')

    def test_only_explicit_scoped_allowance(self):
        self.gap()
        allow = [{'logic': 'MissingAquatisPiece', 'reason': 'test-only synthetic example',
                  'basis': 'out-of-scope', 'levels': [12]}]
        self.assertEqual(check.assess(self.report, allow, [])['status'], 'pass')
        allow[0]['levels'] = [1]
        self.assertEqual(check.assess(self.report, allow, [])['status'], 'fail')
        allow[0]['reason'] = ''
        self.assertEqual(check.assess(self.report, allow, [])['status'], 'error')

    def test_partial_or_faulted_load_is_error(self):
        for field, value in [('visited', 0), ('duplicate_visits', 1), ('fault', 1), ('skipped_count', 1)]:
            report = copy.deepcopy(self.report)
            report['levels'][0][field] = value
            self.assertEqual(check.assess(report, [], [])['status'], 'error', field)


if __name__ == '__main__':
    unittest.main()
