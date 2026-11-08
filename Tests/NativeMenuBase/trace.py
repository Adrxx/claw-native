"""Read-only original-menu discovery; never substitutes a game function.

Run: work/test-env/bin/python -m Tests.NativeMenuBase.trace
Physical font dependency: work/test-env/bin/pip install Pillow==12.0.0
The ignored JSON is a partial trace on failure, not a native parity test or an
admission. Exit 2 means blocked, including an unsupported platform service.

Native startup replaces WinMain/MFC startup. Execute the original application
constructor and mode-5 factory, suspend the factory before initialization, then
construct its actual scene managers and open the hash-verified original archive.
Resume the suspended factory with its CPU/stack/exception state intact. Original
directory, sound and image loaders run against physical read-only services.
Unknown initializer and frame services still fail closed at exact sites.
Only the emulated address space and the selected ignored JSON output are written.
The default run also checks physical transport and withheld-service controls.
An initializer or transport pass alone cannot make the overall trace pass.
No frame is inferred from a surface upload or an incomplete update cycle.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version

from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
from unicorn import (Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE,
                     UC_HOOK_MEM_INVALID, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE)
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW,
    UC_X86_REG_FPSW, UC_X86_REG_FPTAG, UC_X86_REG_FP0)
from Tests.clawparity.program import claw

ROOT = Path(__file__).resolve().parents[2]
GAME_RANGES = ((0x401000, 0x4A1300), (0x4B3400, 0x4F0000))
STOP = 0x70000080
CALLBACK_RETURN = 0x7000f000
ARRAY_RETURN = 0x7000f010
STACK = 0x02008000
REZ_SHA256 = 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
REZ_PATH = ROOT / 'Original/claw-disc/files/DATA/CLAW.REZ'
INLINE_SPANS = {0x42637d: 0x4263ae, 0x4264cc: 0x4264dc,
                0x4261f7: 0x42620c, 0x426565: 0x426594}


def game(address):
    return 0x401000 <= address < 0x4a1300 or 0x4b3400 <= address < 0x4f0000


class Blocked(RuntimeError):
    pass


def parse_xmidi(data):
    """Validate physical IFF/XMIDI bytes before accepting a sequence handle.

    Only sequence zero in a single-sequence XDIR is elected. Event timing is
    retained in XMIDI ticks; this initializer transport does not synthesize audio
    or advance sequence playback (the frame task must provide that clock).
    """
    event_chunks, sequence_counts = [], []
    def chunks(start, end, depth=0):
        if depth > 8:
            raise Blocked('Excessive physical XMIDI container nesting')
        while start < end:
            if start + 8 > end:
                raise Blocked('Truncated physical XMIDI chunk header')
            tag, length = data[start:start + 4], int.from_bytes(data[start + 4:start + 8], 'big')
            body, limit = start + 8, start + 8 + length
            if limit + (length & 1) > end:
                raise Blocked('Truncated physical XMIDI chunk data')
            if tag in (b'FORM', b'CAT '):
                if length < 4 or data[body:body + 4] not in (b'XDIR', b'XMID'):
                    raise Blocked('Unknown physical XMIDI container type')
                chunks(body + 4, limit, depth + 1)
            elif tag == b'INFO':
                if length != 2:
                    raise Blocked('Invalid XMIDI INFO size')
                sequence_counts.append(int.from_bytes(data[body:limit], 'little'))
            elif tag == b'EVNT':
                event_chunks.append(data[body:limit])
            elif tag == b'TIMB':
                if length < 2 or length != 2 + 2 * int.from_bytes(data[body:body + 2], 'little'):
                    raise Blocked('Invalid XMIDI timbre table')
            else:
                raise Blocked(f'Unprovided physical XMIDI chunk {tag!r}')
            start = limit + (length & 1)
    chunks(0, len(data))
    if sequence_counts != [1] or len(event_chunks) != 1:
        raise Blocked('Physical XMIDI profile requires one original sequence')
    events, tick, duration, cursor, ended = 0, 0, 0, 0, False
    stream = event_chunks[0]
    def byte():
        nonlocal cursor
        if cursor >= len(stream):
            raise Blocked('Truncated physical XMIDI event')
        value = stream[cursor]
        cursor += 1
        return value
    def variable():
        result = 0
        for _ in range(4):
            value = byte()
            result = result * 128 + (value & 127)
            if value < 128:
                return result
        raise Blocked('Invalid physical XMIDI variable integer')
    while cursor < len(stream):
        status = byte()
        if status < 128:
            tick += status
            continue
        events += 1
        if status == 0xff:
            meta, length = byte(), variable()
            for _ in range(length):
                byte()
            if meta == 0x2f:
                # Retail EVNT includes its single zero alignment byte in the
                # chunk length. No event data may follow end-of-track.
                if length or stream[cursor:] not in (b'', b'\0'):
                    raise Blocked('Invalid XMIDI end-of-track event')
                cursor = len(stream)
                ended = True
        elif status in (0xf0, 0xf7):
            for _ in range(variable()):
                byte()
        elif 0x80 <= status < 0xf0:
            message = status >> 4
            for _ in range(1 if message in (0xc, 0xd) else 2):
                if byte() >= 128:
                    raise Blocked('Invalid physical XMIDI channel data')
            if message == 9:
                duration = max(duration, tick + variable())
        else:
            raise Blocked('Unsupported physical XMIDI event status')
    if not ended:
        raise Blocked('XMIDI sequence has no end-of-track')
    return dict(events=events, duration_ticks=max(duration, tick))


class MenuTrace:
    is_game = staticmethod(game)

    def __init__(self, instruction_limit=80_000_000, deny_platform=None, missing_resource=False,
                 machine_factory=Uc, startup_paper=False):
        self.program = claw()  # Mandatory executable hash check, before mapping.
        self.plan_path = ROOT / 'work/menu-map/plan.json'
        self.plan = json.loads(self.plan_path.read_text())
        self.entries = {int(a, 16) for a in self.plan['nodes']}
        self.machine = machine_factory(UC_ARCH_X86, UC_MODE_32)
        self.machine.mem_map(self.program.base, (self.program.size + 4095) & ~4095)
        for section in self.program.sections:
            self.machine.mem_write(section.address, section.data)
        for base, size in ((0, 4096), (0x01ff0000, 0x20000),
                           (0x61000000, 0x1000000), (0x70000000, 0x10000)):
            self.machine.mem_map(base, size)
        self.put(0, 0xffffffff)
        self.machine.reg_write(UC_X86_REG_FPCW, 0x027f)
        self.machine.reg_write(UC_X86_REG_FPSW, 0)
        self.machine.reg_write(UC_X86_REG_FPTAG, 0xffff)
        self.heap_next = 0x61000000
        self.allocations = {}
        self.imports = {}
        for index, (slot, name) in enumerate(self.program.imports.items()):
            target = 0x70001000 + index * 16
            self.put(slot, target)
            self.imports[target] = (slot, name)
        self.decoder = Cs(CS_ARCH_X86, CS_MODE_32)
        self.decoder.detail = True
        self.decoded = {}
        self.pending = None
        self.last_transfer = None
        self.recent = deque(maxlen=32)
        self.functions = Counter()
        self.phases = {}
        self.edges = Counter()
        self.branch_targets = Counter()
        self.platform = Counter()
        self.platform_names = {}
        self.phase = 'setup'
        self.phase_results = []
        self.instructions = 0
        self.instruction_limit = instruction_limit
        self.deny_platform = deny_platform
        self.boundary = None
        self.paused = False
        self.stop = None
        self.milliseconds = 1000
        self.startup_paper = startup_paper
        self.clock_step = 1 if startup_paper else 0
        self.random_state = 1
        self.cursor = (320, 240)
        self.messages = []
        self.cursor_display_count = 0
        self.pressed_keys = set()
        self.midi_started = False
        self.midi_drivers = {}
        self.midi_master_volume = 127  # MSS default before any AIL_set_XMIDI_master_volume
        self.sequences = {}
        self.math_events = []
        self.com_methods = {}
        self.com_tables = {}
        self.com_objects = {}
        self.physical_events = []
        self.callback = None
        self.array_callbacks = []
        self.display_mode = (640, 480, 8)
        self.scene_evidence = None
        self.resource_evidence = None
        self.factory_resume = None
        self.initializer_return = None
        self.factory_return = None
        self.startup_evidence = []
        self.presentations = []
        self.frame_cycles = []
        self.exit_callbacks = []
        self.dcs = {}
        # Explicit native physical font election, not a Windows SYSTEM_FONT
        # pixel-parity claim. Pillow embeds this font; no host font discovery.
        if pillow_version != '12.0.0':
            raise Blocked('Physical text requires Pillow 12.0.0 in work/test-env')
        self.font = ImageFont.load_default(size=13)
        self.font_evidence = dict(engine='Pillow 12.0.0', name=self.font.getname(),
            size=13, metrics=self.font.getmetrics(), antialias=False,
            palette='nearest RGB squared distance; lowest index breaks ties')
        self.files = {}
        self.closed_files = set()
        self.maps = {}
        self.memory_files = {}
        self.archives = {}
        self.missing_resource = missing_resource
        self.empty_string = self.cstring(b'', immortal=True)
        self.machine.hook_add(UC_HOOK_CODE, self.hook)
        self.machine.hook_add(UC_HOOK_MEM_INVALID, self.invalid_memory)
        self.machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.low_memory, begin=0, end=4095)

    def word(self, address):
        return struct.unpack('<I', self.machine.mem_read(address, 4))[0]

    def put(self, address, value):
        self.machine.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def allocate(self, size):
        if not 0 <= size <= 0x800000:
            raise Blocked(f'Invalid fixture allocation size {size}')
        address = self.heap_next
        self.heap_next += (max(size, 1) + 15) & ~15
        if self.heap_next >= 0x62000000:
            raise Blocked('Bounded fixture heap exhausted')
        self.allocations[address] = size
        # Poison, so game constructors cannot silently depend on a zeroed heap.
        self.machine.mem_write(address, b'\xa5' * max(size, 1))
        return address

    def bytestring(self, address):
        for length in range(65536):
            if self.machine.mem_read(address + length, 1) == b'\0':
                return bytes(self.machine.mem_read(address, length))
        raise Blocked('Unterminated platform string')

    def cstring(self, value, immortal=False):
        address = self.allocate(len(value) + 13)
        self.put(address, -1 if immortal else 1)
        self.put(address + 4, len(value))
        self.put(address + 8, len(value))
        self.machine.mem_write(address + 12, value + b'\0')
        return address + 12

    def returned(self, result, pop=0):
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        self.machine.reg_write(UC_X86_REG_EAX, result & 0xffffffff)
        self.machine.reg_write(UC_X86_REG_EIP, self.word(sp))
        self.machine.reg_write(UC_X86_REG_ESP, sp + 4 + pop)

    def invalid_memory(self, machine, access, address, size, value, user):
        self.stop = dict(kind='unmapped_memory', address=hex(machine.reg_read(UC_X86_REG_EIP)),
                         memory_address=hex(address), access=access, size=size,
                         reason='Missing or invalid native startup/physical fixture state; no automatic mapping')
        return False

    def low_memory(self, machine, access, address, size, value, user):
        # The low page exists solely for FS:[0], not for null game receivers.
        pc = machine.reg_read(UC_X86_REG_EIP)
        if address != 0 or size != 4 or bytes(machine.mem_read(pc, 1)) != b'\x64':
            self.stop = dict(kind='null_context_access', address=hex(pc), memory_address=hex(address),
                             access=access, size=size, reason='Missing native startup object; low page is only FS:[0]')
            raise Blocked(self.stop['reason'])

    def platform_call(self, address, name):
        self.platform[address] += 1
        self.platform_names[address] = name
        if self.deny_platform == address:
            raise Blocked(f'Negative control: platform fixture deliberately withheld: {name}')

    def x87_state(self):
        return dict(control=self.machine.reg_read(UC_X86_REG_FPCW),
                    status=self.machine.reg_read(UC_X86_REG_FPSW),
                    tags=self.machine.reg_read(UC_X86_REG_FPTAG))

    def cpu_state(self):
        registers = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                     UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
                     UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW,
                     UC_X86_REG_FPSW, UC_X86_REG_FPTAG)
        return [self.machine.reg_read(r) for r in registers] + [
            self.machine.reg_read(UC_X86_REG_FP0 + i) for i in range(8)]

    def x87_value(self, index):
        state = self.x87_state()
        slot = ((state['status'] >> 11) + index) & 7
        if (state['tags'] >> (slot * 2)) & 3 == 3:
            raise Blocked('Empty x87 fixture operand')
        significand, exponent = self.machine.reg_read(UC_X86_REG_FP0 + slot)
        if exponent & 0x7fff == 0x7fff:
            raise Blocked('Non-finite x87 fixture operand')
        value = math.ldexp(significand, (exponent & 0x7fff) - 16383 - 63)
        return -value if exponent & 0x8000 else value

    def x87_result(self, consumed, value=None):
        # FP0..FP7 are physical registers. FPSW.TOP selects logical ST(0),
        # while the full tag word indexes physical registers, not ST indices.
        state = self.x87_state()
        top = (state['status'] >> 11) & 7
        tags = state['tags']
        for index in range(consumed):
            tags |= 3 << (((top + index) & 7) * 2)
        top = (top + consumed) & 7
        if value is not None:
            if not math.isfinite(value):
                raise Blocked('Non-finite mathematical fixture result')
            top = (top - 1) & 7
            fraction, exponent = math.frexp(abs(value))
            bits = (int(fraction * (1 << 64)), exponent + 16382) if value else (0, 0)
            self.machine.reg_write(UC_X86_REG_FP0 + top,
                                   (bits[0], bits[1] | (0x8000 if math.copysign(1, value) < 0 else 0)))
            tags &= ~(3 << (top * 2))
            if not value:
                tags |= 1 << (top * 2)
        self.machine.reg_write(UC_X86_REG_FPTAG, tags)
        self.machine.reg_write(UC_X86_REG_FPSW, (state['status'] & ~0x3800) | (top << 11))

    def math_fixture(self, address):
        before = self.x87_state()
        if before['control'] != 0x027f:
            raise Blocked('Math fixture requires the elected masked binary64 round-to-nearest x87 control')
        operands = [self.x87_value(i) for i in range(2 if address == 0x4f1b30 else 1)]
        eax = self.machine.reg_read(UC_X86_REG_EAX)
        if address == 0x4f1b30:
            # CRT _CIpow consumes exponent ST(0), base ST(1).
            table_power = operands[0] == 10 and 1 < operands[1] <= 100
            inverse_volume = operands[1] == 2 and -10 <= operands[0] <= 0
            if not (table_power or inverse_volume):
                raise Blocked('Power operands outside the scene audio-table profile')
            result = math.pow(operands[1], operands[0])
            self.x87_result(2, result)
        elif address == 0x4f2400:
            if not -1 <= operands[0] <= 1:
                raise Blocked('Inverse cosine operand outside the finite unit interval')
            result = math.acos(operands[0])
            self.x87_result(1, result)
        elif address == 0x4f1a60:
            if not 1 < operands[0] <= 1e20:
                raise Blocked('Logarithm operand outside the scene audio-table profile')
            result = math.log(operands[0])
            self.x87_result(1, result)
        else:
            result = math.trunc(operands[0])
            if not -(1 << 63) <= result < (1 << 63):
                raise Blocked('Out-of-range CRT integer conversion')
            self.x87_result(1)
            eax = result
            self.machine.reg_write(UC_X86_REG_EDX, (result >> 32) & 0xffffffff)
        self.math_events.append(dict(address=hex(address), operands=operands, result=result,
                                     before=before, after=self.x87_state()))
        self.returned(eax)

    def array_resize(self, receiver, size, grow=0xffffffff):
        if size > 4096:
            raise Blocked('Array fixture size outside scene profile')
        old, count = self.word(receiver + 4), self.word(receiver + 8)
        if count > 4096 or old and old not in self.allocations:
            raise Blocked('Invalid array backing')
        data = self.allocate(size * 4) if size else 0
        if data:
            self.machine.mem_write(data, bytes(size * 4))
            if old:
                self.machine.mem_write(data, bytes(self.machine.mem_read(old, min(count, size) * 4)))
        self.allocations.pop(old, None)
        for offset, value in ((4, data), (8, size), (12, size)):
            self.put(receiver + offset, value)
        if grow != 0xffffffff:
            self.put(receiver + 16, grow)

    def com_object(self, kind, **state):
        # Legacy COM layout and descriptor contracts:
        # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/ns-ddraw-ddsurfacedesc
        # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/nc-ddraw-lpddenummodescallback
        # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/ns-ddraw-ddcaps_dx3
        methods = {
            'IDirectDraw': {20: 'CreatePalette', 24: 'CreateSurface',
                            32: 'EnumDisplayModes', 44: 'GetCaps', 48: 'GetDisplayMode',
                            80: 'SetCooperativeLevel', 84: 'SetDisplayMode', 88: 'WaitForVerticalBlank'},
            'IDirectSound': {12: 'CreateSoundBuffer', 20: 'DuplicateSoundBuffer', 24: 'SetCooperativeLevel'},
            'IDirectSoundBuffer': {8: 'Release', 24: 'GetVolume', 28: 'GetPan', 32: 'GetFrequency', 36: 'GetStatus', 44: 'Lock',
                                  48: 'Play', 52: 'SetCurrentPosition', 60: 'SetVolume',
                                  64: 'SetPan', 68: 'SetFrequency', 72: 'Stop', 76: 'Unlock'},
            'IDirectDrawSurface': {8: 'Release', 20: 'Blt', 28: 'BltFast', 44: 'Flip', 48: 'GetAttachedSurface', 68: 'GetDC', 104: 'ReleaseDC', 88: 'GetSurfaceDesc',
                                  96: 'IsLost', 100: 'Lock', 116: 'SetColorKey', 124: 'SetPalette', 128: 'Unlock'},
            'IDirectDrawPalette': {8: 'Release', 16: 'GetEntries', 24: 'SetEntries'},
        }
        table = self.com_tables.get(kind)
        if table is None:
            table = self.allocate(0x100)
            self.com_tables[kind] = table
            for offset in range(0, 0x100, 4):
                target = 0x70008000 + len(self.com_methods) * 16
                if target >= CALLBACK_RETURN:
                    raise Blocked('Bounded physical method table exhausted')
                self.com_methods[target] = (kind, methods[kind].get(offset, f'unsupported slot {offset:#x}'))
                self.put(table + offset, target)
        obj = self.allocate(4)
        self.put(obj, table)
        self.com_objects[obj] = dict(kind=kind, references=1, **state)
        return obj

    def surface(self, width, height, caps):
        if not 0 < width <= 800 or not 0 < height <= 600:
            raise Blocked('Surface dimensions outside scene fixture profile')
        pixels = self.allocate(width * height)
        self.machine.mem_write(pixels, bytes(width * height))
        return self.com_object('IDirectDrawSurface', width=width, height=height,
                               pitch=width, pixels=pixels, caps=caps, lost=False, locked=False)

    def display_description(self, address):
        if self.word(address) != 108:
            raise Blocked('Expected legacy 108-byte DDSURFACEDESC')
        self.machine.mem_write(address, bytes(108))
        width, height, depth = self.display_mode
        # DDSD_HEIGHT | WIDTH | PITCH | PIXELFORMAT; indexed RGB8.
        for offset, value in ((0, 108), (4, 0x100e), (8, height), (12, width),
                              (16, width), (72, 32), (76, 0x60), (84, depth)):
            self.put(address + offset, value)

    def com_fixture(self, address):
        kind, method = self.com_methods[address]
        self.platform_call(address, f'{kind}::{method}')
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        arg = lambda i: self.word(sp + 4 * i)
        obj = self.com_objects.get(arg(1))
        if not obj or obj['kind'] != kind or not obj['references']:
            raise Blocked('Invalid COM fixture receiver')
        event = dict(service=f'{kind}::{method}', object=hex(arg(1)),
                     phase=self.phase, milliseconds=self.milliseconds,
                     caller=self.last_transfer)
        self.physical_events.append(event)
        if method == 'GetDC':
            # GetDC owns a surface lock until matching ReleaseDC:
            # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/nf-ddraw-idirectdrawsurface7-getdc
            if obj['locked'] or obj['lost'] or obj.get('dc') or not arg(2):
                raise Blocked('Invalid physical GetDC surface state/output')
            palette = self.com_objects.get(obj.get('palette'))
            if not palette:
                parents = [s for s in self.com_objects.values() if s.get('back') == arg(1)]
                palette = self.com_objects.get(parents[0].get('palette')) if len(parents) == 1 else None
            if not palette:
                # An unpaletted offscreen DC uses the exclusive display's
                # primary/system palette. An attached offscreen palette wins.
                # Wine's native-Windows conformance test covers this route:
                # dlls/ddraw/tests/ddraw7.c, test_palette_gdi(), primary/offscreen.
                primaries = [surface for surface in self.com_objects.values()
                             if surface['kind'] == 'IDirectDrawSurface'
                             and surface['references'] and surface['caps'] & 0x200]
                if len(primaries) == 1:
                    palette = self.com_objects.get(primaries[0].get('palette'))
                    if palette and palette['references']:
                        event['palette_source'] = 'live-primary-display'
            if not palette or not palette['references']:
                raise Blocked('Physical text surface has no live indexed palette')
            handle = self.allocate(4)
            self.dcs[handle] = dict(surface=arg(1), pixels=obj['pixels'],
                palette=palette['entries'], background_mode=2, text_color=0)
            obj.update(locked=True, dc=handle)
            self.put(arg(2), handle)
            event.update(dc=hex(handle), font=self.font_evidence,
                palette_sha256=hashlib.sha256(bytes.fromhex(palette['entries'])).hexdigest())
            self.returned(0, 8)
        elif method == 'ReleaseDC':
            dc = self.dcs.get(arg(2))
            if not dc or dc['surface'] != arg(1) or obj.get('dc') != arg(2) or not obj['locked']:
                raise Blocked('Invalid physical ReleaseDC lifetime/receiver')
            del self.dcs[arg(2)]
            obj.update(locked=False, dc=None)
            event.update(dc=hex(arg(2)), pixels_sha256=hashlib.sha256(
                bytes(self.machine.mem_read(obj['pixels'], obj['pitch'] * obj['height']))).hexdigest())
            self.returned(0, 8)
        elif method == 'CreatePalette':
            if arg(2) != 0x44 or arg(5):
                raise Blocked('Unsupported indexed palette flags/aggregation')
            entries = bytes(self.machine.mem_read(arg(3), 1024))
            palette = self.com_object('IDirectDrawPalette', entries=entries.hex())
            self.put(arg(4), palette)
            event.update(palette=hex(palette), entries_sha256=hashlib.sha256(entries).hexdigest())
            self.returned(0, 20)
        elif method == 'SetPalette':
            palette = self.com_objects.get(arg(2))
            if not palette or palette['kind'] != 'IDirectDrawPalette' or not palette['references']:
                raise Blocked('Invalid physical palette attachment')
            previous = obj.get('palette')
            if previous:
                self.com_objects[previous]['references'] -= 1
            obj['palette'] = arg(2)
            palette['references'] += 1
            event['palette'] = hex(arg(2))
            self.returned(0, 8)
        elif kind == 'IDirectDrawPalette' and method in ('GetEntries', 'SetEntries'):
            if arg(2) or arg(3) + arg(4) > 256:
                raise Blocked('Invalid physical palette entry range')
            entries = bytearray.fromhex(obj['entries'])
            start, end = arg(3) * 4, (arg(3) + arg(4)) * 4
            if method == 'GetEntries':
                self.machine.mem_write(arg(5), bytes(entries[start:end]))
            else:
                entries[start:end] = self.machine.mem_read(arg(5), end - start)
                obj['entries'] = entries.hex()
            event.update(start=arg(3), count=arg(4), entries_sha256=hashlib.sha256(entries).hexdigest())
            self.returned(0, 20)
        elif method == 'Flip':
            # DirectDraw swaps surface memory associations, not COM identities.
            # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/nf-ddraw-idirectdrawsurface7-flip
            back = self.com_objects.get(obj.get('back'))
            if (obj['caps'] != 0x218 or not back or arg(2) or arg(3) != 1
                    or any(s['locked'] or s['lost'] or not s['references'] for s in (obj, back))):
                raise Blocked('Unsupported physical flip chain, target, flags or surface state')
            palette = self.com_objects.get(obj.get('palette'))
            if not palette or not palette['references']:
                raise Blocked('Indexed presentation has no live primary palette')
            obj['pixels'], back['pixels'] = back['pixels'], obj['pixels']
            pixels = bytes(self.machine.mem_read(obj['pixels'], obj['pitch'] * obj['height']))
            event.update(back=hex(obj['back']), pixels_sha256=hashlib.sha256(pixels).hexdigest(),
                palette_sha256=hashlib.sha256(bytes.fromhex(palette['entries'])).hexdigest(),
                nonzero_pixels=sum(bool(p) for p in pixels), flags=arg(3))
            self.presentations.append(dict(event))
            self.returned(0, 12)
        elif method == 'Blt':
            if arg(5) == 0x01000400:
                fx = arg(6)
                if (arg(2) or arg(3) or arg(4) or not fx or self.word(fx) != 100
                        or self.word(fx + 80) > 255 or obj['lost'] or obj['locked']
                        or any(self.word(fx + 4 * i) for i in range(1, 25) if i != 20)):
                    raise Blocked('Invalid physical indexed color fill')
                color = self.word(fx + 80)
                for row in range(obj['height']):
                    self.machine.mem_write(obj['pixels'] + row * obj['pitch'], bytes([color]) * obj['width'])
                event.update(fill_color=color, flags=arg(5))
                self.returned(0, 24)
                return
            # Elected menu profile: equal-sized, in-bounds source-keyed copies.
            # Unsupported stretch/effects fail closed instead of guessing pixels.
            source = self.com_objects.get(arg(3))
            if (not source or source['kind'] != 'IDirectDrawSurface' or arg(6)
                    or arg(5) & ~0x1008000
                    or any(s['lost'] or s['locked'] or not s['references'] for s in (obj, source))):
                raise Blocked('Unsupported physical Blt source, effects, flags or state')
            def rectangle(pointer, surface):
                return struct.unpack('<4i', self.machine.mem_read(pointer, 16)) if pointer else (0, 0, surface['width'], surface['height'])
            dst, src = rectangle(arg(2), obj), rectangle(arg(4), source)
            if any(not (0 <= r[0] < r[2] <= s['width'] and 0 <= r[1] < r[3] <= s['height'])
                   for r, s in ((dst, obj), (src, source))):
                raise Blocked(f'Blt rectangle outside physical surfaces: {src} -> {dst}')
            if (dst[2] - dst[0], dst[3] - dst[1]) != (src[2] - src[0], src[3] - src[1]):
                raise Blocked('Physical Blt stretch is outside the elected menu profile')
            key = source.get('color_key') if arg(5) & 0x8000 else None
            if arg(5) & 0x8000 and key is None:
                raise Blocked('Blt source color key was not set')
            rows = [bytes(self.machine.mem_read(source['pixels'] + y * source['pitch'] + src[0], src[2] - src[0]))
                    for y in range(src[1], src[3])]
            for row, pixels in enumerate(rows):
                destination = obj['pixels'] + (dst[1] + row) * obj['pitch'] + dst[0]
                if key:
                    old = self.machine.mem_read(destination, len(pixels))
                    pixels = bytes(a if key[0] <= b <= key[1] else b for a, b in zip(old, pixels))
                self.machine.mem_write(destination, pixels)
            event.update(source=hex(arg(3)), source_rectangle=src, destination_rectangle=dst, flags=arg(5))
            self.returned(0, 24)
        elif method == 'BltFast':
            source = self.com_objects.get(arg(4))
            if (not source or source['kind'] != 'IDirectDrawSurface' or not source['references']
                    or source['lost'] or source['locked'] or obj['lost'] or obj['locked']
                    or arg(6) & ~0x11):
                raise Blocked('Unsupported BltFast source, state or flags')
            rect = struct.unpack('<4i', self.machine.mem_read(arg(5), 16)) if arg(5) else (0, 0, source['width'], source['height'])
            left, top, right, bottom = rect
            x, y = arg(2), arg(3)
            if not (0 <= left <= right <= source['width'] and 0 <= top <= bottom <= source['height']
                    and x + right - left <= obj['width'] and y + bottom - top <= obj['height']):
                raise Blocked('BltFast rectangle outside physical surfaces')
            key = source.get('color_key') if arg(6) & 1 else None
            if arg(6) & 1 and key is None:
                raise Blocked('BltFast source color key was not set')
            rows = [bytes(self.machine.mem_read(source['pixels'] + row * source['pitch'] + left, right - left))
                    for row in range(top, bottom)]
            for row, pixels in enumerate(rows):
                destination = obj['pixels'] + (y + row) * obj['pitch'] + x
                if key:
                    previous = self.machine.mem_read(destination, len(pixels))
                    pixels = bytes(old if key[0] <= new <= key[1] else new for old, new in zip(previous, pixels))
                if pixels:
                    self.machine.mem_write(destination, pixels)
            event.update(source=hex(arg(4)), rectangle=rect, destination=(x, y), flags=arg(6),
                pixels_sha256=hashlib.sha256(bytes(self.machine.mem_read(obj['pixels'], obj['pitch'] * obj['height']))).hexdigest())
            self.returned(0, 24)
        elif method == 'CreateSoundBuffer':
            descriptor = arg(2)
            size, flags, length, reserved, fmt = [self.word(descriptor + i * 4) for i in range(5)]
            if size != 20 or flags != 0xe0 or reserved or arg(4) or not 0 < length <= 0x800000:
                raise Blocked('Unsupported legacy sound buffer descriptor')
            wave = bytes(self.machine.mem_read(fmt, 18))
            tag, channels, rate, average, alignment, depth, extra = struct.unpack('<HHIIHHH', wave)
            if tag != 1 or channels not in (1, 2) or depth not in (8, 16) or extra or alignment != channels * depth // 8 or average != rate * alignment:
                raise Blocked('Unsupported physical PCM format')
            data = self.allocate(length)
            self.machine.mem_write(data, bytes([128 if depth == 8 else 0]) * length)
            buffer = self.com_object('IDirectSoundBuffer', data=data, length=length, format=wave.hex(),
                volume=0, pan=0, frequency=rate, position=0, write_cursor=0, playing=False, locked=None)
            self.put(arg(3), buffer)
            event.update(buffer=hex(buffer), length=length, format=wave.hex())
            self.returned(0, 16)
        elif method == 'DuplicateSoundBuffer':
            source = self.com_objects.get(arg(2))
            if not source or source['kind'] != 'IDirectSoundBuffer' or not source['references'] or source['locked']:
                raise Blocked('Invalid physical sound buffer duplication')
            # Shared sample memory with independent playback/control state:
            # https://learn.microsoft.com/en-us/previous-versions/windows/desktop/mt708944(v=vs.85)
            state = {key: source[key] for key in ('data', 'length', 'format', 'volume', 'pan', 'frequency')}
            duplicate = self.com_object('IDirectSoundBuffer', **state,
                position=0, write_cursor=0, playing=False, locked=None)
            self.put(arg(3), duplicate)
            event.update(source=hex(arg(2)), duplicate=hex(duplicate), shared_data=hex(source['data']))
            self.returned(0, 12)
        elif kind == 'IDirectSoundBuffer' and method == 'Lock':
            offset, length, flags = arg(2), arg(3), arg(8)
            if obj['locked'] or flags not in (0, 1) or offset >= obj['length'] or length > obj['length']:
                raise Blocked('Unsupported PCM lock range/state')
            if flags == 1:
                if obj['playing']:
                    raise Blocked('Write-cursor lock during playback needs a physical clock model')
                offset = (obj['write_cursor'] + offset) % obj['length']
            first = min(length, obj['length'] - offset)
            lock = (obj['data'] + offset, first, obj['data'] if first < length else 0, length - first)
            for i, value in enumerate(lock):
                self.put(arg(i + 4), value)
            obj['locked'] = lock
            event['regions'] = lock
            self.returned(0, 32)
        elif kind == 'IDirectSoundBuffer' and method == 'Unlock':
            if tuple(arg(i) for i in range(2, 6)) != obj['locked']:
                raise Blocked('PCM unlock does not match its lock')
            obj['locked'] = None
            event['pcm_sha256'] = hashlib.sha256(bytes(self.machine.mem_read(obj['data'], obj['length']))).hexdigest()
            self.returned(0, 20)
        elif kind == 'IDirectSoundBuffer' and method in ('GetVolume', 'GetPan', 'GetFrequency', 'GetStatus'):
            value = int(obj['playing']) if method == 'GetStatus' else obj[method[3:].lower()]
            self.put(arg(2), value)
            self.returned(0, 8)
        elif kind == 'IDirectSoundBuffer' and method in ('SetVolume', 'SetPan', 'SetFrequency', 'SetCurrentPosition'):
            key = 'position' if method == 'SetCurrentPosition' else method[3:].lower()
            value = arg(2)
            if key in ('volume', 'pan'):
                value = struct.unpack('<i', struct.pack('<I', value))[0]
            if ((key == 'volume' and not -10000 <= value <= 0)
                    or (key == 'pan' and not -10000 <= value <= 10000)
                    or (key == 'frequency' and not 100 <= value <= 200000)
                    or (key == 'position' and value >= obj['length'])):
                raise Blocked('Invalid physical sound buffer setting')
            obj[key] = value
            if key == 'position':
                obj['sample_remainder'] = 0
            event[key] = value
            self.returned(0, 8)
        elif kind == 'IDirectSoundBuffer' and method == 'Play':
            if arg(2) or arg(3) or arg(4) not in (0, 1) or obj['locked']:
                raise Blocked('Unsupported PCM playback arguments/state')
            obj.update(playing=True, looping=bool(arg(4)), started_ms=self.milliseconds)
            self.returned(0, 16)
        elif kind == 'IDirectSoundBuffer' and method == 'Stop':
            obj['playing'] = False
            self.returned(0, 4)
        elif method == 'Release':
            if obj.get('locked'):
                raise Blocked('Releasing a locked physical object')
            obj['references'] -= 1
            self.returned(obj['references'], 4)
        elif method == 'SetCooperativeLevel':
            if arg(2) != 1 or arg(3) != (0x11 if kind == 'IDirectDraw' else 1):
                raise Blocked('Unsupported cooperative window/flags')
            obj.update(window=arg(2), cooperative_flags=arg(3))
            event.update(window=arg(2), flags=arg(3))
            self.returned(0, 12)
        elif method == 'GetCaps' and kind == 'IDirectDraw':
            for destination in (arg(2), arg(3)):
                if destination:
                    if self.word(destination) != 0x13c:
                        raise Blocked('Expected legacy DDCAPS size')
                    # No acceleration/overlays advertised by this memory display.
                    self.machine.mem_write(destination, bytes(0x13c))
                    self.put(destination, 0x13c)
            self.returned(0, 12)
        elif method == 'WaitForVerticalBlank':
            if arg(2) != 1 or arg(3):
                raise Blocked('Unsupported native vertical-blank wait flags/event')
            self.returned(0, 12)
        elif method == 'SetDisplayMode':
            if (arg(2), arg(3), arg(4)) not in ((640, 480, 8), (800, 600, 8)) or 'window' not in obj:
                raise Blocked('Unsupported display mode or missing cooperative owner')
            self.display_mode = (arg(2), arg(3), arg(4))
            event['mode'] = self.display_mode
            self.returned(0, 16)
        elif method == 'GetDisplayMode':
            self.display_description(arg(2))
            event['description'] = bytes(self.machine.mem_read(arg(2), 108)).hex()
            self.returned(0, 8)
        elif method == 'EnumDisplayModes':
            if arg(2) or arg(3) or not self.is_game(arg(5)) or self.callback:
                raise Blocked('Unsupported mode enumeration arguments or nested callback')
            descriptor = self.allocate(108)
            self.put(descriptor, 108)
            self.display_description(descriptor)
            callback_sp = sp - 12
            self.callback = dict(context=self.machine.context_save(), fs=self.word(0),
                                 sp=sp, event=event, cpu=self.cpu_state(), descriptor=descriptor)
            event.update(callback=hex(arg(5)), description=bytes(self.machine.mem_read(descriptor, 108)).hex())
            target, context = arg(5), arg(4)
            for index, value in enumerate((CALLBACK_RETURN, descriptor, context)):
                self.put(callback_sp + index * 4, value)
            self.machine.reg_write(UC_X86_REG_ESP, callback_sp)
            self.machine.reg_write(UC_X86_REG_EIP, target)
            self.pending = (address, 'platform_callback')
        elif method == 'CreateSurface':
            descriptor = arg(2)
            flags, caps = self.word(descriptor + 4), self.word(descriptor + 104)
            if self.word(descriptor) != 108 or arg(4):
                raise Blocked('Unsupported surface descriptor or aggregation')
            # An actual physical allocation failure, never a scripted game
            # resize result. The original controller performs its own unwind.
            if caps & 0x200 and getattr(self, 'fail_primary_creation', False):
                self.fail_primary_creation = False
                self.put(arg(3), 0)
                event.update(descriptor=bytes(self.machine.mem_read(descriptor, 108)).hex(),
                             result=0x8007000e)
                self.returned(0x8007000e, 16)
                return
            if caps & 0x200:
                if flags != 0x21 or caps != 0x218 or self.word(descriptor + 20) != 1:
                    raise Blocked('Unsupported primary surface chain')
                width, height, _ = self.display_mode
                surface = self.surface(width, height, caps)
                back = self.surface(width, height, 4)
                self.com_objects[surface]['back'] = back
            else:
                if flags != 7 or caps not in (0x40, 0x840):
                    raise Blocked('Unsupported offscreen surface descriptor')
                surface = self.surface(self.word(descriptor + 12), self.word(descriptor + 8), caps)
            self.put(arg(3), surface)
            event.update(surface=hex(surface), descriptor=bytes(self.machine.mem_read(descriptor, 108)).hex())
            self.returned(0, 16)
        elif method == 'GetAttachedSurface':
            if self.word(arg(2)) != 4 or 'back' not in obj:
                raise Blocked('Unknown attached surface')
            back = obj['back']
            self.com_objects[back]['references'] += 1
            self.put(arg(3), back)
            self.returned(0, 12)
        elif method in ('GetSurfaceDesc', 'Lock') and kind == 'IDirectDrawSurface':
            if method == 'Lock':
                if arg(2) or arg(5) or arg(4) & ~0x31 or obj['locked'] or obj['lost']:
                    raise Blocked('Unsupported physical surface lock rectangle/flags/state')
                destination = arg(3)
            else:
                destination = arg(2)
            self.display_description(destination)
            for offset, value in ((4, 0x102f if 'back' in obj else 0x100f),
                                  (8, obj['height']), (12, obj['width']), (16, obj['pitch']),
                                  (20, 1 if 'back' in obj else 0),
                                  (104, obj['caps'])):
                self.put(destination + offset, value)
            if method == 'Lock':
                self.put(destination + 4, self.word(destination + 4) | 0x800)
                self.put(destination + 36, obj['pixels'])
                obj['locked'] = True
                event.update(pixels=hex(obj['pixels']), pitch=obj['pitch'])
            self.returned(0, 20 if method == 'Lock' else 8)
        elif method == 'Unlock' and kind == 'IDirectDrawSurface':
            if not obj['locked'] or obj.get('dc') or arg(2) not in (0, obj['pixels']):
                raise Blocked('Invalid physical surface unlock')
            obj['locked'] = False
            event['pixels_sha256'] = hashlib.sha256(bytes(self.machine.mem_read(obj['pixels'], obj['pitch'] * obj['height']))).hexdigest()
            self.returned(0, 8)
        elif method == 'IsLost':
            self.returned(0x887601c2 if obj['lost'] else 0, 4)
        elif method == 'SetColorKey':
            if arg(2) != 8 or not arg(3):
                raise Blocked('Only source-blit color keys are provided')
            low, high = self.word(arg(3)), self.word(arg(3) + 4)
            if not 0 <= low <= high <= 255:
                raise Blocked('Invalid indexed color key')
            obj['color_key'] = (low, high)
            self.returned(0, 12)
        else:
            raise Blocked(f'No physical fixture for {kind}::{method}')

    def cstring_list(self, address, receiver, argument=0):
        """Physical CStringList storage with the original 32-bit public layout.

        AddHead/AddTail accept LPCSTR; POSITION is the node address. RemoveHead
        constructs its CString result in the caller's hidden output argument.
        CPlex blocks own nodes; CString buffers have their own reference counts.
        No Python-only ownership state is needed when restoring a checkpoint.
        """
        if address == 0x4f5249:
            if not 1 <= argument <= 4096:
                raise Blocked('CStringList block size outside bounded profile')
            self.machine.mem_write(receiver, bytes(28))
            self.put(receiver, 0x510224)
            self.put(receiver + 24, argument)
            self.returned(receiver, 4)
            return
        block_size = self.word(receiver + 24)
        if not 1 <= block_size <= 4096:
            raise Blocked('CStringList block size outside bounded profile')
        blocks, pool = [], set()
        block = self.word(receiver + 20)
        while block:
            if (block in blocks or len(pool) + block_size > 65536 or
                    self.allocations.get(block) != 4 + block_size * 12):
                raise Blocked('Invalid CStringList CPlex ownership')
            blocks.append(block)
            pool.update(block + 4 + index * 12 for index in range(block_size))
            block = self.word(block)
        nodes, previous, node = [], 0, self.word(receiver + 4)
        while node:
            if node not in pool or node in nodes or self.word(node + 4) != previous:
                raise Blocked('Invalid CStringList links')
            nodes.append(node)
            previous, node = node, self.word(node)
        if len(nodes) != self.word(receiver + 12) or previous != self.word(receiver + 8):
            raise Blocked('Invalid CStringList count/tail')
        free_nodes, node = set(), self.word(receiver + 16)
        while node:
            if node not in pool or node in free_nodes or node in nodes:
                raise Blocked('Invalid CStringList free chain')
            free_nodes.add(node)
            node = self.word(node)
        if set(nodes) | free_nodes != pool:
            raise Blocked('Unowned CStringList pool node')
        empty = {self.empty_string, self.word(0x52e1cc)}
        for node in nodes:
            value = self.word(node + 8)
            if value in empty:
                continue
            size = self.allocations.get(value - 12, 0)
            refs, length, capacity = (self.word(value - offset) for offset in (12, 8, 4))
            if (not 1 <= refs <= 0x7fffffff or size < 13 or
                    not length <= capacity <= size - 13 or
                    self.machine.mem_read(value + length, 1) != b'\0'):
                raise Blocked('Invalid CStringList string ownership')
        if address in (0x4f5382, 0x4f53b7):
            # Read before allocating or publishing a node, including aliasing
            # input that points into another element's CString buffer.
            text = self.bytestring(argument) if argument else b''
            if not self.word(receiver + 16):
                block = self.allocate(4 + block_size * 12)
                self.put(block, self.word(receiver + 20))
                self.put(receiver + 20, block)
                for index in range(block_size - 1, -1, -1):
                    node = block + 4 + index * 12
                    self.put(node, self.word(receiver + 16))
                    self.put(receiver + 16, node)
            node = self.word(receiver + 16)
            self.put(receiver + 16, self.word(node))
            following = self.word(receiver + 4) if address == 0x4f5382 else 0
            previous = self.word(receiver + 8) if address == 0x4f53b7 else 0
            self.put(node, following)
            self.put(node + 4, previous)
            self.put(node + 8, self.cstring(text) if text else self.empty_string)
            self.put(previous if previous else receiver + 4, node)
            self.put(following + 4 if following else receiver + 8, node)
            self.put(receiver + 12, len(nodes) + 1)
            self.returned(node, 4)
        elif address == 0x4f53eb:
            if not nodes or not argument:
                raise Blocked('CStringList RemoveHead needs an element and output')
            node = nodes[0]
            # The original's two CString copies and two destructors have net
            # zero reference-count change: ownership passes to the output.
            self.put(argument, self.word(node + 8))
            following = self.word(node)
            self.put(receiver + 4, following)
            self.put(following + 4 if following else receiver + 8, 0)
            self.put(node, self.word(receiver + 16))
            self.put(receiver + 16, node)
            self.put(receiver + 12, len(nodes) - 1)
            if len(nodes) == 1:
                for block in blocks:
                    self.allocations.pop(block)
                for offset in (16, 20):
                    self.put(receiver + offset, 0)
            self.returned(argument, 4)
        elif address == 0x4f5288:
            for node in nodes:
                value = self.word(node + 8)
                if value not in empty:
                    references = self.word(value - 12) - 1
                    self.put(value - 12, references)
                    if not references:
                        self.allocations.pop(value - 12)
            for block in blocks:
                self.allocations.pop(block)
            for offset in (4, 8, 12, 16, 20):
                self.put(receiver + offset, 0)
            self.returned(0)
        else:
            raise Blocked('Unprovided CStringList operation')

    def fixture(self, address):
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        receiver = self.machine.reg_read(UC_X86_REG_ECX)
        arg = lambda i: self.word(sp + 4 * i)
        names = {
            0x4f58de: 'MFC pointer-array destructor',
            0x4f551d: 'MFC object-array destructor',
            0x4ff5f9: 'CMemFile constructor', 0x4ff645: 'CMemFile Attach',
            0x4ff670: 'CMemFile Detach', 0x4ff682: 'CMemFile destructor',
            0x4ff79f: 'CMemFile Read',
            0x4fda33: 'CArchive constructor', 0x4fdb0f: 'CArchive destructor',
            0x4fddbd: 'CArchive FillBuffer', 0x4fd877: 'CArchive CString extraction',
            0x4f5db6: 'CMapStringToPtr RemoveKey',
            0x4f5e1e: 'CMapStringToPtr GetNextAssoc',
            0x4f61a1: 'CMapStringToPtr RemoveAll',
            0x4a3ce0: 'CRT atoi',
            0x4b0a70: 'CRT strncpy',
            0x4f6286: 'CMapStringToPtr Lookup', 0x4f62a8: 'CMapStringToPtr operator[]',
            0x4a3920: 'CRT sprintf',
            0x4f4f58: 'CString Format',
            0x4a35f0: 'CRT atexit',
            0x4a3050: 'CRT rand',
            0x4a4590: 'CRT vector constructor iterator',
            0x4a4450: 'CRT vector destructor iterator',
            0x4f1d90: 'CRT fopen', 0x4a7840: 'CRT fseek', 0x4a7260: 'CRT fread',
            0x4a7ae0: 'CRT fclose', 0x4a3cf0: 'CRT _stricmp',
            0x4f1b30: 'CRT _CIpow', 0x4f1a60: 'CRT _CIlog',
            0x4f2400: 'CRT _CIacos', 0x4a30e0: 'CRT _ftol',
            0x4f4486: 'DirectDrawCreate', 0x4f4480: 'DirectSoundCreate',
            0x4f5915: 'CPtrArray SetSize', 0x4f582f: 'CPtrArray SetAtGrow',
            0x4f51c5: 'CObList AddTail', 0x4f572a: 'CPtrList InsertBefore',
            0x4f5212: 'CObList RemoveAt',
            0x4f5172: 'CObList RemoveAll',
            0x4f5249: 'CStringList constructor',
            0x4f5382: 'CStringList AddHead', 0x4f53b7: 'CStringList AddTail',
            0x4f53eb: 'CStringList RemoveHead', 0x4f5288: 'CStringList RemoveAll',
            0x4f63ec: 'operator new', 0x4a48e0: 'malloc', 0x4f6428: 'operator delete',
            0x4f6439: 'CString default constructor', 0x4f65f2: 'CString text constructor',
            0x4f6449: 'CString copy constructor',
            0x4f6a1d: 'CString MakeLower', 0x4f4c93: 'CString Find substring',
            0x4f66cc: 'CString text assignment',
            0x4f667d: 'CString assignment', 0x4f6584: 'CString destructor',
            0x4f5133: 'CObList constructor', 0x4f54ea: 'CPtrArray constructor', 0x4f58ab: 'CByteArray constructor',
            0x4f57c5: 'CWordArray constructor', 0x4f5620: 'CPtrList constructor',
            0x4f5cbd: 'CMapStringToPtr constructor', 0x4f6118: 'CMapPtrToPtr constructor',
        }
        name = self.imports[address][1] if address in self.imports else names.get(address)
        if not name:
            self.platform_call(address, 'unprovided CRT/MFC entry')
            raise Blocked('No platform fixture for this CRT/MFC entry; original platform code is not executed')
        self.platform_call(address, name)
        if address in (0x4f5249, 0x4f5382, 0x4f53b7, 0x4f53eb, 0x4f5288):
            self.cstring_list(address, receiver, 0 if address == 0x4f5288 else arg(1))
        elif address == 0x4a3050:
            # Native deterministic random service, with an explicitly elected
            # seed shared by both sides. No actor outcome is supplied here.
            self.random_state = (214013 * self.random_state + 2531011) & 0xffffffff
            value = (self.random_state >> 16) & 0x7fff
            self.physical_events.append(dict(service=name, state=self.random_state, result=value))
            self.returned(value)
        elif address == 0x4a35f0:
            if not self.is_game(arg(1)) or len(self.exit_callbacks) >= 1024:
                raise Blocked('Invalid bounded physical exit callback registration')
            self.exit_callbacks.append(arg(1))
            self.physical_events.append(dict(service=name, callback=hex(arg(1)),
                lifetime='registered until process teardown; not executed during idle trace'))
            self.returned(0)
        elif address == 0x4ff5f9:
            if receiver in self.memory_files:
                raise Blocked('Live CMemFile constructed twice')
            self.memory_files[receiver] = dict(grow=arg(1), data=0, length=0)
            self.machine.mem_write(receiver, bytes(0x28))
            self.put(receiver, 0x5142f4)
            self.put(receiver + 4, 0xffffffff)
            self.put(receiver + 12, self.empty_string)
            self.put(receiver + 16, arg(1))
            self.put(receiver + 36, 1)
            self.returned(receiver, 4)
        elif address == 0x4ff645:
            file = self.memory_files.get(receiver)
            if not file or file['data'] or arg(3) or not arg(1) or arg(2) > 0x800000:
                raise Blocked('Unsupported read-only CMemFile attachment')
            file.update(data=arg(1), length=arg(2), grow=0)
            for offset, value in ((16, 0), (20, 0), (24, arg(2)), (28, arg(2)), (32, arg(1)), (36, 0)):
                self.put(receiver + offset, value)
            self.physical_events.append(dict(service=name, receiver=hex(receiver), bytes=arg(2),
                sha256=hashlib.sha256(bytes(self.machine.mem_read(arg(1), arg(2)))).hexdigest()))
            self.returned(0, 12)
        elif address == 0x4ff79f:
            file = self.memory_files.get(receiver)
            if not file or arg(2) > 0x800000:
                raise Blocked('Invalid bounded CMemFile read')
            position = self.word(receiver + 20)
            if position > file['length'] or arg(2) and not file['data']:
                raise Blocked('Invalid CMemFile read cursor or attachment')
            count = min(arg(2), file['length'] - position)
            if count:
                self.machine.mem_write(arg(1), bytes(self.machine.mem_read(file['data'] + position, count)))
            self.put(receiver + 20, position + count)
            self.physical_events.append(dict(service=name, receiver=hex(receiver),
                position=position, bytes=count))
            self.returned(count, 8)
        elif address in (0x4ff670, 0x4ff682):
            file = self.memory_files.get(receiver)
            if not file or any(a['file'] == receiver for a in self.archives.values()):
                raise Blocked('Invalid CMemFile lifetime')
            data = file['data']
            file.update(data=0, length=0)
            for offset in (20, 24, 28, 32):
                self.put(receiver + offset, 0)
            if address == 0x4ff682:
                del self.memory_files[receiver]
                self.put(receiver, 0x50becc)
            self.returned(data if address == 0x4ff670 else 0)
        elif address == 0x4fda33:
            file = self.memory_files.get(arg(1))
            if not file or not file['data'] or arg(2) != 1 or arg(4) or receiver in self.archives:
                raise Blocked('Unsupported CArchive load source/mode')
            # CMemFile supports direct buffering. Expose its attached bytes;
            # the original game serializers consume +24/+28 inline.
            self.machine.mem_write(receiver, bytes(0x44))
            for offset, value in ((4, 1), (8, 1), (12, 0xffffffff), (16, self.empty_string),
                                  (20, 1), (24, 1), (28, max(128, arg(3))), (32, arg(1)),
                                  (36, file['data']), (40, file['data'] + file['length']),
                                  (44, file['data']), (60, 64), (64, 137)):
                self.put(receiver + offset, value)
            self.archives[receiver] = dict(file=arg(1), start=file['data'], end=file['data'] + file['length'])
            self.returned(receiver, 16)
        elif address == 0x4fddbd:
            raise Blocked('CArchive read past attached physical buffer')
        elif address == 0x4fd877:
            archive, string = arg(1), arg(2)
            length = self.archive_read(archive, 1)[0]
            if length == 255:
                length = int.from_bytes(self.archive_read(archive, 2), 'little')
                if length == 0xfffe:
                    raise Blocked('Unicode CArchive CString transport not provided')
                if length == 0xffff:
                    length = int.from_bytes(self.archive_read(archive, 4), 'little')
            if length > 65536:
                raise Blocked('CArchive string exceeds transport bound')
            self.put(string, self.cstring(self.archive_read(archive, length)))
            self.returned(archive, 8)
        elif address == 0x4fdb0f:
            archive = self.archives.get(receiver)
            if not archive:
                raise Blocked('Unknown CArchive destructor receiver')
            cursor = self.word(receiver + 36)
            if not archive['start'] <= cursor <= archive['end']:
                raise Blocked('Invalid CArchive terminal cursor')
            self.put(archive['file'] + 20, cursor - archive['start'])
            self.physical_events.append(dict(service=name, consumed=cursor - archive['start'],
                                              bytes=archive['end'] - archive['start']))
            del self.archives[receiver]
            self.put(receiver + 32, 0)
            self.returned(0)
        elif address in (0x4f58de, 0x4f551d):
            self.array_resize(receiver, 0)
            self.put(receiver, 0x50becc)
            self.returned(0)
        elif address == 0x4a3ce0:
            match = re.match(rb'\s*([+-]?[0-9]+)', self.bytestring(arg(1)))
            self.returned(int(match[1]) if match else 0)
        elif address == 0x4b0a70:
            count = arg(3)
            if count > 65536:
                raise Blocked('Bounded strncpy count exceeded')
            result = bytearray()
            for index in range(count):
                byte = self.machine.mem_read(arg(2) + index, 1)[0]
                if not byte:
                    break
                result.append(byte)
            self.machine.mem_write(arg(1), bytes(result).ljust(count, b'\0'))
            self.returned(arg(1))
        elif address == 0x4f5e1e:
            mapping = self.maps.get(receiver)
            if not mapping:
                raise Blocked('Cannot enumerate an empty/unknown native map')
            rows = list(mapping.items())
            position = self.word(arg(1))
            if position == 0xffffffff:
                index = 0
            else:
                indices = [i for i,(_,cell) in enumerate(rows) if cell == position]
                if len(indices) != 1:
                    raise Blocked('Invalid native map enumeration position')
                index = indices[0]
            key, cell = rows[index]
            value = self.word(cell)
            following = rows[index+1][1] if index+1 < len(rows) else 0
            self.put(arg(1), following)
            self.put(arg(2), self.cstring(key))
            self.put(arg(3), value)
            self.physical_events.append(dict(service=name, receiver=hex(receiver),
                                            key=key.decode('ascii'), value=hex(value)))
            self.returned(0, 12)
        elif address == 0x4f61a1:
            mapping = self.maps.get(receiver)
            if mapping is None:
                raise Blocked('Unknown native map receiver')
            cells = list(mapping.values())
            if len(set(cells)) != len(cells) or any(cell not in self.allocations for cell in cells):
                raise Blocked('Invalid native map association ownership')
            for cell in cells:
                self.allocations.pop(cell)
            mapping.clear()
            for offset in (4, 12, 16, 20):
                self.put(receiver + offset, 0)
            self.physical_events.append(dict(service=name, receiver=hex(receiver), removed=len(cells)))
            self.returned(0)
        elif address in (0x4f6286, 0x4f62a8, 0x4f5db6):
            if receiver not in self.maps:
                raise Blocked('Unconstructed MFC map')
            mapping = self.maps[receiver]
            key = self.bytestring(arg(1))
            if address == 0x4f6286:
                found = key in mapping
                if found:
                    self.put(arg(2), self.word(mapping[key]))
                self.returned(int(found), 8)
            elif address == 0x4f5db6:
                cell = mapping.pop(key, None)
                if cell is not None:
                    # The map owns its association, never the pointed-to game
                    # object. The original caller performs that destruction.
                    self.physical_events.append(dict(service=name, receiver=hex(receiver),
                        key=key.decode('ascii'), value=hex(self.word(cell))))
                    self.allocations.pop(cell)
                    self.put(receiver + 12, len(mapping))
                self.returned(int(cell is not None), 4)
            else:
                if key not in mapping:
                    mapping[key] = self.allocate(4)
                    self.put(mapping[key], 0)
                    self.put(receiver + 12, len(mapping))
                self.returned(mapping[key], 4)
        elif address in (0x4a3920, 0x4f4f58):
            fmt = self.bytestring(arg(2))
            formats = re.findall(rb'%(?:0?[0-9]*)?[disuxX%]', fmt)
            if b'%' in re.sub(rb'%(?:0?[0-9]*)?[disuxX%]', b'', fmt):
                raise Blocked(f'Unsupported bounded sprintf format {fmt!r}')
            values = []
            for spec in formats:
                if spec == b'%%':
                    continue
                value = arg(3 + len(values))
                if spec.endswith(b's'):
                    value = self.bytestring(value)
                elif spec[-1:] in (b'd', b'i'):
                    value = struct.unpack('<i', struct.pack('<I', value))[0]
                values.append(value)
            result = fmt % tuple(values)
            if len(result) > 4096:
                raise Blocked('Formatted string exceeds fixture bound')
            if address == 0x4f4f58:
                self.put(arg(1), self.cstring(result))
                self.returned(0)
            else:
                self.machine.mem_write(arg(1), result + b'\0')
                self.returned(len(result))
        elif address in (0x4a4590, 0x4a4450):
            if address == 0x4a4590:
                base, stride, count, constructor, destructor = [arg(i) for i in range(1, 6)]
                pop = 20
            else:
                base, stride, count, constructor = [arg(i) for i in range(1, 5)]
                destructor = constructor
                pop = 16
            if count > 4096 or not stride or not self.is_game(constructor) or not self.is_game(destructor):
                raise Blocked('Unsupported vector construction profile')
            event = dict(service=name, base=hex(base), stride=stride, count=count,
                         constructor=hex(constructor), destructor=hex(destructor), completed=0)
            self.physical_events.append(event)
            if not count:
                self.returned(0, pop)
            else:
                if address == 0x4a4450:
                    base += (count - 1) * stride
                    stride = -stride
                frame = dict(context=self.machine.context_save(), fs=self.word(0), sp=sp,
                             cpu=self.cpu_state(), base=base, stride=stride, count=count,
                             constructor=constructor, index=0, event=event, pop=pop, service=address)
                self.array_callbacks.append(frame)
                self.start_array_element(frame)
        elif address == 0x4f1d90:
            path, mode = self.bytestring(arg(1)), self.bytestring(arg(2))
            if path != b'CLAW.REZ' or mode != b'rb':
                raise Blocked(f'Unprovided read-only file/mode: {path!r} {mode!r}')
            handle = 0
            if not self.missing_resource:
                handle = self.allocate(32)
                self.files[handle] = REZ_PATH.open('rb')
            self.physical_events.append(dict(service=name, path=path.decode(), mode=mode.decode(),
                                              handle=hex(handle), missing=self.missing_resource))
            self.returned(handle)
        elif address in (0x4a7840, 0x4a7260, 0x4a7ae0):
            handle = arg(4) if address == 0x4a7260 else arg(1)
            stream = self.files.get(handle)
            if stream is None:
                if address == 0x4a7ae0 and handle in self.closed_files:
                    self.physical_events.append(dict(service=name, result=0xffffffff))
                    self.returned(0xffffffff)
                    return
                raise Blocked('Unknown or closed CRT file handle')
            if address == 0x4a7840:
                offset = struct.unpack('<i', struct.pack('<I', arg(2)))[0]
                if arg(3) not in (0, 1, 2):
                    raise Blocked('Unknown CRT seek origin')
                stream.seek(offset, arg(3))
                self.returned(0)
            elif address == 0x4a7260:
                size, count = arg(2), arg(3)
                if size * count > 0x800000:
                    raise Blocked('Read exceeds physical file fixture bound')
                offset = stream.tell()
                data = stream.read(size * count)
                if data:
                    self.machine.mem_write(arg(1), data)
                self.physical_events.append(dict(service=name, handle=hex(handle), offset=offset,
                    requested=size * count, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
                self.returned(len(data) // size if size else 0)
            else:
                stream.close()
                del self.files[handle]
                self.closed_files.add(handle)
                self.physical_events.append(dict(service=name, result=0))
                self.returned(0)
        elif address == 0x4a3cf0:
            left, right = self.bytestring(arg(1)).lower(), self.bytestring(arg(2)).lower()
            self.returned((left > right) - (left < right))
        elif address in (0x4f1b30, 0x4f1a60, 0x4f2400, 0x4a30e0):
            self.math_fixture(address)
        elif address in (0x4f4486, 0x4f4480):
            if arg(1) or arg(3):
                raise Blocked('Only default nonaggregated DirectX devices are supported')
            obj = self.com_object('IDirectDraw' if address == 0x4f4486 else 'IDirectSound')
            self.put(arg(2), obj)
            self.physical_events.append(dict(service=name, object=hex(obj), output=hex(arg(2))))
            self.returned(0, 12)
        elif address in (0x4f5915, 0x4f582f):
            if address == 0x4f5915:
                self.array_resize(receiver, arg(1), arg(2))
            else:
                if arg(1) >= self.word(receiver + 8):
                    self.array_resize(receiver, arg(1) + 1)
                self.put(self.word(receiver + 4) + arg(1) * 4, arg(2))
            self.returned(0, 8)
        elif address == 0x4f5172:
            current, seen = self.word(receiver + 4), set()
            while current:
                if current in seen or current not in self.allocations or len(seen) >= 4096:
                    raise Blocked('Invalid native list ownership during RemoveAll')
                seen.add(current)
                current = self.word(current)
            if len(seen) != self.word(receiver + 12):
                raise Blocked('Invalid native list count during RemoveAll')
            for node in seen:
                self.allocations.pop(node)
            for offset in (4, 8, 12, 16, 20):
                self.put(receiver + offset, 0)
            self.physical_events.append(dict(service=name, receiver=hex(receiver), removed=len(seen)))
            self.returned(0)
        elif address == 0x4f5212:
            node = arg(1)
            current, seen = self.word(receiver + 4), set()
            while current:
                if current in seen or current not in self.allocations or len(seen) >= 4096:
                    raise Blocked('Invalid MFC list chain')
                seen.add(current)
                current = self.word(current)
            if node not in seen or len(seen) != self.word(receiver + 12):
                raise Blocked('Invalid MFC RemoveAt position/count')
            following, previous = self.word(node), self.word(node + 4)
            self.put(previous if previous else receiver + 4, following)
            self.put(following + 4 if following else receiver + 8, previous)
            self.put(receiver + 12, len(seen) - 1)
            self.allocations.pop(node)
            self.returned(0, 4)
        elif address in (0x4f51c5, 0x4f572a):
            position = arg(1) if address == 0x4f572a else 0
            following = position
            if address == 0x4f572a and not position:
                following = self.word(receiver + 4)
            seen, current = set(), self.word(receiver + 4)
            while current:
                if current in seen or current not in self.allocations or len(seen) >= 4096:
                    raise Blocked('Invalid MFC list chain')
                seen.add(current)
                current = self.word(current)
            if position and position not in seen or len(seen) != self.word(receiver + 12):
                raise Blocked('Invalid MFC list position/count')
            node = self.allocate(12)
            tail = self.word(following + 4) if following else self.word(receiver + 8)
            self.put(node, following)
            self.put(node + 4, tail)
            self.put(node + 8, arg(2) if address == 0x4f572a else arg(1))
            if tail:
                self.put(tail, node)
            else:
                self.put(receiver + 4, node)
            if following:
                self.put(following + 4, node)
            else:
                self.put(receiver + 8, node)
            self.put(receiver + 12, self.word(receiver + 12) + 1)
            self.returned(node, 8 if address == 0x4f572a else 4)
        elif address in (0x4f63ec, 0x4a48e0):
            self.returned(self.allocate(arg(1)))
        elif address == 0x4f6428:
            if arg(1) and arg(1) not in self.allocations:
                raise Blocked('Delete of unknown allocation')
            self.allocations.pop(arg(1), None)
            self.returned(0)
        elif address == 0x4f6a1d:
            value = self.bytestring(self.word(receiver))
            if not value.isascii():
                raise Blocked('CString case conversion requires the elected ASCII locale')
            self.put(receiver, self.cstring(value.lower()))
            self.returned(0)
        elif address == 0x4f4c93:
            self.returned(self.bytestring(self.word(receiver)).find(self.bytestring(arg(1))), 4)
        elif address in (0x4f6439, 0x4f65f2, 0x4f667d, 0x4f6449, 0x4f66cc):
            value = self.empty_string
            if address in (0x4f65f2, 0x4f66cc) and arg(1):
                if arg(1) < 0x10000:
                    raise Blocked('CString resource-ID loading needs an explicit resource fixture')
                value = self.cstring(self.bytestring(arg(1)))
            elif address in (0x4f667d, 0x4f6449):
                value = self.cstring(self.bytestring(self.word(arg(1))))
            self.put(receiver, value)
            self.returned(receiver, 0 if address == 0x4f6439 else 4)
        elif address == 0x4f6584:
            # Fixture storage remains allocated until the process ends. Object
            # references are reset; no game callback/destructor is substituted.
            self.put(receiver, self.empty_string)
            self.returned(0)
        elif address in (0x4f5133, 0x4f54ea, 0x4f58ab, 0x4f57c5, 0x4f5620, 0x4f5cbd, 0x4f6118):
            length = 20 if address in (0x4f54ea, 0x4f58ab, 0x4f57c5) else 28
            self.machine.mem_write(receiver, bytes(length))
            vtables = {0x4f5133: 0x51000c, 0x4f54ea: 0x51079c, 0x4f58ab: 0x5108fc, 0x4f57c5: 0x5108d4, 0x4f5620: 0x5107bc,
                       0x4f5cbd: 0x510054, 0x4f6118: 0x5105c4}
            self.put(receiver, vtables[address])
            if length == 28:
                self.put(receiver + 24, arg(1))
                if address in (0x4f5cbd, 0x4f6118):
                    self.put(receiver + 8, 17)
                    self.maps[receiver] = {}
            self.returned(receiver, 0 if length == 20 else 4)
        else:
            api = name.split('!')[-1]
            if api in ('SetBkMode', 'SetTextColor', 'DrawTextA'):
                self.text_fixture(api, arg)
            elif api in ('timeGetTime', 'GetTickCount'):
                self.milliseconds += getattr(self, 'clock_step', 0)
                self.returned(self.milliseconds)
            elif api == 'PostMessageA':
                if (arg(1), arg(2), arg(3), arg(4)) != (1, 0x10, 0, 0):
                    raise Blocked('Unelected native window message')
                self.messages.append((arg(1), arg(2), arg(3), arg(4)))
                self.physical_events.append(dict(service=api, window=arg(1), message=arg(2),
                                                wparam=arg(3), lparam=arg(4)))
                self.returned(1, 16)
            elif api == 'GetCursorPos':
                self.put(arg(1), self.cursor[0])
                self.put(arg(1) + 4, self.cursor[1])
                self.physical_events.append(dict(service=api, position=self.cursor))
                self.returned(1, 4)
            elif api == 'PeekMessageA':
                if arg(2) not in (0, 1) or arg(5) not in (0, 1) or self.messages:
                    raise Blocked('Message transport only provides the empty initial input queue')
                self.physical_events.append(dict(service=api, window=arg(2),
                    minimum=arg(3), maximum=arg(4), remove=arg(5), queued=len(self.messages)))
                self.returned(0, 20)
            elif api == 'ShowCursor':
                self.cursor_display_count += 1 if arg(1) else -1
                self.physical_events.append(dict(service=api, show=bool(arg(1)), count=self.cursor_display_count))
                self.returned(self.cursor_display_count, 4)
            elif api == 'GetAsyncKeyState':
                if arg(1) > 255:
                    raise Blocked('Invalid physical virtual-key code')
                self.returned(0x8000 if arg(1) in self.pressed_keys else 0, 4)
            elif api == 'GetSystemMetrics':
                if arg(1) not in (0, 1):
                    raise Blocked('Unprovided physical system metric')
                self.returned(self.display_mode[arg(1)], 4)
            elif api == 'SetCursorPos':
                self.cursor = (arg(1), arg(2))
                self.returned(1, 8)
            elif api == '_AIL_startup@0':
                self.midi_started = True
                self.physical_events.append(dict(service=api))
                self.returned(1)
            elif api == '_AIL_midiOutOpen@12':
                if not self.midi_started or arg(2) or arg(3) != 0xffffffff:
                    raise Blocked('Unsupported physical MIDI output profile')
                driver = self.allocate(16)
                self.midi_drivers[driver] = dict(device='default', open=True)
                self.put(arg(1), driver)
                self.physical_events.append(dict(service=api, driver=hex(driver), device='default'))
                self.returned(0, 12)
            elif api == '_AIL_set_XMIDI_master_volume@8':
                if arg(1) not in self.midi_drivers or arg(2) > 127:
                    raise Blocked('Unsupported physical MIDI master volume')
                self.midi_master_volume = arg(2)
                self.physical_events.append(dict(service=api, driver=hex(arg(1)), volume=arg(2)))
                self.returned(0, 8)
            elif api == '_AIL_allocate_sequence_handle@4':
                if arg(1) not in self.midi_drivers:
                    raise Blocked('Unknown physical MIDI driver')
                sequence = self.allocate(16)
                self.sequences[sequence] = dict(driver=arg(1), status=2, initialized=False, loops=1)
                self.physical_events.append(dict(service=api, sequence=hex(sequence), driver=hex(arg(1))))
                self.returned(sequence, 4)
            elif api == '_AIL_init_sequence@12':
                sequence = self.sequences.get(arg(1))
                size = self.allocations.get(arg(2))
                if not sequence or size is None or arg(3):
                    raise Blocked('Unsupported physical XMIDI sequence source/index')
                data = bytes(self.machine.mem_read(arg(2), size))
                parsed = parse_xmidi(data)
                sequence.update(initialized=True, status=2, sha256=hashlib.sha256(data).hexdigest(), **parsed)
                self.physical_events.append(dict(service=api, sequence=hex(arg(1)), bytes=size,
                    sha256=sequence['sha256'], events=parsed['events'], duration_ticks=parsed['duration_ticks']))
                self.returned(1, 12)
            elif api in ('_AIL_sequence_status@4', '_AIL_start_sequence@4', '_AIL_stop_sequence@4',
                         '_AIL_resume_sequence@4', '_AIL_end_sequence@4', '_AIL_set_sequence_loop_count@8',
                         '_AIL_release_sequence_handle@4'):
                sequence = self.sequences.get(arg(1))
                if not sequence or not sequence['initialized']:
                    raise Blocked('Unknown/uninitialized physical XMIDI sequence')
                if sequence['status'] == 4 and self.milliseconds != sequence['started_ms']:
                    raise Blocked('XMIDI playback clock advancement belongs to the idle-frame trace')
                if api in ('_AIL_start_sequence@4', '_AIL_resume_sequence@4'):
                    sequence.update(status=4, started_ms=self.milliseconds)
                elif api == '_AIL_stop_sequence@4':
                    sequence['status'] = 8
                elif api == '_AIL_end_sequence@4':
                    sequence['status'] = 2
                elif api == '_AIL_set_sequence_loop_count@8':
                    sequence['loops'] = arg(2)
                elif api == '_AIL_release_sequence_handle@4':
                    del self.sequences[arg(1)]
                    self.allocations.pop(arg(1))
                self.physical_events.append(dict(service=api, sequence=hex(arg(1)), status=sequence['status']))
                self.returned(sequence['status'] if api == '_AIL_sequence_status@4' else 0,
                              8 if api == '_AIL_set_sequence_loop_count@8' else 4)
            elif api in ('SetRect', 'SetRectEmpty'):
                for i in range(4):
                    self.put(arg(1) + i * 4, arg(i + 2) if api == 'SetRect' else 0)
                self.returned(1, 20 if api == 'SetRect' else 4)
            elif api == 'lstrlenA':
                self.returned(len(self.bytestring(arg(1))), 4)
            elif api in ('InterlockedIncrement', 'InterlockedDecrement'):
                value = self.word(arg(1)) + (1 if api == 'InterlockedIncrement' else -1)
                self.put(arg(1), value)
                self.returned(value, 4)
            else:
                raise Blocked(f'No physical fixture for {name}; unknown imports never return scripted success')

    def text_fixture(self, api, arg):
        dc = self.dcs.get(arg(1))
        if not dc:
            raise Blocked('Unknown or released physical text DC')
        surface = self.com_objects[dc['surface']]
        if (not surface['references'] or surface['lost'] or not surface['locked']
                or surface.get('dc') != arg(1) or dc['pixels'] != surface['pixels']):
            raise Blocked('Physical text DC lost its surface lease')
        event = dict(service=api, dc=hex(arg(1)), phase=self.phase,
            milliseconds=self.milliseconds, caller=self.last_transfer)
        if api == 'SetBkMode':
            if arg(2) not in (1, 2):
                raise Blocked('Invalid physical background mode')
            previous = dc['background_mode']
            dc['background_mode'] = arg(2)
            event.update(previous=previous, value=arg(2))
            self.returned(previous, 8)
        elif api == 'SetTextColor':
            if arg(2) > 0xffffff:
                raise Blocked('Unprovided palette-relative text color')
            previous = dc['text_color']
            dc['text_color'] = arg(2)
            event.update(previous=previous, value=arg(2))
            self.returned(previous, 8)
        else:
            # Reached transparent profiles: single-line left/right and the
            # MPKFA message's DT_CENTER. Control characters (including CR/LF)
            # remain rejected below; no multiline or word-wrap provider.
            # https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-drawtexta
            if arg(5) not in (0x1, 0x20, 0x22) or dc['background_mode'] != 1:
                raise Blocked('Unprovided physical DrawText flags/background')
            if arg(3) != 0xffffffff and arg(3) > 4096:
                raise Blocked('Unbounded physical DrawText length')
            raw = self.bytestring(arg(2)) if arg(3) == 0xffffffff else bytes(self.machine.mem_read(arg(2), arg(3)))
            if len(raw) > 4096 or any(b < 32 or b > 126 for b in raw) or b'&' in raw:
                raise Blocked('Unprovided physical text encoding/control/mnemonic')
            text = raw.decode('ascii')
            rect = struct.unpack('<4i', self.machine.mem_read(arg(4), 16))
            left, top, right, bottom = rect
            if not (-4096 <= left <= right <= 4096 and -4096 <= top <= bottom <= 4096):
                raise Blocked('Invalid physical text rectangle')
            width = math.ceil(self.font.getlength(text))
            x = (left + (right - left - width) // 2 if arg(5) & 1 else
                 right - width if arg(5) & 2 else left)
            mask = Image.new('1', (surface['width'], surface['height']))
            ImageDraw.Draw(mask).text((x, top), text, font=self.font, fill=1, anchor='lt')
            palette = bytes.fromhex(dc['palette'])
            rgb = [(dc['text_color'] >> (8 * c)) & 255 for c in range(3)]
            index = min(range(256), key=lambda i: sum((palette[4 * i + c] - rgb[c]) ** 2 for c in range(3)))
            before = bytes(self.machine.mem_read(dc['pixels'], surface['pitch'] * surface['height']))
            pixels = bytearray(before)
            painted = 0
            for y in range(max(0, top), min(surface['height'], bottom)):
                for x in range(max(0, left), min(surface['width'], right)):
                    if mask.getpixel((x, y)):
                        pixels[y * surface['pitch'] + x] = index
                        painted += 1
            self.machine.mem_write(dc['pixels'], bytes(pixels))
            event.update(text=text, rectangle=rect, flags=arg(5), palette_index=index,
                glyph_pixels=painted, changed_pixels=sum(a != b for a, b in zip(before, pixels)),
                before_sha256=hashlib.sha256(before).hexdigest(),
                pixels_sha256=hashlib.sha256(pixels).hexdigest(),
                glyph_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest())
            self.returned(sum(self.font.getmetrics()) if text else 0, 20)
        self.physical_events.append(event)

    def archive_read(self, receiver, length):
        archive = self.archives.get(receiver)
        if not archive:
            raise Blocked('Unknown CArchive read receiver')
        cursor = self.word(receiver + 36)
        if not archive['start'] <= cursor <= cursor + length <= archive['end']:
            raise Blocked('CArchive read past attached physical buffer')
        data = bytes(self.machine.mem_read(cursor, length))
        self.put(receiver + 36, cursor + length)
        return data

    def start_array_element(self, frame):
        sp = frame['sp'] - 4
        self.put(sp, ARRAY_RETURN)
        self.machine.reg_write(UC_X86_REG_ESP, sp)
        self.machine.reg_write(UC_X86_REG_ECX, frame['base'] + frame['index'] * frame['stride'])
        self.machine.reg_write(UC_X86_REG_EIP, frame['constructor'])
        self.pending = (frame.get('service', 0x4a4590), 'platform_callback')

    def hook(self, machine, address, size, user):
        self.instructions += 1
        self.recent.append(address)
        if self.instructions > self.instruction_limit:
            raise Blocked('Instruction budget exhausted')
        transfer = self.pending
        self.pending = None
        if transfer:
            site, kind = transfer
            self.edges[(site, address, kind)] += 1
            if kind == 'branch':
                self.branch_targets[address] += 1
            elif self.is_game(address):
                self.entries.add(address)
            self.last_transfer = dict(site=hex(site), target=hex(address), kind=kind)
        if address == self.boundary:
            self.paused = True
            machine.emu_stop()
            return
        if address == 0x45ace0:
            sp = machine.reg_read(UC_X86_REG_ESP)
            if self.word(sp) != 0x429335:
                raise Blocked('Menu initializer did not originate at the actual factory call')
            self.initializer_return = dict(entry=hex(address), continuation=hex(self.word(sp)),
                entry_stack=hex(sp), receiver=hex(machine.reg_read(UC_X86_REG_ECX)), status='entered')
        if address == 0x429335 and self.initializer_return:
            expected = int(self.initializer_return['entry_stack'], 16) + 16
            if machine.reg_read(UC_X86_REG_ESP) != expected:
                raise Blocked('Initializer returned with the wrong stack')
            result = machine.reg_read(UC_X86_REG_EAX)
            self.initializer_return.update(status='pass' if result else 'failed', result=result,
                                           return_stack=hex(expected), observed_pc=hex(address))
        if address == ARRAY_RETURN:
            if not self.array_callbacks:
                raise Blocked('Unexpected vector callback return')
            frame = self.array_callbacks[-1]
            cpu = self.cpu_state()
            if (machine.reg_read(UC_X86_REG_ESP) != frame['sp'] or self.word(0) != frame['fs']
                    or any(cpu[i] != frame['cpu'][i] for i in (1, 4, 5, 6))
                    or cpu[10:] != frame['cpu'][10:]):
                raise Blocked('Vector constructor changed preserved CPU/stack/exception state')
            frame['index'] += 1
            frame['event']['completed'] = frame['index']
            machine.context_restore(frame['context'])
            if frame['index'] < frame['count']:
                self.start_array_element(frame)
            else:
                self.array_callbacks.pop()
                self.returned(0, frame.get('pop', 20))
            return
        if address == CALLBACK_RETURN:
            callback = self.callback
            if not callback or machine.reg_read(UC_X86_REG_ESP) != callback['sp'] or self.word(0) != callback['fs']:
                raise Blocked('Physical callback corrupted its stack or exception chain')
            cpu = self.cpu_state()
            if (any(cpu[i] != callback['cpu'][i] for i in (1, 4, 5, 6))
                    or cpu[10:] != callback['cpu'][10:]
                    or bytes(machine.mem_read(callback['descriptor'], 108)).hex() != callback['event']['description']):
                raise Blocked('Physical callback changed preserved CPU state or read-only mode data')
            result = machine.reg_read(UC_X86_REG_EAX)
            if result not in (0, 1):
                raise Blocked('Invalid display enumeration callback result')
            callback['event']['callback_result'] = result
            callback['event']['preserved_cpu_stack_fs_and_descriptor'] = True
            machine.context_restore(callback['context'])
            self.callback = None
            self.returned(0, 20)
            return
        if address in self.com_methods:
            self.com_fixture(address)
            return
        # Dynamic CALL destinations include virtual targets absent from the
        # static map. Indexed entries also capture known tail calls/fallthrough.
        if self.is_game(address) and (transfer and transfer[1] != 'branch' or address in self.entries):
            self.functions[address] += 1
            self.phases.setdefault(address, set()).add(self.phase)
        if address in self.imports or (self.program.base <= address < 0x508000 and not self.is_game(address)):
            self.fixture(address)
            return
        if not self.is_game(address):
            raise Blocked(f'Execution outside elected game/platform ranges at {address:#x}')
        kind = self.decoded.get(address)
        if kind is None:
            instruction = next(self.decoder.disasm(bytes(machine.mem_read(address, size)), address), None)
            if instruction is None:
                raise Blocked('Could not decode executed original instruction')
            kind = ''
            if instruction.mnemonic == 'call':
                kind = 'direct_call' if instruction.operands[0].type == CS_OP_IMM else 'indirect_call'
            elif instruction.mnemonic == 'jmp':
                kind = 'branch'
            self.decoded[address] = kind
        if kind:
            self.pending = (address, kind)

    def run(self, address, receiver, arguments=(), phase='', boundary=None, stack=STACK):
        self.phase, self.boundary, self.paused = phase, boundary, False
        self.pending = (0, 'root')
        self.entries.add(address)
        for index, value in enumerate([STOP, *arguments]):
            self.put(stack + index * 4, value)
        self.machine.reg_write(UC_X86_REG_ESP, stack)
        self.machine.reg_write(UC_X86_REG_ECX, receiver)
        self.machine.emu_start(address, STOP)
        pc = self.machine.reg_read(UC_X86_REG_EIP)
        if not self.paused and pc != STOP:
            raise Blocked('Original did not return to the harness')
        result = self.machine.reg_read(UC_X86_REG_EAX)
        self.phase_results.append(dict(phase=phase, entry=hex(address), result=result,
                                       disposition='suspended' if self.paused else 'returned', pc=hex(pc)))
        return result

    def execute(self):
        # Game-owned static text rectangle initializer, reached through its
        # original tail thunk; native startup replaces only CRT dispatch.
        self.entries.add(0x45acb0)
        self.run(0x45aca0, 0, phase='menu-text-static-initialization')
        self.setup_version()
        application = self.allocate(0x134)
        if self.run(0x4254a0, application, phase='application-construction') != application:
            raise Blocked('Original application constructor did not return its receiver')
        self.run(0x428c40, application, (5, 1, 1, 0), phase='menu-construction', boundary=0x42abf0)
        if not self.paused or not self.word(application + 0x2c):
            raise Blocked('Mode-5 factory did not construct its menu')
        # Keep the real factory suspended while native startup provides scene
        # services. Use a distinct stack and preserve its exception-chain head.
        self.factory_context = self.machine.context_save()
        self.factory_fs = self.word(0)
        factory_cpu = self.cpu_state()
        factory_stack = bytes(self.machine.mem_read(STACK - 0x2000, 0xa000))
        self.put(0, 0xffffffff)
        scene = self.allocate(0x3c)
        self.run(0x4ce960, scene, phase='scene-construction', stack=STACK - 0x4000)
        result = self.run(0x4cea10, scene, (1, 640, 480, 8, 0),
                          phase='scene-initialization', stack=STACK - 0x4000)
        if not result:
            raise Blocked(f'Original scene initialization failed with scene error {self.word(scene + 0x38):#x}')
        self.check_scene(application, scene)
        if bytes(self.machine.mem_read(STACK - 0x2000, 0xa000)) != factory_stack:
            raise Blocked('Scene setup overwrote the suspended factory stack')
        self.machine.context_restore(self.factory_context)
        self.put(0, self.factory_fs)
        if self.cpu_state() != factory_cpu or self.word(0) != self.factory_fs:
            raise Blocked('Suspended factory CPU/exception state was not restored')
        self.scene_evidence['factory_preserved'] = dict(cpu=True, stack=True, exception_head=True,
            pc=hex(self.machine.reg_read(UC_X86_REG_EIP)),
            stack_sha256=hashlib.sha256(factory_stack).hexdigest())
        self.put(0, 0xffffffff)
        self.setup_resources(application, scene)
        if bytes(self.machine.mem_read(STACK - 0x2000, 0xa000)) != factory_stack:
            raise Blocked('Resource setup overwrote the suspended factory stack')
        self.machine.context_restore(self.factory_context)
        self.put(0, self.factory_fs)
        if self.cpu_state() != factory_cpu:
            raise Blocked('Resource setup did not preserve suspended factory CPU')
        self.factory_resume = dict(cpu_preserved=True, stack_preserved=True,
            exception_head_preserved=self.word(0) == self.factory_fs,
            pc=hex(self.machine.reg_read(UC_X86_REG_EIP)),
            stack_sha256=hashlib.sha256(factory_stack).hexdigest())
        self.phase = 'menu-initialization'
        self.boundary = None
        self.paused = False
        self.machine.emu_start(self.machine.reg_read(UC_X86_REG_EIP), STOP)
        result = self.machine.reg_read(UC_X86_REG_EAX)
        pc, sp = self.machine.reg_read(UC_X86_REG_EIP), self.machine.reg_read(UC_X86_REG_ESP)
        if pc != STOP or sp != STACK + 20 or self.word(0) != 0xffffffff:
            raise Blocked('Factory did not return with its original caller stack/exception state')
        self.phase_results.append(dict(phase=self.phase, entry='0x428c40', result=result,
            disposition='resumed-and-returned', pc=hex(pc)))
        self.factory_return = dict(status='pass' if result else 'failed', entry='0x428c40',
            result=result, pc=hex(pc), stack=hex(sp), exception_head=hex(self.word(0)))
        if not result:
            raise Blocked('Original mode-5 factory returned initialization failure')
        self.execute_frames(application)

    def setup_version(self):
        # Native replacement for startup's GetFileVersionInfo/VerQueryValue
        # transport at 0x49f991..0x49f9f9. Read the hash-verified PE resource,
        # not invented display text or a version copied from a test fixture.
        marker = 'FileVersion\0'.encode('utf-16le')
        values = []
        for section in self.program.sections:
            offset = section.data.find(marker)
            if offset < 6:
                continue
            length, count, kind = struct.unpack_from('<3H', section.data, offset - 6)
            start = (offset + len(marker) + 3) & ~3
            if kind != 1 or start + 2 * count > offset - 6 + length:
                raise Blocked('Malformed physical FileVersion resource')
            value = section.data[start:start + 2 * count].decode('utf-16le').rstrip('\0')
            if not re.fullmatch(r'\d+, \d+, \d+, \d+', value):
                raise Blocked('Unprovided physical FileVersion string')
            values.append((section.address + start, value))
        if len(values) != 1:
            raise Blocked('Missing or ambiguous physical FileVersion resource')
        address, value = values[0]
        for index, part in enumerate(value.split(', ')):
            self.put(0x53ec38 + index * 4, int(part))
        self.startup_evidence.append(dict(service='native FileVersion resource',
            resource=hex(address), value=value, original_consumer='0x49f9eb'))

    def advance_time(self, milliseconds):
        if milliseconds <= self.milliseconds:
            raise Blocked('Physical frame clock must advance')
        # Validate before mutating any of the physical clocks.
        if any(s['status'] == 4 for s in self.sequences.values()):
            raise Blocked('Active XMIDI playback needs an advancing physical sequence clock')
        elapsed = milliseconds - self.milliseconds
        for obj in self.com_objects.values():
            if obj['kind'] == 'IDirectSoundBuffer' and obj.get('playing'):
                # Advance integral PCM sample frames, retaining sub-frame time.
                alignment = struct.unpack('<HHIIHHH', bytes.fromhex(obj['format']))[4]
                total = obj.get('sample_remainder', 0) + elapsed * obj['frequency']
                frames, obj['sample_remainder'] = divmod(total, 1000)
                position = obj['position'] + frames * alignment
                if obj['looping']:
                    obj['position'] = position % obj['length']
                else:
                    obj['position'] = min(position, obj['length'])
                    obj['playing'] = position < obj['length']
        self.milliseconds = milliseconds

    def execute_frames(self, application):
        menu = self.word(application + 0x2c)
        update = self.word(self.word(menu) + 0x14)
        if update != 0x45b650:
            raise Blocked('Unexpected original menu update virtual target')
        for index in range(61):
            self.advance_time(self.milliseconds + 17 if self.startup_paper else
                              1000 + (index + 1) * 1000 // 60)
            phase = 'first-presentation' if index == 0 else f'idle-{index:02d}'
            before = len(self.presentations)
            dispatch = ((0x428b9d, update), (0x45b810, 0x4c8fc0),
                        (0x45b826, 0x4d63c0), (0x45b835, 0x4c91d0))
            previous_edges = [self.edges[(s, t, 'indirect_call')] for s, t in dispatch]
            # Original application timing and actual menu virtual dispatch at
            # 0x428b9d; game clocks and animation globals are not synthesized.
            result = self.run(0x428b60, application, phase=phase)
            if (result != 1 or len(self.presentations) != before + 1
                    or self.presentations[-1]['caller']['site'] != '0x4b98cb'
                    or not self.presentations[-1]['nonzero_pixels']
                    or self.machine.reg_read(UC_X86_REG_ESP) != STACK + 4
                    or self.word(0) != 0xffffffff or self.messages or self.pressed_keys or self.dcs
                    or any(self.edges[(s, t, 'indirect_call')] != n + 1
                           for (s, t), n in zip(dispatch, previous_edges))):
                raise Blocked('Original idle cycle did not return with exactly one presentation and idle input')
            self.frame_cycles.append(dict(index=index, phase=phase, milliseconds=self.milliseconds,
                delta=self.word(0x54132c), animation_delta=self.word(0x5430c4),
                update=hex(update), presentation=before, result=result,
                idle_input=dict(pressed_keys=sorted(self.pressed_keys), queued_messages=len(self.messages),
                                cursor=self.cursor),
                original_dispatch=[dict(site=hex(s), target=hex(t)) for s, t in dispatch]))

    def setup_resources(self, application, scene):
        with REZ_PATH.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != REZ_SHA256:
            raise Blocked('Original disc archive hash mismatch')
        self.resource_evidence = dict(archive=str(REZ_PATH.relative_to(ROOT)), sha256=digest,
                                      status='constructing')
        archive = self.allocate(0x48)
        self.run(0x4b7210, archive, phase='archive-construction', stack=STACK - 0x4000)
        path = self.cstring(b'CLAW.REZ')
        result = self.run(0x4b72e0, archive, (path, 1, 0),
                          phase='archive-open', stack=STACK - 0x4000)
        self.resource_evidence.update(archive_object=hex(archive), open_result=result,
                                     root=hex(self.word(archive + 0x24)))
        if not result or not self.word(archive + 0x24):
            raise Blocked('Original archive open failed; resource root is unavailable')
        self.resource_evidence['status'] = 'opened'
        # Native startup publishes actual objects and physical dimensions. No
        # directory nodes, readiness results, or game resources are fabricated.
        self.put(application + 0x30, scene)
        self.put(application + 0x34, archive)
        # Original IFC image callbacks obtain this same application through
        # the process-wide application slot supplied by native startup.
        self.put(0x5371fc, application)
        self.put(application + 0x7c, 640)
        self.put(application + 0x80, 480)
        self.setup_settings(application)
        self.setup_window(application)
        self.setup_input()
        self.setup_profile(application)
        self.setup_music(application)
        self.setup_volumes(application)
        if self.startup_paper:
            self.setup_paper_startup(application)
        # The menu uses five registrations from original startup 0x401000.
        # Run its actual game registrar/constructor, never insert map values or
        # fabricated actor objects. Other level callbacks are outside this run.
        registrar = self.word(scene + 0x14)
        target = self.word(self.word(registrar) + 0x24)
        if target != 0x4d6340:
            raise Blocked('Unexpected original logic registrar')
        for site, callback, name, flags in ((0x401d86, 0x4918b0, 0x522658, 2),
                                            (0x401e26, 0x461730, 0x5225e8, 2),
                                            (0x401fca, 0x498f40, 0x5224d8, 0),
                                            (0x402056, 0x45f840, 0x52246c, 0),
                                            (0x40206a, 0x45f500, 0x522460, 0)):
            result = self.run(target, registrar, (callback, name, flags),
                              phase='menu-logic-registration', stack=STACK - 0x4000)
            if not result:
                raise Blocked('Original menu logic registration failed')
            self.startup_evidence.append(dict(original_site=hex(site), constructor=hex(target),
                callback=hex(callback), name=self.bytestring(name).decode('ascii'), flags=flags,
                object=hex(result)))

    def setup_paper_startup(self, application):
        """Original startup objects, on the suspended factory's resource stack."""
        for size, constructor, initializer, arguments, offset, label in (
                (0x28, 0x4ebf80, 0x4ec010, (0, 0, 0), 0x44, 'fader'),
                (0x18, 0x4c61d0, 0x4c6260, (), 0x58, 'palette')):
            obj = self.allocate(size)
            self.run(constructor, obj, phase=f'paper-{label}-construction', stack=STACK-0x4000)
            if self.run(initializer, obj, arguments, phase=f'paper-{label}-initialization',
                        stack=STACK-0x4000) != 1:
                raise Blocked(f'Paper startup {label} initialization failed')
            self.put(application + offset, obj)
            self.startup_evidence.append(dict(object=hex(obj), binding=f'application+{offset:#x}',
                constructor=hex(constructor), initializer=hex(initializer)))

    def setup_settings(self, application):
        # Native replacement for the stored-settings read in original startup
        # (0x425827..0x425ad9). A fresh install has nothing stored, so each
        # option takes its default. Only the values that differ from the
        # application constructor's are provided; the others (Num Movies,
        # the option globals, Music, Sound, Voice, Ambient, Interlaced,
        # High Detail, Front Layer, checkpoint and Nani factors) default to
        # the value already present.
        for offset, value, setting, site in ((0x68, 10, 'Status Layout', '0x425827'),
                                             (0x70, 1, 'Num Runs', '0x425836..0x425adf'),
                                             (0x12c, 80, 'Sound Volume', '0x425abe..0x425ad9')):
            self.put(application + offset, value)
            self.startup_evidence.append(dict(binding=f'application+{offset:#x}', setting=setting,
                value=value, original_default=site, profile='fresh install, no stored override'))

    def setup_window(self, application):
        host, window = self.allocate(0x254), self.allocate(0x10)
        self.run(0x4b8990, host, phase='host-construction', stack=STACK - 0x4000)
        self.run(0x4b8410, window, phase='window-construction', stack=STACK - 0x4000)
        # Native startup owns the physical window (also used by DirectX), and
        # connects the original wrappers without executing WinMain/CreateWindow.
        self.put(window + 4, 1)
        self.put(window + 8, host)
        self.put(host + 4, window)
        self.put(host + 8, application)
        result = self.run(0x4b8280, application, (window, 0),
                          phase='application-window-attachment', stack=STACK - 0x4000)
        if not result or self.word(application + 4) != window or self.word(application + 8) != host:
            raise Blocked('Original application/window attachment failed')
        self.startup_evidence.append(dict(host=hex(host), window=hex(window), physical_window=1,
            constructors=['0x4b8990', '0x4b8410'], attachment='0x4b8280'))

    def setup_input(self):
        input_state, controller = self.allocate(0x248), self.allocate(0x90)
        # These two constructors are inlined in original application startup.
        # Execute just their bounded instruction spans, including MFC storage
        # construction and the original input reset, on the separate setup stack.
        for entry, end, obj in ((0x42637d, 0x4263ae, input_state),
                                 (0x4264cc, 0x4264dc, controller)):
            self.machine.reg_write(UC_X86_REG_EDI, obj)
            self.machine.reg_write(UC_X86_REG_ESI, 0)
            self.run(entry, obj, phase='input-inline-construction', boundary=end, stack=STACK - 0x4000)
            if not self.paused:
                raise Blocked('Original inline input constructor did not reach its continuation')
        self.put(0x537200, input_state)
        self.put(0x537204, controller)
        result = self.run(0x430590, controller, (input_state, 0),
                          phase='input-controller-initialization', stack=STACK - 0x4000)
        if not result or self.word(controller) != input_state:
            raise Blocked('Original input controller initialization failed')
        self.startup_evidence.append(dict(input=hex(input_state), controller=hex(controller),
            constructors=['0x42637d..0x4263ae', '0x4264cc..0x4264dc'], initializer='0x430590',
            settings_resource=0, profile='original default bindings; no joystick or pending input'))

    def setup_profile(self, application):
        # Fresh-install native startup: construct the original profile manager,
        # then execute the same default creation/lookup/selection as startup.
        # No persistent user file or game profile fields are fabricated.
        manager = self.allocate(0x58)
        self.machine.reg_write(UC_X86_REG_EBX, manager)
        self.machine.reg_write(UC_X86_REG_ESI, 0)
        self.run(0x426565, manager, phase='profile-manager-inline-construction',
                 boundary=0x426594, stack=STACK - 0x4000)
        if not self.paused:
            raise Blocked('Original profile manager constructor missed continuation')
        self.put(application + 0x60, manager)
        profile = self.run(0x49bdb0, manager, (0x5255e8, 0x534938, 0x534938, 0),
                           phase='default-profile-creation', stack=STACK - 0x4000)
        selected = self.run(0x49bee0, manager, (0x5255e8,),
                            phase='default-profile-lookup', stack=STACK - 0x4000)
        if not profile or selected != profile or not self.bytestring(profile + 0x14):
            raise Blocked('Original default profile creation/lookup failed')
        self.run(0x42bf90, application, (selected,), phase='default-profile-selection', stack=STACK - 0x4000)
        if self.word(application + 0x64) != profile:
            raise Blocked('Original profile selection did not publish its result')
        self.startup_evidence.append(dict(manager=hex(manager), profile=hex(profile),
            constructor='0x426565..0x426594', creation='0x49bdb0', lookup='0x49bee0',
            selection='0x42bf90', original_creation_site='0x49b927',
            original_selection_site='0x4266db', name=self.bytestring(profile + 0x14).decode('ascii'),
            data_sha256=hashlib.sha256(bytes(self.machine.mem_read(profile, 0x2648))).hexdigest(),
            physical_profile='fresh install; original default player, no persistent profile import'))

    def setup_music(self, application):
        music = self.allocate(0x2c)
        self.machine.reg_write(UC_X86_REG_EDI, music)
        self.machine.reg_write(UC_X86_REG_ESI, 0)
        self.run(0x4261f7, music, phase='music-inline-construction',
                 boundary=0x42620c, stack=STACK - 0x4000)
        if not self.paused:
            raise Blocked('Original inline music constructor missed its continuation')
        # Window/module handles belong to the physical native startup layer.
        result = self.run(0x4b52a0, music, (1, 1, 0),
                          phase='music-device-initialization', stack=STACK - 0x4000)
        if not result:
            raise Blocked('Original music device initialization failed')
        self.put(application + 0x50, music)
        self.startup_evidence.append(dict(music=hex(music), constructor='0x4261f7..0x42620c',
            initializer='0x4b52a0', enabled=self.word(music + 0x28),
            driver=hex(self.word(0x54131c))))

    def setup_volumes(self, application):
        # Original startup applies the stored volumes right after creating
        # their owners. Fresh install: Music Volume 50 through 0x4b55e0 at
        # 0x42625c (unless 0x537234 disabled music, when startup clears the
        # manager's enabled field instead), then Sound Volume 80 through
        # 0x42cdc0 at 0x426340, which publishes application+0x12c and the
        # animation-sound volume 0x532c10.
        music = self.word(application + 0x50)
        if self.word(0x537234):
            self.put(music + 0x28, 0)
            music_result = None
        else:
            music_result = self.run(0x4b55e0, music, (50,), phase='music-volume', stack=STACK - 0x4000)
        self.run(0x42cdc0, application, (80,), phase='sound-volume', stack=STACK - 0x4000)
        if self.word(application + 0x12c) != 80 or self.word(0x532c10) != 80:
            raise Blocked('Original sound-volume publication did not reach application+0x12c and 0x532c10')
        self.startup_evidence.append(dict(setting='Music Volume', value=50, original_site='0x42625c',
            callee='0x4b55e0', result=music_result, master_volume=self.midi_master_volume,
            profile='fresh install, no stored override'))
        self.startup_evidence.append(dict(setting='Sound Volume', value=80, original_site='0x426340',
            callee='0x42cdc0', animation_sound_volume=self.word(0x532c10),
            sound_events=hex(self.word(application + 0x5c)), profile='fresh install, no stored override'))

    def check_scene(self, application, scene):
        table = [self.word(0x541178 + i * 4) for i in range(101)]
        expected = [(-10000 if i == 0 else 0 if i == 100 else
                     math.trunc(-1000 * math.log2(100 / i))) & 0xffffffff for i in range(101)]
        if table != expected or len(self.math_events) != 396 or self.x87_state() != dict(control=0x27f, status=0, tags=0xffff):
            raise Blocked('Audio table or terminal x87 state differs from the mathematical profile')
        display = self.word(scene + 0x1c)
        if self.word(scene + 0x38) or self.word(display + 0x3f8) != 1:
            raise Blocked('Scene error or missing original-enumerated display mode')
        mode = self.word(self.word(display + 0x3f4))
        if [self.word(mode + offset) for offset in (8, 12, 84)] != [480, 640, 8]:
            raise Blocked('Original display callback did not retain the advertised mode')
        sound = self.word(scene + 0x20)
        device = self.com_objects.get(self.word(sound + 0x14), {})
        if self.word(sound + 0x78) != 1 or device.get('cooperative_flags') != 1:
            raise Blocked('Original sound owner did not initialize its physical device')
        surfaces = [dict(object=hex(a), **s) for a, s in self.com_objects.items()
                    if s['kind'] == 'IDirectDrawSurface']
        if len(surfaces) != 3 or sorted(s['caps'] for s in surfaces) != [4, 0x40, 0x218]:
            raise Blocked('Expected physical primary, back and spare surfaces')
        for surface in surfaces:
            pixels = bytes(self.machine.mem_read(surface['pixels'], surface['pitch'] * surface['height']))
            if (surface['width'], surface['height'], len(pixels)) != (640, 480, 307200):
                raise Blocked('Invalid surface storage')
            surface['pixels_sha256'] = hashlib.sha256(pixels).hexdigest()
        self.scene_evidence = dict(status='pass', application=hex(application),
            menu=hex(self.word(application + 0x2c)), scene=hex(scene), scene_error=0,
            audio_table_entries=len(table), audio_table=table, surfaces=surfaces,
            display_modes=1, original_enumeration_callback='0x4bcda0', sound_device_initialized=True)

    def report(self):
        functions = [dict(address=hex(a), count=count, phases=sorted(self.phases[a]),
                          entry_kind='inline_startup_span' if a in INLINE_SPANS else 'function',
                          inline_end=hex(INLINE_SPANS[a]) if a in INLINE_SPANS else None,
                          snapshot_owner=self.plan['nodes'].get(hex(a)))
                     for a, count in sorted(self.functions.items())]
        imports = [dict(address=hex(a), name=self.platform_names[a], count=count,
                        iat=hex(self.imports[a][0]) if a in self.imports else None)
                   for a, count in sorted(self.platform.items())]
        physical_counts = Counter(e['service'] for e in self.physical_events)
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        receiver = self.machine.reg_read(UC_X86_REG_ECX)
        pc = self.machine.reg_read(UC_X86_REG_EIP)
        physical_stop = None
        if pc in self.com_methods and 0x01ff0000 <= sp < 0x0200ffe0:
            obj = self.word(sp + 4)
            physical_stop = dict(service='::'.join(self.com_methods[pc]), object=hex(obj),
                state=self.com_objects.get(obj),
                arguments=[hex(self.word(sp + 4 * i)) for i in range(1, 7)])
        stopped_map = None
        if receiver in self.maps:
            stopped_map = dict(receiver=hex(receiver), count=len(self.maps[receiver]),
                entries=[dict(key=k.decode('ascii'), value_cell=hex(v), value=hex(self.word(v)))
                         for k, v in self.maps[receiver].items()])
        return dict(schema=1, status='blocked',
                    tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    executable_sha256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',
                    plan_sha256=hashlib.sha256(self.plan_path.read_bytes()).hexdigest(),
                    profile='native startup; original archive and mode-5 initializer; 640x480x8 scene',
                    scope='Partial original execution only; not a completed menu or exhaustive dynamic closure',
                    game_ranges=[[hex(a), hex(b)] for a, b in GAME_RANGES],
                    first_presented_frame=bool(self.presentations), idle_frames=max(0, len(self.frame_cycles) - 1), requested_idle_frames=60,
                    presentations=self.presentations, frame_cycles=self.frame_cycles,
                    counts=dict(game_functions=sum(a not in INLINE_SPANS for a in self.functions),
                                observed_entry_sites=len(functions),
                                inline_startup_spans=sum(a in INLINE_SPANS for a in self.functions),
                                game_entries=sum(c for a, c in self.functions.items() if a not in INLINE_SPANS),
                                platform_functions=len(imports), platform_calls=sum(self.platform.values()),
                                platform_imports=sum(e['iat'] is not None for e in imports),
                                instructions=self.instructions),
                    game_functions=functions, platform_calls=imports,
                    platform_imports=[e for e in imports if e['iat'] is not None],
                    edges=[dict(site=hex(s), target=hex(t), kind=k, count=c,
                                target_is_observed_entry=t in self.functions,
                                entry_transfer='tail_or_entry_branch' if k == 'branch' and t in self.functions else k)
                           for (s, t, k), c in sorted(self.edges.items())],
                    branch_targets=[dict(address=hex(a), count=c,
                        classification='observed_entry' if a in self.functions else 'unresolved_basic_block_or_tail')
                        for a, c in sorted(self.branch_targets.items())],
                    phases=self.phase_results, stop=self.stop, math_events=self.math_events,
                    physical_events=self.physical_events,
                    scene_construction=self.scene_evidence,
                    resources=self.resource_evidence,
                    factory_resume=self.factory_resume,
                    initializer_return=self.initializer_return,
                    factory_return=self.factory_return,
                    startup_context=self.startup_evidence,
                    physical_font=self.font_evidence, live_text_dcs=len(self.dcs),
                    resource_uploads=dict(pcm_buffers=physical_counts['IDirectSoundBuffer::Unlock'],
                        image_surfaces=physical_counts['IDirectDrawSurface::Unlock'],
                        original_archive_reads=physical_counts['CRT fread'],
                        original_vector_constructor_callbacks=sum(e['completed'] for e in self.physical_events
                            if e['service'] == 'CRT vector constructor iterator')),
                    stopped_context=dict(last_transfer=self.last_transfer,
                        physical_service=physical_stop,
                        receiver=hex(receiver), stack=hex(sp),
                        stack_words=[hex(self.word(sp + i * 4)) for i in range(9)]
                            if 0x01ff0000 <= sp < 0x0200ffdc else [],
                        mfc_map=stopped_map,
                        registers={name:hex(self.machine.reg_read(reg)) for name, reg in
                            (('eax',UC_X86_REG_EAX), ('ebx',UC_X86_REG_EBX), ('edx',UC_X86_REG_EDX),
                             ('esi',UC_X86_REG_ESI), ('edi',UC_X86_REG_EDI), ('ebp',UC_X86_REG_EBP))},
                        fpcw=self.machine.reg_read(UC_X86_REG_FPCW),
                        fpsw=self.machine.reg_read(UC_X86_REG_FPSW),
                        fptag=self.machine.reg_read(UC_X86_REG_FPTAG),
                        fp_registers=[self.machine.reg_read(UC_X86_REG_FP0 + i) for i in range(8)]),
                    recent_pcs=[hex(a) for a in self.recent],
                    limitations=['Ownership is the supplied static snapshot, not a new gate result.',
                                 'Unseen indirect targets remain unknown until the complete trace runs.',
                                 'Unindexed branch destinations are recorded as edges, not asserted function entries.',
                                 'Physical display profile supports in-bounds unscaled indexed blits and one attached flip buffer.',
                                 'PCM time advances; active XMIDI playback fails closed pending its physical sequence clock.',
                                 'No game entry is replaced by a fixture; unknown platform entries stop execution.'])


def run_trace(instruction_limit=80_000_000, deny_platform=None, missing_resource=False, startup_paper=False):
    trace = MenuTrace(instruction_limit, deny_platform, missing_resource, startup_paper=startup_paper)
    try:
        trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)),
                              reason=str(error))
        trace.stop['phase'] = trace.phase
        trace.stop['last_transfer'] = trace.last_transfer
    finally:
        for stream in trace.files.values():
            stream.close()
    return trace


def check_x87_transport():
    """Exercise physical/logical register mapping at every TOP, with a live tail."""
    trace = MenuTrace()
    machine = trace.machine
    cases = 0
    for top in range(8):
        for address, operands, expected in ((0x4f1b30, [2., 10.], 1024.),
                                             (0x4f1a60, [2.], math.log(2.)),
                                             (0x4f2400, [-1.], math.pi),
                                             (0x4f2400, [0.25], math.acos(0.25)),
                                             (0x4f2400, [1.], 0.),
                                             (0x4a30e0, [-3.75], -3)):
            machine.reg_write(UC_X86_REG_FPSW, top << 11)
            machine.reg_write(UC_X86_REG_FPTAG, 0xffff)
            machine.reg_write(UC_X86_REG_FPCW, 0x27f)
            # The live tail is not an operand; it must survive every fixture.
            trace.x87_result(0, 7.25)
            for operand in operands:
                trace.x87_result(0, operand)
            before = trace.x87_state()
            machine.reg_write(UC_X86_REG_ESP, STACK)
            trace.put(STACK, STOP)
            trace.math_fixture(address)
            after = trace.x87_state()
            depth = 1 if address == 0x4a30e0 else 2
            expected_top = (top - depth) & 7
            expected_tags = 0xffff
            for index in range(depth):
                expected_tags &= ~(3 << (((expected_top + index) & 7) * 2))
            if address != 0x4a30e0 and expected == 0:
                expected_tags |= 1 << (expected_top * 2)
            actual = machine.reg_read(UC_X86_REG_EAX) if address == 0x4a30e0 else trace.x87_value(0)
            if (actual != (expected & 0xffffffff if isinstance(expected, int) else expected)
                    or trace.x87_value(depth - 1) != 7.25
                    or after != dict(control=0x27f, status=expected_top << 11, tags=expected_tags)
                    or machine.reg_read(UC_X86_REG_ESP) != STACK + 4
                    or machine.reg_read(UC_X86_REG_EIP) != STOP
                    or address == 0x4a30e0 and machine.reg_read(UC_X86_REG_EDX) != 0xffffffff):
                raise Blocked(f'x87 transport control failed at TOP {top}: {before} -> {after}')
            cases += 1
    for value in (-1.01, 1.01):
        machine.reg_write(UC_X86_REG_FPSW, 0)
        machine.reg_write(UC_X86_REG_FPTAG, 0xffff)
        trace.x87_result(0, value)
        try:
            trace.math_fixture(0x4f2400)
        except Blocked:
            pass
        else:
            raise Blocked('Out-of-domain inverse cosine was accepted')
    trace.deny_platform = 0x4f2400
    before = trace.x87_state(), trace.x87_value(0), len(trace.math_events)
    try:
        trace.fixture(0x4f2400)
    except Blocked:
        pass
    else:
        raise Blocked('Withheld inverse cosine service was accepted')
    if before != (trace.x87_state(), trace.x87_value(0), len(trace.math_events)):
        raise Blocked('Withheld inverse cosine service changed x87 state')
    trace.deny_platform = None
    machine.reg_write(UC_X86_REG_FPCW, 0x37f)
    try:
        trace.math_fixture(0x4f1a60)
    except Blocked:
        return dict(status='pass', stack_cases=cases, unsupported_control_rejected=True,
                    inverse_cosine_domain_and_withholding=True)
    raise Blocked('Unsupported x87 precision control was accepted')


def check_scene_controls(trace):
    if not trace.scene_evidence or not trace.scene_evidence.get('factory_preserved'):
        return dict(status='blocked', reason='Scene construction has not completed')
    controls = []
    for address, site in ((0x4f1b30, 0x4b3bc2), (0x4f4486, 0x4bc3b9), (0x4f4480, 0x4b47ed)):
        negative = run_trace(trace.instruction_limit, address)
        exact = (negative.stop['address'] == hex(address)
                 and negative.stop['reason'].startswith('Negative control:')
                 and negative.last_transfer == dict(site=hex(site), target=hex(address), kind='direct_call')
                 and negative.scene_evidence is None)
        if address == 0x4f1b30:
            exact = exact and not negative.math_events and negative.x87_value(0) == 10 and negative.x87_value(1) == 100
        else:
            kind = 'IDirectDraw' if address == 0x4f4486 else 'IDirectSound'
            exact = exact and not any(obj['kind'] == kind for obj in negative.com_objects.values())
        controls.append(dict(status='pass' if exact else 'fail', withheld=hex(address),
                             stop=negative.stop, last_transfer=negative.last_transfer,
                             no_service_effect=True if exact else False))
    transport = check_x87_transport()
    return dict(status='pass' if all(c['status'] == 'pass' for c in controls) else 'fail',
                negative_controls=controls, x87_transport=transport)


def check_resource_controls(trace):
    if not trace.resource_evidence or trace.resource_evidence.get('status') != 'opened':
        return dict(status='blocked', reason='Original archive open has not completed')
    missing = run_trace(trace.instruction_limit, missing_resource=True)
    missing_ok = (missing.resource_evidence.get('open_result') == 0
                  and missing.resource_evidence.get('root') == '0x0'
                  and missing.stop['reason'] == 'Original archive open failed; resource root is unavailable'
                  and not any(e['service'] == 'CRT fread' for e in missing.physical_events)
                  and 'menu-initialization' not in missing.phases.get(0x45ace0, set()))
    denied = run_trace(trace.instruction_limit, deny_platform=0x4a7260)
    denied_ok = (denied.stop['address'] == '0x4a7260'
                 and denied.last_transfer == dict(site='0x4b7afe', target='0x4a7260', kind='direct_call')
                 and denied.stop['reason'].startswith('Negative control:')
                 and not any(e['service'] == 'CRT fread' for e in denied.physical_events))
    unknown = MenuTrace()
    unknown.machine.reg_write(UC_X86_REG_ESP, STACK)
    unknown.put(STACK, STOP)
    try:
        unknown.fixture(0x4f0000)
        unknown_ok = False
    except Blocked:
        unknown_ok = (unknown.machine.reg_read(UC_X86_REG_ESP) == STACK
                      and not unknown.physical_events)
    return dict(status='pass' if missing_ok and denied_ok and unknown_ok else 'fail',
        missing_archive=dict(status='pass' if missing_ok else 'fail', stop=missing.stop,
                             original_open_result=missing.resource_evidence.get('open_result')),
        withheld_read=dict(status='pass' if denied_ok else 'fail', stop=denied.stop,
                           caller=denied.last_transfer),
        unknown_service=dict(status='pass' if unknown_ok else 'fail', address='0x4f0000'))


def check_tail_transport():
    """Independent storage/lifetime controls for the added physical services."""
    trace = MenuTrace()
    def call(address, receiver, *arguments, com=False):
        for index, value in enumerate((STOP, *arguments)):
            trace.put(STACK + index * 4, value)
        trace.machine.reg_write(UC_X86_REG_ESP, STACK)
        trace.machine.reg_write(UC_X86_REG_EIP, address)
        trace.machine.reg_write(UC_X86_REG_ECX, receiver)
        (trace.com_fixture if com else trace.fixture)(address)
        if trace.machine.reg_read(UC_X86_REG_ESP) != STACK + 4 * (1 + len(arguments)):
            raise Blocked('Tail transport did not preserve its callee-pop ABI')
        if trace.machine.reg_read(UC_X86_REG_EIP) != STOP:
            raise Blocked('Tail transport changed its caller continuation')
        return trace.machine.reg_read(UC_X86_REG_EAX)
    def rejects(action):
        try:
            action()
        except Blocked:
            return True
        raise Blocked('Unsupported tail transport state did not fail closed')

    mapping, value = trace.allocate(28), trace.allocate(8)
    trace.machine.mem_write(value, b'payload!')
    call(0x4f6118, mapping, 10)
    keys = [trace.cstring(k) for k in (b'A', b'B', b'C')]
    for key in keys:
        trace.put(call(0x4f62a8, mapping, key), value)
    if call(0x4f5db6, mapping, keys[1]) != 1 or call(0x4f5db6, mapping, keys[1]) != 0:
        raise Blocked('Map removal did not distinguish present/missing keys')
    if (trace.word(mapping + 12) != 2 or value not in trace.allocations
            or bytes(trace.machine.mem_read(value, 8)) != b'payload!'):
        raise Blocked('Map removal changed ownership of the stored game value')
    withheld = trace.deny_platform = 0x4f5db6
    before = dict(trace.maps[mapping])
    rejects(lambda: call(withheld, mapping, keys[0]))
    if trace.maps[mapping] != before:
        raise Blocked('Withheld map service mutated storage')
    trace.deny_platform = None

    collection = trace.allocate(28)
    call(0x4f5620, collection, 10)
    first = call(0x4f51c5, collection, 20)
    last = call(0x4f51c5, collection, 40)
    call(0x4f572a, collection, first, 10)
    middle = call(0x4f572a, collection, last, 30)
    call(0x4f5212, collection, first)
    ordered, node = [], trace.word(collection + 4)
    while node:
        ordered.append(trace.word(node + 8))
        node = trace.word(node)
    if ordered != [10, 30, 40] or trace.word(last + 4) != middle or trace.word(collection + 12) != 3:
        raise Blocked('List insertion/removal did not preserve ordered links')
    rejects(lambda: call(0x4f5212, collection, first))
    for constructor, destructor in ((0x4f58ab, 0x4f58de), (0x4f54ea, 0x4f551d)):
        array = trace.allocate(20)
        call(constructor, array)
        call(0x4f5915, array, 2, 0xffffffff)
        backing = trace.word(array + 4)
        trace.put(backing, value)
        call(destructor, array)
        if backing in trace.allocations or value not in trace.allocations:
            raise Blocked('Array destructor confused storage and game-object lifetime')

    file, archive, string = trace.allocate(40), trace.allocate(68), trace.allocate(4)
    data = trace.allocate(4)
    trace.machine.mem_write(data, b'\x03abc')
    call(0x4ff5f9, file, 1024)
    call(0x4ff645, file, data, 4, 0)
    buffer = trace.allocate(8)
    trace.machine.mem_write(buffer, b'........')
    if (call(0x4ff79f, file, buffer, 2) != 2
            or call(0x4ff79f, file, buffer + 2, 8) != 2
            or call(0x4ff79f, file, buffer + 4, 1) != 0
            or bytes(trace.machine.mem_read(buffer, 8)) != b'\x03abc....'
            or trace.word(file + 20) != 4):
        raise Blocked('Memory-file read changed bytes, short read or EOF cursor')
    trace.put(file + 20, 0)
    trace.deny_platform = 0x4ff79f
    rejects(lambda: call(0x4ff79f, file, buffer, 1))
    trace.deny_platform = None
    if trace.word(file + 20) or bytes(trace.machine.mem_read(buffer, 8)) != b'\x03abc....':
        raise Blocked('Withheld memory-file read changed destination or cursor')
    rejects(lambda: call(0x4ff79f, file, buffer, 0x800001))
    trace.put(file + 20, 5)
    rejects(lambda: call(0x4ff79f, file, buffer, 1))
    trace.put(file + 20, 0)
    call(0x4fda33, archive, file, 1, 4096, 0)
    call(0x4f6439, string)
    call(0x4fd877, 0, archive, string)
    if trace.bytestring(trace.word(string)) != b'abc' or trace.word(archive + 36) != data + 4:
        raise Blocked('Archive transport changed serialized string bytes or cursor')
    rejects(lambda: trace.archive_read(archive, 1))
    rejects(lambda: call(0x4ff670, file))
    call(0x4fdb0f, archive)
    if call(0x4ff670, file) != data or data not in trace.allocations:
        raise Blocked('Memory-file detach lost caller-owned resource storage')
    call(0x4ff682, file)
    rejects(lambda: call(0x4ff79f, file, buffer, 1))

    def com(obj, slot, *arguments):
        return call(trace.word(trace.word(obj) + slot), 0, obj, *arguments, com=True)
    display = trace.com_object('IDirectDraw')
    entries, output = trace.allocate(1024), trace.allocate(4)
    descriptor = trace.allocate(108)
    trace.machine.mem_write(descriptor, bytes(108))
    for offset, value in ((0, 108), (4, 7), (8, 480), (12, 640), (104, 0x840)):
        trace.put(descriptor + offset, value)
    com(display, 24, descriptor, output, 0)
    capture = trace.com_objects[trace.word(output)]
    if (capture['width'], capture['height'], capture['pitch'], capture['caps']) != (640, 480, 640, 0x840):
        raise Blocked('System-memory paper capture lost its physical surface contract')
    trace.put(descriptor + 104, 0x800)
    rejects(lambda: com(display, 24, descriptor, output, 0))
    palette_bytes = bytes(range(256)) * 4
    trace.machine.mem_write(entries, palette_bytes)
    com(display, 20, 0x44, entries, output, 0)
    palette = trace.word(output)
    source, destination = trace.surface(3, 1, 0x40), trace.surface(3, 1, 0x40)
    trace.machine.mem_write(trace.com_objects[source]['pixels'], b'\x01\x02\x03')
    trace.machine.mem_write(trace.com_objects[destination]['pixels'], b'\x09\x09\x09')
    key = trace.allocate(8)
    trace.put(key, 2)
    trace.put(key + 4, 2)
    com(source, 116, 8, key)
    com(destination, 124, palette)
    com(destination, 28, 0, 0, source, 0, 0x11)
    if (bytes(trace.machine.mem_read(trace.com_objects[destination]['pixels'], 3)) != b'\x01\x09\x03'
            or trace.com_objects[palette]['entries'] != palette_bytes.hex()
            or trace.com_objects[palette]['references'] != 2):
        raise Blocked('Palette attachment or keyed pixel transfer changed physical data')
    rejects(lambda: com(destination, 28, 1, 0, source, 0, 0x10))

    sound = trace.com_object('IDirectSound')
    samples = trace.allocate(8)
    trace.machine.mem_write(samples, b'12345678')
    buffer = trace.com_object('IDirectSoundBuffer', data=samples, length=8, format='PCM control',
        volume=-400, pan=20, frequency=11025, position=0, write_cursor=0, playing=False, locked=None)
    com(sound, 20, buffer, output)
    duplicate = trace.word(output)
    com(duplicate, 60, (-800) & 0xffffffff)
    trace.machine.mem_write(trace.com_objects[duplicate]['data'], b'87654321')
    if (trace.com_objects[buffer]['volume'] != -400 or trace.com_objects[duplicate]['volume'] != -800
            or bytes(trace.machine.mem_read(trace.com_objects[buffer]['data'], 8)) != b'87654321'):
        raise Blocked('Sound duplication lost independent controls or shared sample storage')

    def iff_chunk(tag, payload):
        return tag + struct.pack('>I', len(payload)) + payload + (b'\0' if len(payload) & 1 else b'')
    synthetic = iff_chunk(b'FORM', b'XDIR' + iff_chunk(b'INFO', b'\1\0')) + iff_chunk(
        b'CAT ', b'XMID' + iff_chunk(b'FORM', b'XMID' + iff_chunk(b'EVNT',
            b'\x90\x3c\x40\x08\x04\xff\x2f\x00')))
    if parse_xmidi(synthetic) != dict(events=2, duration_ticks=8):
        raise Blocked('XMIDI event/duration transport differs from synthetic note timing')
    rejects(lambda: parse_xmidi(synthetic[:-1]))
    rejects(lambda: parse_xmidi(synthetic.replace(b'\xff\x2f\x00', b'\xff\x01\x00')))

    # A null game object must fault even though FS:[0] has mapped backing.
    rejects(lambda: trace.run(0x4b8910, 0, (0x100, 1), phase='null-context-control'))
    if not trace.stop or trace.stop['kind'] != 'null_context_access':
        raise Blocked('Null game receiver reached a physical service')
    return dict(status='pass', map_value_lifetime=True, withheld_map_has_no_effect=True,
        list_order_and_invalid_position=True, array_storage_lifetime=True,
        archive_bytes_eof_and_detach=True, memory_file_read_cursor_eof_and_withholding=True,
        paper_system_memory_surface=True, palette_and_keyed_pixels=True,
        duplicate_sound_storage_and_controls=True, xmidi_events_and_malformed_data=True,
        null_context_rejected=True)


def check_frame_transport():
    """Physical data controls, independent of whether the menu reaches Flip."""
    trace = MenuTrace()
    def com(obj, slot, *arguments):
        address = trace.word(trace.word(obj) + slot)
        for i, value in enumerate((STOP, obj, *arguments)):
            trace.put(STACK + i * 4, value)
        trace.machine.reg_write(UC_X86_REG_ESP, STACK)
        trace.machine.reg_write(UC_X86_REG_EIP, address)
        trace.com_fixture(address)
        if (trace.machine.reg_read(UC_X86_REG_ESP) != STACK + 4 * (2 + len(arguments))
                or trace.machine.reg_read(UC_X86_REG_EIP) != STOP):
            raise Blocked('Frame transport changed its physical ABI')
    def rejects(action):
        try:
            action()
        except Blocked:
            return
        raise Blocked('Unsupported frame transport did not fail closed')
    def pixels(obj):
        surface = trace.com_objects[obj]
        return bytes(trace.machine.mem_read(surface['pixels'], surface['pitch'] * surface['height']))

    source = trace.surface(3, 2, 0x40)
    front, back = trace.surface(3, 2, 0x218), trace.surface(3, 2, 4)
    trace.com_objects[front]['back'] = back
    trace.com_objects[source]['color_key'] = (2, 2)
    trace.machine.mem_write(trace.com_objects[source]['pixels'], bytes([1, 2, 3, 4, 2, 6]))
    trace.machine.mem_write(trace.com_objects[front]['pixels'], bytes([7]) * 6)
    trace.machine.mem_write(trace.com_objects[back]['pixels'], bytes([9]) * 6)
    palette_bytes = bytes(range(256)) * 4
    palette = trace.com_object('IDirectDrawPalette', entries=palette_bytes.hex())
    com(front, 124, palette)
    com(back, 20, 0, source, 0, 0x1008000, 0)
    expected = bytes([1, 9, 3, 4, 9, 6])
    if pixels(back) != expected or pixels(front) != bytes([7]) * 6:
        raise Blocked('Keyed Blt changed transparent pixels or the front buffer')
    addresses = [trace.com_objects[obj]['pixels'] for obj in (front, back)]
    trace.deny_platform = trace.word(trace.word(front) + 44)
    event_count = len(trace.physical_events)
    rejects(lambda: com(front, 44, 0, 1))
    if (trace.presentations or len(trace.physical_events) != event_count
            or addresses != [trace.com_objects[obj]['pixels'] for obj in (front, back)]):
        raise Blocked('Withheld Flip mutated display state')
    trace.deny_platform = None
    com(front, 44, 0, 1)
    if (pixels(front) != expected or pixels(back) != bytes([7]) * 6
            or addresses[::-1] != [trace.com_objects[obj]['pixels'] for obj in (front, back)]
            or trace.presentations[-1]['pixels_sha256'] != hashlib.sha256(expected).hexdigest()
            or trace.presentations[-1]['palette_sha256'] != hashlib.sha256(palette_bytes).hexdigest()):
        raise Blocked('Flip did not swap storage and record the presented pixels/palette')
    rejects(lambda: com(front, 44, source, 1))
    trace.com_objects[back]['locked'] = True
    rejects(lambda: com(front, 44, 0, 1))
    trace.com_objects[back]['locked'] = False
    rect = trace.allocate(16)
    trace.machine.mem_write(rect, struct.pack('<4i', 0, 0, 4, 2))
    rejects(lambda: com(back, 20, rect, source, 0, 0x1008000, 0))
    trace.machine.mem_write(rect, struct.pack('<4i', 0, 0, 2, 2))
    rejects(lambda: com(back, 20, rect, source, 0, 0x1008000, 0))
    prior = pixels(front), pixels(back), len(trace.presentations)
    rejects(lambda: com(front, 252, rect))  # Unknown slot must not fake a frame.
    if prior != (pixels(front), pixels(back), len(trace.presentations)):
        raise Blocked('Unknown display service changed presentation state')

    wave = struct.pack('<HHIIHHH', 1, 1, 11025, 22050, 2, 16, 0).hex()
    sound = trace.com_object('IDirectSoundBuffer', format=wave, length=882, frequency=11025,
        position=0, playing=True, looping=False, sample_remainder=0)
    looping = trace.com_object('IDirectSoundBuffer', format=wave, length=882, frequency=11025,
        position=0, playing=True, looping=True, sample_remainder=0)
    trace.advance_time(1016)
    if trace.com_objects[sound]['position'] != 352 or trace.com_objects[sound]['sample_remainder'] != 400:
        raise Blocked('PCM clock lost fractional sample time')
    trace.advance_time(1033)
    if trace.com_objects[sound]['position'] != 726 or trace.com_objects[sound]['sample_remainder'] != 825:
        raise Blocked('PCM clock accumulated the wrong sample time')
    trace.advance_time(1040)
    if (trace.com_objects[sound]['position'] != 882 or trace.com_objects[sound]['playing']
            or trace.com_objects[looping]['position'] != 0 or not trace.com_objects[looping]['playing']):
        raise Blocked('PCM clock did not stop or loop at the physical sample boundary')
    trace.sequences[1] = dict(status=4)
    rejects(lambda: trace.advance_time(1041))
    return dict(status='pass', keyed_blt_pixels=True, flip_storage_and_palette=True,
        withheld_flip_has_no_effect=True, unknown_display_service_has_no_presentation=True,
        invalid_rectangles_stretch_and_flip_state_rejected=True,
        pcm_fractional_sample_clock_stop_and_loop=True, active_midi_clock_fails_closed=True)


def check_text_transport():
    trace = MenuTrace()
    def call(address, *arguments, com=False):
        for i, value in enumerate((STOP, *arguments)):
            trace.put(STACK + i * 4, value)
        trace.machine.reg_write(UC_X86_REG_ESP, STACK)
        trace.machine.reg_write(UC_X86_REG_EIP, address)
        (trace.com_fixture if com else trace.fixture)(address)
        if (trace.machine.reg_read(UC_X86_REG_ESP) != STACK + 4 * (1 + len(arguments))
                or trace.machine.reg_read(UC_X86_REG_EIP) != STOP):
            raise Blocked('Text transport violated stdcall ABI')
        return trace.machine.reg_read(UC_X86_REG_EAX)
    def com(obj, slot, *args):
        return call(trace.word(trace.word(obj) + slot), obj, *args, com=True)
    def api(name, *args):
        target = next(a for a, (_, n) in trace.imports.items() if n.split('!')[-1] == name)
        return call(target, *args)
    def rejects(action):
        try:
            action()
        except Blocked:
            return
        raise Blocked('Invalid text operation did not fail closed')
    front, back = trace.surface(64, 32, 0x218), trace.surface(64, 32, 4)
    trace.com_objects[front]['back'] = back
    entries = bytearray(1024)
    entries[4 * 17:4 * 17 + 3] = b'\xff\xff\xff'
    entries[4 * 18:4 * 18 + 3] = b'\xff\xff\xff'  # lowest-index tie
    palette = trace.com_object('IDirectDrawPalette', entries=entries.hex())
    com(front, 124, palette)
    pixels = trace.com_objects[back]['pixels']
    trace.machine.mem_write(pixels, bytes([9]) * 2048)
    output, rect = trace.allocate(4), trace.allocate(16)
    offscreen = trace.surface(64, 32, 0x840)
    trace.com_objects[front]['references'] = 0
    rejects(lambda: com(offscreen, 68, output))
    trace.com_objects[front]['references'] = 1
    trace.deny_platform = trace.word(trace.word(offscreen) + 68)
    rejects(lambda: com(offscreen, 68, output))
    trace.deny_platform = None
    if trace.com_objects[offscreen]['locked'] or trace.dcs:
        raise Blocked('Withheld offscreen GetDC changed physical state')
    com(offscreen, 68, output)
    offscreen_dc = trace.word(output)
    if trace.dcs[offscreen_dc]['palette'] != entries.hex() or trace.com_objects[offscreen].get('palette'):
        raise Blocked('Offscreen GetDC did not inherit the physical display palette')
    com(offscreen, 104, offscreen_dc)
    other_primary = trace.surface(64, 32, 0x218)
    com(other_primary, 124, palette)
    rejects(lambda: com(offscreen, 68, output))
    own_entries = bytes([31]) * 1024
    own_palette = trace.com_object('IDirectDrawPalette', entries=own_entries.hex())
    com(offscreen, 124, own_palette)
    com(offscreen, 68, output)
    offscreen_dc = trace.word(output)
    if trace.dcs[offscreen_dc]['palette'] != own_entries.hex():
        raise Blocked('Attached offscreen palette did not override display fallback')
    com(offscreen, 104, offscreen_dc)
    trace.com_objects[other_primary]['references'] = 0
    trace.put(output, 0xabcdef)
    trace.deny_platform = trace.word(trace.word(back) + 68)
    rejects(lambda: com(back, 68, output))
    if trace.word(output) != 0xabcdef or trace.dcs or trace.com_objects[back]['locked']:
        raise Blocked('Withheld GetDC mutated physical state')
    trace.deny_platform = None
    com(back, 68, output)
    dc = trace.word(output)
    rejects(lambda: com(back, 68, output))
    rejects(lambda: com(front, 44, 0, 1))
    rejects(lambda: com(back, 128, 0))
    if api('SetBkMode', dc, 1) != 2 or api('SetTextColor', dc, 0xffffff) != 0:
        raise Blocked('Text setters did not return previous values')
    text = trace.cstring(b'Player')
    trace.machine.mem_write(rect, struct.pack('<4i', 5, 3, 26, 18))
    target = next(a for a, (_, n) in trace.imports.items() if n.endswith('!DrawTextA'))
    trace.deny_platform = target
    rejects(lambda: api('DrawTextA', dc, text, 0xffffffff, rect, 0x20))
    if bytes(trace.machine.mem_read(pixels, 2048)) != bytes([9]) * 2048:
        raise Blocked('Withheld DrawText mutated pixels')
    trace.deny_platform = None
    height = api('DrawTextA', dc, text, 0xffffffff, rect, 0x20)
    data = bytes(trace.machine.mem_read(pixels, 2048))
    changed = [i for i, value in enumerate(data) if value != 9]
    if (height != 16 or not changed or any(data[i] != 17 or not
            (5 <= i % 64 < 26 and 3 <= i // 64 < 18) for i in changed)):
        raise Blocked('Text did not respect palette mapping, clipping or transparent background')
    left_hash = hashlib.sha256(data).hexdigest()
    trace.machine.mem_write(pixels, bytes([9]) * 2048)
    api('DrawTextA', dc, text, 0xffffffff, rect, 0x22)
    if hashlib.sha256(bytes(trace.machine.mem_read(pixels, 2048))).hexdigest() == left_hash:
        raise Blocked('Right alignment did not affect glyph placement')
    before = bytes(trace.machine.mem_read(pixels, 2048))
    rejects(lambda: api('DrawTextA', dc, text, 0xffffffff, rect, 0x400))
    rejects(lambda: com(front, 104, dc))
    if bytes(trace.machine.mem_read(pixels, 2048)) != before:
        raise Blocked('Rejected text operation changed pixels')
    com(back, 104, dc)
    rejects(lambda: com(back, 104, dc))
    rejects(lambda: api('SetTextColor', dc, 0))
    com(front, 44, 0, 1)
    if trace.presentations[-1]['pixels_sha256'] != hashlib.sha256(before).hexdigest() or trace.dcs:
        raise Blocked('Released text storage did not reach physical presentation')
    return dict(status='pass', font=trace.font_evidence, dc_lifetime_and_surface_exclusion=True,
        transparent_clipped_glyphs=True, palette_mapping_and_ties=True, alignment=True,
        withheld_getdc_and_drawtext_no_effect=True, stale_or_wrong_dc_rejected=True,
        offscreen_primary_palette_and_attached_override=True,
        missing_or_ambiguous_display_palette_rejected=True,
        text_pixels_reach_flip=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/menu-map/trace.json')
    parser.add_argument('--instruction-limit', type=int)
    parser.add_argument('--paper-startup', action='store_true',
                        help='Original fader and palette, 1 ms query clock and 17 ms frame steps')
    parser.add_argument('--deny-platform', type=lambda a: int(a, 0))
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'work').resolve()):
        parser.error('Derived trace output must stay under ignored work/')
    limit = args.instruction_limit if args.instruction_limit is not None else (2_000_000_000 if args.paper_startup else 80_000_000)
    trace = run_trace(limit, args.deny_platform, startup_paper=args.paper_startup)
    report = trace.report()
    if args.deny_platform is None:
        try:
            report['scene_fixture_check'] = check_scene_controls(trace)
            report['resource_fixture_check'] = check_resource_controls(trace)
            report['tail_transport_check'] = check_tail_transport()
            report['frame_transport_check'] = check_frame_transport()
            report['text_transport_check'] = check_text_transport()
            complete = (report['initializer_return'] and report['initializer_return']['status'] == 'pass'
                        and report['factory_return'] and report['factory_return']['status'] == 'pass')
            controls = all(report[key]['status'] == 'pass' for key in
                           ('scene_fixture_check', 'resource_fixture_check', 'tail_transport_check',
                            'frame_transport_check', 'text_transport_check'))
            report['initializer_check'] = dict(status='pass' if complete and controls else 'blocked',
                original_initializer=report['initializer_return'], original_factory=report['factory_return'],
                controls_pass=controls)
            frames_complete = (report['stop'] is None and len(report['frame_cycles']) == 61
                               and len(report['presentations']) == 61 and report['idle_frames'] == 60)
            report['frame_check'] = dict(status='pass' if complete and controls and frames_complete else 'blocked',
                completed_cycles=len(report['frame_cycles']), presentations=len(report['presentations']),
                controls_pass=controls)
            if report['frame_check']['status'] == 'pass':
                report['status'] = 'pass'
                report['scope'] = 'Original initializer, first presentation and 60 deterministic idle cycles; no native parity or admission claim'
        except (Blocked, UcError) as error:
            report['status'] = 'blocked'
            report['control_error'] = str(error)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], counts=report['counts'], stop=report['stop'],
                          scene_fixture_check=report.get('scene_fixture_check'),
                          resource_fixture_check=report.get('resource_fixture_check'),
                          tail_transport_check=report.get('tail_transport_check'),
                          initializer_check=report.get('initializer_check'),
                          resource_uploads=report['resource_uploads'],
                          frame_check=report.get('frame_check'), frame_transport_check=report.get('frame_transport_check'),
                          first_presented_frame=report['first_presented_frame'], idle_frames=report['idle_frames'], output=str(output))))
    return 0 if report['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
