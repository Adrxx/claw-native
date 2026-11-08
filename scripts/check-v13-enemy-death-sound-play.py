#!/usr/bin/env python3
"""Muted Level 6 combat with delivered real keyboard events and enemy-death evidence.

Run after the Release build. Uses the owner's MPSCULLY level progression and
retained MPKFA God Mode for a bounded fight. This is native gameplay evidence;
the separate oracle gate and offline check prove state-bit/interval semantics.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from real_input import Session, build_helper, MAC_TO_VK

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work' / 'v13-enemy-death-sound-play'
KEYS = {'M':46, 'P':35, 'S':1, 'C':8, 'U':32, 'L':37, 'Y':16, 'K':40, 'F':3, 'A':0}


class CombatSession(Session):
    def post(self, *args):
        try:
            return super().post(*args)
        except RuntimeError as error:
            if not args or args[0] != 'press' or 'window event lost twice' not in str(error):
                raise
            # A Catalyst responder change during New Game can lose a release.
            # Refocus only this process's own window, then require the pending
            # real event receipt and unchanged paused frame before proceeding.
            name = f'{MAC_TO_VK[int(args[1])]}:{args[2]}'
            expected = self.transitions().get(name, 0) + 1
            subprocess.run([self.helper,str(self.pid),'click'],check=True,capture_output=True,text=True)
            posted = self._post(args)
            end = time.monotonic() + 5
            while self.transitions().get(name, 0) < expected and time.monotonic() < end:
                time.sleep(.01)
            if self.transitions().get(name, 0) < expected:
                raise error
            self._gate_wait(5)
            self.retries.append({'responder_refocus':list(map(str,args)),'frame':self.frames})
            return posted


def reviewed_god_code():
    registrations = json.loads((ROOT/'work/v13/command-registration-review.json').read_text())['registrations']['v13']
    actions = json.loads((ROOT/'work/v13/command-effect-review.json').read_text())['retained']
    command = next(row for row in actions if row['id'] == '0x8043')
    assert command['effect'] == 'Toggle God Mode.'
    registration = next(row for row in registrations if row['id'] == command['id'])
    code = 'MPKFA'
    assert bytes((ord(c) + 0x11) & 255 for c in code).hex() == registration['key_hex']
    return code


def main():
    result = {'check':'v13-enemy-death-sound-play', 'status':'fail', 'errors':[]}
    out = OUT/'run'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    derived = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT/'work/MacCatalyst'))
    session = CombatSession(out, fast=True, helper=build_helper(ROOT/'work/cheat-codes/post-window-input'))
    marks = []

    def read(name):
        try:
            return json.loads((out/name).read_text())
        except (OSError, ValueError):
            return {}

    def healthy():
        assert not session.failed(), read('real-speed.json').get('error', 'frame failed')

    def hold(keys, seconds):
        for key in keys:
            session.post('press', key, 'down')
        session.sleep(seconds)
        healthy()
        for key in reversed(keys):
            session.post('press', key, 'up')

    def code(text):
        for letter in text:
            session.post('key', KEYS[letter])

    def mark(label):
        entry = session.mark(label)
        assert entry, f'missing mark {label}'
        healthy()
        marks.append(entry)
        return entry

    try:
        god = reviewed_god_code()
        session.launch(derived/'Build/Products/Release-maccatalyst/Claw.app', {},
                       ['--save-dir',str(out/'saves'),'--menu-live-check',str(out),'-ClawCheckDirectory',str(out)])
        result['pid'] = session.pid
        session.sleep(1)
        for _ in range(3):
            session.post('key',36)
            session.sleep(1)
        assert session.wait(lambda: read('live.json').get('level') == 1,90), 'New Game not reached'
        for level in range(1,6):
            code('MPSCULLY')
            assert session.wait(lambda: read('live.json').get('state_vtable') == '0x50c0c4',90), 'results not reached'
            session.sleep(12)
            session.post('key',36)
            assert session.wait(lambda: read('live.json').get('level') == level+1 and read('live.json').get('state_vtable') == '0x50c264',90), 'next level not reached'
        code(god)
        start = mark('level-six-start')
        # Same opening route as enemy_direct, attacking before entering guard range.
        for keys, seconds in (([],1),([124],.5),([49,126],2),([126],4.5),([124,59],1.5)):
            hold(keys,seconds)
        mark('first-guard')
        # Sword and pistol requests use actual delivered events, alternating
        # short moves with stationary attacks to keep targets in reach.
        for index in range(20):
            hold([59], .7)
            hold([58], .3)
            if index in (1,3,5,7,9,11,13,15):
                hold([124,59], .25)
            current = mark(f'fight-{index:02d}')
            counts = current.get('invoke_counts',{})
            if counts.get('43f120',0) > start.get('invoke_counts',{}).get('43f120',0) and counts.get('4208e0',0) > start.get('invoke_counts',{}).get('4208e0',0)+1:
                break
        final = mark('combat-finished')
        before, after = start.get('invoke_counts',{}), final.get('invoke_counts',{})
        delta = {key:after.get(key,0)-before.get(key,0) for key in ('43f120','4208e0','4b45f0')}
        assert delta['43f120'] > 0, 'no live enemy death callback observed'
        assert delta['4208e0'] > 1, 'repeated non-positional sound requests not observed'
        assert final.get('player',{}).get('level') == 6, 'fight left Level 6'
        assert final.get('player',{}).get('health',0) > 0, 'player not alive at final mark'
        transitions = session.transitions()
        assert transitions.get('17:down',0) > 0 and transitions.get('18:down',0) > 0, 'attack input delivery missing'
        result.update(status='pass', invoke_count_delta=delta, input=session.input_state(),
                      start_player=start.get('player'), final_player=final.get('player'), marks=len(marks),
                      assistance='Reviewed retained MPKFA God Mode; MPSCULLY used only for level progression.',
                      limitations=['Live callback counts prove enemy deaths and repeated requests; exact state bits and interval boundaries are checked offline.'])
    except Exception as error:
        result['errors'].append(str(error))
        result.update(live=read('live.json'), state=read('live-state.json'), runtime=read('real-speed.json'), marks=marks)
    finally:
        session.close()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('marks','state','runtime','live','input','start_player','final_player')}))
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
