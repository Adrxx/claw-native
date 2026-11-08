"""Independent original source-frame cases; failure evidence stops at RaiseException."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt

FACTORY, RECORD, MAP, LIST = 0x502301, 0x50210b, 0x4f5e89, 0x4f5133
LOCAL_ALLOC, RAISE = 0x546aa8, 0x546958
REGISTERS = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eip', 'eflags', 'fsHead')


def setup_for(function, pc, argument, profile, offset=0, fail=False, stack_record=False):
    registers, stack_pointer, flags, chain_depth, pattern, padding = profile

    def setup(env):
        # Distinct initial saved words make physical prologue/epilogue stores observable.
        env.write(0x1ff0000, pattern * (0x20000 // len(pattern)))
        env.object(padding, 'allocation-address-padding', fill=0x71)
        size = 0x84 if function == RECORD else 0x1c
        backing = env.object(size + 32, 'record-with-canaries', data=(pattern * 16)[:size + 32])
        receiver = backing + 8 + offset
        if stack_record:
            receiver = stack_pointer + 0x180 + offset
            env.write(receiver - 8, (pattern * 16)[:size + 32])
        fs_head = 0xffffffff
        # Valid, disjoint, nonterminal source registration chains.
        for index in range(chain_depth):
            link = 0x200e000 + index * 0x20
            env.put(link, fs_head, 0x508511, 0xffffffff)
            fs_head = link
        source = NativeSourceContext()
        source.size, source.version = 72, 1
        source.inputMask = source.outputMask = 0x7ff
        source.preserveMask = 0x472
        for field, value in zip(REGISTERS[:7], registers):
            setattr(source, field, value)
        if function != FACTORY:
            source.ecx = receiver
        source.esp, source.eip, source.eflags, source.fsHead = stack_pointer, function, flags, fs_head
        env.put(stack_pointer, pc)
        if function in (MAP, LIST):
            env.put(stack_pointer + 4, argument)
        log = env.object(512, 'physical-service-observation', fill=0)

        def record_call(call, slot):
            context = call.source_context
            values = [call.function, call.receiver, call.receiver2, call.stack_pointer,
                      call.source_return_pc, len(call.arguments), *call.arguments]
            values.extend(getattr(context, name) for name in REGISTERS)
            env.put(log + slot, *values)
            # Capture source registration and caller words without fixture assertions.
            head = context.fsHead
            if head != 0xffffffff:
                env.write(log + slot + 128, env.read(head, 16))
            env.write(log + slot + 160, env.read(call.stack_pointer, 32))

        def physical_alloc(env, call):
            record_call(call, 0)
            count = env.calls_so_far(LOCAL_ALLOC)
            env.put(log + 240, count)
            if fail and count == 1:
                return 0
            # LocalAlloc flags 0x40 supplies genuinely fresh zeroed live backing.
            result = env.object(call.arguments[1], 'LocalAlloc-zeroed', fill=0)
            env.put(log + 244, result)
            return result

        def physical_raise(env, call):
            record_call(call, 256)
            env.write(log + 480, env.read(call.arguments[3], 12))
            raise Halt()

        env.override(LOCAL_ALLOC, physical_alloc)
        env.override(RAISE, physical_raise)
        return {'source': source, 'receiver': receiver}

    return setup


def cases(random_source):
    boundary = (0, 1, 10, 0xffffffff, 0x80000000, 0x7fffffff)
    for index in range(40):
        values = tuple(random_source.getrandbits(32) for _ in range(7))
        if index < len(boundary):
            values = tuple(boundary[(index + field) % len(boundary)] for field in range(7))
        esp = (0x1ff1000, 0x2000000, 0x2008000, 0x200fa00)[index % 4] - (index % 11) * 4
        flags = 2 | (random_source.getrandbits(12) & 0x8d5)
        pattern = bytes(random_source.randrange(1, 256) for _ in range(64))
        profile = (values, esp, flags, index % 4, pattern, 16 + (index % 13) * 32)
        argument = boundary[index] if index < len(boundary) else random_source.getrandbits(32)
        entries = ((MAP, 0x502137), (MAP, 0x502145), (LIST, 0x502153),
                   (RECORD, 0x502329), (FACTORY, 0x5033be))
        for function, pc in entries:
            yield Case(f'full source {function:x} return {pc:x} profile {index}', function,
                       setup_for(function, pc, argument, profile, offset=index % 4),
                       receiver=0 if function == FACTORY else lambda tokens: tokens['receiver'],
                       arguments=(argument,) if function in (MAP, LIST) else (),
                       source_context=lambda tokens: tokens['source'], source_return_pc=pc)
        if index % 4 == 0:
            yield Case(f'physical null then original throw prefix {index}', FACTORY,
                       setup_for(FACTORY, 0x5033be, 0, profile, fail=True), expect='halt',
                       source_context=lambda tokens: tokens['source'], source_return_pc=0x5033be)
        if index % 5 == 0:
            for function, pc in ((MAP, 0x502137), (LIST, 0x502153)):
                yield Case(f'disjoint stack record {function:x} profile {index}', function,
                           setup_for(function, pc, argument, profile, offset=index % 4, stack_record=True),
                           receiver=lambda tokens: tokens['receiver'], arguments=(argument,),
                           source_context=lambda tokens: tokens['source'], source_return_pc=pc)
