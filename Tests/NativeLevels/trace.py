"""Trace original level loading via MPSCULLY/results and 60 seconds of physical input."""
import argparse
from Tests.NativeLevels.storage import exists, fingerprint, load_checkpoint, restore_memory, save_checkpoint, write_trace
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels import ROOT, add_level, output_dir
from Tests.NativeLevelTwo.trace import LevelTwoTrace, Blocked
from Tests.NativeLevels.routes import route_for
from Tests.NativeLevels.grid_fixture import LargeGridFixture
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, SINGLE_PLAYER_VTABLE, CHEAT, LETTERS
from Tests.NativeEndOfLevel import trace as end_trace


class LevelTrace(LargeGridFixture, LevelTwoTrace):
    def __init__(self, *args, level, route=None, play_ms=60000, checkpoint=None, **kwargs):
        super().__init__(*args, level_two_ms=60000, **kwargs)
        if level >= 4:
            # The poison-on-allocation bump heap retains retired storage across
            # level transitions. Four original worlds exceed the Level 1 bound;
            # extend physical storage, preserving allocation/free validation.
            self.machine.mem_map(0x69000000, 0x6000000)
            self.heap_limit = 0x6f000000
        if level >= 6:
            # Six retained worlds exceed that arena. Keep the fixture's code
            # page at 0x70000000 separate and use a bounded lower arena instead.
            self.machine.mem_map(0x30000000, 0x20000000)
            self.heap_next = 0x30000000
            self.heap_limit = 0x50000000
        self.target_level = level
        self.route = route if route is not None else route_for(level)
        self.routes_fingerprint = hashlib.sha256((ROOT/"Tests/NativeLevels/routes.py").read_bytes()).hexdigest()
        self.target_play_ms = play_ms
        self.target_checkpoint = checkpoint
        self.loaded = False
        self.frames = []
        self.played_ms = self.game_ms = 0
        self.completions = []
        self.generic_fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def level_two(self, application):
        # The existing Level 1 completion method calls here after its results.
        current = 2
        while current < self.target_level:
            self.complete_level(application, current)
            current += 1
        if self.target_level == 2:
            return super().level_two(application)
        self.play_target(application)

    def results(self, application):
        if self.target_level == 2:
            return super().results(application)
        self.advance_results(application, 1)
        self.level_two(application)

    def complete_level(self, application, level):
        self.clock_step = 1
        before = len(self.cheat_keys)
        self.level_complete_posted = False
        for index, letter in enumerate(CHEAT):
            vk, scan = LETTERS[letter]
            phase = f'advance-level-{level}-cheat-{index}-{letter}'
            self.deliver_key(application, vk, scan, phase)
            self.cheat_keys.append(dict(letter=letter, key=vk, level=level, milliseconds=self.milliseconds,
                                       game_ms=self.word(0x537208)))
            self.frame(application, phase+'-frame')
        if not self.level_complete_posted:
            raise Blocked(f'Original did not post completion for Level {level}')
        elapsed = self.advance_results(application, level)
        self.completions.append(dict(level=level, next_level=level+1,
            cheat=''.join(k['letter'] for k in self.cheat_keys[before:]),
            posted=True, elapsed_ms=elapsed))

    def advance_results(self, application, level):
        start = self.milliseconds
        waiting_object = None
        while self.milliseconds-start < self.results_limit_ms:
            entry = self.state_snapshot(application, f'level-{level}-results')
            if entry['vtable'] == hex(SINGLE_PLAYER_VTABLE):
                if entry.get('level') == level+1:
                    return self.milliseconds-start
                if entry.get('level') != level:
                    raise Blocked(f'Unexpected level during Level {level} results: {entry}')
            if entry['object'] != waiting_object:
                waiting_object, waiting_since = entry['object'], self.milliseconds
            elif self.milliseconds-waiting_since >= 1000:
                # Ordinary player input advances the results as soon as the
                # original accepts it; no state, counters or timers are patched.
                self.deliver_key(application, 13, 0x1c, f'level-{level}-results-return')
                waiting_since = self.milliseconds
            self.frame(application, f'level-{level}-results-'+entry['vtable'])
        raise Blocked(f'Level {level} results did not advance')

    def checkpoint_inputs(self):
        return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
            'Tests/NativeLevels/trace.py', 'Tests/NativeLevels/grid_fixture.py',
            'Tests/NativeLevelTwo/trace.py',
            'Tests/NativeEndOfLevel/trace.py', 'Tests/NativeLevelOne/trace.py',
            'Tests/NativeMenuBase/trace.py', 'Tests/NativeLevels/storage.py')}

    def resume_target(self, path):
        payload = load_checkpoint(path)
        state = payload['state']
        self.validate_checkpoint_profile(state)
        if state.get('checkpoint_inputs_sha256') != self.checkpoint_inputs():
            raise Blocked('Stale target-level checkpoint')
        if state['target_level'] != self.target_level or state['played_ms'] != 0:
            raise Blocked('Checkpoint is not at the requested level start')
        with end_trace.REZ_PATH.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != end_trace.REZ_SHA256:
                raise Blocked('Original archive hash mismatch')
        keep = {k: getattr(self, k) for k in ('route', 'target_play_ms', 'target_checkpoint', 'instruction_limit')}
        self.__dict__.update(state)
        self.__dict__.update(keep)
        self.resumed_checkpoint = True
        restore_memory(path, self.machine)
        registers = (end_trace.UC_X86_REG_EAX, end_trace.UC_X86_REG_EBX, end_trace.UC_X86_REG_ECX,
            end_trace.UC_X86_REG_EDX, end_trace.UC_X86_REG_ESI, end_trace.UC_X86_REG_EDI,
            end_trace.UC_X86_REG_EBP, end_trace.UC_X86_REG_ESP, end_trace.UC_X86_REG_EIP,
            end_trace.UC_X86_REG_EFLAGS, end_trace.UC_X86_REG_FPCW, end_trace.UC_X86_REG_FPSW,
            end_trace.UC_X86_REG_FPTAG)
        for register, value in zip(registers, payload['cpu']):
            self.machine.reg_write(register, value)
        for index, value in enumerate(payload['cpu'][len(registers):]):
            self.machine.reg_write(end_trace.UC_X86_REG_FP0+index, value)
        for handle, (name, position) in payload['files'].items():
            if Path(name).resolve() != end_trace.REZ_PATH.resolve():
                raise Blocked('Unexpected checkpoint file')
            self.files[handle] = open(name, 'rb')
            self.files[handle].seek(position)
        self.prefix_checkpoint_sha256 = fingerprint(path)
        self.parent_checkpoint = dict(path=str(path), sha256=self.prefix_checkpoint_sha256,
            startup_profile=self.startup_profile)
        self.play_target(self.application)

    def play_target(self, application):
        if self.target_checkpoint and not self.resumed_checkpoint:
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = self.target_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        self.clock_step = 0
        self.loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.frames = [dict(elapsed_ms=0, action='loaded', player=first)]
        while self.milliseconds-start < self.target_play_ms:
            elapsed = self.milliseconds-start
            action = next(a for a in self.route if a['start_ms'] <= elapsed < a['end_ms'])
            self.frame(application, f'level-{self.target_level}-'+action['action'], action['keys'])
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != self.target_level:
                raise Blocked(f'Original left Level {self.target_level} play')
            self.played_ms = self.milliseconds-start
            self.frames.append(dict(elapsed_ms=self.played_ms, action=action['action'],
                                    player=self.player_snapshot(application)))
            if len(self.frames) % 120 == 0:
                print(json.dumps(dict(event=f'level-{self.target_level}', **self.frames[-1])), flush=True)
        self.game_ms = (self.frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, f'level-{self.target_level}-played')

    def report(self):
        if self.target_level == 2:
            result = super().report()
        else:
            result = EndOfLevelTrace.report(self)
            pickup = any(e['increment'] > 0 and e['phase'].startswith(f'level-{self.target_level}-')
                         for e in self.pickup_events)
            result.update(scope=f'Original Level {self.target_level} loading and 60000 ms physical input census; discovery only',
                loaded=self.loaded, played_ms=self.played_ms, game_ms=self.game_ms, frames=self.frames,
                plan=self.route, prefix_checkpoint_sha256=getattr(self, "prefix_checkpoint_sha256", None), treasure_pickup_observed=pickup, completions=self.completions)
            result['status'] = 'pass' if self.stop is None and self.played_ms >= 60000 and pickup else 'blocked'
        result.update(level=self.target_level, generic_tracer_sha256=self.generic_fingerprint,
                      routes_sha256=self.routes_fingerprint,
                      large_grid_fixture_sha256=hashlib.sha256((ROOT/'Tests/NativeLevels/grid_fixture.py').read_bytes()).hexdigest(),
                      provider_tracer_sha256=hashlib.sha256((ROOT/'Tests/NativeLevelTwo/trace.py').read_bytes()).hexdigest())
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_level(parser)
    parser.add_argument('--instruction-limit', type=int, default=15_000_000_000)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan', type=Path, help='Physical input schedule JSON')
    parser.add_argument('--play-ms', type=int, default=60000, help='Shorter diagnostic runs remain blocked')
    parser.add_argument('--checkpoint', type=Path, help='Local target-start cache; resume if present')
    parser.add_argument('--paper-startup', action='store_true')
    args = parser.parse_args()
    output = (args.output or output_dir(args.level)/'trace.json').resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived output must stay under work/')
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.checkpoint and not args.checkpoint.resolve().is_relative_to((ROOT/'work').resolve()):
        parser.error('Checkpoint must stay under work/')
    route = json.loads(args.plan.read_text()) if args.plan else None
    trace = LevelTrace(args.instruction_limit, None, level=args.level, route=route,
                       play_ms=args.play_ms, checkpoint=args.checkpoint, startup_paper=args.paper_startup)
    try:
        if args.checkpoint and exists(args.checkpoint):
            trace.resume_target(args.checkpoint)
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    output = write_trace(output, result)
    print(json.dumps(dict(status=result['status'], counts=result['counts'], stop=result['stop'],
        played_ms=result.get('played_ms',result['level_two_played_ms']), output=str(output))), flush=True)
    return 0 if result['status']=='pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
