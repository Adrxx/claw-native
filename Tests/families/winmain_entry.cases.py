"""Blind original WinMain physical prefixes; wider policies remain blocked.

No source callee, game global, fixed vtable or constructor is replaced.
"""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.fixtures import halt

ROOT = 0x49F8D0
RETURN_PC = 0x4A4802  # original CALL at 4a47fd
IMPORTS = (0x5469F4, 0x5469F8, 0x546C88, 0x546CF8, 0x546D44,
           0x546D48, 0x546D50, 0x546DA4, 0x546DA8, 0x546DAC)


def setup_prefix(registers, filename_result=None):
    def setup(env):
        for address in IMPORTS:
            env.override(address, halt())
        command = env.object(32, 'command tail', data=b'LOBBYLAUNCH /test\0')
        stack = 0x2007000
        # Retain arbitrary untouched stack bytes: only actual source/API writes
        # may define locals. The harness materializes ordinary incoming words.
        context = NativeSourceContext(72, 1, 0x7ff, 0x7ff,
                                      *registers, stack, ROOT, 2,
                                      0xffffffff, 0, 0, 0)
        if filename_result is not None:
            def filename(env, call):
                # Failure publishes an empty, bounded filename; success models
                # the complete executable pathname and excludes the NUL count.
                data = b'' if filename_result == 0 else b'C:\\CLAW\\CLAW.EXE'
                env.write(call.arguments[1], data + b'\0')
                return filename_result
            env.override(0x5469F4, filename)
        return {'source': context, 'command': command}
    return setup


def cases(random_source):
    for index in range(4):
        registers = tuple(random_source.getrandbits(32) for _ in range(7))
        for label, result in (('module filename physical stop', None),
                              ('filename failure reaches version physical stop', 0)):
            yield Case(f'{label} witnesses {index}', ROOT,
                       setup_prefix(registers, result),
                       arguments=(0x400000 + index * 0x10000, 0x10203040,
                                  lambda t: t['command'], 0x80000000 + index),
                       source_context=lambda t: t['source'],
                       source_return_pc=RETURN_PC, expect='halt')


def platform_profile(registers, duplicate=False, window=0, iconic=0,
                     command=b'LOBBYLAUNCH', cd=False, owner_fail=False):
    def setup(env):
        t = setup_prefix(registers)(env)
        for address in (5532148, 5532808, 5532920, 5532996, 5533008, 5532152, 5533000, 5533092, 5533096, 5533100, 5532156, 5532184, 5532160, 5532164, 5532324, 5532332, 5532316, 5532012, 5531940, 5532024, 5532028, 5532124, 5532128, 5532140, 5532136, 5532200, 5532204, 5532208, 5532476, 5531700, 5531692, 5531684, 5531696, 5532900, 5532740, 5532880, 5533084, 5533176, 5533160, 5533172, 5532972, 5532952, 5532980, 5532832, 5532836, 5532284, 5532292, 5532304, 5532096, 5532428, 5532344, 5532328, 5532288, 5532444, 5532296, 5532300, 5532100, 5532104, 5532000, 5532004, 5532048, 5531988, 5531992, 5532020, 5532180, 5532348, 5532404, 5532408, 5532412, 5532844, 5532840, 5532848, 5532548, 5533080, 5532628, 5532544, 5532512, 5531836, 5532556):
            env.override(address, halt())
        env.write(t['command'], command + b'\0')
        path = b'C:\\CLAW\\CLAW.EXE'
        def filename(env, call):
            env.write(call.arguments[1], path + b'\0')
            return len(path)
        env.override(0x5469F4, filename)
        env.override(0x5469FC, lambda e,c: 0x71000000 if duplicate else 0)
        env.override(0x546C88, lambda e,c: window)
        env.override(0x546CF8, lambda e,c: iconic)
        env.override(0x546D44, lambda e,c: 0)
        env.override(0x546D50, lambda e,c: 1)
        # Snapshot records use the pinned original layouts, with independent
        # cursor state in each live physical snapshot object.
        def snapshot(e,c):
            flags,pid = c.arguments
            return e.object(16, 'Toolhelp snapshot', words=[flags,pid,0xffffffff,0])
        def enumerate_record(first, module):
            def effect(e,c):
                handle,record = c.arguments
                index = 0 if first else (e.get(handle+8)+1)&0xffffffff
                e.put(handle+8,index)
                count = 1 if module else 2
                if index >= count:
                    return 0
                size = 0x224 if module else 0x128
                data = bytearray(size)
                import struct
                struct.pack_into('<I',data,0,size)
                if module:
                    pid=e.get(handle+4)
                    struct.pack_into('<II',data,4,7,pid)
                    data[0x20:0x29]=b'CLAW.EXE\0'
                    data[0x120:0x120+len(path)+1]=path+b'\0'
                else:
                    struct.pack_into('<I',data,8,100+index)
                    struct.pack_into('<I',data,0x10,7)
                e.write(record,bytes(data))
                return 1
            return effect
        procedures={
            b'CreateToolhelp32Snapshot':env.stub('CreateToolhelp32Snapshot','stdcall',2,snapshot),
            b'Process32First':env.stub('Process32First','stdcall',2,enumerate_record(True,False)),
            b'Process32Next':env.stub('Process32Next','stdcall',2,enumerate_record(False,False)),
            b'Module32First':env.stub('Module32First','stdcall',2,enumerate_record(True,True)),
            b'Module32Next':env.stub('Module32Next','stdcall',2,enumerate_record(False,True))}
        def resolve(e,c):
            if c.arguments[0] != 0x71000000:
                return 0
            return procedures.get(e.cstr(c.arguments[1]),0)
        env.override(0x546A18,resolve)
        def close(e,c):
            e.release(c.arguments[0]); return 1
        env.override(0x546A04,close)
        # Successful version resource is owned by its real allocated block;
        # the original sscanf writes the image version globals itself.
        env.override(0x546DA4,lambda e,c:64)
        def version(e,c):
            e.write(c.arguments[3], b'12, 34, 56, 78\0'+bytes(49)); return 1
        env.override(0x546DA8,version)
        def query(e,c):
            e.put(c.arguments[2],c.arguments[0]); e.put(c.arguments[3],15); return 1
        env.override(0x546DAC,query)
        # Model single-thread critical sections at their source-provided
        # addresses, including the physical recursion/owner words.
        def initialize(e,c):
            debug=e.object(32,'critical section debug record')
            e.put(c.arguments[0],debug,0xffffffff,0,0,0,0); return 0
        def enter(e,c):
            address=c.arguments[0]
            e.put(address+4,(e.get(address+4)+1)&0xffffffff,e.get(address+8)+1,0x1234)
            return 0
        def leave(e,c):
            address=c.arguments[0]; depth=(e.get(address+8)-1)&0xffffffff
            e.put(address+4,(e.get(address+4)-1)&0xffffffff,depth,0x1234 if depth else 0)
            return 0
        env.override(0x546AA4,initialize)
        env.override(0x546AAC,enter)
        env.override(0x546A9C,leave)
        def cwd(e,c):
            e.write(c.arguments[1],b'C:\\CLAW\0'); return 7
        env.override(0x546A28,cwd)
        env.override(0x546A2C,lambda e,c:5 if cd and e.cstr(c.arguments[0]).upper().startswith(b'D:') else (3 if e.cstr(c.arguments[0]).upper().startswith(b'C:') else 1))
        def exists(e,c):
            # OF_EXIST: an existent disc file closes its transient file handle.
            path=e.cstr(c.arguments[0])
            record=bytearray(136); record[0]=136
            record[8:8+len(path)+1]=path+b'\0'
            e.write(c.arguments[1],bytes(record))
            return 0 if cd and path.upper().startswith(b'D:') else 0xffffffff
        env.override(0x546A30,exists)
        env.override(0x546D48,lambda e,c:2)  # cancel retry when no disc exists
        if owner_fail:
            from clawparity.fixtures import allocate
            default_allocate=allocate()
            def allocation(e,c):
                return 0 if c.arguments[0]==0x254 else default_allocate(e,c)
            env.override(0x4F63EC,allocation)
        return t
    return setup


prefix_cases = cases

def cases(random_source):
    yield from prefix_cases(random_source)
    for window, iconic,command in ((0,0,b''),(0x73001000,0,b''),
                                  (0x73001000,1,b'LOBBYLAUNCH'),
                                  (0x73001000,0,b'xxLOBBYLAUNCHyy'),
                                  (0x73001000,1,b'lobbylaunch')):
        registers=tuple(random_source.getrandbits(32) for _ in range(7))
        yield Case(f'duplicate instance window{window:x} iconic{iconic} command{command!r}',ROOT,
                   platform_profile(registers,True,window,iconic,command),
                   arguments=(0x400000,0,lambda t:t['command'],1),
                   source_context=lambda t:t['source'],source_return_pc=RETURN_PC)
    for cd in (False,True):
        yield Case(f'normal launch original CD {cd}',ROOT,
                   platform_profile(registers,cd=cd),
                   arguments=(0x400000,0,lambda t:t['command'],1),
                   source_context=lambda t:t['source'],source_return_pc=RETURN_PC,
                   expect='halt' if cd else 'return')


def configured_profile(registers, registry='failure', owner_fail=False):
    base = platform_profile(registers, cd=True, owner_fail=owner_fail)
    def setup(env):
        t=base(env)
        if registry=='failure':
            env.override(0x546834,lambda e,c:5)  # ERROR_ACCESS_DENIED; outputs untouched
        else:
            def create(e,c):
                key=e.object(4,'registry key',words=[c.arguments[0]])
                e.put(c.arguments[7],key); e.put(c.arguments[8],2); return 0
            def query(e,c):
                e.put(c.arguments[3],4); e.put(c.arguments[4],1 if registry=='skip' else 0)
                e.put(c.arguments[5],4); return 0
            env.override(0x546834,create)
            env.override(0x54682C,query)
            def close(e,c):
                e.release(c.arguments[0]); return 0
            env.override(0x546830,close)
            env.override(0x546DF8,lambda e,c:0)  # physical machine has no joystick
            env.override(0x546CE4,lambda e,c:0x8000 if registry=='dialog' and c.arguments[0]==0x25 else 0)
            env.override(0x546C44,lambda e,c:1920 if c.arguments[0]==0 else 1080)
            env.override(0x546CD0,lambda e,c:(e.put(c.arguments[0],500,300) or 1))
        env.override(0x546C44,lambda e,c:1920 if c.arguments[0]==0 else 1080)
        env.override(0x546B60,lambda e,c:0x74000001)
        env.override(0x546CA0,lambda e,c:0x74000002)
        env.override(0x5468BC,lambda e,c:0x74000003)
        env.override(0x546B8C,lambda e,c:0)  # no menu resource
        env.override(0x546BD4,lambda e,c:0)  # genuine class registration failure
        return t
    return setup


platform_cases = cases

def cases(random_source):
    yield from platform_cases(random_source)
    for registry,owner_fail in (('failure',True),('failure',False),('skip',False),('dialog',False)):
        registers=tuple(random_source.getrandbits(32) for _ in range(7))
        yield Case(f'CD present registry {registry} owner allocation fails {owner_fail}',ROOT,
                   configured_profile(registers,registry,owner_fail),
                   arguments=(0x400000,0,lambda t:t['command'],1),
                   source_context=lambda t:t['source'],source_return_pc=RETURN_PC,
                   expect='halt' if registry=='dialog' else 'return')
