"""Original-driven cannon object cases."""
from clawparity.cases import Case


def obj(env, *args, **kw):
    kw.setdefault('fill', 0)
    return env.object(*args, **kw)


def name_map(env, entries):
    table = obj(env,0x30, 'resource-map')
    bucket = obj(env,4, 'bucket')
    head = 0
    for name, value in entries:
        text = obj(env,len(name)+1, name, data=name.encode()+b'\0')
        node = obj(env,16, 'hash-node', words=[head, 0, text, value])
        head = node
    env.put(bucket, head)
    env.put(table+0x14, bucket, 1)
    return table


def animation(env, value):
    frame = obj(env,0x30, 'animation-frame')
    env.put(frame+0x1c, value)
    frames = obj(env,4, 'frames', words=[frame])
    anim = obj(env,0x14, 'animation')
    env.put(anim+0xc, frames, 1)
    return anim


def base(env, seed=13):
    r=obj(env,0x7c,'cannon',fill=0x39)
    o=obj(env,0x1b4,'object')
    p=obj(env,0x1b4,'sprite')
    s=obj(env,0x24,'state')
    env.put(r+0xc,o,s)
    env.put(r+0x2c,p)
    env.put(r+0x38,seed)
    env.put(r+0x40,0x80000000)
    env.put(r+0x48,*[animation(env, x) for x in (31,43,59)])
    env.put(r+0x54,0,7,seed+1,0xfffffff1,seed+5,0x80000000)
    env.put(r+0x70,0,123,456)
    env.put(s+0x1c,seed*19)
    env.put(o+0x148,seed,0xfffffff9)
    env.put(p+0x40,0xf3456701)
    env.put(p+0x4c,0x7ffffffa,0x80000003)
    env.put(p+0x64,seed+4)
    env.put(p+0x190,0)
    env.put(p+0x19c,0)
    env.put(p+0x1a4,0)
    env.put(p+0x1b0,0x3f800000)
    for i,a in enumerate((0x118,0x128,0x138)):
        env.put(p+a,seed+i+1)
        env.put(p+a+8,0x80000000 if i==1 else seed*11+i)
    env.put(0x537680,0)
    env.put(0x5430c4,17)
    env.put(0x537210,500)
    env.put(0x532c0c,1)
    return dict(r=r,o=o,p=p,s=s)


def constructor(env, seed=13, present=True):
    t=base(env,seed);p=t['p']
    root=obj(env,0x30,'resources')
    image=obj(env,0x6c,'image')
    image_words=obj(env,4,'image-words',words=[seed+47])
    env.put(image+0x14,image_words)
    env.put(image+0x64,0,0)
    env.put(root+0x10,name_map(env,[('LEVEL_CANNON',image)] if present else []))
    env.put(root+0x14,name_map(env,[]))
    env.put(root+0x2c,name_map(env,[(n,animation(env,v)) for n,v in [('LEVEL_CANNON_HOME',71),('LEVEL_CANNON_FIRING',83)]] if present else []))
    env.put(p+0xc,root)
    env.put(p+0x6c,t['s'])
    env.put(p+0x40,seed&2)
    env.put(p+0x70,0)
    env.put(p+0x78,0)
    t['root']=root
    return t


def table(env,address,lo,hi,callback,stride=4):
    rows=obj(env,(hi-lo+1)*stride,'dispatch-rows')
    for i in range(hi-lo+1):env.put(rows+i*stride,callback)
    fallback=obj(env,stride,'fallback',words=[callback])
    env.put(address+8,lo,hi,rows,fallback,stride,0,0x87654321)
    return rows


def recorder(env,t,label,argc=0):
    record=obj(env,24,'observations-'+label)
    def effect(env,call):
        env.put(record,call.receiver,len(call.arguments),*call.arguments)
        env.put(record+16,env.get(t['s']+0x1c),env.get(t['r']+0x58))
        return 0x73
    return env.stub(label,'thiscall',argc,effect)


def firing(env,seed=13,velocity=-3,mask=0,flags=0,audio=0,repoint=False):
    t=base(env,seed);r,o,p=t['r'],t['o'],t['p']
    env.put(r+0x58,0)
    env.put(o+0x148,velocity,0x80000000)
    anim=animation(env,1)
    env.put(p+0x18c,p,anim)
    env.put(p+0x19c,100,1,1,1,1,0x3f800000)
    manager=obj(env,0x30,'creation-manager')
    bridge=obj(env,12,'manager-bridge');m=obj(env,16,'manager')
    env.put(r+0x30,m);env.put(m+0xc,bridge);env.put(bridge+8,manager)
    root=obj(env,0x30,'ball-resources');env.put(manager+0xc,root)
    template=obj(env,0x14,'ball-template')
    runtime=obj(env,0x144,'ball-runtime',fill=0x53)
    sprite=obj(env,0x144,'ball-flip-sprite',fill=0x27)
    env.put(runtime+0x12c,sprite)
    env.put(runtime+0x138,seed+17);env.put(runtime+0x140,0x80000000)
    env.put(sprite+0x40,0xa1b2c300|flags)
    for i,a in enumerate((0x118,0x128,0x138)):
        env.put(sprite+a,0x80000000 if mask&(1<<i) else seed+5+i)
        env.put(sprite+a+8,0x80000000 if i==2 else seed+23+i)
    record=obj(env,32,'ball-callback-record')
    alternate=obj(env,0x1c,'alternate-control') if repoint else 0
    def setup_ball(env,call):
        ball=call.arguments[0];control=env.get(ball+0x6c)
        env.put(record,ball,control,env.get(r+0x58),env.get(p+0x4c),env.get(p+0x50))
        if repoint:
            env.put(ball+0x6c,alternate);control=alternate
            env.put(o+0x148,0xffffffed,0x7fffffff)
        env.put(control+0x18,runtime)
        return 0x29
    callback=env.stub('ball-setup','cdecl',1,setup_ball)
    env.put(template+0x10,callback)
    env.put(root+0x14,name_map(env,[('CannonBall',template)]))
    node=obj(env,12,'free-list-node')
    env.put(manager+0x20,node)
    if audio:
        owner=obj(env,0x14,'sound-owner');inner=obj(env,0x14,'sound-inner');device=obj(env,0x7c,'silent-audio')
        env.put(owner+0x10,inner);env.put(inner+0x10,device);env.put(device+0x78,0)
        env.put(r+0x54,owner);env.put(0x532c0c,audio-1)
    return t


def cases(random_source):
    for f in (0x4145b0,0x414660,0x414860,0x414640):
        for mode in (0,1,0x80000000):
            for nonnull in (False,True):
                def setup(env,mode=mode,nonnull=nonnull):
                    t=base(env,random_source.randrange(1,10000));env.put(t['r']+0x70,mode)
                    if not nonnull:env.put(t['r']+0x48,0,0,0)
                    return t
                yield Case(f'setup {f:x} {mode} {nonnull}',f,setup,receiver=lambda t:t['r'])
    for now,then,timeout in ((500,123,456),(500,123,377),(500,123,376),(0,0,0),(3,0xfffffffe,5),(0,1,0xffffffff)):
        for mode in (0,1):
            def setup(env,now=now,then=then,timeout=timeout,mode=mode):
                t=base(env);env.put(t['r']+0x70,mode,then,timeout);env.put(0x537210,now);return t
            yield Case(f'timer {now} {then} {timeout} {mode}',0x4145f0,setup,receiver=lambda t:t['r'])
    for f in (0x4146b0,0x4148b0):
        for velocity in (-1,0,1,0x80000000,0x7fffffff):
            for mask in (0,1,2,4,7):
                def setup(env,velocity=velocity,mask=mask):return firing(env,random_source.randrange(1,10000),velocity,mask)
                yield Case(f'fire {f:x} {velocity} {mask}',f,setup,receiver=lambda t:t['r'])
        for variant in range(9):
            def setup(env,variant=variant):
                t=firing(env,flags=2 if variant==0 else 0,audio=variant if variant in (1,2) else 0,repoint=variant==3)
                if variant==4:env.put(t['r']+0x58,0xffffffff)
                if variant==5:env.put(t['p']+0x1ac,2)
                if variant==6:env.put(t['p']+0x1a4,1);env.put(t['p']+0x19c,0)
                if variant==7:env.put(t['p']+0x190,0)
                if variant==8:env.put(t['p']+0x1a4,1)
                return t
            yield Case(f'fire variant {f:x} {variant}',f,setup,receiver=lambda t:t['r'])
    for velocity in (-1,0,1,0x80000000,0x7fffffff):
        for mask in range(8):
            for flipped in (False,True):
                def setup(env,velocity=velocity,mask=mask,flipped=flipped):
                    t=base(env,random_source.randrange(1,10000));env.put(t['o']+0x148,velocity);env.put(t['p']+0x40,0xa3b4c501|(2 if flipped else 0))
                    for i,a in enumerate((0x118,0x128,0x138)):
                        if mask&(1<<i):env.put(t['p']+a,0x80000000)
                    return t
                yield Case(f'flip {velocity} {mask} {flipped}',0x414a60,setup,receiver=lambda t:t['r'])
    for present in (False,True):
        for seed in (1,2,17,0x7fffffff):
            yield Case(f'construct {present} {seed}',0x449480,lambda env,seed=seed,present=present:constructor(env,seed,present),receiver=lambda t:t['r'],arguments=(lambda t:t['p'],))
    for selector in (0,29,30,1000,1,28,31,0xffffffff):
        def setup(env,selector=selector):
            t=constructor(env);env.put(t['s']+0x1c,selector);env.put(t['s']+0x18,t['r'])
            vt=obj(env,0x24,'child-vtable');env.put(t['r'],vt)
            for off in (0x10,0x1c,0x20):env.put(vt+off,recorder(env,t,f'child-{off:x}'))
            for off in (4,8,12):env.put(vt+off,recorder(env,t,f'generic-{off:x}',1))
            string=obj(env,16,'cow-string',words=[1,0,0,0])
            row=table(env,0x537698,selector,selector,0)
            env.put(row,string+12)
            return t
        yield Case(f'object dispatch {selector}',0x4493c0,setup,arguments=(lambda t:t['p'],))
    for selector in (-4,-1,0,1,3,4):
        for empty in (False,True):
            def setup(env,selector=selector,empty=empty):
                t=base(env);callback=recorder(env,t,'dispatch')
                table(env,0x537818,-1,3,0 if empty else callback,8)
                table(env,0x534bf8,-4,4,callback,12)
                return t
            yield Case(f'dispatch table {selector} {empty}',0x449590,setup,receiver=lambda t:t['r'],arguments=(selector,))
    def second_growth(env):
        t=base(env);cb=recorder(env,t,'second-growth')
        rows=obj(env,4,'zero-stride-rows',words=[cb]);fallback=obj(env,4,'fallback',words=[cb])
        env.put(0x537820,1,-1,rows,fallback,0,0,19)
        def reallocate(env,call):
            return obj(env,4,'resized-zero-stride',words=[cb])
        env.override(0x4a9070,reallocate)
        return t
    yield Case('inverted bounds second growth',0x449590,second_growth,receiver=lambda t:t['r'],arguments=(0,))
