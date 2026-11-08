"""Native-only end-of-level join over admitted canonical owners.

Run with work/test-env/bin/python -m Tests.NativeEndOfLevel.native_join [--controls].
The unchanged original route of Tests/NativeEndOfLevel/trace.py (New Game,
Level 1, the typed MPSCULLY level-complete command 0x800e, the results state
0x50c0c4, the state-stack pop 0x8036 and the original continuation into
Level 2, owner decision 2026-10-21) runs with every game entry compiled C++
elected from work/end-of-level-map/ownership.json. The native memory provider
has no instruction executor; physical services are the tracers' stand-ins.
The native record is compared with the retained original trace at every state
boundary. Derived output stays under work/native-end-of-level-join/.
"""
from __future__ import annotations
import argparse
from Tests.NativeLevels.storage import read_trace
import json
import time
from collections import Counter
from Tests.NativeMenuBase.trace import Blocked, ROOT
from Tests.NativeLevelOne import native_join as level_one
from Tests.NativeLevelOne.native_join import LevelOneNativeJoin, SEMANTIC
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace

WORK = ROOT/'work/native-end-of-level-join'
ORIGINAL = ROOT/'work/end-of-level-map/trace.json'
OWNERSHIP = ROOT/'work/end-of-level-map/ownership.json'
# Physical services whose order is a game decision on this route (posted
# commands, window input, the elected wall clock read by the save path).
ORDERED_SERVICES = ('PostMessageA', 'PeekMessageA', 'native window input drain', 'CTime GetCurrentTime', 'CTime GetLocalTm',
                    'CRT vector destructor iterator', 'CPtrList destructor', 'CPtrArray RemoveAt')


def build():
    return level_one.build(OWNERSHIP, WORK, 'native-end-of-level-join')


class EndOfLevelNativeJoin(LevelOneNativeJoin, EndOfLevelTrace):
    """Original end-of-level orchestration with every game entry native.

    Method order: native invocation and services from the Level 1 join, then
    the end-of-level route (play, cheat keys, results, Level 2) and its
    physical fixtures from the original tracer."""
    def __init__(self, library, entries, **options):
        LevelOneNativeJoin.__init__(self, library, entries, **options)

    def fixture(self, address):
        api = self.imports.get(address, (None, ''))[1].split('!')[-1]
        if api == 'SendMessageA':
            # The original route sends no synchronous window command; a native
            # transport for it is not elected.
            raise Blocked('Unelected native SendMessageA command delivery')
        return EndOfLevelTrace.fixture(self, address)


def records(trace):
    """Address-free semantic record of one run (original report or native probe)."""
    get = (lambda k: trace.get(k)) if isinstance(trace, dict) else (lambda k: getattr(trace, k))
    presentations = get('presentations')
    objects = {}
    states = []
    for s in get('state_transitions'):
        objects.setdefault(s['object'], len(objects))
        states.append(dict(label=s['label'], milliseconds=s['milliseconds'], vtable=s['vtable'],
                           level=s.get('level'), menu_id=s.get('menu_id'), identity=objects[s['object']]))
    phases = get('phases') if isinstance(trace, dict) else get('phase_results')
    start = next(i for i, p in enumerate(phases) if p['phase'].startswith('play-'))
    first = next(i for i, p in enumerate(presentations) if p.get('phase', '').startswith('play-'))
    events = []
    for e in get('physical_events'):
        if e.get('service') not in ORDERED_SERVICES:
            continue
        e = {k: v for k, v in e.items() if k not in ('receiver', 'base')}
        # The window input queue 0x4b8910 is native-reuse: the original body
        # removes one message kind with PeekMessageA(min == max, PM_REMOVE);
        # the native provider drains the same kind from its own queue.
        if e['service'] == 'PeekMessageA':
            if e['minimum'] != e['maximum'] or e['remove'] != 1:
                raise Blocked('Unexpected original input queue query')
            e = dict(service='window input drain', window=e['window'], message=e['minimum'], removed=e['queued'])
        elif e['service'] == 'native window input drain':
            e = dict(service='window input drain', window=e['window'], message=e['message'], removed=e['removed'])
        events.append(e)
    return dict(
        level_one_frames=[(f['elapsed_ms'], f['action'], {k: f['player'].get(k) for k in SEMANTIC})
                          for f in get('play_frames')],
        cheat_keys=get('cheat_keys'),
        key_deliveries=[{k: d[k] for k in ('phase', 'key', 'scan', 'target', 'vtable', 'milliseconds')}
                        for d in get('key_deliveries')],
        level_complete_posted=get('level_complete_posted'),
        state_transitions=states,
        navigation=[n for n in get('navigation') if n['phase'] == 'posted-command-delivery'],
        phases=[(p['phase'], p['entry'], p['result']) for p in phases[start:]],
        presentations=[(p.get('phase'), p['milliseconds'], p['pixels_sha256'], p['palette_sha256'],
                        p.get('nonzero_pixels')) for p in presentations[first:]],
        frame_cycles=[(c['phase'], c['milliseconds'], c['keys'], c['presentations'], c['result'])
                      for c in get('frame_cycles') if c['phase'].startswith(('play-', 'cheat-', 'results', 'level-two-'))],
        ordered_services=events,
        level_two_loaded=get('level_two_loaded'),
        level_two_frames=[(f['elapsed_ms'], f['action'], {k: f['player'].get(k) for k in SEMANTIC})
                          for f in get('level_two_frames')],
        level_two_game_ms=get('level_two_game_ms'),
    )


def first_difference(a, b):
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return dict(index=index, original=x, native=y)
    if len(a) != len(b):
        return dict(index=min(len(a), len(b)), reason='length', original=len(a), native=len(b))
    return None


def compare(native_record, original_record):
    divergences = {}
    for key, original in original_record.items():
        native = native_record.get(key)
        if isinstance(original, list):
            difference = first_difference(original, native or [])
        else:
            difference = None if original == native else dict(original=original, native=native)
        if difference:
            divergences[key] = difference
    route = [s['vtable'] for s in original_record['state_transitions']]
    covered = (original_record['level_complete_posted'] and '0x50c0c4' in route
               and [n['wparam'] for n in original_record['navigation']].count(0x8036) >= 1
               and original_record['level_two_loaded'])
    return dict(passed=not divergences and bool(covered), divergences=divergences,
                compared={k: len(v) if isinstance(v, list) else v for k, v in original_record.items()},
                route=route, route_covered=bool(covered))


def run_controls(library, entries, original_record, native_record):
    """Negative controls: each must refuse, never produce a passing comparison."""
    results = {}
    for name, options in (('missing-gameplay-key-down-owner', dict(deny_owner=0x46bb30)),
                          ('missing-results-frame-owner', dict(deny_owner=0x40b1f0))):
        probe = EndOfLevelNativeJoin(library, entries, **options)
        try:
            probe.execute()
        except Blocked as error:
            message = probe.native_error or str(error)
            if 'deliberately withheld' not in message:
                raise Blocked(f'{name} failed for the wrong reason: {message}')
            results[name] = dict(result='refused', error=message, phase=probe.phase)
        else:
            raise Blocked(f'{name} incorrectly completed the end-of-level route')
        finally:
            probe.close()

    def mutated(change):
        record = json.loads(json.dumps(native_record))
        change(record)
        return record
    def results_frame(r):
        index = next(i for i, p in enumerate(r['presentations']) if p[0] and p[0].startswith('results'))
        r['presentations'][index+300][2] = '0'*64
    comparator = (
        ('lost-level-complete-command', lambda r: r['navigation'].remove(
            next(n for n in r['navigation'] if n['wparam'] == 0x800e))),
        ('lost-state-stack-pop', lambda r: r['navigation'].remove(next(n for n in r['navigation'] if n['wparam'] == 0x8036))),
        ('perturbed-results-image', results_frame),
        ('skipped-results-state', lambda r: r['state_transitions'].pop(1)),
        ('perturbed-level-two-position', lambda r: r['level_two_frames'][150][2].__setitem__('x', r['level_two_frames'][150][2]['x']+1)),
    )
    for name, change in comparator:
        if compare(mutated(change), original_record)['passed']:
            raise Blocked(f'Comparator accepted {name}')
        results[name] = 'rejected by comparison'
    (WORK/'controls.json').write_text(json.dumps(results, indent=2)+'\n')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--controls', action='store_true', help='also run the negative controls')
    args = parser.parse_args()
    library, entries = build()
    if args.build_only:
        print(json.dumps(dict(status='built', entries=len(entries))))
        return 0
    original = read_trace(ORIGINAL)
    if original.get('status') != 'pass' or original.get('resumed_checkpoint'):
        raise SystemExit('Original end-of-level trace is not a fresh passing run')
    original_record = json.loads(json.dumps(records(original)))
    del original
    native = EndOfLevelNativeJoin(library, entries)
    started = time.time()
    status = 'blocked'
    try:
        native.execute()
        status = 'native-complete'
    except Blocked as error:
        native.native_error = native.native_error or str(error)
    native_record = None
    comparison = None
    try:
        native_record = json.loads(json.dumps(records(native)))
        comparison = compare(native_record, original_record)
    except StopIteration:
        comparison = dict(passed=False, divergences=dict(record='native run never reached Level 1 play'))
    if status == 'native-complete' and not comparison['passed']:
        status = 'diverged'
    report = dict(status=status, error=native.native_error, error_stack=native.error_stack, phase=native.phase,
                  seconds=round(time.time()-started), calls=list(native.native_calls)[-40:],
                  comparison=comparison, record=native_record, guest_execution=False,
                  x87_returned={hex(k): v for k, v in native.x87_returned.items()},
                  x87_discarded={f'{a:#x}->{b:#x}': v for (a, b), v in native.x87_discarded.items()},
                  native_entries=len(native.native_counts),
                  first_native_counts={hex(k): v for k, v in Counter(native.native_counts).most_common(10)})
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    native.close()
    controls = None
    if args.controls and status == 'native-complete':
        try:
            controls = sorted(run_controls(library, entries, original_record, native_record))
        except Blocked as error:
            status = 'controls-failed'
            native.native_error = str(error)
    print(json.dumps(dict(status=status, error=native.native_error, error_stack=native.error_stack,
                          phase=native.phase, route=comparison.get('route'),
                          divergences=sorted(comparison['divergences']), compared=comparison.get('compared'),
                          controls=controls)))
    return 0 if status == 'native-complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
