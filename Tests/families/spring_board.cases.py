"""Cases for spring_board: SpringBoard object logic (original 0x49db90).

The object is a game actor.  State lives in a data block at actor+0x6c.
State 0 starts the idle animation, state 5 waits for the player to stand on the
board, state 6 plays the bounce, 0x457 and 0x3f0 are the second animation pair.
The animation player at actor+0x188 (original 0x4c82a0) is driven by raw fields
so that its result is chosen by the case; the name lookup (0x4c79e0) walks a
real hash table built here.
"""
from clawparity.cases import Case

FUNCTION = 0x49DB90
G_STRINGS = 0x537960   # pointer to the shared string and float block
G_PLAYER = 0x537E88    # pointer to the player actor
G_DELTA = 0x5430C4     # frame delta handed to the animation player

ACTOR_SIZE = 0x1C0
DATA_SIZE = 0xD0
PLAYER_SIZE = 0xE0
BUCKETS = 7


def name_hash(name):
    value = 0
    for byte in name:
        signed = byte - 256 if byte >= 128 else byte
        value = (value * 0x21 + signed) & 0xFFFFFFFF
    return value % BUCKETS


def random_name(rnd, high=False):
    letters = [rnd.randrange(97, 123) for _ in range(rnd.randrange(3, 12))]
    if high:
        letters[rnd.randrange(len(letters))] = rnd.randrange(128, 256)
    return bytes(letters)


def noise(rnd, size):
    return bytes(rnd.randrange(1, 256) for _ in range(size))


# animation player field sets (offsets from actor+0x188)
#   (set, timer14, loop18, done1c, value20, value24)
# set == 0 makes 0x4c82a0 return -1.  timer14 > 0 with loop18 == 0 counts down by one
# and returns value24.  timer14 == 0 with done1c != 0 returns value20.
def anim_ret(value, remaining=1, done=1):
    """0x4c82a0 returns `value`; timer ends up remaining-1; done flag as given."""
    return {"set": 1, "t14": remaining, "l18": 0, "d1c": done, "v20": 0x2222, "v24": value}


def anim_short(value20, done=1):
    """0x4c82a0 takes the timer == 0 shortcut and returns value20."""
    return {"set": 1, "t14": 0, "l18": 0, "d1c": done, "v20": value20, "v24": 0x3333}


def anim_none():
    return {"set": 0, "t14": 0x41, "l18": 0, "d1c": 1, "v20": 0x4444, "v24": 0x5555}


DEFAULTS = dict(
    state=0, wait=0x2F, damage=0x38, pending=0x77, flag64=0x55, flags8=0x30, flags164=0x300,
    f134=0x1000, anim=None, player_flags=0x10, player_target="self", player_state=0x1C1, player_mode=3,
    player_damage_state=0x1C, delta=3, idle_found=True, alt_found=True, empty_table=False, collide=True,
    fa=None, high=False, names=None, p38=0x1C2, frame_value=0x66,
)


def build(env, rnd, **options):
    s = dict(DEFAULTS)
    s.update(options)
    if s["anim"] is None:
        s["anim"] = anim_none()
    idle = random_name(rnd, s["high"]) if s["names"] is None else s["names"][0]
    alt = random_name(rnd, s["high"]) if s["names"] is None else s["names"][1]
    if alt == idle:
        alt = alt + b"x"
    floats = s["fa"] or [rnd.randrange(1, 0xFFFFFFFF) for _ in range(4)]

    strings = env.object(0x60, "strings", data=noise(rnd, 0x60))
    env.write(strings + 4, idle + b"\0")
    env.write(strings + 0x24, alt + b"\0")
    env.put(strings + 0x48, *floats)
    env.put(G_STRINGS, strings)
    env.put(G_DELTA, s["delta"])

    # animation sets, one per name, with a first frame each
    def animation_set(label, value):
        frame = env.object(0x30, label + "-frame", words=[0x11] * 7 + [value])
        frames = env.object(8, label + "-frames", words=[frame, 0])
        return env.object(0x70, label + "-set", words=[1, 2, 3, frames, 1, 5, 6])

    idle_set = animation_set("idle", s["frame_value"])
    alt_set = animation_set("alt", s["frame_value"] + 1)

    # hash table: header at holder+0x10 {+4 buckets, +8 count}; node {next, ?, key, value}
    holder = env.object(0x40, "table-holder", data=noise(rnd, 0x40))
    buckets = env.object(BUCKETS * 4, "buckets")
    nodes = {}

    def node(key, value, next_node=0):
        keyaddr = env.object(len(key) + 1, "key", data=key + b"\0")
        return env.object(0x10, "node", words=[next_node, 0xAAAA, keyaddr, value])

    entries = []
    if s["idle_found"]:
        entries.append((idle, idle_set))
    if s["alt_found"]:
        entries.append((alt, alt_set))
    heads = {}
    for key, value in entries:
        slot = name_hash(key)
        heads[slot] = node(key, value, heads.get(slot, 0))
    if s["collide"]:
        for key, _ in ((idle, 0), (alt, 0)):
            slot = name_hash(key)
            decoy = b"decoy" + key
            heads[slot] = node(decoy, 0xDEAD, heads.get(slot, 0))
    for slot, head in heads.items():
        env.put(buckets + 4 * slot, head)
    env.put(holder + 0x10, 0, 0 if s["empty_table"] else buckets, BUCKETS)

    owner = env.object(0x40, "owner", data=noise(rnd, 0x40))
    env.put(owner + 0x2C, holder)

    data = env.object(DATA_SIZE, "data", data=noise(rnd, DATA_SIZE))
    env.put(data + 0x1C, s["state"])
    env.put(data + 0x38, s["damage"])
    env.put(data + 0x64, s["flag64"])
    env.put(data + 0xBC, s["pending"])
    env.put(data + 0x20, 0x1234)

    actor = env.object(ACTOR_SIZE, "actor", data=noise(rnd, ACTOR_SIZE))
    env.put(actor + 0x08, s["flags8"])
    env.put(actor + 0x0C, owner)
    env.put(actor + 0x64, s["wait"])
    env.put(actor + 0x6C, data)
    env.put(actor + 0x134, s["f134"])
    env.put(actor + 0x164, s["flags164"])
    a = s["anim"]
    anim_set = env.object(0x70, "current-set", words=[1, 2, 3, 0, 0, 5, 6]) if a["set"] else 0
    env.put(actor + 0x188 + 8, anim_set)
    env.put(actor + 0x188 + 0x14, a["t14"])
    env.put(actor + 0x188 + 0x18, a["l18"])
    env.put(actor + 0x188 + 0x1C, a["d1c"])
    env.put(actor + 0x188 + 0x20, a["v20"])
    env.put(actor + 0x188 + 0x24, a["v24"])

    player_data = env.object(0x90, "player-data", data=noise(rnd, 0x90))
    env.put(player_data + 0x1C, s["player_damage_state"])
    env.put(player_data + 0x14, 0)
    player = env.object(PLAYER_SIZE, "player", data=noise(rnd, PLAYER_SIZE))
    env.put(player + 0x08, s["player_flags"])
    target = {"self": actor, "other": player, "none": 0}[s["player_target"]]
    env.put(player + 0x80, target)
    env.put(player + 0xD0, s["player_mode"])
    env.put(player + 0x6C, player_data)
    env.put(G_PLAYER, player)
    return {"actor": actor, "data": data, "player": player, "strings": strings}


def case(label, rnd, **options):
    return Case(label, FUNCTION, lambda env: build(env, rnd, **options), arguments=(lambda tokens: tokens["actor"],))


def cases(random_source):
    rnd = random_source

    # state 0: start; both wait-timer and pending-timer branches
    for wait in (0, 1, 0x7FFFFFFF, -1 & 0xFFFFFFFF):
        for pending in (0, 1, 0x4B0, 0x80000000):
            for found in (True, False):
                yield case(f"start wait={wait:#x} pending={pending:#x} found={found}", rnd,
                           state=0, wait=wait, pending=pending, idle_found=found)
    yield case("start: empty table", rnd, state=0, empty_table=True, pending=0)
    yield case("start: no collisions", rnd, state=0, collide=False, pending=9)
    yield case("start: high-byte name", rnd, state=0, high=True, pending=0)
    yield case("start: flags with bit 0 and 0x20000 already set", rnd, state=0, flags8=0x20001, flags164=0x10040, wait=0)
    yield case("start: f134 wraps", rnd, state=0, f134=0xFFFFFFF0)
    for _ in range(12):
        yield case("start: random", rnd, state=0, flags8=rnd.randrange(1 << 32), flags164=rnd.randrange(1 << 32),
                   f134=rnd.randrange(1 << 32), wait=rnd.choice([0, rnd.randrange(1 << 32)]),
                   pending=rnd.choice([0, rnd.randrange(1 << 32)]), high=rnd.random() < 0.5)

    # state 5: waiting for the player
    for value in (anim_none(), anim_ret(1), anim_ret(7), anim_short(1)):
        for player_flags in (0, 0x10, 0x8, 0x11, 0xFFFFFFEF):
            for target in ("self", "other", "none"):
                for found in (True, False):
                    yield case(f"wait flags={player_flags:#x} target={target} found={found} anim={value['v24']:#x}", rnd,
                               state=5, anim=value, player_flags=player_flags, player_target=target, alt_found=found)
    yield case("wait: high-byte name", rnd, state=5, player_flags=0x10, high=True, anim=anim_ret(1))
    yield case("wait: empty table", rnd, state=5, player_flags=0x10, empty_table=True)
    yield case("wait: no collisions", rnd, state=5, player_flags=0x10, collide=False)

    # state 6: bounce playing
    for result in (anim_none(), anim_ret(1, 1, 0), anim_ret(1, 2, 1), anim_ret(1, 1, 1), anim_ret(2, 1, 1), anim_short(1),
                   anim_short(0), anim_short(0xFFFFFFFF)):
        for flag64 in (0, 1, 2):
            for player_flags in (0, 0x10):
                for target in ("self", "other"):
                    for damage in (-3 & 0xFFFFFFFF, 0, 1, 0x500):
                        yield case(f"bounce anim={result['t14']}/{result['d1c']}/{result['v24']:#x} flag64={flag64} "
                                   f"pf={player_flags:#x} tg={target} dmg={damage}", rnd,
                                   state=6, anim=result, flag64=flag64, player_flags=player_flags,
                                   player_target=target, damage=damage, player_mode=3)
    for mode in (2, 3):
        for inner in (0x1C, 0x138D, 0x138C):
            yield case(f"bounce: player mode {mode} inner {inner:#x}", rnd, state=6, anim=anim_ret(1), flag64=1,
                       damage=0x44, player_mode=mode, player_damage_state=inner)
    yield case("bounce: empty table, finished", rnd, state=6, anim=anim_ret(1, 1, 1), empty_table=True, flag64=1)
    yield case("bounce: no collisions", rnd, state=6, anim=anim_ret(1, 1, 1), collide=False, flag64=1)
    yield case("bounce: high-byte name", rnd, state=6, anim=anim_ret(1, 1, 1), high=True, flag64=1)
    yield case("bounce: restart name missing", rnd, state=6, anim=anim_ret(1, 1, 1), idle_found=False, flag64=1)

    # state 0x457: begin second animation
    for player_flags in (0, 0x10):
        for found in (True, False):
            yield case(f"0x457 found={found}", rnd, state=0x457, alt_found=found, player_flags=player_flags)
    yield case("0x457: empty table", rnd, state=0x457, empty_table=True)
    yield case("0x457: high-byte name", rnd, state=0x457, high=True)

    # state 0x3f0: second animation playing
    for result in (anim_none(), anim_ret(1, 1, 0), anim_ret(1, 2, 1), anim_ret(1, 1, 1), anim_ret(3, 1, 1), anim_short(1),
                   anim_short(0)):
        for flag64 in (0, 1, 2):
            for flags164 in (0, 0x20000, 0xFFFFFFFF):
                yield case(f"second anim={result['t14']}/{result['d1c']}/{result['v24']:#x} flag64={flag64} "
                           f"flags164={flags164:#x}", rnd, state=0x3F0, anim=result, flag64=flag64, flags164=flags164)
    yield case("second: empty table, finished", rnd, state=0x3F0, anim=anim_ret(1, 1, 1), empty_table=True, flag64=1)
    yield case("second: high-byte name", rnd, state=0x3F0, anim=anim_ret(1, 1, 1), high=True, flag64=1)

    # states with no behavior, and the boundaries between handled states
    for state in (1, 2, 3, 4, 7, 0x3EF, 0x3F1, 0x456, 0x458, 0x80000000, 0xFFFFFFFF, 6 + 0x3EA + 1, 0x1C):
        yield case(f"unhandled state {state:#x}", rnd, state=state, anim=anim_ret(1, 1, 1))
    for _ in range(25):
        yield case("random state", rnd, state=rnd.choice([0, 5, 6, 0x3F0, 0x457, rnd.randrange(1 << 32)]),
                   anim=rnd.choice([anim_none(), anim_ret(1, 1, 1), anim_ret(1, 2, 1), anim_ret(rnd.randrange(4), 1, 0),
                                    anim_short(1)]),
                   flag64=rnd.choice([0, 1, rnd.randrange(1 << 32)]), wait=rnd.choice([0, 2000, rnd.randrange(1 << 32)]), flags164=rnd.randrange(1 << 32),
                   player_flags=rnd.choice([0, 0x10, rnd.randrange(256)]),
                   player_target=rnd.choice(["self", "other", "none"]), damage=rnd.randrange(1 << 32),
                   pending=rnd.choice([0, rnd.randrange(1 << 32)]), high=rnd.random() < 0.5,
                   idle_found=rnd.random() < 0.8, alt_found=rnd.random() < 0.8, delta=rnd.randrange(1, 40))
