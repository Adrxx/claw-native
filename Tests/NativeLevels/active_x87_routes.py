"""Bounded native reachability for the three active x87 transport paths.

Run as Tests.NativeLevels.active_x87_routes --level {2,7,14}.
This runs actual canonical owners and stops after the named boundary returns.
Normal census and owner checks still apply. No original route is used as
comparison truth. Use active_x87_check for focused original/native comparisons
and native_join for route parity.
"""
import argparse
import hashlib
import json
from pathlib import Path

from Tests.NativeLevelOne.native_join import X87
from Tests.NativeMenuBase.trace import Blocked, ROOT

PATHS = {
    2: (0x4dc870, 0x48b0c0, 0x44c840, 0x43d490),
    7: (0x4dc830, 0x483ae0, 0x44df60, 0x483e10, 0x44e0c0,
        0x42df90, 0x40e690, 0x4dca10),
    14: (0x4dc870, 0x460af0, 0x44d000, 0x43e420),
}
STOP = 'Intentional stop after checked active x87 boundary returned'


def architectural(state):
    return dict(control=state.control, status=state.status,
                top=(state.status >> 11) & 7,
                live=[(v.significand, v.exponent) for v in state.slots[:state.count]])


def probe(level):
    path = PATHS[level]
    if level == 2:
        from Tests.NativeLevelTwo.native_join import LevelTwoNativeJoin as Base, build
        library, entries = build()
        options = {}
    else:
        from Tests.NativeLevels.native_join import build
        library, entries = build(level)
        route = json.loads((ROOT/f'work/level-{level}-map/plan.json').read_text())
        if level == 14:
            from Tests.NativeLevels.level_fourteen_join import Native as Base
            options = dict(route=route)
        else:
            from Tests.NativeLevels.native_join import LevelNativeJoin as Base
            options = dict(level=level, route=route)

    class Probe(Base):
        def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
            elected = (address == path[-1]
                       and tuple(self.native_functions[-len(path)+1:]) == path[:-1]
                       # source_ordinary re-enters this method without its
                       # packet; observe the outer checked source CALL only.
                       and (level != 2 or bool(source)))
            if elected:
                if level == 2:
                    if not source or return_pc != 0x44c94a:
                        raise Blocked('Missing checked source CALL in route probe')
                    live = self.x87_ambient
                else:
                    frame = self.x87_frames[-1]
                    if not frame['entered'] or frame['result'] is not None:
                        raise Blocked('Missing active method frame in route probe')
                    live = frame['ordinary_cursor']
                before = architectural(X87.from_buffer_copy(live))
            value = super().invoke(address, receiver, arguments, stack, source, return_pc)
            if elected:
                after = architectural(self.x87_ambient)
                if any(before[k] != after[k] for k in ('control', 'top', 'live')):
                    raise Blocked('Native route changed preserved x87 fields')
                self.witness = dict(path=[hex(a) for a in path], phase=self.phase,
                    incoming=before, outgoing=after,
                    source_continuation=hex(return_pc),
                    environment_calls=self.x87_environments[address])
                raise Blocked(STOP)
            return value

    native = Probe(library, entries, **options)
    error = None
    try:
        native.execute()
    except Blocked as failure:
        error = native.native_error or str(failure)
    finally:
        native.close()
    witness = getattr(native, 'witness', None)
    passed = witness is not None and error == STOP and witness['environment_calls'] > 0
    report = dict(status='boundary-crossed' if passed else 'blocked', level=level,
        error=error, witness=witness, guest_execution=False,
        original_route_validated=False, full_route_parity=False,
        inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__).resolve(),
                      ROOT/'Tests/NativeLevelOne/native_join.py', Path(library._name))})
    evidence = ROOT/f'work/native-active-x87-route-{level}.json'
    evidence.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    return 0 if passed else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level', required=True, type=int, choices=PATHS)
    level = parser.parse_args().level
    try:
        return probe(level)
    except Blocked as error:
        report = dict(status='blocked', level=level, error=str(error), witness=None,
                      original_route_validated=False, full_route_parity=False)
        (ROOT/f'work/native-active-x87-route-{level}.json').write_text(
            json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
