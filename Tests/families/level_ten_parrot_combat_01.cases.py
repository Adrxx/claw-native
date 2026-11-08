"""Independent parrot combat inputs derived from the original branches."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence

FUNCTIONS = (0x466790,0x466a80,0x466e40,0x466ea0,0x467280,0x4672d0,0x467470,0x467530,0x467700,0x4677b0,0x4679a0)

def setup_case(options, salt):
    def setup(env):
        if 'x87_status' in options:
            env.entry_x87_status(options['x87_status'])
        o = env.object(0x500,'parrot')
        sprite = env.object(0x240,'parrot-sprite')
        actor = env.object(0x180,'parrot-actor')
        state = env.object(0x40,'parrot-state')
        marrow = env.object(0x520,'marrow')
        ms = env.object(0x240,'marrow-sprite')
        ma = env.object(0x180,'marrow-actor')
        view = env.object(0x100,'view')
        mt = env.object(0x80,'marrow-vtable')
        ot = env.object(0x80,'parrot-vtable')
        record = env.object(0x100,'callback-observations')
        anim = env.object(0x20,'animation')
        frames = env.object(4,'animation-frames')
        frame = env.object(0x30,'animation-frame')
        sound = env.object(0x20,'sound-wrapper')
        soundplay = env.object(0x30,'sound-play')
        soundbackend = env.object(0x90,'sound-backend')
        carry = env.object(0x180,'carried-object')
        carryowner = env.object(0x40,'carried-owner')
        collision = env.object(0x80,'collision-world')
        manager = env.object(0x200,'sound-manager')
        managerstate = env.object(0x30,'sound-manager-state')
        def callback(env, call):
            count=env.get(record)
            at=record+4+(count%6)*32
            env.put(at,call.receiver,env.get(o+0x40),env.get(o+0x44),env.get(marrow+0x20),env.get(marrow+0x4b8),env.get(marrow+0x4c0))
            env.put(record,count+1)
            if options.get('callback_mutate'):
                env.put(o+0x134,0x76543210)
            return salt
        for off in (0x44,0x48,0x58):
            env.put(ot+off,env.stub('parrot callback '+hex(off),'thiscall',0,callback))
            env.put(mt+off,env.stub('marrow callback '+hex(off),'thiscall',0,callback))
        env.put(o,ot)
        env.put(o+0xc,actor,state)
        env.put(o+0x128,carry,sprite)
        env.put(marrow,mt)
        env.put(marrow+0xc,ma)
        env.put(marrow+0x128,carry,ms)
        env.put(carry+0xc,carryowner)
        env.put(carryowner+0x24,collision)
        env.put(carry+0x118,0x80000000)
        env.put(actor+0x10c,0x13572468 ^ salt)
        env.put(ma+0x10c,0x31415926 ^ salt)
        env.put(state+0x1c,0x24681357 ^ salt)
        env.put(o+0x134,0x11771177 ^ salt)
        env.put(o+0x138,-13 & 0xffffffff,17,29,31)
        env.put(o+0x210,-21 & 0xffffffff,23,37,41, -43 & 0xffffffff,47,53,59)
        for s in (sprite,ms):
            env.put(s+8,0xf3a5)
            env.put(s+0x40,0x5a0 | options.get('flip',0))
            env.put(s+0x50,231)
            env.put(s+0x118,options.get('sentinel',-71)&0xffffffff,73,83)
            env.put(s+0x128,options.get('sentinel2',-89)&0xffffffff,97,101)
            env.put(s+0x138,-103 & 0xffffffff,107,109)
            env.put(s+0x18c,s)
            env.put(s+0x190,anim if options.get('active_countdown') else 0)
            env.put(s+0x19c,options.get('delay',0))
            env.put(s+0x1a0,options.get('timed',0))
            env.put(s+0x1a4,options.get('finished',0))
        env.put(anim+0xc,frames,1)
        env.put(frames,frame)
        env.put(frame+0x1c,0x55aa33cc ^ salt)
        env.put(o+0x408,anim)
        env.put(o+0x410,anim)
        env.put(o+0x18c,options.get('direction',2))
        env.put(o+0x400,options.get('last',1100),options.get('wait',20))
        env.put(o+0x420,0x1230,0x5670,0x9ab0)
        env.put(o+0x434,options.get('ix',120),options.get('iy',90))
        env.put(o+0x41c,sound if options.get('sound',0) else 0)
        env.put(sound+0x10,soundplay)
        env.put(soundplay+0x10,soundbackend)
        env.put(soundbackend+0x78,0)
        env.put(view+0x4c,options.get('viewx',0x9f68),options.get('viewy',150))
        env.put(marrow+0x484,0x11112222 ^ salt)
        env.put(marrow+0x4b8,0x99)
        env.put(marrow+0x4c0,0x88)
        env.put(marrow+0x4d0,options.get('marrowdx',13))
        env.put(0x537e88,view)
        env.put(0x537b14,marrow if options.get('have_marrow',1) else 0)
        env.put(0x53c9c0,options.get('mode',2))
        env.put(0x537210,options.get('now',1200))
        env.put(0x5430c4,7)
        env.put(0x537668+0x18,0)
        env.put(0x532c0c,options.get('sound_enabled',0))
        env.put(0x532c10,0x10203)
        env.put(0x53c9ac,manager)
        env.put(0x53c9a8,0)
        env.put(manager+0x6c,managerstate)
        def double(a,x):env.write(a,struct.pack('<d',x))
        defaults={0x38:0.,0x40:0.,0x48:0.,0x50:1.5,0x58:-3.5,0x60:4.5,0x68:100.,0x70:80.,0x78:5.,0x80:10.,0x88:80.,0x98:200.,0x440:120.,0x448:100.}
        for off,x in defaults.items():double(o+off,options.get(off,x))
        double(marrow+0x68,options.get('marrowx',107.))
        double(marrow+0x70,options.get('marrowy',200.))
        for a,x in {0x50ebd8:options.get('speed',10.),0x50ebe0:options.get('flyspeed',3.),0x50ebf0:100.,0x50ebf8:0.,0x50ec00:5.,0x50ec08:-5.,0x50ec10:0.5,0x50ec18:4.,0x50ec28:0.5,0x50ec30:20.,0x50ec48:30.,0x513e20:options.get('epsilon',1e-8)}.items():double(a,x)
        env.override(0x4a3050,sequence(*options.get('random',(76,76,76,76))))
        return o
    return setup

def cases(random_source):
    n=0
    def make(f,label,**options):
        nonlocal n
        n+=1
        options.update(options.pop("values", {}))
        profile = options.pop('entry_x87', None)
        return Case(f'{f:x} {n} {label}',f,setup_case(options,random_source.randrange(1,0x10000)),receiver=lambda x:x,entry_x87=profile)
    for f in FUNCTIONS:
        yield make(f,'baseline')
    for f in (0x466790,0x467470,0x467700,0x4679a0):
        for finished,delay in ((0,0),(1,0),(1,3)):
            yield make(f,'animation completion',finished=finished,delay=delay)
    for f in (0x466e40,0x467280):
        for x in (10.,100.,200.):
            for y in (90.,100.,110.):
                yield make(f,'position trigger',values={0x68:x,0x70:y})
    for f in (0x467470,0x467700,0x4679a0):
        for velocity in (-2.,0.,2.):
            for x in (119.,120.,121.):
                yield make(f,'arrival',callback_mutate=1,values={0x50:velocity,0x68:x})
    for f in (0x4672d0,0x467530,0x4677b0):
        for flip in (0,2):
            for x in (50.,120.,41000.):
                for sentinel in (-71,0x80000000):
                    yield make(f,'orient and target',flip=flip,sentinel=sentinel,sentinel2=sentinel,viewx=0x9f67 if x==50. else 0x9f68,values={0x68:x})
    for direction in (1,2):
        for flip in (0,2):
            for x in (10.,50.,100.,200.):
                for vel in (0.,1.5):
                    yield make(0x466790,'flyabout boundary',direction=direction,flip=flip,values={0x68:x,0x50:vel})
    for rand in (0,1,74,75,-1,-101):
        for mode in (1,2):
            yield make(0x466790,'random signed and mode',random=(rand,rand,rand,rand),mode=mode,values={0x68:10.,0x70:81.})
    for now,wait in ((1200,100),(1199,100),(0,0xffffffff),(1100,0)):
        yield make(0x466790,'unsigned cooldown',now=now,wait=wait,random=(0,1,0,0))
    for f in (0x466a80,0x466ea0):
        for direction in (1,2):
            for flip in (0,2):
                for speed in (-2.,0.,10.):
                    yield make(f,'motion branches',direction=direction,flip=flip,speed=speed)
        for viewx in (0x9f67,0x9f68,0x9f69):
            for accel in ((1.,2.,3.),(-3.,1.,-2.),(0.,0.,0.)):
                yield make(f,'ballistic',viewx=viewx,values=dict(zip((0x38,0x40,0x48),accel)))
        for speed in (1.,2.,10.):
            for accel in ((10.,0.,0.),(0.,10.,0.),(0.,0.,10.)):
                yield make(f,'discriminant',speed=speed,values=dict(zip((0x38,0x40,0x48),accel)))
    for mode,have in ((1,1),(2,0)):
        yield make(0x466a80,'strike disabled',mode=mode,have_marrow=have)
    for sound,enabled in ((0,1),(1,0),(1,1)):
        yield make(0x466ea0,'optional sound',sound=sound,sound_enabled=enabled)
    for f in (0x466a80,0x466ea0):
        # A single acceleration aligned with the target gives exactly zero discriminant.
        yield make(f,'zero discriminant',speed=10.,viewx=110,viewy=80,values={0x38:-5.,0x40:0.,0x48:0.,0x68:100.,0x70:80.,0x78:0.,0x80:105.,0x98:115.,0x448:80.},random=(0,0))
    for x in (10.,200.):
        yield make(0x466790,'strike from flight',random=(0,0,0,0),values={0x68:x})
    for f in (0x466a80,0x466ea0):
        yield make(f,'positive discriminant',speed=10000.,values={0x38:1.,0x40:2.,0x48:3.})
        yield make(f,'discriminant zero clamp',speed=0.,epsilon=0.,viewx=100,viewy=80,random=(0,0),values={0x38:1.,0x40:0.,0x48:0.,0x68:100.,0x70:80.,0x78:0.,0x98:105.,0x448:80.})
        yield make(f,'near zero discriminant clamp',speed=0.0001,epsilon=1e-8,viewx=100,viewy=80,random=(0,0),values={0x38:1.,0x40:0.,0x48:0.,0x68:100.,0x70:80.,0x78:0.,0x98:105.,0x448:80.})
    for f in FUNCTIONS:
        for _ in range(3):
            values={off:random_source.uniform(-50.,50.) for off in (0x38,0x40,0x48,0x50,0x58,0x60,0x68,0x70,0x78,0x80,0x88,0x98,0x440,0x448)}
            yield make(f,'finite varied mantissas',flip=random_source.choice((0,2)),direction=random_source.choice((1,2)),values=values)
    for f in (0x466790,0x466e40,0x467280,0x467470,0x467700,0x4679a0):
        for off in (0x50,0x68,0x70,0x440,0x448):
            yield make(f,'unordered comparison',values={off:float('nan')})

    # All entries retain masked sticky flags through their real original callees.
    for f in FUNCTIONS:
        for status in (0,0x20,0x21):
            yield make(f,'inherited sticky flags',x87_status=status,
                       values={0x40:1.0/3.0,0x60:-2.0/7.0})
        # A real animation countdown makes dropping the update call observable.
        yield make(f,'observable animation update',active_countdown=1,delay=19,timed=1,
                   x87_status=0x20,values={0x40:2.0/3.0,0x60:5.0/7.0})
    for status in (0,0x20,0x21):
        for x in (10.,200.):
            for flip in (0,2):
                yield make(0x466790,'inherited strike from flight',x87_status=status,
                           flip=flip,random=(0,0,0,0),values={0x68:x,0x40:1.0/3.0,0x60:2.0/7.0})
        for f in (0x466a80,0x466ea0):
            yield make(f,'inherited ballistic positive discriminant',x87_status=status,
                       speed=10000.,values={0x38:1.,0x40:2.0/3.0,0x48:3.,0x60:5.0/7.0})
            yield make(f,'inherited discriminant zero clamp',x87_status=status,
                       speed=0.,epsilon=0.,viewx=100,viewy=80,random=(0,0),
                       values={0x38:1.,0x40:0.,0x48:0.,0x68:100.,0x70:80.,0x78:0.,0x98:105.,0x448:80.,0x60:5.0/7.0})
    # Nonzero low halves make the zero stores in arrival paths observable.
    for f in (0x467470,0x467700,0x4679a0):
        yield make(f,'arrival clears nonzero low word',values={0x40:1.0/3.0,0x50:2.,0x68:121.})
    # Zero-speed exits clear every word of all three velocities. Fractions have
    # nonzero low and high halves, unlike exactly representable half integers.
    for f in (0x466a80,0x466ea0):
        for status in (0,0x20,0x21):
            yield make(f,'zero speed clears every velocity word',speed=0.,x87_status=status,
                       values={0x50:1.0/3.0,0x58:-2.0/7.0,0x60:5.0/11.0})
    # Flight clears vertical velocity at its altitude and copies both words of
    # the configured horizontal speed on midpoint and endpoint transitions.
    for x in (10.,50.,100.,200.):
        for flip in (0,2):
            for velocity in (0.,1.0/3.0):
                yield make(0x466790,'fractional flight speed words',flyspeed=10.0/3.0,
                           flip=flip,random=(76,76,76,76),x87_status=0x21,
                           values={0x68:x,0x50:velocity,0x58:-2.0/7.0,0x60:5.0/11.0})

    # Inherited values are never operands: exact extended payloads, signed zeros,
    # subnormals and NaNs must survive the original's temporary stack unchanged.
    payloads = (
        (0x8000000000000001, 0x3fff),
        (0, 0x8000),
        (1, 0),
        (0x8000000000000000, 0x7fff),
        (0xc000000000001234, 0x7fff),
        (0x8000000000005678, 0xffff),
        (0xdeadbeef01234567, 0xc123),
        (0, 0),
    )
    controls = tuple(0x003f | pc | rc
                     for pc in (0, 0x200, 0x300)
                     for rc in (0, 0x400, 0x800, 0xc00))
    def profile(index, slots):
        return {'control': controls[index % 12],
                'status': (((index % 7) + 1) << 11) | (0x21, 0x4500, 0x3f, 0x0220)[index % 4],
                'slots': tuple(slots)}

    # The deterministic matrix covers all twelve CW precision/rounding settings
    # at every owned entry and nonzero physical TOP. The two unconditional
    # 0x420dd0 callers need all eight physical registers inside that callee.
    for f in FUNCTIONS:
        for i in range(12):
            slots = () if f in (0x4672d0, 0x4677b0) else (payloads[i % 8],)
            yield make(f, 'inherited CW matrix', entry_x87=profile(i, slots))

    # Real flight dispatches directly into the owned strike setup, retaining
    # the same environment over comparisons, sign changes and vector setup.
    for i in range(12):
        for x in (10., 200.):
            yield make(0x466790, 'live flight to strike setup',
                       entry_x87=profile(i, (payloads[(i + 3) % 8],)),
                       flip=i % 2 * 2, random=(0, 0, 0, 0),
                       flyspeed=10.0/3.0, values={0x68:x, 0x50:0.})
        # The original quadratic path uses all eight physical registers.
        # Exercise its non-default CW and TOP with no inherited live slot;
        # live L1 vector transport is exercised by the matrix and flight cases.
        for f in (0x466a80, 0x466ea0):
            yield make(f, 'quadratic inherited CW and TOP',
                       entry_x87=profile(i, ()), speed=10000.,
                       values={0x38:1., 0x40:2.0/3.0, 0x48:3.})
        # Carry dispatch reaches the same eight-temporary original 0x420dd0.
        yield make(0x467700, 'arrival to carry inherited CW and TOP',
                   entry_x87=profile(i, ()),
                   values={0x40:1.0/3.0, 0x50:2., 0x68:121.})

    # Vary depth independently from TOP on the short comparison/negation path.
    for top in range(8):
        for depth in (2, 4):
            inherited = {'control': controls[(top + depth) % 12],
                         'status': (top << 11) | 0x4721,
                         'slots': tuple(payloads[(top + j) % 8] for j in range(depth))}
            yield make(0x466790, 'multiple live slots physical TOP',
                       entry_x87=inherited, random=(76,76,76,76),
                       values={0x68:200., 0x50:0.}, flip=2)
        yield make(0x466e40, 'empty inherited physical TOP',
                   entry_x87={'control':controls[top], 'status':(top << 11) | 0x4520, 'slots':()})
