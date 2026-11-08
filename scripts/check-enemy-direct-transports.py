"""All-level election audit and Level 6 source-context enemy virtual regression.

--tables-only checks the app's native predicate and all 14 retained join
elections. The default also takes the MPSCULLY route with confirmed real keys
on a muted fast-clock Release app, then lingers in enemy strike range.
"""
import argparse
import ctypes as C
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import time
import subprocess

from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/enemy-direct-transports'


def tables():
    # This builds only the small native host transport, never admitted sources.
    while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        time.sleep(10)
    spec = importlib.util.spec_from_file_location('transport_check', ROOT/'scripts/check-level-one-transports.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    lib = shared.build()
    direct = lib.claw_level_tail_direct_ok
    direct.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32]
    direct.restype = shared.U32
    election = json.loads((ROOT/'App/GameData/MENU/level-one-transports.json').read_text())
    app_tail = set(election['tail_only'])
    assert {'0x43efe0', '0x43f740'} <= app_tail
    # After the predicate, a source CALL continues through the ordinary source
    # transport (ClawNativeMenuResources.levelTransport): the owner must be in
    # the registry, must not return or need x87 state, and without a source
    # capability must have a convention claw_level_ordinary_source_ok serves.
    registry = {}
    row = re.compile(r'\{0x([0-9a-f]{8})u, CLAW_CANONICAL_(\w+), (\d+)u, CLAW_CANONICAL_RETURN_(\w+), \w+, "\w+", '
                     r'(\d+)u, \d+u, \d+u, \d+u, \d+u, \d+u, \d+u, (\d+)u\}')
    for m in row.finditer((ROOT/'Sources/ClawCanonicalDispatch.h').read_text()):
        registry[int(m[1], 16)] = dict(convention=m[2], ret=m[4], source=int(m[5]), x87env=int(m[6]))
    def servable(target):
        e = registry.get(int(target, 16))
        return bool(e) and e['ret'] != 'X87' and not e['x87env'] and \
            (e['source'] or e['convention'] in ('CDECL', 'STDCALL', 'THISCALL'))
    levels = []
    checks = 0
    for level in range(1, 15):
        folder = 'native-level-one-join' if level == 1 else 'native-level-two-join' if level == 2 else f'native-level-{level}-join'
        owners = json.loads((ROOT/'work'/folder/'owners.json').read_text())
        assert not owners['unresolved'], f'Level {level}: unresolved election'
        available = set(owners['owners']) | set(owners['tail_only'])
        assert {'0x43efe0', '0x43f740'} <= available, f'Level {level}: missing enemy owner'
        # The app installs the Level 1 election globally. Later joins may elect
        # a shared target as ordinary; test both classifications and contexts.
        targets = app_tail & available | set(owners['tail_only'])
        for target in sorted(targets):
            assert servable(target), f'Level {level}: tail-only owner {target} cannot be served from a source CALL'
            for source in (None, 1):
                q = shared.Call(function=int(target, 16), receiver=0x61000000, source=source)
                assert direct(C.byref(q), 0x497960, 1) == 1, (level, target, source)
                assert direct(C.byref(q), 0x497960, 0) == 0, 'foreign receiver accepted'
                for caller in (0, 0x4a3050, 0x546df0):
                    assert direct(C.byref(q), caller, 1) == 0, 'non-game caller accepted'
                for field in ('receiver', 'compiler', 'callback_cpu', 'x87_count', 'x87_state',
                              'transfer_version', 'transfer_kind', 'transfer_site', 'caller', 'disposition'):
                    bad = shared.Call.from_buffer_copy(q)
                    setattr(bad, field, 0 if field == 'receiver' else 1)
                    assert direct(C.byref(bad), 0x497960, 1) == 0, field
                checks += 15
        levels.append(dict(level=level, checked_targets=len(targets),
                           join_tail_only=len(owners['tail_only']),
                           app_tail_only=len(app_tail & available)))
    return dict(levels=levels, predicate_checks=checks)


def play():
    out = OUT/'run'
    # Session.mark waits for a file to appear: an earlier run's marks must
    # never satisfy that wait or supply the damage/respawn assertions.
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    derived = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT/'work/MacCatalyst'))
    session = Session(out, fast=True, helper=build_helper(ROOT/'work/cheat-codes/post-window-input'))
    def read(name):
        try:
            return json.loads((out/name).read_text())
        except (OSError, ValueError):
            return {}
    def require(ok, message):
        if not ok:
            raise RuntimeError(f"{message}: {read('real-speed.json').get('error', '')}")
    def healthy():
        require(not session.failed(), 'frame fault')
    def hold(keys, seconds):
        for key in keys:
            session.post('press', key, 'down')
        session.sleep(seconds)
        healthy()
        for key in keys:
            session.post('press', key, 'up')
    marks = []
    try:
        session.launch(derived/'Build/Products/Release-maccatalyst/Claw.app', {},
                       ['--save-dir', str(out/'saves'), '--menu-live-check', str(out),
                        '-ClawCheckDirectory', str(out)])
        session.sleep(1)
        for _ in range(3):
            session.post('key', 36)
            session.sleep(1)
        require(session.wait(lambda: read('live.json').get('level') == 1, 90), 'New Game not reached')
        keys = {'M':46, 'P':35, 'S':1, 'C':8, 'U':32, 'L':37, 'Y':16}
        for level in range(1, 6):
            for letter in 'MPSCULLY':
                session.post('key', keys[letter])
            require(session.wait(lambda: read('live.json').get('state_vtable') == '0x50c0c4', 90), 'results not reached')
            session.sleep(12)
            session.post('key', 36)
            require(session.wait(lambda: read('live.json').get('level') == level+1 and
                                 read('live.json').get('state_vtable') == '0x50c264', 90), 'next level not reached')
        # Walk/climb the opening route to the Town Guards, then stay in range
        # through attacks, damage and respawns. Real events have input receipts.
        for keys, seconds in (([], 1), ([124], .5), ([49,126], 2), ([126], 4.5),
                              ([124], 1.5), ([], 8), ([124], 2), ([], 12)):
            hold(keys, seconds)
            marks.append(session.mark(f'combat-{len(marks)}'))
        counts = read('live-state.json').get('transports', {})
        require(counts.get('tail-only-direct-source-43efe0', 0) > 0, '43efe0 source CALL not exercised')
        require(counts.get('tail-only-direct-source-43f740', 0) > 0, '43f740 source CALL not exercised')
        players = [mark.get('player', {}) for mark in marks if mark]
        require(len(players) == 8 and all(p.get('level') == 6 for p in players), 'missing Level 6 marks')
        require(any(0 < p.get('health', 100) < 100 for p in players), 'enemy damage not exercised')
        require(players[-1].get('lives_lost', 0) > players[0].get('lives_lost', 0)
                and players[-1].get('health', 0) > 0, 'death and respawn not exercised')
        return dict(transports=counts, marks=marks, input=session.input_state())
    except Exception:
        (OUT/'failure.json').write_text(json.dumps(dict(live=read('live.json'), state=read('live-state.json'),
                                                       error=read('real-speed.json'), marks=marks), indent=2))
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tables-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(check='enemy-direct-transports', status='fail')
    try:
        report.update(tables())
        if not args.tables_only:
            report['play'] = play()
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = str(error)
    (OUT/'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'play'}))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
