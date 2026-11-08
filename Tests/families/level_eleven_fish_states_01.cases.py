"""Independent fish-state inputs derived from original instruction paths."""
import itertools
import struct
from clawparity.cases import Case


def zobject(env, *args, **kwargs):
    kwargs.setdefault("fill",0)
    return env.object(*args, **kwargs)


def dbl(env, address, value):
    env.write(address, struct.pack('<d', value))


def setup_state(options):
    def setup(env):
        o = options
        fish = zobject(env,0x440, 'fish', fill=0x51)
        actor = zobject(env,0x220, 'actor')
        logic = zobject(env,0x200, 'logic')
        player = zobject(env,0x160, 'player')
        methods = zobject(env,0x60, 'fish virtuals')
        seen = zobject(env,0x40, 'callback observations')
        def callback(env, call):
            env.put(seen, env.get(seen)+1, call.receiver, *(call.arguments or (0x12345678,)))
            env.put(seen+0x10, env.get(fish+0x1a0), env.get(actor+0x40), env.get(logic+0x1c))
            return 0xabcdef01
        for offset, argc in ((0x48,0),(0x58,0),(0x5c,1)):
            env.put(methods+offset, env.stub('fish method '+hex(offset), 'thiscall', argc, callback))
        env.put(fish, methods)
        env.put(fish+0xc, actor, logic)
        env.put(fish+0x12c, actor)
        env.put(fish+0x138, 0xfffffff5, 0x27, 0x16, 0x35)
        env.put(fish+0x210, 0xffffffe1, 0x43, 0x2b, 0x5d)
        env.put(fish+0x220, 0xffffffcb, 0x61, 0x3b, 0x71)
        env.put(actor+0x40, o.get('flip', 0)|0x80)
        for offset in (0x118,0x128,0x138):
            env.put(actor+offset, o.get('sentinel',0xfffffff9), 0x29, 0x13, 0x3d)
        env.put(actor+0xcc, o.get('mode',7))
        env.put(actor+0x16c, o.get('frame',0))
        env.put(actor+0x188+8, 0)
        env.put(actor+0x190, o.get('animation',0))
        env.put(actor+0x19c, o.get('anim_running',0))
        env.put(actor+0x1a4, o.get('anim_done',0))
        if o.get('active_animation'):
            definition=zobject(env,0x20,'active animation definition')
            env.put(actor+0x190,definition)
            env.put(actor+0x19c,7,1)
        env.put(logic+0x1c, 0x13579)
        env.put(fish+0x184, o.get('collision',0))
        env.put(fish+0x18c, o.get('side',2))
        env.put(fish+0x1a0, o.get('latched',0))
        for off in (0x310,0x3a0,0x400,0x404,0x408,0x40c,0x410,0x414):
            env.put(fish+off,0)
        env.put(fish+0x418, o.get('water',30), 10, 50, o.get('target',20), o.get('last',100), o.get('delay',250))
        for off,value in ((0x38,o.get('accel',1.0)),(0x40,0.0),(0x48,0.0),(0x50,o.get('speed',3.0)),(0x58,11.123456789),(0x60,13.234567891),(0x68,o.get('x',20.0)),(0x70,o.get('y',20.0)),(0x78,o.get('z',0.0)),(0x80,o.get('left',10.0)),(0x98,o.get('right',50.0))):
            dbl(env,fish+off,value)
        env.put(fish+0x2a8, o.get('range',300))
        env.put(player+0x4c,o.get('px',20),o.get('py',40))
        env.put(0x537e88,player)
        env.put(0x537210,o.get('clock',200))
        env.put(0x5430c4,1)
        env.put(0x532c0c,o.get('enabled',0))
        sound = zobject(env,0x20,'sound')
        context = zobject(env,0x80,'sound context')
        wrapper = zobject(env,0x14,'sound wrapper')
        env.put(wrapper+0x10,sound)
        env.put(sound+0x10,context)
        for off in o.get('sounds',()): env.put(fish+off,wrapper)
        env.put(0x5272cc,o.get('toggle',0))
        env.put(0x537668+0x18,0)
        env.override(0x4a3050,lambda env,call:o.get('rand',95))
        return {'fish':fish,'actor':actor,'logic':logic,'seen':seen}
    return setup


def state(label, function, **options):
    return Case(label,function,setup_state(options),receiver=lambda t:t['fish'])


def cases(random_source):
    for function in (0x442640,0x442b00,0x442d80,0x442f70):
        yield state('animation countdown '+hex(function),function,active_animation=True)
    for speed,x,flip,sentinel in itertools.product((-3.75,0.0,0.75,3.75),(10.0,20.0,50.0),(0,2),(0x80000000,0xfffffff9)):
        yield state('reset '+str((speed,x,flip,sentinel)),0x442470,speed=speed,x=x,flip=flip,sentinel=sentinel)
    for x,flip,collision,side,speed,rand in itertools.product((10.0,20.0,50.0),(0,2),(3,),(2,3),(-3.0,3.0),(79,90)):
        if collision==0 and rand!=79: continue
        yield state('idle '+str((x,flip,collision,side,speed,rand)),0x442640,x=x,flip=flip,collision=collision,side=side,speed=speed,rand=rand,py=10 if rand in (79,80) else 40)
    for px,rand in itertools.product((9,10,20,50,51),(89,90)):
        yield state('idle water attack '+str((px,rand)),0x442640,collision=3,side=2,speed=3.0,px=px,rand=rand,py=40)
    yield state('idle jump rejected boundary',0x442640,collision=3,side=2,speed=3.0,rand=80,py=10)
    yield state('unordered jump acceleration',0x4427d0,accel=float('nan'))
    for flip,side in itertools.product((0,2),(2,3)):
        yield state('jump launch '+str((flip,side)),0x4427d0,flip=flip,side=side)
        yield state('strike launch '+str((flip,side)),0x442cb0,flip=flip,side=side)
    for done,running,mode,flip,frame,latched,y,x in itertools.product((0,1),(0,1),(1,7),(0,2),(0,202),(0,1),(20.0,31.0),(9.0,20.0,51.0)):
        if done+running+mode+flip+frame+latched not in (1,7,210): continue
        yield state('jump tick '+str((done,running,mode,flip,frame,latched,y,x)),0x442b00,anim_done=done,anim_running=running,mode=mode,flip=flip,frame=frame,latched=latched,y=y,x=x)
    for speed,x,flip,frame,latched in itertools.product((-3.0,0.0,3.0),(19.0,20.0,21.0),(0,2),(0,202),(0,1)):
        yield state('strike tick '+str((speed,x,flip,frame,latched)),0x442d80,speed=speed,x=x,flip=flip,frame=frame,latched=latched)
    for x in (49.25,50.0,51.75,-5.5):
        yield state('flop launch '+str(x),0x442e90,x=x)
    for clock,last,delay,toggle,flip,x,y in itertools.product((200,350,351,0),(100,), (250,), (0,1),(0,2),(9.0,20.0,51.0),(20.0,31.0)):
        yield state('flop tick '+str((clock,toggle,flip,x,y)),0x442f70,clock=clock,last=last,delay=delay,toggle=toggle,flip=flip,x=x,y=y)
    for done,mode in ((1,7),(0,1)):
        yield state('mirrored jump restore '+str((done,mode)),0x442b00,flip=2,anim_done=done,mode=mode)
    for function in (0x4427d0,0x442b00,0x442d80,0x442e90,0x442f70):
        for enabled in (0,1):
            yield state('sounds '+str((function,enabled)),function,sounds=(0x3a0,0x40c,0x410,0x414),enabled=enabled,frame=202,y=31.0,clock=350)
    for function in (0x442470,0x442640,0x4427d0,0x442b00,0x442cb0,0x442d80,0x442e90,0x442f70):
        yield state('varied values '+hex(function),function,x=random_source.uniform(11,49),speed=random_source.choice((-1,1))*random_source.uniform(1,8),water=random_source.randrange(25,40),target=random_source.randrange(12,48),clock=random_source.getrandbits(32))
    for flag in (None,0,1,2,255):
        def destruct(env,flag=flag):
            t=setup_state({})(env)
            f=t['fish']
            env.put(f+0x2f4+8,0)
            env.put(f+0x1a4,env.get(0x52e1c8)+12,env.get(0x52e1c8)+12)
            return t
        yield Case('destructor '+str(flag),0x442400 if flag is None else 0x4423e0,destruct,receiver=lambda t:t['fish'],arguments=() if flag is None else (flag,))
    for grow,registered in itertools.product((-1,0,1),(0,1)):
        def dispatch(env,grow=grow,registered=registered):
            t=setup_state({})(env)
            entries=zobject(env,12,'state methods')
            method=env.stub('registered state','thiscall',0,lambda env,call:0x761234)
            env.put(entries,method if registered else 0,method,method)
            # The base fallback dispatcher has an actual registered callback.
            base_entries=zobject(env,20,'base state methods',words=[method]*5)
            env.put(0x537638+8,0xffffffff,3,base_entries,0,4)
            env.put(0x5376f8+8,0,2,entries,0,4)
            t['key']=-1 if grow<0 else 3 if grow>0 else 0
            return t
        yield Case('dispatch '+str((grow,registered)),0x441d00,dispatch,receiver=lambda t:t['fish'],arguments=(lambda t:t['key'],))
    for dead,kind,count in itertools.product((0,1),(0,32),(0,2)):
        def notify(env,dead=dead,kind=kind,count=count):
            t=setup_state({})(env)
            name=zobject(env,16,'state name',data=b'LS_DEAD\0' if dead else b'ES_IDLE\0')
            entry=zobject(env,4,'reverse state',words=[name])
            cleanup=zobject(env,8,'temporary string pointers')
            env.put(0x537698+8,0x13579,0x13579,entry,0,4,cleanup,count)
            env.put(t['actor']+0x74,t['actor'])
            env.put(t['actor']+0xd0,kind)
            return t
        yield Case('notify '+str((dead,kind,count)),0x4430f0,notify,receiver=lambda t:t['fish'])
    for key in (-1,1):
        def notify_grow(env,key=key):
            t=setup_state({})(env)
            text=zobject(env,8,'old state name',data=b'LS_DEAD\0')
            entries=zobject(env,4,'reverse names',words=[text])
            env.put(0x537698+8,0,0,entries,0,4,0,0)
            env.put(t['logic']+0x1c,key)
            env.put(t['actor']+0x74,t['actor'])
            env.put(t['actor']+0xd0,32)
            return t
        yield Case('reverse state grow '+str(key),0x4430f0,notify_grow,receiver=lambda t:t['fish'])
    yield Case('constructor frame aliases receiver rectangles',0x4420e0,setup_constructor(True,0,10,alias_frame=True),receiver=lambda t:t['fish'],arguments=(lambda t:t['actor'],))
    yield Case('constructor heap bitset default',0x4420e0,setup_constructor(True,0,10,64),receiver=lambda t:t['fish'],arguments=(lambda t:t['actor'],))
    for existing in (False,True):
        for direction in (0,2):
            for water in (0,10):
                yield Case('constructor '+str((existing,direction,water)),0x4420e0,setup_constructor(existing,direction,water),receiver=lambda t:t['fish'],arguments=(lambda t:t['actor'],))


def resource_map(env,names):
    resource=zobject(env,0x40,'resource map owner')
    buckets=zobject(env,4,'resource map buckets')
    node=0
    for name,value in names.items():
        text=zobject(env,len(name)+1,'resource name',data=name.encode()+b'\0')
        node=zobject(env,16,'resource node',words=[node,0,text,value])
    env.put(buckets,node)
    env.put(resource+0x14,buckets,1)
    return resource


def setup_constructor(existing,direction,water,default_bits=32,alias_frame=False):
    def setup(env):
        t=setup_state({'flip':direction})(env)
        env.put(0x533470,default_bits)
        actor,logic=t['actor'],t['logic']
        world=zobject(env,0x100,'world')
        collision=zobject(env,0x80,'collision')
        env.put(actor+0xc,world)
        env.put(actor+0x6c,logic)
        env.put(actor+0x104,water)
        env.put(actor+0x4c,23,31)
        env.put(logic+0x2c,11,53,0,0)
        env.put(logic+0x64,0)
        env.put(logic+0x68,17)
        frame=zobject(env,0x30,'animation frame')
        env.put(frame+0x1c,0x773)
        frames=zobject(env,4,'animation frames',words=[frame])
        anim=zobject(env,0x20,'animation definition')
        env.put(anim+0xc,frames,1)
        names=['LEVEL_FISH_SWIM','LEVEL_FISH_STRIKE1','LEVEL_FISH_KILLFALL','LEVEL_FISH_HIT','LEVEL_FISH_FLOUNDER']
        values={name:anim for name in names} if existing else {'GAME_NULL':anim}
        sprite_frame=t['fish']+0x1f0 if alias_frame else zobject(env,0x30,'sprite frame')
        if not alias_frame: env.put(sprite_frame+0x18,3,5,17,29)
        sprite_frames=zobject(env,4,'sprite frames',words=[sprite_frame])
        sprite=zobject(env,0x70,'sprite')
        env.put(sprite+0x14,sprite_frames)
        env.put(sprite+0x64,0,0)
        sprite_names={'LEVEL_FISH':sprite} if existing else {}
        sound_names={name:zobject(env,0x20,name) for name in ('LEVEL_FISH_CHOMP1','LEVEL_FISH_FISHDEATH','LEVEL_FISH_FISHFLOP','LEVEL_FISH_WATERIN','LEVEL_FISH_WATEROUT')}
        env.put(world+0x10,resource_map(env,sprite_names),resource_map(env,{}))
        env.put(world+0x24,collision,resource_map(env,sound_names),resource_map(env,values))
        env.put(actor+0x188+8,0)
        return t
    return setup
