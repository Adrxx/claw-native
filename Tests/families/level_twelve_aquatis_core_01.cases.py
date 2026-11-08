"""Aquatis cases based on original instructions."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence, reallocate

def string(env, text):
    data=text.encode()+b'\0';p=env.object(12+len(data),'state string')
    env.put(p,1,len(data)-1,len(data)-1);env.write(p+12,data)
    return p+12

def backing(words,direction=2,flags=0x91550000,rand=(0,0),state='LS_IDLE',enabled=1,frenzy=0,count=0,mask=0,audio=0,elapsed=100,delay=100,projectile=None,high=1,dispatch=None,ctor=False,scales=(1.375,0.635)):
    def setup(env):
        obj=env.object(0x4f0,'Aquatis',data=words)
        actor=env.object(0x240,'actor',fill=0);logic=env.object(0x200,'logic',fill=0);render=env.object(0x240,'render',fill=0)
        vt=env.object(0x100,'vtable');record=env.object(0x200,'callback record',fill=0)
        env.put(obj,vt);env.put(obj+0xc,actor,logic);env.put(obj+0x12c,render)
        env.put(actor+0x164,0x91372549,0x31415926);env.put(actor+0x4c,0x27915368)
        env.put(actor+0x6c,logic);env.put(actor+0x38,0xffffffff);env.put(actor+0x50,376);env.put(actor+0x10c,101)
        env.put(logic+0x164,0xaabbccdd);env.put(logic+0x1c,7);env.put(render+0x40,flags);env.put(render+0x190,0x71625384)
        env.put(obj+0x18c,direction);env.put(obj+0x138,0xfffffff1,0x4271,0x29,0x9153)
        for i,o in enumerate((0x118,0x128,0x138)):
            env.put(render+o,0x80000000 if (mask>>(i+2))&1 else 0xffffffed-i*7,0x12340001+i,0x32+i*13,0x56780001+i)
        for i,o in enumerate((0x334,0x338,0x350,0x374,0x460,0x464,0x468,0x46c)):
            frame=env.object(0x40,'frame '+str(i),fill=0x31+i)
            frames=env.object(4,'frames '+str(i),words=[frame]);anim=env.object(0x20,'animation '+str(i))
            env.put(anim+0xc,frames,1);env.put(obj+o,anim)
        for o in (0x390,0x394,0x398,0x39c,0x414,0x418,0x41c,0x470,0x474,0x478):env.put(obj+o,0)
        for i,o in enumerate((0x418,0x41c)):
            if mask&(1<<i):
                sound=env.object(0x20,'sound handle');backend=env.object(0x20,'sound backend');system=env.object(0x80,'sound system',fill=0)
                env.put(sound+0x10,backend);env.put(backend+0x10,system);env.put(obj+o,sound)
        env.put(0x532c0c,audio);env.put(0x532c10,0x139157)
        env.put(obj+0x4b8,enabled);env.put(obj+0x4b4,frenzy);env.put(obj+0x4a8,count)
        env.put(0x537210,0xf2345678);env.put(obj+0x4e4,(0xf2345678-elapsed)&0xffffffff,delay)
        stateptr=string(env,state)
        names=('LS_IDLE','LS_STARTUP','LS_SCARED','LS_SUPERFRENZY','LS_HIGHPUNCH','LS_LOWPUNCH','LS_STALACTITEHIT','LS_DEADACT1','LS_HITHIGH','LS_HITLOW','LS_DEAD')
        entries=[]
        for index,name in enumerate(names):
            entries.append((name.encode()+b'\0',string(env,name),0x71+index*11))
        def bit(data,index):
            return ((data[index//8] if index//8<len(data) else 0)>>(index%8))&1
        def tree(items,start):
            node=env.object(0x14,'state map node',fill=0)
            if len(items)==1:
                data,key,value=items[0];env.put(node,node,node,0,key,value)
            else:
                index=next(i for i in range(start,256) if len({bit(row[0],i) for row in items})==2)
                left=tree([row for row in items if not bit(row[0],index)],index+1)
                right=tree([row for row in items if bit(row[0],index)],index+1)
                env.put(node,left,right,index,items[0][1],0)
            return node
        root=env.object(0x14,'state map root',fill=0)
        env.put(root,tree(entries,1),root,0,entries[0][1],0)
        env.put(0x537680,root)
        states=env.object(4,'inverse states',words=[stateptr]);env.put(0x5376a0,7,7,states,states,4,0,0)
        def record_call(env,call):
            n=env.get(record);env.put(record,n+1)
            env.put(record+4+n*20,call.receiver,env.get(logic+0x1c),env.get(obj+0x24),env.get(obj+0x4a8),call.arguments[0] if call.arguments else 0)
            env.put(record+0x180+n*4,env.get(logic+0x18));env.put(record+0x1c0+n*4,env.get(0x534870))
            return 0xa1b2c300+n
        for off,argc in ((4,1),(8,1),(12,1),(0x10,0),(0x1c,0),(0x20,0),(0x48,0)):
            env.put(vt+off,env.stub('Aquatis method '+str(off),'thiscall',argc,record_call))
        env.override(0x4a3050,sequence(*rand))
        if projectile is not None:
            proj=env.object(0x180,'incoming projectile',fill=0);env.put(proj+0xd0,projectile);env.put(proj+0x138,0x80000000);env.put(actor+0x74,proj)
        root=env.object(0x80,'game root');sub=env.object(0x20,'game sub');settings=env.object(0x20,'settings')
        env.put(root+0x6c,sub);env.put(sub+0x14,settings);env.put(settings+0x14,high-1);env.put(0x537e88,root)
        if dispatch:
            arg,null,fail=dispatch[:3];stride=dispatch[3] if len(dispatch)>3 else 4;table=env.object(3*stride+4,'handlers',fill=0);default=env.object(4,'fallback handler');err=env.object(0x20,'error mode',fill=0);env.put(err+0xc,4)
            env.put(0x5349c0,0,10,env.object(44,'base handlers',words=[env.stub('base handler','thiscall',0,record_call)]*11),0,4,0,0)
            
            for index in range(3):env.put(table+index*stride,0 if null else env.stub('state handler '+str(index),'thiscall',0,record_call))
            env.put(default,env.stub('fallback handler','thiscall',0,record_call))
            env.put(0x534854,err,4,6,table,default,stride,0,0x9af15387)
            if fail:env.override(0x4a9070,reallocate(fail=True))
        if ctor:
            container=env.object(0x40,'resource container',fill=0);resources=env.object(0x40,'resource map',fill=0);animations=env.object(0x40,'animation map',fill=0)
            env.put(actor+0xc,container);env.put(logic+0xc,container);env.put(container+0x10,resources,resources);env.put(container+0x24,env.object(0x80,'collision layer',fill=0));env.put(container+0x28,resources,animations)
            env.put(resources+0x18,1);env.put(animations+0x18,1)
            secondary=env.object(0x40,'secondary resource container',fill=0)
            empty=env.object(0x40,'secondary empty map',fill=0);env.put(empty+0x18,1)
            env.put(secondary+0x10,empty,empty);env.put(secondary+0x28,empty,empty);env.put(logic+0xc,secondary)
            if ctor in (2,3,4,5) or ctor>=6:
                head=0
                keys=((0x5234c0,0x338),(0x52349c,0x334),(0x523488,0x350),(0x523474,0x464),(0x52345c,0x374),(0x523448,0x460),(0x523430,0x468),(0x523418,0x46c)) if ctor in (2,4,5) or ctor>=6 else ((0x5234b4,0x350),)
                for key,offset in keys:
                    node=env.object(16,'animation resource node',fill=0)
                    env.put(node,head,0,key,env.get(obj+offset));head=node
                buckets=env.object(4,'animation buckets',words=[head]);env.put(animations+0x14,buckets)
            if ctor in (4,5) or ctor>=6:
                image=env.object(0x80,'Aquatis image',fill=0)
                imageframe=env.object(0x40,'Aquatis image frame',fill=0)
                env.put(imageframe+0x18,13,17,101,113)
                env.put(image+0x14,env.object(4,'image frame array',words=[imageframe]))
                resource_keys=(0x523400,0x5233e8,0x5233d0,0x5233b8,0x5233a0,0x523388,0x523370,0x523358,0x523340,0x524098)
                head=0
                for index,key in enumerate(resource_keys):
                    # Missing lookups leave the original output local unchanged.
                    if ctor>=6 and index<5 and not ((ctor-6)>>index)&1:continue
                    handle=env.object(0x80,'resource handle '+str(index),fill=0)
                    env.put(handle+0x28,0x61+index*7)
                    node=env.object(16,'sound resource node',words=[head,0,key,handle]);head=node
                node=env.object(16,'image resource node',words=[head,0,0x5234d8,image]);head=node
                env.put(resources+0x14,env.object(4,'resource buckets',words=[head]))
            env.write(0x5262b0,struct.pack('<ff',*scales))
        env.put(obj+0x1a4,env.get(0x52e1c8)+12,env.get(0x52e1c8)+12);env.put(obj+0x2fc,0)
        return dict(obj=obj,actor=actor,logic=logic)
    return setup

def cases(random_source):
    words=struct.pack('<316I',*[random_source.getrandbits(32) for _ in range(316)])
    def case(label,fun,**kw):return Case(label,fun,backing(words,**kw),receiver=lambda t:t['obj'])
    for fun in (0x4053d0,0x4054c0,0x4055e0,0x405740):
        for direction in (2,3):yield case('state %x dir %d'%(fun,direction),fun,direction=direction)
    for direction in (2,3):
        for flags in (0x91550000,0x91550002):
            for sentinel in (0,28):
                for value in (0,49,50,100,101,0xffffffff,0x80000000):yield case('idle %d %x %d %x'%(direction,flags,sentinel,value),0x4050b0,direction=direction,flags=flags,mask=sentinel,rand=(value,0))
                for value in (0,1,2,0xffffffff,0xfffffffe):yield case('attack %d %x %d %x'%(direction,flags,sentinel,value),0x405240,direction=direction,flags=flags,mask=sentinel,rand=(value,))
    yield case('idle disabled',0x4050b0,enabled=0)
    for direction in (2,3):
        for flags in (0x91550000,0x91550002):
            for count in (0,3,4,5,0x7fffffff):
                for mask,audio in ((0,0),(3,0),(1,1),(2,1),(3,1)):yield case('stalactite %d %x %d %d %d'%(direction,flags,count,mask,audio),0x4058b0,direction=direction,flags=flags,count=count,mask=mask,audio=audio)
    for enabled,frenzy in ((0,0),(1,1),(1,0)):
        for state in ('LS_SUPERFRENZY','LS_STALACTITEHIT','LS_DEAD','LS_HITHIGH','LS_HITLOW','LS_DEADACT1','LS_IDLE','LS_SCARED'):yield case('hit gate %d %d %s'%(enabled,frenzy,state),0x405af0,enabled=enabled,frenzy=frenzy,state=state)
    for elapsed,delay in ((99,100),(100,100),(101,100),(0,0),(0xffffffff,0xfffffffe)):yield case('hit clock %x %x'%(elapsed,delay),0x405af0,elapsed=elapsed,delay=delay)
    for kind in (4,0x20,3):
        for state in ('LS_IDLE','LS_SCARED'):
            for high in (1,2):yield case('incoming %d %s %d'%(kind,state,high),0x405af0,projectile=kind,state=state,high=high)
    for state in (1,29,30,31,1000,0xffffffff):
        def setup(env,state=state):
            t=backing(words)(env);env.put(t['logic']+0x18,t['obj'],state);return t
        yield Case('entry state '+str(state),0x4041f0,setup,arguments=(lambda t:t['actor'],))
    for arg in (3,4,5,6,7):
        for null in (False,True):
            for fail in (False,):yield Case('dispatch %d %d %d'%(arg,null,fail),0x404310,backing(words,dispatch=(arg,null,fail)),receiver=lambda t:t['obj'],arguments=(arg,))
    for flag in (0,1,2,3,0x100,0x101):yield Case('delete '+str(flag),0x404e20,backing(words),receiver=lambda t:t['obj'],arguments=(flag,))
    for mode in (1,2,3,4,5):
        yield Case('construct resources '+str(mode),0x404990,backing(words,ctor=mode),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    def startup(env):
        t=backing(words,ctor=2)(env);env.put(t['logic']+0x18,t['obj'],0);return t
    yield Case('entry creates boss',0x4041f0,startup,arguments=(lambda t:t['actor'],))

    def aliased_frame(env):
        t=backing(words)(env)
        obj=t['obj'];animation=env.get(obj+0x46c);frames=env.get(animation+0xc)
        env.put(frames,obj+0x488);env.put(obj+0x4a4,0x71239581)
        return t
    yield Case('low punch observes flag before clearing',0x405740,aliased_frame,receiver=lambda t:t['obj'])

    # Independently suppress each animation box; neighboring boxes stay distinct.
    for mask in (4,8,16,12,20,24):
        for direction,flags in ((2,0x91550000),(3,0x91550002)):
            yield case('independent box %d %d'%(mask,direction),0x405240,direction=direction,flags=flags,mask=mask,rand=(0xffffffff,))
    for stride in (8,12):
        for arg in (4,5,6):
            yield Case('dispatch stride %d slot %d'%(stride,arg),0x404310,backing(words,dispatch=(arg,False,False,stride)),receiver=lambda t:t['obj'],arguments=(arg,))
    for bits in range(32):
        yield Case('constructor sound subset '+str(bits),0x404990,backing(words,ctor=6+bits),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    for scales in ((0.0,1.0),(-1.5,2.125),(0.125,-0.375),(1.999,0.001)):
        yield Case('constructor signed scales '+str(scales),0x404990,backing(words,ctor=37,scales=scales),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))

    # The original sound dispatcher publishes the chosen handle in global memory.
    # Distinct neighboring handles expose signed indexing and every rand%3 arm.
    for choice in (0,1,2,3,0xffffffff,0xfffffffe,0x80000000):
        def audible_idle(env,choice=choice):
            t=backing(words,rand=(50,choice))(env);obj=t['obj']
            voice=env.object(0x190,'sound dispatch actor',fill=0)
            state=env.object(0x20,'sound dispatch logic',fill=0)
            env.put(voice+0x6c,state);env.put(0x53c9ac,voice);env.put(0x53c9a8,0)
            env.put(obj+0x470,0x97150001,0x36270002,0x82190003)
            observation=env.object(0x80,'rand publication observation',fill=0)
            def draw(env,call):
                n=env.calls_so_far(0x4a3050)-1
                env.put(observation+n*24,env.get(obj+0x24),env.get(t['logic']+0x1c),env.get(obj+0x4cc),env.get(obj+0x4d0),env.get(obj+0x134),env.get(env.get(obj+0x12c)+0x190))
                return 50 if n==0 else choice
            env.override(0x4a3050,draw)
            return t
        yield Case('idle sound signed choice '+str(choice),0x4050b0,audible_idle,receiver=lambda t:t['obj'])
