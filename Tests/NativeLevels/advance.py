"""Advance a hash-validated original start checkpoint through ordinary completion input.

This only avoids replaying the earlier prefix. LevelTrace.resume_target validates
its source level, tracer inputs and REZ before restoring the original CPU/memory.
Each subsequent level uses the existing MPSCULLY/results transition, and the
ordinary tracer saves the destination checkpoint and runs its physical route.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from Tests.NativeLevels import ROOT, add_level, output_dir
from Tests.NativeLevels.storage import exists, fingerprint, write_trace
from Tests.NativeLevels.trace import LevelTrace, Blocked
from Tests.NativeLevels.xmidi_clock import TempoClockTrace


class AdvanceTrace(TempoClockTrace):
    def __init__(self, *, source_level, destination, source_checkpoint, **kwargs):
        super().__init__(level=source_level, **kwargs)
        self.destination = destination
        self.advancement = dict(source_level=source_level, destination=destination,
            source_checkpoint=str(source_checkpoint.relative_to(ROOT)),
            source_sha256=fingerprint(source_checkpoint),
            runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    def play_target(self, application):
        destination, advancement = self.destination, self.advancement
        for level in range(self.target_level, destination):
            self.complete_level(application, level)
        self.target_level = destination
        self.advancement = advancement
        # The destination starts a new ordinary checkpoint; the restored source
        # checkpoint already carries all earlier original input and transitions.
        self.resumed_checkpoint = False
        super().play_target(application)

    def report(self):
        result = super().report()
        result['checkpoint_advancement'] = self.advancement
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_level(parser)
    parser.add_argument('--full-prefix', action='store_true',
        help='Replay startup and every earlier level with the same validated clock; restore no checkpoint')
    parser.add_argument('--from-level', type=int)
    parser.add_argument('--source-checkpoint', type=Path)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--play-ms', type=int, default=60000)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--instruction-limit', type=int, default=15_000_000_000)
    args = parser.parse_args()
    if not args.full_prefix and (args.from_level is None or args.source_checkpoint is None or args.checkpoint is None):
        parser.error('Advancement requires --from-level, --source-checkpoint and --checkpoint')
    if args.full_prefix and any(p is not None for p in (args.from_level, args.source_checkpoint, args.checkpoint)):
        parser.error('--full-prefix cannot restore or create advancement checkpoints')
    if not args.full_prefix and not 2 <= args.from_level < args.level:
        parser.error('The destination must follow the source level')
    output = (args.output or output_dir(args.level)/'trace.json').resolve()
    source = args.source_checkpoint.resolve() if args.source_checkpoint else None
    target = args.checkpoint.resolve() if args.checkpoint else None
    if not all(p.is_relative_to(ROOT/'work') for p in (source, target, output) if p is not None):
        parser.error('Derived artifacts must stay under work/')
    output.parent.mkdir(parents=True, exist_ok=True)
    options = dict(instruction_limit=args.instruction_limit, deny_platform=None,
        route=json.loads(args.plan.read_text()), play_ms=args.play_ms, checkpoint=target)
    if args.full_prefix:
        trace = TempoClockTrace(level=args.level, **options)
        resume = None
    elif exists(target):
        trace_type = TempoClockTrace if args.level >= 10 else LevelTrace
        trace = trace_type(level=args.level, **options)
        resume = target
    else:
        trace = AdvanceTrace(source_level=args.from_level, destination=args.level,
            source_checkpoint=source, **options)
        resume = source
    try:
        if resume is None:
            trace.execute()
        else:
            trace.resume_target(resume)
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(reason=str(error), phase=trace.phase)
    report = trace.report()
    if args.full_prefix:
        report['full_prefix_runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    else:
        report['checkpoint_advancement'] = trace.advancement
    write_trace(output, report)
    print(json.dumps(dict(status=report['status'], level=trace.target_level,
        played_ms=report['played_ms'], stop=report['stop'])))
    return 0 if report['status']=='pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
