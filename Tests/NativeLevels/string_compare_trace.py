"""Replay an observer checkpoint with the additive checked CRT boundary.

The original loading/checkpoint and tempo-clock provenance remains mandatory.
An adapter pass proves only passage through the former unsupported service;
the ordinary route report retains its independent status and next stop.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP
from Tests.NativeLevels import ROOT
from Tests.NativeLevels.object_load_trace import ObjectLoadTrace
from Tests.NativeLevels.trace import LevelTrace, Blocked
from Tests.NativeLevels.storage import fingerprint, read_trace, write_trace
from Tests.NativeLevels.string_compare_fixture import StringCompareFixture, ENTRY


class StringCompareTrace(StringCompareFixture, ObjectLoadTrace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.string_comparisons = []

    def play_target(self, application):
        return LevelTrace.play_target(self, application)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--prior-trace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path,
        default=ROOT/'work/level-12-sign-discovery/level-11.checkpoint.gz')
    parser.add_argument('--play-ms', type=int)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'work'):
        parser.error('Derived evidence must remain under work/')
    route = json.loads(args.plan.read_text())
    prior = read_trace(args.prior_trace)
    checkpoint = args.checkpoint.resolve()
    checkpoint_sha = fingerprint(checkpoint)
    if (prior['level'] != 11 or prior['plan'] != route
            or prior['observer_checkpoint']['sha256'] != checkpoint_sha
            or prior['stop']['address'] != hex(ENTRY)):
        raise Blocked('Replay requires the retained Level 11 schedule and its original stopped checkpoint')
    trace = StringCompareTrace(level=11, destination=11, evidence_dir=checkpoint.parent,
        instruction_limit=15_000_000_000, deny_platform=None, route=route,
        play_ms=args.play_ms if args.play_ms is not None else route[-1]['end_ms'])
    if trace.checkpoint_inputs() != prior['observer_checkpoint']['inputs_sha256']:
        raise Blocked('Retained stopped trace has stale loading/clock/checkpoint inputs')
    try:
        trace.resume_target(checkpoint)
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary',
                address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    result['observer_checkpoint'] = dict(path=str(checkpoint.relative_to(ROOT)),
        sha256=checkpoint_sha, inputs_sha256=trace.checkpoint_inputs(),
        runner='Tests/NativeLevels/string_compare_trace.py',
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    prefix_matches = trace.frames[:len(prior['frames'])] == prior['frames']
    crossings = [event for event in trace.string_comparisons
                 if event['entry'] == hex(ENTRY) and event['continuation'] == '0x4319e8']
    passed = bool(prefix_matches and crossings and trace.played_ms > prior['played_ms'])
    result['string_compare_boundary'] = dict(status='pass' if passed else 'fail',
        scope='Original discovery service only; not complete route, native game or app parity',
        adapter_sha256=hashlib.sha256((ROOT/'Tests/NativeLevels/string_compare_fixture.py').read_bytes()).hexdigest(),
        prior_trace_sha256=fingerprint(args.prior_trace),
        plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
        prior_played_ms=prior['played_ms'], prior_frames=len(prior['frames']),
        prior_frame_prefix_matches=prefix_matches, conveyor_crossings=len(crossings),
        comparisons=trace.string_comparisons)
    written = write_trace(output, result)
    print(json.dumps(dict(boundary=result['string_compare_boundary']['status'],
        route_status=result['status'], played_ms=trace.played_ms,
        conveyor_crossings=len(crossings), prior_frame_prefix_matches=prefix_matches,
        stop=result['stop'], output=str(written))), flush=True)
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
