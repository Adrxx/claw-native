"""Original-backed RatBomb cases; no game-function stand-ins."""
import struct
from clawparity.cases import Case


def put_double(env, address, value):
    env.write(address, struct.pack('<d', value))


def record(env, target, tag, argc=0, mutate=None):
    def effect(env, call):
        count = env.get(target)
        env.put(target, count + 1)
        env.put(target + 4 + count * 40, tag, call.receiver, argc,
                *(list(call.arguments) + [0, 0, 0])[:3])
        env.put(target + 28 + count * 40, env.get(call.receiver),
                env.get(call.receiver + 0x120), env.get(call.receiver + 0x168))
        if mutate:
            mutate(env, call)
        return 0xE13579BD
    return env.stub('physical callback ' + str(tag), 'thiscall', argc, effect)


def world(env, animation_result=None):
    logic = env.object(0x200, 'logic', fill=0)
    actor = env.object(0x240, 'actor', fill=0)
    config = env.object(0x180, 'config', fill=0)
    vt = env.object(0x44, 'logic vtable with RTTI prefix', fill=0) + 4
    locator = env.object(0x10, 'physical RTTI locator', fill=0)
    typeinfo = env.object(8, 'physical RTTI descriptor', fill=0)
    env.put(locator + 0xC, typeinfo)
    env.put(vt - 4, locator)
    observations = env.object(0x400, 'callback observations', fill=0)
    env.put(logic, vt)
    env.put(logic + 0xC, config, config)
    env.put(logic + 0x12C, actor)
    env.put(actor + 8, 0x12345601)
    env.put(actor + 0x188 + 4, actor)
    env.put(actor + 0x190, 0)
    env.put(actor + 0x118, 0xFFFFFFF5, 17, 29, 43)
    env.put(actor + 0x128, 0xFFFFFFF9, 41, 53, 67)
    env.put(actor + 0x138, 0xFFFFFFEF, 71, 83, 97)
    env.put(logic + 0x138, 0xFFFFFFE9, 107, 127, 139)
    env.put(config + 0x1C, 0x4567)
    env.put(config + 0x138, 11, 23, 41, 67)
    env.put(0x5430C4, 3)
    env.override(0x546A40, lambda env, call: 0 if len(env.read(call.arguments[0], call.arguments[1])) == call.arguments[1] else 1)
    env.put(0x537680, 0)  # empty original name trie returns ordinary zero
    for slot in (0x10, 0x1C, 0x20, 0x28, 0x2C):
        env.put(vt + slot, record(env, observations, slot))
    if animation_result is not None:
        env.put(actor + 0x190, env.object(4, 'animation identity'))
        env.put(actor + 0x19C, 20)  # timer > tick, physical early return
        env.put(actor + 0x1A0, 1)
        env.put(actor + 0x1AC, animation_result)
    return dict(logic=logic, actor=actor, config=config, vt=vt, observations=observations)


def state_case(label, function, configure=lambda env, t: None, animation_result=None):
    def setup(env):
        t = world(env, animation_result)
        configure(env, t)
        return t
    return Case(label, function, setup, receiver=lambda t: t['logic'])


def cases(random_source):
    for flag in (0, 1, 2, 3, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF):
        def setup(env):
            return env.object(0x20, 'base destructor', words=[0x12345678], fill=0xA7)
        yield Case('delete bit ' + hex(flag), 0x484D90, setup, receiver=lambda p: p, arguments=(flag,))
    yield Case('reset base vtable', 0x456030, setup, receiver=lambda p: p)

    for function, offset in ((0x406150, 0x128), (0x406180, 0x138)):
        for left, right in ((0, 1), (0x80000000, 41), (0x7FFFFFFF, 0x80000000),
                            (0xFFFFFFFF, 0x80000001), (17, 53)):
            def mirror(env, left=left, right=right, offset=offset):
                obj = env.object(0x180, 'mirror', fill=0xA7)
                env.put(obj + offset, left)
                env.put(obj + offset + 8, right)
                return obj
            yield Case(f'mirror {function:x} {left:x} {right:x}', function, mirror, receiver=lambda p: p)

    for i in range(18):
        coords = tuple(random_source.getrandbits(32) for _ in range(4))
        for function in (0x406240, 0x4741F0):
            def rectangles(env, i=i, coords=coords, function=function):
                t = world(env)
                actor = t['actor']
                if i == 0:
                    frame = 0
                elif i % 3 == 0:
                    frame = actor + (0x110 if function == 0x406240 else 0x100)  # raw overlap changes later coordinate reads
                else:
                    frame = env.object(0x30, 'frame', fill=0xAD)
                if frame:
                    env.put(frame + 0x18, *coords)
                env.put(actor + 0x174, frame)
                return dict(t, receiver=actor if function == 0x406240 else t['logic'])
            yield Case(f'rectangle {function:x} {i}', function, rectangles, receiver=lambda t: t['receiver'])

    for minimum, maximum, alias in ((0, 0, None), (7, 19, None), (-3, 5, None),
                                    (9, 8, None), (0x7FFFFFFF, 0x7FFFFFFF, None),
                                    (7, 1, 0x68), (4, 9, 0x64)):
        def select(env, minimum=minimum, maximum=maximum, alias=alias):
            actor = env.object(0x240, 'frame actor', fill=0x9B)
            manager = actor + 0x16C - alias if alias else env.object(0x80, 'frame manager')
            slot = env.object(4, 'selected slot', words=[0x13579BDF])
            env.put(manager + 0x14, (slot - minimum * 4) & 0xFFFFFFFF)
            env.put(manager + 0x64, minimum & 0xFFFFFFFF, maximum & 0xFFFFFFFF)
            env.put(actor + 0x170, manager)
            return actor
        yield Case(f'minimum {minimum} {maximum} alias {alias}', 0x47E1D0, select, receiver=lambda p: p)
    def no_manager(env):
        actor = env.object(0x178, 'no manager', fill=0x9B)
        env.put(actor + 0x170, 0)
        return actor
    yield Case('minimum no manager preserves bytes', 0x47E1D0, no_manager, receiver=lambda p: p)

    for enabled in (0, 1):
        for flags in (0, 0x10000, 0xABCDFFFF):
            def configure(env, t, enabled=enabled, flags=flags):
                env.put(t['logic'] + 0x148, enabled)
                env.put(t['logic'] + 0x120, flags)
            yield state_case(f'base update {enabled} {flags:x}', 0x4742F0, configure)
    for cc in (0, 1, 2):
        for flags in (0, 0x10000):
            for change in (False, True):
                def configure(env, t, cc=cc, flags=flags, change=change):
                    env.put(t['config'] + 0xCC, cc)
                    env.put(t['logic'] + 0x120, flags)
                    if change:
                        def mutate(env, call):
                            env.put(t['logic'] + 0x120, env.get(t['logic'] + 0x120) ^ 0x10000)
                            env.put(t['logic'], t['vt'] + 4)
                        env.put(t['vt'] + 0x2C, record(env, t['observations'], 1, mutate=mutate))
                        env.put(t['vt'] + 0x30, record(env, t['observations'], 2))
                yield state_case(f'fall update {cc} {flags:x} swap {change}', 0x47E180, configure)
    for result in (None, 0, 1, 2, 0xFFFFFFFF):
        for once in (0, 1):
            for final in (0, 1, 2):
                def configure(env, t, once=once, final=final):
                    env.put(t['logic'] + 0x168, once)
                    env.put(t['actor'] + 0x1A4, int(final != 0))
                    if final == 2:
                        env.put(t['actor'] + 0x19C, 20)
                    def inflate(env, call):
                        p, dx, dy = call.arguments
                        a, b, c, d = struct.unpack('<4I', env.read(p, 16))
                        env.put(p, (a-dx)&0xFFFFFFFF, (b-dy)&0xFFFFFFFF,
                                (c+dx)&0xFFFFFFFF, (d+dy)&0xFFFFFFFF)
                        return 1
                    env.override(0x546D24, inflate)
                yield state_case(f'explode update {result} {once} {final}', 0x47DFC0, configure, result)
    for sound_kind in (0, 1, 2):
        def configure(env, t, sound_kind=sound_kind):
            env.put(0x532C0C, int(sound_kind == 2))
            if sound_kind:
                sound = env.object(0x20, 'sound wrapper')
                voice = env.object(0x20, 'muted voice')
                device = env.object(0x80, 'disabled audio device', fill=0)
                env.put(voice + 0x10, device)
                env.put(sound + 0x10, voice)
                env.put(t['logic'] + 0x164, sound)
        yield state_case(f'enter exploding sound {sound_kind}', 0x47DF20, configure)

    def audible_explosion(env, t):
        wrapper = env.object(0x20, 'explosion sound resource', fill=0)
        voice = env.object(0x40, 'original sound owner', fill=0)
        device = env.object(0x80, 'active physical audio device', fill=0)
        sample = env.object(0x38, 'reusable original sound channel', fill=0)
        interface = env.object(4, 'physical DirectSound buffer')
        methods = env.object(0x50, 'DirectSound buffer methods', fill=0)
        env.put(wrapper + 0x10, voice)
        env.put(voice + 0x10, device)
        env.put(voice + 0x18, 11025, 17, 29)
        env.put(voice + 0x30, sample + 4, sample + 4)
        env.put(sample + 0xC, interface, device, 0xABCD0011, 22050)
        env.put(sample + 0x30, 1)
        env.put(interface, methods)
        env.put(device + 0x78, 1)
        env.put(t['logic'] + 0x164, wrapper, 0x12345678)
        env.put(0x532C0C, 1)
        env.put(0x532C10, 7)
        for slot, argc in ((0x24, 2), (0x3C, 2), (0x40, 2), (0x44, 2), (0x30, 4)):
            def physical_buffer(env, call, slot=slot):
                count = env.get(t['observations'])
                env.put(t['observations'], count + 1)
                env.put(t['observations'] + 4 + count * 40, slot,
                        *call.arguments, env.get(t['logic'] + 0xC8),
                        env.get(t['logic'] + 0x168))
                if slot == 0x24:
                    env.put(call.arguments[1], 0)  # physical buffer is idle
                return 0
            env.put(methods + slot, env.stub(f'DirectSound buffer {slot:x}', 'stdcall', argc, physical_buffer))
    yield state_case('explosion sound reaches original playback and physical buffer',
                     0x47DF20, audible_explosion)
    for direction in (-1.0, 0.0, -0.0, 1.0, float('inf'), -float('inf'), float('nan')):
        for flipped in (0, 2):
            for sentinel in (False, True):
                def configure(env, t, direction=direction, flipped=flipped, sentinel=sentinel):
                    for offset, result in ((0x150, 1), (0x154, 2)):
                        animation = env.object(0x18, f'fall animation {offset:x}', fill=0)
                        command = env.object(0x30, f'fall command {offset:x}', fill=0)
                        env.put(command + 8, 4, 9)
                        env.put(command + 0x18, 20, result)
                        env.put(animation + 0xC, env.object(4, 'fall command table', words=[command]), 1)
                        env.put(t['logic'] + offset, animation)
                    env.put(t['actor'] + 0x1B0, 0x3F800000)
                    put_double(env, 0x50F170, 0.0)
                    put_double(env, t['logic'] + 0x50, direction)
                    env.put(t['actor'] + 0x40, 0xABCDEF00 | flipped)
                    if sentinel:
                        env.put(t['actor'] + 0x118, 0x80000000)
                yield state_case(f'fall enter {direction} {flipped} {sentinel}', 0x47E050, configure)

    for state in (29, 30, 1000):
        def callback(env, state=state):
            t = world(env)
            env.put(t['actor'] + 0x6C, t['config'])
            env.put(t['config'] + 0x18, t['logic'], state)
            return t
        yield Case(f'factory existing state {state}', 0x47D7D0, callback, arguments=(lambda t: t['actor'],))

    for function, descriptor in ((0x47DB20, 0x53C118), (0x473F40, 0x538428)):
        for state in (-2, 0, 3):
            def dispatch(env, descriptor=descriptor, state=state):
                t = world(env)
                table = env.object(0x80, 'state table')
                env.put(descriptor + 8, state & 0xFFFFFFFF, state & 0xFFFFFFFF, table)
                env.put(descriptor + 0x18, 12)
                env.put(table, record(env, t['observations'], 91), 0x12345678, 0x9ABCDEF0)
                return t
            yield Case(f'dispatch {function:x} signed {state}', function, dispatch,
                       receiver=lambda t: t['logic'], arguments=(state & 0xFFFFFFFF,))

    for shift in (-3, -2, -1, 1, 2, 3):
        def partial_minimum(env, shift=shift):
            actor = env.object(0x240, 'partially aliased actor', fill=0)
            manager = actor + 0x16C - 0x64 + shift
            slot = env.object(4, 'aliased selected slot', words=[0x2468ACE1])
            minimum = 0x01020304
            env.put(manager + 0x14, (slot - minimum * 4) & 0xFFFFFFFF)
            env.put(manager + 0x64, minimum, 0x7FFFFFFF)
            env.put(actor + 0x170, manager)
            actual = env.get(manager + 0x64)
            env.put(manager + 0x14, (slot - actual * 4) & 0xFFFFFFFF)
            return actor
        yield Case(f'partial minimum alias {shift}', 0x47E1D0, partial_minimum, receiver=lambda p: p)

    for function in (0x473C50, 0x47D890):
        for populated in (False, True):
            for nonzero in (False, True):
                for manager in (False, True):
                    def construct(env, populated=populated, nonzero=nonzero, manager=manager):
                        return constructor_world(env, populated, nonzero, manager)
                    yield Case(f'constructor {function:x} resources {populated} values {nonzero} manager {manager}',
                               function, construct, receiver=lambda t: t['logic'], arguments=(lambda t: t['actor'],))
    for state in (1, 28, 31, 0xFFFFFFFF):
        def generic_callback(env, state=state):
            t = world(env)
            env.put(t['actor'] + 0x6C, t['config'])
            env.put(t['config'] + 0x18, t['logic'], state)
            env.put(t['logic'] + 0x10, t['config'])
            string = env.object(32, 'shared physical string', fill=0)
            env.put(string, 1, 0, 0)
            table = env.object(4, 'generic dispatch table', words=[string+12])
            env.put(0x5376A0, state, state, table)
            env.put(0x5376B0, 4)
            for offset in (4, 8, 12):
                env.put(t['vt'] + offset, record(env, t['observations'], offset, argc=1))
            return t
        yield Case(f'factory generic runtime {state:x}', 0x47D7D0, generic_callback, arguments=(lambda t: t['actor'],))
    def new_callback(env):
        t = constructor_world(env, True, False, True)
        env.put(t['config'] + 0x18, 0xDEAD1234, 0)
        # The constructor publishes its real RatBomb vtable; its ordinary entry
        # callback is original code and performs state/rectangle initialization.
        return t
    yield Case('factory normal allocation and constructor', 0x47D7D0, new_callback,
               arguments=(lambda t: t['actor'],))

    def sound_lookup_alias(env):
        t = constructor_world(env, True, False, True)
        owner = env.get(t['actor'] + 0xC)
        resources = env.get(owner + 0x28)
        bomb_key = env.object(13, 'bomb lookup aliased key', data=b'GAME_BOMBEXP\0')
        boink_key = env.object(13, 'boink lookup preceding key', data=b'GAME_BOINKJR\0')
        bomb = env.object(0x20, 'bomb resource observed before once reset', fill=0xA9)
        boink = env.object(0x20, 'boink resource', fill=0xB7)
        env.put(t['logic'] + 0x164, bomb_key, bomb)
        first = env.object(16, 'boink bucket node before aliased bomb node',
                           words=[t['logic'] + 0x15C, 0x13579BDF, boink_key, boink])
        env.put(resources + 0x14, env.object(4, 'aliased sound bucket', words=[first]))
        return t
    yield Case('sixth constructor lookup observes once field before reset', 0x47D890,
               sound_lookup_alias, receiver=lambda t: t['logic'], arguments=(lambda t: t['actor'],))


    for function, descriptor in ((0x47DB20, 0x53C118), (0x473F40, 0x538428)):
        for state in (-1, 1):
            # A null CRT realloc makes the unchanged game grow-table helper
            # dereference address four in its diagnostic path. That failure
            # cannot be represented as a returning ordinary-ABI case.
            for failed_resize in (False,):
                def outside(env, descriptor=descriptor, state=state, failed_resize=failed_resize):
                    t = world(env)
                    table = env.object(0x40, 'resizable physical table', fill=0)
                    fallback = env.object(4, 'fallback callback slot', words=[record(env, t['observations'], 101)])
                    diagnostic = env.object(0x18, 'noninteractive diagnostic policy', fill=0)
                    env.put(diagnostic + 0xC, 4)
                    env.put(descriptor + 4, diagnostic, 0, 0, table, fallback, 4)
                    env.put(table, record(env, t['observations'], 102))
                    # A different inherited descriptor handles expanded null entries.
                    base = env.object(4, 'base table', words=[record(env, t['observations'], 103)])
                    if descriptor != 0x538428:
                        env.put(0x538430, state & 0xFFFFFFFF, state & 0xFFFFFFFF, base)
                        env.put(0x538440, 4)
                    def resize(env, call):
                        old, size = call.arguments
                        if failed_resize:
                            return 0
                        new = env.object(size, 'resized physical allocation', fill=0xB9)
                        env.write(new, env.read(old, min(4, size)))
                        env.release(old)
                        return new
                    env.override(0x4A9070, resize)
                    return t
                yield Case(f'outside dispatch {function:x} {state} resize fail {failed_resize}', function,
                           outside, receiver=lambda t: t['logic'], arguments=(state & 0xFFFFFFFF,))

    def empty_base(env):
        t = world(env)
        table = env.object(4, 'empty base callback', words=[0])
        env.put(0x538430, 0, 0, table)
        env.put(0x538440, 4)
        methods = env.object(0x44, 'RTTI prefixed methods', fill=0)
        locator = env.object(0x10, 'physical RTTI locator', fill=0)
        typeinfo = env.object(8, 'physical RTTI typeinfo', words=[0x12345678, 0xABCDEF01])
        env.put(locator + 0xC, typeinfo)
        env.put(methods, locator)
        env.put(t['logic'], methods + 4)
        return t
    yield Case('empty base dispatch original RTTI', 0x473F40, empty_base,
               receiver=lambda t: t['logic'], arguments=(0,))


    def cycle(env):
        t = constructor_world(env, False, False, True)
        actor = t['actor']
        animation = env.object(0x18, 'cyclic animation', fill=0)
        command = env.object(0x30, 'backward frame command', fill=0)
        env.put(command + 8, 7, 9, 0, 3, 20, 1)
        env.put(animation + 0xC, env.object(4, 'cyclic command slot', words=[command]), 1)
        env.put(actor + 0x188 + 4, actor, animation, command)
        env.put(actor + 0x1B0, 0x3F800000)
        env.put(t['logic'] + 0x148, 1)
        return t
    yield Case('cyclic original animation reloads owned minimum', 0x4742F0,
               cycle, receiver=lambda t: t['logic'])


    def table_pointer_alias(env):
        actor = env.object(0x240, 'actor aliases manager table pointer', fill=0x37)
        manager = actor + 0x158
        selected = env.object(4, 'live reread table slot', words=[0x12345678])
        stale = env.object(4, 'cached table slot', words=[0x89ABCDEF])
        minimum = (selected * 0xCCCCCCCD) & 0xFFFFFFFF
        env.put(manager + 0x14, (stale - minimum * 4) & 0xFFFFFFFF)
        env.put(manager + 0x64, minimum, minimum)
        env.put(actor + 0x170, manager)
        return actor
    yield Case('minimum store replaces aliased table pointer before reread', 0x47E1D0,
               table_pointer_alias, receiver=lambda p: p)

    for function, descriptor in ((0x47DB20, 0x53C118), (0x473F40, 0x538428)):
        def inverted_wrapping_range(env, descriptor=descriptor):
            t = world(env)
            table = env.object(4, 'physical minimum realloc block',
                               words=[record(env, t['observations'], 104)])
            env.put(descriptor + 8, 0, 0x80000000, table)
            env.put(descriptor + 0x18, 4)
            # Both resize requests are four bytes. The inverted signed range
            # makes prefix/suffix byte counts wrap to zero, preserving the
            # callback while each original growth pass updates one bound.
            env.override(0x4A9070, lambda env, call: call.arguments[0])
            return t
        yield Case(f'inverted wrapping dispatch {function:x} grows twice', function,
                   inverted_wrapping_range, receiver=lambda t: t['logic'], arguments=(0xC0000000,))


def constructor_world(env, populated, nonzero, manager):
    t = world(env)
    actor = t['actor']
    owner = env.object(0x40, 'physical actor resource owner', fill=0)
    collision = env.object(0x80, 'collision map unused by mode seven', fill=0)
    env.put(actor + 0xC, owner)
    env.put(actor + 0x6C, t['config'])
    env.put(actor + 0x64, 0x137E if nonzero else 0)
    env.put(owner + 0x24, collision)
    env.put(actor + 0x4C, 17, 29)
    env.put(actor + 0x148, 3, 5)
    env.put(t['config'] + 0x2C, *(([-7, 11, -13, 19]) if nonzero else ([0]*4)))
    env.put(0x537210, 17)
    env.put(0x513E40, 0x80000001)
    if manager:
        frames = env.object(0x70, 'physical frame manager', fill=0)
        frame = env.object(0x30, 'physical selected frame', fill=0)
        slots = env.object(4, 'frame manager table', words=[frame])
        env.put(frame + 0x18, 3, 7, 19, 31)
        env.put(frames + 0x14, slots)
        env.put(frames + 0x64, 0, 0)
        env.put(actor + 0x170, frames)
    for offset in (0x10, 0x14, 0x28, 0x2C):
        resources = env.object(0x30, f'resource table {offset:x}', fill=0)
        env.put(resources + 0x18, 1)
        env.put(owner + offset, resources)
        if populated and offset == 0x10:
            loaded = env.object(0x70, 'named RatBomb frame manager', fill=0)
            frame = env.object(0x30, 'named RatBomb frame', fill=0)
            env.put(frame + 0x18, 13, 23, 59, 101)
            env.put(loaded + 0x14, env.object(4, 'named RatBomb frame slot', words=[frame]))
            env.put(loaded + 0x64, 0, 0)
            key = env.object(14, 'RatBomb frame resource key', data=b'LEVEL_RATBOMB\0')
            node = env.object(16, 'RatBomb frame resource bucket', words=[0, 0x37, key, loaded])
            env.put(resources + 0x14, env.object(4, 'RatBomb frame bucket slot', words=[node]))
        if populated and offset in (0x28, 0x2C):
            names = (('GAME_BOINKJR', 'GAME_BOMBEXP') if offset == 0x28 else
                     ('LEVEL_RATBOMB_FALL', 'LEVEL_RATBOMB_FALLEASTWEST',
                      'LEVEL_RATBOMB_EXPLODE', 'LEVEL_RATBOMB_BOUNCE'))
            head = 0
            for index, name in enumerate(names):
                value = env.object(0x30, name + ' resource', fill=0)
                command = env.object(0x30, name + ' physical command', fill=0)
                env.put(command + 8, 4, 9)
                env.put(command + 0x18, 20, 1)
                env.put(value + 0xC, env.object(4, name + ' command slot', words=[command]), 1)
                text = env.object(len(name)+1, name + ' key', data=name.encode()+b'\0')
                node = env.object(16, name + ' bucket node', words=[head, 0xA7123456, text, value])
                head = node
            bucket = env.object(4, 'single real resource bucket', words=[head])
            env.put(resources + 0x14, bucket)
    return t
