"""Original CrazyHook dispatch, using original constructor and state delivery."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import world, rectangle_services, sprite, cstring

ENTRY = 0x434190
ANIMATIONS = ('ADVANCE', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'IDLE1', 'JUMP',
              'KILLFALL', 'LIFTED1', 'LIFTED2', 'STRIKE1', 'STRIKE2', 'THROWN', 'BLOCK')


def descriptor(env, duration, name):
    # Original selection reads duration +0x1c and subsequent frame metadata.
    seq = env.object(0x14, name, fill=0)
    frames = env.object(4, name + '-frames', fill=0)
    frame = env.object(0x40, name + '-frame', fill=0)
    env.put(seq + 0xc, frames, 1)
    env.put(frames, frame)
    env.put(frame + 0x1c, duration)
    return seq


def setup_case(command, words, mode='empty', mutate=False, allocate_change=False):
    def setup(env):
        rectangle_services(env)
        env.override(0x4a3050, returns(words[0] % 100))
        resources = {}
        if mode != 'empty':
            resources['animations'] = {'GAME_NULL': descriptor(env, words[1] % 900 + 1, 'fallback')}
        if mode in ('hit', 'mixed'):
            resources['sprites'] = {'LEVEL_CRAZYHOOK': sprite(env, width=words[2] % 100 + 1,
                                      height=words[3] % 100 + 1, origin=(11, -13))}
            for index, key in enumerate(ANIMATIONS):
                if mode == 'hit' or index % 2:
                    resources['animations']['LEVEL_CRAZYHOOK_' + key] = descriptor(
                        env, 20 + index * 7, 'animation-' + key)
        if mode in ('hit', 'mixed'):
            sounds = ('00420008', '00420000', '00420021', '00420002', '00420003',
                      '00420016', '00420004', '00420015', 'DAGGERSTAB1', 'HOOKSWING1',
                      'BLOCK1', 'BLOCK2', '00420009', '00420010')
            resources['sounds'] = {
                'LEVEL_CRAZYHOOK_' + key: env.object(0x40, 'sound-' + key, fill=0)
                for index, key in enumerate(sounds) if mode == 'hit' or index % 2}
        tokens = world(env, resources=resources, bucket_count=1 if mutate else 17,
            owner_words={0x4c: words[0] % 1000 - 500, 0x50: words[1] % 1000 - 500,
                         0x148: 7, 0x14c: -9, 0x40: 2 if mutate else 0,
                         0x108: words[2], 0x114: words[3]},
            state_words={0x1c: command, 0x2c: -213, 0x30: 311, 0x34: -407,
                         0x38: 509, 0x64: 2, 0x68: words[4], 0x168: words[5]},
            idle_state=7)
        owner, state = tokens['owner'], tokens['state']
        child = env.object(0x498, 'previous-child', words=(words * (0x498 // (4*len(words)) + 1))[:0x498 // 4])
        # Fake lifecycle data is explicit; callbacks are fixture function pointers.
        env.put(child + 0x10, state)
        env.put(child + 0xc, owner)
        table = env.object(0x24, 'child-vtable', fill=0)
        replacement = env.object(0x24, 'replacement-vtable', fill=0)
        alternate_state = env.object(0x180, 'alternate-state', fill=0)
        env.put(alternate_state + 0x1c, 0x76543210)
        env.put(child, table)
        env.put(state + 0x18, child)
        name = cstring(env, 'LS_COMMAND_' + str(command), 'command-name')
        env.put(0x5376a0, command, command)
        string_table = env.object(4, 'command-table', words=[name])
        env.put(0x5376a8, string_table, string_table, 4, 0, 0)

        def effect(slot):
            def callback(env, call):
                env.put(child + 0x40 + slot, words[slot % len(words)])
                if mutate:
                    env.put(child, replacement)
                    env.put(state + 0x1c, 0x81234567)
                    env.put(state + 0x18, alternate_state)
                    env.put(owner + 0x6c, alternate_state)
                return words[(slot + 1) % len(words)]
            return callback
        for slot in (4, 8, 12, 16, 28, 32):
            env.put(table + slot, env.stub('child-slot-' + str(slot), 'thiscall',
                                         1 if slot in (4,8,12) else 0, effect(slot)))
            env.put(replacement + slot, env.stub('replacement-slot-' + str(slot), 'thiscall',
                                         1 if slot in (4,8,12) else 0, effect(slot)))
        if allocate_change:
            def allocate(env, call):
                address = env.object(call.arguments[0], 'allocated', fill=0)
                if call.arguments[0] == 0x498:
                    env.put(state + 0x18, alternate_state)
                    env.put(state + 0x1c, 0x11223344)
                    env.put(owner + 0x6c, alternate_state)
                return address
            env.override(0x4f63ec, allocate)
        return tokens
    return setup


def cases(random_source):
    for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7fffffff, 0x80000000, 0xffffffff):
        for mutate in (False, True):
            words = [random_source.randrange(1, 0x100000) + index * 0x100001 for index in range(8)]
            yield Case('command %08x callback changes %s' % (command, mutate), ENTRY,
                       setup_case(command, words, mutate=mutate), arguments=(lambda t: t['owner'],))
    for mode in ('empty', 'fallback', 'hit', 'mixed'):
        for mutate in (False, True):
            words = [random_source.randrange(1, 0x100000) + index * 0x100001 for index in range(8)]
            yield Case('constructor ' + mode + ' collision %s' % mutate, ENTRY,
                       setup_case(0, words, mode, mutate), arguments=(lambda t: t['owner'],))
    words = [random_source.randrange(1, 0x100000) + index * 0x100001 for index in range(8)]
    yield Case('allocation changes owner state and previous child', ENTRY,
               setup_case(0, words, 'hit', allocate_change=True), arguments=(lambda t: t['owner'],))
