"""Independent original-backed outer frame cases."""
from clawparity.cases import Case

CLOCK = 0x546DF0


def manager_setup(pause, countdown, replacement, result, now, previous, accumulated, alias):
    def setup(env):
        manager = env.object(0xC0, "manager", fill=0xA7)
        state = manager if alias else env.object(0x20, "state", fill=0xB3)
        table = env.object(0x20, "state methods", fill=0xD5)
        observed = env.object(0x40, "callback observation", fill=0xE9)
        env.put(manager + 0x1C, 0, 17, now - 100 & 0xFFFFFFFF, 7, state)
        env.put(manager + 0x6C, countdown)
        env.put(manager + 0xB0, pause)
        env.put(state, table)
        env.put(0x541328, previous, 0x11111111, 0, 0, 0)
        env.put(0x537208, 0x13579BDF, 0x2468ACE0, accumulated)

        def clock(env, call):
            env.put(observed + 0x30, call.receiver, len(call.arguments), env.get(manager + 0x6C))
            return now

        def frame(env, call):
            env.put(observed, call.receiver, len(call.arguments), env.get(0x537208),
                    env.get(0x53720C), env.get(0x537210), env.get(manager + 0x6C))
            if replacement is not None:
                env.put(manager + 0x6C, replacement)
            return result

        env.override(CLOCK, clock)
        env.put(table + 0x14, env.stub("state frame", "thiscall", 0, frame))
        return {"receiver": manager}
    return setup


def state_setup(delta, coordinates, changed_delta, null_final, mutate, alias, callback_result):
    def setup(env):
        state = env.object(0xC20, "state", fill=0)
        log = env.object(0x3000, "callback observations", fill=0xBD)
        env.put(log, 0)
        input_object = env.object(0x218, "input object", fill=0x84)
        env.put(input_object + 0x1CC, 0)
        wrapper = env.object(0x74, "input wrapper", fill=0x97)
        env.put(wrapper, input_object)
        env.put(0x537200, input_object, wrapper)
        env.put(0x537208, 0xF13579BD, delta, 0xFFFFFFC7)
        env.put(0x537264, 0x20)
        env.put(state + 0xBF4, 0xFFFFFFFF)
        env.put(state + 0x14C, 0xFA917235)
        if mutate:
            state_methods = env.object(0x54, "state methods", fill=0)
            network = env.object(0x88, "empty network", fill=0)
            env.put(state, state_methods)
            env.put(state + 0x780, network)
            env.put(state + 0x794, 1)
            env.put(state + 0x7AC, 1)
            env.put(state + 0xBC0, 0xD13579BD)
            env.put(state + 0xBCC, 2)
            env.put(network + 0x84, 0xE2468ACE)

            def racer_count(env, call):
                env.put(log + 0x2F00, call.receiver, len(call.arguments),
                        env.get(state + 0x14C), env.get(state + 0x794))
                return 1

            env.put(state_methods + 0x50, env.stub("racer count", "thiscall", 0, racer_count))
        graphs = []
        for index in range(6):
            app = env.object(0x70, f"application {index}", fill=0)
            chat = env.object(0x38, f"chat {index}", fill=0)
            env.put(chat + 0x2C, (-changed_delta if index == 4 and mutate else -delta) & 0xFFFFFFFF, 1)
            audio = env.object(0x30, f"audio {index}", fill=0)
            record = env.object(0x30, f"audio record {index}", fill=0)
            env.put(audio, record)
            env.put(audio + 0x28, 0xE1E1E1E1, 0xF2F2F2F2)
            env.put(app + 0x4C, chat)
            env.put(app + 0x5C, audio)
            scene = env.object(0x30, f"scene {index}", fill=0)
            display = env.object(0x20, f"display {index}", fill=0)
            presentation = env.object(0x30, f"presentation {index}", fill=0)
            world = env.object(0x64, f"world {index}", fill=0)
            plane = env.object(0xB4, f"plane {index}", fill=0)
            env.put(plane + 0x84, (coordinates[0] + index * 101) & 0xFFFFFFFF,
                    (coordinates[1] - index * 79) & 0xFFFFFFFF)
            env.put(world + 0x5C, plane, 0xFFFFFFFF)
            actors = env.object(0x20, f"actors {index}", fill=0)
            methods = env.object(0x44, f"actor methods {index}", fill=0)
            env.put(actors, methods)
            renderer = actors if alias else env.object(4, f"renderer {index}", fill=0)
            renderer_methods = methods if alias else env.object(0x38, f"renderer methods {index}", fill=0)
            env.put(renderer, renderer_methods)
            surface = env.object(0x10, f"surface {index}", fill=0)
            interface = env.object(4, f"COM interface {index}", fill=0)
            com_methods = env.object(0x30, f"COM methods {index}", fill=0)
            env.put(interface, com_methods)
            env.put(surface + 8, interface)
            env.put(presentation + 0x2C, surface)
            target = env.object(0x10, f"target {index}", fill=0x40 + index)
            second = target if alias else env.object(0x10, f"second {index}", fill=0x60 + index)
            env.put(display + 0x10, presentation, target, second)
            env.put(scene + 4, display, actors, renderer)
            env.put(scene + 0x24, world)
            graphs.append(dict(app=app, chat=chat, audio=audio, scene=scene, world=world,
                               plane=plane, methods=methods, renderer_methods=renderer_methods,
                               com_methods=com_methods))

        def observe(env, call, kind, index):
            count = env.get(log)
            env.put(log + 4 + count * 48, kind, index, call.receiver, len(call.arguments),
                    *(tuple(call.arguments) + (0,) * (3 - len(call.arguments))),
                    env.get(0x53720C), env.get(state + 4), env.get(state + 0xC),
                    env.get(graphs[index]["audio"] + 0x28), env.get(graphs[index]["audio"] + 0x2C))
            env.put(log, count + 1)

        def switch(env, index):
            env.put(state + 4, graphs[index]["app"])
            env.put(state + 0xC, graphs[index]["scene"])

        for index, graph in enumerate(graphs):
            def actor_update(env, call, index=index):
                observe(env, call, 1, index)
                return callback_result

            def actor_finish(env, call, index=index):
                observe(env, call, 2, index)
                if mutate:
                    switch(env, 1)
                return callback_result

            def audio_update(env, call, index=index):
                observe(env, call, 3, index)
                if mutate:
                    switch(env, 2)
                return callback_result

            def actor_render(env, call, index=index):
                observe(env, call, 4, index)
                if mutate:
                    switch(env, 3)
                return callback_result

            def render(env, call, index=index):
                observe(env, call, 5, index)
                if mutate:
                    switch(env, 4)
                    env.put(0x53720C, changed_delta)
                return callback_result

            def flip(env, call, index=index):
                observe(env, call, 6, index)
                if mutate:
                    switch(env, 5)
                if null_final:
                    env.put(graphs[5 if mutate else 0]["world"] + 0x5C, 0)
                return 0

            env.put(graph["methods"] + 0x24, env.stub(f"update {index}", "thiscall", 1, actor_update),
                    env.stub(f"actor render {index}", "thiscall", 1, actor_render))
            env.put(graph["methods"] + 0x40, env.stub(f"finish update {index}", "thiscall", 0, actor_finish))
            env.put(graph["renderer_methods"] + 0x34, env.stub(f"renderer {index}", "thiscall", 2, render))
            env.put(graph["com_methods"] + 0x2C, env.stub(f"Flip {index}", "stdcall", 3, flip))
            node = env.object(0xC, f"audio node {index}", fill=0)
            voice = env.object(4, f"voice {index}", fill=0)
            voice_methods = env.object(8, f"voice methods {index}", fill=0)
            env.put(voice, voice_methods)
            env.put(voice_methods + 4, env.stub(f"audio coordinates {index}", "thiscall", 3, audio_update))
            env.put(node + 8, voice)
            env.put(graph["audio"] + 0xC, node)
        switch(env, 0)
        return {"receiver": state}
    return setup


def cases(random_source):
    for pause in (0, 1, 0x80000000):
        for countdown in (0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            for result in (0, 0xF3579BDF):
                yield Case(f"manager pause {pause:x} countdown {countdown:x} result {result:x}",
                           0x428B60, manager_setup(pause, countdown, None, result,
                           0x25, 0xFFFFFFF7, 0xFFFFFFED, False), receiver=lambda t: t["receiver"])
    for replacement in (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield Case(f"manager callback replaces countdown {replacement:x}", 0x428B60,
                   manager_setup(0, 3, replacement, random_source.getrandbits(32),
                                 451, 413, 0xFFFFFFF3, True), receiver=lambda t: t["receiver"])
    for index in range(12):
        now = random_source.randrange(100, 0xFFFFFFFF)
        yield Case(f"manager random {index}", 0x428B60,
                   manager_setup(index % 3 == 0, random_source.getrandbits(32), None,
                                 random_source.getrandbits(32), now, now - index,
                                 random_source.getrandbits(32), index % 2 == 0),
                   receiver=lambda t: t["receiver"])
    for entry in (0x46AC30, 0x475DC0):
        for delta in (0, 1, 18, 19, 36, 37, 99, 100, 0x80000000):
            for mutate in (False, True):
                for null_final in (False, True):
                    yield Case(f"{entry:x} delta {delta:x} reload {mutate} null {null_final}", entry,
                               state_setup(delta, (random_source.getrandbits(32), random_source.getrandbits(32)),
                                           random_source.randrange(1, 1000), null_final, mutate,
                                           delta % 2 == 0, random_source.getrandbits(32)),
                               receiver=lambda t: t["receiver"])
