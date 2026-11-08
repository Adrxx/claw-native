"""Original-only inputs for AquatisStalactite dispatch and construction."""
from clawparity.cases import Case
from clawparity.world import world, cstring, sprite

ENTRY = 0x4073E0
NEW = 0x4F63EC


def setup_dispatch(state_value, words, mutate=False):
    def setup(env):
        owner = env.object(0x200, 'owner', words=words[:128])
        state = env.object(0x180, 'state', words=words[:96])
        actor = env.object(0x1B8, 'published-actor', words=words[:110])
        vtable = env.object(0x24, 'actor-vtable', fill=0)
        log = env.object(0x100, 'callback-observations', fill=0)
        strings = env.object(4, 'numeric-state-string')
        text = cstring(env, 'STATE_UNIQUE')
        env.put(strings, text)
        env.put(0x5376A0, state_value, state_value, strings, strings, 4, 0, 0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, actor, state_value)
        env.put(actor, vtable)
        env.put(actor + 0x10, state)
        def callback(slot, argc):
            def effect(env, call):
                count = env.get(log)
                at = log + 4 + count * 32
                env.put(at, slot, call.receiver, env.get(state + 0x18), env.get(state + 0x1C),
                        env.get(owner + 0x6C), *(call.arguments or (0,)))
                env.put(log, count + 1)
                if mutate:
                    env.put(state + 0x18, owner, words[2])
                    env.put(owner + 0x6C, actor)
                return words[3]
            return env.stub('dispatch-%x' % slot, 'thiscall', argc, effect)
        for slot, argc in ((4,1),(8,1),(12,1),(0x1C,0),(0x20,0)):
            env.put(vtable + slot, callback(slot,argc))
        return owner
    return setup


def backed_animation(env, duration):
    descriptor = env.object(0x14, 'animation', fill=0)
    frames = env.object(4, 'animation-frames', fill=0)
    frame = env.object(0x40, 'animation-frame', fill=0)
    env.put(descriptor + 0xC, frames, 1)
    env.put(frames, frame)
    env.put(frame + 0x18, duration, duration + 7)
    return descriptor


def setup_construct(words, hits, mutate=False):
    def setup(env):
        resources = {}
        if hits:
            resources = {'sprites': {'LEVEL_PROJECTILES_STALACTITE': sprite(env,37,53,(3,-7))},
                         'animations': {key: backed_animation(env,71+i*13) for i,key in enumerate(
                             (('LEVEL_STALACTITE_HOME','LEVEL_STALACTITE_CRUMBLE','GAME_NULL')
                              if hits == 1 else ('GAME_NULL',)))},
                         'sounds': {'LEVEL_STALACTITEHIT2': words[4], 'LEVEL_STALACTITESNAP2': words[5]}}
        tokens = world(env, resources=resources,
                       owner_words={0x4C:words[0],0x50:words[1],0x148:words[2],0x14C:words[3]},
                       state_words={0x2C:17 if hits else 0,0x30:23 if hits else 0,0x34:31 if hits else 0,0x38:41 if hits else 0})
        env.put(tokens['owner']+0x18C,tokens['owner'])
        env.put(tokens['state']+0x18,words[6],0)
        observations = env.object(0x40, 'allocation-observations', fill=0)
        def allocation(env, call):
            count = env.get(observations)
            if count == 0:
                env.put(observations + 4, call.receiver, call.arguments[0],
                        env.get(tokens['state'] + 0x18), env.get(tokens['state'] + 0x1C),
                        env.get(tokens['owner'] + 0x6C))
                if mutate:
                    env.put(tokens['state'] + 0x18, words[7])
            env.put(observations, count + 1)
            return env.object(call.arguments[0], 'original-allocation')
        env.override(NEW, allocation)
        return tokens['owner']
    return setup



def setup_late_alias(words, mutate):
    """Original mode-3 animation writes install the final dispatch table.

    The animation target and new object are backed aliases in one allocation.
    No executable instruction or original callee is replaced.
    """
    def setup(env):
        backing = env.object(0x260, 'aliased-allocation', fill=0)
        actor = backing + 0x60
        target = actor - 0x4C
        table = env.object(0x24, 'late-written-table', fill=0)
        observations = env.object(0x80, 'initialization-observations', fill=0)
        descriptor = backed_animation(env, 97)
        frame = env.get(env.get(descriptor + 0xC))
        env.put(frame + 0x10, 3)
        env.put(frame + 0x20, table, words[9])
        tokens = world(env, resources={'animations': {'LEVEL_STALACTITE_HOME': descriptor}},
                       owner_words={0x4C:words[0],0x50:words[1],0x148:words[2],0x14C:words[3]})
        owner, state = tokens['owner'], tokens['state']
        env.put(owner + 0x18C, target)
        env.put(state + 0x18, words[6], 0)
        def initialize(env, call):
            env.put(observations + 0x20, call.receiver, env.get(state + 0x18),
                    env.get(state + 0x1C), env.get(owner + 0x6C),
                    env.get(call.receiver), env.get(call.receiver + 0x198))
            env.put(observations + 0x38, *call.arguments)
            env.put(observations + 0x1C, env.get(observations + 0x1C) + 1)
            if mutate:
                env.put(state + 0x18, words[7])
                env.put(owner + 0x6C, target)
            return words[8]
        env.put(table + 0x10, env.stub('late-alias-initialize', 'thiscall', 0, initialize))
        def allocation(env, call):
            count = env.get(observations)
            env.put(observations, count + 1)
            if count == 0:
                env.put(observations + 4, call.receiver, call.arguments[0],
                        env.get(state + 0x18), env.get(state + 0x1C))
                return actor
            return env.object(call.arguments[0], 'nested-allocation')
        env.override(NEW, allocation)
        return owner
    return setup

def cases(random_source):
    words = [random_source.getrandbits(32) for _ in range(128)]
    for state_value in (1,28,29,30,31,999,1000,1001,0x7FFFFFFF,0xFFFFFFFF):
        for mutate in (False,True):
            yield Case(f'dispatch {state_value:#x} mutate={mutate}',ENTRY,
                       setup_dispatch(state_value,words,mutate),arguments=(lambda x:x,))
    for hits in (0,1,2):
        for mutate in (False,True):
            yield Case(f'construct resource hits={hits} allocation mutation={mutate}',ENTRY,
                       setup_construct(words,hits,mutate),arguments=(lambda x:x,))

    for mutate in (False, True):
        yield Case(f'original late animation alias mutation={mutate}', ENTRY,
                   setup_late_alias(words, mutate), arguments=(lambda x:x,))
