"""Native-only Level 2 join over admitted canonical owners.

Run with work/test-env/bin/python -m Tests.NativeLevelTwo.native_join [--controls].
The unchanged original route of Tests/NativeLevelTwo/trace.py (New Game,
Level 1, the MPSCULLY level-complete command, results, the original
continuation into Level 2 and its sixty-second walk/jump/attack plan with one
treasure pickup, a death and a respawn) runs with every game entry compiled
C++ elected from the Level 2 census: the original trace rows of
work/level-two-map/ownership.json plus every static closure entry of
work/level-two-map/closure.json, so each closure owner must compile and link
as a canonical module. The native memory provider has no instruction
executor; physical services are the tracers' stand-ins. The native record is
compared with the retained original trace at every state and frame boundary.
Derived output stays under work/native-level-two-join/.
"""
from __future__ import annotations
from Tests.NativeLevels.storage import read_trace
import argparse
import json
import time
from collections import Counter
from Tests.NativeMenuBase.trace import Blocked, ROOT
from Tests.NativeLevelOne import native_join as level_one
from Tests.NativeLevelOne.trace import LevelOneTrace
from Tests.NativeEndOfLevel import native_join as end_join
from Tests.NativeEndOfLevel.native_join import EndOfLevelNativeJoin
from Tests.NativeLevelTwo.trace import LevelTwoTrace

WORK = ROOT/'work/native-level-two-join'
ORIGINAL = ROOT/'work/level-two-map/trace.json'
OWNERSHIP = ROOT/'work/level-two-map/ownership.json'
CLOSURE = ROOT/'work/level-two-map/closure.json'
LEVEL_TWO_MS = 60000
# Level 2 physical services whose order and values are game decisions: the
# CRT SBCS string comparison and the mirrored (DDBLT_DDFX) blits.
LEVEL_TWO_SERVICES = ('CRT multibyte string comparison',)


def census():
    """Trace rows plus every static closure entry, as one ownership census."""
    ownership = json.loads(OWNERSHIP.read_text())
    closure = json.loads(CLOSURE.read_text())
    if closure['trace_sha256'] != ownership['trace_sha256']:
        raise Blocked('Level 2 closure and ownership come from different traces')
    rows = list(ownership['rows'])
    traced = {r['address'] for r in rows}
    closure_only = 0
    for function in closure['functions']:
        if function['address'] in traced:
            continue
        if function['status'] != 'admitted' or not function['owner']:
            raise Blocked(f'Closure entry {function["address"]} has no admitted canonical owner')
        rows.append(dict(address=function['address'], classification='admitted', owner=function['owner'],
                         native_reuse=None, phases=[], count=0))
        closure_only += 1
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK/'census.json'
    path.write_text(json.dumps(dict(trace_sha256=ownership['trace_sha256'], trace_rows=len(traced),
                                    closure_only=closure_only, rows=rows), indent=1)+'\n')
    return path


def build():
    return level_one.build(census(), WORK, 'native-level-two-join')


class LevelTwoNativeJoin(EndOfLevelNativeJoin, LevelTwoTrace):
    """Original Level 2 orchestration with every game entry native.

    Method order: native invocation and services from the end-of-level join,
    then the Level 2 plan, SBCS comparison and mirrored Blt stand-ins."""
    def __init__(self, library, entries, **options):
        EndOfLevelNativeJoin.__init__(self, library, entries, **options)
        self.level_two_ms = LEVEL_TWO_MS

    def fixture(self, address):
        if address == 0x4a3810:
            return LevelTwoTrace.fixture(self, address)
        return EndOfLevelNativeJoin.fixture(self, address)

    def save_checkpoint(self):
        # The native run never writes the original's discovery checkpoint.
        return None

    def player_snapshot(self, application):
        """Original snapshot fields; a pickup is observed natively as an
        increment of the player's own counters at a play frame boundary."""
        snapshot = LevelOneTrace.player_snapshot(self, application)
        counts = snapshot['treasure_counts']
        before = getattr(self, 'native_counts_seen', None)
        if (before is not None and sum(counts) > sum(before)
                and self.phase.startswith(('play-', 'level-two-'))):
            self.pickup_events.append(dict(phase=self.phase, milliseconds=self.milliseconds,
                score=snapshot['score'], before=before, after=counts, increment=sum(counts)-sum(before),
                observed='native player treasure counters'))
        self.native_counts_seen = counts
        return snapshot


def summaries(players):
    """Treasure pickups and life changes (death, respawn, damage) per frame."""
    pickups, lives = [], []
    for i in range(1, len(players)):
        a, b = players[i-1], players[i]
        if sum(b['treasure_counts']) > sum(a['treasure_counts']):
            pickups.append(dict(frame=i, after=b['treasure_counts'], score=b['score']))
        if (a['health'] > 0) != (b['health'] > 0) or b['health'] > a['health']:
            lives.append(dict(frame=i, health=b['health'], score=b['score'],
                              counts=b['treasure_counts'], x=b['x'], y=b['y']))
    return pickups, lives


def records(trace):
    """End-of-level record plus the Level 2 pickups, life events and services."""
    record = end_join.records(trace)
    get = (lambda k: trace.get(k)) if isinstance(trace, dict) else (lambda k: getattr(trace, k))
    pickups, lives = summaries([f['player'] for f in get('level_two_frames')])
    services = []
    for e in get('physical_events'):
        if e.get('service') in LEVEL_TWO_SERVICES:
            services.append({k: v for k, v in e.items()})
        elif e.get('service') == 'IDirectDrawSurface::Blt' and 'mirror' in e:
            # Surface handles are probe allocations; rectangles, flags and
            # mirror bits are the game's decision.
            services.append({k: v for k, v in e.items() if k not in ('object', 'source')})
    record.update(level_two_pickups=pickups, level_two_lives=lives, level_two_services=services)
    return record


def compare(native_record, original_record):
    result = end_join.compare(native_record, original_record)
    lives = original_record['level_two_lives']
    death = any(l['health'] == 0 for l in lives)
    respawn = any(l['health'] > 0 and l['score'] == original_record['level_two_pickups'][0]['score']
                  for l in lives if death)
    covered = (result['route_covered'] and len(original_record['level_two_pickups']) >= 1
               and death and respawn and any(s.get('mirror') for s in original_record['level_two_services'])
               and len(original_record['level_two_frames']) > 3000)
    result.update(passed=result['passed'] and covered, route_covered=covered,
                  level_two_pickups=native_record.get('level_two_pickups'),
                  level_two_lives=native_record.get('level_two_lives'))
    return result


def run_controls(library, entries, original_record, native_record):
    """Negative controls: each must refuse, never produce a passing comparison."""
    results = {}
    for name, options in (('missing-claw-death-owner', dict(deny_owner=0x41ebd0)),
                          ('missing-level-two-enemy-owner', dict(deny_owner=0x4063b0)),
                          ('missing-sbcs-comparison-service', dict(deny_platform=0x4a3810))):
        probe = LevelTwoNativeJoin(library, entries, **options)
        try:
            probe.execute()
        except Blocked as error:
            message = probe.native_error or str(error)
            if 'deliberately withheld' not in message:
                raise Blocked(f'{name} failed for the wrong reason: {message}')
            if not probe.phase.startswith('level-two-'):
                raise Blocked(f'{name} refused outside Level 2 play: {probe.phase}')
            results[name] = dict(result='refused', error=message, phase=probe.phase)
        else:
            raise Blocked(f'{name} incorrectly completed the Level 2 route')
        finally:
            probe.close()

    def mutated(change):
        record = json.loads(json.dumps(native_record))
        change(record)
        return record
    death = next(l['frame'] for l in original_record['level_two_lives'] if l['health'] == 0)
    pickup = original_record['level_two_pickups'][0]['frame']
    def frames(change):
        def apply(r):
            change([f[2] for f in r['level_two_frames']])
            r['level_two_pickups'], r['level_two_lives'] = summaries([f[2] for f in r['level_two_frames']])
        return apply
    def drop_mirror(r):
        r['level_two_services'].pop(next(i for i, s in enumerate(r['level_two_services']) if s.get('mirror')))
    comparator = (
        ('lost-level-two-treasure', frames(lambda p: [x.__setitem__('treasure_counts', [0]*10) for x in p])),
        ('reset-score-after-respawn', frames(lambda p: [x.__setitem__('score', 0) for x in p[death:]])),
        ('survived-death', frames(lambda p: p[death].__setitem__('health', 5))),
        ('perturbed-level-two-position', frames(lambda p: p[pickup].__setitem__('x', p[pickup]['x']+1))),
        ('lost-mirrored-blit', drop_mirror),
        ('reordered-level-two-services', lambda r: r['level_two_services'].reverse()),
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
    if original.get('status') != 'pass' or original.get('resumed_checkpoint') or original.get('prefix_checkpoint_sha256'):
        raise SystemExit('Original Level 2 trace is not a fresh passing run')
    original_record = json.loads(json.dumps(records(original)))
    del original
    native = LevelTwoNativeJoin(library, entries)
    started = time.time()
    status = 'blocked'
    try:
        native.execute()
        status = 'native-complete'
    except Blocked as error:
        native.native_error = native.native_error or str(error)
    native_record = None
    try:
        native_record = json.loads(json.dumps(records(native)))
        comparison = compare(native_record, original_record)
    except (StopIteration, IndexError, KeyError) as error:
        comparison = dict(passed=False, divergences=dict(record=f'native run incomplete: {error!r}'))
    if status == 'native-complete' and not comparison['passed']:
        status = 'diverged'
    report = dict(status=status, error=native.native_error, error_stack=native.error_stack, phase=native.phase,
                  seconds=round(time.time()-started), calls=list(native.native_calls)[-40:],
                  comparison=comparison, record=native_record, guest_execution=False,
                  x87_returned={hex(k): v for k, v in native.x87_returned.items()},
                  x87_environments={hex(k): v for k, v in native.x87_environments.items()},
                  loot_x87_transports=native.loot_x87_transports,
                  source_ordinary={hex(k):v for k,v in native.source_ordinary_calls.items()},
                  x87_discarded={f'{a:#x}->{b:#x}': v for (a, b), v in native.x87_discarded.items()},
                  native_entries=len(native.native_counts), elected_entries=len(entries),
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
                          phase=native.phase, route_covered=comparison.get('route_covered'),
                          divergences=sorted(comparison.get('divergences', {})), compared=comparison.get('compared'),
                          level_two_pickups=comparison.get('level_two_pickups'),
                          level_two_lives=comparison.get('level_two_lives'),
                          elected_entries=len(entries), controls=controls)))
    return 0 if status == 'native-complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
