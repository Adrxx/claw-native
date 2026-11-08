"""Synthetic graph tests; no original program, assets, or derived fixtures."""
import unittest
from tools.claw.graph_plan import build_plan, ownership


def family(fid, owned, callees=None, canonical=True):
    return {'id': fid, 'abi': 'canonical' if canonical else 'legacy', 'owned': owned, 'callees': callees or {}, 'evidence': {'level': 'admitted'}}


def entry(addr, **extra):
    return dict(address=addr, **extra)


class GraphPlanTests(unittest.TestCase):
    def test_canonical_preferred_and_ambiguous_rejected(self):
        legacy = family('old', [entry('0x10')], canonical=False)
        modern = family('new', [entry('0x10')])
        self.assertEqual(ownership([legacy, modern])['0x10'][0]['id'], 'new')
        with self.assertRaisesRegex(ValueError, 'multiple canonical'):
            ownership([modern, family('other', [entry('0x10')])])

    def test_cycles_terminate_and_direct_owned_edge_included(self):
        families = [family('a', [entry('0x10')]), family('b', [entry('0x20')])]
        plan = build_plan(families, ['0x10'], direct={'0x10': ['0x20'], '0x20': ['0x10']})
        self.assertEqual(set(plan['nodes']), {'0x10', '0x20'})
        self.assertTrue(plan['closure']['complete'])
        self.assertEqual(plan['cyclic_components'], [['0x10', '0x20']])
        self.assertFalse(plan['composition']['playable'])

    def test_source_and_callee_contract_gaps(self):
        spec = family('a', [entry('0x10', source_context={'input_mask': 0x7ff, 'output_mask': 1})], {'0x20': {'kind': 'whole'}})
        plan = build_plan([spec], ['0x10'], True)
        self.assertEqual({g['kind'] for g in plan['gaps']}, {'owned_full_context_capability', 'callee_full_context_declaration', 'missing_owner_boundary'})

    def test_compiler_contract_and_fixtures(self):
        spec = family('a', [entry('0x10', compiler_context={'input_mask': 2047, 'output_mask': 2047})], {'0x20': {'kind': 'fixture', 'fixture': 'scripted', 'name': 'Service'}})
        plan = build_plan([spec], ['0x10'], True)
        self.assertEqual(plan['gaps'], [])
        self.assertEqual(plan['nodes']['0x10']['context_kind'], 'compiler')
        self.assertEqual(plan['fixtures'][0]['physical_device_required'], 'unknown')
        self.assertNotIn('0x20', plan['nodes'])

    def test_family_dedup_callbacks_and_no_native_callee_block(self):
        spec = family('a', [entry('0x10'), entry('0x11')])
        spec['evidence']['level'] = 'drafted'
        plan = build_plan([spec], ['0x10', '0x11'], True, unresolved={'0x10': ['indirect callback']})
        self.assertEqual(len(plan['recovery_layers'][0]), 1)
        self.assertFalse(plan['recovery_layers'][0][0]['native_callee_admission_blocks_recovery'])
        self.assertEqual(plan['unresolved_callbacks'][0]['reason'], 'indirect callback')

    def test_ready_callee_still_needs_caller_declaration(self):
        context = {'input_mask': 2047, 'output_mask': 2047}
        caller = family('caller', [entry('0x10', source_context=context)])
        callee = family('callee', [entry('0x20', source_context=context)])
        direct = {'0x10': ['0x20', '0x20']}
        plan = build_plan([caller, callee], ['0x10'], True, direct)
        self.assertEqual(len(plan['edges']), 1)
        self.assertEqual(len(plan['gaps']), 1)
        self.assertEqual(plan['gaps'][0]['kind'], 'required_callee_context_declaration')
        self.assertEqual(plan['gaps'][0]['declaration_state'], 'missing')
        caller['callees'] = {'0x20': {'kind': 'whole', 'source_context': context}}
        plan = build_plan([caller, callee], ['0x10'], True, direct)
        self.assertEqual(plan['gaps'], [])
        caller['callees']['0x20']['source_context'] = {'input_mask': 2047, 'output_mask': 1}
        plan = build_plan([caller, callee], ['0x10'], True, direct)
        self.assertTrue(any(g['kind'] == 'required_callee_context_declaration' and g['declaration_state'] == 'incomplete' for g in plan['gaps']))

    def test_bound_explicit_frontier(self):
        plan = build_plan([], ['0x10'], direct={'0x10': ['0x20']}, max_nodes=1)
        self.assertFalse(plan['closure']['complete'])
        self.assertEqual(plan['closure']['remaining_frontier'], ['0x20'])

    def test_full_masks_do_not_hide_preservation_contract_mismatch(self):
        supplied = {'input_mask': 2047, 'output_mask': 2047, 'preserve_mask': 0}
        required = dict(supplied, preserve_mask=0x472, optional=True)
        caller = family('caller', [entry('0x10', source_context=supplied)],
                        {'0x20': {'kind': 'whole', 'source_context': supplied}})
        callee = family('callee', [entry('0x20', source_context=required)])
        gaps = build_plan([caller, callee], ['0x10'], True)['gaps']
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]['kind'], 'callee_context_contract_mismatch')
        self.assertEqual(gaps[0]['required']['preserve_mask'], 0x472)
        caller['callees']['0x20']['source_context'] = dict(required, optional=False)
        self.assertEqual(build_plan([caller, callee], ['0x10'], True)['gaps'], [])

    def test_context_kind_mismatch_requires_review(self):
        context = {'input_mask': 2047, 'output_mask': 2047}
        caller = family('caller', [entry('0x10', source_context=context)],
                        {'0x20': {'kind': 'whole', 'source_context': context}})
        callee = family('callee', [entry('0x20', compiler_context=context)])
        self.assertEqual(build_plan([caller, callee], ['0x10'], True)['gaps'][0]['kind'],
                         'callee_context_contract_mismatch')


if __name__ == '__main__':
    unittest.main()
