"""Cases for scene_camera_helpers: Scene camera mode helpers called by 0x486240: look up/down, climb, reset and shake."""
from clawparity.cases import Case
from clawparity.fixtures import sequence

LOOK = 0x486620
FOLLOW = 0x486650
LOOK_DOWN = 0x4868E0
LOOK_UP = 0x486910
SHAKE = 0x486A00
PLAYER = 0x537E88
OVERRIDE_X = 0x52BE14
OVERRIDE_Y = 0x52BE18
DELTA = 0x5430C4
RAND = 0x4A3050
MASK = 0xFFFFFFFF


def make(player_x, player_y, mode=0, override=None, delta=10, state=(0, 0, 0, 0, 0), rands=None):
    """Player actor, logic and state records with distinct non-zero contents, plus the camera globals."""
    def setup(env):
        player = env.object(0x100, "player", fill=0)
        for offset in range(0, 0x100, 4):
            env.put(player + offset, 0x71000000 + offset * 3 + 1)
        env.put(player + 0x4C, player_x & MASK, player_y & MASK)
        env.put(player + 0xCC, mode & MASK)
        logic = env.object(0x40, "logic", fill=0)
        for offset in range(0, 0x40, 4):
            env.put(logic + offset, 0x52000000 + offset * 5 + 7)
        record = env.object(0x20, "state", fill=0)
        for offset in range(0, 0x20, 4):
            env.put(record + offset, 0x33000000 + offset * 7 + 3)
        env.put(record, *[value & MASK for value in state])
        owner = env.object(0x20, "owner", fill=0x5A)
        env.put(PLAYER, player)
        if override is None:
            env.put(OVERRIDE_X, MASK, 0x6A6A6A6A)
        else:
            env.put(OVERRIDE_X, override[0] & MASK, override[1] & MASK)
        env.put(DELTA, delta & MASK)
        if rands is not None:
            env.override(RAND, sequence(*rands))
        return {"owner": owner, "logic": logic, "state": record, "player": player}
    return setup


def call(label, function, setup):
    return Case(label, function, setup, arguments=(lambda t: t["owner"], lambda t: t["logic"], lambda t: t["state"]))


def cases(random_source):
    # The three look helpers: constant mode, player position, y offset, the global re-read for y.
    for function, name in ((LOOK, "look"), (LOOK_DOWN, "look down"), (LOOK_UP, "look up")):
        for px, py in ((0, 0), (1, 2), (-5, 7), (1234, -4321), (0x7FFFFFFF, 0x7FFFFF00), (-0x80000000, -0x7FFFFF00),
                       (100, 0x7FFFFFFF - 0xC7), (100, -0x7FFFFFFF + 0xC7), (0x1234567, 0x7654321)):
            yield call(f"{name} at {px},{py}", function, make(px, py, state=(11, 22, 33, 44, 55)))
        yield call(f"{name} ignores camera override and mode", function,
                   make(300, 400, mode=3, override=(5, 6), delta=9, state=(1, 2, 3, 4, 5)))
        for _ in range(2):
            px, py = random_source.randrange(-100000, 100000), random_source.randrange(-100000, 100000)
            yield call(f"{name} random {px},{py}", function,
                       make(px, py, mode=random_source.randrange(0, 12), state=tuple(random_source.getrandbits(32) for _ in range(5))))

    # Camera follow: every mode x override x signed x/y offset between state and target.
    # 900 triggers the >500 snap, 300 moves without clamping, 2 clamps, 0 is the equal branch.
    offsets = (-900, -300, -2, 0, 2, 300, 900)
    for mode in (3, 4, 8, 0):
        for has_override in (False, True):
            for i, dx in enumerate(offsets):
                for j, dy in enumerate(offsets):
                    if has_override and (i + j) % 2:
                        continue
                    px, py = random_source.randrange(-3000, 3000), random_source.randrange(-3000, 3000)
                    override = (random_source.randrange(-3000, 3000), random_source.randrange(-3000, 3000)) if has_override else None
                    tx, ty = override if override else (px, py)
                    delta = (1, 10)[(i + j) % 2]
                    yield call(f"follow mode {mode} override {has_override} dx {dx} dy {dy} dt {delta}", FOLLOW,
                               make(px, py, mode=mode, override=override, delta=delta,
                                    state=(tx - dx, ty - dy, 0x1111, 0x2222, 0x3333)))

    # Timing values: the 4000/1000 and 99999/1000 scalings are unsigned, 32-bit and truncating.
    for mode in (3, 4, 8, 0):
        for delta in (0, 1, 3, 250, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            for dx, dy in ((20000, -20000), (-20000, 20000)):
                # 20000 apart snaps, so place the state near the target but beyond any small step
                yield call(f"follow mode {mode} dt {delta:#x} signs {dx > 0}", FOLLOW,
                           make(-8000, 9000, mode=mode, delta=delta,
                                state=(-8000 - (400 if dx > 0 else -400), 9000 + (400 if dy > 0 else -400), 1, 2, 3)))
    # Snap boundary at exactly 500 and 501 on each axis, with each sign, and an absolute value that overflows.
    for mode in (4, 8, 0):
        for ox, oy in ((500, 0), (501, 0), (0, 500), (0, 501), (-500, 0), (-501, 0), (0, -500), (0, -501), (501, 501), (500, 500)):
            yield call(f"follow mode {mode} snap boundary {ox},{oy}", FOLLOW,
                       make(2000, -3000, mode=mode, delta=3, state=(2000 - ox, -3000 - oy, 9, 9, 9)))
    yield call("follow abs overflow", FOLLOW, make(0x7FFFFFF0, 0x10, mode=4, delta=5, state=(-0x7FFFFFF0, 0x10, 1, 1, 1)))
    yield call("follow int min difference", FOLLOW, make(0, 0, mode=8, delta=5, state=(-0x80000000, 0, 1, 1, 1)))
    yield call("follow override x only sentinel is -1", FOLLOW,
               make(10, 20, mode=4, override=(-1, 77), delta=5, state=(0, 0, 1, 1, 1)))
    yield call("follow override with y sentinel value", FOLLOW,
               make(10, 20, mode=3, override=(-2, -1), delta=5, state=(0, 0, 1, 1, 1)))
    for mode in (3, 4, 8, 0, 1, 2, 5, 6, 9, 0x100, -1, -3):
        yield call(f"follow mode {mode} state equal target", FOLLOW, make(40, 50, mode=mode, delta=10, state=(40, 50, 0, 0, 0)))
    for _ in range(20):
        mode = random_source.choice((3, 4, 8, 0, 1, 2, 5, 6))
        px, py = random_source.randrange(-5000, 5000), random_source.randrange(-5000, 5000)
        override = None if random_source.randrange(3) == 0 else (random_source.randrange(-5000, 5000), random_source.randrange(-5000, 5000))
        tx, ty = override if override else (px, py)
        yield call(f"follow random mode {mode}", FOLLOW,
                   make(px, py, mode=mode, override=override, delta=random_source.randrange(0, 200),
                        state=(tx + random_source.randrange(-700, 700), ty + random_source.randrange(-700, 700),
                               random_source.getrandbits(32), random_source.getrandbits(32), random_source.getrandbits(32))))

    # Shake: unsigned compare of the global against state+0x10, signed remainders of three scripted rand values.
    for delta, timer in ((5, 4), (5, 5), (5, 6), (1, 0), (0, 0), (0, 1), (0x80000000, 5), (5, 0x80000000),
                         (0xFFFFFFFF, 0x7FFFFFFF), (0x7FFFFFFF, 0xFFFFFFFF), (100, 36), (0x80000000, 0x80000000),
                         (0x80000001, 0x80000000)):
        for rands in ((1, 2, 3), (0x7FFF, 0x7FFE, 0x7FFD)):
            yield call(f"shake dt {delta:#x} timer {timer:#x} rand {rands[0]}", SHAKE,
                       make(1, 2, delta=delta, state=(1000, -2000, 3, 4, timer), rands=rands))
    for first in (0, 1, 35, 36, 37, 71, 0x7FFF, 0x4000):
        for second, third in ((0, 0), (5, 7), (6, 6), (12, 12), (13, 13), (0x7FFF, 0), (0, 0x7FFF), (3, 9), (11, 2)):
            yield call(f"shake rand {first} {second} {third}", SHAKE,
                       make(1, 2, delta=50, state=(500, -500, 3, 4, 7), rands=(first, second, third)))
    for rands in ((0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD), (0x80000000, 0x80000001, 0x80000002),
                  (0x80000000, 0xFFFFFFF0, 0x7FFFFFFF), (0xFFFFFFF5, 0xFFFFFFFB, 0xFFFFFFF9)):
        yield call(f"shake negative rand {rands[0]:#x}", SHAKE, make(1, 2, delta=50, state=(500, -500, 3, 4, 7), rands=rands))
    yield call("shake overflowing position", SHAKE, make(1, 2, delta=50, state=(0x7FFFFFFF, -0x80000000, 3, 4, 7), rands=(10, 12, 0)))
    yield call("shake timer subtraction to zero", SHAKE, make(1, 2, delta=9, state=(1, 2, 3, 4, 9)))
    for _ in range(15):
        delta = random_source.randrange(0, 100)
        timer = random_source.randrange(0, 100)
        yield call(f"shake random dt {delta} timer {timer}", SHAKE,
                   make(1, 2, delta=delta, state=tuple(random_source.getrandbits(32) for _ in range(4)) + (timer,),
                        rands=tuple(random_source.randrange(0, 32768) for _ in range(3))))
