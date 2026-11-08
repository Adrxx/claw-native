"""Independent original-derived player publication and physical dialog cases."""
from clawparity.cases import Case
from clawparity.env import DialogCallbackContract, NativeSourceContext, Halt
from clawparity.kernel import STACK_TOP
from clawparity.program import CLAW_SHA256


IDENTITIES = (
    (0x49b730, 0x49b83d, '253fb62a4a33e89b2b6e3ac0ec33fbbf7f7ca536159e99bd4db6a61d22fc71e3'),
    (0x49b160, 0x49b393, 'e9c3e3f6220163984476c7b77733d431504b22d871fc674565c7ff2016d4153e'),
    (0x49b630, 0x49b72b, 'd8d4f3f1cf5f6ec2f6becf08c4f3fe2830cffe71da5e10116db49105bf88ad6d'),
)


def world(words, *, names=(b'Player', b'Claw', b'Swash'), current=1,
          count=None, cache=True, selection=2, text=None, text_result=None,
          add_results=(0, 1, 2), find=1, item=0x1043b,
          cursor=(1, 2), scene=False, modal='accept', no_app=False,
          no_manager=False, mutate=None, source=0, text_no_write=False):
    def setup(env):
        app = env.object(0x70, 'application', fill=0xa7)
        manager = env.object(0x10, 'player-list', fill=0)
        window = env.object(8, 'window-owner', words=[0x12345678, 0x9090])
        module = env.object(0x10, 'module-owner', fill=0)
        env.put(module + 12, 0x5151)
        players = []
        nodes = []
        for index, name in enumerate(names):
            if name is None:
                players.append(0)
            else:
                player = env.object(0x2700, f'player-{index}', fill=0x91 + index)
                env.write(player + 0x14, name + b'\0')
                env.write(player + 0x36, b'Home\0')
                env.write(player + 0x88, b'Info\0')
                env.put(player + 0x2618, *words[:10])
                env.put(player + 0x25d4, *words[10:])
                players.append(player)
            nodes.append(env.object(12, f'node-{index}', fill=0))
        for i, node in enumerate(nodes):
            env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0, 0x98760000 + i, players[i])
        env.put(manager + 4, nodes[0] if nodes else 0)
        env.put(manager + 12, len(nodes) if count is None else count)
        env.put(app + 4, window, module)
        env.put(app + 0x30, 0)
        env.put(app + 0x60, 0 if no_manager else manager, players[current] if current is not None else 0)
        target = env.object(0x70, 'cache', fill=0xd3)
        env.put(0x5371fc, 0 if no_app else app)
        env.put(0x537204, target if cache else 0)
        env.put(0x53725c, 0xfedcba98)
        env.put(0x537e88, 0)
        env.put(0x540e88, 0)
        env.put(0x53ebec, item)
        env.put(0x53ebe0, 0xbad01234)
        # Physical control storage and durable call snapshots are ordinary live
        # memory, independently restored for each comparison side.
        state = env.object(0x2000, 'physical-control-state', fill=0)
        log = env.object(0x10000, 'physical-observation-log', fill=0)
        env.put(state + 8, selection & 0xffffffff)

        def record(e, call):
            n = e.get(log)
            p = log + 4 + n * 64
            e.put(log, n + 1)
            e.put(p, call.function, call.receiver, len(call.arguments), *call.arguments)
            e.put(p + 32, e.get(app + 0x64), e.get(0x53725c), e.get(0x53ebe0), e.get(0x53ebec))
            return p

        def send(e, call):
            record(e, call)
            hwnd, message, w, l = call.arguments
            if message == 0x184:
                e.put(state, 0, 0)
                if mutate == 'reset-count':
                    e.put(manager + 12, 0)
                if mutate == 'reset-head' and nodes:
                    e.put(manager + 4, nodes[-1])
                return 0
            if message == 0x180:
                if mutate == 'halt-add' or (mutate == 'halt-second-add' and e.get(state) == 1):
                    raise Halt()
                n = e.get(state)
                value = e.cstr(l)
                if isinstance(value, str):
                    value = value.encode()
                e.write(state + 0x100 + n * 256, value + b'\0')
                e.put(state, n + 1)
                result = add_results[min(n, len(add_results) - 1)]
                if mutate == 'next' and n == 0 and len(nodes) > 1:
                    e.put(nodes[0], 0)
                if mutate == 'selected-name' and n == 0 and players:
                    e.write(players[-1] + 0x14, b'Renamed\0')
                return result & 0xffffffff
            if message == 0x18f:
                return find & 0xffffffff
            if message == 0x186:
                e.put(state + 4, w)
                return w
            if message == 0x188:
                return e.get(state + 8)
            if message == 0x189:
                e.put(log + 4 + (e.get(log) - 1) * 64 + 52, e.read(l, 1)[0])
                if text_no_write:
                    return 0
                value = text
                if value is None:
                    value = names[selection] if 0 <= selection < len(names) else b'absent'
                if value is not None:
                    e.write(l, value + b'\0')
                return (len(value or b'') if text_result is None else text_result) & 0xffffffff
            return 0

        def end(e, call):
            record(e, call)
            e.put(state + 16, 1, call.arguments[1])
            return 1

        def get_item(e, call):
            record(e, call)
            return item if call.arguments[1] == 0x43b else 0x10000 + call.arguments[1]

        def set_text(e, call):
            p = record(e, call)
            value = e.cstr(call.arguments[2])
            if isinstance(value, str):
                value = value.encode()
            # Preserve the physical control's displayed content for comparison.
            e.write(state + 0x1100, value[:255] + b'\0')
            e.put(p + 48, len(value))
            return 0 if mutate == 'text-failure' else 1

        def cursor_effect(e, call):
            record(e, call)
            n = e.get(state + 24)
            e.put(state + 24, n + 1)
            return cursor[min(n, len(cursor) - 1)] & 0xffffffff

        def plain(e, call):
            record(e, call)
            return 0 if mutate == 'post-failure' else 1

        def clock(e, call):
            record(e, call)
            return (words[0] + e.calls_so_far(call.function) * 137) & 0xffffffff

        def dialog(e, call):
            record(e, call)
            if modal == 'failure':
                return 0xffffffff
            e.put(state + 16, 0, 0)
            hwnd = 0x7777
            e.invoke_dialog_callback(call, (hwnd, 0x110, 0, call.arguments[4]))
            if not e.get(state + 16):
                command = 2 if modal == 'cancel' else 1
                e.invoke_dialog_callback(call, (hwnd, 0x111, command, 0))
            if not e.get(state + 16):
                e.invoke_dialog_callback(call, (hwnd, 0x111, 2, 0))
            return e.get(state + 20)

        for address, effect in ((0x546d44, send), (0x546d34, end), (0x546d40, get_item),
                                (0x546d3c, set_text), (0x546d54, cursor_effect),
                                (0x546d50, plain), (0x546df0, clock), (0x546d2c, dialog)):
            env.override(address, effect)
        if scene:
            obj = env.object(4, 'physical-surface')
            vtable = env.object(0x2c, 'physical-surface-vtable', fill=0)
            env.put(obj, vtable)
            env.put(vtable + 0x28, env.stub('physical-surface-restore', 'stdcall', 1, plain))
            slot = env.object(4, 'surface-slot', words=[obj])
            wrapper = env.object(0x18, 'surface-wrapper', fill=0)
            env.put(wrapper + 0x14, words[2])
            sc = env.object(0x20, 'scene', fill=0)
            env.put(sc + 4, wrapper)
            env.put(sc + 0x1c, slot)
            env.put(app + 0x30, sc)
        for address, stop, digest in (IDENTITIES if source else ()):
            env.dialog_callback(DialogCallbackContract(CLAW_SHA256, 0x546d2c, 0x42bb7b,
                0x42bb81, address, stop, digest, native_owned=address == 0x49b730))
        result = dict(app=app, manager=manager, players=players, cache=target, nodes=nodes)
        if source:
            result['source'] = NativeSourceContext(72, 1, 0x7ff, 0x5f3,
                words[3], words[4], app, words[5], words[6], words[7],
                STACK_TOP - 0x100, STACK_TOP, source, 0x8d7, 0xffffffff, 0x472, 0, 0)
        return result
    return setup


def cases(random_source):
    words = [random_source.getrandbits(32) for _ in range(20)]
    app = lambda t: t['app']
    manager = lambda t: t['manager']
    player = lambda t: t['players'][1]
    for argument in (0, 0xffffd9fc):
        yield Case(f'copy null-base {argument:x}', 0x430ac0, world(words),
                   receiver=lambda t: t['cache'], arguments=(argument,))
    for delta in (None, 0, 0x260c, 0x2608, 0x25c8, 0x25cc):
        def overlap(env, delta=delta):
            t = world(words)(env)
            t['dest'] = t['cache'] if delta is None else t['players'][1] + delta
            return t
        yield Case(f'copy interleaved overlap {delta}', 0x430ac0, overlap,
                   receiver=lambda t: t['dest'], arguments=(player,))
    for flag in (0, 1, 4, 5, 0x7f, 0x80, 0x84, 0xff):
        for cache in (False, True):
            def publish_setup(env, flag=flag, cache=cache):
                t = world(words, cache=cache)(env)
                env.write(t['players'][1] + 4, bytes([flag]))
                return t
            yield Case(f'publish flag {flag:x} cache {cache}', 0x42bf90, publish_setup,
                       receiver=app, arguments=(player,))
    yield Case('publish clears old bit on null', 0x42bf90, world(words), receiver=app, arguments=(0,))
    # Application/cache alias: copy's +0x64 store changes the player that must
    # be reloaded before computing the flag.
    def publication_alias(env):
        t = world(words)(env)
        env.put(0x537204, t['app'])
        env.put(t['players'][1] + 0x25f0, t['players'][2])
        env.write(t['players'][2] + 4, b'\x04')
        return t
    yield Case('publication reloads aliased current player', 0x42bf90, publication_alias,
               receiver=app, arguments=(player,))
    yield Case('post player command exact words', 0x42bbb0, world(words), receiver=app)
    yield Case('post failure ignored', 0x42bbb0, world(words, mutate='post-failure'), receiver=app)
    for current, names in ((1, (b'Player', b'Claw', b'Swash')), (None, (b'other', b'pLaYeR', b'x')),
                           (None, (b'no match', b'Claw', b'Swash'))):
        for hwnd in (0, 0x5555):
            yield Case(f'display {current} {names} hwnd {hwnd}', 0x49b050,
                       world(words, current=current, names=names), arguments=(hwnd,))
    for selection, text, result in ((-1, None, None), (-2, b'cLaW', None), (0, b'pLaYeR', -2),
                                    (1, b'Claw', -1), (1, b'absent', None), (2, b'sWaSh', None),
                                    (0, b'', 0), (0, b'Claw\0ignored', None),
                                    (0, b'\xc0name', None), (0, b'X' * 255, None)):
        yield Case(f'selected {selection} text {text!r} result {result}', 0x49b0c0,
                   world(words, selection=selection, text=text, text_result=result), arguments=(0x1043b,),
                   initial_stack=((-256, bytes(random_source.getrandbits(8) for _ in range(256))),))
    yield Case('selected no HWND', 0x49b0c0, world(words), arguments=(0,))
    for count in (-0x80000000, -1, 0, 1, 0x7fffffff):
        yield Case(f'populate signed count {count}', 0x49c090, world(words, count=count), receiver=manager,
                   arguments=(0x1043b, player, 0))
    yield Case('populate no HWND', 0x49c090, world(words), receiver=manager, arguments=(0, player, 0))
    yield Case('populate positive count null head', 0x49c090, world(words, names=(), current=None, count=7),
               receiver=manager, arguments=(0x1043b, 0, 0))
    for filtering in (0, 1, 0x80000000):
        for found in (-1, -2, 0, 0x7fffffff):
            yield Case(f'populate filter {filtering:x} found {found}', 0x49c090,
                       world(words, names=(b'pLaYeR', b'Claw', b''), find=found, add_results=(-1, -2, 7)),
                       receiver=manager, arguments=(0x1043b, player, filtering))
    yield Case('populate null node player unfiltered', 0x49c090,
               world(words, names=(None, b'Claw', b'Swash')), receiver=manager, arguments=(0x1043b, 0, 0))
    for mutation in ('next', 'selected-name', 'reset-count', 'reset-head'):
        yield Case(f'populate callee changes {mutation}', 0x49c090, world(words, mutate=mutation),
                   receiver=manager, arguments=(0x1043b, lambda t: t['players'][-1], 0))
    for no_app, no_manager, item, current in ((True, False, 0x1043b, 1), (False, True, 0x1043b, 1),
                                             (False, False, 0, 1), (False, False, 0x1043b, 1),
                                             (False, False, 0x1043b, None)):
        yield Case(f'init app {no_app} manager {no_manager} item {item} current {current}', 0x49b730,
                   world(words, no_app=no_app, no_manager=no_manager, item=item, current=current),
                   arguments=(0x7777, 0x110, 0, 0))
    for message, wparam, lparam, item in ((0, 0, 0, 0x1043b), (0x112, 1, 0, 0x1043b),
             (0x111, 1, 0, 0x1043b), (0x111, 2, 0, 0x1043b), (0x111, 1, 0, 0),
             (0x111, 0x20001, 0x1043b, 0x1043b), (0x111, 0x20002, 0, 0x1043b),
             (0x111, 0x10003, 0x1043b, 0x1043b), (0x111, 0x20003, 0, 0),
             (0x111, 0x20003, 0x1043c, 0x1043b)):
        yield Case(f'proc message {message:x} wparam {wparam:x} lparam {lparam:x} item {item:x}',
                   0x49b730, world(words, item=item), arguments=(0x7777, message, wparam, lparam))
    for args in ((0, 0x49b730), (0x525f30, 0)):
        yield Case(f'dialog shortcut {args}', 0x42bb00, world(words), receiver=app, arguments=args)
    # Ordinary wrappers use only creation failure: real callbacks require the
    # separately declared ambient source transport.
    for function in (0x42bb00, 0x42bbd0, 0x42bbe0, 0x42bbf0):
        yield Case(f'ordinary creation failure {function:x}', function, world(words, modal='failure'),
                   receiver=app, arguments=(0x525f30, 0x49b730) if function == 0x42bb00 else ())
    for current, count in ((None, 3), (1, -1), (1, 0), (1, 1)):
        yield Case(f'remove shortcut current {current} count {count}', 0x42bbf0,
                   world(words, current=current, count=count), receiver=app)
    # Actual EndDialog-derived modal outcomes, including original remove-player
    # lookup and its real write to the saved-selection global before command 6.
    for function, continuation in ((0x42bb00, 0x42bbdf), (0x42bbd0, 0x45c752),
                                   (0x42bbe0, 0x45c73a), (0x42bbf0, 0x45c76a)):
        for modal in ('accept', 'cancel', 'failure'):
            yield Case(f'source modal {function:x} {modal}', function,
                       world(words, source=function, modal=modal), receiver=app,
                       arguments=(0x525f30, 0x49b730) if function == 0x42bb00 else (),
                       source_context=lambda t: t['source'], source_return_pc=continuation)
    for index, cursor in enumerate(((0, 0, -1), (-3, -2, -1, 0, 2, 1, 0, -1), (0x7fffffff, 0),
                                    (-0x80000000, 0, -0x80000000))):
        yield Case(f'dialog signed cursor {index}', 0x42bb00,
                   world(words, cursor=cursor, scene=index == 1, source=0x42bb00), receiver=app,
                   arguments=(0x525f30, 0x49b730), source_context=lambda t: t['source'], source_return_pc=0x42bbdf)

    for args in ((0, 0x49b730), (0x525f30, 0)):
        yield Case(f'source dialog shortcut {args}', 0x42bb00,
                   world(words, source=0x42bb00), receiver=app, arguments=args,
                   source_context=lambda t: t['source'], source_return_pc=0x42bbdf)
    for current, count in ((None, 3), (1, -1), (1, 1)):
        yield Case(f'source remove shortcut {current} {count}', 0x42bbf0,
                   world(words, source=0x42bbf0, current=current, count=count), receiver=app,
                   source_context=lambda t: t['source'], source_return_pc=0x45c76a)
    yield Case('source remove failed selection then real cancel', 0x42bbf0,
               world(words, source=0x42bbf0, selection=-1), receiver=app,
               source_context=lambda t: t['source'], source_return_pc=0x45c76a)

    yield Case('successful empty text leaves initialized buffer untouched', 0x49b0c0,
               world(words, names=(b'Player', b'', b'X'), selection=1, text_no_write=True),
               arguments=(0x1043b,), initial_stack=((-256, b'X\0' + bytes(254)),))

    def global_flag_player(env, source=0):
        t = world(words, source=source, cache=False, selection=1)(env)
        # The program data region is valid backing. Player+4 deliberately
        # aliases the global cleared before publication reads its flag.
        t['players'][1] = 0x537258
        env.put(t['nodes'][1] + 8, t['players'][1])
        env.write(t['players'][1] + 0x14, b'Claw\0')
        env.put(0x53725c, 0xffffffff)
        return t

    yield Case('early clear precedes global-backed player flag read', 0x42bf90,
               global_flag_player, receiver=app, arguments=(player,))
    yield Case('source publication clears aliased flag before reading it', 0x42bb00,
               lambda env: global_flag_player(env, 0x42bb00), receiver=app,
               arguments=(0x525f30, 0x49b730), source_context=lambda t: t['source'],
               source_return_pc=0x42bbdf)
    for results in ((-1, -1, -1), (-2, -1, 4)):
        yield Case(f'source populate failed additions {results}', 0x42bb00,
                   world(words, source=0x42bb00, add_results=results), receiver=app,
                   arguments=(0x525f30, 0x49b730), source_context=lambda t: t['source'],
                   source_return_pc=0x42bbdf)
    yield Case('source init absent singleton ends with zero', 0x42bb00,
               world(words, source=0x42bb00, no_app=True), receiver=app,
               arguments=(0x525f30, 0x49b730), source_context=lambda t: t['source'],
               source_return_pc=0x42bbdf)
    yield Case('source populate first physical addition stop', 0x42bb00,
               world(words, source=0x42bb00, mutate='halt-add'), receiver=app,
               arguments=(0x525f30, 0x49b730), source_context=lambda t: t['source'],
               source_return_pc=0x42bbdf, expect='halt')

    # INIT must replace the old published list HWND with GetDlgItem's result.
    # Distinct stale input also makes subsequent publication target observable.
    def stale_list_handle(env):
        t = world(words, source=0x42bb00)(env)
        env.put(0x53ebec, 0x12344321)
        return t

    yield Case('source init replaces stale published list handle', 0x42bb00,
               stale_list_handle, receiver=app, arguments=(0x525f30, 0x49b730),
               source_context=lambda t: t['source'], source_return_pc=0x42bbdf)

    for names in ((b'Other', b'pLaYeR', b'Last'), (b'Other', b'Claw', b'Last')):
        def source_default_lookup(env, names=names):
            t = world(words, source=0x42bb00, current=None, names=names, modal='cancel')(env)
            # +0x60 is the manager, +0x64 is deliberately zero at INIT.
            # Keep all other possible manager inputs distinct, backed objects.
            decoy = env.object(0x10, 'distinct-unused-manager', fill=0)
            env.put(t['app'] + 0x5c, decoy)
            return t
        yield Case(f'source init real default lookup {names!r}', 0x42bb00,
                   source_default_lookup, receiver=app, arguments=(0x525f30, 0x49b730),
                   source_context=lambda t: t['source'], source_return_pc=0x42bbdf)

    for flag in (0, 4, 0x80, 0x84):
        def distinct_published_flag(env, flag=flag):
            t = world(words, source=0x42bb00)(env)
            # Publication reads signed byte +4, not an adjacent player field.
            env.put(t['players'][2], 0xffffffff, flag, flag ^ 4)
            return t
        yield Case(f'source selected publication distinct flag {flag:x}', 0x42bb00,
                   distinct_published_flag, receiver=app, arguments=(0x525f30, 0x49b730),
                   source_context=lambda t: t['source'], source_return_pc=0x42bbdf)

    def ordinary_scene_distinct_fields(env):
        t = world(words, modal='failure', cursor=(0, 0, -1))(env)
        vtable = env.object(0x30, 'ordinary-distinct-COM-vtable', fill=0)
        obj = env.object(4, 'ordinary-COM-object', words=[vtable])
        scene_log = env.object(16, 'ordinary-COM-call-observation', fill=0)

        def physical_slot(index):
            def effect(e, call):
                e.put(scene_log, index, call.receiver, call.arguments[0])
                return 0
            return effect

        for offset in (0x24, 0x28, 0x2c):
            env.put(vtable + offset, env.stub(f'ordinary-COM-slot-{offset:x}', 'stdcall', 1,
                                             physical_slot(offset)))
        slot = env.object(4, 'ordinary-COM-slot', words=[obj])
        wrapper = env.object(0x20, 'ordinary-surface-wrapper', fill=0)
        # Original prepareDialogSurface returns before dereferencing this arg;
        # distinct +0x14/+0x18 values remain physical call witnesses.
        env.put(wrapper + 0x14, words[2], words[2] ^ 0xffffffff)
        scene = env.object(0x20, 'ordinary-scene', fill=0)
        env.put(scene + 4, wrapper)
        env.put(scene + 0x1c, slot)
        env.put(t['app'] + 0x30, scene)
        return t

    yield Case('ordinary scene fields COM slot and zero saved cursor', 0x42bb00,
               ordinary_scene_distinct_fields, receiver=app,
               arguments=(0x525f30, 0x49b730))

    for results in ((-1, 2, 3), (-2, 2, 3)):
        yield Case(f'source second addition observes count prefix {results}', 0x42bb00,
                   world(words, source=0x42bb00, mutate='halt-second-add', add_results=results),
                   receiver=app, arguments=(0x525f30, 0x49b730),
                   source_context=lambda t: t['source'], source_return_pc=0x42bbdf, expect='halt')

    # Original INIT 0x49b7e3 publishes GetDlgItem's HWND unconditionally,
    # before checking the singleton/manager. Keep the old global distinct so
    # a missing publication cannot hide behind world's default equal value.
    for no_app in (False, True):
        def ordinary_stale_list_handle(env, no_app=no_app):
            t = world(words, no_app=no_app)(env)
            env.put(0x53ebec, 0x12344321)
            return t
        yield Case(f'ordinary init replaces stale list handle no_app {no_app}',
                   0x49b730, ordinary_stale_list_handle,
                   arguments=(0x7777, 0x110, 0, 0))

    # The original removal wrapper posts operation 6 only for a signed-positive
    # physical modal result. Exercise its ordinary ABI independently of the
    # explicit source-frame callback path; the fixture supplies only the result.
    for modal_result in (1, 0x7fffffff):
        def ordinary_remove_positive_result(env, modal_result=modal_result):
            t = world(words, modal='failure')(env)
            env.override(0x546d2c, lambda e, call: modal_result)
            return t
        yield Case(f'ordinary remove positive modal result {modal_result:x}',
                   0x42bbf0, ordinary_remove_positive_result, receiver=app)
