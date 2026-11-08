#!/usr/bin/env python3
"""Confirmed real window keys through native player sheets, then persisted records."""
import json
import os
from pathlib import Path
import shutil
import sys

from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'work/save-load'))
import usr


def main():
    out = ROOT / 'work/save-load/real-input'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    helper = build_helper(ROOT / 'work/post-window-input')
    app = ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst') / 'Build/Products/Release-maccatalyst/Claw.app'
    session = Session(out, helper=helper)
    def live():
        return json.loads((out / 'live.json').read_text())
    def tap(code):
        session.post('key', code)
        session.run(24)
    try:
        session.launch(app, {}, ['--no-paper-startup', '--menu-live-check', str(out),
                                 '--save-dir', str(out / 'saves'), '--settings-dir', str(out / 'settings')])
        session.run(1)
        for code in [125, 125, 36, 36]:
            tap(code)
        assert live()['players_dialog'] == 0, live()
        tap(45)  # N: new
        assert live()['players_dialog'] == 1
        for code in [15, 14, 0, 37]:  # REAL
            tap(code)
        tap(36)  # A name without a location must keep USERNEW open.
        assert live()['players_dialog'] == 1
        assert not any(p['name'] == 'REAL' for p in live()['profiles'])
        tap(48)  # Tab: Location
        tap(37)  # L
        tap(48)  # Tab: Comment (the retained third text field)
        for code in [45, 31, 17, 14]:  # NOTE
            tap(code)
        tap(36)
        assert any(p['name'] == 'REAL' and p['selected'] for p in live()['profiles']), live()
        created = usr.decode((out / 'saves/CLAW.USR').read_bytes())
        # The binary record keeps its third text slot; it has no email validation.
        record = next(r for r in created['records'] if r['name'] == 'REAL')
        assert record['location'] == 'L' and record['email'] == 'NOTE', record
        saved_bytes = (out / 'saves/CLAW.USR').read_bytes()
        tap(126)  # Up selects Player immediately; Cancel does not undo it.
        assert any(p['name'] == 'Player' and p['selected'] for p in live()['profiles']), live()
        assert (out / 'saves/CLAW.USR').read_bytes() == saved_bytes
        tap(53)
        assert live()['players_dialog'] == -1
        assert any(p['name'] == 'Player' and p['selected'] for p in live()['profiles'])
        tap(36)  # Reopen Edit Players at the retained Options selection.
        assert live()['players_dialog'] == 0, live()
        tap(125)  # Down selects REAL without requiring an explicit Select action.
        assert any(p['name'] == 'REAL' and p['selected'] for p in live()['profiles']), live()
        tap(15)  # R: remove
        assert live()['players_dialog'] == 2
        tap(53)  # Escape cancels the removal
        assert any(p['name'] == 'REAL' for p in live()['profiles'])
        tap(15)
        tap(36)  # Confirm
        assert live()['profiles'] == [{'name': 'Player', 'selected': True}], live()
        tap(53)
        assert live()['players_dialog'] == -1
        records = usr.decode((out / 'saves/CLAW.USR').read_bytes())
        assert records['valid'] and [r['name'] for r in records['records']] == ['Player'], records
        result = dict(check='edit_players_real_input', status='pass', transitions=session.transitions(),
                      retries=session.retries, records=[r['name'] for r in records['records']])
    finally:
        session.close()
    (out / 'check.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
