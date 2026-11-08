"""Independent Flip wrapper cases derived from 004b98b0's original instructions."""
from clawparity.cases import Case

ENTRY = 0x4B98B0
LOST = 0x887601C2


def cases(random_source):
    def one(label, initial=0, restore=0, retry=0, source=True,
            mutate_initial=False, mutate_restore=False, replace_surface=False,
            diagnostic=True, beep=False):
        payload = bytes(random_source.randrange(256) for _ in range(256))

        def setup(env):
            wrapper = env.object(32, "wrapper", data=payload[:32])
            source_wrapper = env.object(32, "source-wrapper", data=payload[32:64])
            src_a = env.object(16, "captured-source", data=payload[64:80])
            src_b = env.object(16, "changed-source", data=payload[80:96])
            physical_a = env.object(16, "physical-a", data=payload[96:112])
            physical_b = env.object(16, "physical-b", data=payload[112:128])
            table_a = env.object(48, "physical-vtable-a", data=payload[128:176])
            table_b = env.object(48, "physical-vtable-b", data=payload[176:224])
            wrapper_table_a = env.object(32, "wrapper-vtable-a", data=payload[224:256])
            wrapper_table_b = env.object(32, "wrapper-vtable-b", data=payload[:32])
            log = env.object(128, "callback-log", fill=0)
            env.put(wrapper, wrapper_table_a)
            env.put(wrapper + 8, physical_a)
            env.put(source_wrapper + 8, src_a)
            env.put(physical_a, table_a)
            env.put(physical_b, table_b)
            for address in (0x5413A4, 0x54139C, 0x5413A0, 0x5413A8):
                env.put(address, 0)
            env.put(0x5413A0, int(diagnostic))
            env.put(0x5413A4, int(beep))

            def record(env, call, tag):
                index = env.get(log)
                env.put(log + 4 + index * 24, tag, call.receiver,
                        *(tuple(call.arguments) + (0,) * (3 - len(call.arguments))),
                        env.get(source_wrapper + 8))
                env.put(log, index + 1)

            def flip_a(env, call):
                record(env, call, 0xA001)
                count = env.calls_so_far(flip_a_address)
                if count == 1:
                    if mutate_initial:
                        env.put(wrapper, wrapper_table_b)
                        env.put(source_wrapper + 8, src_b)
                    return initial
                return retry

            def flip_b(env, call):
                record(env, call, 0xB002)
                return retry

            def restore_effect(env, call, tag):
                record(env, call, tag)
                if mutate_restore:
                    env.put(source_wrapper + 8, src_b)
                    if replace_surface:
                        env.put(wrapper + 8, physical_b)
                    else:
                        env.put(physical_a, table_b)
                return restore

            def restore_a(env, call):
                return restore_effect(env, call, 0xC003)

            def restore_b(env, call):
                return restore_effect(env, call, 0xD004)

            flip_a_address = env.stub("physical Flip A", "stdcall", 3, flip_a)
            env.put(table_a + 0x2C, flip_a_address)
            env.put(table_b + 0x2C, env.stub("physical Flip B", "stdcall", 3, flip_b))
            env.put(wrapper_table_a + 0x1C, env.stub("restore A", "thiscall", 0, restore_a))
            env.put(wrapper_table_b + 0x1C, env.stub("restore B", "thiscall", 0, restore_b))
            return {"wrapper": wrapper, "source": source_wrapper if source else 0}

        return Case(label, ENTRY, setup,
                    receiver=lambda t: t["wrapper"], arguments=(lambda t: t["source"],))

    for source in (False, True):
        yield one(f"immediate success source={source}", source=source)
        for result in (1, 0x80004005, 0xFFFFFFFF, 0x887601C1, 0x887601C3):
            yield one(f"ordinary failure {result:#x} source={source}", initial=result, source=source)
        yield one(f"restore zero source={source}", initial=LOST, source=source)
        for restore in (1, 2, 0x80000000, 0xFFFFFFFF):
            for retry in (0, 1, 0x80004005, LOST):
                yield one(f"restore {restore:#x} retry {retry:#x} source={source}",
                          initial=LOST, restore=restore, retry=retry, source=source)
    for replace in (False, True):
        for retry in (0, LOST, 0x80070057):
            yield one(f"reload restore/vtable/surface replace={replace} retry={retry:#x}",
                      initial=LOST, restore=0xFFFFFFFE, retry=retry,
                      mutate_initial=True, mutate_restore=True, replace_surface=replace)
    yield one("source captured before first Flip even on restore failure",
              initial=LOST, mutate_initial=True)
    yield one("beep plus ordinary diagnostic", initial=0x80004005, beep=True)
    for _ in range(12):
        result = random_source.randrange(1, 0x100000000)
        yield one(f"random ordinary HRESULT {result:#x}", initial=result,
                  source=bool(random_source.randrange(2)))
