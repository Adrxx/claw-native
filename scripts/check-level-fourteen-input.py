"""Confirm real window keys reach Level 14 and move Claw; closes only its muted instance."""
import json
import os
from pathlib import Path
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/level-fourteen-input'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    helper = build_helper(ROOT/'work/end-of-level/post-window-input')
    session = Session(OUT, helper=helper)
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    report = dict(check='level-fourteen-real-input', status='fail', errors=[])
    def live():
        try: return json.loads((OUT/'live.json').read_text())
        except (OSError, ValueError): return {}
    def at(level):
        return live().get('state_vtable') == '0x50c264' and live().get('level') == level
    try:
        session.launch(app, {}, ['--no-paper-startup', '--save-dir', str(OUT/'saves'), '-ClawCheckDirectory', str(OUT)])
        session.sleep(2)
        for _ in range(3):
            session.post('key', 36)
            session.sleep(2)
        if not session.wait(lambda: at(1), 30): raise RuntimeError('Level 1 did not load')
        for level in range(1, 14):
            for code in (46, 35, 1, 8, 32, 37, 37, 16): session.post('key', code)
            for _ in range(30):
                if session.wait(lambda: at(level+1), 1): break
                if session.failed(): raise RuntimeError(f'App failed after Level {level}')
                session.post('key', 36)
            if not at(level+1): raise RuntimeError(f'Completion did not reach Level {level+1}')
        before = session.mark('before-right')
        session.post('press', 124, 'down')
        session.sleep(0.5)
        session.post('press', 124, 'up')
        after = session.mark('after-right')
        if not before or not after or after['player']['x'] <= before['player']['x']:
            raise RuntimeError('Confirmed right key did not move Claw')
        report.update(status='pass', before=before['player']['x'], after=after['player']['x'],
                      delivered=session.transitions(), retries=session.retries)
    except (RuntimeError, OSError, KeyError) as error:
        report['errors'].append(str(error))
    finally:
        session.close()
    (OUT/'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    return int(report['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
