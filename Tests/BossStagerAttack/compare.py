#!/usr/bin/env python3
"""Original/native named binding followed by real BossStagerAttack contacts.

Only resource lookup and allocation are physical fixtures. Both binders run their
real bodies; contact dispatch uses actor+78 -> record+10 and never a callback
fixture. The compared post-state is carried into the next operation so two
actors share the same player, manager, timer and contact-record lifetimes.
This focused source join does not elect BossStager in the native app.
"""
import ctypes as C
import json
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity import build
from Tests.clawparity.env import Env, HEAP_BASE, STACK_TOP
from Tests.clawparity.fixtures import allocate
from Tests.clawparity.program import claw


class RegistryEntry(C.Structure):
    _fields_ = [('name', C.c_char_p), ('ordinal', C.c_uint32),
                ('original_name', C.c_uint32), ('callback', C.c_uint32),
                ('flags', C.c_uint32)]


def word(side, address, program):
    if address >= HEAP_BASE:
        return struct.unpack_from('<I', side.heap, address - HEAP_BASE)[0]
    return struct.unpack_from('<I', side.image, address - program.data_start)[0]


def main():
    lib = C.CDLL(str(build.library('boss-stager-contact-join', [
        ROOT / 'Tests/BossStagerAttack/binding.cpp',
        ROOT / 'Sources/ActorResourceBindings.cpp',
        ROOT / 'Sources/LogicRegistry.cpp',
        ROOT / 'Sources/BossStagerAttackRuntime.cpp',
    ], dependencies=[ROOT / 'Sources/ActorResourceBindings.h', ROOT / 'Sources/LogicRegistry.h'])))
    lib.claw_logic_registry_find.argtypes = [C.c_char_p]
    lib.claw_logic_registry_find.restype = C.POINTER(RegistryEntry)
    registry = lib.claw_logic_registry_find(b'BossStagerAttack').contents
    assert registry.callback == 0x48e430
    program = claw()
    checks = 0
    negative_controls = 0
    for seed in range(8):
        env = Env(program)
        env._begin_case(random.Random(seed))
        world = env.object(0x40, 'world', fill=0x31)
        manager = env.object(0x30, 'manager', fill=0x42)
        position = env.object(0x4c, 'manager coordinates', fill=0x53)
        player = env.object(0xd0, 'shared player', fill=0x64)
        registry_token = env.object(0x30, 'logic registry', fill=0x75)
        metadata = env.object(20, 'actual registry metadata', words=[
            registry.original_name, registry.ordinal, registry.flags, 0, registry.callback])
        env.put(world + 0x14, registry_token)
        env.put(manager + 0x2c, position)
        env.put(0x5371fc, manager)
        env.put(0x537e88, player)
        initial_timer = [0, 0xffffffff, 0xffff0000, 0xfffe2b40][seed % 4]
        env.put(0x53c9f8, initial_timer)
        actors = []
        records = []
        for index in range(2):
            actor = env.object(512, f'actor {index}', fill=0x86 + index)
            record = env.object(0x40, f'primary {index}', fill=0xa0 + index)
            env.put(actor + 0x0c, world)
            env.put(actor + 0x6c, record)
            env.put(actor + 0x78, 0)
            actors.append(actor)
            records.append(record)
        name = registry.original_name
        assert env.cstr(name) == b'BossStagerAttack'

        def lookup(e, call):
            assert call.receiver == registry_token + 0x10
            assert e.cstr(call.arguments[0]) == b'BossStagerAttack'
            e.put(call.arguments[1], metadata)
            return 1

        env.fixture(0x4f6286, 'thiscall', 2, lookup, arguments=('cstr', 'out:4'))
        env.fixture(0x4f63ec, 'cdecl', 1, allocate())
        env._freeze()

        def step(entry, function, receiver, arguments, stack_pop=0):
            nonlocal checks
            native = env.run_native(entry, function, receiver, arguments)
            original = env.run_original(function, receiver, arguments, check_objects=True)
            failure = env.compare(native, original, True, STACK_TOP + 4 + stack_pop)
            assert failure is None, (seed, hex(function), failure)
            assert native.completed and original.completed
            # Carry all compared bytes and the allocation ledger forward.
            env._frozen = (original.heap,
                           env.pristine_image[:env.data_offset] + original.image,
                           dict(original.spans), env._bump, dict(env.names))
            checks += 1
            return original

        contacts = []
        for actor in actors:
            side = step(lib.claw_boss_stager_binding_test_entry, 0x4c8060, actor, [name], 4)
            assert side.eax == 1
            contact = word(side, actor + 0x78, program)
            assert contact in side.spans and side.spans[contact] == 0x174
            assert word(side, contact + 0x10, program) == registry.callback
            assert word(side, actor + 0x6c, program) == records[len(contacts)]
            contacts.append(contact)
        assert contacts[0] != contacts[1]
        expected_timer = initial_timer
        for index, mode in enumerate([1, 2, 0, 3, 0xffffffff, 2, 1]):
            # Modify the shared inputs between synchronous contact entries.
            heap, image, spans, bump, names = env._frozen
            heap = bytearray(heap)
            x, y = (0x80000000 + seed + index) & 0xffffffff, (0xffffffff - seed - index)
            struct.pack_into('<I', heap, player - HEAP_BASE + 0xcc, mode)
            struct.pack_into('<II', heap, player - HEAP_BASE + 0x4c, x, y)
            env._frozen = (bytes(heap), image, spans, bump, names)
            actor = actors[index % 2]
            callback = word(side, contacts[index % 2] + 0x10, program)
            assert callback == registry.callback
            before = env._frozen
            side = step(lib.claw_boss_stager_attack_entry, callback, 0, [actor])
            assert not side.events and not side.bridged
            accepted = mode in (1, 2)
            assert side.eax == int(accepted)
            if accepted:
                expected_timer = (expected_timer + 120000) & 0xffffffff
                assert word(side, position + 0x44, program) == x
                assert word(side, position + 0x48, program) == y
                assert word(side, actor + 8, program) & 1
                assert word(side, records[index % 2] + 0x1c, program) == 8003
            else:
                assert side.heap == before[0]
                assert side.image == before[1][env.data_offset:]
            assert word(side, 0x53c9f8, program) == expected_timer
            for actor_token, contact in zip(actors, contacts):
                assert word(side, actor_token + 0x78, program) == contact
                assert word(side, contact + 0x10, program) == callback
                assert contact in side.spans and contact not in side.freed
        # Rebinding reuses the existing contact allocation; callback never owns it.
        side = step(lib.claw_boss_stager_binding_test_entry, 0x4c8060, actors[0], [name], 4)
        assert word(side, actors[0] + 0x78, program) == contacts[0]
        assert word(side, 0x53c9f8, program) == expected_timer
        # The contact identity must resolve to this recovered callback.
        rejected = env.run_native(lib.claw_boss_stager_attack_entry, 0x48ded0, 0, [actors[0]])
        assert not rejected.completed and rejected.heap == env._frozen[0]
        negative_controls += 1
        # A detached/per-actor timer cannot pass the shared-global comparison.
        saved = env._frozen
        reference = env.run_original(registry.callback, 0, [actors[0]], check_objects=True)
        heap, image, spans, bump, names = saved
        image = bytearray(image)
        struct.pack_into('<I', image, 0x53c9f8 - program.base, expected_timer ^ 0x100)
        env._frozen = (heap, bytes(image), spans, bump, names)
        detached = env.run_native(lib.claw_boss_stager_attack_entry, registry.callback, 0, [actors[0]])
        failure = env.compare(detached, reference, True, STACK_TOP + 4)
        assert failure and failure['kind'] == 'globals', failure
        env._frozen = saved
        negative_controls += 1
    print(json.dumps({'command': 'boss-stager-attack-contact-join', 'status': 'pass',
                      'profiles': 8, 'compared_operations': checks,
                      'callback': hex(registry.callback), 'callback_fixtures': 0,
                      'negative_controls': negative_controls,
                      'scope': 'named binding, real contact callback, shared timer and retained contact lifetime; no app election'}))


if __name__ == '__main__':
    main()
