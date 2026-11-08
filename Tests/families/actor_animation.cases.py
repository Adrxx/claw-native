"""Original-only animation cases, including raw record and image leaves."""
from clawparity.cases import Case

SEEK, SET, NAMED, ACTION = 0x420970, 0x420a10, 0x4c79e0, 0x4c7a40
CLEAR, SELECT, RESET, UPDATE = 0x4c8210, 0x4c8220, 0x4c8260, 0x4c82a0
RECORD, LAST = 0x4c87f0, 0x4c8810


def scene(**options):
    def setup(env):
        def obj(size, name):
            return env.object(size, name, fill=0xa7)
        actor = obj(0x1c0, 'actor')
        state = actor + 0x188
        if options.get('sequence_alias'):
            state = actor + 0x44  # absolute motion x overwrites state.sequence
        records = [obj(0x30, 'record%d' % i) for i in range(3)]
        seq = obj(0x18, 'sequence')
        table = obj(16, 'record-table')
        tokens = [records[i] if i not in options.get('holes', ()) else 0 for i in range(3)]
        env.put(table, *tokens, 0xfeed4321)
        if options.get('raw_token') is not None:
            env.put(table + 4, options['raw_token'])
        env.put(seq + 0xc, table, options.get('count', 3))
        images = obj(0x100, 'images') + 0x40
        for i in range(-16, 32):
            env.put(images + i * 4, (0x63124500 + i * 17) & 0xffffffff)
        for i in options.get('image_holes', ()):
            env.put(images + i * 4, 0)
        manager = obj(0x70, 'image-manager')
        env.put(manager + 0x14, images)
        env.put(manager + 0x64, options.get('minimum', -3), options.get('maximum', 5))
        env.put(actor + 0x10, 0x1532da87, 0x39dd52c1)
        env.put(actor + 0x40, options.get('orientation', 0x91))
        env.put(actor + 0x4c, options.get('x', 0x7ffffffd), options.get('y', 0xfffffffb))
        env.put(actor + 0x16c, options.get('image_id', 1), 0 if options.get('no_manager') else manager, 0xa1b2c3d4)
        env.put(actor + 0x184, 0x8a7b6c5d)
        env.put(state, 0x01abc234, actor, 0 if options.get('no_sequence') else seq,
                records[0], options.get('index', 0), options.get('delay', 0),
                options.get('timed', 1), options.get('stopped', 0),
                0x11223344, 0x55667788, options.get('speed', 0x3f800000))
        for i, rec in enumerate(records):
            env.put(rec + 4, options.get('flags', 0), options.get('image', 0),
                    options.get('control', 6), options.get('motion', 0),
                    options.get('operand', 2), options.get('duration', 13), 0x23456781 + i * 0x10103,
                    options.get('dx', 7), options.get('dy', 0xfffffff5), 0x9a8b7c6d,
                    obj(0x10, 'sound') if options.get('sound') else 0)
        if options.get('sequence_alias'):
            env.put(records[0] + 0x20, 0, records[1])  # x clears sequence; y changes record
        alias = options.get('manager_alias')
        if alias:
            manager = actor + alias
            env.put(manager + 0x14, images)
            env.put(manager + 0x64, options.get('minimum', -3), options.get('maximum', 5))
            env.put(actor + 0x170, manager)
            if alias == 0x108:
                # max aliases actor.manager, so raw ID equals manager's address.
                env.put(manager + 0x14, (images - manager * 4) & 0xffffffff)
        if options.get('record_alias'):
            # Record.result aliases delay, cleared before the original reload.
            env.put(table, state - 8)
        env.put(0x532c0c, 0)
        env.put(0x532c10, 0x5a67b8c9)
        env.put(0x5430c4, options.get('delta', 17))
        env.put(0x540e00, 0)
        name = env.object(16, 'query', data=b'run-fast\0')
        container = obj(0x30, 'resource-container')
        resource = obj(0x20, 'resource-manager')
        buckets = env.object(4, 'one-hash-bucket', fill=0)
        env.put(resource + 0x14, buckets, 1)
        env.put(container + 0x28, resource, resource)
        env.put(actor + 0xc, container)
        if options.get('lookup', 'found') != 'empty':
            node = obj(16, 'found-node')
            env.put(node, 0, 0x13579246, name,
                    0 if options.get('lookup') == 'zero' else seq)
            wrongkey = env.object(16, 'collision-key', data=b'run-slow\0')
            head = obj(16, 'collision-node')
            env.put(head, node, 0x5a1b2c3d, wrongkey, 0x76543210)
            env.put(buckets, head)
        if options.get('lookup') == 'missing':
            env.write(name, b'run-lost\0')
            # Keep the found node key distinct from the query allocation.
            key = env.object(16, 'actual-key', data=b'run-fast\0')
            env.put(node + 8, key)
        return dict(actor=actor, state=state, seq=seq, name=name, records=records)
    return setup


def case(label, function, arguments=(), **options):
    receiver = 'actor' if function in (SET, NAMED, ACTION, LAST) else 'seq' if function == RECORD else 'state'
    return Case(label, function, scene(**options), receiver=lambda t: t[receiver], arguments=arguments)


def cases(random_source):
    yield case('clear exact three fields preserves surrounding sentinels', CLEAR)
    yield case('select null preserves old current record and state', SELECT, (0,))
    yield case('select first distinct record', SELECT, (lambda t: t['seq'],), delay=91, stopped=3, speed=0xbf400000)
    for no_sequence in (False, True):
        for clear_delay in (0, 1, 0x80000000):
            yield case('reset sequence=%s clear=%x' % (not no_sequence, clear_delay), RESET,
                       (clear_delay,), no_sequence=no_sequence, delay=0x81234567, stopped=5, speed=0x40200000)
    for count in (-1, 0, 1, 3, 0x80000000):
        for index in (-0x80000000, -1, 0, 1, 2, 3, 0x7fffffff):
            yield case('raw record count=%x index=%x' % (count & 0xffffffff, index & 0xffffffff), RECORD,
                       (index,), count=count, holes=(1,))
            yield case('seek count=%x index=%x' % (count & 0xffffffff, index & 0xffffffff), SEEK,
                       (index,), count=count, holes=(1,), delay=95, stopped=9)
    yield case('seek null first fallback preserves results', SEEK, (2,), holes=(0, 2))
    for function in (SELECT, RESET, SEEK):
        arg = (lambda t: t['seq']) if function == SELECT else 1 if function == RESET else 0
        yield case('record result aliases delay during entry %x' % function, function, (arg,),
                   record_alias=True, delay=0x81726354, stopped=7)
    for raw in (0x89abcdef, 0xffffffff, 1):
        yield case('raw record token %x is not dereferenced' % raw, RECORD, (1,), raw_token=raw)
    yield case('last image null manager preserves all actor fields', LAST, no_manager=True)
    for minimum, maximum in ((-3, 5), (-7, -2), (6, 5), (0, 0), (-0x80000000, -2), (0x7fffffff, -1)):
        yield case('last image signed bounds %d..%d' % (minimum, maximum), LAST, minimum=minimum, maximum=maximum)
    yield case('last image raw null table word', LAST, image_holes=(5,))
    yield case('last image write changes unaligned upper bound before reread', LAST,
               manager_alias=0x101, minimum=-100, maximum=0x02000001)
    yield case('last image write changes lower bound before signed check', LAST,
               manager_alias=0x108, minimum=-100, maximum=5)
    for function in (SET, NAMED):
        for update in (0, 1, 0x80000000):
            args = (lambda t: t['seq' if function == SET else 'name'], update)
            yield case('wrapper %x update=%x' % (function, update), function, args, image=6, operand=99, motion=2, control=0)
    yield case('set null sequence with update returns safely', SET, (0, 1))
    for lookup in ('found', 'zero', 'missing', 'empty'):
        yield case('named sequence lookup %s' % lookup, NAMED, (lambda t: t['name'], 1), lookup=lookup)
        yield case('named action lookup %s' % lookup, ACTION, (lambda t: t['name'],), lookup=lookup)
    yield case('update no sequence', UPDATE, (17,), no_sequence=True)
    for delay, timed, delta, stopped in ((1, 0, 999, 0), (0xffffffff, 0, 0, 0), (17, 1, 0, 0),
                                       (0xffffffff, 1, 0x80000000, 0), (17, 7, 17, 0),
                                       (17, 1, 18, 0), (0, 1, 99, 7), (1, 1, 1, 9)):
        yield case('delay %x timed %x delta %x stopped %x' % (delay, timed, delta, stopped),
                   UPDATE, (delta,), delay=delay, timed=timed, stopped=stopped)
    for image in range(1, 8):
        for image_id, operand in ((1, 2), (-3, 100), (5, 0xffffffff)):
            yield case('image command %d id %d operand %x' % (image, image_id, operand), UPDATE,
                       (17,), image=image, image_id=image_id, operand=operand)
        yield case('image command %d null manager' % image, UPDATE, (17,), image=image, no_manager=True)
        yield case('image command %d null lookup fallback' % image, UPDATE, (17,), image=image,
                   image_holes=(-3, -1, 0, 1, 2, 3, 5), image_id=1, operand=2)
    for motion in (0, 1, 2, 3, 4, 0xffffffff):
        for orientation in (0x91, 0x92):
            yield case('motion %x orientation %x' % (motion, orientation), UPDATE, (17,),
                       motion=motion, orientation=orientation)
    for flags in (0, 1, 4, 5, 0xfffffffa):
        for sound in (False, True):
            yield case('flags %x sound %s' % (flags, sound), UPDATE, (17,), flags=flags, sound=sound)
    for speed in (0, 0x3f000000, 0xbf400000, 0x3f800001, 0x40200000):
        for duration in (0, 1, 17, 0x80000001, 0xffffffff):
            yield case('scale %x unsigned duration %x' % (speed, duration), UPDATE, (17,), speed=speed, duration=duration)
    for control in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0xffff, 0x10000, 0x10001, 0x10009):
        for mode in ('advance', 'mismatch', 'wrap', 'negative', 'empty', 'null'):
            if control == 8 and mode in ('empty', 'null'):
                continue  # Original unconditionally reads the reset record.
            image_id = {1: 2, 2: -3, 3: 5, 4: -2, 5: 4}.get(control & 0xffff, 1)
            if mode == 'mismatch':
                image_id = 99
            yield case('control %x %s' % (control, mode), UPDATE, (17,), control=control,
                       image_id=image_id, index=2 if mode == 'wrap' else 0x7fffffff if mode == 'negative' else 0,
                       count=0 if mode == 'empty' else 3,
                       holes=(0, 1, 2) if mode == 'null' else (), duration=0 if mode == 'negative' else 13)
    yield case('control8 sequence reloaded after absolute x alias clears it', UPDATE, (17,),
               sequence_alias=True, motion=3, control=8)
    for _ in range(24):
        image = random_source.randrange(0, 8)
        control = random_source.choice((0, 1, 2, 3, 4, 5, 6, 7, 9, 0x10006))
        duration = random_source.getrandbits(32)
        yield case('random original animation %d %x %x' % (image, control, duration), UPDATE,
                   (random_source.getrandbits(32),), image=image, control=control, duration=duration,
                   motion=random_source.randrange(0, 5), orientation=random_source.getrandbits(8),
                   image_id=random_source.randrange(-3, 6), operand=random_source.getrandbits(32),
                   dx=random_source.getrandbits(32), dy=random_source.getrandbits(32))
