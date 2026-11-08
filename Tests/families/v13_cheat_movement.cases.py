"""Movement cases derived from the pinned v1.3 instruction packet."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

MAIN, RIGHT, LEFT = 0x416EE0, 0x4194D0, 0x4198A0
LOOKUP, NEW, RAND = 0x4FC6B4, 0x4FCAEA, 0x4A595B


def movement(label, function=RIGHT, *, turbo=0, power=0, timer=300, stage=17,
             animation=11, adjustment=0, pose=7, mode=8, facing=1,
             held=0, carried=False, lifted=False, platform=False, tile=0,
             collision_pose=None, frozen=1, state=2, pressed=0, keys=0,
             damage=0, tick_timer=0, long_timer=0, other_timer=0,
             kfa=0, invisible=0, null_private=False, salt=0, rng=99, difficulty=0, images=False, writes=(), checkpoint=(0,0), hud=False, lookup_carried=False, physics_limits=False, teeter_facing=None):
    def setup(env):
        obj = env.object(0x240, 'player', fill=0)
        logic = env.object(0x180, 'player-logic', fill=0)
        private = env.object(0x138, 'player-private', fill=0)
        owner = env.object(0x60, 'scene', fill=0)
        manager = env.object(0x90, 'collision-manager', fill=0)
        world = env.object(0x30, 'world-object-list', fill=0)
        tilemap = env.object(0xB0, 'tile-map', fill=0)
        controls = env.object(0x30, 'controls', fill=0)
        app = env.object(0x180, 'application', fill=0)
        settings = env.object(0x80, 'configuration', fill=0)
        settings_vtable = env.object(0x20, 'configuration-vtable', fill=0)
        env.put(settings, settings_vtable)
        env.put(settings_vtable+0x10,env.stub('profile difficulty','thiscall',0,returns(difficulty)))
        env.put(app+0x2C, settings)
        env.put(settings+0x44,*checkpoint)
        env.put(0x535910,app)
        env.put(0x535918,controls)
        defaults=env.object(0x100,'level-defaults',fill=0)
        env.put(0x5360A8,defaults)
        env.put(controls+4,pressed,keys,0xFB1C3D7E)
        env.put(obj+8,0x10 if platform else 0)
        env.put(obj+0xC,owner)
        env.put(owner+8,world)
        env.put(owner+0x24,manager)
        env.put(manager+0xC,owner)
        env.put(manager+0x5C,tilemap)
        env.put(manager+0x64,0x100000,0x100000)
        env.put(obj+0x7C,logic)
        env.put(obj+0x1B0,obj)
        env.put(logic+0x14,0 if null_private else private)
        env.put(logic+0x1C,state)
        env.put(logic+0x2C,50,950,50,950)
        env.put(logic+0x130,tick_timer)
        env.put(obj+0x5C,500+salt%40,300)
        env.put(obj+0xE4,pose)
        env.put(obj+0xF8,16,16)
        env.put(obj+0x134,-16,-52,16,60)
        env.put(obj+0x144,-15,-45,22,52)
        env.put(obj+0x154,-19,-29,31,57)
        env.put(obj+0x164,0x73729191,0x51517878)
        env.put(obj+0x120,0x13579+salt)
        env.put(obj+0x128,67)
        env.put(private,facing,carried)
        env.put(private+0x20,held)
        env.put(private+0x3C,mode)
        env.put(private+0x40,7)
        env.put(private+0x84,adjustment)
        env.put(private+0xF8,long_timer)
        env.put(private+0x114,timer)
        env.put(private+0x11C,other_timer)
        env.put(private+0xC,damage)
        env.put(0x535954,turbo)
        env.put(0x535924,stage)
        env.put(0x5AAFD8,animation)
        env.put(0x532D34,power)
        env.put(0x532D30,0x10000 if power else 0)
        env.put(0x53592C,kfa)
        env.put(0x535948,invisible)
        env.put(0x532864,0)
        env.put(0x53B0D8,0)
        env.put(0x53B0DC,0)
        env.put(0x5365D4,0)
        env.write(0x532AF0,b'\0'*0x138)
        env.put(0x532BA8,frozen)
        env.write(0x532B90,struct.pack('<d',2.375))
        env.write(0x532BB0,struct.pack('<d',-.625))
        if physics_limits:
            for axis in range(3):
                env.write(0x532AF0+0x70+axis*8,struct.pack('<d',-1000000000.0))
                env.write(0x532AF0+0x88+axis*8,struct.pack('<d',1000000000.0))
                env.write(0x532AF0+0xD8+axis*8,struct.pack('<d',1000000000.0))
                env.write(0x532AF0+0xF0+axis*8,struct.pack('<d',1000000000.0))
        # One 1024x1024 tile; virtual classifier records calls after speed and
        # timer publication, and can elect post-collision actor modes.
        cells=env.object(4,'tile-cells',words=[0])
        rows=env.object(4,'tile-rows',words=[0])
        env.put(tilemap+0x20,cells,rows)
        env.put(tilemap+0x28,1,1,1024,1024)
        env.put(tilemap+0x84,500,300,10,10)
        methods=env.object(0x20,'tile-methods',fill=0)
        tileobj=env.object(4,'tile',words=[methods])
        tileobjs=env.object(4,'tile-objects',words=[tileobj])
        env.put(manager+0x4C,tileobjs)
        observations=env.object(48,'tile-observations',fill=0)
        def classify(e,call):
            e.put(observations,call.receiver,*call.arguments,e.get(obj+0x164),e.get(private+0x114))
            if teeter_facing is not None and e.get(logic+0x1C)==0x138E:e.put(private,teeter_facing)
            if collision_pose is not None:e.put(obj+0xE4,collision_pose)
            if tile=='floor':return int(call.arguments[1]>=361)
            if tile=='edge-left':return int(call.arguments[1]>=361 and call.arguments[0]<500)
            if tile=='edge-right':return int(call.arguments[1]>=361 and call.arguments[0]>=516)
            if tile=='tip-left':return int(call.arguments[1]>=361 and call.arguments[0]<=484)
            if tile in ('teeter-ladder','teeter-floor'):
                if e.get(logic+0x1C)==0x138E:
                    if tile=='teeter-ladder':
                        if call.arguments[1]>=361:return 3
                        e.put(obj+0xE4,6);return 0
                    return int(call.arguments[1]>=361)
                return int(call.arguments[1]>=361 and call.arguments[0]>=516)
            if tile=='tip-right':
                if call.arguments[0]==484 and call.arguments[1]>=361:e.put(obj+8,e.get(obj+8)|0x10)
                return int(call.arguments[1]>=361 and call.arguments[0]>=516)
            return tile
        env.put(methods+0x18,env.stub('tile classifier','thiscall',2,classify))
        resources=env.object(0x40,'animation-map',fill=0)
        sounds=env.object(0x40,'sound-map',fill=0)
        env.put(sounds+0x30,1)
        env.put(owner+0x28,sounds,resources)
        image_map=env.object(0x40,'image-map',fill=0)
        sprite_map=env.object(0x40,'sprite-map',fill=0)
        env.put(owner+0x10,image_map,sprite_map)
        image=env.object(0x80,'player-images',fill=0)
        image_frame=env.object(0x40,'image-frame',fill=0x37)
        image_frames=env.object(0x700,'image-frame-table',fill=0)
        for index in range(0x186):env.put(image_frames+index*4,image_frame)
        env.put(image+0x14,image_frames)
        env.put(image+0x64,0,0x185 if images else 0)
        animations={}
        for name in ('CLAW_STAND','CLAW_WALK','CLAW_FALL','CLAW_JUMP','CLAW_TEETER'):
            head=env.object(0x80,name,fill=0)
            frame=env.object(0x40,name+'-frame',fill=0)
            frames=env.object(4,name+'-frames',words=[frame])
            env.put(frame+8,0)
            env.put(frame+0x1C,29+salt%17)
            env.put(head+0xC,frames,1)
            env.put(head+0x20,0x3F800000)
            animations[name]=head
        env.put(private+0x124,animations['CLAW_FALL'])
        env.put(obj+0x1B0,obj)
        def lookup(e,call):
            if call.receiver==sprite_map+0x10:
                e.put(call.arguments[1],0);return 0
            if call.receiver==image_map+0x10:
                e.put(call.arguments[1],image);return 1
            value=animations.get(e.cstr(call.arguments[0]),animations['CLAW_STAND'])
            if isinstance(e.cstr(call.arguments[0]),bytes):value=animations.get(e.cstr(call.arguments[0]).decode('ascii'),animations['CLAW_STAND'])
            e.put(call.arguments[1],value)
            if lookup_carried:e.put(private+4,1)
            return 1
        env.override(LOOKUP,lookup)
        env.override(NEW,allocate())
        env.override(RAND,returns(rng))
        if platform or tile=='tip-right':
            elevator=env.object(0x200,'supporting-platform',fill=0)
            env.put(obj+0x98,elevator)
            env.put(elevator+0x174,3,5)
            env.put(elevator+0x134,-500,-50,500,60)
            env.put(elevator+0x5C,500,300)
        if lifted or state in (5000,0x138F):
            target=env.object(0x240,'lifted-object',fill=0)
            link=env.object(0x30,'lifted-link',fill=0)
            lifted_logic=env.object(0x340,'lifted-logic',fill=0)
            env.put(target+0x7C,link)
            env.put(link+0x18,lifted_logic)
            env.put(lifted_logic+0x2C,1)
            env.put(lifted_logic+0x324,32)
            env.put(lifted_logic+0x328,0xFE729164)
            env.put(private+0x12C,target)
            env.put(private+0x134,target)
            env.put(lifted_logic+0x10,target)
            env.put(target+0x5C,500,300)
        if hud:
            hud_actor=env.object(0x200,'HUD actor',fill=0)
            hud_record=env.object(0x30,'HUD link',fill=0)
            hud_logic=env.object(4,'HUD logic',fill=0)
            hud_methods=env.object(0xD0,'HUD methods',fill=0)
            env.put(hud_actor+0x7C,hud_record)
            env.put(hud_record+0x18,hud_logic)
            env.put(hud_logic,hud_methods)
            env.put(hud_methods+0xCC,env.stub('HUD respawn callback','thiscall',0,returns(0)))
            env.put(0x532864,hud_actor)
        for target,offset,value in writes:
            address={'obj':obj,'logic':logic,'private':private,'global':0}[target]+offset
            env.put(address,value)
        return obj,logic,private
    args=(lambda t:t[0],) if function==MAIN else (lambda t:t[0],lambda t:t[1],lambda t:t[2])
    return Case(label,function,setup,arguments=args)


def cases(random_source):
    for function in (RIGHT,LEFT):
        for turbo in (0,1,0x80000000):
            for power,timer in ((0,0),(0,1),(0,11),(0,12),(0x26BC,0),(0x26BC,300)):
                for adjustment in (-37,0,71):
                    yield movement(f'{function:x} turbo {turbo} power {power} timer {timer} adj {adjustment}',function,turbo=turbo,power=power,timer=timer,adjustment=adjustment)
        for pose in (1,2,4,7):
            for facing in (0,1):
                for mode in (0,8,9,10,18):
                    yield movement(f'{function:x} pose {pose} face {facing} mode {mode}',function,pose=pose,facing=facing,mode=mode,tile='floor' if pose==1 else 0,lifted=True,carried=True)
        for platform in (False,True):
            for frozen in (0,1):
                yield movement(f'{function:x} platform {platform} frozen {frozen}',function,platform=platform,frozen=frozen,pose=7)
    for state in (2,3,7,0x1390,0xFFFFFFFF):
        for pressed in (0,8):
            for timer in (0,1,17,18,0xFFFFFFFF):
                yield movement(f'main default {state} pressed {pressed} timer {timer}',MAIN,state=state,pressed=pressed,tick_timer=timer,long_timer=timer,other_timer=timer)
    for state in (0,4,8,9,10,0x10,0x18,0x19,0x1A,0x1B,0x1F,5000,0x1389,0x138A,0x138B,0x138C,0x138D,0x138E,0x138F,0x1391):
        for pressed,keys in ((0,0),(1,0x2000000),(0,0x1000000)):
            yield movement(f'main state {state} pressed {pressed} keys {keys}',MAIN,state=state,pressed=pressed,keys=keys,tile='floor',pose=1)
    for direction in (0x1000000,0x2000000):
        for turbo in (0,1):
            for power,timer in ((0,0),(0,300),(0x26BC,300)):
                for outcome in (1,4,7):
                    yield movement(f'inline {direction} turbo {turbo} power {power} timer {timer} outcome {outcome}',MAIN,state=0x18,pressed=direction,keys=direction,turbo=turbo,power=power,timer=timer,tile=0,collision_pose=outcome,adjustment=37)
    for null_private in (False,True):
        for difficulty in (0,4):
            for images in (False,True):
                yield movement(f'initialize allocation {null_private} difficulty {difficulty} images {images}',MAIN,state=0,null_private=null_private,difficulty=difficulty,images=images,tile='floor')
    for x,y in ((-100,-100),(2000,2000),(50,50),(950,950)):
        yield movement(f'clamp {x} {y}',MAIN,writes=(('obj',0x5C,x),('obj',0x60,y)),kfa=1,invisible=1)
    for damage in (0,1):
        for weapon in (0,1,2,3,0xFFFFFFFF):
            yield movement(f'weapon cycle {damage} {weapon}',MAIN,pressed=8,damage=weapon,carried=damage,kfa=1)
    for tile in (0,'floor','edge-left','edge-right'):
        for facing in (0,1):
            for keys in (0,0x4000000,0x8000000):
                yield movement(f'idle tile {tile} face {facing} keys {keys}',MAIN,state=24,tile=tile,facing=facing,keys=keys,pose=1)
    for keys in (0,0x1000000,0x2000000,0x4000000):
        for power in (0,0x26BC):
            for outcome in (4,6,7):
                yield movement(f'jump keys {keys} power {power} outcome {outcome}',MAIN,state=24,pressed=1,keys=keys,power=power,collision_pose=outcome)
    for direction in (0x1000000,0x2000000):
        yield movement(f'inline platform {direction}',MAIN,state=24,pressed=direction,platform=True,pose=7,tile=0)
    for state in (23,24,8,9,0x138B,0x138E):
        for pressed in (0,2,0x8000000):
            yield movement(f'input state {state} pressed {pressed}',MAIN,state=state,pressed=pressed,tile='floor',pose=1,lifted=True)
    for fallback in (False,True):
        for difficulty in (0,4):
            yield movement(f'respawn fallback {fallback} difficulty {difficulty}',MAIN,state=23,tile='floor',difficulty=difficulty,writes=(('global',0x53B130,0),('global',0x52ABEC,3),('global',0x52ABE4,10),('private',0x4C,500),('private',0x50,300),('global',0x532BF8+0x24,1)))
    for stage in (150,200,500,1000):
        for carried in (False,True):
            yield movement(f'jump moving {stage} carried {carried}',MAIN,state=24,pressed=1,keys=0x4000000,stage=stage,frozen=0,carried=carried,held=1,collision_pose=7)
    for outcome in (1,4,6,7):
        for facing in (0,1):
            yield movement(f'idle tip outcome {outcome} facing {facing}',MAIN,state=24,tile='tip-right',collision_pose=outcome,facing=facing,rng=1)
    for direction in (0x1000000,0x2000000):
        for adjustment in (0x7FFFFFFF,0x80000000,0xFFFFFFFF):
            yield movement(f'wrap {direction} adjustment {adjustment}',MAIN,state=24,pressed=direction,keys=direction,turbo=1,adjustment=adjustment,facing=0,pose=7)
    yield movement('inline left expired facing retained',MAIN,state=24,pressed=0x1000000,facing=0,timer=0,pose=7,tile=0)
    yield movement('carried input blocked by held guard',MAIN,state=24,carried=True,held=0,platform=True,tile='floor')
    yield movement('respawn saved coordinates absent and hud',MAIN,state=23,tile='floor',checkpoint=(-1,-1),hud=True,difficulty=4)
    yield movement('weapon cycle zero result',MAIN,pressed=8,writes=(('private',0x30,0xFFFFFFFF),),kfa=1)
    yield movement('teeter walks right without jump',MAIN,state=0x138E,keys=0x2000000)
    for weapon in (1,2,3,4):
        yield movement(f'weapon explicit {weapon}',MAIN,pressed=8,writes=(('private',0x30,weapon),))
    for state in (2,0x138C,0x138D):
        yield movement(f'hazard flag state {state}',MAIN,state=state,writes=(('obj',8,0x400000),))
    for state in (2,0x138C,0x138D):
        yield movement(f'hazard support state {state}',MAIN,state=state,platform=True,tile=4)
    yield movement('inline other mode animation tail',MAIN,state=24,pressed=0x2000000,platform=True,pose=7,tile=0,collision_pose=7)
    yield movement('jump fixture restores carried mode',MAIN,state=24,pressed=1,keys=0x4000000,collision_pose=7,lookup_carried=True)
    for tile in ('tip-left','teeter-ladder','teeter-floor'):
        for facing in (0,1):
            yield movement(f'rare idle {tile} face {facing}',MAIN,state=24,tile=tile,pose=1,facing=facing)
    for stage in (100,150,200,250):
        yield movement(f'jump negative residual {stage}',MAIN,state=24,pressed=1,stage=stage,frozen=0,writes=(('global',0x532BB8,0),('global',0x532BBC,0xC0000000)))
    yield movement('inline walk animation tail survives collision',MAIN,state=24,pressed=0x2000000,tile='floor',collision_pose=7)
    yield movement('teeter reads changed facing after collision',MAIN,state=24,tile='teeter-floor',pose=1,teeter_facing=1)
    for residual in (-2.0,-10.0,-100.0):
        low,high=struct.unpack('<II',struct.pack('<d',residual))
        yield movement(f'jump overshoot residual {residual}',MAIN,state=24,pressed=1,stage=150,frozen=0,physics_limits=True,writes=(('global',0x532BB8,low),('global',0x532BBC,high)))
    # Distinct pre-reset words detect omitted initialization and nearby-field
    # substitutions even when both final branches zero their working state.
    for inventory_mode in (0,1):
        writes=[('global',0x52A314,0x17359123),('global',0x52A318,0x24681234),
                ('global',0x532D34,0x26BC),('global',0x532BC8,0x73829163),
                ('global',0x532BCC,0x40290000),('obj',0x110,0x12345678),
                ('obj',0x118,0x5A7C9E31),('obj',0xE8,0x35791113),
                ('obj',0xEC,0x7F1D3B59),('logic',0x130,713),
                ('global',0x532BF8+0x24,inventory_mode),
                ('global',0x532BF8+0x44,0x123456),
                ('global',0x532BF8+0x48,0x234567),
                ('global',0x532BF8+0x124,0x35791357)]
        writes.extend(('global',0x532BF8+offset,0x13579000+offset*3) for offset in range(0x88,0xB0,4))
        yield movement(f'initial distinct inventory {inventory_mode}',MAIN,state=0,tile='floor',writes=tuple(writes))
    for x,y,saved_x,saved_y in ((500,300,500,111),(500,300,222,500),
                                (300,500,300,111),(300,500,222,300)):
        yield movement(f'respawn equality x{x} y{y} saved{saved_x}-{saved_y}',MAIN,state=23,tile='floor',checkpoint=(x,y),tick_timer=713,writes=(('private',0x18,0x123),('private',0x1C,0x456),('private',0x20,0x789),('private',0x84,0x135),('private',0x11C,0x246),('private',0x4C,saved_x),('private',0x50,saved_y)))
    for function in (RIGHT,LEFT):
        for facing in (0,1):
            yield movement(f'fall clears live vertical speed {function:x} {facing}',function,pose=4,facing=facing,writes=(('global',0x532B20,0),('global',0x532B24,0x40290000)))
    for stage in (0,17,100):
        yield movement(f'jump clears platform and private distance {stage}',MAIN,state=24,pressed=1,platform=True,stage=stage,writes=(('private',0x5C,0x13579),))
    for rng in (44,45,46,144,145,146):
        yield movement(f'idle rng boundary {rng}',MAIN,state=24,tile='teeter-floor',pose=1,rng=rng)
    for left in (3,4,5):
        yield movement(f'teeter left versus probe {left}',MAIN,state=24,tile='edge-right',pose=1,writes=(('obj',0x134,left),('obj',0x13C,16)))
    for i in range(20):
        yield movement(f'random movement {i}',RIGHT if i&1 else LEFT,turbo=random_source.choice((0,1,0xFFFFFFFF)),timer=random_source.randrange(500),stage=random_source.randrange(50),animation=random_source.randrange(50),adjustment=random_source.randrange(-100,100),salt=random_source.getrandbits(16),pose=7)
