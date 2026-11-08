"""Original-only Parrot callback and complete construction cases."""
from clawparity.cases import Case
from clawparity.program import claw
from clawparity.world import world, animation, sprite, cstring, set_rect, set_rect_empty


def cases(random_source):
    # Read resource names from the hash-checked reference, never a native module.
    program = claw()
    def text(address):
        section = next(s for s in program.sections if s.address <= address < s.address + s.size)
        data = section.data[address-section.address:]
        return data[:data.index(b'\0')]

    def setup_for(state_value, hit=False, alias=False):
        noise = [random_source.getrandbits(32) for _ in range(32)]
        def setup(env):
            log = env.object(0x100, 'observed-callbacks', fill=0)
            table = env.object(0x30, 'case-methods', fill=0)
            tokens = world(env, owner_words={0x4c:noise[0], 0x50:noise[1], 0x64:1},
                           state_words={0x1c:state_value, 0x68:noise[2], 0x168:noise[3]},
                           idle_state=table)
            owner, state = tokens['owner'], tokens['state']
            env.put(tokens['idle_registry']+12, cstring(env,text(0x529c08),'parrot-registry-key'))
            target = env.object(0x450, 'existing-parrot', data=b''.join(x.to_bytes(4,'little') for x in noise), fill=0xA7)
            env.put(target, table)
            env.put(target+0x10, state)
            env.put(state+0x18, target)
            def record(slot):
                def effect(env, call):
                    count = env.get(log)
                    at = log + 4 + count * 24
                    env.put(at, slot, call.receiver, env.get(state+0x1c), env.get(state+0x18),
                            call.arguments[0] if call.arguments else noise[4], env.get(owner+0x6c))
                    env.put(log, count+1)
                    env.put(call.receiver+0x30, noise[5] ^ slot)
                    if slot == 16:
                        env.put(state+0x18, noise[22])
                    elif slot in (28,32):
                        env.put(state+0x1c, noise[23])
                    return noise[6]
                return effect
            for slot, argc in ((4,1),(8,1),(12,1),(16,0),(28,0),(32,0)):
                env.put(table+slot, env.stub('parrot-observer-'+str(slot),'thiscall',argc,record(slot)))
            # Existing-state redispatch goes through unchanged original CString logic.
            string = cstring(env, 'captured-'+str(noise[7]))
            entry = env.object(4, 'state-name', words=[string])
            env.put(0x5376a0, state_value, state_value, entry, entry, 4)
            if state_value == 0:
                if alias:
                    backing = env.object(0x650,'overlapping-state-and-construction',fill=0)
                    old = state
                    state = backing
                    env.write(state, env.read(old,0x180))
                    target = backing+0x1c
                    env.put(owner+0x6c,state)
                    env.put(0x537e88, owner)
                    timing = env.object(0x84,'world-timing',fill=0)
                    env.put(timing+0x80, noise[21])
                    env.put(state+0x14,timing)
                    env.put(state+0x18, noise[8])
                    env.override(0x4f63ec, lambda e,c: target if c.arguments[0]==0x450 else e.object(c.arguments[0],'construction-allocation',fill=0))
                env.override(0x546d5c, set_rect)
                env.override(0x546cdc, set_rect_empty)
                if hit:
                    from clawparity.world import resource_manager
                    spr = sprite(env, width=37,height=53,origin=(-7,11))
                    anim = animation(env,duration=73)
                    anim_names = [0x529b94,0x529b80,0x529b6c,0x529b54,0x529b3c,0x5234b4]
                    snd_names = [0x5266ec,0x524870,0x524864,0x524858,0x52484c,0x5266dc,0x529b24,0x529b08,0x529af0,0x529adc,0x529ac8]
                    for category, offset, entries in [('sprites',0x10,{text(0x529ba8):spr}),('animations',0x2c,{text(a):anim for a in anim_names}),('sounds',0x28,{text(a):noise[9+i] for i,a in enumerate(snd_names)})]:
                        manager=resource_manager(env,entries,bucket_count=1,name=category+'-hits')
                        env.put(tokens['world']+offset,manager)
            return {'owner':owner}
        return setup

    for state in (1,28,29,30,31,999,1000,1001,0xffffffff,0x80000000):
        yield Case('dispatch-'+str(state),0x465580,setup_for(state),arguments=(lambda t:t['owner'],))
    for hit in (False,True):
        yield Case('construct-alias-resources-'+str(hit),0x465580,setup_for(0,hit,True),arguments=(lambda t:t['owner'],))
