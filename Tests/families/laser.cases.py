"""Original laser callback cases, including its corpus-split continuation."""
from clawparity.cases import Case
from clawparity.world import world, cstring, animation, sprite

ENTRY = 0x4553D0
NEW = 0x4F63EC


def cases(random_source):
    def setup_case(state_value, hits=False, redirect=False, mutate=False):
        # Draw once: effects are deterministic and store their observations in memory.
        words = [random_source.getrandbits(32) or 1 for _ in range(128)]
        idle = random_source.randrange(2, 28)
        clock = random_source.getrandbits(32)

        def setup(env):
            resources = {}
            if hits:
                image = sprite(env, width=37, height=59, origin=(-7, 11))
                frames = env.object(8, 'two-sprite-frames', fill=0)
                frame0 = env.object(0x28, 'sprite-frame-zero', words=words[:10])
                frame1 = env.object(0x28, 'sprite-frame-one', words=words[10:20])
                env.put(frames, frame0, frame1)
                env.put(image + 0x14, frames)
                env.put(image + 0x64, 0, 1)
                seq = animation(env, duration=random_duration, name='laser-animation')
                logic_hit = env.object(0x14, 'hit-descriptor', words=words[20:25])
                logic_attack = env.object(0x14, 'attack-descriptor', words=words[25:30])
                resources = {'sprites': {'LEVEL_LASER': image},
                             'animations': {'LEVEL_LASER_LASER': seq},
                             'logic': {'LogicHit': logic_hit, 'LogicAttack': logic_attack}}
            tokens = world(env, owner_words={i*4: v for i, v in enumerate(words)},
                           state_words={i*4: v for i, v in enumerate(words[32:96])},
                           resources=resources, idle_state=idle)
            owner, state = tokens['owner'], tokens['state']
            # Optional constructor inputs must describe backed/absent resources.
            env.put(owner + 0x38, 0xFFFFFFFF)
            env.put(owner + 0x188, 0, 0, words[101])
            env.put(owner + 0x170, 0)
            alternative = env.object(0x180, 'alternate-state', words=words[32:96], fill=0)
            env.put(alternative + 0x1C, 17)
            env.put(state + 0x1C, state_value)
            log = env.object(2048, 'observations', fill=0)
            activation_state = env.object(0x58, 'activation-snapshot', fill=0)
            env.put(0x537210, clock)

            def record(env, call, tag):
                index = env.get(log)
                slot = log + 4 + index * 96
                env.put(log, index + 1)
                env.put(slot, tag, call.receiver, len(call.arguments),
                        env.get(owner + 0x6C), env.get(state + 0x18),
                        env.get(state + 0x1C), env.get(alternative + 0x18),
                        env.get(alternative + 0x1C), env.get(owner + 0xD0),
                        env.get(owner + 0xD4))
                for i, arg in enumerate(call.arguments):
                    env.put(slot + 40 + 4*i, arg)
                if tag in (4, 12):
                    env.write(slot + 64, env.read(call.arguments[0], 16))
                return slot

            methods = env.object(0x28, 'existing-vtable', fill=0)
            creature = env.object(0x58, 'existing-creature', words=words[:22])
            env.put(creature, methods)
            env.put(creature + 0x10, state)
            env.put(state + 0x18, creature)
            env.put(alternative + 0x18, creature)

            def effect(tag):
                def callback(env, call):
                    record(env, call, tag)
                    if tag == 16:
                        env.write(activation_state, env.read(call.receiver, 0x58))
                    env.put(call.receiver + 0x14, words[tag % len(words)])
                    if mutate:
                        env.put(owner + 0x6C, alternative)
                        env.put(state + 0x1C, 1000)
                        env.put(state + 0x18, creature)
                    return words[(tag + 1) % len(words)]
                return callback

            for slot, argc in ((4, 1), (8, 1), (12, 1), (28, 0), (32, 0)):
                env.put(methods + slot, env.stub('laser-method-' + str(slot), 'thiscall', argc, effect(slot)))
            # Record activation before the owned callback publishes its creature.
            env.put(0x50E35C + 0x10, env.stub('laser-activation', 'thiscall', 0, effect(16)))
            if hits:
                for offset in (0x70, 0x78):
                    attached = env.object(0x174, 'attached-logic-' + str(offset), words=words[:32])
                    vt = env.object(0x28, 'attached-vtable-' + str(offset), fill=0)
                    env.put(attached, vt)
                    env.put(vt + 0x1C, env.stub('logic-clear-' + str(offset), 'thiscall', 0, effect(28)))
                    env.put(vt + 0x24, env.stub('logic-attach-' + str(offset), 'thiscall', 2, effect(36)))
                    env.put(owner + offset, attached)
            else:
                env.put(owner + 0x70, 0)
                env.put(owner + 0x78, 0)

            def allocating(env, call):
                record(env, call, 1)
                if redirect:
                    env.put(owner + 0x6C, alternative)
                return env.object(call.arguments[0], 'constructed-laser',
                                  data=bytes((i*31+19) % 256 for i in range(call.arguments[0])))
            env.override(NEW, allocating)
            # Signed bounds bracket even negative dispatch values without CRT growth.
            signed = state_value if state_value < 0x80000000 else state_value - 0x100000000
            text = cstring(env, b'laser-state-%08x-unique' % state_value, 'dispatch-string')
            table = env.object(12, 'numeric-state-entry', words=[text, words[99], words[100]])
            env.put(0x5376A0, signed, signed, table, table, 12, 0, 0)
            return tokens

        random_duration = random_source.randrange(1, 10000)
        return setup

    for hits in (False, True):
        for redirect in (False, True):
            for mutate in (False, True):
                yield Case(f'construct resources={hits} redirect={redirect} activation-change={mutate}',
                           ENTRY, setup_case(0, hits, redirect, mutate),
                           arguments=(lambda t: t['owner'],))
    for value in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for mutate in (False, True):
            yield Case(f'state {value:#x} side-effects={mutate}', ENTRY,
                       setup_case(value, mutate=mutate), arguments=(lambda t: t['owner'],))
