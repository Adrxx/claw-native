"""Original-only inputs for MFC record constructors and intrusive prepend."""
from clawparity.cases import Case

THREAD = 0x501F01
MODULE = 0x501FDE
PREPEND = 0x502F26


def patterned(random_source, size):
    # Nonzero bytes make omitted clearing and over-wide stores observable.
    return bytes(random_source.randrange(1, 256) for _ in range(size))


def record_setup(data, prefix):
    def setup(env):
        block = env.object(len(data), "record-with-canaries", data=data)
        return {"receiver": block + prefix}
    return setup


def list_setup(data, layout, link_offset, head_kind):
    def setup(env):
        block = env.object(len(data), "list-and-node-canaries", data=data)
        owner = block + 64
        if layout == "separate":
            node = env.object(256, "new-node", data=data[:256]) + 64
        elif layout == "same":
            node = owner
        elif layout == "node-before-owner":
            node = owner - 32
        else:
            node = owner + 32
        previous = env.object(96, "previous-node", data=data[:96]) + 16
        if head_kind == "empty":
            head = 0
        elif head_kind == "self":
            head = node
        elif head_kind == "owner":
            head = owner
        else:
            head = previous
        env.put(owner, head, link_offset & 0xFFFFFFFF)
        return {"receiver": owner, "node": node}
    return setup


def cases(random_source):
    # Minimum touched sizes and allocation-sized objects, with interior receivers
    # and all bytes compared, catch stores past the exact declared field widths.
    for size, prefix in ((0x108, 0), (0x118, 0), (0x138, 16), (0x139, 17)):
        for trial in range(3):
            yield Case(f"thread size {size:x} prefix {prefix} pattern {trial}",
                       THREAD, record_setup(patterned(random_source, size), prefix),
                       receiver=lambda t: t["receiver"])

    arguments = (0, 1, 0xFF, 0x100, 0x101, 0xFFFFFF00,
                 0xFFFFFFFF, 0x12345678, 0x80000080)
    arguments += tuple(random_source.getrandbits(32) for _ in range(8))
    for index, argument in enumerate(arguments):
        for size, prefix in ((0x106C, 0), (0x1074, 0), (0x1095, 17)):
            yield Case(f"module arg {argument:08x} pattern {index} size {size:x}",
                       MODULE, record_setup(patterned(random_source, size), prefix),
                       receiver=lambda t: t["receiver"], arguments=(argument,))

    # Signed offsets are simply modulo-32-bit address addition. Every resulting
    # link slot has real backing, including slots overlapping owner/head/offset.
    layouts = (("separate", (-32, -1, 0, 1, 4, 7, 16, 63)),
               ("same", (0, 1, 4, 8, 17)),
               ("node-before-owner", (0, 32, 33, 36, 40)),
               ("node-after-owner", (-32, -31, -28, 0, 7)))
    for layout, offsets in layouts:
        for offset in offsets:
            for head_kind in ("empty", "previous", "self", "owner"):
                yield Case(f"prepend {layout} link {offset} head {head_kind}",
                           PREPEND,
                           list_setup(patterned(random_source, 256), layout,
                                      offset, head_kind),
                           receiver=lambda t: t["receiver"],
                           arguments=(lambda t: t["node"],))
    for trial in range(12):
        offset = random_source.randrange(-32, 96)
        yield Case(f"prepend random offset {offset} pattern {trial}", PREPEND,
                   list_setup(patterned(random_source, 256), "separate", offset,
                              "previous"),
                   receiver=lambda t: t["receiver"],
                   arguments=(lambda t: t["node"],))

    # Source-capable calls retain the physical caller frame and its actual
    # continuation. These leaf constructors have no prologue: opaque EBP and
    # an existing registration chain must survive without being dereferenced.
    from clawparity.env import NativeSourceContext
    from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

    def source_setup(function, data, prefix, frame, ebp, chained, registers,
                     flags, stack_data, argument, return_pc, receiver_low=None):
        def setup(env):
            block = env.object(len(data), "source-record-canaries", data=data)
            receiver = block + prefix
            if receiver_low is not None:
                receiver += (receiver_low - receiver) & 0xFF
            env.write(STACK_BASE, stack_data)
            head = 0xFFFFFFFF
            if chained:
                # Three real caller records, away from all selected call slots.
                for offset in (0x480, 0x420, 0x400):
                    record = STACK_BASE + offset
                    env.put(record, head, 0x50235D, 0xA5A5A5A5, 0xFFFFFFFF)
                    head = record
            env.put(frame, return_pc)
            if function == MODULE:
                env.put(frame + 4, argument)
            source = NativeSourceContext(72, 1, 0x7FF, 0x7FF,
                registers[0], registers[1], receiver, registers[2],
                registers[3], registers[4], ebp, frame, function, flags, head,
                0x472, 0, 0)
            return {"receiver": receiver, "source": source}
        return setup

    frames = (STACK_BASE + 32, STACK_TOP, STACK_BASE + STACK_SIZE - 8)
    source_arguments = (0, 1, 0xFF, 0x100, 0x101, 0xFFFFFF00,
                        0xFFFFFFFF, 0x12345678, 0x80000080)
    source_arguments += tuple(random_source.getrandbits(32) for _ in range(8))
    serial = 0
    for function, object_size, return_pc in ((THREAD, 0x118, 0x50235D),
                                            (MODULE, 0x1074, 0x502396)):
        for frame in frames:
            for ebp in (0, 1, 0xFFFFFFFF, frame, frame + 1,
                        0x12345679, random_source.getrandbits(32)):
                for chained in (False, True):
                    for prefix in (16, 17):
                        registers = tuple(random_source.getrandbits(32) for _ in range(5))
                        # Vary every flag supported by the source contract.
                        # Control flags are outside its declared input domain.
                        flag_patterns = (2, 0x8D7, 3, 6, 0x12, 0x42, 0x82, 0x802)
                        flags = (flag_patterns[serial % len(flag_patterns)]
                                 if serial % 2 == 0 else
                                 2 | (random_source.getrandbits(32) & 0x8D5))
                        argument = source_arguments[serial % len(source_arguments)]
                        # Nonzero distinct record and stack bytes expose stray
                        # writes, absent partial-register retention and frames.
                        stack_pattern = patterned(random_source, 257)
                        stack_data = (stack_pattern * ((STACK_SIZE + 256) // 257))[:STACK_SIZE]
                        data = patterned(random_source, object_size + prefix + 32)
                        yield Case(f"source {function:x} frame {frame:x} ebp {ebp:x} "
                                   f"chain {int(chained)} prefix {prefix} trial {serial}",
                            function, source_setup(function, data, prefix, frame, ebp,
                                chained, registers, flags, stack_data, argument, return_pc),
                            receiver=lambda t: t["receiver"],
                            arguments=(argument,) if function == MODULE else (),
                            source_context=lambda t: t["source"],
                            source_return_pc=return_pc)
                        serial += 1


    # LEA adds 0x1048 before MOV CL replaces only the low byte. Enumerating
    # every receiver residue observes both sides of each carry into high bits.
    for receiver_low in range(256):
        frame = frames[receiver_low % len(frames)]
        ebps = (0, 1, 0xFFFFFFFF, frame, frame + 1, 0x12345679,
                random_source.getrandbits(32))
        ebp = ebps[receiver_low % len(ebps)]
        registers = tuple(random_source.getrandbits(32) for _ in range(5))
        flags = 2 | (random_source.getrandbits(32) & 0x8D5)
        argument = source_arguments[receiver_low % len(source_arguments)]
        stack_pattern = patterned(random_source, 257)
        stack_data = (stack_pattern * ((STACK_SIZE + 256) // 257))[:STACK_SIZE]
        yield Case(f"source module receiver low byte {receiver_low:02x}",
            MODULE, source_setup(MODULE, patterned(random_source, 0x1074 + 320),
                16, frame, ebp, bool(receiver_low & 1), registers, flags,
                stack_data, argument, 0x502396, receiver_low),
            receiver=lambda t: t["receiver"], arguments=(argument,),
            source_context=lambda t: t["source"], source_return_pc=0x502396)

    # Prepend's semantic void ABI coexists with an observable machine EAX.
    # The full source envelope observes its scratch registers and PUSH residue.
    def prepend_source_setup(data, layout, offset, head_kind, frame, ebp,
                             chained, registers, flags, stack_data):
        def setup(env):
            tokens = list_setup(data, layout, offset, head_kind)(env)
            env.write(STACK_BASE, stack_data)
            head = 0xFFFFFFFF
            if chained:
                for displacement in (0x680, 0x640, 0x600):
                    record = STACK_BASE + displacement
                    env.put(record, head, 0x5031C7, 0xFFFFFFFF, 0x13579BDF)
                    head = record
            env.put(frame, 0x5031C7, tokens["node"])
            tokens["source"] = NativeSourceContext(72, 1, 0x7FF, 0x7FF,
                registers[0], registers[1], tokens["receiver"], registers[2],
                registers[3], registers[4], ebp, frame, PREPEND, flags, head,
                0x472, 0, 0)
            return tokens
        return setup

    prepend_frames = (STACK_BASE + 4, STACK_BASE + 32, STACK_TOP,
                      STACK_BASE + STACK_SIZE - 8)
    prepend_ebps = (0, 1, 0xFFFFFFFF, 0x12345679)
    trial = 0
    for layout, offsets in layouts:
        for offset in offsets:
            for head_kind in ("empty", "previous", "self", "owner"):
                for chained in (False, True):
                    frame = prepend_frames[trial % len(prepend_frames)]
                    ebp = (prepend_ebps + (frame, frame + 1,
                            random_source.getrandbits(32)))[trial % 7]
                    registers = tuple(random_source.getrandbits(32) for _ in range(5))
                    flags = 2 | (random_source.getrandbits(32) & 0x8D5)
                    stack_pattern = patterned(random_source, 257)
                    stack_data = (stack_pattern * ((STACK_SIZE + 256) // 257))[:STACK_SIZE]
                    yield Case(f"source prepend {layout} offset {offset} head {head_kind} "
                               f"frame {frame:x} chain {int(chained)} trial {trial}",
                        PREPEND, prepend_source_setup(patterned(random_source, 256),
                            layout, offset, head_kind, frame, ebp, chained,
                            registers, flags, stack_data),
                        receiver=lambda t: t["receiver"],
                        arguments=(lambda t: t["node"],),
                        source_context=lambda t: t["source"], source_return_pc=0x5031C7)
                    trial += 1

    # Stack data and incoming argument words are real aliases. All accesses
    # remain backed; no case overwrites the genuine continuation word.
    def prepend_stack_setup(kind, frame, registers, flags, stack_data, data, chained):
        def setup(env):
            env.write(STACK_BASE, stack_data)
            block = env.object(len(data), "prepend-stack-alias-canaries", data=data)
            owner, node, target = block + 32, block + 128, block + 193
            old_esi = registers[3]
            if kind == "argument-link":
                target = frame + 4
            elif kind == "saved-esi-link":
                target = frame - 4
            elif kind == "stack-owner":
                owner = frame - 32
            elif kind == "stack-node":
                node, target = frame + 32, frame + 39
            elif kind == "stack-argument-owner":
                owner = frame + 4
            elif kind == "push-offset-alias":
                owner = frame - 8
            elif kind == "push-head-alias":
                # The node itself is an opaque uint32 operand: only its sum
                # with the captured offset is dereferenced. The saved ESI is
                # equal to that operand, so publication preserves its witness.
                owner = frame - 4
                node = (target - 0x5031C7) & 0xFFFFFFFF
                old_esi = node
            offset = (target - node) & 0xFFFFFFFF
            env.put(frame, 0x5031C7, node)
            if kind == "push-head-alias":
                env.put(owner, 0x2468ACE1)
            elif kind == "stack-argument-owner":
                # Head equals the actual incoming node argument.
                env.put(owner + 4, offset)
            else:
                env.put(owner, old_esi if kind == "saved-esi-link" else 0xA53179BD, offset)
            head = 0xFFFFFFFF
            if chained:
                for displacement in (0x780, 0x740, 0x700):
                    record = STACK_BASE + displacement
                    env.put(record, head, 0x5031C7, 0xAAAAAAAA, 0xFFFFFFFF)
                    head = record
            source = NativeSourceContext(72, 1, 0x7FF, 0x7FF,
                registers[0], registers[1], owner, registers[2], old_esi,
                registers[4], (0, 1, 0xFFFFFFFF, frame + 1)[flags % 4],
                frame, PREPEND, flags, head, 0x472, 0, 0)
            return {"receiver": owner, "node": node, "source": source}
        return setup

    for kind in ("argument-link", "saved-esi-link", "stack-owner", "stack-node",
                 "stack-argument-owner", "push-offset-alias", "push-head-alias"):
        for chained in (False, True):
            for flags in (2, 0x8D7, 0x802, 0x42):
                registers = tuple(random_source.getrandbits(32) for _ in range(5))
                stack_pattern = patterned(random_source, 257)
                stack_data = (stack_pattern * ((STACK_SIZE + 256) // 257))[:STACK_SIZE]
                yield Case(f"source prepend stack {kind} chain {int(chained)} flags {flags:x}",
                    PREPEND, prepend_stack_setup(kind, STACK_TOP, registers, flags,
                        stack_data, patterned(random_source, 256), chained),
                    receiver=lambda t: t["receiver"], arguments=(lambda t: t["node"],),
                    source_context=lambda t: t["source"], source_return_pc=0x5031C7)
