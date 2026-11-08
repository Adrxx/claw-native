"""Original-backed Mercat helper inputs and callback observations."""
import struct
from dataclasses import replace
from clawparity.cases import Case
from clawparity.fixtures import sequence, returns


def animation(env, name):
    anim = env.object(0x30, name, fill=0)
    cmd = env.object(0x40, name+'-command', fill=0)
    cmds = env.object(4, name+'-commands', words=[cmd])
    env.put(anim+0xc, cmds, 1)
    env.put(cmd+0xc, 9)
    env.put(cmd+0x18, 100)
    return anim


def base(**options):
    def setup(env):
        obj = env.object(0x4e0, 'mercat', fill=0)
        world = env.object(0x220, 'sprite', fill=0)
        record = env.object(0x200, 'logic-record', fill=0)
        player = env.object(0x220, 'player', fill=0)
        state = env.object(0x100, 'player-state', fill=0)
        mode = env.object(0x100, 'player-mode', fill=0)
        manager = env.object(0x80, 'resources', fill=0)
        vtable = env.object(0x80, 'mercat-methods', fill=0)
        observation = env.object(0x80, 'callback-observations', fill=0)
        def callback(e, call):
            n = e.get(observation)
            e.put(observation, n + 1)
            e.put(observation + 4 + n * 8, call.receiver, call.arguments[0] if call.arguments else 0)
            return 0x52
        for off in (0x28, 0x44):
            env.put(vtable + off, env.stub('mercat-base-method', 'thiscall', 1 if off == 0x28 else 0, callback))
        env.put(obj, vtable)
        env.put(obj + 0x0c, world, record)
        env.put(obj + 0x128, world, world)
        env.put(world + 0x0c, manager)
        env.put(world + 0x38, 0xffffffff)
        resource = env.object(0x60, 'empty-resource-map', fill=0)
        env.put(resource + 0x18, 1)
        for off in (0x10, 0x14, 0x28, 0x2c):
            env.put(manager + off, resource)
        collision = env.object(0x100, 'collision-map', fill=0)
        env.put(collision+0x64, 0xffffffff, 0xffffffff)
        env.put(manager+0x24, collision)
        strings = env.object(400, 'state-name-table', fill=0)
        for i in range(100):
            env.put(strings + i * 4, 0x523204)
        env.put(0x5376a0, 0, 99, strings)
        env.put(0x5376b0, 4)
        env.put(world + 0x6c, record)
        env.put(world + 0x18c, world)
        env.put(obj + 0x50, 0x11223344, 0x66778899)
        env.put(obj + 0x24, 0xdeadbeef)
        env.put(obj + 0x134, 0x76543210)
        env.put(world + 0x190, 0x42)
        for off in range(0x484, 0x4b9, 4):
            env.put(obj + off, 0x1000 + off)
        env.put(world + 0x118, options.get('bounds', 17), 23, 41)
        env.put(world + 0x128, 13, 19, 37)
        env.put(world + 0x138, 29, 31, 47)
        env.put(obj + 0x138, 11, 13, 37)
        env.put(obj + 0x184, options.get('action', 3))
        env.put(obj + 0x18c, options.get('facing', 2))
        env.put(world + 0x40, options.get('flip', 0))
        env.put(world + 8, 0x10)
        platform = env.object(0x220, 'platform', fill=0)
        env.put(world + 0x80, platform)
        env.put(platform + 0x164, 0x8000)
        platform_record = env.object(0x100, 'platform-record', fill=0)
        env.put(platform + 0x6c, platform_record)
        env.put(platform_record + 0x1c, 5)
        env.put(obj + 0x20, options.get('count', 2))
        env.put(obj + 0x49c, options.get('then', 100))
        env.put(obj + 0x4a0, options.get('delay', 500))
        env.put(obj + 0x4d8, options.get('chance', 90))
        env.put(obj + 0x2fc, 32, 0)
        if options.get('large_bits', False):
            bits = env.object(8, 'external-bits', words=[0x1234,0x5678])
            env.put(obj+0x2fc, 64, bits)
        env.put(record + 0x1c, 41)
        env.put(player + 0x6c, state)
        env.put(state + 0x14, mode)
        env.put(mode, options.get('direction', 0), options.get('enabled', 1))
        env.put(mode + 0x3c, options.get('weapon', 1))
        env.put(player + 0xcc, options.get('player_action', 5))
        env.put(player + 0x4c, options.get('player_x', 100))
        env.put(0x537e88, player)
        env.put(0x537210, options.get('now', 700))
        env.put(0x537964, options.get('level', 11))
        env.put(0x541334, 1)
        env.put(0x534eac, 0x26b7)
        env.put(0x544d18, 0)
        env.put(0x537680, 0)
        env.put(0x5376b8, 0)
        env.put(0x532c0c, options.get('sound_enabled', 0))
        env.put(0x532c10, 1234)
        # A valid sound object can take the original service's disabled-device exit.
        sound = env.object(0x30, 'sound', fill=0)
        device = env.object(0x100, 'sound-device', fill=0)
        env.put(sound + 0x10, device)
        env.put(device + 0x10, device)
        env.put(obj + 0x47c, sound if options.get('sound', False) else 0, sound if options.get('sound', False) else 0)
        if options.get('rich',False):
            for off in (0x344,0x340,0x4bc):
                env.put(obj+off, animation(env,'animation-'+str(off)))
            env.put(obj+0x468, sound, sound, sound, sound)
            channel = env.object(0x200,'effect-channel', fill=0)
            channel_state = env.object(0x80,'effect-channel-state', fill=0)
            env.put(channel+0x6c, channel_state)
            env.put(0x53c9ac, channel)
            env.put(0x53c9a8, 0)
        env.override(0x4a3050, sequence(*options.get('random', (0, 1, 2, 3, 4, 5, 6, 7))))
        # String destructors recognize the shared empty buffer.
        env.put(obj + 0x1a4, env.get(0x52e1c8) + 12, env.get(0x52e1c8) + 12)
        return dict(obj=obj, world=world, record=record, player=player, mode=mode, observation=observation)
    return setup


def case(label, address, options=None, argument=None):
    return Case(label, address, base(**(options or {})), receiver=lambda t:t['obj'], arguments=() if argument is None else (argument,))


def dispatch_setup(argument, present, grow=False, fail=False):
    def setup(env):
        t = base()(env)
        table = env.object(12, 'mercat-dispatch', fill=0)
        fallback = env.object(64, 'base-dispatch', fill=0)
        def callback(e, call):
            e.put(t['observation'], call.receiver, e.get(0x537b88), argument)
            return 77
        stub = env.stub('dispatch-state', 'thiscall', 0, callback)
        env.put(table + (argument-1)*4, stub) if present else None
        env.put(0x537b70, 1, 3, table, table, 4)
        env.put(0x537b88, 0x12345678)
        env.put(0x537880, -4, 9, fallback, fallback, 4)
        for i in range(14):
            env.put(fallback + i * 4, stub)
        if fail:
            env.override(0x4a9070, returns(0))
        return t
    return setup


def constructor_setup(hit, level, scaling, roll):
    def setup(env):
        t = base(level=level, random=(roll,))(env)
        env.put(0x5430c4, 1)
        env.put(t['obj']+0x4d8, 0x12345)
        env.write(0x5262b8, struct.pack('<f', scaling))
        env.write(0x5262b4, struct.pack('<f', scaling+0.125))
        env.write(0x5262b0, struct.pack('<f', scaling+0.25))
        def rect(e, call):
            e.put(call.arguments[0], *call.arguments[1:])
            return 1
        def empty(e, call):
            e.put(call.arguments[0], 0,0,0,0)
            return 1
        env.override(0x546d5c, rect)
        env.override(0x546cdc, empty)
        if hit:
            manager = env.get(t['world']+0xc)
            names = ('ADVANCE','FASTADVANCE','HITHIGH','HITLOW','IDLE1','IDLE2','IDLE3','IDLE4','JUMP','KILLFALL','LIFTED1','LIFTED2','STRIKE1','THROWN','HOME','BLOCK')
            def mapping(offset, values):
                resource = env.object(0x60, 'resource-map-'+str(offset), fill=0)
                env.put(resource+0x18,1)
                bucket = env.object(4,'resource-bucket',fill=0)
                env.put(resource+0x14,bucket)
                head = 0
                for name,value in values:
                    key = env.object(len(name)+1,'resource-key',data=name.encode()+b'\0')
                    node = env.object(16,'resource-node',words=[head,0,key,value])
                    head=node
                env.put(bucket,head)
                env.put(manager+offset,resource)
            mapping(0x2c, [('LEVEL_MERCAT_'+name,animation(env,name)) for name in names])
            sound_names = ('TLIGHTNING','00440000','00440001','00440002','00440003','00440004','00440009','00440007','00440012','00440013','BLOCK1','BLOCK2','00440006','STAB','00440014','00440015')
            mapping(0x28, [('LEVEL_MERCAT_'+name,env.object(0x30,name+'-sound',fill=0)) for name in sound_names])
            sprite = env.object(0x80,'sprite-image-set',fill=0)
            frame = env.object(0x40,'sprite-frame',fill=0)
            frames = env.object(4,'sprite-frame-list',words=[frame])
            env.put(sprite+0x14,frames)
            env.put(sprite+0x64,0,0)
            env.put(frame+0x18,11,17,53,67)
            mapping(0x10,[('LEVEL_MERCAT',sprite)])
        return t
    return setup


def destructor_setup(shared=False):
    def setup(env):
        t=base(large_bits=True)(env)
        payloads=[]
        for index in range(2):
            header=env.object(32,'cstring-'+str(index),fill=0x61+index)
            env.put(header, 2 if shared else 1, 5+index, 19)
            payloads.append(header+12)
        env.put(t['obj']+0x1a4,*payloads)
        def decrement(e,call):
            pointer=call.arguments[0]
            count=(e.get(pointer)-1)&0xffffffff
            e.put(pointer,count)
            return count
        env.override(0x5469e8,decrement)
        return t
    return setup


def baseline_cases(random_source):
    for shared in (False,True):
        for address in (0x460640,0x460620):
            yield Case(f'destroy cstrings {address:x} {shared}',address,destructor_setup(shared),receiver=lambda t:t['obj'],arguments=(1,) if address==0x460620 else ())

    for argument,present in ((1,True),(2,True),(3,True),(1,False),(0,False),(4,False),(-2,False)):
        yield Case(f'dispatch {argument} {present}',0x460710,dispatch_setup(argument,present),receiver=lambda t:t['obj'],arguments=(argument,))
    for hit in (False,True):
        for level in (11,12):
            for scaling in (0.5, 3.0):
                for roll in (49,50):
                    yield Case(f'constructor {hit} {level} {scaling} {roll}',0x45ffc0,constructor_setup(hit,level,scaling,roll),receiver=lambda t:t['obj'],arguments=(lambda t:t['world'],))

    for address in (0x460640,0x460620):
        yield case(f'destroy external bits {address:x}',address,dict(large_bits=True),argument=0 if address==0x460620 else None)
    for address in (0x460bf0,0x460e20,0x461020,0x461170):
        yield case(f'rich original state {address:x}',address,dict(rich=True,level=10,weapon=0,random=(25,1,0,0,0,0)),argument=(lambda t:t['world']) if address in (0x461020,0x461170) else None)
    for address in (0x460640, 0x460620):
        for flag in (0, 1, 2, 3, 0xff, 0x100):
            yield case(f'destroy {address:x} {flag}', address, argument=flag if address==0x460620 else None)
    for address in (0x460bf0, 0x460e20, 0x4612c0):
        for rand in (0, 1, 1000, 1001, 0x7fffffff, 0xffffffff):
            for sound, enabled in ((False,0),(True,0),(True,1)):
                yield case(f'state {address:x} {rand} {sound} {enabled}', address, dict(random=(rand,), sound=sound, sound_enabled=enabled, now=random_source.randrange(0x100000)))
    for level, roll in ((11,0),(11,24),(11,25),(12,49),(12,50),(10,0),(12,0xffffffff)):
        for facing, flip in ((2,0),(2,2),(3,0),(3,2)):
            for bounds in (17,0x80000000):
                yield case(f'high {level} {roll} {facing} {flip} {bounds}',0x461020,dict(level=level,random=(roll,1,0,0,0,0),facing=facing,flip=flip,bounds=bounds),argument=lambda t:t['world'])
    for weapon, action in ((1,5),(2,5),(7,5),(8,5),(0,5),(3,5),(9,5),(1,4)):
        for facing,flip in ((2,0),(2,2),(3,0),(3,2)):
            for bounds in (17,0x80000000):
                yield case(f'low {weapon} {action} {facing} {flip} {bounds}',0x461170,dict(weapon=weapon,player_action=action,facing=facing,flip=flip,bounds=bounds),argument=lambda t:t['world'])
    for enabled,direction,player_x,action,delay,chance,roll,count in (
        (0,0,100,3,500,90,0,2),(1,0,100,3,500,90,0,2),
        (1,1,100,3,500,90,0,2),(1,1,-100,3,500,90,0,2),
        (1,0,-100,4,500,90,0,2),(1,0,100,6,500,90,0,2),
        (1,0,100,3,601,90,0,2),(1,0,100,3,600,90,90,2),
        (1,0,100,3,600,90,89,2),(1,0,100,4,600,20,0,1),
        (1,0,100,4,600,30,0,0),(1,0,100,4,600,31,0,3)):
        yield case(f'tick {enabled} {direction} {player_x} {action} {delay} {chance} {roll} {count}',0x460af0,dict(enabled=enabled,direction=direction,player_x=player_x,action=action,delay=delay,chance=chance,random=(roll,1),count=count),argument=0x523148)



def with_status(setup, status):
    """Elect masked inherited exception flags before the case image is frozen."""
    def prepare(env):
        tokens = setup(env)
        env.entry_x87_status(status)
        return tokens
    return prepare


def constructor_factors(bits, level):
    def setup(env):
        tokens = constructor_setup(True, level, 1.0, 49)(env)
        for address, value in zip((0x5262b8, 0x5262b4, 0x5262b0), bits):
            env.put(address, value)
        return tokens
    return setup


def motion_position(position, player_x):
    def setup(env):
        tokens = base(enabled=0, player_x=player_x)(env)
        env.write(tokens['obj'] + 0x68, struct.pack('<d', position))
        return tokens
    return setup


def real_dispatch(target):
    def setup(env):
        tokens = base(rich=True, sound=True, random=(1, 0, 1, 0))(env)
        table = env.object(12, 'real-mercat-dispatch', words=[0, target, 0])
        env.put(0x537b70, 1, 3, table, table, 4)
        env.put(0x537b88, 0x13579bdf)
        env.put(tokens['obj'] + 0x384, animation(env, 'block-dispatch-animation'))
        env.put(0x5430c4, 1)
        return tokens
    return setup



def registered_dispatch(target):
    def setup(env):
        tokens = base(rich=True, action=7, random=(1, 0, 1, 0))(env)
        table = env.object(12, 'registered-mercat-dispatch', words=[0, target, 0])
        env.put(0x537b70, 1, 3, table, table, 4)
        env.put(0x537b88, 0x2468ace0)
        current = animation(env, 'registered-state-animation')
        command = env.get(env.get(current + 0xc))
        world = tokens['world']
        # The original animation runner owns these fields. A live command with
        # a nonunit scale forces its inherited FILD/FMUL/conversion path.
        env.put(world + 0x190, current, command, 0, 0, 1, 0, 0, 0, 0x3f000001)
        env.put(0x5430c4, 1)
        env.put(tokens['obj'] + 0x4a4, 700, 1000)
        env.put(tokens['obj'] + 0x4dc, 0)
        if target == 0x460ea0:
            # Expire the idle-selection timer and bind every genuine choice.
            # The original animation setter resets its own timing scale.
            env.put(tokens['obj'] + 0x4a4, 0, 0)
            env.put(tokens['obj'] + 0x4bc, current, current, current, current)
        return tokens
    return setup


def cases(random_source):
    # Retain every established branch case, then repeat it with one of two
    # independent incoming sticky-flag profiles. All ten owners get both
    # profiles and direct original calls, independent of the random seed.
    counts = {}
    for baseline in baseline_cases(random_source):
        yield baseline
        count = counts.get(baseline.function, 0)
        status = (0x20, 0x21)[count % 2]
        counts[baseline.function] = count + 1
        yield replace(baseline, label=baseline.label + f' inherited SW {status:#x}',
                      setup=with_status(baseline.setup, status))

    # Three independent source factors distinguish each original FLD/FILD and
    # FMUL. Adjacent binary32 inputs straddle the unsigned 99/100 clamp and
    # integer conversion boundaries; signed zero, tiny and large finite values
    # expose exception/status handling without substituting a game callback.
    factors = (
        (0x3fffffff, 0x3f800001, 0x3f000001),
        (0x40000000, 0x3f7fffff, 0x3effffff),
        (0x40000001, 0x3eaaaaab, 0x3dcccccd),
        (0x00000000, 0x80000000, 0x00000000),
        (0x80000000, 0xbf800001, 0xbeaaaaab),
        (0x00000001, 0x007fffff, 0x00800000),
        (0x7f7fffff, 0x4f000000, 0xcf000000),
        (0xbf800000, 0x3f400000, 0x3f19999a),
    )
    for index, bits in enumerate(factors):
        for status in (0, 0x20, 0x21):
            yield Case(f'exact constructor factors {index} SW {status:#x}', 0x45ffc0,
                       with_status(constructor_factors(bits, 11 + index % 2), status),
                       receiver=lambda t:t['obj'], arguments=(lambda t:t['world'],))

    # The exact inherited base update compares the player's signed integer x
    # against this binary64 x twice. Equal, ordered and unordered inputs produce
    # distinct condition codes while preserving incoming exception flags.
    for position, player_x in ((0.0, 0), (-0.0, 0), (99.5, 100), (100.5, 100),
                               (-100.5, -100), (2147483647.5, 0x7fffffff),
                               (-2147483648.5, -0x80000000), (float('nan'), 17)):
        for status in (0, 0x20, 0x21):
            yield Case(f'inherited update compare {position} {player_x} SW {status:#x}',
                       0x460af0, with_status(motion_position(position, player_x), status),
                       receiver=lambda t:t['obj'], arguments=(0x523148,))

    # Run genuine same-family lifecycle targets through the original state
    # dispatcher, including idle's original animation timer arithmetic.
    for target in (0x460bf0, 0x460e20, 0x4612c0):
        for status in (0, 0x20, 0x21):
            yield Case(f'real lifecycle dispatch {target:x} SW {status:#x}', 0x460710,
                       with_status(real_dispatch(target), status),
                       receiver=lambda t:t['obj'], arguments=(2,))


    # These four targets are the original Mercat initializer's registered
    # callbacks, rather than synthetic callbacks or direct helper stand-ins.
    for target in (0x460ea0, 0x460c50, 0x4614c0, 0x483dc0):
        for status in (0, 0x20, 0x21):
            yield Case(f'registered lifecycle dispatch {target:x} SW {status:#x}',
                       0x460710, with_status(registered_dispatch(target), status),
                       receiver=lambda t:t['obj'], arguments=(2,))
