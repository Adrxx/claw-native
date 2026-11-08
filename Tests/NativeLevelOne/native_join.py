"""Native-only Level 1 join probe over admitted canonical owners.

Run with work/test-env/bin/python -m Tests.NativeLevelOne.native_join.
Every game entry is compiled C++ elected from work/level-one-map/ownership.json;
the native memory provider has no instruction executor. The physical services
are the Level 1 tracer's stand-ins. A missing owner, transport or service is a
failure, never a successful frame. Derived output stays under work/.
"""
from __future__ import annotations
import argparse
import re
import hashlib
import json
import subprocess
import zlib
import sys
import ctypes as C
from pathlib import Path
from Tests.NativeMenuBase import native_join as menu
from Tests.NativeMenuBase.native_join import NativeJoin, NativeMemory, Call, Source, X87
from collections import Counter
from Tests.NativeLevelOne.trace import LevelOneTrace
from Tests.NativeMenuBase.trace import Blocked, ROOT, STACK, game

WORK = ROOT/'work/native-level-one-join'
# Inline constructor spans in the original application startup. Native startup
# provides their effects through the same physical MFC services the tracer uses.
INLINE = {(0x42614c,0x42616b),(0x4262c4,0x4262d7),(0x4260d3,0x4260f5)}
# Admitted callers that reach the x87-result owner 0x420dd0 through an
# ordinary call. Checked against the original: at each call site (0x41653b,
# 0x4183c6, 0x41b799, 0x41bcae, 0x41e966) every earlier value was stored with
# FSTP, so the x87 stack is empty, and the pushed ST(0) is later discarded with
# FSTP ST(0). The owner therefore enters on an empty stack and its result is
# dropped; any other ordinary call into an x87-result owner is refused.
# The 0x4181c0 rope owner uses the separately validated envelope below.
# CLAW_SOURCE_PRESERVABLE: EBX, ESI, EDI, EBP and the exception-chain head.
SOURCE_PRESERVABLE = 0x472
X87_DISCARD = {(0x415df0,0x420dd0),(0x418120,0x420dd0),(0x41b630,0x420dd0),(0x41e710,0x420dd0)}
# Ordinary loot dispatch below the admitted nested-method environment owner.
# The 0x4dc83c virtual CALL reaches these unchanged owners; 0x40e690 inlines
# constructor 0x40e750, whose motion refresh CALL is at 0x40e8f7.
LOOT_X87_PATHS = {
    (0x4dc830,0x434050,0x40e690,0x4dca10),
    (0x4dc830,0x44df60,0x44e0c0,0x42df90,0x40e690,0x4dca10),
    (0x4dc830,0x483ae0,0x44df60,0x483e10,0x44e0c0,0x42df90,0x40e690,0x4dca10),
    (0x4063b0,0x40f2a0,0x4dca10),
}
# Mercat's exact base-update CALL at 0x460af9 carries the current packet.
# The integer prefix of 0x44d000 calls chooseAction at 0x44d02b. Keep that
# packet in a scoped host frame, then return the child's checked SW through
# the still-live exact request. The enclosing Mercat ENTRY is not its cursor.
EXACT_ENV_PATH = (0x44d000,0x43e420)


def validate_rope_x87_call(call, caller, entry):
    """The ordinary rope-release call at 0x4183c6, returning to 0x4183cb.

    The original prepares its coordinates with balanced FILD/FSTP pairs and
    immediately discards the returned ST(0). Its six stack words belong to
    thiscall owner 0x420dd0. No source CPU, explicit frame, callback or transfer
    protocol is elected here. Check before supplying the native child frame.
    See Tests.NativeLevels.rope_x87_check for the original boundary comparison.
    """
    if (caller != 0x4181c0 or call.function != 0x420dd0
            or call.receiver != 0x534db8 or call.count != 6
            or any(getattr(call, name) for name in (
                'receiver2', 'stack', 'source', 'return_pc', 'x87_count',
                'x87_argument', 'compiler', 'transfer_version', 'transfer_kind',
                'transfer_site', 'caller', 'disposition', 'x87_state',
                'x87_operation', 'callback_cpu', 'callback_activation'))
            or (entry.get('convention'), entry.get('argc'), entry.get('returns'))
               != ('thiscall', 6, 'x87')
            or entry.get('x87_result') != dict(pop=0, push=1)):
        raise Blocked('Unelected rope x87 discard boundary')


def build(ownership_path=None, work=None, cache='native-level-one-join', extra_roots=()):
    """Elect and compile admitted owners from an original census.

    The end-of-level join reuses this with its own census and work directory."""
    work=work or WORK
    work.mkdir(parents=True,exist_ok=True)
    ownership=json.loads((ownership_path or ROOT/'work/level-one-map/ownership.json').read_text())
    unresolved=[r['address'] for r in ownership['rows'] if r['classification'] not in ('admitted','native-reuse')]
    specifications={}
    for path in sorted((ROOT/'Tests/families').glob('*.json')):
        spec=json.loads(path.read_text())
        if spec.get('abi')=='canonical':
            specifications[spec['id']]=spec
    owners={}
    for row in ownership['rows']:
        # Native-reuse startup owners are the same recovered modules the menu
        # join elects; native zlib and the window input queue are physical.
        if row['classification']=='native-reuse' and row['native_reuse'] in specifications:
            owners[int(row['address'],16)]=specifications[row['native_reuse']]
            continue
        if row['classification']!='admitted':continue
        owner=row['owner']
        if owner not in specifications:
            raise Blocked(f'Admitted owner {owner} for {row["address"]} is not a canonical specification')
        owners[int(row['address'],16)]=specifications[owner]
    # Menu-only roots retained by the menu join (teardown and transitions).
    roots=(0x4cf020,0x4b97c0,0x42d590,0x4bbd90,0x4c9bd0,0x4d5720,0x4d4280,0x4bd260,0x45f840,0x42a680)
    for address in sorted(set(roots) | set(extra_roots)):
        for spec in specifications.values():
            if any(int(e['address'],16)==address for e in spec.get('owned',[])):
                owners.setdefault(address,spec)
    # Admitted owners reached only by a vtable tail JMP never appear as trace
    # rows. Elect, from the admitted manifests, families whose every owned
    # entry is a vtable word in the original data sections; they dispatch only
    # through an elected thunk whose original body is MOV r,[ECX]; JMP [r+d].
    thunks={a:d for a in owners if (d:=vtable_tail_slot(a)) is not None}
    tail_only=set()
    for spec in specifications.values():
        addresses=[int(e['address'],16) for e in spec.get('owned',[])]
        if (spec['id'] in {s['id'] for s in owners.values()} or not addresses
                or spec.get('evidence',{}).get('level')!='admitted'
                or spec['id'].startswith(('application_','static_','crt_','mfc_'))
                or not all(game(a) and a not in owners and a in data_words() for a in addresses)):continue
        for address in addresses:
            owners[address]=spec;tail_only.add(address)
    elected={s['id']:s for s in owners.values()}
    declarations,rows,sources,metadata=[],{},set(),{}
    for spec in elected.values():
        if spec.get('evidence',{}).get('level')!='admitted' and not spec['id'].startswith(('application_','static_')):
            raise Blocked(f'Native Level 1 requires an admitted owner: {spec["id"]}')
        symbol=spec['oracle']['entry']
        declarations.append(f'extern "C" uint32_t {symbol}(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);')
        shared=[p for s in spec.get('shared_sources',[]) for p in s.get('sources',[])]
        implementations=[p for p in spec.get('sources',[]) if p.endswith('.cpp') and symbol in (ROOT/p).read_text()]
        canonical=[p for p in implementations if 'Canonical' in p]
        # Otherwise the specification's own canonical_sources decide (an app
        # adapter in `sources` may also declare the entry symbol).
        canonical=canonical or [p for p in implementations if p in spec.get('canonical_sources',[])]
        implementations=canonical or implementations
        if len(implementations)!=1:
            raise Blocked(f'Ambiguous native implementation for {spec["id"]}: {implementations}')
        sources.add(implementations[0])
        sources.update(p for p in shared if p.endswith('.cpp'))
        for entry in spec['owned']:
            address=int(entry['address'],16)
            if address in owners and owners[address]['id']!=spec['id']:continue
            if address in rows and rows[address]!=symbol:
                raise Blocked(f'Ambiguous owned surface {address:#x}')
            rows[address]=symbol;metadata[address]=dict(entry,tail_only=True) if address in tail_only else entry
    code='#include "ClawRuntime.h"\n#include <new>\n'+'\n'.join(sorted(set(declarations)))+'\n'
    code+='''extern "C" ClawHost *menu_host(void *u, uint8_t *(*b)(void*,uint32_t,uint32_t), uint32_t (*c)(void*,const ClawCall*)) {
        auto *h = new ClawHost{}; h->user=u; h->bytes=b; h->call=c; h->maximumOperations=2000000000; return h;
    }
    extern "C" void menu_free(ClawHost *h) {delete h;}
    extern "C" void menu_fault(ClawHost *h,uint32_t address) {if(!h->fault){h->fault=CLAW_FAULT_HOST;h->faultAddress=address;}}
    extern "C" uint32_t menu_fault_address(ClawHost *h) {return h->faultAddress;}
    extern "C" uint32_t menu_fault_code(ClawHost *h) {return h->fault;}
    extern "C" uint32_t menu_run(ClawHost *h,uint32_t f,uint32_t receiver,const uint32_t *args,uint32_t n,uint32_t stack,ClawSourceContext *source,uint32_t returnPC,uint32_t *out) {
        auto previous=h->entryStackPointer;h->entryStackPointer=stack;
        auto priorSource=h->sourceContext;auto priorReturn=h->sourceReturnPC;
        h->sourceContext=source;h->sourceReturnPC=returnPC;
        ClawEntry entry=nullptr;
        switch(f) {
    '''
    code+='\n'.join(f'case 0x{a:x}: entry={s};break;' for a,s in sorted(rows.items()))
    code+='''default:menu_fault(h,f);break;
        }
        uint32_t done=entry ? entry(f,receiver,args,n,h,out):0;
        h->entryStackPointer=previous;h->sourceContext=priorSource;h->sourceReturnPC=priorReturn;return done;
    }\n'''
    compiler=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    digest=hashlib.sha256(code.encode())
    for path in sorted(sources|{'Sources/ClawRuntime.h','Sources/ClawRuntime.hpp'}):
        digest.update(path.encode());digest.update((ROOT/path).read_bytes())
    digest.update(subprocess.check_output([compiler,'--version']));digest.update(sdk.encode())
    target=ROOT/'work/build'/cache/digest.hexdigest()[:24]
    target.mkdir(parents=True,exist_ok=True)
    library=target/'level-one.dylib'
    if not library.exists():
        bridge=target/'bridge.cpp';bridge.write_text(code)
        objects=[]
        for source in sorted(s for s in sources if s.endswith('.cpp')):
            obj=target/(source.replace('/','_')+'.o')
            if not obj.exists():
                subprocess.run(['nice','-n','10',compiler,'-std=c++17','-O1','-isysroot',sdk,'-c','-I'+str(ROOT/'Sources'),
                                str(ROOT/source),'-o',str(obj)],check=True)
            objects.append(str(obj))
        subprocess.run([compiler,'-std=c++17','-O1','-isysroot',sdk,'-dynamiclib','-I'+str(ROOT/'Sources'),
                        str(bridge),*objects,'-o',str(library)],check=True)
    (work/'owners.json').write_text(json.dumps(dict(unresolved=unresolved,
        owners={hex(a):s['id'] for a,s in sorted(owners.items()) if a not in tail_only},
        tail_thunks={hex(a):hex(d) for a,d in sorted(thunks.items())},
        tail_only={hex(a):owners[a]['id'] for a in sorted(tail_only)}),indent=2)+'\n')
    return C.CDLL(str(library)),metadata


def data_words(cache=[]):
    """Every aligned dword in the original non-code sections (vtables, tables)."""
    if not cache:
        import struct
        from Tests.clawparity.program import claw
        words=set()
        for section in claw().sections:
            if section.name=='.text':continue
            data=bytes(section.data)
            words.update(struct.unpack_from('<%dI'%(len(data)//4),data))
        cache.append(words)
    return cache[0]


def vtable_tail_slot(address, cache={}):
    """Vtable displacement of an original MOV r,[ECX]; JMP [r+d] thunk, else None."""
    if address in cache:return cache[address]
    import capstone
    from Tests.clawparity.program import claw
    if 'text' not in cache:
        cache['text']=next(s for s in claw().sections if s.name=='.text')
        cache['cs']=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    code=cache['text'];slot=None
    if code.address<=address<code.address+len(code.data):
        pair=list(cache['cs'].disasm(code.data[address-code.address:address-code.address+12],address,2))
        if len(pair)==2 and pair[0].mnemonic=='mov' and pair[1].mnemonic=='jmp':
            first=re.fullmatch(r'(e[a-d]x), dword ptr \[ecx\]',pair[0].op_str)
            second=re.fullmatch(r'dword ptr \[(e[a-d]x) \+ (0x[0-9a-f]+)\]',pair[1].op_str)
            if first and second and first.group(1)==second.group(1):slot=int(second.group(2),16)
    cache[address]=slot
    return slot


class Disposition(C.Structure):
    _fields_=[(name,C.c_uint32) for name in ('size','version','disposition','caller','site','target',
                                             'entry_stack','return_pc')]+[('request',C.c_void_p)]


def original_frame_extent(program, address, cache={}):
    """Bytes the original function reserves below its entry ESP.

    Read from the unchanged prologue: pushes, SEH registration and the
    SUB ESP (or __chkstk) size. Native callees without an explicit ESP get
    a disjoint frame below this extent, so they never overlap the caller's
    live automatic storage (for example 0x4d17e0's 0x43c-byte buffer).
    """
    if address in cache:return cache[address]
    import capstone
    code=next(s for s in program.sections if s.name=='.text')
    disassembler=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    extent,pending=0,None
    for count,instruction in enumerate(disassembler.disasm(code.data[address-code.address:address-code.address+0x60],address)):
        if count>=24 or instruction.mnemonic in ('ret','jmp') or instruction.mnemonic.startswith('j'):break
        operands=instruction.op_str
        if instruction.mnemonic=='push':extent+=4
        elif instruction.mnemonic=='sub' and operands.startswith('esp, '):extent+=int(operands[5:],0)
        elif instruction.mnemonic=='mov' and operands.startswith('eax, 0x'):pending=int(operands[5:],0)
        elif instruction.mnemonic=='call':
            if pending is not None and instruction.op_str=='0x4a3ae0':extent+=pending
            break
    cache[address]=extent
    return extent


class LevelOneNativeJoin(NativeJoin, LevelOneTrace):
    """Original Level 1 tracer orchestration with every game entry native."""
    def __init__(self, library, entries, startup_paper=False, **options):
        NativeJoin.__init__(self,library,entries,**options)
        self.startup_paper=startup_paper
        self.clock_step=1 if startup_paper else 0
        self.stop=None
        self.error_stack=None
        self.x87_steps=Counter()
        self.x87_balanced=Counter()
        self.x87_returned=Counter()
        self.x87_discarded=Counter()
        self.x87_environments=Counter()
        self.x87_transport_paths=Counter()
        self.loot_x87_transports=[]
        # The native startup environment; ordinary admitted environment calls
        # inherit the preceding publication. Exact edges supply their own live
        # packet instead, never a parent's unpublished ENTRY snapshot.
        self.x87_ambient=X87(size=C.sizeof(X87),version=1,control=0x023f)
        self.source_ordinary_calls=Counter()
        # The Level 1 heap extension is contiguous with the menu heap in the
        # original address space; give native spans that cross it one buffer.
        self.machine.coalesce()
        library.menu_fault_code.argtypes=[C.c_void_p]

    def player_snapshot(self, application):
        """Original snapshot fields; a treasure pickup is observed natively as
        an increment of the player's own counters (private+0x88..+0xac)."""
        snapshot=LevelOneTrace.player_snapshot(self,application)
        counts=snapshot['treasure_counts']
        before=getattr(self,'native_counts_seen',None)
        if before is not None and sum(counts)>sum(before) and self.phase.startswith('play-'):
            self.pickup_events.append(dict(phase=self.phase,milliseconds=self.milliseconds,
                score=snapshot['score'],before=before,after=counts,increment=sum(counts)-sum(before),
                observed='native player treasure counters'))
        self.native_counts_seen=counts
        return snapshot

    def child_stack(self):
        """Disjoint automatic frame for an untracked callee of the innermost native entry."""
        caller=self.native_functions[-1]
        gap=max(0x400,(original_frame_extent(self.program,caller)+0x4f)&~0xf)
        return self.native_frames[-1]-gap

    def service(self, unused, pointer):
        q=pointer.contents
        caller=self.native_functions[-1] if self.native_functions else 0
        if q.function==0x43d490 and q.source and not q.x87_count:
            try:
                if (q.count!=1 or any(q.arguments[1:]) or not q.stack
                        or any(getattr(q,name) for name in ('receiver2','x87_argument','compiler',
                            'transfer_version','transfer_kind','transfer_site','caller','disposition',
                            'x87_state','x87_operation','callback_cpu','callback_activation'))):
                    raise Blocked('Malformed base dispatch source environment request')
            except Exception as error:
                if self.native_error is None:self.native_error=str(error)
                if self.error_stack is None:self.error_stack=[hex(a) for a in self.native_functions]+[hex(q.function)]
                self.library.menu_fault(self.host,q.function)
                return 0
        if (not q.x87_count and getattr(self,'x87_frames',None)
                and self.entries.get(q.function,{}).get('x87_environment') is not None):
            try:
                entry=self.entries[q.function]
                if (q.count!=entry.get('argc') or any(q.arguments[q.count:])
                        or any(getattr(q,field) for field in ('receiver2','stack','source','return_pc',
                            'x87_argument','compiler','transfer_version','transfer_kind','transfer_site',
                            'caller','disposition','x87_state','x87_operation','callback_cpu','callback_activation'))):
                    raise Blocked(f'Malformed ordinary x87 environment request {q.function:#x}')
            except Exception as error:
                if self.native_error is None:self.native_error=str(error)
                if self.error_stack is None:self.error_stack=[hex(a) for a in self.native_functions]+[hex(q.function)]
                self.library.menu_fault(self.host,q.function)
                return 0
        rope_x87=(caller,q.function)==(0x4181c0,0x420dd0)
        if rope_x87:
            try:
                validate_rope_x87_call(q,caller,self.entries.get(q.function,{}))
            except Blocked as error:
                if self.native_error is None:self.native_error=str(error)
                if self.error_stack is None:self.error_stack=[hex(a) for a in self.native_functions]+[hex(q.function)]
                self.library.menu_fault(self.host,q.function)
                return 0
        if self.entries.get(q.function,{}).get('tail_only'):
            # A tail-only owner runs only as the vtable target of the innermost
            # elected thunk, read from the receiver's own vtable.
            thunk=self.native_functions[-1] if self.native_functions else 0
            slot=vtable_tail_slot(thunk)
            if (slot is None or q.count or q.source or q.x87_count or q.compiler or q.transfer_version
                    or self.word(self.word(q.receiver)+slot)!=q.function):
                if self.native_error is None:self.native_error=f'Missing native game owner {q.function:#x}'
                self.library.menu_fault(self.host,q.function)
                return 0
        if not q.stack and not q.source and self.native_frames and not q.x87_count:
            # Publish the explicit disjoint frame instead of the base probe's
            # fixed 0x400 gap; the module's request is copied, never edited.
            framed=Call.from_buffer_copy(q)
            framed.stack=self.child_stack()
            pointer=C.pointer(framed);q=framed
        if q.function==0x4d5fe0:
            return self.uncompress(q)
        if (not q.x87_count and q.function in self.entries
                and self.entries[q.function].get('returns')=='x87'):
            try:
                caller=self.native_functions[-1] if self.native_functions else 0
                if (not (rope_x87 or (caller,q.function) in X87_DISCARD) or q.compiler or q.transfer_version
                        or q.callback_cpu or q.x87_state):
                    raise Blocked(f'Ordinary call into x87-result owner {q.function:#x} from {caller:#x}')
                empty=X87();empty.size=C.sizeof(X87);empty.version=1;empty.control=0x023f
                empty.push=1
                value=self.owned_x87_result(q,empty)
                self.x87_discarded[(caller,q.function)]+=1
                return value
            except Exception as error:
                if self.native_error is None:self.native_error=str(error)
                if self.error_stack is None:self.error_stack=[hex(a) for a in self.native_functions]+[hex(q.function)]
                self.library.menu_fault(self.host,q.function)
                return 0
        if (q.function in self.entries and self.is_game(q.function) and not game(q.function)
                and not (q.x87_count or q.compiler or q.transfer_version or q.callback_cpu)):
            # Reviewed game-owned spatial-grid bodies inside the CRT/MFC range.
            try:
                return self.invoke(q.function,q.receiver,list(q.arguments[:q.count]),
                                   q.stack or self.child_stack(),q.source,q.return_pc)
            except Exception as error:
                if self.native_error is None:self.native_error=str(error)
                if self.error_stack is None:self.error_stack=[hex(a) for a in self.native_functions]+[hex(q.function)]
                self.library.menu_fault(self.host,q.function)
                return 0
        if not (q.transfer_version or q.transfer_kind or q.transfer_site or q.caller or q.disposition):
            value=NativeJoin.service(self,unused,pointer)
            if self.native_error and self.error_stack is None:
                self.error_stack=[hex(a) for a in self.native_functions]+[hex(q.function)]
            return value
        try:
            # Explicit zero-argument source tail JMP: the target runs on the
            # caller's frame and returns to the caller's own continuation.
            if (q.transfer_version!=1 or q.transfer_kind!=1 or not q.disposition or not q.source
                    or q.count or q.compiler or q.callback_cpu or not q.return_pc):
                raise Blocked(f'Unelected contextual native boundary {q.function:#x}')
            cpu=Source.from_address(q.source)
            entry_stack=cpu.esp
            if entry_stack!=q.stack or self.word(entry_stack)!=q.return_pc:
                raise Blocked(f'Invalid native tail frame into {q.function:#x}')
            if self.is_game(q.function):
                if q.function not in self.entries:
                    raise Blocked(f'Missing native tail owner {q.function:#x}')
                result=self.invoke(q.function,q.receiver,[],entry_stack,q.source,q.return_pc)
            else:
                # Physical stand-in reached by a tail JMP: same frame, same
                # continuation, served as an ordinary source call would be.
                plain=Call(function=q.function,receiver=q.receiver,receiver2=q.receiver2,count=0,
                           stack=entry_stack,source=q.source,return_pc=q.return_pc)
                result=NativeJoin.service(self,unused,C.pointer(plain))
                if self.native_error:raise Blocked(self.native_error)
            if cpu.eip!=q.return_pc or cpu.esp!=entry_stack+4:
                raise Blocked(f'Native tail {q.function:#x} did not return to its continuation')
            receipt=Disposition.from_address(q.disposition)
            receipt.size=C.sizeof(Disposition);receipt.version=1;receipt.disposition=1
            receipt.caller=q.caller;receipt.site=q.transfer_site;receipt.target=q.function
            receipt.entry_stack=entry_stack;receipt.return_pc=q.return_pc
            receipt.request=C.addressof(q)
            return result
        except Exception as error:
            if self.native_error is None:self.native_error=str(error)
            self.library.menu_fault(self.host,q.function)
            return 0

    def math_service(self, q):
        if q.x87_count in (4,5):
            return self.x87_outer(q)
        if q.x87_count==2 and q.function in self.entries and self.is_game(q.function):
            return self.exact_game_call(q)
        if q.x87_count!=3:
            return NativeJoin.math_service(self,q)
        # Exact x87 primitive: the comparison harness's isolated arithmetic
        # interpreter (no guest code, no shared memory, no host doubles).
        from types import SimpleNamespace
        from Tests.clawparity.kernel import Machine, X87_STEPS
        if q.function or q.receiver or q.source or not q.x87_state or q.x87_operation not in X87_STEPS:
            raise Blocked(f'Malformed native x87 primitive {q.x87_operation}')
        code,argc,pop,push,minimum,stores=X87_STEPS[q.x87_operation]
        state=X87.from_address(q.x87_state)
        if (state.control!=0x023f or q.count!=argc or state.count<minimum or state.count-pop+push>8
                or state.pop!=pop or state.push!=push or state.returned):
            raise Blocked(f'Invalid native x87 primitive operands {q.x87_operation}')
        if not hasattr(self,'arithmetic'):self.arithmetic=SimpleNamespace()
        before=tuple((v.significand,v.exponent) for v in state.slots[:state.count])
        control,status,slots=Machine.x87_step(self.arithmetic,q.x87_operation,(state.control,state.status,before),
                                              tuple(q.arguments[:q.count]))
        if (control!=state.control or len(slots)!=state.count-pop+push or slots[push:]!=before[pop:]
                or (status>>11)&7!=(((state.status>>11)+pop-push)&7)):
            raise Blocked('x87 primitive violated its stack contract')
        state.status,state.count=status,len(slots)
        for i in range(8):
            state.slots[i].significand,state.slots[i].exponent,state.slots[i].reserved=(slots[i] if i<len(slots) else (0,0))+(0,)
        stored=self.arithmetic.x87_stored if stores else 0
        state.eax,state.edx=stored&0xffffffff,stored>>32
        state.returned=1
        self.x87_steps[q.x87_operation]+=1
        return state.eax

    def exact_game_call(self, q):
        """Exact x87 transport into an admitted ordinary owner.

        A balanced boundary (pop 0, push 0) keeps the caller's live x87 stack
        across the call; an ordinary owner neither reads nor changes it.
        Owned x87 results (push 1) need the ENTRY/RESULT protocol instead.
        """
        if not q.x87_state:
            raise Blocked('Missing exact x87 state')
        state=X87.from_address(q.x87_state)
        self.validate_x87_state(state)
        metadata=self.entries[q.function]
        if state.returned or state.eax or state.edx or state.count>8:
            raise Blocked(f'Invalid exact x87 state into {q.function:#x}')
        if metadata.get('x87_environment') is not None:
            return self.environment_call(q,state)
        if (state.pop,state.push)==(0,1) and metadata.get('returns')=='x87' and state.count<8:
            return self.owned_x87_result(q,state)
        if (state.pop,state.push)!=(0,0) or metadata.get('returns')=='x87':
            raise Blocked(f'Owned x87 result transport required for {q.function:#x} '
                          f'(pop {state.pop}, push {state.push}, returns {metadata.get("returns")})')
        before=bytes(state)
        stack=q.stack or self.child_stack()
        scope=None
        if q.function==0x44d000:
            if self.native_functions[-1:]!=[0x460af0]:
                raise Blocked('Unelected exact base-update environment caller')
            parent=self.x87_frames[-1] if getattr(self,'x87_frames',None) else None
            if (parent is None or parent['function']!=0x460af0 or not parent['entered']
                    or parent['result'] is not None):
                raise Blocked('Missing active Mercat environment frame')
            if ((metadata.get('convention'),metadata.get('argc'),metadata.get('returns'))!=('thiscall',1,'void')
                    or q.x87_count!=2 or q.count!=1 or any(q.arguments[1:])
                    or any(getattr(q,name) for name in ('receiver2','source','return_pc',
                        'compiler','transfer_version','transfer_kind','transfer_site','caller',
                        'disposition','callback_cpu','callback_activation','x87_operation','x87_argument'))):
                raise Blocked('Malformed Mercat exact base-update environment request')
            scope=dict(function=q.function,caller=X87.from_buffer_copy(state),entered=True,
                       result=None,push=0,exact_scope=True,ordinary_cursor=X87.from_buffer_copy(state))
            self.x87_frames.append(scope)
        try:
            result=self.invoke(q.function,q.receiver,list(q.arguments[:q.count]),stack,q.source,q.return_pc)
        finally:
            if scope is not None:self.x87_frames.pop()
        if bytes(state)!=before:
            raise Blocked(f'Balanced x87 owner {q.function:#x} changed the caller x87 state')
        if scope is not None and scope.get('ordinary_cursor_used'):
            cursor=scope['ordinary_cursor']
            self.validate_x87_state(cursor)
            if (cursor.control!=state.control or cursor.count!=state.count
                    or (cursor.status^state.status)&0x3800 or bytes(cursor.slots)!=bytes(state.slots)):
                raise Blocked('Mercat base-update corrupted the exact environment')
            state.status=cursor.status
        state.returned=1;state.eax=result;state.edx=0
        self.x87_balanced[q.function]+=1
        return result

    def owned_x87_result(self, q, state):
        """Owned x87 result (pop 0, push 1) through the ENTRY/RESULT protocol.

        The same contract as claw_canonical_x87_invoke: the owner reads the
        caller's exact stack once through ENTRY and publishes it plus one
        pushed ST(0) once through RESULT; lower slots and CW must be intact.
        """
        caller=X87.from_buffer_copy(state)
        frame=dict(function=q.function,caller=caller,entered=False,result=None,push=1)
        if not hasattr(self,'x87_frames'):self.x87_frames=[]
        self.x87_frames.append(frame)
        try:
            stack=q.stack or self.child_stack()
            result=self.invoke(q.function,q.receiver,list(q.arguments[:q.count]),stack,q.source,q.return_pc)
        finally:
            self.x87_frames.pop()
        if self.native_error:raise Blocked(self.native_error)
        published=frame['result']
        if published is None:
            raise Blocked(f'Owned x87 owner {q.function:#x} returned without publishing ST(0)')
        C.memmove(C.addressof(state),C.addressof(published),C.sizeof(X87))
        state.pop,state.push,state.returned,state.eax,state.edx=0,1,1,result,0
        self.x87_returned[q.function]+=1
        return result

    def x87_outer(self, q):
        frame=self.x87_frames[-1] if getattr(self,'x87_frames',None) else None
        if (frame is None or q.x87_count not in (4,5) or q.function!=frame['function']
                or self.native_functions[-1:]!=[q.function] or q.receiver or q.receiver2 or q.count
                or q.stack or q.x87_operation or not q.x87_state or frame['result'] is not None
                or any(getattr(q, field) for field in ('source','compiler','return_pc','transfer_version',
                    'transfer_kind','transfer_site','caller','disposition','callback_cpu','callback_activation',
                    'x87_argument')) or any(q.arguments)):
            raise Blocked(f'Unelected x87 entry/result request from {q.function:#x}')
        state=X87.from_address(q.x87_state)
        caller=frame['caller']
        if q.x87_count==4:
            empty=X87();empty.size=C.sizeof(X87);empty.version=1
            if frame['entered'] or bytes(state)!=bytes(empty):
                raise Blocked(f'Invalid x87 ENTRY request from {q.function:#x}')
            C.memmove(C.addressof(state),C.addressof(caller),C.sizeof(X87))
            state.pop=state.push=0;state.returned=1;state.eax=state.edx=0
            frame['entered']=True
            return 0
        self.validate_x87_state(state)
        push=frame['push']
        if (not frame['entered'] or state.pop or state.push!=push or state.returned or state.eax or state.edx
                or state.control!=caller.control or state.count!=caller.count+push
                or (state.status>>11)&7!=((caller.status>>11)-push)&7
                or any(bytes(state.slots[i+push])!=bytes(caller.slots[i]) for i in range(caller.count))):
            raise Blocked(f'Invalid x87 RESULT publication from {q.function:#x}')
        published=X87.from_buffer_copy(state)
        if frame.get('ordinary_cursor_used'):
            # These elected wrappers perform no local floating operations.
            # Their by-value native packet must remain the exact ENTRY state.
            # Compose the checked child environment in host-owned storage;
            # never retain ENTRY's temporary address or mutate RESULT's packet.
            cursor=frame['ordinary_cursor']
            self.validate_x87_state(cursor)
            if (bytes(state)!=bytes(caller) or cursor.control!=state.control
                    or cursor.count!=state.count or (cursor.status^state.status)&0x3800
                    or bytes(cursor.slots)!=bytes(state.slots)):
                raise Blocked(f'Changed pass-through x87 RESULT from {q.function:#x}')
            published.status=cursor.status
        frame['result']=published
        state.returned=1
        return 0

    @staticmethod
    def validate_x87_state(state):
        if (state.size!=C.sizeof(X87) or state.version!=1 or state.control!=0x023f
                or state.status>0xffff or state.count>8 or state.reserved0 or state.reserved1
                or any(v.reserved or v.exponent>0xffff for v in state.slots)
                or any(v.significand or v.exponent for v in state.slots[state.count:])):
            raise Blocked('Malformed native x87 environment')

    def environment_call(self, q, state):
        """An admitted u32/void owner may change SW without producing ST(0).

        ENTRY borrows the incoming environment; RESULT must preserve CW, TOP
        and every live slot. Status condition/exception bits come from the body.
        Only reviewed pass-through branches may compose a host-owned cursor
        with a nested ordinary child's checked post-callee environment.
        """
        metadata=self.entries[q.function]
        self.validate_x87_state(state)
        effect=metadata.get('x87_environment')
        if (effect!={'pop':0,'push':0} or any(type(v) is not int for v in effect.values())
                or metadata.get('returns')=='x87' or q.x87_count not in (0,2) or state.pop or state.push
                or state.returned or state.eax or state.edx
                or q.count!=metadata.get('argc') or metadata.get('convention') not in ('cdecl','stdcall','thiscall')
                or (metadata['convention']!='thiscall' and q.receiver)
                or any(getattr(q, field) for field in ('receiver2','source','compiler','return_pc',
                    'transfer_version','transfer_kind','transfer_site','caller','disposition',
                    'callback_cpu','callback_activation','x87_operation','x87_argument'))):
            raise Blocked(f'Unelected x87 environment boundary {q.function:#x}')
        frame=dict(function=q.function,caller=X87.from_buffer_copy(state),entered=False,result=None,push=0)
        passthrough=False
        if q.function==0x4dc830:
            logic=self.word(self.word(q.arguments[0]+0x6c)+0x18)
            vtable=self.word(logic)
            target=self.word(vtable+0x14)
            # Original Red Tail fallback 0x483cf4 -> 0x44df60 and death
            # override 0x483e2e -> 0x44e0c0 contain no floating operations.
            # Check both actual virtual targets, rather than just the path.
            passthrough=(target==0x44df60 or
                         # Original 0x434050 and its +0xa8 override 0x433ed0
                         # are integer-only, then 0x42df90 constructs loot.
                         target==0x434050 and self.word(vtable+0xa8)==0x433ed0 or
                         target==0x483ae0 and self.word(vtable+0x5c)==0x483e10)
        elif q.function==0x4063b0 and not self.word(q.receiver+0x14):
            passthrough=self.word(self.word(q.receiver)+0x24)==0x40f2a0
        if passthrough:
            # 0x4dc830 is a single virtual CALL followed by return 1.
            # The no-tracked-callback branch of 0x4063b0 is a terminal virtual
            # CALL. Only the finite ordinary loot paths may use this cursor.
            frame['ordinary_cursor']=X87.from_buffer_copy(state)
        if not hasattr(self,'x87_frames'):self.x87_frames=[]
        self.x87_frames.append(frame)
        try:
            result=self._invoke(q.function,q.receiver,list(q.arguments[:q.count]),q.stack or self.child_stack())
        finally:
            self.x87_frames.pop()
        if self.native_error:raise Blocked(self.native_error)
        published=frame['result']
        if published is None:
            raise Blocked(f'x87 environment owner {q.function:#x} returned without publication')
        C.memmove(C.addressof(state),C.addressof(published),C.sizeof(X87))
        state.returned,state.eax,state.edx=1,result,0
        self.x87_environments[q.function]+=1
        return result

    def uncompress(self, q):
        """Native zlib for the original's statically linked uncompress."""
        try:
            if q.count!=4 or q.receiver or q.source or q.compiler or q.transfer_version:
                raise Blocked('Invalid native uncompress ABI')
            destination,size_pointer,source,length=q.arguments[:4]
            capacity=self.word(size_pointer)
            block=next(((a,n) for a,n in self.allocations.items() if a<=source<a+max(n,1)),None)
            if block is None:raise Blocked('Native uncompress source outside owned buffers')
            available=min(length,block[0]+block[1]-source)
            data=self.machine.mem_read(source,available)
            decoder=zlib.decompressobj()
            try:
                output=decoder.decompress(data,capacity)
            except zlib.error:
                result=0xfffffffd
            else:
                result=0 if decoder.eof else 0xfffffffb
                self.machine.mem_write(destination,output)
                self.put(size_pointer,len(output))
            self.physical_events.append(dict(service='native zlib uncompress',phase=self.phase,
                capacity=capacity,advertised=length,available=available,result=result))
            return result
        except Exception as error:
            if self.native_error is None:self.native_error=str(error)
            self.library.menu_fault(self.host,q.function)
            return 0

    def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        if self.entries.get(address,{}).get('x87_environment') is not None:
            if (source and address==0x43d490
                    and self.native_functions[-1:]==[0x44c840]):
                # Base dispatch's source CALL at 0x44c945 uses the existing
                # checked source/frame provider before electing an environment.
                # Its continuation and original argument words must agree.
                cpu=Source.from_address(source)
                if (return_pc!=0x44c94a or cpu.size!=C.sizeof(Source) or cpu.version!=1
                        or (cpu.input_mask,cpu.output_mask,cpu.preserve_mask)!=(0x7ff,0x7ff,0x472)
                        or cpu.eip!=address or cpu.reserved0 or cpu.reserved1):
                    raise Blocked('Unelected base dispatch source continuation')
                return self.source_ordinary(address,receiver,arguments,stack,source,return_pc)
            frames=getattr(self,'x87_frames',None)
            live=None
            if frames:
                frame=frames[-1]
                paths=({EXACT_ENV_PATH} if frame.get('exact_scope') else LOOT_X87_PATHS)
                path=next((path for path in paths
                           if path[-1]==address and tuple(self.native_functions[-len(path)+1:])==path[:-1]),None)
                if (path is not None and frame['function']==path[0] and frame['entered']
                        and frame['result'] is None and frame.get('ordinary_cursor') is not None):
                    live=frame['ordinary_cursor']
            if source or return_pc or (frames and live is None):
                raise Blocked(f'Explicit x87 environment transport required for {address:#x}')
            incoming=X87.from_buffer_copy(live if live is not None else self.x87_ambient)
            incoming.pop=incoming.push=incoming.returned=incoming.eax=incoming.edx=0
            before=(incoming.control,incoming.status,incoming.count)
            request=Call(function=address,receiver=receiver,count=len(arguments),stack=stack)
            for i,value in enumerate(arguments):request.arguments[i]=value
            result=self.environment_call(request,incoming)
            if live is not None:
                # Copy architectural state, retaining the enclosing packet's
                # own protocol flags and return registers.
                live.control,live.status,live.count=incoming.control,incoming.status,incoming.count
                C.memmove(C.addressof(live.slots),C.addressof(incoming.slots),C.sizeof(live.slots))
                frame['ordinary_cursor_used']=True
                if not hasattr(self,'x87_transport_paths'):self.x87_transport_paths=Counter()
                self.x87_transport_paths[path]+=1
                if not hasattr(self,'loot_x87_transports'):self.loot_x87_transports=[]
                if len(self.loot_x87_transports)<32:
                    self.loot_x87_transports.append(dict(path=[hex(a) for a in path],
                        phase=getattr(self,'phase',''),milliseconds=getattr(self,'milliseconds',None),
                        incoming=before,final=(incoming.control,incoming.status,incoming.count)))
            self.x87_ambient=X87.from_buffer_copy(incoming)
            return result
        return self._invoke(address,receiver,arguments,stack,source,return_pc)

    def _invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        contract=self.entries.get(address,{}).get('source_context')
        if source and not contract and address in self.entries and game(address):
            return self.source_ordinary(address,receiver,arguments,stack,source,return_pc)
        if source and contract:
            caller=Source.from_address(source)
            masks=(contract['input_mask'],contract['output_mask'],contract['preserve_mask'])
            if (caller.input_mask,caller.output_mask,caller.preserve_mask)!=masks:
                # A caller's ordinary source edge may claim less than the
                # admitted callee guarantees. Narrow it explicitly: the callee
                # needs only supplied inputs, writes only what the caller
                # accepts, and preserves everything the caller relies on.
                if (masks[0]&~caller.input_mask or masks[1]&~caller.output_mask
                        or caller.preserve_mask&~masks[2]):
                    raise Blocked(f'Incompatible source edge into {address:#x}: caller '
                                  f'{caller.input_mask:#x}/{caller.output_mask:#x}/{caller.preserve_mask:#x}, callee '
                                  + '/'.join(hex(m) for m in masks))
                adapted=Source.from_buffer_copy(caller)
                adapted.input_mask,adapted.output_mask,adapted.preserve_mask=masks
                try:
                    return self.invoke(address,receiver,arguments,stack,C.addressof(adapted),return_pc)
                finally:
                    for name,_ in Source._fields_[4:15]:setattr(caller,name,getattr(adapted,name))
        if source is None and not contract:
            # Ordinary entries may read their own stack arguments through the
            # original frame (for example 0x426e30 reads LPARAM at ESP+0xc).
            # Publish the frame a real CALL would have built; a root call also
            # receives the harness return word, as the original run does.
            if not self.native_frames:self.put(stack,menu.reference.STOP)
            for index,value in enumerate(arguments):self.put(stack+4*(index+1),value)
        try:
            return NativeJoin.invoke(self,address,receiver,arguments,stack,source,return_pc)
        except Blocked as error:
            if 'Native source fault' in str(error) and 'code' not in str(error):
                raise Blocked(f'{error} (code {self.library.menu_fault_code(self.host)})') from None
            raise

    def source_ordinary(self, address, receiver, arguments, stack, source, return_pc):
        """Ordinary owner reached by a source CALL (for example a logic-state
        dispatcher's indirect call into an ordinary state body): run it
        without the context, then return to the caller's continuation. Same
        conditions as claw_level_ordinary_source_ok in
        Sources/ClawNativeLevelTransport.cpp ("source-ordinary")."""
        entry=self.entries[address]
        cpu=Source.from_address(source)
        convention,argc=entry.get('convention'),entry.get('argc')
        if (entry.get('returns')=='x87' or convention not in ('cdecl','stdcall','thiscall')
                or len(arguments)!=argc or cpu.esp!=stack or not return_pc or self.word(stack)!=return_pc
                or cpu.preserve_mask&~SOURCE_PRESERVABLE
                or (cpu.ecx!=receiver if convention=='thiscall' else receiver!=0)
                or any(self.word(stack+4*(i+1))!=value for i,value in enumerate(arguments))):
            raise Blocked(f'Unelected source-ordinary edge into {address:#x}')
        value=self.invoke(address,receiver,arguments,stack)
        cpu.eax=value;cpu.eip=return_pc
        cpu.esp+=4+(0 if convention=='cdecl' else 4*argc)
        self.source_ordinary_calls[address]+=1
        return value

    def run(self, address, receiver, arguments=(), phase='', boundary=None, stack=STACK):
        if phase=='menu-text-static-initialization':
            if self.word(0x522000) or self.word(0x522244):
                raise Blocked('Original static initializer table sentinel mismatch')
            for slot in range(0x522004,0x522244,4):
                entry=self.word(slot)
                if entry==0x4251e0:continue
                if game(entry):NativeJoin.run(self,entry,0,phase=f'game-static-{entry:06x}')
            return 0
        if boundary is not None and (address,boundary) in INLINE:
            self.phase=phase
            def physical(function,target,args=()):
                call=Call(function=function,receiver=target,count=len(args),stack=stack-0x100)
                for i,value in enumerate(args):call.arguments[i]=value
                value=self.service(None,C.pointer(call))
                if self.native_error:raise Blocked(self.native_error)
                return value
            if address==0x42614c:
                physical(0x4f5249,receiver,[10]);physical(0x4f6439,receiver+0x1c)
                self.put(receiver+0x30,0);self.put(receiver+0x34,0)
            elif address==0x4262c4:
                physical(0x4f5133,receiver+8,[10]);self.put(receiver,0);self.put(receiver+4,0x64)
            else:
                physical(0x4f5cbd,receiver+4,[10]);self.put(receiver,0)
                self.machine.mem_write(receiver+0x20,b'\0')
                for offset in (0x120,0x124,0x128):self.put(receiver+offset,0)
            self.paused=True
            return receiver
        if not phase.startswith('play-'):
            print(json.dumps(dict(event='phase',phase=phase)),flush=True)
        return NativeJoin.run(self,address,receiver,arguments,phase,boundary,stack)

    def execute(self):
        # Native ordering: startup services exist before the mode-5 factory
        # runs, so the factory is never suspended. The original comparison
        # run uses this same ordering under the emulator. Native startup owns
        # an empty structured-exception chain, as the original tracer does.
        self.put(0,0xffffffff)
        self.run(0x45acb0,0,phase='menu-text-static-initialization')
        self.setup_version()
        application=self.allocate(0x134)
        self.run(0x4254a0,application,phase='application-construction')
        scene=self.allocate(0x3c)
        self.run(0x4ce960,scene,phase='scene-construction')
        if not self.run(0x4cea10,scene,(1,640,480,8,0),phase='scene-initialization'):
            raise Blocked('Native scene initialization failed')
        self.setup_resources(application,scene)
        if not self.run(0x428c40,application,(5,1,1,0),phase='menu-initialization'):
            raise Blocked('Native menu initialization failed')
        LevelOneTrace.execute_frames(self,application)


SEMANTIC=('x','y','health','score','player_state','logic_state','treasure_counts','input_mask','game_ms','level','vtable')


def compare(native_frames, native_pickups, original=None):
    """Semantic original/native comparison at every play frame boundary.

    Heap addresses differ (native zlib allocations), so object identities are
    not compared; every recorded player value and the scripted action are.
    """
    original=original or json.loads((ROOT/'work/level-one-map/trace.json').read_text())
    frames=original['play_frames']
    divergence=None
    for index,(a,b) in enumerate(zip(frames,native_frames)):
        fields=[k for k in SEMANTIC if a['player'].get(k)!=b['player'].get(k)]
        if a['elapsed_ms']!=b['elapsed_ms'] or a['action']!=b['action'] or fields:
            divergence=dict(frame=index,elapsed_ms=a['elapsed_ms'],action=a['action'],
                fields={k:[a['player'].get(k),b['player'].get(k)] for k in fields})
            break
    if divergence is None and len(frames)!=len(native_frames):
        divergence=dict(frame=min(len(frames),len(native_frames)),reason='frame count',
                        original=len(frames),native=len(native_frames))
    # The original records the pickup at the counter call; the native side at
    # the next frame boundary. Compare the observable effect: increment,
    # counters and the frame at which it becomes visible.
    def visible(frames):
        return [dict(frame=i,after=f['player']['treasure_counts'],score=f['player']['score'])
                for i,f in enumerate(frames[1:],1)
                if sum(f['player']['treasure_counts'])>sum(frames[i-1]['player']['treasure_counts'])]
    original_pickups,native_visible=visible(frames),visible(native_frames)
    pickups_match=bool(original_pickups) and original_pickups==native_visible and len(native_pickups)==len(native_visible)
    return dict(frames=len(native_frames),original_frames=len(frames),divergence=divergence,
                original_pickups=original_pickups,native_pickups=native_visible,pickups_match=pickups_match,
                passed=divergence is None and pickups_match and original.get('treasure_pickup_observed') is True)


def run_controls(library, entries, original):
    """Negative controls: each must fail, never produce a passing comparison."""
    results={}
    controls=(('missing-play-owner',dict(deny_owner=0x462350),'deliberately withheld'),
              ('missing-collision-owner',dict(deny_owner=0x4cbff0),'deliberately withheld'),
              ('missing-random-service',dict(deny_platform=0x4a3050),'deliberately withheld'),
              ('missing-archive',dict(missing_resource=True),None))
    for name,options,expected in controls:
        probe=LevelOneNativeJoin(library,entries,startup_paper=original.get('startup_paper',False),**options)
        try:
            probe.execute()
        except Blocked as error:
            message=probe.native_error or str(error)
            if expected and expected not in message:
                raise Blocked(f'{name} failed for the wrong reason: {message}')
            results[name]=dict(result='refused',error=message,phase=probe.phase)
        else:
            raise Blocked(f'{name} incorrectly completed Level 1')
        finally:
            probe.close()
    # Comparator controls: a perturbed native record must be rejected.
    reference=json.loads((WORK/'result.json').read_text())
    for name,mutate in (('perturbed-position',lambda f:f[400]['player'].__setitem__('x',f[400]['player']['x']+1)),
                        ('lost-pickup',lambda f:[x['player'].__setitem__('treasure_counts',[0]*10) for x in f])):
        frames=json.loads(json.dumps(reference['play_frames']))
        mutate(frames)
        if compare(frames,reference['pickup_events'],original)['passed']:
            raise Blocked(f'Comparator accepted {name}')
        results[name]='rejected by comparison'
    (WORK/'controls.json').write_text(json.dumps(results,indent=2)+'\n')
    return results


def record_image_spans(native):
    """Record every original-image byte range native code or a physical
    stand-in resolves, after construction. Addresses only; values stay in the
    hash-checked image and are read again by scripts/prepare-menu-assets.py."""
    low=native.program.base;high=max(s.address+s.size for s in native.program.sections)
    touched=set();pointer=native.machine.pointer
    def recording(address,size):
        if low<=address<high:touched.add((address,min(size,high-address)))
        return pointer(address,size)
    native.machine.pointer=recording
    return touched


def image_spans(program, touched):
    """Merge touched ranges into dword-aligned spans clipped to sections."""
    spans=[]
    for address,size in sorted(touched):
        start,end=address&~3,(address+size+3)&~3
        if spans and start<=spans[-1][1]:spans[-1][1]=max(spans[-1][1],end)
        else:spans.append([start,end])
    result=[]
    for start,end in spans:
        for section in program.sections:
            a,b=max(start,section.address),min(end,section.address+section.size)
            if a<b:result.append([f'{a:x}',b-a,section.name])
    return result


def main():
    global WORK
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=ROOT/'work/level-one-map/trace.json')
    parser.add_argument('--output',type=Path,default=WORK)
    parser.add_argument('--paper-startup',action='store_true')
    parser.add_argument('--build-only',action='store_true')
    parser.add_argument('--controls',action='store_true',help='also run the negative controls')
    parser.add_argument('--record-data-spans',action='store_true',
                        help='write the original image spans the run touches to work/native-level-one-join/data-spans.json')
    args=parser.parse_args()
    WORK=args.output.resolve()
    if not WORK.is_relative_to(ROOT/'work'):
        parser.error('Derived output must stay under work/')
    original=None if args.build_only else json.loads(args.reference.read_text())
    if original is not None and original.get('startup_paper',False)!=args.paper_startup:
        parser.error('Reference startup paper profile differs from the requested join')
    extra_roots=([int(row['address'],16) for row in original['game_functions']]
                 if original is not None and args.paper_startup else ())
    library,entries=build(extra_roots=extra_roots)
    if args.build_only:
        print(json.dumps(dict(status='built',entries=len(entries))));return 0
    native=LevelOneNativeJoin(library,entries,startup_paper=args.paper_startup)
    touched=record_image_spans(native) if args.record_data_spans else None
    status='blocked'
    try:
        native.execute()
        status='native-complete'
    except Blocked as error:
        native.native_error=native.native_error or str(error)
    comparison=compare(native.play_frames,native.pickup_events,original)
    if status=='native-complete' and not comparison['passed']:status='diverged'
    report=dict(status=status,error=native.native_error,error_stack=native.error_stack,phase=native.phase,phases=native.phase_results[-20:],
                calls=list(native.native_calls)[-40:],navigation=native.navigation,comparison=comparison,
                x87_returned={hex(k):v for k,v in native.x87_returned.items()},
                x87_discarded={f'{a:#x}->{b:#x}':v for (a,b),v in native.x87_discarded.items()},
                play_frames=native.play_frames,pickup_events=native.pickup_events,guest_execution=False,
                startup_paper=args.paper_startup,reference=str(args.reference.resolve()))
    WORK.mkdir(parents=True,exist_ok=True)
    (WORK/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if touched is not None:
        (WORK/'data-spans.json').write_text(json.dumps(dict(status=status,spans=image_spans(native.program,touched)),indent=1)+'\n')
    native.close()
    controls=None
    if args.controls and status=='native-complete':
        try:
            controls=sorted(run_controls(library,entries,original))
        except Blocked as error:
            status='controls-failed';native.native_error=str(error)
    print(json.dumps(dict(status=status,error=native.native_error,error_stack=native.error_stack,phase=native.phase,
                          play_frames=len(native.play_frames),divergence=comparison['divergence'],
                          pickups_match=comparison['pickups_match'],controls=controls)))
    return 0 if status=='native-complete' else 2


if __name__=='__main__':
    raise SystemExit(main())
