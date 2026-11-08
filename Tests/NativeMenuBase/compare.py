"""Compare the native constructor/base join with the pinned original prefix.

Game constructors and 45ace0 -> 48f0d0 execute unchanged. Only allocation,
Win32 string/atomic/rectangle operations, formatting, native readiness and the
real filesystem directory transport are supplied. Execute 42a000 unchanged
with the dimensions published by native display startup. Resolve the real
STATES_MENU/SOUNDS directories and load their real WAV data through the
constructed scene sound owner, then stop at image-directory lookup 4b7cd0
before IFC parsing. This is prefix evidence, not a constructed menu.
"""
import json
from pathlib import Path
import struct
import sys

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_EBX
from Tests.clawparity.program import claw


def compare(witness, root):
    program = claw()  # Hash verification is mandatory before loading sections.
    machine = Uc(UC_ARCH_X86, UC_MODE_32)
    machine.mem_map(program.base, (program.size + 4095) & ~4095)
    for section in program.sections:
        machine.mem_write(section.address, section.data)
    machine.mem_map(0, 4096)  # Original x86 exception-chain head.
    machine.mem_map(0x02000000, 0x10000)
    machine.mem_map(0x61000000, 0x1000000)
    machine.mem_map(0x63000000, 0x1000000)
    machine.mem_map(0x70000000, 4096)
    machine.mem_map(0x6E130000, 4096)

    def word(token):
        return struct.unpack('<I', machine.mem_read(token, 4))[0]

    def put(token, value):
        machine.mem_write(token, struct.pack('<I', value & 0xFFFFFFFF))

    def text(token):
        data = bytearray()
        while len(data) < 1024:
            byte = machine.mem_read(token + len(data), 1)
            if byte == b'\0':
                return data.decode('ascii')
            data.extend(byte)
        raise AssertionError('Unterminated source string')

    def returned(value, pop=0):
        stack = machine.reg_read(UC_X86_REG_ESP)
        machine.reg_write(UC_X86_REG_EAX, value)
        machine.reg_write(UC_X86_REG_EIP, word(stack))
        machine.reg_write(UC_X86_REG_ESP, stack + 4 + pop)

    put(0, 0xFFFFFFFF)
    imports = {}
    for index, (slot, name) in enumerate(program.imports.items()):
        target = 0x70000100 + index
        put(slot, target)
        imports[target] = name
    allocations = [(witness['menu'], 0x2C8)] + [
        (a['token'], a['bytes']) for a in witness['allocations']]
    dynamic = 0x63000000
    def alloc(size):
        nonlocal dynamic
        token = dynamic
        dynamic += (size + 31) & ~15
        return token

    phase = 'constructor'
    stopped = False
    allocated = 0
    visited = set()
    resolved = []
    base_calls = []
    application_result = None
    sound_events = []
    sound_count = None
    semantic = {0x4ca440,0x4ca3b0,0x4b68e0,0x4b6900,0x4b6920,0x4b6940,0x4b6960,0x4b6980,0x4b61b0,0x4f6286,0x4f62a8,0x4c8850,0x4c88b0,0x4ca670}
    buffers = {}
    loaded = {}
    current_key = None
    missing_path = None
    released = []
    # The original PCM path executes through real RIFF parsing/copying. Only
    # DirectSound buffer creation, properties, locking and release are physical.
    device, device_vtable, buffer_vtable = alloc(4), alloc(16), alloc(80)
    put(device,device_vtable);put(device_vtable+12,0x70000a00)
    for offset in (8,0x18,0x1c,0x20,0x2c,0x4c):put(buffer_vtable+offset,0x70000b00+offset)


    def hook(_, address, size, user):
        nonlocal stopped, allocated, application_result, sound_count, current_key
        visited.add(address)
        stack = machine.reg_read(UC_X86_REG_ESP)
        if phase == 'base' and address in (0x6E130000, 0x4A3920, 0x4B7F20, 0x42A000, 0x4B68C0, 0x4CA440, 0x4B7CD0) and not (address == 0x4ca440 and 0x4ca440 <= word(stack) < 0x4ca606):
            base_calls.append(address)
        if phase == 'base' and address == 0x42A000:
            assert machine.reg_read(UC_X86_REG_ECX) == witness['application']
            assert word(stack + 4) == 0
        nested_loader = address == 0x4ca440 and 0x4ca440 <= word(stack) < 0x4ca606
        if phase in ('base','cleanup','disabled') and address in semantic and not nested_loader:
            sound_events.append(address)
        if phase == 'base' and address == 0x4CA3B0:
            current_key = text(word(stack+4))
        if phase == 'base' and address == 0x4CA440 and not nested_loader:
            assert machine.reg_read(UC_X86_REG_ECX) == witness['soundManager'] != 0
            assert word(stack+4) == witness['soundDirectory']['token']
            assert [word(stack+i) for i in (8,12)] == [0x534938,0x523728]
        if phase == 'base' and address == 0x4B7CD0:
            sound_count = machine.reg_read(UC_X86_REG_EAX)
            assert text(word(stack+4)) == 'IMAGES'
            stopped = True
            machine.emu_stop()
        elif phase == 'sound-constructor' and address == 0x4cec8b:
            stopped = True
            machine.emu_stop()
        elif address == 0x42ABF0 and phase == 'constructor':
            stopped = True
            machine.emu_stop()
        elif phase == 'base' and address == 0x42A052:
            application_result = machine.reg_read(UC_X86_REG_EAX)
        elif address in (0x4F63EC,0x4A48E0):
            count = word(stack+4)
            if phase == 'constructor':
                token, expected = allocations[allocated]
                assert count == expected
                allocated += 1
            elif phase == 'sound-constructor':
                assert count == 52
                token = witness['soundManager']
                machine.mem_write(token,b'\xa5'*52)
            else:
                token = alloc(count)
            returned(token)
        elif address == 0x4F6428:
            released.append(word(stack+4))
            returned(0)
        elif address in (0x4A7BC0,0x4A7C40):
            returned(0)
        elif address == 0x70000a00:
            desc, output = word(stack+8),word(stack+12)
            size,fmt = word(desc+8),word(desc+16)
            token,pcm = alloc(4),alloc(size)
            put(token,buffer_vtable);put(output,token)
            buffers[token] = dict(pcm=pcm,size=size,rate=word(fmt+4),name=current_key)
            returned(0,16)
        elif 0x70000b00 <= address < 0x70000b50:
            offset = address-0x70000b00
            buffer = buffers[word(stack+4)]
            if offset in (0x18,0x1c,0x20):
                put(word(stack+8),buffer['rate'] if offset==0x20 else 0)
                returned(0,8)
            elif offset == 0x2c:
                count = word(stack+12)
                assert count == buffer['size'] and word(stack+8) == 0
                put(word(stack+16),buffer['pcm']);put(word(stack+20),count)
                put(word(stack+24),0);put(word(stack+28),0)
                returned(0,32)
            elif offset == 0x4c:
                loaded[buffer['name']] = list(machine.mem_read(buffer['pcm'],buffer['size']))
                returned(0,20)
            elif offset == 8:
                del buffers[word(stack+4)]
                returned(0,4)
            else:raise AssertionError(offset)
        elif address == 0x6E130000:
            assert phase == 'base'
            assert machine.reg_read(UC_X86_REG_ECX) == witness['application']
            returned(1)  # Native readiness; actual surfaces are checked in Swift.
        elif address == 0x4A3920:
            assert phase == 'base'
            target, fmt, argument = (word(stack + i) for i in (4, 8, 12))
            if text(fmt) == '%s%s%s':
                value = ''.join(text(word(stack+i)) for i in (12,16,20)).encode('ascii')
            else:
                signed = struct.unpack('<i', struct.pack('<I', argument))[0]
                value = (text(fmt) % signed).encode('ascii')
            machine.mem_write(target, value + b'\0')
            returned(len(value))
        elif address in (0x4B7F20, 0x4B68C0):
            assert phase == 'base'
            name = text(word(stack + 4))
            if address == 0x4B7F20:
                assert machine.reg_read(UC_X86_REG_ECX) == witness['resourceRoot']
                assert name in ('LEVEL1', 'STATES_MENU')
                path = name.replace('_', '/')
            else:
                assert name == 'SOUNDS'
                assert machine.reg_read(UC_X86_REG_ECX) == word(witness['menu'] + 32)
                path = 'STATES/MENU/SOUNDS'
            if path == missing_path:
                returned(0,4)
                return
            assert (root / path).is_dir()
            resolved.append(name)
            returned(next(d['token'] for d in witness['directories'] if d['path'] == path), 4)
        elif address in imports:
            name = imports[address].split('!')[1]
            if name == 'SetRect':
                target = word(stack + 4)
                for index in range(4):
                    put(target + 4 * index, word(stack + 8 + 4 * index))
                returned(1, 20)
            elif name == 'lstrlenA':
                returned(len(text(word(stack + 4))), 4)
            elif name in ('InterlockedIncrement', 'InterlockedDecrement'):
                target = word(stack + 4)
                value = (word(target) + (1 if name == 'InterlockedIncrement' else -1)) & 0xFFFFFFFF
                put(target, value)
                returned(value, 4)
            else:
                raise AssertionError(f'Unprovided platform service: {imports[address]}')

    machine.hook_add(UC_HOOK_CODE, hook)

    def run(function, receiver, arguments, boundary=True):
        nonlocal stopped
        stopped = False
        stack = 0x02008000
        for index, value in enumerate([0x70000080] + arguments):
            put(stack + index * 4, value)
        machine.reg_write(UC_X86_REG_ESP, stack)
        machine.reg_write(UC_X86_REG_ECX, receiver)
        machine.emu_start(function, 0x70000080, count=5000000)
        assert stopped == boundary, f'Original did not reach the elected boundary: {function:x}, PC {machine.reg_read(UC_X86_REG_EIP):x}'
        if not boundary:
            assert machine.reg_read(UC_X86_REG_EIP) == 0x70000080, 'Original did not return'

    def equal(token, expected, label):
        actual = bytes(machine.mem_read(token, len(expected)))
        expected = bytes(expected)
        differences = [i for i, (a, b) in enumerate(zip(actual, expected)) if a != b]
        assert not differences, f'{label}: differing byte offsets {differences[:20]}'

    # Empty initial state, no retained previous state: run the actual factory.
    run(0x428C40, witness['application'], [5, 1, 1, 0])
    assert allocated == len(allocations)
    equal(witness['menu'], witness['constructor'], 'mode-5 state (712 bytes)')
    for allocation in witness['allocations']:
        equal(allocation['token'], allocation['data'], 'constructor child allocation')
    assert {0x40B5C0, 0x4DCC40, 0x4F5CBD}.issubset(visited)

    phase = 'sound-constructor'
    machine.reg_write(UC_X86_REG_ESI,witness['scene'])
    machine.reg_write(UC_X86_REG_EBP,0);machine.reg_write(UC_X86_REG_EBX,0)
    run(0x4cec34,0,[])
    assert word(witness['scene']+40) == witness['soundManager']
    assert word(witness['soundManager']+48) == 0xa5a5a5a5
    put(witness['scene']+32,witness['audioManager'])
    put(witness['audioManager']+120,1);put(witness['audioManager']+20,device)
    run(0x4ca280,witness['soundManager'],[1],boundary=False)
    equal(witness['soundManager'],witness['managerBefore'],'constructed and initialized sound manager')
    assert word(0x532c10) == 100
    for block in witness['resourceBlocks']+[witness['soundDirectory']]:
        machine.mem_write(block['token'],bytes(block['data']))
    for resource in witness['soundResources']:
        token = resource['token']
        original_bytes = (root/resource['path']).read_bytes()
        assert bytes(machine.mem_read(word(word(token+36)+32),word(token+20))) == original_bytes

    phase = 'base'
    machine.mem_write(witness['application'], bytes(witness['applicationBytes']))
    put(word(witness['application']) + 12, 0x6E130000)
    put(0x528A60, 1000)
    put(0x53EC44, 0)  # Same native application build-number profile.
    run(0x45ACE0, witness['menu'], [witness['application'], 1, 37])
    equal(witness['menu'], witness['bound'], 'initializer/base state (712 bytes)')
    assert word(0x537B58) == witness['menu']
    assert 0x48F0D0 in visited and 0x4DCDF0 not in visited
    assert 0x42A000 in visited and 0x42A060 not in visited and 0x429E10 not in visited
    assert application_result == witness['applicationResult'] == 1
    assert all(dimensions == [640, 480] for dimensions in witness['displayDimensions'])
    assert word(witness['application'] + 0x7c) == 640
    assert word(witness['application'] + 0x80) == 480
    equal(witness['application'], witness['applicationAfter'], 'application after size guard')
    assert base_calls == witness['baseCalls'], (base_calls, witness['baseCalls'])
    assert resolved == ['LEVEL1', 'STATES_MENU', 'SOUNDS'] and witness['boundary'] == 0x4B7CD0
    assert sound_events == witness['soundEvents'], (sound_events,witness['soundEvents'])
    assert sound_count == witness['soundCount'] == len(witness['soundResources']) > 0
    expected = {entry['name']:entry['pcm'] for entry in witness['soundEntries']}
    assert loaded == expected, 'PCM payload or name differs'
    manager = witness['soundManager']
    assert word(manager+28) == sound_count
    published = {}
    sound_tokens = []
    for bucket in range(word(manager+24)):
        node = word(word(manager+20)+bucket*4)
        while node:
            sound = word(node+12)
            sound_tokens.append(sound)
            published[text(word(node+8))] = word(sound+4)
            assert word(sound+12) == witness['scene'] and word(sound+16) != 0
            node = word(node)
    assert published == {entry['name']:entry['owner'] for entry in witness['soundEntries']}
    assert {0x4ca440,0x4ca3b0,0x4c8850,0x4b4a20,0x4b44f0,0x4f62a8}.issubset(visited)
    phase = 'cleanup'
    sound_events.clear()
    run(0x4ca2e0,manager,[],boundary=False)
    assert sound_events == witness['cleanupEvents'], (sound_events,witness['cleanupEvents'])
    assert word(manager+28) == 0 and word(manager+20) == 0 and word(manager+44) == 0
    assert not buffers and set(sound_tokens).issubset(released)
    phase = 'disabled'
    sound_events.clear()
    put(witness['scene']+32,0);put(manager+48,0xa5a5a5a5)
    run(0x4ca280,manager,[1],boundary=False)
    assert word(manager+48) == 1 and word(manager+44) == 0
    allocation_end = dynamic
    run(0x4ca440,manager,[witness['soundDirectory']['token'],0x534938,0x523728],boundary=False)
    assert machine.reg_read(UC_X86_REG_EAX) == 0 and dynamic == allocation_end
    assert sound_events == [0x4ca440]
    phase = 'base'
    for missing_path in ('STATES/MENU','STATES/MENU/SOUNDS'):
        sound_events.clear()
        run(0x45ace0,witness['menu'],[witness['application'],1,37],boundary=False)
        assert machine.reg_read(UC_X86_REG_EAX) == 0 and not sound_events
    return 52 + sum(len(pcm) for pcm in loaded.values()) + 712 * 2 + len(witness['applicationAfter']) + sum(a['bytes'] for a in witness['allocations'])


if __name__ == '__main__':
    witness = json.loads(Path(sys.argv[1]).read_text())
    from Tests.NativeMenuBase.error_compare import compare as compare_error
    compare_error(witness['errorBoundary'])
    count = compare(witness, Path(sys.argv[2]))
    print(f'PASS original/native menu join: {count} bytes across mode-5 constructor, children and 45ace0/48f0d0/42a000 prefix, constructed sound owner, actual menu WAV PCM and CString identity/count, and ordered services; next exact boundary 4b7cd0 image directory')
