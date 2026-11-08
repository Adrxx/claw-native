"""Negative controls for planner provenance and exact static comparison."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Tests.NativeLevels import regression


class PlannerRegressionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.inputs = {}
        for name in regression.SHARED_INPUTS | regression.GENERIC_INPUTS:
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
            self.inputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.patch = patch.object(regression, 'ROOT', root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.before = dict(
            method='legacy description',
            inputs_sha256={p: self.inputs[p] for p in regression.SHARED_INPUTS},
            roots=2, edges={'0x1': ['0x2']}, tables=[{'entries': ['0x2']}],
            placed_classes=[{'name': 'CaptainClaw'}], created_classes=['Treasure'],
            functions=[{'address': '0x1', 'owner': 'family', 'status': 'admitted'}],
            totals={'reachable': 1}, future_computed_field={'value': 3})
        self.after = copy.deepcopy(self.before)
        self.after.update(method='generic description', inputs_sha256=dict(self.inputs))

    def test_valid_distinct_provenance_preserves_reports(self):
        before, after = copy.deepcopy((self.before, self.after))
        self.assertEqual(regression.compare_closures(self.before, self.after), len(before)-2)
        self.assertEqual((self.before, self.after), (before, after))

    def test_stale_hash_rejected_for_each_planner_input(self):
        for label in ('before', 'after'):
            for path in getattr(self, label)['inputs_sha256']:
                with self.subTest(planner=label, path=path):
                    before, after = copy.deepcopy((self.before, self.after))
                    report = before if label == 'before' else after
                    report['inputs_sha256'][path] = '0'*64
                    with self.assertRaises(AssertionError):
                        regression.compare_closures(before, after)

    def test_missing_or_extra_provenance_rejected(self):
        for label in ('before', 'after'):
            for path in [*getattr(self, label)['inputs_sha256'], 'unexpected.py']:
                with self.subTest(planner=label, path=path):
                    before, after = copy.deepcopy((self.before, self.after))
                    inputs = (before if label == 'before' else after)['inputs_sha256']
                    if path in inputs:
                        del inputs[path]
                    else:
                        inputs[path] = '0'*64
                    with self.assertRaises(AssertionError):
                        regression.compare_closures(before, after)

    def test_current_file_change_rejected_even_when_planners_agree(self):
        for path in self.inputs:
            with self.subTest(path=path):
                file = regression.ROOT/path
                file.write_text('changed')
                with self.assertRaises(AssertionError):
                    regression.compare_closures(self.before, self.after)
                file.write_text(path)

    def test_every_computed_field_remains_exact(self):
        for key in self.before.keys() - {'method', 'inputs_sha256'}:
            for fault in ('changed', 'missing', 'extra'):
                with self.subTest(field=key, fault=fault):
                    after = copy.deepcopy(self.after)
                    if fault == 'changed':
                        after[key] = None
                    elif fault == 'missing':
                        del after[key]
                    else:
                        after[key+'_extra'] = after[key]
                    with self.assertRaises(AssertionError):
                        regression.compare_closures(self.before, after)


if __name__ == '__main__':
    unittest.main()
