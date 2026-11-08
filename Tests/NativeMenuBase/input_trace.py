"""Original main-menu input census and deterministic frame reference.

Run: work/test-env/bin/python -m Tests.NativeMenuBase.input_trace
Windows dispatch forwards key-down to application 429d60 and primary-down
(flags, x, y) to 429d80. Those dispatch the current scene's virtual handlers.
Only physical cursor/key/message state is supplied here; no menu decisions.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from PIL import Image
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EAX
from Tests.NativeMenuBase.trace import MenuTrace, Blocked, ROOT

# Frame numbers are one based, shared with the Mac app evidence input.
EVENTS = [
    dict(frame=9, message=0x100, key=40, label='down'),
    dict(frame=10, message=0x101, key=40),
    dict(frame=17, message=0x100, key=38, label='up'),
    dict(frame=18, message=0x101, key=38),
    dict(frame=25, message=0x100, key=13, label='single-player'),
    dict(frame=26, message=0x101, key=13),
    dict(frame=33, message=0x100, key=27, label='back'),
    dict(frame=34, message=0x101, key=27),
    dict(frame=41, message=0x200, x=320, y=230, label='hover'),
    dict(frame=49, message=0x201, x=320, y=230, label='click'),
    dict(frame=50, message=0x202, x=320, y=230),
]

class InputTrace(MenuTrace):
    def __init__(self, output, frames=61, startup_paper=False):
        super().__init__(instruction_limit=2_000_000_000 if startup_paper else 120_000_000,
                         startup_paper=startup_paper)
        self.output = output
        self.requested_frames = frames
        self.input_witnesses = []

    def fixture(self, address):
        if address == 0x4a4250:
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            value, = struct.unpack('<d', self.machine.mem_read(sp + 4, 8))
            if not math.isfinite(value):
                raise Blocked('Non-finite CRT ceil operand')
            self.platform_call(address, 'CRT ceil')
            result = float(math.ceil(value))
            if result == 0:
                result = math.copysign(0.0, value)
            self.x87_result(0, result)
            self.returned(self.machine.reg_read(UC_X86_REG_EAX))
            return
        if address in self.imports and self.imports[address][1].endswith('!PtInRect'):
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            rect = self.word(sp + 4)
            left, top, right, bottom = struct.unpack('<4i', self.machine.mem_read(rect, 16))
            x, y = struct.unpack('<2i', self.machine.mem_read(sp + 8, 8))
            self.platform_call(address, self.imports[address][1])
            self.returned(int(left <= x < right and top <= y < bottom), 12)
            return
        # Real selective PeekMessage removal, used by recovered menu drains.
        if address in self.imports and self.imports[address][1].endswith('!PeekMessageA'):
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            dest, window, low, high, remove = [self.word(sp + i * 4) for i in range(1, 6)]
            if window not in (0, 1) or remove not in (0, 1):
                raise Blocked('Unsupported physical PeekMessage selector')
            self.platform_call(address, self.imports[address][1])
            self.physical_events.append(dict(service='PeekMessageA', window=window,
                minimum=low, maximum=high, remove=remove, queued=len(self.messages)))
            index = next((i for i, m in enumerate(self.messages)
                if (not window or m[0] == window) and (low == high == 0 or low <= m[1] <= high)), None)
            if index is not None:
                for i, value in enumerate((*self.messages[index], self.milliseconds, *self.cursor)):
                    self.put(dest + i * 4, value)
                if remove:
                    self.messages.pop(index)
            self.returned(int(index is not None), 20)
            return
        super().fixture(address)

    def execute_frames(self, application):
        menu = self.word(application + 0x2c)
        for frame in range(1, self.requested_frames + 1):
            self.advance_time(self.milliseconds + 17 if self.startup_paper else
                              1000 + frame * 1000 // 60)
            self.dispatch_messages(application)
            for event in (e for e in EVENTS if e['frame'] == frame):
                message = event['message']
                if 'key' in event:
                    (self.pressed_keys.add if message == 0x100 else self.pressed_keys.discard)(event['key'])
                    if message == 0x100:
                        self.run(0x429d60, application, (event['key'], 1), phase=event['label'])
                else:
                    self.cursor = (event['x'], event['y'])
                    if message == 0x201:
                        self.pressed_keys.add(1)
                        self.run(0x429d80, application, (1, *self.cursor), phase=event['label'])
                    elif message == 0x202:
                        self.pressed_keys.discard(1)
                        self.run(0x429db0, application, (0, *self.cursor), phase='primary-up')
                    elif message == 0x200:
                        self.run(0x429de0, application, (0, *self.cursor), phase=event['label'])
            before = len(self.presentations)
            result = self.run(0x428b60, application, phase=f'input-frame-{frame}')
            if result != 1 or len(self.presentations) != before + 1:
                raise Blocked('Input cycle did not present exactly one frame')
            selected = self.run(0x4dd480, menu + 0x154, phase='observe-selection')
            page = self.run(0x4dd0c0, menu + 0x154, phase='observe-page')
            witness = dict(frame=frame, selected=selected, page_id=self.word(page + 80) if page else None)
            witness.update(self.extra_witness(application))
            self.input_witnesses.append(witness)
            self.frame_cycles.append(dict(index=frame-1, milliseconds=self.milliseconds, result=result))
            if frame in (1, 9, 17, 26, 33, 41, 50, 61) or frame == self.requested_frames:
                surface = next(o for o in self.com_objects.values() if o.get('caps') == 0x218)
                pixels = bytes(self.machine.mem_read(surface['pixels'], surface['pitch'] * surface['height']))
                palette = bytes.fromhex(self.com_objects[surface['palette']]['entries'])
                image = Image.frombytes('P', (surface['width'], surface['height']), pixels)
                image.putpalette(bytes(v for i, v in enumerate(palette) if i % 4 != 3))
                image.save(self.output / f'original-{frame:02d}.png')
            print(json.dumps(witness), flush=True)

    def dispatch_messages(self, application):
        """Specialized references may supply the native window command pump."""

    def extra_witness(self, application):
        return {}


def main():
    global EVENTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/menu-input')
    parser.add_argument('--frames', type=int, default=61)
    parser.add_argument('--events', type=Path, help='Physical input script for another menu sequence')
    parser.add_argument('--paper-startup', action='store_true')
    args = parser.parse_args()
    if args.events:
        EVENTS = json.loads(args.events.read_text())
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'work').resolve()):
        parser.error('Original-derived evidence must remain under work/')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'events.json').write_text(json.dumps(EVENTS, indent=2) + '\n')
    if not 61 <= args.frames <= 1801:
        parser.error('Input trace supports 61 through 1801 frames')
    trace = InputTrace(output, args.frames, startup_paper=args.paper_startup)
    try:
        trace.execute()
    except (Blocked, UcError) as error:
        trace.stop = dict(address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error), phase=trace.phase)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    idle = json.loads((ROOT / 'work/menu-map/trace.json').read_text())
    for key in ('game_functions', 'platform_calls', 'platform_imports'):
        previous = {x['address'] for x in idle[key]}
        report['new_' + key] = [x for x in report[key] if x['address'] not in previous]
    report.update(status='pass' if trace.stop is None and len(trace.presentations) == args.frames else 'blocked',
        events=EVENTS, input_witnesses=trace.input_witnesses,
        scope='Original scripted menu input and frame census; native comparison separate')
    (output / 'original.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'stop', 'counts', 'new_game_functions', 'new_platform_imports')}))
    return 0 if report['status'] == 'pass' else 2

if __name__ == '__main__':
    raise SystemExit(main())
