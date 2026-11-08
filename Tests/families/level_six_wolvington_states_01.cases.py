"""Wolvington state cases built from the original control flow and layouts."""
import struct
from itertools import product
from clawparity.cases import Case
from clawparity.fixtures import returns

ENTRIES = (0x4A0960,0x4A0A90,0x4A0AE0,0x4A0B30,0x4A0C10,0x4A0CF0,0x4A0EC0,0x4A0F40,0x4A0FD0,0x4A1020,0x4A10B0,0x4A10F0,0x4A1250)


def mapping(env, address, entries):
    """Actual original CString hash table, with one bucket and chained entries."""
    head = 0
    for key, value in entries:
        name = env.object(len(key)+1, 'resource name', data=key.encode()+b'\0')
        node = env.object(16, 'resource map node', words=[head, 0, name, value])
        head = node
    buckets = env.object(4, 'hash buckets', words=[head])
    env.put(address+4, buckets, 1)


def setup_case(salt, **opts):
    def setup(env):
        actor = env.object(0x480, 'Wolvington', fill=0xA7)
        sprite = env.object(0x1C0, 'Wolvington sprite', fill=0xB9)
        body = env.object(0x1C0, 'collision body', fill=0xC3)
        state = env.object(0x40, 'logic state', fill=0xD5)
        world = env.object(0x100, 'world resources')
        animation = env.object(0x40, 'animation descriptor')
        frame = env.object(0x40, 'animation frame')
        frame_table = env.object(4, 'animation frame vector', words=[frame])
        env.put(animation+0xC, frame_table, 1)
        env.put(frame+0x1C, 0x12345678 ^ salt)
        vtable = env.object(0x80, 'state callbacks')
        log = env.object(0x80, 'callback observations')
        def callback(offset):
            def effect(e,c):
                count=e.get(log)
                e.put(log, count+1)
                e.put(log+4+(count%6)*16, offset,c.receiver,e.get(actor+0x460),e.get(actor+0x464))
                if opts.get('mutate_callback'):
                    e.put(actor+0x464, opts.get('counter_after', 7))
                    e.put(actor+0x18C, 3)
                    e.put(actor+0x3C4, 15)
                return 0x12340000+offset
            return effect
        for off in (0x44,0x48,0x64):
            env.put(vtable+off, env.stub('state callback '+hex(off),'thiscall',0,callback(off)))
        env.put(actor, vtable)
        env.put(actor+0xC, body, state)
        env.put(actor+0x128, 0x63729182, sprite, world)
        env.put(actor+0x138, 0x11223344 ^ salt)
        env.put(actor+0x140, 0x55667788 ^ salt)
        env.put(actor+0x184, opts.get('contact',7))
        env.put(actor+0x18C, opts.get('direction',2))
        env.put(actor+0x1A0, opts.get('shot',1))
        env.put(actor+0x2FC, 0)
        env.put(actor+0x308, animation, animation)
        env.put(actor+0x34C, animation)
        env.put(actor+0x3C4, opts.get('distance', -1))
        env.put(actor+0x400, opts.get('speed', 0x12345), opts.get('speed2',opts.get('speed',0x12345)^0x55AA55AA))
        env.put(actor+0x460,opts.get('repeat',1),opts.get('counter',3),0xFFFFFFBF,10,opts.get('projectile_speed',-300),0)
        for off, value in ((0x68,11.5),(0x80,12.5),(0x98,13.5)):
            env.write(actor+off,struct.pack('<d', value))
        if opts.get('equal') == 1:
            env.write(actor+0x80,env.read(actor+0x68,8))
        if opts.get('equal') == 2:
            env.write(actor+0x98,env.read(actor+0x68,8))
        if opts.get('equal') == 3:
            env.write(actor+0x68,struct.pack('<Q',0x7FF8000000000042))
        env.put(state+0x1C,0x66554433 ^ salt)
        env.put(sprite+0xC,world)
        env.put(sprite+0x40, opts.get('flags',0)|0x240)
        env.put(sprite+0x4C, 111,222)
        env.put(sprite+0x64,37)
        for off in (0x118,0x128,0x138):
            env.put(sprite+off,0xFFFFFFED ^ salt,0x79797979,0x2F ^ salt,0x89898989)
        env.put(sprite+0x170,0)
        env.put(sprite+0x188+4,sprite,animation,frame,0,opts.get('timer',0),0,opts.get('finished',1),opts.get('event',0),opts.get('event',0),0x3F800000)
        env.put(sprite+0x190, animation)
        resources = env.object(0x50,'resource registry')
        sounds = env.object(0x50,'sound registry')
        env.put(world+0x28,sounds,resources)
        mapping(env,resources+0x10, [('LEVEL_WOLVINGTON_STRIKE1',animation)] if opts.get('mapped_animation') else [])
        snd = env.object(0x20,'sound entry')
        sound = env.object(0x30,'sound')
        device = env.object(0x90,'audio device')
        env.put(snd+0x10,sound)
        env.put(sound+0x10,device)
        env.put(device+0x78,0)
        env.put(actor+0x474,snd if opts.get('sound') else 0)
        sound_entries = [(k,snd) for k in ('LEVEL_WOLVINGTON_WMAGICLOW','LEVEL_WOLVINGTON_WMAGIC')] if opts.get('sound') else []
        mapping(env,sounds+0x10,sound_entries)
        env.put(0x532C0C,opts.get('enabled',0), 0x3F123456)
        env.put(0x5430C4,1)
        owner=env.object(0xD0,'player state')
        env.put(owner+0xCC,opts.get('player_state',5))
        env.put(0x537E88,owner)
        env.put(0x537668+0x18,0)
        if opts.get('spawn'):
            manager = env.object(0x60, 'object manager',fill=0)
            class_map = env.object(0x40, 'class registry')
            images = env.object(0x40, 'image registry')
            terrain = env.object(0x80, 'collision world')
            descriptor = env.object(0x40, 'WolvingtonBullet class descriptor')
            # The real original factory callback, unchanged.
            env.put(descriptor+0x10, 0x410340)
            env.put(world+8,manager)
            env.put(world+0x10,images,class_map)
            env.put(world+0x24,terrain)
            env.put(manager+0xC,world)
            free_node = env.object(12,'list free node')
            env.put(manager+0x14,0,0,0,free_node)
            mapping(env,class_map+0x10,[('WolvingtonBullet',descriptor)])
            image = env.object(0x70, 'bullet image resource',fill=0)
            image_frame = env.object(0x40, 'bullet frame geometry',fill=0)
            image_frames = env.object(4, 'bullet image frames',words=[image_frame])
            env.put(image+0x14,image_frames)
            env.put(image+0x64,0,0)
            env.put(image_frame+0x18,3,5,17,29)
            mapping(env,images+0x10,[('GAME_BULLETS',image),('LEVEL_WOLVINGTONMAGIC',image)])
            env.put(0x53724C,1)
            env.put(0x537210,0)
            env.put(terrain+0x64,1024,1024)
            allocation_log = env.object(8,'allocation observations',fill=0)
            def allocate_projectile(e,c):
                result=e.object(c.arguments[0], 'original allocation', fill=opts.get('allocation_fill',0))
                if c.arguments[0] == 0x1B4:
                    e.put(allocation_log,result)
                if c.arguments[0] == 0x158 and opts.get('allocation_mutation'):
                    created=e.get(allocation_log)
                    e.put(created+0x128,0xFFFFFFD3,0x21,0x39,0x4B)
                    if opts.get('spawn_flipped'):
                        e.put(created+0x40,e.get(created+0x40)|2)
                    if opts.get('reload_velocity'):
                        e.put(actor+0x470,0x80000000)
                return result
            env.override(0x4F63EC,allocate_projectile)
            env.put(actor+0x130,state)
            env.put(state+0xC,world)

        env.override(0x4A3050,returns(opts.get('random',salt)))
        return {'actor':actor}
    return setup


def case(entry,label,salt=17,**opts):
    return Case(label,entry,setup_case(salt,**opts),receiver=lambda t:t['actor'])


def cases(random_source):
    for entry in ENTRIES:
        yield case(entry,'direct '+hex(entry),shot=1)
    for direction,flags in product((0,2,3),(0,2)):
        for contact,distance in ((7,-1),(0,-1),(0,0),(1,299),(2,300),(1,399),(2,400),(0,999),(0,1000),(3,-1),(3,0),(4,499),(4,500),(5,0),(6,0)):
            yield case(0x4A0960,f'home d{direction} f{flags} c{contact} x{distance}',direction=direction,flags=flags,contact=contact,distance=distance)
    for state in (4,5,6):
        yield case(0x4A0960,f'home player state {state}',contact=3,distance=2,player_state=state)
    for counter in (0,1,2,9,10,11,0xFFFFFFFF,0x7FFFFFFF):
        for flags in (0,2):
            yield case(0x4A0AE0,f'alternating counter {counter} f{flags}',counter=counter,flags=flags)
    yield case(0x4A0AE0,'callback changes the reread counter',counter=10,mutate_callback=True)
    for entry in (0x4A0B30,0x4A0C10,0x4A0EC0):
        for flags,sound,enabled in product((0,2),(0,1),(0,1)):
            yield case(entry,f'attack {entry:x} f{flags} sound{sound} enabled{enabled}',flags=flags,sound=sound,enabled=enabled)
    for value in (0,1,10,11,21,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
        yield case(0x4A0A90,f'random signed remainder {value}',random=value)
    for entry in (0x4A0F40,0x4A1020,0x4A0CF0):
        for event,flags,finished,timer,repeat in product((0,1,2),(0,2),(0,1),(0,3),(0,1)):
            if entry==0x4A0CF0 and event==1:
                continue  # projectile creation profiles are supplied separately below
            yield case(entry,f'animation {entry:x} event{event} f{flags} done{finished} t{timer} r{repeat}',event=event,flags=flags,finished=finished,timer=timer,repeat=repeat,shot=1)
    for contact,direction,speed in product((0,1,2,3,4,5,6,0xFFFFFFFF),(2,3),(0,1,0x80000001)):
        yield case(0x4A10F0,f'run uppercut c{contact} d{direction} s{speed}',contact=contact,direction=direction,speed=speed)
    for contact,distance,direction in product((0,1,2,3,4,5,6,7),(-1,0,9,10,19,20),(2,3)):
        yield case(0x4A1250,f'advance c{contact} x{distance} d{direction}',contact=contact,distance=distance,direction=direction)
    for equal in (0,1,2,3):
        for flags in (0,2):
            yield case(0x4A1250,f'advance position equality {equal} flags {flags}',equal=equal,flags=flags)
    for index in range(12):
        yield case(0x4A1250,f'random integer velocity {index}',salt=random_source.getrandbits(16),speed=random_source.getrandbits(32))

    for direction, speed in product((2,3),(-300,0,300)):
        yield case(0x4A0CF0,f'original projectile creation d{direction} speed{speed}',spawn=True,shot=0,event=1,direction=direction,projectile_speed=speed)
    yield case(0x4A0CF0,'projectile event already fired',event=1,shot=1,direction=3)

    for flipped in (False,True):
        yield case(0x4A0CF0,f'allocator changes live attack bounds flipped {flipped}',spawn=True,shot=0,event=1,allocation_mutation=True,spawn_flipped=flipped)
    yield case(0x4A0CF0,'velocity reread after original initializer allocation',spawn=True,shot=0,event=1,projectile_speed=5,allocation_mutation=True,reload_velocity=True)

    for entry in (0x4A0B30,0x4A0C10):
        yield case(entry,f'changed attack velocity {entry:x}',projectile_speed=0x12345678)
    for event in (0,0x1234567):
        yield case(0x4A0FD0,f'sword resolves real animation {event}',mapped_animation=True,event=event)
    for direction in (2,3):
        yield case(0x4A1250,f'distinct advance and fast speed d{direction}',direction=direction,speed=0x80000000,speed2=17)
    yield case(0x4A0CF0,'nonzero allocated logic bounds',spawn=True,shot=0,event=1,allocation_fill=0x37,allocation_mutation=True)
