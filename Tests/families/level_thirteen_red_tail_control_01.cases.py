"""Original-backed Red Tail control cases, with surviving callback observations."""
import itertools
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_case(random_words, **options):
    def setup(env):
        def alloc(size, name, **kw):
            return env.object(size, name, fill=0, **kw)
        obj = alloc(0x540, 'red-tail')
        actor = alloc(0x240, 'actor')
        replacement = alloc(0x240, 'replacement-actor')
        sprite = alloc(0x220, 'sprite')
        animation = alloc(0x40, 'animation')
        player = alloc(0x80, 'player')
        contact = alloc(0x180, 'contact')
        contact_state = alloc(0x160, 'contact-state')
        vtable = alloc(0x80, 'vtable')
        alternate = alloc(0x80, 'alternate-vtable')
        log = alloc(0x3000, 'callback-observations')
        argument = alloc(0x40, 'argument', words=random_words[:8])
        env.put(argument + 8, random_words[2] & ~0x10000)
        for offset in (0x14, 0x24, 0x134, 0x138, 0x140, 0x404, 0x460, 0x504):
            env.put(obj + offset, random_words[(offset // 4) % len(random_words)])
        for offset in (0x38, 0x40, 0x50, 0x58, 0x60):
            # Distinct finite doubles with nonzero low halves expose each 32-bit store.
            env.put(obj + offset, 0x12345679 + offset, 0x40400000 + offset * 0x100)
        def double(offset, value):
            env.write(obj + offset, struct.pack('<d', value))
        double(0x68, options.get('x', 5.0))
        double(0x70, options.get('y', 10.0))
        double(0x80, options.get('left', 3.0))
        double(0x98, options.get('right', 9.0))
        env.put(obj, vtable)
        env.put(obj + 0xc, actor, animation)
        env.put(obj + 0x20, options.get('count', 2))
        env.put(obj + 0x128, sprite, sprite)
        env.put(obj + 0x184, options.get('state', 0), 0, options.get('direction', 2))
        env.put(obj + 0x2fc, 32, 0x80)
        env.put(obj + 0x30c, 0 if options.get('null-animation') else animation)
        env.put(obj + 0x404, options.get('speed', random_words[1]))
        env.put(obj + 0x460, options.get('action', 0))
        env.put(obj + 0x47c, animation)
        env.put(obj + 0x504, options.get('hits', 2))
        env.put(actor + 0xcc, options.get('actor-state', 1))
        env.put(replacement + 0xcc, 0x76543210)
        env.put(sprite + 8, 0x10)
        env.put(sprite + 0x40, 0xa5b4c6e0 | options.get('flip', 0))
        env.put(sprite + 0x80, contact)
        env.put(contact + 0x164, 0x8000)
        env.put(contact + 0x6c, contact_state)
        env.put(contact_state + 0x1c, 5)
        for index, offset in enumerate((0x118, 0x120, 0x128, 0x130, 0x138, 0x140)):
            env.put(sprite + offset, random_words[index])
        # A real one-frame animation and a real string map, run by original callees.
        frame = alloc(0x40, 'frame')
        frames = alloc(4, 'frames', words=[frame])
        env.put(animation + 0xc, frames, 1)
        env.put(frame + 0x1c, 0x456789)
        env.put(sprite + 0x18c, sprite)
        if options.get('active-animation'):
            env.put(sprite + 0x190, animation, frame)
            env.put(sprite + 0x19c, 0, 10, 1, 1, 0x11223344, 0x22334455, 0x3f800000)
        node = alloc(0x20, 'string-node')
        key = alloc(32, 'string-key', data=options.get('key', b'LS_FASTADVANCE') + b'\0')
        env.put(node, node, node, 0, key, 0x13579bdf)
        env.put(0x537668 + 0x18, node)
        env.put(0x537e88, player)
        env.put(player + 0x4c, options.get('player-x', 7), options.get('player-y', 12))
        env.put(0x52b35c, options.get('threshold', 8))
        env.put(0x541334, 1)
        env.put(0x534eac, 0x26b7)
        env.put(0x5430c4, 3)
        env.put(0x53c19c, 0x87654321)
        env.put(0x5349dc, 0x12345678)
        env.put(0x53c9ac, 0)
        # HITLOW selects a real early callback path in the original hit routine.
        names = alloc(4, 'animation-names', words=[0x523204])
        env.put(animation + 0x1c, 0)
        env.put(0x537698 + 8, 0, 0, names)
        env.put(0x537698 + 0x18, 4)
        env.put(0x5376b4, 0, 0)
        env.override(0x4a3050, sequence(99, 98, 97))

        def observe(slot, alternate_table=False):
            def effect(env, call):
                index = env.get(log)
                at = log + 4 + index * 0x400
                env.put(log, index + 1)
                current_actor = env.get(obj + 0xc)
                env.put(at, slot, int(alternate_table), call.receiver, len(call.arguments), *call.arguments)
                env.write(at + 0x20, env.read(obj, 0x180))
                env.write(at + 0x1a0, env.read(current_actor, 0x160))
                env.write(at + 0x300, env.read(sprite + 0x118, 0x60))
                if options.get('rebind') and slot == 0x24:
                    env.put(obj, alternate)
                    env.put(obj + 0xc, replacement)
                    env.put(obj + 0x40, 0x11223344, 0x55667788)
                if options.get('callback-direction') is not None:
                    env.put(obj + 0x18c, options['callback-direction'])
                return options.get('callback-result', 0xdeadbeef)
            return effect
        for table, other in ((vtable, False), (alternate, True)):
            for slot, argc in ((0x24, 0), (0x28, 1), (0x44, 0), (0x48, 0), (0x5c, 1)):
                env.put(table + slot, env.stub(f'observe-{slot:x}-{other}', 'thiscall', argc, observe(slot, other)))
        return {'obj': obj, 'arg': argument}
    return setup


def cases(random_source):
    words = tuple(random_source.getrandbits(32) for _ in range(16))
    def case(address, label, **options):
        return Case(label, address, setup_case(words, **options), receiver=lambda t: t['obj'],
                    arguments=((lambda t: t['arg']),) if address in (0x482440, 0x482460, 0x482470, 0x482480, 0x482550, 0x4827a0) else ())
    yield case(0x482430, 'reset publishes globals after original reset')

    def reset_alias(env):
        # Alias the original attachment pointer and the owned global zero within backed globals.
        obj = 0x53c19c - 0x44c
        actor = env.object(0x240, 'reset-actor', fill=0)
        attachment = env.object(0x40, 'reset-attachment', fill=0)
        env.put(attachment + 8, 0x12345678)
        env.put(obj + 0xc, actor)
        env.put(obj + 0x44c, attachment)
        env.put(0x53c9ac, 0)
        env.put(0x5349dc, 0x13579bdf)
        return {'obj':obj}

    yield Case('reset global aliases original attachment pointer', 0x482430, reset_alias, receiver=lambda t:t['obj'])
    for address in (0x482440, 0x482460):
        for direction, flip in itertools.product((1, 2, 3), (0, 2)):
            yield case(address, f'block {address:x} {direction} {flip}', direction=direction, flip=flip, key=b'LS_BLOCK')
    yield Case('null block argument', 0x482440, setup_case(words, key=b'LS_BLOCK'), receiver=lambda t:t['obj'], arguments=(0,))
    for count in (-2147483648, -1, 0, 1, 2, 3, 2147483647):
        yield case(0x482470, f'count threshold {count}', count=count)
    for hits, count in itertools.product((-2147483648, -1, 0, 1, 2, 3, 2147483646, 2147483647, 0xffffffff), (1, 2, 3)):
        yield case(0x482480, f'hit counter {hits} count {count}', hits=hits, count=count)
    for y, state in itertools.product((-float('inf'), -1., 0., 8., 8.000000000000002, float('inf'), float('nan')), (0, 1, 2, -1)):
        yield case(0x4824c0, f'y predicate {y} actor {state}', y=y, **{'actor-state':state})
    for a, b in itertools.product((-2147483648, -1, 0, 1, 2147483647), repeat=2):
        yield case(0x4824f0, f'signed player predicate {a} {b}', threshold=a, **{'player-y':b})
    for player_y, y, state in itertools.product((7, 8, 9), (7., 8., 9., float('nan')), (0, 1)):
        yield case(0x482510, f'combined predicate {player_y} {y} {state}', y=y, **{'player-y':player_y, 'actor-state':state})
    for direction, flip, speed, null in itertools.product((1, 2, 3), (0, 2), (-2147483648, -1, 0, 1, 2147483647), (False, True)):
        yield case(0x482550, f'advance {direction} {flip} {speed} {null}', direction=direction, flip=flip, speed=speed, **{'null-animation':null})
    for state, direction, flip, coordinate in itertools.product((0, 1, 2, 3, 4, 5, 6, 7, 0xffffffff), (1, 2, 3), (0, 2), ('interior', 'left', 'right', 'nan')):
        x = {'interior':5., 'left':3., 'right':9., 'nan':float('nan')}[coordinate]
        yield case(0x482620, f'tick {state} {direction} {flip} {coordinate}', state=state, direction=direction, flip=flip, x=x, key=b'LS_PACING', **{'active-animation':True})
    for state, direction, speed in itertools.product((0, 4, 6, 7), (2, 3), (-2147483648, -1, 0, 1, 2147483647)):
        yield case(0x482620, f'tick speed boundary {state} {direction} {speed}', state=state, direction=direction, speed=speed, key=b'LS_PACING')
    for action, changed in itertools.product((0, 6, 0xffffffff), (1, 2, 3)):
        yield case(0x482620, f'action callback mutates direction {action} {changed}', x=3., direction=3, state=4, action=action, **{'callback-direction':changed})
    for threshold, y in itertools.product((-2147483648, -1, 0, 1, 2147483647), (-float('inf'), -2147483648., -0., 2147483647., float('inf'), float('nan'))):
        yield case(0x4824c0, f'height signed boundary {threshold} {y}', threshold=threshold, y=y)
    for y, rebind, result in itertools.product((2089., 2090., 2090.0000000000005, float('inf'), float('nan')), (False, True), (0, 0x80004005)):
        yield case(0x4827a0, f'fall {y} rebind {rebind} result {result}', y=y, **{'rebind':rebind, 'callback-result':result})
