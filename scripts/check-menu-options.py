"""Check Options > Controls > Escape against original execution.

Reference: work/test-env/bin/python -m Tests.NativeMenuBase.options_trace
App: scripts/run-mac.sh --menu-check "$PWD/work/menu-options/native" --menu-input-script "$PWD/work/menu-options/events.json"
Check: work/test-env/bin/python scripts/check-menu-options.py
An incomplete matching prefix is diagnostic evidence only and exits nonzero.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT/'work/menu-options')
    parser.add_argument('--native', type=Path, help='App evidence directory; defaults to evidence/native')
    args = parser.parse_args()
    native = args.native or args.evidence/'native'
    original = json.loads((args.evidence/'original-command.json').read_text())
    actual = json.loads((native/'app-menu.json').read_text())
    problems = []
    def check(condition, detail):
        if not condition:
            problems.append(detail)
    check(original['executable_sha256'] == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263', 'reference binary hash')
    frames = actual.get('frames', [])
    reference = original.get('presentations', [])
    witnesses = original.get('input_witnesses', [])
    compared = 0
    for index, (frame, image, state) in enumerate(zip(frames, reference, witnesses), 1):
        check(frame['frame'] == frame['presentations'] == state['frame'] == index, f'frame {index}: sequence')
        check((frame['width'], frame['height']) == (640,480), f'frame {index}: dimensions')
        check(frame['resourceFault'] == frame['displayFault'] == 0, f'frame {index}: native fault')
        check(frame['pixels'] == image['pixels_sha256'], f'frame {index}: pixels')
        check(frame['palette'] == image['palette_sha256'], f'frame {index}: palette')
        for key in ('selected','page_id','state_vtable'):
            check(key in frame and key in state and frame[key] == state[key], f'frame {index}: {key}')
        compared += 1
    complete = original.get('status') == actual.get('status') == 'pass' and original.get('stop') is None
    complete = complete and len(frames) == len(reference) == len(witnesses) == 61
    owners = {}
    for path in (ROOT/'Tests/families').glob('*.json'):
        family = json.loads(path.read_text())
        if family.get('evidence', {}).get('level') == 'admitted':
            for entry in family.get('owned', []):
                owners.setdefault(entry['address'], []).append(family['id'])
    census = {entry['address']:owners.get(entry['address'], [])
              for entry in original['new_game_functions']}
    if complete:
        check(all(census.values()), 'new game functions without admission')
        check(actual.get('initializer') == '45ace0' and actual.get('frameEntry') == '428b60', 'native entries')
        # State 13 is the original Controls popup; both Escapes must return.
        for frame, mode, page in ((17,5,10004),(33,13,None),(50,5,10004),(61,5,10000)):
            state = witnesses[frame-1]
            check(state['state_id'] == mode, f'frame {frame}: requested state transition')
            if page is not None:
                check(state['page_id'] == page, f'frame {frame}: requested page transition')
        for frame in (1,9,17,26,33,41,50,61):
            for directory, prefix in ((args.evidence,'original'),(native,'native')):
                check((directory/f'{prefix}-{frame:02d}.png').is_file(), f'{prefix} screenshot {frame}')
    report = dict(status='fail' if problems else ('pass' if complete else 'blocked'),
                  complete_sequence=complete, compared_frames=compared, problems=problems,
                  reference_stop=original.get('stop'), native_error=actual.get('error'),
                  new_function_owners=census,
                  reference=str(args.evidence), native=str(native),
                  scope='Mac app exact pixel, palette, menu and current-state comparison; a matching prefix does not prove Controls opens')
    (args.evidence/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
