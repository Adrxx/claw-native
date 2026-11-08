"""Original startup, menu/Credits and New Game primary-surface writes.

Run with work/test-env/bin/python -m Tests.NativeMenuBase.paper_trace.
All derived bytes remain under work/paper-roll/transitions. No game fixtures.
"""
import argparse
import json
import math
import struct
from PIL import Image, ImageDraw
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ECX
from Tests.NativeLevelOne.trace import LevelOneTrace, Blocked, ROOT

OUT = ROOT / 'work/paper-roll/transitions'
RECORD = OUT
FRAME_COUNT = 106
EVENTS = [dict(frame=9, message=513, x=320, y=377),
          dict(frame=10, message=514, x=320, y=377)]
for frame, key in ((33, 27), (57, 13), (81, 13), (105, 13)):
    EVENTS += [dict(frame=frame, message=256, key=key),
               dict(frame=frame+1, message=257, key=key)]


class Complete(Exception):
    pass


class PaperTrace(LevelOneTrace):
    def __init__(self):
        super().__init__(6_000_000_000, startup_paper=True)
        self.paper_frames = []
        self.paper_reached = set()
        self.cursor_handle = 0
        self.paper_next_frame = 1
        self.paper_event_start = 0
        self.regions = {}

    def text_fixture(self, api, arg):
        if api != 'DrawTextA' or arg(5) not in (0x450, 0x50):
            return super().text_fixture(api, arg)
        dc = self.dcs.get(arg(1))
        if not dc:
            raise Blocked('Credits text needs a live surface DC')
        surface = self.com_objects[dc['surface']]
        if not surface['locked'] or surface.get('dc') != arg(1):
            raise Blocked('Credits text lost its surface lease')
        length = arg(3)
        if length != 0xffffffff and length > 65536:
            raise Blocked('Unbounded Credits text')
        raw = self.bytestring(arg(2)) if length == 0xffffffff else bytes(self.machine.mem_read(arg(2), length))
        if any(c not in (9, 10, 13) and not 32 <= c <= 126 for c in raw) or b'&' in raw:
            raise Blocked('Unsupported Credits text encoding')
        text = raw.decode('ascii').expandtabs(8)
        rect = struct.unpack('<4i', self.machine.mem_read(arg(4), 16))
        left, top, right, bottom = rect
        if not (-65536 <= left <= right <= 65536 and -65536 <= top <= bottom <= 65536):
            raise Blocked('Invalid Credits text rectangle')
        measure = lambda s: sum(math.ceil(self.font.getlength(c)) for c in s)
        lines = []
        for line in text.split('\n'):
            line = line.removesuffix('\r')
            start, last_break, i = 0, None, 0
            while i < len(line):
                if line[i] == ' ':
                    last_break = i
                if measure(line[start:i+1]) > right-left and last_break is not None and last_break > start:
                    lines.append(line[start:last_break])
                    start, i, last_break = last_break+1, last_break+1, None
                    continue
                i += 1
            lines.append(line[start:])
        height = sum(self.font.getmetrics()) * len(lines)
        if arg(5) & 0x400:
            self.machine.mem_write(arg(4), struct.pack('<4i',left,top,left+max(map(measure,lines),default=0),top+height))
        else:
            if dc['background_mode'] != 1:
                raise Blocked('Credits drawing requires transparent text')
            mask = Image.new('1',(surface['width'],surface['height']))
            draw = ImageDraw.Draw(mask)
            for n,line in enumerate(lines):
                draw.text((left,top+n*sum(self.font.getmetrics())),line,font=self.font,fill=1,anchor='lt')
            palette = bytes.fromhex(dc['palette'])
            color = [(dc['text_color'] >> (8*c)) & 255 for c in range(3)]
            index = min(range(256),key=lambda i:sum((palette[4*i+c]-color[c])**2 for c in range(3)))
            pixels = bytearray(self.machine.mem_read(dc['pixels'],surface['pitch']*surface['height']))
            clip = dc.get('clip') or (0,0,surface['width'],surface['height'])
            for y in range(max(0,top,clip[1]),min(surface['height'],bottom,clip[3])):
                for x in range(max(0,left,clip[0]),min(surface['width'],right,clip[2])):
                    if mask.getpixel((x,y)):
                        pixels[y*surface['pitch']+x] = index
            self.machine.mem_write(dc['pixels'],bytes(pixels))
        self.physical_events.append(dict(service=api,flags=arg(5),lines=len(lines),height=height,rectangle=rect,phase=self.phase))
        self.returned(height if raw else 0,20)

    def fixture(self, address):
        api = self.imports.get(address, (None, ''))[1].split('!')[-1]
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        arg = lambda i:self.word(sp+4*i)
        if api == 'SelectClipRgn':
            dc = self.dcs.get(arg(1))
            if dc is None or arg(2) and arg(2) not in self.regions:
                raise Blocked('Invalid Credits clipping region')
            dc['clip'] = self.regions.get(arg(2))
            self.platform_call(address,self.imports[address][1])
            self.returned(2,8)
            return
        if address == 0x4fd732:
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            handle = self.word(receiver+4)
            if handle and handle not in self.regions:
                raise Blocked('Invalid Credits region deletion')
            self.platform_call(address,'MFC CGdiObject DeleteObject')
            if handle:
                del self.regions[handle]
                self.allocations.pop(handle)
                self.put(receiver+4,0)
            self.returned(int(bool(handle)))
            return
        if address == 0x4f2190:
            if self.bytestring(arg(1)) != b'' or arg(2) != 0:
                raise Blocked('Paper access probe is outside the empty optional path profile')
            self.platform_call(address,'CRT _access empty path')
            self.returned(0xffffffff)
            return
        if api == 'CreateRectRgn':
            handle = self.allocate(16)
            self.regions[handle] = tuple(arg(i) for i in range(1,5))
            self.platform_call(address, self.imports[address][1])
            self.physical_events.append(dict(service=api,handle=hex(handle),rectangle=self.regions[handle]))
            self.returned(handle,16)
            return
        if address == 0x4fd6db:
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            if arg(1) not in self.regions or self.word(receiver+4):
                raise Blocked('Invalid native region attachment')
            self.platform_call(address,'MFC CGdiObject Attach')
            self.put(receiver+4,arg(1))
            self.returned(1,4)
            return
        if api == 'SetCursor':
            # This startup profile has no loaded HCURSOR. Credits clears it;
            # retain the previous opaque handle as USER32 does, with no pixels.
            handle = self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            if handle != 0:
                raise Blocked('Paper route requested an unelected cursor handle')
            self.platform_call(address, self.imports[address][1])
            previous, self.cursor_handle = self.cursor_handle, handle
            self.physical_events.append(dict(service=api, handle=handle, previous=previous))
            self.returned(previous, 4)
            return
        super().fixture(address)

    def hook(self, machine, address, size, user):
        if address in (0x435a50, 0x45b3f0, 0x48f500, 0x48f740, 0x490130, 0x449940):
            self.paper_reached.add(address)
        super().hook(machine, address, size, user)

    def execute_frames(self, application):
        self.application = application
        if not self.resumed_checkpoint:
            self.checkpoint_path = OUT/'startup.checkpoint'
            self.save_checkpoint()
        # Later command checkpoints must never overwrite the startup cache.
        self.checkpoint_path = None
        primary = next(a for a, o in self.com_objects.items() if o.get('caps') == 0x218)
        start = getattr(self, 'paper_event_start', 0)
        for frame in range(getattr(self, 'paper_next_frame', 1), FRAME_COUNT+1):
            # Scripted events first update physical key/cursor state. Their
            # handlers run after prior posted commands, as in the native pump.
            events = [e for e in EVENTS if e['frame'] == frame]
            for event in events:
                if 'key' in event:
                    (self.pressed_keys.add if event['message'] == 256 else self.pressed_keys.discard)(event['key'])
                else:
                    self.cursor = (event['x'],event['y'])
                    (self.pressed_keys.add if event['message'] == 513 else self.pressed_keys.discard)(1)
            before = len(self.presentations)
            pending = bool(self.messages)
            if not pending:
                self.advance_time(self.milliseconds + 17)
            self.drain_messages(application)
            if self.word(self.word(application+0x2c)) == 0x50c264:
                self.clock_step = 0
            if pending:
                self.advance_time(self.milliseconds + 17)
            for event in events:
                message = event['message']
                if 'key' in event:
                    if message == 256:
                        self.run(0x429d60, application, (event['key'], 1), phase=f'paper-input-{frame}')
                else:
                    target = 0x429d80 if message == 513 else 0x429db0
                    self.run(target, application, (1 if message == 513 else 0, *self.cursor),
                             phase=f'paper-input-{frame}')
            self.run(0x428b60, application, phase=f'paper-frame-{frame}')
            self.paper_frames.append(dict(frame=frame,
                state=self.menu_state(application),
                presentations=self.presentations[before:],
                primary_writes=[e['pixels_sha256'] for e in self.physical_events[start:]
                    if e.get('service') == 'IDirectDrawSurface::Unlock' and e.get('object') == hex(primary)]))
            start = len(self.physical_events)
            if frame == 1:
                self.setup_navigation(application)
            self.paper_next_frame = frame+1
            self.paper_event_start = start
            if frame in (1, 10, 34, FRAME_COUNT):
                self.checkpoint_path = RECORD/'route.checkpoint'
                self.save_checkpoint()
                self.checkpoint_path = None
            print(json.dumps(dict(event='paper-frame',frame=frame,state=self.paper_frames[-1]['state'],
                                  writes=len(self.paper_frames[-1]['primary_writes']))), flush=True)
        raise Complete

    def navigate(self, application):
        # LevelOneTrace's local checkpoint loader resumes here.
        self.execute_frames(application)


def main():
    global RECORD, EVENTS, FRAME_COUNT
    parser = argparse.ArgumentParser(description=__doc__)
    routes = parser.add_mutually_exclusive_group()
    routes.add_argument('--new-game-only', action='store_true')
    routes.add_argument('--credits-only', action='store_true')
    args = parser.parse_args()
    if args.new_game_only:
        RECORD = OUT/'new-game'
        FRAME_COUNT = 61
        EVENTS = [dict(frame=f+offset,message=256+offset,key=13)
                  for f in (9,33,57) for offset in (0,1)]
    elif args.credits_only:
        RECORD = OUT/'credits'
        FRAME_COUNT = 61
        EVENTS = [event for event in EVENTS if event['frame'] <= 34]
    RECORD.mkdir(parents=True, exist_ok=True)
    (RECORD / 'events.json').write_text(json.dumps(EVENTS, indent=2)+'\n')
    trace = PaperTrace()
    error = None
    try:
        if (RECORD/'route.checkpoint').exists():
            trace.resume_checkpoint(RECORD/'route.checkpoint', completed_frame=True)
        elif (OUT/'startup.checkpoint').exists():
            trace.resume_checkpoint(OUT/'startup.checkpoint')
        else:
            trace.execute()
    except Complete:
        pass
    except KeyboardInterrupt:
        error = 'interrupted; resume from the last completed transition checkpoint'
    except Exception as caught:
        error = repr(caught)
    finally:
        for stream in trace.files.values():
            stream.close()
    required = {0x435a50, 0x45b3f0, 0x48f500, 0x48f740, 0x490130}
    if args.new_game_only:
        required = {0x45b3f0, 0x490130}
    elif args.credits_only:
        required.remove(0x490130)
    report = dict(status='pass' if error is None and required <= trace.paper_reached else 'fail',
        error=error, pc=hex(trace.machine.reg_read(UC_X86_REG_EIP)), phase=trace.phase,
        executable_sha256=trace.program.sha256 if hasattr(trace.program,'sha256') else
            '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',
        startup=trace.startup_evidence, clock_query_ms=1, frame_step_ms=17,
        reached=[hex(a) for a in sorted(trace.paper_reached)], frames=trace.paper_frames,
        route='new-game' if args.new_game_only else 'credits' if args.credits_only else 'credits-new-game')
    (RECORD/'original.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('frames','startup')}),flush=True)
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
