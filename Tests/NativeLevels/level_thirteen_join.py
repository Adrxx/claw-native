"""Level 13 full-prefix original/native join, with the original no-ladder outcome.

The retained observer is discovery evidence. --original independently replays
startup, all twelve completions and the retained physical schedule; no checkpoint
is restored. The native run executes the same prefix using canonical modules.
Neither run launches the app or establishes app/device acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import Uc, UcError, UC_HOOK_BLOCK, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels.storage import fingerprint, read_trace, write_trace
from Tests.NativeLevels.trace import Blocked
from Tests.NativeLevels.xmidi_clock import TempoClockTrace
from Tests.NativeLevels.later_reference import ladder_tiles, validate_later_reference
from Tests.NativeLevels.provenance import TRACE_INPUTS, EXE_SHA256, digest
from Tests.NativeEndOfLevel.trace import REZ_PATH, REZ_SHA256
from Tests.NativeLevels import native_join as shared

LEVEL = 13
RUNNER = 'Tests/NativeLevels/level_thirteen_join.py'
OUT = shared.work(LEVEL)
REFERENCE = OUT/'original-route.json'


class BoundaryMachine:
    """Observe block entries plus exact receipts; execute every guest instruction.

    Discovery's instruction census is deliberately not reproduced. All physical
    entries are CALL/JMP destinations (block starts). Exact code hooks additionally
    retain every suspended inline boundary and the inherited non-service receipts.
    The full retained instruction trace remains the ownership census.
    """
    def __init__(self, architecture, mode):
        self.uc = Uc(architecture, mode)

    def __getattr__(self, name):
        return getattr(self.uc, name)

    def hook_add(self, kind, callback, *args, **kwargs):
        if kind != UC_HOOK_CODE:
            return self.uc.hook_add(kind, callback, *args, **kwargs)
        self.boundary_callback = callback
        self.watched = set()
        # CPU/x87 physical-service transport keeps instruction hooks. A block
        # hook is an observation point, not that transport's CPU sync boundary.
        self.service_ranges = ((0x4a1300, 0x4b3400), (0x4f0000, 0x508000),
                               (0x70000000, 0x70010000))
        def block(machine, address, size, user):
            if address not in self.watched and not any(lo <= address < hi for lo,hi in self.service_ranges):
                callback(machine, address, size, user)
        handle = self.uc.hook_add(UC_HOOK_BLOCK, block, *args, **kwargs)
        for lo,hi in self.service_ranges:
            self.uc.hook_add(UC_HOOK_CODE, callback, begin=lo, end=hi-1)
        for address in (0x41f850, 0x41d135, 0x45ace0, 0x429335):
            self.watch(address)
        return handle

    def watch(self, address):
        if address in self.watched:
            return
        self.watched.add(address)
        def receipt(machine, pc, size, user):
            self.boundary_callback(machine, pc, size, user)
        self.uc.hook_add(UC_HOOK_CODE, receipt, begin=address, end=address)


def final_arena(trace):
    # Same physical storage as LaterTrace; allocations remain bounded, poisoned
    # and owned by the inherited provider. There is no guest execution natively.
    trace.machine.mem_map(0x50000000, 0x11000000)
    trace.heap_limit = 0x61000000
    if hasattr(trace.machine, 'coalesce'):
        trace.machine.coalesce()


class Original(TempoClockTrace):
    def __init__(self, route, *, startup_paper=False):
        super().__init__(level=LEVEL, instruction_limit=15_000_000_000,
            deny_platform=None, route=route, play_ms=60000, machine_factory=BoundaryMachine, startup_paper=startup_paper)
        final_arena(self)
        self.rank_sort = None
        self.rank_sorts_completed = 0

    def fixture(self, address):
        # Discovery's adjacent insertion sort preserves ties; the actual CRT
        # does not. Rank bytes are later consumed as pixel indices by mode 50.
        # Execute the pinned CRT here as reference, including its comparator;
        # native gameplay continues to use the admitted byte-sort specialization.
        if address == 0x4f1e20:
            self.platform_call(address, 'CRT qsort')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            base, count, width, comparator = (self.word(sp+4*i) for i in range(1,5))
            if (self.rank_sort or self.sort_frame or self.word(sp) != 0x4c706d
                    or (count,width,comparator) != (256,1,0x4c70b0)):
                raise Blocked('Unelected original rank-sort profile')
            self.machine.mem_read(base, count)
            event = dict(service='CRT qsort', base=hex(base), count=count, width=width,
                comparator=hex(comparator), algorithm='unchanged original CRT 0x4f1e20',
                completed=False)
            self.physical_events.append(event)
            self.rank_sort = dict(sp=sp, event=event)
            return
        if (getattr(self, 'rank_sort', None) and any(lo <= address < hi for lo,hi in
                ((0x4f1e20,0x4f1fc5),(0x4f1fd0,0x4f2029),(0x4f2030,0x4f205c)))):
            return
        return super().fixture(address)

    def hook(self, machine, address, size, user):
        active = getattr(self, 'rank_sort', None)
        if active and address == 0x4c706d:
            if machine.reg_read(UC_X86_REG_ESP) != active['sp']+4:
                raise Blocked('Original rank sort returned with the wrong stack')
            active['event']['completed'] = True
            self.rank_sorts_completed += 1
            self.rank_sort = None
        return super().hook(machine, address, size, user)

    def run(self, address, receiver, arguments=(), phase='', boundary=None, **options):
        if boundary is not None:
            self.machine.watch(boundary)
        return super().run(address, receiver, arguments, phase=phase, boundary=boundary, **options)

    def play_target(self, application):
        if not self.startup_profile['paper']:
            return super().play_target(application)
        # The input plan counts idle frames. A synchronous paper respawn still
        # advances the physical timer, but must not consume later input frames.
        self.clock_step = 0
        self.loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.frames = [dict(elapsed_ms=0, action='loaded', player=first)]
        self.scheduled_play_ms = 0
        while self.scheduled_play_ms < self.target_play_ms:
            action = next(a for a in self.route
                if a['start_ms'] <= self.scheduled_play_ms < a['end_ms'])
            self.frame(application, 'level-13-'+action['action'], action['keys'])
            state = self.word(application+0x2c)
            if self.word(state) != 0x50c264 or self.word(state+0x14) != LEVEL:
                raise Blocked('Original left Level 13 play')
            self.scheduled_play_ms += 17
            self.played_ms = self.milliseconds-start
            self.frames.append(dict(elapsed_ms=self.played_ms, action=action['action'],
                                    player=self.player_snapshot(application)))
            if len(self.frames) % 120 == 0:
                print(json.dumps(dict(event='level-13', scheduled_ms=self.scheduled_play_ms,
                    **self.frames[-1])), flush=True)
        self.game_ms = (self.frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, 'level-13-played')

    def report(self):
        result = super().report()
        if self.startup_profile['paper']:
            result.update(route_scheduler='retained-17-ms-input-frames',
                scheduled_play_ms=getattr(self, 'scheduled_play_ms', 0))
        return result


class Native(shared.LevelNativeJoin):
    def __init__(self, library, entries, route, **options):
        self.denied_service = options.pop('deny_platform', None)
        super().__init__(library, entries, level=LEVEL, route=route, **options)
        final_arena(self)

    def platform_call(self, address, name):
        super().platform_call(address, name)
        if address == self.denied_service and self.phase.startswith('level-13-'):
            raise Blocked(f'Level 13 physical service deliberately withheld: {name}')


def validate_independent(trace, route):
    if (trace.get('status') != 'pass' or trace.get('stop') is not None
            or trace.get('level') != LEVEL or trace.get('plan') != route
            or trace.get('scheduled_play_ms', trace.get('played_ms')) != 60010):
        raise Blocked('Incomplete independent Level 13 original route')
    if trace.get('startup_profile', {}).get('paper'):
        if (trace.get('route_scheduler') != 'retained-17-ms-input-frames'
                or trace.get('played_ms', 0) < trace['scheduled_play_ms']):
            raise Blocked('Level 13 paper route lost physical fade time')
    if any(trace.get(k) for k in ('prefix_checkpoint_sha256', 'resumed_checkpoint',
            'observer_checkpoint', 'checkpoint_advancement', 'later_advancement')):
        raise Blocked('Level 13 comparison cannot restore an observer prefix')
    for field, path in TRACE_INPUTS.items():
        if trace.get(field) != digest(path):
            raise Blocked(f'Stale independent original input: {path}')
    if trace.get('independent_runner_sha256') != digest(RUNNER):
        raise Blocked('Stale independent Level 13 original runner')
    rank = trace.get('rank_sort_reference', {})
    if (rank.get('algorithm') != 'unchanged original CRT 0x4f1e20'
            or not rank.get('completed') or rank.get('active') is not False):
        raise Blocked('Independent Level 13 pixels require original CRT rank tie ordering')
    if (trace.get('executable_sha256') != EXE_SHA256
            or trace.get('resources', {}).get('sha256') != REZ_SHA256
            or trace.get('resources', {}).get('archive') != str(REZ_PATH.relative_to(ROOT))):
        raise Blocked('Independent original binary/archive mismatch')
    clock = trace.get('xmidi_clock_adapter', {})
    if (clock.get('version'), clock.get('hz'), clock.get('sha256')) != (
            shared.CLOCK_VERSION, 120, digest('Tests/NativeLevels/xmidi_clock.py')):
        raise Blocked('Stale independent original physical clock')


def reference_controls(trace, route):
    """Reject stale provenance and any reuse of a discovery checkpoint."""
    validate_independent(trace, route)
    mutations = {
        'wrong-binary': lambda t:t.update(executable_sha256='0'*64),
        'wrong-route': lambda t:t.update(plan=[]),
        'short-route': lambda t:t.update(played_ms=59993, scheduled_play_ms=59993),
        'stale-runner': lambda t:t.update(independent_runner_sha256='0'*64),
        'stale-tracer': lambda t:t.update(generic_tracer_sha256='0'*64),
        'stale-clock': lambda t:t.update(xmidi_clock_adapter={}),
        'discovery-rank-sort': lambda t:t.update(rank_sort_reference={}),
        'wrong-archive': lambda t:t.update(resources={}),
    }
    for field in ('prefix_checkpoint_sha256', 'resumed_checkpoint',
            'observer_checkpoint', 'checkpoint_advancement', 'later_advancement'):
        mutations['restored-'+field] = lambda t,f=field:t.update({f: True})
    results = {}
    for name, mutate in mutations.items():
        changed = dict(trace)
        mutate(changed)
        try:
            validate_independent(changed, route)
        except Blocked:
            results[name] = 'rejected'
        else:
            raise Blocked(f'Independent reference accepted {name}')
    return results


def compare(native, original):
    result = shared.end_join.compare(native, original)
    frames = original['level_frames']
    up = [f for f in frames if f[1] == 'climb-up' and f[2]['input_mask'] & 0x4000000]
    # A key label never certifies climbing. The original world has no ladder
    # tiles; require its actual up-key frames and compare every native frame.
    covered = bool(ladder_tiles(LEVEL) == 0 and up and shared.climbs(frames) == 0
        and original['level_complete_posted'] and '0x50c0c4' in result['route']
        and [n['wparam'] for n in original['navigation']].count(0x8036) == LEVEL-1
        and [c['level'] for c in original['completions']] == list(range(2, LEVEL))
        and any(s['level'] == LEVEL for s in original['state_transitions'])
        and original['level_loaded'] and original['level_played_ms'] == 60010
        and original['level_game_ms'] >= 60000 and frames[-1][0] == 60010
        and len(frames) == 3531 and all(f[2]['level'] == LEVEL for f in frames)
        and {'stand','walk-right','jump-right','attack','climb-up'} <= {f[1] for f in frames}
        and original['level_pickups'] and any(s.get('mirror') for s in original['level_services'])
        and any(s['service'] == shared.GRID_SERVICES[0] and s['count'] > 65536
                for s in original['level_services'])
        and native['level_frames'] == frames)
    result.update(passed=not result['divergences'] and covered, route_covered=covered,
        climb_frames=shared.climbs(frames), up_key_frames=len(up), ladder_tiles=0,
        level_pickups=native['level_pickups'])
    return result


def compare_discovery(independent, retained):
    """Reconcile discovery observations without using its rank-sort pixels.

    Discovery's physical qsort preserves ties; the independent reference runs
    the unchanged original CRT. Keep every presentation's phase, time and
    palette checked here. Pixel hashes and nonzero-pixel counts both depend on
    those ties. Only the independent original supplies pixel truth for the
    strict native comparison above.
    """
    result = compare(independent, retained)
    differences = []
    left, right = independent['presentations'], retained['presentations']
    if len(left) == len(right):
        for index, (actual, discovery) in enumerate(zip(left, right)):
            if actual != discovery:
                if (actual[:2] != discovery[:2] or actual[3] != discovery[3]
                        or not actual[0].startswith('level-13-')):
                    break
                differences.append(dict(index=index, phase=actual[0], milliseconds=actual[1],
                    independent_pixels=actual[2], discovery_pixels=discovery[2],
                    independent_nonzero_pixels=actual[4], discovery_nonzero_pixels=discovery[4]))
        else:
            result['divergences'].pop('presentations', None)
    result.update(passed=not result['divergences'] and result['route_covered'],
        pixel_parity='not established against discovery; native pixels require independent original',
        discovery_pixel_differences=differences)
    return result


def discovery_controls(independent, retained):
    results = {}
    for name, mutate in {
        'wrong-palette': lambda r:r['presentations'][0].__setitem__(3, '0'*64),
        'wrong-presentation-time': lambda r:r['presentations'][0].__setitem__(1, 0),
        'lost-presentation': lambda r:r['presentations'].pop(),
        'lost-services': lambda r:r['level_services'].clear(),
        'lost-progression': lambda r:r['completions'].clear(),
        'changed-prefix-pixels': lambda r:r['presentations'][0].__setitem__(2, '0'*64),
    }.items():
        changed = json.loads(json.dumps(independent))
        mutate(changed)
        if compare_discovery(changed, retained)['passed']:
            raise Blocked(f'Discovery reconciliation accepted {name}')
        results[name] = 'rejected'
    return results


def original(route, *, startup_paper=False, output=REFERENCE):
    trace = Original(route, startup_paper=startup_paper)
    try:
        trace.execute()
    except (Blocked, UcError) as error:
        trace.stop = trace.stop or dict(reason=str(error), phase=trace.phase)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    report['rank_sort_reference'] = dict(algorithm='unchanged original CRT 0x4f1e20',
        completed=trace.rank_sorts_completed, active=trace.rank_sort is not None)
    report['limitations'] = [item for item in report.get('limitations', [])
        if 'equivalent-key ordering is not original CRT parity' not in item]
    report['counts']['observer_blocks_and_receipts'] = report['counts'].pop('instructions')
    report['observation'] = 'Block entries and exact boundary receipts; not an instruction/function census'
    report['independent_runner_sha256'] = digest(RUNNER)
    report['scope'] = 'Independent full-prefix original Level 13 route; no native or app acceptance'
    output.parent.mkdir(parents=True, exist_ok=True)
    write_trace(output, report)
    print(json.dumps(dict(status=report['status'], stop=report['stop'], played_ms=trace.played_ms)))
    return 0 if report['status'] == 'pass' else 2


def controls(library, entries, route, reference, record, evidence, counts):
    results = {}
    denied = shared.denied_owners(evidence, LEVEL, counts)
    for name, options in (*((name, dict(deny_owner=address)) for name,address in denied),
            ('missing-sbcs-comparison-service', dict(deny_platform=0x4a3810))):
        probe = Native(library, entries, route, **options)
        try:
            probe.execute()
        except Blocked as error:
            results[name] = shared.control_refusal(name, probe.native_error or str(error), probe.phase, LEVEL)
        else:
            raise Blocked(f'{name} incorrectly completed Level 13')
        finally:
            probe.close()
    pickup = reference['level_pickups'][0]['frame']
    up = next(i for i,f in enumerate(reference['level_frames']) if f[1] == 'climb-up')
    def change_frame(index, key, value):
        def apply(r):
            r['level_frames'][index][2][key] = value
            r['level_pickups'], r['level_lives'] = shared.summaries([f[2] for f in r['level_frames']])
        return apply
    mutations = {
        'lost-treasure': change_frame(pickup, 'treasure_counts', [0]*10),
        'wrong-pickup-score': change_frame(pickup, 'score', 0),
        'invented-climb': change_frame(up, 'y', reference['level_frames'][up][2]['y']-1),
        'wrong-position': change_frame(pickup, 'x', reference['level_frames'][pickup][2]['x']+1),
        'reordered-services': lambda r:r['level_services'].reverse(),
        'lost-service': lambda r:r['level_services'].pop(),
        'skipped-progression': lambda r:r['completions'].clear(),
        'truncated-route': lambda r:r['level_frames'].pop(),
        'wrong-pixels': lambda r:r['presentations'][0].__setitem__(2, '0'*64),
    }
    for name, mutate in mutations.items():
        changed = json.loads(json.dumps(record))
        mutate(changed)
        if compare(changed, reference)['passed']:
            raise Blocked(f'Comparator accepted {name}')
        results[name] = 'rejected by comparison'
    (OUT/'controls.json').write_text(json.dumps(results, indent=2)+'\n')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', action='store_true')
    parser.add_argument('--paper-startup', action='store_true')
    parser.add_argument('--output', type=Path, default=REFERENCE)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    route = json.loads((output_dir(LEVEL)/'plan.json').read_text())
    if args.original:
        if not args.output.resolve().is_relative_to(ROOT/'work'):
            parser.error('Derived artifacts must stay under work/')
        return original(route, startup_paper=args.paper_startup, output=args.output)
    if args.build_only:
        _, entries = shared.build(LEVEL)
        print(json.dumps(dict(status='built', entries=len(entries))))
        return 0
    retained = read_trace(output_dir(LEVEL)/'trace.json')
    validate_later_reference(retained, LEVEL)
    reference = read_trace(REFERENCE)
    validate_independent(reference, route)
    reference_record = json.loads(json.dumps(shared.records(reference)))
    retained_record = json.loads(json.dumps(shared.records(retained)))
    retained_comparison = compare_discovery(reference_record, retained_record)
    if not retained_comparison['passed']:
        raise Blocked(f'Independent original differs from discovery: {retained_comparison}')
    checked_discovery = discovery_controls(reference_record, retained_record)
    library, entries = shared.build(LEVEL)
    native = Native(library, entries, route)
    status = 'blocked'
    try:
        native.execute()
        status = 'native-complete'
    except Blocked as error:
        native.native_error = native.native_error or str(error)
    comparison, record = None, None
    try:
        record = json.loads(json.dumps(shared.records(native)))
        comparison = compare(record, reference_record)
        if status == 'native-complete' and not comparison['passed']:
            status = 'diverged'
    except (StopIteration, IndexError, KeyError, TypeError) as error:
        comparison = dict(passed=False, error=f'Incomplete native record: {error!r}')
    counts = dict(native.native_counts)
    with open(library._name, 'rb') as stream:
        library_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(status=status, error=native.native_error, error_stack=native.error_stack,
        phase=native.phase, comparison=comparison, guest_execution=False,
        independent_original_sha256=fingerprint(REFERENCE), discovery_sha256=fingerprint(output_dir(LEVEL)/'trace.json'),
        discovery_comparison=retained_comparison, discovery_controls=checked_discovery,
        record=record, elected_entries=len(entries),
        native_library_sha256=library_sha256, runner_sha256=digest(RUNNER),
        validated_clocks=sorted(native.validated_clocks),
        native_counts={hex(a):n for a,n in counts.items()}, app_acceptance='not established')
    native.close()
    (OUT/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    if status == 'native-complete' and args.controls:
        try:
            report['reference_controls'] = reference_controls(reference, route)
            report['controls'] = controls(library, entries, route, reference_record, record, retained, counts)
        except Blocked as error:
            status = report['status'] = 'controls-failed'
            report['error'] = str(error)
        (OUT/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','error','error_stack','phase','comparison','elected_entries')}))
    return 0 if status == 'native-complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
