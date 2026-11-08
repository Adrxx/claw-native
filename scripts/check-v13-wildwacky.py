"""Check v1.3 MPWILDWACKY twice with confirmed real keys in a muted instance.

Checks the sprite mirror word, restoration, command delivery and registration's
presentation-only flag. This covers one command, not all ten v1.3 additions.
"""
import argparse
import json
import os
from pathlib import Path
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
KEYS = dict(zip('MPWILDACKY', (46,35,13,34,37,2,0,8,40,16)))
MENU = [{'ms':ms+d,'key':13,'down':1-d//80} for ms in (3000,5000,7000) for d in (0,80)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=False)
    (out/'menu.json').write_text(json.dumps(MENU))
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    app = ROOT/Path(os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst'))/'Build/Products/Release-maccatalyst/Claw.app'
    report = {'check':'v13-wildwacky','status':'fail','observations':[]}
    session = Session(out,fast=True,helper=helper)

    def live():
        try:return json.loads((out/'live.json').read_text())
        except (OSError,ValueError):return {}

    def wait(predicate,seconds=60):
        if not session.wait(lambda:predicate(live()) or session.failed(),seconds) or session.failed():
            raise RuntimeError('No healthy app response: '+str(live().get('error')))

    def capture(name):
        current = live()['frame']
        frame = (current//300+1)*300
        session.sleep((frame-current+2)/60)
        filename = f'frame-{frame:05d}.png'
        assert (out/filename).is_file(),filename
        report.setdefault('screenshots',{})[name] = filename

    try:
        session.launch(app,{'CLAW_REAL_SPEED_KEYS':out/'menu.json'},
                       ['--save-dir',str(out/'saves'),'-ClawCheckDirectory',str(out)])
        wait(lambda s:s.get('state_vtable')=='0x50c264' and s.get('level')==1 and s.get('game_ms',0)>1000,120)
        initial = live()['v13_cheats']
        assert initial['sprite_flags'] & 4 == 0,initial
        assert initial['cheated'] == 0,initial
        capture('initial')
        for enabled in (True,False):
            before = len(live().get('posted_commands',[]))
            for letter in 'MPWILDWACKY':session.post('key',KEYS[letter])
            wait(lambda s:'0x80b4' in s.get('posted_commands',[])[before:],8)
            session.sleep(.3)
            state = live()
            flags = state['v13_cheats']
            assert bool(flags['sprite_flags'] & 4) == enabled,flags
            assert flags['cheated'] == 0,flags
            assert state.get('state_vtable') == '0x50c264',state.get('state_vtable')
            report['observations'].append({'enabled':enabled,'flags':flags,
                'posted':state['posted_commands'][before:],'frame':state['frame']})
            if enabled:
                facing = []
                for key in (123,124):
                    session.post('key',key)
                    session.sleep(.1)
                    mirror = live()['v13_cheats']['sprite_flags']
                    assert mirror & 4,mirror
                    facing.append(mirror & 2)
                assert facing[0] != facing[1],facing
                report['horizontal_mirror_with_vertical'] = facing
            capture('enabled' if enabled else 'restored')
        report['status'] = 'pass'
    except (AssertionError,RuntimeError,KeyError) as error:
        report['error'] = str(error)
    finally:session.close()
    (out/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    return 0 if report['status']=='pass' else 1


if __name__ == '__main__':raise SystemExit(main())
