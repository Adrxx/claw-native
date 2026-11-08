"""Freshness checks shared by discovery and the native full-prefix comparison.

Checkpoint advancement is discovery evidence. The native join elects a complete
independent prefix, so it requires a fresh full-prefix original reference rather
than comparing restored original observations to a differently executed prefix.
"""
import hashlib
import pickle
import json
from Tests.NativeLevels import ROOT
from Tests.NativeLevels.storage import CHECKPOINT_MAGIC, fingerprint, open_artifact
from Tests.NativeLevels.trace import LevelTrace, Blocked
from Tests.NativeLevels.xmidi_clock import CLOCK_VERSION
from Tests.NativeEndOfLevel.trace import REZ_PATH, REZ_SHA256

EXE_SHA256 = '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'

TRACE_INPUTS = {
    'tracer_sha256': 'Tests/NativeLevelOne/trace.py',
    'storage_sha256': 'Tests/NativeLevels/storage.py',
    'generic_tracer_sha256': 'Tests/NativeLevels/trace.py',
    'routes_sha256': 'Tests/NativeLevels/routes.py',
    'large_grid_fixture_sha256': 'Tests/NativeLevels/grid_fixture.py',
    'provider_tracer_sha256': 'Tests/NativeLevelTwo/trace.py',
    'level_tracer_sha256': 'Tests/NativeLevelOne/trace.py',
    'end_tracer_sha256': 'Tests/NativeEndOfLevel/trace.py',
    'menu_tracer_sha256': 'Tests/NativeMenuBase/trace.py',
    'plan_sha256': 'work/menu-map/plan.json',
}


def digest(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def checkpoint_state(path, level):
    path = path.resolve()
    if not path.is_relative_to(ROOT/'work'):
        raise Blocked('Checkpoint must be a local work artifact')
    with open_artifact(path) as stream:
        if stream.read(len(CHECKPOINT_MAGIC)) != CHECKPOINT_MAGIC or len(stream.read(8)) != 8:
            raise Blocked('Unsupported checkpoint provenance format')
        # Trusted local pickle; only the small header, never memory or event logs.
        state = pickle.load(stream)['state']
    probe = object.__new__(LevelTrace)
    expected = probe.checkpoint_inputs()
    if level >= 10:
        expected['Tests/NativeLevels/xmidi_clock.py'] = digest('Tests/NativeLevels/xmidi_clock.py')
    if state.get('checkpoint_inputs_sha256') != expected:
        raise Blocked('Stale checkpoint tracer/clock provenance')
    if (state.get('generic_fingerprint') != expected['Tests/NativeLevels/trace.py']
            or state.get('routes_fingerprint') != digest('Tests/NativeLevels/routes.py')
            or state.get('plan') != json.loads((ROOT/'work/menu-map/plan.json').read_text())):
        raise Blocked('Stale checkpoint route/plan provenance')
    if state.get('target_level') != level or state.get('played_ms') != 0:
        raise Blocked('Checkpoint is not the requested level start')
    if state.get('advancement'):
        validate_advancement(state['advancement'], level)
    return state


def validate_advancement(advancement, level):
    source = advancement['source_level']
    if not 2 <= source < advancement['destination'] == level:
        raise Blocked('Invalid checkpoint advancement levels')
    path = ROOT/advancement['source_checkpoint']
    if advancement['source_sha256'] != fingerprint(path):
        raise Blocked('Stale advancement source checkpoint')
    if advancement['runner_sha256'] != digest('Tests/NativeLevels/advance.py'):
        raise Blocked('Stale checkpoint advancement runner')
    checkpoint_state(path, source)


def validate_reference(trace, level, *, full_prefix=False):
    if level in (13, 14) and trace.get('observer_checkpoint') and not full_prefix:
        from Tests.NativeLevels.later_reference import validate_later_reference
        return validate_later_reference(trace, level)
    if level in (11, 12) and trace.get('observer_checkpoint') and not full_prefix:
        from Tests.NativeLevels.observer_reference import validate_observer_reference
        return validate_observer_reference(trace, level)
    if trace.get('status') != 'pass' or trace.get('stop') is not None or trace.get('level') != level:
        raise Blocked(f'Original Level {level} trace is not a passing run')
    for field, path in TRACE_INPUTS.items():
        if trace.get(field) != digest(path):
            raise Blocked(f'Stale original trace input: {path}')
    if trace.get('executable_sha256') != EXE_SHA256:
        raise Blocked('Original executable provenance mismatch')
    resources = trace.get('resources') or {}
    if resources.get('sha256') != REZ_SHA256 or resources.get('archive') != str(REZ_PATH.relative_to(ROOT)):
        raise Blocked('Original archive provenance mismatch')
    if level >= 10:
        clock = trace.get('xmidi_clock_adapter', {})
        if (clock.get('version'), clock.get('hz'), clock.get('sha256')) != (
                CLOCK_VERSION, 120, digest('Tests/NativeLevels/xmidi_clock.py')):
            raise Blocked('Stale original XMIDI clock provenance')
    advancement = trace.get('checkpoint_advancement')
    if level >= 10 and not advancement:
        if trace.get('full_prefix_runner_sha256') != digest('Tests/NativeLevels/advance.py'):
            raise Blocked('Stale full-prefix reference runner')
    if advancement:
        validate_advancement(advancement, level)
    restored = trace.get('prefix_checkpoint_sha256') or trace.get('resumed_checkpoint')
    if restored:
        if not advancement:
            raise Blocked('Restored reference has no advancement provenance')
        if trace.get('resumed_checkpoint'):
            path = ROOT/f'work/level-{level}-map/start.checkpoint'
            if trace.get('prefix_checkpoint_sha256') != fingerprint(path):
                raise Blocked('Stale target checkpoint fingerprint')
            state = checkpoint_state(path, level)
            if state.get('advancement') != advancement:
                raise Blocked('Target checkpoint advancement disagrees')
        elif trace.get('prefix_checkpoint_sha256') != advancement['source_sha256']:
            raise Blocked('Advancement prefix disagrees with source checkpoint')
    if full_prefix and (advancement or restored):
        raise Blocked('Native comparison requires independently replayed full-prefix original evidence')
    return True
