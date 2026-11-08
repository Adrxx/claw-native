"""BehindStatue finite binding transport against the hash-verified original."""
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESP
BASE, ALLOC = 0x10000000, 0x61000000
ACTOR, STATE, WORLD, REGISTRY, METADATA = [BASE + i * 0x1000 for i in (1, 2, 3, 4, 10)]
FRONT_ACTOR, FRONT_STATE = BASE + 0x5000, BASE + 0x6000
OWNERS = (0x4717b0, 0x471780, 0x471530, 0x4c7fa0, 0x4f63ec, 0x4c8160, 0x4c81b0)
BOUNDARIES = (0x4717d0, 0x4717d5, 0x4717a0, 0x4717a5, 0x4715a2, 0x4715a7, 0x4c7fbf, 0x4c7fc4, 0x4c7fcb, 0x4c7fd0, 0x4c7f4a, 0x4c7f4f, 0x4c7f40, 0x4c7f43, 0x4c7f94, 0x4c7f97)

class Reference:
    def __init__(self, label, mode='initialize', count=1, enabled=True, exhausted=False):
        self.label, self.mode, self.enabled, self.exhausted = label, mode, enabled, exhausted
        self.m = Machine(claw(), BASE, 0x10000)
        self.m.uc.mem_map(ALLOC, 0x10000)
        self.cursor, self.allocations = ALLOC, []
        self.events, self.calls, self.requests, self.binding_calls, self.boundaries = [], [], [], [], []
        self.frontier = None
        self.blocks = [(ACTOR, 0x200), (STATE, 0x200), (WORLD, 0x200), (REGISTRY, 0x200), (METADATA, 0x14), (0x513740, 0x28), (0x5228dc, 0x20), (0x52a194, 4), (0x510020, 4)]
        # Distinguishable inert bytes expose accidental offsets and over-writes.
        self.m.write(ACTOR, bytes((i * 17 + 3) % 256 for i in range(0x200)))
        self.m.write(STATE, bytes((i * 7 + 11) % 256 for i in range(0x200)))
        self.w(ACTOR + 4, 91, 0x140, WORLD)
        self.w(ACTOR + 0x64, 0); self.w(ACTOR + 0x6c, STATE, 0)
        self.w(ACTOR + 0x10c, count); self.w(ACTOR + 0x170, 0, 0)
        self.w(STATE + 0x10, 0x4717b0); self.w(STATE + 0x1c, 0)
        if mode == 'alternate':
            self.blocks += [(FRONT_ACTOR, 0x200), (FRONT_STATE, 0x200)]
            self.m.write(FRONT_ACTOR, self.m.read(ACTOR, 0x200))
            self.m.write(FRONT_STATE, self.m.read(STATE, 0x200))
            self.w(FRONT_ACTOR + 4, 173)
            self.w(FRONT_ACTOR + 0x6c, FRONT_STATE, 0)
            self.w(FRONT_ACTOR + 0x10c, 7)
            self.w(FRONT_STATE + 0x10, 0x471780)
        self.w(WORLD + 0x14, REGISTRY)
        self.w(METADATA, 11, 12, 13, 14, 0x4717e0)
        self.w(0x52a194, 77)
        for a in OWNERS: self.m.observe(a, self.observe)
        for a in BOUNDARIES: self.m.observe(a, lambda m, a: self.boundaries.append(a))
        for a in (0x4f6286, 0x4a48e0, 0x5022b5): self.m.intercept(a)
        self.m.on_external = self.external
        self.initial = self.snapshot(self.blocks)
    def w(self, a, *v): self.m.write(a, struct.pack('<' + 'I' * len(v), *(x & 0xffffffff for x in v)))
    def get(self, a): return self.m.words(a, 1)[0]
    def snapshot(self, spans): return [dict(address=a, data=self.m.read(a, n).hex()) for a, n in spans]
    def observe(self, m, a):
        receiver = m.register(UC_X86_REG_ECX) if a in (0x4c7fa0, 0x4c8160, 0x4c81b0) else 0
        self.calls.append([a, receiver])
        if a in (0x4c8160, 0x4c81b0):
            self.binding_calls.append([a, receiver, *m.words(m.register(UC_X86_REG_ESP) + 4, 2 if a == 0x4c8160 else 0)])
    def external(self, m, a):
        sp = m.register(UC_X86_REG_ESP); arg = lambda i: self.get(sp + 4 + i * 4)
        if a == 0x4f6286:
            receiver = m.register(UC_X86_REG_ECX)
            key = self.m.read(arg(0), 32).split(b'\0')[0].decode('ascii')
            assert receiver == REGISTRY + 16 and key == 'CrateHit'
            value = METADATA if self.enabled else 0
            self.w(arg(1), value)
            self.events.append(['registry', receiver, key, value]); m.return_from_external(int(value != 0), 8)
        elif a == 0x4a48e0:
            assert arg(0) == 0x174
            self.requests.append([a, self.get(sp), self.get(sp + 20), arg(0), m.register(UC_X86_REG_EBX)])
            value = 0 if self.exhausted else self.cursor
            if value:
                self.cursor += 0x180; self.allocations.append((value, 0x174)); self.m.write(value, bytes([204]) * 0x174)
            self.events.append(['malloc', value, 0x174]); m.return_from_external(value, 0)
        elif a == 0x5022b5:
            assert self.exhausted
            self.frontier = a; m.uc.emu_stop()
        else: raise AssertionError(hex(a))
    def profile(self):
        results, snapshots, completed = [], [], []
        steps = [(0x4717b0, ACTOR, STATE)] * (1 if self.mode == 'initialize' else 2)
        if self.mode == 'alternate':
            steps = [(0x4717b0, ACTOR, STATE), (0x471780, FRONT_ACTOR, FRONT_STATE)] * 2
        for iteration, (root, actor, state) in enumerate(steps):
            if iteration >= (2 if self.mode == 'alternate' else 1):
                token = self.get(actor + 0x70)
                if self.mode == 'retire':
                    self.allocations.remove((token, 0x174)); self.events.append(['release', token, 0x174]); self.w(actor + 0x70, 0)
                else:
                    self.w(token + 8, 77); self.w(token + 0x10, 0x4717e0)
                    self.w(token + 0x20, 123, 456, 789)
                    self.w(token + 0x168, 345, 678)
                self.w(state + 0x1c, 0)
            done = self.m.call(root, arguments=[actor])
            completed.append(done.completed)
            if done.completed: results.append(self.m.register(UC_X86_REG_EAX))
            else: assert self.exhausted and self.frontier == 0x5022b5, done
            if done.completed and root == 0x4717b0:
                assert (self.get(0x52a194), self.get(state + 0x54), self.get(state + 0x64)) == (2, 1, 0)
            spans = [(ACTOR, 0x200), (STATE, 0x200), (METADATA, 0x14), (0x52a194, 4)]
            if self.mode == 'alternate': spans += [(FRONT_ACTOR, 0x200), (FRONT_STATE, 0x200)]
            snapshots.append(self.snapshot(spans + self.allocations))
            if not done.completed: break
        return dict(label=self.label, mode=self.mode, steps=steps, enabled=self.enabled, exhausted=self.exhausted, initial=self.initial, results=results, completed=completed, snapshots=snapshots, events=self.events, calls=self.calls, requests=self.requests, binding_calls=self.binding_calls, boundaries=self.boundaries, frontier=self.frontier)

def prepare(out):
    profiles = [Reference('empty-secondary').profile(), Reference('multi-hit-count', count=4).profile(), Reference('high-count-flags', count=999).profile(), Reference('reset-and-rebind', 'rebind').profile(), Reference('owned-retirement-and-recreate', 'retire').profile(), Reference('lookup-miss', enabled=False).profile(), Reference('allocation-exhaustion', exhausted=True).profile(), Reference('alternating-behind-front-in-one-heap', 'alternate').profile()]
    out.mkdir(parents=True, exist_ok=True)
    (out / 'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256, profiles=profiles), indent=2) + '\n')
    print(json.dumps(dict(status='pass', original_profiles=len(profiles))))

def compare(out):
    ref, native = [json.loads((out / n).read_text()) for n in ('reference.json', 'native.json')]
    failures = []
    if len(ref['profiles']) != len(native['profiles']): failures.append('profile count')
    for r, n in zip(ref['profiles'], native['profiles']):
        for key in ('label', 'results', 'completed', 'snapshots', 'events', 'requests', 'binding_calls', 'frontier'):
            if r[key] != n[key]: failures.append(dict(label=r['label'], field=key))
        actual_calls = [c for c in n['calls'] if c[0] in OWNERS]
        if r['calls'] != actual_calls: failures.append(dict(label=r['label'], field='ordered canonical owners', expected=r['calls'], actual=actual_calls))
        if r['enabled'] and not r['exhausted']:
            expected = []
            for iteration, (root, _, _) in enumerate(r['steps']):
                start, end = (0x4717d0, 0x4717d5) if root == 0x4717b0 else (0x4717a0, 0x4717a5)
                path = [start, 0x4715a2, 0x4c7fbf, 0x4c7fc4, 0x4c7fcb, 0x4c7f4a, 0x4c7f4f, 0x4c7f94, 0x4c7f97, 0x4c7fd0, 0x4715a7, end]
                if (r['mode'] == 'rebind' and iteration) or (r['mode'] == 'alternate' and iteration >= 2):
                    path[5:7] = [0x4c7f40, 0x4c7f43]
                expected += path
            if r['boundaries'] != expected: failures.append(dict(label=r['label'], field='original CALL and continuation witnesses'))
    controls = native['controls']
    if len(controls) < 35: failures.append('missing ownership controls')
    for c in controls:
        if not c['passed']: failures.append(dict(control=c['name']))
    result = dict(status='fail' if failures else 'pass', profiles=len(ref['profiles']), controls=len(controls), failures=failures)
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))
    return bool(failures)

def main():
    out = Path(sys.argv[2]).resolve()
    if (ROOT / 'work').resolve() not in out.parents: raise ValueError('evidence belongs under ignored work/')
    if sys.argv[1] == 'prepare': prepare(out)
    elif sys.argv[1] == 'compare': return compare(out)
    else: raise ValueError(sys.argv[1])
if __name__ == '__main__': raise SystemExit(main())
