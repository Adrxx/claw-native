"""Focused closure controls; fixtures are freshly planned original-world closures."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels.discovery import CREATED, TABLES, class_bindings, validate_later_closure


class LaterDiscoveryControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closures = {level: json.loads((output_dir(level)/'closure.json').read_text())
                        for level in (11, 12, 13, 14)}

    def reject(self, level, mutate, message):
        closure = copy.deepcopy(self.closures[level])
        mutate(closure)
        with self.assertRaisesRegex(AssertionError, message):
            validate_later_closure(closure)

    def test_original_closures(self):
        for closure in self.closures.values():
            validate_later_closure(closure)

    def test_each_placed_root(self):
        for level, original in self.closures.items():
            for row in original['placed_classes']:
                if row['callback'] is None:
                    continue
                with self.subTest(level=level, name=row['name']):
                    def remove(closure):
                        for function in closure['functions']:
                            if function['address'] == row['callback']:
                                function['root'] = None
                    self.reject(level, remove, 'Missing placed')

    def test_each_created_class(self):
        for level in self.closures:
            for name in CREATED[level]:
                with self.subTest(level=level, name=name):
                    self.reject(level, lambda c: c['created_classes'].remove(name),
                                'Missing created-object')

    def test_mechanism_state_roots(self):
        names = {11: {'Siren', 'Mercat', 'Fish', 'Laser'},
                 12: {'Aquatis', 'AquatisCrack', 'AquatisDynamite',
                      'AquatisStalactite', 'Tentacle', 'Stalactite'},
                 13: {'RedTail', 'RedTailWind', 'RedTailSpikes', 'Chameleon'},
                 14: {'Omar', 'TigerGuard', 'LavaGeyser', 'LavaHand', 'LavaMouth', 'JumpSwitch'}}
        for level, original in self.closures.items():
            for row in original['placed_classes']:
                if row['name'] not in names[level]:
                    continue
                for address in set(row['states']):
                    with self.subTest(level=level, name=row['name'], address=address):
                        def remove(closure):
                            for function in closure['functions']:
                                if function['address'] == address:
                                    function['root'] = None
                        self.reject(level, remove, 'Missing placed')

    def test_each_original_vtable(self):
        for level in self.closures:
            for address in TABLES[level]:
                with self.subTest(level=level, address=hex(address)):
                    self.reject(level, lambda c: c.update(tables=[
                        t for t in c['tables'] if t['address'] != hex(address)]),
                        'Missing created/mechanism vtable')
                    def corrupt(closure):
                        table = next(t for t in closure['tables'] if t['address'] == hex(address))
                        table['entries'][0] = '0x401000'
                    self.reject(level, corrupt, 'Changed original vtable')

    def test_fabricated_class_mapping(self):
        names, _ = class_bindings()
        real_callbacks = [hex(names['DoNothing']), hex(names['CaptainClaw'])]
        for level, original in self.closures.items():
            for row in original['placed_classes']:
                with self.subTest(level=level, name=row['name']):
                    def corrupt(closure):
                        fake = next(a for a in real_callbacks if a != row['callback'])
                        next(c for c in closure['placed_classes'] if c['name'] == row['name'])['callback'] = fake
                    self.reject(level, corrupt, 'Fabricated|unregistered')

    def test_retained_plan_required_and_exact(self):
        plan = [{'start_ms': 0, 'end_ms': 60000, 'action': 'stand', 'keys': []}]
        for level, closure in self.closures.items():
            with self.subTest(level=level):
                validate_later_closure(closure, trace={'plan': plan}, retained_plan=plan)
                for absent_or_changed in (None, [], [dict(plan[0], end_ms=17)]):
                    with self.assertRaisesRegex(AssertionError, 'actual input schedule'):
                        validate_later_closure(closure, trace={'plan': plan}, retained_plan=absent_or_changed)

    def test_sign_cannot_be_omitted(self):
        self.reject(12, lambda c: c.update(placed_classes=[
            p for p in c['placed_classes'] if p['name'] != 'Sign']), 'Placed census differs')
        def omit_loader(closure):
            next(r for r in closure['functions'] if r['address'] == '0x4d17e0')['root'] = None
        self.reject(12, omit_loader, 'Missing original Sign loader root')

    def test_original_sign_evidence_controls(self):
        from Tests.NativeLevels.object_loading import EVIDENCE, validate_loading_report
        original = json.loads((ROOT/EVIDENCE).read_text())
        validate_loading_report(original)
        def sign(report):
            return next(e for e in report['object_lookups'] if e['name'] == 'Sign')
        def omit_sign(report):
            report['object_lookups'].remove(sign(report))
        def lose_positive(report):
            report['object_lookups'] = [e for e in report['object_lookups'] if e['name'] != 'Aquatis']
        mutations = {
            'incomplete loading': lambda r: r.update(loaded=False),
            'wrong executable': lambda r: r.update(executable_sha256='0'*64),
            'missing provenance': lambda r: r['inputs_sha256'].pop('Tests/NativeLevels/object_load_trace.py'),
            'missing Sign': omit_sign,
            'fabricated registration': lambda r: sign(r).update({'return': 1}),
            'wrong record': lambda r: sign(r)['registers'].update(edi=0),
            'missing skip branch': lambda r: r['sign_steps'][1].update(address=0),
            'missing destruction return': lambda r: next(s for s in r['sign_steps'] if s['address'] == 0x4d1ab6).update(address=0),
            'wrong consumed byte count': lambda r: next(s for s in r['sign_steps'] if s['address'] == 0x4d1fbf)['registers'].update(eax=0),
            'missing positive control': lose_positive,
        }
        for label, mutate in mutations.items():
            with self.subTest(control=label):
                report = copy.deepcopy(original)
                mutate(report)
                with self.assertRaises(AssertionError):
                    validate_loading_report(report)

    def test_later_batch_preview(self):
        for level, closure in self.closures.items():
            with self.subTest(level=level), tempfile.TemporaryDirectory(dir=ROOT/'work') as folder:
                out = Path(folder)
                (out/'closure.json').write_text(json.dumps(closure))
                result = subprocess.run([sys.executable, '-m', 'Tests.NativeLevels.batches',
                    '--level', str(level), '--output-dir', str(out)], cwd=ROOT,
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                batches = json.loads((out/'batches.json').read_text())
                join = batches['tasks'][-1]
                mapping = 'eleven-twelve' if level in (11,12) else 'thirteen-fourteen'
                self.assertIn(f'parity-levels-{mapping}-map-batch', join['depends_on'])
                self.assertIn(str((out/'plan.json').relative_to(ROOT)), join['start_with'])
                if level in (11,12):
                    self.assertIn('TridentBullet', join['scope'])
                    self.assertIn('Sign load outcome', join['scope'])
                else:
                    self.assertFalse(join['exclusive'])
                    self.assertTrue(join['parallel'])
                    self.assertIn('0x494460', join['scope'])
                addresses = [a for t in batches['tasks'][:-1] for a in t['addresses']]
                self.assertEqual(len(addresses), len(set(addresses)))
                self.assertTrue(all(5 <= len(t['addresses']) <= 15 for t in batches['tasks'][:-1]))


if __name__ == '__main__':
    unittest.main()
