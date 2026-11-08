"""Blind original-only cases for the complete reporter and static list thunk."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_TOP
from clawparity.fixtures import halt

REPORT = 0x4DB4D0
THUNK = 0x50240A
RETURN_PC = 0x4F70A4


def source(env, root, regs, preserve):
    sp = STACK_TOP - 0x1800
    bp = sp + 0x300
    env.write(sp - 0x600, bytes((i * 37 + regs[0]) & 255 for i in range(0xA00)))
    env.put(bp, bp + 0x40, RETURN_PC)
    return NativeSourceContext(72, 1, 0x7ff, 0x7ff,
                               regs[0], regs[1], regs[2], regs[3], regs[4], regs[5],
                               bp, sp, root, 2 | (regs[6] & 0x8d5), 0xffffffff,
                               preserve, 0, 0)


def report_setup(mode, keys, key, prefix, message, code, regs, change):
    def setup(env):
        manager = env.object(40, 'manager-neighbors', fill=0xA9) + 8
        log = env.object(224, 'callback-observation', fill=0xD7)
        p = env.object(len(prefix) + 12, 'prefix-word-guards', data=prefix + b'\0' + b'PQRSUVWX')
        m = env.object(len(message) + 12, 'message-word-guards', data=message + b'\0' + b'abcdefgh')

        def callback(slot):
            def effect(e, call):
                text = e.cstr(call.arguments[0])
                e.put(log, slot, call.receiver, *call.arguments, manager,
                      e.get(manager + 4), e.get(manager + 8), e.get(manager + 12))
                e.put(log + 32, len(text))
                e.write(log + 40, text + b'\0')
                if change:
                    e.put(manager + 12, 1)
                    e.put(manager + 8, 0xBEEF7A19)
                return (0xACED8100 + slot) & 0xffffffff
            return effect

        fallback = env.stub('fallback-error', 'cdecl', 2, callback(0xF0))
        env.put(manager, fallback, 0xDCE71938, 0xE19A5317, mode, 0x51231481, p)
        env.put(0x544D18, len(keys))
        for i, k in enumerate(keys):
            cb = env.stub('table-error-' + str(i), 'cdecl', 2, callback(i + 1))
            env.put(0x544B98 + 12*i, k, cb, 0xDA410000 + i*0x101 + 0x93)
        context = source(env, REPORT, regs, 0x472)
        context.ecx = manager
        return {'manager': manager, 'message': m, 'source': context}
    return setup


def thunk_setup(regs, variant):
    def setup(env):
        ledger = env.object(2048, 'physical-service-state', fill=0)
        tls = ledger + 8
        handle_table = ledger + 64
        locks = ledger + 512
        env.put(ledger, 0, 0)
        def record(e, tag, args):
            n = e.get(ledger)
            e.put(ledger, n + 1)
            e.put(ledger + 1024 + 24*n, tag, len(args), *(list(args) + [0]*4)[:4])
        def alloc(e, flags, size, name):
            return e.object(max(size, 1), name, fill=0 if flags & 0x40 else 0xC3)
        def effect(tag):
            def service(e, call):
                a = call.arguments
                record(e, tag, a)
                if tag == 1: return 0xffffffff if variant == 'tls-fail' else 7
                if tag == 2: return e.get(tls)
                if tag == 3:
                    if variant != 'publish-fail': e.put(tls, a[1])
                    return int(variant != 'publish-fail')
                if tag in (4, 5, 6):
                    # Actual section addresses identify independent recursive owners.
                    index = (a[0] >> 2) % 48
                    slot = locks + index*8
                    e.put(slot, a[0])
                    depth = e.get(slot + 4)
                    if tag == 4:
                        e.write(a[0], bytes(24)); e.put(slot + 4, 0)
                    else: e.put(slot + 4, (depth + (1 if tag == 5 else -1)) & 0xffffffff)
                    return 0
                if tag == 7:
                    if variant == 'global-fail': return 0
                    data = alloc(e, a[0], a[1], 'global-data')
                    handle = e.object(4, 'global-handle', words=[data])
                    e.put(handle_table, handle, data, a[1], 0)
                    return handle
                if tag == 8:
                    return e.get(handle_table) if a[0] else 0
                if tag == 9:
                    e.put(handle_table + 12, max(0, e.get(handle_table + 12)-1)); return 0
                if tag == 10:
                    if variant == 'global-resize-fail': return 0
                    old = e.get(a[0]); size = e.get(handle_table + 8)
                    new = alloc(e, 0, a[1], 'global-resized')
                    e.write(new, e.read(old, min(size, a[1])))
                    e.put(a[0], new); e.put(handle_table + 4, new, a[1]); e.release(old)
                    return a[0]
                if tag == 11:
                    if not a[0]: return 0
                    e.put(handle_table + 12, e.get(handle_table + 12)+1)
                    return e.get(a[0])
                if tag == 12:
                    if variant == 'local-fail': return 0
                    return alloc(e, a[0], a[1], 'local-data')
                if tag == 13:
                    if variant == 'local-resize-fail': return 0
                    # This fixture's actual supplied old block has four words.
                    new = alloc(e, 0, a[1], 'local-resized')
                    e.write(new, e.read(a[0], min(16, a[1])))
                    e.release(a[0]); return new
                if tag == 14:
                    return halt()(e, call)
                if tag == 15: return 0x80000003 if variant == 'old-windows' else 4
            return service
        slots = [0x546A90,0x546A7C,0x546A84,0x546AA4,0x546AAC,0x546A9C,
                 0x546B1C,0x546A8C,0x5469C8,0x546A88,0x5469C4,0x546AA8,
                 0x546A80,0x546958,0x546ABC]
        for tag, slot in enumerate(slots, 1): env.override(slot, effect(tag))
        env.put(0x5408E8, 0)
        env.put(0x540A88, 0)
        env.write(0x540AA8, bytes(68))
        env.put(0x53EC9C, 1)
        owner = env.object(60, 'tls-manager', fill=0)
        env.put(owner, 7, 4, 2, 4, 0, 0, 4)
        env.put(0x540AF0, owner)
        module = env.object(0x1074, 'existing-module', fill=0x79)
        node = env.object(32, 'old-list-head', fill=0x6A)
        env.put(module + 28, node, 20)
        env.put(0x53ECA0, module if variant != 'cold-module' else 0)
        env.put(0x52E2A0, 0x8A91BCDE, 0x9B82CDEF, 0xA1739248, 0xCA8F1702, 0xBC918231, 0x72513DAB)
        thread = env.object(0x118, 'existing-thread', fill=0)
        env.put(thread + 4, module if variant not in ('fallback', 'cold-module') else 0)
        entries = env.object(16, 'tls-values', words=[0x13821491, thread, 0, 0])
        container = env.object(16, 'tls-container', words=[0x511A64, 0, 4, entries])
        env.put(tls, container)
        if variant in ('cold', 'tls-fail', 'global-fail'):
            env.put(0x53EC9C, 0); env.put(0x540AF0, 0); env.put(tls, 0)
        elif variant in ('global-resize', 'global-resize-fail'):
            flags = env.object(32, 'occupied-global-slots', words=[1, 0xA1, 1, 0xB2, 1, 0xC3, 1, 0xD4])
            handle = env.object(4, 'existing-global-handle', words=[flags])
            env.put(handle_table, handle, flags, 32, 1)
            env.put(owner + 4, 4, 4, 4, flags)
            env.put(0x53EC9C, 0)
        elif variant in ('local-resize', 'local-resize-fail'):
            env.put(owner + 12, 6)
            env.put(0x53EC9C, 5)
        elif variant in ('new-thread', 'local-fail', 'publish-fail'):
            env.put(tls, 0)
        return {'source': source(env, THUNK, regs, 0)}
    return setup


def cases(random_source):
    def regs(): return [random_source.getrandbits(32) for _ in range(7)]
    keys = [11, 27, 65, 108, 301]
    for mode in (0, 1, 2, 3, 4, 0xffffffff):
        for key in (0, 11, 65, 301, 302):
            for populated in (False, True):
                code = random_source.getrandbits(32)
                yield Case(f'mode {mode:x} key {key} table {populated}', REPORT,
                           report_setup(mode, keys if populated else [], key, b'Pfx:', b'failure?', code, regs(), key == 65),
                           receiver=lambda t:t['manager'], arguments=(key, lambda t:t['message'], code),
                           source_context=lambda t:t['source'], source_return_pc=RETURN_PC)
    for n in range(36):
        ml = (0,1,2,3,4,78,79,80,120)[n % 9]
        pl = (0,1,2,3,4,7,31,80)[n % 8]
        if pl + min(ml,79) + 1 > 160: pl = 80
        prefix = bytes(65 + (i+n)%26 for i in range(pl))
        message = bytes(97 + (i+2*n)%26 for i in range(ml))
        code = (0xFEDC0000, 0x80000000, 0xffffffff, 0, 1, 0x12345678)[n%6]
        yield Case(f'fallback prefix {pl} message {ml} sample {n}', REPORT,
                   report_setup(2, keys if n%2 else [], 0x4271, prefix, message, code, regs(), n%3 == 0),
                   receiver=lambda t:t['manager'], arguments=(0x4271, lambda t:t['message'],code),
                   source_context=lambda t:t['source'], source_return_pc=RETURN_PC)
    for variant in ('warm','fallback','cold-module','cold','new-thread','publish-fail','old-windows','tls-fail','global-fail','local-fail','global-resize','global-resize-fail','local-resize','local-resize-fail'):
        yield Case('whole MFC '+variant, THUNK, thunk_setup(regs(),variant),
                   source_context=lambda t:t['source'], source_return_pc=RETURN_PC,
                   expect='halt' if variant in ('tls-fail','global-fail','local-fail','global-resize-fail','local-resize-fail') else 'return')
