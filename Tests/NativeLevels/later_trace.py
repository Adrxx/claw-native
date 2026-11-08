"""Level 13/14 discovery through original completion input and physical keys.

Loading starts at the retained original Level 12 observer. Each later start
checkpoint retains the preceding checkpoint hash and this runner's hash.
Navigation consumes JSON key commands; no player or world state is patched.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels import ROOT, output_dir
from Tests.NativeLevels.string_compare_trace import StringCompareTrace
from Tests.NativeLevels.trace import Blocked
from Tests.NativeLevels.storage import fingerprint, write_trace

RUNNER = 'Tests/NativeLevels/later_trace.py'


class LaterTrace(StringCompareTrace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # The poison-on-allocation observer retains twelve retired worlds.
        # Add physical storage only; allocation and free validation stay intact.
        self.machine.mem_map(0x50000000, 0x11000000)

    def play_target(self, application):
        self.destination = self.requested_destination
        self.heap_limit = 0x61000000
        source_level = self.target_level
        if source_level < self.destination:
            source = self.requested_source
            for level in range(source_level, self.destination):
                self.complete_level(application, level)
            self.target_level = self.destination
            self.later_advancement = dict(source_level=source_level,
                destination=self.destination, source_checkpoint=str(source.relative_to(ROOT)),
                source_sha256=fingerprint(source), runner=RUNNER,
                runner_sha256=hashlib.sha256((ROOT/RUNNER).read_bytes()).hexdigest())
            self.played_ms = 0
            self.resumed_checkpoint = False
            self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
            self.checkpoint_path = output_dir(self.target_level)/'start.checkpoint'
            self.save_checkpoint()
            self.checkpoint_path = None
        self.clock_step = 0
        self.loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.frames = [dict(elapsed_ms=0, action='loaded', player=first)]
        prefix = list(self.route)
        self.route = []
        print(json.dumps(dict(event='ready', elapsed_ms=0, player=first)), flush=True)
        while self.milliseconds-start < self.target_play_ms:
            elapsed = self.milliseconds-start
            if prefix:
                command = prefix.pop(0)
                end = command['end_ms']
            else:
                line = sys.stdin.readline()
                if not line:
                    raise Blocked('Navigation input closed before route complete')
                command = json.loads(line)
                if command.get('finish'):
                    break
                end = min(self.target_play_ms, elapsed+command['duration_ms'])
            action, keys = command['action'], command['keys']
            assert end > elapsed and set(keys) <= {0x25,0x26,0x27,0x28,0x20,0x11,0x12,0x10}
            self.route.append(dict(start_ms=elapsed, end_ms=end, action=action, keys=keys))
            while self.milliseconds-start < end:
                self.frame(application, f'level-{self.target_level}-'+action, keys)
                self.played_ms = self.milliseconds-start
                now = self.player_snapshot(application)
                if now['level'] != self.target_level:
                    raise Blocked('Original left target level')
                self.frames.append(dict(elapsed_ms=self.played_ms, action=action, player=now))
            self.route[-1]['end_ms'] = self.played_ms
            (output_dir(self.target_level)/'plan.json').write_text(json.dumps(self.route,indent=2)+'\n')
            print(json.dumps(dict(event='ready', elapsed_ms=self.played_ms, player=now)), flush=True)
        self.game_ms = (self.frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, f'level-{self.target_level}-played')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level', type=int, choices=(13,14), required=True)
    parser.add_argument('--source-level', type=int, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--play-ms', type=int, default=60000)
    args = parser.parse_args()
    out = output_dir(args.level)
    out.mkdir(parents=True,exist_ok=True)
    source = args.checkpoint.resolve()
    assert source.is_relative_to(ROOT/'work')
    LaterTrace.requested_destination = args.level
    LaterTrace.requested_source = source
    tracer = LaterTrace(level=args.source_level, destination=args.level, evidence_dir=out,
        instruction_limit=15_000_000_000, deny_platform=None,
        route=json.loads(args.plan.read_text()) if args.plan else [], play_ms=args.play_ms)
    tracer.discovery_source = source
    try:
        tracer.resume_target(source)
    except (Blocked,UcError) as error:
        if tracer.stop is None:
            tracer.stop = dict(kind='unsupported_boundary',
                address=hex(tracer.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        tracer.stop.update(phase=tracer.phase, last_transfer=tracer.last_transfer)
    finally:
        for stream in tracer.files.values():
            stream.close()
    report = tracer.report()
    report['later_advancement'] = getattr(tracer,'later_advancement',None)
    report['observer_checkpoint'] = dict(path=str(source.relative_to(ROOT)),
        sha256=fingerprint(source), inputs_sha256=tracer.checkpoint_inputs(),
        source_level=args.source_level, runner=RUNNER,
        runner_sha256=hashlib.sha256((ROOT/RUNNER).read_bytes()).hexdigest())
    report['string_compare_boundary'] = dict(adapter_sha256=hashlib.sha256(
        (ROOT/'Tests/NativeLevels/string_compare_fixture.py').read_bytes()).hexdigest())
    write_trace(out/'trace.json',report)
    (out/'plan.json').write_text(json.dumps(tracer.route,indent=2)+'\n')
    print(json.dumps(dict(event='result',status=report['status'],played_ms=tracer.played_ms,
        pickup=report['treasure_pickup_observed'],stop=report['stop'])),flush=True)
    return 0 if report['status']=='pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
