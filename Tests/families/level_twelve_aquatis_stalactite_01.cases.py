"""Original-driven Aquatis stalactite state, lifetime and construction cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate


def zobject(env, *args, **kwargs):
    kwargs.setdefault("fill", 0)
    return env.object(*args, **kwargs)


def real_map(env, entries, name):
    owner = zobject(env, 0x30, name)
    bucket = zobject(env, 4, name + '-bucket')
    link = 0
    for key, value in reversed(entries):
        text = zobject(env, len(key) + 1, name + '-key', data=key.encode() + b'\0')
        node = zobject(env, 16, name + '-node', words=[link, 0, text, value])
        link = node
    env.put(owner + 0x14, bucket, 1)
    env.put(bucket, link)
    return owner


def sequence_record(env, name, tag):
    frame = zobject(env, 0x30, name + '-frame')
    env.put(frame + 0xc, 9)
    env.put(frame + 0x18, 17, tag)
    pointers = zobject(env, 4, name + '-frames', words=[frame])
    record = zobject(env, 0x18, name, words=[0, 0, 0, pointers, 1, 0])
    return record


def setup_case(random_source, **options):
    salt = random_source.randrange(0x1000, 0x100000)
    def setup(env):
        receiver = zobject(env, 0x1c0, 'stalactite', fill=(salt & 0xff) or 0xa5)
        base = zobject(env, 0x240, 'base-entity')
        logic = zobject(env, 0x120, 'logic')
        singleton = zobject(env, 0x4f0, 'aquatis')
        owner = zobject(env, 0x40, 'resources')
        collision = zobject(env, 0x80, 'collision')
        env.put(collision + 0x64, 16, 16)
        home = sequence_record(env, 'home', salt + 1)
        crumble = sequence_record(env, 'crumble', salt + 2)
        null_sequence = sequence_record(env, 'null-sequence', salt + 3)
        sequence_entries = [('GAME_NULL', null_sequence)]
        if options.get('resources', True):
            sequence_entries += [('LEVEL_STALACTITE_HOME', home), ('LEVEL_STALACTITE_CRUMBLE', crumble)]
        sprite_entries = []
        if options.get('sprite'):
            sprite_frame = zobject(env, 0x28, 'sprite-frame')
            env.put(sprite_frame + 0x18, 3, -11, 19, 37)
            sprite_frames = zobject(env, 8, 'sprite-frames', words=[0, sprite_frame])
            sprite = zobject(env, 0x6c, 'sprite')
            env.put(sprite + 0x14, sprite_frames)
            env.put(sprite + 0x64, 1, 1)
            sprite_entries = [('LEVEL_PROJECTILES_STALACTITE', sprite)]
        maps = [real_map(env, sprite_entries, 'sprites'), real_map(env, [], 'logic-map'), real_map(env, [], 'sounds'), real_map(env, sequence_entries, 'sequences')]
        env.put(owner + 0x10, maps[0], maps[1])
        env.put(owner + 0x24, collision, maps[2], maps[3])
        env.put(base + 0xc, owner)
        env.put(base + 0x6c, logic)
        env.put(base + 0x4c, options.get('x', -31), options.get('yint', 107))
        env.put(base + 0x148, 13, -19)
        env.put(base + 0xcc, 7)
        env.put(base + 0x108, options.get('ordinal', 3))
        env.put(base + 8, options.get('flags', 0x92))
        env.put(base + 0x40, 0xa5)
        env.put(base + 0x190, salt + 7)
        env.put(base + 0x19c, options.get('active_frame', 0))
        env.put(base + 0x1a4, options.get('ready', 1))
        env.put(base + 0x18c, base)
        env.put(base + 0x190, 0)
        env.put(logic + 0x1c, salt + 11)
        for offset, value in zip((0x2c, 0x30, 0x34, 0x38), options.get('limits', (0, 0, 0, 0))):
            env.put(logic + offset, value)
        env.put(receiver, 0x50b26c)
        env.put(receiver + 0xc, 0 if options.get('base_null') else base, logic)
        env.put(receiver + 0x12c, base)
        for offset in (0x20, 0x24, 0xc8, 0x134):
            env.put(receiver + offset, salt + offset)
        for offset in (0x40, 0x50, 0x58, 0x60):
            env.write(receiver + offset, struct.pack('<d', offset + 1.0 / 3.0))
        env.write(receiver + 0x68, struct.pack('<d', -76.25))
        env.write(receiver + 0x70, struct.pack('<d', options.get('y', 107.5)))
        env.put(receiver + 0x19c, home if options.get('animation', True) else 0)
        env.put(receiver + 0x1a0, crumble if options.get('animation', True) else 0)
        env.put(receiver + 0x1a4, options.get('saved_x', -143), options.get('saved_y', 678), options.get('mask', 0x12))
        env.put(singleton + 0xc, 0x12340000)
        env.put(singleton + 0x4b0, options.get('height', 107))
        env.put(singleton + 0x4b8, options.get('enabled', 1), options.get('release', 1))
        env.put(singleton + 0x4c4, salt + 99)
        env.put(singleton + 0x4ec, options.get('reset_mask', 0x17))
        env.put(0x534874, singleton if options.get('singleton', True) else 0)
        env.put(0x5349dc, 0x12340000 if options.get('identity', True) else 0x12340004)
        env.put(0x5235e0, options.get('counter', 3))
        env.put(0x53490c, options.get('count', 0))
        env.put(0x5231f4, options.get('maximum', 5))
        env.put(0x5231e0, 0x11, 0x22, 0x44, 0x88, 0x100)
        env.put(0x5430c4, options.get('elapsed', 2))
        env.put(0x537210, options.get('clock', 0))
        env.put(0x532c0c, options.get('sound_enabled', 0))
        env.put(0x532c10, salt + 0x100)
        env.put(0x540e00, 0)
        env.put(0x537680, 0)  # empty original state registry
        state = options.get('state')
        if state:
            name = zobject(env, len(state) + 1, 'state-name', data=state.encode() + b'\0')
            node = zobject(env, 20, 'state-node')
            env.put(node, node, node, 0, name, salt + 0x400)
            env.put(0x537680, node)
        env.put(receiver + 0x1b0, 0, 0)
        if options.get('sound'):
            record = zobject(env, 0x14, 'sound-record')
            sound = zobject(env, 0x14, 'sound')
            source = zobject(env, 0x7c, 'sound-source')
            env.put(record + 0x10, sound)
            env.put(sound + 0x10, source)
            env.put(receiver + 0x1b0, record)
            env.put(receiver + 0x1b4, record)
        log = zobject(env, 0x40, 'callback-log')
        table = zobject(env, 0x28, 'stalactite-vtable')
        def callback(env, call):
            env.put(log, env.get(log) + 1, call.receiver, env.get(receiver + 0x68), env.get(receiver + 0x6c), env.get(receiver + 0x70), env.get(receiver + 0x74), env.get(base + 8), env.get(0x5235e0))
            if options.get('mutate') == 'drop-singleton':
                env.put(0x534874, 0)
            if options.get('mutate'):
                env.put(receiver + 0x1ac, 0x80)
                env.put(singleton + 0x4ec, 0x193)
            return salt + 42
        env.put(table + 0x24, env.stub('reset-publication', 'thiscall', 0, callback))
        env.put(receiver, table)
        return {'receiver': receiver, 'base': base, 'logic': logic, 'log': log, 'singleton': singleton, 'salt': salt}
    return setup


def entry(random_source, address, label, **options):
    return Case(label, address, setup_case(random_source, **options), receiver=lambda t: t['receiver'], arguments=(0x76543210,) if address == 0x407c10 else ())


def dispatch_setup(random_source, index, low, high, slot=True, fail=False):
    base_setup = setup_case(random_source)
    def setup(env):
        tokens = base_setup(env)
        receiver = tokens['receiver']
        # Coherent original RTTI for the null dispatch slot branch.
        methods_backing = zobject(env, 12, 'rtti-methods')
        descriptor = zobject(env, 16, 'rtti-descriptor')
        name = zobject(env, 16, 'rtti-name', data=b'Object\0')
        env.put(methods_backing, descriptor)
        env.put(descriptor + 0xc, name)
        env.put(receiver, methods_backing + 4)
        table = zobject(env, (high-low+1)*4, 'dispatch-table')
        def callback(env, call):
            env.put(tokens['log'], call.receiver, env.get(0x534908), env.get(0x5348f0), env.get(0x5348f4))
            return 0x11223344
        target = env.stub('stalactite-dispatch', 'thiscall', 0, callback)
        if slot:
            for offset in range(high-low+1):
                env.put(table + 4*offset, target)
        env.put(0x5348e8, 0, 0, low, high, table, table, 4, 0x44332211, 0xaabbccdd)
        if fail:
            def no_memory(env, call):
                return 0
            env.override(0x4a9070, no_memory)
        return tokens
    return setup


def cases(random_source):
    for flags in (0, 1, 2, 0x100, 0x101, 0xfffffffe, 0xffffffff):
        yield Case('delete flags %x' % flags, 0x407bd0, setup_case(random_source, count=flags), receiver=lambda t:t['receiver'], arguments=(flags,))
    for count in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff):
        yield entry(random_source, 0x407bf0, 'destructor count %x' % count, count=count)
    for index,low,high,slot in ((0,0,0,True),(-1,-2,2,True),(2,-2,2,True),(0,-2,2,False),(-3,-2,2,True),(3,-2,2,True)):
        yield Case('dispatch %d %d..%d slot%d' % (index,low,high,slot), 0x407500, dispatch_setup(random_source,index,low,high,slot), receiver=lambda t:t['receiver'],arguments=(index,))
    for address,state in ((0x407c40,'ES_IDLE'),(0x407e90,'ES_DEAD'),(0x407f80,'ES_WAITING')):
        for singleton in (False,True):
            for animation in (False,True):
                for sound,sound_enabled in ((False,0),(True,0),(True,1)):
                    yield entry(random_source,address,'initializer %x %s %s %s %s' %(address,singleton,animation,sound,sound_enabled),singleton=singleton,animation=animation,sound=sound,sound_enabled=sound_enabled,state=state)
    for address in (0x407cc0,0x407d50,0x407e40,0x407f20):
        for options in ({'singleton':False},{'identity':False},{'enabled':0},{'release':0},{'base_null':True,'enabled':0},{'ordinal':2},{'ready':0},{'active_frame':17},{'height':108},{'height':106},{'height':107},{'y':float('nan')},{'sound':True,'sound_enabled':0},{'sound':True,'sound_enabled':1},{}):
            yield entry(random_source,address,'state %x %r' %(address,options),**options)
    for singleton in (False,True):
        for mutate in (False,True):
            for x,y in ((0,0),(-1,1),(0x7fffffff,0x80000000),(-347,659)):
                yield entry(random_source,0x407fb0,'reset %s %s %s %s' %(singleton,mutate,x,y),singleton=singleton,mutate=mutate,saved_x=x,saved_y=y,state='ES_IDLE')
    for singleton,mask,reset in ((False,1,1),(True,0,0xffffffff),(True,2,4),(True,2,2),(True,0x80000000,0x80000000)):
        yield entry(random_source,0x407c10,'reset guard %s %x %x' %(singleton,mask,reset),singleton=singleton,mask=mask,reset_mask=reset)
    for resources in (False,True):
        for limits in ((0,0,0,0),(1,2,3,4),(-1,-2,-3,-4),(0,7,-12,0)):
            for count in (0,4,5,6):
                yield Case('construct %s %s count%d' %(resources,limits,count),0x4078b0,setup_case(random_source,resources=resources,limits=limits,count=count,singleton=bool(count%2)),receiver=lambda t:t['receiver'],arguments=(lambda t:t['base'],))

    for clock in (1, 123456, 0x80000000, 0xffffffff):
        yield Case('construct unsigned clock %x' % clock,0x4078b0,setup_case(random_source,clock=clock,limits=(5,-6,7,-8)),receiver=lambda t:t['receiver'],arguments=(lambda t:t['base'],))

    yield entry(random_source,0x407cc0,'idle with missing base',base_null=True)
    yield entry(random_source,0x407fb0,'reset callback clears singleton',mutate='drop-singleton',state='ES_IDLE')

    for clock in (0, 1, 123456, 0x80000000):
        yield Case('construct rectangle helpers clock %x' % clock,0x4078b0,setup_case(random_source,sprite=True,clock=clock,limits=(3,7,-11,19)),receiver=lambda t:t['receiver'],arguments=(lambda t:t['base'],))
