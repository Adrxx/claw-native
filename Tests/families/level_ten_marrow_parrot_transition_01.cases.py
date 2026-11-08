"""Original-derived cases for Marrow's Parrot transition callback."""
import struct
from clawparity.cases import Case

ENTRY = 0x459830


def transition_setup(**options):
    def setup(env):
        o = options
        a = env.object(0x500, 'Marrow', fill=0x6d)
        sprite = env.object(0x200, 'sprite', fill=0x93)
        logic = env.object(0x40, 'actor logic', fill=0xb7)
        entity = env.object(0x200, 'speech entity', fill=0x59)
        speech_actor = env.object(0x200, 'speech actor', fill=0x42)
        speech_logic = env.object(0x40, 'speech logic', fill=0x37)
        env.put(a + 0xc, entity, logic)
        env.put(a + 0x12c, sprite)
        env.put(logic + 0x1c, o.get('old_state', 0xc31a709d))
        env.write(a + 0x68, struct.pack('<d', o.get('x', 1.0)))
        env.put(a + 0x138, o.get('actor_left', 0x17), 0xa39182b7, o.get('actor_right', 0x39))
        env.put(sprite + 0x40, o.get('flip', 2))
        env.put(sprite + 8, o.get('flags', 0x12345678))
        sentinels = o.get('sentinels', 0)
        for index, offset in enumerate((0x118, 0x128, 0x138)):
            env.put(sprite + offset, 0x80000000 if sentinels & (1 << index) else o.get('left', 0x21 + 0x13*index), 0x94a10000+index, o.get('right', 0x47 + 0x17*index))
        env.put(sprite + 0x190, o.get('old_animation', 0x749a3210))
        asset = 0
        if o.get('animation', True):
            asset = env.object(0x20, 'animation', fill=0x13)
            frames = env.object(4, 'animation frames', fill=0)
            frame = env.object(0x30, 'animation frame', fill=0x87)
            env.put(asset + 0xc, frames, 1)
            env.put(frames, frame)
            env.put(frame + 0x1c, o.get('duration', 73))
        env.put(a + 0x4a4, asset)
        env.put(a + 0x488, o.get('speech', 0x81234567))
        env.put(0x537210, o.get('clock', 0xd13972e4))
        # Empty Patricia tree or a one-node self-linked match for the fixed name.
        node = 0
        if o.get('registry', True):
            node = env.object(0x18, 'registry node', fill=0)
            env.put(node, node, node, 0, 0x528758, o.get('new_state', 0x9634a127))
        env.put(0x537668 + 0x18, node)
        env.put(speech_actor + 0x6c, speech_logic if o.get('speech_logic', True) else 0)
        env.put(0x53c9ac, speech_actor if o.get('speech_actor', True) else 0)
        env.put(0x53c9a8, o.get('speech_busy', 0))
        if not o.get('entity', True):
            env.put(a + 0xc, 0)
        return {'actor': a}
    return setup


def transition(label, **options):
    return Case(label, ENTRY, transition_setup(**options), receiver=lambda t: t['actor'])


def cases(random_source):
    # All owned branches are covered by this deterministic matrix, regardless of seed.
    for x in (-float('inf'), -0.0, 0.0, 40807.999999, 40808.0, 40808.000001, float('inf'), float('nan')):
        for flip in (0, 2, 0x80000100, 0x80000102):
            for sentinels in (0, 1, 2, 4, 7):
                yield transition(f'position {x} flip {flip:x} sentinels {sentinels}', x=x, flip=flip, sentinels=sentinels)
    for key, values in (
        ('animation', (False, True)),
        ('registry', (False, True)),
        ('entity', (False, True)),
        ('speech', (0, 1, 0x80000000, 0xffffffff)),
        ('speech_actor', (False, True)),
        ('speech_logic', (False, True)),
        ('speech_busy', (0, 1, 0x80000000)),
        ('clock', (0, 1, 0xffffffff)),
        ('flags', (0, 4, 0x80, 0x84, 0xffffffff)),
        ('duration', (0, 1, 0x80000000, 0xffffffff)),
        ('old_state', (0, 1, 0xffffffff)),
        ('new_state', (0, 1, 0xffffffff)),
    ):
        for value in values:
            yield transition(f'{key} {value}', **{key: value})
    for left, right in ((0, 1), (1, 0), (0xffffffff, 0x80000000), (0x80000000, 0x7fffffff), (0x7fffffff, 0xffffffff)):
        for x, flip in ((40809.0, 2), (40807.0, 0)):
            yield transition(f'negation boundaries {left:x} {right:x} {x}', x=x, flip=flip, left=left, right=right, actor_left=left, actor_right=right)
    for i in range(45):
        yield transition(f'random independent values {i}', x=random_source.choice((40807.0, 40808.0, 40809.0)), flip=random_source.getrandbits(32), sentinels=random_source.randrange(8), old_state=random_source.getrandbits(32), new_state=random_source.getrandbits(32), actor_left=random_source.getrandbits(32), actor_right=random_source.getrandbits(32), left=random_source.getrandbits(32), right=random_source.getrandbits(32), old_animation=random_source.getrandbits(32), duration=random_source.getrandbits(32), flags=random_source.getrandbits(32), speech=random_source.getrandbits(32), clock=random_source.getrandbits(32))
