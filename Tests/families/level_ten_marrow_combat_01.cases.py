"""Marrow combat cases derived from the original instruction packet."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_world(options):
    def setup(env):
        o = options
        boss = env.object(0x500, 'Marrow', fill=0)
        sprite = env.object(0x200, 'Marrow sprite', fill=0)
        actor = env.object(0x200, 'Marrow actor', fill=0)
        state = env.object(0x40, 'state controller', fill=0)
        vt = env.object(0xa0, 'Marrow callbacks', fill=0)
        log = env.object(0x200, 'callback observations', fill=0)
        player = env.object(0x200, 'player', fill=0)
        pc = env.object(0x40, 'player controller', fill=0)
        attack = env.object(0x50, 'player attack', fill=0)
        hit = env.object(0x150, 'incoming hit', fill=0x39)
        world = env.object(0x80, 'world', fill=0)
        level = env.object(0x80, 'level', fill=0)
        terrain = env.object(0xa0, 'terrain', fill=0)
        cells = env.object(4, 'terrain cells', words=[0xffffffff])
        rows = env.object(4, 'terrain rows', words=[0])
        env.put(boss, vt)
        env.put(boss + 0xc, actor, state)
        env.put(boss + 0x128, actor, sprite, actor, 0x11223344, 17, 23, 31)
        env.put(boss + 0x140, 47)
        env.put(boss + 0x18c, o.get('direction', 2))
        env.put(boss + 0x190, actor, actor)
        env.put(boss + 0x1a0, o.get('fired', 0))
        env.put(boss + 0x3bc, 0x12345678, 0xabcdef01, o.get('combat', 50))
        env.put(boss + 0x450, o.get('x', 187), o.get('y', -273))
        env.put(boss + 0x470, o.get('stamp', 100), o.get('delay', 50))
        env.put(boss + 0x478, o.get('stamp', 100), o.get('delay', 50))
        env.put(boss + 0x48c, 0x111, 0x222, 0x333, 0x444)
        env.put(boss + 0x4c0, o.get('health_limit', 100), 65, -24, o.get('velocity', 600))
        env.put(actor + 0xc, world)
        env.put(actor + 0x38, o.get('active', -1))
        env.put(actor + 0x4c, 200, 250)
        env.put(actor + 0x10c, o.get('health', 100))
        env.put(actor + 0x118, 0x80000000)
        env.put(world + 0x24, level)
        env.put(level + 0x5c, terrain)
        env.put(terrain + 0x20, cells, rows)
        env.put(terrain + 0x30, 1024, 1024)
        env.put(terrain + 0x8c, 10, 10)
        env.put(sprite + 0x40, o.get('flags', 0x94))
        env.put(sprite + 0x4c, 200, 250)
        env.put(sprite + 0x118, 11, 13, 19, 29, 37, 41, 43, 53, 59, 61, 67)
        # A paused animation returns its current event without walking assets.
        env.put(sprite + 0x190, 1)
        env.put(sprite + 0x19c, 1)
        env.put(sprite + 0x1a4, o.get('finished', 0), o.get('event', 0), o.get('event', 0))
        if o.get('animation'):
            animation = env.object(0x20, 'firing animation', fill=0)
            frame = env.object(0x30, 'firing frame', fill=0)
            frame_list = env.object(4, 'firing frames', words=[frame])
            env.put(animation + 0xc, frame_list, 1)
            env.put(frame + 0x1c, 0x39)
            env.put(boss + 0x4a0, animation)
        env.put(state + 0x1c, 0)
        env.put(player + 0x4c, 232, o.get('player_y', 250))
        env.put(player + 0x6c, pc)
        env.put(player + 0xcc, o.get('player_state', 5))
        env.put(pc + 0x14, attack)
        env.put(attack + 0x14, o.get('high', 0))
        env.put(attack + 0x3c, o.get('attack', 1))
        env.put(hit + 0x138, 0x80000000)
        env.put(0x537e88, player)
        env.put(0x537210, o.get('now', 150))
        env.put(0x5430c4, 1)
        env.write(0x5262b4, struct.pack('<f', o.get('multiplier', 1.0)))
        env.put(0x534eac, o.get('mode', 0))
        env.put(0x541334, o.get('disabled', 0))
        env.put(0x532c0c, 0)
        env.put(0x53c9ac, 0)
        if o.get('spawn'):
            manager = env.object(0x40, 'object manager', fill=0)
            resources = env.object(0x40, 'logic resources', fill=0)
            animations = env.object(0x40, 'animation resources', fill=0)
            bucket = env.object(4, 'logic bucket', fill=0)
            node = env.object(16, 'Bullet logic entry', fill=0)
            descriptor = env.object(24, 'Bullet descriptor', fill=0)
            bullet_name = env.object(8, 'Bullet name', data=b'Bullet\0')
            free_node = env.object(12, 'manager available list node', fill=0)
            bullet_actor = env.object(0x180, 'bullet actor', fill=0x29)
            bullet_sprite = env.object(0x150, 'bullet sprite', fill=0x47)
            env.put(bullet_actor + 0x12c, bullet_sprite)
            env.put(bullet_actor + 0x138, 17, 23, 53)
            env.put(bullet_sprite + 0x40, o.get('bullet_flags', 0x80))
            env.put(bullet_sprite + 0x118, o.get('rect', 11), 13, 31, 41, o.get('rect', 19), 61, 71, 89, 97, 101, 103)
            def publish(e, call):
                bullet = call.arguments[0]
                controller = e.get(bullet + 0x6c)
                e.put(log + 0x140, bullet, e.get(bullet+0x4c), e.get(bullet+0x50), e.get(bullet+0x64), e.get(bullet+0x104), e.get(bullet+0xd0), e.get(boss+0x1a0), e.get(bullet+0x170))
                e.put(controller + 0x18, bullet_actor)
                if 'velocity_after_publish' in o:
                    e.put(boss + 0x4cc, o['velocity_after_publish'])
                return o.get('publish_return', 0)
            env.put(descriptor + 0x10, env.stub('Bullet publish', 'cdecl', 1, publish))
            env.put(node + 8, bullet_name, descriptor)
            env.put(bucket, node)
            env.put(resources + 0x14, bucket, 1)
            env.put(animations + 0x18, 1)
            env.put(manager + 0xc, world)
            env.put(manager + 0x20, free_node)
            env.put(world + 8, manager)
            env.put(world + 0x10, animations, resources)
            if o.get('sound'):
                sound = env.object(0x20, 'firing sound', fill=0)
                sound_interface = env.object(0x80, 'sound interface', fill=0)
                sound_backend = env.object(0x80, 'sound backend disabled', fill=0)
                env.put(sound + 0x10, sound_interface)
                env.put(sound_interface + 0x10, sound_backend)
                env.put(boss + 0x480, sound)
                env.put(0x532c0c, o.get('sound_enabled', 1))
        if o.get('destroy'):
            env.put(0x544d18, 0)
            env.put(boss + 0x2fc, 0)
            if o.get('external_array'):
                buffer = env.object(48, 'Marrow array buffer', fill=0x43)
                env.put(boss + 0x2fc, 40, buffer)
            def decrement(e, call):
                ptr = call.arguments[0]
                value = (e.get(ptr) - 1) & 0xffffffff
                e.put(ptr, value)
                return value
            env.override(0x5469e8, decrement)
            for offset, count in ((0x1a4,o.get('refs',1)),(0x1a8,o.get('refs',1))):
                string = env.object(32, 'Marrow CString', words=[count,4,7], data=b'')
                env.write(string + 12, b'claw\0')
                env.put(boss + offset, string + 12)
            if o.get('empty_strings'):
                # The canonical empty string header bypasses atomic release.
                env.put(boss + 0x1a4, env.get(0x52e1c8) + 12)
                env.put(boss + 0x1a8, env.get(0x52e1c8) + 12)
        # Minimal valid string id array and empty state-name trie.
        name = env.object(32, 'state name', data=o.get('name', b'LS_IDLE') + b'\0')
        names = env.object(4, 'state names', words=[name])
        env.put(0x537698 + 8, 0, 0, names, 0, 4, 0, 0)
        env.put(0x537668 + 0x18, 0)
        env.override(0x4a3050, sequence(*o.get('random', (99, 99, 99, 99))))
        for slot, argc in ((0x24,0),(0x28,1),(0x44,0),(0x48,0),(0x58,0),(0x9c,0)):
            def effect(e, call, slot=slot):
                n = e.get(log)
                at = log + 4 + n * 32
                e.put(at, slot, call.receiver, e.get(actor + 0xcc), e.get(boss + 0x3bc), e.get(boss + 0x3c4), e.get(boss + 0x1a0), call.arguments[0] if call.arguments else 0)
                e.put(log, n + 1)
                if slot == 0x9c and 'after_callback' in o:
                    e.put(boss + 0x3c4, o['after_callback'])
                return o.get('callback_return', 0x7badcafe)
            env.put(vt + slot, env.stub(f'Marrow slot {slot:x}', 'thiscall', argc, effect))
        if o.get('pacing_callback'):
            env.put(boss + 0x2fc, 3, 4)
        # Distinct subordinate storage makes initialization stores observable.
        if o.get('separate_subordinate'):
            subordinate = env.object(0x200, 'combat subordinate', fill=0x53)
            env.put(subordinate + 0xc, world)
            env.put(subordinate + 0x118, 0x80000000)
            env.put(boss + 0x128, subordinate)
        if o.get('dirty_initialize'):
            env.put(boss + 0x4b4, 0x31415926, 0x27182818, 0x11235813)
        if o.get('speech'):
            speaker = env.object(0x190, 'speech actor', fill=0x51)
            speaker_controller = env.object(0x40, 'speech controller', fill=0x62)
            env.put(speaker + 0x6c, speaker_controller)
            env.put(0x53c9ac, speaker)
            env.put(0x53c9a8, 0)
        if o.get('observe_terrain'):
            tile = env.object(4, 'collision tile', fill=0)
            tile_vt = env.object(0x24, 'collision methods', fill=0)
            tile_slots = env.object(4, 'collision tiles', words=[tile])
            env.put(tile, tile_vt)
            env.put(cells, 0)
            env.put(level + 0x4c, tile_slots)
            def collision(e, call):
                n = e.get(log + 0x1e0)
                e.put(log + 0x1e0, n+1)
                e.put(log + 0x180 + (n % 4)*16, call.receiver, *call.arguments)
                return o.get('collision_result', 0)
            env.put(tile_vt + 0x20, env.stub('terrain probe', 'thiscall', 2, collision))
        if o.get('sound_play'):
            # Run the actual sound selector and setters through a ready channel.
            channel = env.object(0x40, 'ready sound channel', fill=0)
            buffer = env.object(4, 'DirectSound buffer', fill=0)
            buffer_vt = env.object(0x48, 'DirectSound methods', fill=0)
            env.put(sound_backend + 0x78, 1)
            env.put(sound_interface + 0x18, 22050, 23, 37)
            env.put(sound_interface + 0x30, channel + 4, channel + 4)
            env.put(channel + 0xc, buffer, sound_backend)
            env.put(channel + 0x18, 22050)
            env.put(channel + 0x30, 1)
            env.put(buffer, buffer_vt)
            def ds_call(e, call):
                n = e.get(log + 0x1e4)
                e.put(log + 0x1e4, n+1)
                e.put(log + 0x180 + (n % 4)*16, call.receiver, *call.arguments)
                return 0
            for slot, argc in ((0x30,4),(0x3c,2),(0x40,2),(0x44,2)):
                env.put(buffer_vt + slot, env.stub(f'DirectSound {slot:x}', 'stdcall', argc, ds_call))
            def ds_status(e, call):
                e.put(call.arguments[1], 0)
                return 0
            env.put(buffer_vt + 0x24, env.stub('DirectSound GetStatus', 'stdcall', 2, ds_status))
            env.put(0x532c10, 0)
        return dict(boss=boss, hit=hit)
    return setup


def case(label, fn, **options):
    return Case(label, fn, setup_world(options), receiver=lambda t:t['boss'], arguments=(lambda t:t['hit'],) if fn in (0x459d60,0x459ee0) else ())


def cases(random_source):
    for flags in (0x94,0x96):
        for direction in (2,3,0xffffffff):
            yield case(f'begin fire flags {flags} direction {direction}',0x459f90,flags=flags,direction=direction)
    for stamp,delay,now in ((100,50,149),(100,50,150),(100,50,151),(0xfffffff0,32,16),(200,0,100),(0,0xffffffff,0xffffffff)):
        for rnd in (0,1,2,3,0xffffffff,0x80000000):
            yield case(f'fire timer {stamp} {delay} {now} random {rnd}',0x459f10,stamp=stamp,delay=delay,now=now,random=(rnd,))
    for mode,py,active in ((0x26b7,250,0),(0,250,0),(0,200,0),(0,201,0),(0,299,0),(0,300,0),(0,250,-1)):
        yield case(f'idle proximity {mode} {py} {active}',0x459b70,mode=mode,player_y=py,active=active,stamp=100,delay=60)
    for disabled,rnd,pacing in ((1,(0,),False),(0,(99,),False),(0,(4,24),False),(0,(4,25),False),(0,(0,0),True),(0,(5,),True),(0,(0xffffffff,0xffffffff),False)):
        yield case(f'idle random {disabled} {rnd} {pacing}',0x459b70,mode=0x26b7,disabled=disabled,random=rnd,pacing_callback=pacing)
    for state in (b'LS_HITLOW',b'LS_HITHIGH',b'LS_IDLE'):
        for combat in (-1,0,99,299,300,399,400):
            for rnd in (0,1,0xffffffff):
                yield case(f'hit {state!r} {combat} {rnd}',0x459d60,name=state,combat=combat,health=75,random=(rnd,3,4,5))
    for high in (0,1):
        for attack in (0,1,2,3,7,8,9):
            for ps in (4,5):
                yield case(f'damaging hit {high} {attack} {ps}',0x459d60,combat=-1,high=high,attack=attack,player_state=ps,random=(0,1,2,3))
    for combat in (-1,299,300,399,400):
        yield case(f'hit callback changes combat to {combat}',0x459d60,combat=50,after_callback=combat,random=(1,))
    for fired in (0,1):
        for event in (0,2):
            for finished in (0,1):
                yield case(f'update fire no spawn {fired} {event} {finished}',0x45a0b0,fired=fired,event=event,finished=finished)
    for _ in range(12):
        x=random_source.randrange(-10000,10000); y=random_source.randrange(-10000,10000)
        yield case(f'initialize {x} {y}',0x459c80,x=x,y=y)
        yield case(f'clear hit {x} {y}',0x459ee0,x=x,y=y)

    for velocity in (-600,0,600):
        for flags in (0x80,0x82):
            for rect in (11,0x80000000):
                yield case(f'spawn velocity {velocity} flags {flags} rect {rect}',0x45a0b0,spawn=True,event=1,velocity=velocity,bullet_flags=flags,rect=rect)
    for refs in (0,1,2,0x80000000):
        for external in (False,True):
            yield case(f'destructor refs {refs} external {external}',0x45a260,destroy=True,refs=refs,external_array=external)
    yield case('destructor canonical empty strings',0x45a260,destroy=True,empty_strings=True)

    for enabled in (0,1):
        yield case(f'spawn sound enabled {enabled}',0x45a0b0,spawn=True,event=1,sound=True,sound_enabled=enabled)
    for velocity in (-731,0,813):
        yield case(f'publication changes velocity {velocity}',0x45a0b0,spawn=True,event=1,velocity_after_publish=velocity)

    for multiplier in (-1.25,0.0,0.33333334,1.0,2.375):
        yield case(f'initialize multiplier {multiplier}',0x459c80,multiplier=multiplier)
    for combat in (-1,0,99,100):
        for rnd in (-3,-2,-1,0,3):
            yield case(f'expired timer speech boundary {combat} random {rnd}',0x459f10,combat=combat,random=(rnd,),animation=True)
    for flags in (0x94,0x96):
        for direction in (2,3):
            yield case(f'begin real animation {flags} {direction}',0x459f90,flags=flags,direction=direction,animation=True)
    yield case('already fired event one',0x45a0b0,event=1,fired=1)
    for _ in range(8):
        stamp=random_source.randrange(0x100000000)
        delay=random_source.randrange(0x100000000)
        now=random_source.randrange(0x100000000)
        rnd=random_source.randrange(-0x80000000,0x80000000)
        yield case(f'random unsigned timer {stamp} {delay} {now} {rnd}',0x459f10,stamp=stamp,delay=delay,now=now,random=(rnd,))

    yield case('initialize distinct subordinate and dirty flags',0x459c80,separate_subordinate=True,dirty_initialize=True)
    for fired in (1,0x31415926):
        yield case(f'begin fire clears existing latch {fired}',0x459f90,fired=fired,animation=True)
    for player_y in (200,201,250,299,300):
        yield case(f'idle observable terrain y {player_y}',0x459b70,observe_terrain=True,player_y=player_y,active=0)
    yield case('idle blocked terrain',0x459b70,observe_terrain=True,collision_result=1)
    for rnd in (0,24,25):
        yield case(f'idle speech publishes actor {rnd}',0x459b70,mode=0x26b7,random=(0,rnd),speech=True)
    for combat in (299,300,399,400):
        yield case(f'hit reload observes speech range {combat}',0x459d60,combat=50,after_callback=combat,random=(1,),speech=True)
    yield case('fire plays original sound through ready channel',0x45a0b0,spawn=True,event=1,sound=True,sound_play=True)
