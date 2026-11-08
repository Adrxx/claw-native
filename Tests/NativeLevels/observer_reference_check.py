"""Level 11 observer provenance rejection controls; no game execution."""
import copy
import json
import pickle
from unittest.mock import patch
from Tests.NativeLevels import ROOT
from Tests.NativeLevels.storage import read_trace, open_artifact, CHECKPOINT_MAGIC, fingerprint
from Tests.NativeLevels.observer_reference import validate_observer_reference
from Tests.NativeLevels.trace import Blocked


def run_controls(trace):
    validate_observer_reference(trace, 11)
    checksum = fingerprint(ROOT/trace['observer_checkpoint']['path'])
    with open_artifact(ROOT/trace['observer_checkpoint']['path']) as stream:
        assert stream.read(len(CHECKPOINT_MAGIC)) == CHECKPOINT_MAGIC
        stream.read(8)
        header = pickle.load(stream)
    # No event stream is needed for metadata rejection controls.
    keys = ('physical_events', 'math_events')
    metadata = {k: v for k, v in trace.items() if k not in keys}
    changes = [
        ('incomplete', lambda t: t.update(status='blocked')),
        ('wrong-level', lambda t: t.update(level=12)),
        ('short-route', lambda t: t.update(played_ms=1)),
        ('wrong-executable', lambda t: t.update(executable_sha256='stale')),
        ('wrong-archive', lambda t: t['resources'].update(sha256='stale')),
        ('stale-clock', lambda t: t['xmidi_clock_adapter'].update(version='stale')),
        ('checkpoint-path', lambda t: t['observer_checkpoint'].update(path='work/other.gz')),
        ('checkpoint-hash', lambda t: t['observer_checkpoint'].update(sha256='stale')),
        ('prefix-hash', lambda t: t.update(prefix_checkpoint_sha256='stale')),
        ('missing-input', lambda t: t['observer_checkpoint']['inputs_sha256'].pop('Tests/NativeLevels/object_load_trace.py')),
        ('stale-loading-input', lambda t: t['observer_checkpoint']['inputs_sha256'].update({'Tests/NativeLevels/trace.py': 'stale'})),
        ('stale-runner', lambda t: t['observer_checkpoint'].update(runner_sha256='stale')),
        ('unelected-runner', lambda t: t['observer_checkpoint'].update(runner='work/other.py')),
        ('stale-string-adapter', lambda t: t['string_compare_boundary'].update(adapter_sha256='stale')),
        ('missing-completion', lambda t: t['completions'].pop()),
        ('missing-transition', lambda t: t.update(state_transitions=[])),
        ('unexpected-advancement', lambda t: t.update(checkpoint_advancement={'source_level': 10})),
    ]
    results = {}
    with patch('Tests.NativeLevels.observer_reference.fingerprint', return_value=checksum):
        for name, change in changes:
            candidate = copy.deepcopy(metadata)
            change(candidate)
            try:
                validate_observer_reference(candidate, 11)
            except Blocked:
                results[name] = 'refused'
            else:
                raise AssertionError(f'Observer reference accepted {name}')
        for field, value in (('target_level', 12), ('played_ms', 17),
                             ('checkpoint_inputs_sha256', {}), ('routes_fingerprint', 'stale')):
            candidate = copy.deepcopy(header)
            candidate['state'][field] = value
            with patch('Tests.NativeLevels.observer_reference.pickle.load', return_value=candidate):
                try:
                    validate_observer_reference(metadata, 11)
                except Blocked:
                    results['checkpoint-'+field] = 'refused'
                else:
                    raise AssertionError(f'Observer checkpoint accepted {field}')
    return results


if __name__ == '__main__':
    print(json.dumps(dict(status='pass', controls=run_controls(
        read_trace(ROOT/'work/level-11-map/trace.json')))))
