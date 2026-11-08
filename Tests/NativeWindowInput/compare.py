"""Focused native replacement join; never a platform-family admission.

Run: work/test-env/bin/python -m Tests.NativeWindowInput.compare
The only original service is a deterministic pending-message queue replacing
PeekMessageA. Every other original call is rejected; no dispatch is permitted.
"""
import json
import random
import struct
import subprocess
import tempfile
from pathlib import Path

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from Tests.clawparity.program import claw

ROOT = Path(__file__).resolve().parents[2]
ENTRY, PEEK, STOP = 0x4B8910, 0x3000000, 0x3000100
RECEIVER, STACK = 0x3100000, 0x3208000


def original(program, profile):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(program.base, program.size)
    for section in program.sections:
        uc.mem_write(section.address, section.data)
    for base in (PEEK, RECEIVER, STACK - 0x8000):
        uc.mem_map(base, 0x10000)
    def put(at, *words):
        uc.mem_write(at, struct.pack('<' + 'I' * len(words), *words))
    def get(at, count=1):
        return struct.unpack('<' + 'I' * count, uc.mem_read(at, count * 4))
    put(0x546CAC, PEEK)
    assert program.imports[0x546CAC].endswith('!PeekMessageA')
    put(RECEIVER, 0xAABBCCDD, profile['windows'][0])
    put(STACK, STOP, profile['message'], profile['maximum'])
    uc.reg_write(UC_X86_REG_ECX, RECEIVER)
    uc.reg_write(UC_X86_REG_ESP, STACK)
    survivors, queries = list(profile['events']), []
    stopped = False
    def hook(machine, address, size, _):
        nonlocal stopped
        if address == STOP:
            stopped = True
            machine.emu_stop()
            return
        if address == PEEK:
            esp = machine.reg_read(UC_X86_REG_ESP)
            ret, output, window, low, high, flags = get(esp, 6)
            assert low == high == profile['message'] and flags == 1
            queries.append(window)
            found = next((i for i, event in enumerate(survivors)
                          if event['window'] == window and (low == 0 or event['message'] == low)), None)
            if found is not None:
                event = survivors.pop(found)
                put(output, window, event['message'], event['mask'], 0, 0, 0, 0)
                # A service may replace the window field between removals.
                put(RECEIVER + 4, profile['windows'][min(len(queries), len(profile['windows']) - 1)])
            machine.reg_write(UC_X86_REG_EAX, int(found is not None))
            machine.reg_write(UC_X86_REG_ESP, esp + 24)
            machine.reg_write(UC_X86_REG_EIP, ret)
            return
        assert ENTRY <= address <= 0x4B8950, f'Unexpected call/dispatch {address:#x}'
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(ENTRY, STOP + 1, count=100000)
    assert stopped and uc.reg_read(UC_X86_REG_ESP) == STACK + 12, 'thiscall2 return'
    assert get(RECEIVER)[0] == 0xAABBCCDD
    return dict(label=profile['label'], survivors=survivors, queries=queries)


def main():
    program = claw()  # Always verify the pinned binary before executing it.
    # The reviewed menu initializer, menu command, scene completion and special
    # command call sites still target this semantic-void compatibility entry.
    for site in (0x45B00E, 0x45B020, 0x45B4A6, 0x46B76D, 0x40AD9F):
        section = next(s for s in program.sections if s.address <= site < s.address + s.size)
        instruction = section.data[site-section.address:site-section.address+5]
        assert instruction[0] == 0xE8 and site + 5 + struct.unpack('<i', instruction[1:])[0] == ENTRY
    rng = random.Random(8910)
    def event(i, window=1, message=0x100):
        return dict(window=window, message=message, mask=i, pressed=message in (0x100, 0x201))
    mixed = [event(i, 1 + i % 2, [0x100, 0x101, 0x201, 0x202][(i // 2) % 4]) for i in range(600)]
    profiles = []
    for message in (0, 0x100, 0x101, 0x201, 0x202):
        for maximum in (0xFFFFFFFF, 0x80000000, 0, 1, 64, 0x7FFFFFFF):
            for label, events in [('empty', []), ('mixed', mixed), ('exhausted', mixed[:9]),
                                  ('no-match', [event(1, 2)])]:
                profiles.append(dict(label=f'{label}-{message}-{maximum}', events=events,
                                     message=message, maximum=maximum, windows=[1]))
    profiles.append(dict(label='receiver-reload', events=mixed, message=0x100, maximum=64, windows=[1, 2] * 32))
    for i in range(40):
        events = [event(j, rng.choice([1, 2]), rng.choice([0x100, 0x101, 0x201, 0x202])) for j in range(rng.randrange(150))]
        profiles.append(dict(label=f'random-{i}', events=events, message=rng.choice([0, 0x100, 0x201]),
                             maximum=rng.choice([0, 1, 64]), windows=[rng.choice([1, 2]) for _ in range(64)]))
    build = ROOT / 'work/build'
    build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='message-drain-', dir=build) as temp:
        temp = Path(temp)
        inputs, outputs, binary = temp / 'profiles.json', temp / 'witness.json', temp / 'native'
        inputs.write_text(json.dumps(profiles))
        subprocess.run(['xcrun', 'swiftc', '-O', str(ROOT / 'Sources/ClawNativeWindowInputQueue.swift'),
                        str(Path(__file__).with_name('main.swift')), '-o', str(binary)], check=True, cwd=ROOT)
        subprocess.run([str(binary), str(inputs), str(outputs)], check=True)
        native = json.loads(outputs.read_text())
        assert len(native) == len(profiles)
        for profile, actual in zip(profiles, native):
            expected = original(program, profile)
            assert actual == expected, profile['label']
    print(json.dumps(dict(status='pass', comparison='original/native message drain', profiles=len(profiles),
                          admission=False, binary_sha256=program.sha256)))


if __name__ == '__main__':
    main()
