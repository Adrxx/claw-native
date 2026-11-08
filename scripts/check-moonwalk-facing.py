"""Restore facing, then exercise delivered movement against the original turn/walk oracle.

Keyboard events are confirmed by real_input. Controller axes are labelled native
provider samples (not physical hardware). Runs only its own muted Release app.
"""
import argparse
import json
import os
from pathlib import Path
from real_input import Session, build_helper, MAC_TO_VK

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--expect-bug', action='store_true')
    parser.add_argument('--version', choices=['1.0', '1.3'], default='1.0')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper = build_helper(ROOT/'work/moonwalk-facing/post-window-input')
    app = ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst') / 'Build/Products/Release-maccatalyst/Claw.app'
    report = dict(check='moonwalk-facing', version=args.version, status='fail', samples=[], errors=[],
                  controller_delivery='Diagnostic native provider samples; no hardware acceptance.',
                  keyboard_delivery='Confirmed real window events.')
    session = None
    def live():
        return json.loads((session.out/'live.json').read_text())
    def run(frames):
        if session.run(frames).get('status') == 'fail':
            raise RuntimeError(str(session.gate()))
    def tap(key, *flags):
        session.post('key', key, *flags);run(4)
    def launch(name, level=None):
        nonlocal session
        if session: session.close()
        folder = out/name;folder.mkdir()
        session = Session(folder, helper=helper)
        session.launch(app, {'CLAW_GAME_VERSION':args.version}, ['--save-dir', str(out/'saves'), '--settings-dir', str(out/'settings'),
            '--game-version', args.version, '--stationary-cursor', '--no-paper-startup',
            '--custom-checkpoint-check', '--controller-input-check',
            *(['--custom-checkpoint-level', str(level)] if level else []),
            '-ClawCheckDirectory', str(folder)], start_seconds=120)
        run(120)
    def sample(name):
        state = live()
        fields = ['x','y','player_state','render_flags','velocity_x','velocity_y','logic_state',
                  'facing_rectangles','input_mask','controller','custom_checkpoint','v13_cheats']
        row = dict(name=name, **{k:state[k] for k in fields if k in state})
        row['delivery'] = session.input_state()
        report['samples'].append(row)
        return row
    def aligned(row, direction=None):
        facing = row['player_state']
        assert (row['render_flags'] & 2) == (0 if facing else 2), f'private/render facing split: {row}'
        if direction:
            expected = original_walk(2 if saved_left else 0, direction)
            assert facing == expected['private_facing'], f'original facing differs: {row}, {expected}'
            assert row['render_flags'] & 2 == expected['render_flags'] & 2, f'original mirror differs: {row}'
            assert row['velocity_x'] == expected['vx'], f'original walk velocity differs: {row}, {expected}'
            assert row['logic_state'] == expected['logic_state'], f'original walk state differs: {row}'
            row['original'] = expected
    def walk(direction, name):
        key = 123 if direction == 'left' else 124
        session.post('press',key,'down');run(4)
        row = sample(name)
        aligned(row, direction)
        session.post('press',key,'up');run(4)
    def restore(name):
        path = session.out/'custom-restore.json'
        path.unlink(missing_ok=True)
        count = sum(e['action']=='restore' for e in live().get('custom_checkpoint', []))
        tap(20,'command,shift')
        result = json.loads(path.read_text())
        assert sum(e['action']=='restore' for e in live()['custom_checkpoint']) == count + 1, 'Restore event missing'
        assert result['status'] == 'pass', result
        row = sample(name)
        if not args.expect_bug:
            aligned(row)
            expected = original_restore(2 if saved_left else 0, initial=initial)
            assert row['player_state'] == expected['private_facing'], f'restored direction differs: {row}, {expected}'
            assert row['facing_rectangles'] == expected['facing_rectangles'], f'restored rectangles differ: {row}, {expected}'
            row['original_restore'] = expected
        return row
    try:
        if not args.expect_bug:
            from moonwalk_oracle import original_walk, original_restore, original_airborne, original_evidence
            report['oracle'] = original_evidence()
        launch('direct', 2)
        initial = sample('fresh-player')
        for saved_left in (True, False):
            key = 123 if saved_left else 124
            session.post('press',key,'down');run(4)
            session.post('press',key,'up');run(4)
            tap(20,'command')
            saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
            assert saved['facing'] == (2 if saved_left else 0), saved
            opposite = 124 if saved_left else 123
            session.post('press',opposite,'down');run(4)
            session.post('press',opposite,'up');run(4)
            restored = restore('restore-left' if saved_left else 'restore-right')
            if args.expect_bug:
                session.post('press',124,'down');run(4)
                row = sample('bug-right-after-left-restore')
                session.mark('first-mismatch')
                assert row['velocity_x'] > 0 and row['render_flags'] & 2 and row['player_state'] == 1, row
                report['status'] = 'reproduced'
                break
            walk('right','keyboard-right');walk('left','keyboard-left')
            # Relaunch from disk uses the same restore path with freshly initialized player data.
            launch('relaunch-left' if saved_left else 'relaunch-right')
            restore('disk-restore')
            walk('right','disk-keyboard-right');walk('left','disk-keyboard-left')
            for direction, x in [('right',65535),('left',0)]:
                with session.control.open('a') as stream:stream.write(f'j 1 {x} 32767 0\n')
                run(4);aligned(sample('controller-'+direction), direction)
                with session.control.open('a') as stream:stream.write('j 1 32767 32767 0\n')
                run(4)
            # Normal airborne movement changes facing through the same original turn routines.
            session.post('press',49,'down')
            for key in (124,123):
                session.post('press',key,'down');run(4)
                row=sample('jump-'+str(key));aligned(row)
                assert row['player_state'] == (key == 124), row
                assert row['velocity_x'] == (225 if key == 124 else -225), row
                session.post('press',key,'up')
            session.post('press',49,'up')
            session.post('press',123,'down');session.post('press',124,'down')
            for _ in range(60):
                run(1)
                if live()['logic_state'] == 25:break
            assert live()['logic_state'] == 25, 'Did not reach original falling state'
            run(2);row=sample('fall-both-directions');aligned(row)
            expected=original_airborne(2 if saved_left else 0, 0x3000000)
            assert row['velocity_x'] == expected['vx'] and row['player_state'] == expected['private_facing'], (row, expected)
            row['original_airborne']=expected
            session.post('press',123,'up');session.post('press',124,'up');run(90)
            # Analog noise in the dead zone must leave the facing coherent and no horizontal input held.
            for x in (32766,32767,32768):
                with session.control.open('a') as stream:stream.write(f'j 1 {x} 32767 0\n')
                run(2);row=sample('controller-neutral');aligned(row)
                assert row['input_mask'] & 0x3000000 == 0, row
            if args.version == '1.3':
                keys = {chr(v):k for k,v in MAC_TO_VK.items() if 65 <= v <= 90}
                for c in 'MPTWINTURBO':tap(keys[c])
                assert live()['v13_cheats']['turbo'] != 0, live()
                for key in (124,123):
                    session.post('press',key,'down');run(4)
                    row=sample('turbo-'+str(key));aligned(row)
                    assert row['player_state'] == (key == 124), row
                    assert row['velocity_x'] == (450 if key == 124 else -450), row
                    session.post('press',key,'up');run(4)
                for c in 'MPTWINTURBO':tap(keys[c])
        if not args.expect_bug: report['status'] = 'pass'
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if session:session.close()
        # Evidence is in JSON; retain only an explicitly marked first mismatch.
        for frame in out.rglob('frame-*.png'):frame.unlink()
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],errors=report['errors'],result=str(out/'result.json'))))
    return 0 if report['status'] in ('pass','reproduced') else 1


if __name__ == '__main__': raise SystemExit(main())
