"""Original-behavior cases for the Raux core."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate, reallocate


def floats(env, address, *values):
    env.write(address, struct.pack('<' + 'f' * len(values), *values))


def record(env, log, tag, call, obj=0):
    n = env.get(log)
    env.put(log, n + 1)
    env.put(log + 4 + n * 32, tag, call.receiver, len(call.arguments),
            *(list(call.arguments[:2]) + [0, 0])[:2],
            env.get(obj + 0x14) if obj else 0,
            env.get(obj + 0x20) if obj else 0,
            env.get(obj + 0x3c4) if obj else 0)



def rectangle_is(call, destination, left, top, right, bottom):
    return call.arguments == tuple(value & 0xffffffff for value in
                                  (destination,left,top,right,bottom))

def base(env, data):
    obj = env.object(0x478, 'raux', data=data)
    ent = env.object(0x180, 'entity', fill=0)
    state = env.object(0x40, 'logic-state', fill=0)
    vt = env.object(0xc0, 'vtable', fill=0)
    log = env.object(4096, 'callback-log', fill=0)
    env.put(obj, vt)
    env.put(obj + 0xc, ent, state)
    env.put(ent + 0x6c, state)
    env.put(obj + 0x128, 0, ent)
    return dict(obj=obj, ent=ent, state=state, vt=vt, log=log)


def callback(env, t, offset, argc=0, mutate=False):
    def effect(env, call):
        record(env, t['log'], offset, call, t['obj'])
        if mutate:
            env.put(t['obj'] + 0x20, 0x12345678)
        return 0xabc00000 + offset
    ptr = env.stub('observe-%x' % offset, 'thiscall', argc, effect)
    env.put(t['vt'] + offset, ptr)
    return ptr


def cleanup_setup(data, width=0, refs=(1, 2)):
    def setup(env):
        t = base(env, data)
        env.put(t['obj'] + 0x2fc, width)
        if width > 32:
            env.put(t['obj'] + 0x300, env.object(16, 'bitset-storage', fill=0x81))
        for off, ref in zip((0x1a4, 0x1a8), refs):
            s = env.object(32, 'cstring-data', words=[ref, 4, 16, 0x41424344])
            env.put(t['obj'] + off, s + 12)
        def decrement(env, call):
            ptr = call.arguments[0]
            record(env, t['log'], 0xd, call, t['obj'])
            value = (env.get(ptr) - 1) & 0xffffffff
            env.put(ptr, value)
            return value
        env.override(0x5469e8, decrement)
        return t
    return setup


def dispatch_setup(data, state, kind, stride=4, null=False):
    def setup(env):
        t = base(env, data)
        ptr = callback(env, t, 0x80, mutate=True)
        table = env.object(stride * 5, 'dispatch-table', fill=0)
        fallback = env.object(4, 'dispatch-fallback', words=[0 if null else ptr])
        lo, hi = (-2, 2)
        for index in range(5):
            env.put(table + index * stride, 0 if null else ptr)
        error = env.object(32, 'error-object', words=[0, 0, 0, 4])
        env.put(0x53c148, 0, error, lo, hi, table, fallback, stride, 0, 0xcccccccc)
        parent = env.object(4, 'base-dispatch', words=[ptr])
        env.put(0x5349b8, 0, error, -100, 100, parent, parent, 0, 0, 0)
        if kind == 'fail':
            env.override(0x4a9070, reallocate(fail=True))
        return t
    return setup



def string_map(env, entries, name):
    owner = env.object(64, name, fill=0)
    buckets = env.object(4, name + '-buckets', fill=0)
    env.put(owner + 0x14, buckets, 1)
    last = 0
    for key, value in entries:
        text = env.object(len(key)+1, name+'-key', data=key.encode()+b'\0')
        node = env.object(16, name+'-node', words=[last, 0, text, value])
        last = node
    env.put(buckets, last)
    return owner


def attack_setup(data, range_value, selection, threshold, facing, control, enabled, mode, counter, health, mutate=False):
    def setup(env):
        t = base(env, data)
        obj, ent = t['obj'], t['ent']
        sprite = env.object(0x200, 'sprite', fill=0)
        owner = env.object(0x40, 'owner', fill=0)
        env.put(sprite + 0xc, owner)
        entries = [(name, 0x71000000+i*0x100) for i,name in enumerate(('LEVEL_STAB','LEVEL_STAB2','LEVEL_STAB3','LEVEL_RAUX_BLOCK1','LEVEL_RAUX_BLOCK2'))]
        env.put(owner + 0x28, string_map(env,entries,'sounds'))
        env.put(obj + 0x128, ent, sprite)
        env.put(obj + 0x184, mode)
        env.put(obj + 0x2fc, 32, 0x34560000)
        env.put(obj + 0x20, counter)
        env.put(obj + 0x2e4, health)
        env.write(obj + 0x68, struct.pack('<d', 100.5))
        env.put(0x534eac, 0x26b7)
        env.put(0x541334, 0)
        env.put(ent + 8, 0x10)
        linked = env.object(0x180,'linked-entity', fill=0)
        linked_state = env.object(0x40,'linked-state',fill=0)
        env.put(linked+0x164,0x8000)
        env.put(linked+0x6c,linked_state)
        env.put(linked_state+0x1c,5)
        env.put(sprite+8,0x10)
        env.put(sprite+0x80,linked)
        world = env.object(0x180,'world',fill=0)
        worldstate = env.object(0x40,'world-state',fill=0)
        controls = env.object(0x20,'controls',words=[control,enabled,0,0,0,0])
        env.put(world+0x6c,worldstate)
        env.put(worldstate+0x14,controls)
        env.put(world+0x4c, 99 if facing == 3 else 101)
        env.put(0x537e88,world)
        def rng(env,call):
            record(env,t['log'],0xa3050,call,obj)
            n = env.calls_so_far(call.function)
            if mutate and n == 3:
                env.put(obj+0x2e4, health ^ 0x7fffffff)
                env.put(obj+0x3c4, range_value)
                env.put(obj+0x20, 3-counter)
            return (range_value,selection,threshold)[min(n,3)-1] & 0xffffffff
        env.override(0x4a3050,rng)
        return t
    return setup


ANIM_NAMES = ('ADVANCE','FASTADVANCE','STRIKE','FALL','DEAD','HITLOW','HITHIGH','JUMP','JUMPBACK','HOME','HOME1','IDLE','LIFTED','LIFTED2','THROWN','BLOCKHIGH','BLOCKLOW')


def constructor_setup(data, present=False, scale=1.0, count=10, mutate_rect=False):
    def setup(env):
        t = base(env,data)
        obj = t['obj']
        # Base constructors treat the original entity as the sprite too.
        ent2=env.object(0x220,'complete-entity',fill=0)
        state2=env.object(0x180,'complete-logic',fill=0)
        t['ent'],t['state']=ent2,state2
        owner=env.object(0x80,'entity-owner',fill=0)
        physics=env.object(0x80,'physics',fill=0)
        env.put(owner+0x24,physics)
        env.put(ent2+0xc,owner)
        env.put(ent2+0x6c,state2)
        env.put(ent2+0x4c,123,456)
        env.put(ent2+0x118,0x80000000)
        empty=string_map(env,[],'empty-resources')
        for off in (0x10,0x14,0x28,0x2c):env.put(owner+off,empty)
        if present:
            entries=[]
            for i,name in enumerate(ANIM_NAMES+('NULL',)):
                frame=env.object(64,'animation-frame-'+name,fill=0)
                env.put(frame+0x1c,17+i)
                frames=env.object(4,'animation-frames-'+name,words=[frame])
                anim=env.object(32,'animation-'+name,fill=0)
                env.put(anim+0xc,frames,1)
                entries.append(('GAME_NULL' if name=='NULL' else 'LEVEL_RAUX_'+name,anim))
            env.put(owner+0x2c,string_map(env,entries,'animation-map'))
            env.put(owner+0x28,string_map(env,[('LEVEL_RAUX_00840005',0x73123123),('LEVEL_DOGINAIR',0x74234234)],'ctor-sounds'))
        env.put(0x537668+0x18,0)
        floats(env,0x5262b8,scale)
        floats(env,0x50f178,100.0)
        floats(env,0x5262b4,1.125)
        floats(env,0x5262b0,0.75)
        # The source bitset is copied by the original base constructor.
        env.put(0x534938,0x39)
        # SetRect is a physical fixture: observe publication and vary bitset count
        # after base construction, before the owned toggle reads it.
        def rect(env,call):
            env.put(call.arguments[0],*call.arguments[1:])
            record(env,t['log'],0x546d5c,call,obj)
            if rectangle_is(call,obj+0x220,-117,-4,-30,21):
                env.put(t['log']+3000,0x434f554e,call.arguments[0],env.calls_so_far(call.function),count)
                env.put(obj+0x2fc,count)
                if count>32:
                    env.put(obj+0x300,env.object(16,'ctor-bits',fill=0x39))
            if mutate_rect and rectangle_is(call,obj+0x260,-15,-60,15,52):
                env.put(t['log']+3040,0x52454354,*call.arguments,env.calls_so_far(call.function))
                env.put(obj+0x250,0xdead1234,0x12345678,0x80000000,0x7fffffff)
            return 1
        env.override(0x546d5c,rect)
        return t
    return setup


def react_setup(data, text, distance, high, mutate=False):
    def setup(env):
        t=base(env,data)
        obj,ent=t['obj'],t['ent']
        env.put(obj+0x3c4,distance)
        env.put(obj+0x184,3)
        env.put(obj+0x18c,3)
        env.put(ent+0x38,0xffffffff)
        env.put(obj+0x334,0,0)
        env.put(obj+0x414,0,0,0)
        env.put(obj+0x390,0,0,0,0)
        env.put(0x532c0c,0)
        env.put(0x537668+0x18,0)
        string=env.object(len(text)+1,'reaction-state',data=text.encode()+b'\0')
        cell=env.object(4,'reaction-cell',words=[string])
        tmp=env.object(16,'temporary-strings',fill=0)
        env.put(0x537698,0,0,0,0,cell,cell,4,tmp,0)
        env.put(t['state']+0x1c,0)
        for off,argc in ((0x44,0),(0x9c,0),(0x28,1)):
            callback(env,t,off,argc,mutate)
        if mutate:
            sibling=env.object(0x180,'reaction-new-entity',fill=0)
            env.put(sibling+0x38,0xffffffff)
            env.put(sibling+0x64,0x12345678)
            def changed_receiver(env,call):
                record(env,t['log'],0x28,call,obj)
                env.put(obj+0xc,sibling)
                env.write(obj+0x68,struct.pack('<dd',-37.125,93.875))
                return 0x84672
            env.put(t['vt']+0x28,env.stub('mutating-hit','thiscall',1,changed_receiver))
        world=env.object(0x80,'reaction-world',fill=0)
        ws=env.object(32,'reaction-world-state',fill=0)
        control=env.object(32,'reaction-control',fill=0)
        env.put(world+0x6c,ws)
        env.put(ws+0x14,control)
        env.put(control+0x14,high)
        env.put(0x537e88,world)
        env.override(0x4a3050,lambda env,call: 7)
        argument=env.object(0x180,'hit-argument',fill=0)
        env.put(argument+0x138,0x80000000)
        env.write(obj+0x68,struct.pack('<dd',17.25,-18.75))
        t['arg']=argument
        return t
    return setup


def factory_setup(data,state,present=False):
    def setup(env):
        if state==0:
            t=constructor_setup(data,present,1.25,10)(env)
        else:
            t=base(env,data)
        obj,entity,logic=t['obj'],t['ent'],t['state']
        env.put(entity+0x6c,logic)
        env.put(logic+0x18,obj,state)
        for off,argc in ((4,1),(8,1),(12,1),(0x1c,0),(0x20,0)):
            callback(env,t,off,argc,True)
        def initialize(env,call):
            record(env,t['log'],0x10,call,call.receiver)
            n=env.get(t['log'])
            env.put(t['log']+2048,env.get(logic+0x18),env.get(logic+0x1c),call.receiver,n)
            env.put(logic+0x1c,0x1234)
            return 0x12345678
        env.put(0x50f1ac+0x10,env.stub('factory-initialize','thiscall',0,initialize))
        # Default factory states call the original virtual dispatch helper.
        st=env.object(32,'factory-state-string',words=[1,7,16],data=None,fill=0)
        env.put(st,1,7,16)
        env.write(st+12,b'LS_IDLE\0')
        cell=env.object(4,'factory-state-cell',words=[st+12])
        env.put(0x537698,0,0,-0x10000,0x10000,cell,cell,0,0,0)
        env.put(t['state']+0x1c,state)
        return t
    return setup


def double_growth_setup(data):
    def setup(env):
        t=dispatch_setup(data,4,'grow',4,False)(env)
        ptr=env.get(t['vt']+0x80)
        def resizing(env,call):
            record(env,t['log'],0xa9070,call,t['obj'])
            result=env.object(max(4,call.arguments[1]),'mutable-growth',fill=0)
            env.put(result,ptr)
            env.put(0x53c160,0)
            if env.calls_so_far(call.function)==1:
                env.put(0x53c150,5)
            return result
        env.override(0x4a9070,resizing)
        return t
    return setup


def reaction_growth_setup(data,high):
    def setup(env):
        t=react_setup(data,'LS_IDLE',100,high)(env)
        # Lookup's temporary string initialization aliases the live state index.
        # That changes the second requested index and exercises a second resize.
        alias=env.object(4,'aliased-state-index',words=[0])
        env.put(t['obj']+0x10,alias-0x1c)
        env.put(0x537698+8,1,1)
        env.put(0x537698+0x18,0)
        def resizing(env,call):
            record(env,t['log'],0xa9070,call,t['obj'])
            if env.calls_so_far(call.function)>1:
                env.put(0x537698+0xc,env.get(alias)-1)
            return alias
        env.override(0x4a9070,resizing)
        return t
    return setup


def perturbed_constructor_setup(data, sentinels):
    def setup(env):
        t=constructor_setup(data,True,1.0,33)(env)
        obj=t['obj']
        def rect(env,call):
            env.put(call.arguments[0],*call.arguments[1:])
            record(env,t['log'],0x546d5c,call,obj)
            if rectangle_is(call,obj+0x260,-15,-60,15,52):
                env.put(t['log']+3072,0x50455254,*call.arguments,env.calls_so_far(call.function))
                for index,(offset,value) in enumerate(sentinels):
                    env.put(obj+offset,value)
                    env.put(t['log']+3136+index*12,offset,value,env.get(obj+offset))
            return 1
        env.override(0x546d5c,rect)
        return t
    return setup

def cases(random_source):
    data = bytes(random_source.randrange(1, 256) for _ in range(0x478))
    for scale in (0.0, 0.01, 0.995, 1.0, 1.125, -1.0, 123.456):
        def setup(env, scale=scale):
            t = base(env, data)
            env.put(t['obj'] + 0x450, 0x80000000, 0x7fffffff)
            floats(env, 0x5262b4, scale)
            return t
        yield Case('reset health %s' % scale, 0x47eeb0, setup, receiver=lambda t:t['obj'])
    for width in (0, 9, 10, 32, 33, 64):
        for refs in ((1,2), (2,1), (0,0)):
            yield Case('destructor %s %s' % (width, refs), 0x47e810, cleanup_setup(data,width,refs), receiver=lambda t:t['obj'])
    for flag in (0,1,2,3,0x100,0xffffffff):
        yield Case('deleting destructor %x' % flag, 0x47e7f0, cleanup_setup(data,33), receiver=lambda t:t['obj'], arguments=(flag,))
    for state in (-4,-2,0,2,4):
        for null in (False, True):
            for kind in ('grow',) if abs(state)>2 else ('inside',):
                yield Case('dispatch %d %s null%s' % (state,kind,null), 0x47e8e0, dispatch_setup(data,state,kind,8,null), receiver=lambda t:t['obj'], arguments=(state,))

    for distance in (-2147483648,-1,0,1,99,100,101,199,200,201,499,500,1000,2147483647):
        for counter in (1,2):
            for selection in (-2,-1,0,1,2):
                yield Case('attack range %d count%d select%d' % (distance,counter,selection), 0x47ece0,
                    attack_setup(data,distance,selection,0,3,1,1,3,counter,100),
                    receiver=lambda t:t['obj'],arguments=(0x52720c,))
    for facing,control,enabled,mode,health,threshold in (
        (2,0,1,3,100,99),(3,0,1,4,100,0),(2,1,1,3,100,0),
        (3,1,0,3,100,0),(3,1,1,2,100,0),(3,1,1,4,0,0),
        (3,1,1,4,99,99),(3,1,1,4,100,99),(3,1,1,4,-1,-2)):
        yield Case('attack conditions %s' % ((facing,control,enabled,mode,health,threshold),),0x47ece0,
            attack_setup(data,150,1,threshold,facing,control,enabled,mode,2,health),
            receiver=lambda t:t['obj'],arguments=(0x52720c,))

    for present in (False,True):
        for count in (0,9,10,32,33,64):
            yield Case('construct resources%s count%d' % (present,count),0x47e2d0,
                constructor_setup(data,present,1.5 if present else 0.5,count),
                receiver=lambda t:t['obj'],arguments=(lambda t:t['ent'],))
    for text in ('LS_HITLOW','LS_HITHIGH','LS_IDLE','ls_hitlow'):
        for distance in (-1,0,99,100,500):
            for high in (0,1):
                yield Case('react %s distance%d high%d' % (text,distance,high),0x47eef0,
                    react_setup(data,text,distance,high),receiver=lambda t:t['obj'],arguments=(lambda t:t['arg'],))

    for state in (0,1,28,29,30,31,999,1000,1001,0xffffffff):
        yield Case('factory state %x' % state,0x47e210,factory_setup(data,state),arguments=(lambda t:t['ent'],))
    yield Case('factory populated resources',0x47e210,factory_setup(data,0,True),arguments=(lambda t:t['ent'],))
    yield Case('dispatch repeats lookup after allocator changes bounds',0x47e8e0,double_growth_setup(data),receiver=lambda t:t['obj'],arguments=(4,))
    for high in (0,1):
        yield Case('reaction temporary cells change live index high%d' % high,0x47eef0,reaction_growth_setup(data,high),receiver=lambda t:t['obj'],arguments=(lambda t:t['arg'],))

    yield Case('constructor observes rect mutation before bounds copy',0x47e2d0,constructor_setup(data,True,1.0,33,True),receiver=lambda t:t['obj'],arguments=(lambda t:t['ent'],))
    for i in range(40):
        distance=random_source.randrange(-300,800)
        health=random_source.randrange(-2,103)
        threshold=random_source.randrange(-200,201)
        count=random_source.randrange(-1,5)
        selection=random_source.randrange(-0x80000000,0x80000000)
        yield Case('random mutable attack %d' % i,0x47ece0,
            attack_setup(data,distance,selection,threshold,3,1,1,4,count,health,True),
            receiver=lambda t:t['obj'],arguments=(0x52720c,))
    for high in (0,1):
        for distance in (-1,100,200):
            yield Case('hit callback replaces entity high%d range%d' % (high,distance),0x47eef0,
                react_setup(data,'LS_IDLE',distance,high,True),receiver=lambda t:t['obj'],arguments=(lambda t:t['arg'],))

    numeric_offsets=(0x28c,0x290,0x29c,0x2a0,0x2a4,0x2a8,0x2ac,0x2b0,0x2b4,0x2b8,0x2bc,0x2c0,0x2c4,0x2c8,0x2e4)
    for i in range(4):
        sentinels=tuple((off,random_source.randrange(0x10000001,0x7fffffff)) for off in numeric_offsets)
        yield Case('constructor overwrites perturbed defaults %d' % i,0x47e2d0,
            perturbed_constructor_setup(data,sentinels),receiver=lambda t:t['obj'],arguments=(lambda t:t['ent'],))
