"""Independent inputs for the twelve v1.3 enemy lifecycle roots."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

ROOTS = (
    ("BearSailor", 0x40A020, 0x4C8, 0x50CAE8),
    ("Chameleon", 0x422290, 0x4B0, 0x50D410),
    ("CrazyHook", 0x435BA0, 0x4C0, 0x50E180),
    ("CutThroat", 0x439170, 0x4A8, 0x50E25C),
    ("Fish", 0x443020, 0x458, 0x50F514),
    ("HermitCrab", 0x44B500, 0x460, 0x50F90C),
    ("Mercat", 0x461E50, 0x508, 0x510264),
    ("Officer", 0x464850, 0x498, 0x510440),
    ("Parrot", 0x467AE0, 0x478, 0x51065C),
    ("PegLeg", 0x46AC10, 0x510, 0x510734),
    ("PunkRat", 0x475E90, 0x438, 0x51092C),
    ("Rat", 0x47F0C0, 0x448, 0x510AC4),
)
NEW = 0x4FCAEA


def routing(event, noise, result, installed=None, mutate=False, null_instance=False):
    def setup(env):
        world = env.object(0x180, "world", fill=0x67)
        logic = env.object(0x160, "logic", fill=0x93)
        alternate = env.object(0x160, "alternate-logic", fill=0xB2)
        instance = env.object(0x520, "instance", fill=noise)
        methods = env.object(0x80, "virtual-methods", fill=0)
        observations = env.object(0x200, "callback-observations", fill=0)
        env.put(world + 0x7C, logic)
        env.put(logic + 0x18, 0 if null_instance else instance, event)
        env.put(alternate + 0x18, instance, 0x10203040)
        env.put(instance, methods)
        env.put(instance + 0x10, world, logic)
        # Generic dispatch executes the real registry and CString code. Two
        # distinct strings let callback-driven event changes be observable.
        signed_event = event if event < 0x80000000 else event - 0x100000000
        low = min(signed_event, 0x7FFFFFFE)
        registry = env.object(24, "registry", fill=0x49)
        for index, text in enumerate((b"before-event", b"after-event")):
            string = env.object(76, "unique-string", fill=0x5D)
            env.put(string, 1, len(text), 63)
            env.write(string + 12, text + b"\0")
            env.put(registry + index * 12, string + 12)
        env.put(0x5ACD38, low, low + 1, registry, registry, 12, 0, 0x579)

        def callback(slot, argc):
            def effect(env, call):
                count = env.get(observations)
                at = observations + 4 + count * 28
                env.put(at, slot, call.receiver,
                        call.arguments[0] if argc else 0xF00DFACE,
                        env.get(world + 0x7C), env.get(logic + 0x18),
                        env.get(logic + 0x1C), env.get(0x5ACD50))
                env.put(observations, count + 1)
                if mutate:
                    env.put(world + 0x7C, alternate)
                    env.put(logic + 0x18, world)
                    if slot == 0x0C:
                        env.put(logic + 0x1C, low + 1)
                    elif slot >= 0x28:
                        env.put(logic + 0x1C, 0xFFFFFFFF)
                return result
            return effect

        for slot in range(0, 0x80, 4):
            argc = 1 if slot in (0x0C, 0x10, 0x14) else 0
            env.put(methods + slot, env.stub(f"virtual-{slot:02x}", "thiscall", argc,
                                          callback(slot, argc)))
        if installed is not None:
            env.put(instance, installed)
        return world
    return setup


def allocation_failure(noise):
    def setup(env):
        world = routing(0, noise, 0)(env)
        env.override(NEW, allocate(fail=True))
        return world
    return setup


def construction(noise):
    def setup(env):
        world = env.object(0x900, "constructor-world", fill=0)
        logic = env.object(0x200, "constructor-logic", fill=0)
        resources = env.object(0x1000, "resource-manager", fill=0)
        physics = env.object(0x200, "empty-physics", fill=0)
        resources_map = env.object(0x80, "empty-resource-map", fill=0)
        old = env.object(0x40, "old-publication", fill=0xB7)
        observer = env.object(0x1000, "allocation-observations", fill=0)
        env.put(world + 0xC, resources)
        env.put(world + 0x38, 0xFFFFFFFF)
        env.put(world + 0x5C, 19, 71)
        env.put(world + 0x74, 0x1234)
        env.put(world + 0x7C, logic)
        env.put(world + 0x124, 100)
        env.put(world + 0x1B0, world)
        env.put(logic + 0xC, resources)
        env.put(logic + 0x14, logic)
        env.put(logic + 0x18, old, 0)
        env.put(logic + 0x80, 25)
        for offset in (0x10, 0x14, 0x28, 0x2C):
            env.put(resources + offset, resources_map)
        collection = env.object(0x100, "world-collection", fill=0)
        env.put(collection + 0xC, resources)
        env.put(collection + 0x28, 10)
        env.put(collection + 0x34, 17)
        env.put(collection + 0x44, 10)
        env.put(collection + 0x50, 17)
        env.put(collection + 0x60, 10)
        env.put(resources + 8, collection)
        classes = env.object(0x80, "class-map", fill=0)
        buckets = env.object(4, "class-buckets", fill=0)
        association = env.object(16, "class-association", fill=0)
        classname = env.object(16, "class-name", data=b"GroundCannon\0")
        klass = env.object(0x20, "ground-cannon-class", fill=0)
        env.put(klass + 0x10, 0x44ABF0)
        env.put(association, 0, 0, classname, klass)
        env.put(buckets, association)
        env.put(classes + 0x14, buckets, 1)
        env.put(resources + 0x14, classes)
        env.put(resources + 0x24, physics)
        env.put(resources_map + 0x18, 1)
        env.put(physics + 0x64, 256, 256)
        env.put(0x5ACD54, 1)
        env.put(0x5ACD18, 0)
        env.put(0x5365D4, world)
        env.put(0x5AE2DC, 1)
        env.put(0x53F958, 0, 0, 0, 0)
        env.override(0x4A595B, returns(75))
        env.override(0x50C58C, returns(123456))

        def inflate(env, call):
            rect, dx, dy = call.arguments
            env.put(rect, env.get(rect) - dx, env.get(rect + 4) - dy,
                    env.get(rect + 8) + dx, env.get(rect + 12) + dy)
            return 1

        def new(env, call):
            n = env.calls_so_far(NEW) - 1
            env.put(observer + 16 * n, call.arguments[0], env.get(world + 0x7C),
                    env.get(logic + 0x18), env.get(logic + 0x1C))
            return env.object(call.arguments[0], "constructed-allocation", fill=0)

        env.override(NEW, new)
        env.override(0x50C468, inflate)
        return world
    return setup


def cases(random_source):
    events = (1, 2, 28, 29, 30, 31, 63, 79, 80, 81, 82, 83, 84,
              255, 256, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    for name, root, size, vtable in ROOTS:
        for event in events:
            noise = random_source.randrange(1, 256)
            result = random_source.getrandbits(32)
            yield Case(f"{name}: route {event:#x}", root,
                       routing(event, noise, result), arguments=(lambda w: w,))
        for event in (29, 30, 80, 81, 82, 83, 1, 84, 0xFFFFFFFF):
            yield Case(f"{name}: callback mutation {event:#x}", root,
                       routing(event, random_source.randrange(1, 256), 0x80004005, mutate=True),
                       arguments=(lambda w: w,))
        for event in (80, 81, 82, 83):
            yield Case(f"{name}: installed lifecycle no-op {event}", root,
                       routing(event, random_source.randrange(1, 256), 0, installed=vtable),
                       arguments=(lambda w: w,))
        yield Case(f"{name}: dormant null instance", root,
                   routing(1000, 0xB3, 0, null_instance=True), arguments=(lambda w: w,))
        yield Case(f"{name}: original constructor and initializer", root,
                   construction(random_source.randrange(1, 256)), arguments=(lambda w: w,))
