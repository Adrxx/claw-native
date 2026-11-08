"""Original-only Marrow cases with backed callback records."""
from clawparity.cases import Case
from clawparity.world import world, rectangle_services, cstring, animation, sprite

ENTRY = 0x458680


def fixture(state_value, noise, construction=False, hits=False):
    def setup(env):
        rectangle_services(env)
        resources = {}
        if hits:
            names = ('ADVANCE FASTADVANCE STRIKE1 STRIKE2 IMPACT KILLFALL HITLOW HITHIGH '
                     'JUMP HOME HOME1 IDLE1 IDLE2 IDLE3 IDLE4 LIFTED BLOCK').split()
            resources['animations'] = {'LEVEL_MARROW_' + n: animation(env, 30+i*7) for i,n in enumerate(names)}
            resources['animations']['GAME_NULL'] = animation(env, 73)
            resources['sprites'] = {'LEVEL_MARROW': sprite(env, 39, 47, (-9, 13))}
            sound_names = ('00430008 00430003 PISTOL 00430006 WHISTLE 00430015 STAB2 BLOCK1 BLOCK2 00430010').split()
            resources['sounds'] = {'LEVEL_MARROW_' + n: env.object(0x80, 'sound-'+n, fill=i+17) for i,n in enumerate(sound_names)}
        tokens = world(env, owner_words={0x4c: noise[0], 0x50: noise[1]}, resources=resources)
        owner = tokens['owner']
        env.put(0x537e88, env.object(0x200, 'reference-player', fill=0))
        state = env.object(0x600, 'backed-state-and-construction', fill=0)
        env.put(owner+0x6c, state)
        record = env.object(0x100, 'callback-observations', fill=0)
        table = env.object(0x30, 'callbacks', fill=0)
        creature = env.object(0x4d8, 'existing-creature',
                              words=[(noise[i % 5] + i*0x10203) & 0xffffffff for i in range(0x4d8//4)])
        env.put(creature, table)
        env.put(creature+0x10, state)
        env.put(state+0x18, creature, state_value)
        for index, offset in enumerate((4,8,12,16,28,32)):
            argc = 1 if offset in (4,8,12) else 0
            snapshot = env.object(0x4d8, 'observed-creature-'+str(offset), fill=0)
            def effect(env, call, index=index, snapshot=snapshot):
                env.write(snapshot, env.read(call.receiver, 0x4d8))
                pos = record + index*32
                env.put(pos, call.receiver, len(call.arguments), env.get(state+0x18), env.get(state+0x1c), env.get(0x537b14))
                if call.arguments:
                    env.put(pos+20, call.arguments[0])
                env.put(pos+24, env.get(call.receiver+0x24))
                env.put(state+0x20, noise[2] + index)
                env.put(call.receiver+0x44, noise[3] + index)
                return noise[4]
            env.put(table+offset, env.stub('observe-'+str(offset), 'thiscall', argc, effect))
        # Original state dispatch consumes a CString for the selected state.
        text = cstring(env, 'dispatch-state')
        slot = env.object(4, 'state-cstring', words=[text])
        env.put(0x5376a0, state_value, state_value, slot)
        env.put(0x5376b0, 4)
        if construction:
            # Constructor's final state write reaches the allocated object's
            # first word. Its LS_STARTUP lookup supplies a fresh callback table.
            key = cstring(env, 'LS_STARTUP')
            node = env.object(20, 'startup-registry', fill=0)
            env.put(node, node, node, 0, key, table)
            env.put(0x537668+0x18, node)
            def alloc(env, call):
                if call.arguments[0] == 0x4d8:
                    env.put(record+0xe0, env.get(state+0x1c), call.arguments[0], env.get(state+0x18))
                    return state+0x1c
                return env.object(call.arguments[0], 'allocation', fill=0)
            env.override(0x4f63ec, alloc)
        return {'owner': owner}
    return setup


def cases(random_source):
    for state in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xffffffff, 0x80000000):
        noise = [random_source.randrange(1, 0x10000) for _ in range(5)]
        yield Case('state '+str(state), ENTRY, fixture(state, noise), arguments=(lambda t:t['owner'],))
    for hits in (False, True):
        noise = [random_source.randrange(1, 0x10000) for _ in range(5)]
        yield Case('construct resources '+str(hits), ENTRY, fixture(0, noise, True, hits), arguments=(lambda t:t['owner'],))
