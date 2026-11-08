"""Original-backed terminal Gabriel states."""
import struct
from clawparity.cases import Case


def decrement(env,call):
    address=call.arguments[0]
    value=(env.get(address)-1)&0xFFFFFFFF
    env.put(address,value)
    return value


def setup_case(o):
    def setup(env):
        env.override(0x5469E8, decrement)
        a=env.object(0x600,'Gabriel',fill=0xA5)
        s=env.object(0x300,'sprite',fill=0x69)
        p=a+0x384 if o.get('alias_player',False) else env.object(0x200,'world actor',fill=0x3C)
        state=env.object(0x40,'state',fill=0x77)
        other=env.object(0x200,'other sprite',fill=0x57)
        ctx=env.object(0x80,'collision context')
        terrain=env.object(0x80,'terrain')
        vt=env.object(0x80,'vtable')
        witness=env.object(0x100,'callback observations',fill=0)
        env.put(a,vt)
        env.put(a+0xC,p,state)
        env.put(a+0x128,other,s)
        env.put(other+0xC,ctx)
        env.put(ctx+0x24,terrain)
        env.put(other+0x118,0x80000000)
        env.put(s+0x190,env.object(0x20,'prior animation',fill=0) if o.get('old_animation',False) else 0)
        env.put(s+0x1A4,o.get('finished',1))
        env.put(s+0x19C,o.get('remaining',0))
        env.put(s+0x40,o.get('flags',0x89))
        env.put(s+0x16C,o.get('frame',900))
        for i,off in enumerate((0x118,0x128,0x138)):
            env.put(s+off,0x80000000 if o.get('sentinels',0)&(1<<i) else 17+i*11)
            env.put(s+off+8,91+i*13)
        env.put(a+0x138,31)
        env.put(a+0x140,47)
        env.put(a+0x46C,0,0,0)
        env.put(a+0x4D0,0,0,0)
        env.put(a+0x4E4,o.get('started',400),o.get('delay',4000))
        env.put(a+0x4FC,o.get('last',950),o.get('interval',100))
        env.put(a+0x50C,o.get('spoken',1),o.get('latched',0))
        env.put(a+0x520,o.get('complete',0))
        env.put(a+0x45C,1)
        env.put(a+0x450,o.get('x',231),o.get('y',375))
        env.put(a+0x52C,o.get('target_x',450),o.get('target_y',600))
        bits=o.get('bits',8)
        env.put(a+0x2FC,bits)
        env.put(a+0x300,env.object(0x10,'external bit array',words=[0xA468C032,0x17]) if bits>32 else 0x95480421)
        env.put(p+0xCC,o.get('state',0))
        env.put(p+0x10C,o.get('health',0))
        game=env.object(0x200,'active player')
        active=env.object(0x40,'active state')
        env.put(game+0x10C,o.get('health',0))
        env.put(game+0x6C,active)
        env.put(0x537E88,game)
        env.put(0x53C9B0,p if o.get('speaker_busy',False) else 0)
        env.put(0x537210,o.get('now',1000))
        env.put(0x5430C4,o.get('tick',23))
        env.put(0x537680,0)
        empty=env.get(0x52E1C8)+12
        strings=[]
        for count in o.get('refcounts',(None,None)):
            if count is None:
                strings.append(empty)
            else:
                storage=env.object(32,'CString storage',fill=0x51)
                env.put(storage,count,5,19)
                strings.append(storage+12)
        env.put(a+0x1A4,*strings)
        for off,vals in ((0x38,o.get('velocity',(1.25,-0.75,0.5))),(0x68,o.get('position',(100.25,200.5,17.))),(0x50,(7.123456789,-11.234567891,15.345678912))):
            for i,v in enumerate(vals):
                env.write(a+off+8*i,struct.pack('<d',v))
        def callback(slot):
            def effect(env,call):
                n=env.get(witness)
                env.put(witness+4+n*0x20,slot,call.receiver,env.get(p+0xCC),env.get(a+0x520),env.get(a+0x534))
                env.put(witness,n+1)
                if slot==0x24 and o.get('callback_move',False):
                    env.write(a+0x68,struct.pack('<d',-123.75))
                return 0x31415926
            return effect
        for slot in (0x24,0x48):
            env.put(vt+slot,env.stub('Gabriel virtual '+hex(slot),'thiscall',0,callback(slot)))
        return {'actor':a,'player':p}
    return setup


def case(f,label,**o):
    o['old_animation']=f in (0x4452D0,0x445600,0x4456C0)
    return Case(hex(f)+' '+label,f,setup_case(o),receiver=lambda t:t['actor'])


def cases(r):
    for flags in (0x89,0x8B):
        for sentinels in range(8):
            yield case(0x445090,f'turn {flags} bounds {sentinels}',flags=flags,sentinels=sentinels,last=899)
    for interval in (0,49,50,51,0xFFFFFFFF):
        for frame in (899,900,901):
            yield case(0x445090,f'timer {interval} frame {frame}',interval=interval,frame=frame)
    for spoken,busy in ((0,False),(0,True),(1,False)):
        for latched in (0,1):
            for elapsed in (3999,4000,4001):
                yield case(0x445090,f'speech {spoken} busy {busy} latch {latched} time {elapsed}',spoken=spoken,speaker_busy=busy,latched=latched,now=400+elapsed)
    yield case(0x445090,'unsigned timer wrap',now=2,last=0xFFFFFFA0,started=0xFFFFF000)
    for velocity in ((0.,0.,0.),(1e-8,0.,0.),(0.1,0.,0.),(0.,0.2,0.),(0.,0.,0.5),(1.25,-0.75,0.5),(-2.,3.,-4.)):
        for flags in (0x89,0x8B):
            for sentinels in (0,7):
                yield case(0x4452D0,f'ballistic {velocity} flags {flags} bounds {sentinels}',velocity=velocity,flags=flags,sentinels=sentinels)
    for i in range(12):
        yield case(0x4452D0,f'random trajectory {i}',velocity=tuple(r.uniform(-10,10) for _ in range(3)),position=tuple(r.uniform(-1000,1000) for _ in range(3)),target_x=r.randrange(-2000,2000),target_y=r.randrange(-2000,2000))
    for state in (0,1,2,0xFFFFFFFF):
        yield case(0x4455B0,f'world state {state}',state=state)
    for f in (0x445600,0x4456C0):
        yield case(f,'direct transition',latched=0x13579)
    for finished in (0,1,7):
        for remaining in (0,1,0xFFFFFFFF):
            for latched in (0,1):
                yield case(0x445660,f'animation {finished} left {remaining} latch {latched}',finished=finished,remaining=remaining,latched=latched)
    for spoken,busy in ((0,False),(0,True),(1,False)):
        for finished,remaining,latched in ((0,0,0),(1,1,0),(1,0,1),(1,0,0)):
            for health in (0,1,0xFFFFFFFF):
                yield case(0x445720,f'speech {spoken} busy {busy} animation {finished}/{remaining} latch {latched} health {health}',spoken=spoken,speaker_busy=busy,finished=finished,remaining=remaining,latched=latched,health=health)
    for bits in (0,4,5,31,32,33,64):
        yield case(0x445720,f'bit capacity {bits}',health=1,bits=bits)
    for complete in (0,1,0xFFFFFFFF):
        for x in (-1001,0,231,0x7FFFFFFF):
            yield case(0x445810,f'complete {complete} x {x}',complete=complete,x=x)
    yield case(0x445810,'callback moves actor',callback_move=True)
    yield case(0x445810,'aliased world state and position',alias_player=True)
    for bits in (0,32,33,64):
        for counts in ((None,None),(1,2),(3,1),(0,-1)):
            yield case(0x445950,f'destructor storage {bits} refs {counts}',bits=bits,refcounts=counts)
    for value in (0,1,0xFFFFFFFF,0x12345678):
        for matches in (False,True):
            def setup(env,value=value,matches=matches):
                env.override(0x5469E8,decrement)
                env.put(0x53C9B0,value if matches else value^0x80000000)
                return {}
            yield Case(f'speaker {value:x} matches {matches}',0x48CF90,setup,arguments=(value,))
