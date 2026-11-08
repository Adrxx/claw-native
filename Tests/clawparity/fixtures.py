"""Ready-made effects for fixtures. An effect is called as effect(env, call) and returns EAX.

Effects run once on each side, so they must not keep state of their own. Use
env.calls_so_far(call.function) to behave differently on later calls.
"""
from .env import Halt, HarnessError


def returns(value):
    return lambda env, call: value


def sequence(*values):
    """Return values[0] on the first call, values[1] on the second, and the last one from then on."""
    return lambda env, call: values[min(env.calls_so_far(call.function), len(values)) - 1]


def allocate(size_argument=0, fail=False, fail_from_call=None):
    """The allocator: a new live object of the requested size, or 0 when told to fail."""
    def effect(env, call):
        if fail or (fail_from_call is not None and env.calls_so_far(call.function) >= fail_from_call):
            return 0
        return env.object(call.arguments[size_argument], name="allocation")
    return effect


def release(pointer_argument=0):
    """The deallocator. Freeing 0 is a no-op, as in the original."""
    def effect(env, call):
        if call.arguments[pointer_argument]:
            env.release(call.arguments[pointer_argument])
        return 0
    return effect


def halt():
    """A service the test must not pass: both sides stop here and are compared up to this call."""
    def effect(env, call):
        raise Halt()
    return effect


def store_words(pointer_argument, words, result=0):
    """Write `words` through a pointer argument, then return `result`."""
    def effect(env, call):
        env.put(call.arguments[pointer_argument], *words)
        return result
    return effect


def reallocate(pointer_argument=0, size_argument=1, fail=False, fail_from_call=None):
    """The C runtime realloc: allocate when the pointer is 0, free and return 0 when the size is 0,
    otherwise a new live object holding the old bytes up to the new size, with the old one freed.
    When told to fail it returns 0 and leaves the old object live, as the C runtime does."""
    def effect(env, call):
        pointer, size = call.arguments[pointer_argument], call.arguments[size_argument]
        if pointer and pointer not in env.spans:
            raise HarnessError(f"realloc of {pointer:#x}, which is not a live object")
        if pointer and not size:
            env.release(pointer)
            return 0
        if fail or (fail_from_call is not None and env.calls_so_far(call.function) >= fail_from_call):
            return 0
        moved = env.object(size, name="allocation")
        if pointer:
            env.write(moved, env.read(pointer, min(env.spans[pointer], size)))
            env.release(pointer)
        return moved
    return effect


def readable(env, address, count):
    """True when [address, address + count) lies inside one live object, the program image or the stack."""
    from .kernel import STACK_BASE, STACK_SIZE
    end = address + count
    if any(token <= address and end <= token + size for token, size in env.spans.items()):
        return True
    program = env.program
    return (program.base <= address and end <= program.base + program.size or
            STACK_BASE <= address and end <= STACK_BASE + STACK_SIZE)


def is_bad_read_ptr(env, call):
    """KERNEL32 IsBadReadPtr(pointer, size), stdcall: 0 when the whole range is readable memory of this run."""
    pointer, size = call.arguments[0], call.arguments[1]
    return 0 if not size or readable(env, pointer, size) else 1


def set_rect(env, call):
    """USER32 SetRect(rect, left, top, right, bottom), stdcall: stores the four values and returns 1."""
    env.put(call.arguments[0], *call.arguments[1:5])
    return 1


def set_rect_empty(env, call):
    """USER32 SetRectEmpty(rect), stdcall: stores four zeros and returns 1."""
    env.put(call.arguments[0], 0, 0, 0, 0)
    return 1


CATALOGUE = {
    "allocate": allocate(),
    "release": release(),
    "reallocate": reallocate(),
    "is-bad-read-ptr": is_bad_read_ptr,
    "set-rect": set_rect,
    "set-rect-empty": set_rect_empty,
    "return-zero": returns(0),
    "return-one": returns(1),
    "halt": halt(),
    "scripted": None,  # every case must supply the effect with env.override
}
