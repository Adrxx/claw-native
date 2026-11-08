"""Prepare bounded Level 2 recovery tasks from the retained union; --write-queue installs them."""
from Tests.NativeLevels.storage import read_trace
import argparse
import hashlib
import json
from collections import defaultdict
from Tests.NativeMenuBase.trace import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-queue', action='store_true')
    args = parser.parse_args()
    out = ROOT/'work/level-two-map'
    closure = json.loads((out/'closure.json').read_text())
    assert not args.write_queue or not closure['static_only'], 'Final trace required before queue edit'
    ownership = json.loads((out/'ownership.json').read_text()) if (out/'ownership.json').exists() else dict(rows=[])
    rows = {r['address']:r for r in closure['functions']}
    missing = {a for a,r in rows.items() if r['status'] not in ('admitted','native-reuse')}
    missing.update(r['address'] for r in ownership['rows'] if r['classification'] not in ('admitted','native-reuse'))
    # Re-read the shared queue immediately before deriving the edit. Refuse to
    # overwrite another session's change between this read and atomic replace.
    path = ROOT/'tools/queue.json'
    before = path.read_bytes()
    queue = json.loads(before)
    assigned = {}
    for t in queue['tasks']:
        if t['state'] != 'done':
            for a in t.get('addresses', []):
                if a in missing:
                    assigned.setdefault(a,t['id'])
    fresh = sorted(missing-assigned.keys(), key=lambda a:int(a,16))
    # Reviewed semantic groups from the static closure. The boss's shared
    # helpers and body/state entries are separate bounded families; cannon
    # object actions and projectile transport have distinct call surfaces.
    reviewed = {
        'raux-shared': '404e40 405060 40e0d0 40e190 40e280 40e560 40e580 40e660 420590 44e620 455350 4a07e0',
        'raux-core': '47e210 47e2d0 47e7f0 47e810 47e8e0 47ece0 47eeb0 47eef0',
        'raux-states': '47f020 47f0c0 47f160 47f290 47f600 47f680 47f6b0',
        'cannon-projectiles': '414030 4141f0 414b20 414be0 495ec0 495f90',
        'cannon-objects': '4145b0 4145f0 414640 414660 4146b0 414860 4148b0 414a60 4493c0 449480 449590',
        'punk-rat': '474330 4743f0 4746f0 474710 4747e0 474bc0 474c50 474d00 474db0 474e10 474e60 474ec0',
        'end-gem': '40e5c0 4205b0 43ca60 43cb20 43cdc0 43d070 43d0f0 4701b0',
    }
    groups=[]; labels=[]; covered=set()
    for label, text in reviewed.items():
        group = [hex(int(a,16)) for a in text.split() if hex(int(a,16)) in fresh]
        if group:
            groups.append(group); labels.append(label); covered.update(group)
    remaining=sorted(set(fresh)-covered,key=lambda a:int(a,16))
    for i in range(0,len(remaining),10):
        groups.append(remaining[i:i+10]);labels.append(f'traced-services-{i//10+1:02d}')
    small=[(g,l) for g,l in zip(groups,labels) if len(g)<5]
    normal=[(g,l) for g,l in zip(groups,labels) if len(g)>=5]
    for group,label in small:
        destination=next((g for g,l in normal if len(g)+len(group)<=15),None)
        assert destination is not None, 'Review a small remaining batch manually'
        destination.extend(group)
    groups=[g for g,l in normal];labels=[l for g,l in normal]
    assert all(5<=len(g)<=15 for g in groups)
    tasks=[]
    for i,(label,group) in enumerate(zip(labels,groups),1):
        tid=f'level-two-batch-{label}-01'
        for a in group:
            assigned[a]=tid
        owners=sorted({rows[a]['owner'] for a in group if a in rows and rows[a]['owner']})
        tasks.append(dict(id=tid,title=f'Level 2 closure: {label.replace(chr(45),chr(32))} ({len(group)} entries)',
            model='cheaper',state='open',depends_on=[],addresses=group,
            why='Original Level 2 trace and static class/state/created-vtable closure list these entries without current admission. Existing legacy owners are reuse candidates, not proof of admission.',
            start_with=['work/level-two-map/trace.json','work/level-two-map/ownership.json','work/level-two-map/closure.json']+
                [f'Tests/families/{o}.json' for o in owners if (ROOT/f'Tests/families/{o}.json').exists()],
            scope='Review listed game entries and reuse existing bodies where available. Recover or adapt only the missing owned surface through fresh case-author and translator workers and the gate pipeline in docs/OPERATING.md. Keep each family at most about 600 cases with seed-independent coverage; at most 15 functions per batch. Borrow admitted bodies with shared_sources. Do not edit Tests/clawparity/, lower thresholds, or replace game bodies with fixtures. Missing harness support requires an exclusive prerequisite. Do not build or open the app.',
            done_when='Every listed address has a current admitted canonical owner, shown by make gate FAMILY=<id> ARGS="--record --jobs 1" and the refreshed Level 2 ownership/closure census.'))
    # Follow through admitted helpers to the next unadmitted boundary. Cyclic
    # batches retain original-backed gate callees; the native join requires all
    # peers. Only acyclic prerequisites enter depends_on to avoid deadlock.
    edges=closure['edges']
    dependencies=defaultdict(set)
    for t in tasks:
        stack=list(t['addresses']);seen=set(stack)
        while stack:
            a=stack.pop()
            for b in edges.get(a,[]):
                owner=assigned.get(b)
                if owner and owner!=t['id']:
                    dependencies[t['id']].add(owner)
                    continue
                if b not in seen:
                    seen.add(b);stack.append(b)
    def reaches(a,b):
        todo=[a];seen=set()
        while todo:
            x=todo.pop()
            if x==b:return True
            if x in seen:continue
            seen.add(x);todo.extend(dependencies[x])
        return False
    for t in tasks:
        tid=t['id']
        cyclic={d for d in dependencies[tid] if reaches(d,tid)}
        t['depends_on']=sorted(dependencies[tid]-cyclic)
        if cyclic:
            t['co_required']=sorted(cyclic)
            t['scope']+=' Cyclic peers in co_required remain original-backed gate callees until all are admitted; none may be omitted from the native join.'
    ordered=[]; todo=list(tasks); ids={t['id'] for t in tasks}
    while todo:
        ready=next((t for t in todo if not (set(t['depends_on']) & ids)-{x['id'] for x in ordered}),None)
        assert ready is not None, 'Unexpected prerequisite cycle'
        ordered.append(ready); todo.remove(ready)
    tasks=ordered
    required=sorted(set(assigned.values()))
    join=dict(id='level-two-native-batch-join',title='Join admitted Level 2 loading and gameplay in the native host',
        model='strong',state='open',exclusive=True,
        depends_on=sorted(set(required+['level-two-trace-and-batch','end-of-level-native-batch-join'])),
        start_with=['Tests/NativeLevelTwo/trace.py','Tests/NativeLevelTwo/plan.py','Tests/NativeLevelTwo/check.py','Tests/NativeLevelTwo/service_check.py',
            'work/level-two-map/trace.json','work/level-two-map/ownership.json','work/level-two-map/closure.json',
            'tools/workflows/NATIVE-INTEGRATION.md','Sources/ClawNativeScene.swift','Sources/ClawNativeCanonicalHost.swift'],
        scope='Join current canonical owners and existing native physical services for original Level 2 loading and the retained sixty-second walk/jump/attack/treasure route, including the observed death and respawn with retained score/counter. Require all closure and trace batches including cyclic peers. Preserve missing-service faults, ownership and original state/actor/global bytes. No guest execution, scripted game success or return-zero fallbacks may stand in for game bodies. Use the smallest original/native boundary comparisons for new joins, then coordinate visible app work with the Claude orchestrator.',
        done_when='Focused original/native comparisons cross actual Level 2 attachment and dispatch for the retained route, with treasure counter changes, ordered service calls and missing-service negative controls; every static closure entry has a reviewed current canonical/native owner. Record comparison commands separately from compilation and orchestrator app/device acceptance.')
    tasks.append(join)
    result=dict(trace_sha256=closure['trace_sha256'],unresolved_union=len(missing),new_functions=len(fresh),
        reused_tasks=sorted(set(assigned[a] for a in missing if a not in fresh)),tasks=tasks)
    (out/'batches.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.write_queue:
        trace = read_trace(out/'trace.json')
        assert trace['status']=='pass' and trace['level_two_played_ms']>=60000 and trace['level_two_treasure_pickup_observed'], 'Complete original route required'
        ids={t['id'] for t in queue['tasks']}
        assert not ids.intersection(t['id'] for t in tasks), 'Tasks already installed'
        pos=next(i for i,t in enumerate(queue['tasks']) if t['id']=='level-two-trace-and-batch')+1
        queue['tasks'][pos:pos]=tasks
        assert path.read_bytes()==before, 'Shared queue changed; rerun'
        temporary=path.with_name('queue.level-two.tmp')
        temporary.write_text(json.dumps(queue,indent=2)+'\n')
        temporary.replace(path)
    print(json.dumps(dict(status='pass',unresolved_union=len(missing),new_functions=len(fresh),
        new_batches=len(groups),reused_tasks=result['reused_tasks'],queue_written=args.write_queue)))


if __name__=='__main__':
    main()
