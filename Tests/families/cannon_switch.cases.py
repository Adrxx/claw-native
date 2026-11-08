"""Original-only cases for the switch's event dispatch and construction."""
from clawparity.cases import Case
from clawparity.program import claw
from clawparity.world import world, sprite, animation, cstring, resource_manager

ENTRY = 0x415350
NEW = 0x4F63EC


def text_at(program, address):
    for section in program.sections:
        if section.address <= address < section.address + len(section.data):
            return section.data[address - section.address:].split(b"\0", 1)[0]
    raise ValueError("original string is not backed")


def cases(random_source):
    program = claw()  # The loader verifies the reference hash before any read.
    keys = [text_at(program, a) for a in (0x522D54, 0x522D48, 0x524664, 0x524648, 0x52462C)]

    def setup_for(event, hit=False, alias=False, change=False, salt=1):
        def setup(env):
            log = env.object(0x400, "callback-observations", fill=0)
            table = env.object(0x40, "switch-methods", fill=0)
            resources = {}
            if hit:
                image = sprite(env, width=37 + salt % 19, height=43 + salt % 23,
                               origin=(salt % 13, salt % 17))
                anim = animation(env, duration=31 + salt % 127)
                sound = env.object(0x40, "sound-resource", fill=salt % 254 + 1)
                resources = {"sprites": {keys[2]: image}, "animations": {keys[3]: anim},
                             "sounds": {keys[4]: sound}}
            w = world(env, resources=resources, idle_state=table if alias else 7 + salt % 101)
            owner, state = w["owner"], w["state"]
            env.put(owner + 4, salt)
            env.put(owner + 0x128, salt ^ 0x18273645, salt ^ 0xAABBCCDD,
                    salt ^ 0x19283746, salt ^ 0xFEDCBA98)
            if hit:
                logic_table = env.object(0x30, "logic-methods", fill=0)
                logic_record = env.object(0x80, "existing-logic", fill=0x65)
                env.put(logic_record, logic_table)

                def logic_effect(e, call):
                    count = e.get(log)
                    row = log + 4 + count * 0x60
                    e.put(row, 0xAC, call.receiver, e.get(state + 0x18), e.get(state + 0x1C),
                          e.get(owner + 0x6C), len(call.arguments), *call.arguments)
                    e.write(row + 0x20, e.read(call.receiver, 0x40))
                    e.put(log, count + 1)
                    return salt ^ 0x517B

                env.put(logic_table + 0x1C, env.stub("logic-reset", "thiscall", 0, logic_effect))
                env.put(logic_table + 0x24, env.stub("logic-select", "thiscall", 2, logic_effect))
                env.put(owner + 0x70, logic_record)
                env.put(owner + 0x78, logic_record)
                descriptors = []
                for n in range(2):
                    value = env.object(0x20, f"logic-value-{n}", fill=0x78 + n)
                    env.put(value + 0x10, salt ^ (0x18DA3412 + n))
                    descriptors.append(value)
                manager = resource_manager(env, dict(zip(keys[:2], descriptors)), bucket_count=1)
                env.put(w["world"] + 0x14, manager)
            old = env.object(0x80, "existing-switch", fill=salt % 254 + 1)
            env.put(old, table)
            env.put(old + 0x10, state)
            env.put(state + 0x18, old, event)

            def observe(tag, argc=0):
                def effect(e, call):
                    count = e.get(log)
                    row = log + 4 + count * 0x60
                    e.put(row, tag, call.receiver, e.get(state + 0x18), e.get(state + 0x1C),
                          e.get(owner + 0x6C), len(call.arguments), *call.arguments)
                    e.write(row + 0x20, e.read(call.receiver, 0x40))
                    e.put(log, count + 1)
                    if change:
                        e.put(state + 0x18, old, salt ^ 0xBADC0FFE)
                        e.put(owner + 0x6C, replacement)
                    return salt ^ tag
                return effect

            replacement = env.object(0x180, "replacement-state", fill=0xBC)
            for offset, tag, argc in ((0x10, 16, 0), (0x1C, 28, 0), (0x20, 32, 0),
                                      (4, 4, 1), (8, 8, 1), (12, 12, 1)):
                env.put(table + offset, env.stub(f"switch-{tag}", "thiscall", argc, observe(tag, argc)))

            # Numeric-state lookup uses a real CString descriptor and unchanged game code.
            descriptor = env.object(4, "numeric-state-description", words=[cstring(env, b"TEST_SWITCH")])
            env.put(0x5376A0, event, event, descriptor)
            env.put(0x5376B0, 4)
            if event == 0:
                def allocation(e, call):
                    e.put(log + 0x380, e.get(state + 0x1C), e.get(state + 0x18),
                          e.get(owner + 0x6C), *call.arguments)
                    if alias:
                        # A backed alias: the constructor's final state store supplies the
                        # fresh callback table; no original code or vtable is modified.
                        return state + 0x1C
                    return e.object(call.arguments[0], "constructed-switch", fill=salt % 254 + 1)
                env.override(NEW, allocation)
            return owner
        return setup

    for event in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF, 0x80000000):
        for change in (False, True):
            salt = random_source.getrandbits(32)
            yield Case(f"event {event:#x} effects {change}", ENTRY,
                       setup_for(event, change=change, salt=salt), arguments=(lambda t: t,))
    for hit in (False, True):
        for alias in (False, True):
            for change in (False, True):
                salt = random_source.getrandbits(32)
                yield Case(f"construct resources {hit} alias {alias} effects {change}", ENTRY,
                           setup_for(0, hit, alias, change, salt), arguments=(lambda t: t,))
