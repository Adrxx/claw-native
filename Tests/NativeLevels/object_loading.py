"""Validate retained original evidence for placed, unregistered object names."""
import hashlib
import json
import struct
import zlib
from Tests.NativeLevels import ROOT
from Tests.clawparity.program import claw


EVIDENCE = 'work/level-12-sign-discovery/object-loading.json'


def sign_records():
    packed = (ROOT/'Original/retail-assets/LEVEL12/WORLDS/WORLD.WWD').read_bytes()
    header = struct.unpack_from('<I', packed)[0]
    assert header == 1524
    world = packed[:header]+zlib.decompress(packed[header:]) if struct.unpack_from('<I', packed, 8)[0] & 2 else packed
    count, offset = struct.unpack_from('<II', world, 0x2dc)
    result = []
    for plane in range(count):
        objects = struct.unpack_from('<I', world, offset+plane*160+0x80)[0]
        at = struct.unpack_from('<I', world, offset+plane*160+0x8c)[0]
        for index in range(objects):
            lengths = struct.unpack_from('<4I', world, at+4)
            end = at+284+sum(lengths)
            logic = world[at+284+lengths[0]:at+284+sum(lengths[:2])].split(b'\0')[0]
            if logic == b'Sign':
                x, y = struct.unpack_from('<ii', world, at+20)
                result.append(dict(plane=plane, index=index, id=struct.unpack_from('<I', world, at)[0],
                    x=x, y=y, z=struct.unpack_from('<i', world, at+28)[0],
                    record_offset=at, byte_count=end-at,
                    record_sha256=hashlib.sha256(world[at:end]).hexdigest()))
            at = end
    assert len(result) == 3, 'Unexpected original Sign records'
    return result


def validate_loading_report(report):
    assert report['schema'] == 1 and report['level'] == 12
    assert report['status'] == 'pass' and report['loaded'] and report['stop'] is None, 'Original loading incomplete'
    assert report['executable_sha256'] == claw().sha256, 'Wrong original executable'
    from Tests.NativeLevels.object_load_trace import ObjectLoadTrace
    # This method only hashes files; constructing an emulator is unnecessary.
    configuration = object.__new__(ObjectLoadTrace)
    configuration.target_level = 12
    expected_inputs = configuration.checkpoint_inputs()
    assert report['inputs_sha256'] == expected_inputs, 'Missing or stale original loading provenance'
    assert ''.join(k['letter'] for k in report['cheat_keys']) == 'MPSCULLY'*11
    assert [c['level'] for c in report['completions']] == list(range(2, 12))
    assert all(c['posted'] and c['next_level'] == c['level']+1 for c in report['completions'])
    assert set(range(1, 13)) <= {s.get('level') for s in report['state_transitions']}
    events = [e for e in report['object_lookups'] if e['name'] == 'Sign']
    assert len(events) == 3, 'Missing original Sign lookup records'
    assert all(e.get('return') == 0 and e.get('value') == 0 for e in events), 'Sign must be unregistered in the original'
    positives = {e['name'] for e in report['object_lookups']
                 if e.get('return') == 1 and e.get('value') and e['phase'] == 'command-8075'}
    assert {'Aquatis', 'AquatisCrack', 'AquatisDynamite', 'AquatisStalactite',
            'Tentacle', 'Stalactite'} <= positives, 'Missing registered-class positive controls'
    # The pinned loader checks the class-map result, destroys the temporary
    # object on a miss, and returns the consumed WWD byte count to its caller.
    # Check the executed path, not merely the absence of a registration string.
    prefix = [0x4f6286, 0x4d1a98, 0x4d1a9c, 0x4d1a9e, 0x4d1aa0,
              0x4d1aa4, 0x4d1aab, 0x4d1aad, 0x4d1aaf, 0x4d1ab1,
              0x4d1ab3, 0x4c9be0]
    steps = report['sign_steps']
    for event, record in zip(events, sign_records()):
        assert event['caller'] == 0x4d1a98 and event['phase'] == 'command-8075'
        registers = event['registers']
        assert (registers['edi'], registers['esi']) == (record['x'], record['y']), 'Wrong Sign position'
        assert struct.unpack_from('<I', bytes.fromhex(event['memory']['ebx']), 4)[0] == record['id'], 'Wrong Sign object ID'
        starts = [i for i,s in enumerate(steps) if s['address'] == 0x4f6286 and s['registers'] == registers]
        assert len(starts) == 1, 'Missing or duplicate Sign execution window'
        window = steps[starts[0]:starts[0]+400]
        assert [s['address'] for s in window[:len(prefix)]] == prefix, 'Missing original Sign skip branch'
        addresses = [s['address'] for s in window]
        assert 0x4d1abb not in addresses, 'Sign unexpectedly enters registered-class initialization'
        assert 0x4d1ab6 in addresses, 'Missing original Sign destruction return'
        destroy_return = addresses.index(0x4d1ab6)
        assert addresses[destroy_return+1] == 0x4d1f5e, 'Missing destruction continuation'
        ends = [s for s in window if s['address'] == 0x4d1fbf]
        assert len(ends) == 1, 'Missing or ambiguous original Sign loader return'
        end = ends[0]
        assert end['registers']['eax'] == record['byte_count'], 'Sign did not advance past its WWD record'
    return events


def verified_outcomes(level, world_objects=None):
    if level != 12:
        return {}
    path = ROOT/EVIDENCE
    assert path.exists(), 'Missing original Sign loading evidence; run Tests.NativeLevels.object_load_trace'
    raw = path.read_bytes()
    validate_loading_report(json.loads(raw))
    records = sign_records()
    if world_objects is not None:
        actual = [(o['plane'], o['x'], o['y']) for o in world_objects if o['logic'] == 'Sign']
        assert actual == [(o['plane'], o['x'], o['y']) for o in records], 'Changed placed Sign records'
    return {'Sign': dict(load_outcome='unregistered-skipped', load_evidence=EVIDENCE,
        load_evidence_sha256=hashlib.sha256(raw).hexdigest(), object_records=records,
        load_roots=['0x4d17e0'])}


def validate_unregistered(level, row, closure):
    assert level == 12 and row['name'] == 'Sign', 'Unverified unregistered class'
    assert row['callback'] is None and row['states'] == [], 'Fabricated unregistered Sign mapping'
    assert row['placed'] == 3, 'Changed unregistered Sign count'
    expected = verified_outcomes(level)['Sign']
    assert all(row.get(k) == v for k,v in expected.items()), 'Missing or stale unregistered Sign outcome'
    roots = {r['address'] for r in closure['functions'] if r['root']}
    assert set(expected['load_roots']) <= roots, 'Missing original Sign loader root'


def main():
    outcome = verified_outcomes(12)['Sign']
    print(json.dumps(dict(command='level-12-sign-loading-check', status='pass',
        outcome=outcome['load_outcome'], records=[r['id'] for r in outcome['object_records']],
        registered_class_controls=6, scope='Original loading only; no route or native join')))


if __name__ == '__main__':
    main()
