"""Blind original cases: physical noncontinuable prefix, never exception dispatch.

The static exception storage retains loader BSS state. Neither its constructor
nor its contents are tested here. The immutable image template is never edited.
"""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.fixtures import halt

WRAPPER = 0x4F50FD
HELPER = 0x4A5690
RAISE = 0x546958
_CPU = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp',
        'eip', 'eflags', 'fsHead')


def setup_case(root, source_mode, profile, registers, pattern):
    def setup(env):
        # Preserve all original image inputs, including the 32-byte template.
        env.write(0x01FF0000, pattern * (0x20000 // len(pattern)))
        journal = env.object(256, 'physical raise observation', fill=0xA7)
        guard = env.object(128, 'live pointer cell and distinct canaries',
                           data=pattern * 4)
        cell = guard + (4, 20, 60, 116)[profile % 4]
        env.put(cell, 0x540748)
        # Opaque helper metadata transport may use interior backing identities;
        # canonical profiles retain the real ThrowInfo record unchanged.
        metadata = 0x51EB68
        if profile % 3 == 1:
            opaque = env.object(96, 'opaque helper metadata transport',
                                data=pattern * 3)
            metadata = opaque + (4, 28, 76)[profile % 3]
        frame = (0x01FF0100, 0x02000000, 0x02007FF4,
                 0x0200FED0, 0x01FF8014, 0x02004004,
                 0x02008000)[profile % 7]
        fs = 0xFFFFFFFF
        if profile % 2:
            fs = 0x01FF0080
            env.put(0x01FF0040, 0xFFFFFFFF, 0x508525, registers[2])
            env.put(fs, 0x01FF0040, 0x508539, registers[3])

        def physical_raise(e, call):
            # Observe actual arguments and pointed-to vector. No expected owned
            # effects are projected, and no behavioral assertion runs here.
            e.put(journal, call.function, call.receiver, call.stack_pointer,
                  call.source_return_pc, len(call.arguments), *call.arguments)
            e.write(journal + 48, e.read(call.arguments[3], 12))
            if call.source_context is not None:
                e.put(journal + 80, *(getattr(call.source_context, n) for n in _CPU))
            # The actual immutable image supplies noncontinuable flags 1.
            # The sole physical service always stops and never returns.
            return halt()(e, call)

        env.override(RAISE, physical_raise)
        tokens = {'cell': cell, 'metadata': metadata}
        if source_mode:
            source = NativeSourceContext(
                size=72, version=1, inputMask=0x7FF, outputMask=0x7FF,
                preserveMask=0x472, eax=registers[0], ebx=registers[1],
                ecx=registers[2], edx=registers[3], esi=registers[4],
                edi=registers[5], ebp=registers[6], esp=frame, eip=root,
                eflags=registers[7], fsHead=fs)
            env.put(frame, 0x502F9C if root == WRAPPER else 0x4F5116)
            if root == HELPER:
                env.put(frame + 4, cell, metadata)
            tokens['source'] = source
        return tokens
    return setup


def cases(random_source):
    # Fourteen independent profiles per root/mode keep input combinations small
    # while changing frames, flags, FS, poisoned saves and pointer identities.
    for profile in range(14):
        registers = [random_source.getrandbits(32) for _ in range(7)]
        registers[6] = (0, 0xFFFFFFFF, 0x80000000, 0x13579BDF,
                        registers[6])[profile % 5]
        arithmetic = (0, 1, 4, 0x10, 0x40, 0x80, 0x800,
                      0x8D5, random_source.getrandbits(32) & 0x8D5)
        registers.append(2 | arithmetic[profile % len(arithmetic)])
        pattern = bytes(random_source.randrange(1, 256) for _ in range(32))
        for root in (WRAPPER, HELPER):
            for source_mode in (False, True):
                options = {}
                if root == HELPER:
                    options['arguments'] = (lambda t: t['cell'],
                                            lambda t: t['metadata'])
                if source_mode:
                    options['source_context'] = lambda t: t['source']
                    options['source_return_pc'] = (0x502F9C if root == WRAPPER
                                                   else 0x4F5116)
                yield Case(
                    f'{root:08x} {"source" if source_mode else "ordinary"} '
                    f'loader-BSS pointer transport {profile}', root,
                    setup_case(root, source_mode, profile, registers, pattern),
                    expect='halt', **options)
