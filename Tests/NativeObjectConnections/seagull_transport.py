"""Original-backed finite Seagull transport and focused owner x87 diagnostics."""
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'Tests')]
from Tests.clawparity.program import claw
from Tests.clawparity.world import idle_registry
from unicorn.x86_const import UC_X86_REG_ESP


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def prepare(out):
    services = module('seagull_transport_services', 'Tests/NativeObjectConnections/cut_throat_transport.py')
    fixture = module('seagull_original_inputs', 'Tests/families/level_five_seagull_core.cases.py')
    profiles = []
    boundaries = (0x486f50, 0x443170, 0x4332f0, 0x4dca10, 0x44317d, 0x486ee8)
    metadata = [(0x486ec8, 0x4f63ec, 0x486ecd), (0x486ee3, 0x486f50, 0x486ee8), (0x443178, 0x4332f0, 0x44317d)]
    for live, status in ((False, 0), (False, 0x21), (True, 0x21), (True, 0x4500)):
        ref = services.Reference()
        ref.next = services.BASE
        tokens = fixture.construct_setup(True, 0, 1.0, 0xcc)(ref)
        actor, logic = tokens['actor'], tokens['desc']
        ref.put(actor + 0x18c, actor)
        ref.put(actor + 0x38, 0xffffffff)
        ref.put(logic + 0x10, 0x486e90)
        ref.put(logic + 0x1c, 0)
        idle_registry(ref, 5)
        observations = []
        for address in boundaries:
            ref.m.observe(address, lambda m, a: observations.append({
                'pc': a, 'x87': m.x87_state(), 'stack_top': ref.get(m.register(UC_X86_REG_ESP))}))
        for address, target, continuation in metadata:
            code = ref.read(address, 5)
            assert code[0] == 0xe8 and address + 5 + struct.unpack('<i', code[1:])[0] == target
            assert continuation == address + 5
        incoming = [0x23f, status | (3 << 11 if live else 0), [[0xc000000000000000, 0x3fff]] if live else []]
        ref.m.reset_x87()
        ref.m.set_x87_state(*incoming)
        result = ref.m.call(0x486e90, arguments=(actor,))
        assert result.completed, result
        helper = ref.get(logic + 0x18)
        resources = [ref.get(helper + offset) for offset in range(0x400, 0x434, 4)]
        assert helper == services.ALLOC and all(resources)
        assert [row['pc'] for row in observations] == list(boundaries)
        assert all([list(slot) for slot in row['x87'][2]] == incoming[2] for row in observations)
        profiles.append({'incoming': incoming, 'outgoing': ref.m.x87_state(), 'boundaries': observations,
                         'helper': helper, 'resource_bindings': resources, 'completed': True})
    evidence = {'sha256': claw().sha256, 'call_metadata': metadata, 'profiles': profiles,
                'native_comparison': False, 'resource_scope': 'Nonzero map structures, not loaded scene acceptance.'}
    out.mkdir(parents=True, exist_ok=True)
    (out / 'original-x87-boundary.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'command': 'seagull-original-boundary', 'status': 'pass', 'profiles': len(profiles)}))


# The focused inventory uses the normal generator and admission validation.
# Its dispatcher contains the two linked owners and retains their actual contracts.
OWNER_PROBE = r'''
#include "OwnerCanonicalDispatch.h"
static ClawX87State state;
extern "C" void claw_owner_probe_input(const ClawX87State *incoming) { state = *incoming; }
extern "C" const ClawX87State *claw_owner_probe_output() { return &state; }
extern "C" uint32_t claw_owner_probe_entry(uint32_t function, uint32_t receiver,
    const uint32_t *arguments, uint32_t count, ClawHost *host, uint32_t *result) {
    ClawCall call{};
    call.function = function;
    call.receiver = receiver;
    call.argumentCount = count;
    for (uint32_t i = 0; i < count; ++i) call.arguments[i] = arguments[i];
    call.stackPointer = host->entryStackPointer;
    call.x87ArgumentCount = CLAW_X87_EXACT;
    call.x87State = &state;
    return claw_canonical_dispatch(&call, host, result);
}
'''


def owner_environment(spec):
    """Register the unchanged manifest services, without a family entry election."""
    import random
    from Tests.clawparity.env import Env
    from Tests.clawparity.fixtures import CATALOGUE
    from Tests.clawparity.runner import owned_ranges
    from Tests.clawparity.cases import caller_frame_base
    env = Env(claw())
    env._begin_case(random.Random(0x487830))
    for text, callee in spec.get('callees', {}).items():
        address = int(text, 0)
        if callee.get('convention') == 'compiler-context':
            env.compiler_callees[address] = callee['compiler_context']
        elif callee.get('kind') == 'whole' and 'source_context' in callee:
            env.source_callees[address] = callee
        if 'x87_exact' in callee:
            env.whole_x87(address, callee['convention'], callee['argc'], callee.get('name', ''),
                          callee.get('arguments', ()), exact=callee['x87_exact'])
        if 'caller_frame' in callee:
            ranges = owned_ranges(spec)
            env.caller_frame(address, callee['convention'], callee['argc'], [
                (int(row['caller'], 0), int(row['site'], 0),
                 *caller_frame_base(row['ebp']['base'], next(o['argc'] for o in spec['owned']
                                                          if o['address'] == row['caller'])),
                 row['ebp']['offset']) for row in callee['caller_frame']],
                {start: [tuple(r) for r in found] for start, found in ranges.items()})
        if callee['kind'] == 'fixture':
            env.fixture(address, callee['convention'], callee['argc'],
                        CATALOGUE[callee.get('fixture', 'scripted')], callee.get('name', ''),
                        callee.get('arguments', ()))
    # The older object manifest spells the rectangle imports as scripted;
    # this focused caller supplies the real Win32 rectangle effects.
    if spec['id'] == 'level_one_object_actions_01':
        def empty_rect(environment, call):
            environment.put(call.arguments[0], 0, 0, 0, 0)
            return 1
        def rect(environment, call):
            environment.put(call.arguments[0], *call.arguments[1:5])
            return 1
        env.override(0x546cdc, empty_rect)
        env.override(0x546d5c, rect)
    return env


def owners(out, patrol=False):
    """Compare repaired owners under exact callers, including inherited live slots."""
    import ctypes as C
    from Tests.clawparity import build, build_inputs
    from Tests.clawparity.env import U32, NativeHost, NativeX87State
    from Tests.clawparity.kernel import STACK_TOP
    from tools.claw.gen_project import canonical_inventory, canonical_dispatch_text
    fixture = module('seagull_owner_inputs', 'Tests/families/' +
                     ('level_five_seagull_states' if patrol else 'level_five_seagull_core') + '.cases.py')
    specifications = [json.loads((ROOT / 'Tests/families' / (family + '.json')).read_text())
                      for family in (('level_five_seagull_states',) if patrol else
                                     ('level_one_object_actions_01', 'level_five_seagull_core'))]
    pending = []
    for spec in specifications:
        errors = build_inputs.admission_errors(spec)
        level = spec.get('evidence', {}).get('level')
        if level != 'admitted' or errors:
            pending.append({'family': spec['id'], 'evidence_level': level,
                            'admission_errors': errors})
    if pending:
        evidence = {'command': 'seagull-owner-x87', 'status': 'pending-admission',
                    'comparisons': 0, 'profiles': [], 'pending': pending,
                    'native_comparison': False, 'full_transport_acceptance': False,
                    'needed': 'Both owner families must have current gate admissions before this comparison can compile.'}
        out.mkdir(parents=True, exist_ok=True)
        (out / 'owner-x87-comparison.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence))
        return 3
    targets = (0x4879a0,) if patrol else (0x4332f0, 0x443170, 0x486f50, 0x487830)
    for spec in specifications:
        for declaration in spec['owned']:
            if int(declaration['address'], 0) in targets:
                assert declaration.get('x87_environment') == {'pop': 0, 'push': 0}
    out.mkdir(parents=True, exist_ok=True)
    _, _, registry = canonical_inventory(specifications, [])
    generated = out / 'OwnerCanonicalDispatch.h'
    generated.write_text(canonical_dispatch_text(registry))
    wrapper = out / 'owner-x87-probe.cpp'
    wrapper.write_text(OWNER_PROBE)
    sources = [wrapper] + [ROOT / source for spec in specifications for source in spec['sources']]
    library = C.CDLL(str(build.library('seagull-owner-x87', sources, 'O2',
                                      dependencies=[generated])))
    entry = library.claw_owner_probe_entry
    entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
    entry.restype = U32
    library.claw_owner_probe_input.argtypes = [C.POINTER(NativeX87State)]
    library.claw_owner_probe_output.restype = C.POINTER(NativeX87State)
    profiles = [(0x23f, flags, ()) for flags in (0, 0x20, 0x21, 0x4500)]
    profiles += [(0x23f, flags | (3 << 11), ((0xc000000000000000, 0x3fff),))
                 for flags in (0, 0x20, 0x21, 0x4500)]
    profiles += [(0x23f, flags | (5 << 11), ((0x8000000000000001, 0x3fff), (0, 0x8000)))
                 for flags in (0x21, 0x4500)]
    rows = []
    for function in targets:
        spec = specifications[0 if patrol or function == 0x4332f0 else 1]
        patrol_variants = {
            'left': dict(x=0.0, cooldown=1000),
            'right': dict(x=1000.0, flip=2, cooldown=1000),
            'cooldown': dict(cooldown=-1),
            'outside': dict(px=1000),
            'fractional': dict(x=500.25, y=100.125),
            'strike-linear': dict(new_plans=True),
            'strike-zero': dict(speed=0.0, new_plans=True),
        }
        variants = tuple(patrol_variants) if patrol else (
            ('equal', 'unequal', 'unordered') if function == 0x487830 else (1.0, 3.75))
        for variant in variants:
            for incoming in profiles:
                env = owner_environment(spec)
                if patrol:
                    tokens = fixture.setup_actor(patrol_variants[variant])(env)
                    if variant.startswith('strike-'):
                        env.put(env.get(tokens['actor']) + 0x58, 0x487b80)
                    tokens['obj'] = tokens['actor']
                    arguments = ()
                elif function == 0x487830:
                    left, right = {'equal': (1.0, 1.0), 'unequal': (1.0, 2.0),
                                   'unordered': (float('nan'), 1.0)}[variant]
                    tokens = fixture.idle_setup(left, right, 0x82, 0, -3.5, 0xcc)(env)
                    arguments = ()
                else:
                    tokens = fixture.construct_setup(True, 0, variant, 0xcc)(env)
                    arguments = (tokens['actor'],)
                env._freeze()
                state = NativeX87State()
                state.size, state.version = C.sizeof(state), 1
                state.control, state.status, state.count = incoming[0], incoming[1], len(incoming[2])
                for index, (significand, exponent) in enumerate(incoming[2]):
                    state.slots[index].significand = significand
                    state.slots[index].signExponent = exponent
                library.claw_owner_probe_input(C.byref(state))
                native = env.run_native(entry, function, tokens['obj'], arguments)
                result = library.claw_owner_probe_output().contents
                native.x87 = (result.control, result.status, tuple(
                    (result.slots[i].significand, result.slots[i].signExponent) for i in range(result.count)))
                # Direct Machine observation installs the raw caller state before
                # the original's first instruction. This is deliberately separate
                # from the bounded family case API, which elects exception flags only.
                env.machine.observe(function, lambda machine, address, incoming=incoming:
                                    machine.set_x87_state(*incoming))
                original = env.run_original(function, tokens['obj'], arguments)
                original.x87 = env.machine.x87_state()
                difference = env.compare(native, original, True, STACK_TOP + 4 * (1 + len(arguments)))
                preserved = (native.x87[0] == incoming[0] and native.x87[2] == incoming[2] and
                             ((native.x87[1] >> 11) & 7) == ((incoming[1] >> 11) & 7))
                rows.append({'function': function, 'variant': variant, 'incoming': incoming,
                             'native': native.x87, 'original': original.x87,
                             'completed': native.completed and original.completed,
                             'preserved': preserved, 'difference': difference})
    passed = all(row['completed'] and row['preserved'] and row['difference'] is None for row in rows)
    evidence = {'command': 'seagull-owner-x87', 'sha256': claw().sha256,
                'status': 'pass' if passed else 'fail', 'comparisons': len(rows), 'profiles': rows,
                'scope': 'Repaired owner environments only; no full transport or app acceptance.',
                'native_comparison': True, 'full_transport_acceptance': False}
    (out / 'owner-x87-comparison.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({key: evidence[key] for key in ('command', 'status', 'comparisons',
                                                  'native_comparison', 'full_transport_acceptance')}))
    return 0 if passed else 1


def check(out):
    registry = (ROOT / 'Sources/ClawCanonicalDispatch.h').read_text()
    missing = []
    for address in (0x4332f0, 0x486f50):
        row = next(line for line in registry.splitlines() if ('{0x%08xu,' % address) in line)
        if row.rstrip().endswith('0u},'):
            missing.append({'function': address, 'reason': 'canonical owner lacks x87 environment capability'})
    result = {'command': 'seagull-transport', 'status': 'missing-owner-contract' if missing else 'missing-native-comparison',
              'missing': missing, 'native_comparison': False,
              'needed': 'Admit exact constructor x87 contracts, then implement full original/native transport comparison.'}
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 3


TRANSPORT_OBSERVE = {
    0x486f50: 1, 0x443170: 1, 0x4332f0: 1, 0x4dca10: 0, 0x403b40: 2,
    0x405000: 0, 0x4f63ec: 1, 0x4c7fa0: 1, 0x4c8060: 1, 0x4c7970: 1,
    0x4062e0: 1, 0x4061b0: 1, 0x4c8220: 1, 0x4f6286: 2,
    0x4f6439: 0, 0x4dc180: 0, 0x4db620: 1, 0x4dbe10: 2, 0x4dbd60: 1,
    0x4dbcd0: 0, 0x420fc0: 1, 0x4dbd20: 1, 0x406290: 0, 0x4208b0: 4,
    0x487830: 0, 0x4879a0: 0, 0x43e9b0: 0, 0x48cf50: 1, 0x4c96b0: 0,
    0x4dc870: 1, 0x404fc0: 1, 0x4873a0: 1, 0x4063b0: 1, 0x43dfa0: 0,
    0x4f6974: 1, 0x4872b0: 1, 0x4f6584: 0, 0x4f6428: 1, 0x4c82a0: 1,
}


def transport_prepare(out):
    from unicorn import x86_const as x86
    services = module('seagull_transport_base', 'Tests/NativeObjectConnections/cut_throat_transport.py')
    fixture = module('seagull_transport_inputs', 'Tests/families/level_five_seagull_core.cases.py')
    registers = {name: getattr(x86, 'UC_X86_REG_' + name.upper()) for name in
                 ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eflags')}

    class Reference(services.Reference):
        def __init__(self, status, live):
            super().__init__(status, live)
            self.next = services.BASE
            self.tokens = fixture.construct_setup(True, 0, 1.0, 0xcc)(self)
            actor, logic = self.tokens['actor'], self.tokens['desc']
            self.put(actor + 0x18c, actor)
            self.put(actor + 0x38, 0xffffffff)
            self.put(logic + 0x10, 0x486e90)
            self.put(logic + 0x1c, 0)
            self.put(0x537e88, actor)
            idle_registry(self, 5)
            text = self.text(0x523148).encode('ascii')
            name = self.object(13 + len(text), data=struct.pack('<III', 1, len(text), len(text)) + text + b'\0') + 12
            states = self.object(4, words=[0x4879a0])
            names = self.object(4, words=[name])
            self.put(0x53c278, 5, 5, states, states, 4, 0, 0)
            self.put(0x5376a0, 5, 5, names, names, 4, 0, 0)
            self.boundaries = []
            self.callback_frame = None
            self.freed = []
            for address in TRANSPORT_OBSERVE:
                if address not in services.OBSERVE:
                    self.m.observe(address, self.entry)
            for address in (0x486e90, 0x4873a0, 0x487830, 0x4879a0, 0x487469, 0x4dc946, 0x4332f0, 0x4f6439, 0x4c82a0, 0x4879c0):
                self.m.observe(address, self.capture)
            self.m.intercept(0x4f6428)
            self.initial = [dict(address=a, data=self.read(a, n).hex()) for a, n in self.blocks]

        def capture(self, machine, pc):
            cpu = {key: machine.register(value) for key, value in registers.items()}
            cpu['eip'], cpu['fsHead'] = pc, machine.fs_head
            if pc == 0x486e90:
                self.callback_frame = cpu['esp']
            head = machine.fs_head
            self.boundaries.append({'pc': pc, 'cpu': cpu, 'return_pc': self.get(cpu['esp']),
                                    'x87': machine.x87_state(),
                                    'callback_frame': self.callback_frame,
                                    'fs_words': list(machine.words(head, 4)) if head != 0xffffffff else []})

        def entry(self, machine, address):
            if address not in TRANSPORT_OBSERVE:
                return
            cdecl = address in (0x4f63ec, 0x48cf50, 0x4dc870, 0x4f6428)
            receiver = 0 if cdecl else machine.register(x86.UC_X86_REG_ECX)
            args = list(machine.words(machine.register(x86.UC_X86_REG_ESP) + 4, TRANSPORT_OBSERVE[address]))
            self.entries.append([address, receiver, args])
            if address in (0x4f63ec, 0x486f50):
                self.continuations.append([address, self.get(machine.register(x86.UC_X86_REG_ESP))])
            if address == 0x4f6286:
                key = self.text(args[0])
                self.events.append(['lookup', receiver, key, self.lookup(receiver, key)])

        def external(self, machine, address):
            slot = next((key for key, value in machine.import_stub.items() if value == address), address)
            if slot == 0x546cd4:
                rectangle, x, y = machine.words(machine.register(x86.UC_X86_REG_ESP) + 4, 3)
                left, top, right, bottom = struct.unpack('<iiii', self.read(rectangle, 16))
                x, y = struct.unpack('<ii', struct.pack('<II', x, y))
                result = int(left <= x < right and top <= y < bottom)
                self.events.append(['contains', rectangle, x, y, result])
                machine.return_from_external(result, 12)
            elif address == 0x4f6428:
                token = self.get(machine.register(x86.UC_X86_REG_ESP) + 4)
                assert token in [a for a, _ in self.allocations] and token not in self.freed
                self.freed.append(token)
                machine.return_from_external(0, 0)
            else:
                super().external(machine, address)

        def snapshot(self, command):
            actor, logic = self.tokens['actor'], self.tokens['desc']
            helper = self.get(logic + 0x18)
            spans = [(services.BASE, services.SIZE)]
            spans += [(a, n) for a, n in self.allocations if a not in self.freed]
            return dict(command=command, helper=helper, outgoing=self.m.x87_state(), callback_fs_restored=self.m.fs_head == 0xffffffff,
                        events=list(self.events), entries=list(self.entries), boundaries=list(self.boundaries),
                        final=[dict(address=a, data=self.read(a, n).hex()) for a, n in spans])

        def run_transport(self, label):
            actor, logic = self.tokens['actor'], self.tokens['desc']
            self.m.reset_x87()
            self.m.set_x87_state(*self.incoming)
            phases = []
            for command in (0, 1000, 29, 30):
                self.put(logic + 0x1c, command)
                result = self.m.call(0x486e90, arguments=(actor,))
                assert result.completed, (command, result)
                phases.append(self.snapshot(command))
            helper = self.get(logic + 0x18)
            assert all(self.get(helper + offset) for offset in range(0x400, 0x434, 4))
            result = self.m.call(0x4872b0, ecx=helper, arguments=(1,))
            assert result.completed and result.eax == helper, result
            self.put(logic + 0x18, 0)
            phases.append(self.snapshot('retire'))
            self.put(logic + 0x1c, 0)
            result = self.m.call(0x486e90, arguments=(actor,))
            assert result.completed, result
            phases.append(self.snapshot('recreate'))
            self.put(logic + 0x1c, 5)
            result = self.m.call(0x486e90, arguments=(actor,))
            assert result.completed, result
            animation = [row for row in self.boundaries if row['pc'] == 0x4c82a0]
            returned = [row for row in self.boundaries if row['pc'] == 0x4879c0]
            assert len(animation) == len(returned) == 1
            assert animation[0]['return_pc'] == 0x4879c0
            assert animation[0]['x87'] == returned[0]['x87']
            phases.append(self.snapshot(5))
            return dict(label=label, actor=actor, state=logic, initial=self.initial,
                        incoming=self.incoming, continuations=self.continuations, phases=phases)

    profiles = [Reference(status, live).run_transport(f'sw-{status:x}-live-{int(live)}')
                for status, live in ((0, False), (0x21, False), (0x21, True), (0x4500, True))]
    metadata = []
    ref = Reference(0, False)
    for site, target, continuation in ((0x486ec8, 0x4f63ec, 0x486ecd), (0x486ee3, 0x486f50, 0x486ee8),
                                       (0x443178, 0x4332f0, 0x44317d), (0x4879bb, 0x4c82a0, 0x4879c0)):
        code = ref.read(site, 5)
        assert code[0] == 0xe8 and site + 5 + struct.unpack('<i', code[1:])[0] == target and continuation == site + 5
        metadata.append([site, target, continuation])
    # Verify the loaded registry row against the actual original registration
    # store, rather than selecting a constructor's similarly named enter state.
    registration = {'owner': 0x4874b0, 'name': 0x523148, 'table': 0x53c270,
                    'store': 0x48757f, 'target': 0x4879a0}
    assert ref.read(0x4874f4, 5) == b'\x68' + struct.pack('<I', registration['name'])
    assert ref.read(0x48756b, 5) == b'\xb9' + struct.pack('<I', registration['table'])
    assert ref.read(registration['store'], 6) == b'\xc7\x00' + struct.pack('<I', registration['target'])
    out.mkdir(parents=True, exist_ok=True)
    (out / 'reference.json').write_text(json.dumps(dict(executable_sha256=claw().sha256,
        profiles=profiles, call_metadata=metadata, registration=registration), indent=2) + '\n')
    print(json.dumps(dict(command='seagull-original-transport', status='pass', profiles=len(profiles), phases=7)))


def registered_owner_contract(out, reference):
    """Report the registered patrol owner's actual transport capability."""
    registry = (ROOT / 'Sources/ClawCanonicalDispatch.h').read_text()
    row = next(line for line in registry.splitlines() if '{0x004879a0u,' in line)
    fields = row.strip().strip('{}, ').split(', ')
    environment = int(fields[-1].removesuffix('u'))
    source = int(fields[6].removesuffix('u'))
    import re
    implementation = (ROOT / 'Sources/LevelFiveSeagullStatesRuntime.cpp').read_text()
    body = implementation.split('uint32_t function_4879a0(', 1)[1].split('// 0x487b80:', 1)[0]
    returns = re.findall(r'\breturn\s+([^;]+);', body)
    constant_zero_returns = bool(returns) and all(value.strip() == '0' for value in returns)
    observations = []
    for profile in reference['profiles']:
        phase = next(item for item in profile['phases'] if item['command'] == 5)
        entry = next(item for item in phase['boundaries'] if item['pc'] == 0x4879a0)
        returned = next(item for item in phase['boundaries'] if item['pc'] == 0x487469)
        observations.append({'label': profile['label'], 'entry': entry, 'returned': returned})
    missing = []
    if not environment:
        missing.append({'function': 0x4879a0, 'reason': 'Registered Idle patrol owner lacks inherited x87 environment; its Floating helper starts an empty stack instead of importing and publishing the caller state.'})
    if not source and constant_zero_returns and any(item['returned']['cpu']['eax'] != 0 for item in observations):
        missing.append({'function': 0x4879a0, 'reason': 'Original source-call continuation observes nonzero EAX, but the ordinary patrol owner returns zero on every exit and has no source-output contract.'})
    result = {'command': 'seagull-registered-owner-contract', 'sha256': claw().sha256,
              'registration': reference['registration'], 'source_capability': source,
              'x87_environment_capability': environment, 'source_output_mask': 0x5f3,
              'current_ordinary_returns_constant_zero': constant_zero_returns,
              'observations': observations, 'missing': missing,
              'status': 'missing-owner-contract' if missing else 'ready'}
    (out / 'registered-owner-contract.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def transport_compare(out):
    services = module('seagull_transport_normalize', 'Tests/NativeObjectConnections/cut_throat_transport.py')
    reference = json.loads((out / 'reference.json').read_text())
    native = json.loads((out / 'native.json').read_text())
    failures = []
    owner_contract = registered_owner_contract(out, reference)
    if len(reference['profiles']) != 4 or len(native['profiles']) != 4:
        failures.append('profile count')
    # These are genuinely inlined in admitted owners; their descendants and bytes
    # remain in the joined comparison. Internal enemy motion shares its x87 scope.
    selected = set(TRANSPORT_OBSERVE) - {0x443170, 0x4f6286, 0x43dfa0, 0x4dca10}
    def original_calls(rows):
        result, constructor_idle = [], False
        for row in rows:
            if row[0] == 0x486f50:
                constructor_idle = True
            if row[0] == 0x487830 and constructor_idle:
                constructor_idle = False
                continue
            if row[0] in selected:
                result.append(row)
        return services.normalize_calls(result)
    required_controls = {
        'provider required', 'foreign provider rejected', 'wrong callback rejected',
        'missing registry fails', 'missing rectangle fails', 'allocation exhaustion preserved',
        'occupied allocation preserved', 'actor identity replacement rejected',
        'allocation identity replacement rejected', 'physical service reentry rejected',
        'stale live helper rejected', 'owner routed release', 'fresh allocation after release',
        'retirement recreation rejects stale helper', 'double retirement rejected',
        'shared scene cursor advanced by exact extent', 'allocation lease expires',
        'allocation owner retained', 'unsupported x87 CW rejected',
        'foreign provider on same host rejected', 'foreign helper allocation rejected',
        'reentrant wrong constructor request rejected', 'out-of-context constructor request rejected before allocation',
    }
    required_controls |= {'malformed lifecycle source ' + mode + ' rejected' for mode in
                          ('size', 'version', 'input', 'output', 'preserve', 'esp', 'eip', 'receiver', 'return', 'fsHead')}
    required_controls |= {'malformed patrol source ' + mode + ' rejected' for mode in
                          ('size', 'version', 'input', 'output', 'preserve', 'esp', 'eip', 'receiver', 'return', 'fsHead')}
    required_controls |= {'malformed constructor exact x87 ' + mode + ' rejected' for mode in
                          ('control', 'count', 'pop', 'returned')}
    required_controls |= {'malformed animation exact ' + mode + ' rejected' for mode in
                          ('control', 'count', 'pop', 'push', 'returned', 'operation', 'receiver', 'delta', 'stack', 'rate')}
    names = [control['name'] for control in native['controls']]
    if not required_controls.issubset(names) or len(names) != len(set(names)):
        failures.append(dict(field='required unique controls', missing=sorted(required_controls-set(names))))
    for expected, actual in zip(reference['profiles'], native['profiles']):
        if expected['label'] != actual['label']:
            failures.append('profile labels')
        if not actual['allocation_witness']:
            failures.append(dict(label=expected['label'], field='allocation source continuation'))
        for e, a in zip(expected['phases'], actual['phases']):
            for field in ('command', 'helper', 'outgoing', 'events', 'final'):
                if e[field] != a[field]:
                    failures.append(dict(label=expected['label'], command=e['command'], field=field))
            expected_exact = [row['x87'] for row in e['boundaries'] if row['pc'] == 0x4332f0]
            actual_exact = a.get('exact', [])
            if expected_exact != [row['state'] for row in actual_exact] or any(
                    row['pop'] != 0 or row['push'] != 0 or row['returned'] != 0 for row in actual_exact):
                failures.append(dict(label=expected['label'], command=e['command'], field='inherited exact x87 transfer'))
            animation = [row['x87'] for row in e['boundaries'] if row['pc'] == 0x4c82a0]
            if animation != a.get('animation_exact', []):
                failures.append(dict(label=expected['label'], command=e['command'], field='animation exact x87 transfer'))
            original_source = [row for row in e['boundaries'] if row['pc'] == 0x4873a0 or
                               (row['pc'] == 0x4879a0 and row['return_pc'] == 0x487469)]
            native_source = a.get('sources', [])
            if len(original_source) != len(native_source):
                failures.append(dict(label=expected['label'], command=e['command'], field='source boundary count'))
            elif original_source:
                original_frame = original_source[0]['cpu']['esp']
                native_frame = native_source[0]['cpu']['esp']
                for original_row, native_row in zip(original_source, native_source):
                    fields = ['ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp']
                    if original_row['pc'] == 0x4879a0:
                        fields += ['eax']
                    same = (original_row['pc'] == native_row['function'] and
                            original_row['return_pc'] == native_row['return_pc'] and
                            native_row['size'] == 72 and native_row['version'] == 1 and
                            native_row['input'] == 0x7ff and native_row['output'] == 0x5f3 and
                            native_row['preserve'] == 0x472 and
                            original_row['cpu']['esp'] - original_frame == native_row['cpu']['esp'] - native_frame and
                            all(original_row['cpu'][key] == native_row['cpu'][key] for key in fields))
                    if not same:
                        failures.append(dict(label=expected['label'], command=e['command'], field='source live-input envelope',
                                             original=original_row, native=native_row))
            completed_sources = a.get('source_returns', [])
            expected_completions = [(0x4879a0, 0x487469), (0x4873a0, 0x4dc946)] if original_source else []
            if [(row['function'], row['return_pc']) for row in completed_sources] != expected_completions:
                failures.append(dict(label=expected['label'], command=e['command'], field='completed source returns'))
            for row in completed_sources:
                entry_row = next(item for item in original_source if item['pc'] == row['function'])
                exit_row = next(item for item in e['boundaries'] if item['pc'] == row['return_pc'])
                incoming, outgoing = row['input'], row['output']
                output_fields = ('eax', 'ebx', 'esi', 'edi', 'ebp', 'eip')
                # Compiler exception handling is native, not recovered guest
                # execution. Preserve each caller's opaque chain identity: the
                # original callback owns this exact MSVC node; the native C++
                # caller has no guest registration. Do not compare their tokens.
                fs_valid = (entry_row['cpu']['fsHead'] == exit_row['cpu']['fsHead'] and
                            entry_row['cpu']['fsHead'] == entry_row['callback_frame'] - 12 and
                            entry_row['fs_words'][:3] == [0xffffffff, 0x50780b, 0xffffffff] and
                            entry_row['fs_words'] == exit_row['fs_words'] and
                            incoming['fsHead'] == outgoing['fsHead'] == 0xffffffff and e['callback_fs_restored'])
                valid = (fs_valid and all(exit_row['cpu'][key] == outgoing[key] for key in output_fields) and
                         exit_row['cpu']['esp'] - entry_row['cpu']['esp'] == outgoing['esp'] - incoming['esp'] and
                         entry_row['x87'] == row['incoming_x87'] and exit_row['x87'] == row['outgoing_x87'])
                if not valid:
                    failures.append(dict(label=expected['label'], command=e['command'], field='source output or x87 envelope',
                                         function=row['function'], original=exit_row, native=row))
            if not a['completed']:
                failures.append(dict(label=expected['label'], command=e['command'], fault=a['fault']))
            wanted = original_calls(e['entries'])
            found = services.normalize_calls([row for row in a['calls'] if row[0] in selected])
            if wanted != found:
                failures.append(dict(label=expected['label'], command=e['command'], field='ordered calls',
                    expected_count=len(wanted), actual_count=len(found),
                    first_difference=next(((x,y) for x,y in zip(wanted,found) if x!=y),None)))
        if len(expected['phases']) != len(actual['phases']):
            failures.append(dict(label=expected['label'], field='phase count'))
    for control in native['controls']:
        if not control['passed']:
            failures.append(dict(control=control['name']))
    evidence = dict(command='seagull-transport', status='missing-owner-contract' if owner_contract['missing'] else 'fail' if failures else 'pass',
                    missing=owner_contract['missing'], native_comparison=not failures and not owner_contract['missing'],
                    profiles=len(reference['profiles']), controls=len(native['controls']), failures=failures,
                    compiler_exception_boundary='Original callback MSVC node at entry ESP-12 (next ffffffff, handler50780b, state ffffffff) is retained across source edges and removed on callback return; native compiler caller has no guest node and retains FS ffffffff. Other declared source outputs and exact x87 are compared directly.')
    (out / 'comparison.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence))
    return 3 if owner_contract['missing'] else int(bool(failures))


if __name__ == '__main__':
    output = Path(sys.argv[2]).resolve()
    if (ROOT / 'work').resolve() not in output.parents:
        raise ValueError('evidence must remain under work/')
    if sys.argv[1] == 'prepare':
        prepare(output)
    elif sys.argv[1] == 'transport-prepare':
        transport_prepare(output)
    elif sys.argv[1] == 'compare':
        raise SystemExit(transport_compare(output))
    elif sys.argv[1] == 'owners':
        raise SystemExit(owners(output))
    elif sys.argv[1] == 'patrol-owners':
        raise SystemExit(owners(output, patrol=True))
    elif sys.argv[1] == 'check':
        raise SystemExit(check(output))
    else:
        raise ValueError(sys.argv[1])
