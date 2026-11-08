"""Original AquatisCrack behavior with distinct synthetic world data."""
from clawparity.cases import Case
from clawparity.world import world, animation, sprite, cstring, resource_manager


def cases(random_source):
    for state_value in (0, 1, 28, 29, 30, 31, 1000, 0xffffffff, 0x80000000):
        for hit in (False, True):
            values = [random_source.getrandbits(32) for _ in range(128)]
            def setup(env, state_value=state_value, hit=hit, values=values):
                resources = {}
                if hit:
                    resources = {'sprites': {'LEVEL_AQUATISWALLCRACK': sprite(env, 43, 79, (7, -11))},
                                 'animations': {'LEVEL_CRACKGLOW': animation(env, 137)}}
                tokens = world(env, resources=resources, idle_state=13,
                               owner_words={0x128:values[1],0x130:values[2]},
                               state_words={0x1c:state_value,0x18:values[3]})
                owner, state = tokens['owner'], tokens['state']
                observed = env.object(0x200, 'observations', fill=0)
                table = env.object(0x40, 'callbacks', fill=0)
                child = env.object(0x70, 'existing-child', words=values[:28])
                env.put(child, table)
                env.put(child+0x10,state)
                def record(env, call):
                    index = env.get(observed)
                    at = observed+4+index*32
                    env.put(at,call.receiver,len(call.arguments),env.get(state+0x1c),env.get(state+0x18),env.get(owner+0x128),env.get(owner+0x130),*(list(call.arguments)+[0,0])[:2])
                    env.put(observed,index+1)
                    env.put(call.receiver+0x60,values[7])
                    env.put(observed+0x140+index*4,env.get(call.receiver+0x60))
                    return values[8]
                for offset, argc in ((4,1),(8,1),(12,1),(0x1c,0),(0x20,0),(0x24,2)):
                    env.put(table+offset,env.stub('child-slot-'+str(offset),'thiscall',argc,record))
                if hit:
                    logic_values = {}
                    for index, key in enumerate(('LogicHit', 'LogicAttack')):
                        descriptor = env.object(0x20, key+'-descriptor', words=values[16+index*8:24+index*8])
                        logic_values[key] = descriptor
                        service = env.object(0x174,key+'-callback',words=values[:93])
                        env.put(service,table)
                        env.put(owner+(0x70 if index==0 else 0x78),service)
                    manager = resource_manager(env,logic_values,bucket_count=1,name='logic-hits')
                    env.put(tokens['world']+0x14,manager)
                    sounds = {('LEVEL_EARTHQUAKE'+str(i)): env.object(0x20,'quake-'+str(i),words=values[24+i*4:32+i*4]) for i in range(1,6)}
                    env.put(tokens['world']+0x28,resource_manager(env,sounds,bucket_count=1,name='sound-hits'))
                if state_value:
                    env.put(state+0x18,child)
                active = env.object(0x500,'active-controller',fill=0) if hit else 0
                if active:
                    env.put(active+0x4ec,values[11]|2)
                env.put(0x534874,active)
                text = cstring(env,'distinct scheduler state')
                strings=env.object(12,'scheduler-strings',words=[text,text,text])
                env.put(0x5376a0,state_value,state_value,strings,strings,4)
                env.put(0x5376b4,0,0)
                def allocate(env,call):
                    env.put(observed+0x180,call.arguments[0],env.get(state+0x1c),env.get(state+0x18))
                    return env.object(call.arguments[0],'constructed-child',words=values[:call.arguments[0]//4])
                env.override(0x4f63ec,allocate)
                return tokens
            yield Case(f'state {state_value:#x} resources {hit}',0x406400,setup,arguments=(lambda t:t['owner'],))

    for hit in (False, True):
        for effect_value in (0, random_source.getrandbits(32)):
            words = [random_source.getrandbits(32) for _ in range(128)]
            def setup_alias(env, hit=hit, effect_value=effect_value, words=words):
                resources = {}
                if hit:
                    resources = {'sprites': {'LEVEL_AQUATISWALLCRACK': sprite(env, 61, 83, (-17, 29))},
                                 'animations': {'LEVEL_CRACKGLOW': animation(env, 211)}}
                tokens = world(env,resources=resources,idle_state=None,
                               owner_words={0x128:words[1],0x130:words[2]})
                owner = tokens['owner']
                backing = env.object(0x200,'overlapping-state-and-child',words=words)
                child = backing+0x1c
                tokens['state'] = backing
                env.put(owner+0x6c,backing)
                env.put(backing+0x18,words[3],0)
                observations = env.object(0x180,'alias-observations',fill=0)
                methods = env.object(0x40,'alias-fresh-methods',fill=0)
                key = cstring(env,'LS_IDLE','alias-state-key')
                registry = env.object(20,'alias-state-registry',fill=0)
                env.put(registry,registry,registry,0,key,methods)
                env.put(0x537668+0x18,registry)
                def initialized(env,call):
                    env.put(observations,call.receiver,env.get(backing+0x18),env.get(backing+0x1c),env.get(owner+0x128),env.get(owner+0x130))
                    env.write(observations+0x20,env.read(child,0x70))
                    env.write(observations+0xa0,env.read(owner+0x188,0x30))
                    env.put(backing+0x18,effect_value)
                    env.put(child+0x64,words[13])
                    return words[14]
                env.put(methods+0x10,env.stub('alias-initialize','thiscall',0,initialized))
                active=env.object(0x500,'alias-active-controller',fill=0)
                env.put(active+0x4ec,words[15]|2)
                env.put(0x534874,active)
                def allocation(env,call):
                    env.put(observations+0xd0,call.arguments[0],env.get(backing+0x18),env.get(backing+0x1c))
                    return child
                env.override(0x4f63ec,allocation)
                return tokens
            yield Case(f'overlapping state allocation resources {hit} callback {effect_value:#x}',0x406400,setup_alias,arguments=(lambda t:t['owner'],))
