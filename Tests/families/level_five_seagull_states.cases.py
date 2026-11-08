"""Seagull state cases derived only from original instruction packets."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns

def f64(env, address, value):
    env.write(address, struct.pack('<d', value))

def words(value):
    return struct.unpack('<II', struct.pack('<d', value))

def setup_actor(options):
    def setup(env):
        o = options
        if 'x87_status' in o:
            env.entry_x87_status(o['x87_status'])
        actor = env.object(0x480, 'seagull', fill=o.get('fill', 0x35))
        body = env.object(0x220, 'body', fill=0)
        logic = env.object(0x160, 'logic', fill=0x49)
        state = env.object(0x30, 'state', fill=0)
        player = env.object(0x180, 'player', fill=0)
        vtable = env.object(0x80, 'seagull methods')
        log = env.object(0x40, 'callback publication')
        def callback(env, call):
            env.put(log, call.receiver, env.get(call.receiver+0x50), env.get(call.receiver+0x54),
                    env.get(call.receiver+0x70), env.get(call.receiver+0x74),env.get(call.receiver+0x134))
            env.write(log+24,env.read(call.receiver+0x58,16))
            env.put(log+40,env.get(state+0x1c),env.get(body+8),env.get(body+0x40))
            if o.get('callback_changes_velocity'):
                f64(env,call.receiver+0x50,-71.25)
                f64(env,call.receiver+0x70,913.5)
            return 0x18273645
        cb = env.stub('state transition', 'thiscall', 0, callback)
        env.put(vtable+0x48, cb)
        env.put(vtable+0x58, 0x487b80 if o.get('real_strike') else cb)
        env.put(actor, vtable)
        env.put(actor+0xc, logic, state)
        env.put(actor+0x12c, body)
        env.put(state+0x1c, o.get('state_id', 13))
        env.put(actor+0x24, o.get('previous_state', 7))
        env.put(actor+0x134, o.get('prior_plan', 0))
        env.put(body+8, o.get('flags', 0x4220))
        env.put(body+0x38, o.get('frame', 0))
        env.put(body+0x40, o.get('flip', 0))
        for offset in (0x118, 0x128, 0x138):
            env.put(body+offset, 17+offset, -51-offset, 89+offset, 133+offset)
        env.put(logic+8, 0x1280)
        env.put(logic+0x64, o.get('logic_code', 0x1234))
        env.put(actor+0x18c, o.get('direction', 2))
        env.put(actor+0x3c4, o.get('cooldown', 0))
        env.put(actor+0x138, 19, 23, -41, 53)
        env.put(actor+0x210, *o.get('rectangles',(101,102,103,104,201,202,203,204)))
        env.put(actor+0x408, 0)
        env.put(actor+0x418, 0, 0, 0, 0, 0)
        env.put(actor+0x428, 0, 0, 0)
        env.put(actor+0x434, o.get('home_y', 300), o.get('strike_y', 400))
        env.put(actor+0x38c, 0)
        env.put(actor+0x2fc, o.get('bits_count', 5))
        if o.get('bits_count',5)>32:
            bits=env.object(16,'bitset words',words=[o.get('bits',0x2468),0x33335555,0x44446666,0x77779999])
            env.put(actor+0x300,bits)
        else:
            env.put(actor+0x300,o.get('bits',0x2468))
        # The dead state's drop routine sees a valid empty inventory.
        env.put(actor+0x14c,0,0)
        for offset,value in ((0x38,o.get('ax',0.0)),(0x40,o.get('ay',0.0)),(0x48,o.get('az',0.0)),
                             (0x50,o.get('vx',10.0)),(0x58,o.get('vy',17.25)),(0x60,o.get('vz',-9.5)),
                             (0x68,o.get('x',500.0)),(0x70,o.get('y',100.0)),(0x78,o.get('z',0.0)),
                             (0x80,o.get('left',0.0)),(0x98,o.get('right',1000.0))):
            f64(env,actor+offset,value)
        env.put(player+0x4c,o.get('px',800),o.get('py',250))
        env.put(0x537e88,player)
        env.put(0x5430c4,o.get('dt',0))
        # Freeze the real animation at its current frame, except selected end states.
        plan = env.object(0x20,'animation plan')
        frame = env.object(0x34,'animation frame')
        entries = env.object(4,'animation entries',words=[frame])
        env.put(plan+0xc, entries,1)
        env.put(frame+0x1c,0x1badbeef)
        env.put(body+0x188+4,body,plan,frame,0,o.get('timer',1000),1,o.get('ended',0),11,12,0x3f800000)
        if o.get('scaled_animation'):
            # Original advance scales a frame's duration before __ftol.
            env.put(frame+0xc,9)
            env.put(frame+0x18,3)
            env.put(body+0x188+0x28,0x3f000000)
        if o.get('prior_plan_valid'):
            env.put(actor+0x134,plan)
        if o.get('new_plans'):
            for offset in (0x408,0x418,0x41c,0x420,0x428):
                p=env.object(0x20,'new animation')
                f=env.object(0x34,'new frame')
                e=env.object(4,'new entries',words=[f])
                env.put(p+0xc,e,1)
                env.put(f+0x1c,offset*197)
                env.put(actor+offset,p)
        # A real one-node Patricia dictionary, yielding nonzero state IDs.
        name=o.get('lookup','LS_STRIKE')
        key=env.object(len(name)+1,'dictionary key',data=name.encode()+b'\0')
        node=env.object(20,'dictionary node')
        env.put(node,node,node,0,key,o.get('lookup_value',29))
        env.put(0x537668+0x18,node)
        env.put(0x532c0c,o.get('sound_enabled',0))
        env.put(0x532c10,0x50)
        if o.get('sound'):
            sound=env.object(0x20,'sound')
            channel=env.object(0x50,'channel',fill=0)
            device=env.object(0x80,'sound device',fill=0)
            env.put(sound+0x10,channel)
            env.put(channel+0x10,device)
            for off in (0x430,0x42c,0x38c):
                env.put(actor+off,sound)
            if o.get('active_sound'):
                voice=env.object(0x40,'sound voice',fill=0)
                interface=env.object(4,'DirectSound buffer')
                methods=env.object(0x50,'DirectSound methods',fill=0)
                env.put(device+0x78,1)
                env.put(channel+0x30,voice+4,voice+4)
                env.put(voice+0xc,interface,device,0x101,22050)
                env.put(voice+0x30,1)
                env.put(interface,methods)
                def status(env,call):
                    env.put(call.arguments[1],0)
                    return 0
                env.put(methods+0x24,env.stub('GetStatus','stdcall',2,status))
                for offset in (0x3c,0x40,0x44):
                    env.put(methods+offset,env.stub(f'sound setter {offset:x}','stdcall',2,returns(0)))
                env.put(methods+0x30,env.stub('Play','stdcall',4,returns(0)))
            if o.get('drop_sound'):
                env.put(actor+0x148,sound,0,1)
        f64(env,0x50f548,o.get('speed',10.0))
        f64(env,0x50f550,o.get('patrol_speed',30.0))
        env.override(0x4a3050,returns(o.get('rand',49)))
        if o.get('rand_changes_animation'):
            def choose_after_callback(env,call):
                # The RNG callback changes fields read after the random draw.
                env.put(actor+0x41c,env.get(actor+0x408))
                env.put(actor+0x420,env.get(actor+0x428))
                env.put(body+0x190,env.get(actor+0x418))
                return o.get('rand',49)
            env.override(0x4a3050,choose_after_callback)
        if o.get('table'):
            text=env.object(32,'CString text',words=[1,7,19],data=None)
            env.write(text+12,b'RESTORE\0')
            slots=env.object(16,'state table slots',words=[text+12,text+12,text+12,text+12])
            env.put(0x537698+8,6,9,slots,slots,4,0,0,0)
            env.put(actor+0x24,o.get('table_index',7))
        return {'actor':actor,'body':body,'logic':logic,'state':state}
    return setup

def actor_case(label,fn,**options):
    return Case(label,fn,setup_actor(options),receiver=lambda t:t['actor'],arguments=(0x99887766,) if fn==0x488550 else ())

def cases(random_source):
    # Patrol flips and the full attack predicate, each short-circuit independently.
    for x in (0.0,500.0,1000.0):
        for flip in (0,2):
            yield actor_case(f'patrol endpoint {x} flip {flip}',0x4879a0,x=x,flip=flip,fill=random_source.randrange(1,255))
    base=dict(x=500.0,y=100.0,left=0.0,right=1000.0,px=800,py=250,vx=10.0,direction=2)
    variants=[{}, {'cooldown':-1},{'cooldown':999},{'cooldown':1000},{'px':0},{'px':1000},
              {'y':250.0},{'py':200},{'py':201},{'py':339},{'py':340},{'px':650},
              {'px':649},{'vx':-10.0,'direction':3},{'vx':-10.0,'direction':2},
              {'vx':10.0,'direction':3},{'vx':0.0},{'px':200},{'px':501},{'px':-800}]
    for i,v in enumerate(variants):
        yield actor_case(f'patrol predicate {i}',0x4879a0,**(base|v))
    # Inherited masked exceptions survive patrol comparisons and conversions.
    # Duplicate fixed branch witnesses, independent of the unseen random seed.
    for status in (0x20,0x21,0x3f):
        for i,v in enumerate(variants):
            yield actor_case(f'patrol inherited SW {status:x} predicate {i}',
                             0x4879a0,x87_status=status,**(base|v))
        for x in (0.0,1000.0):
            for flip in (0,2):
                yield actor_case(f'patrol inherited SW {status:x} endpoint {x} flip {flip}',
                                 0x4879a0,x87_status=status,x=x,flip=flip)
        for x,left,right in ((137.25,137.25,807.75),(807.75,137.25,807.75),
                             (137.25,137.25,137.25)):
            yield actor_case(f'patrol inherited SW {status:x} fractional {x} {right}',
                             0x4879a0,x87_status=status,x=x,left=left,right=right,
                             patrol_speed=37.125,cooldown=1000)
    # Exercise the real animation callee's x87 scaling path, not just its frozen exit.
    for status in (0,0x20,0x21,0x3f):
        yield actor_case(f'patrol inherited SW {status:x} scaled animation',0x4879a0,
                         x87_status=status,scaled_animation=True,timer=0,cooldown=1000)
    # The registered patrol invokes its real strike method when its full
    # predicate succeeds. Keep callback fixtures above as separate observations.
    for status in (0,0x20,0x21,0x3f):
        for accel in (0.0,2.0):
            for direction in (2,3):
                for audible in (False,True):
                    yield actor_case(f'patrol real strike SW {status:x} accel {accel} direction {direction} sound {audible}',
                                     0x4879a0,x87_status=status,real_strike=True,
                                     new_plans=True,lookup='LS_STRIKE',
                                     vx=10.0 if direction==2 else -10.0,
                                     direction=direction,speed=1000.0,
                                     ax=accel,ay=accel,az=accel,
                                     sound=audible,active_sound=audible,
                                     sound_enabled=int(audible))
    for direction in (2,3):
        for y in (299.0,300.0,301.0):
            yield actor_case(f'withdraw update {direction} y {y}',0x488330,direction=direction,y=y)
    for r in (-1,0,49,50,99,100,149,150,0x7fffffff):
        for sound in (False,True):
            yield actor_case(f'hit rand {r} sound {sound}',0x488390,rand=r,sound=sound,sound_enabled=int(sound),lookup='LS_GENERICHIT',new_plans=True)
    for frame in (-1,0):
        for sound,enable in ((False,0),(True,0),(True,1)):
            yield actor_case(f'dead update {frame} {sound} {enable}',0x488750,frame=frame,sound=sound,sound_enabled=enable)
    for count in (0,1,4,5,32,33,64):
        for bits in (0x2468,0x2479):
            for direction in (2,3):
                yield actor_case(f'death bitset {count} {bits} {direction}',0x488550,bits_count=count,bits=bits,direction=direction,new_plans=True,lookup='LS_DEAD',logic_code=0x2134 if bits&1 else 0x1234)
    for fn in (0x487b80,0x487f80):
        for flip in (0,2):
            for vx in (-10.0,10.0):
                for speed in (-10.0,0.0,10.0,1000.0):
                    for accel in (0.0,2.0,1000.0):
                        yield actor_case(f'ballistic {fn:x} {flip} {vx} {speed} {accel}',fn,flip=flip,vx=vx,speed=speed,ax=accel,ay=accel,az=accel,new_plans=True,lookup='LS_WITHDRAW' if fn==0x487f80 else 'LS_STRIKE')
    yield actor_case('strike sound enabled',0x487b80,sound=True,sound_enabled=1,new_plans=True)
    for opts in ({},{'y':401.0},{'x':0.0},{'x':1000.0}):
        yield actor_case(f'strike update {opts}',0x487f20,**opts,lookup='LS_WITHDRAW',new_plans=True)
    for ended,timer in ((0,1000),(1,1000),(1,0)):
        yield actor_case(f'hit completion {ended} {timer}',0x488420,ended=ended,timer=timer,table=True,prior_plan_valid=True)
    # Real MFC grow success initializes newly introduced CString slots.
    for index in (5,10):
        yield actor_case(f'hit completion grows {index}',0x488420,ended=1,timer=0,table=True,table_index=index,prior_plan_valid=True)
    # Error reporter's own body is observable through a real error-policy object.
    for code in (0,1,0x12345678,0xffffffff):
        def setup(env,code=code):
            reporter=env.object(16,'reporter')
            policy=env.object(32,'error policy')
            message=env.object(9,'message',data=b'seagull\0')
            env.put(reporter+4,policy)
            env.put(policy+8,0x76543210,4)
            return dict(receiver=reporter,message=message)
        yield Case(f'report {code:x}',0x406da0,setup,receiver=lambda t:t['receiver'],arguments=(lambda t:t['message'],code))
    # General ballistic solver: directions, cancellation, infeasible and degenerate roots.
    for speed in (-10.0,0.0,0.00000001,1.0,10.0,100.0):
        for accel in ((0.0,0.0,0.0),(2.0,3.0,4.0),(0.0,-10.0,0.0)):
            for sign in (-1,1):
                def setup(env,speed=speed,accel=accel,sign=sign):
                    obj=env.object(0x70,'trajectory',fill=0x57)
                    for offset,value in zip((0x10,0x18,0x20),accel): f64(env,obj+offset,value)
                    for offset,value in zip((0x40,0x48,0x50),(10.0,20.0,30.0)): f64(env,obj+offset,value)
                    return dict(obj=obj)
                args=(*words(speed),*words(80.0),*words(40.0),*words(-15.0),sign)
                yield Case(f'solver speed {speed} accel {accel} root {sign}',0x467ea0,setup,receiver=lambda t:t['obj'],arguments=args)

    for fn in (0x487b80,0x487f80):
        for speed in (10.0,100.0):
            yield actor_case(f'tangent ballistic {fn:x} {speed}',fn,vx=-10.0,speed=speed,ax=0.0,ay=-10.0,az=0.0,x=500.0,left=510.0,right=600.0,y=100.0,home_y=100,px=510,py=140,new_plans=True)
    def tangent(env):
        obj=env.object(0x70,'tangent solver',fill=0x73)
        for offset,value in ((0x10,0.0),(0x18,-10.0),(0x20,0.0),(0x40,0.0),(0x48,0.0),(0x50,0.0)):
            f64(env,obj+offset,value)
        return {'obj':obj}
    yield Case('solver tangent',0x467ea0,tangent,receiver=lambda t:t['obj'],arguments=(*words(10.0),*words(10.0),*words(0.0),*words(0.0),1))

    for code in (7,0x12345678):
        def report_callback(env):
            reporter=env.object(16,'callback reporter',fill=0x51)
            policy=env.object(32,'callback policy',fill=0)
            message=env.object(9,'callback message',data=b'seagull\0')
            prefix=env.object(8,'error prefix',data=b'prefix:\0')
            log=env.object(96,'reported error',fill=0)
            def callback(env,call):
                env.put(log,call.arguments[1])
                env.write(log+4,env.cstr(call.arguments[0])+b'\0')
                return 0x76543210
            env.put(policy,env.stub('error callback','cdecl',2,callback))
            env.put(policy+0xc,2)
            env.put(policy+0x14,prefix)
            env.put(reporter+4,policy)
            env.put(0x544d18,0)
            return dict(reporter=reporter,message=message)
        yield Case(f'report callback {code:x}',0x406da0,report_callback,receiver=lambda t:t['reporter'],arguments=(lambda t:t['message'],code))
    for fn,name in ((0x487b80,'LS_STRIKE'),(0x488390,'LS_GENERICHIT'),(0x488750,'LS_DEAD')):
        yield actor_case(f'sound globally disabled {fn:x}',fn,sound=True,sound_enabled=0,new_plans=True,lookup=name,frame=-1)

    for fn in (0x4879a0,0x488330):
        yield actor_case(f'transition callback changes fields {fn:x}',fn,
                         callback_changes_velocity=True)
    for draw in (49,50):
        yield actor_case(f'random callback changes animation {draw}',0x488390,
                         rand=draw,rand_changes_animation=True,new_plans=True,
                         lookup='LS_GENERICHIT')
    # Fixed branch witnesses above remain unchanged across seeds. Vary distinct
    # copy sources and 3D geometry independently to expose offsets and widths.
    for i in range(24):
        for fn in (0x487b80,0x487f80):
            rectangle=tuple(random_source.randrange(1,1000000) * (-1 if j%3==0 else 1)
                            for j in range(8))
            yield actor_case(f'seeded geometry {i} {fn:x}',fn,
                             rectangles=rectangle,new_plans=True,flip=2*(i%2),
                             vx=-17.5 if i%2 else 23.25,
                             ax=random_source.randrange(-8,9)/4,
                             ay=random_source.randrange(-8,9)/4,
                             az=random_source.randrange(-8,9)/4,
                             x=random_source.randrange(200,800)/2,
                             y=random_source.randrange(-100,300)/2,
                             z=random_source.randrange(-200,200)/2,
                             speed=random_source.randrange(50,500)/4,
                             px=random_source.randrange(-500,1500),
                             py=random_source.randrange(200,800),
                             state_id=random_source.randrange(1,1000),
                             lookup_value=random_source.randrange(1001,2000),
                             lookup='LS_STRIKE' if fn==0x487b80 else 'LS_WITHDRAW')

    for index in (6,9):
        yield actor_case(f'restore table exact bound {index}',0x488420,
                         ended=1,timer=0,table=True,table_index=index,prior_plan_valid=True)
    for fn in (0x487b80,0x488390,0x488750):
        yield actor_case(f'observable sound {fn:x}',fn,sound=True,active_sound=True,
                         sound_enabled=1,new_plans=True,frame=-1,
                         lookup={0x487b80:'LS_STRIKE',0x488390:'LS_GENERICHIT',0x488750:'LS_DEAD'}[fn])
    for bits in (0x2468,0x2478):
        yield actor_case(f'death bit4 controls audible drop {bits:x}',0x488550,
                         bits=bits,sound=True,active_sound=True,drop_sound=True,
                         sound_enabled=1,new_plans=True,lookup='LS_DEAD',
                         ax=3.25,ay=-4.75,az=8.125,vx=9.375,vy=-15.625,vz=11.875)
    for x,left,right in ((137.25,137.25,807.75),(807.75,137.25,807.75),
                         (137.25,137.25,137.25)):
        for flip in (0x100,0x102):
            yield actor_case(f'fractional endpoint {x} {left} {right} {flip}',0x4879a0,
                             x=x,left=left,right=right,flip=flip,patrol_speed=37.125,
                             cooldown=1000)
