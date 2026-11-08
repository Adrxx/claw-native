"""v1.3 profile routing cases derived from the original instruction packets."""
from clawparity.cases import Case

CLOSE, ROUTE = 0x42A920, 0x487A70
SINGLETON, SELECTED, DIRTY, MODE = 0x535910, 0x53A96C, 0x5362A4, 0x5234BC


def journal(env):
    trace = env.object(8192, 'observed-services', fill=0)
    def record(env, tag, call, extra=()):
        count = env.get(trace)
        env.put(trace, count + 1)
        env.put(trace + 4 + count * 64, tag, call.receiver, len(call.arguments), *call.arguments, *extra)
    return record


def modal_setup(statuses, cursor_first, salt, swap=False):
    def setup(env):
        record = journal(env)
        owner = env.object(0x90, 'application', fill=0xA7)
        window = env.object(0x18, 'window', fill=0xB8)
        instance = env.object(0x20, 'instance', fill=0xC9)
        env.put(owner + 4, window, instance)
        env.put(window + 4, salt ^ 0x31415926)
        env.put(instance + 12, salt ^ 0x27182818)
        env.put(owner + 0x30, 0)
        env.put(0x5365D4, 0)
        env.put(0x53FA14, salt, salt ^ 0xFFFFFFFF, salt ^ 0x55AA55AA)
        env.put(0x535920, salt ^ 0x12345678, salt ^ 0x87654321)
        managers = []
        for index in range(2):
            manager = env.object(0x24, f'manager-{index}', fill=0xD0 + index)
            methods = env.object(0x20, f'manager-methods-{index}', fill=0)
            def state(env, call, index=index):
                record(env, 0x10 + index, call, (env.get(owner + 0x2C),))
                if index == 0 and swap:
                    env.put(owner + 0x2C, managers[1])
                method = env.get(env.get(call.receiver) + 0x10)
                ordinal = env.calls_so_far(method) - 1
                return statuses[min(ordinal + index, len(statuses) - 1)]
            env.put(manager, methods)
            env.put(methods + 0x10, env.stub(f'state-{index}', 'thiscall', 0, state))
            managers.append(manager)
        env.put(owner + 0x2C, managers[0])
        def cursor(env, call):
            record(env, 0x20, call)
            n = env.calls_so_far(0x50C4D0)
            if call.arguments[0]:
                return cursor_first if n == 1 else (0 if n >= 4 else -1)
            return -1
        def dialog(env, call):
            record(env, 0x21, call, (env.get(owner + 0x2C), env.get(owner + 0x30)))
            return 0xFFFFFFFF  # callback-free physical dialog creation failure
        def clock(env, call):
            record(env, 0x22, call, (env.get(0x53FA14), env.get(0x535920)))
            return salt ^ 0x9E3779B9
        env.override(0x50C4D0, cursor)
        env.override(0x50C470, dialog)
        env.override(0x50C58C, clock)
        return owner
    return setup


def route_setup(singleton, same, dirty, salt, mutate_end=False, no_profile=False):
    def setup(env):
        record = journal(env)
        owner = env.object(0x80, 'application', fill=0xE3)
        instance = env.object(0x20, 'instance', fill=0xD2)
        env.put(owner + 8, instance)
        env.put(instance + 12, salt ^ 0xABCD0123)
        env.put(owner + 0x64, 0 if no_profile else (salt if same else salt ^ 0xFFFFFFFF))
        env.put(SINGLETON, owner if singleton else 0)
        env.put(SELECTED, salt)
        env.put(DIRTY, dirty)
        def end(env, call):
            record(env, 0x30, call, (env.get(DIRTY), env.get(SELECTED), env.get(owner + 0x64)))
            if mutate_end:
                env.put(DIRTY, salt ^ 0xFEEDBEEF)
            return salt ^ 0xBF012345
        def item(env, call):
            record(env, 0x31, call)
            return 0
        def message(env, call):
            record(env, 0x32, call)
            return 0xFFFFFFFF
        def dialog(env, call):
            record(env, 0x33, call, (env.get(SINGLETON), env.get(DIRTY)))
            return 0xFFFFFFFF
        env.override(0x50C478, end)
        env.override(0x50C4C0, item)
        env.override(0x50C4C4, message)
        env.override(0x50C470, dialog)
        return owner
    return setup


def route(label, message, command, setup, hwnd, lparam):
    return Case(label, ROUTE, setup, arguments=(hwnd, message, command, lparam))


def cases(random_source):
    salts = [1, 0x80000000, 0xFFFFFFFF] + [random_source.getrandbits(32) for _ in range(4)]
    for index, salt in enumerate(salts):
        for statuses in ((5,), (0, 2), (2, 0), (0, 5), (0xFFFFFFFF, 2), (0x80000000, 0)):
            for swap in (False, True):
                yield Case(f'close {index} statuses {statuses} swap {swap}', CLOSE,
                           modal_setup(statuses, (-3, 0, 1)[index % 3], salt, swap),
                           receiver=lambda owner: owner)
    for index, salt in enumerate(salts):
        hwnd, lparam = salt ^ 0x8765ABCD, random_source.getrandbits(32)
        for message in (0, 0x10F, 0x112, 0xFFFFFFFF, 0x80000110):
            yield route(f'ignored message {index} {message:#x}', message, salt,
                        route_setup(False, True, salt ^ 0x55, salt), hwnd, lparam)
        for command in (1, 2):
            for high in (0, 1, 0x8000, 0xFFFF):
                for same in (False, True):
                    yield route(f'close dialog {index} {command} high {high} same {same}', 0x111,
                                command | (high << 16), route_setup(True, same, salt ^ 0x55, salt,
                                                                  mutate_end=index % 2 == 0), hwnd, lparam)
        for command in (0x43C, 0x43D):
            for high in (0, 1, 0xFFFF):
                for singleton in (False, True):
                    yield route(f'button {index} {command:#x} high {high} app {singleton}',
                                0x111, command | (high << 16),
                                route_setup(singleton, True, salt ^ 0x55, salt, no_profile=command == 0x43D), hwnd, lparam)
        for command in (0, 3, 0x43A, 0x43E, 0x7FFF, 0x8000, 0xFFFF):
            for high in (0, 1, 2, 0xFFFF):
                yield route(f'other command {index} {command:#x} high {high}', 0x111,
                            command | (high << 16), route_setup(False, True, salt, salt), hwnd, lparam)
        for singleton in (False, True):
            def no_profile(env, singleton=singleton, salt=salt):
                owner = route_setup(singleton, True, salt ^ 0x55, salt)(env)
                env.put(owner + 0x64, 0)
                return owner
            yield route(f'initialize no profile {index} app {singleton}', 0x110, salt,
                        no_profile, hwnd, lparam)
        yield route(f'initialize absent level combo {index}', 0x110, salt,
                    route_setup(True, True, salt ^ 0x55, salt), hwnd, lparam)
    for function in (0x425A20, 0x425A40):
        for index, salt in enumerate(salts):
            def setup(env, salt=salt):
                record = journal(env)
                target = env.object(0x40, 'developer-command-target', fill=0xAC)
                methods = env.object(0x1F0, 'developer-command-methods', fill=0)
                env.put(MODE, salt)
                def action(env, call):
                    record(env, 0x40, call, (env.get(MODE), env.get(target + 4)))
                    env.put(target + 8, salt ^ 0x1234ABCD)
                    env.put(MODE, salt ^ 0xFEDC4321)
                    return salt ^ 0xDEADBEEF
                env.put(target, methods)
                env.put(target + 4, salt)
                env.put(methods + 0x1E8, env.stub('developer-mode-action', 'thiscall', 0, action))
                return target
            yield Case(f'developer mode {function:#x} {index}', function, setup,
                       receiver=lambda target: target)
