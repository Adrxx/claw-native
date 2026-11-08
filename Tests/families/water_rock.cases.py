"""Original WaterRock state and animation transitions."""
from clawparity.cases import Case
from clawparity.world import animation, world

ENTRY = 0x49DE10


def setup_case(state, flags, riding, impulse, pending, timer, ended, result, active,
               countdown, resource_hit, words):
    def setup(env):
        idle = animation(env, 29, 'idle-animation')
        spring = animation(env, 71, 'spring-animation')
        resources = {'animations': {'LEVEL_WATERROCK_IDLE': idle,
                                    'LEVEL_WATERROCK_SPRING': spring}} if resource_hit else None
        tokens = world(env, resources=resources, idle_state=None)
        owner, record = tokens['owner'], tokens['state']
        for offset, value in words.items():
            env.put(owner + offset, value)
        env.put(record + 0x1C, state)
        env.put(record + 0x20, 0xCAFE1234)
        env.put(record + 0x38, impulse)
        env.put(record + 0x64, pending)
        env.put(record + 0xBC, countdown)
        env.put(owner + 0x64, timer)
        player = env.object(0x200, 'player', fill=0)
        env.put(player + 8, flags)
        env.put(player + 0x80, owner if riding else record)
        # The player is in a supported non-jumping state; the original impulse
        # callee still runs and observes the exact signed impulse argument.
        env.put(player + 0xD0, 3)
        env.put(0x537E88, player)
        env.put(0x5430C4, 7)
        env.put(owner + 0x18C, owner)
        env.put(owner + 0x190, idle if active else 0)
        frame = env.object(0x30, 'active-frame', fill=0)
        env.put(frame + 0x1C, 29)
        env.put(frame + 0xC, 9)
        env.put(frame + 0x10, 2)
        env.put(frame + 0x18, 13)
        env.put(frame + 0x20, 17, 31)
        env.put(owner + 0x194, frame)
        env.put(owner + 0x198, 0)
        env.put(owner + 0x19C, timer)
        env.put(owner + 0x1A0, 1)
        env.put(owner + 0x1A4, ended)
        env.put(owner + 0x1A8, result)
        env.put(owner + 0x1AC, result)
        env.put(owner + 0x1B0, 0x3F800000)
        return tokens
    return setup


def cases(random_source):
    count = 0
    def emit(state=6, flags=0x10, riding=True, impulse=450, pending=1,
             timer=8, ended=1, result=1, active=True, countdown=0, resource_hit=False):
        nonlocal count
        count += 1
        words = {offset: random_source.getrandbits(32) for offset in
                 (8, 0x128, 0x12C, 0x130, 0x134, 0xD0, 0x158, 0x15C, 0x164)}
        setup = setup_case(state, flags, riding, impulse, pending, timer, ended,
                           result, active, countdown, resource_hit, words)
        return Case(f'water rock transition {count} state {state:#x}', ENTRY,
                    setup, arguments=(lambda t: t['owner'],))

    for state in (1, 2, 4, 7, 1007, 1009, 1110, 1112, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield emit(state=state)
    for timer in (0, 1, 0xFFFFFFFF, 0x80000000):
        for countdown in (0, 1, 0xFFFFFFFF):
            for hit in (False, True):
                yield emit(state=0, timer=timer, countdown=countdown, resource_hit=hit)
    for flags, riding in ((0, True), (0x100, True), (0x10, False), (0xFFFFFFFF, True)):
        for active in (False, True):
            yield emit(state=5, flags=flags, riding=riding, active=active)
    for hit in (False, True):
        yield emit(state=1111, resource_hit=hit)
    for state in (6, 1008):
        for active in (False, True):
            for pending in (0, 1, 2, 0xFFFFFFFF):
                for timer, ended, result in ((8, 0, 1), (8, 1, 1), (0, 1, 1),
                                              (8, 1, 0), (8, 1, 2), (8, 1, 0xFFFFFFFF),
                                              (0, 0, 1), (7, 0, 1), (1, 0, 2)):
                    yield emit(state=state, active=active, pending=pending,
                               timer=timer, ended=ended, result=result)
    for impulse in (0, 1, -1, -2147483648, 2147483647, 449, 450, 451):
        for flags, riding in ((0, True), (0x10, False), (0x10, True)):
            yield emit(impulse=impulse, flags=flags, riding=riding)
    for _ in range(24):
        yield emit(state=random_source.choice((0, 5, 6, 1008, 1111)),
                   timer=random_source.randrange(1, 100),
                   impulse=random_source.randrange(-2000, 2000),
                   pending=random_source.choice((0, 1, 2)), resource_hit=True)
