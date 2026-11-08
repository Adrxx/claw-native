"""Omar acceptance route with the ending's physical window services.

The combat observer and its hash-validated start checkpoint stay unchanged.
This suffix adapter is separately fingerprinted in the resulting reference.
"""
import hashlib
import math
import struct
import json
import subprocess
from PIL import Image, ImageDraw
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX
from Tests.NativeLevels import ROOT
from Tests.NativeLevels import level_fourteen_boss_trace as combat
from Tests.NativeMenuBase.trace import Blocked
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevels.storage import load_checkpoint, fingerprint


class EndingTrace(combat.OmarTrace):
    def __init__(self, **options):
        self.ending_adapter_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.background_movies = {}
        self.background_objects = set()
        self.background_inputs = {}
        super().__init__(**options)

    def checkpoint_inputs(self):
        return {**super().checkpoint_inputs(),
            'Tests/NativeLevels/level_fourteen_ending_trace.py': self.ending_adapter_sha256}

    def background_open(self, receiver, movie):
        path = ROOT/f'App/GameData/MOVIES/movie-{movie:02}.mp4'
        manifest = json.loads((path.parent/'movies.json').read_text())
        entry = next(e for e in manifest['entries'] if e['movieID'] == movie)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry['sha256']: raise Blocked('Changed converted background movie')
        self.background_inputs[str(path.relative_to(ROOT))] = digest
        meta = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'frame=best_effort_timestamp_time:stream=duration,width,height', '-of', 'json', str(path)]))
        stream = meta['streams'][0]; w, h = stream['width'], stream['height']
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'])
        frames = []
        size = w*h
        levels, blues = [0,5,21,47,83,130,187,255], [0,28,113,255]
        channel = [min(range(8), key=lambda i: abs(levels[i]-v)) for v in range(256)]
        blue = [min(range(4), key=lambda i: abs(blues[i]-v)) for v in range(256)]
        for start in range(0, len(raw), size*3//2):
            data = raw[start:start+size*3//2]; indexed = bytearray(size)
            for row in range(h):
                for col in range(w):
                    c = max(0, data[row*w+col]-16)
                    at = (row//2)*(w//2)+col//2
                    d, e = data[size+at]-128, data[size+size//4+at]-128
                    r = min(255,max(0,(298*c+409*e+128)>>8))
                    g = min(255,max(0,(298*c-100*d-208*e+128)>>8))
                    b = min(255,max(0,(298*c+516*d+128)>>8))
                    indexed[row*w+col] = (channel[r] << 5) | (channel[g] << 2) | blue[b]
            frames.append(bytes(indexed))
        palette = bytes(v for i in range(256) for v in (levels[(i>>5)&7], levels[(i>>2)&7], blues[i&3], 0))
        template = next(t for t,o in self.com_objects.items() if o['kind'] == 'IDirectDrawPalette')
        token = self.allocate(4); self.put(token, self.word(template))
        self.com_objects[token] = dict(kind='IDirectDrawPalette', references=1, entries=palette.hex())
        self.put(receiver+32, token)
        self.background_movies[receiver] = dict(movie=movie, frames=frames, width=w, height=h,
            times=[float(f['best_effort_timestamp_time']) for f in meta['frames']], duration=float(stream['duration']), start=None)
        self.physical_events.append(dict(service='BackgroundMovie::Open', movie=movie, frames=len(frames)))

    def text_fixture(self, api, arg):
        if api != 'DrawTextA' or arg(5) not in (0x450, 0x50, 0x75):
            return super().text_fixture(api, arg)
        dc = self.dcs.get(arg(1))
        if not dc: raise Blocked('Unknown credits text DC')
        surface = self.com_objects[dc['surface']]
        if surface.get('dc') != arg(1) or not surface['locked'] or surface['lost']:
            raise Blocked('Credits DC lost its surface lease')
        flags = arg(5)
        if flags == 0x450 and not getattr(self, 'background_enabled', False):
            # The retained prefix has no movie installation. Supply the native
            # startup's prepared container path at the credits boundary, before
            # the unchanged owner copies/tests its CString in 0x436340.
            path = b'C:\\CLAW\\CLAW.FEC'
            block = self.allocate(len(path)+13)
            self.put(block, 1); self.put(block+4, len(path)); self.put(block+8, len(path))
            self.machine.mem_write(block+12, path+b'\0')
            self.put(self.application+0x100, block+12)
            self.background_enabled = True
        if not flags & 0x400 and dc['background_mode'] != 1:
            raise Blocked('Credits require transparent text')
        raw = self.bytestring(arg(2)) if arg(3) == 0xffffffff else bytes(self.machine.mem_read(arg(2), arg(3)))
        if len(raw) > 65536 or any(b not in (9, 10, 13) and not 32 <= b <= 126 for b in raw) or b'&' in raw:
            raise Blocked('Unsupported credits text encoding')
        text = raw.decode('ascii').expandtabs(8)
        left, top, right, bottom = struct.unpack('<4i', self.machine.mem_read(arg(4), 16))
        measure = lambda line: math.ceil(self.font.getlength(line))
        lines = []
        for line in ([text] if flags & 0x20 else text.split('\n')):
            line = line.removesuffix('\r')
            while flags & 0x10 and measure(line) > right-left:
                breaks = [i for i, c in enumerate(line) if c == ' ' and i > 0 and measure(line[:i]) <= right-left]
                if not breaks: break
                cut = breaks[-1]
                lines.append(line[:cut]); line = line[cut+1:]
            lines.append(line)
        height = sum(self.font.getmetrics())*len(lines) if text else 0
        event = dict(service=api, flags=flags, text=text, lines=len(lines), height=height,
                     rectangle=[left, top, right, bottom])
        if flags & 0x400:
            calculated = [left, top, left+max(map(measure, lines), default=0), top+height]
            self.machine.mem_write(arg(4), struct.pack('<4i', *calculated))
            event['calculated'] = True
            event['calculated_rectangle'] = calculated
        else:
            mask = Image.new('1', (surface['width'], surface['height']))
            draw = ImageDraw.Draw(mask)
            line_height = sum(self.font.getmetrics())
            for i, line in enumerate(lines):
                x = left+(right-left-measure(line))//2 if flags & 1 else left
                y = top+i*line_height+((bottom-top-line_height)//2 if flags & 0x24 == 0x24 else 0)
                draw.text((x, y), line, font=self.font, fill=1, anchor='lt')
            palette = bytes.fromhex(dc['palette'])
            rgb = [(dc['text_color'] >> (8*c)) & 255 for c in range(3)]
            index = min(range(256), key=lambda i: sum((palette[4*i+c]-rgb[c])**2 for c in range(3)))
            pixels = bytearray(self.machine.mem_read(dc['pixels'], surface['pitch']*surface['height']))
            clip = dc.get('credits_clip', [0, 0, surface['width'], surface['height']])
            for y in range(max(0, top, clip[1]), min(surface['height'], bottom, clip[3])):
                for x in range(max(0, left, clip[0]), min(surface['width'], right, clip[2])):
                    if mask.getpixel((x, y)): pixels[y*surface['pitch']+x] = index
            self.machine.mem_write(dc['pixels'], bytes(pixels))
            event.update(palette_index=index, pixels_sha256=hashlib.sha256(pixels).hexdigest())
        self.physical_events.append(event)
        self.returned(height, 20)

    def resume_target(self, path):
        if path.name != 'ending.checkpoint':
            return super().resume_target(path)
        state = load_checkpoint(path)['state']
        start = path.parent/'start.checkpoint'
        self.validate_checkpoint_profile(state)
        if state.get('checkpoint_inputs_sha256') != self.checkpoint_inputs():
            raise Blocked('Stale completed-combat ending checkpoint')
        self.boss_requested_plan = self.boss_plan
        self.boss_requested_fight_only = self.fight_only
        prefix = state.get('boss_plan', [])
        if (state.get('prefix_checkpoint_sha256') != fingerprint(start)
                or self.boss_plan[:len(prefix)] != prefix
                or state.get('stop') is not None
                or state['boss_frames'][-1]['elapsed_ms'] != prefix[-1]['end_ms']
                or state['boss_frames'][-1]['boss']['health'] != 0
                or any(e.get('service') in ('SetCursor', 'CreateRectRgn') for e in state['physical_events'])):
            raise Blocked('Invalid completed-combat ending checkpoint')
        self.boss_resume_ending = True
        self.boss_combat_start_checkpoint_sha256 = fingerprint(start)
        return LevelTrace.resume_target(self, path)

    def play_target(self, application):
        if getattr(self, 'boss_resume_ending', False):
            self.boss_plan = self.boss_requested_plan
            self.fight_only = self.boss_requested_fight_only
            elapsed = self.boss_frames[-1]['elapsed_ms']
            start = self.milliseconds-elapsed
            before_functions = self.functions.copy()
            def death(machine, address, size, user):
                snapshot = self.boss_snapshot()
                if snapshot.get('private') == hex(machine.reg_read(UC_X86_REG_ECX)):
                    self.boss_death_callbacks.append(dict(address=hex(address), receiver=snapshot['private'],
                        elapsed_ms=self.milliseconds-start, health=snapshot['health']))
            hook = self.machine.uc.hook_add(UC_HOOK_CODE, death, begin=0x40e5c0, end=0x40e5c0)
            for action in self.boss_plan:
                if action['start_ms'] < elapsed:
                    continue
                if action['start_ms'] != elapsed or action['keys'] or action.get('cheat'):
                    raise Blocked('Ending checkpoint only permits an explicit stationary death-animation tail')
                if 'set_x' in action:
                    actor = self.word(0x537e88)
                    self.put(actor+0x4c, action['set_x']); self.put(actor+0x50, action['set_y'])
                while self.milliseconds-start < action['end_ms']:
                    before = len(self.presentations)
                    self.frame(application, 'level-14-boss-'+action['action'], [])
                    player = self.player_snapshot(application)
                    if player.get('vtable') != '0x50c264' or player.get('level') != 14:
                        raise Blocked('Death-animation tail collected the ending gem before MPSCULLY')
                    self.boss_frames.append(dict(elapsed_ms=self.milliseconds-start, action=action['action'],
                        player=player, boss=self.boss_snapshot(), presentation_start=before,
                        presentation_count=len(self.presentations)-before))
                elapsed = self.milliseconds-start
            self.machine.hook_del(hook)
            for address, count in self.functions.items():
                if count > before_functions[address]:
                    key = hex(address)
                    self.boss_route_functions[key] = self.boss_route_functions.get(key, 0)+count-before_functions[address]
            self.complete_level(application, 14)
            self.clock_step = 0
            self.boss_route_complete = True
            return
        return super().play_target(application)

    def fixture(self, address):
        receiver = self.machine.reg_read(UC_X86_REG_ECX)
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        arg = lambda i: self.word(sp+4*i)
        imported = self.imports.get(address)
        if address == 0x4a3b10:
            self.platform_call(address, 'time')
            value = 1700000000+self.milliseconds//1000
            if arg(1): self.put(arg(1),value)
            self.returned(value); return
        if address == 0x4f72c9:  # Native CFile lifetime; decoder owns the actual file.
            self.platform_call(address, 'CFile::CFile')
            for off, value in [(0,0x510844),(4,0xffffffff),(8,0),(12,0x52e1c4)]: self.put(receiver+off,value)
            self.returned(receiver); return
        if address == 0x4f7369:
            self.platform_call(address, 'CFile::~CFile')
            if [self.word(receiver+i) for i in (0,4,12)] != [0x510844,0xffffffff,0x52e1c4]:
                raise Blocked('Background CFile still owns a handle')
            self.returned(0); return
        if address == 0x4f57f8 and self.word(receiver) == 0x5108d4:
            self.platform_call(address, 'CArray::~CArray')
            if any(self.word(receiver+i) for i in (4,8,12)):
                raise Blocked('Background queue still owns entries')
            self.put(receiver,0x50becc); self.returned(0); return
        if imported and imported[1] == 'KERNEL32.dll!OpenFile' and getattr(self, 'background_enabled', False):
            if self.bytestring(arg(1)).upper().endswith(b'CLAW.FEC') and arg(3) == 0x4000:
                self.platform_call(address, 'OpenFile'); self.returned(1, 12); return
        if address == 0x4f0000:
            self.background_objects.add(receiver)
            self.platform_call(address, 'BackgroundMovie::Initialize'); self.returned(1, 124); return
        if address == 0x4f02e0 and arg(2) in (11, 12):
            self.platform_call(address, 'BackgroundMovie::Open')
            self.background_open(receiver, arg(2)); self.returned(1, 24); return
        if address == 0x4f0610 and receiver in self.background_movies:
            self.platform_call(address, 'BackgroundMovie::Frame')
            movie = self.background_movies[receiver]
            if movie['start'] is None: movie['start'] = self.milliseconds
            elapsed = (self.milliseconds-movie['start'])/1000
            if elapsed >= movie['duration']:
                self.physical_events.append(dict(service='BackgroundMovie::Frame', movie=movie['movie'], frame=len(movie['frames'])-1, playing=False))
                self.returned(0, 8); return
            frame = max(i for i,t in enumerate(movie['times']) if t <= elapsed)
            surface = self.com_objects[arg(1)]
            image = Image.frombytes('L', (movie['width'], movie['height']), movie['frames'][frame])
            image = image.resize((surface['width'],surface['height']), Image.Resampling.NEAREST)
            pixels = image.tobytes()
            for y in range(surface['height']):
                self.machine.mem_write(surface['pixels']+y*surface['pitch'], pixels[y*surface['width']:(y+1)*surface['width']])
            self.physical_events.append(dict(service='BackgroundMovie::Frame', movie=movie['movie'], frame=frame, playing=True, milliseconds=self.milliseconds))
            self.returned(1, 8); return
        if address in (0x4f06e0, 0x4f0120) and receiver in self.background_objects:
            self.platform_call(address, 'BackgroundMovie::Close')
            if receiver in self.background_movies:
                self.physical_events.append(dict(service='BackgroundMovie::Close', movie=self.background_movies[receiver]['movie']))
                del self.background_movies[receiver]
                token = self.word(receiver+32)
                self.com_objects[token]['references'] -= 1
            self.put(receiver+32, 0); self.returned(0); return
        if address in (0x4fd6db, 0x4fd732):
            self.platform_call(address, 'CGdiObject::Attach' if address == 0x4fd6db else 'CGdiObject::DeleteObject')
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            handle = self.word(receiver+4)
            if address == 0x4fd6db:
                sp = self.machine.reg_read(UC_X86_REG_ESP)
                region = self.word(sp+4)
                if handle or region not in getattr(self, 'boss_regions', {}):
                    raise Blocked('Invalid GDI region attachment')
                self.put(receiver+4, region)
                self.physical_events.append(dict(service='CGdiObject::Attach'))
                self.returned(1, 4)
            else:
                if handle:
                    if handle not in self.boss_regions: raise Blocked('Unknown owned GDI region')
                    del self.boss_regions[handle]
                    self.allocations.pop(handle)
                    self.put(receiver+4, 0)
                    self.physical_events.append(dict(service='CGdiObject::DeleteObject'))
                self.returned(int(bool(handle)))
            return
        imported = self.imports.get(address)
        if imported and imported[1] == 'GDI32.dll!SelectClipRgn':
            self.platform_call(address, 'SelectClipRgn')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            dc, region = self.word(sp+4), self.word(sp+8)
            if dc not in self.dcs or (region and region not in getattr(self, 'boss_regions', {})):
                raise Blocked('Unknown credits clip region/DC')
            if region: self.dcs[dc]['credits_clip'] = list(self.boss_regions[region])
            else: self.dcs[dc].pop('credits_clip', None)
            self.physical_events.append(dict(service='SelectClipRgn', dc=dc, region=region))
            self.returned(2, 8)
            return
        if imported and imported[1] == 'GDI32.dll!CreateRectRgn':
            self.platform_call(address, 'CreateRectRgn')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            rectangle = [self.word(sp+4*i) for i in range(1, 5)]
            region = self.allocate(16)
            for i, value in enumerate(rectangle): self.put(region+4*i, value)
            if not hasattr(self, 'boss_regions'): self.boss_regions = {}
            self.boss_regions[region] = rectangle
            self.physical_events.append(dict(service='CreateRectRgn', rectangle=rectangle, region=region))
            self.returned(region, 16)
            return
        if imported and imported[1] == 'GDI32.dll!DeleteObject':
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            region = self.word(sp+4)
            if region in getattr(self, 'boss_regions', {}):
                self.platform_call(address, 'DeleteObject')
                del self.boss_regions[region]
                self.allocations.pop(region)
                self.physical_events.append(dict(service='DeleteObject', region=region))
                self.returned(1, 4)
                return
        if imported and imported[1] == 'USER32.dll!SetCursor':
            if self.word(0x546cd8) != address:
                raise Blocked('Unreviewed ending cursor import')
            self.platform_call(address, 'SetCursor')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            cursor = self.word(sp+4)
            previous = getattr(self, 'boss_cursor_handle', 0)
            self.boss_cursor_handle = cursor
            self.physical_events.append(dict(service='SetCursor', cursor=cursor, previous=previous))
            self.returned(previous, 4)
            return
        return super().fixture(address)

    def complete_level(self, application, level):
        if level == 14 and not getattr(self, 'boss_resume_ending', False):
            # A diagnostic boundary for any further ending-service probes.
            # Acceptance is still recorded from the validated start checkpoint.
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.target_checkpoint.parent/'ending.checkpoint'
            self.save_checkpoint()
            self.checkpoint_path = None
        return super().complete_level(application, level)

    def report(self):
        result = super().report()
        result['adapter_inputs'][str(Path(__file__).relative_to(ROOT))] = self.ending_adapter_sha256
        result['adapter_inputs'].update(self.background_inputs)
        return result


def main():
    # Reuse the combat CLI, including checkpoint identity, archive validation,
    # signal handling and trace storage. Its observer factory is elected here.
    previous = combat.OmarTrace
    combat.OmarTrace = EndingTrace
    try:
        return combat.main()
    finally:
        combat.OmarTrace = previous


if __name__ == '__main__':
    raise SystemExit(main())
