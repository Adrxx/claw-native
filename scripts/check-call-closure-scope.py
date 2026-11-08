#!/usr/bin/env python3
"""Focused controls for the single-player missing-game acceptance scope."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('closure', Path(__file__).with_name('check-call-closure.py'))
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


class ScopeControls(unittest.TestCase):
    def edge(self, **changes):
        return dict(dict(caller=0x477790, site=0x4777b5, target=0x4e0cc0,
            outcome='owner-unresolved', original_site={'site':0x4777b5},
            shape_evidence={'path':'emitted-source'}), **changes)

    def exclude(self, rows, root=closure.ROOT):
        return closure.call_closure_native.multiplayer_exclusions(
            root, rows, closure.body, closure.digest)

    def test_warnings_preserve_all_unproved_classes(self):
        outcomes=['provider-unresolved','caller-owner-unresolved',
            'receiver-provenance-unresolved','profile-adapter-unresolved',
            'indirect-call-shape-unresolved','call-shape-unresolved']
        result=closure.closure_acceptance([dict(outcome=o) for o in outcomes],[{}])
        self.assertTrue(result['complete'])
        self.assertEqual(sum(result['warnings'].values()),7)

    def test_missing_game_and_real_refusals_fail(self):
        for outcome in ('owner-unresolved','transport-refused'):
            self.assertFalse(closure.closure_acceptance([dict(outcome=outcome)],[])['complete'])

    def test_exact_site_exclusion_retains_witnesses(self):
        edge=self.edge()
        witnesses=copy.deepcopy([edge['original_site'],edge['shape_evidence']])
        self.exclude([edge])
        self.assertEqual(edge['outcome'],'unreachable-single-player')
        self.assertEqual([edge['original_site'],edge['shape_evidence']],witnesses)
        self.assertIn('Sources/ClawNativeMenuInterface.swift',edge['single_player_exclusion']['source_inputs'])

    def test_other_callers_sites_targets_stay_open(self):
        rows=[self.edge(**changes) for changes in
            ({'caller':0x477791},{'site':0x4777b6},{'target':0x4e0cc1})]
        self.exclude(rows)
        self.assertTrue(all(r['outcome']=='owner-unresolved' for r in rows))

    def test_missing_witness_refuses_exclusion(self):
        with self.assertRaises(ValueError):self.exclude([self.edge(shape_evidence={})])

    def test_menu_policy_drift_refuses_exclusion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'Sources').mkdir()
            path='Sources/ClawNativeMenuInterface.swift'
            source=(closure.ROOT/path).read_text()
            (root/path).write_text(source.replace(
                '[11004,11005,12001,12002,12003,12201]','[11004]'))
            with self.assertRaises(ValueError):self.exclude([self.edge()],root)


if __name__=='__main__':unittest.main()
