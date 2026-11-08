"""Check both final-level discovery censuses and shared batch dependencies."""
import argparse
import json
import subprocess
import sys
from Tests.NativeLevels import ROOT, WORDS, output_dir
from Tests.NativeLevels.storage import read_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--levels', type=int, choices=(13,14), nargs='+', default=[13,14])
    levels = parser.parse_args().levels
    queue = json.loads((ROOT/'tools/queue.json').read_text())['tasks']
    by_id = {task['id']:task for task in queue}
    positions = {task['id']:i for i,task in enumerate(queue)}
    assignments = {}
    for task in queue:
        for address in task.get('addresses',[]):
            assignments.setdefault(address,[]).append(task['id'])
    summary = []
    for level in levels:
        subprocess.run([sys.executable,'-m','Tests.NativeLevels.check','--level',str(level)],check=True)
        out = output_dir(level)
        closure = json.loads((out/'closure.json').read_text())
        ownership = json.loads((out/'ownership.json').read_text())
        unresolved = {r['address'] for r in closure['functions'] if r['status'] not in ('admitted','native-reuse')}
        unresolved |= {r['address'] for r in ownership['rows'] if r['classification'] not in ('admitted','native-reuse')}
        required = set()
        for address in unresolved:
            assert len(assignments.get(address,[])) == 1, address
            required.add(assignments[address][0])
        join_id = f'level-{WORDS[level]}-native-batch-join'
        join = by_id[join_id]
        previous = f'level-{WORDS[level-1]}-native-batch-join'
        assert {previous,'parity-levels-thirteen-fourteen-map-batch',
                'level-eight-batch-base-x87-environment'} | required <= set(join['depends_on'])
        if level == 14:
            assert 'level-fourteen-complete-route-and-native-join-map' in join['depends_on']
        assert join.get('exclusive') is False and join.get('parallel') is True
        for task in queue:
            if task['id'].startswith(f'level-{WORDS[level]}-batch-'):
                assert task.get('exclusive') is False and task.get('parallel') is True
        for task_id in required:
            assert positions[task_id] < positions[join_id]
        trace = read_trace(out/'trace.json')
        assert trace['plan'] == json.loads((out/'plan.json').read_text())
        assert trace['later_advancement']['destination'] == level
        assert all(5 <= len(by_id[tid].get('addresses',[])) <= 15
                   for tid in required if tid.startswith(('level-thirteen-batch-','level-fourteen-batch-')))
        summary.append(dict(level=level,played_ms=trace['played_ms'],closure=closure['totals'],
            unresolved=len(unresolved),required_batches=sorted(required),join=join_id,
            app_parity='unknown'))
    report = dict(status='pass',levels=summary,incomplete_levels=sorted({13,14}-set(levels)),
        scope='Selected original discovery and queue coverage only; no app parity')
    (output_dir(13)/'completion-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
