"""Independent original-backed palette, resource and controller profiles."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns, sequence

NEW = 0x4f63ec


def profile(payload, status=0, backup=True, entries=True, global_holder=False,
            dc=1, caps=20, query_failure=0, mutate=False):
    def setup(env):
        for address in (0x541374, 0x54139c, 0x5413a0, 0x5413a4, 0x5413a8):
            env.put(address, 0)
        receipt = env.object(0x5000, 'physical observations', fill=0)
        def record(env, call, data=None):
            n = env.get(receipt)
            at = receipt + 4 + n * 0x440
            env.put(at, call.receiver, len(call.arguments), *call.arguments)
            if data is not None:
                env.write(at + 0x40, data)
            env.put(receipt, n + 1)
        def com(name, slots):
            table = env.object(0x84, name + ' methods', fill=0)
            obj = env.object(4, name, words=[table])
            for offset, argc, effect in slots:
                env.put(table + offset, env.stub(name + str(offset), 'stdcall', argc, effect))
            return obj
        def get_entries(env, call):
            record(env, call)
            env.write(call.arguments[4], payload[:1024])
            return status
        def set_entries(env, call):
            count = call.arguments[3]
            data = env.read(call.arguments[4], min(count, 256) * 4) if count <= 256 else b''
            record(env, call, data)
            return status
        palette = com('palette', [(0x10, 5, get_entries), (0x18, 5, set_entries)])
        def create(env, call):
            record(env, call, env.read(call.arguments[2], 1024))
            env.put(call.arguments[3], palette)
            if mutate:
                env.put(call.arguments[3] + 8, alternate)
            return status
        dd = com('draw', [(0x14, 5, create), (0x58, 3, lambda e,c: (record(e,c),0)[1])])
        buf = env.object(1024, 'entries', data=payload[:1024])
        alternate = env.object(1024, 'alternate entries', data=payload[1024:2048])
        back = env.object(0x38, 'backend', fill=0x51)
        env.put(back, 0, palette, 0xa6, buf if entries else 0,
                env.object(1024, 'backup', fill=0xb9) if backup else 0, 0x87654321, 0)
        manager = env.object(0x3f0, 'manager', fill=0)
        env.put(manager, dd)
        # CPtrList with a free node and no plex allocations.
        nodes = env.object(12 * 8, 'free list nodes', fill=0)
        for i in range(8):
            env.put(nodes + i * 12, nodes + (i + 1) * 12 if i < 7 else 0)
        env.put(manager + 0x3d4 + 0x10, nodes)
        env.put(manager + 0x3d4 + 0x18, 8)
        surface = com('surface', [(0x7c, 2, lambda e,c: (record(e,c), status)[1]),
                                 (0x60, 1, returns(status)), (0x6c, 1, returns(0))])
        holder = env.object(12, 'surface holder', fill=0)
        env.put(holder + 8, surface)
        display = env.object(0x30, 'display', fill=0)
        env.put(display + 0x18, 8)
        env.put(display + 0x2c, holder)
        middle = env.object(0x14, 'middle', fill=0)
        env.put(middle + 0x10, display)
        context = env.object(0x20, 'context', fill=0)
        env.put(context + 4, middle)
        env.put(context + 0x1c, manager)
        wrapper = env.object(20, 'wrapper', words=[0x513d78, 0x13579, 0xa4, context, back])
        control = env.object(0x68, 'controller', fill=0)
        env.put(control + 0xc, context)
        env.put(control + 0x2c, holder)
        name = env.object(16, 'name', data=b'palette_key\0')
        # One bucket, one existing key: registration and removal execute MFC.
        string = env.object(28, 'CString key', words=[4, 11, 15], data=None)
        env.write(string + 12, b'palette_key\0')
        assoc = env.object(16, 'association', words=[0, 0, string + 12, wrapper])
        buckets = env.object(4, 'buckets', words=[assoc])
        env.put(control + 0x14, buckets, 1, 1, 0, 0, 4)
        env.put(control + 0x64, wrapper)
        owner = env.object(0x24, 'resource owner', fill=0)
        resource = env.object(0x2c, 'resource', fill=0)
        kind = env.object(4, 'resource kind', words=[0x504358])
        resource_bytes = env.object(len(payload), 'resource bytes', data=payload)
        env.put(resource, name)
        env.put(resource + 8, kind)
        env.put(resource + 0x14, len(payload), resource_bytes)
        env.put(resource + 0x24, owner)
        env.put(0x541390, 0x73a1)
        env.override(0x546ac8, lambda e,c: (record(e,c),0x814)[1])
        env.override(0x546acc, lambda e,c: (record(e,c),0x915)[1])
        env.override(0x546ac4, lambda e,c: (record(e,c),resource_bytes)[1])
        env.override(0x546910, returns(dc))
        env.override(0x546894, lambda e,c: 256 if c.arguments[1] == 0x68 else caps)
        def query(env, call):
            n = env.calls_so_far(0x546914)
            record(env, call)
            if n == query_failure:
                return 0
            if call.arguments[2] <= 256:
                env.write(call.arguments[3], payload[:call.arguments[2] * 4])
            return 1
        env.override(0x546914, query)
        env.override(0x5468b0, returns(1))
        env.override(0x546df0, sequence(100, 110, 110, 117, 130, 300, 0xffffffff))
        env.override(0x5469e4, lambda e,c: len(e.cstr(c.arguments[0])))
        def interlocked(delta):
            def effect(e,c):
                value = (e.get(c.arguments[0]) + delta) & 0xffffffff
                e.put(c.arguments[0], value)
                return value
            return effect
        env.override(0x5469e8, interlocked(-1))
        env.override(0x5469ec, interlocked(1))
        if global_holder:
            env.put(0x541374, env.object(4, 'global holder', words=[dd]))
        return dict(back=back, manager=manager, wrapper=wrapper, control=control,
                    name=name, resource=resource, owner=owner, kind=kind, buf=buf,
                    alternate=alternate, holder=holder, surface=surface, display=display,
                    dd=dd, data=resource_bytes, assoc=assoc, buckets=buckets, receipt=receipt)
    return setup


def cases(random_source):
    payload = bytes(random_source.randrange(256) for _ in range(2048))
    def case(label, function, receiver='back', args=(), configure=None, **options):
        setup_base = profile(payload, **options)
        def setup(env):
            t = setup_base(env)
            if configure:
                configure(env, t)
            return t
        def resolve(arg):
            return (lambda t: t[arg]) if isinstance(arg, str) else arg
        return Case(label, function, setup, receiver=resolve(receiver), arguments=tuple(resolve(a) for a in args),
                    initial_stack=((-0x400, payload[:1024]),))
    for full in (False, True):
        def prepare(env,t, full=full):
            if full:
                env.put(t['back'] + 0x18, env.object(32, 'auxiliary', fill=0x72))
            else:
                env.put(t['back'] + 0xc, 0, 0)
        yield case(f'destroy buffers {full}', 0x4bb2a0, configure=prepare)
    for status in (0, 0x887601c2):
        for backup in (False, True):
            yield case(f'backup existing {backup} status {status}', 0x4bb870, status=status, backup=backup)
    yield case('backup allocation failure', 0x4bb870, backup=False, configure=lambda e,t:e.override(NEW, allocate(fail=True)))
    for function, args in ((0x4bb100, ('dd','data',0x947)), (0x4bb240, ('dd','data',0x45)),
                           (0x4bb5a0, ('dd','data',2048,0x33))):
        for status in (0, 0x80004005):
            yield case(f'initialize {function:x} status {status}', function, args=args, status=status)
    for length in (0, 767, 768, 769):
        yield case(f'PCX length {length}', 0x4bb5a0, args=('dd','data',length,0x44))
    for start,count in ((0,0),(0,1),(3,5),(255,1),(0,256),(0xffffffff,1)):
        for global_holder in (False,True):
            yield case(f'copy {start} {count} global {global_holder}',0x4bb800,args=(start,count,'data',0x1357),global_holder=global_holder)
    for start,count in ((0,0),(3,1),(3,5),(255,1),(0,256),(3,0xffffffff)):
        for status in (0,0x80004005):
            yield case(f'fill {start} {count} {status}',0x4bb910,args=(start,count,0x123,0x245,0x367,0x29),status=status)
    for duration in (0,10,11,35):
        for count in (0,4):
            yield case(f'fade duration {duration} count {count}',0x4bb990,args=(5,count,0x121,0x2d3,0x3a4,duration),status=0x80004005 if duration==10 else 0)
    for dc,caps,query_failure,entries,status in ((0,20,0,True,0),(1,20,1,True,0),(1,20,2,True,0),
                                              (1,20,0,False,0),(1,0,0,True,0),(1,20,0,True,0),(1,20,0,True,0x80004005)):
        yield case(f'system palette {dc} {caps} {query_failure} {entries} {status}',0x4bbf60,dc=dc,caps=caps,query_failure=query_failure,entries=entries,status=status)
    for function,args in ((0x4bcac0,('data',0x83)),(0x4bcb40,('data',0x44)),(0x4bcbc0,('data',2048,0x17))):
        for status in (0,0x80004005):
            yield case(f'factory {function:x} status {status}',function,'manager',args,status=status)
    yield case('factory rejects short PCX',0x4bcbc0,'manager',('data',767,0x44))
    yield case('register backend',0x4bc9b0,'manager',('back',))
    def linked(env,t):
        node=env.object(12,'active list node',words=[0,0,t['back']])
        env.put(t['manager']+0x3d8,node,node,1)
        env.put(t['back'],node)
    yield case('remove linked backend',0x4bca10,'manager',('back',),configure=linked)
    for function in (0x4d6670,0x4d4810,0x4d47f0):
        for present in (False,True):
            def prepare(env,t,present=present):
                if present: linked(env,t)
                else: env.put(t['wrapper']+0x10,0)
            for flags in ((0,3) if function==0x4d47f0 else (0,)):
                yield case(f'wrapper teardown {function:x} backend {present} flags {flags}',function,'wrapper',(flags,) if function==0x4d47f0 else (),configure=prepare)
    for function,args in ((0x4d65a0,('data',0)),(0x4d65e0,('data',0)),(0x4d6620,('data',2048,0))):
        for flags,status in ((0,0),(3,0),(0x102,0),(1,0x80004005)):
            yield case(f'wrapper load {function:x} flags {flags} status {status}',function,'wrapper',args[:-1]+(flags,),status=status)
    for depth in (8,16,32):
        for status in (0,0x80004005):
            yield case(f'apply depth {depth} {status}',0x4d6690,'wrapper',status=status,configure=lambda e,t,d=depth:e.put(t['display']+0x18,d))
    for status in (0,0x80004005):
        yield case(f'display status {status}',0x4b96f0,'holder',('back',0xdeadbeef),status=status)
    yield case('surface no holder',0x4d4240,'control',configure=lambda e,t:e.put(t['control']+0x2c,0))
    for lost,restore in ((0,0),(0x887601c2,0),(0x887601c2,0x80004005)):
        def readiness(env,t,lost=lost,restore=restore):
            table=env.get(t['surface'])
            env.put(table+0x60,env.stub('IsLost','stdcall',1,returns(lost)))
            env.put(table+0x6c,env.stub('Restore','stdcall',1,returns(restore)))
        yield case(f'readiness {lost} {restore}',0x4d4240,'control',configure=readiness)
    for function,args in ((0x4d4420,('resource','name',0)),(0x4d45f0,('resource','name',0)),
                           (0x4d44f0,('data','name',0)),(0x4d4570,('name','name',0))):
        for status in (0,0x80004005):
            yield case(f'named resource {function:x} {status}',function,'control',args,status=status)
        if function in (0x4d4420,0x4d45f0):
            yield case(f'resource fallback name {function:x}',function,'control',('resource',0,1))
            def missing(env,t): env.put(t['resource']+0x14,0,0)
            yield case(f'resource missing {function:x}',function,'control',args,configure=missing)
    yield case('PCX resource type mismatch',0x4d45f0,'control',('resource','name',0),configure=lambda e,t:e.put(t['kind'],0x50414c))
    for match,cache,empty in ((True,True,False),(True,False,False),(False,True,False),(False,False,True)):
        def removal(env,t,match=match,cache=cache,empty=empty):
            if not match: env.put(t['assoc']+12,t['back'])
            if not cache: env.put(t['control']+0x64,t['back'])
            if empty: env.put(t['control']+0x1c,0)
            # Physical deleting destructor, observing receiver and cache publication.
            table=env.object(8,'deleting destructor methods')
            def destroy(e,c):
                e.put(t['receipt'],c.receiver,*c.arguments,e.get(t['control']+0x64),e.get(t['control']+0x1c))
                return c.receiver
            env.put(table+4,env.stub('deleting destructor','thiscall',1,destroy))
            env.put(t['wrapper'],table)
        yield case(f'remove wrapper match {match} cache {cache} empty {empty}',0x4d46f0,'control',('wrapper',),configure=removal)
    yield case('initialize callback changes entry buffer',0x4bb100,args=('dd','data',0x55),mutate=True)
    def second_allocation_fails(env,t):
        def effect(e,c):
            return 0 if e.calls_so_far(NEW)==2 else e.object(c.arguments[0], 'successful allocation', fill=0x8f)
        env.override(NEW,effect)
    yield case('initialize permits absent backup allocation',0x4bb100,args=('dd','data',0x51),configure=second_allocation_fails)
    yield case('null PCX backend with invalid short input',0x4bcbc0,'manager',('data',767,0x44),configure=lambda e,t:e.override(NEW,allocate(fail=True)))
    def changed_surface(env,t):
        table=env.object(0x70,'replacement surface methods',fill=0)
        other=env.object(4,'replacement surface',words=[table])
        env.put(table+0x6c,env.stub('replacement Restore','stdcall',1,returns(0x80004005)))
        holder=env.object(12,'replacement holder',fill=0)
        env.put(holder+8,other)
        def lost(e,c):
            e.put(t['control']+0x2c,holder)
            return 0x887601c2
        env.put(env.get(t['surface'])+0x60,env.stub('IsLost replaces holder','stdcall',1,lost))
    yield case('readiness reloads holder after IsLost',0x4d4240,'control',configure=changed_surface)
    def empty_match(env,t):
        env.put(t['assoc']+12,0)
        env.put(t['control']+0x64,0)
    yield case('remove null association value',0x4d46f0,'control',(0,),configure=empty_match)
    def later_match(env,t):
        key=env.object(20,'first key',words=[4,5,7],fill=0)
        env.write(key+12,b'other\0')
        new=env.object(16,'first nonmatching association',words=[t['assoc'],0,key+12,t['back']])
        env.put(t['buckets'],new)
        env.put(t['control']+0x1c,2)
        env.put(t['wrapper']+0x10,0)
    yield case('remove traverses prior association',0x4d46f0,'control',('wrapper',),configure=later_match)
    for failed_import in (0x546ac8,0x546acc,0x546ac4):
        yield case(f'embedded resource service fails {failed_import:x}',0x4d4570,'control',('name','name',0),configure=lambda e,t,a=failed_import:e.override(a,returns(0)))
    def overlap_reloads(env,t):
        env.put(t['back']+0xc,t['back'])
        env.put(t['data'],t['alternate'],0xc193742b)
    yield case('copy reloads entry buffer after aliasing store',0x4bb800,args=(3,2,'data',0x1b),configure=overlap_reloads)
    # The constructor installs the original 0x513d78 table. Leave slot +0x2c
    # untouched: its real 0x4d6560 target must parse the filename/resource key,
    # acquire embedded RGB triples and forward the fixed creation flags 0x44.
    # The separately owned 0x4d65e0 raw-entry loader cannot satisfy these cases.
    for resource_key in (b'EMBEDDED_PALETTE\0', b'palette.unknown\0',
                         b'folder.name.palette.unknown\0'):
        for flags, status, failed_import in (
                (0, 0, 0), (3, 0, 0), (0x102, 0, 0),
                (0, 0x80004005, 0),
                (0, 0, 0x546ac8), (0, 0, 0x546acc),
                (0, 0, 0x546ac4)):
            def embedded_route(env, t, resource_key=resource_key,
                               failed_import=failed_import):
                t['resource_key'] = env.object(len(resource_key),
                                               'embedded palette key',
                                               data=resource_key)
                if failed_import:
                    def fail(e, c):
                        # Preserve the call's observed physical arguments,
                        # receiver and current registration/list publication.
                        at = t['receipt'] + 0x4000
                        e.put(at, c.receiver, len(c.arguments), *c.arguments)
                        e.put(at + 0x20, e.get(t['assoc'] + 12),
                              e.get(t['manager'] + 0x3d8),
                              e.get(t['manager'] + 0x3e0))
                        return 0
                    env.override(failed_import, fail)
            yield case(
                f'real filename virtual embedded {resource_key!r} flags {flags:x} '
                f'status {status:x} failure {failed_import:x}',
                0x4d4570, 'control', ('resource_key', 'name', flags),
                configure=embedded_route, status=status)
