"""Original-backed inputs for the results and treasure counters."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def base(env):
    obj = env.object(0x240, 'results', fill=0)
    return {'obj': obj}


def destructor(count, populated, flags=0):
    def setup(env):
        t = base(env)
        obj = t['obj']
        log = env.object(0x200, 'destruction log', fill=0)
        def destroy(env, call):
            n = env.get(log)
            env.put(log, n + 1)
            env.put(log + 4 + n * 16, call.receiver, call.arguments[0],
                    env.get(obj), env.get(0x53cac4))
            return 0xfeed0011
        vt = env.object(4, 'destructor vtable', words=[env.stub('destroy child', 'thiscall', 1, destroy)])
        children = [env.object(0x34, 'child ' + str(i), words=[vt], fill=i + 1) for i in range(6)]
        env.put(obj + 0x60, *([*children[:4]] if populated else [0] * 4))
        env.put(0x53cac4, count, children[4] if populated else 0, children[5] if populated else 0)
        return t
    return setup


def skip_states(states, active=3):
    def setup(env):
        t = base(env)
        for i, state in enumerate(states):
            if state is None:
                continue
            sprite = env.object(0x180, 'treasure sprite ' + str(i), fill=0x31 + i)
            logic = env.object(0x180, 'treasure logic ' + str(i), fill=0x51 + i)
            env.put(sprite + 0x6c, logic)
            env.put(logic + 0x1c, state)
            env.put(t['obj'] + 0x15c + i * 4, sprite)
        env.put(0x52d4e0, active, 0x76543210)
        return t
    return setup


def digit_group(env, name, count, value=37):
    group = env.object(0x38, name, fill=0x17)
    env.put(group + 4, value, count)
    for i in range(max(0, count)):
        digit = env.object(0x1c0, name + ' digit ' + str(i), fill=0x30 + i)
        logic = env.object(0x180, name + ' digit logic ' + str(i), fill=0x60 + i)
        image = env.object(0x70, name + ' image ' + str(i), fill=0)
        frames = env.object(40, name + ' frames ' + str(i), words=[0xa100 + i * 16 + j for j in range(10)])
        env.put(image + 0x14, frames)
        env.put(image + 0x64, 2, 7)
        env.put(digit + 0x6c, logic)
        env.put(digit + 0x170, image if i % 3 else 0)
        env.put(digit + 0x4c, 0x7ffffff0 + i)
        env.put(group + 0xc + 4 * i, digit)
    return group


def counters(parity, count, glitter):
    def setup(env):
        t = base(env)
        for offset in (0x60, 0x64, 0x68, 0x6c):
            env.put(t['obj'] + offset, digit_group(env, 'counter ' + str(offset), count))
        for offset in (0x70, 0x74, 0x78, 0x7c, 0x80, 0x84, 0x88):
            sprite = env.object(0x80, 'symbol ' + str(offset), fill=0x46)
            env.put(sprite + 0x4c, offset * 31)
            env.put(t['obj'] + offset, sprite if offset != 0x80 or glitter else 0)
        env.put(t['obj'] + 0x8c, parity)
        env.put(0x53cac8, digit_group(env, 'global total', count), digit_group(env, 'global score', count))
        return t
    return setup


def animation(state, timer=0, delta=5, category=2):
    def setup(env):
        t = counters(category, 2, True)(env)
        sprite = env.object(0x240, 'animated sprite', fill=0)
        logic = env.object(0x180, 'animated logic', fill=0)
        env.put(sprite + 0x6c, logic)
        env.put(logic + 0x18, t['obj'], state)
        env.put(logic + 0x130, timer, timer, timer)
        env.put(logic + 0x64, 100, 200, 0)
        env.put(sprite + 0x4c, 100, 200)
        env.put(sprite + 0x190, 0)
        env.put(t['obj'] + 0x8c, category, 8, 7, 2, 9, 100, 200)
        env.put(t['obj'] + 0xa8, *struct.unpack('<II', struct.pack('<d', 1.25)))
        env.put(0x52d4e0, 11, 17, 25, 300)
        env.put(0x53cad0, 400)
        env.put(0x53720c, delta)
        services = env.object(0x30, 'animation services', fill=0)
        images = env.object(0x30, 'animation images', fill=0)
        env.put(images + 0x18, 1)
        env.put(services + 0x10, images)
        env.put(sprite + 0xc, services)
        env.put(sprite + 0x170, images)
        t.update(sprite=sprite, logic=logic)
        return t
    return setup


def cases(random_source):
    for count in (0, 1, 2):
        for populated in (False, True):
            yield Case(f'destruct counter count {count} populated {populated}', 0x40db60,
                       destructor(count, populated), receiver=lambda t: t['obj'])
    for flags in (0, 1, 2, 0x101):
        yield Case(f'deleting counter flags {flags}', 0x40db10, destructor(1, True),
                   receiver=lambda t: t['obj'], arguments=(flags,))
    yield Case('cleanup without services', 0x40dc10, base, receiver=lambda t: t['obj'])
    for address in (0x40df00, 0x40df60):
        def failed_virtual(env):
            t = base(env)
            vt = env.object(0x40, 'results vtable', fill=0)
            env.put(vt + 0xc, env.stub('enter fails', 'thiscall', 0, returns(0)))
            env.put(t['obj'], vt)
            return t
        yield Case(f'{address:x} virtual failure', address, failed_virtual, receiver=lambda t: t['obj'])
    states = [0x2331, 0x232c, 0x232d, 0x232e, 0x232f, 0x2329, 0x2334, 0x7777, None]
    for active in (-1, 4):
        yield Case(f'skip every counter state active {active}', 0x40e040, skip_states(states, active), receiver=lambda t: t['obj'])
    for key in (0x1b, 0x20, 0xd, 0, 0xffffffff):
        yield Case(f'key {key:x}', 0x40e020, skip_states(states), receiver=lambda t: t['obj'], arguments=(key, 0x1234))
    yield Case('fade without screen', 0x48f470, base, receiver=lambda t: t['obj'], arguments=(250,))
    for missing in (0xc, 8, 0x20):
        def no_resource(env, missing=missing):
            t = base(env)
            for off in (0xc, 8, 0x20):
                env.put(t['obj'] + off, 0 if off == missing else env.object(0x80, 'service ' + str(off), fill=0))
            t['name'] = env.object(8, 'screen name', data=b'BOOTY\0')
            return t
        yield Case(f'load missing {missing:x}', 0x48ffa0, no_resource, receiver=lambda t: t['obj'], arguments=(lambda t:t['name'], 1, 0, 0))
    for parent, window in ((False, False), (True, False), (True, True)):
        def paint(env, parent=parent, window=window):
            t = base(env)
            p = env.object(0x140, 'application', fill=0)
            w = env.object(12, 'window', fill=0)
            env.put(w + 4, 0x1357)
            env.put(p + 4, w if window else 0)
            env.put(t['obj'] + 4, p if parent else 0)
            env.override(0x546cb4, returns(0x123))
            env.override(0x546cb8, returns(1))
            return t
        yield Case(f'paint {parent} {window}', 0x490370, paint, receiver=lambda t:t['obj'])
    for count in (0, 1, 3):
        for value in (37, 0, -2147483648, 90213, random_source.randrange(1, 999999)):
            def update(env, count=count):
                return {'obj': digit_group(env, 'number', count)}
            yield Case(f'number count {count} value {value}', 0x499c30, update, receiver=lambda t:t['obj'], arguments=(value,))
    for parity in (0, 1, 2, 0xffffffff):
        for count in (0, 3):
            yield Case(f'move parity {parity} digits {count}', 0x4997c0, counters(parity, count, count != 0), receiver=lambda t:t['obj'], arguments=(random_source.randrange(1, 500),))
            yield Case(f'move totals parity {parity} digits {count}', 0x499cd0, counters(parity, count, False), receiver=lambda t:t['obj'], arguments=(-31,))
    for numerator, denominator, factor in ((0, 5, 1.), (1, 4, .5), (8, 3, 1.25), (17, 9, -2.), (-3, 7, 2.5)):
        def speed(env, n=numerator, d=denominator, f=factor):
            t = base(env)
            env.put(t['obj'] + 0x90, n, d)
            env.write(t['obj'] + 0xa8, struct.pack('<d', f))
            return t
        yield Case(f'speed {numerator} {denominator} {factor}', 0x4995d0, speed, receiver=lambda t:t['obj'])
    for state in (0, 1, 5, 6, 0x2332, 0x2333, 0xffffffff):
        for timer in (0, 3, 8):
            yield Case(f'treasure flight state {state:x} timer {timer}', 0x498f90, animation(state, timer), arguments=(lambda t:t['sprite'],))
    for state in (0, 1, 5, 6, 0x2329, 0x232a, 0x232c, 0x232d, 0x232e, 0x232f, 0x2330, 0x2331, 0x2332, 0x2334):
        yield Case(f'counter state {state:x}', 0x498930, animation(state, 8), arguments=(lambda t:t['sprite'],))
    for count in (-1, 0):
        for value in (-12345, 17):
            def init_number(env):
                t = animation(1)(env)
                return t
            yield Case(f'init number count {count} value {value}', 0x4903c0, init_number, receiver=lambda t:t['obj'], arguments=(lambda t:t['sprite'], value, count, 11, 90, -1, 0))
    def tail(env):
        t = base(env)
        vt = env.object(0x40, 'tail vtable', fill=0)
        log = env.object(12, 'tail callback log', fill=0)
        def callback(env, call):
            env.put(log, call.receiver, env.get(call.receiver), 0x55aa)
            return 0x1234
        env.put(vt + 0x3c, env.stub('clear sprites', 'thiscall', 0, callback))
        env.put(t['obj'], vt)
        return t
    yield Case('tail dispatch', 0x4c89e0, tail, receiver=lambda t:t['obj'])
    def empty_map(env, name):
        p = env.object(0x30, name, fill=0)
        env.put(p + 8, 1)
        return p
    def scene(env):
        env.override(0x5469e4, lambda e, c: len(e.cstr(c.arguments[0])))
        def decrement(e, c):
            value = (e.get(c.arguments[0]) - 1) & 0xffffffff
            e.put(c.arguments[0], value)
            return value
        env.override(0x5469e8, decrement)
        def increment(e,c):
            value = (e.get(c.arguments[0]) + 1) & 0xffffffff
            e.put(c.arguments[0],value)
            return value
        env.override(0x5469ec,increment)
        env.override(0x4a3050,returns(17))
        t = base(env)
        obj = t['obj']
        app = env.object(0x180, 'application', fill=0)
        services = env.object(0x40, 'services', fill=0)
        renderer = env.object(0x40, 'renderer', fill=0)
        env.put(obj + 4, app)
        env.put(obj + 0xc, services)
        env.put(app + 0x30, services)
        env.put(0x5371fc, app)
        env.put(services + 4, renderer)
        for off in (8, 0xc, 0x10, 0x14, 0x18, 0x28, 0x2c):
            part = env.object(0x80, 'service part ' + str(off), fill=0)
            vt = env.object(0x60, 'service methods ' + str(off), fill=0)
            env.put(part, vt)
            for slot, argc in ((0x24, 1), (0x28, 1), (0x34, 2), (0x58, 0), (0x3c, 0)):
                env.put(vt + slot, env.stub('service %s method %s' % (off, slot), 'thiscall', argc, returns(0)))
            env.put(part + 0x18, 1)
            env.put(services + off, part)
            if off in (0x10, 0x14, 0x28, 0x2c):
                env.put(part + 0x18, 1)
                env.put(part + 0x14, 0)
        for off in (0x10, 0x14, 0x18):
            surf = env.object(0x80, 'surface ' + str(off), fill=0)
            wrapper = env.object(0xc0, 'surface wrapper ' + str(off), fill=0)
            interface = env.object(4, 'directdraw interface ' + str(off), fill=0)
            vt = env.object(0x80, 'directdraw methods ' + str(off), fill=0)
            env.put(interface, vt)
            env.put(wrapper + 8, interface)
            env.put(vt + 0x2c, env.stub('surface flip', 'stdcall', 3, returns(0)))
            env.put(vt + 0x1c, env.stub('surface blit', 'stdcall', 6, returns(0)))
            env.put(surf + 0x2c, wrapper)
            env.put(renderer + off, surf)
        env.put(renderer + 0x18, 0)
        env.put(obj + 0x180, env.get(0x52e1c8) + 12)
        env.put(obj + 0x70, renderer)
        t.update(app=app, services=services, renderer=renderer)
        return t
    # String destructor can use the original shared empty-string allocation.
    for addr in (0x40b020, 0x40b040):
        for flag in (0, 1, 2):
            def empty_string(env):
                t = base(env)
                env.put(t['obj'] + 0x180, env.get(0x52e1c8) + 12)
                return t
            yield Case(f'base destructor {addr:x} flags {flag}', addr, empty_string,
                       receiver=lambda t:t['obj'], arguments=(flag,) if addr == 0x40b020 else ())
    for count in (0, 3):
        def clear_list(env, count=count):
            t = base(env)
            following = 0
            vt = env.object(8, 'list child vtable', fill=0)
            log = env.object(64, 'list destruction log', fill=0)
            def drop(env, call):
                n = env.get(log)
                env.put(log + 4 + n * 8, call.receiver, call.arguments[0])
                env.put(log, n + 1)
                return 0
            env.put(vt + 4, env.stub('list child destructor', 'thiscall', 1, drop))
            for i in range(count):
                child = env.object(8, 'list child ' + str(i), words=[vt, i]) if i != 1 else 0
                following = env.object(12, 'list link ' + str(i), words=[following, 0, child])
            env.put(t['obj'] + 0x14, following)
            return t
        yield Case(f'clear {count} list nodes', 0x4c89f0, clear_list, receiver=lambda t:t['obj'])
    for addr in (0x499170, 0x499450):
        yield Case(f'creation already present {addr:x}', addr, scene if addr == 0x499450 else animation(1),
                   receiver=lambda t:t['obj'], arguments=(lambda t:t.get('sprite', t['obj']),))
    for addr in (0x4998c0,):
        for mode in (0, 1):
            def update_totals(env):
                t = counters(2, 3, True)(env)
                app = env.object(0x140, 'score application', fill=0)
                services = env.object(0x40, 'score services', fill=0)
                sound = env.object(0x40, 'sound disabled', fill=0)
                env.put(sound + 0x30, 1)
                env.put(app + 0x30, services)
                env.put(services + 0x28, sound)
                env.put(0x5371fc, app)
                env.put(t['obj'] + 0x90, 49, 19, 3, 60)
                env.put(t['obj'] + 0xb0, 123, 456)
                return t
            yield Case(f'update scores mode {mode}', addr, update_totals, receiver=lambda t:t['obj'], arguments=(mode,))
    def finish_counter(env):
        t = animation(1)(env)
        env.put(t['obj'] + 0x90, 37)
        env.put(t['obj'] + 0x9c, 41)
        return t
    yield Case('finish without complete award', 0x499d60, finish_counter, receiver=lambda t:t['obj'], arguments=(lambda t:t['sprite'],))
    for count in (0, -1):
        def no_spawn(env, count=count):
            t = scene(env)
            env.put(t['obj'] + 0x90, 0, count)
            return t
        yield Case(f'no remaining treasure {count}', 0x499630, no_spawn, receiver=lambda t:t['obj'], arguments=(lambda t:t['obj'],))
    yield Case('cleanup active services', 0x40dc10, scene, receiver=lambda t:t['obj'])
    def draw_scene(env):
        t = scene(env)
        renderer = t['renderer']
        # Back surface must survive both the blit source and the presentation callback.
        back = env.object(0x80, 'back surface', fill=0)
        wrapper = env.object(0xc0, 'back wrapper', fill=0)
        interface = env.object(4, 'back interface', fill=0)
        vt = env.object(0x80, 'back methods', fill=0)
        env.put(interface, vt)
        env.put(wrapper + 8, interface)
        env.put(back + 0x2c, wrapper)
        env.put(renderer + 0x18, back)
        input_state = env.object(0x250, 'disabled input', fill=0)
        env.put(0x537200, input_state)
        window = env.object(12, 'completion window', words=[0, 0x4321, 0])
        env.put(t['app'] + 4, window)
        env.put(0x546d50, env.get(0x546d50))
        env.override(0x546d50, returns(0x9876))
        return t
    for announced in (0, 1):
        def draw(env, announced=announced):
            t = draw_scene(env)
            env.put(t['obj'] + 0x154, announced)
            return t
        yield Case(f'draw and completion announced {announced}', 0x40dd50, draw, receiver=lambda t:t['obj'])
    for missing in (False, True):
        def before_draw(env, missing=missing):
            t = draw_scene(env)
            vt = env.object(0x40, 'before draw vtable', fill=0)
            env.put(vt + 0xc, env.stub('before draw', 'thiscall', 0, returns(1)))
            env.put(t['obj'], vt)
            if missing:
                env.put(t['app'] + 4, 0)
            else:
                window = env.object(12, 'draw window', words=[0, 0x3141, 0])
                env.put(t['app'] + 4, window)
            env.override(0x546cb4, returns(1))
            env.override(0x546cb8, returns(1))
            env.override(0x546d54, returns(0xffffffff))
            return t
        yield Case(f'redraw window absent {missing}', 0x40df60, before_draw, receiver=lambda t:t['obj'])
    def startup_failure(env):
        t = scene(env)
        surf = env.get(t['renderer'] + 0x10)
        wrapper = env.get(surf + 0x2c)
        iface = env.get(wrapper + 8)
        vt = env.get(iface)
        env.put(vt + 0x60, env.stub('is lost', 'stdcall', 1, returns(1)))
        env.put(vt + 0x6c, env.stub('restore fails', 'stdcall', 1, returns(1)))
        return t
    yield Case('resource restore failure', 0x40de90, startup_failure, receiver=lambda t:t['obj'])
    def factory_scene(env):
        t = scene(env)
        def reused_storage(e,c):
            size=c.arguments[0]
            serial=e.calls_so_far(0x4f63ec)
            payload=bytes(((i*29+serial*43+0x51)%255)+1 for i in range(size)) if size in (0x34,0x60,0xb8) else bytes(size)
            return e.object(size,'reused allocator storage '+str(serial),data=payload)
        env.override(0x4f63ec,reused_storage)
        services = t['services']
        manager = env.get(services + 8)
        env.put(manager + 0xc, services)
        env.put(manager + 0x10, 0, 0, 0, 0, 0, 0, 10)
        logic_service = env.get(services + 0x14)
        buckets = env.object(4, 'logic hash buckets', fill=0)
        env.put(logic_service + 0x14, buckets, 1)
        following = 0
        for name in ('SimpleAnimation', 'StatusNumberDigit', 'TreasureCounter', 'TreasureLogic'):
            text = env.object(len(name) + 1, 'logic name ' + name, data=name.encode() + b'\0')
            descriptor = env.object(0x14, 'logic descriptor ' + name, fill=0)
            env.put(descriptor + 0x10, 0x498930)
            following = env.object(16, 'logic hash node ' + name, words=[following, 0, text, descriptor])
        env.put(buckets, following)
        t['manager'] = manager
        return t
    for number in (-12345, 617):
        for digits in (1, 3, 11):
            def build_number(env):
                t = factory_scene(env)
                sprite = env.object(0x1c0, 'parent sprite', fill=0)
                logic = env.object(0x180, 'parent sprite logic', fill=0)
                controller = env.object(0x60, 'parent controller', fill=0)
                env.put(sprite + 0x6c, logic)
                env.put(sprite + 0xc, t['services'])
                env.put(sprite + 0x64, 78)
                env.put(logic + 0x18, controller)
                env.put(controller + 4, 11, 13, 17, 19, 23)
                t['sprite'] = sprite
                return t
            yield Case(f'create digits {digits} value {number}', 0x4903c0, build_number, receiver=lambda t:t['obj'], arguments=(lambda t:t['sprite'], number, digits, 13, 90, -4, 0x524070))
    for address in (0x499170, 0x499450, 0x499630, 0x499d60):
        def create_components(env, address=address):
            t = factory_scene(env)
            sprite = env.object(0x1c0, 'parent treasure sprite', fill=0)
            logic = env.object(0x180, 'parent treasure logic', fill=0)
            controller = env.object(0x60, 'treasure placement', fill=0)
            env.put(sprite + 0xc, t['services'])
            env.put(sprite + 0x6c, logic)
            env.put(logic + 0x18, controller)
            env.put(controller + 4, 10, 0, 4, 60, 20, 99)
            env.put(t['obj'] + 0x64, 0)
            env.put(t['obj'] + 0x70, 0)
            env.put(t['obj'] + 0x8c, 2, 4, 3, 2, 4, 100, 150)
            env.write(t['obj'] + 0xa8, struct.pack('<d', 1.25))
            env.put(0x52d4e8, 25, 300)
            env.put(0x53cad0, 400)
            env.override(0x4a3050, returns(13))
            t['sprite'] = sprite
            return t
        yield Case(f'create component {address:x}', address, create_components, receiver=lambda t:t['obj'], arguments=(lambda t:t['sprite'],))
    def directory(env, name, entries):
        root = env.object(0xa0, name, fill=0)
        buckets = env.object(5 * 16, name + ' buckets', fill=0)
        env.put(root + 0x3c, 5, buckets)
        file_types=env.object(9*16,name+' empty file types',fill=0)
        env.put(root+0x44,9,file_types)
        for label, value in entries.items():
            b = label.encode() + b'\0'
            text = env.object(len(b), name + ' key ' + label, data=b)
            record = env.object(4, name + ' resource record ' + label, words=[text])
            link = env.object(0x18, name + ' link ' + label, fill=0)
            bucket = len(label) % 5
            previous = env.get(buckets + bucket * 16 + 8)
            env.put(link + 4, previous)
            env.put(link + 0x14, value)
            # Directory lookup returns the resource object; its first word is the name pointer.
            env.put(value, text)
            env.put(buckets + bucket * 16 + 8, link + 4)
        return root
    for level in (1, 6):
        for missing in ('level', 'booty', 'claw', None):
            def construct(env, level=level, missing=missing):
                t = factory_scene(env)
                booty = directory(env, 'booty resources', {})
                claw = directory(env, 'claw resources', {})
                state = directory(env, 'states resources', {} if missing == 'booty' else {'BOOTY':booty})
                leveldir = directory(env, 'level resources', {})
                entries = {'STATES':state}
                if missing != 'claw': entries['CLAW'] = claw
                if missing != 'level': entries['LEVEL' + str(level)] = leveldir
                root = directory(env, 'disc root', entries)
                rez = env.object(0x30, 'rez manager', fill=0)
                env.put(rez + 0x24, root)
                env.put(t['app'] + 0x34, rez)
                t['level'] = level
                return t
            yield Case(f'construct level {level} missing {missing}', 0x40d470, construct, receiver=lambda t:t['obj'], arguments=(lambda t:t['app'], level, 0x31415926))
    def reset_scene(env):
        t = scene(env)
        env.put(t['renderer'] + 0x10, 0)
        target = env.object(0x40, 'presentation target', fill=0)
        vt = env.object(0x40, 'presentation methods', fill=0)
        env.put(target, vt)
        env.put(vt + 0x14, env.stub('presentation unavailable', 'thiscall', 0, returns(1)))
        env.put(vt + 0x1c, env.stub('presentation reset', 'thiscall', 0, returns(0)))
        env.put(t['renderer'] + 0x18, target)
        return t
    for address in (0x40dc50, 0x40dca0):
        yield Case(f'reset results {address:x}', address, reset_scene, receiver=lambda t:t['obj'], arguments=(0x3141,) if address == 0x40dca0 else ())
    yield Case('title absent', 0x40dcb0, scene, receiver=lambda t:t['obj'], arguments=(0x1234,))
    for x, y, vx, vy in ((0, 0, 10., 20.), (99, 199, 50., 60.), (150, 250, -10., -20.)):
        for timer in (0, 8):
            def flight(env, x=x,y=y,vx=vx,vy=vy,timer=timer):
                t = animation(0x2333, timer)(env)
                env.put(t['sprite'] + 0x4c, x, y)
                env.write(t['logic'] + 0x160, struct.pack('<ff',vx,vy))
                return t
            yield Case(f'flight position {x} {y} timer {timer}',0x498f90,flight,arguments=(lambda t:t['sprite'],))
    for state in (5, 0x2329, 0x232b, 0x232c, 0x232d, 0x232f, 0x2330, 0x2334):
        for expired in (False, True):
            for active in (-1, 2):
                def state_machine(env,state=state,expired=expired,active=active):
                    t = animation(state,0 if expired else 20,category=2)(env)
                    f = factory_scene(env)
                    env.put(t['sprite'] + 0xc,f['services'])
                    env.put(0x52d4e0,active)
                    env.put(t['logic'] + 0xac,1 if expired else 0)
                    env.put(t['logic'] + 0x64,25,0 if expired else 25,0 if expired else 25)
                    env.put(t['sprite'] + 0x4c,90,190)
                    env.write(t['logic'] + 0x160,struct.pack('<ff',10.,20.))
                    env.put(0x5349a8,0)
                    # Shared string header is backed and has zero length for the sound skip.
                    env.put(0x53499c,env.get(0x52e1c8)+12)
                    return t
                yield Case(f'state matrix {state:x} expired {expired} active {active}',0x498930,state_machine,arguments=(lambda t:t['sprite'],))
    def palette_scene(env):
        t = scene(env)
        palette = env.object(0x40,'palette',fill=0)
        interface = env.object(4,'palette interface',fill=0)
        vt = env.object(0x40,'palette methods',fill=0)
        colors = env.object(0x400,'palette colors',data=bytes((i * 17 + 39) % 256 for i in range(0x400)))
        saved = env.object(0x400,'palette saved colors',data=bytes((i * 13 + 57) % 256 for i in range(0x400)))
        env.put(interface,vt)
        env.put(vt+0x10,env.stub('GetEntries','stdcall',5,returns(0)))
        env.put(vt+0x18,env.stub('SetEntries','stdcall',5,returns(0)))
        env.put(palette+4,interface)
        env.put(palette+0xc,colors,saved)
        screen = env.object(0x40,'screen',fill=0)
        methods = env.object(0x40,'screen methods',fill=0)
        env.put(screen,methods)
        env.put(methods+0x34,env.stub('show screen','thiscall',0,returns(1)))
        env.put(screen+0x10,palette)
        env.put(t['obj']+0x2c,screen)
        env.override(0x546df0,lambda e,c:e.calls_so_far(0x546df0)*1000)
        t.update(screen=screen,palette=palette)
        return t
    for fade in (0,1,250):
        yield Case(f'fade screen {fade}',0x48f470,palette_scene,receiver=lambda t:t['obj'],arguments=(fade,))
    def title_present(env):
        t = palette_scene(env)
        wrapper = env.get(env.get(t['renderer']+0x14)+0x2c)
        vt = env.get(env.get(wrapper+8))
        env.put(vt+0x14,env.stub('clear background surface','stdcall',6,returns(0)))
        return t
    yield Case('title palette reset',0x40dcb0,title_present,receiver=lambda t:t['obj'],arguments=(0x7777,))
    def load_screen(env):
        t = palette_scene(env)
        file = env.object(0x40,'screen image resource',fill=0)
        file_name = env.object(6,'screen image name',data=b'BOOTY\0')
        env.put(file,file_name)
        file_link = env.object(0x18,'file hash link',fill=0)
        env.put(file_link+0x14,file)
        file_buckets = env.object(19*16,'file hash buckets',fill=0)
        env.put(file_buckets+5*16+8,file_link+4)
        extension = env.object(0x30,'PCX resources',fill=0)
        env.put(extension,0x504358)
        env.put(extension+0x24,19,file_buckets)
        type_link = env.object(0x18,'extension hash link',fill=0)
        env.put(type_link+0x14,extension)
        type_buckets = env.object(9*16,'extension buckets',fill=0)
        env.put(type_buckets+(0x504358%9)*16+8,type_link+4)
        screens = directory(env,'screen resources',{})
        env.put(screens+0x44,9,type_buckets)
        root = directory(env,'screen root',{'SCREENS':screens})
        env.put(t['obj']+0x20,root)
        env.put(t['obj']+8,root)
        manager = env.get(t['services']+0x18)
        methods = env.get(manager)
        log = env.object(80,'screen creation log',fill=0)
        def screen_create(e,c):
            e.put(log,c.receiver,*c.arguments)
            e.write(log+20,e.cstr(c.arguments[1])+b'\0')
            return t['screen']
        env.put(methods+0x30,env.stub('create screen','thiscall',3,screen_create))
        surf = env.get(t['renderer']+0x14)
        surf_vt = env.object(0x40,'render screen methods',fill=0)
        env.put(surf,surf_vt)
        env.put(surf_vt+0x30,env.stub('install background','thiscall',1,returns(1)))
        # Initial screen is cleared by the original; the service list contains no matching node.
        env.put(t['obj']+0x2c,0)
        t['name']=file_name
        return t
    for flag in (0,1):
        for fade in (0,1):
            yield Case(f'load screen flag {flag} fade {fade}',0x48ffa0,load_screen,receiver=lambda t:t['obj'],arguments=(lambda t:t['name'],flag,0x80000000,fade))
    def entry_slot(e,root,label):
        link=e.get(e.get(root+0x40)+(len(label)%5)*16+8)
        while link:
            value=e.get(link-4+0x14)
            if e.cstr(e.get(value))==label.encode(): return link-4+0x14
            link=e.get(link)
        return 0
    for missing in ('images','anis',None):
        def custom_constructor(env,missing=missing):
            t=construct(env,level=3,missing=None)
            entries={}
            if missing!='images':entries['IMAGES']=directory(env,'custom images',{})
            if missing!='anis':entries['ANIS']=directory(env,'custom animations',{})
            booty=directory(env,'custom booty',entries)
            state=directory(env,'custom states',{'BOOTY':booty})
            leveldir=directory(env,'custom level',{})
            claw=directory(env,'custom claw',{})
            root=directory(env,'custom root',{'STATES':state,'LEVEL3':leveldir,'CLAW':claw})
            env.put(env.get(t['app']+0x34)+0x24,root)
            env.put(t['app']+0x130,1)
            images=env.get(t['services']+0x10)
            env.put(env.get(images)+0x48,env.stub('load custom images','thiscall',3,returns(2)))
            env.put(0x5349a0,1)
            for i in range(9):
                env.put(0x534d08+i*4,i+1)
                env.put(0x5381e0+i*4,i+3 if i%2 else i)
            return t
        yield Case(f'custom constructor missing {missing}',0x40d470,custom_constructor,receiver=lambda t:t['obj'],arguments=(lambda t:t['app'],3,0x778899))
    for result in (-1,3):
        def reload(env,result=result):
            t=reset_scene(env)
            images=directory(env,'reload images',{})
            root=directory(env,'reload booty',{'IMAGES':images})
            env.put(t['obj']+0x20,root)
            service=env.get(t['services']+0x10)
            env.put(env.get(service)+0x4c,env.stub('reload images','thiscall',3,returns(result)))
            env.override(0x546d54,lambda e,c:0xffffffff if e.calls_so_far(0x546d54)>2 else 0)
            return t
        yield Case(f'reload images status {result}',0x40de90,reload,receiver=lambda t:t['obj'])
    for screen in (False,True):
        def enter(env,screen=screen):
            t=reset_scene(env)
            p=palette_scene(env)
            env.put(t['obj']+0x2c,p['screen'] if screen else 0)
            vt=env.object(0x40,'enter methods',fill=0)
            env.put(vt+0xc,env.stub('enter results','thiscall',0,returns(1)))
            env.put(t['obj'],vt)
            env.override(0x546d54,lambda e,c:0xffffffff if e.calls_so_far(0x546d54)>2 else 0)
            return t
        yield Case(f'enter existing screen {screen}',0x40df00,enter,receiver=lambda t:t['obj'])
    for failure in ('lookup','create','background','old'):
        def screen_failure(env,failure=failure):
            t=load_screen(env)
            if failure=='lookup':
                env.put(t['obj']+0x20,directory(env,'missing screens',{}))
            elif failure=='create':
                part=env.get(t['services']+0x18)
                env.put(env.get(part)+0x30,env.stub('screen creation fails','thiscall',3,returns(0)))
            elif failure=='background':
                surf=env.get(t['renderer']+0x14)
                env.put(env.get(surf)+0x30,env.stub('background fails','thiscall',1,returns(0)))
            else:
                env.put(t['obj']+0x2c,t['screen'])
            return t
        yield Case('screen failure '+failure,0x48ffa0,screen_failure,receiver=lambda t:t['obj'],arguments=(lambda t:t['name'],1,0,0))
    for width in (0,3):
        for value in (123,456):
            def equal_totals(env,width=width,value=value):
                t=update_totals(env)
                env.put(env.get(0x53cac8)+4,123)
                env.put(env.get(0x53cacc)+4,456)
                env.put(env.get(0x53cac8)+8,width)
                env.put(env.get(0x53cacc)+8,width)
                return t
            yield Case(f'equal totals width {width} value {value}',0x4998c0,equal_totals,receiver=lambda t:t['obj'],arguments=(1,))
    def map_entry(env,service,label,value):
        text=env.object(len(label)+1,'map key '+label,data=label.encode()+b'\0')
        bucket=env.object(4,'one bucket '+label,fill=0)
        node=env.object(16,'map node '+label,words=[0,0,text,value])
        env.put(bucket,node)
        env.put(service+0x14,bucket,1)
    def with_sound(env):
        t=create_components(env)
        sound=env.object(0x20,'sound resource',fill=0)
        voice=env.object(0x20,'voice',fill=0)
        device=env.object(0x80,'disabled sound device',fill=0)
        env.put(sound+0x10,voice)
        env.put(voice+0x10,device)
        service=env.get(t['services']+0x28)
        label=env.cstr(env.get(0x523d94+2*32)).decode()
        map_entry(env,service,label,sound)
        env.put(0x532c0c,1)
        env.put(0x532c10,57)
        t['sound']=sound
        return t
    yield Case('category sound present',0x499450,with_sound,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    for maximum in (4,1000):
        def award_sound(env,maximum=maximum):
            t=with_sound(env)
            map_entry(env,env.get(t['services']+0x28),'BOOTY_CATNMAG',t['sound'])
            env.put(t['obj']+0x90,maximum)
            env.put(t['obj']+0x9c,maximum)
            return t
        yield Case(f'award sound count {maximum}',0x499d60,award_sound,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    def input_draw(env):
        t=draw_scene(env)
        input_state=env.get(0x537200)
        env.put(input_state+0x1cc,1)
        env.override(0x546ce4,returns(1))
        sprite=env.object(0x80,'incomplete treasure',fill=0)
        logic=env.object(0x180,'incomplete treasure logic',fill=0)
        env.put(sprite+0x6c,logic)
        env.put(logic+0x1c,0x232a)
        env.put(t['obj']+0x15c,sprite)
        env.put(t['app']+0x9c,1)
        surface=env.get(t['renderer']+0x14)
        vt=env.get(env.get(env.get(surface+0x2c)+8))
        env.put(vt+0x44,env.stub('get device context unavailable','stdcall',2,returns(0)))
        return t
    yield Case('draw input and incomplete treasure',0x40dd50,input_draw,receiver=lambda t:t['obj'])
    def cursor_loop(env):
        t=before_draw(env,missing=False)
        env.override(0x546d54,lambda e,c:0xffffffff if e.calls_so_far(0x546d54)>2 else 0)
        return t
    yield Case('redraw cursor repeats',0x40df60,cursor_loop,receiver=lambda t:t['obj'])
    for count in (0,-1,1):
        def fail_number(env,count=count):
            t=build_number(env)
            if count==0:
                env.put(env.get(t['sprite']+0x6c)+0x18,0)
            else:
                service=env.get(t['services']+0x14)
                env.put(service+0x14,0)
            return t
        yield Case(f'number missing parent or logic {count}',0x4903c0,fail_number,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],1,count,13,90,0,0x524070))
    for which in ('moving','perfect','sound','zero_count','empty_remaining','counting'):
        def extra_state(env,which=which):
            state={'moving':0x232d,'perfect':0x2329,'sound':0x2329,'zero_count':0x232b,'empty_remaining':0x232b,'counting':0x232b}[which]
            t=animation(state,0)(env)
            f=with_sound(env)
            env.put(t['sprite']+0xc,f['services'])
            env.put(0x52d4e0,-1)
            env.put(0x5349a8,1)
            env.put(0x53cad4,0)
            env.put(0x53cad8,0)
            env.put(0x53499c,env.get(0x52e1c8)+12)
            env.put(t['logic']+0x64,25,25,25)
            if which=='sound':
                text=env.object(32,'level sound string',fill=0)
                env.put(text,1,6,6)
                env.write(text+12,b'ENDING\0')
                env.put(0x53499c,text+12)
                map_entry(env,env.get(f['services']+0x28),'ENDING',f['sound'])
            elif which in ('zero_count','empty_remaining','counting'):
                env.put(t['logic']+0xac,1)
                env.put(t['logic']+0x134,0 if which!='counting' else 17)
                if which=='zero_count':env.put(t['obj']+0x90,0)
                if which=='empty_remaining':env.put(t['obj']+0x94,0)
            return t
        yield Case('extra state '+which,0x498930,extra_state,arguments=(lambda t:t['sprite'],))
    for value in (123,999):
        def framed_digits(env):
            t=build_number(env)
            image=env.object(0x70,'digit image range',fill=0)
            frames=env.object(40,'digit frame payloads',words=[0x123400+i*13 for i in range(10)])
            env.put(image+0x14,frames)
            env.put(image+0x64,2,7)
            map_entry(env,env.get(t['services']+0x10),'BOOTY_SCORENUMBERS',image)
            return t
        yield Case(f'create framed number {value}',0x4903c0,framed_digits,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],value,3,11,90,0,0x524070))
    def group_allocation_fails(env):
        t=create_components(env)
        env.put(env.get(t['sprite']+0x6c)+0x18,0)
        env.override(0x4f63ec,lambda e,c:0 if c.arguments[0]==0x34 else e.object(c.arguments[0],'new allocation',fill=0))
        return t
    yield Case('number group allocations fail with absent parent controller',0x499170,group_allocation_fails,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    def loud_award(env):
        t=award_sound(env)
        env.put(0x532c10,1000)
        return t
    yield Case('award clamps sound volume',0x499d60,loud_award,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    def bounce(env):
        t=update_totals(env)
        f=with_sound(env)
        map_entry(env,env.get(f['services']+0x28),'BOOTY_BOUNCE1',f['sound'])
        return t
    yield Case('counter bounce sound resource',0x4998c0,bounce,receiver=lambda t:t['obj'],arguments=(0,))
    def no_reload_images(env):
        t=reset_scene(env)
        env.put(t['obj']+0x20,directory(env,'no images directory',{}))
        return t
    yield Case('reload has no images',0x40de90,no_reload_images,receiver=lambda t:t['obj'])
    def amulet_constructor(env):
        t=construct(env,level=7,missing=None)
        env.put(0x5349a0,1)
        return t
    yield Case('standard amulet constructor',0x40d470,amulet_constructor,receiver=lambda t:t['obj'],arguments=(lambda t:t['app'],7,0x19283746))
    def initial_coin_animation(env):
        t=animation(0)(env)
        f=factory_scene(env)
        env.put(t['sprite']+0xc,f['services'])
        env.put(t['sprite']+0x170,0)
        return t
    yield Case('initial matching coin animation',0x498930,initial_coin_animation,arguments=(lambda t:t['sprite'],))
    def ending_sound(env):
        t=extra_state(env,which='sound')
        env.put(0x5349a0,0)
        return t
    yield Case('ending sound on standard game',0x498930,ending_sound,arguments=(lambda t:t['sprite'],))
    for expired in (False,True):
        def first_countdown(env,expired=expired):
            t=animation(0x232b,0 if expired else 20)(env)
            f=factory_scene(env)
            env.put(t['sprite']+0xc,f['services'])
            env.put(t['logic']+0xac,0)
            env.put(t['sprite']+0x4c,99)
            env.write(t['logic']+0x160,struct.pack('<f',50000.))
            return t
        yield Case(f'first countdown expiry {expired}',0x498930,first_countdown,arguments=(lambda t:t['sprite'],))
    def flight_clamps(env):
        t=animation(0x2333,8)(env)
        env.put(t['sprite']+0x4c,99,199)
        env.write(t['logic']+0x160,struct.pack('<ff',50000.,60000.))
        return t
    yield Case('flight clamps both coordinates',0x498f90,flight_clamps,arguments=(lambda t:t['sprite'],))
    def perfect_sound(env):
        t=extra_state(env,which='perfect')
        # This map owns the actual resource graph used by the original sound lookup.
        services=env.get(env.get(0x5371fc)+0x30)
        sound_service=env.get(services+0x28)
        sound=env.object(0x20,'perfect sound resource',fill=0)
        voice=env.object(0x20,'perfect sound voice',fill=0)
        device=env.object(0x80,'perfect sound disabled device',fill=0)
        env.put(sound+0x10,voice)
        env.put(voice+0x10,device)
        map_entry(env,sound_service,'BOOTY_PERFECT',sound)
        return t
    yield Case('perfect sound resource present',0x498930,perfect_sound,arguments=(lambda t:t['sprite'],))
    def enabled_sound(env):
        t=factory_scene(env)
        resource=env.object(0x20,'enabled sound resource',fill=0)
        holder=env.object(0x40,'sound holder with active list',fill=0)
        voice=env.object(0x40,'reusable playing voice',fill=0)
        device=env.object(0x80,'enabled sound device',fill=0)
        interface=env.object(4,'directsound buffer',fill=0)
        methods=env.object(0x50,'directsound buffer methods',fill=0)
        env.put(device+0x78,1)
        env.put(interface,methods)
        env.put(holder+0x10,device)
        env.put(holder+0x18,11025,321,-456)
        env.put(holder+0x30,voice+4,voice+4)
        env.put(voice+0xc,interface,device,0x512,22050,-123,-234)
        env.put(voice+0x30,1)
        log=env.object(0x400,'audio physical receipts',fill=0)
        def receipt(slot):
            def effect(e,c):
                n=e.get(log)
                e.put(log,n+1)
                e.put(log+4+n*32,slot,c.receiver,len(c.arguments),*c.arguments)
                if slot==0x24:e.put(c.arguments[1],0)
                return 0
            return effect
        for slot,argc in ((0x24,2),(0x3c,2),(0x40,2),(0x44,2),(0x30,4)):
            env.put(methods+slot,env.stub('DirectSoundBuffer '+str(slot),'stdcall',argc,receipt(slot)))
        env.put(resource+0x10,holder)
        env.put(0x532c0c,1)
        env.put(0x532c10,63)
        sprite=env.object(0x1c0,'sound counter parent sprite',fill=0)
        logic=env.object(0x180,'sound counter parent logic',fill=0)
        env.put(sprite+0xc,t['services'])
        env.put(sprite+0x6c,logic)
        env.put(sprite+0x64,37)
        env.put(t['obj']+0x8c,2,47,9,3,47,123,234)
        env.put(t['obj']+0x70,0)
        env.write(t['obj']+0xa8,struct.pack('<d',1.25))
        t.update(sound=resource,sprite=sprite,log=log)
        return t
    for category in (0,2,8):
        def sounding_category(env,category=category):
            t=enabled_sound(env)
            env.put(t['obj']+0x8c,category)
            label=env.cstr(env.get(0x523d94+category*32)).decode()
            map_entry(env,env.get(t['services']+0x28),label,t['sound'])
            return t
        yield Case('enabled category audio '+str(category),0x499450,sounding_category,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    for volume in (1,67,1000):
        def sounding_award(env,volume=volume):
            t=enabled_sound(env)
            env.put(0x532c10,volume)
            map_entry(env,env.get(t['services']+0x28),'BOOTY_CATNMAG',t['sound'])
            return t
        yield Case('enabled award audio '+str(volume),0x499d60,sounding_award,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    for address in (0x40b020,0x40b040):
        for references in (1,3):
            def string_destructor(env,references=references):
                t=scene(env)
                env.put(t['obj']+0xc,0)
                env.put(t['obj']+0x34,0x8a7b6c5d)
                allocation=env.object(32,'owned result CString',fill=0x37)
                env.put(allocation,references,13,19)
                env.write(allocation+12,b'BOOTY_RESULTS\0')
                env.put(t['obj']+0x180,allocation+12)
                return t
            yield Case(f'nonempty string destructor {address:x} references {references}',address,string_destructor,receiver=lambda t:t['obj'],arguments=(0,) if address==0x40b020 else ())
    def populated_cleanup(env):
        t=scene(env)
        resource=env.get(t['services']+0x2c)
        buckets=env.object(4,'animation cleanup map buckets',fill=0)
        log=env.object(128,'animation destruction receipts',fill=0)
        methods=env.object(8,'animation object methods',fill=0)
        def destroy(e,c):
            n=e.get(log)
            e.put(log,n+1)
            e.put(log+4+n*16,c.receiver,c.arguments[0],e.get(resource+0x1c),e.get(t['obj']))
            return 0x55aa
        env.put(methods+4,env.stub('animation object destruction','thiscall',1,destroy))
        next_node=0
        for index in range(3):
            label=('CYCLE_'+str(index)).encode()
            text=env.object(32,'animation name '+str(index),fill=0)
            env.put(text,1,len(label),19)
            env.write(text+12,label+b'\0')
            animation_object=env.object(0x20,'animation object '+str(index),words=[methods,index],fill=0x34+index)
            next_node=env.object(16,'animation map node '+str(index),words=[next_node,0,text+12,animation_object])
        env.put(buckets,next_node)
        env.put(resource+0x14,buckets,1,3,0,0,10)
        return t
    yield Case('cleanup populated animation map',0x40dc10,populated_cleanup,receiver=lambda t:t['obj'])
    for address in (0x40dc50,0x40dca0):
        def active_reset(env):
            t=load_screen(env)
            log=env.object(0x400,'reset physical callback receipts',fill=0)
            def receipt(kind,result=0):
                def effect(e,c):
                    n=e.get(log)
                    e.put(log,n+1)
                    e.put(log+4+n*40,kind,c.receiver,len(c.arguments),*c.arguments)
                    return result
                return effect
            target=env.object(0x40,'active presentation target',fill=0)
            vt=env.object(0x40,'active presentation methods',fill=0)
            env.put(target,vt)
            env.put(vt+0x14,env.stub('presentation status','thiscall',0,receipt(1)))
            env.put(vt+0x1c,env.stub('presentation restore','thiscall',0,receipt(2)))
            env.put(vt+0x24,env.stub('presentation resize','thiscall',2,receipt(3,1)))
            env.put(t['renderer']+0x18,target)
            front=env.get(t['renderer']+0x10)
            back=env.get(t['renderer']+0x14)
            env.put(back+0x10,641,479)
            front_wrapper=env.get(front+0x2c)
            back_wrapper=env.get(back+0x2c)
            env.put(front_wrapper+0x7c,11,23,653,503)
            env.put(back_wrapper+0x7c,31,43,673,523)
            env.put(target+0x2c,front_wrapper)
            env.put(t['obj']+0x180,t['name'])
            env.put(env.get(env.get(front_wrapper+8))+0x1c,env.stub('reset presentation blit','stdcall',6,receipt(5)))
            env.put(env.get(env.get(back_wrapper+8))+0x14,env.stub('reset surface copy','stdcall',6,receipt(4)))
            return t
        yield Case(f'active screen reset callback ordering {address:x}',address,active_reset,receiver=lambda t:t['obj'],arguments=(0x5141,) if address==0x40dca0 else ())
    def busy_voice_category(env):
        t=enabled_sound(env)
        holder=env.get(t['sound']+0x10)
        first=env.get(holder+0x30)-4
        second=env.object(0x40,'second reusable sound voice',fill=0)
        interface=env.get(first+0xc)
        device=env.get(first+0x10)
        env.put(first+4,second+4,0)
        env.put(second+4,0,first+4,interface,device,0x216,16000,245,-678)
        env.put(second+0x30,1)
        env.put(holder+0x34,second+4)
        def status(e,c):
            n=e.get(t['log'])
            e.put(t['log'],n+1)
            e.put(t['log']+4+n*32,0x24,c.receiver,len(c.arguments),*c.arguments)
            e.put(c.arguments[1],1 if e.calls_so_far(status_function)==1 else 0)
            return 0
        status_function=env.stub('DirectSoundBuffer busy then reusable','stdcall',2,status)
        env.put(env.get(interface)+0x24,status_function)
        label=env.cstr(env.get(0x523d94+2*32)).decode()
        map_entry(env,env.get(t['services']+0x28),label,t['sound'])
        return t
    yield Case('enabled category chooses second reusable voice',0x499450,busy_voice_category,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    def resource_map(env,service,entries):
        bucket=env.object(4,'populated resource buckets',fill=0)
        link=0
        for label,value in entries.items():
            text=env.object(len(label)+1,'resource key '+label,data=label.encode()+b'\0')
            link=env.object(16,'resource link '+label,words=[link,0,text,value])
        env.put(bucket,link)
        env.put(service+0x14,bucket,1)
    def populate_visuals(env,t):
        names={'BOOTY_SYMBOLS','BOOTY_SCORENUMBERS','BOOTY_PERFECT','BOOTY_GLITTER'}
        for category in range(9):
            stem=env.cstr(env.get(0x523d90+category*32)).decode()
            names.add(stem)
            for suffix in range(4):
                names.add(stem+env.cstr(env.get(0x523eb0+suffix*4)).decode())
        entries={}
        for serial,name in enumerate(sorted(names)):
            image=env.object(0x70,'loaded image '+name,fill=0)
            frames=env.object(40,'loaded image frames '+name,words=[0x43100000+serial*0x100+j*11 for j in range(10)])
            env.put(image+0x14,frames)
            env.put(image+0x64,0,9)
            entries[name]=image
        resource_map(env,env.get(t['services']+0x10),entries)
        animations={}
        for serial,name in enumerate(('BOOTY_CYCLE100','BOOTY_CYCLE200')):
            frame=env.object(0x30,'loaded animation frame '+name,fill=0)
            env.put(frame+4,1,3,9,0,serial+2,23+serial*18,0x451+serial)
            frames=env.object(4,'loaded animation frames '+name,words=[frame])
            animation_object=env.object(0x20,'loaded animation '+name,fill=0)
            env.put(animation_object+0xc,frames,1)
            animations[name]=animation_object
        resource_map(env,env.get(t['services']+0x2c),animations)
        t['images']=entries
        return t
    def dirty_initial(state):
        def setup(env):
            t=animation(state,timer=13)(env)
            f=factory_scene(env)
            populate_visuals(env,f)
            t['services']=f['services']
            env.put(t['sprite']+0xc,f['services'])
            env.put(t['sprite']+8,0x20340080)
            env.put(t['sprite']+0xc8,0xa127bd35)
            env.put(t['logic']+0x20,0x1947)
            env.put(t['logic']+0x130,13,29,47)
            env.put(t['logic']+0x168,0x78563412)
            env.put(0x53cad4,env.object(0x1c0,'prior perfect announcement',fill=0))
            env.put(0x53cad8,0x31415926)
            env.put(t['sprite']+0x170,f['images']['BOOTY_TREASURE_COINS'])
            return t
        return setup
    yield Case('counter initial state overwrites distinct prior scalar state',0x498930,dirty_initial(0),arguments=(lambda t:t['sprite'],))
    yield Case('flying initial state overwrites distinct prior scalar state',0x498f90,dirty_initial(0),arguments=(lambda t:t['sprite'],))
    for address in (0x499170,0x499450,0x499630,0x499d60):
        def loaded_children(env,address=address):
            t=create_components(env)
            populate_visuals(env,t)
            env.put(t['obj']+0x60,digit_group(env,'previous score',2,193))
            env.put(t['obj']+0x68,digit_group(env,'previous quantity',3,241))
            env.put(t['obj']+0x6c,digit_group(env,'previous maximum',1,17))
            for off in (0x74,0x78,0x7c,0x80,0x84,0x88):
                previous=env.object(0x1c0,'previous symbol '+str(off),fill=0)
                env.put(previous+0x4c,off*19,off*23)
                env.put(t['obj']+off,previous)
            return t
        yield Case('loaded visual children '+hex(address),address,loaded_children,receiver=lambda t:t['obj'],arguments=(lambda t:t['sprite'],))
    for mode in (0,173,0xffffffff):
        def dirty_constructor(env,mode=mode):
            t=construct(env,level=3,missing=None)
            populate_visuals(env,t)
            env.put(0x52d4e0,mode)
            env.put(0x5349a8,0x7abcd123)
            env.put(0x53cac4,7)
            prior1=digit_group(env,'previous shared total',3,765)
            prior2=digit_group(env,'previous shared score',2,321)
            env.put(0x53cac8,prior1,prior2)
            for index in range(9):
                env.put(0x534d08+index*4,index*7+3)
                env.put(0x5381e0+index*4,index*7+3)
            return t
        yield Case('constructor replaces prior result globals '+str(mode),0x40d470,dirty_constructor,receiver=lambda t:t['obj'],arguments=(lambda t:t['app'],3,0x31427185))
    for step in (-3,0,3):
        for mode in (0,1):
            def exact_score(env,step=step):
                t=update_totals(env)
                current=37
                env.put(t['obj']+0x90,current+step,17,step,91)
                env.put(t['obj']+0xb0,119,227)
                return t
            yield Case(f'score reaches exact target step {step} mode {mode}',0x4998c0,exact_score,receiver=lambda t:t['obj'],arguments=(mode,))
    for address,state in ((0x498930,0x232b),(0x498f90,0x2333)):
        def equal_position(env,address=address,state=state):
            t=animation(state,19)(env)
            env.put(t['logic']+0x130,19,37,61)
            env.put(t['logic']+0xac,0)
            env.put(t['sprite']+0x4c,100,200)
            env.write(t['logic']+0x160,struct.pack('<ff',-50000.,-60000.))
            return t
        yield Case('equal target with negative velocity '+hex(address),address,equal_position,arguments=(lambda t:t['sprite'],))
    for address,state in ((0x498930,0x232a),(0x498930,0x232e),(0x498f90,0x2332)):
        def dirty_transition(env,state=state):
            t=animation(state,13)(env)
            env.put(t['logic']+0x20,0x2345)
            env.put(t['logic']+0x130,13,29,47)
            env.put(t['logic']+0x168,0x78563412)
            env.put(t['logic']+0xac,0x12345678)
            env.put(t['logic']+0x64,193,271,319)
            env.write(t['logic']+0x160,struct.pack('<ff',123.25,-271.5))
            env.put(t['sprite']+0x4c,719,853)
            env.put(t['sprite']+0xc8,0xa5b6c7d8)
            return t
        yield Case('transition replaces distinct scalar state '+hex(state)+' callback '+hex(address),address,dirty_transition,arguments=(lambda t:t['sprite'],))
