"""Original-only CrabNest closure cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence

def object_(env, *args, **kwargs):
    kwargs.setdefault('fill', 0)
    return env.object(*args, **kwargs)

TREASURE_OFFSETS=(0xf0,0xf8,0xf4,0xfc,0x100,0x108,0x104,0x10c)

def string_map(env, entries=()):
    obj=object_(env,0x40,'map')
    buckets=object_(env,4,'buckets')
    env.put(obj+4,buckets,1)
    head=0
    for key,value in entries:
        text=object_(env,len(key)+1,'key',data=key.encode()+b'\0')
        node=object_(env,16,'assoc',words=[head,0,text,value])
        head=node
    env.put(buckets,head)
    return obj

def base(env, count=0, treasures=(), inhibit=0):
    receiver=object_(env,0x58,'nest',fill=0x65)
    owner=object_(env,0x1b4,'owner')
    logic=object_(env,0x174,'logic')
    scene=object_(env,0x80,'scene')
    manager=object_(env,0x40,'objects')
    env.put(manager+0xc,scene)
    # A preallocated list node keeps the platform list allocation out of scope.
    free_node=0
    for i in range(16):
        free_node=object_(env,12,'list free node',words=[free_node,0,0])
    env.put(manager+0x20,free_node)
    empty=string_map(env)
    for offset in (0x10,0x14,0x28,0x2c): env.put(scene+offset,empty-0x10)
    env.put(scene+8,manager)
    env.put(owner+0xc,scene)
    env.put(owner+0x4c,117,-91)
    env.put(owner+0x64,4)
    env.put(owner+0x6c,logic)
    env.put(owner+0x18c,owner)
    env.put(logic+0xc,scene)
    env.put(logic+0x1c,0x13579)
    env.put(logic+0x2c,70,180,-120,-20)
    env.put(logic+0x64,count,inhibit)
    for i,value in enumerate(treasures):
        env.put(owner+0x100 if i==0 else logic+TREASURE_OFFSETS[i-1],value)
    env.put(receiver+8,owner,owner,logic)
    env.put(receiver+0x28,owner,owner,logic)
    env.put(receiver+0x48,0,0,0,0)
    idle_text=object_(env,8,'idle state name',data=b'ES_IDLE\0')
    hatch_text=object_(env,9,'hatch state name',data=b'ES_HATCH\0')
    idle_leaf=object_(env,20,'idle state leaf',words=[0,0,0,idle_text,0x432c50])
    hatch_leaf=object_(env,20,'hatch state leaf',words=[0,0,0,hatch_text,0x432d50])
    root=object_(env,20,'state trie root',words=[hatch_leaf,idle_leaf,24,0,0])
    env.put(0x537668+0x18,root)
    env.put(0x5430c4,11)
    env.put(0x532c0c,0)
    env.put(0x53721c,0)
    env.override(0x4a3050,sequence(-201,49,401,200,50,-401,0,99,400,201,0,0,100,1,5,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36))
    return dict(receiver=receiver,owner=owner,logic=logic,scene=scene,manager=manager)

def setup_common(options):
    def setup(env):
        t=base(env,options.get('count',0),options.get('treasures',()),options.get('inhibit',0))
        r,o,l,s=t['receiver'],t['owner'],t['logic'],t['scene']
        if options.get('distinct_graphs'):
            # The two inherited owner/logic pairs are independent inputs.
            hatch_owner=object_(env,0x1b4,'hatch owner',data=env.read(o,0x1b4))
            hatch_logic=object_(env,0x174,'hatch logic',data=env.read(l,0x174))
            env.put(hatch_owner+0x4c,-239,173)
            env.put(hatch_owner+0x64,7)
            env.put(hatch_owner+0x6c,hatch_logic)
            env.put(hatch_owner+0x18c,hatch_owner)
            env.put(r+0x28,hatch_owner,hatch_owner,hatch_logic)
        if options.get('constructor'):
            if options.get('discriminate'):
                alternate=object_(env,0x1b4,'pre-construction owner',data=env.read(o,0x1b4))
                alternate_logic=object_(env,0x174,'pre-construction logic',data=env.read(l,0x174))
                env.put(alternate+0x6c,alternate_logic)
                env.put(r+8,alternate,alternate,alternate_logic)
                env.put(r+0x28,alternate,alternate,alternate_logic)
                env.put(r+0x48,0x37,0x49,0x51,0x63)
                env.put(o+8,0x1853049)
                env.put(l+0x1c,options.get('state',0x13579))
            rect=options.get('rect',(1,2,3,4))
            env.put(l+0x2c,*rect)
            env.put(o+0x64,options.get('level',4))
            frame=object_(env,0x28,'frame',fill=0x38)
            env.put(frame+0x18,7,11,23,31)
            env.put(o+0x174,frame)
        if 'player_mode' in options:
            player=object_(env,0x128,'player')
            env.put(0x537e88,player)
            env.put(player+0x4c,options.get('px',100),options.get('py',-80))
            env.put(player+0xcc,options['player_mode'])
            env.put(player+0x118,-5,-7,9,13)
            env.put(r+0x50,options.get('active',0))
            def intersect(env,call):
                dst,a,b=call.arguments
                aa=struct.unpack('<4i',env.read(a,16));bb=struct.unpack('<4i',env.read(b,16))
                out=(max(aa[0],bb[0]),max(aa[1],bb[1]),min(aa[2],bb[2]),min(aa[3],bb[3]))
                yes=out[0]<out[2] and out[1]<out[3]
                env.write(dst,struct.pack('<4i',*(out if yes else (0,0,0,0))))
                return int(yes)
            env.override(0x546ce0,intersect)
        if options.get('animation') or options.get('constructor'):
            ani=object_(env,0x18,'animation')
            frame=object_(env,0x30,'animation command')
            array=object_(env,4,'animation array',words=[frame])
            env.put(ani+0xc,array,1)
            env.put(frame+0x1c,0x123456)
            env.put(r+0x4c,ani)
            env.put(o+0x190,0x7a123456)
            if options.get('constructor'):
                am=string_map(env,[('LEVEL_HATCHNEST',ani)])
                sound_marker=object_(env,0x14,'constructor sound')
                sm=string_map(env,[('GAME_BOINK',sound_marker)])
                env.put(s+0x2c,am-0x10)
                env.put(s+0x28,sm-0x10)
                if options.get('map_miss'):
                    env.put(s+0x2c,string_map(env)-0x10)
                    env.put(s+0x28,string_map(env)-0x10)
                if options.get('discriminate'):
                    receipts=object_(env,0x400,'constructor callback observations')
                    def observe(env,call):
                        n=env.get(receipts)
                        at=receipts+4+n*112
                        env.put(at,call.receiver,len(call.arguments),*call.arguments)
                        env.write(at+16,env.read(r,0x58))
                        env.put(receipts,n+1)
                        return 0x521a73
                    methods=object_(env,0x28,'existing hit attack methods')
                    env.put(methods+0x1c,env.stub('reset existing logic','thiscall',0,observe))
                    env.put(methods+0x24,env.stub('install logic callback','thiscall',2,observe))
                    descriptors=[]
                    for offset,tag in ((0x70,0x19371),(0x78,0x29583)):
                        existing=object_(env,0x174,'existing owner logic',fill=0x73)
                        env.put(existing,methods)
                        env.put(o+offset,existing)
                        desc=object_(env,0x14,'logic descriptor',fill=0x48)
                        env.put(desc+0x10,tag)
                        descriptors.append(desc)
                    lm=string_map(env,[('LogicHit',descriptors[0]),('LogicAttack',descriptors[1])])
                    env.put(s+0x14,lm-0x10)
        if 'frame' in options:
            env.put(o+0x16c,options['frame'])
            env.put(r+0x54,options.get('hatched',0))
            env.put(o+0x190,0)
            env.put(o+0x1a4,options.get('ended',0))
            env.put(o+0x19c,options.get('delay',0))
            if options.get('tick'):
                animation=object_(env,0x18,'live hatch animation')
                command=object_(env,0x30,'live hatch animation command')
                env.put(command+0xc,9)
                env.put(command+0x18,17,0x136759)
                env.put(o+0x190,animation,command,0,options.get('delay',0),1,options.get('ended',0),0x12379,0x2468b,0x3f800000)
            if options.get('sound'):
                wrapper=object_(env,0x14,'sound wrapper')
                sound=object_(env,0x14,'sound')
                descriptor=object_(env,0x7c,'sound descriptor')
                env.put(wrapper+0x10,sound);env.put(sound+0x10,descriptor)
                env.put(r+0x48,wrapper)
                env.put(0x532c0c,options.get('enabled',1))
        if options.get('crabs'):
            log=object_(env,0x1000,'callback observations')
            def launch(env,call):
                actor=env.get(call.receiver+0x12c)
                n=env.get(log)
                at=log+4+n*48
                env.put(at,call.receiver,actor,env.get(actor+0x100),env.get(r+0x54))
                env.write(at+16,env.read(call.receiver+0x40,32))
                env.put(log,n+1)
                if options.get('callback_changes'):
                    env.put(l+0x68,1)
                    env.put(o+0x4c,-313,271)
                return 0
            # Stub registration is setup-only: Env does not reset its stub
            # address counter between the two executions of one case.
            launch_callback=env.stub('crab launch','thiscall',0,launch)
            def init(env,call):
                actor=call.arguments[0]
                li=env.get(actor+0x6c)
                state=object_(env,0x430,'created crab state',fill=0x51)
                vtable=object_(env,0x50,'crab state methods')
                env.put(vtable+0x4c,launch_callback)
                env.put(state,vtable)
                env.put(state+0x12c,actor)
                env.put(li+0x18,state)
                return 0
            descriptor=object_(env,0x14,'crab logic descriptor')
            env.put(descriptor+0x10,env.stub('created crab init','cdecl',1,init))
            mp=string_map(env,[('HermitCrab',descriptor)])
            env.put(s+0x14,mp-0x10)
        if 'random_values' in options:
            env.override(0x4a3050,sequence(*options['random_values']))
        return t
    return setup

def dispatch(index, callback=True, malformed=False):
    def setup(env):
        r=object_(env,0x58,'dispatcher receiver')
        records=object_(env,16,'rtti')
        target=object_(env,8,'rtti target',fill=0x53)
        vt=object_(env,8,'rtti vtable')
        env.put(vt,records);env.put(r,vt+4);env.put(records+0xc,target)
        log=object_(env,16,'callback receipt')
        def effect(env,call):
            env.put(log,call.receiver,env.get(0x5372f8),env.get(call.receiver))
            env.put(call.receiver+0x20,0xa5139b7)
            return 0
        cb=env.stub('state callback','thiscall',0,effect) if callback else 0
        table=object_(env,12,'dispatch table',words=[cb,cb,cb])
        env.put(0x5372e0,10,12,table,0,4,0x765432)
        env.put(0x5372f8,0x6abc0173)
        if malformed:
            env.put(0x5372e0,12,10,table,0,0,0x765432)
            def zero_size_realloc(env, call):
                result=object_(env,4,'zero-size realloc backing',words=[cb])
                if call.arguments[0]: env.release(call.arguments[0])
                return result
            env.override(0x4a9070,zero_size_realloc)
        return {'receiver':r}
    return Case(f'dispatch {index} callback={callback} malformed={malformed}',0x432690,setup,receiver=lambda t:t['receiver'],arguments=(index,))

def cases(random_source):
    for index in (10,11,12,9,13):
        for callback in (False,True): yield dispatch(index,callback)
    yield dispatch(11,True,True)
    for count in (0,1,9,10,-1,0x7fffffff):
        for rect in ((0,0,0,0),(1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)):
            for level in (0,1,4):
                yield Case(f'constructor {count} {rect} level {level}',0x432a60,setup_common(dict(constructor=True,count=count,rect=rect,level=level)),receiver=lambda t:t['receiver'],arguments=(lambda t:t['owner'],))
    yield Case('save idle state',0x432c20,setup_common({}),receiver=lambda t:t['receiver'])
    for ani in (False,True): yield Case(f'begin hatch animation {ani}',0x432d00,setup_common(dict(animation=ani)),receiver=lambda t:t['receiver'])
    for mode in (0,1,2,3,-1):
        for active in (0,1):
            for px in (100,500):
                yield Case(f'idle mode {mode} active {active} x {px}',0x432c50,setup_common(dict(player_mode=mode,active=active,px=px)),receiver=lambda t:t['receiver'])
    for frame in (1,2,3):
        for hatched in (0,1):
            for ended,delay in ((0,0),(1,0),(1,2)):
                for sound,enabled in ((False,0),(True,0),(True,1)):
                    yield Case(f'hatch frame {frame} flag {hatched} end {ended} delay {delay} sound {sound} {enabled}',0x432d50,setup_common(dict(frame=frame,hatched=hatched,ended=ended,delay=delay,sound=sound,enabled=enabled)),receiver=lambda t:t['receiver'])
    for count in (-1,0,1,2,9,10):
        for mask in (0,1,0x100,0x155,0x1ff):
            treasures=tuple((30+i if mask>>i&1 else 0) for i in range(9))
            for inhibit in (0,1):
                yield Case(f'hatch crabs {count} mask {mask:x} inhibit {inhibit}',0x432dd0,setup_common(dict(count=count,treasures=treasures,inhibit=inhibit,crabs=True)),receiver=lambda t:t['receiver'])
    for i in range(12):
        yield Case(f'random idle {i}',0x432c50,setup_common(dict(player_mode=random_source.choice((1,2)),px=random_source.randrange(-200,300),py=random_source.randrange(-200,300))),receiver=lambda t:t['receiver'])
    for changes in (False,True):
        for distinct in (False,True):
            yield Case(f'hatch callback rereads {changes} distinct graphs {distinct}',0x432dd0,setup_common(dict(count=3,treasures=(31,47,59,61,73),crabs=True,callback_changes=changes,distinct_graphs=distinct)),receiver=lambda t:t['receiver'])
    for i in range(16):
        count=random_source.randrange(1,10)
        treasures=tuple(random_source.choice((0,random_source.randrange(1,100))) for _ in range(9))
        values=tuple(random_source.randrange(-0x80000000,0x80000000) for _ in range(40))
        yield Case(f'random hatch operands {i}',0x432dd0,setup_common(dict(count=count,treasures=treasures,crabs=True,random_values=values)),receiver=lambda t:t['receiver'])
    for miss in (False,True):
        for count in (0,1,9,10,-1):
            yield Case(f'constructor distinct fields miss {miss} count {count}',0x432a60,setup_common(dict(constructor=True,discriminate=True,map_miss=miss,count=count,rect=(0,0,0,0),level=0,state=random_source.getrandbits(32))),receiver=lambda t:t['receiver'],arguments=(lambda t:t['owner'],),initial_stack=((-96,random_source.randbytes(80)),))
    for frame in (1,2,3):
        for delay in (0,1,23):
            for ended in (0,1):
                yield Case(f'live hatch animation tick frame {frame} delay {delay} ended {ended}',0x432d50,setup_common(dict(frame=frame,delay=delay,ended=ended,tick=True)),receiver=lambda t:t['receiver'])
