"""Original-backed constructor and nine-ring cases, independent branch matrix."""
import struct
from clawparity.cases import Case
from clawparity.world import world, resource_manager, animation, sprite
from clawparity.fixtures import returns


def dbl(env, address, value):
    env.write(address, struct.pack('<d', value))


def real_world(env, entropy, x=251, y=361, priority=17, hits=False):
    t = world(env, owner_words={0x4C:x, 0x50:y, 0x64:priority}, state_words={0x1C:37})
    env.put(t['state'] + 0xC, t['world'])
    env.put(t['state'] + 0x2C,19,35,51,67)
    env.put(t['owner'] + 0x148,123,-77)
    spawn = env.object(0x40, 'ring manager', fill=0)
    env.put(spawn + 0xC, t['world'])
    env.put(spawn + 0x28, 16)
    env.put(t['world'] + 8, spawn)
    definition = env.object(0x14, 'shield definition', fill=0)
    receipts = env.object(0x400, 'publication receipts', fill=0)
    def created(env, call):
        ring = call.arguments[0]
        index = env.get(receipts)
        env.put(receipts + 4 + 32 * index, ring, env.get(ring+8), env.get(ring+0x4C),
                env.get(ring+0x50), env.get(ring+0x64), env.get(t['state']+0x1C))
        env.put(receipts, index+1)
        return entropy
    env.put(definition + 0x10, env.stub('ring logic construction', 'cdecl', 1, created))
    env.put(t['world'] + 0x14, resource_manager(env, {'OmarShield':definition}, name='shield definitions'))
    alternate=env.object(0x40,'adjacent resource context',fill=0)
    env.put(alternate+8,spawn)
    for off in (0x10,0x14,0x28,0x2C):
        env.put(alternate+off,resource_manager(env,{},name='adjacent resources'))
    env.put(t['owner']+0x10,alternate)
    env.put(t['state']+0xC,alternate)
    if hits:
        names = ('LEVEL_OMAR_HITHIGH','LEVEL_OMAR_HITLOW','LEVEL_OMAR_IDLE','LEVEL_OMAR_KILLFALL',
                 'LEVEL_OMAR_KILLFALL3','LEVEL_OMAR_STRIKE1','LEVEL_OMAR_BLOCK','GAME_NULL')
        env.put(t['world']+0x2C, resource_manager(env, {k:animation(env,11+19*i) for i,k in enumerate(names)}, bucket_count=1))
        env.put(t['world']+0x10, resource_manager(env, {'LEVEL_OMAR':sprite(env,47,63,(3,-9))}))
    env.put(0x537668 + 0x18, 0)
    env.put(0x537E88, t['owner'])
    env.put(0x534EAC, 0x26B7)
    env.put(0x541334, 1)
    env.override(0x4A3050, returns(3))
    t.update(spawn=spawn, receipts=receipts)
    return t


def constructor(rng, hits, bitcount, priority, scale):
    entropy = rng.getrandbits(32)
    def setup(env):
        t = real_world(env, entropy, x=entropy%10000-5000, y=(entropy>>16)%10000-5000, priority=priority, hits=hits)
        obj=env.object(0xD48,'Omar constructor receiver',fill=0xA7)
        env.put(0x533470,bitcount)
        env.put(0x513E10,0x10203040,0x3FF12345,0x55667788,0xC000AABB)
        def rect(env, call):
            target,*coords=call.arguments
            env.put(target,*coords)
            # Observe publication and the original base-initialized scalar values.
            if target==obj+0x260 and tuple(coords)==(0xFFFFFFF5,0xFFFFFFD1,0x17,0x3D):
                offsets=(0,0x2FC,0x300,0x2B8,0x2C4,0x28C,0x298,0x2A0,0x80,0x54,0x4A8)
                env.put(t['receipts']+0x200,*(env.get(obj+off) for off in offsets))
            return 1
        env.override(0x546D5C,rect)
        env.write(0x5262B8,struct.pack('<f',scale))
        env.write(0x5262B4,struct.pack('<f',0.875))
        env.write(0x5262B0,struct.pack('<f',1.375))
        return dict(t,obj=obj)
    return setup


def rings(rng, mask, mutate=False, scale=1.0):
    entropy=rng.getrandbits(32)
    def setup(env):
        t=real_world(env,entropy,x=-12345,y=67890,priority=0x7FFFFFFF)
        obj=env.object(0xD48,'Omar ring creator',fill=0x9B)
        methods=env.object(0x50,'Omar methods',fill=0)
        env.put(obj,methods)
        env.put(obj+0xC,t['owner'])
        env.put(obj+0x12C,t['owner'],t['state'])
        env.put(t['owner']+8,0xA5A5FFFF)
        env.put(t['owner']+0x40,0x55AAFFFF)
        env.put(obj+0xD18,7,8,9)
        def position(env,call):
            env.put(t['receipts']+0x300,call.receiver,env.get(obj+0xD18),env.get(obj+0xD1C),env.get(obj+0xD20))
            if mutate:
                env.put(obj+0x128,t['owner'],t['owner'])
                env.put(t['owner']+0x4C,0x7FFFFFF0,0x80000010)
            return entropy
        env.put(methods+0x48,env.stub('Omar integer position','thiscall',0,position))
        for i in range(9):
            existing=env.object(0x70,'existing ring %d'%i,fill=i+31) if mask&(1<<i) else 0
            env.put(obj+0x484+i*4,existing)
        env.write(0x5262B4,struct.pack('<f',scale))
        return dict(t,obj=obj)
    return setup


def position(rng, active, mode, angle, x, y, radius):
    entropy=rng.getrandbits(32)
    def setup(env):
        t=real_world(env,entropy,x=x,y=y)
        obj=env.object(0xD48,'Omar live rings',fill=0)
        env.put(obj+0xC,t['owner'])
        env.put(obj+0x128,t['owner'],t['owner'])
        env.put(obj+0xD18,mode)
        env.put(t['owner']+8,0x10)
        dbl(env,obj+0x68,x+0.25)
        env.put(obj+0x2FC,32,entropy & ~0x200)
        for i in range(9):
            ring=env.object(0x80,'live ring %d'%i,fill=0x71+i)
            logic=env.object(0x30,'ring logic %d'%i,fill=0)
            shield=env.object(0x40,'shield state %d'%i,fill=0)
            wrapper=env.object(0x10,'shield wrapper %d'%i,fill=0)
            env.put(ring+0x6C,logic)
            env.put(logic+0x18,shield)
            env.put(shield+0xC,wrapper)
            env.put(wrapper+0xC,t['world'])
            env.put(shield+0x2C,t['owner'])
            env.put(obj+0x484+i*4,ring if active else 0)
            dbl(env,obj+0x4E8+i*0xF0,angle+i*33.125)
        env.write(0x50EAD0,struct.pack('<d',radius))
        return dict(t,obj=obj)
    return setup


def cases(random_source):
    for hits in (False,True):
        for bits in (0,10,32,64):
            for priority in (0x1005,17):
                for scale in (0.25,10.0):
                    yield Case(f'constructor hits={hits} bits={bits} priority={priority} scale={scale}',0x463460,
                        constructor(random_source,hits,bits,priority,scale),receiver=lambda t:t['obj'],arguments=(lambda t:t['owner'],))
    for mask in (0,0x1FF,1,0x100,0x155,0xAA):
        for scale in (0.0,0.875,1.375):
            yield Case(f'create rings mask={mask:x} healthscale={scale}',0x464110,rings(random_source,mask,scale=scale),receiver=lambda t:t['obj'])
    yield Case('creation position callback changes origin',0x464110,rings(random_source,0,True),receiver=lambda t:t['obj'])
    yield Case('no live rings',0x464010,position(random_source,False,2,0.0,23,-57,250.0),receiver=lambda t:t['obj'],arguments=(0x52720C,))
    for mode in (0,1,2,0xFFFFFFFF):
        for angle in (0.0,-0.0,0.5,-179.99,359.999,1e8,-1e8):
            yield Case(f'live rings mode={mode} angle={angle}',0x464010,
                position(random_source,True,mode,angle,123456,-987654,250.0),receiver=lambda t:t['obj'],arguments=(0x52720C,))
    for i in range(16):
        angle=random_source.uniform(-1e6,1e6)
        x=random_source.randrange(-2000000,2000000)
        y=random_source.randrange(-2000000,2000000)
        radius=random_source.uniform(-3000,3000)
        yield Case(f'random live ring {i}',0x464010,position(random_source,True,2,angle,x,y,radius),receiver=lambda t:t['obj'],arguments=(0x52720C,))
