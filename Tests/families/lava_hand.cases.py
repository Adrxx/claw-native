"""Original-only inputs for LavaHand dispatch and construction."""
from clawparity.cases import Case
from clawparity.world import world, animation, sprite, cstring

ENTRY = 0x4561C0
NEW = 0x4F63EC


def setup_dispatch(state_value, words):
    def setup(env):
        owner = env.object(0x200, 'owner', words=words[:128])
        state = env.object(0x180, 'state', words=words[:96])
        target = env.object(0xB8, 'target', words=words[:46])
        table = env.object(0x24, 'methods', fill=0)
        record = env.object(0x200, 'callback-observations', fill=0)
        alternate = env.object(0x180, 'alternate-state', words=words[:96])
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, target, state_value)
        env.put(target, table)
        env.put(target + 0x10, state)
        text = cstring(env, 'dispatch-state', 'dispatch-string')
        holder = env.object(4, 'dispatch-string-holder', words=[text])
        env.put(0x5376A0, 0x80000000, 0x7FFFFFFF, holder, holder, 0)
        def effect(slot):
            def callback(env, call):
                count = env.get(record)
                at = record + 4 + count * 28
                args = list(call.arguments)
                env.put(at, slot, call.receiver, len(args), args[0] if args else 0,
                        env.get(state + 0x18), env.get(state + 0x1C), env.get(owner + 0x6C))
                env.put(record, count + 1)
                env.put(owner + 0x6C, alternate)
                env.put(state + 0x18, alternate)
                env.put(target + 0xA0, words[80] ^ slot)
                return words[81] ^ slot
            return callback
        for slot, argc in ((4, 1), (8, 1), (12, 1), (0x10, 0), (0x1C, 0), (0x20, 0)):
            env.put(table + slot, env.stub(f'observe-{slot:x}', 'thiscall', argc, effect(slot)))
        return owner
    return setup


def setup_construct(words, hit, health, alias=False, redirect=False):
    def setup(env):
        resources = {}
        if hit:
            seq = animation(env, duration=words[0] % 400 + 1)
            image = sprite(env, width=37, height=59, origin=(-13, 7))
            resources = {'animations': {'LEVEL_LAVAHAND': seq, 'GAME_NULL': seq},
                         'sprites': {'LEVEL_LAVAHAND': image}}
        tokens = world(env, owner_words={0x4C: words[1], 0x50: words[2], 0x108: health},
                       state_words={0x2C: words[4], 0x30: words[5], 0x34: words[6],
                                    0x38: words[7], 0xBC: words[8]}, resources=resources)
        if alias:
            tokens['owner'] = env.object(0x300, 'alias-owner', data=env.read(tokens['owner'], 0x200))
        state = tokens['state']
        alternate = env.object(0x180, 'constructor-alternate-state', data=env.read(state, 0x180))
        record = env.object(0x40, 'construction-observations', fill=0)
        old = env.object(0xB8, 'prior-publication', words=words[:46])
        env.put(state + 0x18, old, 0)
        def initialize(env, call):
            env.put(record, call.receiver, len(call.arguments), env.get(state + 0x18),
                    env.get(state + 0x1C), env.get(call.receiver + 0x24),
                    env.get(call.receiver + 0xA4), env.get(call.receiver + 0xB0),
                    env.get(tokens['owner'] + 0x6C), env.get(alternate + 0x1C))
            env.put(call.receiver + 0xB4, words[90])
            env.put(state + 0x18, words[91])
            return words[92]
        env.put(0x50E4DC + 0x10, env.stub('constructed-initialize', 'thiscall', 0, initialize))
        def alloc(env, call):
            result = (tokens['owner'] + 0x150 if alias else
                      env.object(call.arguments[0], 'construction-allocation', words=words[:46]))
            if alias:
                env.put(result, *words[:46])
            if redirect:
                env.put(tokens['owner'] + 0x6C, alternate)
            env.put(record + 0x20, call.arguments[0], env.get(state + 0x1C), env.get(state + 0x18))
            return result
        env.override(NEW, alloc)
        return tokens['owner']
    return setup


def cases(random_source):
    words = [random_source.getrandbits(32) for _ in range(128)]
    for value in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield Case(f'dispatch {value:#x}', ENTRY, setup_dispatch(value, words), arguments=(lambda owner: owner,))
    for hit in (False, True):
        for health in (0xFFFFFFFF, 0, 1, 47):
            yield Case(f'construct resource-hit={hit} health={health:#x}', ENTRY,
                       setup_construct(words, hit, health), arguments=(lambda owner: owner,))
        for alias, redirect in ((True, False), (False, True), (True, True)):
            yield Case(f'construct hit={hit} alias={alias} redirect={redirect}', ENTRY,
                       setup_construct(words, hit, words[3], alias, redirect),
                       arguments=(lambda owner: owner,))
