"""Check discovery evidence and bounded queue coverage, never family admission."""
import argparse
import json
from Tests.NativeLevelOne.plan import ROOT, census, read, fingerprint


def check(allow_prefix=False):
    trace_path=ROOT/'work/level-one-map/trace.json'
    trace=read(trace_path)
    ownership=census(trace_path)
    queue=read(ROOT/'tools/queue.json')
    contract=queue['level_one_batch_contract']
    tasks={t['id']:t for t in queue['tasks']}
    positions={t['id']:i for i,t in enumerate(queue['tasks'])}
    assert trace['tracer_sha256']==fingerprint(ROOT/'Tests/NativeLevelOne/trace.py')
    assert trace['menu_tracer_sha256']==fingerprint(ROOT/'Tests/NativeMenuBase/trace.py')
    assert trace['executable_sha256']=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
    assert contract['trace_sha256']==fingerprint(trace_path)
    assert trace['resources']['sha256']=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
    states=[n['state']['menu_id'] for n in trace['navigation'] if 'state' in n]
    assert states[:3]==[10000,10001,11001],states
    assert any(n.get('wparam')==0x807f and n.get('lparam')==1 for n in trace['navigation'])
    if trace['status']!='pass':
        assert allow_prefix, 'Incomplete original gameplay census: '+str(trace['stop'])
        assert trace['stop']['address']==contract['stop']['address']
        assert contract['missing_stand_in'] and trace['stop']['last_transfer']['site']
        assert contract['continuation'] in tasks
        assert tasks[contract['continuation']]['exclusive']
        assert contract['continuation'] in tasks[contract['native_join']]['depends_on']
    else:
        assert trace['status']=='pass' and trace['stop'] is None
        assert trace['level_one_loaded'] and trace['treasure_pickup_observed']
        assert not trace['resumed_checkpoint'], 'Final evidence must be a fresh original run'
        assert trace['input_bindings']['keys']==dict(left=37,right=39,up=38,down=40,jump=32,attack=17)
        frames=trace['play_frames']
        assert frames[0]['elapsed_ms']==0 and frames[-1]['elapsed_ms']>=30000
        assert frames[-1]['elapsed_ms']==trace['completed_play_ms']
        assert frames[-1]['player']['game_ms']-frames[0]['player']['game_ms']>=30000
        assert all(0<b['elapsed_ms']-a['elapsed_ms']<=100 for a,b in zip(frames,frames[1:]))
        assert all(f['player']['level']==1 and f['player']['vtable']=='0x50c264' for f in frames)
        assert {a['action'] for a in trace['scripted_input']}<={f['action'] for f in frames}
        assert len({f['player']['x'] for f in frames})>1, 'No observed player movement'
        assert len({f['player']['y'] for f in frames})>1, 'No observed vertical player movement'
        for action,mask in (('walk-right',0x2000000),('jump-right',0x2000001),('attack',2)):
            assert any(f['action']==action and f['player']['input_mask']&mask==mask for f in frames),action
        assert any(e['increment']==1 and e['phase'].startswith('play-') and
            sum(e['after'])-sum(e['before'])==1 for e in trace['pickup_events'])
        assert sum(frames[-1]['player']['treasure_counts'])>sum(frames[0]['player']['treasure_counts'])
        assert frames[-1]['player']['score']>frames[0]['player']['score']
        jump=[f['player'] for f in frames if f['action']=='jump-right']
        assert any(b['y']<a['y'] for a,b in zip(jump,jump[1:])), 'Jump input never moved the player upward'
        # Sword attacks keep the coarse standing state. Require the reached
        # original breakable-object and loot paths during the attack instead.
        entries={e['address']:e for e in trace['game_functions']}
        for address in ('0x433ed0','0x42df90'):
            assert 'play-attack' in entries[address]['phases'], 'Attack did not reach original crate/loot logic'
    rows=ownership['rows']
    assert len(rows)==trace['counts']['game_functions']==sum(ownership['counts'].values())
    assert len({r['address'] for r in rows})==len(rows)
    unresolved={r['address'] for r in rows if r['classification'] in ('owned-but-unadmitted','partial','unowned')}
    assert contract['functions_executed']==len(rows)
    assert contract['unresolved_functions']==len(unresolved)
    assigned=[]
    for identifier in contract['batches']:
        task=tasks[identifier]
        assert '-admit-' in identifier or '-batch-' in identifier
        assert 5<=len(task['addresses'])<=15,(identifier,len(task['addresses']))
        assigned.extend(task['addresses'])
        assert task['depends_on']
        assert all(d in tasks for d in task['depends_on'])
        assert positions[identifier]<positions['new-game-to-level-one']
        assert identifier in tasks['new-game-to-level-one']['depends_on']
        assert identifier in tasks[contract['native_join']]['depends_on']
    assert len(assigned)==len(set(assigned)), 'Duplicate batch ownership'
    # Preserve already queued batches as their owners become admitted. Their
    # entries must remain observed game entries; all current gaps stay assigned.
    assert unresolved<=set(assigned), sorted(unresolved-set(assigned))
    assert set(assigned)<={r['address'] for r in rows if r['classification']!='native-reuse'}
    assert contract['native_join'] in tasks['new-game-to-level-one']['depends_on']
    visiting=set();visited=set()
    def visit(identifier):
        assert identifier not in visiting, 'Dependency cycle: '+identifier
        if identifier in visited:return
        visiting.add(identifier)
        for dependency in tasks[identifier].get('depends_on',[]):
            assert dependency in tasks, dependency
            visit(dependency)
        visiting.remove(identifier);visited.add(identifier)
    visit('new-game-to-level-one')
    assert ownership['counts']==contract['ownership_counts']
    result=dict(status='partial' if trace['stop'] else 'pass',scope='Original discovery and queue check only; no native parity or admission',
        functions_executed=len(rows),counts=ownership['counts'],platform_iat_imports=trace['counts']['platform_imports'],
        platform_import_thunks=[p for p in trace['platform_calls'] if p['name'] in ('DirectDrawCreate','DirectSoundCreate')],
        batches=len(contract['batches']),stop=trace['stop'],completed_play_ms=trace['completed_play_ms'])
    (ROOT/'work/level-one-map/ownership.json').write_text(json.dumps(ownership,indent=2)+'\n')
    (ROOT/'work/level-one-map/check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-prefix',action='store_true',help='Validate retained partial evidence without claiming completed play')
    check(parser.parse_args().allow_prefix)
