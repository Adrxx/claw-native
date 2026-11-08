"""Original-only Hermit Crab core cases, from packet layouts and branches."""
from clawparity.cases import Case

def obj(env, *args, **kwargs):
    kwargs.setdefault("fill", 0)
    return env.object(*args, **kwargs)


MASK = 0xffffffff
ANIM_KEYS = ('LEVEL_HERMITCRAB_FASTADVANCE','LEVEL_HERMITCRAB_CROUCH4','LEVEL_HERMITCRAB_HIDE','LEVEL_HERMITCRAB_STRIKE1','LEVEL_HERMITCRAB_KILLFALL','LEVEL_HERMITCRAB_HIT','LEVEL_HERMITCRAB_FALL','LEVEL_HERMITCRAB_LIFT','GAME_NULL')
SOUND_KEYS = ('GAME_SPLASH','GAME_HIT1','GAME_HIT2','GAME_HIT3','GAME_HIT4','GAME_PURELEASE1','LEVEL_HERMITCRAB_CRABSNIP','GAME_THRWBOMB','LEVEL_HERMITCRAB_CRABDEATH','LEVEL_HERMITCRAB_CRABLEFT','GAME_BOINKJR')


def text(env, value):
    return obj(env,len(value)+1, 'key '+value, data=value.encode()+b'\0')


def dictionary(env, entries):
    d = obj(env,0x30, 'dictionary')
    bucket = obj(env,4, 'bucket')
    head = 0
    for key, value in entries:
        head = obj(env,16, 'node '+key, words=[head, 0x91827163, text(env,key), value])
    env.put(bucket, head)
    env.put(d+0x14, bucket, 1)
    return d


def animation(env, n):
    frame = obj(env,0x30, 'animation frame')
    env.put(frame+0x1c, n)
    frames = obj(env,4, 'frame pointers', words=[frame])
    a = obj(env,0x18, 'animation sequence')
    env.put(a+0xc, frames, 1)
    return a


def registry(env, key, value):
    node = obj(env,0x14, 'state registry node')
    env.put(node, node, node, 0, text(env,key), value)
    env.put(0x537680, node)


def inflate(env, call):
    p, dx, dy = call.arguments
    l,t,r,b = (env.get(p+i) for i in (0,4,8,12))
    env.put(p, (l-dx)&MASK,(t-dy)&MASK,(r+dx)&MASK,(b+dy)&MASK)
    return 1


def scene(seed=0x234571, **options):
    def setup(env):
        s = obj(env,0x434, 'crab', fill=(seed&255) or 0x79)
        for offset in range(0,0x434,4):
            env.put(s+offset,((seed*0x10203+offset*0x10101)&MASK) or 1)
        p = obj(env,0x1c0, 'sprite')
        w = obj(env,0x180, 'world object')
        ctx = obj(env,0x30, 'asset context')
        env.put(s+0xc,p,w)
        env.put(s+0x128,p,p,w)
        env.put(p+0xc,ctx)
        env.put(ctx+0x24,obj(env,0x6c,'movement context'))
        env.put(p+0x6c,w)
        env.put(w+0x168,p)
        env.put(w+0x1c,seed)
        env.put(w+0x68,seed+67)
        env.put(p+0x4c,17,29)
        env.put(p+0x108,seed+1)
        env.put(p+0x114,seed+3,11,13,19,23,31,37,41,43,47,53,59)
        env.put(p+0x164,seed|0x80)
        env.put(p+0x190,0)
        env.put(p+0x19c,0)
        env.put(p+0x1a4,1)
        env.put(s+0x184,options.get('difficulty',0))
        env.put(s+0x18c,options.get('direction',0))
        env.put(s+0x138,seed+9)
        env.put(s+0x140,seed+21)
        env.put(p+0x40,(seed&~2)|options.get('flip',0))
        env.put(s+0x410,options.get('last',100),options.get('duration',200))
        env.put(s+0x420,options.get('launch_last',seed+41),options.get('launch_duration',seed+43),options.get('bomber',0),seed+47)
        env.put(0x537210,options.get('now',300))
        env.put(0x5430c4,options.get('delta',1))
        env.put(0x532c0c,options.get('sound_enabled',0))
        env.put(0x532c10,seed+27)
        registry(env,options.get('state','ES_HOME'),seed+101)
        log = obj(env,0x100, 'callback observations')
        methods = obj(env,0x68,'crab vtable')
        def callback(tag):
            def effect(env,call):
                n=env.get(log)
                env.put(log+4+n*24,tag,call.receiver,env.get(s+0x428),env.get(w+0x1c),env.get(s+0x410),env.get(p+0x164))
                env.put(log,n+1)
                if options.get('callback_change'):
                    env.put(s+0x428,seed+303)
                    env.put(w+0x1c,seed+305)
                return options.get('callback_return',seed+tag)
            return effect
        env.put(methods+0x44,env.stub('home','thiscall',0,callback(0x44)))
        env.put(methods+0x64,env.stub('advance','thiscall',0,callback(0x64)))
        env.put(s,methods)
        a=animation(env,seed+111)
        defense=animation(env,seed+113)
        strike=animation(env,seed+115)
        env.put(s+0x408,0 if options.get('null_animation') else a,defense)
        env.put(s+0x310,strike)
        if options.get('prior_animation'):
            env.put(p+0x190,animation(env,seed+117))
        if options.get('active_animation'):
            env.put(p+0x190,a)
            env.put(p+0x18c,p)
            frame=env.get(env.get(a+0xc))
            env.put(p+0x194,frame,0)
            if options.get('finish_animation'):
                env.put(frame+0xc,9)
            env.put(p+0x19c,options.get('delay',0))
            env.put(p+0x1a0,1)
            env.put(p+0x1a4,options.get('complete',1))
            env.put(p+0x1a8,seed+119,seed+121,0x3f800000)
        if options.get('sound',0):
            sound=obj(env,0x14,'sound wrapper')
            player=obj(env,0x14,'sound player')
            soundctx=obj(env,0x7c,'sound context')
            env.put(sound+0x10,player)
            env.put(player+0x10,soundctx)
            env.put(s+0x400,sound)
        else:
            env.put(s+0x400,0)
        entries=[] if options.get('missing_assets') else [(k,animation(env,seed+151+i)) for i,k in enumerate(ANIM_KEYS)]
        if options.get('fallback_only'):
            entries=[('GAME_NULL',animation(env,seed+177))]
        ad=dictionary(env,entries)
        sd=dictionary(env,[(k,seed+211+i) for i,k in enumerate(SOUND_KEYS)])
        images=[]
        if options.get('geometry'):
            for i,key in enumerate(('LEVEL_HERMITCRAB','LEVEL_BOMBERCRAB')):
                frame=obj(env,0x28,'image geometry '+key)
                env.put(frame+0x18,3+i,7+i,31+i*2,47+i*3)
                frames=obj(env,4,'image frame table '+key,words=[frame])
                image=obj(env,0x6c,'image '+key)
                env.put(image+0x14,frames)
                env.put(image+0x64,0,0)
                images.append((key,image))
        image=dictionary(env,images)
        logic=dictionary(env,[])
        env.put(ctx+0x10,image,logic)
        env.put(ctx+0x28,sd,ad)
        env.put(s+0x1a4,env.get(0x52e1cc),env.get(0x52e1cc))
        env.put(s+0x2f4,0,0,32,seed)
        env.override(0x546d24,inflate)
        def rand(e,c):
            if options.get('rand_change'):
                e.put(0x537210,options['rand_change'])
                e.put(s+0x414,0x71)
            values=options.get('randoms',(0,))
            return values[min(e.calls_so_far(0x4a3050)-1,len(values)-1)] & MASK
        env.override(0x4a3050,rand)
        return {'s':s,'p':p,'w':w,'ctx':ctx,'log':log,'key':text(env,options.get('key','LEVEL_HERMITCRAB_HIDE'))}
    return setup


def case(label, fn, setup, args=(), facade=False):
    return Case(label, fn, setup, receiver=lambda t:t['s']+(0x128 if facade else 0),arguments=args)


def dispatch(seed, index, bounds=(10,12), empty=False, stride=4):
    def setup(env):
        t=scene(seed)(env)
        s=t['s']; log=t['log']
        def cb(e,c):
            e.put(log,seed,c.receiver,e.get(0x537850),e.get(0x537854),e.get(0x537868))
            return seed
        target=env.stub('dispatch','thiscall',0,cb)
        lo,hi=bounds
        buf=obj(env,(hi-lo+1)*stride,'dispatch vector')
        for n in range(hi-lo+1): env.put(buf+n*stride,0 if empty else target)
        fallbackptr=obj(env,stride,'fallback',words=[target])
        error=obj(env,0x18,'error context',words=[0,0,seed,4])
        env.put(0x53784c,error,lo,hi,buf,fallbackptr,stride,0,seed)
        base=obj(env,4,'parent dispatch',words=[target])
        env.put(0x537640,index,index,base,base,4,0,seed)
        return t
    return setup


def _cases(random_source):
    for bomber in (0,1,-3):
        for flip in (0,2):
            for assets in ('all','fallback','missing'):
                seed=random_source.randrange(1000,20000)
                base=scene(seed,flip=flip,fallback_only=assets=='fallback',missing_assets=assets=='missing')
                def setup(env,base=base,bomber=bomber):
                    t=base(env)
                    env.put(t['w']+0x64,bomber)
                    env.put(t['p']+0x104,0 if bomber==0 else 9)
                    return t
                yield case(f'constructor {bomber=} {flip=} {assets}',0x44a380,setup,args=(lambda t:t['p'],))
    for assets in ('all','fallback','missing'):
        for key in ('LEVEL_HERMITCRAB_HIDE','GAME_NULL','UNKNOWN'):
            yield case(f'lookup {assets} {key}',0x44aa90,scene(391,fallback_only=assets=='fallback',missing_assets=assets=='missing',key=key),args=(lambda t:t['key'],),facade=True)
    for bomber in (0,1):
        for flip in (0,2):
            base=scene(random_source.randrange(1000,20000),geometry=True,flip=flip)
            def geometry_setup(env,base=base,bomber=bomber):
                t=base(env)
                env.put(t['w']+0x64,bomber)
                return t
            yield case(f'constructor backed image geometry {bomber=} {flip=}',0x44a380,geometry_setup,args=(lambda t:t['p'],))
    for capacity in (33,65,129):
        base=scene(random_source.randrange(1000,20000),geometry=True)
        def heap_bitset_constructor(env,base=base,capacity=capacity):
            t=base(env)
            env.put(0x533470,capacity)
            return t
        yield case(f'constructor initial bitset capacity {capacity}',0x44a380,heap_bitset_constructor,args=(lambda t:t['p'],))
    for bomber in (0,1):
        for fallback in (False,True):
            base=scene(random_source.randrange(1000,20000),geometry=True,fallback_only=fallback)
            def locale_lookup_constructor(env,base=base,bomber=bomber):
                t=base(env)
                env.put(t['w']+0x64,bomber)
                env.put(0x540e00,1)
                env.write(0x540bf9,bytes(256))
                return t
            yield case(f'constructor single-byte locale lookups {bomber=} {fallback=}',0x44a380,locale_lookup_constructor,args=(lambda t:t['p'],))
    for flags in (0,1,2,3,0x100,0x101,0xffffffff):
        yield case(f'delete flags {flags:#x}',0x44ac40,scene(581),args=(flags,))
    yield case('destructor direct inline bitset',0x44ac60,scene(891))
    def heap_bitset(env):
        t=scene(892)(env)
        b=obj(env,12,'bitset heap',words=[3,5,7])
        env.put(t['s']+0x2fc,96,b)
        return t
    yield case('destructor direct heap bitset',0x44ac60,heap_bitset)
    for bomber in (0,1,2,-1,0x100):
        yield case(f'change bomber {bomber}',0x44acd0,scene(441),args=(bomber,))
    for direction in (0,1,2,-1,0x100):
        for flip in (0,2):
            for seed in (123,0x80000000,random_source.randrange(1000,100000)):
                yield case(f'home {direction=} {flip=} {seed=}',0x44ae30,scene(seed,direction=direction,flip=flip))
    for now,last,duration in ((299,100,200),(300,100,200),(301,100,200),(0,1,0xffffffff),(0,0xffffffff,1),(0xffffffff,0,0xffffffff)):
        for lo,hi in ((1000,3000),(0,0),(5,4),(-1,-2),(10,-5)):
            for rand in (0,1,99,0xffffffff):
                yield case(f'hide timer {now,last,duration} range {lo,hi} rand {rand}',0x44ad10,scene(711,state='ES_HIDE',now=now,last=last,duration=duration,randoms=(rand,)),args=(lo,hi))
    yield case('hide rereads tick after rand',0x44ad10,scene(719,state='ES_HIDE',rand_change=917,randoms=(173,)),args=(1000,3000))
    yield case('hide saves distinct prior animation',0x44ad10,scene(721,state='ES_HIDE',prior_animation=True),args=(1000,3000))
    yield case('hide callback returns error',0x44ade0,scene(729,randoms=(0,),callback_return=0xffffffff))
    yield case('advance callback returns zero',0x44afd0,scene(731,difficulty=2,randoms=(99,0),callback_return=0))
    for now in (299,300,301):
        for rand in (0,89,90,99,100,0xffffffff):
            yield case(f'hide tick {now} random {rand}',0x44ade0,scene(733,now=now,randoms=(rand,),callback_change=True))
    for complete in (0,1):
        for delta in (0,1,3,4):
            yield case(f'hide animated tick {complete=} {delta=}',0x44ade0,scene(739,active_animation=True,complete=complete,delay=3,delta=delta,finish_animation=True,randoms=(0,)))
    for difficulty in (-1,0,1,2,3,4,5,6,7):
        for rand in (0,39,40,99,0xffffffff):
            yield case(f'reaction {difficulty} random {rand}',0x44aef0,scene(747,difficulty=difficulty,randoms=(rand,1731),state='ES_HIDE'))
    for null in (False,True):
        yield case(f'defense {null=}',0x44af70,scene(751,state='ES_DEFENSE',null_animation=null))
    yield case('defense saves distinct prior animation',0x44af70,scene(757,state='ES_DEFENSE',prior_animation=True))
    for difficulty in (-1,0,1,2,3,4,5):
        for bomber in (0,1):
            for r1,r2 in ((0,0),(9,0),(10,0),(19,9),(20,19),(29,20),(30,29),(39,39),(40,40),(49,99),(50,0),(99,99),(-1,-1)):
                yield case(f'defense tick {difficulty=} {bomber=} rand {r1,r2}',0x44afd0,scene(773,difficulty=difficulty,bomber=bomber,randoms=(r1,r2,1731),state='ES_HIDE'))
    for difficulty in range(5):
        for bomber in (0,1):
            hide,action = (((50,20),(50,20),(30,40),(20,30),(10,20)) if not bomber else ((10,0),(10,0),(10,10),(20,20),(40,40)))[difficulty]
            for r1,r2 in ((hide-1,action),(hide,action),(hide,action-1),(hide+1,action+1)):
                seed=random_source.randrange(1000,20000)
                yield case(f'defense exact thresholds {difficulty=} {bomber=} rand {r1,r2}',0x44afd0,scene(seed,difficulty=difficulty,bomber=bomber,randoms=(r1,r2,1731),state='ES_HIDE'))
    for complete,delay in ((0,3),(1,3)):
        yield case(f'animation gate {complete,delay}',0x44afd0,scene(781,complete=complete,delay=delay,active_animation=True))
    for sound,enabled in ((0,1),(1,0),(1,1)):
        yield case(f'advance sound {sound,enabled}',0x44afd0,scene(787,difficulty=2,randoms=(99,0),sound=sound,sound_enabled=enabled))
    for index in (9,10,11,12,13):
        for stride in (4,12):
            yield case(f'dispatch {index} stride {stride}',0x449d60,dispatch(803,index,stride=stride),args=(index,))
    yield case('dispatch null reaches parent',0x449d60,dispatch(811,11,empty=True),args=(11,))


def cases(random_source):
    yield from sorted(_cases(random_source), key=lambda c: c.function)
