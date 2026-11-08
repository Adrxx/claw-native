"""Independent original-only cases for the menu actor state machine."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import sequence

ENTRY = 0x45F500
RAND = 0x4A3050
TARGETS = (-60, 110, 530, 700)


def scenario(label, *, state=9003, index=1, direction=1, x=0, timer=10000,
             delta=16, speed=200.0, flags=0xA5B6C7D9, rand=0,
             animation_delta=19, active_animation=True, payload=bytes(range(256)),
             missing_data=False, animation_lookup=False, alias_frame=False):
    def setup(env):
        actor = env.object(0x1B4, "actor", data=(payload * 2)[:0x1B4])
        data = env.object(0x164, "navigation", data=(payload[::-1] * 2)[:0x164])
        resource = env.object(0x30, "resource", fill=0)
        resource_map = env.object(0x40, "resource-map-empty", fill=0)
        env.put(actor + 0x0C, resource)
        env.put(resource + 0x2C, resource_map)
        env.put(resource_map + 0x18, 17)  # empty map bucket count
        env.put(actor + 0x40, flags)
        env.put(actor + 0x4C, x & 0xFFFFFFFF)
        env.put(actor + 0x6C, 0 if missing_data else data)
        env.put(data + 0x1C, state)
        env.put(data + 0x64, direction)
        env.put(data + 0x94, index)
        env.put(data + 0x130, timer)
        env.write(data + 0x160, struct.pack("<f", speed))
        # A live animation with a long countdown observes the update receiver
        # and tick argument while avoiding unrelated frame/audio descendants.
        env.put(actor + 0x190, resource if active_animation else 0)
        env.put(actor + 0x19C, 0x7FFFFFFF)
        env.put(actor + 0x1A0, 1)
        if animation_lookup:
            # Both original menu keys resolve through the actual CString map
            # lookup. Distinct frames expose selection and actual update effects.
            env.put(actor + 0x18C, actor)
            sequences = []
            for number in range(2):
                selected = (state == 9003 and number == 0) or (state == 9004 and number == 1)
                frame = data if alias_frame and selected else env.object(0x30, f"frame-{number}", fill=0)
                env.put(frame + 0x04, 0, 0, 9, 1, 0, 193 + number * 101)
                # frame+1c aliases navigation state in the ordering cases. The
                # selector copies it before the owned state publication; command
                # 9 leaves that copy in animation +20/+24 after the real update.
                if frame != data:
                    env.put(frame + 0x1C, 0x13579BDF + number * 0x11111111)
                env.put(frame + 0x20, 0x12340000 + number, 0x56780000 + number, 0)
                env.put(frame + 0x2C, 0)  # no audio command
                frames = env.object(4, f"frames-{number}", words=[frame])
                animation = env.object(0x14, f"sequence-{number}", fill=0)
                env.put(animation + 0x0C, frames, 1)
                sequences.append(animation)
            walk_node = env.object(0x10, "walk-node", words=[0, 0, 0x528B20, sequences[1]])
            stand_node = env.object(0x10, "stand-node", words=[walk_node, 0, 0x529198, sequences[0]])
            buckets = env.object(4, "animation-map-buckets", words=[stand_node])
            env.put(resource_map + 0x14, buckets, 1)
        env.put(0x53720C, delta)
        env.put(0x5430C4, animation_delta)
        env.override(RAND, sequence(rand))
        return actor
    return Case(label, ENTRY, setup, arguments=(lambda actor: actor,))


def cases(random_source):
    yield Case("null actor", ENTRY, arguments=(0,))
    yield scenario("null navigation", missing_data=True)
    for state in (0, 1, 2, 3, 4, 5, 6, 9000, 9005, 0x7FFFFFFF, 0xFFFFFFFF):
        yield scenario(f"dispatch {state}", state=state)
    yield scenario("state 5 empty animation", state=5, active_animation=False)
    for state in (9001, 9004):
        for timer, delta in ((0, 0), (0, 1), (1, 0), (1, 1), (2, 1),
                             (9, 10), (0xFFFFFFFF, 0x80000000),
                             (0x80000000, 0xFFFFFFFF)):
            yield scenario(f"countdown {state} timer {timer} delta {delta}",
                           state=state, timer=timer, delta=delta)
    # Every old/new pair, including both same-index correction branches.
    for old in range(4):
        for chosen in range(4):
            yield scenario(f"choose {old} rand residue {chosen}", state=9002,
                           index=old, rand=chosen + 0x123450, direction=17, speed=73.25,
                           flags=0xD3E5A7C2 if chosen & 1 else 0x9B7D5F11)
    for index, target in enumerate(TARGETS):
        for direction in (0, 1, 0xFFFFFFFF):
            for offset in (-1, 0, 1):
                yield scenario(f"target comparison {index} dir {direction} off {offset}",
                               index=index, direction=direction, x=target + offset,
                               speed=200, delta=16)
        # Arrival, exact arrival and movement that has not arrived, both ways.
        for direction in (0, 1):
            for distance in (1, 2, 3, 100):
                yield scenario(f"move {index} dir {direction} distance {distance}",
                               index=index, direction=direction,
                               x=target + (distance if direction == 0 else -distance),
                               speed=1000, delta=2, rand=15000)
        for rand in (0, 1, 15000, 15001, 32767, 0x7FFFFFFF, 0xFFFFFFFF):
            yield scenario(f"stand rand {rand} index {index}", index=index,
                           x=target, timer=1, delta=1, rand=rand)
    for alias_frame in (False, True):
        for index, target in enumerate(TARGETS):
            for state in (9003, 9004):
                yield scenario(f"successful lookup state {state} index {index} frame alias {alias_frame}",
                               state=state, index=index, x=target, timer=1, delta=1,
                               rand=15000, animation_lookup=True, alias_frame=alias_frame)
    # Ceil thresholds use adjacent float32 values around exact integral steps.
    for direction in (0, 1):
        for speed in (0.0, -0.0, 0.00001, 199.99998474121094, 200.0,
                      200.00001525878906, 999.9999389648438, 1000.0,
                      1000.0000610351562, -0.25, -1000.0,
                      1.401298464324817e-45, 2147483520.0,
                      3.4028234663852886e38, -3.4028234663852886e38):
            for delta in (0, 1, 5, 1001):
                yield scenario(f"ceil dir {direction} speed {speed} delta {delta}",
                               direction=direction, x=300 if direction == 0 else -300,
                               speed=speed, delta=delta, timer=0xFFFFFFFF)
    for direction in (0, 1):
        for delta in (0xFFFFFF, 0x1000001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            yield scenario(f"unsigned delta {delta} dir {direction}",
                           direction=direction, speed=0.00001,
                           x=0x7FFFFFF0 if direction == 0 else -0x7FFFFFF0,
                           delta=delta, timer=0xFFFFFFFF)
    for number in range(32):
        index = random_source.randrange(4)
        direction = random_source.choice((0, 1, 17, 0xFFFFFFFF))
        target = TARGETS[index]
        yield scenario(f"random {number}", index=index, direction=direction,
                       x=target + random_source.randrange(-1000, 1001),
                       speed=random_source.uniform(0.001, 1000),
                       delta=random_source.randrange(0, 5000),
                       timer=random_source.randrange(0, 10000),
                       flags=random_source.getrandbits(32),
                       rand=random_source.randrange(0x80000000),
                       animation_delta=random_source.randrange(10000),
                       payload=bytes(random_source.randrange(256) for _ in range(256)))
