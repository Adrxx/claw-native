"""Cutthroat inputs built from the original layouts and physical service boundaries."""
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence
from clawparity.env import NativeSourceContext

RAND = 0x4a3050

def object_memory(env, size, *args, **kwargs):
    kwargs.setdefault("fill", 0)
    return env.object(size, *args, **kwargs)

def words(env, at, *values):
    env.put(at, *(v & 0xffffffff for v in values))

def resource_map(env, entries, label):
    wrapper = object_memory(env, 0x40, label)
    head = 0
    for name, value in entries:
        key = object_memory(env, len(name)+1, label+'-key', data=name.encode()+b'\0')
        head = object_memory(env, 16, label+'-node', words=[head, 0x913527ab, key, value])
    bucket = object_memory(env, 4, label+'-bucket', words=[head])
    env.put(wrapper+0x14, bucket, 1)
    return wrapper

def setup_case(config, salt):
    def setup(env):
        obj = object_memory(env, 0x480, 'cutthroat', fill=0x71)
        actor = object_memory(env, 0x1b4, 'actor')
        logic = object_memory(env, 0x174, 'logic')
        world = object_memory(env, 0x40, 'world')
        player = object_memory(env, 0x1b4, 'player')
        record = object_memory(env, 512, 'callback-observations')
        vt = object_memory(env, 0xa8, 'cutthroat-methods')
        def callback(slot):
            def effect(e, call):
                i=e.get(record)
                words(e,record+4+i*24,slot,call.receiver,e.get(obj+0x1a0),e.get(logic+0x1c),e.get(0x537210),e.get(obj+0x468))
                e.put(record,i+1)
                if slot == config.get('change_slot'):
                    words(e,player+0x50,config.get('changed_y',100))
                    if 'changed_global' in config: e.put(0x534eac,config['changed_global'])
                return (salt ^ slot) & 0xffffffff
            return effect
        for slot in (0x44,0x48,0x58,0x90,0xa4):
            env.put(vt+slot,env.stub('state-method-'+hex(slot),'thiscall',1 if slot==0x90 else 0,callback(slot)))
        env.put(obj,vt)
        env.put(obj+0xc,actor,logic)
        env.put(obj+0x12c,actor,logic)
        env.put(obj+0x190,actor,actor)
        env.put(actor+0xc,world)
        words(env,actor+0x38,config.get('visible',0))
        words(env,actor+0x40,config.get('flags',0x104))
        words(env,actor+0x4c,config.get('actor_x',100),config.get('actor_y',100))
        env.put(actor+0x64,19,0,logic)
        env.put(actor+0x188+4,actor)
        env.put(logic+0xc,world)
        words(env,logic+0x1c,salt)
        for off in (0x118,0x128,0x138):
            words(env,actor+off,-17,31,43,59)
        words(env,obj+0x138,-23)
        words(env,obj+0x140,61)
        words(env,obj+0x184,config.get('mode',7),0,config.get('facing',2))
        words(env,obj+0x1a0,config.get('latch',1))
        words(env,obj+0x2fc,16,4)
        words(env,obj+0x468,config.get('sound_latch',1),config.get('stamp',100),config.get('interval',100),config.get('altstamp',37),config.get('altinterval',79))
        words(env,obj+0x2e4,config.get('threshold',50))
        words(env,obj+0x450,config.get('projectile_x',-65),config.get('projectile_y',20),config.get('speed',-400))
        env.put(0x537e88,player)
        words(env,player+0x4c,160,config.get('y',100))
        env.put(player+0xcc,config.get('posture',0))
        env.put(0x537210,config.get('now',200))
        env.put(0x5430c4,config.get('delta',1))
        env.put(0x537964,config.get('difficulty',1))
        env.put(0x534eac,config.get('level',0))
        for g in (0x54130c,0x541310,0x541314,0x541318,0x537668+0x18,0x53c9a8): env.put(g,0)
        voice_actor=object_memory(env,0x188,'voice-actor')
        voice_logic=object_memory(env,0x20,'voice-logic')
        env.put(voice_actor+0x6c,voice_logic)
        env.put(0x53c9ac,voice_actor)
        env.put(0x52f01c,1)
        # The inverse state registry names the current state as idle, so the
        # unchanged LS_HOME helper performs a real lookup and takes its no-op path.
        home_name = object_memory(env, 8,'inverse-name',data=b'LS_IDLE\0')
        inv = object_memory(env, 4,'inverse-slot',words=[home_name])
        policy = object_memory(env, 0x20,'error-policy',words=[0,0,0,4])
        for base in (0x537698,):
            words(env,base+4,policy,salt,salt,inv,inv,4,0,0)
        # Animation resources have separate sequences and distinct event payloads.
        names = ['WALK','STRIKE1','STRIKE2','FALL','HITLOW','HITHIGH','HOME','LIFTED','LIFTED2','STAND1','STAND2','STAND3','STAND4','JUMP','THROWN','STRIKE3']
        animations=[]; seqs=[]
        for index,name in enumerate(names+['NULL']):
            frame=object_memory(env, 0x30,'frame-'+name)
            env.put(frame+0xc,9)
            env.put(frame+0x18,3)
            env.put(frame+0x1c,config.get('event',2) if name=='NULL' else 0x100+index)
            arr=object_memory(env, 4,'frame-array-'+name,words=[frame])
            seq=object_memory(env, 0x14,'sequence-'+name)
            env.put(seq+0xc,arr,1)
            seqs.append(seq)
            animations.append(('GAME_NULL' if name=='NULL' else 'LEVEL_CUTTHROAT_'+name,seq))
        if not config.get('resources',True): animations=animations[-1:]
        animation_map=resource_map(env,animations,'animations')
        sound_backend=object_memory(env,0x80,'sound-backend')
        sound_device=object_memory(env, 0x80,'sound-device')
        env.put(sound_device+0x10,sound_backend)
        sound=object_memory(env, 0x14,'sound',words=[0,0,0,0,sound_device])
        soundnames=['THROWHIGH','THROWLOW','00350010','00350017','00350003','00350012','00350013']
        sound_values=[object_memory(env,0x18,'sound-'+name,words=[salt+i,0,0,0,sound_device,0xa700+i]) for i,name in enumerate(soundnames)]
        soundmap=resource_map(env,list(zip(('LEVEL_CUTTHROAT_'+name for name in soundnames),sound_values)) if config.get('resources',True) else [],'sounds')
        image_frame=object_memory(env,0x80,'image-frame',fill=0x19)
        image_frames=object_memory(env,8,'image-frame-array',words=[image_frame,image_frame])
        image=object_memory(env,0x70,'image-resource')
        env.put(image+0x14,image_frames)
        env.put(image+0x64,0,1)
        images=resource_map(env,[('LEVEL_KNIFE',image),('LEVEL_CUTTHROAT',image)] if config.get('images',True) else [],'images')
        movement=object_memory(env,0x144,'projectile-movement',fill=0x53)
        movement_actor=object_memory(env,0x1b4,'projectile-movement-actor')
        env.put(movement+0x12c,movement_actor)
        words(env,movement+0x138,-27)
        words(env,movement+0x140,39)
        words(env,movement_actor+0x40,config.get('projectile_flags',0))
        for off in (0x118,0x128,0x138):
            words(env,movement_actor+off,0x80000000 if config.get('sentinel') else -17,13,41,29)
        def bullet_init(e,call):
            projectile=call.arguments[0]
            projectile_logic=e.get(projectile+0x6c)
            words(e,record+196,projectile,projectile_logic,e.get(projectile+0x104),e.get(projectile+0xd0),e.get(obj+0x1a0),e.get(projectile+0x4c),e.get(projectile+0x50))
            e.put(projectile_logic+0x18,movement)
            if 'callback_speed' in config: words(e,obj+0x458,config['callback_speed'])
            return salt
        bullet_callback=env.stub('Bullet logic initialize','cdecl',1,bullet_init)
        definition=object_memory(env,0x14,'Bullet-definition')
        env.put(definition+0x10,bullet_callback)
        logicmap=resource_map(env,[('Bullet',definition)],'logic-names')
        manager=object_memory(env,0x38,'object-manager')
        env.put(manager+0xc,world)
        node=object_memory(env,12,'projectile-list-free-node')
        env.put(manager+0x20,node)
        env.put(manager+0x2c,4)
        env.put(world+8,manager)
        env.put(world+0x10,images,logicmap)
        env.put(world+0x28,soundmap,animation_map)
        for off,idx in ((0x318,9),(0x31c,10),(0x320,11),(0x324,12),(0x334,4),(0x344,6),(0x34c,0),(0x370,2)):
            env.put(obj+off,seqs[idx])
        env.put(obj+0x45c,salt+11,salt+17,salt+23)
        env.put(obj+0x3b4,sound if config.get('sound',False) else 0)
        env.put(0x532c0c,config.get('sound_enabled',0))
        # Delayed/finished animation states give controlled return events without
        # replacing any animation code.
        env.put(actor+0x190,seqs[-1])
        env.put(actor+0x194,env.get(env.get(seqs[-1]+0xc)))
        words(env,actor+0x19c,config.get('delay',0),1,config.get('finished',1),config.get('event',2),config.get('event',2),0x3f800000)
        tilemap=object_memory(env, 0x94,'tilemap')
        cells=object_memory(env, 4,'cells',words=[0 if config.get('blocked') else 0xeeeeeeee])
        rows=object_memory(env, 4,'rows')
        env.put(tilemap+0x20,cells,rows)
        env.put(tilemap+0x30,1024,1024)
        env.put(tilemap+0x8c,10,10)
        collision=object_memory(env, 0x6c,'collision')
        tilevt=object_memory(env, 0x24,'tile-vtable')
        env.put(tilevt+0x20,env.stub('tile-block','thiscall',2,returns(1)))
        tile=object_memory(env, 4,'tile',words=[tilevt])
        tiles=object_memory(env, 4,'tiles',words=[tile])
        env.put(collision+0x4c,tiles)
        env.put(collision+0x5c,tilemap)
        env.put(world+0x24,collision)
        random_values=sequence(*config.get('randoms',(99,99,99,99)))
        def physical_random(e,call):
            # Preserve the object's publication state at this real physical
            # service call; no expected values or fixture assertions are used.
            e.write(record+256,e.read(obj+0x28c,0x60))
            words(e,record+352,e.get(obj+0xc),e.get(obj+0x10),e.get(obj+0x12c),e.get(obj+0x130),e.get(obj+0x24))
            return random_values(e,call)
        env.override(RAND,physical_random)
        def decrement(e,c):
            n=(e.get(c.arguments[0])-1)&0xffffffff
            e.put(c.arguments[0],n)
            return n
        env.override(0x5469e8,decrement)
        empty=env.get(0x52e1c8)+12
        env.put(obj+0x1a4,empty,empty)
        if config.get('strings'):
            for off,count in ((0x1a4,1),(0x1a8,3)):
                text=object_memory(env, 24,'cstring',words=[count,5,8],data=None)
                env.write(text+12,b'abcde\0')
                env.put(obj+off,text+12)
        if config.get('heapbits'):
            bits=object_memory(env, 12,'bitset',words=[0x1937,0xabcd,0x1234])
            env.put(obj+0x2fc,65,bits)
        if config.get('constructor'):
            env.put(0x5262b8,config.get('scale',0x3f800000))
            env.put(0x5262bc,0x3f800000)
            env.put(0x533470,config.get('bit_capacity',32))
            # The original base preserves these two independently supplied world
            # pointers. Its embedded helper uses the actor's world for resources.
            constructor_logic_world=object_memory(env,0x40,'constructor-logic-world',data=env.read(world,0x40))
            constructor_alt_frame=object_memory(env,0x30,'constructor-other-frame')
            env.put(constructor_alt_frame+0xc,9)
            env.put(constructor_alt_frame+0x18,11)
            env.put(constructor_alt_frame+0x1c,salt+0x817)
            constructor_alt_frames=object_memory(env,4,'constructor-other-frames',words=[constructor_alt_frame])
            constructor_alt_sequence=object_memory(env,0x14,'constructor-other-sequence')
            env.put(constructor_alt_sequence+0xc,constructor_alt_frames,1)
            constructor_alt_animations=resource_map(env,[(name,constructor_alt_sequence) for name,value in animations],'constructor-other-animations')
            env.put(constructor_logic_world+0x2c,constructor_alt_animations)
            env.put(logic+0xc,constructor_logic_world)
        if config.get('distinct',True) and not config.get('constructor'):
            # These are independent pointer roles in the original. Give each a
            # backed object so a neighbouring-field read cannot pass by aliasing.
            state_logic=object_memory(env,0x174,'independent-state-logic',data=env.read(logic,0x174))
            origin_actor=object_memory(env,0x1b4,'independent-origin-actor',data=env.read(actor,0x1b4))
            words(env,origin_actor+0x4c,83,127)
            env.put(origin_actor+0x6c,state_logic)
            collision_actor=object_memory(env,0x1b4,'independent-collision-context',data=env.read(actor,0x1b4))
            position_actor=object_memory(env,0x1b4,'independent-position-actor',data=env.read(actor,0x1b4))
            words(env,position_actor+0x4c,config.get('x',100),100)
            independent_world=object_memory(env,0x40,'independent-world',data=env.read(world,0x40))
            env.put(collision_actor+0xc,independent_world)
            helper_world=object_memory(env,0x40,'independent-helper-logic-world',data=env.read(world,0x40))
            alternate_frame=object_memory(env,0x30,'alternative-context-frame')
            env.put(alternate_frame+0xc,9)
            env.put(alternate_frame+0x18,7)
            env.put(alternate_frame+0x1c,salt+0x731)
            alternate_frames=object_memory(env,4,'alternative-context-frames',words=[alternate_frame])
            alternate_sequence=object_memory(env,0x14,'alternative-context-sequence')
            env.put(alternate_sequence+0xc,alternate_frames,1)
            alternate_map=resource_map(env,[(name,alternate_sequence) for name,value in animations],'alternative-context-animations')
            alternate_sound=object_memory(env,0x18,'alternative-context-sound',words=[salt+0x713,0,0,0,sound_device,salt])
            alternate_soundmap=resource_map(env,[('LEVEL_CUTTHROAT_'+name,alternate_sound) for name in soundnames],'alternative-context-sounds')
            alternate_image=object_memory(env,0x70,'alternative-context-image',data=env.read(image,0x70))
            env.put(alternate_image+0x64,1,1)
            alternate_imagemap=resource_map(env,[('LEVEL_KNIFE',alternate_image),('LEVEL_CUTTHROAT',alternate_image)],'alternative-context-images')
            env.put(helper_world+0x10,alternate_imagemap)
            env.put(helper_world+0x28,alternate_soundmap,alternate_map)
            env.put(logic+0xc,helper_world)
            env.put(obj+0xc,origin_actor,state_logic)
            env.put(obj+0x190,collision_actor,position_actor)
            # Record state from the receiver's actual state block in callbacks.
            logic=state_logic
        if config.get('registry'):
            name=config['registry'].encode()+b'\0'
            registry_name=object_memory(env,len(name),'registered-state-name',data=name)
            registry_node=object_memory(env,0x14,'registered-state-node')
            env.put(registry_node,registry_node,registry_node,0,registry_name,salt+0x10000)
            env.put(0x537668+0x18,registry_node)
        source=None
        if config.get('dispatch'):
            state=config.get('state',0)
            cb=env.stub('dispatch-state','thiscall',0,callback(0x20))
            fallback=object_memory(env, 4,'dispatch-fallback',words=[cb if config.get('fallback',True) else 0])
            table=object_memory(env, 12,'dispatch-table',words=[cb,0 if config.get('base') else cb,cb])
            words(env,0x53759c,policy,0,2,table,fallback,4,0,0)
            base_table=object_memory(env, 84,'base-dispatch',words=[cb]*21)
            words(env,0x53787c,policy,-10,10,base_table,fallback,4,0,0)
            if config.get('fail'):
                env.override(0x4a9070,returns(0))
            source=NativeSourceContext()
            source.size=72; source.version=1; source.inputMask=0x7ff; source.outputMask=0x5f3; source.preserveMask=0x472
            source.eax=salt; source.ebx=salt^0x3571; source.edx=salt^0x1a79
            source.esi=salt^0xa713; source.edi=salt^0x5179; source.ebp=salt^0x1357
            source.esp=0x02008000; source.eip=0x438100; source.ecx=obj; source.eflags=2; source.fsHead=0xffffffff
        return {'obj':obj,'actor':actor,'source':source}
    return setup

def cases(random_source):
    def case(label,fn,config=None,args=()):
        config={} if config is None else dict(config)
        if fn in (0x4384f0,0x4388a0,0x438900,0x437a90):
            config['registry']='LS_IDLE' if fn in (0x4384f0,0x437a90) else 'LS_FIRING'
        source=bool(config.get('dispatch'))
        return Case(label,fn,setup_case(config,random_source.randrange(1,0x10000)),receiver=lambda t:t['obj'],arguments=args,source_context=(lambda t:t['source']) if source else None,source_return_pc=0x401000 if source else 0)
    for flags in (0,1,2,0x100,0x101,0xff):
        for heap in (False,True):
            yield case(f'delete flags {flags} heap {heap}',0x438010,{'heapbits':heap,'strings':True},(flags,))
    yield case('destructor directly',0x438030,{'strings':True,'heapbits':True})
    for state in (-2,-1,0,1,2,3,4):
        for fail in (False,):
            for base in (False,True):
                yield case(f'dispatch {state} fail {fail} base {base}',0x438100,{'dispatch':True,'state':state,'fail':fail,'base':base},(state,))
    for first in (-101,-1,0,32,33,99,100,0x7fffffff):
        for second in (-3,-2,-1,0,1,2,3):
            yield case(f'idle voice {first} {second}',0x4384f0,{'randoms':(first,second),'visible':-1 if second==-2 else 0})
    for mode in (-1,0,1,2,3,4,5,6,7):
        for rand in (-5,-4,-3,-2,-1,0,1,2,3,19,20):
            yield case(f'update idle mode {mode} rand {rand}',0x4385b0,{'mode':mode,'randoms':(rand,rand)})
    for now,stamp,interval in ((199,100,100),(200,100,100),(201,100,100),(0,0xffffffff,1),(0xffffffff,0,0xffffffff)):
        yield case(f'idle timer {now} {stamp} {interval}',0x4385b0,{'mode':5,'now':now,'stamp':stamp,'interval':interval,'altinterval':0xffffffff})
    for altstamp,altinterval,now in ((101,99,199),(101,99,200),(101,99,201),(0xffffffff,1,0)):
        yield case(f'idle independent pacing timer {altstamp} {altinterval} {now}',0x4385b0,{'mode':6,'now':now,'interval':0xffffffff,'altstamp':altstamp,'altinterval':altinterval,'randoms':(19,)})
    for mode in (0,1,2,3,4,5,0xffffffff):
        for y in (49,50,51,100,149,150,151):
            yield case(f'home mode {mode} y {y}',0x4386d0,{'mode':mode,'y':y,'sound_latch':0,'randoms':(49,)})
    for config in ({'facing':0,'flags':2},{'facing':2,'flags':2},{'blocked':True},{'level':0x26b7},{'visible':-1,'sound_latch':0},{'mode':3,'randoms':(50,)},{'mode':3,'randoms':(-1,)},{'y':150,'change_slot':0x48,'changed_y':100},{'y':150,'change_slot':0x48,'changed_global':0x26b7}):
        yield case('home variants '+str(config),0x4386d0,{'mode':0,**config})
    for fn in (0x438900,0x4388a0):
        for posture in (0,5):
            for flags in (0,2):
                for resources in (False,True):
                    for difficulty in (1,3):
                        yield case(f'firing {fn:x} posture {posture} flags {flags} resources {resources} difficulty {difficulty}',fn,{'posture':posture,'flags':flags,'resources':resources,'difficulty':difficulty})
    yield case('try fire timer not elapsed',0x4388a0,{'now':199})
    for event in (0,1,2,0xffffffff):
        for latch in (0,1):
            for finished in (0,1):
                for delay in (0,3):
                    # Emission inputs below use the real Bullet lookup and allocation path.
                    if event==1 and not latch: continue
                    yield case(f'update firing event {event} latch {latch} finished {finished} delay {delay}',0x438a90,{'event':event,'latch':latch,'finished':finished,'delay':delay})
    for offset_x,offset_y,actor_x,actor_y in ((-91,37,11,213),(0,-23,73,59),(0x7fffffff,1,-19,0x7fffffff)):
        config={'event':1,'latch':0,'projectile_x':offset_x,'projectile_y':offset_y,'actor_x':actor_x,'actor_y':actor_y}
        yield case('projectile distinct coordinates '+str(config),0x438a90,config)
    for speed in (-0x80000000,-401,-1,0,1,400,0x7fffffff):
        for projectile_flags in (0,2):
            for sentinel in (False,True):
                yield case(f'projectile speed {speed} flags {projectile_flags} sentinel {sentinel}',0x438a90,{'event':1,'latch':0,'speed':speed,'projectile_flags':projectile_flags,'sentinel':sentinel,'sound':True,'sound_enabled':1})
    for before,after in ((400,-713),(-400,919),(0,-1)):
        yield case(f'projectile initializer changes speed {before} to {after}',0x438a90,{'event':1,'latch':0,'speed':before,'callback_speed':after})
    for resources in (False,True):
        for difficulty in (1,3):
            for scale in (0x3f800000,0x40400000):
                yield case(f'constructor resources {resources} difficulty {difficulty} scale {scale:x}',0x437a90,{'constructor':True,'images':resources,'resources':resources,'difficulty':difficulty,'scale':scale,'bit_capacity':64 if scale==0x40400000 else 32},(lambda t:t['actor'],))
