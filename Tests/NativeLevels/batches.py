"""Prepare bounded selected-level recovery tasks from the retained union; --write-queue installs them."""
from Tests.NativeLevels.storage import read_trace, fingerprint
import argparse
import hashlib
from pathlib import Path
import json
from collections import defaultdict
from Tests.NativeMenuBase.trace import ROOT
from Tests.NativeLevels import add_level, output_dir, WORDS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-queue', action='store_true')
    parser.add_argument('--mapping-task', help='Queue task owning this discovery (for a bounded mapping follow-up)')
    parser.add_argument('--output-dir', type=Path, help='Alternate local artifacts for preview')
    add_level(parser)
    args = parser.parse_args()
    level = args.level
    word = WORDS[level]
    out = (args.output_dir or output_dir(level)).resolve()
    if not out.resolve().is_relative_to((ROOT/"work").resolve()):
        parser.error("Derived output must stay under work/")
    prefix = f'level-{word}'
    mapping_tasks = {7: 'seven-eight', 8: 'seven-eight', 9: 'nine-ten',
                     10: 'nine-ten', 11: 'eleven-twelve', 12: 'eleven-twelve',
                     13: 'thirteen-fourteen', 14: 'thirteen-fourteen'}
    mapping_task = args.mapping_task or (f'parity-levels-{mapping_tasks[level]}-map-batch'
                    if level in mapping_tasks else f'{prefix}-trace-and-batch')
    closure = json.loads((out/'closure.json').read_text())
    if level in (11, 12, 13, 14):
        from Tests.NativeLevels.discovery import validate_later_closure
        validate_later_closure(closure)
    assert not args.write_queue or not closure['static_only'], 'Final trace required before queue edit'
    if args.write_queue:
        assert closure['trace_sha256'] == fingerprint(out/'trace.json'), 'Refresh the closure before queueing'
    ownership = json.loads((out/'ownership.json').read_text()) if (out/'ownership.json').exists() else dict(rows=[])
    trace_name = 'trace.json' if (out/'trace.json').exists() else 'trace.json.gz'
    retained_inputs = (trace_name, 'ownership.json', 'closure.json')
    if level in mapping_tasks:
        retained_inputs += ('plan.json',)
    rows = {r['address']:r for r in closure['functions']}
    missing = {a for a,r in rows.items() if r['status'] not in ('admitted','native-reuse')}
    missing.update(r['address'] for r in ownership['rows'] if r['classification'] not in ('admitted','native-reuse'))
    # Re-read the shared queue immediately before deriving the edit. Refuse to
    # overwrite another session's change between this read and atomic replace.
    path = ROOT/'tools/queue.json'
    before = path.read_bytes()
    queue = json.loads(before)
    assigned = {}
    duplicates = {}
    for t in queue['tasks']:
        if t.get("addresses"):
            for a in t.get('addresses', []):
                if a in missing:
                    if a in assigned:
                        duplicates.setdefault(a, [assigned[a]]).append(t['id'])
                    assigned.setdefault(a,t['id'])
    assert not duplicates, f"Existing queue duplicates need reconciliation: {duplicates}"
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
    if level == 3:
        reviewed = {
            'rope': '403100 4031c0 4035a0 403850 4038d0 465450',
            'cutthroat': '437a90 438010 438030 438100 4384f0 4385b0 4386d0 4388a0 438900 438a90',
            'robber-thief': '485330 485870 485890 485960 485d60 485d90 485ec0 485f00 486090',
        }
    elif level == 4:
        reviewed = {
            'katherine-core-springboard': '41e810 453d30 453df0 4542f0 454310 4543e0 4547c0 4548c0',
            'katherine-states': '454a10 454b90 454c20 454cb0 4550e0 455230 455280 4552d0 455360 4553a0',
        }
    elif level == 5:
        reviewed = {
            'break-single-plank': '40f870 40fb30 40fde0 40fe20 488e30 488ef0 4890f0 4894b0 489530 4895b0 489600 489640 489680',
            'seagull-core': '443170 443200 443220 486f50 4872b0 4872d0 4873a0 4877a0 4877d0 487800 487830',
            'seagull-states': '406da0 467ea0 4879a0 487b80 487f20 487f80 488330 488390 488420 488550 488750',
            'town-guard-core': '496110 496840 496860 496990 497040 497060 497130 497510',
            'town-guard-states-switch': '453bd0 483dc0 497750 497970 4979b0 497a50 497ab0 497b00 497c50 497dc0',
        }
    elif level == 6:
        reviewed = {
            'vents-and-blowers': '4486e0 448850 448b00 448b50 448e30 4490e0 449270 4492c0',
            'wolvington-projectile': '410340 411cf0 411e70 412150 458010',
            'wolvington-core': '49fb30 49fbf0 4a0140 4a0160 4a0230 4a0740 4a0800',
            'wolvington-states': '4a0960 4a0a90 4a0ae0 4a0b30 4a0c10 4a0cf0 4a0ec0 4a0f40 4a0fd0 4a1020 4a10b0 4a10f0 4a1250',
        }
    elif level == 7:
        reviewed = {
            'bear-sailor': '409920 409ee0 409f70 40a040 40a490 40a610 40a690 40a740 40a7f0 40aa40 40aa70 40ab20 435130',
            'crab-bomb-shared': '41fce0 41fe80 431cd0 431df0 4320d0 432250 432460 4324e0 432550 432560',
            'crab-nest': '432690 432a60 432c20 432c50 432d00 432d50 432dd0',
            'hermit-crab-core': '449d60 44a380 44aa90 44ac40 44ac60 44acd0 44ad10 44ade0 44ae30 44aef0 44af70 44afd0',
            'hermit-crab-combat': '44b130 44b200 44b2b0 44b300 44b480 44b6a0 44b780 44b7e0 44b860 44b960 44b9e0 44bb40 44bc50',
            'red-tail-pirate': '4828e0 483090 4830b0 483180 483560 4837b0 483ae0 483d20 483e10 483f30 484210 484240 484260',
        }
    elif level == 8:
        reviewed = {
            'cannon-controls': '414de0 415090 415210 415250 4152e0 415470 415840 4159b0 4159f0 415a60',
            'gabriel-core': '405f60 443290 4433b0 443ab0 444120 444140 4441b0 4441f0 4442c0 444330',
            'gabriel-attacks-pirate': '483e40 4444d0 4445d0 4446f0 444760 444850 444960 444aa0 444b70 444c20 444d00 444d90 444f80',
            'gabriel-death': '445090 4452d0 4455b0 445600 445660 4456c0 445720 445810 445950 48cf90',
            'gabriel-bomb': '4459d0 445af0 445ef0 446130 446340 4463f0 446490',
            'gabriel-cannon': '446550 446670 446a70 446c20 446ca0 446d70 446e10 446eb0',
        }
    elif level == 9:
        reviewed = {
            'conveyor': '431440 431810 431a70 431b10 431b40 431b70 431bd0 431c90',
            'crazy-hook': '434250 434860 434880 434950 434d30 434eb0 4350e0 435140 4353a0 4354e0 4355a0 435600 435700 435720 435740',
            'peg-leg-core': '468ad0 468eb0 469480 4694a0 469510 469570 469840 469a40 469c40 469e20',
            'peg-leg-roll': '46a000 46a040 46a1c0 46a280 46a420 46a430 46a5b0 46a610 46a650 46a690',
            'projectile-hazards': '462330 48a8c0 497f70 4981c0 498580 498590 4985f0 498690 4988b0 4988f0',
        }
    elif level == 10:
        reviewed = {
            'marrow-core': '4587a0 458d40 4593d0 4593f0 459440 459470 459660 4596a0 4599b0 459ad0',
            'marrow-combat': '459b70 459c80 459d60 459ee0 459f10 459f90 45a0b0 45a260',
            'marrow-floor': '45a400 45a7c0 45a940 45a980 45a9f0 45aa40 45aa90 45aae0 45ab40 45abc0 45ac40',
            'parrot-core': '465640 465cc0 465ce0 465db0 4663d0 4664d0 466580 466730',
            'parrot-combat': '466790 466a80 466e40 466ea0 467280 4672d0 467470 467530 467700 4677b0 4679a0',
            'parrot-states': '467ae0 467b50 467bf0 467c60 467c90 467e30',
        }
    elif level == 11:
        reviewed = {
            'siren-trident-projectiles': '4104c0 410580 412880 4129d0 412cb0 412ce0 413280 413470',
            'fish-states': '441d00 4420e0 4423e0 442400 442470 442640 4427d0 442b00 442cb0 442d80 442e90 442f70 4430f0',
            'laser-state': '455449 455490 455600 4558b0 455960',
            'mercat-states': '460c50 460ea0 461360 4614c0 4616e0',
            'siren-states': '489850 489c50 48a0d0 48a0f0 48a160 48a240 48a2e0 48a420 48a590 48a7d0',
        }
    elif level == 12:
        reviewed = {
            'aquatis-core': '4041f0 404310 404990 404e20 4050b0 405240 4053d0 4054c0 4055e0 405740 4058b0 405af0',
            'aquatis-states': '4051a0 405440 405540 405640 4057a0 4059e0 405a60 405d50 405df0 405ed0 405fa0',
            'aquatis-crack': '406520 4068f0 406af0 406b10 406b50 406c40 406cb0',
            'aquatis-dynamite': '406ef0 4071a0 4072f0 407310 407360',
            'aquatis-stalactite': '407500 4078b0 407bd0 407bf0 407c10 407c40 407cc0 407d50 407e40 407e90 407f20 407f80 407fb0',
            'shake-state': '488870 4889e0 488c90 488cd0 488cf0',
            'stalactite-states': '48e5c0 48e990 48ed10 48ed70 48edd0 48ee10 48ee30 48eee0 48ef00 48ef90 48efd0 48f040',
            'tentacle-core': '4923e0 4928f0 492c40 492c60 492ce0 492d30 492da0 492f70 492fb0 493110 493450 4936d0',
            'tentacle-states': '492ec0 493030 493200 493550 493600 493680 493830 493890 493920 4939a0 493be0',
        }
    elif level in (13, 14):
        from Tests.NativeLevels.later_batches import reviewed_groups
        reviewed = reviewed_groups(level)
    elif level != 2:
        reviewed = {}
    groups=[]; labels=[]; covered=set()
    for label, text in reviewed.items():
        group = [hex(int(a,16)) for a in text.split() if hex(int(a,16)) in fresh]
        if group:
            groups.append(group); labels.append(label); covered.update(group)
    remaining=sorted(set(fresh)-covered,key=lambda a:int(a,16))
    for i in range(0,len(remaining),10):
        groups.append(remaining[i:i+10]);labels.append(f'traced-services-{i//10+1:02d}')
    # Balance a short final group with its preceding batch.
    if len(groups)>1 and len(groups[-1])<5:
        needed=5-len(groups[-1])
        groups[-1][:0]=groups[-2][-needed:]
        del groups[-2][-needed:]
    small=[(g,l) for g,l in zip(groups,labels) if len(g)<5]
    normal=[(g,l) for g,l in zip(groups,labels) if len(g)>=5]
    for group,label in small:
        destination=next((g for g,l in normal if len(g)+len(group)<=15),None)
        assert destination is not None, 'Review a small remaining batch manually'
        destination.extend(group)
    groups=[g for g,l in normal];labels=[l for g,l in normal]
    assert all(5<=len(g)<=15 for g in groups)
    flattened = [a for group in groups for a in group]
    assert len(flattened)==len(set(flattened)) and set(flattened)==set(fresh), "Batch partition is not exact"
    tasks=[]
    for i,(label,group) in enumerate(zip(labels,groups),1):
        tid=f'{prefix}-batch-{label}-01'
        for a in group:
            assigned[a]=tid
        owners=sorted({rows[a]['owner'] for a in group if a in rows and rows[a]['owner']})
        tasks.append(dict(id=tid,title=f'Level {level} closure: {label.replace(chr(45),chr(32))} ({len(group)} entries)',
            model='cheaper',state='open',depends_on=[],addresses=group,
            why='Original Level 2 trace and static class/state/created-vtable closure list these entries without current admission. Existing legacy owners are reuse candidates, not proof of admission.',
            start_with=[str((out/p).relative_to(ROOT)) for p in retained_inputs]+
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
        t['depends_on']=sorted((dependencies[tid]-cyclic) | ({mapping_task} if level > 2 else set()))
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
    join=dict(id=f'{prefix}-native-batch-join',title=f'Join admitted Level {level} loading and gameplay in the native host',
        model='strong',state='open',exclusive=True,
        depends_on=sorted(set(required+[mapping_task, 'end-of-level-native-batch-join' if level == 2 else f'level-{WORDS[level-1]}-native-batch-join'])),
        start_with=['Tests/NativeLevels/trace.py','Tests/NativeLevels/routes.py','Tests/NativeLevels/plan.py','Tests/NativeLevels/check.py','Tests/NativeLevels/service_check.py','Tests/NativeLevels/regression.py','Tests/NativeLevelTwo/service_check.py',
            *[str((out/p).relative_to(ROOT)) for p in retained_inputs],
            'tools/workflows/NATIVE-INTEGRATION.md','Sources/ClawNativeScene.swift','Sources/ClawNativeCanonicalHost.swift'],
        scope='Join current canonical owners and existing native physical services for original Level 2 loading and the retained sixty-second walk/jump/climb/attack/treasure route, including the observed death and respawn with retained score/counter. Require all closure and trace batches including cyclic peers. Preserve missing-service faults, ownership and original state/actor/global bytes. No guest execution, scripted game success or return-zero fallbacks may stand in for game bodies. Use the smallest original/native boundary comparisons for new joins, then coordinate visible app work with the Claude orchestrator.',
        done_when='Focused original/native comparisons cross actual Level 2 attachment and dispatch for the retained route, with treasure counter changes, ordered service calls and missing-service negative controls; every static closure entry has a reviewed current canonical/native owner. Record comparison commands separately from compilation and orchestrator app/device acceptance.')
    for task in tasks + [join]:
        task['scope'] += ' Read the retained trace with Tests.NativeLevels.storage.read_trace so large event streams stay on disk.'
        for field in ('why', 'scope', 'done_when'):
            if field in task:
                task[field] = task[field].replace('Level 2', f'Level {level}')
        if task is join:
            task['scope'] = task['scope'].replace('including the observed death and respawn with retained score/counter', 'including every observed state transition')
    for task in tasks:
        task['scope'] += f' Refresh ownership with work/test-env/bin/python -m Tests.NativeLevels.plan --level {level}.'
    if level == 4:
        join['start_with'].append('work/level-4-map/plan.json')
        join['scope'] += (' Replay the fixed physical input schedule with work/test-env/bin/python -m '
                          'Tests.NativeLevels.trace --level 4 --plan work/level-4-map/plan.json; '
                          'the original route climbs the opening springboards, fights the upper enemies, '
                          'jumps to the first ladder and repeatedly climbs both ways.')
    if level == 5:
        join['start_with'].append('work/level-5-map/plan.json')
        join['scope'] += (' Replay the retained physical input schedule with work/test-env/bin/python -m '
                          'Tests.NativeLevels.trace --level 5 --plan work/level-5-map/plan.json. '
                          'Use the recorded original frames to verify movement, climbing, attacks and pickups.')
    if level == 6:
        join['start_with'].append('work/level-6-map/plan.json')
        join['scope'] += (' Replay the retained physical input schedule with work/test-env/bin/python -m '
                          'Tests.NativeLevels.trace --level 6 --plan work/level-6-map/plan.json. '
                          'Use the recorded original frames to verify movement, climbing, attacks and pickups.')
    if level in (7, 8, 9, 10, 11, 12, 13, 14):
        join['scope'] += (f' Replay the retained physical input schedule with work/test-env/bin/python -m '
                          f'Tests.NativeLevels.trace --level {level} --plan work/level-{level}-map/plan.json. '
                          'Use the recorded original frames to verify movement, climbing, attacks and pickups. '
                          'Static closure includes every placed boss and unique mechanism even when absent from the short route.')
    if level in (11, 12):
        join['start_with'] += ['Tests/NativeLevels/advance.py', 'Tests/NativeLevels/discovery.py',
                               'Tests/NativeLevels/object_loading.py', 'Tests/NativeLevels/object_load_trace.py']
        join['scope'] += (' Use the tempo-aware original progression in Tests.NativeLevels.advance with a '
                          'hash-valid start checkpoint; retain its provenance and the actual plan. '
                          'Include SirenBullet and TridentBullet created vtables, and for Level 12 include '
                          'Aquatis, AquatisCrack, AquatisDynamite, AquatisStalactite, Tentacle and Stalactite. '
                          'Preserve the original-verified Sign load outcome; never invent a callback.')
    if level == 10:
        join['start_with'].append('Tests/NativeLevels/advance.py')
        join['scope'] += (' The retained trace advances the hash-validated Level 9 start checkpoint '
                          'through original MPSCULLY/results input. Replay using work/test-env/bin/python '
                          '-m Tests.NativeLevels.advance --level 10 --from-level 9 '
                          '--source-checkpoint work/level-9-map/start.checkpoint '
                          '--checkpoint work/level-10-map/start.checkpoint '
                          '--plan work/level-10-map/plan.json. Include Marrow, MarrowFloor and Parrot '
                          'entry/state/created-vtable surfaces even though the short route is near the start.')
    if level in (13, 14):
        join['exclusive'] = False
        join['parallel'] = True
        join['depends_on'] = sorted(set(join['depends_on']) | {'level-eight-batch-base-x87-environment'})
        join['start_with'] += ['Tests/NativeLevels/later_trace.py', 'Tests/NativeLevels/later_reference.py',
                               'Tests/NativeLevels/later_service_check.py', 'Tests/NativeLevels/later_batches.py',
                               'Tests/NativeLevels/later_reference_check.py', 'Tests/NativeLevels/later_mapping_check.py',
                               str((out/'static-review.json').relative_to(ROOT))]
        join['scope'] += (' Retained observer checkpoints are discovery evidence. Require an independent '
                          'original prefix for native comparison. Preserve RedTail and wind/knife/bullet '
                          'surfaces for Level 13, and Omar/shield/projectile, TigerGuard and all lava '
                          'surfaces for Level 14. Level 14 must cover the owner-reported first-checkpoint '
                          'fault at 0x494460. Keep the previous level progression dependency. '
                          'Do not edit Tests/clawparity/; queue shared harness needs separately as exclusive.')
        if level == 13:
            join['scope'] += (' The original Level 13 gameplay plane has zero ladder tiles. '
                              'Its retained up-key input is an attempt, not a certified climb. '
                              'Match that original outcome and retain every placed rope surface.')
        for task in tasks:
            task['exclusive'] = False
            task['parallel'] = True
    tasks.append(join)
    result=dict(trace_sha256=closure['trace_sha256'],unresolved_union=len(missing),new_functions=len(fresh),
        reused_tasks=sorted(set(assigned[a] for a in missing if a not in fresh)),tasks=tasks)
    (out/'batches.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.write_queue:
        trace = read_trace(out/'trace.json')
        if level in (11, 12, 13, 14):
            validate_later_closure(closure, trace=trace,
                retained_plan=json.loads((out/'plan.json').read_text()))
        played = trace['level_two_played_ms'] if level == 2 else trace['played_ms']
        pickup = trace['level_two_treasure_pickup_observed'] if level == 2 else trace['treasure_pickup_observed']
        assert trace['status']=='pass' and played>=60000 and pickup, 'Complete original route required'
        ids={t['id'] for t in queue['tasks']}
        assert not ids.intersection(t['id'] for t in tasks), 'Tasks already installed'
        pos=next(i for i,t in enumerate(queue['tasks']) if t['id']==mapping_task)+1
        if level >= 8:
            previous = next(i for i,t in enumerate(queue['tasks'])
                            if t['id']==f'level-{WORDS[level-1]}-native-batch-join')
            pos = max(pos, previous+1)
        queue['tasks'][pos:pos]=tasks
        assert path.read_bytes()==before, 'Shared queue changed; rerun'
        temporary=path.with_name(f'queue.{prefix}.tmp')
        temporary.write_text(json.dumps(queue,indent=2)+'\n')
        temporary.replace(path)
    print(json.dumps(dict(status='pass',unresolved_union=len(missing),new_functions=len(fresh),
        new_batches=len(groups),reused_tasks=result['reused_tasks'],queue_written=args.write_queue)))


if __name__=='__main__':
    main()
