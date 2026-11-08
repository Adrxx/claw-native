"""Original RedTail callback over a scene-attached WWD actor and real assets.

Native inputs supply only physical allocation, resource dictionaries and RNG.
The original constructor, vtable targets and lifecycle state code execute intact.
"""
import json
from pathlib import Path
import re
import shutil
import struct
import zlib
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x47f6e0
OBSERVE = (0x4F63EC,0x47FF90,0x40E0D0,0x44C000,0x40E1B0,0x482430,
           0x4C96B0,0x4DC870,0x4827A0,0x47F800,0x4441B0,0x44D3C0,
           0x4805A0,0x4DBCD0,0x4F6584,0x4F6439,0x4DB620,0x4DBD60,0x4DBE10)


def prepare(directory):
    directory = directory.resolve()
    root = directory / 'resources'
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    source = (ROOT / 'App/GameData').resolve()

    def link_tree(target, child):
        assert target.parent.resolve().is_relative_to(root), target
        if child.is_dir():
            if target.is_symlink():
                target.unlink()
            target.mkdir(exist_ok=True)
            for entry in child.iterdir():
                link_tree(target / entry.name, entry)
        else:
            if target.is_symlink() and not target.exists():
                target.unlink()
            if not target.exists():
                target.symlink_to(child.resolve())

    for child in source.iterdir():
        link_tree(root / child.name, child)
    found = []
    for name, payload in entries():
        if name == 'LEVEL13/WORLDS/WORLD.WWD':
            (directory / 'WORLD13.WWD').write_bytes(payload)
        if name.startswith('LEVEL13/'):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            # Own overlay leaves only; never write through App/GameData links.
            if target.is_symlink():
                target.unlink()
            assert target.parent.resolve().is_relative_to(root)
            target.write_bytes(payload)
            found.append(name)
    assert (directory / 'WORLD13.WWD').exists()
    assert any('/IMAGES/' in name for name in found)
    assert any('/ANIS/REDTAIL/' in name for name in found)
    assert any('/SOUNDS/' in name for name in found)
    (directory / 'physical-assets.json').write_text(json.dumps(
        dict(asset_sha256=verify_assets(), files=found), indent=2) + '\n')


def string(machine, address):
    value = bytearray()
    for offset in range(256):
        byte = machine.read(address + offset, 1)
        if byte == b'\0':
            return value.decode('ascii')
        value.extend(byte)
    raise AssertionError('Unterminated physical dictionary key')


def reference(profile):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    mapped = {0x10000000}

    def map_span(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page in mapped or any(begin <= page <= end for begin, end, _ in machine.uc.mem_regions()):
                continue
            machine.uc.mem_map(page, 4096)
            mapped.add(page)

    # Check static vtable/constant/string values against the authenticated image.
    # Registry arrays and globals are live scene inputs, not immutable metadata.
    reviewed = [(0x50F264, 0x4c), (0x50F358, 8), (0x510020, 4)]
    addresses = (0x522D54, 0x522D48, 0x523268, 0x5234EC)
    audit(ROOT / "work/native-object-connections/red_tail")
    reviewed += [(address, len(string(machine, address).encode('ascii')) + 1)
                 for address in addresses]
    original_metadata = {address: machine.read(address, size) for address, size in reviewed}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data))
        machine.write(address, data)
    for address, data in original_metadata.items():
        assert machine.read(address, len(data)) == data, f'Native metadata differs from original at {address:#x}'
    actor, state = profile['actor'], profile['state']
    allocations = iter(profile['allocations'])
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    required = {'LEVEL_REDTAIL', 'LEVEL_REDTAIL_IDLE', 'LEVEL_REDTAIL_KILLFALL'}
    assert required <= {name for _, name in bindings}
    assert all(value for (_, name), value in bindings.items() if name in required)
    calls, services, allocated, rng = [], [], [], []
    freed = []
    # The extra entry is an inlined C++ body; independently require it and its
    # descendants rather than treating a native observer omission as execution.
    inlined = []

    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append(
            [a, 0 if a in (0x4F63EC, 0x4DC870, 0x48CF50) else m.register(UC_X86_REG_ECX)]))
    for function in (0x4A48E0, 0x4A49B0, 0x4F6286, 0x4A3050, 0x4F6974):
        machine.intercept(function)
    # The scene has its own physical import entry identities. Intercept those
    # exact target tokens without rewriting import slots or game instructions.
    imports = {}
    for slot in (0x546D5C, 0x546CDC, 0x546CD4, 0x5469E8):
        target = machine.words(slot, 1)[0]
        imports[target] = slot
        map_span(target, 1)
        machine.intercept(target)

    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        word = lambda offset: m.words(stack + offset, 1)[0]
        slot = imports.get(address, address)
        if address == 0x4A48E0:
            count = word(4)
            row = next(allocations)
            assert count == row['count']
            allocated.append(count)
            map_span(row['token'], count)
            m.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count])
            m.return_from_external(row['token'], 0)
        elif address == 0x4A49B0:
            token = word(4)
            assert token in [row['token'] for row in profile['allocations']] and token not in freed
            freed.append(token)
            m.return_from_external(0, 0)
        elif address == 0x4F6286:
            name_token, output = m.words(stack + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_token)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token))
            services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4F6974:
            m.return_from_external(m.words(m.register(UC_X86_REG_ECX), 1)[0], 4)
        elif address == 0x4A3050:
            value = rng.pop(0)
            services.append(['rand', value])
            m.return_from_external(value, 0)
        elif slot in (0x546D5C, 0x546CDC):
            destination = word(4)
            values = list(m.words(stack + 8, 4)) if slot == 0x546D5C else [0] * 4
            m.write(destination, struct.pack('<4I', *values))
            services.append(['rectangle', destination, *values] if slot == 0x546D5C
                            else ['empty-rectangle', destination])
            m.return_from_external(1, 20 if slot == 0x546D5C else 4)
        elif slot == 0x546CD4:
            rectangle, raw_x, raw_y = m.words(stack + 4, 3)
            x, y = struct.unpack('<ii', struct.pack('<II', raw_x, raw_y))
            left, top, right, bottom = struct.unpack('<iiii', m.read(rectangle, 16))
            result = int(left <= x < right and top <= y < bottom)
            services.append(['point-in-rectangle', rectangle, raw_x, raw_y, result])
            m.return_from_external(result, 12)
        elif slot == 0x5469E8:
            pointer = word(4)
            value = (m.words(pointer, 1)[0] - 1) & 0xffffffff
            m.write(pointer, struct.pack('<I', value))
            m.return_from_external(value, 4)
        else:
            raise AssertionError(f'Unresolved physical boundary {address:#x}')

    machine.on_external = external
    outputs = []
    machine.reset_x87()
    machine.set_x87_state(0x23F, 0, [])
    for step in profile['steps']:
        calls.clear(); services.clear()
        rng[:] = step['random']
        machine.write(state + 0x1C, struct.pack('<I', step['command']))
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[actor])
        assert result.completed, (profile['name'], step['command'], result)
        assert not rng, 'Original did not consume the same RNG calls'
        outputs.append(dict(command=step['command'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex())
                   for span in step['spans']]))
    # The genuine shared enemy constructor binds both registered secondary
    # logics. Their source allocations and bytes are part of this comparison.
    assert allocated == [0x508, 0x174, 0x174], allocated
    assert next(allocations, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0, 1000, 29, 30)

    result = dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)
    if profile['retire']:
        helper = machine.words(state + 0x18, 1)[0]
        retired = machine.call(0x4805a0, ecx=helper, arguments=[1])
        assert retired.completed and freed == [helper], retired
        result['retirement'] = dict(helper=helper, hex=machine.read(helper, 0x508).hex())
    return result


def verify_world_projection(profile, data):
    """Independent raw WWD check of the existing scene-owned collision world."""
    def word(raw, offset):
        return struct.unpack_from('<I', raw, offset)[0]
    assert word(data, 0) == 1524
    offset, count, description_offset = word(data, 736), word(data, 732), word(data, 740)
    raw = data[:offset] + zlib.decompress(data[offset:]) if word(data, 8) & 2 else data
    if word(data, 8) & 2:
        assert len(raw) - offset == word(data, 744)
    planes = [offset + i * 160 for i in range(count)]
    plane = next(at for at in planes if word(raw, at + 8) & 1)
    tw, th, width, height = struct.unpack_from('<4I', raw, plane + 88)
    cells_at = word(raw, plane + 132)
    segments = [(row['address'], bytes.fromhex(row['hex'])) for row in profile['segments']]
    def read(address, size):
        for start, block in segments:
            if start <= address and address + size <= start + len(block):
                return block[address - start:address - start + size]
        raise AssertionError(f'Projection span missing {address:#x}+{size}')
    def get(address):
        return struct.unpack('<I', read(address, 4))[0]
    world = get(get(profile['actor'] + 12) + 0x24)
    handlers, tilemap = get(world + 0x4c), get(world + 0x5c)
    assert get(tilemap + 0x30) == width * tw and get(tilemap + 0x34) == height * th
    assert get(tilemap + 0x8c) == tw.bit_length() - 1
    assert get(tilemap + 0x90) == th.bit_length() - 1
    assert read(get(tilemap + 0x20), width * height * 4) == raw[cells_at:cells_at + width * height * 4]
    assert list(struct.unpack('<' + 'I' * height, read(get(tilemap + 0x24), height * 4))) == [i * width for i in range(height)]
    assert word(raw, description_offset) == 32
    n = word(raw, description_offset + 8)
    at = description_offset + 32
    for index in range(n):
        kind = word(raw, at)
        assert kind in (1, 2)
        # The original 4cb700 allocator chooses these vtables, then +14
        # invokes 4d5840/4d5c30: 3/8 WWD words at +8 copied to object +4.
        vtable, words = (0x513980, 3) if kind == 1 else (0x5139c8, 8)
        token = get(handlers + index * 4)
        assert get(token) == vtable
        assert read(token + 4, words * 4) == raw[at + 8:at + 8 + words * 4], index
        at += 20 if kind == 1 else 40
    program = claw()
    def original(address, size):
        section = next(s for s in program.sections if s.address <= address and address + size <= s.address + len(s.data))
        return section.data[address - section.address:address - section.address + size]
    for vtable, initializer, point in ((0x513980, 0x4d5840, 0x4cddc0), (0x5139c8, 0x4d5c30, 0x4cde10)):
        assert struct.unpack('<I', original(vtable + 0x14, 4))[0] == initializer
        assert struct.unpack('<I', original(vtable + 0x20, 4))[0] == point
        assert get(vtable + 0x20) == point



def comparable_calls(step):
    # The ordinary native caller reserves its own frame. The temporary range
    # registry has the same constructor/grow/destructor identity, but no
    # consumer observes its absolute stack address. Keep raw calls in evidence;
    # compare this one local by identity while actor/helper addresses stay exact.
    calls = step['calls']
    local_functions = (0x4DBE10, 0x4DB620, 0x4DBCD0)
    local = [(function, receiver) for function, receiver in calls
             if function in local_functions and 0x01FF0000 <= receiver < 0x02010000]
    if step['command'] == 0:
        assert [function for function, _ in local] == list(local_functions), local
        assert len({receiver for _, receiver in local}) == 1, local
        assert local[0][1] + 44 <= 0x02010000, local
    else:
        assert not local, local
    return [[function, 'temporary-range-registry' if (function, receiver) in local else receiver]
            for function, receiver in calls]


def compare(directory):
    source = json.loads((directory / 'town-native-input.json').read_text())
    native = json.loads((directory / 'town-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    for profile in source['profiles']:
        verify_world_projection(profile, (directory / 'resources/LEVEL13/WORLDS/WORLD.WWD').read_bytes())
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'town-original-output.json').write_text(json.dumps(original, indent=2) + '\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        assert expected.get('retirement') == actual.get('retirement'), 'Original scalar destructor bytes'
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            assert comparable_calls(ref) == comparable_calls(got), (actual['name'], got['command'], 'calls')
            for key in ('command', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key,
                    ref[key] if key != 'spans' else 'see original output',
                    got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert {0x4F63EC,0x47FF90,0x40E0D0,0x44C000,0x40E1B0,
            0x482430,0x4C96B0,0x4DC870,0x4827A0,0x47F800,0x4441B0} <= owners
    trace = native['trace']
    positions = [trace.index(value) for value in
                 ('loadGridObject', 'scene.gameplay', 'ClawNativeRedTail', '0x47f6e0')]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawNativeCanonicalHost.0x4805a0' in trace
    expected_controls = {'scene_registry_survives_world_load_and_actor_recreation',
        'scene_destruction_retires_all_allocations', 'same_scene_recreates_actor_and_helper',
        'retired_helper_rejected', 'missing_resource_service_rejected', 'replacement_actor_rejected',
        'foreign_helper_rejected', 'service_outside_callback_rejected',
        'primary_logic_4c80e0_retires_helper', 'primary_logic_4c80c0_retires_helper',
        'replacement_logic_teardown_rejected', 'foreign_scene_pointer_rejected'}
    assert expected_controls <= native['controls'].keys() and all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x47f6e0', native_owner='ClawNativeRedTail', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in
                    sorted(owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x4805a0, 0x4F4680})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Original Level 13 WWD actor attached to the Level 13 native scene and physical assets, five commands and same-scene recreation; no live-play claim')


def audit(directory):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from Tests.clawparity.program import claw

    program = claw()  # Verifies the reference executable hash.

    def read(address, count):
        for section in program.sections:
            offset = address - section.address
            if 0 <= offset and offset + count <= len(section.data):
                return section.data[offset:offset + count]
        raise ValueError(hex(address))

    calls = []
    expected = {
        0x47f718: (0x47f71d, "0x4f63ec"),
        0x47f733: (0x47f738, "0x47ff90"),
        0x47f74a: (0x47f74d, "dword ptr [eax + 0x10]"),
        0x47f757: (0x47f75a, "dword ptr [edx + 0x20]"),
        0x47f76c: (0x47f771, "0x4dc870"),
        0x47f77b: (0x47f77e, "dword ptr [edx + 0x1c]"),
    }
    for instruction in Cs(CS_ARCH_X86, CS_MODE_32).disasm(read(0x47f6e0, 0xb7), 0x47f6e0):
        if instruction.mnemonic == "call":
            assert expected[instruction.address] == (instruction.address + instruction.size, instruction.op_str)
            calls.append(dict(site=hex(instruction.address), continuation=hex(instruction.address + instruction.size), target=instruction.op_str))
    assert len(calls) == len(expected)
    targets = {offset: struct.unpack("<I", read(0x50f264 + offset, 4))[0]
               for offset in (0, 4, 8, 12, 16, 28, 32)}
    assert targets == {0: 0x4805a0, 4: 0x4827a0, 8: 0x47f800, 12: 0x44d3c0,
                       16: 0x40e1b0, 28: 0x4c96b0, 32: 0x482430}
    dispatch = (ROOT / "Sources/ClawCanonicalDispatch.h").read_text()
    owners = {}
    for address in sorted({0x47f6e0, 0x47ff90, 0x40e0d0, 0x4dc870, 0x4f63ec, *targets.values()}):
        row = re.search(r'\{0x%08xu,[^"\n]+"([^"\n]+)"[^\n]*' % address, dispatch)
        assert row, hex(address)
        owners[hex(address)] = row.group(1)
    host = (ROOT / "Sources/ClawNativeCanonicalHost.swift").read_text()
    memory = (ROOT / "Sources/ClawNativeMfcMemory.swift").read_text()
    host_new = host.split("private func invokeObjectNew(", 1)[1].split("// The admitted ordinary body", 1)[0]
    memory_new = memory.split("func allocateObject(", 1)[1].split("performingService=true", 1)[0]
    # These are source inspection observations, not execution results.
    blockers = []
    if "0x47f6e0" not in host_new:
        blockers.append("ClawNativeCanonicalHost.invokeObjectNew has no RedTail callback election")
    if "0x47f6e0" not in memory_new:
        blockers.append("ClawNativeMfcMemory.allocateObject has no RedTail root/0x508 allocation election")
    result = dict(command="red-tail-prerequisite-audit", status="blocked" if blockers else "needs-transport-comparison",
                  reference_sha256=program.sha256, callback="0x47f6e0", helper_size="0x508",
                  constructor="0x47ff90", vtable="0x50f264", calls=calls,
                  virtual_targets={hex(k): hex(v) for k, v in targets.items()}, canonical_owners=owners,
                  blockers=blockers, connection_comparison=False)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "prerequisites.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 2 if blockers else 0



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-prerequisites", action="store_true", required=True)
    parser.add_argument("directory", nargs="?", type=Path, default=ROOT / "work/native-object-connections/red_tail")
    args = parser.parse_args()
    raise SystemExit(audit(args.directory))
