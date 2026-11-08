"""Original-driven town guard state and defensive-switch cases."""
from clawparity.cases import Case
from clawparity.fixtures import sequence
from clawparity.env import NativeSourceContext


def setup_case(**kw):
    def setup(e):
        r=e.object(0x500,'guard',fill=0x39)
        actor=e.object(0x220,'actor',fill=0); control=e.object(0x100,'control',fill=0)
        vt=e.object(0xa0,'guard-vtable',fill=0); log=e.object(0x100,'callback-log',fill=0)
        def callback(slot):
            def effect(env,call):
                n=env.get(log)
                env.put(log+4+n*16,slot,call.receiver,env.get(r+0x20),env.get(r+0x3a0))
                env.put(log,n+1)
                if kw.get('change'):
                    env.put(r+0x20,0x12345678)
                    env.put(r+0x3a0,0x1a2b3c4d)
                return 0xdecafbad
            return effect
        for s in (0x44,0x48,0x58,0x64,0x68):
            e.put(vt+s,e.stub('guard-'+hex(s),'thiscall',0,callback(s)))
        e.put(r,vt);e.put(r+0xc,actor);e.put(r+0x10,control)
        e.put(control+0x1c,0)
        e.put(r+0x12c,actor);e.put(r+0x138,kw.get('left',17),29,kw.get('right',41),53)
        e.put(r+0x184,kw.get('state',3));e.put(r+0x18c,kw.get('direction',2))
        e.put(r+0x484,kw.get('seen',1));e.put(r+0x2e4,kw.get('chance',20))
        e.put(r+0x2fc,3,4) # pacing callee takes its callback path
        e.put(r+0x350,0);e.put(r+0x34c,0);e.put(r+0x384,0);e.put(r+0x450,0)
        e.put(r+0x488,kw.get('then',100));e.put(r+0x48c,kw.get('delay',10))
        e.put(actor+8,kw.get('flags',0xabcdef07));e.put(actor+0x40,kw.get('flip',0x12345600))
        e.put(actor+0x38,kw.get('frame',5));e.put(actor+0x190,0)
        e.put(actor+0x19c,kw.get('pending',0));e.put(actor+0x1a4,kw.get('finished',1))
        for off in (0x118,0x128,0x138):e.put(actor+off,11+off,23+off,31+off)
        # Callee registry: id zero resolves to HITLOW, avoiding unrelated hit policy.
        table=e.object(4,'state-name-table',words=[0x5234ec if kw.get('home') else 0x523204])
        e.put(0x537698+8,0,0,table,0,4);e.put(0x5376b4,0,0)
        e.put(0x537668+0x18,0)
        if kw.get('lookup'):
            node=e.object(0x14,'state-node',fill=0)
            e.put(node,node,node,0,0x526a38 if kw['lookup']=='block' else 0x52d464,7)
            e.put(0x537668+0x18,node)
        if kw.get('anim'):
            command=e.object(0x30,'animation-command',fill=0)
            e.put(command+0xc,9);e.put(command+0x18,3,0xabcdef12)
            pointers=e.object(4,'animation-frames',words=[command])
            old=e.object(0x20,'old-animation',fill=0);e.put(old+0xc,pointers,1)
            new=e.object(0x20,'new-animation',fill=0);e.put(new+0xc,pointers,1)
            e.put(actor+0x18c,actor)
            e.put(actor+0x190,old,command,0,kw.get('pending',0),0x76543210,kw.get('finished',1),0x87654321,0,0x3f800000)
            for off in (0x350,0x34c,0x384,0x450):e.put(r+off,new)

        player=e.object(0x120,'player',fill=0);pc=e.object(0x40,'player-control',fill=0);weapon=e.object(0x80,'weapon',fill=0)
        e.put(player+0x6c,pc);e.put(pc+0x14,weapon);e.put(weapon+0x3c,kw.get('weapon',1))
        e.put(player+0xcc,kw.get('playerstate',1));e.put(player+0x4c,96,kw.get('dy',0)+64)
        e.put(0x537e88,player);e.put(0x537964,kw.get('level',6))
        e.put(0x537210,kw.get('now',110));e.put(0x5430c4,kw.get('delta',1))
        e.put(0x534eac,kw.get('mode',0));e.put(0x532c0c,kw.get('sound',1));e.put(0x532c10,0x654321)
        # A real original sound callee returns early with its disabled backend.
        backend=e.object(0x90,'sound-backend',fill=0);sound=e.object(0x30,'sound',fill=0);entry=e.object(0x20,'sound-entry',fill=0)
        e.put(sound+0x10,backend);e.put(entry+0x10,sound)
        if kw.get('live_sound'):
            e.put(backend+0x78,1);e.put(0x532c10,35)
            soundlog=e.object(0x1000,'sound-callback-log',fill=0)
            def make_sound(slot):
                snd=e.object(0x50,'live-sound-'+hex(slot),fill=0)
                local_backend=e.object(0x90,'live-sound-backend-'+hex(slot),fill=0)
                e.put(local_backend+0x78,1)
                device=e.object(4,'sound-device-'+hex(slot),fill=0)
                device_methods=e.object(0x18,'sound-device-methods-'+hex(slot),fill=0)
                iface=e.object(4,'sound-interface-'+hex(slot),fill=0)
                methods=e.object(0x48,'sound-methods-'+hex(slot),fill=0)
                def effect(method):
                    def observe(env,call):
                        n=env.get(soundlog);env.put(soundlog,n+1)
                        env.put(soundlog+4+n*24,slot,method,*call.arguments,*([0]*(4-len(call.arguments))))
                        if method in (0x18,0x1c,0x20):env.put(call.arguments[1],22050 if method==0x20 else slot)
                        if method==0x14:env.put(call.arguments[2],iface)
                        return 0
                    return observe
                for method,argc in ((0x18,2),(0x1c,2),(0x20,2),(0x30,4),(0x3c,2),(0x40,2),(0x44,2)):
                    e.put(methods+method,e.stub('sound-'+hex(slot)+'-'+hex(method),'stdcall',argc,effect(method)))
                e.put(device,device_methods);e.put(device_methods+0x14,e.stub('duplicate-sound-'+hex(slot),'stdcall',3,effect(0x14)))
                e.put(local_backend+0x14,device);e.put(iface,methods)
                e.put(snd+0xc,iface,local_backend)
                return snd
        else:
            make_sound=lambda slot:sound

        for off in range(0x454,0x480,4):
            slot=e.object(0x20,'sound-slot-'+hex(off),fill=off & 255)
            e.put(slot+0x10,make_sound(off))
            e.put(r+off,slot if kw.get('entry',1) else 0)
        speech=e.object(0x190,'speech',fill=0);sc=e.object(0x30,'speech-control',fill=0)
        e.put(speech+0x6c,sc);e.put(0x53c9ac,speech);e.put(0x53c9a8,0)
        # Original visibility query runs over an ordinary empty tile map.
        world=e.object(0xa0,'world',fill=0);tilemap=e.object(0xa0,'tile-map',fill=0)
        tiles=e.object(4,'tiles',words=[0xffffffff]);rows=e.object(4,'rows',fill=0)
        e.put(world+0x5c,tilemap);e.put(tilemap+0x20,tiles,rows);e.put(tilemap+0x30,1024,1024)
        e.put(tilemap+0x8c,10,10)
        engine=e.object(0x40,'engine',fill=0);ec=e.object(0x40,'engine-control',fill=0)
        e.put(engine+0xc,ec);e.put(ec+0x24,world);e.put(r+0x190,engine,actor)
        e.put(actor+0x4c,64,64)
        if kw.get('blocked'):
            block=e.object(4,'blocking-tile',fill=0);bvt=e.object(0x24,'blocking-vtable',fill=0);objects=e.object(4,'tile-objects',words=[block])
            e.put(block,bvt);e.put(bvt+0x20,e.stub('tile-collision','thiscall',2,lambda env,call:1));e.put(world+0x4c,objects);e.put(tiles,0)
        e.override(0x4a3050,sequence(*kw.get('random',(0,0,0,0,0,0,0,0))))
        return {'r':r,'actor':actor,'control':control}
    return setup


def case(fn,label,**kw):
    return Case(label,fn,setup_case(**kw),receiver=lambda t:t['r'],arguments=((lambda t: t['actor']),) if fn in (0x497ab0,0x497b00,0x497c50) else ())


def ctor(seed):
    def setup(e):
        r=e.object(0x40,'constructor',fill=seed & 255);a=e.object(0x180,'actor',fill=0x56)
        control=e.object(0x50,'control',fill=0);manager=e.object(0x40,'manager',fill=0)
        e.put(a+0xc,control);e.put(control+0x14,manager);e.put(manager+0x18,17)
        e.put(a+0x6c,seed)
        if seed & 1:
            buckets=e.object(17*4,'logic-buckets',fill=0);e.put(manager+0x14,buckets)
            for text,offset in ((b'LogicHit',0x70),(b'LogicAttack',0x78)):
                name=e.object(len(text)+1,'logic-name',data=text+b'\0')
                descriptor=e.object(0x20,'logic-descriptor',fill=0);e.put(descriptor+0x10,seed^offset)
                h=0
                for c in text:h=(h*33+c)&0xffffffff
                index=h%17
                node=e.object(0x10,'logic-node',words=[e.get(buckets+index*4),0,name,descriptor]);e.put(buckets+index*4,node)
                component=e.object(0x30,'logic-component',fill=0);methods=e.object(0x28,'logic-methods',fill=0)
                e.put(component,methods);e.put(a+offset,component)
                e.put(methods+0x1c,e.stub('logic-clear-'+hex(offset),'thiscall',0,lambda env,call:0))
                e.put(methods+0x24,e.stub('logic-setup-'+hex(offset),'thiscall',2,lambda env,call:0))
        return {'r':r,'actor':a}
    return setup


def source_case(fn, label, pc, variant, random_source, **kw):
    # Every source case supplies independent nonzero CPU and stack witnesses.
    # The PCs are the original TownGuard dispatch CALL continuations.
    registers = [random_source.getrandbits(32) for _ in range(7)]
    residue = bytes(random_source.getrandbits(8) for _ in range(0x140))

    def setup(e):
        tokens = setup_case(**kw)(e)
        esp = 0x02007ff0
        e.write(esp - 0x100, residue)
        e.put(esp, pc)
        fs = 0xffffffff
        if variant % 2:
            fs = 0x02008080
            e.put(fs, 0xffffffff, 0x5067f8, 0xffffffff)
        ebp = (0, 0xffffffff, registers[6], fs)[variant % 4]
        tokens['source'] = NativeSourceContext(
            size=72, version=1, inputMask=0x7ff, outputMask=0x5ff,
            eax=registers[0], ebx=registers[1], ecx=tokens['r'],
            edx=registers[2], esi=registers[3], edi=registers[4],
            ebp=ebp, esp=esp, eip=fn, eflags=2 | (variant & 1),
            fsHead=fs, preserveMask=0x472)
        return tokens

    return Case(label, fn, setup, receiver=lambda t: t['r'],
                source_context=lambda t: t['source'], source_return_pc=pc)


def cases(random_source):
    for n in range(10):
        yield Case('constructor distinct '+str(n),0x453bd0,ctor((random_source.getrandbits(32)&~1)|(n%2)),receiver=lambda t:t['r'],arguments=(lambda t:t['actor'],))
    for fn in (0x483dc0,0x4979b0,0x497a50):
        for finished,pending in ((0,0),(1,0),(1,7)):
            for sound in (0,1):
                yield case(fn,f'animation {fn:x} {finished}/{pending}/{sound}',finished=finished,pending=pending,sound=sound,change=sound,random=(2000,19,0))
    for now,then,delay in ((109,100,10),(110,100,10),(111,100,10),(5,0xfffffff0,21),(5,0xfffffff0,22),(0,0,0),(0,0,0xffffffff)):
        yield case(0x497a50,f'timer {now}/{then}/{delay}',now=now,then=then,delay=delay)
    for state in (0,3,4,5,6):
        for v in (-1,0,19,20,39,40,49,50,69,70,99,120,121):
            yield case(0x497750,f'home state {state} rand {v}',state=state,random=(v,v,1,99),direction=2 if v%2 else 1,flip=0xabcdef00 if v%3 else 0xabcdef02,change=v%2)
    for mode,blocked,dy,frame in ((0x26b7,False,0,5),(0,True,0,5),(0,False,50,5),(0,False,-50,5),(0,False,49,-1),(0,False,49,5),(0,False,-49,5),(0,False,0,5)):
        for v in (69,70):
            yield case(0x497750,f'home visibility {mode}/{blocked}/{dy}/{frame}/{v}',seen=0,mode=mode,blocked=blocked,dy=dy,frame=frame,random=(v,1,99,99))
    for state in (3,6):
        for v in (-1,0,19,20,99):
            yield case(0x497970,f'enter idle {state}/{v}',state=state,random=(v,99))
    for fn in (0x497ab0,0x497b00,0x497c50,0x497dc0):
        for entry,sound in ((0,0),(1,0),(1,1)):
            for v in (-1,0,1,39,40,99):
                yield case(fn,f'sound slots {fn:x}/{entry}/{sound}/{v}',entry=entry,sound=sound,level=0,weapon=0,random=(v,v,v,v))
    for fn in (0x497b00,0x497c50):
        for weapon in (0,1,2,3,7,8,9):
            for level in (4,5,6):
                for v in (24,25,49,50):
                    yield case(fn,f'switch {fn:x}/{weapon}/{level}/{v}',weapon=weapon,level=level,random=(v,1,99,0),direction=2 if v%2 else 1,flip=0xabcdef02 if v%2 else 0xabcdef00)
        for playerstate in (0,1,5,6):
            for direction in (1,2):
                for flip in (0xabcdef00,0xabcdef02):
                    yield case(fn,f'orientation {fn:x}/{playerstate}/{direction}/{flip}',playerstate=playerstate,direction=direction,flip=flip,random=(0,0,99,0))
    for n in range(12):
        yield case(0x497dc0,f'random block {n}',left=random_source.getrandbits(32),right=random_source.getrandbits(32),flags=random_source.getrandbits(32),random=(n%2,n*9,n%2))

    for fn in (0x497ab0,0x497b00,0x497c50,0x497dc0):
        for v in (0,1,-1,39,40):
            yield case(fn,f'live sound {fn:x}/{v}',live_sound=True,random=(v,v,1,99),level=0,weapon=0)
    for fn in (0x483dc0,0x4979b0,0x497a50):
        for finished,pending in ((0,0),(0,2),(1,0),(1,2)):
            yield case(fn,f'active animation {fn:x}/{finished}/{pending}',anim=True,finished=finished,pending=pending,lookup='idle',random=(-1,0))
    for state in (3,4):
        for v in (0,1,99):
            yield case(0x497750,f'home next state reevaluation {state}/{v}',home=True,state=state,chance=200,random=(v,v,v,v))
    for v in (0,1):
        yield case(0x497dc0,f'block successful state lookup {v}',lookup='block',anim=True,live_sound=True,random=(v,0,v))

    # Source capability must retain the registers and the physical CALL frame
    # that an ordinary result-only projection cannot reconstruct.
    for pc in (0x4971f9, 0x49722c):
        for n, (now, then, delay) in enumerate((
                (100,90,20), (109,100,10), (110,100,10), (111,100,10),
                (5,0xfffffff0,21), (5,0xfffffff0,22), (0,0,0), (0,0,0xffffffff))):
            yield source_case(0x497a50, f'source timer {pc:x}/{n}', pc, n,
                              random_source, now=now, then=then, delay=delay)
        for fn in (0x483dc0, 0x4979b0, 0x497a50):
            for n, (anim, finished, pending) in enumerate((
                    (False,0,0), (False,1,0), (False,1,7),
                    (True,0,0), (True,1,0), (True,1,7))):
                yield source_case(fn, f'source animation {fn:x}/{pc:x}/{n}', pc, n,
                                  random_source, anim=anim, finished=finished,
                                  pending=pending, lookup='idle', change=n % 2,
                                  random=(-1,2000,19,0))
        for state in (0,3,4,5,6):
            for n, v in enumerate((0,19,20,39,50,99)):
                yield source_case(0x497750, f'source state {pc:x}/{state}/{v}', pc, n,
                                  random_source, state=state, random=(v,v,1,99),
                                  direction=2 if n % 2 else 1,
                                  flip=0xabcdef00 if n % 3 else 0xabcdef02,
                                  change=n % 2)
        for n, (mode, blocked, dy, frame) in enumerate((
                (0x26b7,False,0,5), (0,True,0,5), (0,False,50,5),
                (0,False,-50,5), (0,False,49,-1), (0,False,49,5),
                (0,False,-49,5), (0,False,0,5))):
            yield source_case(0x497750, f'source visibility {pc:x}/{n}', pc, n,
                              random_source, seen=0, mode=mode, blocked=blocked,
                              dy=dy, frame=frame, random=(69+n%2,1,99,99))
