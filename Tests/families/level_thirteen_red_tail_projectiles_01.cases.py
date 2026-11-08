"""Original-driven cases for the two Red Tail projectile classes."""
import struct
from clawparity.cases import Case


def _map(env, entries):
    owner = env.object(0x40, 'resource-manager', fill=0)
    bucket = env.object(4, 'resource-bucket', fill=0)
    head = 0
    for key, value in entries:
        key = key.encode() + b'\0'
        text = env.object(len(key), 'resource-name', data=key)
        node = env.object(0x10, 'resource-node', words=[head, 0, text, value])
        head = node
    env.put(bucket, head)
    env.put(owner + 0x14, bucket, 1)
    return owner


def _animation(env, value):
    frame = env.object(0x30, 'animation-frame', fill=0)
    env.put(frame + 0x1c, value)
    frames = env.object(4, 'animation-frames', words=[frame])
    animation = env.object(0x20, 'animation', fill=0)
    env.put(animation + 0xc, frames, 1)
    return animation


def _base(env, words, sprite=True, maps=True):
    obj = env.object(0x160, 'projectile', data=struct.pack('<88I', *words))
    placed = env.object(0x200, 'placed-object', fill=0)
    state = env.object(0x200, 'object-state', fill=0)
    root = env.object(0x40, 'scene-root', fill=0)
    collision = env.object(0x80, 'collision', fill=0)
    env.put(collision + 0x64, 64, 48)
    picture = env.object(0x30, 'picture', fill=0)
    env.put(picture + 0x18, 7, 11, 31, 39)
    pictures = env.object(4, 'pictures', words=[picture])
    group = env.object(0x70, 'image-group', fill=0)
    env.put(group + 0x14, pictures)
    env.put(group + 0x64, 0, 0)
    cycle = _animation(env, 43)
    explosion = _animation(env, 71)
    knife_group = env.object(0x70, 'knife-image-group', fill=0)
    bullet_group = env.object(0x70, 'bullet-image-group', fill=0)
    env.put(knife_group + 0x14, pictures)
    env.put(knife_group + 0x64, 0, 0)
    env.put(bullet_group + 0x14, pictures)
    env.put(bullet_group + 0x64, 0, 0)
    image = _map(env, [('GAME_BULLETS', group), ('LEVEL_REDTAILKNIFE', knife_group), ('LEVEL_REDTAILBULLET', bullet_group), ('LEVEL_REDTAILBULLET_EXPLOSION', knife_group)] if sprite else [])
    sound = _map(env, [])
    animation = _map(env, [('GAME_CYCLE50', cycle), ('LEVEL_REDTAILBULLETEXPLOSION', explosion)] if maps else [])
    env.put(root + 0x10, image, sound)
    env.put(root + 0x24, collision)
    env.put(root + 0x2c, animation)
    env.put(root + 8, placed)
    env.put(placed + 0xc, root)
    env.put(placed + 0x4c, 137, 251)
    env.put(placed + 0x64, 13)
    env.put(placed + 0x6c, state)
    env.put(placed + 0x164, words[0] & 0xffff)
    env.put(obj + 8, placed, placed, state)
    env.put(obj + 0x12c, placed, state)
    env.put(obj + 0x148, cycle)
    env.put(obj + 0x150, explosion)
    alternate_root = env.object(0x40, 'alternate-state-root', fill=0)
    alternate_animation = _map(env, [('GAME_CYCLE50', explosion), ('LEVEL_REDTAILBULLETEXPLOSION', cycle)])
    env.put(alternate_root + 8, placed)
    env.put(alternate_root + 0x10, image, sound)
    env.put(alternate_root + 0x24, collision)
    env.put(alternate_root + 0x2c, alternate_animation)
    env.put(state + 0xc, alternate_root)
    env.put(state + 0x4c, 312, 519)
    env.put(state + 0x64, 27)
    env.put(0x540e00, 1)
    env.put(state + 0x1c, 7)
    env.put(0x537210, 12345)
    env.put(0x53724c, 1)
    owner = env.object(0x130, 'global-player', fill=0)
    env.put(0x5371fc, owner)
    env.put(owner + 0x124, 0)
    env.put(0x537680, 0) # state-name trie has no root
    return dict(obj=obj, placed=placed, state=state, root=root, cycle=cycle, explosion=explosion, owner=owner)


def _callback(env, label, receiver, result=0):
    log = env.object(0x20, label + '-log', fill=0)
    def effect(env, call):
        count = env.get(log)
        env.put(log, count + 1, call.receiver, len(call.arguments), result)
        if call.arguments:
            env.put(log + 0x10, *call.arguments[:4])
        env.put(receiver + 0x144, (env.get(receiver + 0x144) + 0x173) & 0xffffffff)
        return result
    return env.stub(label, 'thiscall', 0, effect)


def _dispatch_setup(words, table, index, present, grow=False):
    def setup(env):
        t = _base(env, words)
        callback = _callback(env, 'state-method', t['obj'], words[3])
        basecallback = _callback(env, 'base-state-method', t['obj'], words[4])
        slots = env.object(12, 'dispatch-slots', words=[callback if present else 0] * 3)
        env.put(table, 0, 0, 4, 6, slots, slots, 4, slots, 0x71)
        if grow:
            index_value = 3 if index < 4 else 7
        else:
            index_value = index
        base = env.object(64, 'base-dispatch-slots', words=[basecallback] * 16)
        env.put(0x538428, 0, 0, 0, 15, base, base, 4, base, 0x29)
        return dict(t, index=index_value)
    return setup


def _factory_setup(words, state):
    def setup(env):
        t = _base(env, words)
        env.put(t['state'] + 0x1c, state)
        child = env.object(0x160, 'existing-projectile', fill=0)
        methods = env.object(0x24, 'projectile-methods', fill=0)
        env.put(child, methods)
        env.put(child + 0x10, t['state'])
        for offset in (0x10, 0x1c, 0x20):
            env.put(methods + offset, _callback(env, 'factory-method-'+str(offset), child, words[offset // 4]))
        env.put(t['state'] + 0x18, child)
        # A unique, writable CString with sufficient capacity avoids refcount imports.
        string = env.object(0x20, 'unique-string', words=[1, 0, 16, 0, 0, 0, 0, 0])
        cell = env.object(64, 'string-cells', words=[string + 12] * 16)
        env.put(0x537698, 0, 0, 0, 15, cell, cell, 4, cell, 0)
        for offset in (4, 8, 12):
            def effect(env, call, offset=offset):
                env.put(child + 0x150 + offset, call.arguments[0], call.receiver)
                return words[offset]
            env.put(methods + offset, env.stub('default-method-'+str(offset), 'thiscall', 1, effect))
        return t
    return setup


def cases(random_source):
    words = [random_source.getrandbits(32) for _ in range(88)]
    # Both wrappers: dispatch and fallback paths, including signed/unsigned state edges.
    for function in (0x410640, 0x410700):
        for state in (0, 1, 2, 0x1c, 0x1d, 0x1e, 0x1f, 999, 1000, 1001, 0xffffffff):
            yield Case(f'factory {function:x} state {state:x}', function, _factory_setup(words, state), arguments=(lambda t:t['placed'],))
    for function, table in ((0x413660, 0x534b78), (0x413b80, 0x534b50)):
        for index in (4, 5, 6):
            for present in (False, True):
                yield Case(f'dispatch {function:x} {index} callback {present}', function, _dispatch_setup(words, table, index, present), receiver=lambda t:t['obj'], arguments=(lambda t:t['index'],))
        for index in (3, 7):
            yield Case(f'dispatch {function:x} grow {index}', function, _dispatch_setup(words, table, index, False, True), receiver=lambda t:t['obj'], arguments=(lambda t:t['index'],))
    for sprite in (False, True):
        for maps in (False, True):
            for branch in (0, 1, 2):
                def constructor(env, sprite=sprite, maps=maps, branch=branch):
                    t = _base(env, words, sprite=sprite, maps=maps)
                    env.put(0x53724c, 1 if branch == 0 else 0)
                    env.put(t['owner'] + 0x124, 1 if branch == 2 else 0)
                    return t
                for function in (0x4134e0, 0x4139c0):
                    yield Case(f'constructor {function:x} image {sprite} map {maps} branch {branch}', function, constructor, receiver=lambda t:t['obj'], arguments=(lambda t:t['placed'],))
    for animation in (False, True):
        def falling(env, animation=animation):
            t = _base(env, words)
            env.put(t['obj'] + 0x148, t['cycle'] if animation else 0)
            return t
        yield Case(f'knife enter falling animation {animation}', 0x413940, falling, receiver=lambda t:t['obj'])
    for mapped in (False, True):
        def explosion(env, mapped=mapped):
            t = _base(env, words)
            env.put(t['obj'] + 0x150, t['explosion'] if mapped else 0)
            return t
        yield Case(f'bullet enter explosion mapped {mapped}', 0x413f80, explosion, receiver=lambda t:t['obj'])
    for cycle in (False, True):
        for elapsed in (0, 1, 9999, 10000, 10001, 0xffffffff):
            for y in (-1.0, 0.0, 1.0, 1024.0, float('nan')):
                def update(env, cycle=cycle, elapsed=elapsed, y=y):
                    t = _base(env, words)
                    env.put(t['obj'] + 0x148, t['cycle'] if cycle else 0)
                    env.put(t['placed'] + 0x190, 0) # inactive original animation player
                    env.put(t['obj'] + 0x150, (12345 - elapsed) & 0xffffffff, 10000)
                    env.write(t['obj'] + 0x70, struct.pack('<d', y))
                    env.put(0x52b360, 1024)
                    env.put(t['placed'] + 8, words[1])
                    return t
                yield Case(f'knife update animation {cycle} elapsed {elapsed:x} y {y}', 0x413960, update, receiver=lambda t:t['obj'])
