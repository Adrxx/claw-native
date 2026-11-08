"""Original-only inputs; prepared application states are unit inputs, not startup proof."""
from clawparity.cases import Case
from clawparity.fixtures import halt

ENTRY = 0x5028ec


def scenario(mode, app=False, hook_byte=1, previous=0, hook_result=0x71001234,
             thread_id=2, switch_at=0, name_setup=False, failure=None, callback=False,
             alias_offset=None, operand_change_at=0):
    def setup(env):
        state = env.object(0x1000, 'physical-services', fill=0)
        # Mode, TLS next index, thread, event cursor and handle cursor.
        env.put(state, previous, 1, thread_id, 0, 0)
        tls = env.object(0x4000, 'thread-tls', fill=0)
        local_sizes = env.object(0x1000, 'local-allocation-records', fill=0)
        handles = env.object(0x400, 'global-handles', fill=0)
        observations = env.object(0x4000, 'physical-observations', fill=0)
        module = env.object(0x1074, 'prepared-module', fill=0)
        env.put(module + 0x14, 0xD3C2B100 | hook_byte)
        app_object = (0x02008000 + alias_offset - 0x68 if alias_offset is not None else
                      env.object(0xc0, 'prepared-application', data=bytes((i * 37 + 11) & 255 for i in range(0xc0))))
        name_pointers = []
        command = env.object(64, 'command-line', data=b'-level 1 -unit-state\x00')
        for offset, text in ((0x78,b'Application title\x00'),(0x88,b'Executable\x00'),(0x8c,b'Custom.HLP\x00'),(0x90,b'Custom.INI\x00')):
            pointer = env.object(40, 'application-string', data=text)
            name_pointers.append((offset,pointer))
            if alias_offset is None: env.put(app_object + offset, 0 if name_setup else pointer)
        env.put(module + 4, app_object if app else 0)
        second = env.object(0x1074, 'alternate-module', fill=0)
        env.put(second + 0x14, 0x88776680)
        env.put(second + 4, app_object if app else 0)
        if mode == 'prepared':
            env.put(0x53eca0, module)
        def log(e, call, code):
            cursor = e.get(state + 12)
            slot = observations + cursor * 64
            e.put(slot, code, call.receiver, len(call.arguments), *call.arguments)
            e.put(slot + 32, e.get(module + 8), e.get(module + 12), e.get(module + 0x14),
                  e.get(app_object + 0x68), e.get(app_object + 0x6c),
                  e.get(app_object + 0x70), e.get(app_object + 0x74))
            e.put(state + 12, cursor + 1)
        def service(code, effect):
            def wrapped(e, call):
                log(e, call, code)
                if failure == code:
                    if code == 0x546aa8: return 0
                    return halt()(e, call)
                return effect(e, call)
            env.override(code, wrapped)
        def tls_alloc(e,c):
            n=e.get(state+4); e.put(state+4,n+1); return n
        def tls_get(e,c):
            n=e.calls_so_far(0x546a7c)
            if operand_change_at and n == operand_change_at:
                e.put(0x02008004,0x9A102030,0xB1425364,0xC1758697,0xD1A8B9CA)
                e.put(observations+0x3F00,n,*[e.get(0x02008004+i*4) for i in range(4)])
            if switch_at and n == switch_at:
                e.put(0x53eca0, second)
            return e.get(tls+(e.get(state+8)%16)*0x400+c.arguments[0]*4)
        def tls_set(e,c):
            e.put(tls+(e.get(state+8)%16)*0x400+c.arguments[0]*4,c.arguments[1]); return 1
        service(0x546a90,tls_alloc)
        service(0x546a7c,tls_get)
        service(0x546a84,tls_set)
        def local_alloc(e,c):
            flags,size=c.arguments
            pointer=e.object(size,'LocalAlloc',fill=0 if flags & 0x40 else 0xA5)
            count=e.get(state+20); e.put(local_sizes+count*8,pointer,size); e.put(state+20,count+1)
            return pointer
        service(0x546aa8,local_alloc)
        def local_resize(e,c):
            old,size,flags=c.arguments
            new=e.object(size,'LocalReAlloc',fill=0xA5)
            oldsize=0
            for i in range(e.get(state+20)):
                if e.get(local_sizes+i*8)==old: oldsize=e.get(local_sizes+i*8+4)
            e.write(new,e.read(old,min(size,oldsize)))
            count=e.get(state+20); e.put(local_sizes+count*8,new,size); e.put(state+20,count+1)
            e.release(old)
            return new
        service(0x546a80,local_resize)
        def global_alloc(e,c):
            flags,size=c.arguments
            data=e.object(size,'global-data',fill=0)
            handle=e.object(16,'global-handle',words=[data,size,1,flags])
            count=e.get(state+16); e.put(handles+count*4,handle); e.put(state+16,count+1)
            return handle if flags & 2 else data
        service(0x546b1c,global_alloc)
        def global_handle(e,c):
            for i in range(e.get(state+16)):
                handle=e.get(handles+i*4)
                if e.get(handle)==c.arguments[0]: return handle
            return 0
        service(0x546a8c,global_handle)
        def global_unlock(e,c):
            h=c.arguments[0]; e.put(h+8,max(0,e.get(h+8)-1)); return 0
        service(0x5469c8,global_unlock)
        def global_resize(e,c):
            h,size,flags=c.arguments; old=e.get(h); oldsize=e.get(h+4)
            new=e.object(size,'global-resized',fill=0); e.write(new,e.read(old,min(size,oldsize)))
            e.put(h,new,size); e.release(old); return h
        service(0x546a88,global_resize)
        def global_lock(e,c):
            h=c.arguments[0]; e.put(h+8,e.get(h+8)+1); return e.get(h)
        service(0x5469c4,global_lock)
        def initialize(e,c): e.put(c.arguments[0],0,0,0,0,0,0); return 0
        def enter(e,c):
            a=c.arguments[0]; e.put(a+4,e.get(a+4)+1,e.get(state+8)); return 0
        def leave(e,c):
            a=c.arguments[0]; depth=e.get(a+4)-1; e.put(a+4,depth,e.get(state+8) if depth else 0); return 0
        service(0x546aa4,initialize); service(0x546aac,enter); service(0x546a9c,leave)
        service(0x546abc,lambda e,c:0x00000A04)
        def error_mode(e,c):
            old=e.get(state); e.put(state,c.arguments[0])
            if alias_offset is not None and e.calls_so_far(0x546b18)==2:
                # Above-root stack fields survive all nested original prologues.
                # Install only names, leaving return, saved ESI and input words intact.
                for offset,pointer in name_pointers: e.put(app_object+offset,pointer)
            return old
        service(0x546b18,error_mode)
        path=b'C:\\Games.with.dot\\Captain.Claw.EXE\x00'
        def filename(e,c):
            e.write(c.arguments[1],path[:c.arguments[2]]); return len(path)-1
        service(0x5469f4,filename)
        def copy(e,c):
            dst,src=c.arguments[:2]; data=e.cstr(src)
            if isinstance(data,str): data=data.encode()
            if len(c.arguments)==3: data=data[:max(0,c.arguments[2]-1)]
            e.write(dst,data+b'\x00'); return dst
        service(0x5469cc,copy); service(0x546b10,copy)
        def concat(e,c):
            dst,src=c.arguments; a=e.cstr(dst); b=e.cstr(src)
            if isinstance(a,str): a=a.encode()
            if isinstance(b,str): b=b.encode()
            e.write(dst,a+b+b'\x00'); return dst
        service(0x546b14,concat)
        service(0x546d28,lambda e,c:0)
        service(0x5469c0,lambda e,c:e.get(state+8))
        service(0x546bfc,lambda e,c:hook_result)
        service(0x546958,halt())
        if callback:
            singleton=env.object(0x30,'prepared-hook-singleton',fill=0)
            def observe(e,c):
                log(e,c,0xCB001); e.put(module+0x14,0xCCBBAA01); return 0xBAD01234
            env.put(singleton+0x14,env.stub('hook singleton callback','stdcall',1,observe))
            env.put(0x540b30,singleton)
        if mode in ('warm','second-thread'):
            # Real original invocation builds source TLS/factory state before the tested call.
            env.run_original(ENTRY,0,(0x66112233,0,command,1),check_objects=True)
            if mode == 'second-thread': env.put(state+8,thread_id+1)
        return {'command':command,'module':module,'app':app_object}
    return setup


def cases(random_source):
    for previous in (0,0x8000,0xFFFF7FFE,0x12345678,random_source.getrandbits(32)):
        yield Case(f'cold source module previous mode {previous:#x}',ENTRY,
                   scenario('cold',previous=previous),arguments=(0x77112233,0,0,1))
    for mode in ('warm','second-thread'):
        yield Case(f'{mode} after genuine original initialization',ENTRY,
                   scenario(mode,previous=0xCDEF2345),
                   arguments=(0x77001234,0x76543210,lambda t:t['command'],7))
    for app in (False,True):
        for byte in (0,1,0x80,0xFF):
            for result in ((0,0x7123ABCD) if byte==0 else (0x7123ABCD,)):
                values=[random_source.getrandbits(32) for _ in range(3)]
                yield Case(f'prepared app={app} flag={byte:#x} hook={result:#x}',ENTRY,
                           scenario('prepared',app=app,hook_byte=byte,previous=values[0],hook_result=result),
                           arguments=(values[1],values[2],lambda t:t['command'],0xFFFFFFFF))
    for count in (1,2,3,4,5):
        yield Case(f'physical lookup changes current module at lookup {count}',ENTRY,
                   scenario('prepared',app=True,hook_byte=0,switch_at=count),
                   arguments=(0x78563412,0x10203040,lambda t:t['command'],5))
    yield Case('prepared hook callback sees published module',ENTRY,
               scenario('prepared',app=True,hook_byte=0,callback=True),
               arguments=(0x77000001,0x55667788,lambda t:t['command'],5))
    yield Case('original application name setup fallback and extensions',ENTRY,
               scenario('prepared',app=True,hook_byte=0,name_setup=True),
               arguments=(0x77000002,0,lambda t:t['command'],3))
    for service in (0x546b18,0x546aa4,0x546bfc,0x546aa8):
        yield Case(f'honest physical service halt {service:#x}',ENTRY,
                   scenario('cold' if service==0x546aa4 else 'prepared',hook_byte=0,failure=service),
                   arguments=(1,2,3,4),expect='halt')

    # app+68 begins above the root return word. A shifted destination can
    # overwrite later incoming operands before the coordinator reloads them.
    for offset in (4,8,12,16):
        yield Case(f'valid application aliases incoming frame at +{offset}',ENTRY,
                   scenario('prepared',app=True,alias_offset=offset),
                   arguments=(0x11223344,0x55667788,0x99AABBCC,0xDDEEFF00))
    # With an app, lookup 3 belongs to unchanged name setup; lookup 4
    # is the coordinator's final lookup.
    for lookup in (1,2,3,4):
        yield Case(f'physical TLS lookup {lookup} changes incoming operand words',ENTRY,
                   scenario('prepared',app=True,operand_change_at=lookup),
                   arguments=(0x11223344,0x55667788,0x99AABBCC,0xDDEEFF00))
