"""Numbered object scene join against the authenticated original."""
import json
import struct
import zlib
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACKS={0x461FE0,0x462000,0x462020,0x4622F0,0x462310,0x49EAD0,0x49EAF0,0x49EB10}
BASES={0x461D50,0x462040,0x49E810}
OBSERVE={address:(False,1) for address in BASES}
OBSERVE.update({0x40F680:(True,1),0x49E470:(False,2),0x49E4B0:(False,3),0x4C79E0:(True,2),0x4C82A0:(True,1),0x4CA610:(True,4)})
PHYSICAL=set()


def prepare(directory):
    directory=directory.resolve()
    root=directory/'resources'
    root.mkdir(exist_ok=True)
    def link_tree(target,source):
        assert target.parent.resolve().is_relative_to(root)
        if source.is_dir():
            if target.is_symlink(): target.unlink()
            target.mkdir(exist_ok=True)
            for child in source.iterdir(): link_tree(target/child.name,child)
        elif not target.exists():
            if target.is_symlink(): target.unlink()
            target.symlink_to(source.resolve())
    for source in (ROOT/'App/GameData').resolve().iterdir(): link_tree(root/source.name,source)
    found=[]
    for name,payload in entries():
        if name in {f'LEVEL{level}/WORLDS/WORLD.WWD' for level in (3,4,9,12,14)}:
            (directory/('WORLD'+name.split('/')[0][5:]+'.WWD')).write_bytes(payload)
        selected=(name.startswith('LEVEL3/IMAGES/FLOORSPIKES2/') or name.startswith('LEVEL9/IMAGES/FLOORSAW/') or name.startswith('LEVEL9/ANIS/SAWBLADE/') or name.startswith('LEVEL4/IMAGES/STEPPINGSTONE/') or name in {'GAME/ANIS/FORWARD100.ANI','GAME/ANIS/BACKWARD100.ANI','GAME/ANIS/FORWARD50.ANI','GAME/ANIS/BACKWARD50.ANI'})
        if selected:
            target=root/(name.replace(name.split('/')[0]+'/', 'LEVEL1/',1) if name.startswith('LEVEL') else name)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.is_symlink(): assert target.read_bytes()==payload,name
            else: target.write_bytes(payload)
            found.append(name)
            if name.startswith('LEVEL'):
                actual=root/name;actual.parent.mkdir(parents=True,exist_ok=True)
                if actual.is_symlink(): assert actual.read_bytes()==payload,name
                else: actual.write_bytes(payload)
        if name in {f'LEVEL{level}/PALETTES/MAIN.PAL' for level in (3,4,9)}:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            if target.is_symlink(): assert target.read_bytes()==payload,name
            else: target.write_bytes(payload)
    assert sum('/IMAGES/FLOORSPIKES2/' in name for name in found)==6
    assert sum('/IMAGES/FLOORSAW/' in name for name in found)==20
    assert sum('/IMAGES/STEPPINGSTONE/' in name for name in found)==6
    # The shared service grid is the authenticated Level 1 world for every
    # profile; original source-level WWD records stay in WORLD{N}.WWD above.
    # Never overwrite a GameData link when providing this controlled grid.
    grid=(ROOT/'App/GameData/LEVEL1/WORLDS/WORLD.WWD').read_bytes()
    for level in (3,4,9):
        target=root/f'LEVEL{level}/WORLDS/WORLD.WWD'
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_symlink(): target.unlink()
        target.write_bytes(grid)
    (directory/'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(),files=found),indent=2)+'\n')


def string(machine, address):
    result = bytearray()
    for offset in range(256):
        value = machine.read(address + offset, 1)
        if value == b'\0': return result.decode('ascii')
        result.extend(value)
    raise AssertionError('Unterminated resource key')


def reference(profile):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    pages = {page for start, end, _ in machine.uc.mem_regions()
             for page in range(start, end + 1, 4096)}
    def mapped(address, count):
        for page in range(address & ~4095, (address + count + 4095) & ~4095, 4096):
            if page not in pages:
                machine.uc.mem_map(page, 4096); pages.add(page)
    def put(address, *words):
        machine.write(address, struct.pack('<' + 'I' * len(words), *words))
    literals = {address: string(machine, address) for address in (0x529584,0x52959C,0x5295B0,0x5295C0,0x5295D4,0x5295E8,0x5295FC,0x529610,0x529624,0x52DD7C,0x52DD04,0x52DD14,0x52DD8C)}
    constant = machine.read(0x513768, 4)
    for segment in profile['segments']:
        data = bytes.fromhex(segment['hex'])
        mapped(segment['address'], len(data)); machine.write(segment['address'], data)
    assert {address: string(machine, address) for address in literals} == literals
    assert machine.read(0x513768, 4) == constant
    bindings = {(row['receiver'], row['name']): row['token'] for row in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    calls, services, physical = [], [], []
    allocations = iter(profile['allocations'])
    for address, (thiscall, count) in OBSERVE.items():
        def observe(m, function, thiscall=thiscall, count=count):
            calls.append(dict(function=function, receiver=m.register(UC_X86_REG_ECX) if thiscall else 0,
                arguments=list(m.words(m.register(UC_X86_REG_ESP) + 4, count))))
        machine.observe(address, observe)
    for address in PHYSICAL | {0x4F6286, 0x4A48E0}:
        if address in PHYSICAL:
            mapped(address, 4); machine.write(address, b'\xc3')
        machine.intercept(address)
    def external(m, address):
        sp = m.register(UC_X86_REG_ESP)
        if address == 0x4F6286:
            name_pointer, output = m.words(sp + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_pointer)
            token = bindings[(receiver, name)]
            put(output, token); services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4A48E0:
            count = m.words(sp + 4, 1)[0]
            row = next(allocations); assert row['count'] == count == 56
            mapped(row['token'], count); machine.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count]); m.return_from_external(row['token'], 0)
        else:
            assert physical, f'Unexpected physical service {address:#x}'
            event = physical.pop(0); assert event['function'] == address
            args = list(m.words(sp + 4, len(event['arguments'])))
            if 'output' in event:
                assert args[:-1] == event['arguments'][:-1]
                value = event['output']
                if address == 0x71020014:
                    mapped(value, 16); put(value, m.words(args[1], 1)[0])
                put(args[-1], value)
            else: assert args == event['arguments'], (args, event)
            m.return_from_external(event['result'], len(args) * 4)
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear(); physical[:] = step['physical']
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(step['callback'], arguments=[step['actor']])
        assert result.completed and not physical, (profile['name'], step['name'])
        if step['callback'] in BASES:
            assert calls[0]['function'] == step['callback']
            calls.pop(0)  # Native tracing observes dependency entries, not its invoked root.
        outputs.append(dict(name=step['name'], callback=step['callback'], actor=step['actor'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert next(allocations, None) is None
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    inputs=json.loads((directory/'object-variants-native-input.json').read_text())
    actual=json.loads((directory/'object-variants-native-output.json').read_text())
    assert len(inputs['profiles'])==len(actual['profiles'])==3
    worlds=[]
    for level in (3,4,9,12,14):
        raw=(directory/f'WORLD{level}.WWD').read_bytes()
        offset=struct.unpack_from('<I',raw,736)[0]
        if struct.unpack_from('<I',raw,8)[0]&2: raw=raw[:offset]+zlib.decompress(raw[offset:])
        worlds.append(raw)
    for profile in inputs['profiles']:
        for record in profile['recordProvenance']:
            data=bytes.fromhex(record['sourceEncoded']);offset=record['sourceRecordOffset']
            assert any(raw[offset:offset+len(data)]==data for raw in worlds),record['logic']
            assert struct.unpack_from('<ii',data,20)==(record['sourceX'],record['sourceY'])
            assert record['controlledX']==record['controlledY']==1024
    expected=[reference(profile) for profile in inputs['profiles']]
    (directory/'object-variants-original-output.json').write_text(json.dumps(expected,indent=2)+'\n')
    comparisons=0;tested=set()
    for native,original in zip(actual['profiles'],expected,strict=True):
        assert native['name']==original['name']
        for got,want in zip(native['steps'],original['steps'],strict=True):
            for key in ('name','callback','actor','calls','services','spans'):
                assert got[key]==want[key],(native['name'],got['name'],key)
            tested.add(got['callback']);comparisons+=1
        variant_steps=[step for step in native['steps'] if step['callback'] in CALLBACKS]
        assert variant_steps and all(any(call['function'] in BASES for call in step['calls']) for step in variant_steps)
        assert any(step['callback'] in BASES for step in native['steps'])
        for callback in {step['callback'] for step in variant_steps}:
            names={step['name'].split(':')[-1] for step in variant_steps if step['callback']==callback}
            assert {'initialize','active-transition','physical-animation'} <= names
            physical_steps=[step for step in variant_steps if step['callback']==callback and step['name'].endswith(':physical-animation')]
            assert len(physical_steps)==1 and any(call['function']==0x4C79E0 for call in physical_steps[0]['calls']), (native['name'],hex(callback),'physical animation boundary')
            assert any(event[0]=='registry' for event in physical_steps[0]['services'])
    assert CALLBACKS|BASES <= tested
    trace=actual['trace']
    for callback in CALLBACKS:
        positions=[trace.index(item) for item in ('loadGridObject','scene.gameplay','ClawNativeObjectVariants',hex(callback))]
        assert positions==sorted(positions)
    executed={call['function'] for profile in actual['profiles'] for step in profile['steps'] for call in step['calls']}
    assert BASES|{0x49E470,0x49E4B0,0x4C79E0} <= executed
    required={'missing_service_rejected','replacement_actor_rejected','replacement_private_state_rejected',
              'service_outside_callback_rejected','scene_destruction_retires_actor_and_private_state','retired_owner_rejected',
              'callback_identity_preserved','variant_globals_shared_with_bases'}
    assert required <= actual['controls'].keys()
    assert all(actual['controls'].values()),actual['controls']
    assert actual['faults']==0 and not actual['unresolvedDependencies']
    return dict(original_callback=[hex(callback) for callback in sorted(CALLBACKS)],native_owner='ClawNativeObjectVariants',
        comparisons=comparisons,exercised_service_edges=[hex(address) for address in sorted(executed|{0x4F6286})],
        controls=actual['controls'],faults=0,unresolved_dependencies=[],
        evidence='Original numbered WWD callbacks interleaved with base callbacks on the scene heap, silent physical resource services; no live-play claim',
        executable_sha256=claw().sha256,asset_sha256=verify_assets())
