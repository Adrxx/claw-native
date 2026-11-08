"""Reject changed provenance on a retained final-level observer reference."""
import argparse
import copy
import json
from Tests.NativeLevels import output_dir
from Tests.NativeLevels.later_reference import validate_later_reference
from Tests.NativeLevels.storage import read_trace


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level',type=int,choices=(13,14),required=True)
    level=parser.parse_args().level
    trace=read_trace(output_dir(level)/'trace.json')
    validate_later_reference(trace,level)
    # Share only immutable disk event streams; changing metadata must never
    # alter the original retained observations or duplicate those large logs.
    mutations = {
        'wrong executable':lambda t:t.update(executable_sha256='0'*64),
        'stale route runner':lambda t:t['observer_checkpoint'].update(runner_sha256='0'*64),
        'stale source checkpoint':lambda t:t['observer_checkpoint'].update(sha256='0'*64),
        'stale advancement runner':lambda t:t['later_advancement'].update(runner_sha256='0'*64),
        'stale clock':lambda t:t['xmidi_clock_adapter'].update(hz=60),
        'stale CRT adapter':lambda t:t['string_compare_boundary'].update(adapter_sha256='0'*64),
    }
    if level == 14:
        mutations['missing frame budget'] = lambda t:t.update(frame_budget={})
        mutations['invalid frame diagnostics'] = lambda t:t.update(frames=[
            t['frames'][0], dict(t['frames'][1],
                observer_budget=dict(steps=0, wall_seconds=0))])
        mutations['wrong navigation runner'] = lambda t:t['observer_checkpoint'].update(
            runner='Tests/NativeLevels/later_trace.py')
    for name,mutate in mutations.items():
        changed=dict(trace)
        for field in ('observer_checkpoint','later_advancement','xmidi_clock_adapter','string_compare_boundary'):
            changed[field]=copy.deepcopy(trace[field])
        mutate(changed)
        try:validate_later_reference(changed,level)
        except AssertionError:pass
        else:raise AssertionError(f'Accepted {name}')
    report=dict(status='pass',level=level,controls=list(mutations))
    (output_dir(level)/'reference-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
