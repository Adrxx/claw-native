"""Real keyboard check of the original IFC disabled path for unsupported services.

Owner decision 2026-10-27 permits disabling these features. The multiplayer
page remains reachable; its service actions and score upload
use the original disabled callback instead of opening a native service.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from real_input import Session, build_helper, real_time_requested

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/unavailable-menu-items/check'
ITEMS = {11005: 'Upload Scores',
         12001: 'Racing', 12002: 'Game Lobby / Engage online',
         12003: 'Edit Chat Macros'}


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-time', action=argparse.BooleanOptionalAction, default=True,
                        help='Normal frame pacing (default); --no-real-time uses the input gate')
    args = parser.parse_args()
    real_time = real_time_requested(args.real_time)
    WORK = WORK / ('real-time' if real_time else 'fast')
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        time.sleep(10)
    helper = build_helper(ROOT / 'work/unavailable-menu-items/post-window-input')
    app = ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst') / 'Build/Products/Release-maccatalyst/Claw.app'
    session = Session(WORK, fast=not real_time, helper=helper)
    result = dict(check='unavailable-menu-items', status='fail', items=[], errors=[])

    def live():
        return json.loads((WORK / 'live.json').read_text())

    def require(value, message):
        if not value:
            raise RuntimeError(message)

    def tap(key):
        session.post('key', {'down': 125, 'ret': 36, 'esc': 53}[key])
        session.sleep(.3)
        require(not session.failed() and live().get('status') != 'fail', 'app fault after ' + key)

    def choose(identifier):
        for _ in range(12):
            if live().get('menu_selected') == identifier:
                return
            tap('down')
        raise RuntimeError(f'cannot select {identifier}: {live().get("menu_selected")}')

    try:
        session.launch(app, {}, ['--save-dir', str(WORK / 'saves'),
                                 '--settings-dir', str(WORK / 'settings')])
        session.sleep(3)
        # Re-enter both pages: original entry code updates availability again.
        for visit in range(2):
            for parent, ids in ((10001, (11005,)), (10002, (12001, 12002, 12003))):
                choose(parent)
                tap('ret')
                require(live().get('menu_page') == parent, 'page did not open')
                flags = live().get('unavailable_menu_flags', {})
                for identifier in ids:
                    require(flags.get(str(identifier), 0) & 0x20, f'{identifier} is enabled or absent')
                name = f'{visit}-{parent}'
                before = session.mark(name + '-before')
                commands = live().get('posted_commands', [])
                if parent == 10002:
                    # IFC page entry initially selects index zero, even disabled.
                    require(live().get('menu_selected') == 12001 and live().get('menu_selected_disabled'),
                            'Racing is not the disabled initial selection')
                    tap('ret')
                    session.sleep(.7)
                    require(live().get('menu_page') == parent, 'disabled Racing entered a service')
                    require(live().get('menu_selected') == 12001, 'disabled Racing changed selection')
                visited = []
                for _ in range(8):
                    tap('down')
                    require(live().get('menu_page') == parent, 'navigation left page')
                    visited.append(live().get('menu_selected'))
                require(not set(ids).intersection(visited), f'disabled actions selectable: {visited}')
                require(live().get('posted_commands', []) == commands, 'unsupported service command posted')
                after = session.mark(name + '-after')
                require(before is not None and after is not None, 'frame evidence missing')
                if parent == 10002:
                    # 45fa50 is the IFC virtual callback into 45c240; the latter
                    # is an internal call in the same compiled family.
                    counts = lambda mark: mark.get('invoke_counts', {}).get('45fa50', 0)
                    require(counts(after) > counts(before), 'Racing did not reach original disabled callback')
                for identifier in ids:
                    result['items'].append(dict(id=identifier, item=ITEMS[identifier], visit=visit,
                        behavior='disabled; keyboard navigation skips; no service command',
                        enter_checked=identifier == 12001, flags=flags[str(identifier)],
                        evidence=name + '-after.png'))
                tap('esc')
                require(live().get('menu_page') == 10000, 'Escape did not return to main')
        choose(10001)
        tap('ret')
        choose(11001)
        tap('ret')
        require(live().get('menu_page') == 11001, 'supported New Game page no longer opens')
        result['status'] = 'pass'
    except Exception as error:
        result['errors'].append(str(error))
    finally:
        session.close()
    (WORK / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
