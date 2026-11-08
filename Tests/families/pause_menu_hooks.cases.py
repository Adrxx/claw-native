"""Cases for pause_menu_hooks: Pause menu state slots, rectangles and volume gauges.

Layout of the pause menu M (offsets from the disassembly):
  +0 vtable (+0xc: ready test, +0x1c: paint)   +4 application A (+4 window W, +4 of W handle)
  +0xc C (+4 G, +8 control, +0x1c surface manager, +0x24 view)
  +0x19c a widget node whose id is at +0x1ec and whose state word is at +0x21c
  +0x254..+0x26c seven slot objects (flags word at +0x40)   +0x274 D (+0 vtable, +4 E, +0xc C)
  +0x298 the state id handed to the slot dispatcher.
"""
from clawparity.cases import Case

F_RESUME, F_PREPARE, F_SHOW, F_RESTORE, F_SETFLAGS, F_ENTER = 0x450310, 0x450380, 0x4503C0, 0x450430, 0x452930, 0x4529A0
F_THUNK = 0x46DDE0
SLOTS = (0x254, 0x258, 0x25C, 0x260, 0x264, 0x268, 0x26C)
LOST = 0x887601C2
STATES = (0x59DA, 0x59DB)

# log areas: each callback records receiver, call number and first two arguments, four calls deep
(LOG_MENU_READY, LOG_MENU_PAINT, LOG_D_QUERY, LOG_BLT, LOG_UNLOCK, LOG_LOCK, LOG_CONTROL,
 LOG_S1_RESTORE, LOG_S2_RESTORE, LOG_DDS1, LOG_COPY, LOG_CURSOR, LOG_BEGIN, LOG_END, LOG_CS, LOG_Q30, LOG_Q24) = (0x40 * i for i in range(17))


def vtable(env, name, methods, size=0x200):
    """An object whose words are stand-ins: methods maps byte offset -> (convention, argc, effect)."""
    table = env.object(size, name, fill=0)
    for offset, (convention, argc, effect) in methods.items():
        env.put(table + offset, env.stub("%s+%x" % (name, offset), convention, argc, effect))
    return table


def recorder(log, result):
    """A callback that records its receiver, call number and arguments in the log and returns result
    (a number, or a tuple giving the result of the first, second, ... call)."""
    def effect(env, call):
        n = env.calls_so_far(call.function)
        arguments = tuple(call.arguments) + (0, 0)
        env.put(log + 16 * ((n - 1) % 4), call.receiver, n, arguments[0], arguments[1])
        return result[min(n, len(result)) - 1] if isinstance(result, tuple) else result
    return effect


COPY_RECT, SHOW_CURSOR, BEGIN_PAINT, END_PAINT, ENTER_CS, LEAVE_CS = 0x546D58, 0x546D54, 0x546CB4, 0x546CB8, 0x546AAC, 0x546A9C


def copy_rect(log):
    def effect(env, call):
        env.write(call.arguments[0], env.read(call.arguments[1], 16))
        env.put(log, call.arguments[0], call.arguments[1])
        return 1
    return effect


def script_services(env, log, cursor, paint, menu=0, poke=False):
    """Stand-ins for the Win32 services: CopyRect copies the rectangle, ShowCursor walks through the scripted
    counter values, painting and critical sections succeed."""
    env.override(COPY_RECT, copy_rect(log + LOG_COPY))
    shown = recorder(log + LOG_CURSOR, cursor)

    def show_cursor(env, call):
        slot = env.get(menu + 0x254) if poke else 0
        if slot:  # the service raises the flag of the first slot behind the caller's back
            env.put(slot + 0x40, env.get(slot + 0x40) | 1)
        return shown(env, call)

    env.override(SHOW_CURSOR, show_cursor)
    env.override(BEGIN_PAINT, recorder(log + LOG_BEGIN, paint))
    env.override(END_PAINT, recorder(log + LOG_END, 1))
    env.override(ENTER_CS, recorder(log + LOG_CS, 0))
    env.override(LEAVE_CS, recorder(log + LOG_CS + 0x40, 0))


def create_surface(env, log):
    """IDirectDraw::CreateSurface(dd, desc, out, outer): hands back one of the surface interfaces made in setup,
    so both sides see the same stand-in addresses."""
    pool = []
    for k in range(3):
        created = env.object(8, "created%d" % k, fill=0)
        env.put(created, vtable(env, "created-vt%d" % k, {0x58: ("stdcall", 2, recorder(log + 0x40, 0)),
                                                          0x14: ("stdcall", 6, recorder(log + 0x80, 0)),
                                                          0x08: ("stdcall", 1, recorder(log + 0xC0, 0))}))
        pool.append(created)

    def effect(env, call):
        n = env.calls_so_far(call.function)
        env.put(log + 16 * ((n - 1) % 4), call.arguments[0], call.arguments[1])
        env.put(call.arguments[2], pool[min(n, len(pool)) - 1])
        return 0
    return effect


def world(rs, depth=0, active=1, d_present=True, flag=1, slots=127, state=None, node_id=0, node_state=0,
          dds1=0, blt=0, restore=1, j_flags=0, no_s2=False, no_app=False, no_window=False,
          cursor=-1, paint=1, create=True, a14=0, a50=True, a1c=True, poke=False):
    """A pause menu and its collaborators. Every slot object has distinct non-zero contents."""
    def setup(env):
        t = {}
        log = t["log"] = env.object(0x500, "log", fill=0)
        m = t["menu"] = env.object(0x2A0, "menu", fill=0)
        a = t["a"] = env.object(0x90, "a", fill=0)
        w = env.object(0x10, "w", fill=0)
        c = t["c"] = env.object(0x40, "c", fill=0)
        g = env.object(0x40, "g", fill=0)
        h = env.object(0x40, "h", fill=0)
        i = env.object(0x40, "i", fill=0)
        j = env.object(0x40, "j", fill=0)
        s1 = env.object(0xC0, "s1", fill=0)
        s2 = env.object(0xC0, "s2", fill=0)
        e = t["e"] = env.object(0x90, "e", fill=0)
        d = t["d"] = env.object(0x20, "d", fill=0)
        env.put(m, vtable(env, "menu-vt", {0xC: ("thiscall", 0, recorder(log + LOG_MENU_READY, active)),
                                           0x1C: ("thiscall", 0, recorder(log + LOG_MENU_PAINT, 0))}))
        if not no_app:
            env.put(m + 4, a)
        env.put(m + 0xC, c)
        if not no_window:
            env.put(a + 4, w)
        env.put(w + 4, rs.getrandbits(32) | 1)
        env.put(a + 0x7C, 640 + rs.randrange(0, 200), 480 + rs.randrange(0, 100))
        env.put(a + 0x14, a14)
        if a50:
            pane = env.object(0x30, "pane", fill=0)
            if a1c:
                q = env.object(8, "q", fill=0)
                env.put(q, vtable(env, "q-vt", {0x30: ("thiscall", 0, recorder(log + LOG_Q30, 0)),
                                                0x24: ("thiscall", 2, recorder(log + LOG_Q24, 5))}))
                env.put(pane + 0x1C, q)
            env.put(pane + 0x20, rs.getrandbits(32))
            env.put(a + 0x50, pane)
        env.put(c + 4, g)
        env.put(g + 0xC, j)
        env.put(g + 0x10, h)
        env.put(g + 0x14, i)
        env.put(j + 0x34, j_flags)
        # surfaces s1 (the front buffer) and s2 (the back buffer) with their DirectDraw interfaces
        for surface, name, table in ((s1, "dds1", {0x2C: ("stdcall", 3, recorder(log + LOG_DDS1, dds1))}),
                                     (s2, "dds2", {0x14: ("stdcall", 6, recorder(log + LOG_BLT, blt)),
                                                   0x64: ("stdcall", 5, recorder(log + LOG_LOCK, 0)),
                                                   0x80: ("stdcall", 2, recorder(log + LOG_UNLOCK, 0))})):
            iface = env.object(8, name, fill=0)
            env.put(iface, vtable(env, name + "-vt", table))
            env.put(surface + 8, iface)
        env.put(s1, vtable(env, "s1-vt", {0x1C: ("thiscall", 0, recorder(log + LOG_S1_RESTORE, restore))}))
        env.put(s2, vtable(env, "s2-vt", {0x1C: ("thiscall", 0, recorder(log + LOG_S2_RESTORE, restore))}))
        rows, width = rs.randrange(1, 5), 4 * rs.randrange(1, 5)
        pitch = 2 * width + 4 * rs.randrange(0, 3)
        pixels = t["pixels"] = env.object(rows * pitch, "pixels", fill=0)
        env.write(pixels, bytes(rs.getrandbits(8) for _ in range(rows * pitch)))
        env.put(s2 + 0x14, rows, width, pitch)
        env.put(s2 + 0x30, pixels)
        c24 = env.object(0x70, "c24", fill=0)
        env.put(c24 + 0x60, 0xFFFFFFFF)
        env.put(c + 0x24, c24)
        c8 = env.object(8, "c8", fill=0)
        env.put(c8, vtable(env, "c8-vt", {0x28: ("thiscall", 1, recorder(log + LOG_CONTROL, 0))}))
        env.put(c + 8, c8)
        env.put(h + 0x2C, s1)
        if not no_s2:
            env.put(i + 0x2C, s2)
        env.put(d, vtable(env, "d-vt", {0x18: ("thiscall", 0, recorder(log + LOG_D_QUERY, flag))}))
        env.put(d + 4, e)
        env.put(d + 0xC, c)
        env.put(e + 0x78, depth)
        if d_present:
            env.put(m + 0x274, d)
        for index, offset in enumerate(SLOTS):
            if slots >> index & 1:
                slot = env.object(0x180, "slot%x" % offset, fill=0)
                env.put(slot + 0x40, rs.getrandbits(32))
                env.put(slot + 0x3C, rs.getrandbits(32))
                env.put(slot + 0x16C, rs.getrandbits(32), rs.getrandbits(32), rs.getrandbits(32))
                owner = env.object(0x20, "slot-owner", fill=0)
                table = env.object(0x40, "slot-table", fill=0)
                env.put(table + 0x18, rs.randrange(5, 40))
                env.put(owner + 0x10, table)
                env.put(slot + 0xC, owner)
                env.put(m + offset, slot)
                t["slot%x" % offset] = slot
        mgr = env.object(0x500, "mgr", fill=0)
        env.put(mgr + 0x3B8 + 0x18, 10)
        if create:
            dd = env.object(8, "dd", fill=0)
            env.put(dd, vtable(env, "dd-vt", {0x18: ("stdcall", 4, create_surface(env, log + 0x140))}))
            env.put(mgr, dd)
        env.put(c + 0x1C, mgr)
        script_services(env, log, cursor, paint, m, poke)
        env.put(m + 0x298, rs.getrandbits(32) if state is None else state)
        env.put(m + 0x1EC, node_id)
        env.put(m + 0x21C, node_state)
        return t
    return setup


def menu_case(label, function, setup, **options):
    return Case(label, function, setup, receiver=lambda t: t["menu"], **options)


def cases(random_source):
    rs = random_source
    singles = [1 << i for i in range(7)]
    masks = [0, 127] + singles + [127 ^ b for b in singles]

    # 0x452930: set bit 0 of the flags of every present slot
    for mask in masks + [rs.randrange(1, 127) for _ in range(5)]:
        yield menu_case("set flags %02x" % mask, F_SETFLAGS, world(rs, slots=mask))

    # 0x4529a0: clear bit 0 of the first four slots, then dispatch on the state id at +0x298
    for mask in masks:
        yield menu_case("enter other %02x" % mask, F_ENTER, world(rs, slots=mask, state=rs.randrange(0, 0x59D0)))
    for state in STATES:
        for mask in (127, 0, 0x40, 0x10, 0x20, 0x30, 0x0F, 0x70, 0x7F ^ 0x40, 0x7F ^ 0x10, 0x7F ^ 0x20):
            for node_id, node_state in ((0x5B06, 0), (0x5B06, 0x20), (0x5B06, 0x26), (0x5AA1, 0x20), (0x5AA1, 0),
                                        (0x5AA4, 0x20), (0x5AA4, 6), (0, 0x20)):
                yield menu_case("enter %x mask %02x node %x/%x" % (state, mask, node_id, node_state), F_ENTER,
                                world(rs, slots=mask, state=state, node_id=node_id,
                                      node_state=node_state | rs.getrandbits(4) << 8))

    # 0x46dde0: pixel gauges by display depth
    for depth in (0, 1, 7, 8, 9, 15, 16, 17, 24, 32, 0x100, 0xFFFFFFFF, rs.randrange(18, 1000)):
        yield Case("thunk depth %d" % depth, F_THUNK, world(rs, depth=depth), receiver=lambda t: t["d"])
    for depth in (8, 16):
        for _ in range(2):
            yield Case("thunk random pixels depth %d" % depth, F_THUNK, world(rs, depth=depth), receiver=lambda t: t["d"])

    # 0x4503c0: show the menu surfaces
    yield menu_case("show not ready", F_SHOW, world(rs, active=0))
    yield menu_case("show not ready no gauge", F_SHOW, world(rs, active=0, d_present=False))
    yield menu_case("show no gauge", F_SHOW, world(rs, d_present=False))
    yield menu_case("show no gauge ready 7", F_SHOW, world(rs, active=7, d_present=False))
    for depth in (0, 8, 16, 9):
        for dds1 in (0, 0x80004005, (LOST, 0), (LOST, LOST), (0, LOST), (0, 0, 0x80004005), (LOST, 0, 0x80004005)):
            for j_flags in (0, 2, 0x13):
                if depth == 9 and (j_flags != 2 or dds1 not in (0, (LOST, 0))):
                    continue
                if depth in (8, 16) and j_flags == 0x13 and dds1 not in (0, (LOST, 0)):
                    continue
                yield menu_case("show depth %d dds1 %s j %x" % (depth, dds1, j_flags), F_SHOW,
                                world(rs, depth=depth, dds1=dds1, j_flags=j_flags, active=rs.randrange(1, 100),
                                      slots=rs.randrange(0, 128)))
    for blt in (1, LOST, 0x80004005):
        for restore in (0, 1):
            for j_flags in (0, 2):
                yield menu_case("show blt %x restore %d j %x" % (blt, restore, j_flags), F_SHOW,
                                world(rs, blt=blt, restore=restore, j_flags=j_flags))
    yield menu_case("show no back buffer", F_SHOW, world(rs, no_s2=True))
    yield menu_case("show no back buffer j2", F_SHOW, world(rs, no_s2=True, j_flags=2))
    for mask in masks:
        for state in (None, 0x59DA, 0x59DB):
            yield menu_case("show slots %02x state %s" % (mask, state), F_SHOW,
                            world(rs, slots=mask, state=state, node_id=0x5B06 if state == 0x59DA else 0x5AA1,
                                  node_state=0x20 if mask & 1 else 0))

    # 0x450430: repaint after the application window is validated
    yield menu_case("restore not ready", F_RESTORE, world(rs, active=0))
    yield menu_case("restore not ready no app", F_RESTORE, world(rs, active=0, no_app=True))
    yield menu_case("restore no app", F_RESTORE, world(rs, no_app=True))
    yield menu_case("restore no window", F_RESTORE, world(rs, no_window=True))
    yield menu_case("restore no window not ready", F_RESTORE, world(rs, no_window=True, active=0))
    for paint in (1, 0, 0x1234):
        for slots in (0, 127, 0x41):
            yield menu_case("restore paint %x slots %02x" % (paint, slots), F_RESTORE, world(rs, paint=paint, slots=slots))

    # 0x450380: prepare the pause surfaces
    for cursor in ((-1,), (0, -1), (1, 0, -1)):
        for depth in (0, 8, 16):
            yield menu_case("prepare depth %d cursor %s" % (depth, cursor), F_PREPARE,
                            world(rs, depth=depth, cursor=cursor, j_flags=2 if depth else 0, slots=rs.randrange(0, 128)))
    for create in (True, False):
        for no_s2 in (False, True):
            yield menu_case("prepare create %s no_s2 %s" % (create, no_s2), F_PREPARE, world(rs, create=create, no_s2=no_s2))
    for state in STATES:
        yield menu_case("prepare state %x" % state, F_PREPARE, world(rs, state=state, node_id=0x5B06 if state == 0x59DA else 0x5AA4, node_state=0x20))
    for slots in masks:
        yield menu_case("prepare slots %02x" % slots, F_PREPARE, world(rs, slots=slots))

    # 0x450310: resume
    yield menu_case("resume no gauge", F_RESUME, world(rs, d_present=False))
    yield menu_case("resume no gauge no app", F_RESUME, world(rs, d_present=False, no_app=True))
    yield menu_case("resume no app", F_RESUME, world(rs, no_app=True))
    yield menu_case("resume query says no", F_RESUME, world(rs, flag=0))
    yield menu_case("resume query says no, slots", F_RESUME, world(rs, flag=0, slots=rs.randrange(1, 128)))
    for flag in (1, 0x55):
        for a14, a50, a1c in ((0, True, True), (rs.randrange(1, 1 << 30), True, True), (rs.randrange(1, 1 << 30), True, False),
                              (0, False, False)):
            for cursor in ((-1,), (0, -1), (3, 2, 1, 0, -1), (-5,)):
                for slots in (127, 1, 126):
                    yield menu_case("resume flag %x a14 %s a50 %s a1c %s cursor %s slots %02x" % (flag, bool(a14), a50, a1c, cursor, slots),
                                    F_RESUME, world(rs, flag=flag, a14=a14, a50=a50, a1c=a1c, cursor=cursor, slots=slots,
                                                    depth=(0, 8, 16)[rs.randrange(3)], j_flags=2))
    # 0x450364 clears bit 0 of the first slot after the cursor service has raised it
    for slots in (127, 1, 0, 126):
        for cursor in ((-1,), (1, 0, -1)):
            yield menu_case("resume poke slots %02x cursor %s" % (slots, cursor), F_RESUME,
                            world(rs, slots=slots, cursor=cursor, poke=True))
