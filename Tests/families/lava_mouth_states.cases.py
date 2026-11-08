"""Lava-mouth inputs from the original instructions."""
from clawparity.cases import Case


def hashmap(env, address, entries):
    bucket = env.object(4, 'hash bucket')
    head = 0
    for key, value in reversed(entries):
        text = env.object(len(key)+1, 'hash key', data=key.encode()+b'\0')
        head = env.object(16, 'hash link', words=[head,0,text,value])
    env.put(bucket, head)
    env.put(address+4,bucket,1)


def setup_state(seed, frame=7, first=1, last=22, animation=True, now=1000,
                elapsed=11, interval=10, reset=False, sound=0, enabled=0,
                cycle=True, ctor=False, fallback=False, active=False, separate=False,
                scale=0x3F800000, sound_mask=3, active_sound=False,
                observe_logic=False):
    def setup(env):
        obj=env.object(0xB8,'runtime',fill=(seed & 127)+1)
        actor=env.object(0x220,'actor')
        data=env.object(0x120,'runtime data')
        context=env.object(0x40,'level context')
        world=env.object(0x90,'world timing')
        player=env.object(0x80,'player')
        player_data=env.object(0x20,'player data')
        env.put(player+0x6C,player_data)
        env.put(player_data+0x14,world)
        env.put(world+0x80,seed ^ 0x2A17)
        env.put(0x537E88,player)
        env.put(0x537210,now)
        env.put(0x5430C4,17)
        env.put(0x532C0C,enabled)
        env.put(0x532C10,seed ^ 0x7711)
        env.put(actor+0xC,context)
        env.put(actor+0x6C,data)
        env.put(data+0x1C,seed ^ 0x51)
        env.put(data+0x64,seed ^ (0x3A17 if reset else 0x2A17))
        env.put(data+0xBC,(seed*3+17)&0xFFFFFFFF)
        env.put(data+0xF0,11,13,17,19,23,29,31,37)
        env.put(obj+0xC,actor,data)
        env.put(obj+0x2C,actor)
        env.put(obj+0x9C,(now-elapsed)&0xFFFFFFFF,interval,(now-elapsed)&0xFFFFFFFF,interval)
        root=env.object(20,'state trie root')
        left=env.object(20,'fall leaf',words=[0,0,0,0x5235F8,seed ^ 0x3344])
        right=env.object(20,'idle leaf',words=[0,0,0,0x523604,seed ^ 0x1122])
        env.put(root,left,right,24)
        env.put(0x537680,root)
        frames=env.object(0x100,'animation frames')
        for n in range(64):
            env.put(frames+n*4,seed ^ (0x800+37*n))
        ani=env.object(0x70,'animation')
        env.put(ani+0x14,frames)
        env.put(ani+0x64,first,last)
        env.put(actor+0x16C,frame,ani if animation else 0,seed ^ 0x8A)
        env.put(actor+0x138,0x12345678,0x89ABCDEF,seed ^ 0x719,seed ^ 0x291)
        env.put(actor+0x188,0,actor,0)
        command=env.object(0x30,'cycle command',words=[0,0,1,9,0,0,100,seed ^ 0x9917])
        arr=env.object(4,'cycle array',words=[command])
        cycles=env.object(0x14,'cycles')
        env.put(cycles+0xC,arr,1)
        env.put(obj+0xAC,cycles if cycle else 0)
        if active:
            env.put(actor+0x190,cycles,command,0,0,0,0,seed ^ 0x7191,seed ^ 0x8191,0x3F800000)
        if separate:
            destination=env.object(0x220,'separate collision receiver',fill=0x79)
            env.put(obj+0xC,destination)
        audio=env.object(0x40,'sound object')
        audio_state=env.object(0x7C,'sound state')
        sound_item=env.object(0x14,'sound wrapper')
        env.put(sound_item+0x10,audio)
        env.put(audio+0x10,audio_state)
        env.put(audio_state+0x78,0)
        audio2=env.object(0x40,'second sound object')
        sound_item2=env.object(0x14,'second sound wrapper')
        env.put(audio2+0x10,audio_state)
        env.put(sound_item2+0x10,audio2)
        env.put(obj+0xB0,sound_item if sound else 0,sound_item2 if sound else 0)
        if active_sound:
            env.put(audio_state+0x78,1)
            env.put(0x532C10,37)
            observations=env.object(0x200,'audio observations',fill=0)
            def audio_method(tag):
                def effect(env,call):
                    n=env.get(observations)
                    env.put(observations,n+1)
                    env.put(observations+4+n*28,tag,*call.arguments,
                            *([0]*(4-len(call.arguments))),
                            env.get(obj+0xA4),env.get(obj+0xA8))
                    return 0
                return effect
            for number,audio_object in enumerate((audio,audio2)):
                voice=env.object(0x34,'audio voice',fill=0)
                interface=env.object(4,'DirectSound buffer')
                methods=env.object(0x48,'DirectSound methods')
                env.put(interface,methods)
                env.put(voice+0xC,interface,audio_state,0xA6,22050)
                env.put(voice+0x30,1)
                env.put(audio_object+0x18,22050,0,0)
                env.put(audio_object+0x30,voice+4,voice+4)
                def status(env,call):
                    env.put(call.arguments[1],0)
                    return 0
                env.put(methods+0x24,env.stub(f'audio {number} status','stdcall',2,status))
                for slot,argc in ((0x30,4),(0x3C,2),(0x40,2),(0x44,2)):
                    env.put(methods+slot,env.stub(f'audio {number} method {slot:x}',
                            'stdcall',argc,audio_method(number*256+slot)))
        for i in range(22):
            env.put(0x50E570+i*16,*(seed ^ (i*101+k*29) for k in range(4)))
        if ctor:
            env.put(0x5262B0,scale)
            anims=env.object(0x24,'animation registry')
            logics=env.object(0x24,'logic registry')
            sounds=env.object(0x24,'sound registry')
            seqs=env.object(0x24,'sequence registry')
            env.put(context+0x10,anims,logics)
            env.put(context+0x28,sounds,seqs)
            hashmap(env,anims+0x10,[('LEVEL_LAVAMOUTH',ani)] if animation else [])
            logic_entries=[]
            if observe_logic:
                observations=env.object(0x400,'constructor publication observations',fill=0)
                def logic_effect(tag):
                    def effect(env,call):
                        n=env.get(observations)
                        env.put(observations,n+1)
                        at=observations+4+n*64
                        env.put(at,tag,call.receiver,len(call.arguments),
                                *(call.arguments+(0,0))[:2])
                        env.write(at+20,env.read(obj,44))
                        return seed ^ tag
                    return effect
                for i,key in enumerate(('LogicHit','LogicAttack')):
                    resource=env.object(0x14,key+' resource',fill=0x79+i)
                    handler=env.object(4,key+' handler')
                    methods=env.object(0x28,key+' methods')
                    env.put(handler,methods)
                    env.put(methods+0x1C,env.stub(key+' clear','thiscall',0,logic_effect(i*16)))
                    env.put(methods+0x24,env.stub(key+' load','thiscall',2,logic_effect(i*16+1)))
                    env.put(actor+(0x70 if i==0 else 0x78),handler)
                    logic_entries.append((key,resource))
            hashmap(env,logics+0x10,logic_entries)
            hashmap(env,sounds+0x10,[(key,value) for bit,key,value in (
                (1,'LEVEL_LAVAMOUTH2',sound_item),
                (2,'LEVEL_LAVAMOUTH1',sound_item2)) if sound_mask & bit])
            hashmap(env,seqs+0x10,[('GAME_NULL' if fallback else 'GAME_CYCLE50',cycles)] if cycle else [])
            decoy_actor=env.object(0x220,'previous receiver actor',data=env.read(actor,0x220))
            decoy_data=env.object(0x120,'previous receiver data',data=env.read(data,0x120))
            env.put(decoy_data+0x1C,seed ^ 0x7114)
            env.put(obj+0xC,decoy_actor,decoy_data)
        return {'obj':obj,'actor':actor}
    return setup


def make(label,fn,setup,args=()):
    return Case(label,fn,setup,receiver=lambda t:t['obj'],arguments=args)


def dispatch_setup(seed,index=3,lower=2,upper=5,stride=4,empty=False):
    def setup(env):
        obj=env.object(0xB8,'dispatch receiver',fill=seed & 255)
        record=env.object(24,'callback observations')
        rtti=env.object(16,'RTTI locator')
        typeinfo=env.object(8,'RTTI type')
        vtable=env.object(8,'RTTI vtable')
        env.put(vtable,rtti,0)
        env.put(rtti+0xC,typeinfo)
        env.put(obj,vtable+4)
        def callback(slot):
            def effect(env,call):
                env.put(record,call.receiver,env.get(0x537AB0),env.get(0x537A98),env.get(0x537A9C),slot,env.get(call.receiver+0xA4))
                env.put(call.receiver+0xA4,seed ^ (0x71913+slot))
                return seed ^ (0x4F+slot)
            return effect
        ptr=env.stub('fallback mouth state callback','thiscall',0,callback(0x71))
        table=env.object((upper-lower+1)*stride,'dispatch table',fill=0xA7)
        for i in range(upper-lower+1):
            cell=env.stub(f'mouth state slot {i}','thiscall',0,callback(i))
            env.put(table+i*stride,0 if empty else cell)
        env.put(0x537A98,lower,upper,table,0,stride)
        env.put(0x537AB0,seed ^ 0x2F)
        error=env.object(0x18,'error context',words=[0,0,0,4,0,0])
        fallback=env.object(4,'fallback callback',words=[ptr])
        env.put(0x537A94,error)
        env.put(0x537AA4,fallback)
        return {'obj':obj,'table':table,'record':record}
    return setup


def cases(random_source):
    for index in (2,3,5,0,-1,6,9):
        for stride in (4,8):
            yield make(f'dispatch {index} stride {stride}',0x457740,dispatch_setup(0x6B,index,stride=stride),(index,))
    yield make('empty dispatch',0x457740,dispatch_setup(0x491,empty=True),(3,))
    for index in (-4,-3,-1,-5,0):
        yield make(f'negative registry index {index}',0x457740,
                   dispatch_setup(0x719,index,lower=-4,upper=-1,stride=8),(index,))
    for animation,first,last in ((False,1,22),(True,1,22),(True,2,22),(True,1,0),(True,-1,1)):
        yield make(f'idle {animation} {first}:{last}',0x457CD0,setup_state(0xAB31,animation=animation,first=first,last=last))
    for now,elapsed,interval in ((1000,9,10),(1000,10,10),(1000,11,10),(0,0,0),(3,8,7),(0x80000000,0x80000000,0x7FFFFFFF),(1,0xFFFFFFFF,0xFFFFFFFF)):
        yield make(f'wait {now}/{elapsed}/{interval}',0x457D60,setup_state(0x112A,now=now,elapsed=elapsed,interval=interval))
    for cycle in (False,True):
        yield make(f'fall cycle {cycle}',0x457D80,setup_state(0x91AA,cycle=cycle))
    for frame in (-1,0,1,2,3,18,19,20,22,23,0x80000000):
        for elapsed in (9,10,11):
            yield make(f'falling {frame} elapsed {elapsed}',0x457DE0,setup_state(0x18A1,frame=frame,elapsed=elapsed,interval=10))
    for frame in (2,19):
        for sound,enabled in ((0,1),(1,0),(1,1)):
            yield make(f'sound {frame} {sound}/{enabled}',0x457DE0,setup_state(0x99AA,frame=frame,sound=sound,enabled=enabled))
        for enabled in (0,1,0x80000000):
            yield make(f'observable audio {frame} enabled {enabled}',0x457DE0,
                       setup_state(0x7991,frame=frame,sound=1,enabled=enabled,active_sound=True))
    for frame in (0,2,19,23):
        yield make(f'reset {frame}',0x457DE0,setup_state(0xAB11,frame=frame,reset=True))
    for fallback in (False,True):
        for animation in (False,True):
            yield make(f'ctor fallback {fallback} ani {animation}',0x457B10,setup_state(0x3941,ctor=True,fallback=fallback,animation=animation),(lambda t:t['actor'],))
    for frame in range(1,23):
        yield make(f'every collision rectangle {frame}',0x457DE0,setup_state(0x7193,frame=frame,separate=True))
    for fn in (0x457D80,0x457DE0):
        yield make(f'active animation {fn:x}',fn,setup_state(0x1819,frame=7,active=True))
    for scale in (0,0x3F000000,0x3FA00000,0xC0000000):
        yield make(f'constructor scale {scale:x}',0x457B10,setup_state(0xA819,ctor=True,scale=scale),(lambda t:t['actor'],))
    for sound_mask in (0,1,2,3):
        yield make(f'constructor distinct sounds mask {sound_mask}',0x457B10,
                   setup_state(0x7931,ctor=True,sound_mask=sound_mask),(lambda t:t['actor'],))
    yield make('constructor both cycle lookups miss',0x457B10,
               setup_state(0x3719,ctor=True,cycle=False),(lambda t:t['actor'],))
    yield make('constructor logic observes publication order',0x457B10,
               setup_state(0x7195,ctor=True,observe_logic=True),(lambda t:t['actor'],))
    for i in range(4):
        yield make(f'random constructor {i}',0x457B10,
                   setup_state(random_source.randrange(1,0x7FFFFFFF),ctor=True,
                               fallback=bool(i & 1),animation=bool(i & 2),
                               sound_mask=i),(lambda t:t['actor'],))
    for i in range(20):
        seed=random_source.randrange(1,0x7FFFFFFF)
        fn=(0x457CD0,0x457D60,0x457D80,0x457DE0)[i%4]
        yield make(f'random {i}',fn,setup_state(seed,frame=random_source.randrange(0,25),elapsed=random_source.randrange(0,0x10000),interval=random_source.randrange(0,0x10000),now=random_source.getrandbits(32),reset=bool(i%2),sound=i%2,enabled=i%3==0))
