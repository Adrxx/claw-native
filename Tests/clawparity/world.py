"""Small synthetic worlds for executing original creature constructors.

These helpers create input data, never replace game functions. Empty resource
maps and an absent collision plane are supported original paths, not evidence
of a loaded level. Resource values may be supplied to exercise lookup hits.
"""

RESOURCE_OFFSETS = {"sprites": 0x10, "logic": 0x14, "sounds": 0x28, "animations": 0x2C}
RECT_IMPORTS = {
    0x546D5C: {"name": "SetRect", "convention": "stdcall", "argc": 5},
    0x546CDC: {"name": "SetRectEmpty", "convention": "stdcall", "argc": 1},
}


def set_rect(env, call):
    env.put(call.arguments[0], *call.arguments[1:])
    return 1


def set_rect_empty(env, call):
    env.put(call.arguments[0], 0, 0, 0, 0)
    return 1


def rectangle_services(env):
    """Provide effects for the two imports already declared by the family.

    Declare both as kind=fixture, fixture=scripted, returns=u32, with the
    signatures in RECT_IMPORTS. Undeclared imports remain an error.
    """
    env.override(0x546D5C, set_rect)
    env.override(0x546CDC, set_rect_empty)


def _text(value):
    value = value.encode("ascii") if isinstance(value, str) else bytes(value)
    if not value or b"\0" in value:
        raise ValueError("resource keys must be nonempty and contain no NUL")
    return value


def cstring(env, text, name="world-key"):
    """Create a CString buffer with its reference count and size header."""
    text = _text(text)
    capacity = (len(text) + 4) & ~3
    buffer = env.object(12 + capacity, name, fill=0)
    env.put(buffer, 1, len(text), capacity - 1)
    env.write(buffer + 12, text + b"\0")
    return buffer + 12


def resource_manager(env, entries=None, bucket_count=17, name="resources"):
    """Build a manager containing the map consumed by original lookups.

    Entries map byte/string keys to existing emulated addresses or values.
    Buckets and linked associations are ordinary data; the original lookup
    hashes keys, follows collisions, compares strings and returns values.
    """
    if not isinstance(bucket_count, int) or not 1 <= bucket_count <= 4096:
        raise ValueError("bucket_count must be between 1 and 4096")
    entries = dict(entries or {})
    manager = env.object(0x40, name, fill=0)
    env.put(manager + 0x18, bucket_count, len(entries))
    if not entries:
        return manager
    buckets = env.object(4 * bucket_count, name + "-buckets", fill=0)
    env.put(manager + 0x14, buckets)
    for index, (key, value) in enumerate(entries.items()):
        key = _text(key)
        hashed = 0
        for byte in key:
            signed_byte = byte if byte < 128 else byte - 256
            hashed = (hashed * 33 + signed_byte) & 0xFFFFFFFF
        bucket = hashed % bucket_count
        key_address = cstring(env, key, f"{name}-key-{index}")
        link = buckets + 4 * bucket
        association = env.object(16, f"{name}-entry-{index}",
                                 words=[env.get(link), bucket, key_address, value], fill=0)
        env.put(link, association)
    return manager


def animation(env, duration=100, name="world-animation"):
    """One frame sufficient for original animation selection and timing setup.

    This is a synthetic sequence descriptor, without decoded image or audio
    payloads. It is not suitable evidence for rendering or animation playback.
    """
    if not 1 <= duration <= 0x7FFFFFFF:
        raise ValueError("duration must be a positive signed 32-bit integer")
    sequence = env.object(0x14, name, fill=0)
    frames = env.object(4, name + "-frames", fill=0)
    frame = env.object(0x20, name + "-frame", fill=0)
    env.put(sequence + 0xC, frames, 1)
    env.put(frames, frame)
    env.put(frame + 0x1C, duration)
    return sequence


def sprite(env, width=32, height=32, origin=(0, 0), name="world-sprite"):
    """One synthetic sprite frame for original image selection/bounds setup."""
    if not 1 <= width <= 0x7FFFFFFF or not 1 <= height <= 0x7FFFFFFF:
        raise ValueError("sprite dimensions must be positive signed 32-bit integers")
    resource = env.object(0x6C, name, fill=0)
    frames = env.object(4, name + "-frames", fill=0)
    frame = env.object(0x28, name + "-frame", fill=0)
    env.put(resource + 0x14, frames)
    env.put(resource + 0x64, 0, 0)
    env.put(frames, frame)
    env.put(frame + 0x18, origin[0], origin[1], width, height)
    return resource


def idle_registry(env, value=1):
    """Install a singleton synthetic LS_IDLE registry, preserving original lookup.

    The state value is a fixture parameter, not a recovered universal state ID.
    Other names intentionally miss. Repeated original callbacks will need the
    corresponding numeric-state/string table as well.
    """
    key = cstring(env, b"LS_IDLE", "idle-registry-key")
    node = env.object(20, "idle-registry-node", fill=0)
    env.put(node, node, node, 0, key, value)
    env.put(0x537668 + 0x18, node)
    return node


def world(env, *, owner_words=None, state_words=None, resources=None,
          collision_step=(64, 64), idle_state=1, bucket_count=17):
    """Return owner/state/world/collision addresses and resource managers.

    owner_words and state_words map byte offsets to individual 32-bit words.
    Both records start zeroed, with owner +0x38 disabling optional audio.
    Resources map category names from RESOURCE_OFFSETS to key/value mappings.
    Collision steps are configurable; the collision plane remains absent.
    Call rectangle_services separately after declaring those imports.
    """
    resources = dict(resources or {})
    if resources.keys() - RESOURCE_OFFSETS.keys():
        raise ValueError("unknown resource category")
    if len(collision_step) != 2 or any(not 1 <= n <= 0x7FFFFFFF for n in collision_step):
        raise ValueError("collision_step requires two positive signed 32-bit integers")
    owner = env.object(0x200, "world-owner", fill=0)
    state = env.object(0x180, "world-state", fill=0)
    level = env.object(0x40, "world-context", fill=0)
    collision = env.object(0x100, "world-collision", fill=0)
    env.put(owner + 0x38, 0xFFFFFFFF)
    for address, size, words in ((owner, 0x200, owner_words), (state, 0x180, state_words)):
        for offset, value in (words or {}).items():
            if offset % 4 or not 0 <= offset <= size - 4:
                raise ValueError("record fields must be aligned words within the record")
            env.put(address + offset, value)
    env.put(owner + 0xC, level)
    env.put(owner + 0x6C, state)
    env.put(level + 0x24, collision)
    env.put(collision + 0x64, *collision_step)
    managers = {}
    for category, offset in RESOURCE_OFFSETS.items():
        managers[category] = resource_manager(env, resources.get(category), bucket_count, category)
        env.put(level + offset, managers[category])
    registry = idle_registry(env, idle_state) if idle_state is not None else 0
    if idle_state is None:
        env.put(0x537668 + 0x18, 0)
    return {"owner": owner, "state": state, "world": level, "collision": collision,
            "managers": managers, "idle_registry": registry}
