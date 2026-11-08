"""Original-only cases for audio metadata, voice pools and RIFF scanning."""
import struct
from clawparity.cases import Case

NEW = 0x4F63EC


def silence(env):
    for address in (0x54130C, 0x541310, 0x541314, 0x541318):
        env.put(address, 0)


def buffer_interface(env, tag, values, errors=(0, 0, 0), mutate=False):
    interface = env.object(8, tag + '-interface', fill=0x9B)
    tables = [env.object(0x48, tag + '-vtable-' + str(i), fill=0x67) for i in range(3)]
    observations = env.object(3 * 80, tag + '-observations', fill=0xCD)
    env.put(interface, tables[0])
    alternate = env.object(8, tag + '-alternate-interface', words=[tables[0], 0xA13579BD])
    alternate_owner = env.object(0x80, tag + '-alternate-owner', fill=0x7F)
    env.put(alternate_owner + 0x78, 0)
    for stage, offset in enumerate((0x20, 0x1C, 0x18)):
        def get(env, call, stage=stage, offset=offset):
            obj, output = call.arguments
            target = output - (0x18 + 4 * stage)
            record = observations + stage * 80
            env.put(record, call.receiver, obj, output, env.get(obj))
            env.write(record + 16, env.read(target, 56))
            env.put(output, values[stage])
            if mutate and stage < 2:
                env.put(interface, tables[stage + 1])
                env.put(target + 0x0C, alternate)
            if mutate and stage == 2:
                env.put(target + 0x10, alternate_owner, values[0] | 1)
            return errors[stage]
        for table_index, table in enumerate(tables):
            def routed(env, call, get=get, table_index=table_index, stage=stage):
                env.put(observations + stage * 80 + 72, table_index)
                return get(env, call)
            env.put(table + offset, env.stub(tag + '-get-' + str(stage) + '-' + str(table_index), 'stdcall', 2, routed))
    return interface


def base_setup(payload, values, errors=(0, 0, 0), absent=False, mutate=False):
    def setup(env):
        silence(env)
        target = env.object(64, 'target', data=payload[:64])
        owner = env.object(0x80, 'owner', fill=0xA9)
        source = 0 if absent else buffer_interface(env, 'source', values, errors, mutate)
        return dict(target=target, owner=owner, source=source)
    return setup


def pool_setup(payload, values, enabled=True, failure=False, duplicate_error=0, mode=7,
               states=(), status_error=0, mutate=False):
    def setup(env):
        silence(env)
        resource = env.object(56, 'resource', data=payload[:56])
        owner = env.object(0x80, 'manager', fill=0x57)
        replacement_owner = env.object(0x80, 'replacement-manager', fill=0x83)
        source = buffer_interface(env, 'resource-buffer', values, mutate=mutate)
        device = env.object(8, 'device', fill=0x6D)
        table = env.object(0x48, 'device-vtable', fill=0x41)
        env.put(device, table)
        env.put(owner + 0x78, int(enabled))
        env.put(owner + 0x14, device)
        env.put(replacement_owner + 0x78, 1)
        env.put(replacement_owner + 0x14, device)
        env.put(resource + 0x0C, source, owner)
        env.put(resource + 0x18, *values)
        env.put(resource + 0x30, 0, 0)
        record = env.object(256, 'pool-observations', fill=0xEF)
        duplicate = buffer_interface(env, 'duplicate-buffer', tuple(v ^ 0x31313131 for v in values))
        def dup(env, call):
            env.put(record, call.receiver, *call.arguments)
            env.write(record + 16, env.read(resource, 56))
            voice = call.arguments[2] - 0x0C
            env.write(record + 72, env.read(voice, 56))
            env.put(call.arguments[2], duplicate)
            if mutate:
                env.put(resource + 0x10, replacement_owner)
            return duplicate_error
        env.put(table + 0x14, env.stub('DuplicateSoundBuffer', 'stdcall', 3, dup))
        def alloc(env, call):
            env.put(record + 128, call.arguments[0], env.get(resource + 0x10))
            if mutate:
                env.put(resource + 0x10, replacement_owner)
            return 0 if failure else env.object(call.arguments[0], 'voice-allocation', data=payload[:call.arguments[0]])
        env.override(NEW, alloc)
        voices = []
        for i, (eligible, playing) in enumerate(states):
            voice = env.object(56, 'voice-' + str(i), data=payload[:56])
            iface = buffer_interface(env, 'voice-' + str(i), values)
            vt = env.get(iface)
            obs = env.object(128, 'voice-observations-' + str(i), fill=0xB1)
            def status(env, call, playing=playing, obs=obs):
                env.put(obs, call.receiver, *call.arguments)
                env.put(call.arguments[1], playing)
                return status_error
            env.put(vt + 0x24, env.stub('GetStatus-' + str(i), 'stdcall', 2, status))
            for j, offset in enumerate((0x3C, 0x40, 0x44)):
                def setter(env, call, j=j, obs=obs):
                    env.put(obs + 16 + j * 16, call.receiver, *call.arguments)
                    if mutate:
                        env.put(resource + 0x18, values[0] ^ (j + 1), values[1] ^ (j + 2), values[2] ^ (j + 3))
                    return 0
                env.put(vt + offset, env.stub('setter-' + str(i) + '-' + str(j), 'stdcall', 2, setter))
            env.put(voice + 0x0C, iface, owner)
            env.put(voice + 0x30, eligible)
            voices.append(voice)
        if voices:
            env.put(resource + 0x30, voices[0] + 4, voices[-1] + 4)
            for i, voice in enumerate(voices):
                env.put(voice + 4, voices[i + 1] + 4 if i + 1 < len(voices) else 0,
                        voices[i - 1] + 4 if i else 0)
        return dict(target=resource, mode=mode)
    return setup


def manager_setup(payload, values, size=117, rate=8000, enabled=True, format_tag=1,
                  null_format=False, error=0, null_output=False, mutate=False, existing=False):
    def setup(env):
        silence(env)
        manager = env.object(0x80, 'manager', fill=0x7D)
        device = env.object(8, 'device', fill=0x49)
        vt = env.object(16, 'device-vtable', fill=0x3B)
        env.put(device, vt)
        env.put(manager + 0x78, int(enabled))
        env.put(manager + 0x14, device)
        if existing:
            old = env.object(16, 'existing-resource-node', fill=0x83)
            env.put(old, 0, 0)
            env.put(manager + 4, old, old)
        else:
            env.put(manager + 4, 0, 0)
        fmt = env.object(24, 'format', data=payload[:24])
        env.write(fmt, struct.pack('<HHIIHHH', format_tag, 2, 44100, rate, 4, 16, 0x3719))
        interface = buffer_interface(env, 'created-buffer', values, mutate=mutate)
        obs = env.object(160, 'create-observations', fill=0xD7)
        def create(env, call):
            obj, desc, output, outer = call.arguments
            env.put(obs, call.receiver, obj, desc, output, outer)
            env.write(obs + 20, env.read(desc, 20))
            env.write(obs + 40, env.read(env.get(desc + 16), 18))
            env.put(obs + 60, env.get(output))
            env.put(output, 0 if null_output else interface)
            if mutate:
                env.put(fmt + 8, rate + 17)
            return error
        env.put(vt + 12, env.stub('CreateSoundBuffer', 'stdcall', 4, create))
        def alloc(env, call):
            env.put(obs + 64, call.arguments[0])
            if mutate:
                env.put(fmt + 8, rate + 41)
            return env.object(call.arguments[0], 'resource-allocation', data=payload[:call.arguments[0]])
        env.override(NEW, alloc)
        return dict(target=manager, fmt=0 if null_format else fmt, size=size)
    return setup


def riff_setup(payload, chunks, riff=b'RIFF', wave=b'WAVE', size_override=None, alias=False):
    def setup(env):
        blob = wave
        for name, data in chunks:
            blob += name + struct.pack('<I', len(data)) + data + (b'\x91' if len(data) & 1 else b'')
        raw = riff + struct.pack('<I', len(blob) if size_override is None else size_override) + blob
        src = env.object(len(raw) + 16, 'riff', data=raw + payload[:16])
        out = env.object(16, 'outputs', data=payload[:16])
        return dict(src=src, fmt=out, data=out if alias else out + 4, size=out + 8)
    return setup


def cases(random_source):
    for sample in range(4):
        payload = bytes(random_source.randrange(256) for _ in range(128))
        values = tuple(random_source.getrandbits(32) for _ in range(3))
        for function, argc in ((0x4B3CB0, 2), (0x4B4200, 2), (0x4B46B0, 3)):
            for absent, errors, mutate in ((True, (0, 0, 0), False), (False, (0, 0, 0), False),
                                            (False, (1, 0x80004005, 0xFFFFFFFF), True)):
                yield Case(f'construct {function:x} {sample} {absent} {errors}', function,
                           base_setup(payload, values, errors, absent, mutate), receiver=lambda t: t['target'],
                           arguments=(lambda t: t['source'], lambda t: t['owner']) + ((values[0],) if argc == 3 else ()))
        for mode in (0, 1, 0xFFFFFFFF, values[0]):
            yield Case(f'allocate mode {sample} {mode}', 0x4B42E0,
                       pool_setup(payload, values, mode=mode, mutate=True), receiver=lambda t: t['target'], arguments=(mode,))
        for options in (dict(enabled=False), dict(failure=True), dict(duplicate_error=1), dict(duplicate_error=0x80004005)):
            yield Case(f'allocate failure {sample} {options}', 0x4B42E0, pool_setup(payload, values, **options),
                       receiver=lambda t: t['target'], arguments=(values[2],))
        for states in ((), ((0, 0),), ((1, 1),), ((1, 0),), ((0, 1), (1, 1), (1, 0), (1, 0)),
                       ((1, 0), (1, 1)), ((1, 1), (0, 0))):
            yield Case(f'acquire {sample} {states}', 0x4B4430, pool_setup(payload, values, states=states, mutate=True), receiver=lambda t: t['target'])
        yield Case(f'acquire disabled {sample}', 0x4B4430, pool_setup(payload, values, enabled=False), receiver=lambda t: t['target'])
        yield Case(f'acquire status failure {sample}', 0x4B4430, pool_setup(payload, values, states=((1, 0),), status_error=1), receiver=lambda t: t['target'])
        for options in (dict(size=0), dict(null_format=True), dict(enabled=False), dict(format_tag=0),
                        dict(format_tag=0xFFFF), dict(error=1), dict(error=0x80004005), dict(null_output=True),
                        dict(), dict(size=1, rate=1), dict(size=0xFFFFFFFF, rate=0xFFFFFFFF),
                        dict(size=0x80000001, rate=137, mutate=True, existing=True)):
            yield Case(f'create {sample} {options}', 0x4B48B0, manager_setup(payload, values, **options),
                       receiver=lambda t: t['target'], arguments=(lambda t: t['fmt'], lambda t: t['size'], values[1]),
                       initial_stack=((-0x34, payload[:0x28]),))
        for count in (0, 1, 4):
            def append_setup(env, count=count, payload=payload):
                head = env.object(8, 'list', data=payload[:8])
                nodes = [env.object(16, 'node-' + str(i), data=payload[16:32]) for i in range(count)]
                env.put(head, nodes[0] if nodes else 0, nodes[-1] if nodes else 0)
                for i, node in enumerate(nodes):
                    env.put(node, nodes[i + 1] if i + 1 < count else 0, nodes[i - 1] if i else 0)
                new = env.object(16, 'new-node', data=payload[32:48])
                return dict(target=head, node=new)
            yield Case(f'append {sample} {count}', 0x4B5240, append_setup, receiver=lambda t: t['target'], arguments=(lambda t: t['node'],))
        for alias in ('list-tail', 'old-tail'):
            def alias_setup(env, alias=alias, payload=payload):
                head = env.object(24, 'aliased-list', data=payload[:24])
                node = env.object(16, 'aliased-node', data=payload[24:40])
                env.put(head, node, node)
                env.put(node, 0, 0)
                return dict(target=head, node=head + 4 if alias == 'list-tail' else node)
            yield Case(f'append alias {sample} {alias}', 0x4B5240, alias_setup,
                       receiver=lambda t: t['target'], arguments=(lambda t: t['node'],))
        layouts = [[], [(b'fmt ', payload[:18])], [(b'data', payload[:7])],
                   [(b'fmt ', payload[:18]), (b'data', payload[:11])],
                   [(b'JUNK', b''), (b'JUNK', payload[:3]), (b'fmt ', payload[:1]), (b'fmt ', payload[:21]), (b'data', b'')],
                   [(b'fmt ', b''), (b'data', payload[:2]), (b'fmt ', payload[:4])]]
        for i, chunks in enumerate(layouts):
            for alias in (False, True):
                yield Case(f'riff {sample} {i} {alias}', 0x4B4E30, riff_setup(payload, chunks, alias=alias),
                           arguments=tuple((lambda t, k=k: t[k]) for k in ('src', 'fmt', 'data', 'size')))
        for options in (dict(riff=b'RIFX'), dict(wave=b'AVI '), dict(size_override=0), dict(size_override=4)):
            yield Case(f'riff invalid {sample} {options}', 0x4B4E30, riff_setup(payload, [], **options),
                       arguments=tuple((lambda t, k=k: t[k]) for k in ('src', 'fmt', 'data', 'size')))
