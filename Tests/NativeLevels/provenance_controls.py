"""Focused reference-freshness and native physical-clock election controls."""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from Tests.NativeLevels import provenance as p
from Tests.NativeLevels.native_join import EndOfLevelNativeJoin, LevelNativeJoin
from Tests.NativeLevels.xmidi_clock import CLOCK_VERSION, TempoClockTrace, linear_xmidi_ticks
from Tests.NativeLevels.trace import Blocked


def run_controls():
    trace = dict(status='pass', stop=None, level=10, executable_sha256=p.EXE_SHA256,
                 full_prefix_runner_sha256=p.digest('Tests/NativeLevels/advance.py'),
                 resources=dict(sha256=p.REZ_SHA256, archive=str(p.REZ_PATH.relative_to(p.ROOT))),
                 **{field: p.digest(path) for field, path in p.TRACE_INPUTS.items()},
                 xmidi_clock_adapter=dict(version=CLOCK_VERSION, hz=120,
                     sha256=p.digest('Tests/NativeLevels/xmidi_clock.py')))
    assert p.validate_reference(trace, 10, full_prefix=True)
    results = {}

    def refuse(name, change):
        altered = copy.deepcopy(trace)
        change(altered)
        try:
            p.validate_reference(altered, 10, full_prefix=True)
        except Blocked as error:
            results[name] = str(error)
        else:
            raise AssertionError(f'Accepted {name}')

    for field in p.TRACE_INPUTS:
        refuse('stale-'+field, lambda t, f=field: t.__setitem__(f, '0'*64))
    refuse('wrong-executable', lambda t: t.update(executable_sha256='bad'))
    refuse('wrong-archive', lambda t: t['resources'].update(sha256='bad'))
    refuse('stale-full-prefix-runner', lambda t: t.update(full_prefix_runner_sha256='bad'))
    for field in ('version', 'hz', 'sha256'):
        refuse('stale-clock-'+field, lambda t, f=field: t['xmidi_clock_adapter'].__setitem__(f, None))
    refuse('unproven-restored-prefix', lambda t: t.update(resumed_checkpoint=True))
    advance = dict(source_level=9, destination=10, source_checkpoint='work/missing-checkpoint',
                   source_sha256='bad', runner_sha256=p.digest('Tests/NativeLevels/advance.py'))
    with patch.object(p, 'fingerprint', return_value='current'):
        refuse('stale-source-checkpoint', lambda t: t.update(checkpoint_advancement=advance))
        advance['source_sha256'] = 'current'
        advance['runner_sha256'] = 'bad'
        refuse('stale-advancement-runner', lambda t: t.update(checkpoint_advancement=advance))
        advance['runner_sha256'] = p.digest('Tests/NativeLevels/advance.py')
        with patch.object(p, 'checkpoint_state', side_effect=Blocked('Stale checkpoint tracer/clock provenance')):
            refuse('stale-source-inputs', lambda t: t.update(checkpoint_advancement=advance))
        with patch.object(p, 'checkpoint_state', return_value={}):
            refuse('unreviewed-prefix-mixing', lambda t: t.update(checkpoint_advancement=advance))

    # Check the real small-header validator independently of the reference mocks.
    import pickle
    with tempfile.TemporaryDirectory(dir=p.ROOT/'work') as directory:
        checkpoint = Path(directory)/'start.checkpoint'
        def header(state):
            data = pickle.dumps(dict(state=state))
            checkpoint.write_bytes(p.CHECKPOINT_MAGIC+len(data).to_bytes(8, 'little')+data)
        probe = object.__new__(p.LevelTrace)
        inputs = probe.checkpoint_inputs()
        inputs['Tests/NativeLevels/xmidi_clock.py'] = p.digest('Tests/NativeLevels/xmidi_clock.py')
        state = dict(target_level=10, played_ms=0, checkpoint_inputs_sha256=inputs,
                     generic_fingerprint=inputs['Tests/NativeLevels/trace.py'],
                     routes_fingerprint=p.digest('Tests/NativeLevels/routes.py'),
                     plan=json.loads((p.ROOT/'work/menu-map/plan.json').read_text()))
        header(state)
        assert p.checkpoint_state(checkpoint, 10) == state
        for name, field in (('checkpoint-tracer', 'Tests/NativeLevels/trace.py'),
                            ('checkpoint-clock', 'Tests/NativeLevels/xmidi_clock.py')):
            stale = copy.deepcopy(state)
            stale['checkpoint_inputs_sha256'][field] = 'bad'
            header(stale)
            try:
                p.checkpoint_state(checkpoint, 10)
            except Blocked as error:
                results[name] = str(error)
            else:
                raise AssertionError(name)

        # A genuine current earlier-level header needs no retroactive clock
        # label. Validate its real fingerprint and runner before accepting it.
        source = copy.deepcopy(state)
        source['target_level'] = 9
        source['checkpoint_inputs_sha256'].pop('Tests/NativeLevels/xmidi_clock.py')
        header(source)
        advancement = dict(source_level=9, destination=10,
            source_checkpoint=str(checkpoint.relative_to(p.ROOT)),
            source_sha256=p.fingerprint(checkpoint),
            runner_sha256=p.digest('Tests/NativeLevels/advance.py'))
        p.validate_advancement(advancement, 10)
        results['current-advancement'] = 'validated header, source fingerprint and runner'
        source['routes_fingerprint'] = 'bad'
        header(source)
        advancement['source_sha256'] = p.fingerprint(checkpoint)
        try:
            p.validate_advancement(advancement, 10)
        except Blocked as error:
            results['checkpoint-route'] = str(error)
        else:
            raise AssertionError('Accepted stale checkpoint route')

    # Native objects must dispatch the physical adapter; no machine/emulator is
    # constructed for this election test.
    native = object.__new__(LevelNativeJoin)
    native.target_level = 10
    with patch.object(TempoClockTrace, 'verify_sequence_clock') as clock:
        native.verify_sequence_clock(7, {'duration_ticks': 120})
        clock.assert_called_once_with(native, 7, {'duration_ticks': 120})
    results['native-clock-election'] = 'physical adapter called'

    def xmi(events):
        chunk = b'EVNT'+len(events).to_bytes(4, 'big')+events
        if len(events) & 1:
            chunk += b'\0'
        body = b'XMID'+b'INFO\x00\x00\x00\x02\x01\x00'+chunk
        return b'FORM'+len(body).to_bytes(4, 'big')+body
    end = b'\xff\x2f\x00'
    assert linear_xmidi_ticks(xmi(b'\xff\x51\x03\x07\xa1\x20\x78'+end)) == 120
    for name, data in (
            ('zero-tempo', xmi(b'\xff\x51\x03\x00\x00\x00\x78'+end)),
            ('loop-controller', xmi(b'\xb0\x74\x01\x78'+end)),
            ('sysex', xmi(b'\xf0\x01\x00\x78'+end)),
            ('truncated', xmi(b'\x90\x40')),
            ('zero-duration', xmi(end))):
        try:
            linear_xmidi_ticks(data)
        except Blocked as error:
            results[name] = str(error)
        else:
            raise AssertionError(f'Accepted {name}')
    # Exercise the elected native method with actual initialized bytes, not
    # just a mocked dispatch. The native memory provider is byte storage only.
    import hashlib
    from types import SimpleNamespace
    data = xmi(b'\xff\x51\x03\x07\xa1\x20\x78'+end)
    native.physical_events = [dict(service='_AIL_init_sequence@12', sequence=hex(7), bytes=len(data))]
    native.allocations = {0x2000: len(data)}
    native.machine = SimpleNamespace(mem_read=lambda address, size: data)
    sequence = dict(sha256=hashlib.sha256(data).hexdigest(), duration_ticks=120)
    native.verify_sequence_clock(7, sequence)
    assert sequence['clock_verified'] == (CLOCK_VERSION, sequence['sha256'], 120)
    assert native.validated_clocks == {sequence['clock_verified']}
    for name, sequence in (
            ('uninitialized-native-clock', dict(sha256='bad', duration_ticks=120)),
            ('native-duration-mismatch', dict(sha256=hashlib.sha256(data).hexdigest(), duration_ticks=121))):
        try:
            native.verify_sequence_clock(7, sequence)
        except Blocked as error:
            results[name] = str(error)
        else:
            raise AssertionError(name)
    native.deny_idle_random = True
    native.native_functions = [0x420480]
    native.phase = 'level-10-stand'
    try:
        native.fixture(0x4a3050)
    except Blocked as error:
        results['gameplay-idle-service-refusal'] = str(error)
    else:
        raise AssertionError('Idle random control did not refuse target gameplay')
    native.phase = 'command-8075'
    with patch.object(EndOfLevelNativeJoin, 'fixture', return_value='provided') as provider:
        assert native.fixture(0x4a3050) == 'provided'
        provider.assert_called_once_with(native, 0x4a3050)
    results['loading-idle-service-retained'] = 'provided outside target gameplay'
    return results


def main():
    print(json.dumps(dict(status='pass', controls=run_controls()), sort_keys=True))


if __name__ == '__main__':
    main()
