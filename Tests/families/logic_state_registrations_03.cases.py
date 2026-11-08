"""Original-only registration cases: table bounds, physical growth and hit/miss trees."""
from clawparity.cases import Case

ROOTS = (0x433BE0, 0x434A60, 0x438210, 0x43AE30, 0x43CEE0,
         0x43D5B0, 0x4413F0, 0x441E10, 0x4434C0, 0x445C00)
# Original literal operands of the leading inherited-class comparisons.
CLASSES = {
    0x433BE0: (0x52670C, 0x526714),
    0x434A60: (0x523A5C, 0x526A44),
    0x438210: (0x523A5C, 0x526D44),
    0x43AE30: (0x523714, 0x526F8C),
    0x441E10: (0x52670C, 0x5272FC),
    0x4434C0: (0x523274, 0x527480),
    0x445C00: (0x523714, 0x527798),
}
TABLES = (0x534910, 0x5349B8, 0x537308, 0x537338, 0x537598,
          0x5375D8, 0x537608, 0x537638, 0x537698, 0x5376C8,
          0x5376F8, 0x537728, 0x537758, 0x537878)
STATES = {
    0x433BE0: (0x526700, 0x5266F8),
    0x434A60: (0x523148, 0x5234EC, 0x526A38, 0x526A2C),
    0x438210: (0x5234EC, 0x523148, 0x524548),
    0x43AE30: (0x524418, 0x5236FC),
    0x43CEE0: (0x523148,),
    0x43D5B0: (0x5236FC, 0x52720C, 0x5234F4, 0x527204, 0x5271F4,
                 0x5271E4, 0x5240E8, 0x524418, 0x5271D8, 0x5271CC,
                 0x5271C0, 0x5271B4, 0x5271A8, 0x527198, 0x527188,
                 0x52717C, 0x527170, 0x5234EC, 0x523148),
    0x4413F0: (0x523604, 0x527278, 0x5235F8, 0x5235F0, 0x52726C),
    0x441E10: (0x523604, 0x5272F0, 0x5272E0, 0x5272D0),
    0x4434C0: (0x523268, 0x523148, 0x52746C, 0x52745C, 0x52744C,
                 0x52743C, 0x527430, 0x5231F8, 0x527424, 0x527418, 0x52740C),
    0x445C00: (0x524418, 0x5236FC),
}


def prepare(root, salt, bounds=(1, 128), failure=False, hit=0,
            class_text=b"ABCD", parent=False, perturb=False, fail_new=0,
            stride=4, index=7):
    def setup(env):
        # CRT ordinary heap selection, with retries disabled.
        env.put(0x52F2B0, 0x52F2B0)
        env.put(0x540FE8, 0)
        env.put(0x544D18, 0)
        env.put(0x52E1B8, 0xFFFFFFFF, 0, 0, 0)
        env.put(0x52E1CC, 0x52E1C4)
        sizes = env.object(4096, "physical heap sizes", fill=0)
        error = env.object(24, "diagnostic receiver", fill=0x73)
        prefix = env.object(2, "diagnostic prefix", data=b"!\0")
        env.put(error + 0xC, 4)
        env.put(0x544B4C, prefix)

        def remember(e, ptr, size):
            n = e.get(sizes)
            e.put(sizes + 4 + n * 8, ptr, size)
            e.put(sizes, n + 1)

        lo, hi = bounds
        for table in TABLES:
            width = stride if table != 0x537698 else 4
            size = (hi - lo + 1) * width
            data = env.object(size, f"table {table:x} cells", fill=salt)
            fallback = env.object(64, f"table {table:x} fallback", fill=salt ^ 0xA5)
            if table == 0x537698:
                for offset in range(0, size, 4):
                    env.put(data + offset, 0x52E1C4)
                env.put(fallback, 0x52E1C4)
            env.put(table, salt * 0x01010101, error, lo, hi, data, fallback,
                    width, fallback, 0x13579BDF)
            remember(env, data, size)
        env.put(0x537668, 0x2468ACE1, error, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        env.put(0x52712C, index)
        # Avoid unknown projectile grandparents while retaining the owned parent edge.
        env.write(0x523708, b"ABCD\0")
        env.write(0x523714, b"ABCD\0")
        if root in CLASSES:
            left, right = CLASSES[root]
            env.write(left, class_text + b"\0")
            env.write(right, (b"Z" if parent else class_text) + b"\0")
        if hit:
            node = env.object(20, "pre-existing state node")
            env.put(node, node, node, 0, hit, index)
            env.put(0x537680, node)
            env.put(0x53767C, 1)

        def string_length(e, call):
            return len(e.cstr(call.arguments[0]))

        def resize(e, call):
            old, new_size = call.arguments[2:4]
            if failure:
                return 0
            old_size = 0
            for n in range(e.get(sizes)):
                entry = sizes + 4 + n * 8
                if e.get(entry) == old:
                    old_size = e.get(entry + 4)
            fresh = e.object(new_size, "HeapReAlloc result", fill=salt ^ 0x5A)
            e.write(fresh, e.read(old, min(old_size, new_size)))
            e.release(old)
            remember(e, fresh, new_size)
            return fresh

        if perturb or fail_new:
            def allocate_and_change_counter(e, call):
                if e.calls_so_far(0x4F63EC) == fail_new:
                    return 0
                if perturb and e.calls_so_far(0x4F63EC) == 1:
                    # Insertion receives the old id; its caller must reload the
                    # global id before selecting the name/callback vector cell.
                    e.put(0x52712C, index + 3)
                return e.object(call.arguments[0], "operator new result")
            env.override(0x4F63EC, allocate_and_change_counter)

        env.override(0x5469E4, string_length)
        env.override(0x546928, resize)
        env.override(0x546960, lambda e, c: 0 if failure else e.object(c.arguments[2], "HeapAlloc"))
        return {"table": 0x537308}
    return setup


def cases(random_source):
    for root in ROOTS:
        salt = random_source.randrange(1, 255)
        yield Case(f"{root:x} existing capacity distinct canaries", root,
                   prepare(root, salt))
        yield Case(f"{root:x} append growth", root,
                   prepare(root, salt, bounds=(1, 1)))
        yield Case(f"{root:x} prepend growth", root,
                   prepare(root, salt, bounds=(40, 41)))
        # Actual HeapReAlloc failure is outside this returning profile:
        # 4db6e0 sets EBP to its NULL result, then 4dc680 dereferences
        # [EBP+4] before the owned fallback continuation can execute.
        yield Case(f"{root:x} insertion changes global counter", root,
                   prepare(root, salt, perturb=True))
        if len(STATES[root]) > 1:
            yield Case(f"{root:x} second insertion node allocation fails", root,
                       prepare(root, salt, fail_new=4))
        for state in STATES[root]:
            yield Case(f"{root:x} existing registration {state:x}", root,
                       prepare(root, salt, hit=state))
        if root in CLASSES:
            yield Case(f"{root:x} inherited registration", root,
                       prepare(root, salt, parent=True))
            yield Case(f"{root:x} empty inherited class names", root,
                       prepare(root, salt, class_text=b""))
    for index in (-8, -2, -1, 0, 1, 2, 7, 8):
        for failure in (False,):
            salt = random_source.randrange(1, 255)
            yield Case(f"signed table index {index} failure={failure}", 0x441030,
                       prepare(0, salt, bounds=(-2, 2), failure=failure, stride=12),
                       receiver=lambda t: t["table"], arguments=(index & 0xFFFFFFFF,))
    for lo in (-0x80000000, 0x7FFFFFFD):
        for index in (lo, lo + 1, lo + 2):
            yield Case(f"signed extreme {index}", 0x441030,
                       prepare(0, random_source.randrange(1, 255),
                               bounds=(lo, lo + 2), stride=16),
                       receiver=lambda t: t["table"], arguments=(index & 0xFFFFFFFF,))
