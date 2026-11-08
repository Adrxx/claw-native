"""Version 2 of the later-level physical XMIDI clock (no audio synthesis).

AIL intervals and note durations are fixed at 120 Hz, not MIDI PPQN. Tempo
meta-events change beat/bar accounting, not this elapsed-time/status clock.
The AIL 2 reference implementation's XMIDI_meta/__set_tempo writes only
time_per_beat; serve_driver uses the separate API tempo_percent for playback.
Sources (original public AIL documentation/implementation, not game recovery):
https://github.com/Mindwerks/wildmidi/blob/master/docs/formats/XMIFileFormat-AIL.txt
https://github.com/Tronix286/AIL2/blob/master/XMIDI.ASM

Earlier tracer files stay unchanged. Checkpoints at Level 10 and later include
this adapter's hash; earlier checkpoints still require every original input hash.
No beat-count, branching, SysEx or audible synthesis service is supplied here.
"""
import hashlib
from pathlib import Path

from Tests.NativeMenuBase.trace import Blocked, parse_xmidi
from Tests.NativeLevels.trace import LevelTrace

CLOCK_VERSION = 'ail-fixed-120hz-tempo-metadata-v2'


def linear_xmidi_ticks(data):
    """Validate the bounded linear profile, retaining all real-time intervals."""
    parsed = parse_xmidi(data)  # Bounds, VLQs, channel data, containers and EOT.
    streams = []

    def chunks(start, end):
        while start < end:
            tag = data[start:start+4]
            length = int.from_bytes(data[start+4:start+8], 'big')
            body, limit = start+8, start+8+length
            if tag in (b'FORM', b'CAT '):
                chunks(body+4, limit)
            elif tag == b'EVNT':
                streams.append(data[body:limit])
            start = limit+(length & 1)

    chunks(0, len(data))
    stream, cursor = streams[0], 0

    def byte():
        nonlocal cursor
        value = stream[cursor]
        cursor += 1
        return value

    def variable():
        result = 0
        while True:
            value = byte()
            result = result*128+(value & 127)
            if value < 128:
                return result

    sizes = {0x2f: 0, 0x51: 3, 0x54: 5, 0x58: 4, 0x21: 1, 0x59: 2}
    while cursor < len(stream):
        status = byte()
        if status < 128:
            continue
        if status == 255:
            meta, length = byte(), variable()
            payload = stream[cursor:cursor+length]
            cursor += length
            if sizes.get(meta) != length:
                raise Blocked('Unsupported or malformed XMIDI clock metadata')
            if meta == 0x51 and not int.from_bytes(payload, 'big'):
                raise Blocked('Invalid zero XMIDI tempo metadata')
            if meta == 0x2f:
                break
        elif status in (0xf0, 0xf7):
            raise Blocked('XMIDI SysEx needs a physical sequencer provider')
        else:
            message = status >> 4
            values = [byte() for _ in range(1 if message in (12, 13) else 2)]
            if message == 11 and values[0] >= 110:
                raise Blocked('XMIDI branch/loop/trigger controller is outside the linear clock profile')
            if message == 9:
                variable()
    if not parsed['duration_ticks']:
        raise Blocked('Zero-duration XMIDI sequence')
    return parsed['duration_ticks']


class TempoClockTrace(LevelTrace):
    """Opt-in adapter; inherits sequence start/stop/loop and elapsed-time logic."""

    def checkpoint_inputs(self):
        inputs = super().checkpoint_inputs()
        if self.target_level >= 10:
            inputs['Tests/NativeLevels/xmidi_clock.py'] = hashlib.sha256(
                Path(__file__).read_bytes()).hexdigest()
        return inputs

    def verify_sequence_clock(self, handle, sequence):
        if max(self.target_level, getattr(self, 'destination', self.target_level)) < 10:
            return super().verify_sequence_clock(handle, sequence)
        identity = (CLOCK_VERSION, sequence['sha256'], sequence['duration_ticks'])
        if sequence.get('clock_verified') == identity:
            return
        event = next((e for e in reversed(self.physical_events)
                      if e['service'] == '_AIL_init_sequence@12'
                      and e['sequence'] == hex(handle)), None)
        if event is None:
            raise Blocked('XMIDI clock has no initialization evidence')
        for address, length in self.allocations.items():
            if length != event['bytes']:
                continue
            data = bytes(self.machine.mem_read(address, length))
            if hashlib.sha256(data).hexdigest() == sequence['sha256']:
                if linear_xmidi_ticks(data) != sequence['duration_ticks']:
                    raise Blocked('XMIDI initialization and clock durations disagree')
                sequence['clock_verified'] = identity
                return
        raise Blocked('XMIDI clock could not validate its original initialized bytes')

    def report(self):
        result = super().report()
        if max(self.target_level, getattr(self, 'destination', self.target_level)) >= 10:
            result['xmidi_clock_adapter'] = dict(version=CLOCK_VERSION, hz=120,
                sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                tempo_semantics='beat/bar metadata; elapsed intervals unchanged')
        return result
