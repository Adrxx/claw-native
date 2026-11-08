"""Original factory construction prefixes and complete transition lifecycles."""
from clawparity.cases import Case
from clawparity.fixtures import halt, returns, release

ENTRY = 0x428c40
TYPES = (2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14)


def setup_factory(payload, fail=False, prefix=False, bypass=0, mode=None, outcome=1,
                  retain=1, old=False, change=None, flags=0, context=True):
    def setup(env):
        owner = env.object(0x200, 'owner', fill=0)
        app = env.object(0x248, 'application', fill=0x75)
        log = env.object(0x400, 'callback journal', fill=0)
        env.put(owner + 8, app)
        env.put(owner + 0xa0, bypass)
        env.put(owner + 0xec, 3)
        env.put(0x537e88, 0)
        input_record = env.object(0x248, 'input', fill=0)
        event = env.object(0x74, 'events', fill=0x37)
        env.put(event, input_record)
        env.write(input_record + 0x1cc, bytes([flags]))
        env.put(0x537200, input_record)
        env.put(0x537204, event)
        if context:
            ctx = env.object(0x40, 'context', fill=0)
            sound = env.object(0x40, 'sound manager', fill=0)
            env.put(ctx + 0x28, sound)
            env.put(owner + 0x30, ctx)
        music = env.object(0x100, 'music manager', fill=0)
        env.put(owner + 0x50, music)
        root = env.object(0x50, 'resource root', fill=0)
        buckets = env.object(80, 'empty directory buckets', fill=0)
        manager = env.object(0x28, 'resource manager', fill=0)
        env.put(root + 0x40, buckets)
        env.put(manager + 0x24, root)
        env.put(owner + 0x34, manager)
        empty = env.object(16, 'empty text', fill=0)
        env.put(0x53ec44, empty)
        title = env.object(24, 'CString storage', fill=0)
        env.put(title, 1, 5, 5)
        env.write(title + 12, b'level\0')
        env.put(0x53c9bc, title + 12)
        ownervt = env.object(0x20, 'owner virtual table', fill=0)
        env.put(owner, ownervt)
        env.put(ownervt + 12, env.stub('owner readiness', 'thiscall', 0, returns(0)))

        def record(code, call):
            index = env.get(log)
            at = log + 4 + index * 32
            args = list(call.arguments) + [0, 0, 0]
            env.put(at, code, call.receiver, env.get(owner + 0x2c), env.get(app + 0x244), *args[:3])
            env.put(log, index + 1)

        states = []
        def state(label):
            obj = env.object(0x200, label, fill=0)
            vt = env.object(0x2c, label + ' vtable', fill=0)
            env.put(obj, vt)
            states.append(obj)
            def destroy(e, call):
                record(1, call)
                if mode == 'reentry' and obj == states[0]:
                    e.put(owner + 0x2c, states[1])
                return obj
            def query(e, call):
                record(2, call)
                if change == 'query':
                    e.put(owner + 0x2c, states[1])
                return 5 if mode == 'type11' else 0x81234567
            def leave(e, call):
                record(3, call)
                if change == 'leave':
                    e.put(owner + 0x2c, states[2])
                elif change == 'leave-null':
                    e.put(owner + 0x2c, 0)
                return 0x98765432
            def initialize(e, call):
                record(4, call)
                if change == 'init-null':
                    e.put(owner + 0x2c, 0)
                elif change == 'init':
                    e.put(owner + 0x2c, states[2])
                return outcome
            def activate(e, call):
                record(5, call)
                if change == 'activate':
                    e.put(owner + 8, replacement_app)
                return 0
            for off, name, argc, effect in ((0,'delete',1,destroy),(4,'initialize',3,initialize),
                    (0x10,'query',0,query),(0x24,'activate',1,activate),(0x28,'leave',1,leave)):
                env.put(vt + off, env.stub(label + ' ' + name, 'thiscall', argc, effect))
            return obj
        replacement_app = env.object(0x248, 'replacement application', fill=0x29)
        if mode or old:
            for label in ('prior state', 'replacement state', 'third state'):
                state(label)
            if mode == 'reentry':
                buffer = env.object(12, 'retained buffer', words=[states[0], 0, 0])
                env.put(owner + 0xe0, buffer, 1, 3)
            if old:
                env.put(owner + 0x2c, states[0])

        def allocation(e, call):
            if fail and e.calls_so_far(0x4f63ec) == 1:
                return 0
            size = call.arguments[0]
            data = (payload * ((size + len(payload)-1)//len(payload)))[:size]
            return e.object(size, 'operator new allocation', data=data)
        env.override(0x4f63ec, allocation)
        env.override(0x4f6428, release())
        def rect(e, call):
            e.put(call.arguments[0], *call.arguments[1:])
            return 1
        env.override(0x546d5c, rect)
        def clock(e,c):
            return (0xfedcba98 + e.calls_so_far(0x546df0) * 0x1020304) & 0xffffffff
        env.override(0x546df0, halt() if prefix else clock)
        env.override(0x5469e4, lambda e,c: len(e.cstr(c.arguments[0])) if c.arguments[0] else 0)
        for address, delta in ((0x5469e8,-1),(0x5469ec,1)):
            def atomic(e, c, delta=delta):
                value = (e.get(c.arguments[0]) + delta) & 0xffffffff
                e.put(c.arguments[0], value)
                return value
            env.override(address, atomic)
        env.override(0x546d54, returns(0xffffffff))
        env.override(0x546cd8, returns(0x76543210))
        alternate_input = env.object(0x248, 'alternate input', fill=0)
        alternate_event = env.object(0x74, 'alternate events', fill=0x69)
        env.put(alternate_event, alternate_input)
        def key(e,c):
            if change == 'input-globals':
                e.put(0x537200, alternate_input)
                e.put(0x537204, alternate_event)
            return 0x8001
        env.override(0x546ce4, key)
        env.override(0x546c44, lambda e,c: 1920 if c.arguments[0] == 0 else 1080)
        def cursor(e,c):
            e.put(log + 0x3c0, *c.arguments)
            return 1
        env.override(0x546d9c, cursor)
        return owner
    return setup


def cases(random_source):
    random_payload = bytes(random_source.randrange(1, 256) for _ in range(307))
    for typ in TYPES:
        for payload in (random_payload, b'\xa5\x39\xfe\x62'):
            yield Case(f'type {typ} randomized construction prefix {payload[0]}', ENTRY,
                setup_factory(payload, prefix=True), receiver=lambda o:o,
                arguments=(typ, 0x12345678, 1, 0xabcdef01), expect='halt')
        yield Case(f'type {typ} top allocation failure', ENTRY,
            setup_factory(random_payload, fail=True), receiver=lambda o:o,
            arguments=(typ, 0x76543210, 1, 0x91827364))
    for fail in (False, True):
        yield Case(f'bypass allocation failure {fail}', ENTRY,
            setup_factory(random_payload, fail=fail, bypass=0x80000000), receiver=lambda o:o,
            arguments=(13, 0x456789ab, 0, 0xffffffff))
    for typ in (0, 1, 6, 7, 15, 0xffffffff, 0x80000000):
        yield Case(f'unsupported unsigned type {typ}', ENTRY, setup_factory(random_payload),
                   receiver=lambda o:o, arguments=(typ, 0x12345678, 1, 0xabcdef01))
    for typ in (2,5,8,9,12,13,14):
        yield Case(f'original type {typ} missing-resource failure lifecycle', ENTRY,
                   setup_factory(b'\0'), receiver=lambda o:o, arguments=(typ,1,1,0x13579bdf))
    yield Case('original type11 retained prior incompatible state', ENTRY,
        setup_factory(b'\0',mode='type11',old=True), receiver=lambda o:o, arguments=(11,1,1,91))
    for outcome in (0, 1, 0x80000000, 0xffffffff):
        for change in (None,'init','activate') if outcome else (None,'init','init-null'):
            for flags in (0, 0x12):
                yield Case(f'retained cleanup reentry result {outcome} change {change} flags {flags}', ENTRY,
                    setup_factory(random_payload,mode='reentry',outcome=outcome,change=change,flags=flags),
                    receiver=lambda o:o, arguments=(0,0x89abcdef,0,0x12345678))
    for retain in (0,1,0x80000000):
        for change in (None,'query','leave','leave-null'):
            yield Case(f'old callback reload retain {retain} change {change}', ENTRY,
                setup_factory(random_payload,old=True,change=change), receiver=lambda o:o,
                arguments=(0,0x24681357,retain,0xabcdef01))

    for context in (False, True):
        yield Case(f'input reset callbacks replace globals context {context}', ENTRY,
            setup_factory(random_payload,mode='reentry',outcome=7,change='input-globals',flags=0x12,context=context),
            receiver=lambda o:o, arguments=(7,random_source.getrandbits(32),0,random_source.getrandbits(32)))
    for _ in range(8):
        yield Case(f'random type13 prefix {_}', ENTRY,
            setup_factory(bytes(random_source.randrange(1,256) for _ in range(337)),prefix=True,context=False),
            receiver=lambda o:o,arguments=(13,random_source.getrandbits(32),random_source.randrange(1,0xffffffff),random_source.getrandbits(32)),expect='halt')
