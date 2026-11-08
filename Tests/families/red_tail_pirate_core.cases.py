"""Original-derived Red Tail Pirate object and state cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns

RAND = 0x4A3050

def signed(v):
    return v if v < 0x80000000 else v - 0x100000000


def world(options):
    def setup(env):
        o = options
        actor = env.object(0x4C0, 'pirate', fill=0)
        sprite = env.object(0x220, 'sprite', fill=0)
        logic = env.object(0x200, 'logic', fill=0)
        scene = env.object(0x100, 'scene', fill=0)
        player = env.object(0x220, 'player', fill=0)
        plogic = env.object(0x100, 'player-logic', fill=0)
        pstate = env.object(0x100, 'player-state', fill=0)
        special = env.object(0x540, 'special-mode', fill=0)
        hit = env.object(0x200, 'hit-source', fill=0)
        terrain = env.object(0xA0, 'terrain', fill=0)
        grid = env.object(0xA0, 'empty-grid', fill=0)
        cells = env.object(4, 'empty-cell', words=[0xFFFFFFFF])
        rows = env.object(4, 'grid-row', words=[0])
        env.put(scene + 0x24, terrain)
        env.put(terrain + 0x5C, grid)
        env.put(terrain + 0x64, 1024, 1024)
        env.put(grid + 0x20, cells, rows)
        env.put(grid + 0x30, 1024, 1024)
        env.put(grid + 0x8C, 10, 10)
        env.put(sprite + 0xC, scene)
        env.put(sprite + 0x6C, logic)
        env.put(sprite + 0x74, hit)
        env.put(sprite + 0x38, o.get('ground', 1))
        env.put(sprite + 0x40, o.get('flip', 0))
        env.put(sprite + 0x4C, 200, 300)
        env.put(sprite + 0xCC, 7)
        env.put(sprite + 0x10C, 100)
        env.put(sprite + 0x118, -17, -23, 31, 43)
        env.put(sprite + 0x128, -37, -41, 47, 53)
        env.put(sprite + 0x138, -59, -61, 67, 71)
        env.put(sprite + 0x190, 0x12345678)
        env.put(logic + 0x1C, 7)
        env.put(logic + 0x14, actor)
        env.put(player + 0x4C, o.get('px', 230), 300 + o.get('dy', 0))
        env.put(player + 0x6C, plogic)
        env.put(player + 0xCC, o.get('player_mode', 1))
        env.put(plogic + 0x14, pstate)
        env.put(pstate, o.get('player_facing', 0), o.get('player_attack', 1))
        env.put(pstate + 0x3C, o.get('player_state', 1))
        env.put(pstate + 0xE8, o.get('hit_id', 71))
        env.put(hit + 0xD0, o.get('hit_type', 2))
        env.put(special + 0x520, o.get('special_flag', 0), o.get('special_count', 9), o.get('limit_x', 300), o.get('target_x', 450), o.get('target_y', 800))
        env.put(0x53774C, special if o.get('special', False) else 0)
        env.put(0x537E88, player)
        env.put(0x537210, o.get('now', 10000))
        env.put(0x5430C4, 17)
        env.put(0x534EAC, 0x26B7 if o.get('blind', False) else 0)
        env.put(0x537964, o.get('level', 8))
        env.put(0x541334, 1)
        env.put(0x544D18, 0)
        env.put(0x537668 + 0x18, 0)  # empty original state-name trie
        env.put(0x532C0C, o.get('audio', 0))
        env.put(0x532C10, 0x123)
        env.put(0x53C9A8, 0)
        env.put(0x53C9AC, player)  # 0x48ce40 publishes selected voice here
        env.put(actor + 0x8, sprite, sprite, logic)
        env.put(actor + 0x20, o.get('busy', 2), 0x24681357)
        for off, value in ((0x38, 1.0), (0x40, 9.0), (0x48, 0.5), (0x50, 21.5), (0x58, -31.25), (0x60, 41.0), (0x68, 200.0), (0x70, 300.0), (0x78, 5.0), (0x98, 200.0)):
            env.write(actor + off, struct.pack('<d', value))
        env.put(actor + 0x128, sprite, sprite, logic)
        env.put(actor + 0x138, -13, -19, 29, 37)
        env.put(actor + 0x14C, 9, 4)
        env.put(actor + 0x184, o.get('state', 3), 0, o.get('facing', 2), sprite, sprite)
        env.put(actor + 0x19C, o.get('prior_hit', 17))
        env.put(actor + 0x2E4, o.get('chance', 50))
        env.put(actor + 0x2FC, 32, 0x10)
        env.put(actor + 0x400, 123, 247)
        env.put(actor + 0x424, o.get('bounces', 0))
        env.put(actor + 0x414, 0x19384756, 0x82736451)
        env.put(actor + 0x450, o.get('dodge_chance', 90))
        env.put(actor + 0x494, o.get('then', 9000), o.get('delay', 500))
        env.put(actor + 0x4A4, o.get('dodge_then', 9000), o.get('dodge_delay', 500), o.get('hurt', 0), o.get('seen', 1))
        for off in range(0x210, 0x280, 4):
            env.put(actor + off, (off * 7) ^ 0x1931)
        for off in (0x1A4, 0x1A8):
            ref = env.object(32, 'ref-string', words=[o.get('references', 2), 3, 3, 0x616263])
            env.put(actor + off, ref + 12)
        # Real original hash containers; each value has a distinct backing object.
        frame = env.object(0x40, 'animation-frame', fill=0)
        env.put(frame + 0xC, 9)
        env.put(frame + 0x1C, 0x1749)
        frame_list = env.object(4, 'frame-list', words=[frame])
        anim_names = ('ADVANCE FASTADVANCE HITHIGH HITLOW IDLE JUMP KILLFALL LIFTED1 LIFTED2 STRIKE1 STRIKE2 THROWN BLOCK HOME QUICKBLOCK').split()
        animations = {}
        for i, name in enumerate(anim_names + ['NULL']):
            anim = env.object(0x20, 'animation-' + name, fill=0)
            env.put(anim + 0xC, frame_list, 1)
            animations['GAME_NULL' if name == 'NULL' else 'LEVEL_REDTAILPIRATE_' + name] = anim
        env.put(sprite + 0x18C, sprite, next(iter(animations.values())), frame)
        env.put(sprite + 0x1B0, 0x3F800000)
        if o.get('missing', False):
            animations = {'GAME_NULL': animations['GAME_NULL']}
        if o.get('no_null', False):
            animations = {}
        def hash_table(entries, name):
            table = env.object(0x40, name, fill=0)
            buckets = env.object(4, name + '-bucket', fill=0)
            head = 0
            for key, value in entries.items():
                text = env.object(len(key) + 1, name + '-key', data=key.encode() + b'\0')
                head = env.object(16, name + '-node', words=[head, 0, text, value])
            env.put(buckets, head)
            env.put(table + 0x14, buckets, 1)
            return table
        sound_env = env.object(0x80, 'disabled-sound-environment', fill=0)
        sound_impl = env.object(0x20, 'sound-implementation', fill=0)
        env.put(sound_impl + 0x10, sound_env)
        voices = {}
        for i in range(1, 30):
            voice = env.object(0x20, 'voice-%02d' % i, fill=0)
            env.put(voice + 0x10, sound_impl)
            voices['LEVEL_REDTAILPIRATE_004900%02d' % i] = voice
        for key in ('BLOCK1', 'BLOCK2'):
            voice = env.object(0x20, 'voice-' + key, fill=0)
            env.put(voice + 0x10, sound_impl)
            voices['LEVEL_REDTAILPIRATE_' + key] = voice
        for key in o.get('omit_voices', ()):
            voices.pop(key, None)
        empty = hash_table({}, 'empty-resources')
        amap = hash_table(animations, 'animation-map')
        vmap = hash_table(voices if not o.get('mute', False) else {}, 'voice-map')
        env.put(scene + 0x10, empty, empty)
        env.put(scene + 0x28, vmap, amap)
        for off in range(0x308, 0x38C, 4):
            env.put(actor + off, list(animations.values())[0] if animations else 0)
        env.put(actor + 0x454, list(animations.values())[-1] if animations else 0)
        voice_values = list(voices.values())
        for i, off in enumerate(range(0x458, 0x494, 4)):
            env.put(actor + off, voice_values[i] if not o.get('mute', False) else 0)
        # Virtual observations survive in heap, recording receiver, state and order.
        records = env.object(0x800, 'virtual-observations', fill=0)
        vt = env.object(0xC0, 'pirate-vtable', fill=0)
        def callback(slot):
            def effect(e, call):
                count = e.get(records)
                dest = records + 4 + count * 48
                e.put(dest, slot, call.receiver, len(call.arguments), *call.arguments)
                e.put(dest + 20, e.get(actor + 0x20), e.get(actor + 0x310), e.get(actor + 0x494), e.get(actor + 0x498), e.get(actor + 0x4AC))
                e.put(records, count + 1)
                if o.get('callback_mutate', False):
                    e.put(0x537210, 0xF1234567)
                    e.put(actor + 0x450, 21)
                return 0x97531
            return effect
        for slot in range(0, 0xC0, 4):
            argc = 1 if slot in (0x2C, 0x30, 0x34, 0x38, 0x3C, 0x40, 0x5C, 0x90) else 0
            env.put(vt + slot, env.stub('pirate-virtual-%x' % slot, 'thiscall', argc, callback(slot)))
        env.put(actor, vt)
        values = o.get('random', (80, 80, 80, 80))
        def rand(e, call):
            index = e.calls_so_far(RAND) - 1
            return values[min(index, len(values) - 1)] & 0xFFFFFFFF
        env.override(RAND, rand)
        def decrement(e, call):
            value = (e.get(call.arguments[0]) - 1) & 0xFFFFFFFF
            e.put(call.arguments[0], value)
            return value
        env.override(0x5469E8, decrement)
        def copy_rect(e, call):
            e.write(call.arguments[0], e.read(call.arguments[1], 16))
            return 1
        env.override(0x546D58, copy_rect)
        def contains(e, call):
            l, t, r, b = struct.unpack('<4i', e.read(call.arguments[0], 16))
            x, y = map(signed, call.arguments[1:])
            return int(l <= x < r and t <= y < b)
        env.override(0x546CD4, contains)
        if o.get('physics'):
            for off, value in zip((0x38, 0x40, 0x48, 0x68, 0x70, 0x78), o['physics']):
                env.write(actor + off, struct.pack('<d', value))
        return {'actor': actor, 'sprite': sprite, 'logic': logic, 'records': records, 'callback': callback, 'special': special}
    return setup


def test(label, address, options=None, arg=None, customize=None, initial_stack=()):
    def setup(env):
        tokens = world(options or {})(env)
        if customize:
            customize(env, tokens)
        return tokens
    return Case(label, address, setup, receiver=lambda t: t['actor'], arguments=() if arg is None else (arg,), initial_stack=initial_stack)


def cases(random_source):
    # Constructor CALLs 483006/483033/483056 consume the original FLD/FILD
    # products independently. Elect each sticky flag, plus combined flags,
    # while varying which conversion is integral, fractional or negative.
    # The ambient contract compares the original's complete final CW/SW.
    # No case API elects live slots or TOP; finite transport covers those.
    products = (
        (1.0, 120.0, 1.0, 1.0),
        (1.0, 99.0, 1.0, 1.0),
        (1.25, 100.5, 1.0, 1.0),
        (1.0, 120.0, 1.125, 1.0),
        (1.0, 120.0, 1.0, 1.375),
        (0.0, 120.0, 0.0, 0.0),
        (-1.25, 120.0, -1.125, -1.375),
        (0.125, 799.0, 0.375, 0.625),
    )
    for status in (0, 1, 2, 4, 8, 16, 32, 33, 63):
        for index, factors in enumerate(products):
            def ambient(e, t, status=status, factors=factors):
                e.entry_x87_status(status)
                for address, value in zip((0x5262B8, 0x50F360, 0x5262B4, 0x5262B0), factors):
                    e.write(address, struct.pack('<f', value))
            yield test('constructor ambient sw=%02x products=%d' % (status, index),
                       0x4828E0, arg=lambda t: t['sprite'], customize=ambient)
    for missing in (False, True):
        for mode in (0, 1, 2):
            for scale in (0.5, 1.0, 3.0):
                def scale_globals(e, t, scale=scale):
                    for a in (0x5262B0, 0x5262B4, 0x5262B8):
                        e.write(a, struct.pack('<f', scale))
                yield test('construct missing=%s mode=%d scale=%s' % (missing, mode, scale), 0x4828E0,
                           {'missing': missing, 'special': mode != 0, 'special_flag': mode - 1},
                           arg=lambda t: t['sprite'], customize=scale_globals)
    for refs in (1, 2, 5):
        for flag in (0, 1, 2, 255, 0x100):
            yield test('delete refs=%d flag=%d' % (refs, flag), 0x483090, {'references': refs}, flag)
        yield test('destruct refs=%d' % refs, 0x4830B0, {'references': refs})
    for special, flag in ((False, 0), (True, 0), (True, 1)):
        for value in (0, 1, 2, 3, 4, 0xFFFFFFFF):
            yield test('death special=%s flag=%s kind=%s' % (special, flag, value), 0x483E10,
                       {'special': special, 'special_flag': flag, 'random': (80,)}, value)
    for hurt in (0, 1, 7):
        for bounces in (0, 1, 2, 3):
            yield test('bounce hurt=%s count=%s' % (hurt, bounces), 0x484240, {'hurt': hurt, 'bounces': bounces})
    for r in (-4, -1, 0, 1, 2, 3, 4, 5, 24, 25, 100, 0x7FFFFFFF):
        yield test('lift voice=%s' % r, 0x484210, {'random': (r, 80)})
        for second in (-3, -1, 0, 1, 2, 3):
            yield test('strike voice=%s/%s' % (r, second), 0x484260, {'random': (r, second)})
    for facing in (2, 3):
        for muted, audio in ((False, 1), (False, 0), (True, 1)):
            for r in (-1, 0, 1, 2):
                yield test('block %s %s %s %s' % (facing, muted, audio, r), 0x483D20,
                           {'facing': facing, 'mute': muted, 'audio': audio, 'random': (r,)})
    for state in range(8):
        for r in (0, 49, 50, 59, 60, 79, 80, 120):
            for elapsed in (499, 500):
                yield test('think state=%d rand=%d elapsed=%d' % (state, r, elapsed), 0x4837B0,
                           {'state': state, 'random': (r, r, r), 'then': 10000 - elapsed, 'callback_mutate': elapsed == 500})
    for hurt in (0, 1):
        for seen in (0, 1):
            for dy in (-50, -49, 0, 49, 50):
                yield test('notice hurt=%s seen=%s dy=%s' % (hurt, seen, dy), 0x4837B0,
                           {'hurt': hurt, 'seen': seen, 'dy': dy, 'state': 7, 'random': (0, 1, 80)})
    for level in (8, 13, 4):
        for hit_type in (2, 32, 3):
            for r in (0, 24, 25, 49, 50, 74, 75, 100):
                yield test('react level=%s hit=%s rand=%s' % (level, hit_type, r), 0x483AE0,
                           {'level': level, 'hit_type': hit_type, 'random': (r, 0), 'audio': 1})
    for state in (0, 1, 2, 7, 8, 9):
        for facing in (2, 3):
            yield test('react player-state=%s facing=%s' % (state, facing), 0x483AE0,
                       {'player_state': state, 'facing': facing, 'hit_type': 32, 'random': (0, 1), 'flip': 2})
    yield test('react repeated hit returns early', 0x483AE0, {'prior_hit': 71})
    for missing in (False, True):
        for mode in (1, 5):
            for chance in (0, 20, 90):
                yield test('attack missing=%s player-mode=%s chance=%s' % (missing, mode, chance), 0x483560,
                           {'missing': missing, 'player_mode': mode, 'dodge_chance': chance, 'state': 3, 'random': (0,), 'blind': True}, 0x52720C)
    # Original 483681 resets a successful dodge delay to 500. Give it a
    # distinct inherited value rather than the world setup's default 500.
    for state, delay in ((3, 1), (3, 499), (4, 777)):
        yield test('successful dodge replaces delay state=%d delay=%d' % (state, delay),
                   0x483560, {'blind': True, 'state': state, 'random': (0,),
                             'dodge_chance': 90, 'dodge_delay': delay}, 0x52720C)
    for state_name in (0x52BA88, 0x527204, 0x523148):
        def attack_state(e, t, state_name=state_name):
            table = e.object(4, 'state-name', words=[state_name])
            e.put(0x537698 + 8, 7, 7, table, table, 4)
        yield test('special skips state %x' % state_name, 0x483560, {'special': True, 'blind': True}, 0x52720C, attack_state)
    yield test('special disabled attack invokes death virtual', 0x483560, {'special': True, 'special_flag': 1}, 0x52720C)
    yield test('physics special absent', 0x483F30)
    for vector in ((0., 0., 0.), (1e-8, 0., 0.), (.1, 0., 0.), (1., 9., .5), (-3., -7., 4.)):
        for origin in ((200., 300., 5.), (451., 300., 0.), (450., 400., 0.)):
            yield test('physics a=%s origin=%s' % (vector, origin), 0x483F30,
                       {'special': True, 'limit_x': 450, 'physics': vector + origin})
    for i in range(12):
        values = tuple(random_source.uniform(-20., 20.) for _ in range(3)) + (random_source.uniform(-200., 300.), random_source.uniform(-100., 700.), random_source.uniform(-30., 30.))
        yield test('random trajectory %d' % i, 0x483F30, {'special': True, 'physics': values})
    for index in (-1, 0, 1, 2, 3):
        for present in (True, False):
            def dispatch(e, t, index=index, present=present):
                callback = e.stub('state-dispatch', 'thiscall', 0, t['callback'](0x180))
                data = e.object(12, 'dispatch-table', words=[callback if present else 0] * 3)
                fallback = e.object(4, 'fallback-dispatch', words=[callback])
                error = e.object(24, 'error-policy', words=[0, 0, 0, 4, 0, 0])
                e.put(0x53C1A8 + 4, error, 0, 2, data, fallback, 4)
                base = e.object(12, 'base-dispatch', words=[callback] * 3)
                e.put(0x537878 + 4, error, -1, 3, base, fallback, 0)
            yield test('dispatch index=%s present=%s' % (index, present), 0x483180, arg=index, customize=dispatch)

    for missing in (True, False):
        yield test('think facing-left fallback=%s' % missing, 0x4837B0, {'state': 1, 'facing': 3, 'missing': missing, 'random': (0,)})
    yield test('react block facing-left', 0x483AE0, {'facing': 3, 'hit_type': 2, 'random': (0, 1), 'audio': 1})
    for state in (3, 4):
        yield test('attack opposite player facing state=%s' % state, 0x483560, {'blind': True, 'state': state, 'px': 100, 'player_facing': 1, 'random': (0,)}, 0x52720C)

    # Missing resource lookups must clear output cells before calling the
    # unchanged original map. Nonzero local backing distinguishes that store.
    poison = bytes(random_source.randrange(1, 256) for _ in range(256))
    for special in (False, True):
        yield test('constructor missing voices nonzero locals special=%s' % special, 0x4828E0,
                   {'mute': True, 'special': special},
                   arg=lambda t: t['sprite'], initial_stack=((-256, poison),))
    for r in (0, 10, 11):
        yield test('reaction missing voices nonzero output rand=%s' % r, 0x483AE0,
                   {'mute': True, 'hit_type': 3, 'random': (80, r)}, initial_stack=((-256, poison),))
    for vector in ((.1, .2, .3), (-.2, .3, -.1), (.01, -.02, .03)):
        yield test('normalized trajectory distinct components %s' % (vector,), 0x483F30,
                   {'special': True, 'physics': vector + (200., 300., 17.)})

    # A successful lookup followed by a missing lookup must not reuse the
    # previous output. Exercise each constructor position independently.
    for number in (5, 10, 11, 12, 13, 18, 21, 22, 16, 8, 1, 19, 14, 28):
        yield test('constructor partial voice map missing %02d' % number, 0x4828E0,
                   {'omit_voices': ('LEVEL_REDTAILPIRATE_004900%02d' % number,)},
                   arg=lambda t: t['sprite'], initial_stack=((-256, poison),))
    for omitted in (23, 24):
        yield test('reaction partial voice map missing %02d' % omitted, 0x483AE0,
                   {'omit_voices': ('LEVEL_REDTAILPIRATE_004900%02d' % omitted,),
                    'hit_type': 3, 'random': (80, 0)}, initial_stack=((-256, poison),))

    # The first normalized-path exchange selects the abs-sum addition order.
    # Small equal components beside one large component expose rounding at
    # both double and extended significand boundaries.
    for exponent in (52, 53, 54, 63, 64):
        for small in (1., 3., 7.):
            yield test('normalized disparate magnitudes 2**%s small=%s' % (exponent, small),
                       0x483F30, {'special': True,
                       'physics': (.1, .2, .3, 450. - 2.**exponent, 400. - small, -small)})

    # The original normalizes target displacement with three independent FABS
    # instructions when the acceleration norm is near zero. Exercise every
    # displacement sign; target X may be behind the actor even while the
    # separate encounter activation limit remains ahead of it.
    for acceleration in ((1e-8, 2e-8, 3e-8), (1., 2., 3.)):
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    yield test('trajectory signed components acceleration=%s signs=%s' %
                               (acceleration, (sx, sy, sz)), 0x483F30,
                               {'special': True, 'limit_x': 450,
                                'target_x': sx * 100, 'target_y': 400 + sy * 200,
                                'physics': acceleration + (0., 0., -sz * 300.)})
