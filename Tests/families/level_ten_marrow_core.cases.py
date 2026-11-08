"""Original-derived Marrow dispatch cases."""
from clawparity.cases import Case
from clawparity.fixtures import returns


def dispatch_setup(index=0, fail=False):
    def setup(env):
        a = env.object(0x500, 'marrow', fill=0)
        error = env.object(0x18, 'error', fill=0)
        env.put(error + 0xc, 4)
        entries = env.object(12, 'dispatch entries', fill=0)
        fb = env.object(4, 'fallback', fill=0)
        log = env.object(16, 'callback observation', fill=0)

        def callback_for(slot):
            def cb(env, call):
                env.put(log, call.receiver, slot, env.get(error+8), env.get(0x537b10))
                return 0x76543210+slot
            return env.stub('dispatch callback '+str(slot),'thiscall',0,cb)

        callback = callback_for(99)
        env.put(entries, *(callback_for(slot) for slot in range(3)))
        env.put(fb, callback)
        env.put(0x537af4, error, 0, 2, entries, fb, 4, 0, 0x93718264)
        base = env.object(12, 'base dispatch entries', fill=0)
        env.put(base, callback, callback, callback)
        env.put(0x5349bc, error, -8, 8, env.object(68, 'base entries', words=[callback]*17), fb, 4, 0, 0)
        if fail:
            env.override(0x4a9070, returns(0))
        return dict(a=a)
    return setup


def actor_setup(**o):
    def setup(env):
        import struct
        a = env.object(0x500, 'marrow', fill=0)
        e = env.object(0x200, 'entity', fill=0)
        s = env.object(0x200, 'sprite', fill=0)
        l = env.object(0x180, 'logic', fill=0)
        w = env.object(0x40, 'world', fill=0)
        grid = env.object(0x100, 'grid', fill=0)
        m = env.object(0x100, 'map', fill=0)
        rows = env.object(16, 'rows', fill=0)
        tiles = env.object(16, 'tiles', words=[0xffffffff]*4)
        p = env.object(0x200, 'player', fill=0)
        ctl = env.object(0x20, 'control', fill=0)
        inp = env.object(8, 'input', fill=0)
        vt = env.object(0xb0, 'vtable', fill=0)
        log = env.object(0x300, 'callbacks', fill=0)
        strings = env.object(0x100, 'state strings', fill=0)
        def record(slot):
            def effect(env, call):
                n = env.get(log)
                env.put(log+4+n*28,slot,call.receiver,env.get(a+0x14),env.get(env.get(a+0xc)+0xcc),env.get(a+0x20),env.get(a+0x4b8),call.arguments[0] if call.arguments else 0)
                env.put(log,n+1)
                if slot==0x24 and o.get('swap_entity'):
                    env.write(replacement,env.read(e,0x200))
                    env.put(replacement+0xcc,0x83746512)
                    env.put(replacement+0x10c,74)
                    env.put(a+0xc,replacement)
                    
                    env.put(a,replacement_vt)
                return 0x12340000+slot
            return effect
        for off in (0x24,0x44,0x58,0x64,0x68,0xa4):
            env.put(vt+off,env.stub('marrow callback '+hex(off),'thiscall',0,record(off)))
        env.put(vt+0x90,env.stub('marrow timer callback','thiscall',1,record(0x90)))
        env.put(a,vt)
        env.put(a+0xc,e,l)
        env.put(a+0x128,e,s)
        env.put(a+0x184,o.get('state',6),0,o.get('direction',2),e,e)
        env.put(a+0x138,17,19,31,37)
        env.put(a+0x2e4,o.get('threshold',50))
        env.put(a+0x454,100)
        env.put(a+0x3c4,o.get('distance',0))
        env.put(a+0x468,o.get('start',10),o.get('duration',100))
        env.put(a+0x4c0,o.get('previous_health',100))
        env.put(a+0x20,o.get('count',2))
        env.put(a+0x1a0,o.get('event',0))
        for off in range(0x38,0x68,4): env.put(a+off,0x40000000+off)
        env.write(a+0x68,struct.pack('<d',o.get('x',0.0)))
        env.write(a+0x70,struct.pack('<d',o.get('y',0.0)))
        env.put(e+0xc,w)
        env.put(e+0x38,o.get('enemy_status',0))
        env.put(e+0x4c,64,64)
        env.put(e+0x6c,l)
        env.put(e+0x10c,o.get('health',100))
        env.put(e+0x118,0x80000000)
        env.put(s+0xc,w)
        env.put(s+0x40,o.get('flip',0))
        env.put(s+0x50,96)
        env.put(s+0x164,0x2468)
        for off in (0x10,0x14,0x28,0x2c):
            resource=env.object(0x40,'resource map',fill=0)
            env.put(resource+0x18,1)
            env.put(w+off,resource)
        env.put(s+0x19c,o.get('frame_delay',0))
        env.put(s+0x1a4,o.get('finished',0))
        env.put(l+0x1c,o.get('logic_state',0))
        env.put(w+0x24,grid)
        env.put(grid+0x5c,m)
        env.put(m+0x20,tiles,rows)
        env.put(m+0x30,128,128)
        env.put(m+0x8c,7,7)
        env.put(p+0x4c,o.get('player_x',64),o.get('player_y',64))
        env.put(p+0x6c,ctl)
        env.put(ctl+0x14,inp)
        env.put(inp,o.get('input_x',0),o.get('input_active',0))
        env.put(0x537e88,p)
        env.put(0x53c9c0,o.get('mode',2))
        env.put(0x534eac,o.get('level',0x26b7))
        env.put(0x5430c4,o.get('delta',0))
        env.put(0x537210,o.get('clock',20))
        env.put(0x53c9ac,0)
        env.put(0x540e00,0)
        env.put(0x541334,o.get('distance_disabled',0))
        env.put(0x537680,0)
        # Ordinary in-range state table; the original base can read state names.
        env.put(strings,*([o.get('state_name',0x5234ec)]*64))
        error = env.object(0x18,'table error', fill=0); env.put(error+0xc,4)
        env.put(0x53769c,error,0,63,strings,strings,4,0,0)
        header=env.object(16,'empty string',fill=0)
        env.put(header,0xffffffff)
        env.put(0x52e1c8,header,header+12)
        env.put(a+0x1a4,header+12,header+12)
        env.put(a+0x344,0)
        env.put(a+0x350,0)
        env.put(s+0x190,0)
        env.put(s+8,o.get('sprite_flags',0xa5b6c784))
        if o.get('animation'):
            asset = animation_asset(env,37,'active animation')
            env.put(a+0x344,asset)
            env.put(a+0x350,asset)
            env.put(s+0x18c,s,asset,env.get(env.get(asset+0xc)))
            env.put(s+0x1a8,37,37,0x3f800000)
        if o.get('expand_strings'):
            env.put(l+0x1c,o['expand_strings'])
        from clawparity.fixtures import sequence
        env.override(0x4a3050,sequence(*o.get('random',(0,0,0,0))))
        env.override(0x546cd4,returns(0))
        if o.get('independent'):
            env.put(a+0x24,0x91735264)
            env.put(a+0x134,0xa1763845)
            env.put(a+0x470,0xb2734651,0xc3845726)
            env.put(a+0x4b8,0xd4956837)
            entity128=env.object(0x200,'actor128 entity',data=env.read(e,0x200))
            entity190=env.object(0x200,'actor190 entity',data=env.read(e,0x200))
            entity194=env.object(0x200,'actor194 entity',data=env.read(e,0x200))
            separate_world=env.object(0x40,'entity190 world',data=env.read(w,0x40))
            separate_grid=env.object(0x100,'entity190 grid',data=env.read(grid,0x100))
            separate_map=env.object(0x100,'sight map',data=env.read(m,0x100))
            sight_tiles=env.object(16,'sight tiles',words=[0]*4)
            tile_vt=env.object(0x24,'sight tile vtable',fill=0)
            tile=env.object(4,'sight tile',words=[tile_vt])
            tile_table=env.object(4,'sight tile table',words=[tile])
            tile_log=env.object(0x200,'sight tile observations',fill=0)
            def tile_query(env,call):
                count=env.get(tile_log)
                env.put(tile_log+4+count*12,call.receiver,*call.arguments)
                env.put(tile_log,count+1)
                return o.get('tile_blocked',0)
            env.put(tile_vt+0x20,env.stub('sight tile query','thiscall',2,tile_query))
            env.put(separate_map+0x20,sight_tiles)
            env.put(separate_grid+0x4c,tile_table)
            env.put(separate_grid+0x5c,separate_map)
            env.put(separate_world+0x24,separate_grid)
            env.put(entity190+0xc,separate_world)
            env.put(entity194+0x4c,71,89)
            env.put(entity128+0xcc,0xe5a67948)
            env.put(a+0x128,entity128)
            env.put(a+0x190,entity190,entity194)
            env.put(l+0x1c,o.get('logic_state',17))
        if o.get('swap_entity'):
            replacement=env.object(0x200,'callback replacement entity',fill=0)
            replacement_vt=env.object(0xb0,'callback replacement vtable',data=env.read(vt,0xb0))
            env.put(replacement_vt+0x44,env.stub('replacement callback44','thiscall',0,record(0x144)))
        return dict(a=a,e=e,s=s,l=l,p=p,vt=vt,log=log)
    return setup


def cases(random_source):
    # The original 4db6e0 fails at 4dc680 ([EBP+4] with EBP=0) on
    # allocation failure, before either dispatcher failure arm can execute.
    for index in (0,1,2,-1,3):
        yield Case('dispatch '+str(index),0x4587a0,dispatch_setup(index),receiver=lambda t:t['a'],arguments=(index,))
    for fn in (0x4593f0,0x459440,0x459660,0x459ad0):
        for mode in (0,2,3):
            for distance in (-1,0,499,500):
                yield Case(f'{fn:x} mode {mode} distance {distance}',fn,actor_setup(mode=mode,distance=distance),receiver=lambda t:t['a'])
    for state in (0,2,3,4,5,6,7):
        for direction,flip in ((2,0),(2,2),(3,0),(3,2)):
            for r in (0,39,40,49,50,69,70,120,-1):
                yield Case(f'home tick {state} {direction} {flip} {r}',0x4596a0,actor_setup(state=state,direction=direction,flip=flip,random=(r,r),level=0),receiver=lambda t:t['a'])
    for finished,delay,event in ((0,0,0),(1,1,0),(1,0,1),(1,0,0)):
        for clock,start,duration in ((20,10,100),(110,10,100),(111,10,100),(4,0xfffffff0,20)):
            yield Case(f'parrot {finished} {delay} {event} {clock}',0x4599b0,actor_setup(finished=finished,frame_delay=delay,event=event,clock=clock,start=start,duration=duration),receiver=lambda t:t['a'])
    for _ in range(12):
        d=random_source.randrange(-1000,1000)
        yield Case('random idle '+str(d),0x459ad0,actor_setup(distance=d,clock=random_source.getrandbits(32)),receiver=lambda t:t['a'])
    for y in (0.0,100.0,101.0):
        for hp in (74,75,76,100):
            yield Case(f'evaluate {y} {hp}',0x459470,actor_setup(y=y,health=hp),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for flags in (0,1,2,3,0x100):
        yield Case('destructor '+str(flags),0x4593d0,actor_setup(),receiver=lambda t:t['a'],arguments=(flags,))

    for active,x,state,px in ((1,0,3,64),(1,1,3,-64),(1,0,4,64),(1,0,5,64),(1,1,3,64),(1,0,3,-64)):
        for r in (-1,0,199,200,599,600):
            yield Case(f'attack {active} {x} {state} {px} {r}',0x459470,actor_setup(input_active=active,input_x=x,state=state,player_x=px,random=(r,0,0,0)),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for py,status,level in ((114,0,0),(14,0,0),(64,-1,0),(64,0,0x26b7)):
        yield Case(f'home rejection {py} {status} {level}',0x4596a0,actor_setup(state=5,player_y=py,enemy_status=status,level=level),receiver=lambda t:t['a'])
    for present in (False,True):
        yield Case('constructor '+str(present),0x458d40,constructor_setup(present),receiver=lambda t:t['a'],arguments=(lambda t:t['e'],))


    for scale in (-1.0,0.0,98.9,99.0,99.9,100.0,123.75):
        for bitcount in (9,10,32,33):
            yield Case(f'constructor scale {scale} flags {bitcount}',0x458d40,constructor_setup(True,scale,bitcount),receiver=lambda t:t['a'],arguments=(lambda t:t['e'],))
    for state_id in (-2,64,66):
        yield Case('evaluate expands strings '+str(state_id),0x459470,actor_setup(state=3,input_active=1,expand_strings=state_id),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for name in (0x5234f4,0x528758):
        yield Case('evaluate named state '+hex(name),0x459470,actor_setup(y=101.0,state=3,state_name=name,input_active=1),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for count in (0,1,2,0x7fffffff):
        for hp in (74,75,76):
            yield Case(f'evaluate health count {count} {hp}',0x459470,actor_setup(count=count,health=hp),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for fn in (0x4593f0,0x459440,0x459ad0):
        for delta in (0,1,36,37,38,100):
            yield Case(f'animation {fn:x} delta {delta}',fn,actor_setup(animation=True,delta=delta),receiver=lambda t:t['a'])
    for _ in range(24):
        values=dict(direction=random_source.choice((2,3,7)),state=random_source.choice((2,3,4,5,6)),threshold=random_source.randrange(-20,140),random=(random_source.randint(-1000,1000),random_source.randint(-1000,1000)),flip=random_source.getrandbits(32),player_y=random_source.randrange(15,114),clock=random_source.getrandbits(32))
        yield Case('random home '+str(values),0x4596a0,actor_setup(**values),receiver=lambda t:t['a'])


    yield Case('evaluate callbacks replace entity and vtable',0x459470,actor_setup(y=101.0,swap_entity=True),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for y in (float('nan'),float('inf'),-float('inf'),99.999,100.001):
        yield Case('evaluate floating boundary '+str(y),0x459470,actor_setup(y=y),receiver=lambda t:t['a'],arguments=(0x5234ec,))
    for direction,input_x in ((2,0),(2,1),(3,0),(3,1),(7,0)):
        for px in (-600,-200,-1,0,199,200,599,600):
            yield Case(f'evaluate facing distance {direction} {input_x} {px}',0x459470,actor_setup(state=3,direction=direction,input_x=input_x,input_active=1,player_x=px),receiver=lambda t:t['a'],arguments=(0x5234ec,))


    for present in (False,True):
        for bitcount in (9,33):
            yield Case(f'patterned constructor {present} {bitcount}',0x458d40,constructor_setup(present,123.5,bitcount,True),receiver=lambda t:t['a'],arguments=(lambda t:t['e'],))
    for fn in (0x4593f0,0x459440,0x459660,0x459ad0,0x4596a0,0x4599b0):
        for animation in (False,True):
            for mode in (0,2):
                yield Case(f'independent objects {fn:x} animation {animation} mode {mode}',fn,actor_setup(independent=True,animation=animation,mode=mode,finished=1,clock=110,logic_state=17),receiver=lambda t:t['a'])


    for key in (0x528840,0x528858,0x5287d0,0x5289c8,0x5288fc):
        yield Case('constructor missing resource '+hex(key),0x458d40,constructor_setup(True,123.5,33,True,key),receiver=lambda t:t['a'],arguments=(lambda t:t['e'],))
    for blocked in (0,1):
        for direction,flip in ((2,0),(3,2)):
            yield Case(f'independent sight {blocked} facing {direction}',0x4596a0,actor_setup(independent=True,level=0,state=5,direction=direction,flip=flip,tile_blocked=blocked),receiver=lambda t:t['a'])


def animation_asset(env, duration, label):
    asset=env.object(0x20,label,fill=0)
    frames=env.object(4,label+' frames',fill=0)
    frame=env.object(0x30,label+' frame',fill=0)
    env.put(asset+0xc,frames,1)
    env.put(frames,frame)
    env.put(frame+0x1c,duration)
    return asset


def constructor_setup(present, scale=1.0, bitcount=None, patterned=False, missing_key=None):
    def setup(env):
        t=actor_setup()(env)
        if patterned:
            env.write(t['a'],bytes(((index*73+29)%255)+1 for index in range(0x500)))
        import struct
        for address,value in ((0x5262b8,scale),(0x50e770,1.0),(0x5262b4,1.25),(0x5262b0,0.75)):
            env.write(address,struct.pack('<f',value))
        # Original base constructor parses this global bit-index string,
        # copies the resulting bitset, then sets bit nine itself.
        env.write(0x534938,(str(bitcount) if bitcount is not None else '').encode()+b'\0')
        e,s,l=t['e'],t['s'],t['l']
        env.put(e+0x6c,l)
        if present:
            resource=env.get(env.get(e+0xc)+0x2c)
            bucket=env.object(4,'animation bucket',fill=0)
            env.put(resource+0x14,bucket)
            keys=(0x5289c8,0x5289ac,0x528994,0x52897c,0x528968,0x528950,0x52893c,0x528924,0x528910,0x5288fc,0x5288e8,0x5288d4,0x5288c0,0x5288ac,0x528898,0x528884,0x528870,0x5234b4)
            node=0
            for index,key in enumerate(keys):
                if key==missing_key: continue
                asset=animation_asset(env,17+index,'resource '+hex(key))
                node=env.object(16,'animation node',words=[node,0,key,asset])
            env.put(bucket,node)
            sound_map=env.get(env.get(e+0xc)+0x28)
            sound_bucket=env.object(4,'sound bucket',fill=0)
            env.put(sound_map+0x14,sound_bucket)
            sound_keys=(0x528858,0x528840,0x52882c,0x528814,0x5287fc,0x5287e4,0x5287d0,0x5287bc,0x5287a8,0x528790,0x524098,0x524870,0x5246f8,0x527d50,0x527d40,0x527d34)
            sound_node=0
            for index,key in enumerate(sound_keys):
                if key==missing_key: continue
                value=env.object(0x80,'sound resource '+hex(key),words=[0x18630475+index]*32)
                sound_node=env.object(16,'sound node',words=[sound_node,0,key,value])
            env.put(sound_bucket,sound_node)
        return t
    return setup
