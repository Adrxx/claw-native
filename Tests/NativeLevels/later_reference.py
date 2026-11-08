"""Validate Level 13/14 observer provenance and the original ladder census."""
import hashlib
import json
import pickle
import struct
import zlib
from Tests.NativeLevels import ROOT
from Tests.NativeLevels.storage import CHECKPOINT_MAGIC, fingerprint, open_artifact
from Tests.NativeLevels.provenance import TRACE_INPUTS, EXE_SHA256, digest
from Tests.NativeLevels.object_load_trace import ObjectLoadTrace
from Tests.NativeLevels.xmidi_clock import CLOCK_VERSION
from Tests.NativeEndOfLevel.trace import REZ_PATH, REZ_SHA256

RUNNER = 'Tests/NativeLevels/later_trace.py'
BASE = 'work/level-12-sign-discovery/level-12.checkpoint.gz'


def validate_checkpoint(path, level):
    assert path.resolve().is_relative_to(ROOT/'work')
    with open_artifact(path) as stream:
        assert stream.read(len(CHECKPOINT_MAGIC)) == CHECKPOINT_MAGIC
        assert len(stream.read(8)) == 8
        state = pickle.load(stream)['state']
    probe = object.__new__(ObjectLoadTrace)
    probe.target_level = level
    assert state['checkpoint_inputs_sha256'] == probe.checkpoint_inputs(), 'Stale loading checkpoint'
    assert state['target_level'] == level and state['played_ms'] == 0
    assert state['generic_fingerprint'] == digest('Tests/NativeLevels/trace.py')
    assert state['routes_fingerprint'] == digest('Tests/NativeLevels/routes.py')
    assert state['plan'] == json.loads((ROOT/'work/menu-map/plan.json').read_text())
    assert ''.join(k['letter'] for k in state['cheat_keys']) == 'MPSCULLY'*(level-1)
    if level == 12:
        assert str(path.relative_to(ROOT)) == BASE
        assert not state.get('later_advancement')
    else:
        assert str(path.relative_to(ROOT)) in (f'work/level-{level}-map/start.checkpoint',
                                               f'work/level-{level}-map/start.checkpoint.gz')
        validate_advancement(state['later_advancement'], level)
    return state


def validate_advancement(row, level):
    assert row['source_level'] == level-1 and row['destination'] == level
    assert row['runner'] == RUNNER and row['runner_sha256'] == digest(RUNNER)
    source = ROOT/row['source_checkpoint']
    assert fingerprint(source) == row['source_sha256']
    validate_checkpoint(source, level-1)


def validate_later_reference(trace, level):
    assert trace['level'] == level and level in (13,14)
    assert trace['status'] == 'pass' and trace['stop'] is None
    for field,path in TRACE_INPUTS.items():
        assert trace[field] == digest(path), f'Stale observer input: {path}'
    assert trace['executable_sha256'] == EXE_SHA256
    assert trace['resources']['sha256'] == REZ_SHA256
    assert trace['resources']['archive'] == str(REZ_PATH.relative_to(ROOT))
    clock = trace['xmidi_clock_adapter']
    assert (clock['version'],clock['hz'],clock['sha256']) == (CLOCK_VERSION,120,digest('Tests/NativeLevels/xmidi_clock.py'))
    observer = trace['observer_checkpoint']
    navigation_runner = ('Tests/NativeLevels/level_fourteen_trace.py'
                         if level == 14 else RUNNER)
    assert observer['runner'] == navigation_runner
    assert observer['runner_sha256'] == digest(navigation_runner)
    if level == 14:
        assert trace['frame_budget'] == dict(instructions=5_000_000, wall_seconds=45)
        assert trace['frames'][1:], 'Missing completed frame diagnostics'
        for frame in trace['frames'][1:]:
            budget = frame['observer_budget']
            assert 0 < budget['steps'] < 5_000_000+16384
            assert budget['wall_seconds'] >= 0
    source = ROOT/observer['path']
    state = validate_checkpoint(source, observer['source_level'])
    assert observer['inputs_sha256'] == state['checkpoint_inputs_sha256']
    assert observer['sha256'] == trace['prefix_checkpoint_sha256'] == fingerprint(source)
    validate_advancement(trace['later_advancement'], level)
    if observer['source_level'] == level:
        assert trace['later_advancement'] == state['later_advancement']
    else:
        assert observer['source_level'] == level-1
        assert trace['later_advancement']['source_sha256'] == observer['sha256']
    assert trace['string_compare_boundary']['adapter_sha256'] == digest('Tests/NativeLevels/string_compare_fixture.py')
    return True


def ladder_tiles(level):
    packed = (ROOT/f'Original/retail-assets/LEVEL{level}/WORLDS/WORLD.WWD').read_bytes()
    world = packed[:1524]+zlib.decompress(packed[1524:])
    u = lambda offset: struct.unpack_from('<I',world,offset)[0]
    offset = u(0x2e4)
    count = u(offset+8)
    offset += 32
    attributes = []
    for _ in range(count):
        kind,_,_,_,outside = struct.unpack_from('<5I',world,offset)
        offset += 20
        inside = outside
        if kind == 2:
            inside = u(offset)
            offset += 20
        attributes.append((outside,inside))
    plane = u(0x2e0)+160
    cols,rows,tiles = u(plane+0x60),u(plane+0x64),u(plane+0x84)
    return sum(3 in attributes[t] for i in range(cols*rows)
               if (t:=u(tiles+4*i)) < len(attributes))
