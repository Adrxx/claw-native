"""Native-only canonical menu composition probe over the original physical services.

All game entries are compiled C++; the native memory provider has no instruction
executor. A missing source owner, unsupported transport, or failed initializer
is a failure, never a successful menu. Derived build inputs stay under work/.
"""
from __future__ import annotations
import ctypes as C
import hashlib
import json
import math
import struct
from pathlib import Path
from collections import Counter, deque
import subprocess
import sys
from Tests.NativeMenuBase import trace as reference

ROOT = reference.ROOT
WORK = ROOT / 'work/native-menu-join'
U32 = C.c_uint32

class Source(C.Structure):
    _fields_ = [(name,U32) for name in ('size','version','input_mask','output_mask',
        'eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fs_head',
        'preserve_mask','reserved0','reserved1')]

REGISTERS = [getattr(reference,'UC_X86_REG_'+name.upper()) for name in
             ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags')]

class X87Value(C.Structure):
    _fields_=[('significand',C.c_uint64),('exponent',U32),('reserved',U32)]

class X87(C.Structure):
    _fields_=[(name,U32) for name in ('size','version','control','status','count','pop','push',
                                     'returned','eax','edx','reserved0','reserved1')]+[('slots',X87Value*8)]

class Call(C.Structure):
    _fields_ = [('function', U32), ('receiver', U32), ('receiver2', U32),
                ('count', U32), ('arguments', U32 * 32), ('stack', U32),
                ('x87_count', U32), ('x87_argument', C.c_double),
                ('compiler', C.c_void_p), ('source', C.c_void_p),
                ('return_pc', U32), ('transfer_version', U32), ('transfer_kind', U32),
                ('transfer_site', U32), ('caller', U32), ('disposition', C.c_void_p),
                ('x87_state', C.c_void_p), ('x87_operation', U32),
                ('callback_cpu', C.c_void_p), ('callback_activation', C.c_uint64)]

class NativeMemory:
    """Owned native buffers and physical-service register packets; no emulator."""
    def __init__(self, *unused):
        self.regions = []
        self.registers = {}
    def mem_map(self, base, size):
        if any(base < b + n and b < base + size for b, n, _ in self.regions):
            raise reference.Blocked('Overlapping native memory mapping')
        self.regions.append((base, size, C.create_string_buffer(size)))
    def coalesce(self):
        """Join adjacent storage before native execution publishes pointers.

        A physical allocation may cross a mapped extension. Keep gaps unmapped
        and retain every byte; this is initialization, never live relocation.
        """
        merged = []
        for base, size, data in sorted(self.regions):
            if merged and merged[-1][0] + merged[-1][1] == base:
                previous = merged.pop()
                combined = C.create_string_buffer(previous[1] + size)
                C.memmove(combined, previous[2], previous[1])
                C.memmove(C.addressof(combined) + previous[1], data, size)
                merged.append((previous[0], previous[1] + size, combined))
            else:
                merged.append((base, size, data))
        self.regions[:] = merged
    def pointer(self, address, size):
        if address < 4096 and (address != 0 or size != 4):
            raise reference.Blocked('Native low page is reserved for the four-byte exception head')
        for base, count, data in self.regions:
            if base <= address and address + size <= base + count:
                return C.addressof(data) + address - base
        raise reference.Blocked(f'Unmapped native bytes {address:#x}+{size:#x}')
    def mem_read(self, address, size):
        return C.string_at(self.pointer(address, size), size)
    def mem_write(self, address, data):
        C.memmove(self.pointer(address, len(data)), bytes(data), len(data))
    def reg_read(self, key):
        return self.registers.get(key, 0)
    def reg_write(self, key, value):
        self.registers[key] = value
    def hook_add(self, *unused, **kwargs):
        pass
    def context_save(self):
        return self.registers.copy()
    def context_restore(self, context):
        self.registers = context.copy()
    def emu_start(self, *unused):
        raise reference.Blocked('Guest execution is forbidden in the native join')


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    trace = json.loads((ROOT / 'work/menu-map/trace.json').read_text())
    addresses = {int(row['address'], 16) for row in trace['game_functions']}
    addresses.update((0x4cf020,0x4b97c0,0x42d590,0x4bbd90,0x4c9bd0,0x4d5720,0x4d4280,0x4bd260,0x45f840,0x42a680))
    # Admitted entry roots reached only by original menu teardown. Their
    # complete family surfaces supply internal sibling calls without aliases.
    addresses.update((0x4c92f0, 0x4c9be0, 0x4b4b40, 0x4ca300, 0x4d0240,
                      0x4ce8e0, 0x4cdf40, 0x4c89e0, 0x4d46f0))
    # Prior-state transitions require the complete paper owner, including the
    # uncached palette loader; the successful idle trace does not reach it.
    addresses.update((0x42a4f0, 0x48f500, 0x48f740, 0x4ecb40, 0x4ee880,
                      0x4ee8c0, 0x4ee8e0, 0x4ee9a0, 0x4eecc0, 0x4ef010,
                      0x4ef7d0, 0x4efac0, 0x4c6260, 0x4c7360, 0x4c7730,
                      0x4c7850, 0x4b9c50, 0x4c96b0, 0x4d4100,
                      0x4ec050, 0x4c7510, 0x4ec010))
    specifications = []
    for path in sorted((ROOT / 'Tests/families').glob('*.json')):
        spec = json.loads(path.read_text())
        if spec.get('abi') == 'canonical':
            specifications.append(spec)
    owners = {}
    for address in addresses:
        candidates = [s for s in specifications if any(int(e['address'], 16) == address for e in s.get('owned', []))]
        if address == 0x40f680:
            candidates = [s for s in candidates if s['id'] == 'pickup_points']
        if len(candidates) == 1:
            owners[address] = candidates[0]
        elif len(candidates) > 1:
            raise reference.Blocked(f'Ambiguous canonical owner {address:#x}: {[s["id"] for s in candidates]}')
    elected = {s['id']: s for s in owners.values()}
    declarations, rows, sources, metadata = [], [], set(), {}
    for spec in elected.values():
        if spec.get('evidence',{}).get('level') != 'admitted':
            raise reference.Blocked(f'Native menu requires an admitted owner: {spec["id"]}')
        symbol = spec['oracle']['entry']
        declarations.append(f'extern "C" uint32_t {symbol}(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);')
        implementations = [p for p in spec['sources'] if p.endswith('.cpp') and
                           symbol in (ROOT/p).read_text()]
        canonical = [p for p in implementations if 'Canonical' in p]
        implementations = canonical or implementations
        if len(implementations) != 1:
            raise reference.Blocked(f'Ambiguous native implementation for {spec["id"]}: {implementations}')
        sources.add(implementations[0])
        # The admitted module owns its complete surface, including error paths
        # absent from the successful original trace.
        for entry in spec['owned']:
            address = int(entry['address'], 16)
            if address in owners and owners[address]['id'] != spec['id']:
                continue
            rows.append((address, symbol))
            metadata[address] = entry
    entries = dict(rows)
    code = '#include "ClawRuntime.h"\n#include <new>\n' + '\n'.join(declarations) + '\n'
    code += '''extern "C" ClawHost *menu_host(void *u, uint8_t *(*b)(void*,uint32_t,uint32_t), uint32_t (*c)(void*,const ClawCall*)) {
        auto *h = new ClawHost{}; h->user=u; h->bytes=b; h->call=c; h->maximumOperations=200000000; return h;
    }
    extern "C" void menu_free(ClawHost *h) {delete h;}
    extern "C" void menu_fault(ClawHost *h,uint32_t address) {if(!h->fault){h->fault=CLAW_FAULT_HOST;h->faultAddress=address;}}
    extern "C" uint32_t menu_fault_address(ClawHost *h) {return h->faultAddress;}
    extern "C" uint32_t menu_run(ClawHost *h,uint32_t f,uint32_t receiver,const uint32_t *args,uint32_t n,uint32_t stack,ClawSourceContext *source,uint32_t returnPC,uint32_t *out) {
        auto previous=h->entryStackPointer;h->entryStackPointer=stack;
        auto priorSource=h->sourceContext;auto priorReturn=h->sourceReturnPC;
        h->sourceContext=source;h->sourceReturnPC=returnPC;
        ClawEntry entry=nullptr;
        switch(f) {
    '''
    code += '\n'.join(f'case 0x{address:x}: entry={symbol};break;' for address, symbol in sorted(entries.items()))
    code += '''default:menu_fault(h,f);break;
        }
        uint32_t done=entry ? entry(f,receiver,args,n,h,out):0;
        h->entryStackPointer=previous;h->sourceContext=priorSource;h->sourceReturnPC=priorReturn;return done;
    }\n'''
    compiler = subprocess.check_output(['xcrun', '--find', 'clang++'], text=True).strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    digest = hashlib.sha256(code.encode())
    for path in sorted(sources | {'Sources/ClawRuntime.h', 'Sources/ClawRuntime.hpp'}):
        digest.update(path.encode());digest.update((ROOT/path).read_bytes())
    digest.update(subprocess.check_output([compiler,'--version']))
    digest.update(sdk.encode())
    target = ROOT / 'work/build/native-menu-join' / digest.hexdigest()[:24]
    target.mkdir(parents=True, exist_ok=True)
    library = target/'menu.dylib'
    if not library.exists():
        bridge = target/'bridge.cpp';bridge.write_text(code)
        subprocess.run([compiler,'-std=c++17','-O0','-isysroot',sdk,'-dynamiclib','-I'+str(ROOT/'Sources'),str(bridge),
                        *[str(ROOT/s) for s in sorted(sources) if s.endswith('.cpp')],'-o',str(library)],check=True)
    (WORK/'owners.json').write_text(json.dumps({hex(a):s['id'] for a,s in owners.items()},indent=2)+'\n')
    return C.CDLL(str(library)), metadata


class NativeJoin(reference.MenuTrace):
    def __init__(self, library, entries, *, deny_owner=None, deny_platform=None, missing_resource=False, frame_count=61):
        super().__init__(machine_factory=NativeMemory,deny_platform=deny_platform,missing_resource=missing_resource)
        self.library, self.entries = library, entries
        self.deny_owner=deny_owner
        self.frame_count=frame_count
        self.clock_step=0
        self.native_error = None
        self.native_frames = []
        self.native_functions = []
        self.native_calls = deque(maxlen=256)
        self.native_counts = Counter()
        self._bytes = C.CFUNCTYPE(C.c_void_p,C.c_void_p,U32,U32)(self.resolve)
        self._call = C.CFUNCTYPE(U32,C.c_void_p,C.POINTER(Call))(self.service)
        library.menu_host.argtypes = [C.c_void_p, type(self._bytes), type(self._call)]
        library.menu_host.restype = C.c_void_p
        library.menu_run.argtypes = [C.c_void_p,U32,U32,C.POINTER(U32),U32,U32,C.c_void_p,U32,C.POINTER(U32)]
        library.menu_fault.argtypes = [C.c_void_p,U32]
        library.menu_fault_address.argtypes = [C.c_void_p]
        library.menu_free.argtypes = [C.c_void_p]
        self.host = library.menu_host(None,self._bytes,self._call)
    def close(self):
        """Release probe-owned physical resources, not recovered game teardown."""
        for stream in self.files.values():
            stream.close()
        self.files.clear()
        self.closed_files.clear()
        if self.host:
            self.library.menu_free(self.host)
            self.host=None
        self.machine.regions.clear()
        for table in (self.com_objects,self.maps,self.memory_files,self.archives,
                      self.dcs,self.sequences,self.midi_drivers):
            table.clear()
    def resolve(self, unused, address, size):
        try:
            return self.machine.pointer(address,size)
        except Exception as error:
            self.native_error = str(error)
            self.library.menu_fault(self.host,address)
            return None
    def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        if not self.host:raise reference.Blocked('Native probe host is closed')
        if address==self.deny_owner:raise reference.Blocked(f'Native owner deliberately withheld: {address:#x}')
        if len(self.native_frames) >= 32:
            raise reference.Blocked('Native graph depth exceeded')
        self.native_frames.append(stack)
        self.native_functions.append(address)
        self.native_counts[address]+=1
        self.native_calls.append(dict(function=hex(address),receiver=hex(receiver),arguments=list(arguments)))
        output = U32()
        contract = self.entries.get(address,{}).get('source_context')
        if contract and source is None:
            cpu=Source(size=C.sizeof(Source),version=1,input_mask=contract['input_mask'],
                       output_mask=contract['output_mask'],preserve_mask=contract['preserve_mask'],
                       esp=stack,eip=address,ecx=receiver,eflags=2,fs_head=self.word(0))
            source=C.addressof(cpu)
            return_pc=reference.STOP
            for index,value in enumerate([return_pc,*arguments]):self.put(stack+4*index,value)
        try:
            done = self.library.menu_run(self.host,address,receiver,(U32*len(arguments))(*arguments),len(arguments),stack,source,return_pc,C.byref(output))
            if not done:
                raise reference.Blocked(self.native_error or f'Native source fault at {self.library.menu_fault_address(self.host):#x} from {address:#x}')
            return output.value
        finally:
            self.native_frames.pop()
            self.native_functions.pop()
    def service(self, unused, pointer):
        q = pointer.contents
        try:
            if q.x87_count:
                return self.math_service(q)
            if q.compiler or q.transfer_version or q.callback_cpu:
                raise reference.Blocked(f'Unelected contextual native boundary {q.function:#x}')
            args = list(q.arguments[:q.count])
            # Ordinary canonical modules without explicit source ESP receive a
            # disjoint automatic frame. Explicit aliases in arguments are kept.
            stack = q.stack or self.native_frames[-1]-0x400
            if q.function == 0x4b90b0:
                # Native application shutdown replaces this platform receiver.
                # Keep the original first-error latch and close-message order.
                if q.function == self.deny_owner:
                    raise reference.Blocked('Native error owner deliberately withheld: 0x4b90b0')
                if q.count != 2 or q.receiver != self.word(self.application+8):
                    raise reference.Blocked('Invalid native application error receiver')
                if not self.word(q.receiver+0x248):
                    self.put(q.receiver+0x248,1)
                    window=self.word(q.receiver+4)
                    if window and not self.word(window+0xc):
                        request=Call(function=0x546d50,count=4,stack=stack-0x100)
                        for i,value in enumerate((self.word(window+4),0x10,0,0)):
                            request.arguments[i]=value
                        self.service(None,C.pointer(request))
                        if self.native_error:raise reference.Blocked(self.native_error)
                    self.put(q.receiver+0x244,0)
                    self.put(q.receiver+0x24c,args[0])
                    self.put(q.receiver+0x250,args[1])
                return 0
            # Reviewed factory CALL at 0x429332, continuation 0x429335.
            # This boundary exposes the IFC's nested CMemFile automatic object.
            if q.function==0x45ace0 and self.native_functions[-1]==0x428c40 and not q.stack:
                if q.count!=3:raise reference.Blocked('Invalid factory initializer ABI')
                stack=self.native_frames[-1]-0x30
            # Factory virtual CALL 0x429350, continuation 0x429353: its
            # 0x20-byte frame, one argument and return address place menu entry
            # at S-0x28. The paper palette loader exposes a nested CMemFile.
            if q.function==0x45b3f0 and self.native_functions[-1]==0x428c40 and not q.stack:
                if q.count!=1 or self.word(self.word(q.receiver)+0x24)!=q.function:
                    raise reference.Blocked('Invalid factory menu-entry ABI')
                stack=self.native_frames[-1]-0x28
            if q.function==0x4b8910:
                if q.count!=2 or not q.receiver or self.word(q.receiver+4)!=1:
                    raise reference.Blocked('Invalid native window input receiver')
                if self.messages or args[0] not in (0,0x100,0x101,0x201,0x202):
                    raise reference.Blocked('Native menu probe only elects an idle physical input queue')
                self.physical_events.append(dict(service='native window input drain',window=1,
                                                message=args[0],maximum=args[1],removed=0))
                return 0
            if q.function in self.entries and reference.game(q.function):
                return self.invoke(q.function,q.receiver,args,stack,q.source,q.return_pc)
            if reference.game(q.function):
                raise reference.Blocked(f'Missing native game owner {q.function:#x}')
            saved = self.machine.context_save()
            try:
                cpu=Source.from_address(q.source) if q.source else None
                if cpu:
                    for register,(name,_) in zip(REGISTERS,Source._fields_[4:14]):
                        self.machine.reg_write(register,getattr(cpu,name))
                    self.put(0,cpu.fs_head)
                continuation=q.return_pc if cpu else reference.STOP
                for index,value in enumerate([continuation,*args]):
                    self.put(stack+4*index,value)
                self.machine.reg_write(reference.UC_X86_REG_ESP,stack)
                self.machine.reg_write(reference.UC_X86_REG_ECX,q.receiver)
                self.machine.reg_write(reference.UC_X86_REG_EDX,q.receiver2)
                self.machine.reg_write(reference.UC_X86_REG_EIP,q.function)
                self.last_transfer = dict(site='native',target=hex(q.function),kind='native-service')
                if q.function in self.com_methods:
                    self.com_fixture(q.function)
                    if self.callback:
                        callback=self.callback
                        target=self.machine.reg_read(reference.UC_X86_REG_EIP)
                        callback_stack=self.machine.reg_read(reference.UC_X86_REG_ESP)
                        result=self.invoke(target,0,[self.word(callback_stack+4),self.word(callback_stack+8)],callback_stack)
                        if result not in (0,1) or self.machine.mem_read(callback['descriptor'],108).hex()!=callback['event']['description']:
                            raise reference.Blocked('Native enumeration callback changed its descriptor or result contract')
                        callback['event'].update(callback_result=result,native_callback=True)
                        self.machine.context_restore(callback['context'])
                        self.callback=None
                        self.returned(0,20)
                else:
                    target = next((target for target,(slot,_) in self.imports.items() if slot == q.function),q.function)
                    self.fixture(target)
                    if target in (0x4a4590,0x4a4450) and self.array_callbacks:
                        frame=self.array_callbacks[-1]
                        for index in range(frame['count']):
                            self.invoke(frame['constructor'],frame['base']+index*frame['stride'],[],frame['sp']-4)
                            frame['event']['completed']=index+1
                        self.machine.context_restore(frame['context'])
                        self.array_callbacks.pop()
                        self.returned(0,frame.get("pop",20))
                if self.machine.reg_read(reference.UC_X86_REG_EIP) != continuation:
                    raise reference.Blocked(f'Native physical callback transport required at {q.function:#x}')
                if cpu:
                    for register,(name,_) in zip(REGISTERS,Source._fields_[4:14]):
                        setattr(cpu,name,self.machine.reg_read(register))
                    cpu.fs_head=self.word(0)
                return self.machine.reg_read(reference.UC_X86_REG_EAX)
            finally:
                self.machine.context_restore(saved)
        except Exception as error:
            if self.native_error is None:
                self.native_error = str(error)
            self.library.menu_fault(self.host,q.function)
            return 0
    def math_service(self,q):
        if q.function:
            self.platform_call(q.function, 'native mathematical service')
        if q.x87_count==1 and q.function==0x4a30e0:
            if not math.isfinite(q.x87_argument):raise reference.Blocked('Non-finite native conversion')
            return math.trunc(q.x87_argument)&0xffffffff
        if q.x87_count not in (2,3) or not q.x87_state:
            raise reference.Blocked(f'Unelected native floating boundary {q.function:#x}')
        state=X87.from_address(q.x87_state)
        if state.control!=0x023f or state.size!=C.sizeof(X87) or state.version!=1 or state.count>8:
            raise reference.Blocked('Unsupported native floating control/state')
        def number(slot):
            # This finite menu election contains binary64 and integral operands.
            # Reject an extended-precision operand rather than round it silently.
            if slot.reserved or slot.exponent&0x7fff==0x7fff or slot.significand&0x7ff:
                raise reference.Blocked('Native extended-precision arithmetic provider required')
            value=math.ldexp(slot.significand,(slot.exponent&0x7fff)-16383-63)
            return -value if slot.exponent&0x8000 else value
        values=[number(state.slots[i]) for i in range(state.count)]
        args=list(q.arguments[:q.count]); result=None; eax=edx=0
        f64=lambda:struct.unpack('<d',struct.pack('<II',*args))[0]
        if q.x87_count==3:
            operation=q.x87_operation
            if operation==2:result=float(C.c_int32(args[0]).value)
            elif operation==3:result=f64()
            elif operation==5:result=values[0]/values[1]
            elif operation==6:pass
            elif operation==7:result=-values[0]
            elif operation==8:result=f64()-values[0]
            elif operation==9:result=values[0]*f64()
            elif operation==10:result=values[0]
            elif operation==11:result=values[0]/f64()
            else:raise reference.Blocked(f'Native extended-precision arithmetic operation {operation} required')
        elif q.function==0x4a30e0:
            integer=math.trunc(values[0]);eax=integer&0xffffffff;edx=(integer>>32)&0xffffffff
        elif q.function==0x4f1b30:
            result=math.pow(values[1],values[0])
        elif q.function==0x4f2400:
            if state.pop!=1 or state.push!=1 or not -1.0<=values[0]<=1.0:
                raise reference.Blocked('Unsupported native acos stack or domain')
            result=math.acos(values[0])
        else:
            raise reference.Blocked(f'Unelected native mathematical function {q.function:#x}')
        remaining=[bytes(state.slots[i]) for i in range(state.pop,state.count)]
        C.memset(C.addressof(state.slots),0,C.sizeof(state.slots))
        if state.push:
            if result is None or not math.isfinite(result):raise reference.Blocked('Invalid native mathematical result')
            fraction,exponent=math.frexp(abs(result))
            state.slots[0].significand=int(fraction*(1<<64))
            state.slots[0].exponent=(exponent+16382 if result else 0)|(0x8000 if math.copysign(1,result)<0 else 0)
        for index,slot in enumerate(remaining):C.memmove(C.addressof(state.slots[state.push+index]),slot,len(slot))
        state.count=state.count-state.pop+state.push
        state.status=(state.status&~0x3800)|((((state.status>>11)+state.pop-state.push)&7)<<11)
        state.returned=1;state.eax=eax;state.edx=edx
        self.math_events.append(dict(function=hex(q.function),operation=q.x87_operation,operands=values,result=result,eax=eax))
        return eax
    def fixture(self,address):
        return super().fixture(address)
    def run(self,address,receiver,arguments=(),phase='',boundary=None,stack=reference.STACK):
        if boundary is not None:
            # Native startup owns the inline platform object storage. The game
            # reset and all subsequent initialization still use their owners.
            self.phase=phase
            def physical(function,target,args=()):
                call=Call(function=function,receiver=target,count=len(args),stack=stack-0x100)
                for i,value in enumerate(args):call.arguments[i]=value
                value=self.service(None,C.pointer(call))
                if self.native_error:raise reference.Blocked(self.native_error)
                return value
            if (address,boundary)==(0x42637d,0x4263ae):
                self.put(receiver,0xffffffff)
                for offset in (0x1d0,0x1d4,0x1cc,0x210,0x214,0x20c):self.put(receiver+offset,0)
                self.invoke(0x4b3410,receiver,[],stack)
            elif (address,boundary)==(0x4264cc,0x4264dc):
                physical(0x4f5cbd,receiver+0x74,[10]);self.put(receiver,0)
            elif (address,boundary)==(0x4261f7,0x42620c):
                physical(0x4f6118,receiver,[10])
                for token in (receiver+0x1c,receiver+0x20,0x54131c):self.put(token,0)
            elif (address,boundary)==(0x426565,0x426594):
                physical(0x4f5620,receiver,[10]);physical(0x4f6439,receiver+0x1c)
                self.machine.mem_write(receiver+0x20,bytes(0x24));self.put(receiver+0x44,0x4d505255)
            else:
                raise reference.Blocked(f'Unelected native startup constructor {address:#x}')
            self.paused=True
            return receiver
        self.phase=phase
        result = self.invoke(address,receiver,list(arguments),stack)
        self.phase_results.append(dict(phase=phase,entry=hex(address),result=result))
        return result
    def execute(self):
        self.run(0x45acb0,0,phase='menu-text-static-initialization')
        self.setup_version()
        application=self.allocate(0x134)
        self.run(0x4254a0,application,phase='application-construction')
        scene=self.allocate(0x3c)
        self.run(0x4ce960,scene,phase='scene-construction')
        if not self.run(0x4cea10,scene,(1,640,480,8,0),phase='scene-initialization'):
            raise reference.Blocked('Native scene initialization failed')
        self.setup_resources(application,scene)
        if not self.run(0x428c40,application,(5,1,1,0),phase='menu-construction-and-initialization'):
            raise reference.Blocked('Native menu initialization failed')
        self.application=application
        self.menu=self.word(application+0x2c)
        sparkles=self.word(self.menu+0x26c)
        if not sparkles or any(not self.word(sparkles+4*i) for i in range(15)):
            raise reference.Blocked('MenuSparkle registration did not construct all 15 menu actors')
        self.menu_sparkles=[self.word(sparkles+4*i) for i in range(15)]
        self.initialized_state=self.machine.mem_read(self.menu,0x2c8).hex()
        self.interface_nodes=interface_nodes(self)
        self.initialized_heap=heap_digest(self)
        for index in range(getattr(self,'frame_count',61)):
            self.advance_time(1000+(index+1)*1000//60)
            phase='first-presentation' if index==0 else f'idle-{index:02d}'
            before=len(self.presentations)
            result=self.run(0x428b60,application,phase=phase)
            if result!=1 or len(self.presentations)!=before+1:
                raise reference.Blocked(f'Native frame {index} did not present exactly once')
            self.frame_cycles.append(dict(index=index,phase=phase,milliseconds=self.milliseconds,
                delta=self.word(0x54132c),animation_delta=self.word(0x5430c4),result=result,
                state=self.machine.mem_read(self.menu,0x2c8).hex(),
                live_heap_sha256=heap_digest(self)))


def heap_digest(host):
    """Witness every live allocation, including actor/logic state and pixels."""
    digest=hashlib.sha256()
    for address,size in sorted(host.allocations.items()):
        digest.update(struct.pack('<II',address,size))
        digest.update(host.machine.mem_read(address,max(size,1)))
    return digest.hexdigest()


def interface_nodes(host):
    nodes=[]
    def visit(token,depth):
        count=host.word(token+32)
        if len(nodes)>512 or depth>16 or count>512:raise reference.Blocked('Invalid IFC tree')
        images=[host.bytestring(host.word(token+84+4*i)).decode('ascii') for i in range(8)]
        selected=[]
        array=host.word(token+64)
        for i in range(8):
            surface=host.word(array+4*i)
            physical=host.com_objects.get(host.word(surface+8))
            if not physical or physical['kind']!='IDirectDrawSurface' or not physical['references']:
                raise reference.Blocked('IFC selection has no live native image surface')
            selected.append(dict(surface=hex(surface),width=physical['width'],height=physical['height']))
        nodes.append(dict(depth=depth,id=host.word(token+80),name=host.bytestring(host.word(token+20)).decode('ascii'),
                          children=count,images=images,selected=selected))
        for i in range(count):visit(host.word(host.word(token+28)+4*i),depth+1)
    visit(host.menu+0x154+72,0)
    profile=json.loads((ROOT/'Tests/state_five_interface_profile.json').read_text())
    fields=('depth','id','name','children','images')
    if [{k:n[k] for k in fields} for n in nodes]!=[{k:n[k] for k in fields} for n in profile['nodes']]:
        (WORK/'ifc-nodes.json').write_text(json.dumps(nodes,indent=2)+'\n')
        raise reference.Blocked('Parsed native IFC nodes/images differ from retail profile')
    return nodes


def physical_events(host):
    result=[]
    for event in host.physical_events:
        event={k:v for k,v in event.items() if k not in ('caller','native_callback','preserved_cpu_stack_fs_and_descriptor')}
        if event['service']=='native window input drain':
            if 0<event['maximum']<0x80000000:
                event=dict(service='PeekMessageA',window=event['window'],minimum=event['message'],
                           maximum=event['message'],remove=1,queued=0)
            else:continue
        result.append(event)
    return result


def check_controls(library, entries):
    from Tests.NativeMenuBase.resources import compare as compare_resources
    results={'failed-archive-game-cleanup':compare_resources(library,entries)}
    controls=(('missing-owner',dict(deny_owner=0x4dcdf0),'deliberately withheld'),
              ('missing-sparkle-owner',dict(deny_owner=0x45f840),'deliberately withheld'),
              ('missing-random-service',dict(deny_platform=0x4a3050),'deliberately withheld'),
              ('missing-physical-service',dict(deny_platform=0x4a7260),'deliberately withheld'),
              ('missing-archive',dict(missing_resource=True),'Original archive open failed; resource root is unavailable'))
    for name,options,expected in controls:
        frames=1 if name in ('missing-sparkle-owner','missing-random-service') else 0
        probe=NativeJoin(library,entries,frame_count=frames,**options)
        try:
            probe.execute()
        except reference.Blocked as error:
            if expected and expected not in str(error):raise
            if name=='missing-archive' and not any(e.get('missing') for e in probe.physical_events):raise
            results[name]=str(error)
        else:
            raise reference.Blocked(f'{name} incorrectly completed initialization')
        finally:
            streams=list(probe.files.values())
            probe.close()
            if not all(s.closed for s in streams) or probe.host or probe.machine.regions or any((
                probe.com_objects,probe.maps,probe.memory_files,probe.archives,
                probe.dcs,probe.sequences,probe.midi_drivers)):
                raise reference.Blocked('Probe physical teardown leaked resources')
        try:
            probe.run(0x45acb0,0)
        except reference.Blocked as error:
            if str(error)!='Native probe host is closed':raise
        else:
            raise reference.Blocked('Closed native host accepted work')
    results['probe_physical_teardown']='files, host, native memory and physical tables released; closed host rejects work; recovered game cleanup is checked separately by lifecycle'
    (WORK/'controls.json').write_text(json.dumps(results,indent=2)+'\n')


def resize_probe(library, entries):
    from Tests.NativeMenuBase.resize import compare
    return compare(library, entries)


def main():
    library,entries=build()
    if sys.argv[1:]==['--controls-only']:
        check_controls(library,entries)
        print(json.dumps(dict(status='compared',scope='native failure and host-lifetime controls')))
        return 0
    if sys.argv[1:]==['--transition-probe']:
        from Tests.NativeMenuBase.transitions import compare
        return compare(library,entries)
    if sys.argv[1:]==['--resource-probe']:
        from Tests.NativeMenuBase.resources import compare
        print(json.dumps(compare(library,entries)))
        return 0
    if sys.argv[1:]==['--lifecycle-probe']:
        from Tests.NativeMenuBase.lifecycle import compare
        return compare(library,entries)
    if sys.argv[1:]==['--resize-probe']:
        return resize_probe(library,entries)
    native=NativeJoin(library,entries)
    status='blocked'
    try:
        native.execute()
        status='frames-complete'
        original=reference.MenuTrace()
        NativeJoin.execute(original)
        comparisons={
            'initialized_menu':native.initialized_state==original.initialized_state,
            'allocation_identity':native.allocations==original.allocations,
            'initialized_live_heap':native.initialized_heap==original.initialized_heap,
            'frame_state':native.frame_cycles==original.frame_cycles,
            'interface_nodes_and_native_surfaces':native.interface_nodes==original.interface_nodes,
            'ordered_physical_services':physical_events(native)==physical_events(original),
            'pixels_and_palette':all(a['pixels_sha256']==b['pixels_sha256'] and a['palette_sha256']==b['palette_sha256']
                                     for a,b in zip(native.presentations,original.presentations)),
        }
        (WORK/'original.json').write_text(json.dumps(dict(initialized_state=original.initialized_state,
            initialized_live_heap=original.initialized_heap,frames=original.frame_cycles,physical_events=original.physical_events,presentations=original.presentations),indent=2)+'\n')
        (WORK/'comparison.json').write_text(json.dumps(comparisons,indent=2)+'\n')
        if not all(comparisons.values()):
            raise reference.Blocked('Native/original comparison mismatch: '+str(comparisons))
        from Tests.NativeMenuBase.lifecycle import cleanup, controls as cleanup_controls
        expected_cleanup=cleanup(original)
        actual_cleanup=cleanup(native)
        lifecycle=dict(comparisons={key:expected_cleanup[key]==actual_cleanup[key] for key in expected_cleanup})
        (WORK/'lifecycle-original.json').write_text(json.dumps(expected_cleanup,indent=2)+'\n')
        (WORK/'lifecycle-native.json').write_text(json.dumps(actual_cleanup,indent=2)+'\n')
        if not all(lifecycle['comparisons'].values()):
            raise reference.Blocked('Native/original recovered menu cleanup mismatch')
        lifecycle['controls']=cleanup_controls(library,entries)
        lifecycle['status']='compared'
        (WORK/'lifecycle.json').write_text(json.dumps(lifecycle,indent=2)+'\n')
        check_controls(library,entries)
        status='compared'
    except reference.Blocked as error:
        native.native_error=str(error)
    report=dict(status=status,scope='Headless canonical construction, frames and recovered cleanup over native buffers and physical test services; Swift shared-host application integration remains separate',
                error=native.native_error,phases=native.phase_results,calls=list(native.native_calls),
                counts={hex(k):v for k,v in native.native_counts.items()},initialized_state=getattr(native,'initialized_state',None),
                interface_nodes=getattr(native,'interface_nodes',None),
                menu_sparkles=getattr(native,'menu_sparkles',None),
                initialized_live_heap=getattr(native,'initialized_heap',None),
                physical_events=native.physical_events,guest_execution=False,
                frames=native.frame_cycles,presentations=native.presentations)
    (WORK/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    native.close()
    if 'original' in locals():
        for stream in original.files.values():stream.close()
    print(json.dumps(dict(status=status,error=native.native_error,frames=len(native.frame_cycles),guest_execution=False)))
    return 0 if status=='compared' else 2

if __name__=='__main__':
    raise SystemExit(main())
