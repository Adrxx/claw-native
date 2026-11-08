"""Original FrontStatue delegation and state-publication cases."""
from clawparity.cases import Case
from clawparity.world import world, sprite
from clawparity.fixtures import allocate

ENTRY = 0x471780


def cases(random_source):
    def setup_for(state, lifetime=0, count=0, tick=0, timer=0, timed=0,
                  active=0, completed=0, image=False, sound=False, fail=False, update=False):
        words = [random_source.getrandbits(32) for _ in range(0x200 // 4)]
        state_data = [random_source.getrandbits(32) for _ in range(0x180 // 4)]
        sentinel = random_source.getrandbits(32)
        def setup(env):
            tokens = world(env)
            owner, record = tokens['owner'], tokens['state']
            env.put(owner, *words)
            env.put(record, *state_data)
            env.put(owner + 0xc, tokens['world'])
            env.put(owner + 0x6c, record)
            env.put(owner + 0x64, lifetime)
            env.put(owner + 0x10c, count)
            env.put(owner + 0x170, 0, 0)
            env.put(owner + 0x190, active)
            env.put(owner + 0x19c, timer, timed, completed)
            if update:
                descriptor = env.object(0x30, 'animation-step', fill=0)
                env.put(descriptor + 0x18, 13, 29)
                sequence = env.object(0x14, 'animation-sequence', fill=0)
                frames = env.object(4, 'animation-frames', words=[descriptor])
                env.put(sequence + 0xc, frames, 1)
                env.put(owner + 0x18c, owner, sequence, descriptor, 0)
                env.put(owner + 0x1a8, 31, 37, 0x3f800000)
            env.put(record + 0x1c, state)
            env.put(record + 0x10, 0x471720 if image else sentinel)
            env.put(record + 0x130, tick)
            env.put(0x5430c4, 7)
            env.put(0x52a190, sentinel, sentinel ^ 0x12345678, sentinel ^ 0x87654321)
            if image:
                resource = sprite(env, width=43, height=61, origin=(-11, 19))
                env.put(owner + 0x170, resource)
            if sound:
                descriptor = env.object(0x20, 'sound-descriptor', fill=0)
                env.put(descriptor + 0x10, sentinel)
                from clawparity.world import resource_manager
                manager = resource_manager(env, {'CrateHit': descriptor})
                env.put(tokens['world'] + 0x14, manager)
                if fail:
                    env.put(owner + 0x70, 0)
                    env.override(0x4f63ec, allocate(fail=True))
                else:
                    recorder = env.object(0x80, 'callback-observations', fill=0)
                    interface = env.object(0x30, 'sound-interface', fill=0)
                    table = env.object(0x28, 'fresh-sound-methods', fill=0)
                    env.put(interface, table)
                    env.put(owner + 0x70, interface)
                    def observe(e, c):
                        index = e.get(recorder)
                        at = recorder + 4 + index * 28
                        e.put(at, c.receiver, e.get(0x52a194), e.get(record + 0x64),
                              e.get(record + 0x54), e.get(owner + 0xd0),
                              c.arguments[0] if c.arguments else 0,
                              c.arguments[1] if len(c.arguments) > 1 else 0)
                        e.put(recorder, index + 1)
                        return sentinel
                    env.put(table + 0x1c, env.stub('sound reset', 'thiscall', 0, observe))
                    env.put(table + 0x24, env.stub('sound start', 'thiscall', 2, observe))
            else:
                env.put(owner + 0x70, 0)
            return tokens
        return setup

    combinations = [(s, 23, 0, 0, 0, 0, 0, 0) for s in (1, 4, 6, 30, 32, -1, 0x80000000)]
    for count in (-0x80000000, -1, 0, 1, 2, 998, 999, 0x7fffffff):
        for lifetime in (0, 1, 0xffffffff):
            for image in (False, True):
                yield Case(f'initialize count={count} lifetime={lifetime} image={image}', ENTRY,
                           setup_for(0, lifetime, count, image=image), arguments=(lambda t: t['owner'],))
    for sound, fail in ((True, False), (True, True)):
        yield Case(f'sound hit allocation-fail={fail}', ENTRY,
                   setup_for(0, sound=sound, fail=fail), arguments=(lambda t: t['owner'],))
    for tick in (0, 1, 7, 8, 0xffffffff):
        combinations.append((5, 23, 0, tick, 0, 0, 0, 0))
    for state in (5, 31):
        for timer, timed, complete in ((10, 1, 0), (7, 1, 1), (1, 0, 1), (0, 1, 1)):
            combinations.append((state, 23, 0, 19, timer, timed, 1, complete))
    for state in (5, 31):
        for timer, timed in ((0, 0), (0, 1), (1, 1), (7, 1), (1, 0)):
            yield Case(f'animation step state={state} timer={timer} timed={timed}', ENTRY,
                       setup_for(state, timer=timer, timed=timed, active=1, update=True),
                       arguments=(lambda t: t['owner'],))
    combinations.extend([(10, 23, 0, 0, 0, 0, 0, 0), (31, 23, 0, 0, 0, 0, 0, 1)])
    for index, values in enumerate(combinations):
        yield Case(f'delegate state branch {index}', ENTRY, setup_for(*values),
                   arguments=(lambda t: t['owner'],))
