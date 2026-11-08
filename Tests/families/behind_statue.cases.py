"""Original-only inputs for BehindStatue publication and crate delegation."""
from clawparity.cases import Case
from clawparity.fixtures import allocate
from clawparity.world import world, animation, resource_manager

ENTRY = 0x4717B0


def cases(random_source):
    def build(mode, health=0, sprite_kind=0, clock=17, timer=0, active=0, wait=0, count=None, animation_timer=None, logic_hit=False, allocation_fail=False):
        owner_data = [random_source.getrandbits(32) for _ in range(128)]
        state_data = [random_source.getrandbits(32) for _ in range(96)]
        global_data = [random_source.getrandbits(32) for _ in range(3)]

        def setup(env):
            tokens = world(env)
            owner, state = tokens['owner'], tokens['state']
            context = env.get(owner + 0xC)
            env.put(owner, *owner_data)
            env.put(state, *state_data)
            env.put(owner + 0xC, context)
            env.put(owner + 0x6C, state)
            env.put(owner + 0x64, health)
            env.put(owner + 0x10C, health if count is None else count)
            env.put(owner + 0x170, 0, 0)
            env.put(owner + 0x190, 0)
            env.put(owner + 0x19C, wait)
            env.put(owner + 0x1A4, active)
            if animation_timer is not None:
                sequence = animation(env, duration=73)
                env.put(owner + 0x190, sequence)
                env.put(owner + 0x194, env.get(env.get(sequence + 0xC)))
                env.put(owner + 0x198, 0)
                env.put(owner + 0x19C, animation_timer)
                env.put(owner + 0x1A0, 1)
                env.put(owner + 0x1A4, 1)
                env.put(owner + 0x1A8, 73, 31, 0x3F800000)
            env.put(state + 0x10, 0x471720 if sprite_kind == 2 else 0x4717B0)
            env.put(state + 0x1C, mode)
            env.put(state + 0x130, timer)
            env.put(0x52A190, *global_data)
            env.put(0x5430C4, clock)
            if logic_hit:
                record = env.object(64, 'callback-observations', fill=0)
                logic = env.object(0x20, 'crate-hit-logic', fill=0)
                env.put(logic + 0x10, 0x8BAD7123)
                manager = resource_manager(env, {'CrateHit': logic})
                env.put(context + 0x14, manager)
                controller = env.object(0x174, 'existing-controller', fill=0)
                methods = env.object(0x28, 'controller-methods', fill=0)
                env.put(controller, methods)
                env.put(owner + 0x70, controller)

                def reset(observed, call):
                    observed.put(record, call.receiver, observed.get(0x52A194),
                                 observed.get(state + 0x54), observed.get(state + 0x64),
                                 observed.get(owner + 0xD0), observed.get(owner + 0xD4),
                                 observed.get(state + 0x130), observed.get(state + 0x168))
                    return 0x13579BDF

                def select(observed, call):
                    observed.put(record + 32, call.receiver, *call.arguments,
                                 observed.get(state + 0x1C), observed.get(owner + 0x10C))
                    return 0x2468ACE0

                env.put(methods + 0x1C, env.stub('controller-reset', 'thiscall', 0, reset))
                env.put(methods + 0x24, env.stub('controller-select', 'thiscall', 2, select))
                if allocation_fail:
                    env.put(owner + 0x70, 0)
                    env.override(0x4F63EC, allocate(fail=True))
            if mode == 0 and sprite_kind:
                frame = env.object(0x28, 'distinct-frame', words=[random_source.getrandbits(32) for _ in range(10)])
                env.put(frame + 0x18, 13, 29, 83, 157)
                resource = env.object(0x6C, 'sprite-resource', fill=0)
                frames = env.object(16, 'sprite-indexes', words=[0, frame, 0, 0])
                env.put(resource + 0x14, frames)
                env.put(resource + 0x64, 1, 1)
                env.put(owner + 0x170, resource)
            return tokens
        return setup

    for mode in (1, 4, 6, 11, 30, 32, 0xFFFFFFFF):
        yield Case(f'default state {mode}', ENTRY, build(mode), arguments=(lambda t: t['owner'],))
    for health in (0, 1, 2, 998, 999, 1000, 0xFFFFFFFF, 0x80000000):
        for sprite_kind in (0, 1, 2):
            yield Case(f'initial health {health} sprite {sprite_kind}', ENTRY,
                       build(0, health, sprite_kind), arguments=(lambda t: t['owner'],))
    yield Case('damage sees freshly cleared flag', ENTRY, build(10), arguments=(lambda t: t['owner'],))
    for timer, clock in ((0, 0), (0, 17), (1, 0), (1, 1), (7, 8), (8, 7), (0xFFFFFFFF, 0x80000000)):
        yield Case(f'idle timer {timer} delta {clock}', ENTRY, build(5, timer=timer, clock=clock),
                   arguments=(lambda t: t['owner'],))
    for active, wait in ((0, 0), (1, 0), (0x87654321, 0), (1, 1), (1, 0xFFFFFFFF)):
        yield Case(f'animation active {active} wait {wait}', ENTRY, build(31, active=active, wait=wait),
                   arguments=(lambda t: t['owner'],))

    for sprite_kind in (0, 1, 2):
        for count in (0, 1, 2, 998, 999, 0xFFFFFFFF, 0x80000000):
            yield Case(f'zero health count {count} sprite {sprite_kind}', ENTRY,
                       build(0, 0, sprite_kind, count=count), arguments=(lambda t: t['owner'],))
    for mode in (5, 31):
        for timer, clock in ((1, 0), (19, 7), (7, 7), (7, 19)):
            yield Case(f'live animation mode {mode} timer {timer} clock {clock}', ENTRY,
                       build(mode, clock=clock, animation_timer=timer), arguments=(lambda t: t['owner'],))

    for health in (0, 5):
        yield Case(f'logic hit preserves publication order health {health}', ENTRY,
                   build(0, health, 1, logic_hit=True), arguments=(lambda t: t['owner'],))

    yield Case('logic allocation failure returns to crate initialization', ENTRY,
               build(0, 0, 1, logic_hit=True, allocation_fail=True), arguments=(lambda t: t['owner'],))
