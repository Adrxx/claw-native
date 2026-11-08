"""Original-derived robber thief behavioral cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_base(env):
    obj = env.object(0x480, 'thief', fill=0)
    image = env.object(0x200, 'sprite', fill=0)
    state = env.object(0x180, 'state', fill=0)
    player = env.object(0x200, 'player', fill=0)
    methods = env.object(0xB0, 'thief-vtable', fill=0)
    record = env.object(0x80, 'observed', fill=0)
    env.put(obj, methods)
    env.put(obj + 0x10, state)
    env.put(obj + 0x12c, image)
    env.put(obj + 0x194, image)
    env.put(obj + 0x138, 17, 0x89898989, 39)
    env.put(image + 0x38, 0xffffffff)
    env.put(image + 0x118, 23, 0x67676767, 47)
    env.put(image + 0x128, 19, 0x78787878, 53)
    env.put(image + 0x138, 31, 0x56565656, 71)
    env.put(image + 0x4c, 10, 80)
    env.put(player + 0x4c, 42, 80)
    env.put(0x537e88, player)
    env.put(0x537210, 10000)
    env.put(0x537668 + 0x18, 0)
    env.put(state + 0x1c, 0x2468ACE0)
    for off in (0x44, 0x48, 0xa4):
        def callback(e, c, off=off):
            n = e.get(record)
            e.put(record, n+1)
            e.put(record+4+n*12, off, c.receiver, e.get(c.receiver+0x18c))
            return 0x97531
        env.put(methods+off, env.stub('thief-method-%x' % off, 'thiscall', 0, callback))
    return {'obj': obj, 'image': image, 'state': state, 'player': player, 'record': record}


def case(label, function, configure=None, arguments=()):
    def setup(env):
        t = setup_base(env)
        if configure:
            configure(env, t)
        return t
    return Case(label, function, setup, receiver=lambda t:t['obj'], arguments=arguments,
                initial_stack=((-4,b'\x21\x43\x65\x87'),) if function==0x485f00 else ())


def cases(random_source):
    for orientation in (0, 2, 0xffffffff):
        for flags in (0, 2, 0xa5a55a58, 0xa5a55a5a):
            def configure(e,t,orientation=orientation,flags=flags):
                e.put(t['obj']+0x18c, orientation)
                e.put(t['image']+0x40, flags)
                e.put(0x534eac, 0x26b7)
            yield case('attack disabled facing %x flags %x' % (orientation,flags),0x485d90,configure)
    for now,last,delay in ((100,99,2),(0,0xffffffff,2),(0,1,0xffffffff),(0xffffffff,0,0xffffffff-1)):
        def configure(e,t,now=now,last=last,delay=delay):
            resource_setup(e,t,False)
            e.put(0x537210,now)
            e.put(t['obj']+0x470,last,delay)
        yield case('timer pending %x %x %x'%(now,last,delay),0x485ec0,configure)
    for latched in (0,1,0xffffffff):
        for done,delay in ((0,0),(1,1),(1,0)):
            def configure(e,t,latched=latched,done=done,delay=delay):
                e.put(t['obj']+0x1a0,latched)
                e.put(t['image']+0x19c,delay)
                e.put(t['image']+0x1a4,done)
            yield case('update no animation %x %x %x'%(latched,done,delay),0x486090,configure)
    for flags in (0,1,2,0xff,0x100):
        def configure(e,t):
            empty = e.get(0x52e1c8)+12
            e.put(t['obj']+0x1a4,empty,empty)
            e.put(t['obj']+0x474,0)
        yield case('deleting destructor flags %x'%flags,0x485870,configure,(flags,))
    def destroy_config(e,t):
        empty = e.get(0x52e1c8)+12
        e.put(t['obj']+0x1a4,empty,empty)
        e.put(t['obj']+0x474,0)
    yield case('direct destroy empty inline bitset',0x485890,destroy_config)
    def distinct_strings(e,t):
        first=e.object(24,'first-string',words=[3,3,8,0x616263])
        second=e.object(24,'second-string',words=[1,5,8,0x646566])
        e.put(t['obj']+0x1a4,first+12,second+12)
        def decrement(e,c):
            ref=c.arguments[0]
            value=(e.get(ref)-1)&0xffffffff
            e.put(ref,value)
            return value
        e.override(0x5469e8,decrement)
    yield case('destroy distinct owned CString reference counts',0x485890,distinct_strings)
    for index in (-2,0,2,4,6):
        for fallback in (False,True):
            def configure(e,t,index=index,fallback=fallback):
                def effect(e,c):
                    e.put(t['record'],c.receiver,e.get(0x53c258))
                    return 0
                target=e.stub('state-dispatch','thiscall',0,effect)
                table=e.object(20,'state-table',words=[0 if fallback else target]*5)
                base=e.object(36,'base-state-table',words=[target]*9)
                e.put(0x53c240,0,4,table,0,4)
                e.put(0x537880,-2,6,base,0,4)
            yield case('dispatch %d fallback %s'%(index,fallback),0x485960,configure,(index,))
    for level in (0,5,64,65,66,67,68):
        def configure(e,t,level=level):
            resource_setup(e,t,level==65)
            e.put(t['obj']+0x470,0x13572468,0x24681357)
            e.put(t['obj']+0xc,t['image'])
            e.put(t['image']+0x6c,t['state'])
            collision=e.object(0x70,'base-collision',fill=0)
            e.put(t['manager']+0x24,collision)
            for off in (0x10,0x14):
                container=e.object(0x30,'base-resources',fill=0)
                e.put(container+0x18,1)
                e.put(t['manager']+off,container)
                if off==0x10:
                    images=e.object(0x70,'image-resource',fill=0)
                    image_frame=e.object(0x20,'image-resource-frame',fill=0)
                    frame_table=e.object(4,'image-frame-pointers',words=[image_frame])
                    e.put(images+0x14,frame_table)
                    e.put(images+0x64,0,0)
                    map_values(e,container,[('LEVEL_ROBBERTHIEF',images)])
            if level>=66:
                factor={66:-4.25,67:0.0,68:24.75}[level]
                e.write(0x50f490,struct.pack('<f',factor))
                e.write(0x5262b4,struct.pack('<f',1.5))
                e.write(0x5262b0,struct.pack('<f',0.625))
            e.put(0x537964,level)
            e.put(0x533470,64 if level==64 else 32)
            e.override(0x4a3050,sequence(0,50))
        yield case('construct level %d'%level,0x485330,configure,(lambda t:t['image'],))
    for velocity in (-400,0,400,0x80000000):
        for mirrored,first_sentinel,second_sentinel in ((0,False,False),(0,True,False),(0,False,True),(2,False,False)):
            for sound in (0,1,2):
                def configure(e,t,velocity=velocity,mirrored=mirrored,first_sentinel=first_sentinel,second_sentinel=second_sentinel,sound=sound):
                    firing_setup(e,t,velocity,mirrored,first_sentinel,second_sentinel,sound)
                yield case('fire velocity %x mirror %d sentinels %s %s sound %d'%(velocity,mirrored,first_sentinel,second_sentinel,sound),0x486090,configure)
    def callback_changes_velocity(e,t):
        firing_setup(e,t,-400,0,False,False,0,True)
    yield case('fire callback changes velocity and runtime pointer',0x486090,callback_changes_velocity)
    for posture in (0,5):
        def sound_hit_animation_miss(e,t,posture=posture):
            resource_setup(e,t,True)
            e.put(t['player']+0xcc,posture)
            animations=e.get(t['manager']+0x2c)
            e.put(animations+0x14,0)
            frame=e.object(0x30,'stale-sound-frame',fill=0)
            e.put(frame+0x1c,0x19)
            frames=e.object(4,'stale-sound-frame-table',words=[frame])
            sound=e.object(0x30,'sound-hit-valid-stale-animation',fill=0)
            e.put(sound+0xc,frames,1)
            sounds=e.get(t['manager']+0x28)
            map_values(e,sounds,[('LEVEL_ROBBERTHIEF_ARROWHIGH',sound),('LEVEL_ROBBERTHIEF_ARROWLOW',sound)])
        yield case('begin sound hit animation miss posture %d'%posture,0x485f00,sound_hit_animation_miss)
    for posture in (0,5):
        for flags in (0,2):
            for populated in (False, True):
                def configure(e,t,posture=posture,flags=flags,populated=populated):
                    resource_setup(e,t,populated)
                    e.put(t['player']+0xcc,posture)
                    e.put(t['image']+0x40,flags)
                yield case('begin posture %d flags %d resources %s'%(posture,flags,populated),0x485f00,configure)
                def timed_config(e,t,configure=configure):
                    configure(e,t)
                    e.put(t['obj']+0x470,9000,1000)
                yield case('elapsed begin %d %d %s'%(posture,flags,populated),0x485ec0,timed_config)
    for value in (0,1,2,3,4,0x7fffffff,0xffffffff,0xfffffffe,0xfffffffd,0x80000000):
        for facing,flags in ((0,0),(2,0),(2,2),(0,2)):
            def configure(e,t,value=value,facing=facing,flags=flags):
                resource_setup(e,t,False)
                e.put(t['obj']+0x18c,facing)
                e.put(t['image']+0x40,flags)
                e.put(t['obj']+0x454,*[random_source.randrange(1,0xffffffff) for _ in range(7)])
                e.override(0x4a3050,sequence(value,50))
            yield case('idle signed rand %x facing %d flags %d'%(value,facing,flags),0x485d60,configure)
    def blocked_attack(e,t):
        collision_setup(e,t,True)
        e.put(t['image']+0x38,17)
        e.put(t['obj']+0x2e4,100)
    yield case('attack occluded by collision tile',0x485d90,blocked_attack)
    for dy in (-51,-50,-49,0,49,50,51):
        for excluded in (False,True):
            for probability in (0,1,50,100):
                def configure(e,t,dy=dy,excluded=excluded,probability=probability):
                    collision_setup(e,t)
                    e.put(t['image']+0x38,0xffffffff if excluded else 17)
                    e.put(t['player']+0x50,80+dy)
                    e.put(t['obj']+0x2e4,probability)
                    e.override(0x4a3050,sequence(49))
                yield case('attack geometry %d excluded %s probability %d'%(dy,excluded,probability),0x485d90,configure)


def resource_setup(e,t,populated):
    manager=e.object(0x40,'resource-manager',fill=0)
    e.put(t['image']+0xc,manager)
    for off in (0x28,0x2c):
        container=e.object(0x30,'resources',fill=0)
        e.put(manager+off,container)
        e.put(container+0x18,1)
        if populated and off==0x2c:
            frame=e.object(0x30,'frame',fill=0)
            e.put(frame+0x1c,7)
            frames=e.object(4,'frames',words=[frame])
            animation=e.object(0x20,'animation',fill=0)
            e.put(animation+0xc,frames,1)
            head=0
            for name in ('LEVEL_ROBBERTHIEF_STRIKE1','LEVEL_ROBBERTHIEF_STRIKE2','GAME_NULL','LEVEL_ROBBERTHIEF_FASTADVANCE','LEVEL_ROBBERTHIEF_FALL','LEVEL_ROBBERTHIEF_HITLOW','LEVEL_ROBBERTHIEF_HITHIGH','LEVEL_ROBBERTHIEF_HOME','LEVEL_ROBBERTHIEF_IDLE','LEVEL_ROBBERTHIEF_LIFTED','LEVEL_ROBBERTHIEF_LIFTED2','LEVEL_ROBBERTHIEF_JUMP','LEVEL_ROBBERTHIEF_THROWN'):
                animation=e.object(0x20,'distinct-animation',fill=0)
                e.put(animation+0xc,frames,1)
                key=e.object(len(name)+1,'key',data=name.encode()+b'\0')
                head=e.object(16,'map-node',words=[head,0,key,animation])
            buckets=e.object(4,'buckets',words=[head])
            e.put(container+0x14,buckets)
        elif populated:
            sound=e.object(0x20,'sound-entry',fill=0)
            map_values(e,container,[(name,sound) for name in ('LEVEL_ROBBERTHIEF_00340014','LEVEL_ROBBERTHIEF_00340012','LEVEL_ROBBERTHIEF_ARROWHIGH','LEVEL_ROBBERTHIEF_ARROWLOW','LEVEL_ROBBERTHIEF_00340004','LEVEL_ROBBERTHIEF_00360002','LEVEL_ROBBERTHIEF_00360009','LEVEL_ROBBERTHIEF_00360010','LEVEL_ROBBERTHIEF_00340010')])
    t['manager']=manager


def collision_setup(e,t,blocked=False):
    e.put(0x534eac,0)
    world=e.object(0x20,'world',fill=0)
    manager=e.object(0x40,'world-manager',fill=0)
    collision=e.object(0x70,'collision-world',fill=0)
    grid=e.object(0xA0,'grid',fill=0)
    cells=e.object(4,'cells',words=[0xffffffff])
    rows=e.object(4,'rows',words=[0])
    e.put(t['obj']+0x190,world)
    e.put(world+0xc,manager)
    e.put(manager+0x24,collision)
    e.put(collision+0x5c,grid)
    e.put(grid+0x20,cells,rows)
    e.put(grid+0x30,1024,1024)
    e.put(grid+0x8c,10,10)
    if blocked:
        tile=e.object(4,'collision-tile',fill=0)
        methods=e.object(0x24,'tile-vtable',fill=0)
        def effect(e,c):
            e.put(t['record']+0x40,c.receiver,*c.arguments)
            return 1
        e.put(methods+0x20,e.stub('tile-collision','thiscall',2,effect))
        e.put(tile,methods)
        entries=e.object(4,'tiles',words=[tile])
        e.put(collision+0x4c,entries)
        e.put(cells,0)


def map_values(e,container,values):
    head=0
    for name,value in values:
        key=e.object(len(name)+1,'resource-key',data=name.encode()+b'\0')
        head=e.object(16,'resource-map-node',words=[head,0,key,value])
    buckets=e.object(4,'resource-buckets',words=[head])
    e.put(container+0x14,buckets,1)


def firing_setup(e,t,velocity,mirrored,first_sentinel,second_sentinel,sound,mutate=False):
    resource_setup(e,t,False)
    manager=t['manager']
    image_map=e.object(0x30,'projectile-image-map',fill=0)
    e.put(image_map+0x18,1)
    e.put(manager+0x10,image_map)
    definitions=e.object(0x30,'definitions',fill=0)
    e.put(manager+0x14,definitions)
    spawner=e.object(0x40,'spawner',fill=0)
    e.put(spawner+0xc,manager)
    e.put(spawner+0x28,8)
    e.put(manager+8,spawner)
    e.put(t['obj']+0x130,t['image'])
    runtime=e.object(0x160,'projectile-runtime',fill=0x67)
    sprite=e.object(0x150,'projectile-sprite',fill=0)
    e.put(runtime+0x12c,sprite)
    e.put(runtime+0x138,23,0x78787878,51)
    e.put(sprite+0x40,mirrored | 0xa5a55a58)
    e.put(sprite+0x118,0x80000000 if first_sentinel else 31,0x98989898,67)
    e.put(sprite+0x128,0x80000000 if second_sentinel else 43,0x89898989,79)
    e.put(sprite+0x138,29,0x68686868,83)
    def initialize(e,c):
        bullet=c.arguments[0]
        logic=e.get(bullet+0x6c)
        e.put(t['record'],bullet,e.get(bullet+0x104),e.get(bullet+0xd0),e.get(t['obj']+0x1a0))
        e.put(logic+0x18,runtime)
        if mutate:
            e.put(t['obj']+0x458,31337)
        return 0
    callback=e.stub('initialize-projectile','cdecl',1,initialize)
    definition=e.object(0x18,'Bullet-definition',fill=0)
    e.put(definition+0x10,callback)
    map_values(e,definitions,[('Bullet',definition)])
    e.put(t['image']+0x190,0x13579)
    e.put(t['image']+0x19c,17,0,0)
    e.put(t['image']+0x1ac,1)
    e.put(t['obj']+0x450,0xffffffbf,20,velocity)
    e.put(t['image']+0x64,23)
    if sound:
        sound_resource=e.object(0x20,'sound-resource',fill=0)
        sound_object=e.object(0x20,'sound-object',fill=0)
        sound_context=e.object(0x80,'sound-context',fill=0)
        e.put(sound_resource+0x10,sound_object)
        e.put(sound_object+0x10,sound_context)
        e.put(t['obj']+0x3b4,sound_resource)
    e.put(0x532c0c,1 if sound==2 else 0)
