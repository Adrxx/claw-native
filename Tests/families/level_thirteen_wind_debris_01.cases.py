"""Original-derived wind-debris cases: resource maps, state dispatch and timing."""
import struct
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.fixtures import returns

FACTORY, DISPATCH, CONSTRUCT, START, TICK = 0x49F0A0, 0x49F1C0, 0x49F470, 0x49F770, 0x49F7E0


def put_double(env, address, value):
    env.write(address, struct.pack('<d', value))


def resource_map(env, entries, label):
    owner = env.object(0x40, label, fill=0)
    bucket = env.object(4, label + ' bucket', fill=0)
    env.put(owner + 0x14, bucket, 1)
    head = 0
    for key, value in entries:
        text = env.object(len(key) + 1, label + ' key', data=key.encode() + b'\0')
        node = env.object(16, label + ' node', words=[head, 0, text, value])
        head = node
    env.put(bucket, head)
    return owner


def base(env, marker=0x13579BDF, image=True, ranges=(0, 0, 0, 0), rand_value=0):
    actor = env.object(0x1B0, 'physical debris object', fill=0)
    config = env.object(0x140, 'debris configuration', fill=0)
    world = env.object(0x90, 'world resources', fill=0)
    collision = env.object(0x80, 'collision world', fill=0)
    frame = env.object(0x30, 'image frame', fill=0)
    env.put(frame + 0x18, 3, 5, 19, 29)
    frame_words = env.object(4, 'frame pointers', words=[frame])
    asset = env.object(0x70, 'image asset', fill=0)
    env.put(asset + 0x14, frame_words)
    env.put(asset + 0x64, 0, 0)
    images = resource_map(env, [(key, asset) for key in ('LEVEL_WINDGRASS', 'LEVEL_WINDLEAF', 'LEVEL_WINDSAND')] if image else [], 'images')
    empty = resource_map(env, [], 'empty resources')
    env.put(world + 0x10, images, empty)
    env.put(world + 0x24, collision)
    env.put(world + 0x2C, empty)
    env.put(actor + 0x0C, world)
    env.put(actor + 0x6C, config)
    env.put(actor + 0x4C, 41, 63)
    env.put(actor + 0x148, 2, 4)
    env.put(actor + 0x164, marker)
    env.put(actor + 0x190, marker ^ 0x33333333)
    env.put(config + 0x1C, 71)
    for offset, value in zip((0x2C, 0x34, 0x30, 0x38), ranges):
        env.put(config + offset, value & 0xFFFFFFFF)
    env.put(0x537210, marker)
    env.put(0x5430C4, 17)
    # The original trie has no ES_MOVING entry; its real lookup returns zero.
    env.put(0x537680, 0)
    env.override(0x4A3050, returns(rand_value & 0xFFFFFFFF))
    log = env.object(64, 'callback observations', fill=0)
    return dict(actor=actor, config=config, world=world, frame=frame, asset=asset, log=log)


def ordinary(label, function, setup, arguments=()):
    return Case(label, function, setup, receiver=lambda t: t['receiver'], arguments=arguments)


def constructor_setup(marker, ranges, rand_value, image):
    def setup(env):
        t = base(env, marker, image, ranges, rand_value)
        t['receiver'] = env.object(0x1B0, 'wind-debris receiver', fill=0xA5)
        return t
    return setup


def dispatch_setup(index, low, high, stride, present, growth=False, marker=0x79ABCDE0):
    def setup(env):
        receiver = env.object(0x1B0, 'dispatch receiver', fill=0xA6)
        log = env.object(64, 'dispatch observations', fill=0)
        rtti = env.object(16, 'RTTI locator', fill=0)
        typeinfo = env.object(16, 'type information', fill=0x53)
        env.put(rtti + 0xC, typeinfo)
        vtable = env.object(12, 'RTTI vtable', words=[rtti, 0, 0])
        env.put(receiver, vtable + 4)
        def callback(env, call):
            env.put(log, call.receiver, env.get(0x53EC08), env.get(0x53EC0C), env.get(0x53EC10), env.get(0x53EC20))
            env.put(call.receiver + 0x164, marker)
            return marker ^ 0x43434343
        cb = env.stub('debris state callback', 'thiscall', 0, callback)
        table = env.object((high-low+1)*stride, 'callback table', fill=0)
        for i in range(high-low+1):
            env.put(table+i*stride, cb if present else 0)
        error = env.object(24, 'registry error sink', fill=0)
        env.put(error + 0xC, 4)
        fallback = env.object(4, 'fallback callback', words=[cb if present else 0])
        env.put(0x53EC04, error, low & 0xFFFFFFFF, high & 0xFFFFFFFF, table, fallback, stride, 0, marker)
        env.put(0x544B4C, 0x533428)
        context = NativeSourceContext(72, 1, 0x7FF, 0x5F3)
        context.eax, context.ebx, context.ecx, context.edx = marker, marker ^ 1, receiver, marker ^ 2
        context.esi, context.edi, context.ebp = marker ^ 3, marker ^ 4, marker ^ 5
        context.esp, context.eip, context.eflags, context.fsHead = 0x02008000, DISPATCH, 2, 0xFFFFFFFF
        context.preserveMask = 0x472
        env.put(context.esp, 0x49F13E, index & 0xFFFFFFFF)
        return dict(receiver=receiver, source=context)
    return setup


def cases(random_source):
    # Distinct defaults and object words expose missing or misaddressed stores.
    for n in range(36):
        marker = random_source.randrange(1, 0xFFFFFFFF)
        receiver_bytes = bytes(random_source.randrange(1, 256) for _ in range(0x1B0))
        defaults = ((-37.12345, 93.62345), (1.0 / 3.0, -1.0 / 7.0), (0.000123, 987654.37567))[n % 3]
        ranges = ((0, 0, 0, 0), (0, -19, 73, 0), (-31, 0, 0, 47), (2147483647, -2147483648, 123, -456))[n % 4]
        rand_value = (0, 1, 2, -1, -2, -3)[n % 6]
        def setup(env, n=n, marker=marker, receiver_bytes=receiver_bytes, defaults=defaults, ranges=ranges, rand_value=rand_value):
            t=base(env, marker, True, ranges, rand_value)
            receiver=env.object(0x1B0, 'distinct constructor receiver', data=receiver_bytes)
            t['receiver']=receiver
            put_double(env,0x513E10,defaults[0])
            put_double(env,0x513E18,defaults[1])
            env.put(0x513E40,(0xFFFFFFFF,0x80000001,1,17)[n % 4])
            put_double(env,0x50FF18,(0.125,0.0037,1.25)[n % 3])
            env.put(t['actor']+0x4C,(-813 & 0xFFFFFFFF),1793)
            env.put(t['actor']+0x148,(-71 & 0xFFFFFFFF),137)
            entries=[]
            for j,key in enumerate(('LEVEL_WINDGRASS','LEVEL_WINDLEAF','LEVEL_WINDSAND')):
                frame=env.object(0x30,'distinct image frame',fill=0x67+j)
                env.put(frame+0x18,(-13-j)&0xFFFFFFFF,7+j,31+j*3,61+j*5)
                pointers=env.object(4,'distinct frame pointers',words=[frame])
                asset=env.object(0x70,'distinct image asset',fill=0)
                env.put(asset+0x14,pointers)
                env.put(asset+0x64,0,0)
                entries.append((key,asset))
            images=resource_map(env,entries,'distinct wind images')
            env.put(t['world']+0x10,images)
            def choose_and_change(env,call):
                # Record the boundary state and vary fields reset after rand.
                env.write(t['log'],env.read(receiver+0x190,32))
                env.put(receiver+0x19C,0xBEEF1234,0x7FFFFFFF)
                env.put(t['actor']+8,0x84A50240)
                env.put(t['actor']+0x164,0x12734080)
                return rand_value & 0xFFFFFFFF
            env.override(0x4A3050,choose_and_change)
            return t
        yield ordinary(f'construct distinct words defaults resources and late reset {n}',CONSTRUCT,setup,(lambda t:t['actor'],))
    for n in range(24):
        marker = random_source.randrange(1, 0xFFFFFFFF)
        ranges = ((0, 0, 0, 0), (1, -2, 3, -4), (-2147483648, 2147483647, -17, 23), (0, 7, 0, -9))[n % 4]
        setup = constructor_setup(marker, ranges, (0, 1, 2, -1, -2, 2147483647)[n % 6], n % 2 == 0)
        yield ordinary(f'construct defaults signed ranges and asset selection {n}', CONSTRUCT, setup, (lambda t: t['actor'],))
    for state in (0, 1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF):
        def setup(env, state=state):
            t = base(env, random_source.randrange(1, 0xFFFFFFFF))
            receiver = env.object(0x1B0, 'existing wind debris', fill=0)
            vt = env.object(0x24, 'existing wind vtable', fill=0)
            env.put(receiver, vt)
            env.put(receiver + 0x10, t['config'])
            env.put(t['config'] + 0x18, receiver, state)
            def observe(env, call):
                env.put(t['log'], call.receiver, env.get(t['config']+0x18), env.get(t['config']+0x1C))
                return 0x83724159
            for offset in (4, 8, 12, 16, 28, 32):
                env.put(vt + offset, env.stub(f'virtual {offset}', 'thiscall', 1 if offset in (4,8,12) else 0, observe))
            env.put(0x50FEFC, env.stub('constructed object initialize', 'thiscall', 0, observe))
            # Real state registry storage, with a null counted array.
            table = env.object(4, 'state registry cell', words=[0])
            env.put(0x5376A0, 71, 71, table, table, 4, 0, 0)
            return t
        yield Case(f'factory lifecycle state {state}', FACTORY, setup, arguments=(lambda t: t['actor'],))
    for low, high in ((0, 2), (-5, -3), (27, 29)):
        for index in (low-1, low, high, high+1):
            for present in (False, True):
                yield Case(f'dispatch {low}:{high} index {index} callback {present}', DISPATCH,
                           dispatch_setup(index, low, high, 8, present), receiver=lambda t:t['receiver'], arguments=(index & 0xFFFFFFFF,),
                           source_context=lambda t:t['source'], source_return_pc=0x49F13E)
    for n in range(12):
        marker = random_source.randrange(1, 0xFFFFFFFF)
        def setup(env, marker=marker):
            t=base(env, marker)
            receiver=env.object(0x1B0, 'start receiver', fill=0xA7)
            env.put(receiver+0x0C,t['actor'], t['config'])
            env.put(receiver+0x12C,t['actor'])
            t['receiver']=receiver
            return t
        yield ordinary(f'start captures current state and unsigned clock {n}', START, setup)
    comparisons = ((-1.0, 0), (0.0, 0), (1.0, 0), (-17.5, -17), (19.0, 20), (20.0, 20), (float('nan'), 0), (float('inf'), 7), (float('-inf'), -7))
    timings = ((0,0,0), (99,0,100), (100,0,100), (101,0,100), (5,0xFFFFFFFE,7), (0,1,0xFFFFFFFF))
    for distance,limit in comparisons:
        for now,started,duration in timings:
            marker=random_source.randrange(1,0xFFFFFFFF)
            def setup(env,distance=distance,limit=limit,now=now,started=started,duration=duration,marker=marker):
                t=base(env,marker)
                receiver=env.object(0x1B0,'moving receiver',fill=0xA8)
                env.put(receiver+0x12C,t['actor'])
                put_double(env,receiver+0x68,distance)
                env.put(receiver+0x1A0,limit & 0xFFFFFFFF,started,duration)
                env.put(t['actor']+0x190,0)
                env.put(0x537210,now)
                t['receiver']=receiver
                return t
            yield ordinary(f'tick distance {distance}/{limit} clock {now}-{started}/{duration}',TICK,setup)
    for index in (-4, 9):
        def setup(env,index=index):
            t=dispatch_setup(index,index+1,index+3,8,True)(env)
            def resize(env,call):
                old,size=call.arguments
                ptr=env.object(max(8,size),'reallocated callback storage',fill=0)
                cb=env.get(old)
                env.put(ptr,cb)
                if env.calls_so_far(0x4A9070)==1:
                    env.put(0x53EC08,index & 0xFFFFFFFF,(index-1)&0xFFFFFFFF)
                else:
                    env.put(0x53EC0C,index & 0xFFFFFFFF)
                env.release(old)
                return ptr
            env.override(0x4A9070,resize)
            return t
        yield Case(f'dispatch repeats lookup after realloc changes bounds {index}',DISPATCH,setup,
                   receiver=lambda t:t['receiver'],arguments=(index&0xFFFFFFFF,),
                   source_context=lambda t:t['source'],source_return_pc=0x49F13E)
