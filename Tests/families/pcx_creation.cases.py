"""Original-backed creation, decoding, conversion and cleanup witnesses."""
import struct

from clawparity.cases import Case

CREATE = 0x4BE810
NEW = 0x4F63EC
SCRATCH = 0x541FB0


def creation(label, width=4, height=3, planes=1, depth=8, *,
             palette_present=1, create_result=1, allocation_fail=False,
             null_input=False, null_pixels=False, lost=False, mutate=False,
             flags=0xA53C, origin=(-7, 11), salt=19, extra=5):
    def setup(env):
        # Unrelated fields and row padding are nonzero, distinct witnesses.
        image = env.object(0xBC, "image", fill=0xA7)
        methods = env.object(0x20, "image methods", fill=0x79)
        device = env.object(0x87C, "device", fill=0x37)
        interface = env.object(4, "DirectDraw surface")
        ddmethods = env.object(0x84, "DirectDraw methods", fill=0x5D)
        record = env.object(0x500, "callback observations", fill=0xD3)
        pitch = max(1, width) * max(1, depth // 8) + extra
        decodes = bool(create_result) and not allocation_fail
        pixel_size = max(1, max(0, height)) * pitch + 64 if decodes else 64
        pixels = env.object(pixel_size,
                            "pixels and padding", fill=0x6B)
        payload = bytearray()
        for row in range(max(0, height) if decodes else 0):
            for plane in range(planes if planes in (1, 3) else 1):
                column = 0
                while column < max(0, width):
                    count = min(3 if (column + row + plane) % 2 else 1, width - column)
                    value = (salt + row * 41 + plane * 67 + column * 23) & 255
                    if count > 1 or value >= 0xC0:
                        payload.extend((0xC0 | count, value))
                    else:
                        payload.append(value)
                    column += count
        header = bytearray([0x69] * 0x80)
        x, y = origin
        struct.pack_into('<4H', header, 4, x & 65535, y & 65535,
                         (x + width - 1) & 65535, (y + height - 1) & 65535)
        header[0x41] = planes
        palette = bytes((salt + i * 29 + (i // 3) * 7) & 255 for i in range(768))
        data = bytes(header) + bytes(payload) + b'\x0c' + palette
        pcx = env.object(len(data), "PCX bytes", data=data)
        env.put(image, methods)
        env.put(image + 8, interface)
        env.put(image + 0x14, height & 0xFFFFFFFF, width & 0xFFFFFFFF, pitch)
        env.put(image + 0x30, pixels)
        env.put(image + 0xA4, depth)
        env.put(device + 0x474, depth)
        env.write(device + 0x478, bytes((i * 17 + salt) & 255 for i in range(1024)))
        env.put(device + 0x878, palette_present)
        env.put(interface, ddmethods)
        env.write(SCRATCH, bytes((i * 13 + 5) & 255 for i in range(1024)))
        # Optional diagnostic UI is disabled; pixel-format words are deterministic.
        env.put(0x54139C, 0, 0, 0, 0)
        for address, value in ((0x54135C, 3), (0x541360, 3),
                               (0x541368, 2), (0x54136C, 11), (0x541370, 5)):
            env.put(address, value)

        def create(env, call):
            env.put(record, call.receiver, *call.arguments)
            env.write(record + 0x40, env.read(SCRATCH, 1024))
            env.put(record + 0x20, env.get(image + 0x30), env.get(device + 0x474))
            if mutate:
                # Dimensions, planes, conversion decision and palette address were saved.
                env.write(pcx + 4, struct.pack('<4H', 200, 300, 201, 301))
                env.write(pcx + 0x41, b'\x02')
                env.put(device + 0x474, 32)
                env.put(device + 0x878, 0)
                env.write(SCRATCH, bytes((255 - i * 3) & 255 for i in range(1024)))
                env.write(device + 0x478, bytes((255 - i * 11) & 255 for i in range(1024)))
            if null_pixels:
                env.put(image + 0x30, 0)
            return create_result

        def lock(env, call):
            count = env.calls_so_far(call.function)
            env.put(record + 0x450, count, call.receiver, *call.arguments)
            env.put(record + 0x478, env.get(image + 0x30), env.get(image + 0xA4))
            return 0x887601C2 if lost else 0

        def unlock(env, call):
            env.put(record + 0x490, call.receiver, *call.arguments)
            return 0x80004005  # Unlock status is not a creation failure.

        def restore(env, call):
            env.put(record + 0x4A0, call.receiver)
            return 0

        def allocate(env, call):
            env.put(record + 0x4B0, call.arguments[0])
            if allocation_fail:
                return 0
            return env.object(max(1, call.arguments[0]), "temporary decode", fill=0x91)

        env.put(methods + 0x0C, env.stub("create surface", "thiscall", 5, create))
        env.put(methods + 0x1C, env.stub("restore", "thiscall", 0, restore))
        env.put(ddmethods + 0x64, env.stub("Lock", "stdcall", 5, lock))
        env.put(ddmethods + 0x80, env.stub("Unlock", "stdcall", 2, unlock))
        env.override(NEW, allocate)
        return {"image": image, "device": device, "pcx": 0 if null_input else pcx,
                "length": len(data)}

    return Case(label, CREATE, setup, receiver=lambda t: t["image"],
                arguments=(lambda t: t["device"], lambda t: t["pcx"],
                           lambda t: t["length"], flags))


def cases(random_source):
    yield creation("null input", null_input=True)
    for planes in (0, 2, 4, 255):
        yield creation(f"unsupported planes {planes}", planes=planes)
    yield creation("RGB to indexed requires palette", planes=3, depth=8, palette_present=0)
    for planes in (1, 3):
        for depth in (8, 16, 24, 32, 0):
            yield creation(f"planes {planes} to depth {depth}", planes=planes, depth=depth)
            yield creation(f"creation refuses {planes}/{depth}", planes=planes,
                           depth=depth, create_result=0)
        direct_depth = planes * 8
        for failure in ("null pixels", "lost surface"):
            yield creation(f"direct {planes} {failure}", planes=planes, depth=direct_depth,
                           null_pixels=failure == "null pixels", lost=failure == "lost surface")
        conversion_depth = 16
        for width in (1, 3, -1, -3):
            yield creation(f"odd converted width {planes}/{width}", width=width,
                           planes=planes, depth=conversion_depth)
        for width, height in ((4, 3), (0, 0), (-2, 0), (4, -1)):
            yield creation(f"allocation fails {planes}/{width}x{height}", width, height,
                           planes, conversion_depth, allocation_fail=True)
        for width, height in ((0, 0), (2, 0), (4, 1), (6, 2)):
            yield creation(f"converted boundary {planes}/{width}x{height}", width, height,
                           planes, conversion_depth)
        yield creation(f"converter fails after decode {planes}", planes=planes,
                       depth=16, null_pixels=True)
        yield creation(f"converter lost surface {planes}", planes=planes, depth=16, lost=True)
        yield creation(f"saved fields and live palettes {planes}", planes=planes,
                       depth=16, mutate=True)
        yield creation(f"direct saved fields {planes}", planes=planes,
                       depth=direct_depth, mutate=True)
    for width, height, origin in ((65536, 1, (-32768, 0)), (1, 65536, (0, -32768)),
                                  (-65534, 1, (32767, 0)), (0, -2, (12, 5))):
        # No payload is needed when creation declines; avoid huge source buffers.
        yield creation(f"signed endpoints {width}x{height}", width, height,
                       create_result=0, origin=origin)
    for planes in (1, 3):
        for width, height, origin in ((65536, 65536, (-32768, -32768)),
                                      (65536, 32768, (-32768, 0)),
                                      (-65534, 65536, (32767, -32768))):
            yield creation(f"wrapped allocation {planes}/{width}x{height}",
                           width, height, planes, 16, allocation_fail=True, origin=origin)
    for index in range(24):
        planes = random_source.choice((1, 3))
        depth = random_source.choice((8, 16, 24, 32))
        width = random_source.randrange(1, 7) * 2
        height = random_source.randrange(1, 5)
        yield creation(f"random {index}: {planes}/{depth} {width}x{height}",
                       width, height, planes, depth, salt=random_source.randrange(256),
                       flags=random_source.getrandbits(32), extra=random_source.randrange(1, 9),
                       origin=(random_source.randrange(-200, 200), random_source.randrange(-200, 200)))
