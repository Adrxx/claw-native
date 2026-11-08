"""Compare the Mac application's scripted input frames with the original.

Reference: work/test-env/bin/python -m Tests.NativeMenuBase.input_trace
App: scripts/run-mac.sh --menu-check "$PWD/work/menu-input" --menu-input-script "$PWD/work/menu-input/events.json"
Check: work/test-env/bin/python scripts/check-menu-input.py
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, default=ROOT / 'work/menu-input')
parser.add_argument('--live', action='store_true', help='Also verify saved real UI input checkpoints')
args = parser.parse_args()
original = json.loads((args.evidence / 'original.json').read_text())
actual = json.loads((args.evidence / 'app-menu.json').read_text())
assert original['status'] == actual['status'] == 'pass'
assert original['stop'] is None
assert original['executable_sha256'] == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
assert actual['initializer'] == '45ace0' and actual['frameEntry'] == '428b60'
assert len(actual['frames']) == len(original['presentations']) == len(original['input_witnesses']) >= 61
for index, (frame, reference, state) in enumerate(zip(actual['frames'], original['presentations'], original['input_witnesses']), 1):
    assert frame['frame'] == frame['presentations'] == index
    assert (frame['width'], frame['height']) == (640, 480)
    assert frame['resourceFault'] == frame['displayFault'] == 0
    assert frame['pixels'] == reference['pixels_sha256'], (index, 'pixels')
    assert frame['palette'] == reference['palette_sha256'], (index, 'palette')
    if original.get('startup_paper'):
        assert frame['frame_ms'] == state['frame_ms'], (index, 'frame clock')
        assert frame['milliseconds'] - actual['frames'][0]['milliseconds'] == state['milliseconds'] - original['input_witnesses'][0]['milliseconds'], (index, 'elapsed clock')
    assert (frame['selected'], frame['page_id']) == (state['selected'], state['page_id']), (index, 'selection/page')
# Prove the requested transitions happened, rather than matching two idle runs.
for frame, selected, page in ((1, 0, 10000), (9, 1, 10000), (17, 0, 10000),
                              (26, 0, 10001), (33, 0, 10000), (50, 0, 10001)):
    state = actual['frames'][frame - 1]
    assert (state['selected'], state['page_id']) == (selected, page)
for frame in (1, 9, 17, 26, 33, 41, 50, 61):
    for prefix in ('original', 'native'):
        assert (args.evidence / f'{prefix}-{frame:02d}.png').is_file()
# Reconcile newly visited code with existing admissions plus the new forwarding
# family. This does not replace the admission gate or claim source freshness.
owners = {}
for path in (ROOT / 'Tests/families').glob('*.json'):
    family = json.loads(path.read_text())
    if family.get('evidence', {}).get('level') == 'admitted':
        for entry in family.get('owned', []):
            owners.setdefault(entry['address'], []).append(family['id'])
census = {entry['address']: owners.get(entry['address'], []) for entry in original['new_game_functions']}
# The horizontal raw PID transport is a previously completed native adapter,
# not a canonical family admission. Keep that evidence category explicit.
transports = {'0x4c0450': dict(owner='ClawNativeDisplay.rawSelectedPID',
    evidence='menu-native-shared-route-controls: 72 original/native raw profiles',
    scope='existing bounded eight-bit transport; no canonical entry admission')}
assert all(value or address in transports for address, value in census.items()), ('unowned input functions', census)
report = dict(status='pass', compared_frames=len(actual['frames']), pixels='original', palette='original',
    input='down, up, Enter, Escape, pointer move and primary click', new_function_owners=census,
    new_platform_imports=original['new_platform_imports'], existing_native_transports=transports, evidence=str(args.evidence),
    scope='Mac app frame and menu-state comparison; real UI input verified separately')
if args.live:
    checkpoints = {}
    for name, selected, page, key in (('down', 1, 10000, 40), ('up', 0, 10000, 38),
                                    ('enter', 0, 10001, 13), ('escape', 0, 10000, 27),
                                    ('click', 0, 10001, None)):
        state = json.loads((args.evidence / f'live-{name}.json').read_text())
        assert state['status'] == 'running' and state['error'] == '', (name, state)
        assert (state['selected'], state['page_id']) == (selected, page), name
        assert (args.evidence / f'live-{name}.png').is_file(), name
        if key is not None:
            assert any(e.get('key') == key and e.get('down') for e in state['events']), name
        else:
            assert any(e.get('message') == 0x201 for e in state['events']), name
        checkpoints[name] = dict(frame=state['frames'], selected=selected, page_id=page)
    report['live_ui_checkpoints'] = checkpoints
(args.evidence / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
