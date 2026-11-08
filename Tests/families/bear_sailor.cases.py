"""Original-only inputs for BearSailor entry and real constructor effects."""
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence
from clawparity.world import world, animation, sprite, cstring, rectangle_services

ENTRY = 0x409860
ANIMS = ('ADVANCE', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'IDLE', 'JUMP',
         'KILLFALL', 'LIFTED1', 'LIFTED2', 'STRIKE1', 'THROWN', 'HOME')
SOUNDS = ('00380000', '00380007', '00380015', '00380018', '00380019',
          '00380002', '00380020', '00380023', 'BEARGRAB', 'BEARHUG',
          '00380024', '00380006')


def cases(random_source):
    for mode in ('empty', 'fallback', 'hit', 'mixed'):
        for index in range(4):
            x, y = random_source.randrange(-1000, 1000), random_source.randrange(-1000, 1000)
            bits = random_source.getrandbits(32)
            idle = random_source.randrange(1, 20)
            duration = random_source.randrange(1, 1000)
            rand_values = (random_source.randrange(0, 32768), random_source.randrange(0, 32768))
            def setup(env, mode=mode, index=index, x=x, y=y, bits=bits,
                      idle=idle, duration=duration, rand_values=rand_values):
                rectangle_services(env)
                env.override(0x4A3050, sequence(*rand_values))
                resources = {}
                if mode != 'empty':
                    resources['animations'] = {'GAME_NULL': animation(env, duration)}
                if mode in ('hit', 'mixed'):
                    for n, key in enumerate(ANIMS):
                        if mode == 'hit' or n % 2:
                            resources['animations']['LEVEL_BEARSAILOR_' + key] = animation(env, duration+n+1, 'animation-'+key)
                    resources['sprites'] = {'LEVEL_BEARSAILOR': sprite(env, 47+index, 65+index, (19, 31))}
                    resources['sounds'] = {'LEVEL_BEARSAILOR_'+key: env.object(0x40, 'sound-'+key, fill=0)
                                           for n, key in enumerate(SOUNDS) if mode == 'hit' or n % 2}
                return world(env, resources=resources, idle_state=idle, bucket_count=1 if index == 0 else 17,
                             collision_step=(31+index, 43+index),
                             owner_words={8: bits, 0x4C:x, 0x50:y, 0x40:index%3, 0x108:101+index,
                                          0x104:39+index, 0x10C:81+index, 0x114:300+index,
                                          0x148:index-2, 0x14C:2-index},
                             state_words={0x1C:0, 0x2C:-111, 0x30:133, 0x34:-222, 0x38:244,
                                          0x64:index, 0x68:1234+index, 0x168:37+index})
            yield Case(f'constructor {mode} {index}', ENTRY, setup, arguments=(lambda t:t['owner'],))

    for state in (1, 28, 29, 30, 31, 999, 1000, 1001, -1, -2147483648, 2147483647):
        for alter in (False, True):
            marker = random_source.getrandbits(32)
            def setup(env, state=state, alter=alter, marker=marker):
                tokens = world(env, state_words={0x1C:state, 0x68:marker})
                # Zeroed live record: no dangling destructor/count/pointer fields.
                child = env.object(0x4A0, 'existing-child', fill=0)
                methods = env.object(0x24, 'child-methods', fill=0)
                env.put(child, methods)
                env.put(child+0xC, tokens['owner'], tokens['state'])
                env.put(tokens['state']+0x18, child)
                text = cstring(env, b'LS_BEAR_TEST', 'dispatch-name')
                table = env.object(4, 'dispatch-name-table', words=[text], fill=0)
                env.put(0x5376A0, state, state, table)
                env.put(0x5376B0, 4)
                for offset, argc in ((4,1),(8,1),(12,1),(0x1C,0),(0x20,0)):
                    def effect(env, call, offset=offset):
                        env.put(call.receiver+0x498, marker ^ offset)
                        if alter:
                            env.put(tokens['state']+0x1C, 1000)
                        return marker
                    env.put(methods+offset, env.stub('bear-callback-'+str(offset), 'thiscall', argc, effect))
                return tokens
            yield Case(f'state {state} mutate {alter}', ENTRY, setup, arguments=(lambda t:t['owner'],))
