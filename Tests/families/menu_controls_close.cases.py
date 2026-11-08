"""Original-driven close dispatch and control-bit cases."""
from clawparity.cases import Case

CONFIRM = 0x4247C0
CANCEL = 0x4247E0
DISPATCH = 0x424800
ACTIVATE = 0x42EAB0
DEACTIVATE = 0x42EAE0
POST = 0x546D50
DECISION = 0x52545C
MODAL = 0x5375C4
PENDING = 0x5375C0
APPLICATION = 0x5371FC


def poison(random_source, size):
    return bytes(random_source.randrange(1, 256) for _ in range(size))


def close_setup(random_source, modal, has_app, post_result, window):
    receiver_data = poison(random_source, 0x2D0)
    table_data = poison(random_source, 0x200)
    app_data = poison(random_source, 0x30)
    window_data = poison(random_source, 0x30)
    guards = [poison(random_source, n) for n in (12, 16, 12)]
    decision = random_source.getrandbits(32) | 0x80
    pending = random_source.getrandbits(32) | 0x100

    def setup(env):
        receiver = env.object(len(receiver_data), "controls", data=receiver_data)
        table = env.object(len(table_data), "controls-vtable", data=table_data)
        app = env.object(len(app_data), "application", data=app_data)
        host = env.object(len(window_data), "window-owner", data=window_data)
        trace = env.object(64, "post-observation", fill=0xB7)
        env.put(receiver, table)
        # Preserve actual game dispatch; only the physical queue is a fixture.
        env.put(table + 0x1E8, DISPATCH)
        env.put(receiver + 0x2B4, 0xF17E5A93)
        env.put(app + 4, host)
        env.put(host + 4, window)
        env.write(DECISION - 4, guards[0])
        env.write(PENDING - 4, guards[1])
        env.write(APPLICATION - 4, guards[2])
        env.put(DECISION, decision)
        env.put(PENDING, pending, modal)
        env.put(APPLICATION, app if has_app else 0)

        def post(env, call):
            env.put(trace, env.calls_so_far(POST), *call.arguments)
            env.put(trace + 20, call.receiver, env.get(DECISION),
                    env.get(PENDING), env.get(MODAL), env.get(APPLICATION),
                    env.get(receiver + 0x2B4), env.get(app + 4), env.get(host + 4))
            # A physical queue return value, never an executed game handler.
            return post_result

        env.override(POST, post)
        return receiver

    return setup


def activation_setup(random_source, layout, first_flags, second_flags, activating):
    receiver_data = poison(random_source, 0x320)
    first_data = poison(random_source, 0x60)
    second_data = poison(random_source, 0x60)

    def setup(env):
        receiver = env.object(len(receiver_data), "controls", data=receiver_data)
        first = env.object(len(first_data), "first-control", data=first_data)
        second = env.object(len(second_data), "second-control", data=second_data)
        env.put(first + 0x40, first_flags)
        env.put(second + 0x40, second_flags)
        if layout == "neither":
            left, right = 0, 0
        elif layout == "first":
            left, right = first, 0
        elif layout == "second":
            left, right = 0, second
        elif layout == "distinct":
            left, right = first, second
        elif layout == "same":
            left, right = first, first
        elif layout == "overlapping":
            # Both flags words overlap, so operation width/order is observable.
            left, right = first, first + 1
        elif layout == "receiver":
            left, right = receiver + 0x80, receiver + 0xC1
            env.put(left + 0x40, first_flags)
            env.put(right + 0x40, second_flags)
        else:
            # The first flags word IS the second pointer. Bit zero changes its
            # address; both possible targets and all their flags are backed.
            left = receiver + 0x280
            right = second + 1 if activating else second
        env.put(receiver + 0x2BC, left, right)
        return receiver

    return setup


def cases(random_source):
    # Structural branch combinations never depend on the random seed.
    modes = [(0, False), (0, True)]
    modes += [(modal, has_app) for modal in (1, 2, 0x80000000, 0xFFFFFFFF)
              for has_app in (False, True)]
    for entry in (CONFIRM, CANCEL, DISPATCH):
        for modal, has_app in modes:
            for result in (0, 1, 0x87654321):
                window = random_source.getrandbits(32) | 0x100
                yield Case(f"close {entry:x} modal={modal:x} app={has_app} queue={result:x}",
                           entry, close_setup(random_source, modal, has_app, result, window),
                           receiver=lambda receiver: receiver)
        for index in range(8):
            modal = random_source.getrandbits(32) if index & 1 else 0
            yield Case(f"random close {entry:x} {index}", entry,
                       close_setup(random_source, modal, True,
                                   random_source.getrandbits(32),
                                   random_source.getrandbits(32)),
                       receiver=lambda receiver: receiver)

    flags = [(0, 0xFFFFFFFF), (1, 0xFFFFFFFE), (0x80000000, 0x80000001),
             (0x13579BDF, 0x2468ACE0), (0xAA55AA54, 0x55AA55AB)]
    layouts = ("neither", "first", "second", "distinct", "same", "overlapping",
               "receiver", "pointer-reload")
    for entry in (ACTIVATE, DEACTIVATE):
        for layout in layouts:
            for index, (left, right) in enumerate(flags):
                argument = (0, 1, 0xFFFFFFFF, 0x80000000, 0x13579BDF)[index]
                yield Case(f"flags {entry:x} {layout} {left:x}/{right:x}", entry,
                           activation_setup(random_source, layout, left, right,
                                            entry == ACTIVATE),
                           receiver=lambda receiver: receiver, arguments=(argument,))
        for index in range(24):
            layout = layouts[index % len(layouts)]
            yield Case(f"random flags {entry:x} {layout} {index}", entry,
                       activation_setup(random_source, layout,
                                        random_source.getrandbits(32),
                                        random_source.getrandbits(32), entry == ACTIVATE),
                       receiver=lambda receiver: receiver,
                       arguments=(random_source.getrandbits(32),))
