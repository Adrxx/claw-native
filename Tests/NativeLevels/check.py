"""Validate retained discovery, ownership, closure and unique queued coverage without emulation."""
from Tests.NativeLevels.storage import read_trace, fingerprint
import argparse
import hashlib
import json
import re
from Tests.NativeLevels import ROOT, WORDS, add_level, output_dir
from Tests.NativeLevels.provenance import validate_reference


def closure_batches(tasks, prefix):
    # batches.py emits numbered function batches. Integration follow-ups may
    # share the prefix without owning a batch of function addresses.
    batches = [t for t in tasks if t['id'].startswith(prefix+'-batch-')
               and ('addresses' in t or re.search(r'-[0-9]{2}$', t['id']))]
    for task in batches:
        assert 5<=len(task['addresses'])<=15 and 'depends_on' in task and '600' in task['scope'], task['id']
    return batches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_level(parser)
    parser.add_argument('--closure-only', action='store_true',
                        help='Check static later-level surfaces only; does not certify a route or ownership')
    args = parser.parse_args()
    level = args.level
    if args.closure_only and level not in (7, 8, 9, 10, 11, 12, 13, 14):
        parser.error('--closure-only covers Levels 7 through 14')
    if level == 2:
        from Tests.NativeLevelTwo.check import main as level_two_check
        level_two_check()
        return
    out = output_dir(level)
    read = lambda name: read_trace(out/name) if name == 'trace.json' else json.loads((out/name).read_text())
    if args.closure_only:
        from Tests.NativeLevels.discovery import validate_later_closure
        closure = read('closure.json')
        validate_later_closure(closure)
        assert closure['world_sha256'] == hashlib.sha256((ROOT/closure['world_source']).read_bytes()).hexdigest()
        for path, digest in closure['inputs_sha256'].items():
            assert digest == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path
        print(json.dumps(dict(command=f'level-{level}-closure-check', status='pass',
            placed_classes=len(closure['placed_classes']),
            placed_logic_names=sum(c['placed'] > 0 for c in closure['placed_classes']),
            scope='Static discovery only')))
        return
    trace, closure, ownership = (read(n+'.json') for n in ('trace','closure','ownership'))
    if level in (13, 14):
        later_services = read('later-service-check.json')
        assert later_services['status'] == 'pass' and later_services['controls'] == 3
        assert later_services['runner_sha256'] == hashlib.sha256(
            (ROOT/'Tests/NativeLevels/later_trace.py').read_bytes()).hexdigest()
    if level == 14:
        runner_controls = read('runner-controls.json')
        assert runner_controls['status'] == 'pass' and len(runner_controls['controls']) == 4
        assert runner_controls['runner'] == 'Tests/NativeLevels/level_fourteen_trace.py'
        assert runner_controls['runner_sha256'] == hashlib.sha256(
            (ROOT/runner_controls['runner']).read_bytes()).hexdigest()
    validate_reference(trace, level)
    queue = json.loads((ROOT/'tools/queue.json').read_text())
    for key,path in (('storage_sha256', 'Tests/NativeLevels/storage.py'),
                     ('generic_tracer_sha256','Tests/NativeLevels/trace.py'),
                     ('routes_sha256','Tests/NativeLevels/routes.py'),
                     ('provider_tracer_sha256','Tests/NativeLevelTwo/trace.py'),
                     ('level_tracer_sha256','Tests/NativeLevelOne/trace.py'),
                     ('end_tracer_sha256','Tests/NativeEndOfLevel/trace.py')):
        assert trace.get(key) == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path
    if 'checkpoint_advancement' in trace:
        advancement = trace['checkpoint_advancement']
        assert advancement['source_level'] < advancement['destination'] == level
        assert advancement['source_sha256'] == fingerprint(ROOT/advancement['source_checkpoint'])
        assert advancement['runner_sha256'] == hashlib.sha256((ROOT/'Tests/NativeLevels/advance.py').read_bytes()).hexdigest()
    services = read('service-check.json')
    assert services['status']=='pass' and services['controls']==7
    if level >= 4:
        assert services['heap_controls']==3
        assert services['heap_limit']==('0x50000000' if level >= 6 else '0x6f000000')
    assert services['tracer_sha256']==trace['generic_tracer_sha256']
    regression = json.loads((ROOT/'work/level-3-map/level-two-regression/check.json').read_text())
    assert regression['status']=='pass' and regression['play_delegation']
    for path, digest in regression['inputs_sha256'].items():
        assert digest == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path
    assert trace['status']=='pass' and trace['stop'] is None, trace['stop']
    assert trace['level']==level and trace['loaded'] and trace['played_ms']>=60000 and trace['game_ms']>=60000
    assert ''.join(k['letter'] for k in trace['cheat_keys']) == 'MPSCULLY'*(level-1)
    assert [e['level'] for e in trace['completions']] == list(range(2,level))
    assert all(e['posted'] and e['next_level']==e['level']+1 for e in trace['completions'])
    transitions = {e.get('level') for e in trace['state_transitions']}
    assert set(range(1,level+1)) <= transitions
    frames = trace['frames']
    assert all(f['player']['level']==level for f in frames)
    assert len({f['player']['x'] for f in frames})>1
    assert {'stand','walk-right','jump-right','climb-up','attack'} <= {f['action'] for f in frames}
    pickups = [e for e in trace['pickup_events'] if e['phase'].startswith(f'level-{level}-') and e['increment']>0]
    assert trace['treasure_pickup_observed'] and pickups
    assert all(e.get('owner_status') for e in trace['game_functions'] if e['entry_kind']=='function')
    assert trace['platform_calls'] and trace['platform_imports'], 'Incomplete platform census'
    assert sum(e['count'] for e in trace['platform_calls']) == trace['counts']['platform_calls']
    assert len(trace['platform_imports']) == trace['counts']['platform_imports']
    # The scripted labels alone do not prove a climb. The original must move
    # vertically with the up key held, without a jump input or horizontal drift.
    climbs = [(a,b) for a,b in zip(frames,frames[1:])
              if a['action']==b['action']=='climb-up' and
              a['player']['x']==b['player']['x'] and
              a['player']['y']>b['player']['y'] and
              a['player']['logic_state']==b['player']['logic_state']==27 and
              b['player']['input_mask'] & 0x4000000 and
              not b['player']['input_mask'] & 1]
    if level == 13:
        from Tests.NativeLevels.later_reference import ladder_tiles
        assert ladder_tiles(level) == 0, 'Review changed original ladder census'
        assert any(f['action'] == 'climb-up' and f['player']['input_mask'] & 0x4000000
                   for f in frames), 'Retain the actual up-key attempt'
    else:
        assert len(climbs)>=10, 'No sustained original upward climb observed'
    digest = fingerprint(out/'trace.json')
    assert closure['trace_sha256']==ownership['trace_sha256']==digest
    assert not closure['static_only'] and closure['level']==level
    assert closure['placed_classes']
    if level not in (11, 12):
        assert all(c['callback'] for c in closure['placed_classes'])
    for path,digest in closure['inputs_sha256'].items():
        assert digest == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path
    assert closure['world_sha256']==hashlib.sha256((ROOT/closure['world_source']).read_bytes()).hexdigest()
    assert 'CaptainClaw' in {c['name'] for c in closure['placed_classes']}
    assert not closure['commands_unmapped'], closure['commands_unmapped']
    if level in (7, 8, 9, 10, 11, 12, 13, 14):
        from Tests.NativeLevels.discovery import validate_later_closure
        item = validate_later_closure(closure, trace=trace, retained_plan=read('plan.json'))
        assert f'level-{WORDS[level]}-native-batch-join' in item['follow_up']
        assert item['app_status'] == 'unknown', 'Discovery does not certify app parity'
    functions = {r['address']:r for r in closure['functions']}
    assert len(functions)==closure['totals']['reachable']
    assignments = {}
    for task in queue['tasks']:
        for address in task.get('addresses',[]):
            assignments.setdefault(address,[]).append(task['id'])
    unresolved = {a for a,r in functions.items() if r['status'] not in ('admitted','native-reuse')}
    unresolved.update(r['address'] for r in ownership['rows'] if r['classification'] not in ('admitted','native-reuse'))
    assert all(len(assignments.get(a,[]))==1 for a in unresolved), {a:assignments.get(a) for a in unresolved if len(assignments.get(a,[]))!=1}
    prefix = f'level-{WORDS[level]}'
    batches = closure_batches(queue['tasks'], prefix)
    joins = [t for t in queue['tasks'] if t['id']==prefix+'-native-batch-join']
    # A join runs alone (exclusive) or, by owner decision 2026-10-24, beside other work when marked parallel.
    assert len(joins)==1 and (joins[0].get('exclusive') is True or joins[0].get('parallel') is True)
    positions = {t['id']: i for i,t in enumerate(queue['tasks'])}
    assert all(positions[t['id']]<positions[joins[0]['id']] for t in batches)
    assert all(d in positions for t in batches+[joins[0]] for d in t['depends_on'])
    required = {assignments[a][0] for a in unresolved}
    # Joins chain on the previous level's join, or (owner decision 2026-10-25, generic tooling since Level 4) on Level 4's.
    previous = {f'level-{WORDS[level-1]}-native-batch-join', 'level-four-native-batch-join'}
    assert required <= set(joins[0]['depends_on']), required-set(joins[0]['depends_on'])
    assert previous & set(joins[0]['depends_on']), previous
    print(json.dumps(dict(command=f'level-{level}-discovery-check',status='pass',played_ms=trace['played_ms'],
        treasure_pickups=len(pickups),climb_frames=len(climbs),trace_functions=len(ownership['rows']),trace_owner_counts=ownership['counts'],
        closure=closure['totals'],placed_classes=len(closure['placed_classes']),unresolved_union=len(unresolved),new_batches=len(batches))))


if __name__=='__main__':
    main()
