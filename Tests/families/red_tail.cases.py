"""Blind original-backed RedTail dispatch and construction cases."""
from clawparity.cases import Case
from clawparity.world import world, rectangle_services, animation, sprite, cstring

ENTRY = 0x47F6E0
NEW = 0x4F63EC


def cases(random_source):
    def dispatch(state_value, salt):
        def setup(env):
            owner = env.object(0x200, 'dispatch-owner', fill=0xA7)
            state = env.object(0x180, 'dispatch-state', fill=0x59)
            target = env.object(0x508, 'dispatch-target', fill=0xD3)
            methods = env.object(0x24, 'dispatch-methods', fill=0)
            log = env.object(0x200, 'callback-observations', fill=0)
            env.put(owner + 0x6C, state)
            env.put(state + 0x18, target, state_value)
            env.write(target, bytes(((salt + i * 73 + (i >> 3)) & 255) for i in range(0x508)))
            env.put(target, methods)
            env.put(target + 0x10, state)
            text = cstring(env, 'LS_ACTIVE_' + str(salt))
            row = env.object(4, 'state-name-row', words=[text])
            env.put(0x5376A0, state_value, state_value, row, row, 4, 0, 0)
            def effect(tag):
                def callback(env, call):
                    count = env.get(log)
                    at = log + 4 + count * 32
                    env.put(at, tag, call.receiver, len(call.arguments),
                            call.arguments[0] if call.arguments else 0,
                            env.get(state + 0x18), env.get(state + 0x1C),
                            env.get(target + 0x24), env.get(owner + 0x6C))
                    env.put(log, count + 1)
                    env.put(target + 0x24, salt ^ tag)
                    env.put(state + 0x1C, (salt + tag) & 0xFFFFFFFF)
                    return salt ^ (tag * 19)
                return callback
            for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
                env.put(methods + offset, env.stub('dispatch-' + str(offset), 'thiscall', argc, effect(offset)))
            return {'owner': owner}
        return setup

    for state_value in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        salt = random_source.randrange(1, 0x7FFFFFFF)
        yield Case('dispatch ' + str(state_value), ENTRY, dispatch(state_value, salt), arguments=(lambda t: t['owner'],))

    def construction(hit, salt):
        def setup(env):
            rectangle_services(env)
            prior = env.object(0x508, 'prior-published-creature', fill=0x39)
            resources = {}
            if hit:
                animations = {}
                for name in ('FASTADVANCE', 'HITHIGH', 'HITLOW', 'HOME', 'IDLE', 'JUMP', 'KILLFALL', 'STRIKE2', 'STRIKE3', 'STRIKE4', 'STRIKE6', 'STRIKE7', 'STRIKE8', 'BLOCK'):
                    animations['LEVEL_REDTAIL_' + name] = animation(env, 20 + (salt % 117) + len(animations))
                animations['GAME_NULL'] = animation(env, 23)
                resources['animations'] = animations
                resources['sprites'] = {'LEVEL_REDTAIL': sprite(env, 37, 61, (-7, 13))}
                sounds = {}
                for name in ('FLAREGUN3', '01040006', '01040007', '01040021', '01040022', '01040023', '01040025', '01040001', 'RTSLIDE', '01040012', '01040020', '01040004', '01040002', 'BLOCK2', '3KNIVES', 'RTJUMP'):
                    sounds['LEVEL_REDTAIL_' + name] = env.object(0x40, 'sound-' + name, fill=(len(sounds) + 31))
                resources['sounds'] = sounds
            tokens = world(env, resources=resources,
                           owner_words={0x4C: salt % 300 - 150, 0x50: salt % 217 - 90},
                           state_words={0x18: prior, 0x1C: 0, 0x2C: 3, 0x30: 5, 0x34: 7, 0x38: 11, 0x68: salt})
            log = env.object(0x100, 'construction-observations', fill=0)
            from clawparity.world import set_rect, set_rect_empty
            def rectangle(effect, tag):
                def callback(env, call):
                    count = env.get(log)
                    at = log + 4 + count * 16
                    env.put(at, tag, call.arguments[0], env.get(tokens['state'] + 0x18), env.get(tokens['state'] + 0x1C))
                    env.put(log, count + 1)
                    return effect(env, call)
                return callback
            env.override(0x546D5C, rectangle(set_rect, 5))
            env.override(0x546CDC, rectangle(set_rect_empty, 1))
            def allocate(env, call):
                if call.arguments[0] == 0x508:
                    env.put(log + 224, env.get(tokens['state'] + 0x18), env.get(tokens['state'] + 0x1C), call.arguments[0])
                size = call.arguments[0]
                return env.object(size, 'constructor-allocation',
                                  data=bytes(((salt + i * 37 + (i >> 2)) & 255) for i in range(size)))
            env.override(NEW, allocate)
            return tokens
        return setup

    for hit in (False, True):
        for _ in range(3):
            salt = random_source.randrange(1, 0x7FFFFFFF)
            yield Case('construct resources ' + str(hit) + ' ' + str(salt), ENTRY,
                       construction(hit, salt), arguments=(lambda t: t['owner'],))
