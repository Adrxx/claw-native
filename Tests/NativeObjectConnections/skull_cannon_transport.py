"""SkullCannon original/native shared-owner transport; no scene promotion."""
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP
BASE, SIZE, ALLOC = 0x10000000, 0x10000, 0x61000000
ACTOR, STATE, WORLD, REGISTRY, IMAGES, ANIMATIONS, TABLE, METHODS, STRING = [BASE + i * 0x1000 for i in range(1, 10)]
HOME, FIRING, IMAGESET = BASE+0xc000, BASE+0xd000, BASE+0xe000
OBSERVE = (0x484d90, 0x4f6428, 0x414030, 0x4f63ec, 0x48a8c0, 0x4c7fa0, 0x4c8060, 0x4c7970, 0x4145b0, 0x4dba00, 0x4c8220, 0x4c96b0, 0x4dc870, 0x4c9e30, 0x4141f0, 0x4145f0, 0x4146b0, 0x4148b0, 0x4041b0, 0x4db6e0)
BOUNDARIES = (0x48a835, 0x48a83a, 0x48a850, 0x48a855, 0x4dc93a, 0x4dc93d, 0x4dc943, 0x4dc946, 0x4142b7, 0x4142b9, 0x4dc9fa, 0x4dc9fd)

CALLBACK_BOUNDARIES = (0x48a867, 0x48a86a, 0x48a874, 0x48a877, 0x48a898, 0x48a89b, 0x48a889, 0x48a88e)

class Reference:
    def __init__(self, label, method, timeout=False, vertical=False, growth=False, exhausted=False):
        self.label, self.method, self.timeout, self.vertical = label, method, timeout, vertical
        self.growth, self.exhausted = growth, exhausted
        self.m = Machine(claw(), BASE, SIZE)
        self.m.uc.mem_map(ALLOC, 0x10000)
        self.events, self.calls, self.boundaries, self.requests, self.contexts = [], [], [], [], []
        self.callback_boundaries = []
        self.blocks = [(a, 0x200) for a in (ACTOR, STATE, WORLD, REGISTRY, IMAGES, ANIMATIONS, TABLE, METHODS, STRING)]
        self.blocks += [(HOME,0x200),(FIRING,0x200),(IMAGESET,0x200)]
        self.blocks += [(0x50fa64, 0x24), (0x50f744, 0x24), (0x50b9c4, 4), (0x510020, 4), (0x534bf8, 0x30), (0x537668, 0x60), (0x537210, 4), (0x5430c4, 4)]
        self.blocks += [(a, 0x30) for a in (0x522d48, 0x5234ec, 0x524538)]
        self.blocks += [(0x52c22c, 0x80)]
        self.w(ACTOR + 0xc, WORLD); self.w(ACTOR + 0x6c, STATE); self.w(STATE + 0x10, 0x48a800)
        self.w(WORLD + 0x10, IMAGES, REGISTRY); self.w(WORLD + 0x2c, ANIMATIONS)
        self.w(0x537668, *([0] * 12)); self.w(0x537698, 0, 0, 0, 63, TABLE, 0, 4, 0, 0, 0, 0, 0)
        self.w(0x534bf8, 0, 0, 0, 63, METHODS, 0, 4, 0, 0, 0, 0, 0)
        for i in range(64): self.w(TABLE + i * 4, STRING + 12); self.w(METHODS + i * 4, method)
        self.w(STRING,1,7,7);self.m.write(STRING+12,b'LS_HOME\0')
        self.w(STRING+0x40,1,9,9);self.m.write(STRING+0x4c,b'LS_FIRING\0')
        self.w(TABLE+8*4,STRING+0x4c);self.w(METHODS+7*4,0x4145f0);self.w(METHODS+8*4,0x4146b0)
        self.w(STRING+0x100,STRING+0x100,STRING+0x120,25,0x5234ec,7)
        self.w(STRING+0x120,STRING+0x120,STRING+0x120,0,0x524548,8)
        self.w(0x537668+0x18,STRING+0x100)
        for resource in (HOME,FIRING):
            self.w(resource+0xc, resource+0x100, 1); self.w(resource+0x100,resource+0x140); self.w(resource+0x158,99999)
        self.w(IMAGESET+0x14,IMAGESET+0x100);self.w(IMAGESET+0x100,0x12345678);self.w(ACTOR+0x18c,ACTOR)
        self.w(0x537210, 113 if timeout else 0); self.w(0x5430c4, 17)
        for a in OBSERVE: self.m.observe(a, self.observe)
        for a in BOUNDARIES: self.m.observe(a, lambda m, a: self.boundaries.append(a))
        for a in CALLBACK_BOUNDARIES: self.m.observe(a, lambda m, a: self.callback_boundaries.append(a))
        self.m.observe(0x4f6974, self.buffer)
        self.m.observe(0x4a5290, lambda m, a: self.events.append(["move", *m.words(m.register(UC_X86_REG_ESP) + 4, 3)]))
        self.m.intercept(0x4a48e0); self.m.intercept(0x4f6286)
        for address in (0x4a9070, 0x4a36f0, 0x5022b5): self.m.intercept(address)
        self.m.on_external = self.external
        self.initial = [dict(address=a, data=self.m.read(a, n).hex()) for a, n in self.blocks]
    def w(self, a, *values): self.m.write(a, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))
    def get(self, a): return self.m.words(a, 1)[0]
    def observe(self, m, a):
        receiver = m.register(UC_X86_REG_ECX) if a not in (0x4f63ec, 0x4dc870, 0x4f6428) else 0
        self.calls.append([a, receiver])
        if a in (0x4141f0, 0x4145f0, 0x4146b0):
            sp = m.register(UC_X86_REG_ESP)
            self.contexts.append([a, receiver, self.get(sp), m.register(UC_X86_REG_EBX), m.register(UC_X86_REG_EBP), m.register(UC_X86_REG_EAX), m.register(UC_X86_REG_ESI), m.register(UC_X86_REG_EDI), m.register(UC_X86_REG_EDX)])
    def buffer(self, m, a):
        sp, receiver = m.register(UC_X86_REG_ESP), m.register(UC_X86_REG_ECX)
        assert self.get(sp + 4) == 0 and TABLE <= receiver < TABLE + 256
        value = self.get(receiver)
        assert value in (STRING+12,STRING+0x4c) and self.get(value-12)==1
        self.events.append(['buffer', receiver, value])
    def external(self, m, a):
        sp = m.register(UC_X86_REG_ESP); arg = lambda i: self.get(sp + 4 + i * 4)
        if a == 0x4a48e0:
            assert arg(0) == 0x7c
            self.requests.append([a, self.get(sp), self.get(sp + 20), arg(0), m.register(UC_X86_REG_EBX)])
            value = 0 if self.exhausted else ALLOC
            if value: self.m.write(ALLOC, bytes([204]) * 0x7c)
            self.events.append(['malloc', value, 0x7c]); m.return_from_external(value, 0)
        elif a == 0x4f6286:
            receiver = m.register(UC_X86_REG_ECX)
            assert receiver in (REGISTRY + 16, IMAGES + 16, ANIMATIONS + 16)
            key = self.m.read(arg(0), 64).split(b'\0')[0].decode('ascii')
            value = HOME if receiver==ANIMATIONS+16 and arg(0)==0x52c22c else FIRING if receiver==ANIMATIONS+16 and arg(0)==0x52c244 else IMAGESET if receiver==IMAGES+16 else 0
            self.w(arg(1), value); self.events.append(['registry', receiver, key, value]); m.return_from_external(int(value!=0), 8)
        elif a == 0x4a9070:
            assert self.growth and (arg(0), arg(1)) == (ALLOC + 0x80, 12)
            self.m.write(ALLOC + 0x90, self.m.read(arg(0), 8) + bytes([204]) * 4)
            self.events.append(['realloc', arg(0), arg(1), ALLOC + 0x90]); m.return_from_external(ALLOC + 0x90, 0)
        elif a == 0x4a36f0:
            assert self.growth
            self.frontier = a; m.uc.emu_stop()
        elif a == 0x5022b5:
            assert self.exhausted
            self.frontier = a; m.uc.emu_stop()
        else: raise AssertionError(hex(a))
    def run(self):
        results, snapshots = [], []
        commands = [0] if self.exhausted else [0, 1000, 29, 30, 7] + ([8] if self.timeout else [])
        self.frontier = None
        for command in commands:
            self.w(STATE + 0x1c, command)
            if command == 7:
                self.w(ALLOC + 0x74, 0, 100 if self.timeout else 500)
                self.w(ALLOC + 0x70, int(self.vertical))
                if self.growth:
                    self.w(ALLOC + 0x80, self.method, self.method)
                    self.w(0x534c00, 8, 9, ALLOC + 0x80)
                    self.events.append(['table-owner', ALLOC + 0x80, 8])
            done = self.m.call(0x48a800, arguments=[ACTOR])
            if not done.completed:
                if self.frontier is None: raise RuntimeError((self.label, command, done))
                break
            results.append(self.m.register(UC_X86_REG_EAX))
            spans = [(ACTOR,0x200),(STATE,0x200),(ALLOC,0x7c),(0x534bf8,0x30),(0x537668,0x60)]
            snapshots.append([dict(address=a,data=self.m.read(a,n).hex()) for a,n in spans])
        spans = [(ACTOR, 0x200), (STATE, 0x200), (ALLOC, 0x7c), (0x534bf8, 0x30), (0x537668, 0x60)]
        if self.growth: spans.append((ALLOC + 0x90, 12))
        if self.exhausted: spans = [(ACTOR, 0x200), (STATE, 0x200)]
        return dict(snapshots=snapshots, growth=self.growth, frontier=self.frontier, label=self.label, method=self.method, timeout=self.timeout, vertical=self.vertical, commands=commands, initial=self.initial, results=results, events=self.events, calls=self.calls, requests=self.requests, boundaries=self.boundaries, callback_boundaries=self.callback_boundaries, contexts=self.contexts, final=[dict(address=a, data=self.m.read(a, n).hex()) for a, n in spans])

HIT, ATTACK = BASE + 0xa000, BASE + 0xb000
BIND_OWNERS = (0x4f63ec, 0x48a8c0, 0x4c7fa0, 0x4c8060, 0x4c8160, 0x4c81b0, 0x4dc830, 0x4dc850)
BIND_BOUNDARIES = (0x4c7f4a, 0x4c7f4f, 0x4c800a, 0x4c800f, 0x4c7f40, 0x4c7f43, 0x4c8000, 0x4c8003, 0x4c7f94, 0x4c7f97, 0x4c8054, 0x4c8057)

class BindingReference(Reference):
    def __init__(self, label, hit=True, attack=True, rebind=False):
        self.hit, self.attack, self.rebind = hit, attack, rebind
        self.cursor, self.allocations, self.binding_calls, self.binding_boundaries = ALLOC, [], [], []
        self.retired=[]
        super().__init__(label, 0x4145f0)
        self.w(ACTOR + 4, 91)
        self.w(HIT, 11, 12, 13, 14, 0x4dc830)
        self.w(ATTACK, 21, 22, 23, 24, 0x4dc850)
        self.blocks += [(HIT, 0x14), (ATTACK, 0x14), (0x513740, 0x28)]
        self.initial = [dict(address=a, data=self.m.read(a, n).hex()) for a, n in self.blocks]
        self.m.intercept(0x4f6428)
        for a in (0x4c8160, 0x4c81b0, 0x4dc830, 0x4dc850): self.m.observe(a, self.observe)
        for a in BIND_BOUNDARIES: self.m.observe(a, lambda m, a: self.binding_boundaries.append(a))
    def observe(self, m, a):
        super().observe(m, a)
        if a in (0x4c8160, 0x4c81b0):
            sp = m.register(UC_X86_REG_ESP)
            self.binding_calls.append([a, m.register(UC_X86_REG_ECX), *m.words(sp + 4, 2 if a == 0x4c8160 else 0)])
    def external(self, m, a):
        sp = m.register(UC_X86_REG_ESP)
        arg = lambda i: self.get(sp + 4 + i * 4)
        if a==0x4f6428:
            helper=arg(0); assert (helper,0x7c) in self.allocations
            self.retired.append(dict(address=helper,data=self.m.read(helper,0x7c).hex()))
            self.allocations.remove((helper,0x7c)); self.events.append(['release',helper,0x7c]); m.return_from_external(0,0)
        elif a == 0x4a48e0:
            count = arg(0)
            assert count in (0x7c, 0x174), hex(count)
            self.requests.append([a, self.get(sp), self.get(sp + 20), count, m.register(UC_X86_REG_EBX)])
            value = self.cursor; self.cursor += (count + 15) & ~15
            self.allocations.append((value, count))
            self.m.write(value, bytes([204]) * count)
            self.events.append(['malloc', value, count]); m.return_from_external(value, 0)
        elif a == 0x4f6286:
            receiver = m.register(UC_X86_REG_ECX)
            assert receiver in (REGISTRY + 16, IMAGES + 16, ANIMATIONS + 16)
            key = self.m.read(arg(0), 64).split(b'\0')[0].decode('ascii')
            value = HIT if receiver == REGISTRY + 16 and key == 'LogicHit' and self.hit else ATTACK if receiver == REGISTRY + 16 and key == 'LogicAttack' and self.attack else HOME if receiver==ANIMATIONS+16 and arg(0)==0x52c22c else FIRING if receiver==ANIMATIONS+16 and arg(0)==0x52c244 else IMAGESET if receiver==IMAGES+16 else 0
            self.w(arg(1), value); self.events.append(['registry', receiver, key, value]); m.return_from_external(int(value != 0), 8)
        else: super().external(m, a)
    def profile(self):
        results, snapshots = [], []
        for iteration in range(2 if self.rebind else 1):
            if iteration:
                helper = self.get(STATE + 0x18)
                target=self.get(self.get(helper)); assert target==0x484d90
                done=self.m.call(target,ecx=helper,arguments=[1]); assert done.completed and self.m.register(UC_X86_REG_EAX)==helper
                self.w(STATE+0x18,0)
                for offset in (0x70, 0x78):
                    token = self.get(ACTOR + offset)
                    if token:
                        # Keep the real allocation and let reset/bind clear these fields.
                        self.w(token + 8, 77); self.w(token + 0x10, 0x4145f0)
                        self.w(token + 0x20, 123, 456, 789)
            self.w(STATE + 0x1c, 0)
            done = self.m.call(0x48a800, arguments=[ACTOR])
            assert done.completed, (self.label, done)
            results.append(self.m.register(UC_X86_REG_EAX))
            spans = [(ACTOR, 0x200), (STATE, 0x200), (HIT, 0x14), (ATTACK, 0x14)] + self.allocations
            snapshots.append([dict(address=a, data=self.m.read(a, n).hex()) for a, n in spans])
        bound = [self.get(ACTOR + offset) for offset in (0x70, 0x78)]
        assert [self.get(t + 0x10) if t else 0 for t in bound] == [0x4dc830 if self.hit else 0, 0x4dc850 if self.attack else 0]
        assert not any(a in (0x4dc830, 0x4dc850) for a, _ in self.calls)
        return dict(retired=self.retired, label=self.label, binding=True, hit=self.hit, attack=self.attack, rebind=self.rebind, method=self.method, initial=self.initial, results=results, events=self.events, calls=self.calls, requests=self.requests, binding_calls=self.binding_calls, binding_boundaries=self.binding_boundaries, snapshots=snapshots)

def compare_bindings(ref, actual, failures):
    if len(ref) != len(actual): failures.append('binding profile count')
    for r, n in zip(ref, actual):
        for key in ('label', 'results', 'events', 'requests', 'binding_calls', 'snapshots', 'retired'):
            if r[key] != n[key]: failures.append(dict(label=r['label'], field=key))
        if n['completed'] != [True] * (2 if r['rebind'] else 1) or n['frontier'] is not None:
            failures.append(dict(label=r['label'], field='binding completion', frontier=n['frontier']))
        expected, boundaries = [0x4f63ec, 0x48a8c0], []
        for enabled, owner, alloc, bind in ((r['hit'], 0x4c7fa0, [0x4c7f4a, 0x4c7f4f], [0x4c7f94, 0x4c7f97]), (r['attack'], 0x4c8060, [0x4c800a, 0x4c800f], [0x4c8054, 0x4c8057])):
            expected.append(owner)
            if enabled: expected += [0x4f63ec, 0x4c8160]; boundaries += alloc + bind
        if r['rebind']:
            expected += [0x4f63ec, 0x48a8c0]
            for enabled, owner, reset, bind in ((r['hit'], 0x4c7fa0, [0x4c7f40, 0x4c7f43], [0x4c7f94, 0x4c7f97]), (r['attack'], 0x4c8060, [0x4c8000, 0x4c8003], [0x4c8054, 0x4c8057])):
                expected.append(owner)
                if enabled: expected += [0x4c81b0, 0x4c8160]; boundaries += reset + bind
        if [c for c in n['calls'] if c[0] in OBSERVE or c[0] in BIND_OWNERS] != r['calls']: failures.append(dict(label=r['label'],field='complete constructor ordered calls'))
        for side in (r, n):
            seen = [a for a, _ in side['calls'] if a in BIND_OWNERS]
            if seen != expected: failures.append(dict(label=r['label'], field='binding ordered owners', expected=expected, actual=seen))
        if r['binding_boundaries'] != boundaries: failures.append(dict(label=r['label'], field='binding original CALL/continuations', expected=boundaries, actual=r['binding_boundaries']))

def review_boundaries():
    m = Machine(claw(), BASE, SIZE)
    assert m.words(0x50f744,9)==(0x484d90,0x4c9e30,0x4141f0,0x4041b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0)
    direct = ((0x48a835, 0x48a83a, 0x4f63ec), (0x48a850, 0x48a855, 0x48a8c0), (0x48a889, 0x48a88e, 0x4dc870))
    for site, continuation, target in direct:
        instruction = m.read(site, 5)
        assert instruction[0] == 0xe8 and site + 5 == continuation
        assert (continuation + struct.unpack('<i', instruction[1:])[0]) & 0xffffffff == target
    # Decode the finite memory-call operands, checking register and displacement.
    indirect = ((0x48a867, 0x48a86a, 0, 0x10), (0x48a874, 0x48a877, 2, 0x20), (0x48a898, 0x48a89b, 2, 0x1c), (0x4dc93a, 0x4dc93d, 3, 4), (0x4dc943, 0x4dc946, 2, 8), (0x4dc9fa, 0x4dc9fd, 7, 12))
    for site, continuation, register, displacement in indirect:
        opcode, modrm, offset = m.read(site, 3)
        assert opcode == 0xff and modrm >> 6 == 1 and (modrm >> 3) & 7 == 2
        assert modrm & 7 == register and offset == displacement and site + 3 == continuation
    opcode, modrm = m.read(0x4142b7, 2)
    assert opcode == 0xff and modrm >> 6 == 0 and (modrm >> 3) & 7 == 2 and modrm & 7 == 6
    assert 0x4142b7 + 2 == 0x4142b9
    return dict(direct=direct, indirect=indirect, method=[0x4142b7, 0x4142b9])

def prepare(out):
    boundary_review = review_boundaries()
    profiles = [Reference('home-wait',0x4145f0).run(),Reference('home-to-real-firing',0x4145f0,True).run()]
    exhaustion = Reference('allocation-exhaustion', 0x4145f0, exhausted=True).run()
    bindings = [BindingReference('real-hit-and-attack').profile(), BindingReference('isolated-hit', attack=False).profile(), BindingReference('isolated-attack', hit=False).profile(), BindingReference('retained-hit-and-attack', rebind=True).profile()]
    out.mkdir(parents=True, exist_ok=True)
    (out / 'reference.json').write_text(json.dumps(dict(version=1, boundary_review=boundary_review, executable_sha256=claw().sha256, profiles=profiles, exhaustion=exhaustion, binding_profiles=bindings), indent=2) + '\n')
    print(json.dumps(dict(status='pass', profiles=len(profiles))))

def compare(out):
    ref, actual = [json.loads((out / name).read_text()) for name in ('reference.json', 'native.json')]
    failures = []
    if len(ref['profiles']) != len(actual['profiles']): failures.append('profile count')
    for r, n in zip(ref['profiles'], actual['profiles']):
        for key in ('label', 'results', 'events', 'requests', 'contexts', 'final', 'snapshots'):
            if r[key] != n[key]: failures.append(dict(label=r['label'], field=key))
        if [c['completed'] for c in n['completions']] != [True]*len(r['commands']): failures.append(dict(label=r['label'], field='completion', actual=n['completions']))
        if n.get('frontier') != r['frontier']: failures.append(dict(label=r['label'], field='unsupported frontier'))
        if [c for c in n['calls'] if c[0] in OBSERVE] != r['calls']: failures.append(dict(label=r['label'],field='complete ordered calls'))
        wanted = [0x4f63ec,0x48a8c0,0x414030,0x4145b0,0x4c96b0,0x4c96b0,0x4c96b0,0x4dc870,0x4c9e30,0x4141f0,0x4145f0,0x4041b0]
        if r['timeout']: wanted += [0x4dc870,0x4c9e30,0x4141f0,0x4146b0,0x4041b0]
        selected=set(wanted)
        for side in (r,n):
            seen=[a for a,_ in side['calls'] if a in selected]
            if seen!=wanted: failures.append(dict(label=r['label'],field='ordered elected owners',actual=seen,expected=wanted))
        callback_boundaries=[0x48a867,0x48a86a,0x48a89b,0x48a89b,0x48a874,0x48a877,0x48a89b,0x48a898,0x48a89b]
        callback_boundaries += [0x48a889,0x48a88e,0x48a89b]*(2 if r['timeout'] else 1)
        if r['callback_boundaries']!=callback_boundaries: failures.append(dict(label=r['label'],field='original callback virtual CALL continuations',actual=r['callback_boundaries'],expected=callback_boundaries))
        lifecycle=[0x4dc93a,0x4dc93d,0x4dc943,0x4142b7,0x4142b9,0x4dc946,0x4dc9fa,0x4dc9fd]
        expected_boundaries=[0x48a835,0x48a83a,0x48a850,0x48a855]+lifecycle*(2 if r['timeout'] else 1)
        if r['boundaries']!=expected_boundaries: failures.append(dict(label=r['label'],field='original CALL continuations',actual=r['boundaries']))
        ctor={b['address']:bytes.fromhex(b['data']) for b in r['snapshots'][0]}
        assert struct.unpack_from('<II',ctor[ALLOC],0x48)==(HOME,FIRING)
        assert struct.unpack_from('<I',ctor[ACTOR],0x190)[0]==HOME
        assert struct.unpack_from('<I',ctor[STATE],0x1c)[0]==7
    for field in ('requests', 'events', 'frontier'):
        if ref['exhaustion'][field] != actual['exhaustion'][field]: failures.append(dict(label='allocation-exhaustion', field=field))
    compare_bindings(ref['binding_profiles'], actual.get('binding_profiles', []), failures)
    for control in actual['controls']:
        if not control['passed']: failures.append(dict(control=control['name']))
    result = dict(status='fail' if failures else 'pass', profiles=len(ref['profiles']), binding_profiles=len(ref['binding_profiles']), controls=len(actual['controls']), failures=failures)
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))
    return bool(failures)

def main():
    out = Path(sys.argv[2]).resolve()
    if (ROOT / 'work').resolve() not in out.parents: raise ValueError('evidence belongs under ignored work/')
    if sys.argv[1] == 'prepare': prepare(out)
    elif sys.argv[1] == 'compare': return compare(out)
    else: raise ValueError(sys.argv[1])
if __name__ == '__main__': raise SystemExit(main())
