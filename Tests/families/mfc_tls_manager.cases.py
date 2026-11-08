"""Independent original-only cases for the MFC physical TLS services."""
from clawparity.cases import Case
from clawparity.fixtures import halt
from clawparity.env import NativeSourceContext

LOW, STACK_SIZE = 0x01FF0000, 0x20000
CPU_FIELDS = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eip', 'eflags', 'fsHead')

INIT, SLOT = 0x502FB6, 0x502FF8
TLS, INITIALIZE, ENTER, LEAVE = 0x546A90, 0x546AA4, 0x546AAC, 0x546A9C
ALLOC, HANDLE, UNLOCK, REALLOC, LOCK, RAISE = (0x546B1C, 0x546A8C, 0x5469C8, 0x546A88, 0x5469C4, 0x546958)


def profile(capacity=0, candidate=1, highwater=0, free=(), failure=False,
            inplace=False, tls=17, constructor=False, stop_init=False,
            locks=1, salt=0x78ABC240, reread=False, cached=False, source=None,
            frame=LOW+0x10000, alias=0, memoryfree=False, stop_tag=0,
            enter_state=None, leave_highwater=None):
    def setup(env):
        manager = env.object(0x44, 'manager-and-canaries', fill=0xB7)
        context = None
        if source is not None:
            pattern, registers, flags, chain = source
            env.write(LOW, (pattern * (STACK_SIZE//len(pattern)+1))[:STACK_SIZE])
            head = 0xFFFFFFFF
            for index in range(chain):
                slot = LOW+0x18000+index*16
                env.put(slot, head, 0x508CA4, 0xFFFFFFFF)
                head = slot
            if constructor and alias:
                manager = frame-28
            context = NativeSourceContext(72,1,0x7ff,0x7ff,
                registers[0],registers[1],manager,registers[2],registers[3],
                registers[4],registers[5],frame,INIT if constructor else SLOT,
                flags,head,0x462 if constructor else 0x400,0,0)
            env.put(frame,0x503381 if constructor else 0x503392)
        meta = env.object(8192 if source is not None else 2048, 'physical-services-observations', fill=0)
        # Current handle, data, physical size, lock count, flags, CS depth,
        # event count and allocated TLS index. All service state survives.
        olddata = 0
        if capacity:
            olddata = env.object((capacity + (32 if inplace else 0))*8,
                                 'old-global-data', fill=0xD6)
            for i in range(capacity):
                flags = ((salt + i*0x112244) & 0xFFFFFFFE) | (i not in free)
                env.put(olddata+i*8, flags, (salt ^ (i*0x1020305)) & 0xFFFFFFFF)
        if source is not None and alias and not constructor:
            olddata = frame+alias
        handle = 0xAB001123 if olddata else 0
        env.put(meta, handle, olddata, capacity*8, locks if olddata else 0,
                0x2002 if olddata else 0, 0, 0, 0xFFFFFFFF)
        if not constructor:
            env.put(manager, tls, capacity, candidate, highwater, olddata,
                    0xACDC1298, 4, 0x10293847, 0, 0, 0x557799BB, 0x88776655, 0)

        def record(e, c, tag):
            n = e.get(meta+24)
            at = meta+128+n*(512 if source is not None else 96)
            e.put(at, tag, c.stack_pointer, c.receiver, len(c.arguments),
                  *(list(c.arguments)+[0]* (4-len(c.arguments))))
            e.write(at+32, e.read(manager, 0x34))
            e.put(at+84, e.get(meta+12), e.get(meta+20), e.get(meta))
            e.put(meta+24, n+1)
            # Physical service policy: EAX is the explicit return value;
            # other CPU fields and arithmetic flags remain incoming.
            if c.source_context is not None:
                e.put(at+96,c.source_return_pc,e.get(LOCK),
                      *(getattr(c.source_context, field) for field in CPU_FIELDS))
                e.write(at+160,e.read(c.stack_pointer,256))
            if stop_tag == tag:
                return halt()(e,c)

        def tlsalloc(e, c):
            record(e,c,1)
            # Seeded live indices 2, 3 and 9 remain distinct from the result.
            e.put(meta+40, 2, 3, 9)
            if tls != 0xFFFFFFFF:
                e.put(meta+28, tls)
            return tls

        def initialize(e,c):
            record(e,c,2)
            if stop_init:
                return halt()(e,c)
            if not memoryfree:
                e.put(c.arguments[0], 0xF013579B, 0xFFFFFFFF, 0, 0, 0x2468ACE0, 0)
            return 0xFABC0192

        def enter(e,c):
            record(e,c,3)
            depth=e.get(meta+20)+1
            e.put(meta+20,depth)
            if not memoryfree:
                e.put(c.arguments[0]+8,depth,0x13579)
            if enter_state is not None:
                e.put(manager+8,*enter_state)
            return 0xDA315725

        def leave(e,c):
            record(e,c,4)
            depth=(e.get(meta+20)-1)&0xFFFFFFFF
            e.put(meta+20,depth)
            if not memoryfree:
                e.put(c.arguments[0]+8,depth,0 if not depth else 0x13579)
            if leave_highwater is not None:
                e.put(manager+12,leave_highwater)
            return 0xFA129A21

        def alloc(e,c):
            record(e,c,5)
            if failure:
                return 0
            flags,size=c.arguments
            data=e.object(size,'new-global-data',fill=0xCA)
            newhandle=0xBC002257
            e.put(meta,newhandle,data,size,0,flags)
            return newhandle

        def gethandle(e,c):
            record(e,c,6)
            if cached and e.calls_so_far(HANDLE)>1:
                # Change the source IAT after the allocator cached GlobalLock.
                # It must retain the saved physical import identity.
                e.put(LOCK,e.get(UNLOCK))
            return e.get(meta) if c.arguments[0] == e.get(meta+4) and c.arguments[0] else 0

        def unlock(e,c):
            record(e,c,7)
            if c.arguments[0] and c.arguments[0]==e.get(meta):
                count=max(0,e.get(meta+12)-1)
                e.put(meta+12,count)
                return int(count != 0)
            return 0

        def realloc(e,c):
            record(e,c,8)
            h,size,flags=c.arguments
            if failure:
                return 0
            old=e.get(meta+4)
            oldsize=e.get(meta+8)
            if inplace:
                data=old
            else:
                data=e.object(size,'moved-global-data',fill=0xEC)
                e.write(data,e.read(old,oldsize))
                e.release(old)
            newhandle=h if inplace else 0xCD003379
            e.put(meta,newhandle,data,size,0,flags)
            return newhandle

        def lock(e,c):
            record(e,c,9)
            h=c.arguments[0]
            if not h or h != e.get(meta):
                return 0
            e.put(meta+12,e.get(meta+12)+1)
            if reread:
                # Physical observer changes capacity before its source reread;
                # the affected existing prefix remains patterned.
                e.put(manager+4,capacity+1)
            return e.get(meta+4)

        def raise_exception(e,c):
            record(e,c,10)
            pointer=c.arguments[3]
            e.put(meta+64,pointer,*[e.get(pointer+i*4) for i in range(3)])
            alias=e.get(pointer+4)
            e.put(meta+80,alias,e.get(alias),c.stack_pointer,e.get(meta+20))
            return halt()(e,c)

        for address,effect in ((TLS,tlsalloc),(INITIALIZE,initialize),(ENTER,enter),
                               (LEAVE,leave),(ALLOC,alloc),(HANDLE,gethandle),
                               (UNLOCK,unlock),(REALLOC,realloc),(LOCK,lock),
                               (RAISE,raise_exception)):
            env.override(address,effect)
        return {'receiver':manager,'source':context} if source is not None else manager
    return setup


def cases(random_source):
    for tls in (0,1,17,0xFFFFFFFE,0xFFFFFFFF):
        yield Case(f'initialize TLS {tls:x}',INIT,profile(tls=tls,constructor=True),
                   receiver=lambda p:p,expect='halt' if tls==0xFFFFFFFF else 'return')
    yield Case('physical InitializeCriticalSection stop',INIT,
               profile(constructor=True,stop_init=True),receiver=lambda p:p,expect='halt')
    scenarios = [
        ('initial table',{}),
        ('initial physical allocation failure',dict(failure=True)),
        ('capacity one grows',dict(capacity=1,candidate=1)),
        ('free candidate highwater advances',dict(capacity=7,candidate=4,highwater=2,free=(4,))),
        ('free candidate highwater equal',dict(capacity=7,candidate=4,highwater=4,free=(4,))),
        ('free candidate highwater preserved',dict(capacity=7,candidate=4,highwater=6,free=(4,))),
        ('slot zero fast candidate',dict(capacity=4,candidate=0,free=(0,),highwater=0)),
        ('occupied scans first free',dict(capacity=8,candidate=5,free=(1,3))),
        ('outside candidate scans later free',dict(capacity=8,candidate=19,free=(6,))),
        ('full table moving growth',dict(capacity=6,candidate=3)),
        ('full table inplace growth',dict(capacity=6,candidate=6,inplace=True)),
        ('failed moving realloc retains old block',dict(capacity=6,candidate=3,failure=True)),
        ('cached GlobalLock on restoration',dict(capacity=6,candidate=6,failure=True,cached=True)),
        ('capacity reread after successful lock',dict(capacity=6,candidate=6,reread=True)),
        ('lock count two final unlock remains locked',dict(capacity=6,candidate=6,locks=2)),
        ('signed negative highwater',dict(capacity=5,candidate=2,free=(2,),highwater=0xFFFFFFFF)),
        ('signed maximal highwater preserves',dict(capacity=5,candidate=2,free=(2,),highwater=0x7FFFFFFF)),
    ]
    for label,options in scenarios:
        yield Case(label,SLOT,profile(**options),receiver=lambda p:p,
                   expect='halt' if options.get('failure') else 'return')
    for n in range(32):
        cap=random_source.randrange(2,65)
        candidate=random_source.randrange(0,cap+5)
        free=tuple(i for i in range(cap) if random_source.randrange(4)==0)
        options=dict(capacity=cap,candidate=candidate,free=free,
                     highwater=random_source.randrange(0,cap+8),
                     salt=random_source.getrandbits(32),inplace=bool(n%2))
        yield Case(f'random slot state {n}',SLOT,profile(**options),receiver=lambda p:p)


def source_case(label, random_source, **options):
    function = INIT if options.get('constructor') else SLOT
    registers = [random_source.getrandbits(32) for _ in range(6)]
    # Even saved words let the backed alias profiles select slot zero.
    if options.get('alias') and function == SLOT:
        registers = [value & 0xFFFFFFFE for value in registers]
    registers[5] = (0,0xFFFFFFFF,0x80000000,registers[5])[random_source.randrange(4)]
    if options.get('alias') and function == SLOT:
        registers[5] &= 0xFFFFFFFE
    flags = (2,0x8D7,0x47,0x892)[random_source.randrange(4)]
    pattern = bytes(random_source.randrange(256) for _ in range(257))
    source = (pattern, registers, flags, random_source.randrange(4))
    return Case('source '+label,function,profile(source=source,**options),
                receiver=lambda p:p['receiver'],source_context=lambda p:p['source'],
                source_return_pc=0x503381 if function == INIT else 0x503392,
                expect='halt' if options.get('failure') or options.get('stop_init') or
                       options.get('stop_tag') or options.get('tls') == 0xFFFFFFFF else 'return')


ordinary_cases = cases

def cases(random_source):
    yield from ordinary_cases(random_source)
    for tls in (0,1,17,0xFFFFFFFE,0xFFFFFFFF):
        yield source_case(f'initialize {tls:x}',random_source,constructor=True,tls=tls)
    yield source_case('initializer saved ESI alias',random_source,
                      constructor=True,alias=1,memoryfree=True)
    yield source_case('initializer physical section halt',random_source,constructor=True,stop_init=True)
    for tag in (1,2):
        yield source_case(f'initializer service halt {tag}',random_source,constructor=True,stop_tag=tag)
    scenarios = [
        ('cold',{}),('cold allocation failure',dict(failure=True)),
        ('capacity one grows',dict(capacity=1,candidate=1)),
        ('slot zero',dict(capacity=4,candidate=0,free=(0,))),
        ('candidate advances highwater',dict(capacity=7,candidate=4,highwater=2,free=(4,))),
        ('candidate equal highwater',dict(capacity=7,candidate=4,highwater=4,free=(4,))),
        ('candidate preserves highwater',dict(capacity=7,candidate=4,highwater=6,free=(4,))),
        ('scan earliest',dict(capacity=8,candidate=5,free=(1,3))),
        ('scan later',dict(capacity=8,candidate=19,free=(6,))),
        ('moving growth',dict(capacity=6,candidate=3)),
        ('inplace growth',dict(capacity=6,candidate=6,inplace=True)),
        ('failed realloc',dict(capacity=6,candidate=3,failure=True)),
        ('cached lock restoration',dict(capacity=6,candidate=6,failure=True,cached=True)),
        ('capacity reread',dict(capacity=6,candidate=6,reread=True)),
        ('nested existing locks',dict(capacity=6,candidate=6,locks=2)),
        ('signed negative highwater',dict(capacity=5,candidate=2,free=(2,),highwater=0xFFFFFFFF)),
        ('signed maximal highwater',dict(capacity=5,candidate=2,free=(2,),highwater=0x7FFFFFFF)),
        ('enter publishes candidate',dict(capacity=5,candidate=4,free=(2,),enter_state=(2,0x55667788))),
        ('leave observes then publishes highwater',dict(capacity=5,candidate=2,free=(2,),leave_highwater=0x12345678)),
    ]
    for label,options in scenarios:
        for repeat in range(3):
            yield source_case(f'{label} {repeat}',random_source,**options)
    for alias in (-12,-16,-20,-24):
        for repeat in range(4):
            yield source_case(f'saved register table alias {alias} {repeat}',random_source,
                              capacity=1,candidate=0,highwater=1,alias=alias,memoryfree=True)
    for tag in (3,4,5,6,7,8,9,10):
        options = dict(capacity=6,candidate=6,stop_tag=tag)
        if tag == 5:
            options.update(capacity=0,candidate=1)
        if tag == 10:
            options['failure']=True
        yield source_case(f'physical stop tag {tag}',random_source,**options)
    for capacity in (0,6):
        for tag in (6,9,4):
            yield source_case(f'failure restoration prefix {capacity} {tag}',random_source,
                              capacity=capacity,candidate=capacity or 1,failure=True,
                              cached=bool(capacity),stop_tag=tag)
    for n in range(64):
        cap=random_source.randrange(2,65)
        candidate=random_source.randrange(cap+5)
        free=tuple(i for i in range(cap) if random_source.randrange(4)==0)
        yield source_case(f'random {n}',random_source,capacity=cap,candidate=candidate,free=free,
                          highwater=random_source.getrandbits(32),salt=random_source.getrandbits(32),
                          inplace=bool(n%2),frame=LOW+0x8000+n*52)
