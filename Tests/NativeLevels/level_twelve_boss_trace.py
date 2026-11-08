"""Original Aquatis combat, coordinate-only placements, MPSCULLY and Level 13."""
import argparse
import hashlib
import json
import signal
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels.string_compare_trace import StringCompareTrace
from Tests.NativeLevels.trace import LevelTrace
from Tests.NativeLevelTwo.boss_trace import BossTrace, validate_plan
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, LETTERS
from Tests.NativeLevels.storage import write_trace, fingerprint
from Tests.NativeLevels import ROOT
from Tests.NativeMenuBase.trace import Blocked


class AquatisTrace(StringCompareTrace):
    HEAP_EXTENSION_MIB = (0, 64, 128, 256)

    def __init__(self, *, boss_plan, fight_only=False, heap_extension_mib=128, **kwargs):
        if heap_extension_mib not in self.HEAP_EXTENSION_MIB:
            raise Blocked('Unsupported Aquatis fixture heap extension')
        super().__init__(level=12, destination=13, evidence_dir=ROOT/'work/level-twelve-boss',
                         route=boss_plan, **kwargs)
        self.boss_plan = boss_plan
        self.fight_only = fight_only
        self.heap_extension_mib = heap_extension_mib
        self.fixture_heap = None
        self.boss_actor_seen = 0
        self.boss_frames = []
        self.next_frames = []
        self.boss_cheat_keys = []
        self.boss_route_functions = {}
        self.boss_route_complete = False

    def complete_level(self, application, level):
        LevelTrace.complete_level(self, application, level)

    def boss_snapshot(self):
        private = self.word(0x534874)
        if private and private in self.allocations:
            self.boss_actor_seen = self.word(private+0xc)
        result = BossTrace.boss_snapshot(self)
        if private and private in self.allocations:
            result['mechanism'] = {hex(o): self.word(private+o) for o in
                (0x4a8, 0x4b4, 0x4b8, 0x4bc, 0x4c0, 0x4c4, 0x4c8, 0x4ec)}
        return result

    def play_target(self, application):
        # resume_target has already verified the unchanged checkpoint inputs and
        # restored its memory and allocator state. Extend only unused physical
        # storage: never reset the bump pointer or recycle retired allocations.
        # The upper bound stays below the existing arena at 0x60000000 and the
        # fixture code at 0x70000000. Allocation limits and poison stay inherited.
        if self.heap_limit != 0x50000000 or not 0x30000000 <= self.heap_next < self.heap_limit:
            raise Blocked('Unexpected Aquatis checkpoint fixture heap')
        previous_limit = self.heap_limit
        extension = self.heap_extension_mib * 1024 * 1024
        if extension:
            self.machine.mem_map(previous_limit, extension)
            self.heap_limit += extension
        self.fixture_heap = dict(extension_mib=self.heap_extension_mib,
            checkpoint_next=hex(self.heap_next), checkpoint_limit=hex(previous_limit),
            limit=hex(self.heap_limit))
        print(json.dumps(dict(event='fixture-heap', **self.fixture_heap)), flush=True)
        self.clock_step = 0
        start = self.milliseconds
        self.boss_frames = [dict(elapsed_ms=0, action='loaded', player=self.player_snapshot(application), boss=self.boss_snapshot())]
        before_functions = self.functions.copy()
        placed, cheats = set(), {}
        while self.milliseconds-start < self.boss_plan[-1]['end_ms']:
            elapsed = self.milliseconds-start
            index, action = next((i,a) for i,a in enumerate(self.boss_plan) if a['start_ms'] <= elapsed < a['end_ms'])
            if 'set_x' in action and index not in placed:
                placed.add(index)
                actor = self.word(0x537e88)
                self.put(actor+0x4c, action['set_x']); self.put(actor+0x50, action['set_y'])
            before = len(self.presentations)
            if action.get('cheat'):
                if action['cheat'] != 'MPKFA': raise Blocked('Only MPKFA assistance is permitted')
                progress = cheats.get(index, 0)
                if progress < 5:
                    letter = 'MPKFA'[progress]
                    vk, scan = dict(LETTERS, K=(0x4b,0x25), F=(0x46,0x21), A=(0x41,0x1e))[letter]
                    phase = f"boss-cheat-{action['start_ms']}-{progress}-{letter}"
                    self.deliver_key(application, vk, scan, phase)
                    self.boss_cheat_keys.append(dict(letter=letter, phase=phase))
                    cheats[index] = progress+1
            self.frame(application, 'level-12-boss-'+action['action'], action['keys'])
            player = self.player_snapshot(application)
            if player['level'] != 12: raise Blocked('Boss route left Level 12 before completion')
            self.boss_frames.append(dict(elapsed_ms=self.milliseconds-start, action=action['action'], player=player,
                boss=self.boss_snapshot(), presentation_start=before, presentation_count=len(self.presentations)-before))
            if len(self.boss_frames)%120 == 0:
                print(json.dumps(dict(event='boss-frame', **self.boss_frames[-1])), flush=True)
        self.boss_route_functions = {hex(a):n-before_functions[a] for a,n in self.functions.items() if n>before_functions[a]}
        if not self.fight_only:
            self.complete_level(application, 12)
            self.clock_step = 0
            for index in range(10):
                before = len(self.presentations)
                self.frame(application, 'level-thirteen-stand')
                player = self.player_snapshot(application)
                if player['level'] != 13: raise Blocked('Completion did not reach Level 13')
                self.next_frames.append(dict(index=index, player=player, presentation_start=before,
                    presentation_count=len(self.presentations)-before))
        self.boss_route_complete = True

    def report(self):
        result = EndOfLevelTrace.report(self)
        result.update(scope='Original Aquatis combat and Level 13; app integration reference',
            tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            adapter_inputs={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                ('Tests/NativeLevels/string_compare_fixture.py', 'Tests/NativeLevels/string_compare_trace.py',
                 'Tests/NativeLevelTwo/boss_trace.py')}, plan=self.boss_plan,
            boss_frames=self.boss_frames, next_frames=self.next_frames, boss_cheat_keys=self.boss_cheat_keys,
            boss_route_functions=self.boss_route_functions, fight_only=self.fight_only,
            fixture_heap=dict(self.fixture_heap, final_next=hex(self.heap_next)) if self.fixture_heap else None,
            status='pass' if self.stop is None and self.boss_route_complete else 'blocked')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, default=ROOT/'work/level-12-sign-discovery/level-12.checkpoint.gz')
    parser.add_argument('--fight-only', action='store_true')
    parser.add_argument('--paper-startup', action='store_true')
    parser.add_argument('--heap-extension-mib', type=int, choices=AquatisTrace.HEAP_EXTENSION_MIB,
        default=128, help='Bounded extra fixture storage after checkpoint validation (default: 128 MiB; 0 retains the old bound)')
    args = parser.parse_args()
    for path in (args.output, args.checkpoint):
        if not path.resolve().is_relative_to(ROOT/'work'): parser.error('Derived artifacts must stay under work/')
    plan = json.loads(args.plan.read_text()); validate_plan(plan)
    trace = AquatisTrace(boss_plan=plan, fight_only=args.fight_only, heap_extension_mib=args.heap_extension_mib,
        instruction_limit=15_000_000_000, deny_platform=None, startup_paper=args.paper_startup)
    def interrupted(signum, frame):
        raise Blocked("Reference interrupted; partial evidence only")
    previous = signal.signal(signal.SIGINT, interrupted)
    try:
        trace.resume_target(args.checkpoint.resolve())
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        signal.signal(signal.SIGINT, previous)
        for stream in trace.files.values(): stream.close()
    result = trace.report()
    result['observer_checkpoint'] = dict(path=str(args.checkpoint.resolve().relative_to(ROOT)),
        sha256=fingerprint(args.checkpoint), inputs_sha256=trace.checkpoint_inputs())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(args.output, result)
    print(json.dumps(dict(status=result['status'], stop=result['stop'], boss_frames=len(trace.boss_frames), output=str(output))), flush=True)
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
