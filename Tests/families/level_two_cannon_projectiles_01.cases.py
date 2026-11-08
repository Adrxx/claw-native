"""Cannon constructors and callback dispatch, from original code."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_TOP


def backed(e,*args,**kwargs):
    kwargs.setdefault('fill',0)
    return e.object(*args,**kwargs)


def dictionary(e, entries, name):
    root=backed(e,40,name); buckets=backed(e,4,name+' buckets')
    e.put(root+0x14,buckets,1)
    previous=0
    for key,value in entries:
        text=backed(e,len(key)+1,key,data=key.encode()+b'\0')
        previous=backed(e,16,name+' node',words=[previous,0x98765432,text,value])
    e.put(buckets,previous)
    return root


def record(e,log,tag,actor,state,argc=0,convention='thiscall'):
    def effect(e,call):
        n=e.get(log); at=log+4+n*40
        e.put(at,tag,call.receiver,e.get(state+0x1c),e.get(state+0x18),e.get(actor),
              e.get(actor+0x40),e.get(actor+0x44),len(call.arguments),
              *(list(call.arguments)+[0,0])[:2])
        e.put(log,n+1)
        return 0x12340000+tag
    return e.stub('callback '+str(tag),convention,argc,effect)


def world(e,values,resources,mutate=False):
    actor=backed(e,0x180,'runtime',fill=0x6d); obj=backed(e,0x200,'object')
    state=backed(e,0x110,'state'); context=backed(e,0x40,'context')
    collision=backed(e,0x100,'collision'); grid=backed(e,0xa0,'grid')
    tiles=backed(e,4,'empty tile',words=[0xffffffff]); rows=backed(e,4,'rows')
    e.put(grid+0x20,tiles,rows);e.put(grid+0x30,4096,4096);e.put(grid+0x8c,12,12)
    e.put(collision+0x5c,grid,0,4096,4096); e.put(context+0x24,collision)
    e.put(obj+0xc,context);e.put(obj+0x6c,state)
    for offset,value in values.items():e.put(obj+offset,value)
    log=backed(e,1024,'observations');methods=backed(e,0x30,'methods')
    for slot,argc in ((4,1),(8,1),(12,1),(16,0),(28,0),(32,0),(36,2)):
        e.put(methods+slot,record(e,log,slot,actor,state,argc))
    e.put(actor,methods);e.put(actor+0x10,state);e.put(state+0x18,actor)
    def sequence(name, index):
        seq=backed(e,0x30,name)
        frame=backed(e,0x30,name+' frame',fill=0x20+index)
        frames=backed(e,4,name+' frames',words=[frame])
        e.put(seq+0xc,frames,1)
        return seq
    def animation(name,index):
        image=backed(e,0x70,name)
        picture=backed(e,16,name+' picture',fill=0x51+index)
        pictures=backed(e,4,name+' pictures',words=[picture])
        e.put(image+0x14,pictures);e.put(image+0x64,0,0)
        return image
    handler=backed(e,4,'existing handler',words=[methods]);e.put(obj+0x70,handler);e.put(obj+0x78,handler)
    logic_entries=[]
    for i,n in enumerate(('LogicHit','LogicAttack')):
        resource=backed(e,0x20,n+' resource',words=[0,0,0,0,0x72819+i*0x1234])
        logic_entries.append((n,resource))
    logic=dictionary(e,logic_entries if resources else [],'logic')
    images=dictionary(e,[(n,animation(n,i)) for i,n in enumerate(('LEVEL_TOWERCANNONLEFT','LEVEL_TOWERCANNONRIGHT','LEVEL_CANNONBALL'))] if resources else [],'images')
    sequences=dictionary(e,[(n,sequence(n,i)) for i,n in enumerate(('LEVEL_TOWERCANNONLEFT_FIRING','LEVEL_TOWERCANNONLEFT_HOME','LEVEL_TOWERCANNONRIGHT_FIRING','LEVEL_TOWERCANNONRIGHT_HOME','LEVEL_CANNONBALL_FALL'))] if resources else [],'sequences')
    e.put(context+0x10,images,logic);e.put(context+0x2c,sequences);e.put(0x537680,0)
    e.put(0x50ba14,record(e,log,0x150,actor,state))
    if mutate:
        replacement=backed(e,0x200,'replacement object',data=e.read(obj,0x200))
        e.put(replacement+0x148,0x10203040);e.put(replacement+0x104,0x345678)
        def republish(e,call):
            n=e.get(log);e.put(log+4+n*40,0x77,call.receiver,e.get(state+0x1c),
                e.get(state+0x18),e.get(actor+0xc),e.get(obj+0x148),
                e.get(replacement+0x148),len(call.arguments),*(list(call.arguments)+[0,0])[:2])
            e.put(log,n+1);e.put(actor+0xc,replacement)
            return 0x98765432
        e.put(methods+0x1c,e.stub('republish object during logic callback','thiscall',0,republish))
    return dict(actor=actor,obj=obj,state=state,log=log,methods=methods)


def dispatch_setup(value,mode,random_words):
    def setup(e):
        t=world(e,{},False);actor=t['actor'];state=t['state'];log=t['log']
        # A backed RTTI descriptor for a missing state handler.
        data=backed(e,8,'RTTI data',words=[0x21436587,0x11223344])
        rtti=backed(e,16,'RTTI',words=[0,0,0,data]);vt=backed(e,8,'RTTI vtable',words=[rtti,0])
        e.put(actor,vt+4)
        callback=record(e,log,0x41,actor,state)
        fallback=backed(e,4,'fallback slot',words=[callback if mode!='empty' else 0])
        table=backed(e,16,'dispatch table',words=[callback,callback,callback,callback])
        handler=backed(e,24,'error handler',words=[0,0,0,4])
        e.put(0x534bfc,handler,10,13,table,fallback,4,fallback,0)
        e.put(0x544d18,0)
        if mode=='inverted':
            e.put(0x534c00,10,5,table,fallback,0)
            e.override(0x4a9070,lambda e,call:table)
        if mode=='empty':
            e.put(table+(value-10)*4,0)
        cpu=NativeSourceContext(72,1,0x7ff,0x5f3)
        for name,v in zip(('eax','ebx','ecx','edx','esi','edi','ebp'),random_words):setattr(cpu,name,v)
        cpu.esp=STACK_TOP-0x1000;cpu.eip=0x4141f0;cpu.eflags=2;cpu.fsHead=0xffffffff;cpu.ecx=actor;cpu.preserveMask=0x472
        t['source']=cpu
        return t
    return setup


def cases(random_source):
    fields=(0x148,0x14c,0x104,0x64,0x40)
    for function in (0x414030,0x414be0,0x495ec0,0x495f90):
        for mode in range(32):
            values={o:0 if not mode&(1<<i) else (2 if o==0x40 else 11+i) for i,o in enumerate(fields)}
            values.update({8:0x400,0x4c:53,0x50:67,0x170:0 if mode&1 else 0x1234})
            yield Case(f'{function:x} defaults {mode}',function,lambda e,v=values,r=bool(mode&2):world(e,v,r),receiver=lambda t:t['actor'],arguments=(lambda t:t['obj'],))
        yield Case(f'{function:x} callback republishes object',function,lambda e:world(e,{0x4c:53,0x50:67},True,True),receiver=lambda t:t['actor'],arguments=(lambda t:t['obj'],))
        for index in range(12):
            values={o:random_source.getrandbits(32) for o in fields};values[8]=random_source.getrandbits(32)&~0x10
            values.update({0x4c:53,0x50:67,0x170:0})
            yield Case(f'{function:x} random {index}',function,lambda e,v=values:world(e,v,True),receiver=lambda t:t['actor'],arguments=(lambda t:t['obj'],))
    for value in (0,1,2,28,29,30,31,999,1000,1001,0x7fffffff,0x80000000,0xffffffff):
        def setup(e,value=value):
            t=world(e,{0x4c:17,0x50:19},True);e.put(t['state']+0x1c,value)
            dispatch_state=backed(e,0x30,'dispatch state');e.put(t['actor']+0x10,dispatch_state)
            string=backed(e,20,'CString',words=[1,0,4,0,0]);slot=backed(e,4,'state string',words=[string+12])
            e.put(0x5376a0,0,0,slot,slot,4,slot,0)
            return t
        yield Case(f'event {value:#x}',0x414b20,setup,arguments=(lambda t:t['obj'],))
    for value,mode in ((10,'normal'),(13,'normal'),(11,'empty'),(9,'normal'),(14,'normal'),(6,'inverted')):
        words=[random_source.getrandbits(32) for _ in range(7)]
        yield Case(f'dispatch {value} {mode}',0x4141f0,dispatch_setup(value,mode,words),receiver=lambda t:t['actor'],arguments=(value,),source_context=lambda t:t['source'],source_return_pc=0x44677a)

