"""Original-driven branch and state-transition cases for CrazyHook."""
import struct
from clawparity.cases import Case


def setup_case(seed, **opts):
    def setup(env):
        actor = env.object(0x800, 'crazy-hook', fill=0)
        obj = env.object(0x300, 'world-object', fill=0)
        if opts.get('argument_alias'):
            obj = actor + opts['argument_alias']
        logic = env.object(0x200, 'logic-descriptor', fill=0)
        world = env.object(0x100, 'world', fill=0)
        assets = env.object(0x100, 'asset-manager', fill=0)
        player = env.object(0x300, 'player', fill=0)
        player_logic = env.object(0x100, 'player-logic', fill=0)
        player_desc = env.object(0x100, 'player-descriptor', fill=0)
        methods = env.object(0x100, 'virtual-methods', fill=0)
        log = env.object(0x1000, 'callback-observations', fill=0)
        env.put(actor, methods)
        env.put(actor + 0xc, obj, logic)
        env.put(actor + 0x128, obj, obj, logic)
        env.put(actor + 0x178, obj, obj, logic)
        env.put(actor + 0x190, obj, obj, logic)
        env.put(obj + 0xc, world)
        env.put(obj + 0x6c, logic)
        env.put(world + 0x10, assets, assets)
        env.put(world + 0x24, assets, assets, assets)
        tile = env.object(0xa0, 'tile-grid', fill=0)
        rows = env.object(4, 'tile-rows', fill=0)
        tiles = env.object(4, 'empty-tile', words=[0xffffffff])
        env.put(assets + 0x5c, tile)
        env.put(tile + 0x30, 1, 1)
        env.put(tile + 0x20, tiles, rows)
        env.put(tile + 0x8c, 8, 8)
        for off in (0x10,):
            env.put(assets + off + 8, 1)
        env.put(player + 0x6c, player_logic)
        env.put(player_logic + 0x14, player_desc)
        env.put(player_desc + 0x3c, opts.get('weapon', 0))
        env.put(player_desc + 0x14, opts.get('high', 0))
        env.put(player + 0xcc, opts.get('player_mode', 0))
        env.put(0x537e88, player)
        env.put(0x534eac, 0x26b7)
        env.put(0x537964, opts.get('level', 8))
        env.put(0x537210, opts.get('clock', 4000))
        env.put(0x5430c4, 1)
        env.put(0x541334, 1)
        env.put(0x532c0c, 0)
        env.put(0x53c9ac, 0)
        env.put(0x537680, 0)
        env.put(actor + 0x184, opts.get('state', 7))
        env.put(actor + 0x18c, opts.get('direction', 1))
        env.put(actor + 0x2e4, opts.get('threshold', 30))
        env.put(actor + 0x48c, opts.get('then', 1000), opts.get('delay', 2000), opts.get('seen', 1))
        env.put(actor + 0x2fc, 32, 0)
        env.put(actor + 0x138, seed | 1, 0xffffffe3, seed + 43, 67)
        for off in (0x210,0x220,0x230,0x240,0x260):
            env.put(actor + off, seed + off, 0xffffffc3, seed + off + 19, 73)
        env.put(obj + 0x40, 0x5a5a0000 | opts.get('flip', 0))
        env.put(obj + 0x164, 0xa5a5a5a5)
        env.put(obj + 0x38, 3)
        env.put(obj + 8, 0x10000)
        env.put(obj + 0x190, 0x11335577)
        env.put(obj + 0x10c, opts.get('health', 10))
        env.put(actor + 0x50, seed + 5, seed + 6)
        env.put(obj + 0x188 + 8, 0)
        if opts.get('frame'):
            frame = env.object(0x40, 'animation-frame', fill=0)
            env.put(frame + 0x18, seed + 1, 0xfffffff9, seed + 17, 29)
            env.put(obj + 0x174, frame)
        def callback(env, call):
            n = env.get(log)
            env.put(log + 4 + n * 16, call.receiver, len(call.arguments), call.arguments[0] if call.arguments else 0, env.get(actor + 0x184))
            env.put(log, n + 1)
            return 0x3157
        for offset, argc in ((0,0),(0x28,1),(0x44,0),(0x48,0),(0x58,0)):
            env.put(methods + offset, env.stub('virtual-%x' % offset, 'thiscall', argc, callback))
        values = opts.get('randoms', (70,))
        def rand(env, call):
            return values[(env.calls_so_far(0x4a3050)-1) % len(values)] & 0xffffffff
        env.override(0x4a3050, rand)
        def copy_rect(env, call):
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            return 1
        env.override(0x546d58, copy_rect)
        def decrement(env, call):
            a = call.arguments[0]
            v = (env.get(a)-1) & 0xffffffff
            env.put(a,v)
            return v
        env.override(0x5469e8, decrement)
        env.put(actor + 0x1a4, env.get(0x52e1c8) + 12, env.get(0x52e1c8) + 12)
        env.put(actor + 0x2fc, 0)
        def text(s):
            return env.object(len(s)+1, 'text', data=s.encode()+b'\0')
        state_name = opts.get('name', 'LS_OTHER')
        state_text = text(state_name)
        state_row = env.object(4, 'state-name', words=[state_text])
        env.put(logic + 0x1c, 5)
        env.put(0x537698 + 8, 5, 5, state_row, 0, 4, 0, 0)
        env.put(0x5376b4, 0, 0)
        env.put(0x537338 + 8, 5, 5)
        handler_row = env.object(4, 'handler-row')
        env.put(handler_row, env.stub('state-handler', 'thiscall', 0, callback) if opts.get('handler', True) else 0)
        env.put(0x537348, handler_row, handler_row, 4)
        if opts.get('string_ref'):
            for off in (0x1a4,0x1a8):
                ref = env.object(0x20,'refcounted-string',words=[opts['string_ref'],0,0,0])
                env.put(actor+off,ref+12)
        if opts.get('temps'):
            temporary = env.object(8, 'temporary-strings', fill=0)
            env.put(temporary, env.get(0x52e1c8)+12, env.get(0x52e1c8)+12)
            env.put(0x5376b4, temporary, 2)
        if opts.get('grow_temps'):
            env.put(logic + 0x1c, 4)
            def resize_names(env, call):
                out = env.object(max(16, call.arguments[1]), 'grown-state-names', fill=0)
                env.write(out, env.read(call.arguments[0], 4))
                if env.calls_so_far(0x4a9070) == 1:
                    env.put(logic + 0x1c, 6)
                return out
            env.override(0x4a9070, resize_names)
        if opts.get('sound'):
            sound = env.object(0x20, 'sound-handle', fill=0)
            playback = env.object(0x20, 'sound-playback', fill=0)
            engine = env.object(0x80, 'sound-engine', fill=0)
            env.put(sound+0x10,playback)
            env.put(playback+0x10,engine)
            for off in (0x474,0x478,0x47c,0x480):
                env.put(actor+off,sound)
            env.put(0x532c0c,opts.get('enabled',1))
        if opts.get('all_sounds'):
            for offset in range(0x450, 0x484, 4):
                sound = env.object(0x20, 'sound-slot-%x' % offset, fill=0)
                playback = env.object(0x80, 'playback-slot-%x' % offset, fill=0)
                engine = env.object(0x80, 'engine-slot-%x' % offset, fill=0)
                env.put(sound + 0x10, playback)
                env.put(playback + 0x10, engine)
                if opts.get('play_sounds'):
                    voice = env.object(0x80, 'voice-%x' % offset, fill=0)
                    interface = env.object(4, 'buffer-%x' % offset, fill=0)
                    com_methods = env.object(0x60, 'buffer-methods-%x' % offset, fill=0)
                    env.put(engine + 0x78, 1)
                    env.put(playback + 0x30, voice + 4, voice + 4)
                    env.put(voice + 0xc, interface, engine, 0, 22050)
                    env.put(voice + 0x30, 1)
                    env.put(interface, com_methods)
                    def com_callback(env, call):
                        n = env.get(log)
                        env.put(log + 4 + n * 16, call.arguments[0], len(call.arguments),
                                call.arguments[1] if len(call.arguments) > 1 else 0,
                                env.get(actor + 0x184))
                        env.put(log, n + 1)
                        return 0
                    def status_callback(env, call):
                        env.put(call.arguments[1], 0)
                        return com_callback(env, call)
                    for slot, argc in ((0x24, 2), (0x30, 4), (0x3c, 2), (0x40, 2), (0x44, 2)):
                        env.put(com_methods + slot, env.stub('sound-%x-slot-%x' % (offset, slot),
                                'stdcall', argc, status_callback if slot == 0x24 else com_callback))
                env.put(actor + offset, sound)
            env.put(0x532c0c, 1)
        if opts.get('saved_animation'):
            env.put(obj + 0x190, opts['saved_animation'])
            env.put(actor + 0x134, 0xcafebabe)
        if opts.get('dispatch'):
            mode=opts['dispatch']
            env.put(handler_row,0)
            base_handler=env.object(4,'base-state-handler',words=[env.stub('base-state-handler','thiscall',0,callback)])
            env.put(0x537880,4,6,base_handler,base_handler,0)
            env.put(0x537890,0)
            if mode=='missing':
                pass
            else:
                grown_handler = env.stub('grown-handler', 'thiscall', 0, callback)
                def resize(env,call):
                    if mode=='fail': return 0
                    out=env.object(max(16,call.arguments[1]), 'grown-handlers', fill=0)
                    env.write(out,env.read(call.arguments[0],4))
                    if mode=='second' and env.calls_so_far(0x4a9070)==1:
                        env.put(0x537344,3)
                        env.put(0x537350,0)
                        env.put(out,grown_handler)
                    return out
                env.override(0x4a9070,resize)
        if not opts.get('seen',1):
            env.put(0x534eac,opts.get('discriminator',0))
            env.put(actor+0x194,player)
            env.put(player+0x38,opts.get('player_height',0))
            env.put(player+0x50,opts.get('player_y',0))
        if opts.get('refill'):
            env.put(actor+0x2e4,120)
        if opts.get('rich'):
            def resource_map(addresses, sound=False):
                manager = env.object(0x80, 'populated-resource-manager', fill=0)
                bucket = env.object(4, 'resource-bucket', fill=0)
                env.put(manager + 0x14, bucket, 1)
                head = 0
                for number, name_address in enumerate(addresses):
                    value = env.object(0x80, 'distinct-resource-%x' % name_address, fill=0)
                    if sound:
                        playback = env.object(0x80, 'resource-playback', fill=0)
                        env.put(value + 0x10, playback)
                    else:
                        command = env.object(0x40, 'animation-command', fill=0)
                        commands = env.object(4, 'animation-commands', words=[command])
                        env.put(command + 0x1c, 23 + number)
                        env.put(value + 0xc, commands, 1)
                    node = env.object(16, 'resource-node', words=[head, number, name_address, value])
                    head = node
                env.put(bucket, head)
                return manager
            animation_names = (0x526a04, 0x5269e8, 0x5269d0, 0x5269b8, 0x5269a0,
                               0x526988, 0x52696c, 0x526954, 0x52693c, 0x526924,
                               0x52690c, 0x5268f4, 0x5268dc, 0x5234b4)
            sound_names = (0x5268c0, 0x5268a4, 0x526888, 0x52686c, 0x526850,
                           0x526834, 0x526818, 0x5267fc, 0x5267e0, 0x5267c4,
                           0x5267ac, 0x526794, 0x526778, 0x52675c)
            animation_manager = resource_map(animation_names)
            sound_manager = resource_map(sound_names, sound=True)
            env.put(world + 0x28, sound_manager, animation_manager)
            for offset in range(0x308, 0x38c, 4):
                env.put(actor + offset, seed * 131 + offset)
            for offset in range(0x450, 0x498, 4):
                env.put(actor + offset, seed * 257 + offset)
            for offset in (0x28c, 0x290, 0x29c, 0x2a0, 0x2a4, 0x2a8, 0x2ac,
                           0x2b0, 0x2b4, 0x2b8, 0x2bc, 0x2c0, 0x2c4, 0x2c8):
                env.put(actor + offset, seed * 19 + offset)
            for address, value in zip((0x5262b0, 0x5262b4, 0x5262b8),
                                      opts.get('tuning', (1.25, 2.75, 3.5))):
                env.write(address, struct.pack('<f', value))
        if opts.get('maps_only'):
            for offset in range(0x308, 0x38c, 4):
                env.put(actor + offset, 0)
            for offset in range(0x450, 0x498, 4):
                env.put(actor + offset, 0)
        if opts.get('argument_alias'):
            env.put(obj + 0xc, world)
            env.put(obj + 0x6c, logic)
        if opts.get('attack_flag'):
            env.put(actor + 0x2fc, 10, 0x200)
        if opts.get('publish_sound'):
            # Original 48ce40 publishes its object and cue through this graph.
            controller = env.object(0x200, 'sound-publication-controller', fill=0)
            controller_logic = env.object(0x40, 'sound-publication-logic', fill=0)
            env.put(controller + 0x6c, controller_logic)
            env.put(controller + 0x184, seed + 0x1357)
            env.put(controller_logic + 0x1c, seed + 0x2468)
            env.put(0x53c9ac, controller)
            env.put(0x53c9a8, 0)
            env.put(0x53c9b0, seed + 0x369a)
        if opts.get('rectangle_updates_tuning'):
            def set_rect_and_update_tuning(env, call):
                env.put(call.arguments[0], *call.arguments[1:])
                env.put(actor + 0x290, seed + 0x7319)
                return 1
            env.override(0x546d5c, set_rect_and_update_tuning)
        if opts.get('distinct_actor_neighbors'):
            # The adapter's neighbors are backed but are not aliases of its actor.
            neighbors = [env.object(0x300, 'actor-pointer-neighbor-%d' % i, fill=0)
                         for i in range(2)]
            env.put(actor + 0x128, neighbors[0], obj, neighbors[1])
            for i, target in enumerate((obj, *neighbors)):
                for off in (0x118, 0x128, 0x138):
                    env.put(target + off, seed + 101 * i + off, seed + 7,
                            seed + 101 * i + off + 31, seed + 11)
        if 'entry_x87_status' in opts:
            env.entry_x87_status(opts['entry_x87_status'])
        return dict(actor=actor,obj=obj,logic=logic,player=player,log=log)
    return setup


def cases(random_source):
    seeds = [random_source.randrange(1,200) for _ in range(3)]
    for seed in seeds:
        for f in (0x434880,0x435700,0x435720,0x435740,0x4354e0,0x4355a0):
            for r in (0,34,35,39,40,99,0xffffffff):
                yield Case('%x seed%d rand%x'%(f,seed,r),f,setup_case(seed,randoms=(r,)),receiver=lambda t:t['actor'])
        for flags in (0,1,2,3):
            yield Case('delete flags%d seed%d'%(flags,seed),0x434860,setup_case(seed),receiver=lambda t:t['actor'],arguments=(flags,))
        for frame in (False,True):
            for flip in (0,2):
                for clock in (2999,3000,3001):
                    yield Case('hold frame%s flip%d clock%d seed%d'%(frame,flip,clock,seed),0x435600,setup_case(seed,frame=frame,flip=flip,clock=clock),receiver=lambda t:t['actor'])
        for state in range(8):
            for rand in (0,29,30,59,60,120):
                yield Case('home state%d rand%d seed%d'%(state,rand,seed),0x434eb0,setup_case(seed,state=state,randoms=(rand,),level=9),receiver=lambda t:t['actor'])
        for state in (1,2,3,4,6):
            for rand in (0,19,20,99):
                yield Case('strike state%d rand%d seed%d'%(state,rand,seed),0x434d30,setup_case(seed,state=state,randoms=(rand,)),receiver=lambda t:t['actor'],arguments=(0x52720c,))
        for state in (6,7):
            for rand in (0,19,20,99):
                yield Case('idle state%d rand%d seed%d'%(state,rand,seed),0x4350e0,setup_case(seed,state=state,randoms=(rand,)),receiver=lambda t:t['actor'])
        for direction in (1,2):
            for flip in (0,2):
                for name in ('LS_HOLDHOOK','LS_OTHER'):
                    yield Case('hit dir%d flip%d %s seed%d'%(direction,flip,name,seed),0x4353a0,setup_case(seed,direction=direction,flip=flip,name=name),receiver=lambda t:t['actor'],arguments=(0x52720c,))
        for name in ('LS_HITLOW','LS_HITHIGH','LS_OTHER'):
            yield Case('damage '+name+' seed%d'%seed,0x435140,setup_case(seed,name=name),receiver=lambda t:t['actor'],arguments=(lambda t:t['obj'],))
        for direction in (1,2):
            yield Case('damage level9 block%d seed%d'%(direction,seed),0x435140,setup_case(seed,level=9,weapon=1,player_mode=1,direction=direction),receiver=lambda t:t['actor'],arguments=(lambda t:t['obj'],))
        yield Case('state dispatch seed%d'%seed,0x434950,setup_case(seed),receiver=lambda t:t['actor'],arguments=(5,))
    yield Case('constructor',0x434250,setup_case(seeds[0]),receiver=lambda t:t['actor'],arguments=(lambda t:t['obj'],))

    for mode,index in (('missing',5),('grow',4),('grow',6),('second',4)):
        yield Case('dispatch '+mode+str(index),0x434950,setup_case(41,dispatch=mode),receiver=lambda t:t['actor'],arguments=(index,))
    for f in (0x435140,0x4353a0,0x4354e0):
        for enabled in (0,1):
            yield Case('sound %x enabled%d'%(f,enabled),f,setup_case(47,sound=True,enabled=enabled,temps=True,high=1),receiver=lambda t:t['actor'],arguments=((lambda t:t['obj']),) if f!=0x4354e0 else ())
    for discriminator in (0,0x26b7):
        for y in (-50,-49,0,49,50):
            for r in (0,70):
                yield Case('home sight%d y%d rand%d'%(discriminator,y,r),0x434eb0,setup_case(41,seen=0,discriminator=discriminator,player_y=y,randoms=(r,),direction=2),receiver=lambda t:t['actor'])
    for state in (1,2):
        yield Case('home elapsed short %d'%state,0x434eb0,setup_case(41,state=state,clock=2999,refill=True,randoms=(59,)),receiver=lambda t:t['actor'])

    for f in (0x435140, 0x4353a0):
        yield Case('state name growth %x' % f, f,
                   setup_case(53, grow_temps=True),
                   receiver=lambda t: t['actor'], arguments=(lambda t: t['obj'],))

    for tuning in ((1.25, 2.75, 3.5), (0.5, 0.75, 0.25)):
        yield Case('constructor populated resources %s' % (tuning,), 0x434250,
                   setup_case(59, rich=True, tuning=tuning),
                   receiver=lambda t:t['actor'], arguments=(lambda t:t['obj'],))
    # Observe the exact environment at the constructor's immediate return, after
    # the real base constructor, owned conversions, home publication and idle
    # descendants. No fixture calculates or supplies the expected status word.
    for flags in (0, 0x20, 0x21):
        for tuning in ((0.125, 0.375, 0.0625), (1.025, 2.075, 0.3375),
                       (1.25, 2.75, 3.5), (0.5, 0.75, 0.25)):
            yield Case('constructor exact return flags%x factors%s' % (flags, tuning),
                       0x434250,
                       setup_case(seeds[2], rich=True, tuning=tuning,
                                  entry_x87_status=flags),
                       receiver=lambda t:t['actor'], arguments=(lambda t:t['obj'],))
    for count in (1, 2):
        yield Case('destructor refcount %d' % count, 0x434880,
                   setup_case(61, string_ref=count), receiver=lambda t:t['actor'])

    for function in (0x4354e0, 0x4355a0):
        yield Case('save distinct current animation %x' % function, function,
                   setup_case(67, saved_animation=0x12345678), receiver=lambda t:t['actor'])
    for function in (0x435740, 0x4354e0, 0x4350e0, 0x4353a0, 0x435140, 0x434d30):
        for random_value in (0, 1, 19, 20, 34, 35, 39, 40, 99, 0xffffffff):
            yield Case('distinct sound slots %x rand%x' % (function, random_value), function,
                       setup_case(71, all_sounds=True, state=1, randoms=(random_value,)),
                       receiver=lambda t:t['actor'],
                       arguments=(lambda t:t['obj'],) if function in (0x435140,0x4353a0,0x434d30) else ())

    for function in (0x4354e0, 0x4353a0, 0x435140, 0x4350e0, 0x435740):
        for r in (0, 1):
            yield Case('physical sound %x rand%d' % (function, r), function,
                       setup_case(73, all_sounds=True, play_sounds=True, randoms=(r,), high=1),
                       receiver=lambda t:t['actor'],
                       arguments=(lambda t:t['obj'],) if function in (0x435140,0x4353a0) else ())
    for action in (1, 3, 6):
        for r in (0, 20):
            yield Case('strike populated map action%d rand%d' % (action, r), 0x434d30,
                       setup_case(79, rich=True, maps_only=True, state=action, attack_flag=True, randoms=(r,)),
                       receiver=lambda t:t['actor'], arguments=(0x526a2c,))
    yield Case('damage populated animation map', 0x435140,
               setup_case(83, rich=True, maps_only=True, high=1),
               receiver=lambda t:t['actor'], arguments=(lambda t:t['obj'],))
    for offset in (0x1a4, 0x1b4, 0x1c4):
        yield Case('constructor argument alias%x' % offset, 0x434250,
                   setup_case(89, argument_alias=offset),
                   receiver=lambda t:t['actor'], arguments=(lambda t:t['obj'],))

    for seed in seeds:
        # A platform callback may update state after the base constructor's stores.
        yield Case('constructor callback updates tuning seed%d' % seed, 0x434250,
                   setup_case(seed, rectangle_updates_tuning=True),
                   receiver=lambda t:t['actor'], arguments=(lambda t:t['obj'],))

    for direction, flip in ((1, 2), (2, 0)):
        for seed in seeds[:2]:
            yield Case('hold distinct actor neighbors dir%d seed%d' % (direction, seed),
                       0x4353a0, setup_case(seed, name='LS_HOLDHOOK', direction=direction,
                                          flip=flip, distinct_actor_neighbors=True),
                       receiver=lambda t:t['actor'], arguments=(lambda t:t['obj'],))

    for r in (0, 1, 69, 70, 0xffffffff):
        yield Case('one-shot cue publication rand%x' % r, 0x434eb0,
                   setup_case(seeds[1], seen=0, all_sounds=True, publish_sound=True,
                              randoms=(r,), state=7), receiver=lambda t:t['actor'])
    for function in (0x4350e0, 0x4354e0, 0x435740):
        for r in (0, 1, 39):
            yield Case('cue object publication %x rand%x' % (function, r), function,
                       setup_case(seeds[2], all_sounds=True, publish_sound=True,
                                  randoms=(r,), state=7), receiver=lambda t:t['actor'])
