"""Original-backed parrot state cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_state(kind, value=0, variant=0, payload=123):
    def setup(env):
        def obj(size, name):
            return env.object(size, name, fill=0)
        def fp(address, value):
            env.write(address, struct.pack('<d', value))
        self = obj(0x460, 'parrot')
        owner = obj(0x200, 'object')
        state = obj(0x40, 'state')
        visual = obj(0x200, 'visual')
        world = obj(0x200, 'world')
        layer = obj(0x100, 'layer')
        record = obj(0x100, 'record')
        collision = obj(0x100, 'collision')
        root = obj(0x40, 'root')
        target = obj(0x180, 'hit-target')
        vt = obj(0x80, 'parrot-vtable')
        log = obj(0x200, 'callback-observations')
        env.put(self, vt)
        env.put(self + 0xc, owner, state)
        env.put(self + 0x12c, visual)
        env.put(owner + 0xc, root)
        env.put(root + 0x24, collision)
        env.put(owner + 0x38, 0xffffffff)
        env.put(owner + 0x74, target)
        env.put(target + 0x138, 0x80000000)
        env.put(owner + 0xcc, 7)
        env.put(0x537e88, world)
        env.put(world + 0x6c, layer)
        env.put(layer + 0x14, record)
        env.put(record + 0xe8, payload)
        env.put(record + 0x80, payload ^ 0x4567)
        env.put(state + 0x1c, 17)
        env.put(visual + 0x8, 0xabc00000 | (variant & 1))
        env.put(visual + 0x40, 2 if variant & 1 else 0)
        env.put(visual + 0x118, 0x80000000)
        def animation(name, tag):
            frame = obj(0x30, name + '-frame')
            pointers = obj(4, name + '-frames')
            clip = obj(0x20, name)
            env.put(pointers, frame)
            env.put(clip + 0xc, pointers, 1)
            env.put(frame + 0x1c, tag)
            return clip
        old_animation = animation('old-animation', 0x1234)
        new_animation = animation('new-animation', 0x5678)
        callback_animation = animation('callback-animation', 0x9abc)
        env.put(self + 0x134, old_animation)
        env.put(self + 0x410, new_animation, callback_animation)
        env.put(visual + 0x190, old_animation)
        env.put(self + 0x138, 17, 23, 31, 47)
        env.put(self + 0x210, 11, 13, 19, 29)
        env.put(self + 0x434, payload, payload ^ 0x31)
        env.put(self + 0x430, int(value))
        env.put(self + 0x42c, int(value))
        env.put(self + 0x19c, payload if variant & 2 else payload ^ 1)
        for offset in range(0x28, 0x118, 8):
            fp(self + offset, 0.0)
        for offset in (0x50, 0x58, 0x60):
            fp(self + offset, 4.25 + offset)
        fp(self + 0x68, 5.0)
        fp(self + 0x70, 7.0)
        fp(self + 0x88, 7.0)
        env.put(0x537680, 0)
        env.put(0x532c0c, 0)
        env.put(0x532c10, payload)
        env.put(0x5430c4, 3)
        env.put(0x540e00, 0)
        env.override(0x4a3050, sequence(3, 7, 11, 13))
        def callback(env, call):
            env.put(log, call.receiver, env.get(call.receiver + 0x42c), env.get(call.receiver + 0x134))
            env.write(log + 0x10, env.read(call.receiver + 0x24, 0x100))
            if variant & 4:
                env.put(call.receiver + 0x134, callback_animation)
            return payload
        env.put(vt + 0x48, env.stub('parrot-state callback', 'thiscall', 0, callback))
        if kind == 0x467b50:
            for offset in (0x50, 0x54, 0x58, 0x5c, 0x60, 0x64):
                env.put(self + offset, payload ^ offset)
            if variant:
                sound = obj(0x20, 'sound')
                device = obj(0x20, 'sound-device')
                context = obj(0x80, 'sound-context')
                env.put(self + 0x418, sound)
                env.put(sound + 0x10, device)
                env.put(device + 0x10, context)
                env.put(context + 0x78, 0)
                env.put(0x532c0c, variant & 1)
        if kind == 0x467e30:
            fp(self + 0x40, -7.123456789)
        if kind == 0x467bf0:
            env.put(visual + 0x1a4, variant & 1)
            env.put(visual + 0x19c, (variant >> 1) & 1)
            env.put(visual + 0x190, new_animation if variant & 1 else 0)
        if kind == 0x467c90:
            player = obj(0x200, 'player')
            player_obj = obj(0x100, 'player-object')
            pvt = obj(0x40, 'player-vtable')
            env.put(player, pvt)
            env.put(player + 0xc, player_obj)
            env.put(0x537b14, player)
            def player_callback(env, call):
                env.put(log, call.receiver)
                env.write(log + 8, env.read(call.receiver + 0x28, 0x98))
                env.put(log + 0xb0, env.get(player_obj + 0xcc))
                return payload
            env.put(pvt + 0x24, env.stub('released player', 'thiscall', 0, player_callback))
            text = obj(32, 'state-name')
            env.write(text, b'LS_CARRYMARROW\0' if not variant & 1 else b'LS_OTHER\0')
            strings = obj(4, 'state-name-entry')
            env.put(strings, text)
            env.put(0x5376a0, 17, 17, strings, 0, 4)
            env.put(0x5376b8, 0)
            if variant & 2:
                scratch = obj(12, 'temporary-state-array')
                env.put(scratch, 0x12345, 0x23456, 0x34567)
                env.put(0x5376b4, scratch, 3)
            if variant & 4:
                env.put(0x5376b4, 0, 1)
            if variant & 64:
                env.put(0x5376a0, 16, 16, strings, 0, 4)
            env.put(0x537210, 1000)
            env.put(self + 0xc8, 1 if variant & 8 else 0)
            env.put(self + 0x2fc, 0)
            for offset in (0x80, 0x88, 0x90):
                fp(self + offset, -1e9)
            for offset in (0x98, 0xa0, 0xa8, 0xe8, 0xf0, 0xf8, 0x100, 0x108, 0x110):
                fp(self + offset, 1e9)
            fp(self + 0x50, float(value))
            fp(self + 0x58, float(value) / 2)
            fp(self + 0x38, 0.0)
            fp(self + 0x40, 0.0)
            fp(player + 0x38, (0.0, 2.0, -2.0)[(variant >> 4) % 3])
            fp(player + 0x40, 3.141592653589793)
            fp(player + 0x50, float(payload))
            fp(player + 0x58, -3.75)
            fp(player + 0x68, 100.0)
            fp(player + 0x70, 200.0)
        return self
    return setup


def cases(random_source):
    def case(address, value=0, variant=0, payload=123):
        args = (value,) if address in (0x467b50, 0x467c60) else ()
        return Case(f'{address:x} value={value} variant={variant} payload={payload}', address,
                    setup_state(address, value, variant, payload), receiver=lambda token: token, arguments=args)
    for value in (-2, -1, 0, 1, 2, 3, 0x7fffffff):
        for variant in (0, 2):
            yield case(0x467ae0, value, variant)
    for value in (0, 1, 2, 0xffffffff, 0xabcdef01):
        for variant in (0, 1, 2):
            yield case(0x467b50, value, variant)
    for value in (0, 1, 2, 3, 0xffffffff):
        for variant in (0, 1, 3, 5):
            yield case(0x467bf0, value, variant)
        yield case(0x467c60, value)
    for value in (-17, -0.1, 0, 0.1, 17, 17.125):
        for variant in (0, 1, 2, 4, 8, 16, 32, 64):
            yield case(0x467c90, value, variant, -3 if variant & 16 else 3)
    for value in (-2147483648, -31, 0, 1, 2147483647):
        yield case(0x467e30, payload=value)
    for _ in range(12):
        payload = random_source.randrange(1, 10000)
        yield case(0x467b50, random_source.randrange(0, 4), random_source.randrange(0, 3), payload)
        yield case(0x467c90, random_source.randrange(-50, 51), random_source.choice((0, 2, 16, 32)), payload)
