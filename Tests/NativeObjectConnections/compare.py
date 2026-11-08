"""Selected connection runner. Original-derived evidence stays under work/.

Modes (each prints one JSON line last):
  elections               every elected family, adapter class and callbacks
  adapters                elected native adapter Swift files that exist
  resolve FAMILY          the selected family's files; exit 2 if unelected,
                          exit 3 with the missing files if not implemented
  prepare FAMILY          bridge-control inputs, then FAMILY's prepare(directory)
  compare FAMILY          bridge controls, then FAMILY's compare(directory)

A consumer family supplies Sources/<adapter>.swift (an @objc(<adapter>)
ClawNativeObjectAdapter subclass), Tests/NativeObjectConnections/<family>.swift
(defining runConnection(_ directory: URL) throws) and
Tests/NativeObjectConnections/<family>.py (defining prepare(directory) and
compare(directory) -> result fields).
"""
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BRIDGE = ROOT / 'Sources/ClawNativeObjectConnections.swift'
TESTS = ROOT / 'Tests/NativeObjectConnections'
ELECTION = re.compile(r'Election\(family: "(\w+)", adapter: "(\w+)", callbacks: \[([0-9a-fx, ]+)\]\)')
REQUIRED_RESULT = ('original_callback', 'native_owner', 'comparisons', 'exercised_service_edges',
                   'controls', 'faults', 'unresolved_dependencies')


def elections():
    """The explicit election table in the Swift bridge is the only source."""
    text = BRIDGE.read_text()
    body = text[text.index('static let elections'):text.index('static func resolve')]
    found = {family: dict(family=family, adapter=adapter,
                          callbacks=[c.strip() for c in callbacks.split(',')])
             for family, adapter, callbacks in ELECTION.findall(body)}
    if len(found) != len(ELECTION.findall(body)):
        raise SystemExit('Duplicate family election')
    return found


def files(election):
    family = election['family']
    return [f"Sources/{election['adapter']}.swift",
            f'Tests/NativeObjectConnections/{family}.swift',
            f'Tests/NativeObjectConnections/{family}.py']


def resolve(family):
    table = elections()
    if family not in table:
        print(json.dumps(dict(command='native-object-connection', family=family, status='unelected')))
        raise SystemExit(2)
    paths = files(table[family])
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        print(json.dumps(dict(command='native-object-connection', family=family,
                              status='missing-implementation', missing=missing)))
        raise SystemExit(3)
    print('\n'.join(paths[:2]))


def bridge_controls(directory):
    controls = json.loads((directory / 'bridge-controls.json').read_text())['controls']
    expected = {'adapter_dispatch_and_teardown', 'canonical_precedence', 'duplicate_callback_rejected',
                'scene_owner_callback_not_displaced', 'unknown_callback_rejected', 'unowned_actor_rejected',
                'missing_implementation_reported', 'missing_service_fault'}
    if set(controls) != expected or not all(controls.values()):
        raise AssertionError(f'Bridge controls failed: {controls}')
    return controls


def main():
    mode, family = (sys.argv[1:] + [''])[:2]
    if mode == 'elections':
        print(json.dumps(list(elections().values())))
        return
    if mode == 'adapters':
        print('\n'.join(f"Sources/{e['adapter']}.swift" for e in elections().values()
                        if (ROOT / 'Sources' / f"{e['adapter']}.swift").is_file()))
        return
    if mode == 'resolve':
        resolve(family)
        return
    if mode not in ('prepare', 'compare') or family not in elections():
        raise SystemExit('Unelected connection or operation')
    directory = ROOT / 'work/native-object-connections' / family
    directory.mkdir(parents=True, exist_ok=True)
    module = importlib.import_module(f'Tests.NativeObjectConnections.{family}')
    if mode == 'prepare':
        importlib.import_module('Tests.NativeObjectConnections.ani_cycle').prepare(directory)
        module.prepare(directory)
        return
    controls = bridge_controls(directory)
    fields = module.compare(directory)
    missing = [key for key in REQUIRED_RESULT if key not in fields]
    assert not missing, f'Comparison result lacks {missing}'
    assert fields['comparisons'] > 0 and fields['controls'] and all(fields['controls'].values())
    assert fields['faults'] == 0 and not fields['unresolved_dependencies']
    result = dict(command='native-object-connection', family=family, status='pass', **fields,
                  bridge_controls=controls)
    (directory / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
