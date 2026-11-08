"""Compare the native Level 2 boss route with its hash-verified original trace.

--reuse reads retained app evidence. --fight-only is diagnostic and never claims
acceptance. Normal mode requires combat, boss defeat, results and Level 3.
--original-only validates the original route without launching or reading the app.
"""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import read_trace, stored_path

WORK = ROOT/'work/level-two-boss'
OUT = WORK/'run'
BOSS_FIELDS = ('live', 'active', 'x', 'y', 'health', 'actor_flags', 'logic_state', 'vtable',
               'animation_id', 'callback', 'action_phase', 'mode', 'facing')


def screens(trace, frame):
    start, count = frame.get('presentation_start', 0), frame.get('presentation_count', 0)
    return [[p['pixels_sha256'][:16], p['palette_sha256'][:16]]
            for p in trace['presentations'][start:start+count]]


def compact_original(path):
    source = stored_path(path).resolve()
    stat = source.stat()
    identity = dict(source=str(source), mtime_ns=stat.st_mtime_ns, size=stat.st_size,
                    paper=os.environ.get('PAPER') == '1',
                    checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    cache = OUT.parent/'original-boss.json'
    if cache.exists():
        try:
            cached = json.loads(cache.read_text())
            if cached.get('identity') == identity:
                return cached['data']
        except (OSError, ValueError, KeyError):
            pass
    trace = read_trace(path)
    if trace.get('status') != 'pass':
        raise ValueError('Original boss trace is not a passing run')
    if os.environ.get('PAPER') == '1':
        queries = trace.get('startup_queries', {})
        objects = trace.get('startup_objects') or {}
        bindings = {e.get('binding') for e in trace.get('startup_context', [])}
        if (trace.get('startup_profile') != dict(paper=True, query_ms=1)
                or not queries.get('count')
                or queries.get('increments') != {'1': queries['count']}
                or any(objects.get(hex(o), '0x0') == '0x0' for o in (0x44, 0x58))
                or not {'application+0x44', 'application+0x58'} <= bindings):
            raise ValueError('Paper comparison requires original paper startup and 1 ms initialization queries')
    validation = None if trace['fight_only'] else original_report(trace)
    if validation is not None and not validation['accepted']:
        raise ValueError('Original route acceptance: '+ '; '.join(validation['errors']))
    fights = trace['boss_frames']
    for frame in fights[1:]:
        frame['screens'] = screens(trace, frame)
    third = trace['level_three_frames']
    for frame in third:
        frame['screens'] = screens(trace, frame)
    data = dict(plan=trace['level_two_plan'], fight_only=trace['fight_only'],
                end_on_boss_defeat=trace.get('end_on_boss_defeat', False),
                defeat_endpoint=trace.get('boss_defeat_endpoint'),
                one=trace['play_frames'], two=fights, three=third,
                states=trace['state_transitions'], keys=trace['key_deliveries'],
                posted=[hex(e['wparam']) for e in trace['physical_events']
                        if e.get('service') == 'PostMessageA'],
                functions=trace['boss_route_functions'], validation=validation,
                startup_profile=trace.get('startup_profile'),
                startup_queries=trace.get('startup_queries'),
                startup_objects=trace.get('startup_objects'),
                parent_checkpoint=trace.get('parent_checkpoint'))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(identity=identity, data=data)))
    return data


def signed(value):
    return value-0x100000000 if value >= 0x80000000 else value


def coverage(frames):
    living = [(i, f['boss']) for i, f in enumerate(frames)
              if f.get('boss', {}).get('live') and 'health' in f['boss']]
    positive = [(i, b) for i, b in living if signed(b['health']) > 0]
    damage = any(i < j and signed(b['health']) < signed(a['health'])
                 for (i, a), (j, b) in zip(living, living[1:]) if signed(a['health']) > 0)
    defeat = bool(positive) and any(i > positive[0][0] and signed(b['health']) <= 0 for i, b in living)
    transitions = {(b.get("animation_id"), b.get("logic_state")) for _, b in living}
    callbacks = {b.get('callback') for _, b in living} - {None, '0x0'}
    player_damage = any(0 < signed(a['player']['health']) and
                        signed(b['player']['health']) < signed(a['player']['health'])
                        for a, b in zip(frames, frames[1:]))
    return dict(boss_active=bool(positive), boss_takes_damage=damage, boss_defeated=defeat,
                boss_attacks=len(transitions) > 1 and player_damage,
                animation_logic_transitions=max(0, len(transitions)-1),
                callback_changes=max(0, len(callbacks)-1), player_damage=player_damage)


def original_report(trace):
    """Judge only original observations; boss_route_functions is fight-local."""
    report = dict(check='level-two-boss-original', status='fail', accepted=False,
                  scope='Original route only; no native comparison or family admission', errors=[])
    errors = report['errors']
    report['stop'] = trace.get('stop')
    if trace.get('status') != 'pass':
        errors.append('Original boss trace is not a passing run')
    if report['stop'] is not None:
        errors.append('Original boss trace has a non-null stop')
    if trace.get('fight_only') is not False:
        errors.append('Original trace is not a full route (fight_only must be false)')
    frames = trace['boss_frames']
    cov = coverage(frames)
    report['coverage'] = cov
    health = [dict(elapsed_ms=f['elapsed_ms'], health=signed(f['boss']['health']))
              for f in frames if f.get('boss', {}).get('live') and 'health' in f['boss']]
    report['boss_health'] = dict(minimum=min((h['health'] for h in health), default=None),
                               final=health[-1]['health'] if health else None,
                               first_positive=next((h for h in health if h['health'] > 0), None),
                               first_defeated=next((h for h in health if h['health'] <= 0), None))
    def damage_events(actor):
        events = []
        for a, b in zip(frames, frames[1:]):
            if actor == 'boss' and not (a.get(actor, {}).get('live') and b.get(actor, {}).get('live')):
                continue
            old, new = a.get(actor, {}).get('health'), b.get(actor, {}).get('health')
            if old is not None and new is not None and 0 < signed(old) and signed(new) < signed(old):
                events.append(dict(elapsed_ms=b['elapsed_ms'], before=signed(old), after=signed(new)))
        return events
    report['damage_events'] = {actor: damage_events(actor) for actor in ('boss', 'player')}
    for key in ('boss_active', 'boss_takes_damage', 'boss_defeated', 'boss_attacks'):
        if not cov[key]:
            errors.append('Original route lacks '+key)
    plan = trace['level_two_plan']
    assistance = [a['start_ms'] for a in plan if a.get('cheat') == 'MPKFA']
    report['assisted_route'] = bool(assistance)
    if not assistance:
        errors.append('Original route lacks required MPKFA assistance')
    if assistance:
        start = min(assistance)
        prior = coverage([f for f in frames if f['elapsed_ms'] <= start])
        report['assistance_start_ms'] = start
        report['coverage_before_assistance'] = prior
        report['mutual_damage_before_assistance'] = prior['boss_takes_damage'] and prior['player_damage']
        if not report['mutual_damage_before_assistance']:
            errors.append('Original route lacks observed mutual damage before MPKFA')
        delivered = [k for k in trace['key_deliveries'] if k['phase'].startswith('boss-cheat-')]
        report['assistance_key_deliveries'] = delivered
        report['damage_before_assistance'] = {
            actor: [e for e in events if e['elapsed_ms'] <= start]
            for actor, events in report['damage_events'].items()}
        if [k['key'] for k in delivered[:5]] != [ord(c) for c in 'MPKFA']:
            errors.append('Original MPKFA assistance lacks complete physical key delivery')
    functions = trace['boss_route_functions']
    report['original_boss_functions'] = functions
    for address in ('0x44e0c0', '0x491fa0'):
        if functions.get(address, 0) <= 0:
            errors.append('Original fight lacks '+address+' execution')
    attack_entries = ('0x47f160', '0x47f290', '0x44e620', '0x455350', '0x47f600')
    if not any(functions.get(a, 0) > 0 for a in attack_entries):
        errors.append('Original route lacks observed Raux combat function execution')
    keys = trace['key_deliveries']
    completion = [k for k in keys if k['phase'].startswith('level-two-complete-key-')]
    expected_phases = [f'level-two-complete-key-{i}-{c}' for i, c in enumerate('MPSCULLY')]
    complete = ([k['phase'] for k in completion] == expected_phases and
                [k['key'] for k in completion] == [ord(c) for c in 'MPSCULLY'])
    posts = [e for e in trace['physical_events'] if e.get('service') == 'PostMessageA' and
             e.get('message') == 0x111 and e.get('wparam') == 0x800e]
    report['level_two_completion_keys'] = completion
    report['level_complete_posted_commands'] = posts
    report['level_two_mpscully_completion'] = complete and trace.get('level_complete_posted') is True and len(posts) >= 2
    if not report['level_two_mpscully_completion']:
        errors.append('Original lacks Level 2 MPSCULLY keys and posted completion after Level 1')
    returns = [k for k in keys if k['key'] == 13 and k.get('scan') == 0x1c and
               k['phase'].startswith('level-two-results-return-')]
    report['level_two_results_return_deliveries'] = len(returns)
    report['level_two_results_return_keys'] = returns
    if not returns or (completion and returns[0]['milliseconds'] < completion[-1]['milliseconds']):
        errors.append('Original lacks Level 2 results Return delivery after completion')
    levels = [s.get('level') for s in trace['state_transitions'] if s.get('level') is not None]
    report['state_levels'] = levels
    cursor = iter(levels)
    full_prefix = all(any(observed == level for observed in cursor) for level in (1, 2, 3))
    if not trace['play_frames'] or not full_prefix:
        errors.append('Original full route lacks Level 1, Level 2 and Level 3 progression')
    progression = iter((s['vtable'], s.get('level')) for s in trace['state_transitions'])
    expected = [('0x50c264', 1), ('0x50c0c4', None), ('0x50c264', 2),
                ('0x50c0c4', None), ('0x50c264', 3)]
    if not all(any(state == wanted for state in progression) for wanted in expected):
        errors.append('Original route lacks both results states between Levels 1, 2 and 3')
    third = trace['level_three_frames']
    report['frames'] = dict(level_one=len(trace['play_frames']), boss=len(frames), level_three=len(third))
    if len(third) < 10 or any(f['player'].get('level') != 3 for f in third):
        errors.append('Original full route lacks ten Level 3 standing frames')
    report['defeat_endpoint'] = trace.get('boss_defeat_endpoint')
    report['status'] = 'fail' if errors else 'pass'
    report['accepted'] = not errors
    return report


def check_original(path):
    try:
        report = original_report(read_trace(path))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        report = dict(check='level-two-boss-original', status='fail', accepted=False, errors=[str(error)])
    report['evidence'] = str(stored_path(path).resolve())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent/'original-result.json').write_text(json.dumps(report, indent=1))
    print(json.dumps(report))
    return 0 if report['accepted'] else 1


def uninitialized_intro_facing(reference, index):
    """Only the first live Raux snapshot precedes the facing initializer.

    Original allocator poison is not game state: the Raux/base constructors
    leave +0x18c untouched. The next update's 0x47ece0 -> 0x44d000 -> 0x43e420
    chain reaches stores at 0x43e43d/0x43e45c that establish facing 2/3.
    Require that exact observed boundary;
    never treat poison in another field or a later combat frame as a wildcard.
    """
    if index != 2 or len(reference) <= index+1:
        return False
    boss = reference[index].get('boss', {})
    next_boss = reference[index+1].get('boss', {})
    return (not any(f.get('boss', {}).get('live') for f in reference[:index]) and
            reference[index].get('action') == 'boss-intro' and
            reference[index].get('elapsed_ms') == 34 and boss.get('live') is True and
            boss.get('vtable') == '0x50f1ac' and boss.get('facing') == 0xa5a5a5a5 and
            boss.get('mode') == 6 and boss.get('logic_state') == 2028 and
            reference[index+1].get('elapsed_ms') == 51 and next_boss.get('facing') == 3)


def compare_frames(reference, actual, fields, label, errors):
    if len(reference) != len(actual):
        errors.append(f'{label} frame count: original {len(reference)}, app {len(actual)}')
    for index, (a, b) in enumerate(zip(reference, actual)):
        differences = {}
        for key in ('elapsed_ms', 'action', 'index'):
            if key in a and a.get(key) != b.get(key):
                differences[key] = [a.get(key), b.get(key)]
        for key in fields:
            if a.get('player', {}).get(key) != b.get('player', {}).get(key):
                differences['player.'+key] = [a.get('player', {}).get(key), b.get('player', {}).get(key)]
        if 'boss' in a:
            for key in BOSS_FIELDS:
                if (key == 'facing' and uninitialized_intro_facing(reference, index) and
                        b.get('boss', {}).get('facing') == 0):
                    continue
                if a['boss'].get(key) != b.get('boss', {}).get(key):
                    differences['boss.'+key] = [a['boss'].get(key), b.get('boss', {}).get(key)]
        if 'screens' in a and a['screens'] != b.get('screens', []):
            differences['screens'] = [a['screens'], b.get('screens', [])]
        if differences:
            errors.append(f'{label} first divergence at frame {index}: {differences}')
            break


def run_app(plan, fight_only, end_on_boss_defeat=False):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ('app-menu.json', 'live-state.json', 'level-two-route.json'):
        (OUT/name).unlink(missing_ok=True)
    route = OUT.parent/'app-plan.json'
    route.write_text(json.dumps(plan))
    command = [str(ROOT/'work/new-game/launch.sh'), str(OUT), '900', '--menu-check', str(OUT),
               '--menu-input-script', str(ROOT/'work/new-game/play-events.json'), '--menu-frames', '9000',
               '--menu-live-check', str(OUT), '--new-game-clock', '--level-two-route', str(route),
               '--level-two-boss']
    if end_on_boss_defeat:
        command.append('--boss-end-on-defeat')
    if fight_only:
        command.append('--boss-fight-only')
    subprocess.run(command, check=True, env=dict(os.environ), cwd=ROOT, timeout=1000)


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--fight-only', action='store_true')
    parser.add_argument('--original-only', action='store_true')
    parser.add_argument('--trace', type=Path, default=WORK/'trace.json')
    parser.add_argument('--output', type=Path, default=OUT,
                        help='App evidence directory; staged comparisons leave retained evidence intact')
    args = parser.parse_args()
    OUT = args.output.resolve()
    if not OUT.is_relative_to((ROOT/'work').resolve()):
        parser.error('App evidence must stay under work/')
    if args.original_only:
        if args.reuse or args.fight_only:
            parser.error('--original-only cannot be combined with --reuse or --fight-only')
        return check_original(args.trace)
    spec = importlib.util.spec_from_file_location('level_two_play_check', ROOT/'scripts/check-level-two-play.py')
    play = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(play)
    report = dict(check='level-two-boss', status='fail', accepted=False,
                  diagnostic=args.fight_only, reused=args.reuse,
                  reference=str(stored_path(args.trace).resolve()),
                  paper=os.environ.get('PAPER') == '1',
                  config=os.environ.get('CLAW_CONFIG', 'Release'),
                  evidence=str(OUT.relative_to(ROOT)), errors=[])
    errors = report['errors']
    try:
        reference = compact_original(args.trace)
        report['startup_profile'] = reference['startup_profile']
        report['startup_queries'] = reference['startup_queries']
        report['startup_objects'] = reference['startup_objects']
        report['parent_checkpoint'] = reference['parent_checkpoint']
        if reference['fight_only'] != args.fight_only:
            raise ValueError('Trace fight-only mode does not match checker mode')
        if not args.reuse:
            run_app(reference['plan'], args.fight_only, reference['end_on_boss_defeat'])
        app = json.loads((OUT/'level-two-route.json').read_text())
        if app.get('status') != 'pass':
            errors.append(f"App route status: {app.get('status')}")
        compare_frames(reference['one'], app.get('level_one_frames', []), play.FIELDS, 'Level 1', errors)
        actual = app.get('level_two_frames', [])
        assisted = any(a.get('cheat') == 'MPKFA' for a in reference['plan'])
        report['assisted_route'] = assisted
        if assisted:
            assistance_start = min(a['start_ms'] for a in reference['plan'] if a.get('cheat') == 'MPKFA')
            prior = [f for f in reference['two'] if f['elapsed_ms'] <= assistance_start]
            prior_coverage = coverage(prior)
            mutual_before_assistance = prior_coverage['boss_takes_damage'] and prior_coverage['player_damage']
            report['mutual_damage_before_assistance'] = mutual_before_assistance
            report['assistance_note'] = 'Original built-in MPKFA assists the route; MPSCULLY finishes Level 2.'
            if not args.fight_only and not mutual_before_assistance:
                errors.append('Assisted route lacks observed mutual damage before MPKFA')
        # Raux 0x47f160 dispatches combat; 0x47f290 and 0x44e620 are
        # attack bodies. Callback +0x14 can remain zero across sampled frames.
        attack_entries = ('0x47f160', '0x47f290', '0x44e620', '0x455350', '0x47f600')
        report['original_attack_entries'] = {a: reference['functions'].get(a, 0) for a in attack_entries}
        if not args.fight_only and not any(report['original_attack_entries'].values()):
            errors.append('Original route lacks observed Raux combat function execution')
        compare_frames(reference['two'], actual, play.FIELDS, 'Boss fight', errors)
        compare_frames(reference['three'], app.get('level_three_frames', []), play.FIELDS, 'Level 3', errors)
        shape = lambda states: [(s['vtable'], s.get('level')) for s in states]
        if shape(reference['states']) != shape(app.get('state_transitions', [])):
            errors.append('State transition vtables/levels differ')
        def key_shape(keys):
            if not keys:
                return []
            start = keys[0]['milliseconds']
            return [(k['key'], k['scan'], k['target'], k['phase'], k['vtable'],
                     k['milliseconds']-start) for k in keys]
        if key_shape(reference['keys']) != key_shape(app.get('key_deliveries', [])):
            errors.append('Physical cheat/Return deliveries differ')
        def completion_tail(commands):
            return commands[commands.index('0x800e'):] if '0x800e' in commands else []
        if completion_tail(reference['posted']) != completion_tail(app.get('posted_commands', [])):
            errors.append('Posted commands after Level 1 completion differ')
        count = app.get('transports', {}).get('boss-base-direct', 0)
        report['boss_base_direct'] = count
        if count <= 0:
            errors.append('boss-base-direct transport was not exercised')
        report['coverage'] = dict(original=coverage(reference['two']), app=coverage(actual))
        report['frames'] = dict(original=len(reference['two']), app=len(actual),
                                level_three=len(app.get('level_three_frames', [])))
        # The renderer census establishes execution; exact screen parity at
        # positive health and each health reduction establishes visual evidence.
        reference_frames = reference['two']
        positive_frames = [i for i, f in enumerate(reference_frames)
                           if f.get('boss', {}).get('live') and
                           signed(f['boss'].get('health', 0)) > 0 and f.get('screens')]
        damage_frames = [i for i in range(1, len(reference_frames))
                         if reference_frames[i-1].get('boss', {}).get('live') and
                         reference_frames[i].get('boss', {}).get('live') and
                         signed(reference_frames[i-1]['boss'].get('health', 0)) > 0 and
                         signed(reference_frames[i]['boss'].get('health', 0)) <
                         signed(reference_frames[i-1]['boss'].get('health', 0))]
        def screen_matches(index):
            return (index < len(actual) and bool(reference_frames[index].get('screens')) and
                    reference_frames[index]['screens'] == actual[index].get('screens', []) and
                    reference_frames[index]['boss'].get('health') == actual[index].get('boss', {}).get('health'))
        renderer_count = reference['functions'].get('0x491fa0', 0)
        report['health_bar_visual'] = dict(renderer='0x491fa0', original_renderer_calls=renderer_count,
            positive_health_presented_frames=len(positive_frames),
            positive_health_matching_frames=sum(screen_matches(i) for i in positive_frames),
            health_reduction_frames=damage_frames,
            matching_health_reduction_frames=[i for i in damage_frames if screen_matches(i)])
        report['health_bar_visual_reference'] = (renderer_count > 0 and bool(positive_frames) and
            all(screen_matches(i) for i in positive_frames) and bool(damage_frames) and
            all(screen_matches(i) for i in damage_frames))
        if not args.fight_only:
            for side, cov in report['coverage'].items():
                for key in ('boss_active', 'boss_takes_damage', 'boss_defeated', 'boss_attacks'):
                    if not cov[key]:
                        errors.append(f'{side} route lacks {key}')
            if (len(reference['three']) < 10 or len(app.get('level_three_frames', [])) < 10 or
                    any(f['player'].get('level') != 3 for f in app.get('level_three_frames', []))):
                errors.append('Full route lacks ten Level 3 standing frames after results')
            for side, keys in [('original', reference['keys']), ('app', app.get('key_deliveries', []))]:
                if not any(k['key'] == 13 and 'level-two-results' in k['phase'] for k in keys):
                    errors.append(f'{side} lacks Level 2 results Return delivery')
            if not report['health_bar_visual_reference']:
                errors.append('Health bar lacks original renderer execution or matching presented screens at positive health and every health reduction')
        report['original_boss_functions'] = reference['functions']
        report['original_route_validation'] = reference['validation']
        report['uninitialized_intro_facing_frames'] = [
            i for i in range(len(reference['two'])) if uninitialized_intro_facing(reference['two'], i)]
        report['defeat_endpoint'] = reference['defeat_endpoint']
        if reference['end_on_boss_defeat'] and reference['functions'].get('0x44e0c0', 0) <= 0:
            errors.append('End-on-defeat reference lacks original death callback 0x44e0c0 execution')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        errors.append(str(error))
    report['status'] = 'fail' if errors else ('diagnostic-pass' if args.fight_only else 'pass')
    report['accepted'] = not errors and not args.fight_only
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent/('fight-result.json' if args.fight_only else 'result.json')).write_text(json.dumps(report, indent=1))
    print(json.dumps(report))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
