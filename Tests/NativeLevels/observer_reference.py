"""Validate the retained later-level observers without restoring it into native code."""
import json
import pickle
from Tests.NativeLevels import ROOT
from Tests.NativeLevels.storage import CHECKPOINT_MAGIC, fingerprint, open_artifact
from Tests.NativeLevels.object_load_trace import ObjectLoadTrace
from Tests.NativeLevels.provenance import TRACE_INPUTS, EXE_SHA256, digest
from Tests.NativeLevels.xmidi_clock import CLOCK_VERSION
from Tests.NativeEndOfLevel.trace import REZ_PATH, REZ_SHA256
from Tests.NativeLevels.trace import Blocked


def require(condition, reason):
    if not condition:
        raise Blocked(reason)


def validate_observer_reference(trace, level):
    require(level == trace.get('level') and level in (11, 12),
            'Observer reference is elected only for Levels 11 and 12')
    require(trace.get('status') == 'pass' and trace.get('stop') is None
            and trace.get('played_ms', 0) >= 60000, 'Incomplete observer route')
    for field, path in TRACE_INPUTS.items():
        require(trace.get(field) == digest(path), f'Stale observer input: {path}')
    require(trace.get('executable_sha256') == EXE_SHA256, 'Wrong observer executable')
    resources = trace.get('resources', {})
    require(resources.get('sha256') == REZ_SHA256
            and resources.get('archive') == str(REZ_PATH.relative_to(ROOT)), 'Wrong observer archive')
    clock = trace.get('xmidi_clock_adapter', {})
    require((clock.get('version'), clock.get('hz'), clock.get('sha256')) ==
            (CLOCK_VERSION, 120, digest('Tests/NativeLevels/xmidi_clock.py')), 'Stale observer clock')
    observer = trace.get('observer_checkpoint', {})
    path = f'work/level-12-sign-discovery/level-{level}.checkpoint.gz'
    require(observer.get('path') == path, 'Unelected observer checkpoint')
    checksum = fingerprint(ROOT/path)
    require(observer.get('sha256') == trace.get('prefix_checkpoint_sha256') == checksum,
            'Stale observer checkpoint fingerprint')
    probe = object.__new__(ObjectLoadTrace)
    probe.target_level = level
    expected = probe.checkpoint_inputs()
    require(observer.get('inputs_sha256') == expected, 'Stale observer loading input hashes')
    with open_artifact(ROOT/path) as stream:
        require(stream.read(len(CHECKPOINT_MAGIC)) == CHECKPOINT_MAGIC
                and len(stream.read(8)) == 8, 'Invalid observer checkpoint header')
        state = pickle.load(stream)['state']
    require(state.get('checkpoint_inputs_sha256') == expected, 'Stale observer checkpoint inputs')
    require(state.get('target_level') == level and state.get('played_ms') == 0,
            f'Observer checkpoint is not at Level {level} start')
    require(state.get('generic_fingerprint') == digest('Tests/NativeLevels/trace.py')
            and state.get('routes_fingerprint') == digest('Tests/NativeLevels/routes.py')
            and state.get('plan') == json.loads((ROOT/'work/menu-map/plan.json').read_text()),
            'Stale observer checkpoint route provenance')
    require(trace.get('resumed_checkpoint') is True and not trace.get('checkpoint_advancement')
            and not state.get('advancement'), 'Unexpected observer advancement provenance')
    runner = observer.get('runner')
    elected = (('work/level-11-map/route_observer.py', 'work/level-11-map/navigate_route.py')
               if level == 11 else ('work/level-12-map/sustained_ladder_route.py',))
    require(runner in elected
            and observer.get('runner_sha256') == digest(runner), 'Stale observer runner')
    require(trace.get('string_compare_boundary', {}).get('adapter_sha256') ==
            digest('Tests/NativeLevels/string_compare_fixture.py'), 'Stale observer comparison service')
    require(''.join(k['letter'] for k in trace['cheat_keys']) == 'MPSCULLY'*(level-1)
            and [c['level'] for c in trace['completions']] == list(range(2, level))
            and all(c['posted'] and c['next_level'] == c['level']+1 for c in trace['completions'])
            and set(range(1, level+1)) <= {s.get('level') for s in trace['state_transitions']},
            'Incomplete observer loading progression')
    if level == 12:
        validate_resumed_prefix(trace)
    return True


def validate_resumed_prefix(trace):
    """Bind Level 12 discovery to the independently compared cache and streams."""
    import hashlib
    from Tests.NativeLevels.storage import read_trace

    out = ROOT/'work/level-12-map'
    proof = json.loads((out/'climb-resume-equivalence.json').read_text())
    require(proof.get('status') == 'pass' and proof.get('cpu_state_equal') is True
            and proof.get('file_state_equal') is True, 'Missing exact Level 12 cache proof')
    require(proof.get('from_ms') == 42330 and proof.get('to_ms') == 100062,
            'Unelected Level 12 cache boundary')
    require(proof.get('checker') == 'work/level-12-map/check_checkpoint_prefix.py'
            and proof.get('checker_sha256') == digest(proof['checker']),
            'Stale Level 12 checkpoint comparison')
    for key in ('continuous', 'resumed', 'verified_checkpoint', 'prefix_equivalence'):
        require(proof.get(key+'_sha256') == fingerprint(ROOT/proof[key]),
                f'Stale Level 12 proof artifact: {key}')
    require(proof.get('checkpoint') == trace.get('resumed_observer'),
            'Different Level 12 resumed checkpoint')
    require(proof['checkpoint']['sha256'] == fingerprint(ROOT/proof['checkpoint']['path']),
            'Stale Level 12 resumed checkpoint')
    for provenance in (proof['checkpoint'], proof['verified_checkpoint_provenance']):
        require(provenance['runner_sha256'] == digest(provenance['runner'])
                and provenance['original_start_sha256'] == fingerprint(ROOT/provenance['original_start']),
                'Stale Level 12 checkpoint runner/start')
        require(all(digest(path) == checksum for path, checksum in provenance['inputs_sha256'].items()),
                'Stale Level 12 checkpoint input')
    source = read_trace(ROOT/proof['resumed'])
    require(trace['played_ms'] == source['played_ms'] == 105706
            and trace['plan'] == source['plan'] == json.loads((out/'plan.json').read_text()),
            'Changed Level 12 complete route')
    require(trace.get('retained_stream_sha256') == source.get('retained_stream_sha256'),
            'Changed Level 12 retained stream identities')
    # Ownership refresh may annotate the census, but cannot change original observations.
    for key in ('route', 'frames', 'physical_events', 'math_events', 'frame_cycles', 'peg_frames'):
        rows = trace['plan'] if key == 'route' else trace[key]
        checksum = hashlib.sha256(b'[')
        for index, row in enumerate(rows):
            if index:
                checksum.update(b',')
            checksum.update(json.dumps(row, sort_keys=True, separators=(',', ':')).encode())
        checksum.update(b']')
        require(checksum.hexdigest() == source['retained_stream_sha256'][key],
                f'Changed Level 12 original observation stream: {key}')
