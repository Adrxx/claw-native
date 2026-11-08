"""Acceptance controls without app, compiler or original execution."""
import copy
import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('boss_check', Path(__file__).with_name('check-level-two-boss.py'))
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def original():
    frames = []
    for i in range(5):
        boss = dict(live=False, active=False)
        if i >= 2:
            boss.update(live=True, active=True, health=(100, 90, 0)[i-2], vtable='0x50f1ac',
                        mode=6, logic_state=2028 if i == 2 else 2000,
                        facing=0xa5a5a5a5 if i == 2 else 3, animation_id=2028 if i == 2 else 2000)
        frames.append(dict(elapsed_ms=i*17, action='boss-intro', boss=boss,
                           player=dict(level=2, health=100 if i < 3 else 90),
                           presentation_start=i, presentation_count=1))
    keys = [dict(phase=f'boss-cheat-60-{i}-{c}', key=ord(c)) for i, c in enumerate('MPKFA')]
    keys.extend(dict(phase=f'level-two-complete-key-{i}-{c}', key=ord(c), milliseconds=200+i)
                for i, c in enumerate('MPSCULLY'))
    keys.append(dict(phase='level-two-results-return-0x50c0c4', key=13, scan=0x1c, milliseconds=300))
    return dict(status='pass', stop=None, fight_only=False, play_frames=[dict(player=dict(level=1))],
                boss_frames=frames, level_two_plan=[dict(start_ms=60, cheat='MPKFA')], key_deliveries=keys,
                boss_route_functions={'0x44e0c0': 1, '0x491fa0': 3, '0x47f160': 1},
                physical_events=[dict(service='PostMessageA', message=0x111, wparam=0x800e)]*2,
                level_complete_posted=True,
                state_transitions=[dict(vtable=v, level=n) for v, n in
                                   [('0x50c264', 1), ('0x50c0c4', None), ('0x50c264', 2),
                                    ('0x50c0c4', None), ('0x50c264', 3)]],
                level_three_frames=[dict(player=dict(level=3)) for _ in range(10)],
                presentations=[dict(pixels_sha256='a'*64, palette_sha256='b'*64)]*5)


class AcceptanceControls(unittest.TestCase):
    def test_complete_reference(self):
        self.assertTrue(CHECK.original_report(original())['accepted'])

    def test_compaction_rejects_incomplete_reference(self):
        mutations = {
            'stop': lambda t: t.update(stop='fault'),
            'death': lambda t: t['boss_route_functions'].pop('0x44e0c0'),
            'meter': lambda t: t['boss_route_functions'].pop('0x491fa0'),
            'completion-letter': lambda t: t['key_deliveries'].pop(5),
            'return': lambda t: t['key_deliveries'].pop(),
            'nine-third-level-frames': lambda t: t['level_three_frames'].pop(),
            'wrong-third-level': lambda t: t['level_three_frames'][0]['player'].update(level=2),
            'missing-second-results': lambda t: t['state_transitions'].pop(3),
            'no-mutual-damage-before-assistance': lambda t: t['level_two_plan'][0].update(start_ms=34),
            'missing-completion-post': lambda t: t['physical_events'].pop(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                trace = original()
                mutate(trace)
                path = Path(directory)/'trace.json'
                path.write_text('{}')
                with patch.object(CHECK, 'WORK', Path(directory)), patch.object(CHECK, 'read_trace', return_value=trace):
                    with self.assertRaises(ValueError):
                        CHECK.compact_original(path)

    def test_only_uninitialized_intro_facing_is_exempt(self):
        reference = original()['boss_frames']
        reference[2]['screens'] = ['correct']
        actual = copy.deepcopy(reference)
        actual[2]['boss']['facing'] = 0
        errors = []
        CHECK.compare_frames(reference, actual, ('health',), 'Boss', errors)
        self.assertEqual(errors, [])
        mutations = {
            'initialized-facing': lambda a: a[3]['boss'].update(facing=0),
            'other-poison-field': lambda a: a[2]['boss'].update(health=0xa5a5a5a5),
            'arbitrary-intro-facing': lambda a: a[2]['boss'].update(facing=1),
            'intro-mode': lambda a: a[2]['boss'].update(mode=4),
            'intro-state': lambda a: a[2]['boss'].update(logic_state=2000),
            'screen': lambda a: a[2].update(screens=['wrong']),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                altered = copy.deepcopy(actual)
                mutate(altered)
                errors = []
                CHECK.compare_frames(reference, altered, ('health',), 'Boss', errors)
                self.assertTrue(errors)

    def test_poison_later_in_reference_is_compared(self):
        reference = original()['boss_frames']
        reference[3]['boss']['facing'] = 0xa5a5a5a5
        actual = copy.deepcopy(reference)
        actual[3]['boss']['facing'] = 0
        errors = []
        CHECK.compare_frames(reference, actual, (), 'Boss', errors)
        self.assertTrue(errors)


    def test_native_acceptance_mutations(self):
        trace = original()
        for key in trace['key_deliveries']:
            key.setdefault('milliseconds', 100)
            key.setdefault('scan', 0)
            key.update(target='0x40b300' if key['key'] == 13 else '0x46bb30',
                       vtable='0x50c0c4' if key['key'] == 13 else '0x50c264')
        with tempfile.TemporaryDirectory(dir=CHECK.WORK) as directory:
            work = Path(directory)
            source = work/'trace.json'
            source.write_text('{}')
            with patch.object(CHECK, 'WORK', work), patch.object(CHECK, 'read_trace', return_value=trace):
                reference = CHECK.compact_original(source)
            native = dict(status='pass', level_one_frames=reference['one'],
                          level_two_frames=reference['two'], level_three_frames=reference['three'],
                          key_deliveries=reference['keys'], state_transitions=reference['states'],
                          posted_commands=reference['posted'], transports={'boss-base-direct': 1})
            mutations = {
                'valid': lambda a: None,
                'no-route-local-transport': lambda a: a.pop('transports'),
                'zero-transport': lambda a: a['transports'].update({'boss-base-direct': 0}),
                'key-phase': lambda a: a['key_deliveries'][0].update(phase='wrong'),
                'key-vtable': lambda a: a['key_deliveries'][0].update(vtable='0x0'),
                'nine-level-three-frames': lambda a: a['level_three_frames'].pop(),
                'missing-results': lambda a: a['state_transitions'].pop(3),
                'missing-return': lambda a: a['key_deliveries'].pop(),
                'missing-completion': lambda a: a['posted_commands'].pop(),
            }
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    app = copy.deepcopy(native)
                    mutate(app)
                    (work/'level-two-route.json').write_text(json.dumps(app))
                    # A separate census must not rescue absent route-local proof.
                    (work/'live-state.json').write_text(json.dumps(dict(transports={'boss-base-direct': 99})))
                    with patch.object(CHECK, 'WORK', work), patch.object(CHECK, 'OUT', work), \
                            patch.object(CHECK, 'compact_original', return_value=reference), \
                            patch.object(sys, 'argv', ['checker', '--reuse']), contextlib.redirect_stdout(io.StringIO()):
                        result = CHECK.main()
                    self.assertEqual(result, 0 if name == 'valid' else 1)


if __name__ == '__main__':
    unittest.main()
