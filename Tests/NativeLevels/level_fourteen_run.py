"""Level 14 join driver: historical discovery, fresh independent original truth.

Discovery input hashes are retained as historical provenance. Current game/frame,
service and pixel truth comes only from the full-prefix independent original.
Every retained semantic observation is reconciled before native comparison.
"""
import argparse
import hashlib
import json
from Tests.NativeLevels.level_fourteen_join import (
    LEVEL, RUNNER, OUT, REFERENCE, Native, original, shared, output_dir,
    read_trace, fingerprint, validate_independent, compare_discovery,
    discovery_controls, compare, reference_controls, controls as common_controls, Blocked, digest,
    TRACE_INPUTS, EXE_SHA256, REZ_PATH, REZ_SHA256)


def validate_discovery(trace, route):
    # A stale observer is never accepted as the independent comparison oracle.
    # Keep its original provenance intact; require every semantic observation
    # to match an independently executed current prefix in main below.
    if (trace.get('status') != 'pass' or trace.get('stop') is not None
            or trace.get('level') != LEVEL or trace.get('played_ms') != 60010
            or trace.get('plan') != route or trace.get('executable_sha256') != EXE_SHA256
            or trace.get('resources', {}).get('sha256') != REZ_SHA256
            or trace.get('resources', {}).get('archive') != str(REZ_PATH.relative_to(shared.ROOT))):
        raise Blocked('Incomplete or mismatched historical Level 14 discovery')
    stale = sorted({path for field,path in TRACE_INPUTS.items()
                    if trace.get(field) != digest(path)})
    observer = trace.get('observer_checkpoint', {})
    if (observer.get('runner') != 'Tests/NativeLevels/level_fourteen_trace.py'
            or observer.get('runner_sha256') != digest(observer['runner'])
            or observer.get('sha256') != trace.get('prefix_checkpoint_sha256')
            or observer.get('sha256') != fingerprint(shared.ROOT/observer['path'])
            or trace.get('frame_budget') != dict(instructions=5_000_000, wall_seconds=45)):
        raise Blocked('Changed historical observer identity or runner')
    return dict(role='Historical discovery only; never native comparison truth',
        stale_inputs=stale, trace_sha256=fingerprint(output_dir(LEVEL)/'trace.json'))


def controls(library, entries, route, reference, record, evidence, counts):
    results = common_controls(library, entries, route, reference, record, evidence, counts)
    name = 'missing-tiger-guard-initializer-0x494460'
    probe = Native(library, entries, route, deny_owner=0x494460)
    try:
        probe.execute()
    except Blocked as error:
        results[name] = shared.control_refusal(name, probe.native_error or str(error), probe.phase, LEVEL)
    else:
        raise Blocked('Withheld TigerGuard initializer incorrectly completed Level 14')
    finally:
        probe.close()
    (OUT/'controls.json').write_text(json.dumps(results, indent=2)+'\n')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', action='store_true')
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    route = json.loads((output_dir(LEVEL)/'plan.json').read_text())
    if args.original:
        return original(route)
    if args.build_only:
        _, entries = shared.build(LEVEL)
        print(json.dumps(dict(status='built', entries=len(entries))))
        return 0
    retained = read_trace(output_dir(LEVEL)/'trace.json')
    discovery_provenance = validate_discovery(retained, route)
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
        discovery_provenance=discovery_provenance,
        record=record, elected_entries=len(entries),
        native_library_sha256=library_sha256, runner_sha256=digest(RUNNER),
        driver_sha256=digest('Tests/NativeLevels/level_fourteen_run.py'),
        validated_clocks=sorted(native.validated_clocks),
        x87_environments={hex(a):n for a,n in native.x87_environments.items()},
        loot_x87_transports=native.loot_x87_transports,
        x87_transport_paths={'->'.join(hex(a) for a in path):n for path,n in native.x87_transport_paths.items()},
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
