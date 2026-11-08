"""Original-backed state, constructor and callback cases for lava geyser."""
from clawparity.cases import Case
from clawparity.fixtures import allocate


def scene(words, frame=1, finished=0, delay=0, changed=False, action=True, fallback=False, constructor=False, alias_control=False, active=False, animation=False):
    def setup(env):
        base = env.object(0x240, 'geyser-state-backing', words=words[:80])
        owner = base + 0x40
        actor = env.object(0x240, 'actor', fill=0)
        control = owner - 0x1c if alias_control else env.object(0x120, 'control', words=words[:72])
        context = env.object(0x40, 'resources', fill=0)
        root = env.object(0x120, 'world', fill=0)
        clock = env.object(0x90, 'clock', fill=0)
        maps = [env.object(0x30, 'resource-map', fill=0) for _ in range(3)]
        for table in maps:
            env.put(table + 0x18, 1)
        env.put(context + 0x10, maps[0], maps[1])
        env.put(context + 0x2c, maps[2])
        env.put(actor + 0xc, context)
        env.put(actor + 0x6c, control)
        env.put(actor + 0x16c, frame)
        env.put(owner + 0xc, actor, control)
        env.put(owner + 0x2c, actor)
        env.put(owner + 0x9c, 0x10203040, delay, 0)
        env.put(root + 0x6c, clock)
        env.put(clock + 0x14, root)
        env.put(root + 0x80, 0x88776655)
        env.put(control + 0x64, 0x88776654 if changed else 0x88776655)
        env.put(0x537e88, root)
        env.put(0x537210, 0x10203040 + 7)
        env.put(0x5430c4, 3)
        env.put(0x537668 + 0x18, 0)
        env.put(actor + 0x188 + 0x1c, finished)
        env.put(actor + 0x188 + 0x14, 0)
        if action:
            timeline = env.object(0x18, 'action-timeline', fill=0)
            commands = env.object(4, 'action-command-pointers', fill=0)
            command = env.object(0x30, 'first-command', words=words[:12])
            env.put(timeline + 0xc, commands, 1)
            env.put(commands, command)
            env.put(command + 0x1c, 0x1234abcd)
            env.put(owner + 0xa4, timeline)
            buckets = env.object(4, 'action-map-buckets', fill=0)
            node = env.object(0x10, 'action-map-node', fill=0)
            env.put(maps[2] + 0x14, buckets)
            env.put(buckets, node)
            env.put(node, 0, 0, 0x5234b4 if fallback else 0x5285bc, timeline)
        if active:
            # The real animator decrements delay and returns before touching a command.
            env.put(actor + 0x190, timeline if action else maps[0])
            env.put(actor + 0x19c, 11, 0, finished)
        if constructor:
            alternate = env.object(0x240, 'old-actor', fill=0)
            alternate_control = env.object(0x120, 'old-control', words=words[:72])
            env.put(alternate + 0xc, context)
            env.put(alternate + 0x6c, alternate_control)
            env.put(owner + 0xc, alternate, alternate_control)
            env.put(owner + 0xa4, 0)
            # Sound resource lookup uses real hash nodes and indirect service methods.
            buckets = env.object(4, 'sound-buckets', fill=0)
            env.put(maps[1] + 0x14, buckets)
            head = 0
            for name in (0x522d54, 0x522d48):
                resource = env.object(0x18, 'sound-resource', words=words[:6])
                node = env.object(0x10, 'sound-hash-node', words=[head, 0, name, resource])
                head = node
            env.put(buckets, head)
            observations = env.object(8 * 0xb0, 'sound-observations', fill=0)
            def observe(env, call):
                ordinal = env.get(observations)
                env.write(observations + 4 + ordinal * 0xac, env.read(owner, 0xa8))
                env.put(observations, ordinal + 1)
                return 0x76abcdef
            for offset in (0x70, 0x78):
                sound = env.object(4, 'sound-instance', fill=0)
                methods = env.object(0x28, 'sound-methods', fill=0)
                env.put(methods + 0x1c, env.stub('sound stop', 'thiscall', 0, observe))
                env.put(methods + 0x24, env.stub('sound play', 'thiscall', 2, observe))
                env.put(sound, methods)
                env.put(actor + offset, sound)
                env.put(alternate + offset, sound)
        if constructor:
            env.put(owner + 0xa0, 0x719283a4)
        if animation:
            # The animation header aliases ordinary actor fields: its first/last
            # frame are actor+d0/d4, so the ordering of the lookup and store matters.
            resource = actor + 0x6c
            frame_pointers = env.object(21 * 4, 'animation-frame-pointers', words=words[:21])
            env.put(resource + 0x14, frame_pointers)
            env.put(resource + 0x64, 19, 20)
            buckets = env.object(4, 'animation-buckets', fill=0)
            node = env.object(0x10, 'animation-hash-node', words=[0,0,0x5285bc,resource])
            env.put(buckets, node)
            env.put(maps[0] + 0x14, buckets)
        return {'owner': owner, 'actor': actor, 'control': control}
    return setup


def dispatch(words, callback=True, fail=False):
    def setup(env):
        owner = env.object(0x40, 'dispatch-receiver', words=words[:16])
        metadata = env.object(0x20, 'RTTI-metadata', fill=0)
        readable = env.object(8, 'RTTI-type-info', fill=0)
        vt = env.object(12, 'RTTI-vtable', fill=0)
        env.put(vt, metadata)
        env.put(owner, vt + 4)
        env.put(metadata + 0xc, readable)
        records = env.object(3 * 8, 'state-table', fill=0)
        observed = env.object(16, 'callback-observation', fill=0)
        def effect(env, call):
            env.put(observed, call.receiver, env.get(0x537a20), env.get(owner + 4), 0xabcdef01)
            return 0x56473829
        fn = env.stub('state callback', 'thiscall', 0, effect)
        for i in range(3):
            env.put(records + 8 * i, fn if callback else 0, words[i])
        fallback = env.object(8, 'fallback-record', words=[fn, 0x12345678])
        err = env.object(0x20, 'error-channel', fill=0)
        env.put(err + 0xc, 4)
        env.put(0x537a00 + 4, err, 1, 3, records, fallback, 8)
        env.put(0x537a20, 0xdeadbeef)
        if fail:
            env.override(0x4a9070, allocate(fail=True))
        return {'owner': owner}
    return setup


def cases(random_source):
    words = [random_source.getrandbits(32) for _ in range(80)]
    for function in (0x456040, 0x4560c0):
        for action in (False, True):
            yield Case(f'{function:x} action={action}', function, scene(words, action=action), receiver=lambda t:t['owner'])
    for elapsed, threshold in ((0,0),(0,1),(1,1),(6,7),(7,7),(8,7),(0xffffffff,7),(0x80000000,0x7fffffff)):
        def setup(env, elapsed=elapsed, threshold=threshold):
            t=scene(words, delay=threshold)(env)
            env.put(0x537210, (0x10203040 + elapsed)&0xffffffff)
            return t
        yield Case(f'timer {elapsed:x}/{threshold:x}',0x4560a0,setup,receiver=lambda t:t['owner'])
    for frame in (0,1,2,10,19,20,21,0xffffffff,0x80000000,0x7fffffff):
        for finished, changed in ((0,False),(1,False),(0,True),(1,True)):
            for action in (False,True):
                yield Case(f'update frame={frame:x} finished={finished} changed={changed} action={action}',0x456120,scene(words,frame,finished,changed=changed,action=action),receiver=lambda t:t['owner'])
    for fallback in (False,True):
        for action in (False,True):
            yield Case(f'constructor fallback={fallback} action={action}',0x455ed0,scene(words,action=action,fallback=fallback,constructor=True),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],),initial_stack=((-20, b'\x67\x45\x23\x01'),))
    for index in (1,2,3,0,4,-1):
        for callback in (True,False):
            yield Case(f'dispatch index={index} callback={callback}',0x455b00,dispatch(words,callback=callback),receiver=lambda t:t['owner'],arguments=(index&0xffffffff,))
    for alias_control in (False,True):
        for fallback in (False,True):
            yield Case(f'constructor alias-control={alias_control} fallback={fallback}',0x455ed0,scene(words,constructor=True,alias_control=alias_control,fallback=fallback),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],),initial_stack=((-20,b'\x67\x45\x23\x01'),))
    for finished in (0,1):
        for action in (False,True):
            yield Case(f'active animator finished={finished} action={action}',0x456120,scene(words,finished=finished,action=action,active=True),receiver=lambda t:t['owner'])
    for fallback in (False,True):
        yield Case(f'constructor populated animation fallback={fallback}',0x455ed0,scene(words,constructor=True,animation=True,fallback=fallback),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))
