"""Original-only reset cases with distinct object fields and real helper execution."""
from clawparity.cases import Case

ROOT = 0x420170


def state(seed, facing=0, carried=None, activity=1, restore=0, present=False,
          skip=False, mutate=False, sentinel=False, alias=None, input_alias=None, audio=False, input_player=None, record_alias=None, bit_alias=False):
    def setup(env):
        def obj(size, name):
            return env.object(size, name, words=[(seed + 0x1020304 * (i + 1)) & 0xffffffff
                                              for i in range(size // 4)])
        player = obj(0x500, 'player')
        primary = obj(0x20, 'primary')
        private = obj(0x130, 'private') if alias is None else player + alias
        input_ = obj(0x10, 'input') if input_alias is None else private + input_alias - 0xc
        if input_player is not None:
            input_ = player + input_player - 0xc
        world = obj(0x30, 'world')
        registry = env.object(0x30, 'registry', fill=0)
        env.put(0x537e88, player)
        env.put(0x537204, input_)
        env.put(input_ + 0xc, seed | 0x03000000)
        env.put(0x534e60, *[(seed ^ (0x11111111 * i)) & 0xffffffff for i in range(1, 7)])
        env.put(player + 8, seed & 0xffffff7f)
        env.put(player + 0xc, world)
        env.put(world + 0x2c, registry)
        env.put(registry + 0x18, 1)  # one hash bucket, absent map by default
        env.put(player + 0x6c, primary)
        env.put(primary + 0x14, private)
        env.put(primary + 0x1c, 0x1391 if skip else seed)
        env.put(private, facing, restore)
        env.put(private + 0x12c, 0)
        env.put(player + 0x18c, player)  # animation owner
        env.put(player + 0x138, 0x80000000 if sentinel else 0xffffffdd,
                0xfffffff9, 0x49, 0x63)
        env.put(0x5430c4, 0)
        ani = env.object(0x20, 'animation', fill=0)
        frame = (env.object(0x30, 'animation-frame', fill=0) if record_alias is None
                 else private + record_alias)
        frames = env.object(4, 'frames', words=[frame])
        env.put(ani + 0xc, frames, 1)
        if record_alias is None:
            env.put(frame + 0x1c, 0x10000)
        env.put(private + 0x124, ani if restore != 2 else 0)
        if present:
            bucket = env.object(4, 'bucket', fill=0)
            node = env.object(0x10, 'stand-resource', words=[0, 0, 0x5246d0, ani])
            env.put(bucket, node)
            env.put(registry + 0x14, bucket)
        if audio:
            # Real ANI event -> sound resource -> existing voice -> DirectSound COM methods.
            resource = env.object(0x20, 'sound-resource', fill=0)
            sound = env.object(0x38, 'sound', fill=0)
            voice = env.object(0x38, 'voice', fill=0)
            system = env.object(0x80, 'sound-system', fill=0)
            interface = env.object(4, 'DirectSound-buffer', fill=0)
            methods = env.object(0x48, 'DirectSound-methods', fill=0)
            receipt = env.object(0x600, 'sound-observations', fill=0)
            env.put(frame + 0x2c, resource)
            env.put(frame + 0x18, 99)  # finish this update after the sound event
            env.put(resource + 0x10, sound)
            env.put(sound + 0x10, system)
            env.put(sound + 0x30, voice + 4, voice + 4)
            env.put(voice + 0xc, interface, system)
            env.put(voice + 0x18, 22050)
            env.put(voice + 0x30, 1)
            env.put(system + 0x78, 1)
            env.put(interface, methods)
            env.put(0x532c0c, 1)
            env.put(0x532c10, 0)
            def observe(env, call):
                index = env.get(receipt)
                at = receipt + 4 + index * 0xc0
                env.put(receipt, index + 1)
                env.put(at, call.receiver, len(call.arguments), *call.arguments)
                env.write(at + 0x20, env.read(private, 0x40))
                env.write(at + 0x60, env.read(player + 0x118, 0x30))
                env.put(at + 0x90, env.get(primary + 0x1c), env.get(player + 8),
                        env.get(player + 0xcc), env.get(player + 0x148),
                        env.get(private + 0x12c), env.get(private + 0x114))
                if index == 0:
                    env.put(private, 0 if facing else 7)
                    env.put(player + 8, 0x13572410)
                    env.put(private + 4, 0x97)
                    env.put(private + 0x20, 0x68)
                return 0
            def status(env, call):
                env.put(call.arguments[1], 0)
                return 0
            env.put(methods + 0x24, env.stub('DirectSound::GetStatus', 'stdcall', 2, status))
            for slot, argc, label in ((0x3c, 2, 'SetVolume'), (0x40, 2, 'SetPan'),
                                      (0x44, 2, 'SetFrequency'), (0x30, 4, 'Play')):
                env.put(methods + slot, env.stub('DirectSound::' + label, 'stdcall', argc, observe))
        env.put(private + 0x12c, 0)
        if carried is not None:
            actor = obj(0x70, 'carried-actor')
            cp = obj(0x20, 'carried-primary')
            enemy = obj(0x304, 'enemy-private')
            error = env.object(0x20, 'bit-error', fill=0)
            env.put(error + 0xc, 4)
            env.put(actor + 0x6c, cp)
            env.put(cp + 0x18, enemy)
            env.put(private + 0x12c, actor)
            env.put(enemy + 0x20, activity)
            env.put(enemy + 0x2f8, error)
            env.put(enemy + 0x2fc, carried)
            if carried > 32:
                bits = private + 4 if bit_alias else obj(16, 'external-bits')
                env.put(enemy + 0x300, bits)
            else:
                env.put(enemy + 0x300, seed & 0xfffffffe)
            if mutate:
                receipt = env.object(32, 'allocation-observations', fill=0)
                def allocation(env, call):
                    env.put(receipt, call.receiver, call.arguments[0],
                            env.get(private + 0x12c), env.get(primary + 0x1c),
                            env.get(input_ + 0xc), env.get(enemy + 0x14),
                            env.get(private + 0x20), env.get(private + 0x3c))
                    env.put(private, 0 if facing else 9)
                    env.put(player + 8, 0x76543210)
                    return env.object(call.arguments[0], 'allocated-bits', fill=0)
                env.override(0x4a48e0, allocation)
        return {}
    return setup


def cases(random_source):
    def no_player(env):
        env.put(0x537e88, 0)
    yield Case('null player', ROOT, no_player)
    yield Case('already staged leaves everything untouched', ROOT, state(0xa5a5a5a5, skip=True))
    for facing in (0, 1, 0xffffffff, 0x80000000):
        for restore in (0, 1, 2):
            seed = random_source.getrandbits(32)
            yield Case(f'facing {facing:x} restore {restore}', ROOT,
                       state(seed, facing=facing, restore=restore, sentinel=restore == 2))
    for capacity in (0, 1, 31, 32, 33, 64, 0xffffffff):
        for activity in (0x80000000, 0, 1, 0x7fffffff):
            seed = random_source.getrandbits(32)
            yield Case(f'carried capacity {capacity} activity {activity:x}', ROOT,
                       state(seed, carried=capacity, activity=activity,
                             facing=activity & 1, restore=1))
    for facing in (0, 1):
        yield Case(f'allocation changes facing from {facing}', ROOT,
                   state(random_source.getrandbits(32), carried=0, facing=facing, mutate=True))
        yield Case(f'found stand animation facing {facing}', ROOT,
                   state(random_source.getrandbits(32), facing=facing, present=True, restore=1))

    for facing in (0, 1):
        yield Case(f'sound callbacks mutate facing {facing}', ROOT,
                   state(random_source.getrandbits(32), facing=facing, present=True, audio=True))
    for offset in (4, 0x14, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38, 0x40, 0x44, 0x4c, 0x50):
        for facing in (0, 1):
            yield Case(f'private aliases player+{offset:x} facing {facing}', ROOT,
                       state(random_source.getrandbits(32), facing=facing, alias=offset))
    for offset in (0, 4, 0x20, 0x3c, 0xfc, 0x114, 0x118, 0x120):
        yield Case(f'input flags alias private+{offset:x}', ROOT,
                   state(random_source.getrandbits(32), input_alias=offset))

    for facing in (0, 1):
        for present in (False, True):
            yield Case(f'input flags alias animation resource facing {facing} present {present}', ROOT,
                       state(random_source.getrandbits(32), facing=facing, restore=1,
                             present=present, input_player=0x190))
        yield Case(f'sound sees restored flags facing {facing}', ROOT,
                   state(random_source.getrandbits(32), facing=facing, restore=1,
                         present=True, audio=True))
        for record_alias in (4, 0x20):
            yield Case(f'saved ANI record aliases private+{record_alias:x} facing {facing}', ROOT,
                       state(random_source.getrandbits(32), facing=facing, restore=1,
                             record_alias=record_alias))
    for offset in (0x70, 0x74, 0x78):
        for facing in (0, 1):
            yield Case(f'saved ANI aliases animation state private+{offset:x} facing {facing}', ROOT,
                       state(random_source.getrandbits(32), facing=facing, restore=1, alias=offset))

    for activity in (0, 1):
        yield Case(f'carried bits alias restore flag activity {activity}', ROOT,
                   state(random_source.getrandbits(32), facing=0, restore=1, alias=0x74,
                         carried=33, activity=activity, bit_alias=True))
