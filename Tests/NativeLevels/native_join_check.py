"""Bounded native heap and retained-route controls, without guest execution.

Run: work/test-env/bin/python -m Tests.NativeLevels.native_join_check
"""
import json
from types import SimpleNamespace
from Tests.NativeMenuBase.native_join import NativeMemory
from Tests.NativeMenuBase.trace import Blocked
from Tests.NativeLevelOne.trace import LevelOneTrace
from Tests.NativeLevels.native_join import LevelNativeJoin, control_refusal, denied_owners, extend_heap, owner_control_candidates
from unicorn.x86_const import UC_X86_REG_ESP


def refuses(call):
    try:
        call()
    except Blocked:
        return
    raise AssertionError('Invalid native operation succeeded')


def main():
    memory = NativeMemory()
    memory.mem_map(0x1000, 16)
    memory.mem_map(0x1010, 16)
    memory.mem_map(0x1030, 16)
    memory.mem_write(0x1000, b'a' * 16)
    memory.mem_write(0x1010, b'b' * 16)
    memory.mem_write(0x1030, b'c' * 16)
    refuses(lambda: memory.pointer(0x1008, 16))
    memory.coalesce()
    assert memory.mem_read(0x1008, 16) == b'a' * 8 + b'b' * 8
    assert memory.mem_read(0x1030, 16) == b'c' * 16
    refuses(lambda: memory.pointer(0x1018, 32))
    refuses(lambda: memory.mem_map(0x1010, 16))
    refuses(lambda: memory.pointer(0, 4))
    refuses(lambda: memory.emu_start(0, 0))

    # Exercise an allocation that actually spans the old Level 3 heap bound.
    # A small initial region keeps this check independent of game initialization.
    physical = object.__new__(LevelOneTrace)
    physical.machine = NativeMemory()
    physical.machine.mem_map(0x68fffff0, 16)
    physical.heap_next = 0x68fffff0
    physical.heap_limit = 0x69000000
    physical.allocations = {}
    extend_heap(physical, 4)
    pointer = physical.allocate(32)
    assert physical.machine.mem_read(pointer, 32) == b'\xa5' * 32
    assert physical.allocations == {pointer: 32}
    physical.heap_next = physical.heap_limit - 32
    assert physical.allocate(16) == 0x6effffe0
    before = physical.heap_next, physical.allocations.copy()
    for size in (16, -1, 0x800001):
        refuses(lambda: physical.allocate(size))
        assert (physical.heap_next, physical.allocations) == before
    physical.machine.regions.clear()

    # Every selectable later level has the same arenas as the original tracer.
    # Check mapping policy without allocating fourteen worlds or emulating them.
    for level in range(3, 15):
        mappings = []
        probe = SimpleNamespace(heap_next=0x61000000, heap_limit=0x69000000,
            machine=SimpleNamespace(mem_map=lambda *args: mappings.append(args), coalesce=lambda: None))
        extend_heap(probe, level)
        expected = [(0x69000000, 0x6000000)] if level >= 4 else []
        if level >= 6:
            expected.append((0x30000000, 0x20000000))
        assert mappings == expected
        assert probe.heap_limit == (0x50000000 if level >= 6 else 0x6f000000 if level >= 4 else 0x69000000)
        assert probe.heap_next == (0x30000000 if level >= 6 else 0x61000000)

    def row(address, owner, phases):
        return dict(address=address, owner=owner, phases=phases, count=1,
                    entry_kind='function', owner_status='admitted')
    route = dict(game_functions=[
        row('0x401000', 'level_four_test', ['loading', 'level-4-attack']),
        row('0x402000', 'shared_enemy', ['level-4-attack']),
        row('0x403000', 'level_four_test', ['level-4-stand']),
        row('0x404000', 'level_four_test', ['level-4-stand'])])
    dispatch = {0x401000: 1, 0x402000: 2, 0x403000: 3, 0x404000: 4}
    assert [a for _, a in denied_owners(route, 4, dispatch)] == [0x403000, 0x402000]
    refuses(lambda: denied_owners(route, 5, dispatch))

    # The original-reached seagull helper is compiled inside a native module;
    # it is not a host dispatch and cannot exercise deny_owner. Keep its
    # evidence, then elect an actual boundary from the same recovered family.
    route = dict(game_functions=[
        row('0x453bd0', 'level_five_town_guard_states_switch', ['level-5-walk-right']),
        row('0x467ea0', 'level_five_seagull_states', ['level-5-climb-up']),
        row('0x4873a0', 'level_five_seagull_core', ['level-5-stand']),
        row('0x4879a0', 'level_five_seagull_states', ['level-5-climb-up']),
        row('0x401000', 'shared_enemy', ['level-5-stand']),
        row('0x402000', 'other_enemy', ['level-5-stand']),
        row('0x443170', 'level_five_seagull_core', ['command-8075'])])
    dispatch = {0x453bd0: 1, 0x467ea0: 0, 0x4873a0: 8, 0x4879a0: 7, 0x443170: 3,
                0x401000: 4, 0x402000: 5, 0x488550: 6}
    expected = [0x453bd0, 0x4879a0]
    assert [a for _, a in denied_owners(route, 5, dispatch)] == expected
    assert [a for _, a in denied_owners(route, 5, {a: n for a, n in dispatch.items() if n})] == expected
    candidates = owner_control_candidates(route, 5, dispatch)
    internal = next(r for r in candidates if r['address'] == '0x467ea0')
    assert internal == dict(address='0x467ea0', owner='level_five_seagull_states',
                            original_count=1, original_phases=['level-5-climb-up'], native_dispatch_calls=0)
    assert not any(r['address'] in ('0x443170', '0x488550') for r in candidates)
    refuses(lambda: denied_owners(route, 5, {}))
    refuses(lambda: denied_owners(route, 5, {0x453bd0: 1}))
    # Two shared boundaries cannot silently replace every recovered Level 5 owner.
    refuses(lambda: denied_owners(route, 5, {0x401000: 4, 0x402000: 5}))
    for phase in ('loading', 'command-8075', 'level-4-climb-up', 'level-50-stand'):
        refuses(lambda: control_refusal('missing-owner', 'Native owner deliberately withheld', phase, 5))
    refuses(lambda: control_refusal('missing-owner', 'unrelated native fault', 'level-5-stand', 5))
    assert control_refusal('missing-owner', 'Native owner deliberately withheld', 'level-5-stand', 5)['result'] == 'refused'
    # Exercise the actual native fixture wiring, including its bounded string
    # reader. This is a physical service; no canonical game return is invented.
    probe = object.__new__(LevelNativeJoin)
    probe.target_level, probe.phase, probe.deny_platform = 11, 'level-11-walk-right', None
    probe.machine = NativeMemory()
    for pointer, data in ((0x3000, b'ConveyorLeft\0'), (0x4000, b'conveyorRight\0')):
        probe.machine.mem_map(pointer, len(data))
        probe.machine.mem_write(pointer, data)
    probe.machine.reg_read = lambda register: 0x2000 if register == UC_X86_REG_ESP else 0
    probe.machine.reg_write = lambda *args: None
    words = {0x2000: 0x4319e8, 0x2004: 0x3000, 0x2008: 0x4000,
             0x540e00: 0, 0x540e88: 0}
    probe.word = lambda address: words[address]
    returned = []
    probe.returned = lambda result: returned.append(result)
    probe.platform_call = lambda *args: None
    probe.physical_events, probe.string_comparisons = [], []
    probe.fixture(0x4a3dc0)
    assert returned == [-1] and len(probe.string_comparisons) == 1
    assert probe.string_comparisons[0]['left'] == 'ConveyorLeft'
    probe.deny_platform = 0x4a3dc0
    refuses(lambda: probe.fixture(0x4a3dc0))
    assert returned == [-1], 'Withheld comparison must not supply a result'
    probe.deny_platform = None
    words[0x540e88] = 1
    refuses(lambda: probe.fixture(0x4a3dc0))
    print(json.dumps(dict(status='pass', heap_levels=list(range(3, 15)),
                         cross_boundary_allocation=True, missing_owner_selection=True,
                         zero_native_dispatch_candidate=True, refusal_phase_checks=True,
                         level_eleven_comparison_service=True, guest_execution=False)))


if __name__ == '__main__':
    main()
