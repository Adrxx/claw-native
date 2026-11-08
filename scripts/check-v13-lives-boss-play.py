#!/usr/bin/env python3
"""Muted Release New Game, real controls and shipped boss initialization.

Uses MPSCULLY for level completion. Original comparisons and the offline
composition check separately cover score boundaries and projectile defaults.
"""
import json
import os
from pathlib import Path
import shutil

from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/v13-lives-boss-play'
KEYS = {'M': 46, 'P': 35, 'S': 1, 'C': 8, 'U': 32, 'L': 37, 'Y': 16}
BOSSES = {2: ('Raux', 5), 4: ('Katherine', 5), 6: ('Wolvington', 5),
          8: ('Gabriel', 10), 10: ('Marrow', 10), 12: ('Aquatis', 10),
          13: ('RedTail', 10), 14: ('Omar', 30)}


def main():
    out = OUT / 'run'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    result = {'check': 'v13-lives-boss-play', 'status': 'fail', 'errors': []}
    derived = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT / 'work/MacCatalyst'))
    session = Session(out, fast=True,
                      helper=build_helper(ROOT / 'work/cheat-codes/post-window-input'))
    marks = []

    def read(name):
        try:
            return json.loads((out / name).read_text())
        except (OSError, ValueError):
            return {}

    def mark(label):
        value = session.mark(label)
        assert value and not session.failed(), read('real-speed.json')
        marks.append(label)
        return value

    def hold(key, seconds):
        session.post('press', key, 'down')
        session.sleep(seconds)
        session.post('press', key, 'up')

    def playing(level):
        live = read('live.json')
        return live.get('level') == level and live.get('state_vtable') == '0x50c264'

    try:
        session.launch(derived / 'Build/Products/Release-maccatalyst/Claw.app',
                       {'CLAW_COMBAT_HUD': '1'},
                       ['--save-dir', str(out / 'saves'), '--menu-live-check', str(out),
                        '-ClawCheckDirectory', str(out), '--v13-boss-initialization-check'])
        result['pid'] = session.pid
        session.sleep(1)
        for _ in range(3):
            session.post('key', 36)
            session.sleep(1)
        assert session.wait(lambda: playing(1), 90), 'New Game not reached'
        start = mark('new-game')
        player = start['player']
        assert [player[k] for k in ('lives', 'spare_lives', 'health')] == [7, 6, 100], player
        assert player['ammo'] == [10, 5, 3], player
        assert player['inventory_extra_life_threshold'] == 500000, player
        assert start['hud_lives'] == [6], start.get('hud_lives')
        result['new_game'] = player

        hold(124, .25)
        moved = mark('move-right')
        assert moved['player']['x'] > player['x'], 'right control did not move Claw'
        session.post('press', 49, 'down')
        session.sleep(.15)
        jumped = mark('jump')
        session.post('press', 49, 'up')
        assert jumped['player']['y'] < moved['player']['y'], 'jump control did not lift Claw'
        session.sleep(1)
        session.post('press', 59, 'down')
        session.sleep(.15)
        sword = mark('sword')
        session.post('press', 59, 'up')
        # +0xe8 increments on attack start and survives animation completion;
        # the +4 active flag can already be cleared by the sampled frame.
        assert sword['player']['combat']['owner_tag'] > player['combat']['owner_tag'], 'sword did not start an attack'
        assert sword['player']['ammo'] == player['ammo'], 'sword consumed projectile ammo'
        session.sleep(.5)
        hold(58, .3)
        session.sleep(.3)
        attacks = mark('attacks')
        assert attacks['player']['ammo'][0] < player['ammo'][0], 'pistol did not consume ammo'
        assert attacks['invoke_counts'].get('40ff80', 0) > start['invoke_counts'].get('40ff80', 0), 'pistol callback absent'
        for key in (39, 32, 17, 18):
            assert session.transitions().get(f'{key}:down', 0), f'input {key} not delivered'
        result['controls'] = {'movement': moved['player'], 'jump': jumped['player'],
                              'sword': sword['player'], 'attacks': attacks['player']}

        observed = {}
        for level in range(1, 15):
            if level in BOSSES:
                name, damage = BOSSES[level]
                deferred = mark(f'level-{level}-{name.lower()}-before')
                actors = [actor for actor in deferred['boss_actors'] if actor['name'] == name]
                assert len(actors) == 1, (name, actors)
                if actors[0]['state'] == 0:
                    session._command(f"v13-boss-init {actors[0]['actor']}")
                    session._gate_wait()
                snapshot = mark(f'level-{level}-{name.lower()}')
                initialized = [actor for actor in snapshot['boss_actors'] if actor['name'] == name]
                assert len(initialized) == 1 and initialized[0]['state'] != 0, initialized
                actual = snapshot['boss_damage'].get(name)
                observed[name] = actual
            if level == 14:
                break
            for letter in 'MPSCULLY':
                session.post('key', KEYS[letter])
            assert session.wait(lambda: read('live.json').get('state_vtable') == '0x50c0c4', 90), f'Level {level} results absent'
            session.sleep(12)
            session.post('key', 36)
            assert session.wait(lambda: playing(level + 1), 90), f'Level {level + 1} not reached'
        result['bosses'] = observed
        assert observed == {name: {'damage': damage, 'health': 100} for name, damage in BOSSES.values()}, observed
        result.update(status='pass', bosses=observed, input=session.input_state(), marks=marks,
                      limitations=['Offscreen bosses use explicit registered-callback initialization fixtures; marks observe damage and health, not battle hits.',
                                   'Separate original gates and native composition checks cover projectiles, Easy Mode and score/save boundaries.'])
    except Exception as error:
        result['errors'].append(str(error))
        result.update(live=read('live.json'), runtime=read('real-speed.json'), marks=marks)
    finally:
        session.close()
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input', 'new_game', 'controls', 'live', 'runtime')}))
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
