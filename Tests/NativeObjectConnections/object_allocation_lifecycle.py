"""Original constructor comparison for the opt-in native scene storage profile."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.NativeObjectConnections import boss_warp_transport as transport
from Tests.clawparity.program import claw

class SceneReference(transport.Reference):
    def external(self, machine, address):
        super().external(machine, address)
        # The physical allocator reserves snapshot storage, while malloc still
        # observes the original requested extent and constructor identity.
        if address == 0x4a48e0:
            token, requested = self.allocations[-1]
            if requested == 0x1b4:
                self.next_alloc = token + 512

def prepare(directory):
    transport.ALLOC = 0x65000000
    profiles = [SceneReference('health', flags=flags).run(label)
                for label, flags in [('scene-deferred', 0), ('scene-initialized', 0x240000)]]
    result = dict(version=1, executable_sha256=claw().sha256, profiles=profiles)
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status='pass', original_profiles=len(profiles))))

def compare(directory):
    reference = json.loads((directory/'reference.json').read_text())
    native = json.loads((directory/'native.json').read_text())
    failures = []
    if reference['executable_sha256'] != claw().sha256:
        failures.append('reference executable hash')
    if len(reference['profiles']) != len(native['profiles']):
        failures.append('profile count')
    for expected, actual in zip(reference['profiles'], native['profiles']):
        for field in ('label', 'results', 'requests', 'events', 'final'):
            if expected[field] != actual[field]:
                failures.append(dict(profile=expected['label'], field=field))
        if expected['allocations'] != [[0x65000000, 0x1b4], [0x65000200, 0x174]]:
            failures.append(dict(profile=expected['label'], field='allocation identities'))
        if not all(c['completed'] for c in actual['completions']):
            failures.append(dict(profile=expected['label'], field='construction completion'))
    for control in native['controls']:
        if not control['passed']:
            failures.append(dict(control=control['name']))
    result = dict(status='fail' if failures else 'pass', profiles=len(reference['profiles']),
                  controls=len(native['controls']), failures=failures,
                  original='0x4c8da0 -> 0x4f63ec -> 0x4a48e0',
                  native_owner='ClawNativeMfcMemory / ClawNativeScene shared ClawTokenHeap')
    (directory/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return bool(failures)

if __name__ == '__main__':
    directory = Path(sys.argv[2]).resolve()
    if (ROOT/'work').resolve() not in directory.parents:
        raise ValueError('Evidence must stay under work/')
    if sys.argv[1] == 'prepare':
        prepare(directory)
    elif sys.argv[1] == 'compare':
        raise SystemExit(compare(directory))
    else:
        raise ValueError(sys.argv[1])
