"""Archive lookup cases derived from the original entry points."""
from clawparity.cases import Case

RESOLVE = 0x42CAB0
EXISTS = 0x48C190
DIRECTORY = 0x546A28
OPEN = 0x546A30


def physical_strings(env):
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))

    def decrement(e, c):
        address = c.arguments[0]
        value = (e.get(address) - 1) & 0xFFFFFFFF
        e.put(address, value)
        return value

    env.override(0x5469E8, decrement)


def cstring(env, text, name, refs=1, extra=0):
    capacity = len(text) + extra
    header = env.object(12 + capacity + 1, name, fill=0xA7)
    env.put(header, refs, len(text), capacity)
    env.write(header + 12, text + b'\0')
    return header + 12


def resolver_setup(directory, drive, statuses, globals_, display, notify, salt,
                   directory_result=None, change=None):
    def setup(env):
        physical_strings(env)
        app = env.object(0x140, 'application', fill=0x73)
        env.put(app + 8, 0)
        env.put(app + 0x30, display)
        env.put(app + 0x78, 8)
        env.write(app + 0xCC, bytes([drive]))
        env.put(app + 0xD0, 0x13579BDF)
        for index, offset in enumerate((0xF8, 0xFC, 0x100)):
            text = b'old-' + bytes([65 + index]) * (5 + salt % 13 + index)
            env.put(app + offset, cstring(env, text, 'old path ' + str(index),
                                         refs=1 + (salt + index) % 2,
                                         extra=(salt + index) % 7))
        env.put(0x53724C, globals_[0])
        env.put(0x537250, globals_[1])
        log = env.object(512, 'service observation', fill=0)
        if notify:
            target = env.object(16, 'notification receiver', fill=0x69)
            vtable = env.object(32, 'notification vtable', fill=0)

            def notification(e, c):
                e.put(log + 448, c.receiver, *c.arguments)
                e.write(log + 464, e.read(app + 0x104, 20))
                return 0x79A1F002

            env.put(target, vtable)
            env.put(vtable + 0x1C, env.stub('notify', 'thiscall', 2, notification))
            env.put(app + 8, target)

        def current_directory(e, c):
            e.write(c.arguments[1], directory + b'\0')
            return len(directory) if directory_result is None else directory_result

        def open_file(e, c):
            index = e.calls_so_far(OPEN) - 1
            e.write(c.arguments[1], bytes((salt + index * 19 + k) & 255 for k in range(136)))
            e.put(log + index * 32, index, c.arguments[2])
            e.write(log + index * 32 + 8, e.read(app + 0x104, 20))
            if change is not None and index == change[0]:
                e.put(app + change[1], change[2])
            return statuses[index % len(statuses)]

        env.override(DIRECTORY, current_directory)
        env.override(OPEN, open_file)
        return app
    return setup


def cases(random_source):
    for path in (None, b'', b'x', b'C:\\CLAW\\CLAW.REZ', b'\xE9-path', b'a' * 250):
        for status in (0xFFFFFFFF, 0, 1, 0x80000000, 0xFFFFFFFE):
            payload = bytes(random_source.randrange(256) for _ in range(136))

            def setup(env, path=path, status=status, payload=payload):
                p = 0 if path is None else env.object(len(path) + 1, 'path', data=path + b'\0')

                def open_file(e, c):
                    e.write(c.arguments[1], payload)
                    return status

                env.override(OPEN, open_file)
                return p

            yield Case('existence %r status %08x' % (path, status), EXISTS, setup,
                       arguments=(lambda p: p,))

    # Every initial/fallback success combination, with different requirements.
    for mask in range(64):
        statuses = tuple(0 if mask & (1 << n) else 0xFFFFFFFF for n in range(6))
        high = (mask % 3 == 0, mask % 3 == 1)
        salt = random_source.randrange(1, 200)
        yield Case('independent file results %02x' % mask, RESOLVE,
                   resolver_setup(b'C:\\Games\\Claw-' + str(salt).encode(), ord('D'),
                                  statuses, high, mask & 1, True, salt),
                   receiver=lambda app: app)

    for drive in (0, ord('C'), ord('D'), 0x80, 0xFF):
        for high in ((0, 0), (0x80000000, 0), (0, 0xFFFFFFFF)):
            for display in (0, 0x1234):
                yield Case('missing drive %02x high %s display %s' % (drive, high, display),
                           RESOLVE, resolver_setup(b'C:\\', drive, (0xFFFFFFFF,), high,
                                                   display, bool(display), random_source.randrange(256)),
                           receiver=lambda app: app)

    for high in ((0, 0), (1, 0), (0, 0x80000000)):
        yield Case('directory unavailable %s' % (high,), RESOLVE,
                   resolver_setup(b'ignored', ord('D'), (0,), high, 0, False, 17,
                                  directory_result=0), receiver=lambda app: app)

    for change in ((0, 0x108, 1), (1, 0x108, 1), (0, 0x104, 1), (2, 0x104, 0)):
        yield Case('service changes field %s' % (change,), RESOLVE,
                   resolver_setup(b'Z:\\odd space', ord('D'), (0xFFFFFFFF,), (0, 0),
                                  0, True, 39, change=change), receiver=lambda app: app)
