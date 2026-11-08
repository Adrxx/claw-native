"""Independent scenery callback cases, using unchanged animation callees."""
from clawparity.cases import Case

ENTRIES = (0x461730, 0x461750, 0x461770, 0x4617D0,
           0x461830, 0x461870, 0x4618E0, 0x461970)
ANIMATED = ENTRIES[5:]


def scenery(flags, state=0, z=0, enabled=0, animation="present", delta=7,
            countdown=19, timed=1, alias=None):
    def setup(env):
        actor = env.object(0x220, "actor", fill=0xA6)
        logic = env.object(0x20, "logic", fill=0xB7)
        settings = env.object(0x128, "settings", fill=0xC8)
        ani = env.object(0x18, "animation", fill=0xD9)
        frame = env.object(0x30, "animation-frame", fill=0)
        frames = env.object(4, "animation-frames", words=[frame])
        env.put(ani + 0xC, frames, 1)
        env.put(frame + 0x1C, 0x73AC1952)
        env.put(actor + 8, flags)
        env.put(actor + 0x64, z)
        env.put(actor + 0x6C, logic)
        env.put(logic + 0x1C, state)
        env.put(settings + 0x124, enabled)
        env.put(0x5371FC, settings)
        env.put(0x5430C4, delta)
        # Updater is a real embedded animation object, not a game fixture.
        env.put(actor + 0x18C, actor, ani, frame, 0, countdown, timed,
                1, 0x18792A3B, 0x4758697A, 0x3F800000)
        if animation in ("absent", "lookup-miss", "lookup-hit"):
            env.put(actor + 0x190, 0)
        if animation.startswith("lookup"):
            world = env.object(0x30, "world", fill=0)
            registry = env.object(0x24, "animation-registry", fill=0)
            env.put(actor + 0xC, world)
            env.put(world + 0x2C, registry)
            # Original CMap lookup: table +4, bucket count +8.
            env.put(registry + 0x18, 1)
            if animation == "lookup-hit":
                key = env.object(14, "animation-key", data=b"GAME_CYCLE100\0")
                node = env.object(16, "animation-map-node", words=[0, 0, key, ani])
                buckets = env.object(4, "animation-buckets", words=[node])
                env.put(registry + 0x14, buckets)
        if alias == "state-flags":
            env.put(actor + 8, 0)
            env.put(actor + 0x6C, actor + 8 - 0x1C)
        elif alias == "state-z":
            env.put(actor + 0x64, 0)
            env.put(actor + 0x6C, actor + 0x64 - 0x1C)
        elif alias == "settings-z":
            env.put(0x5371FC, actor + 0x64 - 0x124)
        elif alias == "state-settings":
            env.put(settings + 0x124, 0)
            env.put(actor + 0x6C, settings + 0x124 - 0x1C)
        return actor
    return setup


def case(label, function, **options):
    return Case(label, function, scenery(**options), arguments=(lambda actor: actor,))


def cases(random_source):
    for function in ENTRIES:
        for flags in (0, 1, 0x10000, 0x20000, 0xFFFFFFFF,
                      random_source.getrandbits(32) & ~0x30001):
            yield case(f"{function:x} initial flags {flags:x}", function, flags=flags)
        if function in ENTRIES[:2]:
            continue
        for state in (1, 5, 0xFFFFFFFF):
            yield case(f"{function:x} existing state {state:x}", function,
                       flags=random_source.getrandbits(32), state=state,
                       animation="absent" if function in ANIMATED else "present")
        for z in (0, 1, 0xFFFFFFFF, random_source.randrange(2, 10000)):
            for enabled in (0, 1, 0x80000000):
                yield case(f"{function:x} z {z:x} setting {enabled:x}", function,
                           flags=random_source.getrandbits(32) & ~0x30001,
                           z=z, enabled=enabled)
        for alias in ("state-flags", "state-z", "settings-z", "state-settings"):
            yield case(f"{function:x} alias {alias}", function,
                       flags=0x8540, alias=alias)
        if function in ANIMATED:
            for animation in ("lookup-miss", "lookup-hit"):
                for z in (0, 0x9753):
                    yield case(f"{function:x} {animation} z {z}", function,
                               flags=0x4820, animation=animation, z=z)
            for timed in (0, 1):
                for delta in (0, 1, 7, 19, 20, 0xFFFFFFFF):
                    yield case(f"{function:x} updater timed {timed} delta {delta}", function,
                               flags=0x12345678, state=5, delta=delta,
                               timed=timed)
            yield case(f"{function:x} stopped updater no countdown", function,
                       flags=0xABCDEF00, state=1, countdown=0)
