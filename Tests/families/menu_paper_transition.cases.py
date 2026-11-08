"""Independent cases from the retail paper-transition instructions."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns

NEW = 0x4F63EC
FREE = 0x4F6428


def physical(env):
    env.override(0x546910,returns(0))
    env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))
    for address, change in ((0x5469E8, -1), (0x5469EC, 1)):
        def atomic(e, c, change=change):
            value = (e.get(c.arguments[0]) + change) & 0xffffffff
            e.put(c.arguments[0], value)
            return value
        env.override(address, atomic)
    for address in (0x546A24, 0x546DF0):
        env.override(address, lambda e, c, a=address: e.calls_so_far(a) * 100)
    env.override(0x546A64, returns(0xffffffff))
    env.override(0x546B0C, returns(2))
    for address in (0x54139c, 0x5413a0, 0x5413a4, 0x5413a8):
        env.put(address, 0)


def surface(env, width=24, height=3, bpp=1, extra=7, salt=31):
    pitch = max(1, width * bpp + extra)
    pixels = env.object(max(512, pitch * max(1, height) + 512), 'surface pixels',
                        data=bytes((i * 37 + salt) & 255 for i in range(max(512, pitch * max(1, height) + 512))))
    target = env.object(0xbc, 'retail surface', fill=0)
    interface = env.object(4, 'DirectDraw surface')
    methods = env.object(0x84, 'DirectDraw methods', fill=0)
    env.put(target, 0x513690)
    env.put(target + 8, interface)
    env.put(target + 0x14, height, width, pitch)
    pixels += 128
    env.put(target + 0x30, pixels)
    env.put(target + 0xa4, bpp * 8)
    env.put(target + 0xac, bpp)
    env.put(methods+0x7c,env.stub('DirectDraw.SetPalette','stdcall',2,returns(0)))
    env.put(interface, methods)
    env.put(methods + 0x64, env.stub('DirectDraw.Lock', 'stdcall', 5, returns(0)))
    env.put(methods + 0x80, env.stub('DirectDraw.Unlock', 'stdcall', 2, returns(0)))
    env.put(methods + 0x14, env.stub('DirectDraw.Blt', 'stdcall', 6, returns(0)))
    env.put(methods + 0x2c, env.stub('DirectDraw.Flip', 'stdcall', 3, returns(0)))
    return target, pixels


def fader(env, mode=1, direction=0, bpp=1, shade=0, height=3, width=24, radius=3, alias=False, salt=19):
    physical(env)
    target = env.object(0x494, 'paper fader', fill=0x6d)
    surfaces = [surface(env, width, height, bpp, extra, salt + i * 53) for i, extra in enumerate((5, 9, 13))]
    if alias:
        surfaces[2] = surfaces[1]
    env.put(target + 4, 1)
    env.put(target + 8, 0, 0, 0, 0, 0)
    env.put(target + 0x1c, 0, 0)
    env.put(target + 0x30, 0)
    env.put(target + 0x38, *(s[0] for s in surfaces))
    for offset, (s, pixels) in zip((0x44, 0x48, 0x4c), surfaces):
        rows = env.object(max(4, height * 4), 'row offsets', fill=0)
        for row in range(max(0, height)):
            env.put(rows + row * 4, row * env.get(s + 0x1c))
        env.put(target + offset, rows)
    env.put(target + 0x50, mode, direction, radius, shade, width, height, width, height, width, height)
    curl = env.object(max(4, radius * 8), 'nonlinear curl offsets', fill=0)
    for i in range(max(0, radius * 2)):
        env.put(curl + i * 4, (i * 3 + 1) % max(1, radius * 2))
    env.put(target + 0x478, curl, *(s[1] for s in surfaces))
    scratch = env.object(512, 'scratch row', data=bytes((i * 13 + 3) & 255 for i in range(512)))
    env.put(target + 0x488, scratch + 128)
    shading = env.object(max(1, radius * 2), 'shading levels', data=bytes((i * 7 + 2) % 32 for i in range(max(1, radius * 2))))
    env.put(target + 0x48c, shading)
    palette = env.object(12, 'palette descriptor', fill=0)
    lookup = env.object(16384, 'palette lookup', data=bytes((i * 11 + i // 64) & 255 for i in range(16384)))
    env.put(palette + 8, lookup)
    if shade:
        env.put(target + 0x1c, palette)
    return {'this': target, 'surfaces': surfaces, 'palette': palette}


def plain(size, fill=0xa7):
    def setup(env):
        physical(env)
        return {'this': env.object(size, 'object', fill=fill)}
    return setup


def initialize(**options):
    def setup(env):
        t = fader(env, **{k: v for k, v in options.items() if k in ('mode', 'direction', 'bpp', 'height', 'width', 'radius', 'salt')})
        obj = t['this']
        init = env.object(44, 'paper init', fill=0)
        surfaces = [s[0] for s in t['surfaces']]
        env.put(obj + 0x24, surfaces[0], surfaces[1])
        env.put(init, 1, *surfaces, options.get('radius', 3), options.get('mode', 1), options.get('direction', 0), options.get('shade', 0), t['palette'])
        env.put(init + 0x24, 0x52e1cc, 0)
        if options.get('defaults'):
            env.put(init + 4, 0, 0, 0)
        if options.get('no_destination'):
            env.put(init + 4, 0)
            env.put(obj + 0x24, 0)
        if options.get('no_source'):
            env.put(init + 8, 0)
            env.put(obj + 0x28, 0)
        if 'mismatch' in options:
            surface_index, offset = options['mismatch']
            env.put(surfaces[surface_index] + offset, 17)
        if 'stale_dimensions' in options:
            # Previous receiver state differs from every value this initializer
            # must publish. Keep valid old surfaces so missed stores remain
            # observable behavior instead of failing fixture setup.
            env.put(obj + 0x38, surfaces[1], surfaces[2], surfaces[0])
            env.put(obj + 0x20, 0x35)
            env.put(obj + 0x50, 2 if options.get('mode', 1) != 2 else 1,
                    1 - options.get('direction', 0), 2,
                    0 if options.get('shade', 0) else 1)
            env.put(obj + 0x60, *options['stale_dimensions'])
            env.put(obj + 0x1c, env.object(12, 'previous palette descriptor', fill=0x61))
            env.put(obj + 0x30, 1)
        t['init'] = 0 if options.get('null') else init
        return t
    return setup


def cases(random_source):
    for state in ('missing','empty','valid','invalid'):
        def application_load(env,state=state):
            physical(env)
            app=env.object(0x90,'application',fill=0)
            vt=env.object(16,'application methods',fill=0)
            env.put(app,vt)
            env.put(vt+12,env.stub('palette enabled','thiscall',0,returns(1)))
            env.put(app+0x58,palette_manager(env))
            entries=[] if state=='missing' else [('STATES_ROLLER_PALETTES_ROLLER',0x434c54,palette_bytes(33),state=='empty')]
            manager,_=namespace(env,entries)
            env.put(app+0x34,manager)
            if state=='invalid':
                def allocate_fail_payload(e,c):
                    size=c.arguments[0]
                    return 0 if size==33 else e.object(max(1,size),'allocation',fill=0)
                env.override(NEW,allocate_fail_payload)
            return {'this':app}
        yield Case('application load palette '+state,0x42a4f0,application_load,receiver=lambda t:t['this'])
    for replacement in (False, True):
        def application_publication(env, replacement=replacement):
            physical(env)
            app=env.object(0x90,'application release publication',fill=0)
            vt=env.object(16,'application publication methods',fill=0)
            env.put(app,vt)
            env.put(vt+12,env.stub('palette enabled publication','thiscall',0,returns(1)))
            env.put(app+0x58,palette_manager(env))
            manager,_=namespace(env,[('STATES_ROLLER_PALETTES_ROLLER',0x434c54,palette_bytes(33),False)],cached_bytes=True)
            env.put(app+0x34,manager)
            log=env.object(8,'application release observations',fill=0)
            alternate=env.object(12,'replacement cached palette',fill=0x53)
            def release_bytes(e,c):
                e.put(log,e.get(app+0x8c),c.arguments[0])
                if replacement:e.put(app+0x8c,alternate)
                e.release(c.arguments[0])
                return 0
            env.override(FREE,release_bytes)
            return {'this':app}
        yield Case(f'application cache published before resource release replace{replacement}',0x42a4f0,application_publication,receiver=lambda t:t['this'])
    for fallback in ('generate','file-fail','file-success'):
        def fallback_setup(env,fallback=fallback):
            tokens=initialize(shade=1)(env)
            env.put(tokens['init']+0x20,0)
            # Failed file loads must clear a previously published palette.
            env.put(tokens['this']+0x1c,tokens['palette'])
            storage=env.object(24,'palette CString storage',fill=0)
            env.put(storage,1,11,11)
            name=storage+12
            env.write(name,b'PALETTE.CLT\0')
            env.put(tokens['init']+0x24,name)
            source=env.object(16,'palette source',fill=0)
            env.put(source+12,env.object(1024,'source colors',data=bytes(i%251 for i in range(1024))))
            env.put(tokens['init']+0x28,source)
            env.override(0x546AD0,returns(0))
            def copy_path(e,c):
                dest,src,count=c.arguments
                raw=e.cstr(src).encode('latin1') if isinstance(e.cstr(src),str) else e.cstr(src)
                e.write(dest,raw[:max(0,count-1)]+b'\0')
                return dest
            env.override(0x5469CC,copy_path)
            env.override(0x546B00,returns(0xffffffff if fallback=='file-fail' else 91))
            def file_read(e,c):
                handle,out,count,done,overlap=c.arguments
                if count==4:e.put(out,128)
                else:e.write(out,bytes((i*29+7)&255 for i in range(count)))
                e.put(done,count)
                return 1
            env.override(0x546AFC,file_read)
            if fallback!='generate':env.override(0x546A64,returns(0))
            else:
                def no_palette(e,c):
                    size=c.arguments[0]
                    return 0 if size==12 and e.calls_so_far(NEW)==2 else e.object(max(1,size),'allocation',fill=0)
                env.override(NEW,no_palette)
            return tokens
        yield Case('initialize palette '+fallback,0x4ee9a0,fallback_setup,receiver=lambda t:t['this'],arguments=(lambda t:t['init'],))
    for responses,restore in (((0,),1),((0x80004005,),1),((0x887601c2,0),1),((0x887601c2,0x80004005),1),((0x887601c2,),0)):
        def copy_setup(env,responses=responses,restore=restore):
            physical(env)
            dst,_=surface(env)
            src,_=surface(env,salt=153)
            vt=env.get(env.get(dst+8))
            def blt(e,c):
                index=min(e.calls_so_far(blt_address)-1,len(responses)-1)
                return responses[index]
            blt_address=env.stub('copy Blt','stdcall',6,blt)
            env.put(vt+0x14,blt_address)
            env.put(dst+0xb4,env.stub('surface restore callback','cdecl',1,returns(restore)))
            env.put(0x54138c,env.stub('display restore fallback','cdecl',0,returns(0)))
            return {'this':dst,'source':src}
        yield Case(f'surface copy responses{responses}',0x4b9c50,copy_setup,receiver=lambda t:t['this'],arguments=(lambda t:t['source'],))
    for cached in (False,True):
        for screen_cached in (False,True):
            for delay in (False,True):
                for flags in ((0,0,0),(1,5,2)):
                    yield Case(f'unroll paperCache{cached} screenCache{screen_cached} delay{delay} flags{flags}',0x48f740,
                               coordinator(function=0x48f740,cached=cached,screen_cached=screen_cached,delay=delay),receiver=lambda t:t['this'],arguments=(lambda t:t['screen'],*flags,3))
    for failure in ('screen-resource','screen-bytes','surface-create','screen','resource','bytes','width','height','fader'):
        yield Case('unroll failure '+failure,0x48f740,coordinator(function=0x48f740,cached=failure in ('width','height','fader'),screen_cached=failure!='screen',failure=failure),receiver=lambda t:t['this'],arguments=(lambda t:t['screen'],0,0,0,3))
    for dimensions in (None,(0,7),(7,0),(-1,7),(7,-1),(-2147483648,1),(1,-2147483648),(1,1),(641,479),(2147483647,123)):
        def bind_surface(env,dimensions=dimensions):
            receiver=env.object(0x34,'image bind receiver',fill=0xa3)
            target=0
            if dimensions is not None:
                width,height=dimensions
                target=env.object(0x1c,'bound surface',fill=0x57)
                env.put(target+0x14,height,width)
            return {'this':receiver,'surface':target}
        yield Case(f'image bind dimensions {dimensions}',0x4d4100,bind_surface,receiver=lambda t:t['this'],arguments=(lambda t:t['surface'],))
    def unlock_reload(env):
        tokens=fader(env)
        obj=tokens['this']
        log=env.object(16,'unlock observations',fill=0)
        def unlock(e,c):
            e.put(log,e.get(obj+0x20),e.get(obj+0x50),c.arguments[0],c.arguments[1])
            e.put(obj+0x40,e.get(obj+0x3c))
            e.put(obj+0x20,0x13572468)
            return 0x80004005
        vt=env.get(env.get(tokens['surfaces'][0][0]+8))
        env.put(vt+0x80,env.stub('unlock publication mutation','stdcall',2,unlock))
        return tokens
    yield Case('render publishes progress then unlock reloads paper alias',0x4eecc0,unlock_reload,receiver=lambda t:t['this'],arguments=(3,))
    def manager_reload(env):
        physical(env)
        manager=palette_manager(env,0,3,0,True)
        def allocate_and_publish(e,c):
            if e.calls_so_far(NEW)==1:e.put(manager+0xc,1)
            return e.object(max(1,c.arguments[0]),'allocated bytes',fill=0x29)
        env.override(NEW,allocate_and_publish)
        data=palette_bytes(11)
        raw=env.object(len(data),'palette serialized',data=data)
        return {'this':manager,'raw':raw,'length':len(data)}
    yield Case('palette vector reloads count after table allocation',0x4c7360,manager_reload,receiver=lambda t:t['this'],arguments=(lambda t:t['raw'],lambda t:t['length']))
    for unroll_delay in (0,2):
        for sound in ('missing','found-muted','found-play'):
            key='DELAYUNROLL' if unroll_delay else 'UNROLL'
            yield Case(f'unroll sound {key} {sound}',0x48f740,coordinator(function=0x48f740,cached=True,delay=False,sound=sound,sound_key=key),receiver=lambda t:t['this'],arguments=(lambda t:t['screen'],0,0,unroll_delay,3))
    for function,unroll_delay in ((0x48f500,0),(0x48f740,0),(0x48f740,2)):
        key='ROLLUP' if function==0x48f500 else ('DELAYUNROLL' if unroll_delay else 'UNROLL')
        yield Case(f'physical sound publication {function:x} delay{unroll_delay}',function,
                   coordinator(function=function,cached=True,delay=False,sound='physical-play',sound_key=key),
                   receiver=lambda t:t['this'],arguments=(3,) if function==0x48f500 else (lambda t:t['screen'],0,0,unroll_delay,3))
    for sound in ('missing','found-muted','found-play'):
        yield Case('paper sound '+sound,0x48f500,coordinator(cached=True,delay=False,sound=sound),receiver=lambda t:t['this'],arguments=(3,))
    yield Case('paper fader initialization rejected',0x48f500,coordinator(failure='fader'),receiver=lambda t:t['this'],arguments=(3,))
    for cached in (False,True):
        for palette in (False,True):
            for delay in (False,True):
                yield Case(f'paper success cached{cached} palette{palette} delay{delay}',0x48f500,
                           coordinator(cached=cached,palette=palette,delay=delay),receiver=lambda t:t['this'],arguments=(3,))
    for function in (0x48f500,0x48f740):
        yield Case(f'paper cache published across cached resource release {function:x}',function,
                   coordinator(function=function,cached=False,cached_resource_bytes=True),receiver=lambda t:t['this'],
                   arguments=(3,) if function==0x48f500 else (lambda t:t['screen'],0,0,0,3))
    for failure in ('surface-create','copy','resource','bytes','width','height'):
        yield Case('paper failure '+failure,0x48f500,coordinator(cached=failure in ('width','height'),failure=failure),receiver=lambda t:t['this'],arguments=(3,))
    yield Case('palette manager initialize',0x4c6260,plain(24),receiver=lambda t:t['this'])
    yield Case('image palette accessor no-op',0x4c96b0,plain(32),receiver=lambda t:t['this'])
    for size in (0,1,7,64):
        for fail in (False,True):
            def stream_setup(env,size=size,fail=fail):
                physical(env)
                table=env.object(12,'palette table',fill=0)
                old=env.object(13,'old table bytes',fill=0x9a)
                env.put(table,0x42,13,old)
                stream=env.object(4,'byte stream',fill=0)
                vt=env.object(64,'stream methods',fill=0)
                env.put(stream,vt)
                def read(e,c):
                    out,count=c.arguments
                    if out==table+4:e.put(out,size)
                    else:
                        e.write(out,bytes((i*17+37)&255 for i in range(count)))
                        # The stream may invalidate the table while reading data;
                        # the owner must publish valid=1 again after it returns.
                        e.put(table,0x6b27d591)
                    return count
                env.put(vt+0x3c,env.stub('CMemFile.Read','thiscall',2,read))
                if fail:env.override(NEW,returns(0))
                return {'this':table,'stream':stream}
            yield Case(f'palette stream size{size} allocationFail{fail}',0x4c7730,stream_setup,receiver=lambda t:t['this'],arguments=(lambda t:t['stream'],))
            def bytes_setup(env,size=size,fail=fail):
                physical(env)
                table=env.object(12,'palette table',fill=0)
                env.put(table,0x7135a9c2)
                data=palette_bytes(size)
                raw=env.object(len(data),'raw palette',data=data)
                if fail:env.override(NEW,returns(0))
                return {'this':table,'raw':raw,'length':len(data)}
            yield Case(f'palette raw size{size} allocationFail{fail}',0x4c7850,bytes_setup,receiver=lambda t:t['this'],arguments=(lambda t:t['raw'],lambda t:t['length']))
    for count,capacity,growth,allocated in ((0,0,0,False),(0,3,0,True),(3,3,0,True),(8,8,1,True),(40,40,0,True),(8200,8200,0,True)):
        def manager_setup(env,count=count,capacity=capacity,growth=growth,allocated=allocated):
            physical(env)
            manager=palette_manager(env,count,capacity,growth,allocated)
            data=palette_bytes(7)
            raw=env.object(len(data),'serialized palette',data=data)
            return {'this':manager,'raw':raw,'length':len(data)}
        yield Case(f'palette vector count{count} cap{capacity} growth{growth}',0x4c7360,manager_setup,receiver=lambda t:t['this'],arguments=(lambda t:t['raw'],lambda t:t['length']))
    for allowed, manager, cache, resources in ((0,1,1,1),(1,0,1,1),(1,1,1,1),(1,1,0,0)):
        def palette_setup(env, allowed=allowed, manager=manager, cache=cache, resources=resources):
            physical(env)
            obj = env.object(0x90, 'application', fill=0)
            vtable = env.object(16, 'application methods', fill=0)
            env.put(obj, vtable)
            env.put(vtable + 12, env.stub('application palette mode', 'thiscall', 0, returns(allowed)))
            env.put(obj + 0x58, env.object(0x18, 'palette manager', fill=0) if manager else 0)
            env.put(obj + 0x8c, env.object(12, 'cached palette', fill=0x49) if cache else 0)
            env.put(obj + 0x34, env.object(0x20, 'resource manager', fill=0) if resources else 0)
            return {'this': obj}
        yield Case(f'palette allowed{allowed} manager{manager} cache{cache} resource{resources}', 0x42a4f0, palette_setup, receiver=lambda t:t['this'])
    for function in (0x48f500, 0x48f740):
        for missing in ('fader', 'surface manager', 'destination'):
            def early(env, missing=missing):
                physical(env)
                obj = env.object(0x44, 'menu state', fill=0x37)
                services = env.object(0x2c, 'services', fill=0)
                chain = env.object(0x18, 'platform chain', fill=0)
                node = env.object(0x30, 'surface node', fill=0)
                env.put(obj + 0xc, services)
                env.put(obj + 0x10, 0 if missing == 'fader' else env.object(0x28, 'fader manager', fill=0))
                env.put(services + 4, chain)
                env.put(chain + 0x10, node)
                env.put(services + 0x1c, 0 if missing == 'surface manager' else env.object(0x400, 'surface manager', fill=0))
                return {'this':obj}
            yield Case(f'coordinator {function:x} missing {missing}',function,early,receiver=lambda t:t['this'],arguments=(1,) if function==0x48f500 else (0,0,0,0,1))
    yield Case('init local nonzero backing', 0x4ecb40, plain(44), receiver=lambda t: t['this'])
    yield Case('fader constructor nonzero backing', 0x4ee880, plain(0x494), receiver=lambda t: t['this'])
    for mask in (0, 1, 2, 0x15, 0x2a, 0x3f):
        def destroy(env, mask=mask):
            physical(env)
            obj = env.object(0x494, 'destroy fader', fill=0)
            for i, offset in enumerate((0x478, 0x44, 0x48, 0x4c, 0x488, 0x48c)):
                env.put(obj + offset, env.object(23 + i, 'owned buffer', fill=0x31 + i) if mask & (1 << i) else 0)
            return {'this': obj}
        yield Case(f'destroy ownership mask {mask}', 0x4ee8e0, destroy, receiver=lambda t: t['this'])
        for flag in (0, 1, 2, 3, 0x100):
            yield Case(f'deleting destructor mask {mask} flag {flag}', 0x4ee8c0, destroy, receiver=lambda t: t['this'], arguments=(flag,))
    for mode in (0, 1, 2, 3, 4, 0xffffffff):
        for width, radius in ((0, 0), (25, 3), (1, 7), (0xfffffff9, 2)):
            yield Case(f'extent mode {mode} width {width} radius {radius}', 0x4efac0,
                       lambda e, m=mode, w=width, r=radius: fader(e, mode=m, width=w, radius=r) if w < 100 else extent_only(e, m, w, r), receiver=lambda t: t['this'])
    for index in range(8):
        radius=random_source.randrange(1,20)
        width=radius*4+random_source.randrange(1,12)
        height=random_source.randrange(1,6)
        mode=random_source.choice((1,2,3))
        yield Case(f'random shaded init {index} radius{radius} width{width} height{height}',0x4ee9a0,initialize(radius=radius,width=width,height=height,mode=mode,shade=1),receiver=lambda t:t['this'],arguments=(lambda t:t['init'],))
    configs = [dict(null=True), dict(no_destination=True), dict(no_source=True), dict(defaults=True)]
    configs += [dict(mismatch=(index, offset)) for index in (1, 2) for offset in (0x14, 0x18)]
    configs += [dict(mode=mode) for mode in (0, 1, 2, 3, 4, 0xffffffff)]
    configs += [dict(radius=0), dict(radius=12, width=8), dict(height=0), dict(height=30, width=24)]
    configs += [dict(shade=1, bpp=bpp) for bpp in (1, 2, 3)]
    for index, opts in enumerate(configs):
        yield Case(f'initialize variant {index} {opts}', 0x4ee9a0, initialize(**opts), receiver=lambda t: t['this'], arguments=(lambda t: t['init'],))
    for mode in (0, 1, 2, 3):
        for direction in (0, 1):
            for bpp in (1, 2, 3, 4):
                for delta in (0, 1, 3):
                    shade = int(bpp == 1 and delta == 3)
                    salt = random_source.randrange(256)
                    for address in (0x4ef010, 0x4ef7d0):
                        for position in ((12, 15, 18) if address == 0x4ef010 and ((mode == 1 and direction) or (mode == 2 and not direction)) else (0, 3, 6)):
                            # Unsupported modes and zero delta never enter a pixel loop.
                            # Retain one direct representative per entry and condition,
                            # without duplicating every unrelated pixel configuration.
                            if mode in (0, 3):
                                if (direction, bpp, delta, position) != (0, 1, 1, 0):
                                    continue
                            elif delta == 0:
                                if (mode, direction, bpp, position) != (1, 0, 1, 0):
                                    continue
                            yield Case(f'curl {address:x} m{mode} d{direction} b{bpp} p{position} n{delta} shade{shade}', address,
                                       lambda e, m=mode, d=direction, b=bpp, sh=shade, s=salt: fader(e, mode=m, direction=d, bpp=b, shade=sh, salt=s),
                                       receiver=lambda t: t['this'], arguments=(position, delta))
            for position in (0, 1, 4, 8, 15, 20, 24):
                for alias in (False, True):
                    yield Case(f'render m{mode} d{direction} p{position} alias{alias}', 0x4eecc0,
                               lambda e, m=mode, d=direction, a=alias: fader(e, mode=m, direction=d, alias=a),
                               receiver=lambda t: t['this'], arguments=(position,))
    for mode in (1, 2, 3):
        for direction in (0, 1):
            stale=tuple(random_source.randrange(31, 48) + index * 19 for index in range(6))
            opts=dict(mode=mode,direction=direction,radius=4+mode,width=48+mode,height=2+direction,
                      shade=direction,stale_dimensions=stale)
            yield Case(f'initialize replaces prior fields mode{mode} direction{direction}',0x4ee9a0,
                       initialize(**opts),receiver=lambda t:t['this'],arguments=(lambda t:t['init'],))


    # Distinct source/paper rows and nonlinear remaps expose wrong offsets,
    # component order, row pitch, and stale scratch bytes at useful row sizes.
    for mode in (1, 2):
        for direction in (0, 1):
            for bpp, shade in ((1, 0), (1, 1), (2, 0), (3, 0)):
                for address in (0x4ef010, 0x4ef7d0):
                    position = 520 if address == 0x4ef010 and ((mode == 1 and direction) or (mode == 2 and not direction)) else 40
                    yield Case(f'large rows {address:x} m{mode} d{direction} b{bpp} shade{shade}', address,
                               lambda e, m=mode, d=direction, b=bpp, sh=shade: fader(e, mode=m, direction=d, bpp=b, shade=sh, width=640, height=7, radius=40),
                               receiver=lambda t:t['this'], arguments=(position, 33))
    for direction in (0, 1):
        yield Case(f'large render initial row direction{direction}', 0x4eecc0,
                   lambda e, d=direction: fader(e, mode=1, direction=d, width=640, height=7, radius=40),
                   receiver=lambda t:t['this'], arguments=(0,))
    for address in (0x4ef010, 0x4ef7d0):
        for kind in ('fader', 'map', 'shades', 'palette descriptor', 'palette lookup', 'source', 'paper', 'destination'):
            position = 15 if address == 0x4ef010 else 3
            yield Case(f'curl scratch aliases {kind} {address:x}', address,
                       lambda e, k=kind, p=position: alias_scratch(e, k, p),
                       receiver=lambda t:t['this'], arguments=(position, 3))
    for shift in (1, 3, 7):
        yield Case(f'render initial row forward overlap +{shift}', 0x4eecc0,
                   lambda e, sh=shift: overlapping_rows(e, sh),
                   receiver=lambda t:t['this'], arguments=(0,))


def alias_scratch(env, kind, position):
    # A single row keeps a remap overwritten after consumption from becoming
    # next-row input. All alias spans remain fully backed, including copy tails.
    t = fader(env, mode=1, direction=1, shade=int(kind in ('shades', 'palette descriptor', 'palette lookup')), height=1)
    obj = t['this']
    if kind == 'fader':
        scratch = obj + 0x100  # unused receiver storage, away from control fields
    elif kind == 'map':
        scratch = env.get(obj + 0x478)
    elif kind == 'shades':
        scratch = env.object(32, 'extended shading alias', data=bytes((i * 7 + 2) % 32 for i in range(32)))
        env.put(obj + 0x48c, scratch)
    elif kind == 'palette descriptor':
        scratch = t['palette']
    elif kind == 'palette lookup':
        scratch = env.get(t['palette'] + 8) + 128
    else:
        index = {'destination': 0, 'source': 1, 'paper': 2}[kind]
        scratch = t['surfaces'][index][1] + position + (1 if kind != 'destination' else -1)
    env.put(obj + 0x488, scratch)
    return t


def overlapping_rows(env, shift):
    t = fader(env, mode=0, direction=0, width=192, height=3)
    obj = t['this']
    source = t['surfaces'][1][1]
    env.put(t['surfaces'][0][0] + 0x30, source + shift)
    env.put(obj + 0x47c, source + shift)
    # Shared pitch makes every destination row overlap its own source forward.
    pitch = env.get(t['surfaces'][1][0] + 0x1c)
    env.put(t['surfaces'][0][0] + 0x1c, pitch)
    rows = env.get(obj + 0x44)
    for row in range(3):
        env.put(rows + row * 4, row * pitch)
    return t


def extent_only(env, mode, width, radius):
    obj = env.object(0x64, 'extent input', fill=0x51)
    env.put(obj + 0x50, mode, 0x134, radius, 0x53, width)
    return {'this': obj}


def palette_bytes(size=48, salt=5):
    return struct.pack('<I', size) + bytes((i * 31 + salt) & 255 for i in range(size))


def palette_manager(env, count=0, capacity=0, growth=0, allocated=False):
    obj = env.object(24, 'palette manager', fill=0)
    env.put(obj, 1, 0x5136e8)
    if allocated:
        old = env.object(max(4, capacity * 4), 'existing palette vector', fill=0)
        env.put(obj + 8, old)
    env.put(obj + 12, count, capacity, growth)
    return obj


def map_insert(env, owner, offset, index, value, buckets=19):
    table = env.get(owner + offset + 4)
    if not table:
        table = env.object(buckets * 16, 'lookup buckets', fill=0)
        env.put(owner + offset + 4, table)
    node = env.object(24, 'lookup node', fill=0)
    env.put(node + 4, env.get(table + 8 + index * 16))
    env.put(node + 20, value)
    env.put(table + 8 + index * 16, node + 4)


def namespace(env, entries, cached_bytes=False):
    root = env.object(0x50, 'resource directory', fill=0)
    env.put(root+0x40,env.object(5*16,'empty directory buckets',fill=0))
    env.put(root+0x48,env.object(9*16,'empty type buckets',fill=0))
    dirs = {'':root}
    for path, typeword, payload, empty in entries:
        pieces = path.split('_')
        directory = root
        key = ''
        for component in pieces[:-1]:
            key += '/' + component
            if key not in dirs:
                child = env.object(0x50, 'resource directory ' + key, fill=0)
                env.put(child+0x40,env.object(5*16,'directory buckets',fill=0))
                env.put(child+0x48,env.object(9*16,'type buckets',fill=0))
                name = env.object(len(component)+1, 'directory name', data=component.encode()+b'\0')
                env.put(child, name)
                # Directory hashes use length modulo19, just as resource hashes.
                map_insert(env,directory,0x3c,len(component)%5,child,buckets=5)
                dirs[key]=child
            directory=dirs[key]
        kind = env.object(0x2c,'resource type',fill=0)
        env.put(kind,typeword)
        map_insert(env,directory,0x44,typeword%9,kind,buckets=9)
        resource=env.object(0x2c,'resource '+path,fill=0)
        leaf=pieces[-1]
        env.put(resource,env.object(len(leaf)+1,'resource name',data=leaf.encode()+b'\0'))
        env.put(resource+8,kind)
        env.put(resource+0x14,0 if empty else len(payload))
        archive=env.object(0x24,'archive',fill=0)
        if not empty:
            data=env.object(len(payload),'resident resource bytes',data=payload)
            env.put(archive+0x20,data)
            if cached_bytes:
                env.put(resource+0x18,data)
        env.put(resource+0x24,archive,0)
        map_insert(env,kind,0x24,len(leaf)%19,resource)
    manager=env.object(0x28,'resource manager',fill=0)
    env.put(manager+0x24,root)
    return manager,root


def pcx(width=192,height=3):
    data=bytearray(128)
    data[0:4]=bytes((10,5,1,8))
    struct.pack_into('<4H',data,4,0,0,width-1,height-1)
    data[65]=1
    struct.pack_into('<H',data,66,width)
    return bytes(data)+bytes((i*7+11)%190 for i in range(width*height))+bytes(768)


def coordinator(function=0x48f500, cached=True, palette=False, delay=True, failure='', **options):
    def setup(env):
        physical(env)
        width,height=192,3
        obj=env.object(0x44,'menu state',fill=0)
        app=env.object(0x90,'application',fill=0)
        methods=env.object(16,'application vtable',fill=0)
        env.put(app,methods)
        def application_mode(e,c):
            if failure=='fader':
                e.put(e.get(obj+0x3c)+0x18,width+1)
            return 1
        env.put(methods+12,env.stub('application color mode','thiscall',0,application_mode))
        env.put(app+0x58,palette_manager(env))
        pal=env.object(12,'cached shading palette',fill=0)
        env.put(pal+8,env.object(16384,'shade lookup',data=bytes(i%251 for i in range(16384))))
        env.put(app+0x8c,pal if palette else 0)
        if not palette:
            env.put(app+0x58,0)
        services=env.object(0x2c,'scene services',fill=0)
        chain=env.object(0x18,'platform controller',fill=0)
        primary_node=env.object(0x30,'primary image',fill=0)
        back_node=env.object(0x30,'back image',fill=0)
        primary,pixels=surface(env,width,height)
        back,_=surface(env,width,height,salt=79)
        env.put(primary_node+0x2c,primary)
        env.put(primary_node+0x18,8)
        env.put(back_node+0x2c,back)
        env.put(chain+0x10,primary_node,back_node)
        graphics=env.object(0x880,'surface manager',fill=0)
        env.put(graphics+0x474,8)
        env.put(graphics+0x3d0,4)
        env.put(graphics+0x3ec,4)
        dd=env.object(4,'DirectDraw',fill=0)
        dd_methods=env.object(28,'DirectDraw methods',fill=0)
        env.put(dd,dd_methods)
        env.put(graphics,dd)
        # Physical callback identities must be frozen with setup, not registered
        # while either side executes. Surface metadata belongs to each COM object.
        def describe(e,c):
            iface,dest=c.arguments
            e.put(dest,108,0x1007,e.get(iface+8),e.get(iface+4),e.get(iface+12))
            e.put(dest+0x24,e.get(iface+16))
            e.put(dest+0x48,32,0x20,0,8)
            return 0
        def lock_created(e,c):
            iface=c.arguments[0]
            e.put(c.arguments[2]+0x24,e.get(iface+16))
            return 0
        describe_method=env.stub('DirectDraw.GetSurfaceDesc','stdcall',2,describe)
        lock_method=env.stub('DirectDraw.Lock','stdcall',5,lock_created)
        unlock_method=env.stub('DirectDraw.Unlock','stdcall',2,returns(0))
        release_method=env.stub('DirectDraw.Release','stdcall',1,returns(0))
        blt_method=env.stub('DirectDraw.Blt','stdcall',6,returns(0x80004005 if failure=='copy' else 0))
        palette_get_method=env.stub('Palette.GetEntries','stdcall',5,lambda e,c:(e.write(c.arguments[4],bytes((i*7+3)&255 for i in range(c.arguments[3]*4))) or 0))
        palette_set_method=env.stub('Palette.SetEntries','stdcall',5,returns(0))
        def create(e,c):
            if failure=='surface-create':return 0x80004005
            descriptor,out=c.arguments[1:3]
            w,h=e.get(descriptor+12),e.get(descriptor+8)
            iface=e.object(24,'new DirectDraw surface',fill=0)
            vtable=e.object(0x84,'new DirectDraw methods',fill=0)
            raw=e.object(max(1,w*h+1024),'new pixels',fill=0x3d)
            e.put(iface,vtable,w,h,w,raw)
            e.put(vtable+0x58,describe_method)
            e.put(vtable+0x64,lock_method)
            e.put(vtable+0x80,unlock_method)
            e.put(vtable+8,release_method)
            e.put(vtable+0x14,blt_method)
            e.put(out,iface)
            return 0
        def create_palette(e,c):
            if failure=='screen':return 0x80004005
            palcom=e.object(4,'DirectDraw palette',fill=0)
            palvt=e.object(28,'palette methods',fill=0)
            e.put(palcom,palvt)
            e.put(palvt+0x10,palette_get_method)
            e.put(palvt+0x18,palette_set_method)
            e.put(c.arguments[3],palcom)
            return 0
        env.put(dd_methods+0x14,env.stub('DirectDraw.CreatePalette','stdcall',5,create_palette))
        env.put(dd_methods+0x18,env.stub('DirectDraw.CreateSurface','stdcall',4,create))
        sound=env.object(0x34,'sound manager',fill=0)
        env.put(sound+0x30,0 if options.get('sound') else 1)
        buckets=env.object(17*4,'sound map buckets',fill=0)
        env.put(sound+0x14,buckets,17)
        if options.get('sound') in ('found-muted','found-play','physical-play'):
            node=env.object(16,'sound map association',fill=0)
            record=env.object(20,'sound record',fill=0)
            actual=env.object(0x38,'sound',fill=0)
            sound_device=env.object(0x7c,'disabled sound device',fill=0)
            env.put(actual+0x10,sound_device)
            if options.get('sound')=='physical-play':
                # One stopped reusable voice follows the original's intrusive
                # list. Setters, status, and play use physical COM callbacks.
                env.put(sound_device+0x78,1)
                voice=env.object(0x38,'stopped sound voice',fill=0)
                iface=env.object(4,'DirectSound buffer',fill=0)
                methods=env.object(0x48,'DirectSound buffer methods',fill=0)
                log=env.object(16,'sound play observations',fill=0x87)
                env.put(iface,methods)
                env.put(voice+0xc,iface,sound_device,1,22050)
                env.put(voice+0x30,1)
                env.put(actual+0x18,22050,0,0)
                env.put(actual+0x30,voice+4,voice+4)
                def status(e,c):
                    e.put(c.arguments[1],0)
                    return 0
                def play(e,c):
                    e.put(log,*c.arguments)
                    return 0
                env.put(methods+0x24,env.stub('DirectSound.GetStatus','stdcall',2,status))
                env.put(methods+0x30,env.stub('DirectSound.Play','stdcall',4,play))
                for offset,name in ((0x3c,'Volume'),(0x40,'Pan'),(0x44,'Frequency')):
                    env.put(methods+offset,env.stub('DirectSound.Set'+name,'stdcall',2,returns(0)))
                env.put(0x532c10,0)
            env.put(record+0x10,actual)
            keyname=options.get('sound_key','ROLLUP')
            key=env.object(len(keyname)+1,'sound key',data=keyname.encode()+b'\0')
            hashed=0
            for char in keyname:hashed=(hashed*33+ord(char))&0xffffffff
            env.put(node,0,hashed%17,key,record)
            env.put(buckets+(hashed%17)*4,node)
        fader_manager=env.object(40,'fader manager',fill=0)
        env.put(services+4,chain)
        env.put(services+0x1c,graphics)
        env.put(services+0x28,sound)
        env.put(obj+4,app)
        env.put(obj+0xc,services,fader_manager)
        paper,_=surface(env,width+(1 if failure=='width' else 0),height+(1 if failure=='height' else 0),salt=139)
        env.put(obj+0x40,paper if cached else 0)
        entries=[] if failure=='resource' else [('STATES_ROLLER_SCREENS_PAPER',0x504358,pcx(width,height),failure=='bytes')]
        if function==0x48f740 and failure!='screen-resource':
            entries.append(('SCREENS_TEST',0x504358,pcx(width,height),failure=='screen-bytes'))
        manager,root=namespace(env,entries,cached_bytes=options.get('cached_resource_bytes',False))
        env.put(obj+8,manager)
        env.put(obj+0x20,root)
        if function==0x48f740:
            image_manager=env.object(0x68,'image manager',fill=0)
            env.put(image_manager,0x513b28)
            env.put(image_manager+0xc,services)
            env.put(image_manager+0x14,env.object(17*4,'image hash buckets',fill=0),17)
            env.put(image_manager+0x28,4)
            env.put(services+0x18,image_manager)
            if options.get('screen_cached',True):
                screen=env.object(20,'cached screen image',fill=0)
                env.put(screen,0x513d78)
                env.put(screen+0xc,services)
                descriptor=env.object(56,'screen palette descriptor',fill=0)
                palette_out=env.object(4,'palette output',fill=0)
                create_palette(env,type('Call',(),{'arguments':(dd,0,0,palette_out,0)})())
                env.put(descriptor+4,env.get(palette_out))
                env.put(descriptor+0xc,env.object(1024,'palette colors',fill=0x35),env.object(1024,'saved colors',fill=0x52))
                env.put(screen+0x10,descriptor)
                env.put(obj+0x2c,screen)
        env.put(0x537238,int(delay))
        env.put(0x532c0c,int(options.get('sound') in ('found-play','physical-play')))
        return {'this':obj,'screen':env.object(5,'screen name',data=b'TEST\0')}
    return setup
