"""Independent v1.3 LogicBump registration, binding and tail-adapter cases."""
from clawparity.cases import Case

NEW = 0x4fcaea
NAMES = (b'LogicHit', b'LogicAttack', b'LogicBump')


def cases(random_source):
    # All combinations force each registry guard independently, including later
    # registration after earlier callbacks have had observable effects.
    for present in range(8):
        for replacement in (False, True):
            noise = random_source.getrandbits(32)
            def setup(env, present=present, replacement=replacement, noise=noise):
                actor = env.object(0x190, 'actor', fill=0x65)
                scene = env.object(0x40, 'scene', fill=0x3d)
                manager = env.object(0x40, 'registry', fill=0)
                other = env.object(0x40, 'replacement-registry', fill=0)
                log = env.object(0x100, 'registration-observations', fill=0)
                env.put(actor+0xc, scene)
                env.put(scene+0x14, manager)
                table = env.object(0x24, 'registry-methods', fill=0)
                env.put(manager, table)
                env.put(other, table)
                nodes = []
                for i, name in enumerate(NAMES):
                    if present & (1 << i):
                        key = env.object(16, f'key-{i}', data=name+b'\0', fill=0)
                        meta = env.object(20, f'metadata-{i}', fill=0xa0+i)
                        node = env.object(16, f'entry-{i}', fill=0)
                        env.put(node, nodes[-1] if nodes else 0, 0, key, meta)
                        nodes.append(node)
                for reg in (manager, other):
                    bucket = env.object(4, 'bucket', words=[nodes[-1] if nodes else 0])
                    env.put(reg+0x14, bucket, 1)
                def register(env, call):
                    index = env.get(log)
                    dst = log+4+index*0x20
                    env.put(dst, call.receiver, *call.arguments, env.get(scene+0x14), noise)
                    env.put(log, index+1)
                    if replacement:
                        env.put(scene+0x14, other)
                    return noise
                method = env.stub('register-logic', 'thiscall', 3, register)
                env.put(table+0x1c, method)
                return actor
            yield Case(f'registry present={present} replace={replacement}', 0x404400,
                       setup, arguments=(lambda a:a,),
                       initial_stack=((-4, (noise | 1).to_bytes(4, 'little')),))

    # Each path starts with patterned fields to reveal unwanted clearing,
    # allocation-size changes and partial initialization.
    for named in (False, True):
        for state in ('null-meta', 'allocate', 'allocate-null-callback', 'allocate-fail', 'existing', 'clear-null', 'clear-replace'):
            for result in (0, 1, 0x81234567):
                noise = random_source.getrandbits(32)
                def setup(env, named=named, state=state, result=result, noise=noise):
                    actor = env.object(0x190, 'actor', fill=0x67)
                    scene = env.object(0x40, 'scene', fill=0x4b)
                    manager = env.object(0x40, 'registry', fill=0)
                    methods = env.object(0x24, 'logic-methods', fill=0)
                    prior = env.object(0x17c, 'prior-logic', fill=0x85)
                    alternate = env.object(0x17c, 'alternate-logic', fill=0x79)
                    log = env.object(0x180, 'binding-observations', fill=0)
                    metadata = env.object(20, 'metadata', fill=0x2a)
                    callback = 0 if state=='allocate-null-callback' else (noise | 1)
                    env.put(metadata+0x10, callback)
                    env.put(actor+4, noise)
                    env.put(actor+0xc, scene)
                    existing = state in ('existing', 'clear-null', 'clear-replace')
                    env.put(actor+0x90, prior if existing else 0)
                    env.put(scene+0x14, manager)
                    name = env.object(16, 'name', data=b'LogicBump\0', fill=0)
                    node = env.object(16, 'map-entry', words=[0, 0, name, metadata])
                    bucket = env.object(4, 'map-bucket', words=[0 if state=='null-meta' else node])
                    env.put(manager+0x14, bucket, 1)
                    env.put(prior, methods)
                    env.put(alternate, methods)
                    def clear(env, call):
                        env.put(log+0x10, call.receiver, env.get(actor+0x90), env.get(metadata+0x10))
                        env.put(log, env.get(log)+1)
                        env.put(metadata+0x10, callback ^ 0x10203040)
                        if state=='clear-null':
                            env.put(actor+0x90, 0)
                        elif state=='clear-replace':
                            env.put(actor+0x90, alternate)
                        return noise
                    def initialize(env, call):
                        env.put(log+0x30, call.receiver, *call.arguments, env.get(actor+0x90), env.get(log))
                        env.put(log+4, env.get(log+4)+1)
                        return result
                    env.put(methods+0x14, env.stub('clear-bump', 'thiscall', 0, clear))
                    env.put(methods+0x1c, env.stub('initialize-bump', 'thiscall', 2, initialize))
                    def allocate(env, call):
                        env.put(log+0x60, *call.arguments, env.get(actor+0x90))
                        if state=='allocate-fail':
                            return 0
                        # Object header reads happen AFTER allocation and must
                        # observe values changed by the allocator provider.
                        env.put(actor+4, noise ^ 0x55555555)
                        env.put(actor+0xc, manager)
                        return env.object(call.arguments[0], 'allocated-bump', fill=0xac)
                    env.override(NEW, allocate)
                    return dict(actor=actor, arg=name if named else (0 if state=='null-meta' else metadata))
                yield Case(f'{"named" if named else "direct"} {state} result={result:x}',
                           0x4c78f0 if named else 0x4c7850, setup,
                           receiver=lambda t:t['actor'], arguments=(lambda t:t['arg'],),
                           initial_stack=((-4, (noise | 1).to_bytes(4, 'little')),))

    # Tail thunk preserves the caller's single actor argument but dispatches
    # the C++ hook with no stack arguments and ECX from primary logic+0x18.
    for result in (0, 1, 2, 0xffffffff, random_source.getrandbits(32)):
        def setup(env, result=result):
            actor = env.object(0x190, 'actor', fill=0x71)
            logic = env.object(0x17c, 'primary-logic', fill=0x4a)
            body = env.object(0x4c8, 'cpp-instance', fill=0x37)
            methods = env.object(0x40, 'cpp-methods', fill=0)
            log = env.object(20, 'hook-observations', fill=0)
            env.put(actor+0x7c, logic)
            env.put(logic+0x18, body)
            env.put(body, methods)
            def hook(env, call):
                env.put(log, call.receiver, env.get(actor+0x7c), env.get(logic+0x18), len(call.arguments))
                env.put(body+0x34, result ^ 0xf0f0f0f0)
                return result
            env.put(methods+0x20, env.stub('bump-hook', 'thiscall', 0, hook))
            return actor
        yield Case(f'bump tail result={result:x}', 0x4def30, setup, arguments=(lambda a:a,))

    # The default C++ bump method is a real original entry, not a fixture.
    # Patterned receivers make accidental writes visible; null checks would
    # also change the unconditional result for the null-receiver case.
    for fill in (None, 0x00, 0xa5):
        payload = bytes(random_source.getrandbits(8) for _ in range(0x4c8))
        def setup(env, fill=fill, payload=payload):
            if fill is None:
                return 0
            return env.object(0x4c8, 'default-bump-instance', data=payload, fill=fill)
        yield Case(f'default bump direct fill={fill}', 0x40b630, setup,
                   receiver=lambda body:body)

    # Exercise the app callback chain through the actual default method.
    # These cases retain the complete three-object lookup, with independently
    # patterned objects, and compare the original method's consumed EAX result.
    for index in range(3):
        actor_data = bytes(random_source.getrandbits(8) for _ in range(0x190))
        logic_data = bytes(random_source.getrandbits(8) for _ in range(0x17c))
        body_data = bytes(random_source.getrandbits(8) for _ in range(0x4c8))
        def setup(env, actor_data=actor_data, logic_data=logic_data, body_data=body_data):
            actor = env.object(0x190, 'default-bump-actor', data=actor_data)
            logic = env.object(0x17c, 'default-bump-primary-logic', data=logic_data)
            body = env.object(0x4c8, 'default-bump-cpp-instance', data=body_data)
            methods = env.object(0x40, 'default-bump-cpp-methods', fill=0)
            env.put(actor+0x7c, logic)
            env.put(logic+0x18, body)
            env.put(body, methods)
            env.put(methods+0x20, 0x40b630)
            return actor
        yield Case(f'bump tail actual default method {index}', 0x4def30, setup,
                   arguments=(lambda actor:actor,))

    # Shared initializer: null callback leaves the entire patterned image alone.
    for callback in (0, 1, 0xffffffff, random_source.getrandbits(32) | 1):
        for argument in (0, 1, 0x80000000, random_source.getrandbits(32)):
            payload = bytes(random_source.getrandbits(8) for _ in range(0x17c))
            def setup(env, payload=payload):
                return env.object(0x17c, 'initializer-logic', data=payload)
            yield Case(f'initialize callback={callback:x} argument={argument:x}',
                       0x4c83f0, setup, receiver=lambda logic:logic,
                       arguments=(callback, argument))

    # Observe cleanup publication at both external calls and change the object
    # from delete so that the later body pointer must be reloaded.
    for buffer_present in (False, True):
        for body_present in (False, True):
            for replace_body in (False, True):
                noise = random_source.getrandbits(32) | 1
                def setup(env, buffer_present=buffer_present, body_present=body_present,
                          replace_body=replace_body, noise=noise):
                    logic = env.object(0x17c, 'cleanup-logic', fill=0xab)
                    buffer = env.object(28, 'cleanup-buffer', fill=0x73)
                    body = env.object(32, 'cleanup-body', fill=0x35)
                    alternate = env.object(32, 'cleanup-alternate-body', fill=0xc7)
                    methods = env.object(4, 'cleanup-body-methods', fill=0)
                    log = env.object(0x80, 'cleanup-observations', fill=0)
                    env.put(logic+0x10, noise, buffer if buffer_present else 0,
                            body if body_present else 0)
                    env.put(logic+0x170, noise ^ 0x11111111)
                    env.put(logic+0x178, noise ^ 0x22222222)
                    env.put(body, methods)
                    env.put(alternate, methods)
                    def destroy(env, call):
                        env.put(log+0x30, call.receiver, *call.arguments,
                                env.get(logic+0x10), env.get(logic+0x14),
                                env.get(logic+0x18), env.get(logic+0x170), env.get(logic+0x178))
                        env.put(logic+0x18, body)
                        env.put(logic+0x170, noise ^ 0x33333333)
                        env.release(call.receiver)
                        return noise
                    env.put(methods, env.stub('destroy-cpp-body', 'thiscall', 1, destroy))
                    def delete(env, call):
                        env.put(log, *call.arguments, env.get(logic+0x10),
                                env.get(logic+0x14), env.get(logic+0x18),
                                env.get(logic+0x170), env.get(logic+0x178))
                        if replace_body:
                            env.put(logic+0x18, alternate)
                        env.put(logic+0x14, 0)
                        env.release(call.arguments[0])
                        return 0
                    env.override(0x4fcb13, delete)
                    return logic
                yield Case(f'cleanup buffer={buffer_present} body={body_present} replace={replace_body}',
                           0x4c8440, setup, receiver=lambda logic:logic)

    # Sibling binding slots differ only in their actor field. Give every other
    # slot a distinct backed object to expose writes or dispatch to a wrong slot.
    for function, offset in ((0x4c7690, 0x80), (0x4c7770, 0x88)):
        for state in ('null-meta', 'allocate', 'allocate-null-callback', 'allocate-fail',
                      'existing', 'clear-null', 'clear-replace'):
            for result in (0, 1, random_source.getrandbits(32) | 1):
                noise = random_source.getrandbits(32) | 1
                def setup(env, offset=offset, state=state, result=result, noise=noise):
                    actor = env.object(0x190, 'sibling-actor', fill=0x69)
                    metadata = env.object(20, 'sibling-metadata', fill=0x31)
                    methods = env.object(0x24, 'sibling-methods', fill=0)
                    prior = env.object(0x17c, 'sibling-prior', fill=0x75)
                    alternate = env.object(0x17c, 'sibling-alternate', fill=0x89)
                    scene = env.object(0x40, 'sibling-scene', fill=0x21)
                    log = env.object(0x100, 'sibling-observations', fill=0)
                    env.put(actor+4, noise)
                    env.put(actor+0xc, scene)
                    for slot in (0x80, 0x88, 0x90):
                        decoy = env.object(0x17c, f'sibling-decoy-{slot:x}', fill=slot)
                        env.put(decoy, methods)
                        env.put(actor+slot, decoy)
                    existing = state in ('existing', 'clear-null', 'clear-replace')
                    env.put(actor+offset, prior if existing else 0)
                    callback = 0 if state=='allocate-null-callback' else noise
                    env.put(metadata+0x10, callback)
                    env.put(prior, methods)
                    env.put(alternate, methods)
                    def clear(env, call):
                        env.put(log, call.receiver, env.get(actor+offset), env.get(metadata+0x10))
                        env.put(metadata+0x10, callback ^ 0x12345678)
                        if state=='clear-null':
                            env.put(actor+offset, 0)
                        elif state=='clear-replace':
                            env.put(actor+offset, alternate)
                        return noise
                    def initialize(env, call):
                        env.put(log+0x20, call.receiver, *call.arguments, env.get(actor+offset))
                        return result
                    env.put(methods+0x14, env.stub('clear-sibling', 'thiscall', 0, clear))
                    env.put(methods+0x1c, env.stub('initialize-sibling', 'thiscall', 2, initialize))
                    def allocate(env, call):
                        env.put(log+0x40, *call.arguments, env.get(actor+offset))
                        if state=='allocate-fail':
                            return 0
                        env.put(actor+4, noise ^ 0x55555555)
                        env.put(actor+0xc, prior)
                        return env.object(call.arguments[0], 'sibling-allocation', fill=0xda)
                    env.override(NEW, allocate)
                    return dict(actor=actor, metadata=0 if state=='null-meta' else metadata)
                yield Case(f'sibling {function:x} {state} result={result:x}', function, setup,
                           receiver=lambda t:t['actor'], arguments=(lambda t:t['metadata'],))

    # Real initializer and cleanup composition for all three binding slots,
    # including allocated logic using its original vtable directly.
    for function, offset in ((0x4c7690, 0x80), (0x4c7770, 0x88), (0x4c7850, 0x90)):
        for mode in ('allocate', 'existing-empty', 'existing-resources'):
            for callback in (0, 1, random_source.getrandbits(32) | 1):
                payload = bytes(random_source.getrandbits(8) for _ in range(0x17c))
                noise = random_source.getrandbits(32) | 1
                def setup(env, offset=offset, mode=mode, callback=callback, payload=payload, noise=noise):
                    actor = env.object(0x190, 'composed-actor', fill=0x79)
                    scene = env.object(0x40, 'composed-scene', fill=0x27)
                    metadata = env.object(20, 'composed-metadata', fill=0x98)
                    logic = env.object(0x17c, 'composed-prior-logic', data=payload)
                    methods = env.object(0x24, 'composed-logic-methods', fill=0)
                    env.put(methods+0x14, 0x4c8440)
                    env.put(methods+0x1c, 0x4c83f0)
                    env.put(logic, methods)
                    env.put(logic+0x14, 0, 0)
                    env.put(actor+4, noise)
                    env.put(actor+0xc, scene)
                    for slot in (0x80, 0x88, 0x90):
                        decoy = env.object(0x17c, f'composed-decoy-{slot:x}', fill=slot)
                        env.put(decoy, methods)
                        env.put(decoy+0x14, 0, 0)
                        env.put(actor+slot, decoy)
                    env.put(actor+offset, 0 if mode=='allocate' else logic)
                    env.put(metadata+0x10, callback)
                    if mode=='existing-resources':
                        buffer = env.object(24, 'composed-buffer', fill=0xb1)
                        body = env.object(32, 'composed-body', fill=0xc3)
                        body_methods = env.object(4, 'composed-body-methods', fill=0)
                        log = env.object(32, 'composed-destruction-observations', fill=0)
                        env.put(body, body_methods)
                        env.put(logic+0x14, buffer, body)
                        def destroy(env, call):
                            env.put(log, call.receiver, *call.arguments, env.get(actor+offset),
                                    env.get(logic+0x10), env.get(logic+0x14),
                                    env.get(logic+0x18), env.get(logic+0x178))
                            env.put(metadata+0x10, callback ^ 0xa5a5a5a5)
                            env.release(call.receiver)
                            return noise
                        env.put(body_methods, env.stub('composed-body-destruction', 'thiscall', 1, destroy))
                    def allocate(env, call):
                        env.put(actor+4, noise ^ 0x13579bdf)
                        env.put(actor+0xc, logic)
                        return env.object(call.arguments[0], 'composed-allocation', data=payload)
                    env.override(NEW, allocate)
                    return dict(actor=actor, metadata=metadata)
                yield Case(f'composed binder {function:x} {mode} callback={callback:x}',
                           function, setup, receiver=lambda t:t['actor'],
                           arguments=(lambda t:t['metadata'],))
