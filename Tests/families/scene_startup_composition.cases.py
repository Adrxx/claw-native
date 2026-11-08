"""Independent original-derived sound-controller election and readiness cases."""
from clawparity.cases import Case

INITIALIZE = 0x4CA280
READY = 0x4CF7E0
GLOBAL = 0x532C10


def initialize_setup(parent_present, manager_present, device, payloads, old_fields, global_value):
    def setup(env):
        receiver = env.object(64, "sound-controller", data=payloads[0])
        parent = env.object(48, "parent", data=payloads[1])
        manager = env.object(136, "manager", data=payloads[2])
        env.put(receiver + 12, parent if parent_present else 0)
        env.put(receiver + 44, *old_fields)
        env.put(parent + 32, manager if manager_present else 0)
        env.put(manager + 120, device)
        env.put(GLOBAL, global_value)
        return receiver
    return setup


def ready_setup(manager, missing, payload, global_value):
    def setup(env):
        receiver = env.object(64, "sound-controller", data=payload)
        env.put(receiver + 44, manager, missing)
        env.put(GLOBAL, global_value)
        return receiver
    return setup


def cases(random_source):
    def payload(size):
        # Distinct nonzero bytes expose unintended zeroing and offset/width errors.
        return bytes(random_source.randrange(1, 256) for _ in range(size))

    paths = (
        ("no parent strict", False, False, 0, 0),
        ("no parent permissive", False, True, 1, 1),
        ("no manager strict", True, False, 0, 0),
        ("no device strict", True, True, 0, 0),
        ("device strict", True, True, 1, 0),
        ("no manager permissive", True, False, 0, 1),
        ("no device permissive", True, True, 0, 1),
        ("device permissive", True, True, 1, 1),
    )
    for repeat in range(4):
        for label, parent, manager, device, allow in paths:
            argument = (1, 2, 0x80000000, 0xFFFFFFFF)[repeat] if allow else 0
            device_value = (1, 0x80000000, 0xFFFFFFFF,
                            random_source.randrange(1, 1 << 32))[repeat] if device else 0
            old_fields = (random_source.randrange(1, 1 << 32),
                          random_source.randrange(2, 1 << 32))
            setup = initialize_setup(parent, manager, device_value,
                                     (payload(64), payload(48), payload(136)),
                                     old_fields, random_source.randrange(101, 1 << 32))
            yield Case(f"{label} variant {repeat}", INITIALIZE, setup,
                       receiver=lambda receiver: receiver, arguments=(argument,))

    # Every readiness truth combination, including arbitrary high-bit token/flag
    # values. These are opaque values, not dereferenced manager pointers.
    values = (0, 1, 2, 0x80000000, 0xFFFFFFFF,
              random_source.randrange(2, 1 << 32))
    for manager in values:
        for missing in values:
            yield Case(f"ready manager {manager:#x} missing {missing:#x}", READY,
                       ready_setup(manager, missing, payload(64),
                                   random_source.randrange(101, 1 << 32)),
                       receiver=lambda receiver: receiver)

    # A global-backed receiver aliases one output with the reset word. This makes
    # the original's final reset observable even if stores are reordered.
    for output_offset in (44, 48):
        for manager_present in (False, True):
            initial = payload(64)

            def aliased_setup(env, offset=output_offset, present=manager_present,
                              initial=initial):
                receiver = GLOBAL - offset
                env.write(receiver, initial)
                parent = env.object(48, "alias-parent", data=payload(48))
                manager = env.object(136, "alias-manager", data=payload(136))
                env.put(receiver + 12, parent)
                env.put(parent + 32, manager if present else 0)
                return receiver

            yield Case(f"reset aliases output +{output_offset} manager {manager_present}",
                       INITIALIZE, aliased_setup, receiver=lambda receiver: receiver,
                       arguments=(0x80000000,))
