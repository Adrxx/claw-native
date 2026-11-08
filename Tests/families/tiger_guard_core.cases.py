"""Tiger guard inputs built from original object and container layouts."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def actor(env, seed=31, direction=2, mirrored=0, animation=False):
    obj = env.object(0x500, 'guard', fill=0)
    sprite = env.object(0x200, 'sprite', fill=0)
    props = env.object(0x180, 'properties', fill=0)
    state = env.object(0x180, 'state', fill=0)
    player = env.object(0x200, 'player', fill=0)
    vt = env.object(0x100, 'virtual methods', fill=0)
    log = env.object(0x100, 'callback observations', fill=0)
    env.put(obj, vt)
    env.put(obj+0xc, props, state)
    env.put(obj+0x12c, sprite)
    env.put(obj+0x18c, direction)
    env.put(obj+0x184, 4)
    env.put(obj+0x138, seed, seed+7, -seed-13)
    env.put(sprite+0x40, mirrored | 0x140)
    env.put(sprite+8, 0x121)
    for off in (0x118, 0x128, 0x138):
        env.put(sprite+off, seed+off, 7, seed+off+19)
    env.put(sprite+0x18c, sprite)
    env.put(obj+0x194, sprite)
    env.put(state+0x1c, 7)
    env.put(player+0x4c, seed+101, seed+201)
    env.put(0x537e88, player)
    env.put(0x537680, 0)  # empty state-name trie
    env.put(0x532c0c, 0)
    env.put(0x5430c4, 17)
    env.put(0x537210, 1000)
    env.put(0x5262b0, struct.unpack('<I', struct.pack('<f', 1.375))[0])
    for off in (0x50, 0x54, 0x4dc, 0x4cc, 0x134, 0x498, 0x49c):
        env.put(obj+off, seed+off)
    env.put(obj+0x498, 100)
    env.put(obj+0x49c, 50)
    env.put(0x53c9ac, 0)
    def callback(env, call):
        env.put(log, env.get(log)+1, call.receiver, env.get(obj+0x4dc), env.get(obj+0x50), env.get(obj+0x54))
        return 0x12340000 | seed
    stub = env.stub('guard virtual observation', 'thiscall', 0, callback)
    for off in range(0, 0x100, 4):
        env.put(vt+off, stub)
    if animation:
        anim = env.object(0x30, 'animation', fill=0)
        frame = env.object(0x40, 'animation frame', fill=0)
        frames = env.object(4, 'frame array', words=[frame])
        env.put(anim+0xc, frames, 1)
        env.put(frame+0xc, 9)
        env.put(frame+0x18, 100, seed+23)
        env.put(obj+0x350, anim)
        env.put(obj+0x45c, anim)
    return dict(obj=obj, sprite=sprite, props=props, state=state, player=player, log=log)


def action(function, label, seed=31, direction=2, mirrored=0, rand=(0,40,1,0), animation=False, **fields):
    def setup(env):
        t = actor(env, seed, direction, mirrored, animation)
        for key, value in fields.items():
            env.put(t['obj']+int(key[1:],16), value)
        env.override(0x4a3050, sequence(*rand))
        return t
    return Case(label, function, setup, receiver=lambda t:t['obj'])


def dispatch(label, index, entry=True):
    def setup(env):
        obj = env.object(0x500, 'dispatch receiver', fill=0x69)
        log = env.object(32, 'dispatch observations', fill=0)
        error = env.object(32, 'error sink', fill=0)
        env.put(error+0xc, 4)
        def callback(tag):
            def called(env, call):
                env.put(log, call.receiver, env.get(0x53ca60), env.get(0x53ca48), env.get(0x53ca4c),tag)
                return 0x1234+tag
            return env.stub(f'state dispatch {tag}', 'thiscall', 0, called)
        stub=callback(91)
        data = env.object(12, 'dispatch table', words=[callback(i) if entry else 0 for i in range(3)])
        fallback = env.object(4, 'fallback callback', words=[stub])
        env.put(0x53ca44, error, 10, 12, data, fallback, 4, 0, 9)
        base_data = env.object(12, 'base dispatch table', words=[callback(i+10) for i in range(3)])
        env.put(0x53787c, error, index, index+2, base_data, fallback, 4, 0, 9)
        return dict(obj=obj)
    return Case(label, 0x493fd0, setup, receiver=lambda t:t['obj'], arguments=(index,))


def destruction(label, function, flags=0, heapbits=False, strings=False, refs=(1,2)):
    def setup(env):
        obj = env.object(0x500, 'destruction receiver', fill=0x37)
        sentinel = env.get(0x52e1c8)
        env.put(obj+0x1a4, sentinel+12, sentinel+12)
        if strings:
            for index,off in enumerate((0x1a4,0x1a8)):
                backing=env.object(32,f'owned string {index}',fill=0x61+index)
                env.put(backing,refs[index],7,19)
                env.put(obj+off,backing+12)
        if strings:
            observations=env.object(64,'string decrement observations',fill=0)
            def decrement(env,call):
                pointer=call.arguments[0]
                before=env.get(pointer)
                after=(before-1)&0xffffffff
                env.put(pointer,after)
                n=env.calls_so_far(0x5469e8)-1
                env.put(observations+n*16,pointer,before,after,env.get(obj))
                return after
            env.override(0x5469e8,decrement)
        env.put(obj+0x2fc, 64 if heapbits else 16)
        if heapbits:
            env.put(obj+0x300, env.object(8, 'dynamic bitset', fill=0x75))
        return dict(obj=obj)
    return Case(label, function, setup, receiver=lambda t:t['obj'], arguments=(flags,) if function==0x494a80 else ())


def basic_cases(random_source):
    for index in (10,11,12,9,13):
        yield dispatch(f'dispatch index {index}', index)
    yield dispatch('base dispatch fallback',10,False)
    for heapbits in (False, True):
        yield destruction(f'destructor bits {heapbits}',0x494aa0,heapbits=heapbits)
        for flags in (0,1,2,255,256):
            yield destruction(f'deleting destructor {flags} bits {heapbits}',0x494a80,flags,heapbits)
    for direction in (2,3,7):
        for mirrored in (0,2):
            for animation in (False,True):
                yield action(0x495130,f'lunge {direction} mirror {mirrored} animation {animation}',random_source.randrange(1,10000),direction,mirrored,animation=animation)
    for animation in (False,True):
        yield action(0x494cc0,f'idle animation {animation}',random_source.randrange(1,10000),animation=animation)
    yield action(0x495000,'cooldown callback',o498=995,o49c=6)
    yield action(0x495000,'cooldown unsigned wrap',o498=1001,o49c=0xffffffff)
    for direction in (2,3):
        for mirrored in (0,2):
            for branch in (0,39,40,79,80,100):
                yield action(0x495000,f'choice dir {direction} mirror {mirrored} rand {branch}',random_source.randrange(1,10000),direction,mirrored,rand=(751,branch,2,99))
    for flag in (0,1):
        for entered in (0,1):
            for state in range(8):
                for chance in (0,100):
                    def setup(env,flag=flag,entered=entered,state=state,chance=chance):
                        t=actor(env,37)
                        env.put(t['obj']+0x4d0,flag,entered)
                        env.put(t['obj']+0x184,state)
                        env.put(0x534eac,0x26b7)
                        env.override(0x4a3050,sequence(chance,2,100,0))
                        return t
                    yield Case(f'home bypass flags {flag} {entered} state {state} rand {chance}',0x494d40,setup,receiver=lambda t:t['obj'])
    for pending in (0,1):
        for delta in (-50,-49,0,49,50):
            for chance in (0,50,100):
                def setup(env,pending=pending,delta=delta,chance=chance):
                    t=actor(env,41,3,2)
                    obj,sprite=t['obj'],t['sprite']
                    env.put(obj+0x4d0,pending,0)
                    env.put(0x534eac,0)
                    world=env.object(0x100,'world',fill=0)
                    desc=env.object(0x100,'world descriptor',fill=0)
                    collision=env.object(0x100,'collision map',fill=0)
                    grid=env.object(0x100,'tile grid',fill=0)
                    tiles=env.object(4,'tiles',words=[0xeeeeeeee])
                    rows=env.object(4,'rows',words=[0])
                    env.put(obj+0x190,world)
                    env.put(world+0xc,desc)
                    env.put(desc+0x24,collision)
                    env.put(collision+0x5c,grid)
                    env.put(grid+0x20,tiles,rows)
                    env.put(grid+0x30,1024,1024)
                    env.put(grid+0x8c,10,10)
                    env.put(sprite+0x38,1)
                    env.put(sprite+0x4c,100,200)
                    env.put(t['player']+0x4c,150,200+delta)
                    env.override(0x4a3050,sequence(chance,2,100,0))
                    return t
                yield Case(f'home line pending {pending} dy {delta} chance {chance}',0x494d40,setup,receiver=lambda t:t['obj'])

def audio_cases(random_source):
    def audio(env):
        t=actor(env,79)
        sound=env.object(0x30,'sound',fill=0)
        voice=env.object(0x30,'voice',fill=0)
        service=env.object(0x90,'sound service',fill=0)
        env.put(t['obj']+0x490,sound)
        env.put(sound+0x10,voice)
        env.put(voice+0x10,service)
        env.put(0x532c0c,1,37)
        return t
    yield Case('lunge audio service unavailable',0x495130,audio,receiver=lambda t:t['obj'])

def empty_map(env,name):
    obj=env.object(0x40,name,fill=0)
    env.put(obj+0x18,1)
    return obj


def constructor(variant, populated=False, scale=1.0, omit=None, missing_sound=None):
    def setup(env):
        t=actor(env,43)
        obj,sprite,props,state=t['obj'],t['sprite'],t['props'],t['state']
        env.put(obj+0x4ac,0x7135a9c1)
        env.put(obj+0x4bc,0x29e86b43)
        desc=env.object(0x80,'resource catalogs',fill=0)
        for off in (0x10,0x14,0x28,0x2c):
            env.put(desc+off,empty_map(env,f'catalog {off:x}'))
        env.put(sprite+0xc,desc)
        env.put(props+0xc,desc)
        collision=env.object(0x100,'position service',fill=0)
        env.put(desc+0x24,collision)
        env.put(props+0x6c,state)
        env.put(props+0x108,variant)
        env.put(props+0x4c,93,147)
        env.put(state+0x68,7)
        if populated:
            catalog=env.get(desc+0x2c)
            names=(0x52cd8c,0x52cd74,0x52cd60,0x52cd4c,0x52cd38,0x52cd24,0x52cd0c,0x52ccf8,0x52cce4,0x52ccd0,0x52ccbc,0x52cca8,0x52cc90,0x52cc78,0x52cc64,0x5234b4)
            head=0
            for index,key in enumerate(names):
                if index==omit:
                    continue
                animation=env.object(0x30,f'animation {index}',fill=0)
                frame=env.object(0x40,f'frame {index}',fill=0)
                frames=env.object(4,f'frames {index}',words=[frame])
                env.put(animation+0xc,frames,1)
                env.put(frame+0xc,13+index)
                env.put(frame+0x18,70+index,301+index)
                head=env.object(16,f'animation lookup {index}',words=[head,0,key,animation])
            bucket=env.object(4,'animation bucket',words=[head])
            env.put(catalog+0x14,bucket)
            sounds=env.get(desc+0x28)
            sound_keys=(0x52cc48,0x52cc2c,0x52cc10,0x52cbf4,0x52cbd8,0x52cbbc,0x52cba0,0x52cb84,0x52cb68,0x52cb4c,0x52cb14,0x52cafc,0x52cae4,0x52cacc)
            head=0
            for index,key in enumerate(sound_keys):
                if index==missing_sound:
                    continue
                resource=env.object(0x30,f'sound resource {index}',fill=0x31+index)
                head=env.object(16,f'sound lookup {index}',words=[head,0,key,resource])
            env.put(sounds+0x14,env.object(4,'sound bucket',words=[head]))
        env.put(0x5262b8,struct.unpack('<I',struct.pack('<f',scale))[0])
        return dict(t,argument=props)
    return Case(f'constructor variant {variant} populated {populated} omit {omit} missing sound {missing_sound} scale {scale}',0x494460,setup,receiver=lambda t:t['obj'],arguments=(lambda t:t['argument'],))

def empty_constructor_cases(random_source):
    yield constructor(0)
    yield constructor(1,scale=0.25)


def update(name='LS_HOME',direction=2,state=3,active=1,face=0,elapsed=500,threshold=500,chance=0,count=2):
    def setup(env):
        t=actor(env,61,direction)
        obj,sprite=t['obj'],t['sprite']
        env.put(0x534eac,0x26b7)
        env.put(0x541334,1)
        parent=env.object(0x200,'carrying actor',fill=0)
        parent_state=env.object(0x180,'carrying state',fill=0)
        env.put(parent+0x164,0x8000)
        env.put(parent+0x6c,parent_state)
        env.put(parent_state+0x1c,5)
        env.put(sprite+8,0x10)
        env.put(sprite+0x80,parent)
        env.put(obj+0x20,count)
        env.put(obj+0x184,state)
        env.write(obj+0x68,struct.pack('<d',100.0))
        env.put(t['player']+0x4c,200 if direction==2 else 0)
        controls=env.object(0x100,'target state',fill=0)
        buttons=env.object(0x100,'target controls',fill=0)
        env.put(t['player']+0x6c,controls)
        env.put(controls+0x14,buttons)
        env.put(buttons,face,active)
        env.put(obj+0x4a8,(1000-elapsed)&0xffffffff,threshold)
        env.put(obj+0x4c8,40)
        text=env.object(len(name)+1,'state name',data=name.encode()+b'\0')
        data=env.object(4,'state-name table',words=[text])
        error=env.object(32,'registry error',fill=0)
        env.put(error+0xc,4)
        fallback=env.object(4,'name fallback',words=[text])
        env.put(0x53769c,error,7,7,data,fallback,4,0,0)
        env.override(0x4a3050,sequence(chance,0,0))
        return t
    return Case(f'update {name} dir {direction} state {state} active {active} face {face} elapsed {elapsed}/{threshold} chance {chance} count {count}',0x494b10,setup,receiver=lambda t:t['obj'],arguments=(0x5234b4,))

def update_cases(random_source):
    for name in ('LS_BACKFLIP','LS_FRONTFLIP','LS_BLOCK','LS_LUNGEATTACK','LS_HOME'):
        yield update(name)
    for direction,face in ((2,0),(2,1),(3,0),(3,1)):
        for state in (2,3,4):
            for chance in (0,39,40,99):
                yield update(direction=direction,face=face,state=state,chance=chance)
    for active in (0,1):
        for count in (0,1,2,0xffffffff):
            for elapsed,threshold in ((499,500),(500,500),(501,500),(0xffffffff,500)):
                yield update(active=active,count=count,elapsed=elapsed,threshold=threshold,chance=random_source.randrange(100))


def growing_update(index=8):
    def setup(env):
        t=update().setup(env)
        # The first original lookup grows the registry to this initial id.
        # Later lookups see its stable id and already expanded bounds.
        env.put(t['state']+0x1c,index)
        return t
    return Case(f'update registry initial growth to {index}',0x494b10,setup,receiver=lambda t:t['obj'],arguments=(0x5234b4,))

def cases(random_source):
    yield from basic_cases(random_source)
    yield from audio_cases(random_source)
    yield from empty_constructor_cases(random_source)
    yield from update_cases(random_source)
    for variant in (0,1):
        yield constructor(variant,True,1.75)
        for omit in range(16):
            yield constructor(variant,True,0.125 if omit%2 else 2.0,omit)
    for index in (8,9,10):
        yield growing_update(index)

    # Deterministic edges keep coverage independent of the admission seed.
    for count in (0,1,2,0xffffffff):
        yield update(count=count,chance=0)
    for chance in (0xffffffff,100,101,0x7fffffff):
        yield update(chance=chance)
    for tick,timeout in ((0,0),(0,1),(1000,0),(1000,1),(1001,0xffffffff)):
        yield action(0x495000,f'cooldown boundary {tick} {timeout}',o498=tick,o49c=timeout)

    for refs in ((1,2),(2,1),(0xffffffff,1),(0,3)):
        yield destruction(f'destructor owned strings refs {refs}',0x494aa0,strings=True,refs=refs)
        yield destruction(f'deleting destructor owned strings refs {refs}',0x494a80,flags=1,strings=True,refs=refs)

    # Preserve distinct preexisting timers and partial lookup outputs.
    for threshold in (0,1,499):
        yield update(threshold=threshold,elapsed=500,chance=0,count=2)
    for missing_sound in (0,1,2):
        yield constructor(1,True,1.25,missing_sound=missing_sound)
