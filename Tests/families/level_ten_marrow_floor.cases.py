"""Original-driven marrow floor inputs, including arithmetic and pointer aliases."""
from clawparity.cases import Case
from clawparity.fixtures import reallocate


def world(position=100, low=0, high=200, speed=1000, tick=1, player=True,
          direction=1, requested=0, opened=0, changed=False, sound=0, salt=0,
          alias=None, registry=False, state_name='ES_IDLE'):
    def setup(env):
        receiver = env.object(0x6c, 'floor', fill=0x51)
        actor = env.object(0x180, 'actor', fill=0xa3)
        logic = env.object(0x40, 'logic', fill=0xc7)
        if alias == 'actor-logic': logic = actor + 0x20
        if alias == 'self-logic': logic = receiver
        if alias == 'target-velocity': logic = actor + 0x12c
        if alias == 'high-position': logic = actor + 0x1c
        env.put(receiver+0xc, actor)
        env.put(receiver+0x10, logic)
        env.put(receiver+0x48, 0x10203040 if not changed else 0x10203041)
        env.put(receiver+0x4c, 73+salt)
        env.put(receiver+0x68, opened)
        env.put(receiver+0x5c, 0)
        env.put(actor+0x4c, position)
        env.put(actor+0x110, direction)
        env.put(actor+0x148, speed)
        env.put(actor+0x158, 0xa1b2c3d4, 0x43e2d1c0)
        env.put(logic+0x1c, 0x11223344 ^ salt)
        env.put(logic+0x2c, low, high)
        if alias == 'target-position':
            logic = actor + 0x20
            env.put(receiver+0x10, logic)
            env.put(logic+0x1c, 0x11223344 ^ salt)
            env.put(actor+0x4c, position, high)
        serial_owner = env.object(0x84, 'serial-owner')
        root_logic = env.object(0x70, 'root-logic')
        root = env.object(0x70, 'root')
        env.put(serial_owner+0x80, 0x10203040)
        env.put(root_logic+0x14, serial_owner)
        env.put(root+0x6c, root_logic)
        env.put(0x537e88, root)
        controller = env.object(0x4c4, 'controller', fill=0x69)
        player_actor = env.object(0x110, 'player-actor', fill=0x37)
        env.put(player_actor+0x10c, 0x87654321 ^ salt)
        env.put(controller+0xc, player_actor)
        env.put(controller+0x4b4, requested)
        env.put(0x537b14, controller if player else 0)
        env.put(0x5430c4, tick)
        env.put(0x537680, 0)
        if registry:
            # A one-leaf original bit tree with distinct key/value for each entry.
            key = env.object(16, 'registry-key', data=state_name.encode()+b'\0')
            leaf = env.object(20, 'registry-leaf')
            env.put(leaf, leaf, leaf, 0, key, 0xdecafbad ^ salt)
            env.put(0x537680, leaf)
        env.put(0x532c0c, int(sound == 2))
        env.put(0x532c10, 0xaabbccdd ^ salt)
        if sound:
            resource = env.object(0x14, 'sound-resource')
            audio = env.object(0x14, 'audio')
            data = env.object(0x7c, 'audio-data', fill=0)
            env.put(resource+0x10, audio)
            env.put(audio+0x10, data)
            env.put(receiver+0x5c, resource)
        return dict(receiver=receiver, actor=actor, logic=logic, controller=controller)
    return setup


def ordinary(address, label, **options):
    return Case(label, address, world(**options), receiver=lambda t:t['receiver'])


def dispatch(index, lower=0, upper=2, stride=12, grow=0, salt=0):
    def setup(env):
        receiver = env.object(0x6c, 'dispatch-receiver', fill=0xb7)
        vtable = env.object(8, 'vtable-with-rtti')
        rtti = env.object(16, 'rtti-record')
        descriptor = env.object(8, 'rtti-descriptor', fill=0x75)
        env.put(receiver, vtable+4)
        env.put(vtable, rtti)
        env.put(rtti+0xc, descriptor)
        observed = env.object(24, 'callback-observation', fill=0x92)
        def make_callback(row):
            def callback(env, call):
                env.put(observed, call.receiver, env.get(0x537b40), env.get(call.receiver+0x24), env.get(0x537b28), env.get(0x537b2c), row)
                env.put(call.receiver+0x24, row ^ salt)
                return 0x87654321
            return env.stub(f'floor-state-callback-{row}', 'thiscall', 0, callback)
        rows = env.object((upper-lower+1)*stride, 'dispatch-rows', fill=0x6e)
        for i in range(upper-lower+1): env.put(rows+i*stride, make_callback(0x31410000+i))
        env.put(0x537b28, lower, upper, rows, rows, stride, 0, 0xabcdef01)
        if grow in ('mutate', 'twice', 'fail'):
            allocation_observed = env.object(32, 'growth-observation', fill=0x83)
            def resize(env, call):
                number = env.calls_so_far(call.function)
                env.put(allocation_observed+(number-1)*16, call.arguments[0], call.arguments[1], env.get(receiver+0x24), env.get(0x537b40))
                if grow == 'fail': return 0
                moved = reallocate()(env, call)
                # Mutable state at the allocator boundary makes both reloads observable.
                env.put(0x537b28, index)
                env.put(0x537b2c, index-1 if grow == 'twice' and number == 1 else index)
                return moved
            env.override(0x4a9070, resize)
        return dict(receiver=receiver)
    return Case(f'dispatch index {index} bounds {lower}:{upper} stride {stride} grow {grow}',0x45a400,setup,receiver=lambda t:t['receiver'],arguments=(index,))


def constructor(salt, hit=False, sound=False, overlap=False):
    def setup(env):
        t = world(salt=salt)(env)
        actor, receiver = t['actor'], t['receiver']
        scene = env.object(0x2c, 'actor-scene')
        env.put(actor+0xc, scene)
        env.put(actor+0x6c, t['logic'])
        env.put(actor+0x8, 0xa0b0c0d0 ^ salt)
        env.put(actor+0x70, 0)
        env.put(actor+0x78, 0)
        env.put(actor+0x174, 0)
        def table(label, name=None, value=0):
            obj = env.object(0x30, label, fill=0)
            env.put(obj+0x18, 1)
            if name:
                buckets=env.object(4,label+'-buckets')
                row=env.object(16,label+'-row')
                key=env.object(len(name)+1,label+'-key',data=name.encode()+b'\0')
                env.put(row,0,0,key,value)
                env.put(buckets,row)
                env.put(obj+0x14,buckets)
            return obj
        env.put(scene+0x10, table('animations'))
        env.put(scene+0x14, table('logic-resources'))
        resource=env.object(0x14,'constructor-sound',fill=0x86)
        env.put(scene+0x28, table('audio-resources','LEVEL_PEGSLIDE' if sound else None,resource))
        rectangle=env.object(0xa8,'rectangle-source',fill=0x42)
        if overlap:
            rectangle=actor+(0x8c if overlap == 'before' else 0x94)
        env.put(rectangle+0x98,0x12340000^salt,0x56780000^salt,0x9abc0000^salt,0xdef00000^salt)
        env.put(0x537960,rectangle)
        return t
    return Case(f'construct salt {salt} sound {sound} rectangle-alias {overlap}',0x45a7c0,setup,receiver=lambda t:t['receiver'],arguments=(lambda t:t['actor'],))


def cases(random_source):
    for address in (0x45a940,0x45a9f0,0x45aa90):
        for sound in (0,1,2):
            for registry in (False,True):
                yield ordinary(address,f'entry {address:x} sound {sound} registry {registry}',sound=sound,registry=registry,state_name={0x45a940:'ES_IDLE',0x45a9f0:'ES_OPENING',0x45aa90:'ES_CLOSING'}[address],salt=random_source.getrandbits(24))
    for player in (False,True):
        for changed in (False,True):
            for requested in (0,1,0x80000000):
                for opened in (0,1,0xffffffff):
                    yield ordinary(0x45a980,f'idle player {player} changed {changed} request {requested} opened {opened}',player=player,changed=changed,requested=requested,opened=opened)
    for address in (0x45aa40,0x45aae0):
        yield ordinary(address,f'{address:x} no controller',player=False)
        for direction in (-1,0,1):
            for position in (-20,0,1,99,100,199,200,220):
                yield ordinary(address,f'{address:x} direction {direction} position {position}',direction=direction,position=position,tick=7)
    for address in (0x45ab40,0x45abc0):
        for position in (-0x80000000,-1,0,1,199,200,201,0x7fffffff):
            for speed,tick in ((0,0),(1,999),(1,1000),(15999,1),(16000,1),(16001,1),(17000,1),(0xffffffff,0xffffffff),(0x80000000,3)):
                yield ordinary(address,f'move {address:x} position {position} product {speed:x}*{tick:x}',position=position,speed=speed,tick=tick)
        for alias in ('actor-logic','self-logic','target-position','target-velocity','high-position'):
            for position in (-1,1,199,201):
                yield ordinary(address,f'move {address:x} alias {alias} position {position}',position=position,alias=alias,tick=19)
        for i in range(15):
            yield ordinary(address,f'random movement {address:x} {i}',position=random_source.getrandbits(32),low=random_source.getrandbits(32),high=random_source.getrandbits(32),speed=random_source.getrandbits(32),tick=random_source.getrandbits(32))
    for player in (False,True):
        yield ordinary(0x45ac40,f'reset controller {player}',player=player,salt=random_source.getrandbits(32),opened=0xffffffff,registry=True)
    for lower in (-3,0,7):
        for stride in (4,12,20):
            for index in (lower,lower+1,lower+2): yield dispatch(index,lower,lower+2,stride)
    for overlap in (False,'before','after'):
        for sound in (False,True):
            for i in range(2):
                yield constructor(random_source.getrandbits(32),sound=sound,overlap=overlap)
    for stride in (4,12,20):
        for index in (-2,4):
            yield dispatch(index,stride=stride,grow='natural')
            yield dispatch(index,stride=stride,grow='mutate')
        yield dispatch(-2,stride=stride,grow='twice')
