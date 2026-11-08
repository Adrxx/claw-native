"""Independent pointer, null and distinguished resource-token inputs."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.fixtures import allocate, release, halt
from clawparity.kernel import STACK_TOP

ROOT = 0x4F65F2
RETURN_PC = 0x40B83F


def byte_length(env, call):
    pointer = call.arguments[0]
    length = 0
    while env.read(pointer + length, 1) != b"\0":
        length += 1
    return length


def world(payload, offset=0, alias=None, resource=None, source=False,
          witnesses=(), flags=2, fs=False, stop_new=False, static=False):
    def setup(env):
        env.override(0x5469E4, byte_length)
        env.override(0x4F63EC, halt() if stop_new else allocate())
        env.override(0x4F6428, release())
        if static:
            receiver, token = 0x53499C, 0x534938
            # Genuine uninitialized image caller: zero token storage.
            env.write(token, b"\0")
            env.put(receiver, 0xDCA73189)
        else:
            receiver = env.object(4, "minimal receiver", words=[0xDCA73189])
            token = 0
            if payload is not None:
                storage = env.object(offset + len(payload) + 1, "ANSI input", fill=0xAD)
                token = storage + offset
                env.write(token, payload + b"\0")
            if alias == "source":
                receiver = token
            elif alias == "slot":
                receiver = 0x52E1CC
            elif alias == "custom-empty":
                empty = env.object(13, "independent empty header", fill=0xB7)
                env.put(empty, 0xFFFFFFFF, 0, 0)
                env.write(empty + 12, b"\0")
                env.put(0x52E1CC, empty + 12)
        if resource is not None:
            token = resource[0]
            content = resource[1]
            manager = env.object(4, "warm TLS manager", words=[37])
            module = env.object(16, "warm module state", fill=0)
            env.put(module + 12, 0x63A70001)
            holder = env.object(8, "warm module holder", words=[0xBA7319, module])
            table = env.object(8, "warm TLS slots", words=[0, holder])
            tls = env.object(16, "warm TLS record", fill=0)
            env.put(tls + 8, 2, table)
            env.put(0x53EC9C, 1)
            env.put(0x540AF0, manager)

            def lookup(env, call):
                return tls

            def load(env, call):
                capacity = call.arguments[3]
                copied = content[:max(0, capacity - 1)]
                env.write(call.arguments[2], copied + b"\0")
                return len(copied)

            def decrement(env, call):
                value = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
                env.put(call.arguments[0], value)
                return value

            # Real imported WinAPI boundaries only; module/TLS/CString helpers
            # execute their unchanged original bodies on the declared warm graph.
            env.put(0x546A7C, env.stub("KERNEL32.dll!TlsGetValue", "stdcall", 1, lookup))
            env.put(0x546D28, env.stub("USER32.dll!LoadStringA", "stdcall", 4, load))
            env.put(0x5469E8, env.stub("KERNEL32.dll!InterlockedDecrement", "stdcall", 1, decrement))
        tokens = {"receiver": receiver, "token": token}
        if source:
            context = NativeSourceContext()
            context.size, context.version = 72, 1
            context.inputMask = context.outputMask = 0x7FF
            context.preserveMask = 0x472
            context.eax, context.ebx, context.edx, context.esi, context.edi, context.ebp = witnesses
            context.ecx, context.esp, context.eip = receiver, STACK_TOP - 0x1000, ROOT
            context.eflags, context.fsHead = flags, 0xFFFFFFFF
            env.write(context.esp - 0x800, bytes(range(256)) * 8)
            if fs:
                context.fsHead = context.esp + 0x100
                env.put(context.fsHead, 0xFFFFFFFF, 0x401234, 0xA7315)
            tokens["source"] = context
        return tokens
    return setup


def pair(label, random_source, **options):
    for source in (False, True):
        witnesses = tuple(random_source.getrandbits(32) for _ in range(6))
        yield Case(label + (" full-source" if source else " ordinary"), ROOT,
                   setup=world(source=source, witnesses=witnesses, **options),
                   receiver=lambda t: t["receiver"], arguments=(lambda t: t["token"],),
                   source_context=(lambda t: t["source"]) if source else None,
                   source_return_pc=RETURN_PC if source else 0,
                   expect="halt" if options.get("stop_new") else "return",
                   covers=("declared warm caller memory" if options.get("resource") else "declared pointer/null caller memory",
                           "scalar resource identifier, no string mapping" if options.get("resource") else "minimal receiver and byte string spans"))


def cases(random_source):
    yield from pair("null minimal object", random_source, payload=None)
    yield from pair("actual static image caller", random_source, payload=None, static=True)
    yield from pair("empty byte pointer", random_source, payload=b"")
    yield from pair("pointer slot receiver alias", random_source, payload=None, alias="slot")
    yield from pair("indirect alternate empty pointer", random_source, payload=None, alias="custom-empty")
    for length in (1, 2, 3, 4, 5, 7, 8, 15, 16, 31, 32, 63, 127, 255, 256, 513):
        payload = bytes(random_source.randrange(1, 256) for _ in range(length))
        yield from pair(f"ANSI byte length {length}", random_source,
                        payload=payload, offset=length % 4,
                        flags=(2, 0x47, 0x897)[length % 3], fs=bool(length % 2))
    for offset in range(4):
        yield from pair(f"receiver overwrites source offset {offset}", random_source,
                        payload=b"abcdefghijklmnopqrst", offset=offset, alias="source")
    yield from pair("embedded NUL ends bytes", random_source, payload=b"A\x80\0TAIL\xff")
    for identifier, content in ((1, b""), (0x7FFF, b"A"), (0x8000, b"\x80\xffABC"),
                                (0xFFFF, bytes(range(1, 255))),
                                (37, b"Z" * 600)):
        yield from pair(f"warm resource token {identifier} length {len(content)}", random_source,
                        payload=None, resource=(identifier, content), fs=True)
    # Allocation failure has no normal root return; retain honest service prefixes.
    yield from pair("new physical stop", random_source, payload=b"allocation needed", stop_new=True)
