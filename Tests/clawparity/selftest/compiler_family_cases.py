"""Synthetic compiler frames only; no recovered game inputs."""
from clawparity.cases import Case
from clawparity.env import NativeCompilerContext
from clawparity.kernel import CONTEXT_ALL, STACK_BASE, STACK_SIZE, STACK_TOP


def cases(random_source):
    for frame in (STACK_BASE + 4, STACK_TOP, STACK_BASE + STACK_SIZE - 12):
        for head in (0xffffffff, STACK_BASE + 0x100):
            for continuation in (0x401080, 0x401090):
                values = [random_source.getrandbits(32) for _ in range(6)]
                def setup(env, frame=frame, head=head, continuation=continuation, values=values):
                    env.put(frame - 4, values[4], continuation, values[5])
                    return NativeCompilerContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                        *values[:4], 0x87654321, 0xabcdef01,
                        STACK_TOP + 0x100, frame, 0x401000, 0x8d7, head, continuation, 0, 0)
                yield Case(f"{frame:x}/{head:x}/{continuation:x}", 0x401000,
                           setup=setup, compiler_context=lambda value: value)
