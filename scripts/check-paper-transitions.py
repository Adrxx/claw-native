"""Compare every primary Unlock used by the paper transitions.

Loading-bar Blt writes retain their separate check-loading-screen comparison.

Reference: work/test-env/bin/python -m Tests.NativeMenuBase.paper_trace
App: work/test-env/bin/python scripts/check-paper-transitions.py --run
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/paper-roll/transitions'


def compare(reference, app, directory):
    errors = []
    required = {'0x435a50', '0x45b3f0', '0x48f500', '0x48f740', '0x490130'}
    new_game = reference.get('route') == 'new-game'
    credits = reference.get('route') == 'credits'
    if new_game:
        required = {'0x45b3f0','0x490130'}
    elif credits:
        required.remove('0x490130')
    if reference.get('status') != 'pass' or not required <= set(reference.get('reached', [])):
        errors.append('original did not finish all required transitions')
    if app.get('status') != 'pass':
        errors.append('app did not finish')
    ticks = {row['frame']: row for row in app.get('multi_flip_frames', [])}
    frames = {row['frame']: row for row in app.get('frames', [])}
    writes = 0
    for expected in reference.get('frames', []):
        number = expected['frame']
        tick = ticks.get(number, {})
        if frames.get(number, {}).get('state_vtable') != int(expected['state']['vtable'], 16):
            errors.append(f'frame {number}: state differs')
        actual = [w['pixels_sha256'] for w in tick.get('primary_writes', [])
                  if w.get('service') == 'IDirectDrawSurface::Unlock']
        if actual != expected['primary_writes']:
            first = next((i for i, (a,b) in enumerate(zip(expected['primary_writes'], actual)) if a != b),
                         min(len(actual),len(expected['primary_writes'])))
            errors.append(f'frame {number}: primary writes differ at {first} '
                          f'(original {len(expected["primary_writes"])}, app {len(actual)})')
        writes += len(expected['primary_writes'])
        presentations = expected['presentations']
        actual_flips = tick.get('flips', [])
        if (number in ticks or len(presentations) > 1) and [(p['pixels_sha256'],p['palette_sha256']) for p in presentations] != [
                (p['pixels_sha256'],p['palette_sha256']) for p in actual_flips]:
            errors.append(f'frame {number}: presentations differ')
        if presentations:
            last = presentations[-1]
            frame = frames.get(number, {})
            if (frame.get('pixels'),frame.get('palette')) != (last['pixels_sha256'],last['palette_sha256']):
                errors.append(f'frame {number}: final screen differs')
        for write in tick.get('primary_writes', []):
            if not (directory / write['png']).is_file():
                errors.append(f'frame {number}: missing primary image {write["png"]}')
    if len(frames) != len(reference.get('frames', [])):
        errors.append('frame counts differ')
    # Require visible transitions, including both Credits directions and the
    # New Game roll, rather than accepting an idle route with equal pixels.
    transitions = [(r['frame'],r['state']['vtable']) for i,r in enumerate(reference.get('frames', []))
                   if not i or r['state']['vtable'] != reference['frames'][i-1]['state']['vtable']]
    states = ['0x50c1e4','0x50c264'] if new_game else ['0x50c1e4','0x50c174','0x50c1e4','0x50c264']
    if credits:
        states = states[:-1]
    if [state for _,state in transitions] != states:
        errors.append('original state sequence is incomplete')
    transition_writes = {str(number):len(reference['frames'][number-1]['primary_writes'])
                         for number,_ in transitions}
    # Original menu entry from Credits (prior state 8) has no paper.
    if any(count <= 1 for number,count in transition_writes.items()
           if reference['frames'][int(number)-1]['state']['vtable'] != '0x50c1e4' or int(number) == 1):
        errors.append('a required transition has no paper animation')
    return dict(check='paper-new-game' if new_game else 'paper-credits' if credits else 'paper-credits-new-game', status='fail' if errors else 'pass',
                frames=len(reference.get('frames', [])), primary_writes=writes,
                paper_primary_unlocks_equal=reference.get('status') == app.get('status') == 'pass'
                    and len(frames) == len(reference.get('frames', []))
                    and not any('primary writes differ' in e for e in errors),
                transitions=transitions, transition_writes=transition_writes, errors=errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    routes = parser.add_mutually_exclusive_group()
    routes.add_argument('--new-game-only', action='store_true')
    routes.add_argument('--credits-only', action='store_true')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    work = WORK/'new-game' if args.new_game_only else WORK/'credits' if args.credits_only else WORK
    args.evidence = args.evidence or work/'app'
    reference = json.loads((work/'original.json').read_text())
    args.evidence.mkdir(parents=True, exist_ok=True)
    if args.run:
        (args.evidence/'app-menu.json').unlink(missing_ok=True)
        subprocess.run([str(ROOT/'work/new-game/launch.sh'),str(args.evidence),'240',
                        '--menu-check',str(args.evidence),'--menu-input-script',str(work/'events.json'),
                        '--menu-frames',str(len(reference['frames'])),'--new-game-clock',
                        '--paper-clock-check','--responsiveness-check'],
                       # These primary writes were recorded from v1.0 CLAW.EXE.
                       # Keep standalone runs on that profile too: the app's
                       # v1.3 default changes the HUD in the New Game roll.
                       env={**os.environ,'PAPER':'1','CLAW_GAME_VERSION':'1.0',
                            'CLAW_LIVES_BOSS_PROFILE':'claw-v1.0'},check=True)
    try:
        report = compare(reference,json.loads((args.evidence/'app-menu.json').read_text()),args.evidence)
    except (OSError,ValueError,KeyError) as error:
        report = dict(check='paper-credits-new-game',status='fail',errors=[str(error)])
    (work/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
