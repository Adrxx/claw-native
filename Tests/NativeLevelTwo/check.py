"""Check the retained Level 2 discovery, closure and queue coverage (no emulation)."""
from Tests.NativeLevels.storage import read_trace, fingerprint
import hashlib
import json
from Tests.NativeMenuBase.trace import ROOT


def read(path):
    return read_trace(ROOT/path) if str(path).endswith('trace.json') else json.loads((ROOT/path).read_text())


def main():
    base = 'work/level-two-map/'
    trace = read(base+'trace.json')
    closure = read(base+'closure.json')
    ownership = read(base+'ownership.json')
    queue = read('tools/queue.json')
    for key,path in (('storage_sha256', 'Tests/NativeLevels/storage.py'),
                     ('level_two_tracer_sha256','Tests/NativeLevelTwo/trace.py'),
                     ('level_tracer_sha256','Tests/NativeLevelOne/trace.py'),
                     ('end_tracer_sha256','Tests/NativeEndOfLevel/trace.py')):
        assert trace.get(key) == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path
    assert trace['status'] == 'pass' and trace['stop'] is None, trace['stop']
    assert trace['level_two_loaded'] and trace['level_two_played_ms'] >= 60000
    assert trace['level_two_game_ms'] >= 60000
    assert trace['level_complete_posted'] and ''.join(k['letter'] for k in trace['cheat_keys']) == 'MPSCULLY'
    service_check=read(base+'service-check.json')
    assert service_check['status']=='pass' and service_check['controls']==12
    assert service_check['tracer_sha256']==trace['level_two_tracer_sha256']
    assert any(e.get('mirror') in (2,4,6) for e in trace['physical_events'])
    assert trace['level_two_treasure_pickup_observed']
    pickups = [e for e in trace['pickup_events'] if e['phase'].startswith('level-two-') and e['increment'] > 0]
    assert pickups
    frames = trace['level_two_frames']
    assert all(f['player']['level'] == 2 for f in frames)
    assert len({f['player']['x'] for f in frames}) > 1
    assert {'stand','walk-right','jump-right','attack'} <= {f['action'] for f in frames}
    assert all(e.get('owner_status') for e in trace['game_functions'] if e['entry_kind']=='function')
    digest = fingerprint(ROOT/base/'trace.json')
    assert closure['trace_sha256'] == ownership['trace_sha256'] == digest
    assert not closure['static_only']
    assert closure['level'] == 2 and closure['placed_classes']
    assert all(c['callback'] for c in closure['placed_classes'])
    assert sum(c['placed'] for c in closure['placed_classes']) == 1058
    assert closure['world_sha256'] == hashlib.sha256((ROOT/closure['world_source']).read_bytes()).hexdigest()
    assert 'CaptainClaw' in {c['name'] for c in closure['placed_classes']}
    functions = {r['address']:r for r in closure['functions']}
    assert len(functions) == closure['totals']['reachable']
    assert not closure['commands_unmapped'], closure['commands_unmapped']
    pending = {}
    for task in queue['tasks']:
        if task['state'] != 'done':
            for a in task.get('addresses', []):
                pending.setdefault(a, []).append(task['id'])
    unresolved = {a for a,r in functions.items() if r['status'] not in ('admitted','native-reuse')}
    unresolved.update(r['address'] for r in ownership['rows'] if r['classification'] not in ('admitted','native-reuse'))
    missing = sorted(unresolved-pending.keys())
    assert not missing, missing
    new = [t for t in queue['tasks'] if t['id'].startswith('level-two-batch-')]
    for task in new:
        assert 5 <= len(task['addresses']) <= 15, task['id']
        assert 'depends_on' in task and '600' in task['scope']
    joins = [t for t in queue['tasks'] if t['id']=='level-two-native-batch-join']
    assert len(joins)==1 and joins[0]['exclusive'] is True
    required = {t for a in unresolved for t in pending[a]}
    assert required <= set(joins[0]['depends_on']), required-set(joins[0]['depends_on'])
    print(json.dumps(dict(command='level-two-discovery-check', status='pass',
        played_ms=trace['level_two_played_ms'], treasure_pickups=len(pickups),
        trace_functions=len(ownership['rows']), trace_owner_counts=ownership['counts'],
        closure=closure['totals'], placed_classes=len(closure['placed_classes']),
        unresolved_union=len(unresolved), new_batches=len(new))))


if __name__ == '__main__':
    main()
