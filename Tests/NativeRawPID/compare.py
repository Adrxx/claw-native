#!/usr/bin/env python3
"""Replay native display witnesses through the pinned original raw PID entry.

Only the physical Lock/Unlock boundary is replaced. The original 0x4b9730
wrapper and complete 0x4c00b0 loop execute, using the native allocation tokens.
This is connection evidence, not a new admission or app acceptance claim.
"""
import base64
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'Tests')]
from Tests.clawparity.program import claw
from original_v10 import OriginalV10
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

LOCK, UNLOCK = 0x6e120064, 0x6e120080


def main(path):
    claw()
    witness = json.loads(path.read_text())
    assert len(witness['cases']) == 17 and witness['controls'] == 13, 'Incomplete native witness'
    original = OriginalV10(ROOT / 'Original/claw10/CLAW.EXE')
    u = original.u
    mapped = {page for start, end, _ in u.mem_regions() for page in range(start & ~4095, end + 1, 4096)}

    def map_bytes(address, count):
        for page in range(address & ~4095, (address + count + 4095) & ~4095, 4096):
            if page not in mapped:
                u.mem_map(page, 4096)
                mapped.add(page)

    map_bytes(LOCK, 128)
    events, objects, tokens, policy = [], [], {}, ''
    left = right = 0
    executed = set()

    def put(address, values):
        u.mem_write(address, struct.pack('<' + 'I' * len(values), *values))

    def snapshots():
        return [dict(name=o['name'], token=o['token'],
                     bytes=base64.b64encode(bytes(u.mem_read(o['token'], len(base64.b64decode(o['bytes']))))).decode())
                for o in objects]

    def hook(_, address, size, user):
        if 0x4c00b0 <= address < 0x4c0450:
            executed.update(range(address, address + size))
        if address not in (0x4b9730, LOCK, UNLOCK):
            return
        sp = u.reg_read(UC_X86_REG_ESP)
        count = {0x4b9730: 1, LOCK: 5, UNLOCK: 2}[address]
        args = original.read_words(sp + 4, count)
        events.append(dict(function=address, receiver=u.reg_read(UC_X86_REG_ECX) if address == 0x4b9730 else 0,
                           arguments=args, memory=snapshots()))
        if address == 0x4b9730:
            return  # Execute the real lock wrapper, including its post-call read.
        if address == LOCK:
            assert args == [tokens['dd'], 0, tokens['surface'] + 12, 1, 0]
            descriptor = [0] * 27
            descriptor[0:5] = [108, 7, 16, 32, 32]
            descriptor[9], descriptor[21] = tokens['pixels'], 8
            put(args[2], descriptor)
            if policy == 'lock-reload':
                put(tokens['image'] + 4, [8, 5, tokens['replacement'], 45])
                put(tokens['image'] + 36, [1])
                put(tokens['source'], [left, 1, right, 4])
                put(tokens['destination'], [3, 2, 123, 456])
                put(tokens['surface'] + 28, [39])
                put(tokens['surface'] + 8, [tokens['dd2']])
            result = 0
        else:
            assert args == [tokens['dd2'] if policy == 'lock-reload' else tokens['dd'], 0]
            result = 0x88760001
        return_pc = original.read_words(sp, 1)[0]
        u.reg_write(UC_X86_REG_EAX, result)
        u.reg_write(UC_X86_REG_ESP, sp + 4 * (count + 1))
        u.reg_write(UC_X86_REG_EIP, return_pc)

    u.hook_add(UC_HOOK_CODE, hook)
    compared_events = 0
    for case in witness['cases']:
        objects, events = case['before'], []
        tokens = {o['name']: o['token'] for o in objects}
        policy, left, right = case['policy'], case['left'], case['right']
        for obj in objects:
            data = base64.b64decode(obj['bytes'])
            map_bytes(obj['token'], len(data))
            u.mem_write(obj['token'], data)
        original.call(case['entry'], case['receiver'], struct.pack('<III', *case['arguments']))
        assert len(events) == len(case['events']), (case['label'], 'event count')
        for index, (expected, actual) in enumerate(zip(events, case['events'])):
            assert expected == actual, (case['label'], 'ordered boundary mismatch', index,
                                        [k for k in expected if expected[k] != actual[k]])
        after = snapshots()
        assert after == case['after'], (case['label'], 'final memory',
                                       [a['name'] for a, b in zip(after, case['after']) if a != b])
        compared_events += len(events)
    result = dict(status='pass', nativeDisplayComparisons=len(witness['cases']),
                  orderedMemoryEvents=compared_events, nativeControls=witness['controls'],
                  rawPIDExecutedBytes=len(executed),
                  scope='raw PID -> original lock wrapper -> native display Lock/write/direct Unlock; eight-bit only',
                  rawActorJoin=False, appAcceptance=False)
    path.with_name('raw-pid-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
