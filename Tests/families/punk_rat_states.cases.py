"""PunkRat cases derived from the retail instructions and real callees."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def setup_state(words, *, facing=0, finished=0, countdown=0, sound=0,
                audio=0, rand=10, inhibited=0, level=0, coordinates=(3.25, 3.25, 3.25),
                animation=0, tree=0, dispatch=None, destructor=False):
    def setup(env):
        obj = env.object(0x410, 'punk-rat', words=words)
        sprite = env.object(0x200, 'sprite',fill=0)
        state = env.object(0x180, 'state-data',fill=0)
        record = env.object(0x200, 'callback-observations', fill=0x67)
        vt = env.object(0xac, 'methods',fill=0)
        env.put(obj, vt)
        env.put(obj+0xc, sprite, state)
        env.put(obj+0x12c, sprite)
        env.put(sprite+0x40, facing)
        env.put(sprite+0x190, animation)
        env.put(sprite+0x19c, countdown)
        env.put(sprite+0x1a4, finished)
        # Animation is deliberately absent, so the real update callee returns early.
        env.put(sprite+0x190, 0)
        for offset, value in zip((0x68,0x80,0x98), coordinates):
            env.write(obj+offset, struct.pack('<d',value))
        env.put(0x541334, inhibited)
        env.put(0x534eac, level)
        env.put(0x532c0c, audio)
        env.put(0x532c10, 0x13579bdf)
        env.put(0x5430c4, 7)
        env.override(0x4a3050, returns(rand))
        snd = env.object(0x20, 'sound-resource',fill=0)
        channel = env.object(0x20, 'sound-player',fill=0)
        backend = env.object(0x80, 'disabled-sound-backend',fill=0)
        env.put(snd+0x10, channel)
        env.put(channel+0x10, backend)
        env.put(obj+0x404, snd if sound else 0)
        # Real cannon state used by 0x414640; no fake game body.
        cannon = env.object(0x80, 'cannon',fill=0)
        cannon_state = env.object(0x80, 'cannon-state',fill=0)
        controller = env.object(0x80, 'cannon-controller',fill=0)
        env.put(obj+0x408,cannon)
        env.put(cannon+0x6c,cannon_state)
        env.put(cannon_state+0x18,controller)
        env.put(controller+0x10,state)
        env.put(controller+0x2c,sprite)
        env.put(0x537680,0)
        if tree:
            node=env.object(0x14,'recoil-tree-leaf',fill=0)
            text=env.object(10,'recoil-key',data=b'LS_RECOIL\0',fill=0)
            env.put(node,node,node,0,text,tree)
            env.put(0x537680,node)
        # Callback records argument, receiver and the complete relevant object state.
        for offset, argc in ((4,1),(8,1),(12,1),(0x10,0),(0x1c,0),(0x20,0),
                             (0x58,0),(0x5c,1),(0x6c,1),(0x70,1),(0xa8,0)):
            def effect(e,c,offset=offset):
                count=e.get(record)
                if count == 0x67676767: count=0
                e.put(record,count+1,offset,c.receiver,len(c.arguments))
                e.put(record+16,*(c.arguments or (0xabcdef01,)))
                e.write(record+0x20,e.read(obj+0x120,0x40))
                e.write(record+0x60,e.read(sprite+0x180,0x30))
                return 0x87654321
            env.put(vt+offset,env.stub('method-%x'%offset,'thiscall',argc,effect))
        if destructor:
            env.put(obj+0x1a4,env.get(0x52e1c8)+12,env.get(0x52e1c8)+12)
            env.put(obj+0x2fc,0)
        if dispatch is not None:
            low,high,index,present,growfail=dispatch
            entries=env.object((high-low+1)*4,'dispatch-array',fill=0)
            fallback=env.object(4,'dispatch-fallback',fill=0)
            error=env.object(24,'array-error',fill=0);env.put(error+12,4)
            def callback(e,c):
                e.put(record,0xfade1234,c.receiver,e.get(0x538460),e.get(0x538464),e.get(0x538478))
                return 0x1357
            callback_address=env.stub('state-handler','thiscall',0,callback)
            if low<=index<=high and present: env.put(entries+(index-low)*4,callback_address)
            env.put(fallback,callback_address if present else 0)
            env.put(0x53845c,error,low,high,entries,fallback,4,0,0x3456)
            base_entries=env.object(4,'base-state-handler',words=[callback_address])
            env.put(0x537640,index,index,base_entries,base_entries,4)
            if growfail:
                env.override(0x4a9070,returns(0))
        return {'obj':obj,'sprite':sprite,'state':state,'record':record}
    return setup


def cases(random_source):
    words=[random_source.getrandbits(32) for _ in range(0x410//4)]
    # Signed remainders, exact threshold, disabled sound and all direction exits.
    for fn in (0x474c50,0x474d00):
        for rand in (0,9,10,99,100,-1,0x80000000,0x7fffffff):
            for facing,level,coords in ((0,0,(3.25,3.25,3.25)),(2,0,(3.25,3.25,3.25)),
                                        (0,0x26b7,(3.25,3.25,3.25)),(2,0x26b7,(3.25,3.25,3.25)),
                                        (0,0,(4.25,3.25,3.25))):
                yield Case(f'{fn:x} remainder {rand} facing {facing} level {level} {coords}',fn,
                    setup_state(words,rand=rand,sound=1,audio=1,facing=facing,level=level,coordinates=coords),
                    receiver=lambda t:t['obj'])
        for snd,audio,inhibited in ((0,1,0),(1,0,0),(1,1,1), (1,1,0)):
            for coords in ((0.,-0.,0.),(float('nan'),1.,2.),(float('inf'),float('inf'),float('inf'))):
                yield Case(f'{fn:x} sound {snd} {audio} inhibit {inhibited} coordinates {coords}',fn,
                    setup_state(words,sound=snd,audio=audio,rand=9,inhibited=inhibited,coordinates=coords),receiver=lambda t:t['obj'])
    for fn in (0x474db0,0x474e60):
        for facing in (0,1,2,3,0x80000002):
            for finished,countdown in ((0,0),(1,0),(1,1),(0xffffffff,0),(1,0xffffffff)):
                yield Case(f'{fn:x} facing {facing} done {finished} countdown {countdown}',fn,
                    setup_state(words,facing=facing,finished=finished,countdown=countdown),receiver=lambda t:t['obj'])
    for animation in (0,1):
        for tree in (0,29,0xffffffff):
            def setup(env,animation=animation,tree=tree):
                t=setup_state(words,tree=tree)(env)
                env.put(t['obj']+0x400,0)
                env.put(t['state']+0x1c,0x9876)
                if animation:
                    a=env.object(0x14,'recoil-animation',fill=0)
                    frames=env.object(4,'recoil-frame-array',fill=0)
                    frame=env.object(0x30,'recoil-frame',fill=0x45)
                    env.put(frames,frame);env.put(a+12,frames,1)
                    env.put(t['obj']+0x400,a)
                return t
            yield Case(f'recoil animation {animation} tree {tree}',0x474e10,setup,receiver=lambda t:t['obj'])
    yield Case('idle virtual zero argument',0x474ec0,setup_state(words),receiver=lambda t:t['obj'])
    for fn in (0x474710,0x4746f0):
        for flags in (0,1,2,3,0x100,0xffffffff):
            yield Case(f'destructor {fn:x} flags {flags}',fn,setup_state(words,destructor=True),
                       receiver=lambda t:t['obj'],arguments=(flags,) if fn==0x4746f0 else ())
    # Failed realloc sets EBP=0 inside 0x4db6e0, then its real error helper
    # dereferences [EBP+4]. Such calls cannot return under strict backing.
    for index in (-3,0,2,3,4):
        for present in (0,1):
            for growfail in (False,):
                yield Case(f'dispatch {index} present {present} realloc-fail {growfail}',0x4747e0,
                    setup_state(words,dispatch=(0,3,index,present,growfail)),receiver=lambda t:t['obj'],arguments=(index,))
    for state_id in (1,28,29,30,31,999,1000,0xffffffff):
        def setup(env,state_id=state_id):
            t=setup_state(words)(env)
            env.put(t['sprite']+0x6c,t['state'])
            env.put(t['state']+0x1c,state_id)
            env.put(t['state']+0x18,t['obj'])
            env.put(t['state']+0x1c,state_id)
            # The generic dispatcher indexes the object's state value.
            env.put(t['obj']+0x10,t['state'])
            string=env.object(16,'empty-state-string',words=[1,0,0,0])
            values=env.object(4,'generic-state-values',words=[string+12])
            env.put(0x5376a0,state_id,state_id,values,values,4,0,0)
            return t
        yield Case(f'factory event {state_id}',0x474330,setup,arguments=(lambda t:t['sprite'],))
    # Constructor invokes real base construction, resource lookup and animation setup.
    for defaults in (False,True):
        def setup(env,defaults=defaults):
            t=setup_state(words)(env)
            # Actual base constructor uses the supplied sprite as its game object.
            systems=env.object(0x30,'resource-systems',fill=0)
            env.put(t['sprite']+0xc,systems)
            env.put(t['state']+0xc,systems)
            collision=env.object(0x200,'collision-world',fill=0)
            env.put(systems+0x24,collision)
            for offset in (0x10,0x14,0x28,0x2c):
                resource=env.object(0x30,'empty-resource-map-%x'%offset,fill=0)
                env.put(resource+0x18,1)
                env.put(systems+offset,resource)
            env.put(t['sprite']+0x6c,t['state'])
            env.put(t['sprite']+8,0)
            env.put(t['sprite']+0x108,0 if defaults else 19)
            env.put(t['sprite']+0x148,0 if defaults else 25)
            env.put(t['sprite']+0x14c,17)
            env.put(t['state']+0x64,0)
            env.write(0x534938,b'\0')
            return t
        yield Case(f'constructor default values {defaults}',0x4743f0,setup,
                   receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    constructor_setup=setup
    for fn in (0x474bc0,0x474330):
        for facing in (0,2):
            for initialized in (False,True):
                def cannon_setup(env,facing=facing,initialized=initialized):
                    t=constructor_setup(env)
                    sprite=t['sprite'];systems=env.get(sprite+12)
                    manager=env.object(0x30,'sprite-manager',fill=0)
                    env.put(manager+12,systems)
                    free_node=env.object(12,'manager-list-node',fill=0)
                    env.put(manager+0x20,free_node)
                    env.put(systems+8,manager)
                    env.put(t['obj']+0x130,sprite)
                    env.put(sprite+0x40,facing)
                    env.put(sprite+0x64,0xed8 if initialized else 0x1122)
                    env.put(sprite+0x4c,123,456)
                    template=env.object(0x18,'ground-cannon-template',fill=0)
                    def init_cannon(e,c):
                        cannon=c.arguments[0]
                        controller=e.object(0x80,'created-cannon-controller',fill=0)
                        state=e.get(cannon+0x6c)
                        e.put(state+0x18,controller)
                        e.put(controller+0xc,sprite)
                        e.put(controller+0x2c,cannon)
                        e.put(controller+0x38,13,0,27)
                        e.put(t['record'],cannon,e.get(t['obj']+0x408),e.get(sprite+0x64),e.get(sprite+8))
                        if initialized: e.put(sprite+0x40,facing ^ 2)
                        return 0x2468
                    env.put(template+0x10,env.stub('cannon-object-logic','cdecl',1,init_cannon))
                    map_object=env.get(systems+0x14)
                    key=env.object(13,'ground-cannon-key',data=b'GroundCannon\0')
                    node=env.object(16,'ground-cannon-map-node',words=[0,0,key,template])
                    buckets=env.object(4,'ground-cannon-map-buckets',words=[node])
                    env.put(map_object+0x14,buckets,1)
                    env.put(t['state']+0x1c,0)
                    # Factory's newly constructed object uses this same sprite graph.
                    return t
                yield Case(f'{fn:x} cannon facing {facing} preinitialized {initialized}',fn,cannon_setup,
                           receiver=(lambda t:t['obj']) if fn==0x474bc0 else 0,
                           arguments=(lambda t:t['sprite'],) if fn==0x474330 else ())
    def heap_bitset(env):
        t=constructor_setup(env)
        env.write(0x534938,b'33\0')
        return t
    yield Case('constructor heap bitset',0x4743f0,heap_bitset,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    # Successful resource lookups have distinct animation identities and frame values.
    for missing in (None,'WALK','IDLE','STAND','STRIKE','HOME','RECOIL'):
        def resources(env,missing=missing):
            t=constructor_setup(env)
            systems=env.get(t['sprite']+12)
            env.put(t['sprite']+0x18c,t['sprite'])
            head=0
            for number,name in enumerate(('NULL','WALK','IDLE','STAND','STRIKE','HOME','RECOIL')):
                if name==missing: continue
                animation=env.object(0x14,'animation-'+name,fill=0)
                frame=env.object(0x30,'frame-'+name,fill=0)
                array=env.object(4,'frames-'+name,words=[frame])
                env.put(frame+0xc,9)
                env.put(frame+0x1c,0x100+number)
                env.put(animation+12,array,1)
                text=(('GAME_NULL' if name=='NULL' else 'LEVEL_PUNKRAT_'+name)+'\0').encode()
                key=env.object(len(text),'animation-key-'+name,data=text)
                head=env.object(16,'animation-map-node-'+name,words=[head,0,key,animation])
            buckets=env.object(4,'animation-buckets',words=[head])
            env.put(env.get(systems+0x2c)+0x14,buckets,1)
            return t
        yield Case(f'constructor animation resources missing {missing}',0x4743f0,resources,
                   receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    for flags in (0,1):
        def destructor_heap(env):
            t=setup_state(words,destructor=True)(env)
            data=env.object(8,'owned-bitset-buffer',words=[0x1240,0x6789])
            env.put(t['obj']+0x2fc,64,data)
            return t
        yield Case(f'destructor heap bitset flags {flags}',0x4746f0,destructor_heap,
                   receiver=lambda t:t['obj'],arguments=(flags,))
    # The metadata and sprite worlds are intentionally distinct. Moving a resource
    # receiver by four bytes must select the other graph or fail strict backing.
    for sound_keys in (('GAME_EEHH',),('GAME_MOUSEKILL',),('GAME_EEHH','GAME_MOUSEKILL')):
        for defaults in (False,True):
            def rich_resources(env,sound_keys=sound_keys,defaults=defaults):
                t=constructor_setup(env)
                sprite=t['sprite'];world=env.get(sprite+12)
                other=env.object(0x30,'metadata-world',fill=0)
                env.put(t['state']+12,other)
                for offset in (0x10,0x14,0x28,0x2c):
                    resource=env.object(0x30,'metadata-resource-map-%x'%offset,fill=0)
                    env.put(resource+0x18,1)
                    env.put(other+offset,resource)
                head=0
                for number,key_text in enumerate(sound_keys):
                    text=(key_text+'\0').encode()
                    key=env.object(len(text),'sound-key-'+key_text,data=text)
                    resource=env.object(0x18,'sound-value-'+key_text,fill=0x39+number)
                    head=env.object(16,'sound-node-'+key_text,words=[head,0,key,resource])
                buckets=env.object(4,'sound-buckets',words=[head])
                env.put(env.get(world+0x28)+0x14,buckets,1)
                # A successful GAME_NULL fallback must be different from every
                # successful named resource, including metadata-world lookups.
                head=0
                names=('NULL','WALK','IDLE','STAND','STRIKE','HOME','RECOIL')
                for number,name in enumerate(names):
                    if defaults and name in ('WALK','STRIKE'): continue
                    animation=env.object(0x14,'rich-animation-'+name,fill=0)
                    frame=env.object(0x30,'rich-frame-'+name,fill=0)
                    array=env.object(4,'rich-frames-'+name,words=[frame])
                    env.put(frame+12,9);env.put(frame+0x1c,0x256+number)
                    env.put(animation+12,array,1)
                    text=(('GAME_NULL' if name=='NULL' else 'LEVEL_PUNKRAT_'+name)+'\0').encode()
                    key=env.object(len(text),'rich-animation-key-'+name,data=text)
                    head=env.object(16,'rich-animation-node-'+name,words=[head,0,key,animation])
                buckets=env.object(4,'rich-animation-buckets',words=[head])
                env.put(env.get(world+0x2c)+0x14,buckets,1)
                env.put(sprite+0x18c,sprite)
                return t
            yield Case(f'constructor distinct worlds sounds {sound_keys} fallback {defaults}',0x4743f0,
                       rich_resources,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    for index in (0,1,2,3):
        def scratch(env,index=index):
            t=setup_state(words,dispatch=(0,3,index,1,False))(env)
            env.put(0x538478,0xa1234567)
            return t
        yield Case(f'dispatch nonzero scratch index {index}',0x4747e0,scratch,
                   receiver=lambda t:t['obj'],arguments=(index,))
    for counts in ((1,1),(2,3),(3,1)):
        for fn in (0x474710,0x4746f0):
            def strings(env,counts=counts):
                t=setup_state(words,destructor=True)(env)
                for offset,count in zip((0x1a4,0x1a8),counts):
                    header=env.object(20,'string-header-%x'%offset,words=[count,4,4,0x64636261,0])
                    env.put(t['obj']+offset,header+12)
                def decrement(e,c):
                    pointer=c.arguments[0]
                    value=(e.get(pointer)-1)&0xffffffff
                    e.put(pointer,value)
                    number=e.calls_so_far(0x5469e8)-1
                    e.put(t['record']+number*16,pointer,value,e.get(t['obj']),e.get(t['obj']+0x2fc))
                    return value
                env.override(0x5469e8,decrement)
                return t
            yield Case(f'nonempty destructor {fn:x} refs {counts}',fn,strings,
                       receiver=lambda t:t['obj'],arguments=(1,) if fn==0x4746f0 else ())
    rich_setup=rich_resources
    def sound_publication(env):
        t=rich_setup(env,sound_keys=('GAME_EEHH','GAME_MOUSEKILL'),defaults=False)
        world=env.get(t['sprite']+12)
        head=env.get(env.get(env.get(world+0x28)+0x14))
        while head:
            if env.cstr(env.get(head+8))==b'GAME_MOUSEKILL':
                sound_frame=env.object(0x30,'mouse-sound-and-walk-frame',fill=0x37)
                env.put(head+12,sound_frame)
            head=env.get(head)
        head=env.get(env.get(env.get(world+0x2c)+0x14))
        while head:
            if env.cstr(env.get(head+8))==b'LEVEL_PUNKRAT_WALK':
                # The selected frame is published in +3a4 before the real walk
                # transition reads it. This makes publication order observable.
                env.put(env.get(head+12)+12,t['obj']+0x3a4,1)
            head=env.get(head)
        return t
    yield Case('constructor sound publication before walk transition',0x4743f0,sound_publication,
               receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
