"""Blind cases for the original GooVent callback and unchanged callees."""
from clawparity.cases import Case
from clawparity.world import world, sprite, animation, cstring

ENTRY = 0x448620
NEW = 0x4F63EC


def setup_case(state_value, noise, hit=False, alias=False, mutate=False):
    def setup(env):
        resources = {}
        if hit:
            hit_logic = env.object(0x14, 'hit-logic-resource', fill=0x51)
            attack_logic = env.object(0x14, 'attack-logic-resource', fill=0x32)
            env.put(hit_logic + 0x10, noise ^ 0x32198765)
            env.put(attack_logic + 0x10, noise ^ 0x78943216)
            resources = {
                'logic': {'LogicHit': hit_logic, 'LogicAttack': attack_logic},
                'sprites': {'LEVEL_GOOVENT': sprite(env, width=17 + noise % 29,
                                                    height=23 + noise % 31,
                                                    origin=(-7, 13))},
                'animations': {'LEVEL_GOOVENT_GOOVENT': animation(env, duration=1 + noise % 499)},
            }
        tokens = world(env, resources=resources, bucket_count=1 if hit else 17,
                       state_words={0x1C: state_value, 0xB8: noise ^ 0x19827364},
                       owner_words={0x190: noise ^ 0x28736415})
        owner, state = tokens['owner'], tokens['state']
        for offset in (0x20, 0x24, 0x28, 0x2C, 0x34, 0x38, 0x40):
            env.put(state + offset, (noise + offset * 0x10101) & 0xFFFFFFFF)
        target = env.object(0x80, 'existing-vent', fill=0xA7)
        vtable = env.object(0x24, 'vent-vtable', fill=0)
        changed_vtable = env.object(0x24, 'changed-vent-vtable', fill=0)
        env.put(target, vtable)
        env.put(target + 0x10, state)
        env.put(state + 0x18, target)
        alternate = env.object(0x80, 'alternate-vent', fill=0x6B)
        replacement_state = env.object(0x180, 'replacement-state', fill=0x91)
        env.put(alternate, vtable)
        env.put(alternate + 0x10, state)

        def effect(env, call):
            env.put(call.receiver + 0x40, noise, call.receiver,
                    env.get(state + 0x18), env.get(state + 0x1C))
            if mutate:
                env.put(call.receiver, changed_vtable)
                env.put(state + 0x18, alternate)
                env.put(owner + 0x6C, replacement_state)
                env.put(state + 0x1C, noise ^ 0x61371924)
            return noise ^ 0x87263514

        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x10, 0), (0x1C, 0), (0x20, 0)):
            env.put(vtable + offset, env.stub(f'vent-method-{offset:x}', 'thiscall', argc, effect))
            env.put(changed_vtable + offset, env.stub(f'changed-method-{offset:x}', 'thiscall', argc, effect))
        if hit:
            for offset in (0x70, 0x78):
                handler = env.object(0x40, f'logic-handler-{offset:x}', fill=0x4D)
                methods = env.object(0x28, f'logic-methods-{offset:x}', fill=0)
                env.put(handler, methods)
                def logic_effect(env, call):
                    env.put(call.receiver + 0x10, noise,
                            env.get(state + 0x18), env.get(state + 0x1C),
                            *call.arguments)
                    return noise ^ 0x54176283
                env.put(methods + 0x1C, env.stub('logic-reset', 'thiscall', 0, logic_effect))
                env.put(methods + 0x24, env.stub('logic-bind', 'thiscall', 2, logic_effect))
                env.put(owner + offset, handler)
        if state_value not in (0, 29, 30, 1000):
            # Back the original numeric-state -> CString table without replacing lookup code.
            text = cstring(env, f'state-{state_value:08x}', 'state-name')
            table = env.object(4, 'state-name-table', words=[text])
            env.put(0x5376A0, state_value, state_value, table, table, 4, 0, 0)
        if state_value == 0:
            def allocate(env, call):
                env.put(owner + 0x1F0, env.get(state + 0x1C), env.get(state + 0x18))
                if mutate:
                    env.put(owner + 0x6C, replacement_state)
                    # The original constructor reads the changed state pointer.
                    env.put(replacement_state + 0xB8, noise ^ 0xAAAAAAAA)
                return state if alias else env.object(call.arguments[0], 'new-vent', fill=0xB3)
            env.override(NEW, allocate)
        return tokens
    return setup


def cases(random_source):
    for value in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for mutate in (False, True):
            noise = random_source.getrandbits(32)
            yield Case(f'state {value:#x} mutation {mutate}', ENTRY,
                       setup_case(value, noise, mutate=mutate),
                       arguments=(lambda t: t['owner'],))
    for hit in (False, True):
        for alias in (False, True):
            for mutate in (False, True):
                noise = random_source.getrandbits(32)
                yield Case(f'construct hit {hit} alias {alias} mutate {mutate}', ENTRY,
                           setup_case(0, noise, hit, alias, mutate),
                           arguments=(lambda t: t['owner'],))

    for offset in (0x190, 0x194):
        for mutate in (False, True):
            noise = random_source.getrandbits(32)
            yield Case(f'late animation alias {offset:#x} mutation {mutate}', ENTRY,
                       late_animation_alias(noise, offset, mutate),
                       arguments=(lambda t: t['owner'],))


def late_animation_alias(noise, offset, mutate):
    """Owner animation fields overlap the freshly constructed object header.

    The unchanged constructor's final animation selection supplies the vtable
    through normal descriptor data, so its subsequent virtual call is observable.
    """
    def setup(env):
        sequence = animation(env, duration=1 + noise % 1000)
        frame = env.get(env.get(sequence + 0xC))
        tokens = world(env, resources={
            'animations': {'LEVEL_GOOVENT_GOOVENT': sequence}},
            state_words={0x1C: 0, 0xB8: noise ^ 0x16345278})
        owner, state = tokens['owner'], tokens['state']
        result = owner + offset
        old = env.object(0x58, 'prior-published-object', fill=0x64)
        env.put(state + 0x18, old)
        changed_state = env.object(0x180, 'late-alternate-state', fill=0x25)
        marker = env.object(0x30, 'initialization-observation', fill=0xA9)

        def initialize(env, call):
            env.put(marker, call.receiver, env.get(state + 0x18),
                    env.get(state + 0x1C), env.get(owner + 0x190),
                    env.get(owner + 0x194), env.get(owner + 0x6C), noise)
            if mutate:
                env.put(state + 0x18, marker)
                env.put(owner + 0x6C, changed_state)
                env.put(state + 0x1C, noise ^ 0x72918634)
            return noise ^ 0x65748192

        callback = env.stub('late-animation-init', 'thiscall', 0, initialize)
        if offset == 0x190:
            # Positive frame count doubles as a supplied method in the descriptor.
            env.put(sequence + 0x10, callback)
        else:
            env.put(frame + 0x10, callback)

        def allocate(env, call):
            env.put(marker + 0x20, env.get(state + 0x1C),
                    env.get(state + 0x18), call.arguments[0])
            return result

        env.override(NEW, allocate)
        return tokens
    return setup
