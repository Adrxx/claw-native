"""Load a local generated WWD in the original New Game scene and trace its objects.

The opt-in fixture supplies the source level through the original New Game
command LPARAM and replaces the first 0x4cb200 world-load input pointer. Original
decoding, source-level resources, object loading and gameplay execute unchanged. This is a custom-scene wiring probe, not original-level parity.
No preloaded-world checkpoint is accepted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import signal
import time

from PIL import Image
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP

from Tests.NativeLevels import ROOT
from Tests.NativeLevels.storage import write_trace
from Tests.NativeLevels.string_compare_trace import StringCompareTrace
from Tests.NativeLevels.trace import Blocked


def sha(data):
    return hashlib.sha256(data).hexdigest()


class TestLevelTrace(StringCompareTrace):
    __test__ = False

    def __init__(self, *, wwd, manifest, play_ms, evidence_dir, wall_seconds=600, **kwargs):
        super().__init__(level=manifest['source_level'], destination=manifest['source_level'], evidence_dir=evidence_dir,
            route=[dict(start_ms=0, end_ms=play_ms, action='stand', keys=[])],
            play_ms=play_ms, **kwargs)
        self.custom_wwd = wwd
        self.custom_manifest = manifest
        self.custom_loaded = False
        self.world_inputs = []
        self.new_game_selection = []
        self.selected_loads = []
        self.loading_records = []
        self.loading_returns = set()
        self.actor_records = {}
        self.object_draws = {}
        self.test_output = evidence_dir
        self.runner_sha256 = sha(Path(__file__).read_bytes())
        self.wall_started = time.monotonic()
        self.wall_seconds = wall_seconds
        self.next_wall_probe = 65536
        self.next_progress = 10_000_000

    def hook(self, machine, address, size, user):
        if self.instructions >= self.next_wall_probe:
            self.next_wall_probe = self.instructions+65536
            elapsed = time.monotonic()-self.wall_started
            if elapsed >= self.wall_seconds:
                raise Blocked(f'Original custom-scene wall budget exceeded: {elapsed:.1f} seconds')
            if self.instructions >= self.next_progress:
                self.next_progress = self.instructions+10_000_000
                print(json.dumps(dict(event='progress', phase=self.phase,
                    instructions=self.instructions, wall_seconds=round(elapsed, 1))), flush=True)
        if address == 0x426e30:
            sp = machine.reg_read(UC_X86_REG_ESP)
            if self.word(sp+8) == 0x807f:
                if self.new_game_selection:
                    raise Blocked('Test scene unexpectedly requested another New Game')
                # The original New Game dispatcher forwards LPARAM to429b70
                # as its level argument. Select the source namespace explicitly.
                self.new_game_selection.append(dict(entry=hex(address), command='0x807f',
                    original_lparam=self.word(sp+12), source_level=self.target_level))
                self.put(sp+12, self.target_level)
        if address == 0x4cb200:
            sp = machine.reg_read(UC_X86_REG_ESP)
            if self.custom_loaded:
                raise Blocked('Test scene unexpectedly requested another world load')
            original = self.word(sp+4)
            token = self.allocate(len(self.custom_wwd))
            machine.mem_write(token, self.custom_wwd)
            # Explicit fixture input, shared with the native --test-level path.
            # The original callee and all subsequent game decisions are untouched.
            self.put(sp+4, token)
            self.world_inputs.append(dict(entry=hex(address), original=hex(original),
                fixture=hex(token), bytes=len(self.custom_wwd), sha256=sha(self.custom_wwd)))
            self.custom_loaded = True
        if self.custom_loaded and (address in (0x4d17e0, 0x4c7970, 0x4c7900, 0x4d2890)
                or address in self.loading_returns):
            sp = machine.reg_read(UC_X86_REG_ESP)
            for frame in self.loading_records[:]:
                if address == frame['return'] and sp == frame['sp']+8:
                    self.loading_records.remove(frame)
                    if not any(f['return'] == address for f in self.loading_records):
                        self.loading_returns.discard(address)
            if address == 0x4d17e0:
                pointer = self.word(sp+4)
                words = struct.unpack('<71I', bytes(machine.mem_read(pointer, 284)))
                lengths = words[1:5]
                logic = bytes(machine.mem_read(pointer+284+lengths[0], lengths[1])).split(b'\0', 1)[0].decode('ascii')
                for row in self.custom_manifest['objects']:
                    if (words[0], words[5], words[6], logic) == (row['id'], row['x'], row['y'], row['logic']):
                        event = dict(id=row['id'], logic=logic, x=row['x'], y=row['y'],
                            record=hex(pointer), phase=self.phase)
                        self.selected_loads.append(event)
                        self.loading_records.append({'event': event, 'sp': sp, 'return': self.word(sp)})
                        self.loading_returns.add(self.word(sp))
                        break
            if address in (0x4c7970, 0x4c7900) and self.loading_records:
                actor = machine.reg_read(UC_X86_REG_ECX)
                event = self.loading_records[-1]['event']
                event['actor'] = hex(actor)
                self.actor_records[actor] = event
            if address == 0x4d2890:
                actor = self.word(sp+4)
                if actor in self.actor_records:
                    key = str(self.actor_records[actor]['id'])
                    self.object_draws[key] = self.object_draws.get(key, 0)+1
        super().hook(machine, address, size, user)

    def finish_launch(self, application):
        self.navigation.append(dict(phase='launch-command-returned', state=self.menu_state(application)))
        state = self.word(application+0x2c)
        if self.word(state) != 0x50c264 or self.word(state+0x14) != self.target_level:
            raise Blocked('New Game did not reach the selected source level')
        controller = self.word(0x537204)
        bindings = {name: self.word(controller+offset) for name, offset in
            (('left', 0x38), ('right', 0x3c), ('up', 0x40), ('down', 0x44), ('jump', 0x48), ('attack', 0x4c))}
        if bindings != dict(left=0x25, right=0x27, up=0x26, down=0x28, jump=0x20, attack=0x11):
            raise Blocked('Original input bindings differ from physical key fixture')
        self.input_bindings = dict(controller=hex(controller), keys=bindings,
            initializer='0x430d80', poller='0x430ec0', service='GetAsyncKeyState')
        if not any(e.get('binding') == 'application+0x12c' for e in self.startup_evidence):
            self.setup_audio_preferences(application)
        if not self.word(application+0x4c):
            self.setup_overlay(application)
        self.play(application)

    def play(self, application):
        # Finish New Game normally, then probe this world directly. Inherited
        # later-level observers otherwise complete Level 1 and walk all levels.
        self.play_target(application)
        self.capture_screen()

    def play_target(self, application):
        from Tests.NativeLevels.trace import LevelTrace
        return LevelTrace.play_target(self, application)

    def capture_screen(self):
        primary = next((obj for obj in self.com_objects.values()
            if obj['kind'] == 'IDirectDrawSurface' and obj.get('caps') == 0x218
            and obj.get('references')), None)
        if primary is None:
            raise Blocked('No live original primary surface')
        palette = self.com_objects[primary['palette']]
        raw = bytes(self.machine.mem_read(primary['pixels'], primary['pitch']*primary['height']))
        image = Image.frombytes('P', (primary['width'], primary['height']), raw,
            'raw', 'P', primary['pitch'])
        colors = bytes.fromhex(palette['entries'])
        image.putpalette(bytes(v for i, v in enumerate(colors) if i % 4 != 3))
        image.convert('RGB').save(self.test_output/'original.png')

    def test_report(self):
        rows = []
        for row in self.custom_manifest['objects']:
            loaded = [event for event in self.selected_loads if event['id'] == row['id']]
            draws = self.object_draws.get(str(row['id']), 0)
            rows.append(dict(id=row['id'], logic=row['logic'], x=row['x'], y=row['y'],
                original_loads=len(loaded), image_bound=any('actor' in e for e in loaded),
                original_draw_calls=draws))
        passed = (self.stop is None and self.loaded and self.custom_loaded and len(self.new_game_selection) == 1
            and self.played_ms >= self.target_play_ms and bool(rows)
            and all(row['original_loads'] == 1 and row['image_bound'] and row['original_draw_calls'] > 0 for row in rows))
        return dict(schema=1, status='pass' if passed else 'fail',
            scope='Custom-scene original load and culled image-draw probe; not original-level parity',
            runtime_level=self.target_level, source_level=self.custom_manifest['source_level'],
            new_game_selection=self.new_game_selection,
            executable_sha256=self.program.sha256, archive=self.resource_evidence,
            wwd_sha256=sha(self.custom_wwd), runner_sha256=self.runner_sha256,
            wall_seconds=round(time.monotonic()-self.wall_started, 3), wall_budget_seconds=self.wall_seconds,
            inputs_sha256=self.checkpoint_inputs(), substitution=self.world_inputs,
            loaded=self.loaded, played_ms=self.played_ms, objects=rows,
            selected_loads=self.selected_loads, frames=self.frames,
            presentations=self.presentations[-3:], stop=self.stop,
            limitations=['Original4d2890 calls establish source-selected image draws; inspect original.png for visual layout.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wwd', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--play-ms', type=int, default=170)
    parser.add_argument('--instruction-limit', type=int, default=2_000_000_000)
    parser.add_argument('--wall-seconds', type=int, default=600)
    args = parser.parse_args()
    path = args.wwd.resolve()
    area = (ROOT/'work/test-levels').resolve()
    if not path.is_relative_to(area):
        parser.error('Generated WWD must remain under work/test-levels/')
    output = (args.output_dir or path.parent/'original').resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Evidence must remain under work/')
    if not 1 <= args.wall_seconds <= 3600:
        parser.error('--wall-seconds must be 1 through 3600')
    if not 17 <= args.play_ms <= 60000:
        parser.error('--play-ms must be 17 through 60000')
    data = path.read_bytes()
    manifest = json.loads((args.manifest or path.with_suffix('.json')).read_text())
    if manifest['output_sha256'] != sha(data):
        parser.error('WWD differs from generator manifest')
    output.mkdir(parents=True, exist_ok=True)
    trace = TestLevelTrace(wwd=data, manifest=manifest, evidence_dir=output,
        play_ms=args.play_ms, wall_seconds=args.wall_seconds, instruction_limit=args.instruction_limit, deny_platform=None)
    def interrupted(signum, _frame):
        raise Blocked(f'Original custom-scene interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary',
                address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.test_report()
    write_trace(output/'trace.json', report)
    print(json.dumps(dict(status=report['status'], loaded=report['loaded'],
        played_ms=report['played_ms'], objects=report['objects'], stop=report['stop'],
        output=str(output))), flush=True)
    return 0 if report['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
