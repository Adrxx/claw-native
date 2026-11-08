"""Original-only popup lifecycle cases, including callback-visible publication."""
from clawparity.cases import Case

ENTER, LEAVE, FRAME = 0x438E90, 0x438F10, 0x438FA0
RESTORE, REDRAW, CURSOR = 0x4390C0, 0x439130, 0x43A7F0


def setup_popup(values, **config):
    def setup(env):
        p = env.object(0x17C, 'popup', fill=0)
        log = env.object(0x2000, 'callback-observations', fill=0)
        t = {'popup': p, 'log': log}

        def callback(name, argc=0, result=1, convention='thiscall', mutate=None):
            def effect(env, call):
                index = env.get(log)
                slot = log + 4 + index * 64
                env.put(log, index + 1)
                env.put(slot, call.receiver, argc, *call.arguments)
                env.put(slot + 36, env.get(p + 0x154), env.get(p + 0x15C),
                        env.get(p + 0x160), env.get(p + 0x164), env.get(0x5375BC),
                        env.get(0x5430C4), env.get(0x5430C8))
                if mutate:
                    mutate(env, call)
                return result(env, call) if callable(result) else result
            return env.stub(name, convention, argc, effect)

        def table_object(size, name):
            obj = env.object(size, name, fill=0)
            vt = env.object(0x200, name + '-vtable', fill=0)
            env.put(obj, vt)
            return obj, vt

        services = env.object(0x2C, 'services', fill=0)
        graphics = env.object(0x1C, 'graphics', fill=0)
        options = env.object(0x38, 'graphics-options', fill=0)
        audio = env.object(0x30, 'audio-wrapper', fill=0)
        parent, pvt = table_object(0xC, 'parent')
        timeout, tvt = table_object(4, 'timeout-receiver')
        env.put(parent + 8, timeout)
        env.put(tvt + 0x1C, callback('timeout', 2))
        env.put(p + 4, parent)
        env.put(p + 0xC, services)
        env.put(services + 4, graphics)
        env.put(services + 0x28, audio)
        env.put(graphics + 0xC, options)
        t.update(services=services, graphics=graphics, parent=parent)
        def swap_graphics(env, call):
            if config.get('swap_graphics'):
                env.put(services + 4, t['alternate_graphics'])

        for side, offset in [('front', 0x10), ('back', 0x14)]:
            wrapper = env.object(0x30, side + '-wrapper', fill=0)
            surface, svt = table_object(0x8C, side + '-surface')
            com, cvt = table_object(4, side + '-COM')
            env.put(wrapper + 0x2C, surface)
            env.put(surface + 8, com)
            env.put(surface + 0x7C, *values[:4])
            env.put(graphics + offset, wrapper)
            env.put(cvt + 0x60, callback(side + '-status', 1, config.get('status', 0), 'stdcall'))
            env.put(cvt + 0x6C, callback(side + '-restore', 1, config.get('com_restore', 0), 'stdcall'))
            for off, argc, name in [(0x2C, 3, 'flip'), (0x14, 6, 'blit'), (0x44, 2, 'getdc'), (0x68, 2, 'releasedc')]:
                env.put(cvt + off, callback(side + '-' + name, argc, 0, 'stdcall',
                    swap_graphics if name == 'flip' and config.get('swap_on_flip') else None))
            t[side] = wrapper
            t[side + '_surface'] = surface
            t[side + '_com'] = com
        alternate_graphics = env.object(0x1C, 'alternate-graphics', fill=0)
        env.write(alternate_graphics, env.read(graphics, 0x1C))
        env.put(alternate_graphics + 0x10, t['back'], t['front'])
        t['alternate_graphics'] = alternate_graphics

        dialog, dvt = table_object(0x2B8, 'dialog')
        alternate, avt = table_object(0x2B8, 'alternate-dialog')
        t.update(dialog=dialog, alternate=alternate)
        for obj, vt, prefix in [(dialog, dvt, 'dialog'), (alternate, avt, 'alternate')]:
            env.put(obj + 0x2B4, config.get('mode', 3))
            for off, argc, name, result in [(0, 1, 'delete', 0), (0x1D0, 1, 'enter', config.get('enter_result', values[4])),
                    (0x1D4, 1, 'leave', 0), (0x1D8, 0, 'prepare', config.get('prepare', 1)),
                    (0x1DC, 2, 'render', 1), (0x1E0, 0, 'finish', config.get('finish', 1)),
                    (0x1E4, 0, 'restore', config.get('dialog_restore', 1)), (0x1E8, 0, 'special', 0)]:
                def change(env, call, name=name):
                    if name == 'special' and config.get('replace_special'):
                        env.put(p + 0x160, alternate)
                    if name == 'leave' and config.get('clear_leave'):
                        env.put(p + 0x160, 0)
                    if name == 'leave' and config.get('swap_on_leave'):
                        swap_graphics(env, call)
                env.put(vt + off, callback(prefix + '-' + name, argc, result, mutate=change))
        env.put(p + 0x160, dialog)
        env.put(p + 0x15C, t['back_surface'])

        cursor, cvt = table_object(0x178, 'cursor')
        other_cursor, ocvt = table_object(0x178, 'replacement-cursor')
        for obj, vt in [(cursor, cvt), (other_cursor, ocvt)]:
            env.put(obj + 8, values[5] & ~0x10000)
            env.put(obj + 0x40, values[6] | 1)
            env.put(obj + 0x174, 1)
            def deleting_cursor(env, call):
                if config.get('clear_surface_on_cursor_delete'):
                    env.put(p + 0x15C, 0)
                if config.get('replace_dialog_on_delete'):
                    env.put(p + 0x160, alternate)
            env.put(vt + 4, callback('cursor-delete', 1, 0, mutate=deleting_cursor))
            env.put(vt + 0x2C, callback('cursor-draw', 1, values[7]))
        callbacks = env.object(0x14, 'cursor-callbacks', fill=0)
        def cursor_update(env, call):
            if config.get('replace_cursor'):
                env.put(p + 0x154, other_cursor)
                env.put(p + 0x174, values[9], values[10])
            if config.get('swap_on_cursor'):
                swap_graphics(env, call)
        env.put(callbacks + 0x10, callback('cursor-update-cdecl', 1, 0, 'cdecl', cursor_update))
        env.put(cursor + 0x6C, callbacks)
        env.put(p + 0x154, cursor if config.get('cursor', False) else 0)
        env.put(p + 0x174, values[8], values[9])
        t.update(cursor=cursor, replacement_cursor=other_cursor)

        child, chvt = table_object(0x25C, 'child')
        replacement, rhvt = table_object(0x25C, 'replacement-child')
        optional = env.object(0x44, 'child-optional', fill=0)
        env.put(optional + 0x40, values[6] | 1)
        for obj, vt in [(child, chvt), (replacement, rhvt)]:
            env.put(obj + 0x154, cursor if config.get('child_optional', True) else 0)
            env.put(obj + 0x254, optional if config.get('child_optional', True) else 0)
            env.put(obj + 0x258, optional if config.get('child_optional', True) else 0)
            ids = config.get('ids', (0, 0, 0))
            def state(env, call):
                n = env.get(log + 0x1FF0)
                env.put(log + 0x1FF0, n + 1)
                if config.get('null_at') == n:
                    env.put(p + 0x164, 0)
                elif config.get('replace_child') and n == 0:
                    env.put(p + 0x164, replacement)
                return ids[min(n, len(ids) - 1)]
            env.put(vt + 0x10, callback('child-state', result=state))
            def restore_child(env, call):
                if config.get('clear_dialog'):
                    env.put(p + 0x160, 0)
                if config.get('swap_child_restore'):
                    env.put(p + 0x164, replacement)
            env.put(vt + 0x18, callback('child-restore', mutate=restore_child))
            env.put(vt + 0x1C, callback('child-redraw', result=0))
            env.put(vt + 0x14, callback('child-hide'))
        env.put(p + 0x164, child)
        t.update(child=child, replacement_child=replacement)
        pvt = env.object(0x1C, 'popup-vtable', fill=0)
        env.put(p, pvt)
        env.put(pvt + 0xC, callback('popup-redraw-ready', result=config.get('ready', 1)))
        def frame_ready(env, call):
            if config.get('repair_front'):
                env.put(t['front_surface'] + 8, t['front_com'])
        env.put(pvt + 0x18, callback('popup-frame-ready', result=config.get('ready', 1), mutate=frame_ready))
        env.put(p + 0x170, 1)
        env.put(p + 0x34, values[4])
        env.put(0x5375BC, values[7])
        env.put(0x537208, values[5], values[6])
        env.put(0x5430C4, values[9], values[10])

        def show(env, call):
            count = env.calls_so_far(0x546D54)
            if config.get('show_replace') and count == 1:
                env.put(p + 0x160, alternate)
            if call.arguments[0]:
                return 0
            seq = config.get('hide_sequence', (0xFFFFFFFF,))
            return seq[min(count - 1, len(seq) - 1)]
        env.override(0x546D54, show)
        def copy_rect(env, call):
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            return 1
        env.override(0x546D58, copy_rect)
        def position(env, call):
            env.put(call.arguments[0], values[10], values[11])
            return config.get('position_result', 1)
        env.override(0x546CD0, position)
        for field in config.get('nulls', ()):
            env.put(p + field, 0)
        if config.get('no_parent'):
            env.put(p + 4, 0)
        if config.get('no_front'):
            env.put(graphics + 0x10, 0)
        if config.get('missing_com'):
            env.put(t['front_surface'] + 8, 0)
        if config.get('audio'):
            obj = env.object(0x10, 'audio-empty-list', fill=0)
            env.put(audio + 0x2C, obj)
        if config.get('resource'):
            env.put(p + 0x2C, env.object(4, 'opaque-resource', fill=0))
        if config.get('cleanup'):
            cm = env.object(0x28, 'cursor-manager', fill=0)
            sm = env.object(0x3D0, 'surface-manager', fill=0)
            env.put(services + 8, cm)
            env.put(services + 0x1C, sm)
            for obj, field, manager, offset in [(cursor, 0x68, cm, 0x10), (t['back_surface'], 4, sm, 0x3B8)]:
                node = env.object(8, 'registry-node', fill=0)
                env.put(obj + field, node)
                env.put(manager + offset + 4, node, node, 1)
            env.put(env.get(t['back_surface']), callback('surface-delete', 1, 0))
        return t
    return setup


def cases(random_source):
    def case(label, function, arg=None, **config):
        values = [random_source.getrandbits(32) for _ in range(12)]
        # Different nonzero rectangle words expose coordinate width/order errors.
        values[:4] = [random_source.randrange(1, 32), random_source.randrange(33, 64),
                      random_source.randrange(80, 121), random_source.randrange(130, 181)]
        return Case(label, function, setup_popup(values, **config),
                    receiver=lambda t: t['popup'], arguments=() if arg is None else (arg,))

    for flags in (0, 1, 2, 0x100, 0xFFFFFFFF):
        yield case(f'deleting destructor flag {flags:x}', 0x4299B0, flags, nulls=(0x15C, 0x160))
    for cursor in (False, True):
        for surface in (False, True):
            for dialog in (False, True):
                nulls = (() if surface else (0x15C,)) + (() if dialog else (0x160,))
                yield case(f'release cursor={cursor} surface={surface} dialog={dialog}', 0x438E10,
                           cursor=cursor, cleanup=True, nulls=nulls)
    yield case('enter without dialog', ENTER, 13, nulls=(0x160,))
    yield case('enter without parent', ENTER, 13, no_parent=True)
    for arg in (0, 12, 13, 14, 0xFFFFFFFF):
        for mode in (2, 3, 4):
            yield case(f'enter state={arg:x} mode={mode}', ENTER, arg, cursor=True, mode=mode)
    yield case('enter hide loops through positive and zero', ENTER, 13, hide_sequence=(2, 0, 0x80000000), cursor=True)
    yield case('enter reloads dialog after show import', ENTER, 13, show_replace=True)
    yield case('enter reloads dialog after special', ENTER, 13, replace_special=True, cursor=True)
    for arg in (1, 13):
        yield case(f'enter callback returns zero state={arg}', ENTER, arg, enter_result=0)
    for arg in (0, 13, 0xFFFFFFFF):
        yield case(f'leave success {arg:x}', LEAVE, arg, cursor=True)
        yield case(f'leave null dialog {arg:x}', LEAVE, arg, nulls=(0x160,))
    yield case('leave no backing fails', LEAVE, 12, nulls=(0x15C,))
    yield case('leave callback clears dialog before render', LEAVE, 13, clear_leave=True)
    yield case('leave reloads services after leave virtual', LEAVE, 1,
               swap_graphics=True, swap_on_leave=True)
    yield case('leave reloads services between flip and copy', LEAVE, 1,
               swap_graphics=True, swap_on_flip=True)
    yield case('release cursor callback changes remaining resources', 0x438E10,
               cleanup=True, cursor=True, clear_surface_on_cursor_delete=True,
               replace_dialog_on_delete=True)
    for prepare, finish in ((0, 1), (1, 0), (1, 0x80000000)):
        yield case(f'leave state13 ignores render {prepare}/{finish}', LEAVE, 13, prepare=prepare, finish=finish)
    for config in ({}, {'cursor': True}, {'cursor': True, 'replace_cursor': True}, {'audio': True},
                   {'status': 1}, {'missing_com': True, 'repair_front': True},
                   {'status': 1, 'ready': 0}, {'missing_com': True, 'ready': 0},
                   {'nulls': (0x15C,)}, {'nulls': (0x160,)}, {'prepare': 0}, {'finish': 0},
                   {'cursor': True, 'position_result': 0}):
        yield case(f'frame {config}', FRAME, **config)
    for config in ({'no_front': True, 'nulls': (0x164,)},
                   {'status': 1, 'com_restore': 1}, {'no_front': True},
                   {'no_front': True, 'clear_dialog': True}, {'no_front': True, 'dialog_restore': 0},
                   {'no_front': True, 'swap_child_restore': True}):
        yield case(f'restore {config}', RESTORE, no_parent=True, prepare=0, **config)
    for config in ({'ready': 0}, {}, {'resource': True, 'nulls': (0x164,)}, {'resource': True}):
        yield case(f'redraw {config}', REDRAW, no_parent=True, **config)
    yield case('restore cursor no child', CURSOR, nulls=(0x164,))
    for ids in ((13,), (0, 5), (0, 0, 11), (0, 0, 0), (5, 13, 5), (11, 11, 11)):
        for optional in (False, True):
            yield case(f'restore cursor ids={ids} optional={optional}', CURSOR,
                       ids=ids, child_optional=optional)
    for ids, n in (((13,), 0), ((0, 5), 1), ((0, 0, 11), 2)):
        yield case(f'restore cursor callback nulls at {n}', CURSOR, ids=ids, null_at=n)
        yield case(f'restore cursor replacement ids={ids}', CURSOR, ids=ids, replace_child=True)
    for _ in range(8):
        yield case('random cursor coordinates and callback state', FRAME, cursor=True,
                   replace_cursor=bool(random_source.getrandbits(1)))
    yield case('frame callback replaces cursor and graphics graph', FRAME, cursor=True,
               replace_cursor=True, swap_graphics=True, swap_on_cursor=True)
