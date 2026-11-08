"""Compare the bounded Level 1 combat/HUD route with the hash-pinned original.

First generate the original:
  work/test-env/bin/python -m Tests.NativeLevelOne.combat_trace --plan Tests/NativeLevelOne/combat-plan.json --output work/hud-combat/original.json --checkpoint work/hud-combat/start.pkl
Then build Release through scripts/run-mac.sh and run this check. --reuse reads
retained app evidence. Synthetic ammo and last-timer setup are explicit in the
plan; no full-duration, physical-keyboard or whole-game claim is made.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'work/hud-combat'
PLAN = ROOT/'Tests/NativeLevelOne/combat-plan.json'
FIELDS = ('x','y','health','score','player_state','logic_state','treasure_counts',
          'input_mask','game_ms','level','vtable','ammo','lives','lives_lost','combat')


def validate_coverage(frames):
    errors, variants, powers = [], {}, {}
    for empty in (False, True):
        for wi, weapon in enumerate(('pistol','magic','dynamite')):
            for posture in ('stand','duck','air'):
                name = f'{weapon}-{posture}-'+('empty' if empty else 'loaded')
                selected = [f for f in frames if f['action'] == name+'-select']
                fired = [f for f in frames if f['action'] in (name+'-fire',name+'-release')]
                if not selected or not fired:
                    errors.append(name+': missing frames'); continue
                start, end = selected[-1]['player'], fired[-1]['player']
                spent = start['ammo'][wi]-end['ammo'][wi]
                sequences = sorted({f['player']['combat']['image_id'] for f in fired})
                variants[name] = dict(weapon=start['combat']['weapon'], spent=spent, image_ids=sequences,
                                      frames=len(fired))
                if start['combat']['weapon'] != wi+1 or (spent != 0 if empty else spent <= 0):
                    errors.append(f'{name}: selected weapon or ammo transition not exercised ({variants[name]})')
                firing = [f['player'] for f in frames if f['action']==name+'-fire']
                if posture == 'duck' and not any(f['logic_state']==26 and f['combat']['attack'] for f in firing):
                    errors.append(name+': duck attack state not observed')
                if posture == 'air' and not any(f['player']['y'] < selected[-1]['player']['y'] for f in fired):
                    errors.append(name+': airborne position not observed')
    for name in ('ghost','invulnerable','ice','fire','lightning'):
        active = [f for f in frames if f['action'] == name+'-active']
        expiry = [f for f in frames if f['action'] in (name+'-expiry',name+'-expired')]
        kinds = sorted({f['player']['combat']['power_kind'] for f in active})
        timers = [f['player']['combat']['power_ms'] for f in expiry]
        powers[name] = dict(kinds=kinds, timer_tail=timers)
        if not active or not expiry or not all(kinds) or not any(v>0 for v in timers) or timers[-1] != 0:
            errors.append(name+': active-to-expired timer boundary not observed')
    carried = [f for f in frames if f['action'] in ('lift','carry')]
    thrown = [f for f in frames if f['action'] == 'throw-release']
    if not any(f['player']['combat']['carrying'] for f in carried): errors.append('Lift/carry was not exercised')
    if not thrown or thrown[-1]['player']['combat']['carrying']: errors.append('Throw release was not exercised')
    melee_before = [f['player']['combat'].get('target_health') for f in frames if f['action']=='melee-approach']
    melee_after = [f['player']['combat'].get('target_health') for f in frames if f['action'] in ('melee','melee-release')]
    signed = lambda v: v if v < 0x80000000 else v-0x100000000
    if not melee_before or not melee_after or None in melee_before+melee_after or min(map(signed,melee_after)) >= signed(melee_before[0]):
        errors.append('Melee target damage was not exercised')
    target = [f['player']['combat'] for f in frames]
    retired = [i for i, c in enumerate(target) if c.get('target_live') == 0]
    if not retired or retired[0] == 0:
        errors.append('Officer live-to-retired transition was not exercised')
    else:
        boundary = retired[0]
        if any(c.get('target_live') != int(i < boundary) for i, c in enumerate(target)):
            errors.append('Officer allocation was missing or reacquired')
        if not all(all(k in c for k in ('target_health','target_x','target_y','target_state')) for c in target[:boundary]):
            errors.append('Live officer fields missing')
        if any(any(k in c for k in ('target_health','target_x','target_y','target_state')) for c in target[boundary:]):
            errors.append('Retired officer storage was probed')
        if signed(target[boundary-1].get('target_health', 1)) > 0:
            errors.append('Officer death before retirement was not observed')
    # Original million-point score reward adds a life to the seeded two.
    for name, expected in [('hud-low',(7,3,1234567)),('hud-high',(99,12,99999999))]:
        rows = [f['player'] for f in frames if f['action']==name]
        if not rows or tuple(rows[-1][key] for key in ('health','lives','score')) != expected:
            errors.append(name+': HUD value setup not observed')
    return errors, variants, powers


def target_events(frames):
    events, previous = [], None
    for i, frame in enumerate(frames):
        combat = frame['player']['combat']
        state = {key: combat[key] for key in ('target_live','target_health','target_state') if key in combat}
        if state != previous:
            events.append(dict(frame=i, elapsed_ms=frame['elapsed_ms'], action=frame['action'], **state))
            previous = state
    return events


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reuse', action='store_true')
    args = ap.parse_args()
    ref = json.loads((WORK/'original.json').read_text())
    if ref['status'] != 'pass': raise SystemExit('Original route is blocked: '+str(ref.get('stop')))
    hashes = [('plan_sha256', PLAN), ('tracer_sha256', ROOT/'Tests/NativeLevelOne/combat_trace.py'),
              ('parent_sha256', ROOT/'Tests/NativeLevelOne/trace.py'), ('menu_sha256', ROOT/'Tests/NativeMenuBase/trace.py'),
              ('mirror_provider_sha256', ROOT/'Tests/NativeLevelTwo/trace.py')]
    for key, path in hashes:
        if ref[key] != hashlib.sha256(path.read_bytes()).hexdigest(): raise SystemExit('Stale original: '+str(path))
    out = WORK/'run'; out.mkdir(parents=True, exist_ok=True)
    if not args.reuse:
        for name in ('play-frames.json','app-menu.json'): (out/name).unlink(missing_ok=True)
        env = dict(os.environ, CLAW_COMBAT_HUD='1', CLAW_LIVES_BOSS_PROFILE='claw-v1.0')
        subprocess.run([str(ROOT/'work/new-game/launch.sh'),str(out),'300','--menu-check',str(out),
                        '--menu-input-script',str(ROOT/'work/new-game/play-events.json'),'--menu-frames','6000',
                        '--menu-live-check',str(out),'--new-game-clock','--play-script',str(PLAN)],
                       cwd=ROOT,env=env,check=True,timeout=330)
    result = dict(check='hud-combat',status='fail',errors=[],limitations=ref['limitations'])
    errors = result['errors']
    try:
        app = json.loads((out/'play-frames.json').read_text())
        assert app['status'] == 'pass', 'app route incomplete'
        original, actual = ref['frames'], app['play_frames']
        differences = []
        state_matches = screen_matches = 0
        assert original and actual, 'No captured frames'
        loading = original[0]['loading_screens']
        if not loading or loading != actual[0].get('loading_screens'):
            errors.append('New Game loading prefix differs')
        if original[0]['screens'] or actual[0].get('screens') != []:
            errors.append('Loaded boundary contains gameplay presentations')
        if any('loading_screens' in f for f in original[1:]+actual[1:]):
            errors.append('Loading presentations outside loaded boundary')
        for i,(a,b) in enumerate(zip(original, actual)):
            delta = {key:[a['player'].get(key),b['player'].get(key)] for key in FIELDS if a['player'].get(key)!=b['player'].get(key)}
            for key in ('elapsed_ms','action'):
                if a[key]!=b[key]: delta[key]=[a[key],b[key]]
            if not delta: state_matches += 1
            if i and a['screens'] == b.get('screens'): screen_matches += 1
            if i and a['screens'] != b.get('screens'): delta['screens']=[a['screens'],b.get('screens')]
            if delta and len(differences)<12: differences.append(dict(frame=i,action=a['action'],delta=delta))
        if differences: errors.append('Original/app divergence')
        if len(original)!=len(actual): errors.append('Frame count differs')
        coverage_errors, variants, powers = validate_coverage(original)
        errors.extend(coverage_errors)
        app_coverage_errors, _, _ = validate_coverage(actual)
        errors.extend('app: '+e for e in app_coverage_errors)
        result.update(loading_screens=len(loading), loading_prefix_matches=loading == actual[0].get('loading_screens'),
                      target_retirement_frame=next((i for i,f in enumerate(original) if not f['player']['combat']['target_live']), None),
                      original_target_events=target_events(original), app_target_events=target_events(actual),
                      original_frames=len(original),app_frames=len(actual),matched_state_frames=state_matches,
                      matched_presented_frames=screen_matches, differences=differences,variants=variants,powers=powers)
    except (OSError,ValueError,KeyError,AssertionError) as e:
        errors.append(str(e))
        if (out/'app-menu.json').exists():
            menu=json.loads((out/'app-menu.json').read_text());result['app_failure']=menu.get('error')
    result['status']='fail' if errors else 'pass'
    (WORK/'result.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(result))
    return 1 if errors else 0


if __name__ == '__main__': raise SystemExit(main())
