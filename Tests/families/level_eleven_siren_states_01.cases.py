"""Original-driven Siren states."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def hash_map(env, address, pairs=()):
    buckets = env.object(4, 'resource-bucket')
    head = 0
    for key, value in pairs:
        name = env.object(len(key)+1, 'resource-name', data=key.encode()+b'\0')
        head = env.object(16, 'resource-node', words=[head, 0, name, value])
    env.put(buckets, head)
    env.put(address+4, buckets, 1)


def common(env, rand=(100,50), flip=0, mode=3, direction=2):
    r=env.object(0x4b0,'siren',fill=0); a=env.object(0x200,'actor',fill=0)
    c=env.object(0x180,'controller',fill=0); w=env.object(0x100,'world',fill=0)
    v=env.object(0x80,'virtual-methods',fill=0); log=env.object(0x100,'observations',fill=0)
    col=env.object(0x100,'collision',fill=0); player=env.object(0x200,'player',fill=0)
    pc=env.object(0x180,'player-controller',fill=0); facing=env.object(8,'facing',words=[0,1])
    managers=[]
    for off in (0x10,0x14,0x28,0x2c):
        m=env.object(0x100,'manager',fill=0); env.put(w+off,m); hash_map(env,m+0x10); managers.append(m)
    env.put(w+0x24,col); env.put(col+0x64,0x7fffffff,0x7fffffff)
    env.put(a+0xc,w); env.put(a+0x40,flip|0x100); env.put(a+0x4c,111,222)
    env.put(a+0x64,17); env.put(a+0x6c,c); env.put(a+0xcc,7)
    env.put(a+0x118,-11,-22,33,44,-55,-66,77,88,-99,-111,123,134)
    anim=env.object(0x20,'current-animation',fill=0)
    event=env.object(0x30,'current-animation-event',fill=0)
    env.put(event+0x1c,0x2468); env.put(a+0x190,anim,event,0,17,0)
    env.put(c+0xc,w); env.put(a+0x16c,201); env.put(a+0x18c,a); env.put(c+0x1c,0x123456); env.put(c+0x168,0x1357)
    env.put(r,v); env.put(r+0xc,a,c); env.put(r+0x20,2); env.put(r+0x128,a,a,c)
    env.put(r+0x138,-13,17,29,37); env.put(r+0x184,mode,0,direction); env.put(r+0x194,a)
    env.put(r+0x2fc,32,4); env.put(r+0x400,60)
    env.put(r+0x470,100,1000,100,1000,100,300,100,500,100,1000)
    env.put(r+0x498,-28,-10,-200,47,0,0);
    selected=env.object(0x20,'strike-animation',fill=0); event2=env.object(0x30,'strike-event',fill=0); seq2=env.object(4,'strike-events',words=[event2])
    env.put(selected+0xc,seq2,1); env.put(event2+0x1c,0x1a2b3c); env.put(r+0x310,selected,anim)
    env.put(r+0x344,selected); env.write(r+0x68,struct.pack('<d',111.0))
    env.put(player+0x4c,211,222); env.put(player+0x6c,pc); env.put(pc+0x14,facing)
    env.put(0x537e88,player); env.put(0x537964,12); env.put(0x537210,1100); env.put(0x5430c4,7)
    env.put(0x534eac,0x26b7); env.put(0x541334,1); env.put(0x537680,0)
    sound_actor=env.object(0x200,'sound-actor',fill=0); sound_control=env.object(0x140,'sound-controller',fill=0)
    env.put(sound_actor+0x6c,sound_control); env.put(sound_control+0x1c,15)
    env.put(0x53c9ac,sound_actor); env.put(0x53c9a8,0); env.put(0x53c9b0,a)
    env.put(r+0x410,0x441122); env.put(r+0x45c,0x331122,0x551122,0x661122)
    env.override(0x4a3050,sequence(*rand))
    def copy(e,call): e.write(call.arguments[0],e.read(call.arguments[1],16)); return 1
    def decrement(e,call):
        value=(e.get(call.arguments[0])-1)&0xffffffff; e.put(call.arguments[0],value); return value
    env.override(0x546d58,copy); env.override(0x5469e8,decrement)
    for off in (0x44,0x48,0x58):
        def callback(e,call,off=off):
            i=e.get(log); e.put(log,i+1)
            e.put(log+4+i*24,off,call.receiver,e.get(r+0x4a4),e.get(r+0x50),e.get(r+0x24),e.get(r+0x4ac)); return 0x981237
        env.put(v+off,env.stub('siren-method','thiscall',0,callback))
    return dict(r=r,a=a,c=c,w=w,v=v,log=log,player=player,facing=facing,managers=managers)


def case(label,f,configure=None,args=(),**base):
    def setup(env):
        t=common(env,**base)
        if configure: configure(env,t)
        return t
    return Case(label,f,setup,receiver=lambda t:t['r'],arguments=args)


def cases(random_source):
    for direction in (2,3):
        for flip in (0,2):
            for mode in range(8):
                for rv in ((24,25,49,50) if mode<2 else (73,)):
                    yield case(f'home d{direction} f{flip} m{mode} rand{rv}',0x48a2e0,rand=(rv,),direction=direction,flip=flip,mode=mode)
    for tick,old,interval in ((1099,100,1000),(1100,100,1000),(0,0xffffffff,1),(0x7fffffff,0,0x80000000)):
        def clock(e,t,tick=tick,old=old,interval=interval): e.put(0x537210,tick); e.put(t['r']+0x490,old,interval)
        yield case(f'home clock {tick:x}/{old:x}/{interval:x}',0x48a2e0,clock)
    for rv in (-1001,-1,0,24,25,75,76,100,101,0x7fffffff):
        yield case(f'home setup random {rv}',0x48a240,rand=(rv,rv))
    for direction in (2,3):
        for flip in (0,2):
            for early in (False,True):
                def conf(e,t,early=early):
                    e.put(t['r']+0x50,0x345678,0x99999999); e.put(t['r']+0x470,100,1001 if early else 1000); e.put(t['r']+0x4a8,7,9)
                yield case(f'sing setup d{direction} f{flip} early{early}',0x48a420,conf,direction=direction,flip=flip)
    for flag in (0,1,2,0x100,0x101,0xff):
        def destroy(e,t):
            for off,refs in ((0x1a4,2),(0x1a8,1)):
                h=e.object(20,'string-storage',words=[refs,7,7,0x61626364,0]); e.put(t['r']+off,h+12)
            e.put(t['r']+0x2fc,33); e.put(t['r']+0x300,e.object(8,'bitset',words=[0xa12345,0x98765]))
        yield case(f'delete {flag:x}',0x48a0d0,destroy,args=(flag,))
    def empty_destroy(e,t): e.put(t['r']+0x1a4,0x52e1d4,0x52e1d4); e.put(t['r']+0x2fc,32)
    yield case('direct destructor',0x48a0f0,empty_destroy)
    for _ in range(8):
        fill=random_source.randrange(1,0x100000)
        yield case(f'lifted {fill}',0x48a7d0,lambda e,t,fill=fill:e.put(t['r']+0x410,fill))
    for game,active,face,px,mode,chance,rv,count,elapsed in (
        (11,1,0,211,3,90,1,2,500),(12,0,0,211,3,90,1,2,500),(12,1,1,211,3,90,1,2,500),
        (12,1,0,11,3,90,1,2,500),(12,1,1,11,2,90,1,2,500),(12,1,1,11,3,90,1,2,499),
        (12,1,0,211,3,90,90,2,500),(12,1,0,211,4,90,89,2,500),(12,1,1,11,3,29,-1,1,500),
        (12,1,0,211,3,30,0,3,500),(12,1,0,211,3,0x80000000,0x80000000,2,500),(12,1,0,211,3,31,30,2,500)):
        def notify(e,t,game=game,active=active,face=face,px=px,mode=mode,chance=chance,count=count,elapsed=elapsed):
            e.put(0x537964,game); e.put(t['facing'],face,active); e.put(t['player']+0x4c,px)
            e.put(t['r']+0x184,mode); e.put(t['r']+0x20,count); e.put(t['r']+0x488,1100-elapsed,500); e.put(t['r']+0x4a4,chance)
            e.put(t['a']+8,0x10)
            obj=e.object(0x200,'support',fill=0); ctl=e.object(0x40,'support-control',fill=0)
            e.put(t['a']+0x80,obj); e.put(obj+0x164,0x8000); e.put(obj+0x6c,ctl); e.put(ctl+0x1c,5)
        yield case(f'notify {game}/{active}/{face}/{px}/{mode}/{chance}/{rv}/{count}/{elapsed}',0x48a160,notify,args=(0x52720c,),rand=(rv,))
    for key in (-2,0,1,2,4):
        for selected in (False,True):
            def dispatch(e,t,key=key,selected=selected):
                data=e.object(12,'dispatch-table',fill=0)
                def cb(e,call): e.put(t['log'],call.receiver,e.get(0x53c318)); return 7
                if selected and 0<=key<=2: e.put(data+key*4,e.stub('dispatch-target','thiscall',0,cb))
                e.put(0x53c300,0,2,data,0,4,0,0x8888)
                fallback=e.object(28,'fallback-dispatch',fill=0)
                for i in range(7): e.put(fallback+i*4,e.stub('base-target','thiscall',0,cb))
                e.put(0x537880,-2,4,fallback,0,4)
            yield case(f'dispatch {key}/{selected}',0x489850,dispatch,args=(key,))
    for present in (False,True):
        for scale in (0.5,1.0,2.0):
            def construct(e,t,present=present,scale=scale):
                e.write(t['r'],bytes([0x69])*0x4b0)
                alternate=e.object(0x100,'alternate-world',fill=0); other=e.object(0x100,'alternate-animation-manager',fill=0)
                e.put(alternate+0x2c,other); hash_map(e,other+0x10); e.put(t['c']+0xc,alternate)
                image=e.object(0x6c,'image-group',fill=0); frame=e.object(0x28,'image-frame',fill=0); frames=e.object(4,'image-frames',words=[frame])
                e.put(image+0x14,frames); e.put(image+0x64,0,0); e.put(frame+0x18,19,23,31,37)
                hash_map(e,t['managers'][0]+0x10,[('LEVEL_SIREN',image)])
                e.write(0x5262b8,struct.pack('<f',scale)); e.write(0x5262b4,struct.pack('<f',1.25)); e.write(0x5262b0,struct.pack('<f',0.75))
                if present:
                    animation=e.object(0x20,'animation',fill=0); event=e.object(0x30,'animation-event',fill=0); seq=e.object(4,'animation-sequence',words=[event])
                    e.put(animation+0xc,seq,1); e.put(event+0x1c,0x12345)
                    names=('LEVEL_SIREN_IDLE','LEVEL_SIREN_ADVANCE','LEVEL_SIREN_FASTADVANCE','LEVEL_SIREN_HITHIGH','LEVEL_SIREN_HITLOW','LEVEL_SIREN_JUMP','LEVEL_SIREN_KILLFALL','LEVEL_SIREN_LIFTED1','LEVEL_SIREN_LIFTED2','LEVEL_SIREN_STRIKE1','LEVEL_SIREN_THROWN','GAME_NULL')
                    pairs=[]
                    for i,n in enumerate(names):
                        anim=e.object(0x20,'named-animation',fill=0); event=e.object(0x30,'named-event',fill=0); seq=e.object(4,'named-sequence',words=[event])
                        e.put(anim+0xc,seq,1); e.put(event+0x1c,0x12345+i*77); pairs.append((n,anim))
                    hash_map(e,t['managers'][3]+0x10,pairs)
                sound_names=('LEVEL_SIREN_SIRENCALL','LEVEL_SIREN_00980001','LEVEL_SIREN_00460005','LEVEL_SIREN_00460006','LEVEL_SIREN_00460007','LEVEL_SIREN_00460010','LEVEL_SIREN_00980003','LEVEL_SIREN_00980002')
                hash_map(e,t['managers'][2]+0x10,[(n,0x10001+i*0x101) for i,n in enumerate(sound_names)])
            yield case(f'constructor {present}/{scale}',0x489c50,construct,args=(lambda t:t['a'],))
    for frame in (201,202):
        for started in (0,1):
            for count in (3,4):
                def singing(e,t,frame=frame,started=started,count=count):
                    e.put(t['a']+0x16c,frame); e.put(t['r']+0x4ac,started); e.put(t['r']+0x4a8,count)
                    e.put(t['r']+0x480,100,2000); e.put(t['r']+0x478,100,1001)
                yield case(f'singing {frame}/{started}/{count}',0x48a590,singing)
    # The class definition provides the externally supplied actor initialization callback.
    for velocity in (-200,0,200):
        for count in (-1,3,4,0x7fffffff,0x80000000):
            for flipped in (0,2):
                for sentinel in (0,1,2,3):
                    def projectile(e,t,velocity=velocity,flipped=flipped,sentinel=sentinel,count=count):
                        r=t['r']; e.put(r+0x4ac,1); e.put(r+0x4a8,count)
                        e.put(r+0x480,100,1000); e.put(r+0x478,100,1000); e.put(r+0x4a0,velocity)
                        manager=e.object(0x80,'creation-manager',fill=0); e.put(manager+0xc,t['w']); e.put(manager+0x28,10); e.put(t['w']+8,manager)
                        definition=e.object(0x14,'class-definition',fill=0)
                        e.put(definition+8,0x1234)
                        def init(e,call):
                            created=call.arguments[0]; controller=e.get(created+0x6c)
                            logic=e.object(0x150,'projectile-logic',fill=0); animation=e.object(0x150,'projectile-animation',fill=0)
                            e.put(controller+0x18,logic); e.put(logic+0x12c,animation)
                            e.put(logic+0x40,0x1234,0x4567); e.put(logic+0x58,0x6789,0xabcde)
                            e.put(logic+0x138,-17,29,53,67); e.put(animation+0x40,0xa500|flipped)
                            e.put(animation+0x118,0x80000000 if sentinel&1 else -9,31,47,59)
                            e.put(animation+0x128,0x80000000 if sentinel&2 else -19,41,71,83)
                            e.put(animation+0x138,-37,43,97,101)
                            e.put(t['log']+0x80,created,controller,e.get(r+0x4a8),e.get(created+0x104),e.get(created+0xd0))
                            return 0x9977
                        e.put(definition+0x10,e.stub('projectile-initialization','cdecl',1,init))
                        hash_map(e,t['managers'][1]+0x10,[('SirenBullet',definition)])
                    yield case(f'projectile velocity{velocity} flip{flipped} sentinel{sentinel} count{count}',0x48a590,projectile)
    for duration in (999,1000,1001):
        for frame in (201,202):
            def sound(e,t,duration=duration,frame=frame):
                e.put(0x532c0c,0)
                h=e.object(0x20,'sound-handle',fill=0); data=e.object(0x30,'sound-data',fill=0)
                e.put(h+0x10,data); e.put(data+0x28,duration); e.put(t['r']+0x450,h)
                e.put(t['r']+0x4a8,4); e.put(t['a']+0x16c,frame)
                e.put(t['r']+0x4ac,0 if frame==202 else 1)
                e.put(t['r']+0x478,100,duration)
            yield case(f'sound duration{duration} frame{frame}',0x48a590,sound)
