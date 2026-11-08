"""Original-only palette fades with observable COM and clock effects."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release

RESTORE, ADVANCE, FINISH, BLOCKING = 0x4BB8C0, 0x4BBB70, 0x4BBD20, 0x4BBD90
CLOCK, NEW, DELETE = 0x546DF0, 0x4F63EC, 0x4F6428


def scene(data, *, first=3, count=7, duration=101, elapsed=37, previous=0,
          baseline=1000, active=1, target=True, saved=True, display=False,
          effect='', status=0, get_status=0, ticks=None, alias=''):
    def setup(env):
        owner = env.object(0x38, 'palette-owner', fill=0)
        buffers = [env.object(0x440, name, data=blob) + 16
                   for name, blob in zip(('current', 'saved', 'source', 'target', 'alternate'), data)]
        current, saved_pointer, source, destination, alternate = buffers
        if alias == 'restore-forward':
            saved_pointer = current
            current += 4
        elif alias == 'restore-backward':
            saved_pointer = current + 4
        elif alias == 'source-current':
            source = current
        elif alias == 'source-overlap':
            source = current + 1
        elif alias == 'target-overlap':
            destination = current + 1
        elif alias == 'target-current':
            destination = current
        methods = env.object(0x1C, 'palette-vtable', fill=0)
        interfaces = [env.object(4, name, words=[methods]) for name in ('palette-interface', 'replacement-interface')]
        # Each slot survives return and contains call ABI, owner state and full palette.
        receipts = env.object(40 * 0x480, 'callback-receipts', fill=0)
        serial = env.object(4, 'receipt-count', fill=0)

        def record(env, call, kind):
            index = env.get(serial)
            slot = receipts + index * 0x480
            env.put(serial, index + 1)
            env.put(slot, kind, call.receiver, len(call.arguments), *call.arguments)
            env.write(slot + 0x40, env.read(owner, 0x38))
            env.write(slot + 0x80, env.read(env.get(owner + 0xC), 0x400))

        def set_entries(env, call):
            record(env, call, 2)
            if effect in ('set-state', 'all-effects'):
                env.put(owner + 0x28, 0xBADC0FFE)
                env.put(owner + 0x14, alternate)
                env.put(owner + 0x34, 7)
            if effect in ('set-buffer', 'all-effects'):
                env.put(owner + 0xC, alternate)
                env.put(owner + 4, interfaces[1])
            return status

        def get_entries(env, call):
            record(env, call, 1)
            env.write(call.arguments[4], data[2][16:1040])
            if effect in ('get-buffer', 'all-effects'):
                env.put(owner + 0xC, alternate)
                env.put(owner + 4, interfaces[1])
            return get_status

        env.put(methods + 0x10, env.stub('GetEntries', 'stdcall', 5, get_entries))
        env.put(methods + 0x18, env.stub('SetEntries', 'stdcall', 5, set_entries))
        env.put(owner + 4, interfaces[0])
        env.put(owner + 0xC, current, saved_pointer if saved else 0,
                destination if target else 0, source, 0xA7D13709,
                duration, baseline, previous, first, count, active)
        env.put(0x541374, 0)
        env.put(0x54139C, 0, 0, 1 if get_status or status else 0, 0)
        if display:
            display_methods = env.object(0x5C, 'display-vtable', fill=0)
            display_object = env.object(4, 'display-interface', words=[display_methods])
            holder = env.object(4, 'display-holder', words=[display_object])

            def display_effect(env, call):
                record(env, call, 3)
                if effect in ('display-interface', 'all-effects'):
                    env.put(owner + 4, interfaces[1])
                    env.put(owner + 0x10, alternate)
                return 0x88760001

            env.put(display_methods + 0x58, env.stub('DisplayChange', 'stdcall', 3, display_effect))
            env.put(0x541374, holder)
        schedule = ticks if ticks is not None else ((baseline + elapsed) & 0xFFFFFFFF,)

        def clock(env, call):
            record(env, call, 4)
            if effect == 'clock-fields':
                env.put(owner + 0x20, duration + 17)
                env.put(owner + 0x24, (baseline - 3) & 0xFFFFFFFF)
                env.put(owner + 4, interfaces[1])
            index = env.calls_so_far(CLOCK) - 1
            return schedule[min(index, len(schedule) - 1)] & 0xFFFFFFFF

        env.override(CLOCK, clock)
        env.override(NEW, allocate())
        env.override(DELETE, release())
        return {'owner': owner, 'target': destination}
    return setup


def cases(random_source):
    def emit(label, function, **options):
        data = tuple(bytes(random_source.randrange(1, 256) for _ in range(0x440)) for _ in range(5))
        arguments = (0xE1379,) if function == RESTORE else ()
        if function == BLOCKING:
            arguments = (options.get('first', 3), options.get('count', 7),
                         lambda t: t['target'], options.get('duration', 101))
        return Case(label, function, scene(data, **options),
                    receiver=lambda t: t['owner'], arguments=arguments)

    yield emit('restore absent saved palette', RESTORE, saved=False)
    for display in (False, True):
        yield emit(f'restore full random palette display {display}', RESTORE, display=display)
    yield emit('restore display changes interface and saved field', RESTORE,
               display=True, effect='display-interface', status=0x80004005)
    for alias in ('restore-forward', 'restore-backward'):
        yield emit('restore overlapping words ' + alias, RESTORE, alias=alias)

    yield emit('advance inactive leaves clock untouched', ADVANCE, active=0)
    yield emit('finish inactive leaves palette untouched', FINISH, active=0)
    for target in (False, True):
        for elapsed, previous in ((0, 99), (37, 37), (37, 0), (100, 0), (101, 0), (107, 0)):
            yield emit(f'advance target {target} elapsed {elapsed} previous {previous}', ADVANCE,
                       target=target, elapsed=elapsed, previous=previous)
        for first, count in ((0, 1), (0, 256), (19, 0), (19, -1), (-1, 3), (255, 1)):
            yield emit(f'advance range {first} count {count} target {target}', ADVANCE,
                       target=target, first=first, count=count)
        for duration in (0, 1, 10, 11, 0x80000000, 0xFFFFFFFF):
            yield emit(f'advance duration boundary {duration} target {target}', ADVANCE,
                       target=target, duration=duration, elapsed=0 if duration == 1 else 10,
                       previous=0xFFFFFFFF)
        yield emit(f'advance wraparound target {target}', ADVANCE, target=target,
                   baseline=0xFFFFFFF0, elapsed=47)
        yield emit(f'advance callback last elapsed overwrite target {target}', ADVANCE,
                   target=target, effect='set-state', status=0x80004005)
        yield emit(f'advance clock changes fields target {target}', ADVANCE,
                   target=target, effect='clock-fields')
        yield emit(f'finish active full target {target}', FINISH, target=target, first=0, count=256,
                   display=True)
        yield emit(f'finish callback sees cleared active target {target}', FINISH, target=target,
                   display=True, effect='all-effects', status=0x80004005)
        yield emit(f'finish empty target {target}', FINISH, target=target, count=0)
    for alias in ('source-current', 'source-overlap', 'target-overlap', 'target-current'):
        yield emit('advance alias ' + alias, ADVANCE, alias=alias, first=0, count=11)
    for i in range(12):
        duration = random_source.randrange(12, 100000)
        first = random_source.randrange(0, 220)
        yield emit(f'random advance {i}', ADVANCE, first=first,
                   count=random_source.randrange(1, 257 - first), duration=duration,
                   elapsed=random_source.randrange(1, duration), target=bool(i % 2))

    for duration in (0, 1, 10, 11, 101, 0x80000000, 0xFFFFFFFF):
        ticks = (1000, 1010, 1010, 1037, (1000 + duration) & 0xFFFFFFFF)
        yield emit(f'blocking duration {duration}', BLOCKING, duration=duration, ticks=ticks)
    for first, count in ((0, 1), (0, 256), (7, 0), (7, -1), (255, 1)):
        yield emit(f'blocking range {first} count {count}', BLOCKING, first=first, count=count,
                   ticks=(1000, 1010, 1010, 1037, 1101))
    yield emit('blocking baseline wrap and repeated ticks', BLOCKING, baseline=0xFFFFFFF0,
               ticks=(0xFFFFFFF0, 0xFFFFFFFA, 0xFFFFFFFA, 0x15, 0x55), display=True)
    for effect in ('get-buffer', 'set-buffer', 'all-effects'):
        yield emit('blocking callback changes ' + effect, BLOCKING, effect=effect, display=True,
                   get_status=0x80004005, status=0x887601C2,
                   ticks=(1000, 1010, 1010, 1037, 1101))
    yield emit('blocking source target alias', BLOCKING, alias='target-current',
               ticks=(1000, 1037, 1101))
