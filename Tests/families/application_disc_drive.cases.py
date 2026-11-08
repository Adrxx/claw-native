"""Blind original-only cases for the bounded disc-drive discovery contract."""
from clawparity.cases import Case

DISC = 0x42B020
REGISTRY = 0x54682C
DIRECTORY = 0x546A28
DRIVE = 0x546A2C


def scenario(random_source, *, flag=0, cache=0xE3, configuration=None,
             initialized=1, status=0, value_type=1, payload=b'D:\\CLAW\0',
             reported_size=None, directory=b'C:\\CLAW\0', directory_result=None,
             current_type=3, optical=(), final_type=3):
    app_bytes = bytes(random_source.randrange(256) for _ in range(0xE4))
    config_bytes = bytes(random_source.randrange(256) for _ in range(540))
    key = random_source.getrandbits(32)

    def setup(env):
        app = env.object(0xE4, 'application with field canaries', data=app_bytes)
        config = 0
        if configuration is not None:
            config = env.object(540, 'configuration with canaries', data=config_bytes)
            env.put(config, initialized)
            env.put(config + 0x18, key)
        env.put(app + 0x38, config)
        env.put(app + 0xD0, flag)
        env.write(app + 0xCC, bytes([cache]))
        log = env.object(4096, 'OS call observations and bounded output tails', fill=0xA7)
        env.put(log, 0)

        def record(env, kind, call, tail=b''):
            count = env.get(log)
            row = log + 4 + count * 128
            env.put(row, kind, call.receiver, env.get(app + 0xD0),
                    env.get(app + 0xCC), len(call.arguments))
            for index, argument in enumerate(call.arguments):
                env.put(row + 20 + index * 4, argument)
            env.write(row + 48, tail[:80].ljust(80, b'\0'))
            env.put(log, count + 1)

        def registry(env, call):
            _, _, _, type_out, destination, size = call.arguments
            record(env, 1, call, env.read(size, 4) + env.read(destination, 32))
            # Capacity is the source's 30-byte buffer. Failure outputs here are
            # deterministic robustness inputs, not promises made by Windows.
            env.put(type_out, value_type)
            env.write(destination, payload[:30])
            env.put(size, len(payload) if reported_size is None else reported_size)
            return status

        def current_directory(env, call):
            _, destination = call.arguments
            # Fully defined bounded initial bytes let short/error effects be
            # compared without relying on otherwise unspecified OS output.
            env.write(destination, b'\xD6' * 255)
            env.write(destination, directory[:255])
            record(env, 2, call, env.read(destination + 248, 8))
            return len(directory.rstrip(b'\0')) if directory_result is None else directory_result

        def drive_type(env, call):
            index = env.calls_so_far(DRIVE)
            root = env.cstr(call.arguments[0])
            record(env, 3, call, root + b'\0' + env.read(call.arguments[0] + 248, 8))
            if index == 1:
                return current_type
            letter = chr(ord('A') + index - 2)
            if letter in optical:
                return 5
            return final_type if letter == 'Z' else (index % 5)

        for slot, name, argc, effect in (
            (REGISTRY, 'ADVAPI32.dll!RegQueryValueExA', 6, registry),
            (DIRECTORY, 'KERNEL32.dll!GetCurrentDirectoryA', 2, current_directory),
            (DRIVE, 'KERNEL32.dll!GetDriveTypeA', 1, drive_type),
        ):
            env.override(slot, effect)
        return {'app': app}

    return setup


def cases(random_source):
    def case(label, **options):
        return Case(label, DISC, scenario(random_source, **options),
                    receiver=lambda tokens: tokens['app'])

    for flag, cache in ((1, 0), (2, ord('D')), (0x12345678, 0xE7),
                        (0x80000000, 0xFF), (0xFFFFFF00, 0x15)):
        yield case(f'cached flag {flag:#x}, AL {cache:#x}, full EAX residue',
                   flag=flag, cache=cache, configuration=True)
    for byte in (0, 0x14, 0x15, 0x20, ord('D'), ord('q'), 0x7F, 0x80, 0xFF):
        yield case(f'genuine registry signed byte {byte:#x}', configuration=True,
                   payload=bytes([byte]) + b':\\different suffix\0', optical=('M',))
    yield case('one-byte nonterminated successful registry value',
               configuration=True, payload=b'Z', reported_size=1)
    yield case('capacity thirty successful registry value', configuration=True,
               payload=b'Q' + b'x' * 28 + b'\0', reported_size=30)
    yield case('nonnull uninitialized configuration bypasses registry',
               configuration=True, initialized=0, optical=('D',))
    for status, value_type, size in ((2, 1, 0), (5, 1, 17),
                                     (234, 1, 100), (0, 2, 12), (0, 0, 1)):
        yield case(f'error/wrong-type deterministic bounded outputs {status}/{value_type}',
                   configuration=True, status=status, value_type=value_type,
                   payload=b'Q:\\plausible\0', reported_size=size, optical=('B',))
    for optical in (('A',), ('M',), ('Z',), ('B', 'D', 'Z'), ()):
        yield case(f'null configuration scan optical {optical}', optical=optical)
    for drive_type in (0, 1, 2, 3, 4, 6, 0x105):
        yield case(f'current type {drive_type:#x} is not exact optical five',
                   current_type=drive_type, optical=('A',))
    yield case('current directory optical quirk caches zero', current_type=5,
               directory=b'R:\\CLAW\0')
    for label, directory, result in (
        ('empty output', b'\0', 0), ('short output', b'X\0', 1),
        ('exact fitting output', b'T:\\' + b'x' * 251 + b'\0', 254),
        ('zero-return defined failure effects', b'F:\\error\0', 0),
        ('required-size return defined failure effects', b'L:\\partial\0', 300),
    ):
        yield case(f'directory {label} still probes truncated root',
                   directory=directory, directory_result=result, optical=('C',))
    yield case('undefined OS high-word EAX transport stress on final miss',
               final_type=0x12340003, optical=())
    for _ in range(8):
        letter = chr(random_source.randrange(ord('A'), ord('Z') + 1))
        yield case(f'random virtual optical root {letter}', optical=(letter,),
                   directory=bytes([random_source.randrange(65, 91)]) + b':\\random\0')
