"""Native CONFIGCONTROLS: both entries, actual keyboard edits, CLAW.USR relaunch, Defaults.

Uses confirmed window-server input to its own muted Release app. The original
CONFIGCONTROLS resource exposes nine actions; 430d80 supplies defaults, 430ac0
loads player +25d4..25f8 into the unchanged poller, and 42ed20 saves CLAW.USR.
Duplicate keys are legal in the original's independent combo boxes.
"""
import argparse
import json
import os
import shutil
from pathlib import Path
from real_input import Session, build_helper, real_time_requested

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/menu-controls/check'
DEFAULTS = [32, 17, 18, 16, 90, 49, 50, 51, 52]
MAC = {'up':126, 'down':125, 'ret':36, 'esc':53, 'x':7, 'c':8, 'ctrl':59, 'right':124}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=os.environ.get('CLAW_CONFIG', 'Release'))
    parser.add_argument('--real-time', action='store_true')
    args = parser.parse_args()
    helper = build_helper(ROOT / 'work/menu-controls/post-window-input')
    app = ROOT / f'{os.environ.get("CLAW_DERIVED_DATA", "work/MacCatalyst")}/Build/Products/{args.config}-maccatalyst/Claw.app'
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    result = dict(check='menu-controls', status='fail', steps=[], errors=[])
    session = None
    def live():
        try: return json.loads((session.out / 'live.json').read_text())
        except (OSError, ValueError): return {}
    def controls(): return live().get('controls', {})
    def require(value, message):
        if not value: raise RuntimeError(message + ': ' + json.dumps({k:live().get(k) for k in ('frame','state_vtable','menu_page','menu_selected','controls','weapons','input_mask')}))
    def tap(name, count=1):
        for _ in range(count):
            # Native dialog/page changes can cancel the initiating UIKit press.
            # Confirm the real down and the state assertions below; still post
            # its physical release without requiring a pressesEnded callback
            # for an already cancelled press. Gameplay holds use post directly.
            session.post('press', MAC[name], 'down'); session.sleep(.06)
            session._post(('press', MAC[name], 'up')); session.sleep(.2)
    def mark(name):
        session.mark(name)
        if controls().get('open'):
            require((session.out/(name+'-dialog.png')).exists(), 'native dialog view capture missing')
        result['steps'].append(dict(name=name, controls=controls(), player={k:live().get(k) for k in ('input_mask','player_state','logic_state','x','y')}, attack=live().get('weapons'), state=live().get('state_vtable')))
    def start(name):
        nonlocal session
        out = WORK / name; out.mkdir()
        session = Session(out, fast=not real_time_requested(args.real_time), helper=helper)
        session.launch(app, {}, ['--save-dir',str(WORK/'saves'),'--settings-dir',str(WORK/'settings'),'-ClawCheckDirectory',str(out)])
        session.sleep(3)
        require(not session.failed(), 'startup fault')
    def main_controls():
        # Main: Single Player -> Quit -> Help -> Credits -> Options.
        tap('up',4);tap('ret');tap('down');tap('ret')
        require(controls().get('open'), 'main Controls did not open')
        mark('main-controls')
    def choose_attack(key):
        tap('down');tap('ret');tap(key)
        require(controls().get('draft',[])[1] == {'x':88,'c':67}[key], 'new attack key not captured')
    def save():
        # Hand Attack row -> Jump row -> Save.
        tap('up',2);tap('ret')
        require(not controls().get('open'), 'Controls Save did not close')
    def level():
        tap('esc') # Options -> main, with Options selected.
        for _ in range(10):
            if live().get('menu_selected') == 10001: break
            tap('down')
        require(live().get('menu_selected') == 10001, 'Single Player not selectable')
        tap('ret');tap('ret');tap('ret')
        require(session.wait(lambda: live().get('state_vtable') == '0x50c264' and live().get('game_ms',0)>3000,90), 'Level 1 did not start')
        # Finish Claw's startup animation before testing an attack edge.
        session.sleep(.5)
    def ingame_controls():
        tap('esc');tap('down',2);tap('ret');tap('ret')
        require(controls().get('open'), 'in-game Controls did not open')
        mark('ingame-controls')
        before = live().get('game_ms');session.sleep(.5)
        require(live().get('game_ms') == before, 'gameplay advanced behind the Controls dialog')
    def attack(key, name, moving=False):
        idle = live()
        if moving:
            session.post('press',MAC['right'],'down');session.sleep(.15)
        session.post('press',MAC[key],'down');session.sleep(.1)
        during = live()
        mark(name)
        session.post('press',MAC[key],'up')
        if moving: session.post('press',MAC['right'],'up')
        session.sleep(.8)
        require(during.get('input_mask',0)&2, name+' did not reach original attack poller')
        attack = during.get('weapons', {})
        require(attack.get('attack_active') == 1 and attack.get('attack_code') in (1,3,4,13), name+' did not start a hand attack')
        require(attack.get('attack_sequence',0) > idle.get('weapons',{}).get('attack_sequence',0), name+' did not advance the attack sequence')
        if moving: require(during.get('input_mask',0)&0x2000000, 'right arrow lost during rebound attack')
        return during
    try:
        start('first');main_controls()
        require(controls().get('keys') == DEFAULTS, 'initial default bindings')
        choose_attack('x')
        tap('ret');tap('esc')
        require(controls().get('open') and not controls().get('capturing') and controls().get('draft')[1] == 88, 'Escape did not cancel key capture')
        tap('up');tap('ret');tap('x') # Two actions share X, permitted by the original.
        require(controls().get('draft',[])[:2] == [88,88], 'shared key was not retained')
        mark('shared-keys')
        tap('esc')
        require(not controls().get('open') and controls().get('keys') == DEFAULTS, 'Cancel changed live bindings')
        tap('ret');require(controls().get('open'), 'Controls could not reopen')
        choose_attack('x');save();mark('saved-x')
        require(controls().get('keys') == [32,88,*DEFAULTS[2:]], 'saved X missing')
        require((WORK/'saves/CLAW.USR').exists(), 'profile file missing')
        level();attack('x','x-attacks',moving=True)
        session.post('press',MAC['ctrl'],'down');session.sleep(.1)
        require(not (live().get('input_mask',0)&2), 'old Control still attacks after rebinding')
        session.post('press',MAC['ctrl'],'up');session.sleep(.2)
        ingame_controls();choose_attack('c');tap('esc')
        require(controls().get('keys')[1] == 88, 'in-game Cancel changed attack')
        tap('esc')
        if live().get('state_vtable') != '0x50c264': tap('esc')
        require(live().get('state_vtable') == '0x50c264', 'resume did not restore Level 1')
        session.close();session=None
        start('relaunch');main_controls()
        require(controls().get('keys') == [32,88,*DEFAULTS[2:]], 'X did not survive relaunch')
        tap('esc');level();attack('x','relaunch-x-attacks')
        ingame_controls()
        tap('up',3);tap('ret') # Jump -> Save -> Cancel -> Defaults.
        require(controls().get('draft') == DEFAULTS, 'Defaults did not restore all nine actions')
        tap('down',2);tap('ret') # Defaults -> Cancel -> Save.
        require(not controls().get('open') and controls().get('keys') == DEFAULTS, 'Defaults save failed')
        tap('esc')
        if live().get('state_vtable') != '0x50c264': tap('esc')
        attack('ctrl','default-control-attacks')
        session.post('press',MAC['x'],'down');session.sleep(.1)
        require(not (live().get('input_mask',0)&2), 'old X still attacks after Defaults')
        session.post('press',MAC['x'],'up')
        session.close();session=None
        start('defaults-relaunch');main_controls()
        require(controls().get('keys') == DEFAULTS, 'Defaults did not persist')
        tap('esc');result['status']='pass'
    except Exception as error:
        result['errors'].append(str(error))
    finally:
        if session: session.close()
    (WORK/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['status']=='pass' else 1

if __name__ == '__main__': raise SystemExit(main())
