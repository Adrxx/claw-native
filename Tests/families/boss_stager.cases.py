"""Original BossStager state transitions in synthetic, backed worlds."""
from clawparity.cases import Case
from clawparity.world import world, resource_manager, sprite, set_rect

ENTRY = 0x48DED0


def setup_case(state_id, words, *, active=0, enemy=True, hit=False,
               muted=0, audio=1, same_order=False, scene=False, view=True, fail_attack=False, sound_play=False, lookup_keys=None, switch_sounds=False):
    def setup(env):
        logic = env.object(0x40, "scene-logic", fill=0)
        env.put(logic + 8, 2)
        observations = env.object(0x400, "scene-observations", fill=0)
        def publish(env, call):
            created = call.arguments[0]
            env.put(observations, created, call.receiver,
                    env.get(created + 8), env.get(created + 0x68),
                    env.get(created + 0x180), env.get(0x53c9c0))
            env.put(observations + 0x18, *[env.get(created + o) for o in (0x4c, 0x50, 0x64, 0x6c)])
            env.put(observations + 0x28, env.get(st + 0x1c), env.get(st + 0x20),
                    env.get(layer + 0x14), env.get(0x52be14), env.get(0x52be18))
            if sound_play:
                env.put(player + 0xbc, active ^ 1)
                env.put(foe + 0x4c, words[11] ^ 0x44556677, words[10] ^ 0x778899aa)
            env.put(created + 0x104, words[0])
            return words[1]
        env.put(logic + 0x10, env.stub("scene-published", "cdecl", 1, publish))
        title = sprite(env, 53, 29, (7, 11))
        # Frame one is backed independently from frame zero.
        frames = env.object(8, "title-frames", words=[words[1], words[2]])
        env.put(title + 0x14, frames)
        env.put(title + 0x64, 0, 1)
        resources = {"sprites": {"LEVEL_BOSSNAME": title} if hit else {},
                     "logic": dict(([ ("BossHealthMeter", logic)] if scene else []) +
                                   ([("BossStagerAttack", logic)] if hit else []))}
        tokens = world(env, resources=resources)
        owner, context, st = tokens["owner"], tokens["world"], tokens["state"]
        env.override(0x546D5C, set_rect)
        if fail_attack:
            env.override(0x4F63EC, lambda env, call: 0)
        for offset, value in zip((8, 0x40, 0x4c, 0x50, 0x54, 0x58, 0x5c, 0x60), words):
            env.put(owner + offset, value)
        env.put(owner + 0x64, 8000 if same_order else 17)
        env.put(st + 0x1c, state_id, words[3])
        display = env.object(0x30, "display", fill=0)
        dimensions = env.object(0x20, "dimensions", fill=0)
        env.put(context + 4, display)
        env.put(display + 0x10, dimensions)
        env.put(dimensions + 0x10, words[8], words[9])
        game = env.object(0x50, "game", fill=0)
        if view:
            viewport = env.object(0x30, "viewport", fill=0)
            rectangle = env.object(0x20, "rectangle", fill=0)
            env.put(game + 0x30, viewport)
            env.put(viewport + 0x24, rectangle)
            env.put(rectangle + 0x10, *words[4:8])
        if state_id == 0 and hit:
            interface = env.object(4, "game-interface", fill=0)
            methods = env.object(0x64, "game-interface-methods", fill=0)
            env.put(interface, methods)
            env.put(game + 0x2c, interface)
            def ready(env, call):
                env.put(observations + 0x30, call.receiver, env.get(st + 0x1c))
                return 3
            def reset(env, call):
                env.put(observations + 0x38, call.receiver,
                        env.get(owner + 8), env.get(owner + 0x40))
                env.put(owner + 8, words[0] ^ 0xaaaa55aa)
                env.put(owner + 0x40, words[1] ^ 0x55aaaa55)
                return words[2]
            env.put(methods + 0x10, env.stub("game-ready", "thiscall", 0, ready))
            env.put(methods + 0x60, env.stub("game-reset", "thiscall", 0, reset))
        env.put(0x5371fc, game)
        player = env.object(0x200, "player", fill=0)
        env.put(player + 0xbc, active)
        env.put(0x537960, player)
        foe = env.object(0x200, "enemy", fill=0)
        foe_state = env.object(0x180, "enemy-state", fill=0)
        env.put(foe + 0x6c, foe_state)
        env.put(foe + 0x4c, words[10], words[11])
        env.put(0x5349dc, foe if enemy else 0)
        env.put(0x537e88, 0)
        env.put(0x53c9a4, owner)
        env.put(0x53c9ac, foe)
        env.put(0x532c0c, audio)
        env.put(0x532c10, words[12])
        env.put(0x5430c4, words[13])
        env.put(0x541328, words[14])
        env.put(0x53c260, words[15])
        env.put(0x52be14, words[10] ^ 0x3344, words[11] ^ 0x7788)
        sound_entries = {}
        for i, name in enumerate(("GAME_SDPT1", "GAME_SDPT2", "LEVEL_DEFEAT", "LEVEL_STAGING_CLAW", "LEVEL_STAGING_ENEMY")):
            item = env.object(0x40, name, fill=0)
            body = env.object(0x90, name + "-body", fill=0)
            sound = env.object(0x90, name + "-sound", fill=0)
            env.put(item + 0x10, body)
            env.put(body + 0x10, sound)
            env.put(body + 0x28, words[16] + i * 37)
            if sound_play:
                env.put(sound + 0x78, 1)
                voice = env.object(0x40, name + "-voice", fill=0)
                interface = env.object(4, name + "-buffer", fill=0)
                methods = env.object(0x48, name + "-buffer-methods", fill=0)
                env.put(interface, methods)
                env.put(body + 0x30, voice + 4, voice + 4)
                env.put(voice + 0xc, interface, sound)
                env.put(voice + 0x18, 22050)
                env.put(voice + 0x30, 1)
                def observe(slot, index, argc):
                    def effect(env, call):
                        at = observations + 0x50 + index * 0x90 + slot * 0x18
                        env.put(at, *call.arguments)
                        env.put(at + 0x10, env.get(st + 0x1c), env.get(owner + 0x50))
                        if slot == 4:
                            env.put(observations + 0x350 + index * 8,
                                    env.get(0x53c260), env.get(context + 0x28))
                            env.put(owner + 0x54, words[4] ^ (index + 1))
                            if switch_sounds and index == 1:
                                env.put(context + 0x28, replacement_sounds)
                        return 0
                    return env.stub(name + "-service-" + str(slot), "stdcall", argc, effect)
                for slot, offset, argc in ((0, 0x24, 2), (1, 0x3c, 2),
                                            (2, 0x40, 2), (3, 0x44, 2), (4, 0x30, 4)):
                    env.put(methods + offset, observe(slot, i, argc))
            if hit and (lookup_keys is None or name in lookup_keys):
                sound_entries[name] = item
        sounds = resource_manager(env, sound_entries, name="boss-sounds")
        replacement_sounds = resource_manager(env, {}, name="replacement-sounds")
        env.put(replacement_sounds + 0x30, 1)
        env.put(sounds + 0x30, muted)
        env.put(context + 0x28, sounds)
        layer = env.object(0x40, "scene-layer", fill=0)
        env.put(layer + 0xc, context)
        env.put(layer + 0x28, 4)  # CPtrList allocation block size.
        env.put(context + 8, layer)
        return tokens
    return setup


def cases(random_source):
    for state in (0, 1, 7999, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 0xffffffff):
        for variant in range(4):
            words = [random_source.getrandbits(32) for _ in range(17)]
            words[8:10] = [641 if variant & 1 else -643, 483 if variant & 2 else -485]
            words[13] = (0, 1, 17, 0xffffffff)[variant]
            words[0] = 0x12345
            words[2] = 0x6789a
            if state in (8001, 8002):
                # Movement coordinates straddle both signed threshold outcomes.
                words[2 if state == 8002 else 3] = (-2000, 2000, -1, 0x7fffffff)[variant]
            yield Case(f"state {state} variant {variant}", ENTRY,
                       setup_case(state, words, active=variant & 1, enemy=bool(variant & 2),
                                  hit=bool(variant & 1), muted=variant == 2,
                                  audio=variant != 3, same_order=bool(variant & 2),
                                  scene=state == 8003, view=bool(variant & 1)),
                       arguments=(lambda t: t["owner"],))

    words = [random_source.getrandbits(32) for _ in range(17)]
    words[8:10] = [643, 485]
    words[13] = 17
    yield Case("attack controller allocation fails", ENTRY,
               setup_case(0, words, hit=True, fail_attack=True),
               arguments=(lambda t: t["owner"],))
    for axis_state, coordinate_index, threshold in ((8001, 3, 161), (8002, 2, 964)):
        for delta in (-1, 0, 1):
            words = [random_source.getrandbits(32) for _ in range(17)]
            words[8:10] = [643, 483]
            words[13] = 0
            words[coordinate_index] = threshold + delta
            yield Case(f"movement {axis_state} boundary {delta}", ENTRY,
                       setup_case(axis_state, words, hit=True),
                       arguments=(lambda t: t["owner"],))

    for state in (8000, 8001, 8003, 8004, 8005, 8006, 8007, 8008):
        for variant in range(8):
            words = [random_source.getrandbits(32) for _ in range(17)]
            flag_mask = 0x70004
            words[0] = (words[0] & ~flag_mask) | (flag_mask if variant & 1 else 0)
            words[1] = (words[1] & ~3) | (3 if variant & 2 else 0)
            words[8:10] = [641 + variant, 483 + variant]
            words[13] = (0, 1, 499, 0xffffffff)[variant % 4]
            words[12] = random_source.randrange(1, 101)
            words[3] = 900  # Progress state reaches the two sound lookups.
            keys = (None, {"GAME_SDPT2"}, {"LEVEL_DEFEAT"}, set())[variant % 4]
            yield Case(f"independent state {state} combination {variant}", ENTRY,
                       setup_case(state, words, active=bool(variant & 4), enemy=bool(variant & 2),
                                  hit=True, audio=variant != 6, muted=variant == 7,
                                  same_order=bool(variant & 1), scene=state == 8003,
                                  sound_play=True, lookup_keys=keys,
                                  switch_sounds=variant == 4),
                       arguments=(lambda t: t["owner"],))
