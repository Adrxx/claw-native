"""Original-driven cannon control cases, with deterministic branch coverage."""
from clawparity.cases import Case


def cstring(env, text):
    return env.object(len(text) + 1, text, data=text.encode() + b"\0")


def resource_map(env, entries):
    table = env.object(0x30, "resource-table", fill=0)
    buckets = env.object(4, "resource-bucket", fill=0)
    head = 0
    for key, value in entries:
        head = env.object(0x10, "resource-node", words=[head, 0, cstring(env, key), value])
    env.put(buckets, head)
    env.put(table + 0x14, buckets, 1)
    return table


def state_map(env, key, value):
    node = env.object(0x14, "state-trie-node", fill=0)
    env.put(node, node, node, 0, cstring(env, key), value)
    env.put(0x537668 + 0x18, node)


def common(env, noise, boss=True, disabled=0, active=1, switch_active=1,
           sprite=True, lower=0, upper=3, animation=False, complete=0, delay=0,
           sound=True, enabled=1, state_key="LS_IDLE"):
    control = env.object(0x60, "control", data=noise[:0x60])
    obj = env.object(0x1C0, "game-object", data=noise[:0x1C0])
    logic = env.object(0x30, "logic-owner", data=noise[0x200:0x230])
    frames = [env.object(0x30, f"sprite-frame-{i}", data=noise[0x30*i:0x30*(i+1)])
              for i in range(16)]
    frame = frames[0]
    vector = env.object(0x40, "sprite-vector", words=frames)
    spr = env.object(0x70, "sprite-resource", fill=0)
    env.put(spr + 0x14, vector)
    env.put(spr + 0x64, lower & 0xffffffff, upper & 0xffffffff)
    env.put(obj + 0x6C, logic)
    env.put(obj + 0x16C, 1, spr if sprite else 0, frame if sprite else 0)
    definition = env.object(0x20, "animation-definition", fill=0)
    animframe = env.object(0x30, "animation-frame", fill=0)
    animvector = env.object(4, "animation-vector", words=[animframe])
    env.put(definition + 0x0C, animvector, 1)
    env.put(animframe + 0x1C, 0x100 + noise[0])
    previous = env.object(0x20, "previous-animation-definition", fill=0)
    previous_frame = env.object(0x30, "previous-animation-frame", fill=0)
    previous_vector = env.object(4, "previous-animation-vector", words=[previous_frame])
    env.put(previous + 0x0C, previous_vector, 1)
    env.put(previous_frame + 0x1C, 0x200 + noise[2])
    env.put(obj + 0x188, 0, obj, previous if animation else 0, previous_frame,
            0, delay, 1, complete, 0x3456, 0x789A, 0x3F800000)
    engine = env.object(0x80, "sound-engine", fill=0)
    player = env.object(0x20, "sound-player", fill=0)
    snd = env.object(0x20, "sound-resource", fill=0)
    env.put(player + 0x10, engine)
    env.put(snd + 0x10, player)
    env.put(control + 0x10, logic)
    env.put(control + 0x2C, obj)
    env.put(control + 0x48, snd if sound else 0, definition if animation else 0,
            snd if sound else 0)
    bossobj = env.object(0x530, "boss", data=noise[:0x530])
    env.put(bossobj + 0x518, switch_active, active, disabled)
    env.put(0x53774C, bossobj if boss else 0)
    env.put(0x532C0C, enabled, int.from_bytes(noise[12:16], "little"))
    env.put(0x5430C4, 3)
    state_map(env, state_key, 0x1234 + noise[1])
    return dict(control=control, obj=obj, logic=logic, sprite=spr, frame=frame,
                definition=definition, sound=snd, boss=bossobj)


def dispatch_setup(noise, base, index, callback, width, lower=1, upper=3):
    def setup(env):
        control = env.object(0x60, "dispatch-receiver", data=noise[:0x60])
        rtti = env.object(0x10, "rtti-data", data=noise[:0x10])
        meta = env.object(0x10, "rtti-metadata", fill=0)
        env.put(meta + 0x0C, rtti)
        vtable = env.object(0x10, "rtti-vtable", words=[meta, 0, 0, 0])
        env.put(control, vtable + 4)
        table = env.object((upper - lower + 1) * width, "dispatch-table", fill=0)
        fallback = env.object(width, "fallback", fill=0)
        record = env.object(0x20, "callback-observation", fill=0)
        def invoke(env, call):
            env.put(record, call.receiver, env.get(base + 0x20),
                    env.get(base + 8), env.get(base + 0x0C), env.get(control + 4))
            env.put(control + 4, 0x10203040 + noise[4])
            return 0xF00D + noise[5]
        cb = env.stub("cannon-state", "thiscall", 0, invoke)
        if lower <= index <= upper:
            env.put(table + (index - lower) * width, cb if callback else 0)
        env.put(base, 0, 0, lower, upper, table, fallback, width, 0x76543210, 0x87654321)
        return dict(control=control)
    return setup


def cases(random_source):
    noise = bytes(random_source.randrange(256) for _ in range(0x530))
    for address, base in ((0x414DE0, 0x534C28), (0x415470, 0x534C58)):
        for width in (4, 8, 12):
            for index in (0, 1, 2, 3, 4):
                for callback in (False, True):
                    if index in (0, 4) and callback:
                        continue
                    yield Case(f"dispatch-{address:x}-{width}-{index}-{callback}", address,
                               dispatch_setup(noise, base, index, callback, width),
                               receiver=lambda t: t["control"], arguments=(index,))

    for address, key in ((0x415090, "LS_IDLE"), (0x415840, "LS_IDLE")):
        for sprite in (False, True):
            for animation in (False, True):
                for lookup, sound_lookup in ((False, False), (True, True), (True, False)):
                    def setup(env, sprite=sprite, animation=animation, lookup=lookup,
                              sound_lookup=sound_lookup):
                        t = common(env, noise, sprite=sprite, animation=animation)
                        old_logic = env.object(0x30, "prior-control-owner", data=noise[0x300:0x330])
                        env.put(t["control"] + 0x10, old_logic)
                        manager = env.object(0x40, "resource-manager", fill=0)
                        obj = t["obj"]
                        entries = [("LEVEL_CANNONBUTTON", t["sprite"]),
                                   ("LEVEL_CANNONSWITCH", t["sprite"])] if sprite else []
                        sprites = resource_map(env, entries)
                        empty = resource_map(env, [])
                        anims = resource_map(env, [("LEVEL_CANNONBUTTON_IDLE", t["definition"]),
                                                  ("LEVEL_CANNONSWITCH_SWITCH", t["definition"])]) if lookup and animation else empty
                        sounds = resource_map(env, [("LEVEL_GABRIELCANNON_BUTTON1", t["sound"]),
                                                   ("LEVEL_GABRIELCANNON_SWITCH1", t["sound"])]) if sound_lookup else empty
                        env.put(manager + 0x10, sprites, empty)
                        env.put(manager + 0x28, sounds, anims)
                        env.put(obj + 0x0C, manager)
                        return t
                    yield Case(f"constructor-{address:x}-{sprite}-{animation}-{lookup}-{sound_lookup}", address,
                               setup, receiver=lambda t: t["control"], arguments=(lambda t: t["obj"],))

    for address in (0x415090, 0x415840):
        def setup(env):
            t = common(env, noise, sprite=False)
            control, obj = t["control"], t["obj"]
            old_logic = env.object(0x30, "callback-prior-owner", data=noise[0x300:0x330])
            env.put(control + 0x10, old_logic)
            observation = env.object(4 + 4 * 0x80, "constructor-observations", fill=0)

            def observe(env, call):
                count = env.get(observation)
                at = observation + 4 + count * 0x80
                env.put(at, call.receiver, len(call.arguments), *call.arguments)
                env.write(at + 0x20, env.read(control, 0x60))
                env.put(observation, count + 1)
                return 0x71310000 + noise[count]

            methods = env.object(0x28, "logic-player-methods", fill=0)
            env.put(methods + 0x1C, env.stub("logic-player-reset", "thiscall", 0, observe))
            env.put(methods + 0x24, env.stub("logic-player-load", "thiscall", 2, observe))
            hit = env.object(0x20, "hit-player", words=[methods], fill=0)
            attack = env.object(0x20, "attack-player", words=[methods], fill=0)
            env.put(obj + 0x70, hit)
            env.put(obj + 0x78, attack)
            hit_resource = env.object(0x20, "hit-logic-resource", data=noise[0x350:0x370])
            attack_resource = env.object(0x20, "attack-logic-resource", data=noise[0x380:0x3A0])
            logic_map = resource_map(env, [("LogicHit", hit_resource), ("LogicAttack", attack_resource)])
            empty = resource_map(env, [])
            manager = env.object(0x40, "callback-resource-manager", fill=0)
            env.put(manager + 0x10, empty, logic_map)
            env.put(manager + 0x28, empty, empty)
            env.put(obj + 0x0C, manager)
            return t
        yield Case(f"constructor-callback-order-{address:x}", address, setup,
                   receiver=lambda t: t["control"], arguments=(lambda t: t["obj"],))

    for address in (0x415210, 0x4159F0):
        for animation in (False, True):
            for sound, enabled in ((False, 0), (True, 0), (True, 1)):
                key = "LS_SWITCH" if address == 0x4159F0 else "LS_IDLE"
                yield Case(f"transition-{address:x}-{animation}-{sound}-{enabled}", address,
                           lambda env, a=animation, s=sound, e=enabled, k=key: common(env, noise, animation=a, sound=s, enabled=e, state_key=k),
                           receiver=lambda t: t["control"])

    for boss, disabled, active in ((False, 0, 1), (True, 1, 1), (True, 0, 0), (True, 0, 1)):
        for sprite, lower, upper in ((False, 0, 3), (True, 0, 3), (True, 2, 2),
                                    (True, 3, 4), (True, 0, 1), (True, -2, 0),
                                    (True, -2, 3), (True, -0x80000000, 2),
                                    (True, 2, 0x7fffffff),
                                    (True, -0x80000000, -1)):
            yield Case(f"button-idle-{boss}-{disabled}-{active}-{sprite}-{lower}-{upper}", 0x415250,
                       lambda env,b=boss,d=disabled,a=active,s=sprite,l=lower,u=upper: common(env,noise,boss=b,disabled=d,active=a,sprite=s,lower=l,upper=u),
                       receiver=lambda t:t["control"])

    for index in (0, 1, 2, 3, 0xffffffff):
        for boss, disabled in ((False,0),(True,1),(True,0)):
            for latch in (0, 1, 0xffffffff):
                for sound, enabled in ((False,0),(True,0),(True,1)):
                    def setup(env,i=index,b=boss,d=disabled,l=latch,s=sound,e=enabled):
                        t=common(env,noise,boss=b,disabled=d,sound=s,enabled=e)
                        env.put(t["control"]+0x50,l)
                        env.put(t["obj"]+0x16C,i)
                        return t
                    yield Case(f"button-hit-{index}-{boss}-{disabled}-{latch}-{sound}-{enabled}",0x4152E0,
                               setup,receiver=lambda t:t["control"])

    for boss,disabled,active in ((False,0,1),(True,1,1),(True,0,0),(True,0,1)):
        for animation in (False,True):
            yield Case(f"switch-idle-{boss}-{disabled}-{active}-{animation}",0x4159B0,
                       lambda env,b=boss,d=disabled,a=active,n=animation: common(env,noise,boss=b,disabled=d,switch_active=a,animation=n,complete=1,delay=5,state_key="LS_SWITCH"),
                       receiver=lambda t:t["control"])
    for complete,delay in ((0,0),(0,5),(1,0),(1,5),(0xffffffff,0)):
        for animation in (False,True):
            yield Case(f"switch-complete-{complete}-{delay}-{animation}",0x415A60,
                       lambda env,c=complete,d=delay,a=animation: common(env,noise,complete=c,delay=d,animation=a),
                       receiver=lambda t:t["control"])

    for sound in (False, True):
        for neighbor_sound in (False, True):
            def setup(env, sound=sound, neighbor_sound=neighbor_sound):
                t = common(env, noise, sound=sound)
                env.put(t["control"] + 0x50, 0)
                # Back the neighboring animation slot as a sound-shaped
                # sentinel so a shifted read stays valid for comparison.
                env.put(t["control"] + 0x4C, t["sound"] if neighbor_sound else 0)
                return t
            yield Case(f"button-sound-neighbor-{sound}-{neighbor_sound}", 0x4152E0,
                       setup, receiver=lambda t: t["control"])

    for address in (0x4152E0, 0x4159F0):
        def setup(env, address=address):
            t = common(env, noise, animation=False, state_key="LS_SWITCH")
            env.put(t["control"] + 0x50, 0 if address == 0x4152E0 else t["sound"])
            engine = env.object(0x80, "live-sound-engine", fill=0)
            env.put(engine + 0x78, 1)
            player = env.object(0x40, "live-sound-player", fill=0)
            record = env.object(4 + 16 * 0x30, "sound-observations", fill=0)
            buffer = env.object(4, "sound-buffer", fill=0)
            methods = env.object(0x48, "sound-buffer-methods", fill=0)
            interface = env.object(4, "directsound-interface", fill=0)
            interface_methods = env.object(0x18, "directsound-interface-methods", fill=0)

            def observe(env, call):
                count = env.get(record)
                at = record + 4 + count * 0x30
                env.put(at, len(call.arguments), *call.arguments)
                env.put(at + 0x18, env.get(t["control"] + 0x50),
                        env.get(t["boss"] + 0x51C), env.get(t["logic"] + 0x1C))
                env.put(record, count + 1)
                return 0

            def getter(value):
                def get(env, call):
                    observe(env, call)
                    env.put(call.arguments[1], value)
                    return 0
                return get

            def duplicate(env, call):
                observe(env, call)
                env.put(call.arguments[2], buffer)
                return 0

            for offset, value in ((0x18, 0x34), (0x1C, 0x23), (0x20, 22050)):
                env.put(methods + offset, env.stub(f"sound-buffer-get-{offset:x}", "stdcall", 2,
                                                  getter(value), arguments=("u32", "out:4")))
            for offset in (0x3C, 0x40, 0x44):
                env.put(methods + offset, env.stub(f"sound-buffer-set-{offset:x}", "stdcall", 2, observe))
            env.put(methods + 0x30, env.stub("sound-buffer-play", "stdcall", 4, observe))
            env.put(interface_methods + 0x14, env.stub("duplicate-sound-buffer", "stdcall", 3,
                                                       duplicate, arguments=("u32", "u32", "out:4")))
            env.put(buffer, methods)
            env.put(interface, interface_methods)
            env.put(engine + 0x14, interface)
            env.put(player + 0x0C, buffer)
            env.put(player + 0x10, engine)
            env.put(t["sound"] + 0x10, player)
            env.put(0x532C10, 2)
            env.put(0x541178 + 8, 0x456)
            env.put(0x541308, 0x789)
            return t
        yield Case(f"observable-sound-{address:x}", address, setup,
                   receiver=lambda t: t["control"])
