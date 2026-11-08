"""Original-only MarrowFloor construction and state dispatch cases."""
from clawparity.cases import Case
from clawparity.world import world, sprite, cstring

ENTRY = 0x45A2E0
NEW = 0x4F63EC


def setup_case(state_id, words, hit=False, mutate=False):
    def setup(env):
        resources = {}
        if hit:
            image = sprite(env, width=words[0] % 90 + 7, height=words[1] % 100 + 9,
                           origin=(words[2] % 19, words[3] % 23))
            sound = env.object(0x30, 'sound-resource', words=words, fill=0x61)
            resources = {'sprites': {'LEVEL_TRAPELEVATOR': image},
                         'sounds': {'LEVEL_PEGSLIDE': sound}}
            logic_hit = env.object(0x20, 'LogicHit-resource', words=words, fill=0x62)
            logic_attack = env.object(0x20, 'LogicAttack-resource', words=list(reversed(words)), fill=0x63)
            resources['logic'] = {'LogicHit': logic_hit, 'LogicAttack': logic_attack}
        w = world(env, resources=resources, idle_state=words[4] % 100 + 1,
                  owner_words={8: words[0], 0x4c: words[1], 0x148: words[2]},
                  state_words={0x1c: state_id})
        owner, state = w['owner'], w['state']
        obj = env.object(0x6c, 'existing-floor', words=words * 6, fill=0x57)
        env.put(obj + 0x10, state)
        env.put(state + 0x18, obj)
        trace = env.object(0x200, 'callback-observations', fill=0)
        if hit:
            for offset in (0x70, 0x78):
                logic = env.object(0x174, 'logic-instance-' + str(offset), fill=0x46)
                methods = env.object(0x28, 'logic-methods-' + str(offset), fill=0)
                env.put(logic, methods)
                env.put(owner + offset, logic)
                def logic_effect(e, call):
                    count = e.get(trace)
                    e.put(trace + 4 + count * 32, call.receiver,
                          e.get(state + 0x1c), e.get(state + 0x18),
                          e.get(owner + 0x70), e.get(owner + 0x78),
                          *(list(call.arguments) + [0, 0])[:2])
                    e.put(trace, count + 1)
                    e.put(call.receiver + 0x168, words[7])
                    return words[6]
                env.put(methods + 0x1c, env.stub('logic-clear-' + str(offset),
                                               'thiscall', 0, logic_effect))
                env.put(methods + 0x24, env.stub('logic-select-' + str(offset),
                                               'thiscall', 2, logic_effect))
        table = env.object(0x24, 'callbacks', fill=0)
        env.put(obj, table)
        def callback(slot, argc):
            def effect(e, call):
                count = e.get(trace)
                at = trace + 4 + count * 32
                e.put(at, slot, call.receiver, e.get(state + 0x1c), e.get(state + 0x18),
                      e.get(owner + 0x6c), *(list(call.arguments) + [0, 0])[:2])
                e.put(trace, count + 1)
                e.put(obj + 0x60, words[5] ^ slot)
                if mutate:
                    e.put(state + 0x1c, words[6])
                    e.put(state + 0x18, alternate)
                    e.put(owner + 0x6c, other_state)
                return words[7] ^ slot
            return env.stub('floor-slot-' + str(slot), 'thiscall', argc, effect)
        alternate = env.object(0x6c, 'alternate-floor', fill=0x71)
        other_state = env.object(0x180, 'alternate-state', fill=0x83)
        for slot, argc in ((4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)):
            env.put(table + slot, callback(slot, argc))
        # Cached numeric state -> CString avoids changing the original dispatcher.
        cached = env.object(12, 'cached-state-string', words=[cstring(env, 'STATE_'+str(state_id))], fill=0)
        env.put(0x5376a0, state_id, state_id, cached, cached, 12, 0, 0)
        # Constructor copies four separate words and traverses this scene chain.
        scene = env.object(0xb0, 'scene-record', fill=0x29)
        env.put(scene + 0x98, *words[:4])
        env.put(0x537960, scene)
        player = env.object(0x100, 'player', fill=0)
        player_state = env.object(0x100, 'player-state', fill=0)
        player_detail = env.object(0x100, 'player-detail', fill=0)
        env.put(player + 0x6c, player_state)
        env.put(player_state + 0x14, player_detail)
        env.put(player_detail + 0x80, words[3])
        env.put(0x537e88, player)
        def allocate(e, call):
            block = e.object(call.arguments[0], 'constructed-floor', words=words * 6, fill=0x49)
            e.put(trace + 0x180, call.arguments[0], e.get(state + 0x1c), e.get(state + 0x18),
                  e.get(owner + 0x6c), block)
            return block
        env.override(NEW, allocate)
        return {'owner': owner}
    return setup


def cases(random_source):
    for state_id in (0, 1, 28, 29, 30, 31, 999, 1000, 1001, 0xffffffff, 0x80000000):
        for mutate in (False, True):
            words = [random_source.getrandbits(32) or (index + 1) for index in range(8)]
            yield Case(f'state {state_id:#x} callback mutation {mutate}', ENTRY,
                       setup_case(state_id, words, mutate=mutate),
                       arguments=(lambda t: t['owner'],))
    for hit in (False, True):
        for _ in range(3):
            words = [random_source.getrandbits(32) or (index + 1) for index in range(8)]
            yield Case(f'construction resources {hit} {words[0]:x}', ENTRY,
                       setup_case(0, words, hit=hit), arguments=(lambda t: t['owner'],))


def aliased_construction(words, mutate):
    """The unchanged rectangle copy overlaps the new object's vtable word.

    Return an interior, fully backed allocation at owner+0x128. The late
    constructor copy from scene+0x98 therefore installs our fresh callback
    table through ordinary original stores. Its fourth word changes +0xc to
    a separate owner record; accesses through that resulting alias are backed too.
    """
    def setup(env):
        w = world(env, idle_state=words[0] % 100 + 1)
        base = env.object(0x400, 'overlapping-owner-and-floor', fill=0x67)
        owner = base + 0x40
        floor = owner + 0x128
        state = w['state']
        for offset in range(0, 0x200, 4):
            env.put(owner + offset, words[(offset // 4) % len(words)])
        env.put(owner + 0xc, w['world'])
        env.put(owner + 0x6c, state)
        env.put(owner + 0x38, 0xffffffff)
        env.put(owner + 0x174, 0)
        env.put(state + 0x1c, 0)
        prior = env.object(0x6c, 'prior-published-object', fill=0x43)
        alternate = env.object(0x6c, 'callback-published-object', fill=0x75)
        env.put(state + 0x18, prior)
        trace = env.object(0x200, 'initialization-observations', fill=0)
        table = env.object(0x24, 'fresh-initialization-table', fill=0)
        def initialize(e, call):
            e.put(trace, call.receiver, e.get(state + 0x18), e.get(state + 0x1c),
                  e.get(owner + 0x6c), e.get(floor + 0xc), e.get(floor + 0x10),
                  e.get(floor + 0x24), e.get(floor + 0x48), e.get(floor + 0x4c),
                  e.get(floor + 0x54), e.get(floor + 0x68))
            e.write(trace + 0x40, e.read(floor, 0x6c))
            if mutate:
                e.put(state + 0x18, alternate)
                e.put(state + 0x1c, words[7])
                e.put(floor + 0x60, words[6])
            return words[5]
        env.put(table + 0x10, env.stub('initialize-aliased-floor', 'thiscall', 0, initialize))
        late_owner = env.object(0x200, 'late-constructor-owner', fill=0x35)
        env.put(late_owner + 0x4c, words[4])
        env.put(late_owner + 0x148, words[5])
        scene = env.object(0xb0, 'alias-scene', fill=0x39)
        env.put(scene + 0x98, table, words[1], words[2], late_owner)
        env.put(0x537960, scene)
        player = env.object(0x100, 'alias-player', fill=0)
        ps = env.object(0x100, 'alias-player-state', fill=0)
        pd = env.object(0x100, 'alias-player-detail', fill=0)
        env.put(player + 0x6c, ps)
        env.put(ps + 0x14, pd)
        env.put(pd + 0x80, words[3])
        env.put(0x537e88, player)
        def allocate(e, call):
            e.put(trace + 0x180, call.arguments[0], e.get(state + 0x1c),
                  e.get(state + 0x18), floor)
            return floor
        env.override(NEW, allocate)
        return {'owner': owner}
    return setup


_base_cases = cases


def cases(random_source):
    yield from _base_cases(random_source)
    for mutate in (False, True):
        for index in range(3):
            words = [random_source.getrandbits(32) or (i + 1) for i in range(8)]
            yield Case(f'original-copy alias initialization mutation {mutate} sample {index}',
                       ENTRY, aliased_construction(words, mutate),
                       arguments=(lambda t: t['owner'],))
