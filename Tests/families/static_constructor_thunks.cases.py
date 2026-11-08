"""Blind original-only constructor thunks; shared physical service model only.
No native results, internal constructor substitutions or fabricated tail calls.
"""
import json
import struct
from pathlib import Path
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt, HarnessError
from clawparity.program import claw
from clawparity.env import HEAP_BASE
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / 'Tests/families/static_constructor_thunks.json').read_text())
PROGRAM = claw()  # validates the actual original EXE hash before decoding any bytes
IMAGE = bytearray(PROGRAM.size)
for section in PROGRAM.sections:
    IMAGE[section.address-PROGRAM.base:section.address-PROGRAM.base+len(section.data)] = section.data
ROOTS = [int(f['address'], 0) for f in SPEC['owned']]
ROOT_METADATA = {5251015: (5251010, 'empty-ret'),
 5251704: (5251699, 'empty-ret'),
 5254298: (5254293, 'receiver-tail'),
 5253248: (5253243, 'empty-ret'),
 5254235: (5254230, 'empty-ret'),
 5257004: (5256999, 'empty-ret'),
 5257042: (5257037, 'empty-ret'),
 4207952: (4207941, 'two-argument-call'),
 4211392: (4211381, 'two-argument-call'),
 4220112: (4220101, 'two-argument-call'),
 4222624: (4222613, 'two-argument-call'),
 4224176: (4224165, 'two-argument-call'),
 4228400: (4228389, 'two-argument-call'),
 4231520: (4231509, 'two-argument-call'),
 4235248: (4235237, 'two-argument-call'),
 4241456: (4241445, 'one-argument-call'),
 4252208: (4252197, 'two-argument-call'),
 4254608: (4254597, 'two-argument-call'),
 4258528: (4258517, 'two-argument-call'),
 4262448: (4262437, 'two-argument-call'),
 4263904: (4263893, 'two-argument-call'),
 4265104: (4265093, 'two-argument-call'),
 4266304: (4266293, 'two-argument-call'),
 4267552: (4267541, 'two-argument-call'),
 4269072: (4269061, 'two-argument-call'),
 4270464: (4270453, 'two-argument-call'),
 4271664: (4271653, 'two-argument-call'),
 4273680: (4273669, 'two-argument-call'),
 4274992: (4274981, 'two-argument-call'),
 4276640: (4276629, 'two-argument-call'),
 4279696: (4279685, 'two-argument-call'),
 4281376: (4281365, 'two-argument-call'),
 4283056: (4283045, 'constant-publication'),
 4330192: (4330181, 'two-argument-call'),
 4346352: (4346341, 'one-argument-call'),
 4346480: (4346469, 'receiver-tail'),
 4346544: (4346533, 'receiver-tail'),
 4346608: (4346597, 'receiver-tail'),
 4346672: (4346661, 'receiver-tail'),
 4346736: (4346725, 'receiver-tail'),
 4346800: (4346789, 'receiver-tail'),
 4346864: (4346853, 'receiver-tail'),
 4346928: (4346917, 'receiver-tail'),
 4346992: (4346981, 'receiver-tail'),
 4396016: (4396005, 'two-argument-call'),
 4398496: (4398485, 'two-argument-call'),
 4400704: (4400693, 'two-argument-call'),
 4405888: (4405877, 'two-argument-call'),
 4409600: (4409589, 'two-argument-call'),
 4417696: (4417685, 'receiver-tail'),
 4417760: (4417749, 'receiver-tail'),
 4417824: (4417813, 'receiver-tail'),
 4420880: (4420869, 'one-argument-call'),
 4420960: (4420949, 'one-argument-call'),
 4423856: (4423845, 'two-argument-call'),
 4435152: (4435141, 'two-argument-call'),
 4443504: (4443493, 'two-argument-call'),
 4444992: (4444981, 'one-argument-call'),
 4445168: (4445157, 'two-argument-call'),
 4445248: (4445237, 'two-argument-call'),
 4461184: (4461173, 'two-argument-call'),
 4463792: (4463781, 'two-argument-call'),
 4469600: (4469589, 'two-argument-call'),
 4479648: (4479637, 'two-argument-call'),
 4482592: (4482581, 'two-argument-call'),
 4491264: (4491253, 'two-argument-call'),
 4492768: (4492757, 'two-argument-call'),
 4494656: (4494645, 'two-argument-call'),
 4496656: (4496645, 'two-argument-call'),
 4507632: (4507621, 'two-argument-call'),
 4539280: (4539269, 'two-argument-call'),
 4543920: (4543909, 'two-argument-call'),
 4545200: (4545189, 'two-argument-call'),
 4547216: (4547205, 'two-argument-call'),
 4549584: (4549573, 'two-argument-call'),
 4552432: (4552421, 'two-argument-call'),
 4555312: (4555301, 'two-argument-call'),
 4556624: (4556613, 'two-argument-call'),
 4563888: (4563877, 'two-argument-call'),
 4589248: (4589237, 'two-argument-call'),
 4598432: (4598421, 'two-argument-call'),
 4602608: (4602597, 'two-argument-call'),
 4608336: (4608325, 'two-argument-call'),
 4611424: (4611413, 'two-argument-call'),
 4622976: (4622965, 'two-argument-call'),
 4650576: (4650565, 'two-argument-call'),
 4669168: (4669157, 'two-argument-call'),
 4671376: (4671365, 'two-argument-call'),
 4673248: (4673237, 'receiver-tail'),
 4673328: (4673317, 'receiver-tail'),
 4673392: (4673381, 'receiver-tail'),
 4705568: (4705557, 'two-argument-call'),
 4709072: (4709061, 'two-argument-call'),
 4712592: (4712581, 'two-argument-call'),
 4716464: (4716453, 'two-argument-call'),
 4731184: (4731173, 'two-argument-call'),
 4735872: (4735861, 'two-argument-call'),
 4737152: (4737141, 'two-argument-call'),
 4741392: (4741381, 'two-argument-call'),
 4748112: (4748101, 'two-argument-call'),
 4753808: (4753797, 'two-argument-call'),
 4755616: (4755605, 'two-argument-call'),
 4757504: (4757493, 'two-argument-call'),
 4763760: (4763749, 'two-argument-call'),
 4772320: (4772309, 'receiver-tail'),
 4777328: (4777317, 'two-argument-call'),
 4793232: (4793221, 'two-argument-call'),
 4800384: (4800373, 'two-argument-call'),
 4813024: (4813013, 'two-argument-call'),
 4817264: (4817253, 'two-argument-call'),
 4845936: (4845925, 'two-argument-call'),
 4847712: (4847701, 'receiver-tail'),
 4847776: (4847765, 'receiver-tail'),
 4850144: (4850133, 'two-argument-call'),
 5241179: (5241174, 'empty-ret'),
 5252144: (5252139, 'two-argument-call'),
 5252200: (5252195, 'two-argument-call'),
 5210685: (5210680, 'one-argument-call'),
 5210747: (5210742, 'one-argument-call'),
 5210809: (5210804, 'one-argument-call'),
 5210871: (5210866, 'one-argument-call'),
 5254352: (5254347, 'two-argument-call'),
 5254408: (5254403, 'two-argument-call'),
 5254458: (5254453, 'receiver-tail'),
 4952352: (4952341, 'receiver-tail'),
 4964576: (4964565, 'receiver-tail')}
RETURN = 0x4a5896

def setup_for(root, words, profile=0, failure=None, versions=(0x00000004,)):
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
                elif name=='GetProcessVersion':r=0x30000 if profile==1 else 0x40000
                elif name=='LoadCursorA':r=0x123000+(a[1]&0xffff)
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
            result=env.machine.call_source(entry, NativeSourceContext(72,1,0x7ff,0x7ff,0,0,0,0,0,0,0,STACK_TOP,entry,2,0xffffffff,0,0,0), RETURN)
            if not result.completed: raise HarnessError('original CRT initialization did not return')
        heap=env.read(HEAP_BASE,env.heap_bytes)
        image=env.read(PROGRAM.data_start,PROGRAM.size-(PROGRAM.data_start-PROGRAM.base))
        stack=env.read(STACK_BASE,STACK_SIZE)
        env.backend='initial';env.side='setup';env._source_graph=False
        env.write(HEAP_BASE,heap);env.write(PROGRAM.data_start,image);env.write(STACK_BASE,stack)
        env.put(journal,0)
        # Each case's receiver starts distinct; only original constructors publish it.
        body=IMAGE[root-PROGRAM.base:root-PROGRAM.base+32]
        if ROOT_METADATA[root][1] in ('receiver-tail','one-argument-call','two-argument-call'):
            at=body.index(0xb9)
            receiver=struct.unpack_from('<I',body,at+1)[0]
            env.put(receiver,words[profile%7])
        if root in (0x40b830,0x437510,0x437560):
            text=(b'',b'Claw!',b'A0123456789xyz')[profile]
            env.write(0x534938,text+b'\0')
        if root==0x415ab0:
            env.put(0x513e10,*words[:4])
            for destination in range(0x534db8,0x534ea8,4):
                env.put(destination,words[(destination//4)%7])
        return_pc,shape=ROOT_METADATA[root]
        if shape=='receiver-tail':
            site=root+5
            target=site+5+struct.unpack_from('<i',IMAGE,site-PROGRAM.base+1)[0]
            env.source_tail_edge(root,site,target)
        s=STACK_TOP-profile*0x100
        env.write(STACK_BASE,bytes([0x39+profile])*STACK_SIZE)
        env.put(s-4,0xe1e2e3e4,return_pc,words[1],words[4],words[5])
        fs=0xffffffff
        if profile%2:
            fs=s+0x100;env.put(fs,0xffffffff,0x4a5790,0xa1a2a3a4)
        context=NativeSourceContext(72,1,0x7ff,0x7ff,*words[:7],s,root,0x8d7 if profile%2 else 2,fs,0,0,0)
        return {'source':context, 'journal':journal, 'ledger':ledger}
    return setup


def cases(random_source):
    for root in ROOTS:
        for profile in range(3):
            words=tuple(random_source.getrandbits(32) for _ in range(7))
            yield Case(f'{root:08x} full CPU frame {profile}',root,
                       setup_for(root,words,profile),source_context=lambda t:t['source'],
                       source_return_pc=ROOT_METADATA[root][0])

    # Physical version results select genuine platform child branches.
    for version in (0x80000003,0x80000004,0x00000003,0x00000104):
        root=0x502d3a
        words=tuple(random_source.getrandbits(32) for _ in range(7))
        yield Case(f'platform GetVersion {version:08x}',root,
                   setup_for(root,words,1,versions=(version,)),
                   source_context=lambda t:t['source'],source_return_pc=ROOT_METADATA[root][0])
    for root,outcome in ((0x4251f0,'return'),):
        words=tuple(random_source.getrandbits(32) for _ in range(7))
        yield Case(f'{root:08x} physical allocator refusal',root,
                   setup_for(root,words,1,failure='alloc'),expect=outcome,
                   source_context=lambda t:t['source'],source_return_pc=ROOT_METADATA[root][0])
