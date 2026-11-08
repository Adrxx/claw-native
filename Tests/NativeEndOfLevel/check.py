"""Check end-of-level discovery evidence and bounded queue coverage, never family admission."""
import argparse
import json
from Tests.NativeLevelOne.plan import ROOT, read, fingerprint
from Tests.NativeEndOfLevel.plan import TRACE, OWNERSHIP, end_census


def check(allow_prefix=False):
    trace = read(TRACE)
    ownership = end_census(TRACE)
    queue = read(ROOT/'tools/queue.json')
    contract = queue['end_of_level_batch_contract']
    tasks = {t['id']: t for t in queue['tasks']}
    positions = {t['id']: i for i, t in enumerate(queue['tasks'])}
    assert trace.get('storage_sha256') == fingerprint(ROOT/'Tests/NativeLevels/storage.py')
    assert trace['end_tracer_sha256'] == fingerprint(ROOT/'Tests/NativeEndOfLevel/trace.py')
    assert trace['level_tracer_sha256'] == fingerprint(ROOT/'Tests/NativeLevelOne/trace.py')
    assert trace['menu_tracer_sha256'] == fingerprint(ROOT/'Tests/NativeMenuBase/trace.py')
    assert trace['executable_sha256'] == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
    assert trace['resources']['sha256'] == 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
    assert contract['trace_sha256'] == fingerprint(TRACE)
    assert not trace['resumed_checkpoint'], 'Retained evidence must be a fresh original run'
    assert trace['level_one_loaded'] and trace['level_complete_posted']
    assert ''.join(k['letter'] for k in trace['cheat_keys']) == trace['route']['code']
    vtables = [s['vtable'] for s in trace['state_transitions']]
    assert vtables[:3] == ['0x50c264', '0x50c264', '0x50c0c4'] or vtables[:2] == ['0x50c264', '0x50c0c4'], vtables
    assert '0x50c0c4' in vtables, 'Results state never observed'
    if trace['status'] != 'pass':
        assert allow_prefix, 'Incomplete end-of-level census: '+str(trace['stop'])
        assert trace['stop']['reason'] == contract['stop']['reason']
        assert contract['continuation'] in tasks and tasks[contract['continuation']]['exclusive']
        assert contract['continuation'] in tasks[contract['native_join']]['depends_on']
    else:
        # Owner decision 2026-10-21: after results the original continues into
        # Level 2; the trace follows it for a few seconds of play.
        assert trace['stop'] is None and trace['level_two_loaded']
        assert vtables[-1] == '0x50c264' and trace['state_transitions'][-1].get('level') == 2, vtables
        assert trace['level_two_played_ms'] >= trace['level_two_requested_ms'] >= 3000
        assert trace['level_two_game_ms'] >= 3000, trace['level_two_game_ms']
    rows = ownership['rows']
    assert len(rows) == trace['counts']['game_functions'] == sum(ownership['counts'].values())
    unresolved = {r['address'] for r in rows if r['classification'] in ('owned-but-unadmitted', 'partial', 'unowned')}
    assert contract['functions_executed'] == len(rows)
    assert contract['unresolved_functions'] == len(unresolved)
    assigned = []
    for identifier in contract['batches']:
        task = tasks[identifier]
        assert '-admit-' in identifier or '-batch-' in identifier
        assert 5 <= len(task['addresses']) <= 15, (identifier, len(task['addresses']))
        assigned.extend(task['addresses'])
        assert task['depends_on'] and all(d in tasks for d in task['depends_on'])
        assert positions[identifier] < positions['end-of-level-results']
        assert identifier in tasks['end-of-level-results']['depends_on']
        assert identifier in tasks[contract['native_join']]['depends_on']
    assert len(assigned) == len(set(assigned)), 'Duplicate batch ownership'
    # Entries already queued by Level 1 batches stay with those batches.
    covered = set(assigned) | set(contract.get('covered_by_level_one_batches', []))
    assert unresolved <= covered, sorted(unresolved-covered)
    assert contract['native_join'] in tasks['end-of-level-results']['depends_on']
    assert ownership['counts'] == contract['ownership_counts']
    result = dict(status='partial' if trace['stop'] else 'pass',
        scope='Original discovery and queue check only; no native parity or admission',
        functions_executed=len(rows), counts=ownership['counts'], new_since_level_one=ownership['new_since_level_one'],
        platform_iat_imports=trace['counts']['platform_imports'], platform_functions=trace['counts']['platform_functions'],
        batches=len(contract['batches']), stop=trace['stop'], states=vtables,
        level_two_played_ms=trace.get('level_two_played_ms'), level_two_game_ms=trace.get('level_two_game_ms'))
    OWNERSHIP.write_text(json.dumps(ownership, indent=2)+'\n')
    (ROOT/'work/end-of-level-map/check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-prefix', action='store_true', help='Validate retained partial evidence')
    check(parser.parse_args().allow_prefix)
