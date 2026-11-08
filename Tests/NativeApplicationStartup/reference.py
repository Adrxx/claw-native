"""Fresh original-only constructor/startup prefix, stopped at config entry.

Only imports and allocation are replaced. All reached game and CRT bodies,
including CRT lock initialization, execute from the hash-checked original.
Synthetic platform records prove this boundary, not Windows UI initialization.
"""
import json
import struct
import sys
from pathlib import Path

from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP


class ConfigReached(Exception):
    pass


def reference(name, clocks, tick, cursor, refuse=False):
    program = claw()  # Verify before every original image mapping/read.
    machine = Machine(program, 0x3000000, 0x10000)
    bump = 0x3000000
    spans = {}
    tls = {}
    last_error = 0
    clock_index = 0
    cursor_count = cursor
    phase = "constructor"
    events = []
    crt_services = []
    executed = set()
    reverse_imports = {v: k for k, v in machine.import_stub.items()}

    def allocate(size):
        nonlocal bump
        token = bump
        bump = (bump + size + 15) & ~15
        assert bump < 0x3010000
        spans[token] = size
        machine.write(token, bytes(size))
        return token

    def put(token, *words):
        machine.write(token, struct.pack("<" + "I" * len(words), *words))

    app = allocate(0x134)
    outer = allocate(0x254)
    window = allocate(12)
    command = allocate(1)
    # Explicitly synthetic records at the native platform boundary.
    put(outer, 0x50bbdc, window, app, 0x77000001)
    put(window, 0x50c37c, 0x77000002, outer)

    def snapshot(function, receiver, args, result=None):
        return dict(function=function, receiver=receiver, arguments=list(args), result=result,
                    applicationWords=list(machine.words(app, 77)),
                    clockWords=list(machine.words(0x541328, 5)))

    def observe_srand(m, address):
        executed.add(address)
        if phase == "startup":
            args = m.words(m.register(UC_X86_REG_ESP) + 4, 1)
            events.append(snapshot(address, 0, args, 0))  # Source void result.

    for address in (0x4254a0, 0x4b8240, 0x4b83a0, 0x4b83d0, 0x4b8280,
                    0x4a7d40, 0x4a7b90, 0x4a7da0, 0x4a7dc0):
        machine.observe(address, lambda m, a: executed.add(a))
    machine.observe(0x4a3040, observe_srand)

    # Import-slot identities and exact native stack argument counts.
    signatures = {0x546df0: 0, 0x546a24: 0, 0x546d54: 1,
                  0x546aa4: 1, 0x546a90: 0, 0x546a84: 2,
                  0x5469c0: 0, 0x546b0c: 0, 0x546a7c: 1, 0x546ab8: 1}
    for address in (0x4f63ec, 0x4adf50, 0x4b5c50):
        machine.intercept(address)

    def external(m, address):
        nonlocal last_error, clock_index, cursor_count
        function = reverse_imports.get(address, address)
        argc = signatures.get(function, {0x4f63ec: 1, 0x4adf50: 2, 0x4b5c50: 6}.get(function))
        assert argc is not None, f"Unexpected original service {function:#x}"
        args = m.words(m.register(UC_X86_REG_ESP) + 4, argc)
        receiver = m.register(UC_X86_REG_ECX) if function == 0x4b5c50 else 0
        record = snapshot(function, receiver, args)
        if function == 0x4b5c50:
            assert phase == "startup"
            events.append(record)
            raise ConfigReached
        if function == 0x546df0:
            assert clock_index < len(clocks)
            value = clocks[clock_index]
            clock_index += 1
        elif function == 0x546a24:
            value = tick
        elif function == 0x546d54:
            cursor_count += 1 if args[0] else -1
            assert -(1 << 31) <= cursor_count < (1 << 31)
            value = cursor_count & 0xffffffff
        elif function == 0x4f63ec:
            assert args == (540,)
            value = 0 if refuse else allocate(args[0])
        elif function == 0x4adf50:
            value = allocate(args[0] * args[1])
        elif function == 0x546aa4:
            # OS initializes an otherwise unused lock. No lock body is stubbed.
            assert args[0] != 0
            value = 0
        elif function == 0x546a90:
            value = 0
        elif function == 0x546a84:
            assert args[0] == 0
            tls[args[0]] = args[1]
            value = 1
        elif function == 0x5469c0:
            value = 123
        elif function == 0x546b0c:
            value = last_error
        elif function == 0x546a7c:
            value = tls[args[0]]
            last_error = 0
        elif function == 0x546ab8:
            last_error = args[0]
            value = 0
        else:
            raise AssertionError(hex(function))
        record["result"] = value
        if phase == "startup" and function in (0x546df0, 0x546a24, 0x546d54, 0x4f63ec):
            events.append(record)
        elif function not in (0x546df0, 0x546a24, 0x546d54):
            crt_services.append(function)
        m.return_from_external(value, 4 * argc if function in signatures else 0)

    machine.on_external = external
    def live_access(address, size, is_write, instruction):
        assert any(base <= address and address + size <= base + count for base, count in spans.items()), \
            f"Original heap access outside live objects at {address:#x}, instruction {instruction:#x}"
    machine.watch_heap(live_access)
    constructor = machine.call(0x4254a0, app)
    assert constructor.completed and constructor.eax == app and clock_index == 2
    constructor_words = list(machine.words(app, 77))
    constructor_clock = list(machine.words(0x541328, 5))
    phase = "crt"
    crt = machine.call(0x4a7d40)
    assert crt.completed and crt.eax == 1
    phase = "startup"
    try:
        machine.call(0x425730, app, arguments=(window, command))
        raise AssertionError("Startup unexpectedly returned before missing configuration")
    except ConfigReached:
        pass
    assert clock_index == len(clocks) == 5
    config = machine.words(app + 0x38, 1)[0]
    assert events[-1]["function"] == 0x4b5c50 and events[-1]["receiver"] == config
    assert events[-1]["arguments"] == [0x5258b8, 0x524eec, 0x5258d0, 0, 0x80000002, 0]
    assert config == 0 if refuse else spans[config] == 540
    assert all(machine.words(app + offset, 1)[0] == 0 for offset in (0x2c, 0x30, 0x34))
    expected_executed = {0x4254a0, 0x4b8240, 0x4b83a0, 0x4b83d0, 0x4b8280,
                         0x4a7d40, 0x4a7b90, 0x4a7da0, 0x4a7dc0, 0x4a3040}
    assert expected_executed <= executed
    assert crt_services.count(0x546aa4) == 4
    return dict(name=name, clocks=clocks, tick=tick, cursor=cursor, refused=refuse,
                app=app, outer=outer, window=window, config=config,
                cursorFinal=cursor_count, constructorWords=constructor_words,
                constructorClock=constructor_clock, applicationWords=list(machine.words(app, 77)),
                clockWords=list(machine.words(0x541328, 5)),
                threadWords=list(machine.words(tls[0], 29)), tlsIndex=machine.words(0x52edd8, 1)[0],
                configBytes=machine.read(config, 540).hex() if config else None,
                events=events, executed=sorted(executed), crtServices=crt_services,
                sha256=program.sha256)


if __name__ == "__main__":
    cases = [reference("cursor-three-calls", [100, 125, 200, 225, 250], 400, 2),
             reference("already-hidden", [3, 8, 15, 24, 35], 0, -1),
             reference("unsigned-seed-wrap", [0xfffffff0, 0xfffffff1, 0xfffffff2, 0xfffffff3, 0xfffffff4], 27, 0),
             reference("source-allocation-refused", [0, 1, 2, 3, 4], 6, 0, True)]
    Path(sys.argv[1]).write_text(json.dumps(cases, indent=2) + "\n")
    print(f"PASS {len(cases)} fresh original constructor/startup prefixes; CRT/game bodies real; halt only4b5c50", file=sys.stderr)
