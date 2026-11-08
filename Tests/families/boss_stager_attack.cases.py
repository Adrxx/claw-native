"""Independent original-behavior cases for the Stager contact callback."""
from clawparity.cases import Case

ATTACK = 0x48E430
PLAYER = 0x537E88
MANAGER = 0x5371FC
TIMER = 0x53C9F8


def attack(label, mode, x, y, timer, flags, contents, alias=None):
    def setup(env):
        def object_at(name):
            return env.object(len(contents), name, data=contents)

        actor = object_at("actor")
        primary = object_at("captured-primary")
        player = object_at("player")
        manager = object_at("manager")
        coordinates = object_at("coordinates")
        alternate = object_at("alternate-record")
        alternate_player = object_at("alternate-player")
        alternate_manager = object_at("alternate-manager")
        env.put(alternate_player + 0x50, y ^ 0xF00DBEEF)
        env.put(alternate_manager + 0x2C, alternate)
        env.put(actor + 8, flags)
        env.put(actor + 0x6C, primary)
        env.put(player + 0xCC, mode)
        env.put(player + 0x4C, x, y)
        env.put(manager + 0x2C, coordinates)
        env.put(PLAYER, player)
        env.put(MANAGER, manager)
        env.put(TIMER, timer)

        if alias == "player-reload":
            env.put(manager + 0x2C, PLAYER - 0x44)
            env.put(player + 0x4C, alternate_player)
        elif alias == "manager-reload":
            env.put(manager + 0x2C, MANAGER - 0x44)
            env.put(player + 0x4C, alternate_manager)
        elif alias == "coordinate-pointer-reload":
            env.put(manager + 0x2C, manager - 0x18)
            env.put(player + 0x4C, alternate)
        elif alias == "x-overwrites-player-y":
            env.put(manager + 0x2C, player + 0x0C)
        elif alias == "primary-captured-before-x":
            env.put(manager + 0x2C, actor + 0x28)
            env.put(player + 0x4C, alternate)
        elif alias == "primary-captured-before-y":
            env.put(manager + 0x2C, actor + 0x24)
            env.put(player + 0x50, alternate)
        elif alias == "x-overwrites-timer":
            env.put(manager + 0x2C, TIMER - 0x44)
        elif alias == "y-overwrites-timer":
            env.put(manager + 0x2C, TIMER - 0x48)
        elif alias == "x-overwrites-flags":
            env.put(manager + 0x2C, actor - 0x3C)
        elif alias == "y-overwrites-flags":
            env.put(manager + 0x2C, actor - 0x40)
        elif alias == "primary-overwrites-x":
            env.put(actor + 0x6C, coordinates + 0x28)
        elif alias == "primary-overwrites-y":
            env.put(actor + 0x6C, coordinates + 0x2C)
        elif alias == "primary-overwrites-flags":
            env.put(actor + 0x6C, actor - 0x14)
        elif alias == "primary-overwrites-timer":
            env.put(actor + 0x6C, TIMER - 0x1C)
        elif alias == "actor-is-player":
            env.put(PLAYER, actor)
            env.put(actor + 0xCC, mode)
            env.put(actor + 0x4C, x, y)
        return actor

    return Case(label, ATTACK, setup, arguments=(lambda actor: actor,))


def cases(random_source):
    def emit(label, mode, x=None, y=None, timer=None, flags=None, alias=None):
        values = [random_source.getrandbits(32) for _ in range(4)]
        x, y, timer, flags = [v if supplied is None else supplied for v, supplied in
                              zip(values, (x, y, timer, flags))]
        contents = bytes(random_source.getrandbits(8) for _ in range(0x120))
        return attack(label, mode, x, y, timer, flags, contents, alias)

    for mode in (0, 3, 4, 0x10001, 0x10002, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF):
        yield emit(f"mode {mode:#x} leaves state unchanged and returns zero", mode)
    for mode in (1, 2):
        for index, (x, y) in enumerate(((0, 0), (0, 1), (1, 0), (0x80000000, 0x7FFFFFFF),
                                       (0xFFFFFFFF, 0x12345678), (0x13579BDF, 0x2468ACE0))):
            yield emit(f"mode {mode} coordinate bits {index}", mode, x=x, y=y)
        for timer in (0, 1, 119999, 120000, 0xFFFE2B3E, 0xFFFE2B3F, 0xFFFE2B40,
                      0xFFFFFFFE, 0xFFFFFFFF):
            yield emit(f"mode {mode} timer {timer:#x}", mode, timer=timer)
        for flags in (0, 1, 2, 3, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF):
            yield emit(f"mode {mode} preserves flag bits {flags:#x}", mode, flags=flags)
        for alias in ("player-reload", "manager-reload", "coordinate-pointer-reload",
                      "x-overwrites-player-y", "primary-captured-before-x", "primary-captured-before-y",
                      "x-overwrites-timer", "y-overwrites-timer", "x-overwrites-flags",
                      "y-overwrites-flags", "primary-overwrites-x", "primary-overwrites-y",
                      "primary-overwrites-flags", "primary-overwrites-timer", "actor-is-player"):
            yield emit(f"mode {mode} alias {alias}", mode, alias=alias)
    for index in range(32):
        mode = random_source.choice((1, 2, random_source.getrandbits(32)))
        yield emit(f"random state {index} mode {mode:#x}", mode)
