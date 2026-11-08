"""Native-only later-level join over admitted canonical owners.

Run with work/test-env/bin/python -m Tests.NativeLevels.native_join --level N [--plan PATH] [--controls].
The unchanged original route of Tests/NativeLevels/trace.py (New Game,
Level 1, MPSCULLY and results for each level before the target, then the
retained physical route recorded by that trace, including all 105706 ms for
Level 12) runs
with every game entry compiled C++ elected from the level census: the
original trace rows of work/level-<n>-map/ownership.json plus every static
closure entry of work/level-<n>-map/closure.json, so each closure owner must
compile and link as a canonical module. The native memory provider has no
instruction executor; physical services are the tracers' stand-ins. The
native record is compared with the retained original trace at every state and
frame boundary. Derived output stays under work/native-level-<n>-join/.
"""
from __future__ import annotations
from Tests.NativeLevels.storage import read_trace, fingerprint
import argparse
import ctypes as C
import hashlib
import json
import time
from collections import Counter
from unicorn.x86_const import UC_X86_REG_ESP
from Tests.NativeMenuBase.trace import Blocked, ROOT
from Tests.NativeLevelOne import native_join as level_one
from Tests.NativeLevelOne.native_join import SEMANTIC, Call
from Tests.NativeLevelOne.trace import LevelOneTrace
from Tests.NativeEndOfLevel import native_join as end_join
from Tests.NativeEndOfLevel.native_join import EndOfLevelNativeJoin
from Tests.NativeLevelTwo.trace import LevelTwoTrace
from Tests.NativeLevelTwo.native_join import summaries
from Tests.NativeLevels import add_level, output_dir
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevels.xmidi_clock import CLOCK_VERSION, TempoClockTrace
from Tests.NativeLevels.provenance import validate_reference
from pathlib import Path
from Tests.NativeLevels.string_compare_fixture import StringCompareFixture, SERVICES as STRING_SERVICES

PLAY_MS = 60000
LEVEL_PLAY_MS = {12: 105706}
# Later-level physical services whose order and values are game decisions:
# the CRT SBCS string comparison, mirrored (DDBLT_DDFX) blits and the large
# spatial-grid vector iterators whose element callbacks are game owners.
LEVEL_SERVICES = ('CRT multibyte string comparison',)
GRID_SERVICES = ('CRT vector constructor iterator', 'CRT vector destructor iterator')


def adapt_edge_call(call, caller):
    """Elect the original 0x416ab8 CALL in player owner 0x415df0.

    This call pushes the actor and its continuation discards that argument.
    The shared leaf 0x4bb030 ignores both ECX and stack inputs and has a plain
    RET; its admitted virtual-handler contract is thiscall with no arguments.
    Run that actual owner through its admitted ABI, without changing the
    ordinary caller's frame or synthesizing the leaf's result.
    """
    if (caller != 0x415df0 or call.function != 0x4bb030 or call.count != 1
            or any(getattr(call, field) for field in (
                'receiver', 'receiver2', 'stack', 'source', 'return_pc',
                'x87_count', 'x87_argument', 'compiler', 'transfer_version',
                'transfer_kind', 'transfer_site', 'caller', 'disposition',
                'x87_state', 'x87_operation', 'callback_cpu', 'callback_activation'))):
        raise Blocked('Unelected player edge-check ABI adapter')
    adapted = Call.from_buffer_copy(call)
    adapted.count = 0
    return adapted


def adapt_idle_call(call, caller):
    """Elect player CALL 0x41979f into the zero-argument idle owner.

    The original pushes EDI, EBX and ESI, then discards those three words at
    0x4197a4. The target never reads them and every exit is a plain RET.
    Its random selection, audio call and return remain the admitted owner's
    work. Only this ordinary caller/target transport drops the unused inputs;
    source frames and other contextual contracts are deliberately unelected.
    """
    if (caller != 0x415df0 or call.function != 0x420480 or call.count != 3
            or any(getattr(call, field) for field in (
                'receiver', 'receiver2', 'stack', 'source', 'return_pc',
                'x87_count', 'x87_argument', 'compiler', 'transfer_version',
                'transfer_kind', 'transfer_site', 'caller', 'disposition',
                'x87_state', 'x87_operation', 'callback_cpu', 'callback_activation'))):
        raise Blocked('Unelected player idle-call ABI adapter')
    adapted = Call.from_buffer_copy(call)
    adapted.count = 0
    return adapted


def owner_control_candidates(original, level, native_counts):
    """Keep original reachability separate from native host dispatch evidence.

    A compiled module can execute an internal body without NativeJoin.invoke:
    deny_owner and native_counts both operate at that host boundary. Original
    execution alone (for example Level 5's 0x467ea0) cannot elect a control.
    Retain zero-dispatch candidates in the report rather than hiding them.
    """
    candidates = [r for r in original['game_functions']
                  if r['entry_kind'] == 'function' and r.get('owner_status') == 'admitted'
                  and r.get('count', 0) > 0
                  and r['phases'] and all(p.startswith(f'level-{level}-') for p in r['phases'])]
    from Tests.NativeLevels import WORDS
    candidates.sort(key=lambda r: (not r['owner'].startswith(f'level_{WORDS[level]}_'), r['address']))
    return [dict(address=r['address'], owner=r['owner'], original_count=r['count'],
                 original_phases=r['phases'],
                 native_dispatch_calls=native_counts.get(int(r['address'], 16), 0))
            for r in candidates]


def denied_owners(original, level, native_counts):
    """Elect two distinct gameplay owners after a passing native comparison.

    Prefer a newly recovered level family, and refuse if its original-reached
    candidates have no native dispatch boundary. Loading-only entries and
    compiled internal bodies are not missing-owner controls.
    """
    from Tests.NativeLevels import WORDS
    candidates = owner_control_candidates(original, level, native_counts)
    chosen, owners = [], set()
    # Preserve the original family's priority when its first reached body is
    # internal: choose another actual boundary from that same family first.
    for owner in dict.fromkeys(r['owner'] for r in candidates):
        row = next((r for r in candidates if r['owner'] == owner
                    and r['native_dispatch_calls'] > 0), None)
        if row is None:
            continue
        chosen.append((f'missing-owner-{row["address"]}', int(row['address'], 16)))
        owners.add(row['owner'])
        if len(chosen) == 2:
            break
    if len(chosen) != 2:
        raise Blocked(f'Need two original-reached Level {level} gameplay owners with native dispatch evidence')
    prefix = f'level_{WORDS[level]}_'
    if (any(r['owner'].startswith(prefix) for r in candidates)
            and not any(owner.startswith(prefix) for owner in owners)):
        raise Blocked(f'No reached native boundary for a newly recovered Level {level} gameplay owner')
    return chosen


def control_refusal(name, message, phase, level):
    """A control must fail for withholding during target gameplay."""
    if 'deliberately withheld' not in message:
        raise Blocked(f'{name} failed for the wrong reason: {message}')
    if not phase.startswith(f'level-{level}-'):
        raise Blocked(f'{name} refused outside Level {level} play: {phase}')
    return dict(result='refused', error=message, phase=phase)


def extend_heap(trace, level):
    """Mirror LevelTrace's bounded physical arenas, without an emulator."""
    if level >= 4:
        trace.machine.mem_map(0x69000000, 0x6000000)
        trace.heap_limit = 0x6f000000
    if level >= 6:
        trace.machine.mem_map(0x30000000, 0x20000000)
        trace.heap_next = 0x30000000
        trace.heap_limit = 0x50000000
    trace.machine.coalesce()


def work(level):
    return ROOT/f'work/native-level-{level}-join'


def census(level):
    """Trace rows plus every static closure entry, as one ownership census."""
    out = output_dir(level)
    ownership = json.loads((out/'ownership.json').read_text())
    closure = json.loads((out/'closure.json').read_text())
    digest = fingerprint(out/'trace.json')
    if not closure['trace_sha256'] == ownership['trace_sha256'] == digest:
        raise Blocked(f'Level {level} closure, ownership and trace disagree')
    rows = list(ownership['rows'])
    traced = {r['address'] for r in rows}
    unresolved = [r['address'] for r in rows if r['classification'] not in ('admitted', 'native-reuse')]
    closure_only = reviewed = 0
    traced_rows = {r['address']: r for r in rows}
    for function in closure['functions']:
        if function['status'] not in ('admitted', 'native-reuse'):
            unresolved.append(function['address'])
            continue
        if function['address'] in traced:
            row = traced_rows[function['address']]
            # Startup native-reuse can name an admitted canonical module;
            # both classifications elect that same module, not a fallback.
            if ((function['status'] == 'native-reuse' and row['classification'] != 'native-reuse') or
                    (function['status'] == 'admitted' and function['owner'] !=
                     (row['native_reuse'] if row['classification'] == 'native-reuse' else row['owner']))):
                raise Blocked(f'Conflicting closure/trace owner at {function["address"]}')
            reviewed += 1
            continue
        if function['status'] != 'admitted' or not function['owner']:
            unresolved.append(function['address'])
            continue
        rows.append(dict(address=function['address'], classification='admitted', owner=function['owner'],
                         native_reuse=None, phases=[], count=0))
        closure_only += 1
    if unresolved:
        raise Blocked(f'Level {level} entries without an admitted canonical owner: {sorted(unresolved)}')
    target = work(level)
    target.mkdir(parents=True, exist_ok=True)
    path = target/'census.json'
    path.write_text(json.dumps(dict(trace_sha256=digest, level=level, trace_rows=len(traced),
                                    closure_traced=reviewed, closure_only=closure_only, rows=rows), indent=1)+'\n')
    return path


def build(level):
    return level_one.build(census(level), work(level), f'native-level-{level}-join')


class LevelNativeJoin(EndOfLevelNativeJoin, LevelTwoTrace):
    """Original later-level orchestration with every game entry native.

    Method order: native invocation and services from the end-of-level join,
    then the Level 2 SBCS and mirrored Blt stand-ins. The generic level route
    (completion of each earlier level, results, target play) and its large
    grid adapter are the unchanged LevelTrace methods."""
    level_two = LevelTrace.level_two
    results = LevelTrace.results
    complete_level = LevelTrace.complete_level
    advance_results = LevelTrace.advance_results
    play_target = LevelTrace.play_target
    comparison_string = StringCompareFixture.comparison_string

    def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        # The seagull registry dispatcher (487467 -> 487469) reaches an
        # ordinary state with an admitted x87 environment. First consume its
        # real source CALL through the existing checked ordinary ABI adapter;
        # that adapter re-enters here without source CPU and the environment
        # owner borrows/publishes the native architectural state normally.
        entry = self.entries.get(address, {})
        if source and entry.get('x87_environment') is not None and not entry.get('source_context'):
            return self.source_ordinary(address, receiver, arguments, stack, source, return_pc)
        return super().invoke(address, receiver, arguments, stack, source, return_pc)

    def verify_sequence_clock(self, handle, sequence):
        if self.target_level >= 10:
            TempoClockTrace.verify_sequence_clock(self, handle, sequence)
            # Record physical validation actually reached by native execution.
            # This is observation only; sequence timing remains the provider's.
            identity = sequence.get('clock_verified')
            if identity is not None:
                self.validated_clocks = getattr(self, 'validated_clocks', set())
                self.validated_clocks.add(identity)
            return
        return LevelOneTrace.verify_sequence_clock(self, handle, sequence)

    def __init__(self, library, entries, *, level, route, deny_idle_random=False, **options):
        EndOfLevelNativeJoin.__init__(self, library, entries, **options)
        extend_heap(self, level)
        self.level_two_ms = PLAY_MS
        self.target_level = level
        self.route = route
        self.target_play_ms = LEVEL_PLAY_MS.get(level, PLAY_MS)
        self.target_checkpoint = None
        self.loaded = False
        self.frames = []
        self.played_ms = self.game_ms = 0
        self.completions = []
        self.edge_call_adaptations = 0
        self.idle_call_adaptations = 0
        self.deny_idle_random = deny_idle_random
        self.validated_clocks = set()
        self.string_comparisons = []

    def service(self, unused, pointer):
        call = pointer.contents
        caller = self.native_functions[-1] if self.native_functions else 0
        if caller == 0x415df0 and call.function == 0x4bb030 and call.count == 1:
            try:
                entry = self.entries.get(call.function, {})
                if (entry.get('convention'), entry.get('argc'), entry.get('returns')) != ('thiscall', 0, 'u32'):
                    raise Blocked('Changed admitted edge-check owner ABI')
                adapted = adapt_edge_call(call, caller)
                value = super().service(unused, C.pointer(adapted))
                if self.native_error is None:
                    self.edge_call_adaptations += 1
                return value
            except Blocked as error:
                self.native_error = self.native_error or str(error)
                self.error_stack = self.error_stack or [hex(a) for a in self.native_functions] + [hex(call.function)]
                self.library.menu_fault(self.host, call.function)
                return 0
        if caller == 0x415df0 and call.function == 0x420480 and call.count == 3:
            try:
                entry = self.entries.get(call.function, {})
                if ((entry.get('convention'), entry.get('argc'), entry.get('returns')) != ('cdecl', 0, 'u32')
                        or any(entry.get(field) is not None for field in
                               ('source_context', 'compiler_context', 'x87_result'))):
                    raise Blocked('Changed admitted idle-call owner ABI')
                adapted = adapt_idle_call(call, caller)
                value = super().service(unused, C.pointer(adapted))
                if self.native_error is None:
                    self.idle_call_adaptations += 1
                return value
            except Blocked as error:
                self.native_error = self.native_error or str(error)
                self.error_stack = self.error_stack or [hex(a) for a in self.native_functions] + [hex(call.function)]
                self.library.menu_fault(self.host, call.function)
                return 0
        return super().service(unused, pointer)

    def fixture(self, address):
        if (self.target_level == 11 and address in STRING_SERVICES
                and self.phase.startswith('level-11-')):
            if getattr(self, 'deny_platform', None) == address:
                raise Blocked(f'Conveyor comparison service deliberately withheld: {address:#x}')
            return StringCompareFixture.fixture(self, address)
        if (getattr(self, 'deny_idle_random', False) and address == 0x4a3050
                and self.native_functions[-1:] == [0x420480]
                and self.phase.startswith(f'level-{self.target_level}-')):
            raise Blocked('Idle random service deliberately withheld: 0x4a3050')
        if address in (0x4a4590, 0x4a4450):
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            if self.word(sp+12) > 65536:
                return LevelTrace.fixture(self, address)
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
                and self.phase.startswith(('play-', f'level-{self.target_level}-'))):
            self.pickup_events.append(dict(phase=self.phase, milliseconds=self.milliseconds,
                score=snapshot['score'], before=before, after=counts, increment=sum(counts)-sum(before),
                observed='native player treasure counters'))
        self.native_counts_seen = counts
        return snapshot


def climbs(frames):
    """Sustained original upward climbs (same rule as Tests.NativeLevels.check)."""
    return sum(1 for a, b in zip(frames, frames[1:])
               if a[1] == b[1] == 'climb-up' and a[2]['x'] == b[2]['x'] and a[2]['y'] > b[2]['y']
               and a[2]['logic_state'] == b[2]['logic_state'] == 27
               and b[2]['input_mask'] & 0x4000000 and not b[2]['input_mask'] & 1)


def records(trace):
    """End-of-level record plus target-level frames, completions and services."""
    record = end_join.records(trace)
    get = (lambda k: trace.get(k)) if isinstance(trace, dict) else (lambda k: getattr(trace, k))
    cycles = get('frame_cycles')
    first = next(i for i, c in enumerate(cycles) if c['phase'].startswith('play-'))
    record['frame_cycles'] = [(c['phase'], c['milliseconds'], c['keys'], c['presentations'], c['result'])
                              for c in cycles[first:]]
    frames = [(f['elapsed_ms'], f['action'], {k: f['player'].get(k) for k in SEMANTIC}) for f in get('frames')]
    pickups, lives = summaries([f[2] for f in frames])
    services = []
    for e in get('physical_events'):
        if e.get('service') in LEVEL_SERVICES:
            services.append(dict(e))
        elif e.get('service') == 'IDirectDrawSurface::Blt' and 'mirror' in e:
            # Surface handles are probe allocations; rectangles, flags and
            # mirror bits are the game's decision.
            services.append({k: v for k, v in e.items() if k not in ('object', 'source')})
        elif e.get('service') in GRID_SERVICES and e['count'] > 4096:
            services.append({k: v for k, v in e.items() if k != 'base'})
    record.update(level_frames=frames, level_pickups=pickups, level_lives=lives, level_services=services,
                  completions=get('completions'), level_loaded=get('loaded'),
                  level_played_ms=get('played_ms'), level_game_ms=get('game_ms'))
    comparisons = (trace.get('string_compare_boundary', {}).get('comparisons', [])
                   if isinstance(trace, dict) else trace.string_comparisons)
    # Physical pointers and synthetic native service stacks are provider-owned.
    # Compare the game's operands, result and ordering at this CRT boundary.
    record['string_comparisons'] = [{k: e[k] for k in
        ('service', 'entry', 'phase', 'left', 'right', 'result', 'domain')} for e in comparisons]
    return record


def compare(native_record, original_record, level):
    result = end_join.compare(native_record, original_record)
    if native_record['string_comparisons'] != original_record['string_comparisons']:
        result['divergences']['string_comparisons'] = dict(
            native=native_record['string_comparisons'], original=original_record['string_comparisons'])
    states = original_record['state_transitions']
    frames = original_record['level_frames']
    covered = bool(original_record['level_complete_posted'] and '0x50c0c4' in result['route']
                   and [n['wparam'] for n in original_record['navigation']].count(0x8036) >= level-1
                   and [c['level'] for c in original_record['completions']] == list(range(2, level))
                   and any(s['level'] == level for s in states)
                   and original_record['level_loaded']
                   and original_record['level_played_ms'] >= LEVEL_PLAY_MS.get(level, PLAY_MS)
                   and (level != 12 or original_record['level_played_ms'] == LEVEL_PLAY_MS[level])
                   and native_record['level_played_ms'] == original_record['level_played_ms']
                   and frames[-1][0] == original_record['level_played_ms']
                   and native_record['level_frames'] == frames
                   and len(frames) > 3000 and all(f[2]['level'] == level for f in frames)
                   and len(original_record['level_pickups']) >= 1 and climbs(frames) >= 10
                   and any(s.get('mirror') for s in original_record['level_services'])
                   and any(s['service'] == GRID_SERVICES[0] and s['count'] > 65536
                           for s in original_record['level_services']))
    result.update(passed=not result['divergences'] and covered, route_covered=covered,
                  climb_frames=climbs(frames),
                  level_pickups=native_record.get('level_pickups'),
                  level_lives=native_record.get('level_lives'))
    return result


def run_controls(library, entries, original_record, native_record, level, route, denied):
    """Negative controls: each must refuse, never produce a passing comparison."""
    results = {}
    # Levels 9 and 10 reach idle audio but never the SBCS service used by earlier
    # routes. Withhold its actual idle random dependency only in target play;
    # a loading-time random failure cannot establish this boundary control.
    service_control = (('missing-idle-random-service', dict(deny_idle_random=True)) if level in (9, 10)
                       else ('missing-conveyor-comparison-service', dict(deny_platform=0x4a3dc0)) if level == 11
                       else ('missing-sbcs-comparison-service', dict(deny_platform=0x4a3810)))
    for name, options in (*((n, dict(deny_owner=a)) for n, a in denied),
                          service_control):
        probe = LevelNativeJoin(library, entries, level=level, route=route, **options)
        try:
            probe.execute()
        except Blocked as error:
            message = probe.native_error or str(error)
            results[name] = control_refusal(name, message, probe.phase, level)
        else:
            raise Blocked(f'{name} incorrectly completed the Level {level} route')
        finally:
            probe.close()

    def mutated(change):
        record = json.loads(json.dumps(native_record))
        change(record)
        return record
    pickup = original_record['level_pickups'][0]['frame']
    climb = next(i for i in range(1, len(original_record['level_frames']))
                 if original_record['level_frames'][i][1] == 'climb-up'
                 and original_record['level_frames'][i][2]['y'] < original_record['level_frames'][i-1][2]['y'])
    def frames(change):
        def apply(r):
            change([f[2] for f in r['level_frames']])
            r['level_pickups'], r['level_lives'] = summaries([f[2] for f in r['level_frames']])
        return apply
    def drop(kind):
        def apply(r):
            r['level_services'].pop(next(i for i, s in enumerate(r['level_services']) if kind(s)))
        return apply
    comparator = (
        ('lost-level-treasure', frames(lambda p: [x.__setitem__('treasure_counts', [0]*10) for x in p])),
        ('reset-score-after-pickup', frames(lambda p: [x.__setitem__('score', 0) for x in p[pickup:]])),
        ('stalled-climb', frames(lambda p: p[climb].__setitem__('y', p[climb-1]['y']))),
        ('perturbed-level-position', frames(lambda p: p[pickup].__setitem__('x', p[pickup]['x']+1))),
        ('lost-mirrored-blit', drop(lambda s: s.get('mirror'))),
        ('lost-large-grid-construction', drop(lambda s: s['service'] == GRID_SERVICES[0] and s['count'] > 65536)),
        ('reordered-level-services', lambda r: r['level_services'].reverse()),
        ('skipped-earlier-level-completion', lambda r: r['completions'].clear()),
        ('truncated-level-route', lambda r: r.update(
            level_played_ms=60000, level_frames=r['level_frames'][:3530])),
    )
    for name, change in comparator:
        if compare(mutated(change), original_record, level)['passed']:
            raise Blocked(f'Comparator accepted {name}')
        results[name] = 'rejected by comparison'
    if level == 12:
        for name, change in (
            ('perturbed-final-level-frame', frames(lambda p: p[-1].update(x=p[-1]['x']+1))),
            ('lost-final-level-service', lambda r: r['level_services'].pop()),
        ):
            if compare(mutated(change), original_record, level)['passed']:
                raise Blocked(f'Comparator accepted {name}')
            results[name] = 'rejected by comparison'
    if level == 11:
        for name, change in (
            ('lost-conveyor-comparison', lambda r: r['string_comparisons'].clear()),
            ('wrong-conveyor-comparison-result', lambda r: r['string_comparisons'][0].update(result=99)),
        ):
            if compare(mutated(change), original_record, level)['passed']:
                raise Blocked(f'Comparator accepted {name}')
            results[name] = 'rejected by comparison'
    (work(level)/'controls.json').write_text(json.dumps(results, indent=2)+'\n')
    return results


def reference_control_report(original, level):
    from Tests.NativeLevels.provenance_controls import run_controls as reference_controls
    results = reference_controls()
    if level == 11:
        from Tests.NativeLevels.observer_reference_check import run_controls as observer_controls
        results.update({'observer-'+name: result
                        for name, result in observer_controls(original).items()})
    return results


def independent_level_twelve_route(original):
    """Require a complete replay from level start, without the mid-route cache."""
    from Tests.NativeLevels.provenance import TRACE_INPUTS, digest
    path = ROOT/'work/level-12-join/original-route.json'
    replay = read_trace(path)
    if (replay.get('status') != 'pass' or replay.get('stop') is not None
            or replay.get('level') != 12 or replay.get('played_ms') != LEVEL_PLAY_MS[12]
            or replay.get('plan') != original['plan'] or replay.get('resumed_observer')
            or replay.get('checkpoint_advancement')):
        raise Blocked('Incomplete independent Level 12 original replay')
    for field, source in TRACE_INPUTS.items():
        if replay.get(field) != digest(source):
            raise Blocked(f'Stale independent Level 12 replay: {source}')
    observer = replay.get('observer_checkpoint', {})
    runner = 'work/level-11-map/route_observer.py'
    if (observer.get('runner') != runner or observer.get('runner_sha256') != digest(runner)
            or any(observer.get(k) != original['observer_checkpoint'].get(k)
                   for k in ('path', 'sha256', 'inputs_sha256'))
            or replay.get('prefix_checkpoint_sha256') != observer.get('sha256')
            or replay.get('resumed_checkpoint') is not True):
        raise Blocked('Changed independent Level 12 start/runner provenance')
    for key in ('executable_sha256', 'resources', 'xmidi_clock_adapter'):
        if replay.get(key) != original.get(key):
            raise Blocked(f'Changed independent Level 12 {key}')
    # Observer-only peg rows do not alter execution. Compare every actual frame
    # and ordered physical/math service, including the entire loading prefix.
    streams = {}
    for key in ('frames', 'frame_cycles', 'physical_events', 'math_events'):
        left, right = replay[key], original[key]
        if len(left) != len(right):
            raise Blocked(f'Independent Level 12 {key} count differs: {len(left)} != {len(right)}')
        for index, (a, b) in enumerate(zip(left, right)):
            if a != b:
                raise Blocked(f'Independent Level 12 {key} differs at row {index}')
        streams[key] = len(left)
    if records(replay) != records(original):
        raise Blocked('Independent Level 12 comparison record differs')
    result = dict(status='pass', path=str(path.relative_to(ROOT)), sha256=fingerprint(path),
                  played_ms=replay['played_ms'], compared_streams=streams)
    target = work(12)
    target.mkdir(parents=True, exist_ok=True)
    (target/'original-replay.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_level(parser)
    parser.add_argument('--plan', type=Path, help='Require this exact retained physical input schedule')
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--controls', action='store_true', help='also run the negative controls')
    args = parser.parse_args()
    level = args.level
    if level == 2:
        # Keep the established Level 2 route and its controls at their owner.
        import subprocess
        import sys
        from Tests.NativeLevels.routes import route_for
        if args.plan and json.loads(args.plan.read_text()) != route_for(2):
            raise SystemExit('Level 2 requires its retained physical input schedule')
        return subprocess.call([sys.executable, '-m', 'Tests.NativeLevelTwo.native_join'] +
                               (['--build-only'] if args.build_only else []) +
                               (['--controls'] if args.controls else []))
    if level in (13, 14):
        # Final-world observers are discovery only. Each join separately
        # requires a full-prefix original and its actual ladder outcome.
        import subprocess
        import sys
        if args.plan and json.loads(args.plan.read_text()) != json.loads((output_dir(level)/'plan.json').read_text()):
            raise SystemExit(f'Level {level} requires its retained physical input schedule')
        runner = 'level_thirteen_join' if level == 13 else 'level_fourteen_run'
        return subprocess.call([sys.executable, '-m', f'Tests.NativeLevels.{runner}'] +
                               (['--build-only'] if args.build_only else []) +
                               (['--controls'] if args.controls else []))
    if args.build_only:
        library, entries = build(level)
        print(json.dumps(dict(status='built', entries=len(entries))))
        return 0
    original = read_trace(output_dir(level)/'trace.json')
    if level in (11, 12):
        from Tests.NativeLevels.observer_reference import validate_observer_reference
        validate_observer_reference(original, level)
    else:
        validate_reference(original, level, full_prefix=True)
    route = json.loads(args.plan.read_text()) if args.plan else original['plan']
    if original['plan'] != route:
        raise SystemExit(f'Retained Level {level} route differs from the requested plan')
    independent_replay = independent_level_twelve_route(original) if level == 12 else None
    provenance_controls = None
    if args.controls:
        provenance_controls = reference_control_report(original, level)
    library, entries = build(level)
    owner_evidence = dict(game_functions=original['game_functions'])
    observer_provenance = original.get('observer_checkpoint') if level in (11, 12) else None
    denied = []
    original_record = json.loads(json.dumps(records(original)))
    del original
    native = LevelNativeJoin(library, entries, level=level, route=route)
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
        comparison = compare(native_record, original_record, level)
    except (StopIteration, IndexError, KeyError, TypeError) as error:
        comparison = dict(passed=False, divergences=dict(record=f'native run incomplete: {error!r}'))
    if status == 'native-complete' and not comparison['passed']:
        status = 'diverged'
    report = dict(status=status, error=native.native_error, error_stack=native.error_stack, phase=native.phase,
                  seconds=round(time.time()-started), calls=list(native.native_calls)[-40:],
                  comparison=comparison, record=native_record, guest_execution=False,
                  x87_returned={hex(k): v for k, v in native.x87_returned.items()},
                  x87_environments={hex(k): v for k, v in native.x87_environments.items()},
                  loot_x87_transports=native.loot_x87_transports,
                  x87_transport_paths={'->'.join(hex(a) for a in path):n for path,n in native.x87_transport_paths.items()},
                  x87_discarded={f'{a:#x}->{b:#x}': v for (a, b), v in native.x87_discarded.items()},
                  source_ordinary={hex(k): v for k, v in native.source_ordinary_calls.items()},
                  native_entries=len(native.native_counts), elected_entries=len(entries),
                  first_native_counts={hex(k): v for k, v in Counter(native.native_counts).most_common(10)})
    work(level).mkdir(parents=True, exist_ok=True)
    (work(level)/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    native.close()
    controls = None
    if args.controls and status == 'native-complete':
        try:
            denied = denied_owners(owner_evidence, level, native.native_counts)
            controls = sorted(run_controls(library, entries, original_record, native_record, level, route, denied))
        except Blocked as error:
            status = 'controls-failed'
            native.native_error = str(error)
    report.update(status=status, error=native.native_error, controls=controls,
                  independent_original_replay=independent_replay,
                  observer_checkpoint=observer_provenance,
                  reference_mode=('hash-validated observer checkpoint; native independently executes full prefix'
                                  if level in (11, 12) else 'independently executed full prefix'),
                  provenance_controls=provenance_controls,
                  physical_clock=(dict(version=CLOCK_VERSION, hz=120,
                      sha256=hashlib.sha256((ROOT/'Tests/NativeLevels/xmidi_clock.py').read_bytes()).hexdigest(),
                      validated_sequences=[dict(version=v, sha256=h, duration_ticks=t)
                          for v, h, t in sorted(native.validated_clocks)]) if level >= 10 else None),
                  level=level, plan=route,
                  reached_owners={hex(a): native.native_counts[a] for _, a in denied},
                  owner_control_candidates=owner_control_candidates(owner_evidence, level, native.native_counts),
                  edge_call_adaptations=native.edge_call_adaptations,
                  idle_call_adaptations=native.idle_call_adaptations,
                  trace_sha256=fingerprint(output_dir(level)/'trace.json'),
                  app_acceptance='not established by the native comparison')
    (work(level)/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=status, error=native.native_error, error_stack=native.error_stack,
                          phase=native.phase, route_covered=comparison.get('route_covered'),
                          climb_frames=comparison.get('climb_frames'),
                          divergences=sorted(comparison.get('divergences', {})), compared=comparison.get('compared'),
                          level_pickups=comparison.get('level_pickups'), level_lives=comparison.get('level_lives'),
                          elected_entries=len(entries), controls=controls)))
    return 0 if status == 'native-complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
