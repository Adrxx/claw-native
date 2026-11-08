"""Level 14 full-prefix original/native join, with sustained original climbing.

The retained observer is discovery evidence. --original independently replays
startup, all thirteen completions and the retained physical schedule; no checkpoint
is restored. The native run executes the same prefix using canonical modules.
Neither run launches the app or establishes app/device acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels.storage import fingerprint, read_trace, write_trace
from Tests.NativeLevels.trace import Blocked
from Tests.NativeLevels.xmidi_clock import TempoClockTrace
from Tests.NativeLevels.later_reference import validate_later_reference
from Tests.NativeLevels.level_thirteen_join import BoundaryMachine, final_arena, Original as PriorOriginal
from Tests.NativeLevels.provenance import TRACE_INPUTS, EXE_SHA256, digest
from Tests.NativeEndOfLevel.trace import REZ_PATH, REZ_SHA256
from Tests.NativeLevels import native_join as shared

LEVEL = 14
RUNNER = 'Tests/NativeLevels/level_fourteen_join.py'
OUT = shared.work(LEVEL)
REFERENCE = OUT/'original-route.json'


class Original(PriorOriginal):
    def __init__(self, route, *, startup_paper=False):
        # Reuse only the physical observer and original CRT rank-sort service.
        # Startup and all thirteen completions execute afresh for Level 14.
        TempoClockTrace.__init__(self, level=LEVEL, instruction_limit=15_000_000_000,
            deny_platform=None, route=route, play_ms=60000, machine_factory=BoundaryMachine, startup_paper=startup_paper)
        final_arena(self)
        self.rank_sort = None
        self.rank_sorts_completed = 0

    def checkpoint_inputs(self):
        return {**super().checkpoint_inputs(), **{name: digest(name) for name in (
            RUNNER, 'Tests/NativeLevels/level_fourteen_boss_trace.py',
            'Tests/NativeLevels/level_fourteen_ending_trace.py')}}

    # Borrow only the rank-sort/observer transport, not Level 13's scheduler.
    def play_target(self, application):
        from Tests.NativeLevels.trace import LevelTrace
        return LevelTrace.play_target(self, application)

    def report(self):
        return TempoClockTrace.report(self)


class Native(shared.LevelNativeJoin):
    def __init__(self, library, entries, route, **options):
        self.denied_service = options.pop('deny_platform', None)
        super().__init__(library, entries, level=LEVEL, route=route, **options)
        final_arena(self)

    def platform_call(self, address, name):
        super().platform_call(address, name)
        if address == self.denied_service and self.phase.startswith('level-14-'):
            raise Blocked(f'Level 14 physical service deliberately withheld: {name}')


def validate_independent(trace, route):
    if (trace.get('status') != 'pass' or trace.get('stop') is not None
            or trace.get('level') != LEVEL or trace.get('plan') != route
            or trace.get('played_ms') != 60010):
        raise Blocked('Incomplete independent Level 14 original route')
    if any(trace.get(k) for k in ('prefix_checkpoint_sha256', 'resumed_checkpoint',
            'observer_checkpoint', 'checkpoint_advancement', 'later_advancement')):
        raise Blocked('Level 14 comparison cannot restore an observer prefix')
    for field, path in TRACE_INPUTS.items():
        if trace.get(field) != digest(path):
            raise Blocked(f'Stale independent original input: {path}')
    if trace.get('observer_transport_sha256') != digest('Tests/NativeLevels/level_thirteen_join.py'):
        raise Blocked('Stale shared original observer transport')
    if trace.get('independent_runner_sha256') != digest(RUNNER):
        raise Blocked('Stale independent Level 14 original runner')
    rank = trace.get('rank_sort_reference', {})
    if (rank.get('algorithm') != 'unchanged original CRT 0x4f1e20'
            or not rank.get('completed') or rank.get('active') is not False):
        raise Blocked('Independent Level 14 pixels require original CRT rank tie ordering')
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
        'short-route': lambda t:t.update(played_ms=59993),
        'stale-observer-transport': lambda t:t.update(observer_transport_sha256='0'*64),
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
    result = shared.compare(native, original, LEVEL)
    frames = original['level_frames']
    covered = bool(result['route_covered']
        and original['level_played_ms'] == 60010
        and original['level_game_ms'] >= 60000 and len(frames) == 3531
        and {'stand','walk-right','jump-right','attack','climb-up'} <= {f[1] for f in frames}
        and len({f[2]['x'] for f in frames}) > 1
        and [n['wparam'] for n in original['navigation']].count(0x8036) == LEVEL-1)
    result.update(passed=not result['divergences'] and covered, route_covered=covered)
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
                        or not actual[0].startswith('level-14-')):
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


def original(route, *, startup_paper=False, output=REFERENCE, checkpoint=None):
    trace = Original(route, startup_paper=startup_paper)
    trace.target_checkpoint = checkpoint
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
    report['observer_transport_sha256'] = digest('Tests/NativeLevels/level_thirteen_join.py')
    report['independent_runner_sha256'] = digest(RUNNER)
    report['scope'] = 'Independent full-prefix original Level 14 route; no native or app acceptance'
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
            raise Blocked(f'{name} incorrectly completed Level 14')
        finally:
            probe.close()
    pickup = reference['level_pickups'][0]['frame']
    up = next(i for i in range(1, len(reference['level_frames']))
        if reference['level_frames'][i][1] == 'climb-up'
        and reference['level_frames'][i][2]['y'] < reference['level_frames'][i-1][2]['y'])
    def change_frame(index, key, value):
        def apply(r):
            r['level_frames'][index][2][key] = value
            r['level_pickups'], r['level_lives'] = shared.summaries([f[2] for f in r['level_frames']])
        return apply
    mutations = {
        'lost-treasure': change_frame(pickup, 'treasure_counts', [0]*10),
        'wrong-pickup-score': change_frame(pickup, 'score', 0),
        'stalled-climb': change_frame(up, 'y', reference['level_frames'][up-1][2]['y']),
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
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--paper-startup', action='store_true')
    parser.add_argument('--output', type=Path, default=REFERENCE)
    parser.add_argument('--checkpoint', type=Path, help='Write a fresh Level 14 start snapshot; never restore it here')
    args = parser.parse_args()
    if args.checkpoint:
        args.checkpoint = args.checkpoint.resolve()
        if not args.checkpoint.is_relative_to(ROOT/'work'):
            parser.error('Checkpoints must stay under work/')
        if __import__('Tests.NativeLevels.storage', fromlist=['exists']).exists(args.checkpoint):
            parser.error('Refusing to overwrite an existing start checkpoint')
    if not args.output.resolve().is_relative_to(ROOT/'work'):
        parser.error('Original-derived evidence must stay under work/')
    OUT.mkdir(parents=True, exist_ok=True)
    route = json.loads((output_dir(LEVEL)/'plan.json').read_text())
    if args.original:
        return original(route, startup_paper=args.paper_startup, output=args.output, checkpoint=args.checkpoint)
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
    # The owner-reported first-checkpoint initializer must cross the native
    # dispatch boundary, not merely appear in the static ownership census.
    if status == 'native-complete' and counts.get(0x494460, 0) == 0:
        status = 'diverged'
        native.native_error = 'TigerGuard initializer 0x494460 was not dispatched'
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
