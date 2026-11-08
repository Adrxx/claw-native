"""Blind original-behavior cases for HermitCrab."""
from clawparity.cases import Case
from clawparity.world import world, cstring, animation, sprite

ENTRY = 0x449C40
NEW = 0x4F63EC
MASK = 0xFFFFFFFF


def rectangle_services(env):
    def set_rect(env, call):
        env.put(call.arguments[0], *call.arguments[1:])
        return 1

    def empty(env, call):
        env.put(call.arguments[0], 0, 0, 0, 0)
        return 1

    def inflate(env, call):
        address, dx, dy = call.arguments
        left, top, right, bottom = (env.get(address + i) for i in (0, 4, 8, 12))
        env.put(address, (left - dx) & MASK, (top - dy) & MASK,
                (right + dx) & MASK, (bottom + dy) & MASK)
        return 1

    env.override(0x546D5C, set_rect)
    env.override(0x546CDC, empty)
    env.override(0x546D24, inflate)


def setup_case(state_code, values, construct=False, hits=False, change=False):
    def setup(env):
        resources = {}
        if hits:
            resources['animations'] = {
                name: animation(env, 31 + index * 17, name)
                for index, name in enumerate((
                    'LEVEL_HERMITCRAB_FASTADVANCE', 'LEVEL_HERMITCRAB_CROUCH4',
                    'LEVEL_HERMITCRAB_HIDE', 'LEVEL_HERMITCRAB_STRIKE1',
                    'LEVEL_HERMITCRAB_KILLFALL', 'LEVEL_HERMITCRAB_HIT',
                    'LEVEL_HERMITCRAB_FALL', 'LEVEL_HERMITCRAB_LIFT', 'GAME_NULL'))}
            if hits == 'fallback':
                resources['animations'] = {'GAME_NULL': resources['animations']['GAME_NULL']}
            resources['sprites'] = {name: sprite(env, 27 + index * 9, 39 + index * 7,
                                                   (-13 + index, 11 - index), name)
                                    for index, name in enumerate(('LEVEL_HERMITCRAB', 'GAME_NULL'))}
            resources['sounds'] = {name: env.object(16, name, words=values[:4])
                                  for name in ('GAME_SPLASH', 'GAME_PURELEASE1',
                                      'GAME_THRWBOMB', 'LEVEL_HERMITCRAB_CRABSNIP',
                                      'LEVEL_HERMITCRAB_CRABDEATH', 'LEVEL_HERMITCRAB_CRABLEFT', 'GAME_BOINKJR')}
        tokens = world(env, owner_words={8: values[0], 0x104: values[1], 0x108: values[2], 0x114: values[3]},
                       state_words={0x1C: state_code, 0x64: values[4] % 3,
                                    0x68: values[5], 0x168: values[6]}, resources=resources,
                       collision_step=(47, 73), bucket_count=1)
        owner, state = tokens['owner'], tokens['state']
        record = env.object(0x800, 'callback-observations', fill=0)
        target = env.object(0x438, 'existing-object', words=values, fill=0xA7)
        alternate = env.object(0x438, 'replacement-object', words=values[::-1], fill=0x5D)
        methods = env.object(0x48, 'callback-vtable', fill=0)
        env.put(target, methods)
        env.put(alternate, methods)
        env.put(target + 0x10, state)
        env.put(alternate + 0x10, state)
        env.put(state + 0x18, target)

        def observe(slot):
            def effect(env, call):
                index = env.get(record)
                at = record + 4 + index * 28
                args = list(call.arguments) + [0]
                env.put(at, slot, call.receiver, args[0], env.get(state + 0x18),
                        env.get(state + 0x1C), env.get(owner + 0x6C), env.get(call.receiver + 0x10))
                env.put(record, index + 1)
                if slot == 16:
                    env.write(record + 256, env.read(call.receiver, 0x438))
                env.put(call.receiver + 0x34, values[7])
                if change:
                    env.put(state + 0x18, alternate)
                    env.put(state + 0x1C, values[8])
                    env.put(owner + 0x6C, alternate)
                return values[9]
            return effect

        for slot, argc in ((4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)):
            stub = env.stub(f'crab-callback-{slot}', 'thiscall', argc, observe(slot))
            env.put(methods + slot, stub)
            if slot == 16:
                env.put(0x50E014 + slot, stub)
        # A direct indexed CString table lets the unchanged dispatcher execute.
        text = cstring(env, 'LS_HERMIT_TEST')
        table = env.object(4, 'dispatch-cstring', words=[text])
        env.put(0x5376A0, state_code, state_code, table, table, 4, 0, 0)
        if construct:
            rectangle_services(env)
            def allocate(env, call):
                obj = env.object(call.arguments[0], 'constructed-allocation', fill=0xC3)
                env.put(record + 224, env.get(state + 0x1C), env.get(state + 0x18), obj)
                return obj
            env.override(NEW, allocate)
        return tokens
    return setup


def cases(random_source):
    for state in (1, 28, 29, 30, 31, 1000, 1001, 0xFFFFFFFF, 0x80000000):
        for change in (False, True):
            values = [random_source.getrandbits(32) for _ in range(10)]
            yield Case(f'state {state:#x} callbacks change={change}', ENTRY,
                       setup_case(state, values, change=change), arguments=(lambda t: t['owner'],))
    for hits in (False, True, 'fallback'):
        for change in (False, True):
            values = [random_source.getrandbits(32) for _ in range(10)]
            yield Case(f'full construction hits={hits} change={change}', ENTRY,
                       setup_case(0, values, construct=True, hits=hits, change=change),
                       arguments=(lambda t: t['owner'],))
