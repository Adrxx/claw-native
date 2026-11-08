"""Original-derived laser inputs with fixed branch coverage and seeded payloads."""
from clawparity.cases import Case


def state_setup(payload, sprite="none", animation=False, registry=71, start=10, duration=20, now=30, done=0, wait=0, mode=0, step=1, ctor=False, registry_match=True, distinct=False):
    def setup(e):
        s=e.object(0x58,"state",data=payload[:0x58]); o=e.object(0x1b4,"owner",data=bytes(x ^ 0x5a for x in payload)); d=e.object(0xbc,"data",data=bytes(x ^ 0xa5 for x in payload[:0xbc]))
        e.put(s+8,o,o,d); e.put(s+0x28,o,o,d); e.put(s+0x48,0,duration,start,duration)
        e.put(o+0x6c,d); e.put(o+0x170,0); e.put(o+0x18c,o); e.put(o+0x190,0); e.put(o+0x19c,wait,mode,done); e.put(d+0xb8,duration)
        n=e.object(20,"idle-node"); name=e.object(8,"idle-name",data=b"LS_IDLE\0"); e.put(n,n,n,0,name,registry); e.put(0x537680,n if registry_match else 0)
        spr=0
        if sprite!="none":
            spr=e.object(0x6c,"sprite"); table=e.object(16,"sprite-table",data=payload[:16])
            low,high={"valid":(0,3),"low-equal":(1,3),"low-out":(2,3),"high-equal":(-2,1),"high-out":(-2,0)}[sprite]
            e.put(spr+0x14,table); e.put(spr+0x64,low,high); e.put(o+0x170,spr)
        ani=0
        if animation:
            ani=e.object(0x14,"animation",fill=0); frames=e.object(8,"frame-table"); frame=e.object(0x30,"frame",fill=0)
            e.put(frames,frame,frame); e.put(ani+0xc,frames,2); e.put(frame+0xc,9); e.put(frame+0x18,3,0xf00d1234)
            e.put(o+0x190,ani,frame,0,wait,mode,done); e.put(o+0x1a8,0xa5123498,0x87654321,0x3f800000)
        e.put(s+0x48,ani); e.put(0x537210,now); e.put(0x5430c4,step)
        if ctor:
            ctx=e.object(0x30,"context"); e.put(o+0xc,ctx)
            for offset,pairs in ((0x10,[("LEVEL_LASER",spr)]),(0x14,[]),(0x2c,[("LEVEL_LASER_LASER",ani)])):
                wrapper=e.object(0x34,"map-wrapper"); bucket=e.object(4,"map-bucket"); head=0
                for key,value in pairs:
                    string=e.object(len(key)+1,"map-name",data=key.encode()+b"\0"); head=e.object(16,"map-node",words=[head,0,string,value])
                e.put(bucket,head); e.put(wrapper+0x14,bucket,1); e.put(ctx+offset,wrapper)
        if distinct and not ctor:
            # Back all alternate pointer fields with independently initialized
            # objects so reading a nearby field remains observable.
            other=e.object(0x1b4,"alternate-owner",data=payload)
            other_data=e.object(0xbc,"alternate-data",data=payload[:0xbc])
            e.put(other+0x6c,other_data); e.put(other+0x170,0)
            e.put(other+0x18c,other); e.put(other+0x190,0)
            e.put(other+0x19c,wait,mode,done)
            e.put(s+8,other,other); e.put(s+0x28,other)
            e.put(s+0x30,other_data)
        return {"state":s,"owner":o}
    return setup


def constructor_observed(payload, duration, animation, change, sprite_miss=False, animation_miss=False):
    def setup(e):
        t=state_setup(payload,"valid",animation,0x71625384,duration=duration,
                      now=0x31415926,ctor=True)(e)
        state,owner=t["state"],t["owner"]
        other=e.object(0x1b4,"alternate-constructor-owner",data=bytes(x ^ 0x33 for x in payload))
        data=e.object(0xbc,"alternate-constructor-data",data=payload[:0xbc])
        e.put(data+0xb8,duration ^ 0x73a495b6)
        e.put(other+0xc,e.get(owner+0xc)); e.put(other+0x6c,data)
        e.put(other+0x170,0); e.put(other+0x18c,other); e.put(other+0x190,0)
        e.put(other+0x19c,0,0,0)
        e.put(state+8,other,other,data)
        e.put(state+0x28,other,other,data)
        e.put(state+0x48,0,duration ^ 0x89abcdef,0x98123645,0x782349ab)
        records=e.object(4+4*(16+0x58+0x1b4),"constructor-callback-observations",fill=0)
        def effect(stage):
            def invoke(e,c):
                count=e.get(records); at=records+4+count*(16+0x58+0x1b4)
                e.put(at,stage,c.receiver,len(c.arguments),c.arguments[0] if c.arguments else 0)
                e.write(at+16,e.read(state,0x58)); e.write(at+16+0x58,e.read(owner,0x1b4))
                e.put(records,count+1)
                if stage==1 and change==1: e.put(state+0xc,other)
                if stage==1 and change==2: e.put(state+0x10,data)
                if stage==3 and change==3: e.put(owner+0x6c,data)
                return stage ^ 0x88776655
            return invoke
        for target in (owner,other):
            for offset,stage in ((0x70,0),(0x78,2)):
                logic=e.object(0x174,"existing-logic",data=(payload*2)[:0x174])
                vt=e.object(0x28,"logic-vtable")
                e.put(logic,vt)
                e.put(vt+0x1c,e.stub(f"logic clear {stage}","thiscall",0,effect(stage)))
                e.put(vt+0x24,e.stub(f"logic attach {stage+1}","thiscall",2,effect(stage+1)))
                e.put(target+offset,logic)
        ctx=e.get(owner+0xc); wrapper=e.get(ctx+0x14); bucket=e.get(wrapper+0x14)
        head=0
        for key,token in (("LogicHit",0x91357421),("LogicAttack",0xa2468753)):
            resource=e.object(0x14,"logic-resource",data=payload[:0x14]); e.put(resource+0x10,token)
            name=e.object(len(key)+1,"logic-name",data=key.encode()+b"\0")
            head=e.object(16,"logic-map-node",words=[head,0,name,resource])
        e.put(bucket,head)
        if sprite_miss:
            # Preserve the old nonnull sprite, but remove the registry entry.
            sprite_wrapper=e.get(ctx+0x10)
            e.put(e.get(sprite_wrapper+0x14),0)
        else:
            # The resource lookup must publish a different sprite than input.
            e.put(owner+0x170,0)
        if animation_miss:
            animation_wrapper=e.get(ctx+0x2c)
            e.put(e.get(animation_wrapper+0x14),0)
            # An erroneously uninitialized output aliases the owner argument.
            # Back that alternate interpretation as an animation, so a bad
            # result remains comparable instead of causing a fixture fault.
            frame=e.object(0x30,"alternate-output-frame",data=payload[:0x30])
            e.put(ctx,frame); e.put(owner+0x10,1)
        return t
    return setup


def dispatch_setup(payload,index,low,high,stride,handler):
    def setup(e):
        s=e.object(0x58,"state",data=payload[:0x58]); vt=e.object(12,"vtable"); rtti=e.object(16,"rtti"); typ=e.object(8,"type",data=payload[:8])
        e.put(s,vt+4); e.put(vt,rtti); e.put(rtti+0xc,typ)
        record=e.object(40,"observations",data=payload[:40])
        def callback(slot):
            def invoke(e,c):
                e.put(record,slot,c.receiver,len(c.arguments),e.get(0x5379f0),
                      e.get(0x5379d8),e.get(0x5379dc),e.get(c.receiver+0x20),
                      e.get(c.receiver+0x24),e.get(c.receiver+0x38),e.get(0x5379e0))
                e.put(c.receiver+0x38,slot ^ 0xaabbccdd)
                e.put(0x5379f0,0x87654321)
                return slot ^ 0x88776655
            return e.stub(f"handler slot {slot}","thiscall",0,invoke)
        table=e.object(max(4,(high-low+1)*stride),"state-table",
                       data=(payload * (((high-low+1)*stride)//len(payload)+1))[:(high-low+1)*stride])
        for n in range(high-low+1):
            # Distinct adjacent callbacks expose a wrong signed offset or stride.
            e.put(table+n*stride,0 if low+n == index and not handler else callback(low+n))
        fallback=e.object(4,"fallback",words=[callback(0x12345678)])
        e.put(0x5379d0,0,0,low,high,table,fallback,stride,0,0x13579bdf)
        return {"state":s}
    return setup


def cases(r):
    def payload(): return bytes(r.randrange(256) for _ in range(0x1b4))
    for sprite in ("none","valid","low-equal","low-out","high-equal","high-out"):
        for animation in (False,True):
            for duration in (0,1,0xffffffff):
                yield Case(f"idle {sprite} ani={animation} dur={duration}",0x4558b0,state_setup(payload(),sprite,animation,r.getrandbits(32),duration=duration,now=r.getrandbits(32)),receiver=lambda t:t["state"])
    for sprite in ("none","valid","low-equal","low-out"):
        for animation in (False,True):
            yield Case(f"ctor {sprite} ani={animation}",0x455490,state_setup(payload(),sprite,animation,r.getrandbits(32),ctor=True),receiver=lambda t:t["state"],arguments=(lambda t:t["owner"],))
    timing=[(100,20,119),(100,20,120),(100,20,121),(0xfffffffe,3,0),(0xfffffffe,3,1),(10,0,10),(10,0xffffffff,9),(10,0xffffffff,8),(10,0x80000000,0x80000009),(10,0x80000000,0x8000000a)]
    for start,duration,now in timing:
        for done,wait in ((0,0),(1,0),(0,2),(1,2)):
            yield Case(f"tick {start:x}/{duration:x}/{now:x} done={done} wait={wait}",0x455960,state_setup(payload(),"valid",False,r.getrandbits(32),start,duration,now,done,wait),receiver=lambda t:t["state"])
    for done,wait,mode,step in ((1,0,0,1),(1,2,0,1),(1,1,0,1),(1,2,1,1),(1,2,1,2),(0,0,0,1)):
        yield Case(f"animated tick {done}/{wait}/{mode}/{step}",0x455960,state_setup(payload(),"valid",True,r.getrandbits(32),10,20,30,done,wait,mode,step),receiver=lambda t:t["state"])
    for low,high in ((-2,2),(0,0),(8,12)):
        for index in (low-1,low,high,high+1):
            for handler in (False,True):
                for stride in (4,8):
                    yield Case(f"dispatch {low}:{high} index={index} stride={stride} handler={handler}",0x455600,dispatch_setup(payload(),index,low,high,stride,handler),receiver=lambda t:t["state"],arguments=(index,))

    for registry_match in (False, True):
        for animation in (False, True):
            for sprite in ("none", "valid", "high-out"):
                yield Case(f"idle independent fields {registry_match}/{animation}/{sprite}",
                           0x4558b0,state_setup(payload(),sprite,animation,r.getrandbits(32),
                           duration=r.getrandbits(32),now=r.getrandbits(32),
                           registry_match=registry_match,distinct=True),receiver=lambda t:t["state"])
    for done,wait in ((0,0),(1,0),(1,2)):
        for elapsed in (19,20,21):
            yield Case(f"tick independent fields {done}/{wait}/{elapsed}",0x455960,
                       state_setup(payload(),"valid",False,r.getrandbits(32),100,20,100+elapsed,
                                   done,wait,distinct=True),receiver=lambda t:t["state"])
    for low,high in ((-0x80000000,-0x7ffffffe),(0x7ffffffd,0x7fffffff),(-3,3)):
        for index in range(low,high+1):
            for stride in (4,12):
                yield Case(f"dispatch signed slot {low}:{high}/{index}/{stride}",0x455600,
                           dispatch_setup(payload(),index,low,high,stride,True),
                           receiver=lambda t:t["state"],arguments=(index,))

    for duration in (0,1,0xffffffff,r.getrandbits(32)):
        for animation in (False,True):
            for registry_match in (False,True):
                yield Case(f"ctor duration {duration:x}/{animation}/{registry_match}",0x455490,
                           state_setup(payload(),"valid",animation,r.getrandbits(32),
                                       duration=duration,now=r.getrandbits(32),ctor=True,
                                       registry_match=registry_match),receiver=lambda t:t["state"],
                           arguments=(lambda t:t["owner"],))

    for duration in (0,1,0xffffffff,r.getrandbits(32)):
        for animation in (False,True):
            for change in (0,1,2,3):
                yield Case(f"constructor observed {duration:x}/{animation}/{change}",0x455490,
                           constructor_observed(payload(),duration,animation,change),
                           receiver=lambda t:t["state"],arguments=(lambda t:t["owner"],))

    for animation in (False,True):
        for sprite_miss in (False,True):
            for animation_miss in (False,True):
                yield Case(f"constructor registry publications {animation}/{sprite_miss}/{animation_miss}",
                           0x455490,constructor_observed(payload(),r.getrandbits(32),animation,0,
                                                       sprite_miss,animation_miss),
                           receiver=lambda t:t["state"],arguments=(lambda t:t["owner"],))
