"""Blind original-only static wrapper cases; physical services own guest memory."""
import json
import struct
from pathlib import Path
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt, HarnessError
from clawparity.program import claw
from clawparity.env import HEAP_BASE
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / 'Tests/families/static_initializer_wrappers.json').read_text())
PROGRAM = claw()  # validates the actual original EXE hash before decoding any bytes
IMAGE = bytearray(PROGRAM.size)
for section in PROGRAM.sections:
    IMAGE[section.address-PROGRAM.base:section.address-PROGRAM.base+len(section.data)] = section.data
ROOTS = [int(f['address'], 0) for f in SPEC['owned']]
RETURN = 0x4a5896

def edge(root):
    site = root + (5 if IMAGE[root-PROGRAM.base] == 0xe8 else 0)
    target = site + 5 + struct.unpack_from('<i', IMAGE, site-PROGRAM.base+1)[0]
    return site, target

def setup_for(root, words, profile=0, registrations=0, failure=None, versions=(0x00000004,)):
    def setup(env):
        ledger = env.object(8192, 'physical-owner-ledger', fill=0)
        journal = env.object(16384, 'physical-service-observations', fill=0)
        tls = env.object(1024, 'physical-TLS', fill=0)
        def log(e, service, args, result, call=None):
            n = e.get(journal)
            if n >= 200: raise HarnessError('observation journal exhausted')
            context=call.source_context if call else None
            cpu=tuple(getattr(context,k) for k in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead')) if context else (0,)*11
            e.put(journal+4+n*80, service, len(args), *args, result,call.receiver if call else 0,*cpu)
            e.put(journal,n+1)
            return result
        def find(e,p):
            for i in range(e.get(ledger)):
                a=ledger+4+i*16
                if e.get(a)==p and e.get(a+12): return a
            raise HarnessError(f'unsupported physical allocation base {p:#x}')
        def alloc(e,n):
            if n>32768: raise Halt()
            cap=max(16,(n+15)&~15)
            p=e.object(cap,'physical-owned-allocation',fill=0xa5)
            i=e.get(ledger); e.put(ledger+4+i*16,p,n,cap,1); e.put(ledger,i+1)
            return p
        def retire(e,p):
            if p: a=find(e,p); e.put(a+12,0); e.release(p)
        def service(address,name):
            def effect(e,c):
                a=c.arguments
                if name in ('malloc','operator new'):
                    r=0 if failure=='alloc' and e.side!='setup' else alloc(e,a[0])
                elif name in ('free','operator delete'): retire(e,a[0]); r=0
                elif address==0x4a6560: r=e.get(find(e,a[0])+8)
                elif address==0x4a9070:
                    p,n=a
                    if not p:r=alloc(e,n)
                    elif not n:retire(e,p);r=0
                    elif failure=='realloc' and e.side!='setup':r=0
                    else:
                        old=find(e,p); cap=e.get(old+8)
                        if n<=cap: e.put(old+4,n);r=p
                        else:
                            prefix=e.read(p,min(cap,n));r=alloc(e,n);e.write(r,prefix);retire(e,p)
                elif name=='RaiseException': log(e,address,a,0,c); raise Halt()
                elif name=='GetVersion':r=versions[min(e.calls_so_far(address)-1,len(versions)-1)]
                elif name=='TlsAlloc':r=0xffffffff if failure=='tls' and e.side!='setup' else 7
                elif name=='TlsGetValue':r=e.get(tls+4*a[0])
                elif name=='TlsSetValue':e.put(tls+4*a[0],a[1]);r=1
                elif name in ('LocalAlloc','GlobalAlloc'):
                    r=alloc(e,a[1])
                    if a[0]&0x40:e.write(r,bytes(e.get(find(e,r)+8)))
                elif name in ('LocalReAlloc','GlobalReAlloc'):
                    p,n,flags=a;old=find(e,p);cap=e.get(old+8)
                    prefix=e.read(p,min(cap,n));r=alloc(e,n);e.write(r,prefix)
                    if flags&0x40 and n>cap:e.write(r+cap,bytes(n-cap))
                    retire(e,p)
                elif name in ('GlobalLock','GlobalHandle'):r=a[0]
                elif name=='GlobalUnlock':r=0
                elif name=='InitializeCriticalSection':e.write(a[0],bytes(24));r=0
                elif name=='EnterCriticalSection':e.put(a[0]+4,e.get(a[0]+4)+1);r=0
                elif name=='LeaveCriticalSection':e.put(a[0]+4,e.get(a[0]+4)-1);r=0
                elif name=='lstrlenA':r=len(e.cstr(a[0],8192))
                elif name=='InterlockedDecrement':r=(e.get(a[0])-1)&0xffffffff;e.put(a[0],r)
                elif name=='GetCursorPos':e.put(a[0],17,29);r=1
                elif name=='RegisterWindowMessageA':r=0xc123+profile
                elif name=='GetCurrentThread':r=0xfffffffe
                elif name=='GetCurrentThreadId':r=0x1234+profile
                elif name=='GetProcessVersion':r=0x40000
                elif name=='LoadCursorA':r=0x123000
                elif name=='GetSysColorBrush':r=0x124000+a[0]
                elif name=='GetSysColor':r=(a[0]*0x10307)&0xffffff
                elif name=='GetSystemMetrics':r=640 if a[0]==0 else 480
                elif name=='GetDC':r=0x125000
                elif name=='ReleaseDC':r=1
                elif name=='GetDeviceCaps':r={12:24,14:1,88:96,90:96}.get(a[1],640)
                elif name=='LoadStringA':r=0;e.write(a[2],b'\0')
                elif name=='GetModuleFileNameA':data=b'C:\\CLAW\\CLAW.EXE';r=min(len(data),a[2]-1);e.write(a[1],data[:r]+b'\0')
                elif name in ('LoadLibraryA','GetProcAddress'):r=0
                elif name=='GetStdHandle':r=0x126000
                elif name=='WriteFile':e.put(a[3],a[2]);r=1
                else:log(e,address,a,0,c);raise Halt()
                return log(e,address,a,r,c)
            return effect
        for address,decl in SPEC['callees'].items():
            if decl['kind']=='fixture':
                n=decl['name'].split('!')[-1]
                env.override(int(address,0),service(int(address,0),n))
        # Run genuine CRT setup before freezing; no registry vector or lock cache is seeded.
        env.machine.write(HEAP_BASE,env.read(HEAP_BASE,env.heap_bytes))
        env.machine.write(PROGRAM.data_start,env.read(PROGRAM.data_start,PROGRAM.size-(PROGRAM.data_start-PROGRAM.base)))
        env.machine.write(STACK_BASE,env.read(STACK_BASE,STACK_SIZE))
        env.backend='machine';env.side='setup';env._source_graph=True
        for entry in (0x4a7b90,0x4a3610):
            result=env.machine.call(entry)
            if not result.completed: raise HarnessError('original CRT initialization did not return')
        for i in range(registrations):
            result=env.machine.call(0x4a35f0,arguments=(ROOTS[i%len(ROOTS)],))
            if not result.completed:raise HarnessError('original registration setup did not return')
        heap=env.read(HEAP_BASE,env.heap_bytes)
        image=env.read(PROGRAM.data_start,PROGRAM.size-(PROGRAM.data_start-PROGRAM.base))
        stack=env.read(STACK_BASE,STACK_SIZE)
        env.backend='initial';env.side='setup';env._source_graph=False
        env.write(HEAP_BASE,heap);env.write(PROGRAM.data_start,image);env.write(STACK_BASE,stack)
        env.put(journal,0)
        site,target=edge(root);env.source_tail_edge(root,site,target)
        s=STACK_TOP-profile*0x100
        env.write(STACK_BASE,bytes([0x39+profile])*STACK_SIZE)
        env.put(s-4,0xe1e2e3e4,RETURN,words[1],words[4],words[5])
        fs=0xffffffff
        if profile%2:
            fs=s+0x100;env.put(fs,0xffffffff,0x4a5790,0xa1a2a3a4)
        context=NativeSourceContext(72,1,0x7ff,0x7ff,*words[:7],s,root,0x8d7 if profile%2 else 2,fs,0,0,0)
        return {'source':context}
    return setup

def cases(random_source):
    for root in ROOTS:
        for profile in range(2):
            words=tuple(random_source.getrandbits(32) for _ in range(7))
            yield Case(f'{root:08x} CPU profile {profile}',root,setup_for(root,words,profile),source_context=lambda t:t['source'],source_return_pc=RETURN)

    # Only original registration code fills/grows the owner, using genuine code identities.
    for root in (0x403540,0x425260,0x502d30,0x501fbd):
        for count in (1,31,32,35):
            words=tuple(random_source.getrandbits(32) for _ in range(7))
            yield Case(f'{root:08x} original registry occupancy {count}',root,setup_for(root,words,1,count),source_context=lambda t:t['source'],source_return_pc=RETURN)
        words=tuple(random_source.getrandbits(32) for _ in range(7))
        yield Case(f'{root:08x} registry realloc failure retains owner',root,setup_for(root,words,1,32,'realloc'),source_context=lambda t:t['source'],source_return_pc=RETURN)
    for versions in ((0x80000004,), (0x80000003,0x00000004,0x00000004,0x00000003), (0x00000004,0x80000004), (0x00000004,0x00000004,0x00000004)):
        words=tuple(random_source.getrandbits(32) for _ in range(7))
        yield Case(f'conditional GetVersion sequence {versions}',0x4ffd07,setup_for(0x4ffd07,words,1,versions=versions),source_context=lambda t:t['source'],source_return_pc=RETURN)
    words=tuple(random_source.getrandbits(32) for _ in range(7))
    yield Case('TLS exhaustion reaches genuine RaiseException physical stop',0x503813,setup_for(0x503813,words,1,failure='tls'),expect='halt',source_context=lambda t:t['source'],source_return_pc=RETURN)
    words=tuple(random_source.getrandbits(32) for _ in range(7))
    yield Case('CWinApp strdup allocation failure with original warm registry lock',0x4251e0,setup_for(0x4251e0,words,1,1,'alloc'),source_context=lambda t:t['source'],source_return_pc=RETURN)
