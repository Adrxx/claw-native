"""Original-only SkullCannon dispatch and construction inputs."""
from clawparity.cases import Case
from clawparity.world import world, animation, sprite, cstring

ENTRY = 0x48A800
NEW = 0x4F63EC


def cases(random_source):
    for command in (1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for change in (False, True):
            tag = random_source.randrange(0x10000, 0x7FFFFFFF)
            def setup(env, command=command, change=change, tag=tag):
                t = world(env, state_words={0x1C: command, 0x20: tag})
                obj = env.object(0x7C, 'existing-cannon', fill=0xA7)
                methods = env.object(0x24, 'existing-methods', fill=0)
                env.put(obj, methods)
                env.put(obj + 0x10, t['state'])
                env.put(t['state'] + 0x18, obj)
                alternate = env.object(0x180, 'alternate-state', fill=0x93)
                text = cstring(env, 'dispatch-' + str(tag))
                descriptor = env.object(4, 'dispatch-string', words=[text])
                env.put(0x5376A0, command, command, descriptor, descriptor, 4, 0, 0)
                def effect(env, call):
                    env.put(call.receiver + 0x58, tag)
                    env.put(t['state'] + 0x20, tag ^ 0x7654321)
                    if change:
                        env.put(t['owner'] + 0x6C, alternate)
                        env.put(t['state'] + 0x18, alternate)
                        env.put(obj, methods)
                    return tag ^ 0xABCDE
                for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
                    env.put(methods + offset, env.stub('cannon-slot-' + str(offset), 'thiscall', argc, effect))
                return t
            yield Case(f'dispatch {command:#x} mutation {change}', ENTRY, setup,
                       arguments=(lambda t: t['owner'],))

    for resources_hit in (False, True):
        for alias in (False, True):
            for capture in (False, True):
                tag = random_source.randrange(1, 0x7FFFFFFF)
                def setup(env, resources_hit=resources_hit, alias=alias, capture=capture, tag=tag):
                    resources = {}
                    if resources_hit:
                        resources = {'sprites': {'LEVEL_SKULLCANNON': sprite(env, width=tag % 100 + 1, height=37)},
                                     'animations': {'LEVEL_SKULLCANNON_FIRING': animation(env, tag % 1000 + 1),
                                                    'LEVEL_SKULLCANNON_HOME': animation(env, tag % 701 + 1)}}
                    t = world(env, resources=resources, state_words={0x20: tag, 0x18: tag ^ 0xA95},
                              owner_words={0x148: tag, 0x14C: tag ^ 0x321, 0x104: tag % 31 + 1})
                    observations = env.object(16, 'allocation-observations', fill=0x45)
                    alternate = env.object(0x180, 'allocation-alternate-state', fill=0)
                    env.put(alternate + 0x1C, 77)
                    def allocation(env, call):
                        if env.calls_so_far(NEW) == 1:
                            env.put(observations, call.arguments[0], env.get(t['state'] + 0x1C))
                            if capture:
                                env.put(t['owner'] + 0x6C, alternate)
                            if alias:
                                return t['state']
                        return env.object(call.arguments[0], 'construction-allocation', fill=0xB6)
                    env.override(NEW, allocation)
                    return t
                yield Case(f'construct hit={resources_hit} alias={alias} capture={capture}', ENTRY,
                           setup, arguments=(lambda t: t['owner'],))

    # Overlap the newly constructed record with the owner's animation state.
    # The original's late animation selection then supplies the virtual table.
    for mutate_owner in (False, True):
        for prior in (0, 1, 0xA783921):
            tag = random_source.randrange(1, 0x7FFFFFFF)
            def setup(env, mutate_owner=mutate_owner, prior=prior, tag=tag):
                home = animation(env, tag % 791 + 1, 'alias-home-animation')
                t = world(env, resources={'animations': {'LEVEL_SKULLCANNON_HOME': home}},
                          state_words={0x18: prior, 0x20: tag})
                owner = env.object(0x400, 'overlapping-owner', data=env.read(t['owner'], 0x200), fill=0x71)
                t['owner'] = owner
                target = owner + 0x190
                observations = env.object(24, 'late-initialization-observations', fill=0x47)
                alternate = env.object(0x180, 'late-alternate-state', fill=0x62)
                def initialize(env, call):
                    env.put(observations, call.receiver, env.get(t['state'] + 0x18))
                    env.put(observations + 8, tag ^ 0x531728)
                    env.put(t['state'] + 0x18, tag ^ 0xAB892)
                    if mutate_owner:
                        env.put(owner + 0x6C, alternate)
                    return tag
                # The frame-count field doubles as the +0x10 virtual slot.
                # It is positive, so the original selects the backed first frame.
                env.put(home + 0x10, env.stub('overlap-initialize', 'thiscall', 0, initialize))
                def allocation(env, call):
                    if env.calls_so_far(NEW) == 1:
                        env.put(observations + 12, call.arguments[0], env.get(t['state'] + 0x1C))
                        return target
                    return env.object(call.arguments[0], 'alias-construction-allocation', fill=0xC3)
                env.override(NEW, allocation)
                return t
            yield Case(f'late overlap initialization prior={prior} mutate-owner={mutate_owner}', ENTRY,
                       setup, arguments=(lambda t: t['owner'],))
