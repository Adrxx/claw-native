"""Exercise the fill wrapper through original blit/reporting boundaries."""
from clawparity.cases import Case

FILL = 0x4B97C0
LOST = 0x887601C2


def setup_fill(result, object_bytes, observation_bytes, *, boundary=False,
               diagnostics=False):
    def setup(env):
        surface = env.object(64, "surface", data=object_bytes)
        methods = env.object(32, "surface-vtable", fill=0xA7)
        interface = env.object(16, "directdraw", fill=0x3D)
        com_methods = env.object(24, "directdraw-vtable", fill=0xB9)
        observed = env.object(256, "callback-observations", data=observation_bytes)
        env.put(observed, 0)
        env.put(surface, methods)
        env.put(surface + 8, interface)
        env.put(interface, com_methods)
        # All reporting options off: the original reporter still executes.
        env.put(0x54139C, 0, 0, 0, 0)
        if diagnostics:
            diagnostic_log = env.object(256, "physical-diagnostic-observations",
                                        fill=0xC7)
            env.put(diagnostic_log, 0)
            # Enable only the physical beep; retain the original game reporter.
            env.put(0x5413A4, 1)

            def beep(env, call):
                count = env.get(diagnostic_log)
                env.put(diagnostic_log, count + 1)
                env.put(diagnostic_log + 4 + count * 20,
                        call.arguments[0], env.get(observed),
                        env.get(surface + 60), env.get(observed + 212),
                        env.get(0x5413A4))
                return 1

            env.override(0x546CA4, beep)

        def blit(env, call):
            count = env.get(observed)
            env.put(observed, count + 1)
            env.put(observed + 4, *call.arguments)
            env.write(observed + 32, env.read(call.arguments[5], 100))
            env.write(observed + 132, env.read(surface, 64))
            env.write(observed + 196, env.read(interface, 16))
            if boundary:
                # The first word beyond the exact FX object is the caller's
                # return word. Publish it so a 26-word clear is observable.
                env.write(observed + 248, env.read(call.arguments[5] + 100, 4))
            # A callback-side write remains visible when restore is invoked.
            env.put(surface + 60, 0xD137A009)
            return result

        def restore(env, call):
            env.put(observed + 212, env.get(observed), call.receiver,
                    env.get(surface + 60))
            env.write(observed + 224, env.read(surface, 24))
            return 0

        env.put(com_methods + 0x14,
                env.stub("IDirectDrawSurface::Blt", "stdcall", 6, blit))
        env.put(methods + 0x1C,
                env.stub("Surface::restore", "thiscall", 0, restore))
        return {"surface": surface}

    return setup


def cases(random_source):
    colors = [0, 1, 0xFFFFFFFF, 0x80000000, 0x12345678, 0x00ABCDEF,
              0xFF000001]
    colors += [random_source.getrandbits(32) for _ in range(9)]
    statuses = [0, 1, 0x80004005, 0xFFFFFFFF, LOST]
    for index, color in enumerate(colors):
        # Every FX byte begins nonzero, so missing or short clearing is observable.
        poison = bytes(random_source.randrange(1, 256) for _ in range(100))
        body = bytes(random_source.randrange(1, 256) for _ in range(64))
        observations = bytes(random_source.randrange(1, 256) for _ in range(256))
        for result in statuses:
            yield Case(
                f"fill {index} color {color:#010x} status {result:#010x}",
                FILL, setup_fill(result, body, observations),
                receiver=lambda tokens: tokens["surface"], arguments=(color,),
                initial_stack=((-100, poison),))

    # Keep the original 80 controls and add observable reporting and the word
    # immediately beyond the 100-byte local, across success and error paths.
    for index, color in enumerate((0xA1B2C3D4, random_source.getrandbits(32))):
        poison = bytes(random_source.randrange(1, 256) for _ in range(100))
        body = bytes(random_source.randrange(1, 256) for _ in range(64))
        observations = bytes(random_source.randrange(1, 256) for _ in range(256))
        for result in statuses:
            yield Case(
                f"physical diagnostics {index} color {color:#010x} status {result:#010x}",
                FILL, setup_fill(result, body, observations, boundary=True,
                                 diagnostics=True),
                receiver=lambda tokens: tokens["surface"], arguments=(color,),
                initial_stack=((-100, poison),))
