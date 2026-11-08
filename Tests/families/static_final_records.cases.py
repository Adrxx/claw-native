"""Original-derived final-record inputs; physical policy is per-case, process-local.

GUI handles occupy disjoint typed namespaces. DC zero supports caps/release with
zero results. Brushes/cursors are borrowed; release failure retains DC ownership.
Every physical observation is retained in live memory, including stop prefixes.
"""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt

# Finite owned-source import frontier; descendant imports retain their original
# graph and are recorded in the same history. Invalid owned calls stop honestly.
FRONTIER = {
 0x546a94:{0x502df4:(0,)},
 0x546c44:{0x4fb3c9:(11,),0x4fb3d0:(12,),0x502d6e:(2,),
            0x502d78:(3,),0x502d95:(2,),0x502d9e:(3,)},
 0x546c7c:{0x4fb3ed:(0,)},
 0x546894:{0x4fb3fa:88,0x4fb402:90},
 0x546c80:{0x4fb40e:None},
 0x546d20:{0x4fb384:(15,),0x4fb38b:(16,),0x4fb392:(20,),
            0x4fb399:(18,),0x4fb3a0:(6,)},
 0x546b64:{0x4fb3ad:(15,),0x4fb3b4:(6,)},
 0x546b60:{0x502e1e:(0,32514),0x502e29:(0,32512)},
 0x546c2c:{0x4ffd50:(0x5122d0,)},
}
GUI = (0x502dac, 0x4fb3ba, 0x4fb376)
ROOTS = (0x502d5a, 0x502d8a, 0x4ffce9, 0x4ffd0c,
         0x4db610, 0x4dbb80, 0x4dc170, 0x4dc270, 0x4dc390, 0x4dc3a0)
SLOTS = (0x546a90,0x546a7c,0x546a84,0x546aa4,0x546aac,0x546a9c,
         0x546b1c,0x546a8c,0x5469c8,0x546a88,0x5469c4,0x546aa8,
         0x546a80,0x546958,0x546abc,0x546a94,0x546c44,0x546c7c,
         0x546894,0x546c80,0x546d20,0x546b64,0x546b60,0x546c2c)


def setup_for(root, seed, versions=(10,), process=0x40000, alias=False,
              modern=1, enabled=1, zero=None, stop=None, after=False,
              reread=None, registration=None, arg=0):
    def setup(env):
        receiver = 0x540878 if alias else env.object(0x80, 'receiver', fill=0xA7)
        # Poison all destinations and their neighbors before source execution.
        for base, size in ((0x540878,0x70),(0x540b40,0x20),
                           (0x544b18,24),(0x544b50,24),
                           (0x544b68,24),(0x544b80,24)):
            env.write(base, bytes(((seed + i*37) & 255) for i in range(size)))
        env.put(receiver+0x68, modern)
        env.put(0x5408d4, enabled)
        history = env.object(8192, 'physical history', fill=0)
        state = env.object(64, 'physical ownership and registry', fill=0)
        handles = env.object(1024, 'movable handle table', fill=0)
        # manager must be source-created in cold cases; warm cases are explicit
        # already-existing owner inputs with a valid TLS container.
        container = env.object(16, 'thread container', fill=0)
        slots = env.object(64, 'thread slots', fill=0)
        thread = env.object(16, 'thread value', fill=0)
        module = env.object(0x80, 'current module', fill=0)
        manager = env.object(128, 'TLS manager', fill=0)
        env.put(container+8, 16, slots)
        env.put(slots+4, thread)
        env.put(thread+4, module)
        env.put(module+0x1c, 0x12345678, 20)
        env.put(0x53ec9c, 0 if registration == 'cold' else 1)
        env.put(0x540af0, manager if registration != 'cold' else 0)
        env.put(0x5408e8, 1)
        env.put(0x540a88, 0)
        env.put(0x540aa8, 0 if registration == 'lazy' else 1)
        env.put(state+16, container if registration != 'cold' else 0)
        # TLS index zero for the already-existing manager; source owns its fields.
        env.put(manager, 0)
        env.put(manager+0x1c,0xabcdef01,0,0,0,0,0)
        env.put(0x5408f0,0xabcdef01,0,0,0,0,0)
        env.put(0x540a90,0xabcdef01,0,0,0,0,0)
        metrics = {2: 0xffffffff if seed & 1 else 0, 3: 0x80000000,
                   11: seed, 12: (seed ^ 0x89abcdef)}
        color = {s: ((seed*0x10203) ^ (s*0x1020304)) & 0xffffffff
                 for s in (15,16,20,18,6)}

        def physical(slot):
            def effect(e, call):
                n=e.get(history)
                e.put(history, n+1)
                p=history+4+n*40
                e.put(p,slot,call.source_return_pc,call.receiver,len(call.arguments),
                      *(list(call.arguments)+[0]*4)[:4])
                if stop == slot and not after:
                    raise Halt()
                args=call.arguments
                if slot == 0x546abc and call.source_return_pc not in (0x502db7,0x4ffd16,0x4ffd21,0x4ffd31,0x4ffd37,0x502e60): raise Halt()
                if slot in FRONTIER:
                    sites=FRONTIER[slot]
                    if call.source_return_pc not in sites: raise Halt()
                    wanted=sites[call.source_return_pc]
                    if slot==0x546894:
                        if tuple(args)!=(e.get(state),wanted): raise Halt()
                    elif slot==0x546c80:
                        if tuple(args)!=(0,e.get(state)): raise Halt()
                    elif tuple(args)!=wanted: raise Halt()
                result=0
                if slot == 0x546abc:
                    k=e.calls_so_far(call.function)-1
                    result=versions[min(k,len(versions)-1)]
                elif slot == 0x546a94: result=process
                elif slot == 0x546c44: result=metrics[args[0]]
                elif slot == 0x546c7c:
                    result=0 if zero == 'dc' else 0x71000001
                    e.put(state,result)
                elif slot == 0x546894:
                    result=0 if zero in ('dc','caps') else {88:97,90:143}[args[1]]
                elif slot == 0x546c80:
                    result=0 if zero in ('dc','release') else 1
                    if result: e.put(state,0)
                elif slot == 0x546d20: result=0 if zero=='color' else color[args[0]]
                elif slot == 0x546b64:
                    result=0 if zero=='brush' else {15:0x7200000f,6:0x72000006}[args[0]]
                elif slot == 0x546b60:
                    result=0 if zero=='cursor' else {32514:0x73007f02,32512:0x73007f00}[args[1]]
                    if reread is not None: e.put(receiver+0x5c,reread)
                elif slot == 0x546c2c:
                    # Exact-byte name is recorded instead of trusting its pointer.
                    name=e.cstr(args[0])
                    raw=name.encode() if isinstance(name,str) else name
                    e.write(state+32,raw[:24])
                    result=0 if zero=='message' else 0xc109
                    e.put(state+4,result)
                elif slot == 0x546a7c: result=e.get(state+16)
                elif slot == 0x546a90: result=0xffffffff if zero=='tls' else 0
                elif slot == 0x546a84:
                    result=0 if zero=='tls-set' else 1
                    if result: e.put(state+16,args[1])
                elif slot == 0x546aa4:
                    e.put(args[0],0xabcdef01,0,0,0,0,0)
                elif slot == 0x546aac: e.put(state+8,e.get(state+8)+1)
                elif slot == 0x546a9c: e.put(state+8,(e.get(state+8)-1)&0xffffffff)
                elif slot == 0x546958: raise Halt()
                elif slot == 0x546b1c:
                    if zero != 'allocation':
                        count=e.get(handles)
                        data=e.object(max(1,args[1]),'global data',fill=0xb9)
                        result=0x74000001+count
                        e.put(handles+4+count*16,result,data,args[1],1)
                        e.put(handles,count+1)
                elif slot == 0x546a8c:
                    if args[0]:
                        for i in range(e.get(handles)):
                            q=handles+4+i*16
                            if e.get(q+4)==args[0]: result=e.get(q)
                elif slot in (0x5469c4,0x5469c8):
                    if args[0]:
                        for i in range(e.get(handles)):
                            q=handles+4+i*16
                            if e.get(q)==args[0]:
                                if slot==0x5469c4:
                                    result=e.get(q+4); e.put(q+12,e.get(q+12)+1)
                                else: e.put(q+12,max(0,e.get(q+12)-1))
                elif slot == 0x546aa8:
                    result=0 if zero=='allocation' else e.object(max(1,args[1]),'local allocation',fill=0 if args[0]&0x40 else 0xb9)
                elif slot == 0x546a80:
                    if zero != 'allocation':
                        result=e.object(max(1,args[1]),'local resized',fill=0)
                        # Original local blocks in this bounded path are objects.
                        e.write(result,e.read(args[0],min(e.spans[args[0]],args[1])))
                        e.release(args[0])
                else:
                    # Cold memory APIs are genuine bounded frontiers until their
                    # movable-handle ownership can be supplied coherently.
                    raise Halt()
                e.put(p+32,result)
                if stop == slot and after: raise Halt()
                return result
            return effect
        for slot in SLOTS: env.override(slot,physical(slot))
        sp=0x02007000
        pc=0x503827
        env.put(sp,pc,arg)
        source=NativeSourceContext()
        source.size=72; source.version=1
        source.inputMask=source.outputMask=0x7ff
        for i,key in enumerate(('eax','ebx','ecx','edx','esi','edi','ebp')):
            setattr(source,key,(seed ^ (0x19283746*(i+1))) & 0xffffffff)
        if root in GUI or root==0x4dc3a0: source.ecx=receiver
        source.esp=sp; source.eip=root; source.eflags=2 | (seed & 0x8d5)
        source.fsHead=0xffffffff
        return {'receiver':receiver,'source':source}
    return setup


def case(root,label,seed=0x12345678,**opts):
    expected=opts.pop('expect','return')
    arg=opts.get('arg',0)
    return Case(label,root,setup_for(root,seed,**opts),
                receiver=(lambda t:t['receiver']) if root in GUI or root==0x4dc3a0 else 0,
                arguments=(arg,) if root==0x4dc3a0 else (),
                source_context=lambda t:t['source'], source_return_pc=0x503827,
                expect=expected)


def cases(random_source):
    for root in ROOTS:
        for seed in (0,0xffffffff,random_source.getrandbits(32)):
            yield case(root,f'{root:x} arbitrary CPU {seed:x}',seed,arg=seed)
    for version in (0,3,4,0x80000003,0x80000004,0x1234ff,0xffffffff):
        for process in (0,0x3ffff,0x40000,0xffffffff):
            for alias in (False,True):
                yield case(0x502dac,f'ctor v{version:x} p{process:x} alias{alias}',
                           random_source.getrandbits(32),versions=(version,),process=process,alias=alias)
    for root in (0x4fb3ba,0x502d5a,0x502d8a,0x4fb376):
        for modern in (0,1,0xffffffff):
            for enabled in (0,1):
                yield case(root,f'{root:x} mode{modern} fixed{enabled}',modern=modern,enabled=enabled)
    for value in (0,1,0xffffffff):
        yield case(0x502dac,f'physical callback reread {value}',reread=value)
    for zero in ('dc','caps','release','color','brush','cursor'):
        yield case(0x502dac,'physical zero '+zero,zero=zero)
    for versions in ((0x80000004,), (3,), (10,), (0x80000000,),
                     (0x80000001,0x12340004), (0x80000004,0x80000003,3,0x10003),
                     (0x80000004,5,0x80000000), (0,0x80000000),
                     (0,0,0xffff0003), (0,0,0x10004),
                     (0x80000000,0x10004), (0x80000000,0xffff,0,0xffff)):
        for zero in (None,'message'):
            yield case(0x4ffd0c,f'wheel script {versions} {zero}',versions=versions,zero=zero)
    for slot in (0x546a94,0x546c7c,0x546c80,0x546b64,0x546b60):
        for after in (False,True):
            yield case(0x502dac,f'physical stop {slot:x} after{after}',stop=slot,after=after,expect='halt')
    for mode in ('warm','lazy'):
        yield case(0x503818,'class '+mode,registration=mode)
    yield case(0x503818,'cold TLS exhaustion',registration='cold',zero='tls',expect='halt')
    yield case(0x503818,'cold allocation failure',registration='cold',zero='allocation',expect='halt')
    yield case(0x503818,'cold allocation stop',registration='cold',stop=0x546b1c,expect='halt')

    yield case(0x503818,'cold complete source graph',registration='cold')
    yield case(0x503818,'cold TLS publish failure',registration='cold',zero='tls-set')
