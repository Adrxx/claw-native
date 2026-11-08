"""Original-only TLS cases; physical service state and observations survive in heap."""
from clawparity.cases import Case
from clawparity.fixtures import halt
from clawparity.env import NativeSourceContext, HEAP_BASE
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

GET, SET, PUB = 0x50335e, 0x503167, 0x540af0
IMPORTS = (0x546a90,0x546a7c,0x546a84,0x546aa4,0x546aac,0x546a9c,
           0x546b1c,0x546a8c,0x5469c8,0x546a88,0x5469c4,0x546aa8,0x546a80,0x546958)


def profile(*, cold=False, slot=1, count=4, high=7, missing=False,
            empty=False, value=0x789abcde, failure=None, publish_failure=False,
            factory_change=False, newslot=False, grow_slots=False, thread=3,
            alias=None, negative=False, absent=False, thread_miss=False, owner_alias=False, source_function=None, factory_pc=0x502335,
            frame=STACK_TOP, source_alias=None, registers=None, application=False,
            prelude=None, nested_fs=False, in_place=False):
    def setup(env):
        trace = env.object(65536 if application else 8192, 'physical observations', fill=0)
        state = env.object(16384 if application else 4096, 'physical TLS and allocation registry', fill=0)
        tls_offsets=(64,76,88,100)+tuple(range(4096,8192,12)) if application else (64,76,88,100)
        # state: current thread, next TLS index, registry count; TLS cells start +64.
        env.put(state, thread, 43, 0)
        owner = env.object(4, 'slot owner', words=[0 if cold or newslot else slot])
        if application:
            module = env.object(0x1074, 'live module unit input', fill=0x59)
            owner = module+0x1070
            env.put(owner,0 if cold or newslot else slot)
        env.put(state+20,0 if prelude else 1)
        manager = env.object(0x34, 'warm manager', fill=0)
        table = env.object(32, 'slot records', words=[0xa400,0x11223344,0xa400,0x22334455,
                                                     0xa401,0x33445566,0xa400,0x44556677])
        if grow_slots:
            env.put(table, 0xa401,0x11223344,0xa401,0x22334455,0xa401,0x33445566,0xa401,0x44556677)
        env.put(manager, 17,4,4 if grow_slots else 1,high,table,0,4)
        env.put(manager+0x1c,0xabc001,0xffffffff,0,0,0,0)
        backing = env.object(64, 'existing values with bounded extra backing', fill=0x6d)
        values = backing+4 if negative else backing
        if not empty:
            env.put((values+slot*4)&0xffffffff,value)
        else:
            env.put((values+slot*4)&0xffffffff,0)
        container = env.object(16,'thread container', words=[0x511a64,0x12340000,count,0 if absent else values])
        other = env.object(16,'other thread container', words=[0x511a64,0,count,backing])
        env.put(state+64,thread,17,0 if missing or cold or thread_miss else container)
        env.put(state+76,thread+1,17,other)
        env.put(state+88,thread,18,other)
        env.put(manager+0x14,other)
        if alias == 'manager':
            # In-range store aliases manager high-water field through valid backing.
            env.put(container+0xc,manager)
        elif alias == 'container':
            env.put(container+0xc,container)
        elif alias == 'publication':
            env.put(container+0xc,PUB-4)
        if owner_alias:
            owner=manager+0xc
            env.put(owner,slot)
        if cold:
            env.put(PUB,0)
        else:
            env.put(PUB,manager)

        def register(e,p,n):
            k=e.get(state+8); e.put(state+256+k*12,p,n,0); e.put(state+8,k+1)
        register(env,backing,64)
        # A movable global allocation uses a distinct handle object.
        handle=env.object(12,'initial global handle',words=[table,32,1])
        env.put(state+16,handle)

        if source_function:
            # Fill the complete bounded stack: even untouched bytes remain witnesses.
            env.write(STACK_BASE, bytes((i*37+19)&255 for i in range(STACK_SIZE)))
            if source_alias == 'saved-esi':
                env.put(container+0xc, frame-8); env.put(container+8,4)
            elif source_alias == 'getter-saved-esi':
                env.put(container+0xc,frame-8); env.put(container+8,4)
            elif source_alias == 'getter-saved-edi':
                env.put(container+0xc,frame-12); env.put(container+8,4)
            elif source_alias == 'borrowed-container':
                container=frame-20
                env.put(container,0x511a64,0,17,backing)
                env.put(state+72,container)
            elif source_alias == 'value-argument':
                env.put(container+0xc,frame+4); env.put(container+8,4)
            elif source_alias == 'ordinal-argument':
                env.put(container+0xc,frame); env.put(container+8,4)
            elif source_alias == 'stack-owner':
                owner=frame+16; env.put(owner,slot)
            elif source_alias in ('allocator-ebx','allocator-ebp'):
                table=frame-(32 if source_alias=='allocator-ebx' else 36)
                env.put(table,0xa401,0x11223344,0xa400,0x22334455)
                env.put(manager+4,2,1,high,table)
            # New-container insertion always uses actual offset4; aliases that
            # overwrite prepend's child saved ESI are outside inherited472.

        def observe(e,c,result=0):
            k=e.get(trace); base=trace+4+k*(128 if source_function else 80); e.put(trace,k+1)
            args=list(c.arguments)+[0]*4
            pub=e.get(PUB)
            e.put(base,c.function,c.receiver,c.stack_pointer,len(c.arguments),*args[:4],result,
                  pub,e.get(owner),e.get(manager+0xc),e.get(manager+0x14),
                  e.get(container+8),e.get(container+0xc),e.get(state),e.get(state+64+8))

            if source_function:
                cpu=c.source_context
                e.put(base+68,c.source_return_pc,*[getattr(cpu,n) for n in
                    ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead')])

        def service(addr):
            def effect(e,c):
                a=c.arguments; result=0
                active_failure=failure if e.get(state+20) else None
                if addr==0x546a90:
                    result=0xffffffff if active_failure=='tls' else e.get(state+4)
                    if result!=0xffffffff: e.put(state+4,result+1)
                elif addr==0x546a7c:
                    for off in tls_offsets:
                        if e.get(state+off)==e.get(state) and e.get(state+off+4)==a[0]:
                            result=e.get(state+off+8); break
                elif addr==0x546a84:
                    result=0 if publish_failure else 1
                    if result:
                        off=next((p for p in tls_offsets if e.get(p+state)==0 and e.get(p+state+4)==0),100)
                        for candidate in tls_offsets:
                            if e.get(state+candidate)==e.get(state) and e.get(state+candidate+4)==a[0]:
                                off=candidate;break
                        e.put(state+off,e.get(state),a[0],a[1])
                elif addr==0x546aa4:
                    e.put(a[0],0xabc001,0xffffffff,0,0,0,0)
                elif addr in (0x546aac,0x546a9c):
                    p=a[0]; recursion=e.get(p+8)
                    if addr==0x546aac:
                        e.put(p+4,recursion,recursion+1,e.get(state))
                    else:
                        e.put(p+4,(recursion-2)&0xffffffff,recursion-1,
                              e.get(state) if recursion>1 else 0)
                elif addr==0x546b1c:
                    if active_failure!='global':
                        p=e.object(max(a[1],4096) if in_place else a[1],'global data',fill=0 if a[0]&0x40 else 0xb9)
                        result=e.object(12,'global handle',words=[p,a[1],0]);e.put(state+16,result)
                elif addr==0x546a8c:
                    h=e.get(state+16); result=h if a[0] and e.get(h)==a[0] else 0
                elif addr==0x5469c8:
                    if a[0]:
                        n=e.get(a[0]+8);e.put(a[0]+8,max(0,n-1));result=int(n>1)
                elif addr==0x5469c4:
                    if a[0]:
                        result=e.get(a[0]); e.put(a[0]+8,e.get(a[0]+8)+1)
                elif addr==0x546a88:
                    if active_failure!='global-realloc':
                        h=a[0];p=e.get(h);n=e.get(h+4)
                        q=p if in_place else e.object(a[1],'resized global data',fill=0xb9)
                        if not in_place:
                            e.write(q,e.read(p,min(n,a[1]))); e.release(p)
                        e.put(h,q,a[1],e.get(h+8));result=h
                elif addr==0x546aa8:
                    fail=(active_failure=='container' and a[0]==0x40 and a[1]==16) or (active_failure=='array' and a[0]==0) or (active_failure=='application' and a==(0x40,0x84))
                    if not fail:
                        result=e.object(max(512,a[1]) if in_place else max(1,a[1]),'local block',fill=0 if a[0]&0x40 else 0xd7)
                        register(e,result,max(1,a[1]))
                elif addr==0x546a80:
                    if active_failure!='realloc':
                        n=0
                        for k in range(e.get(state+8)):
                            if e.get(state+256+k*12)==a[0]: n=e.get(state+260+k*12)
                        result=a[0] if in_place else e.object(max(1,a[1]),'resized local block',fill=0xe3)
                        if not in_place:
                            e.write(result,e.read(a[0],min(n,a[1])));e.release(a[0])
                        register(e,result,max(1,a[1]))
                observe(e,c,result)
                if addr==0x546958:
                    # Preserve original exception metadata before noncontinuable Halt.
                    e.write(trace+8000,e.read(a[3],12)); return halt()(e,c)
                return result
            return effect
        for addr in IMPORTS: env.override(addr,service(addr))

        def factory(e,c):
            observe(e,c,value)
            if factory_change:
                e.put(owner,2)
                e.put(PUB,manager)
                e.put(state,thread+1)
            return value
        callback=factory_pc if source_function or application else env.stub('user supplied TLS factory','cdecl',0,factory)
        tokens=dict(owner=owner,manager=manager,callback=callback,state=state,trace=trace)
        if source_function:
            regs=dict(eax=0x19387264,ebx=0x22222220,ecx=owner if source_function==GET else manager,
                      edx=0x44556677,esi=0x13579bdf,edi=0x2468ace0,ebp=0x66666660,
                      esp=frame,eip=source_function,eflags=0x847,fsHead=0xffffffff)
            if source_alias == 'borrowed-container': regs['edi']=backing
            regs.update(registers or {})
            if nested_fs:
                fs=frame+0x100
                env.put(fs,0xffffffff,0x508511,0xffffffff)
                regs['fsHead']=fs
            env.put(frame-4,regs['esi']); env.put(frame-8,regs['edi'])
            tokens['source']=NativeSourceContext(72,1,0x7ff,0x7ff,
                *[regs[n] for n in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead')],
                0x400 if source_function==GET else 0x442,0,0)
        if prelude:
            # The final case begins in state produced by real original roots.
            # No native output, manufactured constructor record or TLS cache is used.
            def original_prefix(prefix_owner, target, return_pc):
                context=NativeSourceContext.from_buffer_copy(tokens['source'])
                context.ecx=prefix_owner
                env._freeze()
                side=env.run_original_context(GET,context,check_objects=True,
                    source_return_pc=return_pc,source_convention='thiscall',
                    receiver=prefix_owner,arguments=(target,))
                if side.errors or not side.completed:
                    raise RuntimeError('original prelude failed: '+str(side.errors))
                stack=env.read(STACK_BASE,STACK_SIZE)
                env.backend,env.side='initial','setup'
                env.write(HEAP_BASE,side.heap)
                env.write(env.program.data_start,side.image)
                env.write(STACK_BASE,stack)
                return side.eax
            if prelude=='thread':
                thread_owner=env.object(4,'earlier genuine thread consumer slot',words=[0])
                original_prefix(thread_owner,0x502335,0x50229e)
            elif prelude in ('warm','second-thread','unpublished'):
                original_prefix(owner,0x502301,0x5025cf)
                if prelude=='second-thread': env.put(state,thread+1)
            elif prelude=='growth':
                for index in range(31):
                    prefix_module=env.object(0x1074,'prior live module unit input',fill=0x59)
                    prefix_owner=prefix_module+0x1070;env.put(prefix_owner,0)
                    original_prefix(prefix_owner,0x502301,0x5025cf)
            env.put(state+20,1)
        return tokens
    return setup


def cases(random_source):
    get_profiles=[('cold original constructor',dict(cold=True,missing=True)),
        ('warm value hit',{}),('TLS miss',dict(missing=True)),
        ('second thread has independent index cell',dict(thread_miss=True,thread=11)),
        ('getter owner aliases manager high-water',dict(owner_alias=True,empty=True)),
        ('zero cached value',dict(empty=True)),('short logical array',dict(count=1)),
        ('null factory result',dict(empty=True,value=0)),
        ('new free slot preserves flags',dict(newslot=True)),
        ('new slot original global growth',dict(newslot=True,grow_slots=True)),
        ('factory republishes manager owner and switches physical thread',dict(missing=True,factory_change=True)),
        ('signed negative count selects factory',dict(count=0xffffffff,empty=True,value=0)),
        ('cold TLS allocation throws',dict(cold=True,failure='tls')),
        ('cold global allocation throws',dict(cold=True,failure='global'))]
    for label,opts in get_profiles:
        yield Case(label,GET,profile(**opts),receiver=lambda t:t['owner'],arguments=(lambda t:t['callback'],),
                   expect='halt' if opts.get('failure') else 'return')
    set_profiles=[('inline existing value',dict(count=4)),
        ('new container inserted',dict(missing=True)),('missing TLS zero still allocates',dict(missing=True,value=0)),
        ('existing array grows',dict(count=1)),('array absent allocates',dict(count=0,absent=True)),
        ('bounded zero out of logical range',dict(count=1,value=0)),
        ('TLS publication failure ignored',dict(missing=True,publish_failure=True)),
        ('container allocation throws',dict(missing=True,failure='container')),
        ('new value allocation throws after list insert',dict(missing=True,failure='array')),
        ('reallocation failure preserves old block',dict(count=1,failure='realloc')),
        ('store aliases manager',dict(alias='manager',slot=3)),
        ('store aliases container',dict(alias='container',slot=1)),
        ('store aliases global manager publication',dict(alias='publication',slot=1)),
        ('signed negative ordinal physically backed',dict(negative=True,slot=0xffffffff))]
    for label,opts in set_profiles:
        yield Case(label,SET,profile(**opts),receiver=lambda t:t['manager'],
                   arguments=(opts.get('slot',1),opts.get('value',0x789abcde)),
                   expect='halt' if opts.get('failure') else 'return')
    for i in range(16):
        ordinal=random_source.randrange(1,6); count=random_source.randrange(1,7)
        value=random_source.randrange(1,0x100000000)
        yield Case(f'random direct write {i}',SET,profile(slot=ordinal,count=count,high=8,value=value),
                   receiver=lambda t:t['manager'],arguments=(ordinal,value))

    source_gets = [
        ('cold thread factory',dict(cold=True,missing=True)),
        ('cold module factory',dict(cold=True,missing=True,factory_pc=0x502369)),
        ('warm cached hit',{}), ('stack backed owner',dict(source_alias='stack-owner')), ('warm repeated value with different physical thread',dict(thread=19)),
        ('TLS miss thread factory',dict(missing=True)),
        ('zero cell module factory',dict(empty=True,factory_pc=0x502369)),
        ('count boundary factory',dict(count=1)),
        ('second physical thread miss',dict(thread_miss=True,thread=23)),
        ('free slot',dict(newslot=True)), ('moving global grow',dict(newslot=True,grow_slots=True)),
        ('owner aliases high water',dict(owner_alias=True,empty=True)),
        ('signed negative ordinal hit',dict(negative=True,slot=0xffffffff,count=0)),
        ('TLS exhaustion',dict(cold=True,failure='tls')),
        ('global allocation failure',dict(cold=True,failure='global')),
        ('global moving allocation failure',dict(newslot=True,grow_slots=True,failure='global-realloc')),
        ('container failure',dict(missing=True,failure='container')),
        ('array failure after published list',dict(missing=True,failure='array')),
        ('moving array failure',dict(count=1,failure='realloc')),
        ('TLS publication failure',dict(missing=True,publish_failure=True)),
        ('saved ESI store',dict(source_alias='getter-saved-esi',registers={'esi':0})),
        ('saved EDI store',dict(source_alias='getter-saved-edi',registers={'edi':0})),
        ('slot allocator saved EBX',dict(newslot=True,source_alias='allocator-ebx')),
        ('slot allocator saved EBP',dict(newslot=True,source_alias='allocator-ebp'))]
    source_sets = [
        ('in range',{}), ('new container',dict(missing=True)),
        ('missing zero',dict(missing=True,value=0)), ('moving growth',dict(count=1)),
        ('fresh array',dict(count=0,absent=True)), ('backed zero beyond count',dict(count=1,value=0)),
        ('TLS publish FALSE',dict(missing=True,publish_failure=True)),
        ('container failure',dict(missing=True,failure='container')),
        ('array failure',dict(missing=True,failure='array')),
        ('moving failure retains old allocation',dict(count=1,failure='realloc')),
        ('manager alias',dict(alias='manager',slot=3)),
        ('container alias',dict(alias='container')), ('global alias',dict(alias='publication')),
        ('negative ordinal backed',dict(negative=True,slot=0xffffffff)),
        ('saved ESI alias',dict(source_alias='saved-esi')),
        ('borrowed stack container changes restored EDI',dict(source_alias='borrowed-container',slot=17,high=32)),
        ('store aliases value argument',dict(source_alias='value-argument')),
        ('store aliases ordinal argument',dict(source_alias='ordinal-argument'))]
    for function, profiles in ((GET,source_gets),(SET,source_sets)):
        for i,(label,opts) in enumerate(profiles):
            yield Case('source '+label,function,
                profile(**opts,source_function=function,frame=STACK_TOP-0x1000*(i%3)),
                receiver=lambda t,f=function:t['owner' if f==GET else 'manager'],
                arguments=(lambda t:t['callback'],) if function==GET else
                          (opts.get('slot',1),opts.get('value',0x789abcde)),
                source_context=lambda t:t['source'],
                source_return_pc=0x50229e if function==GET else 0x5033ce,
                expect='halt' if opts.get('failure') else 'return')
    for i in range(24):
        ordinal=random_source.randrange(1,6); count=random_source.randrange(1,7)
        value=random_source.randrange(1,0x100000000)
        regs={n:random_source.randrange(0,0x100000000) for n in ('eax','ebx','edx','esi','edi','ebp')}
        yield Case(f'source randomized full CPU {i}',SET,
            profile(source_function=SET,slot=ordinal,count=count,high=8,value=value,registers=regs,
                    frame=STACK_TOP-0x2000-64*i),receiver=lambda t:t['manager'],
            arguments=(ordinal,value),source_context=lambda t:t['source'],source_return_pc=0x5033ce)

    app_profiles=[
        ('cold terminal FS',dict(cold=True,missing=True)),
        ('cold nested FS',dict(cold=True,missing=True,nested_fs=True)),
        ('same owner warm original value',dict(cold=True,missing=True,prelude='warm')),
        ('second physical thread same original slot',dict(cold=True,missing=True,prelude='second-thread')),
        ('shared manager after real thread callback',dict(cold=True,missing=True,prelude='thread')),
        ('real 32-entry table crossing moving',dict(cold=True,missing=True,prelude='growth')),
        ('real 32-entry table crossing in place',dict(cold=True,missing=True,prelude='growth',in_place=True)),
        ('application allocation fails',dict(cold=True,missing=True,failure='application')),
        ('later container allocation fails',dict(cold=True,missing=True,failure='container')),
        ('later pointer array allocation fails',dict(cold=True,missing=True,failure='array')),
        ('pointer array resize fails after thread',dict(cold=True,missing=True,prelude='thread',failure='realloc')),
        ('slot table allocation fails',dict(cold=True,missing=True,failure='global')),
        ('slot table resize fails',dict(cold=True,missing=True,prelude='growth',failure='global-realloc')),
        ('TLS index exhausted',dict(cold=True,missing=True,failure='tls')),
        ('TlsSetValue FALSE still returns record',dict(cold=True,missing=True,publish_failure=True)),
        ('unpublished record followed by original retry',dict(cold=True,missing=True,publish_failure=True,prelude='unpublished')),
        ('warm zero cell application callback',dict(empty=True)),
        ('warm count boundary application callback',dict(count=1)),
    ]
    for i,(label,opts) in enumerate(app_profiles):
        regs={n:random_source.randrange(0,0x100000000) for n in ('eax','ebx','edx','esi','edi','ebp')}
        yield Case('source application '+label,GET,
            profile(**opts,application=True,source_function=GET,factory_pc=0x502301,
                frame=STACK_TOP-0x3000-64*i,registers=regs),
            receiver=lambda t:t['owner'],arguments=(0x502301,),
            source_context=lambda t:t['source'],source_return_pc=0x5025cf,
            expect='halt' if opts.get('failure') else 'return')

    for label,opts in (
        ('cold actual application callback',dict(cold=True,missing=True)),
        ('warm application slot miss',dict(empty=True)),
        ('application checked failure',dict(cold=True,missing=True,failure='application')),
        ('application TLS publication FALSE',dict(cold=True,missing=True,publish_failure=True))):
        yield Case('ordinary '+label,GET,profile(**opts,application=True,factory_pc=0x502301),
            receiver=lambda t:t['owner'],arguments=(0x502301,),
            expect='halt' if opts.get('failure') else 'return')
