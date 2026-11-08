"""Focused physical-clock controls; no synthesis or game-parity claim.

AIL XMIDI stores intervals at 120 Hz, independently of MIDI tempo metadata.
Original music hashes and durations come from the retained Level 10 diagnostic.
Run: work/test-env/bin/python -m unittest Tests.NativeLevels.test_xmidi_clock -v
"""
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from Tests.NativeLevelOne.trace import LevelOneTrace
from Tests.NativeMenuBase.trace import Blocked, parse_xmidi
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevels.xmidi_clock import TempoClockTrace, linear_xmidi_ticks


ROOT = Path(__file__).resolve().parents[2]
TRACKS = {
    'PLAY': ('10de0d9ff99757d40a662f843fc7e364c7aec04269b08e41bcbae4213cb244fb', 47375),
    'PLAY0': ('14d2dff682c1bac703b22f145cac96a5d3df48637b4c8ff15064409093500e6e', 47375),
    'BOSS': ('d7b476cd3b3f5bc0343e1a80ade17cd548b33c751b1207c3f727c79e943222bf', 14222),
    'BOSS0': ('49326a00804c19ee03ade3407f4c5b67bb2e41cf9c6f1aa0478f6ea43ca7b4c6', 14222),
}


def chunk(tag, payload):
    return tag + len(payload).to_bytes(4, 'big') + payload + b'\0' * (len(payload) & 1)


def xmi(events):
    return (chunk(b'FORM', b'XDIR' + chunk(b'INFO', b'\1\0')) +
            chunk(b'CAT ', b'XMID' + chunk(b'FORM', b'XMID' + chunk(b'EVNT', events))))


def meta(kind, payload):
    return bytes((255, kind, len(payload))) + payload


END = b'\xff\x2f\0'
TEMPO = meta(0x51, b'\x06\x1a\x80')


def clock_shell(data, duration=None):
    """Use the real clock/service methods with byte storage, without emulation."""
    trace = object.__new__(TempoClockTrace)
    handle, source, stack = 0x1000, 0x2000, 0x3000
    trace.target_level = 10
    trace.milliseconds = 0
    trace.allocations = {handle: 16, source: len(data)}
    trace.physical_events = [dict(service='_AIL_init_sequence@12', sequence=hex(handle), bytes=len(data))]
    trace.sequences = {handle: dict(initialized=True, status=2, loops=1,
        duration_ticks=parse_xmidi(data)['duration_ticks'] if duration is None else duration,
        sha256=hashlib.sha256(data).hexdigest())}
    trace.memory = {source: data}
    trace.stack_words = {stack + 4: handle, stack + 8: 1}
    trace.machine = SimpleNamespace(mem_read=lambda address, size: trace.memory[address][:size],
                                    reg_read=lambda register: stack)
    trace.word = lambda address: trace.stack_words[address]
    trace.platform_call = lambda *args: None
    trace.returned = lambda value, pop=0: setattr(trace, 'service_return', (value, pop))
    trace.imports = {}
    return trace, handle


def service(trace, api, milliseconds=None, argument=None):
    if milliseconds is not None:
        trace.milliseconds = milliseconds
    if argument is not None:
        trace.stack_words[0x3008] = argument
    trace.imports[0x123456] = (None, 'MSS32.DLL!' + api)
    LevelOneTrace.fixture(trace, 0x123456)
    return trace.service_return


class DecoderControls(unittest.TestCase):
    def test_original_tracks(self):
        for name, (digest, duration) in TRACKS.items():
            with self.subTest(track=name):
                data = (ROOT / f'Original/retail-assets/LEVEL10/MUSIC/{name}.XMI').read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                self.assertEqual(linear_xmidi_ticks(data), duration)

    def test_tempo_values_do_not_rescale_intervals_or_note_duration(self):
        for tempo in (1, 400000, 500000, 1000000, 0xffffff):
            with self.subTest(tempo=tempo):
                # A note ends at tick 36; the last event is at tick 24.
                data = xmi(b'\x0c' + meta(0x51, tempo.to_bytes(3, 'big')) +
                           b'\x90\x3c\x64\x18\x0c' + TEMPO + END)
                self.assertEqual(linear_xmidi_ticks(data), 36)

    def test_tempo_at_zero_and_repeated_at_same_tick(self):
        self.assertEqual(linear_xmidi_ticks(xmi(TEMPO + TEMPO + b'\x78' + END)), 120)

    def test_allowed_metadata_sizes(self):
        events = (meta(0x54, bytes(5)) + meta(0x58, b'\x04\x02\x18\x08') +
                  meta(0x21, b'\0') + meta(0x59, b'\0\0') + b'\x78' + END)
        self.assertEqual(linear_xmidi_ticks(xmi(events)), 120)

    def test_wrong_metadata_sizes(self):
        for kind, size in ((0x2f, 0), (0x51, 3), (0x54, 5), (0x58, 4), (0x21, 1), (0x59, 2)):
            for length in {max(0, size - 1), size + 1} - {size}:
                with self.subTest(meta=kind, length=length):
                    with self.assertRaises(Blocked):
                        linear_xmidi_ticks(xmi(b'\x01' + meta(kind, b'\1' * length) + END))

    def test_zero_tempo_at_zero_or_nonzero_time(self):
        for delay in (b'', b'\x01'):
            with self.subTest(delay=delay), self.assertRaises(Blocked):
                linear_xmidi_ticks(xmi(delay + meta(0x51, bytes(3)) + b'\x78' + END))

    def test_truncated_tempo_payload(self):
        with self.assertRaises(Blocked):
            linear_xmidi_ticks(xmi(b'\x01\xff\x51\x03\x06\x1a'))

    def test_unknown_metadata(self):
        for kind in (0x00, 0x01, 0x20, 0x52, 0x7f):
            with self.subTest(meta=kind), self.assertRaises(Blocked):
                linear_xmidi_ticks(xmi(b'\x01' + meta(kind, b'\0') + END))

    def test_sysex_stays_unsupported(self):
        for status in (0xf0, 0xf7):
            with self.subTest(status=status), self.assertRaises(Blocked):
                linear_xmidi_ticks(xmi(bytes((1, status, 1, 0x7e)) + END))

    def test_controller_boundary(self):
        self.assertEqual(linear_xmidi_ticks(xmi(b'\x01\xb0\x6d\0' + END)), 1)
        for controller in range(110, 128):
            with self.subTest(controller=controller), self.assertRaises(Blocked):
                linear_xmidi_ticks(xmi(bytes((1, 0xb0, controller, 64)) + END))

    def test_malformed_transport(self):
        for events in (b'\x01\x90\x80\x40\x01' + END,
                       b'\x01\xff\x51\x80\x80\x80\x80\0' + END,
                       b'\x01\x90\x3c\x40\x01', b'\x01' + END + b'\x90\x3c\x40\x01'):
            with self.subTest(events=events), self.assertRaises(Blocked):
                linear_xmidi_ticks(xmi(events))
        for data in (b'', xmi(b'\x01' + END)[:-1]):
            with self.subTest(data=data), self.assertRaises(Blocked):
                linear_xmidi_ticks(data)

    def test_zero_duration_stays_unsupported(self):
        with self.assertRaises(Blocked):
            linear_xmidi_ticks(xmi(TEMPO + END))


class SequenceControls(unittest.TestCase):
    def new_clock(self):
        return clock_shell(xmi(b'\x3c' + TEMPO + b'\x3c' + END))

    def test_fixed_clock_completion_boundary(self):
        trace, handle = self.new_clock()
        self.assertEqual(service(trace, '_AIL_start_sequence@4'), (0, 4))
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 999), (4, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 119880)
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 1000), (2, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 120000)

    def test_original_track_completion_boundaries(self):
        for name, (_, ticks) in TRACKS.items():
            with self.subTest(track=name):
                trace, handle = clock_shell((ROOT / f'Original/retail-assets/LEVEL10/MUSIC/{name}.XMI').read_bytes())
                service(trace, '_AIL_start_sequence@4', 7)
                last_ms = (ticks * 1000 - 1) // 120
                self.assertEqual(service(trace, '_AIL_sequence_status@4', 7 + last_ms), (4, 4))
                self.assertEqual(service(trace, '_AIL_sequence_status@4', 8 + last_ms), (2, 4))
                self.assertEqual(trace.sequences[handle]['elapsed_units'], ticks * 1000)

    def test_play_tempo_boundaries_preserve_status_and_elapsed_time(self):
        for name in ('PLAY', 'PLAY0'):
            with self.subTest(track=name):
                trace, handle = clock_shell((ROOT / f'Original/retail-assets/LEVEL10/MUSIC/{name}.XMI').read_bytes())
                service(trace, '_AIL_start_sequence@4', 17)
                for tick in (15791, 31583):
                    before = (tick * 1000 - 1) // 120
                    for elapsed in (before, before + 1):
                        with self.subTest(tick=tick, elapsed=elapsed):
                            self.assertEqual(service(trace, '_AIL_sequence_status@4', 17 + elapsed), (4, 4))
                            self.assertEqual(trace.sequences[handle]['elapsed_units'], elapsed * 120)

    def test_stop_and_resume_preserve_elapsed_time(self):
        trace, handle = self.new_clock()
        service(trace, '_AIL_start_sequence@4')
        service(trace, '_AIL_stop_sequence@4', 250)
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 4000), (8, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 30000)
        service(trace, '_AIL_resume_sequence@4', 5000)
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 5749), (4, 4))
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 5750), (2, 4))

    def test_start_rewinds_and_end_stops(self):
        trace, handle = self.new_clock()
        service(trace, '_AIL_start_sequence@4')
        service(trace, '_AIL_sequence_status@4', 500)
        service(trace, '_AIL_start_sequence@4', 600)
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 0)
        service(trace, '_AIL_end_sequence@4', 650)
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 9000), (2, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 6000)

    def test_finite_loops(self):
        trace, handle = self.new_clock()
        self.assertEqual(service(trace, '_AIL_set_sequence_loop_count@8', argument=3), (0, 8))
        service(trace, '_AIL_start_sequence@4')
        for now in (1000, 2000, 2999):
            self.assertEqual(service(trace, '_AIL_sequence_status@4', now), (4, 4))
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 3000), (2, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 360000)
        self.assertEqual(trace.sequences[handle]['loops'], 1)

    def test_infinite_loop(self):
        trace, handle = self.new_clock()
        service(trace, '_AIL_set_sequence_loop_count@8', argument=0)
        service(trace, '_AIL_start_sequence@4')
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 1234567), (4, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 1234567 * 120)

    def test_backward_clock_rejected(self):
        trace, _ = self.new_clock()
        service(trace, '_AIL_start_sequence@4', 100)
        with self.assertRaises(Blocked):
            service(trace, '_AIL_sequence_status@4', 99)

    def test_release_and_unknown_handle(self):
        trace, handle = self.new_clock()
        self.assertEqual(service(trace, '_AIL_release_sequence_handle@4'), (0, 4))
        self.assertNotIn(handle, trace.sequences)
        self.assertNotIn(handle, trace.allocations)
        with self.assertRaises(Blocked):
            service(trace, '_AIL_sequence_status@4')

    def test_sequence_source_hash_validation(self):
        trace, handle = self.new_clock()
        trace.sequences[handle]['sha256'] = '0' * 64
        with self.assertRaises(Blocked):
            trace.verify_sequence_clock(handle, trace.sequences[handle])

    def test_missing_initialization_evidence_rejected(self):
        trace, handle = self.new_clock()
        trace.physical_events.clear()
        with self.assertRaises(Blocked):
            trace.verify_sequence_clock(handle, trace.sequences[handle])

    def test_level_nine_without_tempo_destination_keeps_legacy_profile(self):
        trace, handle = self.new_clock()
        trace.target_level = 9
        with self.assertRaisesRegex(Blocked, 'Unsupported XMIDI clock metadata'):
            trace.verify_sequence_clock(handle, trace.sequences[handle])

    def test_level_nine_transition_to_ten_accepts_tempo_metadata(self):
        trace, handle = self.new_clock()
        trace.target_level = 9
        trace.destination = 10
        service(trace, '_AIL_start_sequence@4')
        self.assertEqual(service(trace, '_AIL_sequence_status@4', 999), (4, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 119880)

    def test_sequence_duration_validation(self):
        trace, handle = self.new_clock()
        trace.sequences[handle]['duration_ticks'] += 1
        with self.assertRaises(Blocked):
            trace.verify_sequence_clock(handle, trace.sequences[handle])

    def test_verified_sequence_can_advance_repeatedly(self):
        trace, handle = self.new_clock()
        trace.verify_sequence_clock(handle, trace.sequences[handle])
        trace.verify_sequence_clock(handle, trace.sequences[handle])
        service(trace, '_AIL_start_sequence@4')
        for now in (1, 2, 3, 10, 100, 999):
            self.assertEqual(service(trace, '_AIL_sequence_status@4', now), (4, 4))
        self.assertEqual(trace.sequences[handle]['elapsed_units'], 119880)

    def test_legacy_boolean_does_not_bypass_revalidation(self):
        trace, handle = self.new_clock()
        trace.sequences[handle].update(clock_verified=True, sha256='0' * 64)
        with self.assertRaises(Blocked):
            trace.verify_sequence_clock(handle, trace.sequences[handle])

    def test_changed_verified_identity_is_revalidated(self):
        for field, replacement in (('sha256', '0' * 64), ('duration_ticks', 121)):
            with self.subTest(field=field):
                trace, handle = self.new_clock()
                trace.verify_sequence_clock(handle, trace.sequences[handle])
                trace.sequences[handle][field] = replacement
                with self.assertRaises(Blocked):
                    trace.verify_sequence_clock(handle, trace.sequences[handle])


class CheckpointControls(unittest.TestCase):
    def test_level_nine_retains_baseline_input_binding(self):
        trace = object.__new__(TempoClockTrace)
        trace.target_level = 9
        self.assertEqual(trace.checkpoint_inputs(), LevelTrace.checkpoint_inputs(trace))

    def test_level_ten_binds_adapter_hash(self):
        trace = object.__new__(TempoClockTrace)
        trace.target_level = 10
        inputs = trace.checkpoint_inputs()
        baseline = LevelTrace.checkpoint_inputs(trace)
        for name, digest in baseline.items():
            self.assertEqual(inputs[name], digest)
        # Hashing is provenance verification, not inspection of implementation.
        with (ROOT / 'Tests/NativeLevels/xmidi_clock.py').open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        self.assertEqual(inputs['Tests/NativeLevels/xmidi_clock.py'], digest)

    def test_wrong_adapter_hash_is_rejected_before_memory_restore(self):
        trace = object.__new__(TempoClockTrace)
        trace.target_level = 10
        inputs = trace.checkpoint_inputs()
        inputs['Tests/NativeLevels/xmidi_clock.py'] = '0' * 64
        payload = dict(state=dict(target_level=10, played_ms=0, checkpoint_inputs_sha256=inputs))
        with patch('Tests.NativeLevels.trace.load_checkpoint', return_value=payload), \
                patch('Tests.NativeLevels.trace.restore_memory') as restore:
            with self.assertRaisesRegex(Blocked, 'Stale target-level checkpoint'):
                trace.resume_target(ROOT / 'work/level-10-map/invalid-test.checkpoint')
            restore.assert_not_called()

    def test_level_ten_checkpoint_without_adapter_hash_is_rejected(self):
        trace = object.__new__(TempoClockTrace)
        trace.target_level = 10
        payload = dict(state=dict(target_level=10, played_ms=0,
                                 checkpoint_inputs_sha256=LevelTrace.checkpoint_inputs(trace)))
        with patch('Tests.NativeLevels.trace.load_checkpoint', return_value=payload), \
                patch('Tests.NativeLevels.trace.restore_memory') as restore:
            with self.assertRaisesRegex(Blocked, 'Stale target-level checkpoint'):
                trace.resume_target(ROOT / 'work/level-10-map/missing-adapter-test.checkpoint')
            restore.assert_not_called()


if __name__ == '__main__':
    unittest.main()
