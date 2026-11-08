"""Blind original-only cases for Tentacle dispatch and construction."""
from clawparity.cases import Case
from clawparity.program import claw
from clawparity.world import world, animation, sprite, cstring, rectangle_services, set_rect
from clawparity.fixtures import returns

ENTRY = 0x4922C0
NEW = 0x4F63EC


def cases(random_source):
    # Reading reference strings uses the canonical hash-checking PE loader.
    program = claw()
    def text(address):
        section = next(s for s in program.sections if s.address <= address < s.address + len(s.data))
        return section.data[address - section.address:].split(b'\0', 1)[0]
    keys = [text(a) for a in (0x52CA44, 0x52CA24, 0x52CA04, 0x52C9E4,
                              0x52C9C4, 0x52C9A8, 0x52C988)]

    for status in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x80000000, 0xFFFFFFFF):
        salt = random_source.getrandbits(32)
        def setup(env, status=status, salt=salt):
            owner = env.object(0x100, 'dispatch-owner', fill=0x97)
            state = env.object(0x180, 'dispatch-state', fill=0xAB)
            target = env.object(0x100, 'dispatch-target', fill=0xCD)
            methods = env.object(0x50, 'dispatch-vtable', fill=0)
            capture = env.object(0x100, 'callback-observations', fill=0)
            alternate = env.object(0x100, 'callback-replacement', fill=0xEF)
            env.put(owner + 0x6C, state)
            env.put(state + 0x18, target, status)
            env.put(target, methods)
            env.put(target + 0x10, state)
            env.put(state + 0x1C, status)
            # The unchanged cleanup callee uses this signed key to fetch a CString.
            cache = env.object(4, 'cleanup-cache', words=[cstring(env, b'distinct-cleanup-key')])
            env.put(0x5376A0, status, status, cache, 0, 4, 0, 0)
            def observe(env, call, slot):
                index = env.get(capture)
                at = capture + 4 + index * 24
                env.put(at, slot, call.receiver, len(call.arguments),
                        call.arguments[0] if call.arguments else salt,
                        env.get(state + 0x18), env.get(state + 0x1C))
                env.put(capture, index + 1)
                env.put(state + 0x18, alternate)
                env.put(state + 0x1C, salt)
                env.put(call.receiver + 0x30 + slot, salt ^ slot)
                return salt
            for slot, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
                env.put(methods + slot, env.stub(f'tentacle-method-{slot}', 'thiscall', argc,
                                                lambda e, c, slot=slot: observe(e, c, slot)))
            return {'owner': owner}
        yield Case(f'dispatch unsigned state {status:#x}', ENTRY, setup,
                   arguments=(lambda t: t['owner'],))

    for mode in ('miss', 'hits', 'fallback'):
        for variant in range(3):
            salt = random_source.getrandbits(32)
            durations = [random_source.randrange(1, 5000) for _ in keys]
            def setup(env, mode=mode, variant=variant, salt=salt, durations=durations):
                resources = {}
                if mode != 'miss':
                    animations = {key: animation(env, duration, f'animation-{index}')
                                  for index, (key, duration) in enumerate(zip(keys, durations))}
                    animations[b'GAME_NULL'] = animation(env, 73 + variant, 'fallback-animation')
                    if mode == 'fallback':
                        animations = {b'GAME_NULL': animations[b'GAME_NULL']}
                    resources['animations'] = animations
                    resources['sprites'] = {b'LEVEL_AQUATISTENTACLE': sprite(env, 41 + variant, 73 + variant)}
                tokens = world(env, owner_words={0x104: 0 if variant == 0 else salt,
                                                0x4C: 103 + variant, 0x50: 207 + variant},
                               state_words={0x18: salt, 0x1C: 0, 0x2C: 3 + variant,
                                            0x30: 5 + variant, 0x34: 7 + variant, 0x38: 9 + variant},
                               resources=resources, bucket_count=1 if variant == 2 else 17)
                state = tokens['state']
                capture = env.object(0x400, 'construction-observations', fill=0)
                rectangle_services(env)
                env.override(0x546B0C, returns(salt))
                def record_service(env, call, service):
                    index = env.get(capture)
                    env.put(capture + 4 + index * 24, service,
                            call.arguments[0], env.get(state + 0x18),
                            env.get(state + 0x1C), env.get(tokens['owner'] + 0x6C),
                            env.get(capture + 0x300))
                    env.put(capture, index + 1)
                def rect(env, call):
                    record_service(env, call, 0x546D5C)
                    return set_rect(env, call)
                alternate = env.object(0x180, 'construction-alternate-state', data=env.read(state, 0x180))
                def random_value(env, call):
                    index = env.get(capture)
                    env.put(capture + 4 + index * 24, 0x4A3050, call.receiver,
                            env.get(state + 0x18), env.get(state + 0x1C),
                            env.get(tokens['owner'] + 0x6C), env.get(capture + 0x300))
                    env.put(capture, index + 1)
                    env.put(state + 0x18, salt ^ 0x77777777)
                    env.put(tokens['owner'] + 0x6C, alternate)
                    return (0, 32767, (salt + variant * 987) & 32767)[variant]
                env.override(0x546D5C, rect)
                env.override(0x4A3050, random_value)
                def allocate(env, call):
                    address = env.object(call.arguments[0], 'constructed-allocation', fill=0xA7)
                    if call.arguments[0] == 0x460:
                        env.put(capture + 0x300, address)
                        env.put(capture + 0x304, env.get(state + 0x18), env.get(state + 0x1C), call.arguments[0])
                    return address
                env.override(NEW, allocate)
                env.put(0x534874, 0)
                env.put(0x53CA30, 3 if variant == 2 else variant)
                env.put(0x5231D0, 0x100, 0x200, 0x400, 3)
                return tokens
            yield Case(f'construct {mode} variant {variant}', ENTRY, setup,
                       arguments=(lambda t: t['owner'],))
