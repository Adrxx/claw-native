"""Load original WWD samples through the visible menu with confirmed real keys.

Samples stay local. Pass a folder containing WWDs (or nested sample folders).
One Man Assault 2 uses SpotAmbientBigSound, absent from the original
registration. --unsupported can name additional negative samples. Companion
folders are copied with their WWDs so portable custom features can load.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/custom-levels/check'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=Path, default=ROOT/'work/custom-levels')
    parser.add_argument('--only')
    parser.add_argument('--unsupported', action='append', default=['One Man Assault 2.wwd'])
    parser.add_argument('--finish', action='store_true', help='MPSCULLY and results back to menu')
    args = parser.parse_args()
    paths = sorted(p.resolve() for p in args.samples.rglob('*') if p.suffix.lower() == '.wwd'
                   and not p.is_relative_to(WORK) and (not args.only or args.only.lower() in p.name.lower()))
    if not paths:
        parser.error('No sample WWDs found')
    WORK.mkdir(parents=True, exist_ok=True)
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    report = dict(check='custom-levels', status='pass', samples=[])
    for index, path in enumerate(paths):
        out = WORK / f'{index}-{path.stem}'
        out.mkdir(exist_ok=True)
        folder = out/'Custom'
        folder.mkdir(exist_ok=True)
        shutil.copy2(path, folder/path.name)
        if path.with_suffix('').is_dir():
            shutil.copytree(path.with_suffix(''),folder/path.stem,dirs_exist_ok=True)
        session = Session(out, helper=helper)
        result = dict(file=path.name, expected_unsupported=path.name in args.unsupported, status='fail', errors=[])
        def live():
            return json.loads((out/'live.json').read_text())
        def tap(code):
            session.post('key', code)
            session.sleep(.25)
            assert not session.failed(), (out/'gate.json').read_text()
        try:
            session.launch(app, {}, ['--custom-dir', str(folder), '--no-paper-startup',
                '--save-dir', str(out/'saves'), '--settings-dir', str(out/'settings'), '--long-trace'])
            session.sleep(1)
            tap(36)  # Single Player
            for _ in range(10):
                if live().get('menu_selected') == 11003:
                    break
                tap(125)
            assert live().get('menu_selected') == 11003, 'Custom menu item unreachable'
            tap(36)
            assert live().get('custom_dialog'), 'Original custom dialog selector did not open'
            # Escape must leave the same menu usable; reopen and confirm.
            tap(53)
            assert not live().get('custom_dialog'), 'Cancel did not close picker'
            tap(36)
            tap(36)
            if path.name in args.unsupported:
                assert live().get('custom_dialog'), 'Unsupported file entered gameplay'
                assert any(kind in live().get('custom_error','') for kind in ('Not implemented:', 'Unsupported execution:')), live()
                result['message'] = live()['custom_error']
                tap(53)
                assert not live().get('custom_dialog') and live().get('menu_page') == 10001
            else:
                assert not live().get('custom_dialog'), live().get('custom_error')
                assert live().get('custom_flag') == 1, live()
                assert live().get('state_vtable') == '0x50c264', live()
                session.run(45)
                before = session.mark('before')
                session.post('press',124,'down')
                session.run(20)
                session.post('press',124,'up')
                after = session.mark('after')
                assert before and after and not session.failed(), 'Gameplay failed'
                result['player_before'] = before['player']
                result['player_after'] = after['player']
                assert (before['player']['x'],before['player']['y']) != (after['player']['x'],after['player']['y']), 'Player did not move during real input'
                result['loaded'] = live()['custom_level']
                assert result['loaded']['reads'] >= 3, 'Original CFile reader did not load the WWD'
                assert session.transitions().get('39:down', 0) > 0, 'Right was not received'
                if args.finish:
                    # Owner-approved completion cheat; never play to finish.
                    for code in [46,35,1,8,32,37,37,16]:
                        tap(code)
                    assert session.wait(lambda: live().get('state_vtable') == '0x50c0c4', 10), live()
                    for _ in range(10):
                        if session.wait(lambda: live().get('state_vtable') != '0x50c0c4', 12):
                            break
                        tap(36)
                    assert session.wait(lambda: live().get('menu_page') in (10000,10001), 20), live()
                    result['completion'] = 'MPSCULLY, results, menu'
            result['status'] = 'pass'
            result['input_transitions'] = session.transitions()
        except Exception as error:
            result['errors'].append(str(error))
            report['status'] = 'fail'
        finally:
            session.close()
        report['samples'].append(result)
        (WORK/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    print(json.dumps({'status':report['status'], 'report':str(WORK/'report.json')}))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
