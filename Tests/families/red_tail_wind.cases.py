"""Original returning dispatch and complete RedTailWind construction."""
from clawparity.cases import Case
from clawparity.world import world, cstring

ENTRY = 0x4847B0


def fixture(status, words, resources=False, mutate=False):
    def setup(env):
        log = env.object(0x400, 'observations', fill=0)
        w = world(env, state_words={0x1c: status}, owner_words={0x40: words[0], 4: words[1]}, idle_state=None)
        owner, state = w['owner'], w['state']
        target = env.object(0x90, 'existing-wind', words=words, fill=0x57)
        table = env.object(0x30, 'wind-callbacks', fill=0)
        env.put(target, table)
        env.put(target + 0x10, state)
        env.put(state + 0x18, target)
        def record(tag, argc=0):
            def effect(e, call):
                count = e.get(log)
                at = log + 4 + count * 0x40
                e.put(at, tag, call.receiver, e.get(state+0x18), e.get(state+0x1c), e.get(owner+0x40), *call.arguments)
                e.write(at+0x24, e.read(call.receiver, 24))
                e.put(log, count+1)
                if mutate:
                    e.put(state+0x1c, words[5])
                    e.put(call.receiver+0x14, words[6])
                return words[7]
            return env.stub('capture-'+str(tag), 'thiscall', argc, effect)
        for off, argc in [(4,1),(8,1),(12,1),(0x1c,0),(0x20,0)]:
            env.put(table+off, record(off,argc))
        # Unchanged dispatch helper consumes a CString array indexed by state.
        base = env.object(8, 'dispatch-strings', fill=0)
        for idx in range(2):
            env.put(base+4*idx, cstring(env, 'state-'+str(idx)))
        env.put(0x5376a0, status, status+1, base, base, 4, 0, 0)
        env.put(0x53c19c, 0)
        if resources:
            from clawparity.world import resource_manager
            for off in (0x70,0x78):
                obj = env.object(0x174, 'existing-logic-'+str(off), fill=0)
                methods = env.object(0x30, 'logic-methods-'+str(off), fill=0)
                env.put(obj,methods)
                env.put(methods+0x1c, record(0x100+off))
                env.put(methods+0x24,record(0x200+off,2))
                env.put(owner+off,obj)
            hits={}
            for key in ('LogicHit','LogicAttack'):
                resource=env.object(0x20,key,fill=0)
                env.put(resource+0x10,words[2] if key=='LogicHit' else words[3])
                hits[key]=resource
            env.put(w['world']+0x14,resource_manager(env,hits,bucket_count=1))
            # Audio lookup hit whose unchanged capability method returns zero.
            audio=env.object(0x20,'wind-audio',fill=0)
            player=env.object(0x20,'audio-player',fill=0)
            capability=env.object(0x80,'audio-capability',fill=0)
            env.put(audio+0x10,player)
            env.put(player+0x10,capability)
            env.put(w['world']+0x28,resource_manager(env,{'LEVEL_REDTAIL_WINDWHISTLING':audio}))
        # Random allocator contents expose omitted constructor initialization.
        def allocate(e,call):
            size = call.arguments[0]
            pattern = b''.join(word.to_bytes(4, 'little') for word in words)
            ptr=e.object(size,'constructed-wind',data=(pattern*((size+31)//32))[:size])
            e.put(log+0x380,ptr,e.get(state+0x1c),e.get(state+0x18))
            return ptr
        env.override(0x4f63ec,allocate)
        return owner
    return setup


def cases(random_source):
    for status in (0,1,28,29,30,31,999,1000,1001,0xffffffff,0x80000000):
        words=[random_source.randrange(1,0xffffffff) for _ in range(8)]
        yield Case('dispatch '+hex(status),ENTRY,fixture(status,words),arguments=(lambda x:x,))
    for hits in (False,True):
        for index in range(4):
            words=[random_source.randrange(1,0xffffffff) for _ in range(8)]
            yield Case('complete construction resources '+str(hits)+' '+str(index),ENTRY,fixture(0,words,hits,index%2==1),arguments=(lambda x:x,))
    for status in (1,29,30):
        words=[random_source.randrange(1,0xffffffff) for _ in range(8)]
        yield Case('callbacks alter surviving state '+str(status),ENTRY,fixture(status,words,mutate=True),arguments=(lambda x:x,))

    # Constructor's unchanged state write can replace its own vtable when the
    # state record aliases the allocation. The ES_IDLE registry supplies an
    # ordinary value, and the original writes it through state + 0x1c.
    for change_state in (False, True):
        words=[random_source.randrange(1,0xffffffff) for _ in range(8)]
        def alias_setup(env, words=words, change_state=change_state):
            w=world(env, state_words={0x1c:0}, owner_words={0x40:words[0]}, idle_state=None)
            owner,state=w['owner'],w['state']
            pattern=b''.join(word.to_bytes(4,'little') for word in words)
            storage=env.object(0x200,'backed-overlapping-wind-state',data=pattern*16)
            wind=storage+0x40
            alias_state=wind-0x1c
            observations=env.object(0x180,'initialization-publication-observations',fill=0)
            methods=env.object(0x30,'constructor-produced-dispatch',fill=0)
            key=cstring(env,'ES_IDLE','alias-idle-key')
            node=env.object(20,'alias-idle-registry',fill=0)
            env.put(node,node,node,0,key,methods)
            env.put(0x537668+0x18,node)
            env.put(0x53c19c,0)
            sentinel=env.object(0x20,'prepublication-sentinel',fill=0x71)
            env.put(state+0x18,sentinel)
            def initialize(e,call):
                e.put(observations,call.receiver,e.get(state+0x18),e.get(state+0x1c),e.get(owner+0x6c),e.get(alias_state+0x1c))
                e.write(observations+0x20,e.read(call.receiver,0x5c))
                e.write(observations+0x80,e.read(alias_state,0x38))
                if change_state:
                    e.put(state+0x18,words[1])
                    e.put(state+0x1c,words[2])
                    e.put(call.receiver+0x54,words[3])
                return words[4]
            env.put(methods+0x10,env.stub('aliased-original-initialization','thiscall',0,initialize))
            def allocation(e,call):
                e.put(observations+0x100,*call.arguments,e.get(state+0x1c),e.get(state+0x18))
                e.put(owner+0x6c,alias_state)
                return wind
            env.override(0x4f63ec,allocation)
            return owner
        yield Case('original late state write supplies init callback '+str(change_state),ENTRY,alias_setup,arguments=(lambda x:x,))
