"""Blind original-only callback and construction cases for GroundBlower."""
import struct
from clawparity.cases import Case
from clawparity.world import world, cstring

ENTRY = 0x448D10


def copy_rect(env, call):
    env.write(call.arguments[0], env.read(call.arguments[1], 16))
    return 1


def rect_empty(env, call):
    left, top, right, bottom = struct.unpack('<4i', env.read(call.arguments[0], 16))
    return int(right <= left or bottom <= top)


def setup_case(command, words, rectangle=None, mutate=False, redirect=False):
    def setup(env):
        tokens = world(env, owner_words={8: words[0], 0x64: words[1],
                         0x118: (rectangle or (0, 0, 0, 0))[0],
                         0x11C: (rectangle or (0, 0, 0, 0))[1],
                         0x120: (rectangle or (0, 0, 0, 0))[2],
                         0x124: (rectangle or (0, 0, 0, 0))[3]},
                       state_words={0x1C: command, 0x24: words[2], 0x28: words[3]})
        owner, state = tokens['owner'], tokens['state']
        env.override(0x546D58, copy_rect)
        env.override(0x546D4C, rect_empty)
        obj = env.object(0x50, 'existing-blower', words=words * 5)
        vt = env.object(0x24, 'supplied-methods', fill=0)
        env.put(obj, vt)
        env.put(obj + 0x10, state)
        env.put(state + 0x18, obj)

        def effect(slot):
            def callback(env, call):
                env.put(call.receiver + 0x38 + (slot % 3) * 4, words[(slot + 1) % len(words)])
                env.put(state + 0x28, words[(slot + 2) % len(words)])
                if mutate:
                    env.put(state + 0x1C, 1000)
                    env.put(state + 0x18, replacement)
                    if slot == 4:
                        env.put(call.receiver, second_vt)
                return words[slot % len(words)]
            return callback

        replacement = env.object(0x50, 'replacement-blower', words=list(reversed(words)) * 5)
        second_vt = env.object(0x24, 'replacement-methods', fill=0)
        for slot, argc in ((4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)):
            env.put(vt + slot, env.stub(f'blower-method-{slot}', 'thiscall', argc, effect(slot)))
            env.put(second_vt + slot, env.stub(f'changed-method-{slot}', 'thiscall', argc, effect(slot)))
        # Real dispatcher reads two CString descriptors from its numeric state table.
        if command not in (0, 29, 30, 1000):
            text = cstring(env, f'ground-state-{command:08x}', 'dispatch-text')
            table = env.object(4, 'dispatch-table', words=[text])
            env.put(0x5376A0, command, command, table, table, 4, 0, 0)
        if redirect:
            alternate = env.object(0x180, 'alternate-state', fill=0)
            env.put(alternate + 0x1C, words[2])

            def allocate_and_redirect(env, call):
                # The callback captures the old state before allocation, while
                # the real constructor subsequently reads the owner's state.
                env.put(owner + 0x6C, alternate)
                env.put(state + 0x18, replacement)
                env.put(state + 0x24, words[3])
                return env.object(call.arguments[0], 'allocated-blower',
                                  data=struct.pack('<4I', *words) * (call.arguments[0] // 16))

            env.override(0x4F63EC, allocate_and_redirect)
        return tokens
    return setup


def cases(random_source):
    for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for mutate in (False, True):
            words = [random_source.randrange(1, 0xFFFFFFFF) for _ in range(4)]
            yield Case(f'command {command:#x} mutation {mutate}', ENTRY,
                       setup_case(command, words, mutate=mutate),
                       arguments=(lambda t: t['owner'],))
    for rectangle in ((0, 0, 0, 0), (-30, -20, 70, 90), (4, 9, 4, 12),
                      (7, 3, 2, 8), (0, -4, 13, 22)):
        for mode in (0, 1, 2, 0xFFFFFFFF):
            words = [random_source.randrange(1, 0xFFFFFFFF), mode,
                     random_source.randrange(1, 0xFFFFFFFF), random_source.randrange(1, 0xFFFFFFFF)]
            yield Case(f'construct rect {rectangle} mode {mode:#x}', ENTRY,
                       setup_case(0, words, rectangle), arguments=(lambda t: t['owner'],))

    for rectangle in ((0, 0, 0, 0), (-23, 17, 46, 81)):
        words = [random_source.randrange(1, 0xFFFFFFFF) for _ in range(4)]
        yield Case(f'constructor captures state across allocation {rectangle}', ENTRY,
                   setup_case(0, words, rectangle, redirect=True),
                   arguments=(lambda t: t['owner'],))

    for publish_effect in (0, 1, 2):
        salt = random_source.randrange(1, 0xFFFFFFFF)

        def aliased_construction(env, publish_effect=publish_effect, salt=salt):
            tokens = world(env, state_words={0x1C: 0, 0x24: salt})
            old_owner, state = tokens['owner'], tokens['state']
            owner = env.object(0x300, 'backed-owner-and-blower', fill=0)
            env.write(owner, env.read(old_owner, 0x200))
            env.put(owner + 0x118, -30, -20, 70, 90)
            env.put(owner + 0x18C, owner)
            obj = owner + 0x194
            frame = env.object(0x40, 'animation-frame-and-method-table', fill=0)
            frames = env.object(4, 'animation-frames', words=[frame])
            sequence = env.object(0x14, 'animation-sequence', fill=0)
            env.put(sequence + 0xC, frames, 1)
            env.put(frame + 0xC, 9)
            env.put(frame + 0x1C, 71)

            def initialized(env, call):
                env.put(owner + 0x250, env.get(state + 0x18), env.get(state + 0x1C), salt)
                env.put(call.receiver + 0x40, salt ^ 0x76124123)
                if publish_effect == 1:
                    env.put(state + 0x18, owner + 0x240)
                elif publish_effect == 2:
                    env.put(owner + 0x6C, old_owner)
                return salt

            env.put(frame + 0x10, env.stub('aliased-initialization', 'thiscall', 0, initialized))
            from clawparity.world import resource_manager
            manager = resource_manager(env, {b'LEVEL_GROUNDBLOWER': sequence}, name='aliased-animations')
            env.put(tokens['world'] + 0x2C, manager)
            env.put(state + 0x18, owner + 0x230)
            env.override(0x546D58, copy_rect)
            env.override(0x546D4C, rect_empty)

            def backed_alias(env, call):
                if call.arguments[0] != 0x50:
                    return env.object(call.arguments[0], 'other-allocation', fill=0)
                return obj

            env.override(0x4F63EC, backed_alias)
            tokens['owner'] = owner
            return tokens

        yield Case(f'constructor animation aliases final method table effect {publish_effect}', ENTRY,
                   aliased_construction, arguments=(lambda t: t['owner'],))
