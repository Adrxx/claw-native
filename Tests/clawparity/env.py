"""The comparison environment.

An Env owns one emulated machine and one set of native buffers that mirror the
machine's address space. A test case is set up once into an initial memory
image, then run twice from that image: through the native module and through
the original instructions. The Env records every outside call on each side,
with a digest of memory at the moment of the call, and compares the two runs.

Outside calls come in two kinds. A fixture is a stand-in that both sides call:
imports, the allocator, services that cannot run, function pointers a case
supplies. Everything else inside the program's code is executed as original
instructions on both sides; on the native side the Env copies the native
buffers into the machine, runs the callee there, and copies the result back.
"""
from .abi import CALL_ARGUMENT_CAPACITY

import ctypes as C
import hashlib
import itertools
import struct
import time
from dataclasses import dataclass, field
from contextlib import contextmanager

from unicorn import UcError, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP

from . import build
from .guest_exception import PhysicalTransfer
from .kernel import supported_x87_control
from .kernel import STACK_BASE, STACK_SIZE, STACK_TOP, STOP, STUB_BASE, STUB_SIZE, PHYSICAL_CALLBACK_RETURN, EmulationFault, Machine, ContextFault, CONTEXT_FIELDS, CONTEXT_REGISTERS, CONTEXT_ALL, CONTEXT_REQUIRED, validate_context, validate_source, validate_source_operands, validate_source_output, SourceFixtureCapability, validate_source_fixture, validate_source_fixture_output

U32 = C.c_uint32
HEAP_BASE = 0x3000000
BRIDGE_STACK = STACK_TOP - 0x4000  # stack pointer for original callees run on behalf of native code
CALLEE_POPS = ("thiscall", "stdcall", "fastcall")
FAULT_NAMES = {1: "memory", 2: "halt", 3: "budget", 4: "unimplemented", 5: "abi", 6: "host"}


class Halt(Exception):
    """Raised by a fixture standing for a service the test must stop at."""


class SourceBudgetFault(Exception):
    """Shared source graph operations exhausted; never a source exception."""


class NativeGuestTransfer(Exception):
    """Local callback marker after an owned capture; never crosses ctypes."""


class HarnessError(Exception):
    """The test itself is wrong or incomplete; not a difference between the two sides."""


class NativeCompilerContext(C.Structure):
    _fields_ = [(name, U32) for name in ('size', 'version', 'inputMask', 'outputMask', *CONTEXT_FIELDS,
                                       'continuation', 'reserved0', 'reserved1')]


class NativeSourceContext(C.Structure):
    _fields_ = [(name, U32) for name in ('size', 'version', 'inputMask', 'outputMask', *CONTEXT_FIELDS,
                                       'preserveMask', 'reserved0', 'reserved1')]


_callback_activations = itertools.count(1)

class NativeCallbackCPU(C.Structure):
    _fields_ = [(n, U32) for n in ('size', 'version', 'target', 'entryStackPointer')] + [
        ('activation', C.c_uint64), ('cpu', NativeSourceContext)]


class NativeX87Value(C.Structure):
    _fields_ = [('significand', C.c_uint64), ('signExponent', U32), ('reserved', U32)]


class NativeX87State(C.Structure):
    _fields_ = [(n, U32) for n in ('size', 'version', 'control', 'status', 'count', 'popCount',
                                  'pushCount', 'returned', 'eax', 'edx', 'reserved0', 'reserved1')] + [
        ('slots', NativeX87Value * 8)]


class NativeCall(C.Structure):
    pass


class NativeSourceDisposition(C.Structure):
    _fields_ = [(name, U32) for name in ('size', 'version', 'disposition', 'callerFunction',
                'sourceSite', 'targetFunction', 'entryStackPointer', 'returnPC')] + [
                ('request', C.POINTER(NativeCall))]


NativeCall._fields_ = [
                ("function", U32), ("receiver", U32), ("receiver2", U32), ("argumentCount", U32),
                ("arguments", U32 * CALL_ARGUMENT_CAPACITY), ("stackPointer", U32), ("x87ArgumentCount", U32), ("x87Argument", C.c_double),
                ("compilerContext", C.POINTER(NativeCompilerContext)),
                ("sourceContext", C.POINTER(NativeSourceContext)), ("sourceReturnPC", U32),
                ("sourceTransferVersion", U32), ("sourceTransferKind", U32),
                ("sourceTransferSite", U32), ("sourceCallerFunction", U32),
                ("sourceDisposition", C.POINTER(NativeSourceDisposition)), ("x87State", C.POINTER(NativeX87State)), ("x87Operation", U32), ("callbackCPU", C.POINTER(NativeCallbackCPU)), ("callbackActivation", C.c_uint64)]


CALLBACK = C.CFUNCTYPE(U32, C.c_void_p, C.POINTER(NativeCall))
BYTES_CALLBACK = C.CFUNCTYPE(C.c_void_p, C.c_void_p, U32, U32)


class NativeHost(C.Structure):
    _fields_ = [("user", C.c_void_p), ("bytes", C.c_void_p), ("call", CALLBACK), ("maximumOperations", U32),
                ("fault", U32), ("faultAddress", U32), ("floatResult", C.c_double),
                ("entryStackPointer", U32), ("remainingOperations", C.POINTER(C.c_uint64)),
                ("compilerContext", C.POINTER(NativeCompilerContext)),
                ("sourceContext", C.POINTER(NativeSourceContext)), ("sourceReturnPC", U32),
                ("guestSession", C.c_void_p), ("callbackCPU", C.POINTER(NativeCallbackCPU))]


def check_host_layout(library):
    """Fail before native execution if a cached or mirrored host ABI is stale."""
    library.claw_call_argument_capacity.restype = U32
    if library.claw_call_argument_capacity() != CALL_ARGUMENT_CAPACITY:
        raise HarnessError("call argument capacity ABI mismatch")
    for prefix, structure in (('host', NativeHost), ('call', NativeCall), ('context', NativeCompilerContext), ('source', NativeSourceContext),
                              ('callback_cpu', NativeCallbackCPU), ('source_disposition', NativeSourceDisposition), ('x87_state', NativeX87State), ('x87_value', NativeX87Value)):
        size, offset = getattr(library, f'claw_{prefix}_sizeof'), getattr(library, f'claw_{prefix}_offset')
        size.restype = C.c_size_t
        offset.argtypes, offset.restype = [U32], C.c_size_t
        expected = (C.sizeof(structure), *(getattr(structure, name).offset for name, _ in structure._fields_))
        actual = (size(), *(offset(i) for i in range(len(structure._fields_))))
        if actual != expected:
            raise HarnessError(f'{prefix} ABI mismatch: native {actual}, ctypes {expected}')


class Span(C.Structure):
    _fields_ = [("token", U32), ("size", U32)]


class Arena(C.Structure):
    _fields_ = [("heap", C.c_void_p), ("heapBase", U32), ("heapSize", U32),
                ("image", C.c_void_p), ("imageBase", U32), ("imageSize", U32),
                ("stack", C.c_void_p), ("stackBase", U32), ("stackSize", U32),
                ("spans", C.POINTER(Span)), ("spanCount", U32), ("strict", U32), ("accesses", C.c_uint64)]


@dataclass(frozen=True)
class Signature:
    address: int
    name: str
    convention: str
    argc: int
    arguments: tuple = ()  # per stack argument: "u32", "cstr", "ptr:N" or "out:N"


@dataclass(frozen=True)
class EnumerationCallbackContract:
    """A case's physical EnumDisplayModes service and its owned stdcall2 target."""
    program_sha256: str
    service: int
    target: int
    body_end: int
    body_sha256: str


@dataclass(frozen=True)
class DialogCallbackContract:
    """Trusted boundary declaration for one synchronous DialogBoxParamA site.

    No caller-selected ABI, target or source continuation is accepted by the
    invocation API. body_sha256 binds unchanged executable bytes in this VM.
    """
    program_sha256: str
    service: int
    call_pc: int
    return_pc: int
    target: int
    body_end: int
    body_sha256: str
    native_owned: bool = False
    end_service: int = 0

    def __post_init__(self):
        from .program import CLAW_SHA256
        if self.program_sha256 == CLAW_SHA256 and type(self.end_service) is int and self.end_service == 0:
            object.__setattr__(self, 'end_service', 0x546d34)


@dataclass(frozen=True)
class WindowCallbackContract:
    """First bounded RegisterClassA -> CreateWindowExA original callback contract."""
    program_sha256: str
    target: int
    body_end: int
    body_sha256: str
    register_site: tuple  # IAT, actual CALL, actual return PC
    create_site: tuple


@dataclass(frozen=True)
class _WindowRegistration:
    contract: WindowCallbackContract
    descriptor: bytes
    name: bytes
    module: int
    atom: int
    generation: object
    nonce: object


@dataclass(frozen=True)
class WindowCreationLease:
    hwnd: int
    create_struct: int
    minmax_info: int
    window_rect: int
    generation: object
    nonce: object


@dataclass(frozen=True)
class WindowShowContract:
    window: WindowCallbackContract
    show_site: tuple
    default_sites: tuple


@dataclass(frozen=True)
class WindowShowProfile:
    # Explicit physical profile: initial hidden, no STARTUPINFO override,
    # no previously active/focused window, rectangular popup client geometry.
    rect: tuple  # x, y, width, height, signed positions / positive dimensions
    flags: int = 0x43  # SHOWWINDOW | NOMOVE | NOSIZE


@dataclass(frozen=True)
class WindowMessageLease:
    hwnd: int
    generation: object
    nonce: object


@dataclass(frozen=True)
class Call:
    function: int
    receiver: int
    receiver2: int
    arguments: tuple
    stack_pointer: int
    x87_arguments: tuple = ()
    source_context: object = None
    source_return_pc: int = 0


@dataclass
class Side:
    """What one run of a case produced."""
    completed: bool = False
    halted: bool = False
    eax: int = 0
    fault: int = 0
    fault_address: int = 0
    stack_pointer: int = 0
    events: list = field(default_factory=list)
    heap: bytes = b""
    image: bytes = b""
    spans: dict = field(default_factory=dict)
    freed: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    bridged: list = field(default_factory=list)
    compiler_context: dict = field(default_factory=dict)
    source_stop: object = None  # complete CPU view at a declared physical Halt boundary
    source_boundaries: list = field(default_factory=list)
    x87: object = None  # (CW, SW, logical slots) after a declared owned x87 publication


class Env:
    def __init__(self, program, heap_bytes=0x40000, strict=True, symbols=None, maximum_operations=50_000_000):
        self.program = program
        self.heap_bytes = heap_bytes
        self.symbols = symbols or {}
        self.machine = Machine(program, HEAP_BASE, heap_bytes)
        self.machine.on_external = self._external
        self.pristine_image = self.machine.read(program.base, program.size)
        self.data_offset = program.data_start - program.base
        self.maximum_operations = maximum_operations
        self.source_callees, self.compiler_callees = {}, {}
        self._source_graph = False
        self._bridge_depth = 0
        self._enumeration_hooks = set()
        self.fixtures = {}       # address -> (Signature, effect), for the whole family
        self.x87_callees = {}    # observed original callees
        self.x87_exact = {}      # explicit stack effects; no fixture implementation
        self.x87_results = {}    # owned ordinary entries returning ST(0): address -> stack effect
        self.x87_environments = {}  # ordinary owners preserving their inherited live stack
        self._x87_outer = None   # active native outer x87 result/environment entry
        self.caller_frames = {}  # original callee -> {owned caller: (site, base, index, offset)}
        self._caller_frame_signatures = {}
        self._frame_entry = None  # (function, receiver, arguments, entry ESP) of the ordinary outer run
        self._entry_ebp = None    # case-elected caller EBP at an ordinary outer entry, or None
        self.stub_function = dict((stub, slot) for slot, stub in self.machine.import_stub.items())
        self.coverage = set()    # (address, size) blocks the original side executed
        # Native side
        self._heap = (C.c_uint8 * heap_bytes)()
        self._image = (C.c_uint8 * program.size)()
        self._stack = (C.c_uint8 * STACK_SIZE)()
        self._hostlib = C.CDLL(str(build.hostlib()))
        check_host_layout(self._hostlib)
        self._arena = Arena(C.addressof(self._heap), HEAP_BASE, heap_bytes, C.addressof(self._image), program.base,
                            program.size, C.addressof(self._stack), STACK_BASE, STACK_SIZE, None, 0, int(strict), 0)
        self._callback = CALLBACK(self._native_call)
        self._arena_bytes = self._hostlib.claw_arena_bytes
        self._arena_bytes.argtypes = [C.c_void_p, U32, U32]
        self._arena_bytes.restype = C.c_void_p
        self._bytes_callback = BYTES_CALLBACK(self._observe_native_bytes)
        self._boundary_hooks = set()
        self._host = NativeHost(C.addressof(self._arena), C.cast(self._hostlib.claw_arena_bytes, C.c_void_p),
                                self._callback, maximum_operations, 0, 0, 0.0, 0, None)
        self._span_array = None
        self.backend = "initial"
        self.side = "setup"
        self._begin_case(None)

    # ---- Family-level fixtures -------------------------------------------------
    def whole_x87(self, address, convention, argc, name="", arguments=(), *, exact=None):
        """Declare a register operand, retaining the original callee on both sides."""
        if (not self.program.in_text(address) or address in self.fixtures or address in self.x87_callees or
                address in self.x87_environments):
            raise HarnessError(f"{address:#x}: x87 callee must be unique original program code")
        if convention not in ("thiscall", "stdcall", "cdecl") or type(argc) is not int or not 0 <= argc <= CALL_ARGUMENT_CAPACITY:
            raise HarnessError(f"{address:#x}: invalid x87 callee signature")
        if address in self.source_callees or address in self.compiler_callees or address in self.caller_frames:
            raise HarnessError('x87 and source/compiler/caller-frame capabilities are exclusive')
        if exact is not None:
            if (not isinstance(exact, dict) or set(exact) != {'pop', 'push'} or
                    type(exact['pop']) is not int or not 0 <= exact['pop'] <= 8 or
                    type(exact['push']) is not int or not 0 <= exact['push'] <= 1):
                raise HarnessError('invalid exact x87 stack effect')
            self.x87_exact[address] = dict(exact)
        self.x87_callees[address] = Signature(address, name, convention, argc, tuple(arguments))
        self.machine.observe(address, self._observe_x87)

    def owned_x87_result(self, address, effect):
        """An owned ordinary entry leaves exactly one pushed ST(0) above its entry stack."""
        if (not self.program.in_text(address) or address in self.x87_results or address in self.x87_environments or address in self.x87_callees or
                address in self.fixtures or address in self.source_callees or address in self.compiler_callees):
            raise HarnessError(f"{address:#x}: x87 result entry must be unique owned program code")
        if not isinstance(effect, dict) or effect != {'pop': 0, 'push': 1} or any(type(v) is not int for v in effect.values()):
            raise HarnessError(f"{address:#x}: owned x87 result must be exactly pop 0, push 1")
        self.x87_results[address] = dict(effect)

    def owned_x87_environment(self, address, effect):
        """Explicit inherited environment for an ordinary u32/void owner."""
        if (not self.program.in_text(address) or address in self.x87_environments or address in self.x87_results or
                address in self.x87_callees or address in self.fixtures or address in self.source_callees or
                address in self.compiler_callees or address in self.caller_frames):
            raise HarnessError(f"{address:#x}: x87 environment requires unique owned program code")
        if not isinstance(effect, dict) or effect != {'pop': 0, 'push': 0} or any(type(v) is not int for v in effect.values()):
            raise HarnessError('owned x87 environment must be exactly pop 0, push 0')
        self.x87_environments[address] = dict(effect)

    def _native_x87_outer(self, raw):
        """ENTRY reads, RESULT publishes, the declared outer entry's exact x87 stack."""
        outer = self._x87_outer
        if (raw.x87ArgumentCount not in (4, 5) or not raw.x87State or raw.x87Argument or raw.x87Operation or
                raw.receiver or raw.receiver2 or raw.argumentCount or raw.stackPointer or raw.compilerContext or
                raw.sourceContext or raw.sourceReturnPC or raw.sourceTransferKind or raw.sourceTransferVersion or
                raw.sourceTransferSite or raw.sourceCallerFunction or raw.sourceDisposition or raw.callbackCPU or
                raw.callbackActivation or self._host.compilerContext or self._host.sourceContext or
                self._host.guestSession or self._bridge_depth or any(raw.arguments)):
            raise ContextFault('owned x87 result transport mixed with another capability')
        if outer is None or raw.function != outer['function']:
            raise ContextFault('x87 entry/result request outside its declared owned outer entry')
        s = raw.x87State.contents
        control, status, slots = outer['entry']
        if raw.x87ArgumentCount == 4:
            request = bytes(s)
            if (s.size != C.sizeof(NativeX87State) or s.version != 1 or any(request[8:]) or outer['queried']):
                raise ContextFault('owned x87 entry request must be empty and issued once')
            outer['queried'] = True
            s.control, s.status, s.count = control, status, len(slots)
            for i in range(8):
                s.slots[i] = NativeX87Value(*(slots[i] if i < len(slots) else (0, 0)), 0)
            s.returned = 1
            return 0
        self._validate_x87_state(s)
        published = (s.control, s.status, tuple((v.significand, v.signExponent) for v in s.slots[:s.count]))
        push = outer.get('push', 1)
        if (s.popCount != 0 or s.pushCount != push or s.returned or s.eax or s.edx or
                len(published[2]) != len(slots) + push or published[2][push:] != slots or published[0] != control or
                (published[1] >> 11) & 7 != ((status >> 11) - push) & 7 or
                (push == 0 and not outer['queried'])):
            raise ContextFault('owned x87 publication violates its declared effect or entry live state')
        outer['result'] = published
        s.returned = 1
        return 0

    def fixture(self, address, convention, argc, effect, name="", arguments=()):
        """Declare a stand-in for `address`: an import slot, or a function inside the program."""
        if convention not in ("thiscall", "stdcall", "cdecl", "fastcall"):
            raise HarnessError(f"{address:#x}: unknown convention {convention!r}")
        if any(c.target == address for c, _ in getattr(self, '_enumeration_contracts', {}).values()):
            raise ContextFault('owned enumeration callback cannot become a fixture')
        if any(v[0].target == address for v in getattr(self,'_window_contracts',{}).values()):
            raise ContextFault('declared window callback cannot become a physical fixture')
        if any(c.target == address for c in getattr(self,'_dialog_contracts',{}).values()):
            raise ContextFault('declared dialog callback cannot become a physical fixture')
        if address in self.source_callees or address in self.compiler_callees:
            raise ContextFault(f"{address:#x}: declared original context dependency cannot become a fixture")
        if address in self.x87_callees or address in self.x87_environments:
            raise HarnessError(f"{address:#x}: x87 original callee cannot become a fixture")
        if address in self.caller_frames:
            raise ContextFault(f"{address:#x}: caller-frame original callee cannot become a fixture")
        if self.program.in_text(address):
            self.machine.intercept(address)
        elif address not in self.program.imports:
            raise HarnessError(f"{address:#x} is neither program code nor an import slot")
        label = name or self.program.imports.get(address, "")
        self.fixtures[address] = (Signature(address, label, convention, argc, tuple(arguments)), effect)

    def caller_frame(self, address, convention, argc, declarations, owned_ranges):
        """Declare the caller EBP an original whole callee reads, per owned caller and direct CALL site.

        `declarations` is [(caller, site, base, index, offset)], already structurally checked by
        cases.caller_frame_errors. EBP is base + offset of the caller's ordinary entry state. The
        original side checks it at every declared site; native bridges receive the same value.
        """
        if (self.backend != 'initial' or not self.program.in_text(address) or address in self.caller_frames or
                address in self.fixtures or address in self.x87_callees or address in self.source_callees or
                address in self.compiler_callees):
            raise ContextFault(f'{address:#x}: caller frame requires a unique exclusive original callee')
        if convention not in ('cdecl', 'stdcall', 'thiscall') or type(argc) is not int or not 0 <= argc <= CALL_ARGUMENT_CAPACITY:
            raise ContextFault(f'{address:#x}: caller frame requires an ordinary signature')
        table = {}
        for caller, site, base, index, offset in declarations:
            ranges = owned_ranges.get(caller)
            if not ranges or caller in table:
                raise ContextFault(f'{address:#x}: caller {caller:#x} has no known owned ranges or is duplicated')
            if not any(low <= site and site + 5 <= high for low, high in ranges):
                raise ContextFault(f'{address:#x}: site {site:#x} is outside the owned ranges of {caller:#x}')
            code = self.pristine_image[site - self.program.base:site - self.program.base + 5]
            if code[0] != 0xE8 or (site + 5 + struct.unpack('<i', code[1:])[0]) & 0xFFFFFFFF != address:
                raise ContextFault(f'{address:#x}: site {site:#x} is not a direct original CALL of the callee')
            if base not in ('receiver', 'entry_esp', 'argument'):
                raise ContextFault(f'{address:#x}: unknown caller frame base {base!r}')
            table[caller] = (site, base, index, offset & 0xFFFFFFFF, tuple(ranges))
        self.caller_frames[address] = table
        self._caller_frame_signatures[address] = (convention, argc)
        self.machine.observe(address, self._observe_caller_frame)

    def _caller_frame_value(self, callee, entry):
        site, base, index, offset, _ = self.caller_frames[callee][entry[0]]
        _, receiver, arguments, esp = entry
        origin = receiver if base == 'receiver' else esp if base == 'entry_esp' else arguments[index]
        return (origin + offset) & 0xFFFFFFFF

    def _native_caller_frame(self, raw):
        """The declared caller EBP for a native bridge, or a ContextFault for any undeclared use."""
        entry = self._frame_entry
        convention, argc = self._caller_frame_signatures[raw.function]
        if (entry is None or self._bridge_depth or self._host.sourceContext or self._host.compilerContext or
                raw.sourceContext or raw.sourceReturnPC or raw.compilerContext or raw.x87ArgumentCount or
                raw.x87State or raw.x87Operation or raw.callbackCPU or raw.receiver2 or
                raw.argumentCount != argc or (convention != 'thiscall' and raw.receiver)):
            raise ContextFault(f'{raw.function:#x}: caller frame requires an ordinary direct call from an ordinary outer entry')
        if entry[0] not in self.caller_frames[raw.function]:
            raise ContextFault(f'{raw.function:#x}: caller frame is undeclared for entry {entry[0]:#x}')
        return self._caller_frame_value(raw.function, entry)

    def _observe_caller_frame(self, machine, address):
        """Original side only: the declared EBP must be the one the original has at its declared site."""
        entry = self._frame_entry
        if self.side != 'original' or entry is None or self._bridge_depth:
            return
        declared = self.caller_frames[address].get(entry[0])
        if declared is None:
            return
        site, _, _, _, ranges = declared
        returned = machine.words(machine.register(UC_X86_REG_ESP), 1)[0]
        if returned - 5 == site:
            expected, actual = self._caller_frame_value(address, entry), machine.register(UC_X86_REG_EBP)
            if expected != actual:
                raise HarnessError(f'declared caller frame of {self.describe(address)} at {site:#x} says EBP '
                                   f'{expected:#x}; the original has {actual:#x}')
        elif any(low <= returned < high for low, high in ranges):
            raise HarnessError(f'{self.describe(address)} called from undeclared caller-frame site {returned - 5:#x}')

    # ---- Per-case helpers, callable from setup() and from fixture effects -------
    def enumeration_callback(self, contract):
        """Elect during setup; native invocations use the outer selected module."""
        if self.backend != 'initial' or type(contract) is not EnumerationCallbackContract:
            raise ContextFault('enumeration declaration requires setup and typed contract')
        c = contract
        if any(type(v) is not int for v in (c.service, c.target, c.body_end)):
            raise ContextFault('enumeration identities require integer addresses')
        found = self._case_fixtures.get(c.service)
        if (c.program_sha256 != self.program.sha256 or
                not self.program.in_text(c.target) or not self.program.in_text(c.body_end - 1) or
                not c.target < c.body_end <= c.target + 4096 or
                not found or found[0].convention != 'stdcall' or found[0].argc != 5 or
                self._lookup(c.target) is not None or c.target in self.source_callees or
                c.target in self.compiler_callees or c.target in self.x87_callees or
                c.service in self._enumeration_contracts):
            raise ContextFault('invalid enumeration service, target or ABI')
        from .program import CLAW_SHA256
        if self.program.name == 'claw-v1.0' or self.program.sha256 == CLAW_SHA256:
            if c.program_sha256 != CLAW_SHA256 or (c.target, c.body_end) != (0x4bcda0, 0x4bcdd5):
                raise ContextFault('enumeration target differs from pinned Claw callback')
        body = self.pristine_image[c.target-self.program.base:c.body_end-self.program.base]
        if hashlib.sha256(body).hexdigest() != c.body_sha256:
            raise ContextFault('enumeration callback body hash mismatch')
        self._enumeration_contracts[c.service] = (c, found[0])
        if c.target not in self._enumeration_hooks:
            def require_original(machine, address):
                if (self._enumeration_graph and self.side == 'native' and
                        any(c.target == address for c, _ in self._enumeration_contracts.values())):
                    raise ContextFault('selected native enumeration owner reached original instructions')
            self.machine.observe(c.target, require_original)
            self._enumeration_hooks.add(c.target)

    def _begin_enumeration_graph(self, entry=None):
        if not self._enumeration_contracts:
            return
        if (self._source_graph or self._dialog_contracts or self._window_contracts or
                self._host.compilerContext or self._host.sourceContext or self._host.guestSession or
                getattr(self, '_guest_adapter', None) is not None):
            raise ContextFault('enumeration callbacks require an ordinary non-EH root')
        self.machine.begin_physical_callbacks(self._consume_physical_operation, self.callback_timeout_seconds)
        self._enumeration_graph = True
        self._enumeration_entry = entry

    def invoke_enumeration_callback(self, request, arguments):
        """Invoke arg 4 of the live stdcall5 request with (descriptor, context).

        This is synchronous physical service transport, never a game fixture.
        An ordinary frame carries no original return-site or hidden CPU contract.
        """
        try:
            self._check_physical_failure()
            return self._invoke_enumeration_callback(request, arguments)
        except BaseException as error:
            if self._enumeration_graph:
                self._physical_failure = self._physical_failure or error
            raise

    def _invoke_enumeration_callback(self, request, arguments):
        if (not self._enumeration_graph or not self.machine._physical_pump or
                not self._physical_requests or self.machine._active_emulations or type(request) is not Call):
            raise ContextFault('enumeration callback has no suspended ordinary request')
        active, signature, generation, _ = self._physical_requests[-1]
        elected = self._enumeration_contracts.get(request.function)
        if active is not request or generation is not self._callback_generation or elected is None:
            raise ContextFault('enumeration request is stale, copied or unsupported')
        c, owner = elected
        if (signature is not owner or self._lookup(c.service)[0] is not owner or
                signature.convention != 'stdcall' or signature.argc != 5 or
                len(request.arguments) != 5 or request.arguments[4] != c.target or
                request.receiver or request.receiver2 or request.source_context is not None or
                request.x87_arguments or request.source_return_pc or
                self._lookup(c.target) is not None or self.machine._owned_scope is not None):
            raise ContextFault('enumeration target or ordinary request ABI mismatch')
        if (type(arguments) is not tuple or len(arguments) != 2 or
                any(type(v) is not int or not 0 <= v <= 0xffffffff for v in arguments) or
                arguments[1] != request.arguments[3]):
            raise ContextFault('enumeration requires descriptor and unchanged uint32 context')
        descriptor = arguments[0]
        if not any(a <= descriptor and descriptor + 0x6c <= a + n for a, n in self.spans.items()):
            raise ContextFault('enumeration descriptor requires 0x6c bytes of live backing')
        if (c.program_sha256 != self.program.sha256 or
                hashlib.sha256(self.read(c.target, c.body_end-c.target)).hexdigest() != c.body_sha256):
            raise ContextFault('enumeration executable identity changed')
        if self._enumeration_depth >= 16:
            raise ContextFault('enumeration callback depth exceeded')
        self._consume_physical_operation()
        if time.monotonic() >= self.machine._physical_deadline:
            raise ContextFault('enumeration callback graph deadline exhausted')
        # Reserve descending transport frames below both the ordinary root and
        # its bridge area. No inferred source CALL/return-PC identity is exposed.
        parent_sp = request.stack_pointer or self._host.entryStackPointer
        if (type(parent_sp) is not int or parent_sp & 3 or parent_sp < STACK_BASE or
                parent_sp + (24 if request.stack_pointer else 4) > STACK_BASE + STACK_SIZE):
            raise ContextFault('enumeration suspended frame outside bounded stack')
        if request.stack_pointer and self.read(parent_sp + 4, 20) != struct.pack('<5I', *request.arguments):
            raise ContextFault('enumeration physical operands differ from request')
        frame = min(parent_sp, BRIDGE_STACK, self._enumeration_frame or STACK_TOP) - 0x1000
        if frame < STACK_BASE + 0x1000 or frame & 3:
            raise ContextFault('enumeration callback frame outside bounded stack')
        parent_bytes = self.read(parent_sp, 24 if request.stack_pointer else 4)
        saved_frame, saved_backend = self._enumeration_frame, self.backend
        saved_host_frame = self._host.entryStackPointer
        saved_budget = C.cast(self._host.remainingOperations, C.c_void_p).value
        saved_cpu, saved_fs = self.machine.uc.context_save(), self.machine.fs_head
        record = dict(target=c.target, arguments=arguments, entered=False, returned=False,
                      backend=self.side, frame=frame)
        self.callback_executions.append(record)
        self._enumeration_depth += 1
        self._enumeration_frame = frame
        try:
            if self.side == 'original':
                parent = NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                    *(self.machine.register(r) for r in CONTEXT_REGISTERS), saved_fs, 0, 0, 0)
                result = self.machine._call_physical_callback(c.target, parent, arguments, parent_bytes,
                    lambda: record.update(entered=True), enumeration_frame=frame)
                value = result.eax
            else:
                if self._enumeration_entry is None or self.backend not in ('native', 'machine'):
                    raise ContextFault('enumeration has no selected native owner')
                if self.backend == 'machine':
                    self._copy_machine_to_native()
                self.backend = 'native'
                self.put(frame, PHYSICAL_CALLBACK_RETURN, *arguments)
                self._host.entryStackPointer = frame
                words, result = (U32 * 2)(*arguments), U32()
                record['entered'] = True
                completed = self._enumeration_entry(c.target, 0, words, 2, C.byref(self._host), C.byref(result))
                if self._host.fault == 2:
                    raise Halt()
                if not completed or self._host.fault:
                    raise ContextFault('selected native enumeration callback did not return')
                if (self._host.entryStackPointer != frame or
                        C.cast(self._host.remainingOperations, C.c_void_p).value != saved_budget or
                        self._host.compilerContext or self._host.sourceContext or
                        self._host.sourceReturnPC or self._host.guestSession or
                        self.get(frame) != PHYSICAL_CALLBACK_RETURN):
                    raise ContextFault('native enumeration changed borrowed ABI scope or return word')
                value = result.value
            if self.read(parent_sp, len(parent_bytes)) != parent_bytes:
                raise ContextFault('enumeration changed suspended parent frame')
            record['returned'] = True
            record['eax'] = value
            return value
        finally:
            if self.side == 'native' and saved_backend == 'machine':
                self.machine.write(HEAP_BASE, bytes(self._heap))
                self.machine.write(self.program.data_start, bytes(self._image)[self.data_offset:])
                self.machine.write(STACK_BASE, bytes(self._stack))
            self.machine.uc.context_restore(saved_cpu)
            self.machine.fs_head = saved_fs
            self._host.entryStackPointer = saved_host_frame
            self.backend = saved_backend
            self._enumeration_frame = saved_frame
            self._enumeration_depth -= 1

    def _copy_machine_to_native(self):
        C.memmove(self._heap, self.machine.read(HEAP_BASE, self.heap_bytes), self.heap_bytes)
        data = self.machine.read(self.program.data_start, self.program.size - self.data_offset)
        C.memmove(C.addressof(self._image) + self.data_offset, data, len(data))
        C.memmove(self._stack, self.machine.read(STACK_BASE, STACK_SIZE), STACK_SIZE)

    def window_callback(self, contract):
        """Elect registration/creation sites; does not pre-register a class."""
        if self.backend != 'initial' or type(contract) is not WindowCallbackContract:
            raise ContextFault('window callback declaration requires setup and typed contract')
        c=contract
        if (type(c.register_site) is not tuple or type(c.create_site) is not tuple or
            len(c.register_site)!=3 or len(c.create_site)!=3 or
            c.program_sha256 != self.program.sha256 or
            any(type(v) is not int for v in (c.target,c.body_end,*c.register_site,*c.create_site)) or
            len(c.register_site)!=3 or len(c.create_site)!=3 or
            not self.program.in_text(c.target) or not self.program.in_text(c.body_end-1) or
            not c.target<c.body_end<=c.target+4096):
            raise ContextFault('invalid window callback identity')
        from .program import CLAW_SHA256
        if self.program.name=='claw-v1.0' or self.program.sha256==CLAW_SHA256:
            if (c.program_sha256!=CLAW_SHA256 or c.target!=0x4b8500 or c.body_end!=0x4b87e1 or
                c.register_site!=(0x546bd4,0x4b8af8,0x4b8afe) or
                c.create_site!=(0x546bf8,0x4b849c,0x4b84a2)):
                raise ContextFault('window callback differs from pinned Claw boundary')
        if self._lookup(c.target) or c.target in self.compiler_callees or c.target in self.x87_callees:
            raise ContextFault('window callback must execute original code')
        body=self.pristine_image[c.target-self.program.base:c.body_end-self.program.base]
        if hashlib.sha256(body).hexdigest()!=c.body_sha256:
            raise ContextFault('window callback body hash mismatch')
        owners=[]
        for site,name,argc in ((c.register_site,'registerclassa',1),(c.create_site,'createwindowexa',12)):
            iat,pc,rpc=site; found=self._lookup(iat)
            if (self.program.imports.get(iat,'').lower()!='user32.dll!'+name or
                not self.program.in_text(pc) or not self.program.in_text(rpc) or rpc!=pc+6 or
                self.pristine_image[pc-self.program.base:rpc-self.program.base]!=b'\xff\x15'+struct.pack('<I',iat) or
                not found or found[0].convention!='stdcall' or found[0].argc!=argc or
                (iat,rpc) in self._window_contracts):
                raise ContextFault('invalid or duplicate window physical site')
            owners.append(found[0])
        for site,signature in zip((c.register_site,c.create_site),owners):
            self._window_contracts[(site[0],site[2])]=(c,site,signature,self.machine,self.program)

    @contextmanager
    def _window_guard(self):
        try:
            self._check_physical_failure()
            yield
        except BaseException as error:
            if self._source_graph and self._physical_requests:
                self._physical_failure=self._physical_failure or error
            raise

    def _window_request(self, request, kind):
        if not self.machine._physical_pump or not self._source_graph or not self._physical_requests:
            raise ContextFault('window operation has no live physical request')
        active,signature,generation,witness=self._physical_requests[-1]
        elected=self._window_contracts.get((request.function,request.source_return_pc))
        if active is not request or generation is not self._callback_generation or elected is None:
            raise ContextFault('copied, retired or undeclared window request')
        c,site,owner,vm,program=elected
        argc=1 if kind=='register' else 12
        expected=c.register_site if kind=='register' else c.create_site
        if (site!=expected or owner is not signature or vm is not self.machine or program is not self.program or
            signature.convention!='stdcall' or signature.argc!=argc or len(request.arguments)!=argc or
            request.source_context is None or bytes(request.source_context)!=witness or
            request.source_context.inputMask!=CONTEXT_ALL or request.source_context.esp!=request.stack_pointer or
            request.source_context.eip!=site[0] or self.machine._owned_scope is not None or
            c.program_sha256!=self.program.sha256 or self._lookup(c.target) or
            c.target in self.compiler_callees or c.target in self.x87_callees or
            (self.side=='native' and c.target==self._native_source_entry)):
            raise ContextFault('window request ownership, ABI or source identity mismatch')
        validate_source(request.source_context,site[0],site[2],self.program)
        frame=struct.pack(f'<{argc+1}I',site[2],*request.arguments)
        if self.read(request.stack_pointer,len(frame))!=frame:
            raise ContextFault('window request frame changed')
        for read in (self.read,self.machine.read):
            if (any(read(s[1],6)!=b'\xff\x15'+struct.pack('<I',s[0]) for s in (c.register_site,c.create_site)) or
                hashlib.sha256(read(c.target,c.body_end-c.target)).hexdigest()!=c.body_sha256):
                raise ContextFault('window executable identity changed')
        return c,frame

    def _window_name(self, pointer):
        if type(pointer) is not int or pointer<=0xffff:
            raise ContextFault('first window profile requires a bounded class string')
        result=bytearray()
        for i in range(256):
            value=self.read(pointer+i,1)
            if value==b'\0':
                if not result:raise ContextFault('empty window class')
                return bytes(result)
            result.extend(value)
        raise ContextFault('unterminated window class')

    def register_window_class(self, request, atom):
        """Stage physical registration; _serve commits its matching normal result."""
        with self._window_guard():
            c,_=self._window_request(request,'register')
            if type(atom) is not int or not 0<atom<=0xffff or id(request) in self._window_pending:
                raise ContextFault('invalid ATOM or repeated registration')
            descriptor=self.read(request.arguments[0],40)
            words=struct.unpack('<10I',descriptor)
            name=self._window_name(words[9]);key=(words[4],name)
            if words[1]!=c.target or not words[4] or key in self._window_classes:
                raise ContextFault('class descriptor target/module or duplicate registration')
            if any(r.atom==atom for r in self._window_classes.values()):
                raise ContextFault('class ATOM collision')
            registration=_WindowRegistration(c,descriptor,name,words[4],atom,self._callback_generation,object())
            self._window_pending[id(request)]=(request,registration)
            return atom

    @contextmanager
    def window_operation(self, request, hwnd):
        """A creation-only lease; show/destroy/message-loop requests are not elected."""
        with self._window_guard():
            c,_=self._window_request(request,'create')
            if type(hwnd) is not int or not 0<hwnd<=0xffffffff or hwnd in self._window_handles or id(request) in self._window_pending:
                raise ContextFault('invalid, live or repeated window handle')
            a=request.arguments;name=self._window_name(a[1])
            registration=self._window_classes.get((a[10],name))
            if registration is None or registration.contract is not c or registration.generation is not self._callback_generation:
                raise ContextFault('window class/module is not registered in this graph')
            # This first profile has no parent/menu/userdata or arbitrary creation payload.
            if a[8] or a[9] or a[11]:
                raise ContextFault('unsupported parent, menu or creation parameter')
            raw=struct.pack('<12I',a[11],a[10],a[9],a[8],a[7],a[6],a[5],a[4],a[3],a[2],a[1],a[0])
            create=self.object(48,data=raw);minmax=self.object(40,fill=0);rect=self.object(16,fill=0)
            lease=WindowCreationLease(hwnd,create,minmax,rect,self._callback_generation,object())
            state=dict(request=request,registration=registration,lease=lease,create_bytes=raw,
                       next=0,rejected=False,closed=False)
            self._window_pending[id(request)]=(request,state)
            self._window_handles[hwnd]=state
            self._window_sessions.append(state)
            self.window_history.append(('creating',hwnd))
            try:
                yield lease
                self._check_physical_failure()
                state['closed']=True
            finally:
                if not self._window_sessions or self._window_sessions[-1] is not state:
                    raise ContextFault('window lease scope corrupted')
                self._window_sessions.pop()

    def invoke_window_callback(self, request, lease, message, wparam, lparam):
        """Invoke one reviewed creation message on the registered original WNDPROC."""
        with self._window_guard():
            c,frame=self._window_request(request,'create')
            if not self._window_sessions:
                raise ContextFault('no active window creation lease')
            state=self._window_sessions[-1];registration=state['registration']
            if (state['request'] is not request or state['lease'] is not lease or
                lease.generation is not self._callback_generation or state['closed'] or state['rejected'] or
                self._window_handles.get(lease.hwnd) is not state or
                self._window_classes.get((registration.module,registration.name)) is not registration):
                raise ContextFault('stale or mismatched window lease/registration')
            if any(type(v) is not int or not 0<=v<=0xffffffff for v in (message,wparam,lparam)):
                raise ContextFault('window message operands require uint32')
            order=(0x24,0x81,0x83,1)
            expected_pointer={0x24:lease.minmax_info,0x81:lease.create_struct,0x83:lease.window_rect,1:lease.create_struct}
            if state['next']>=len(order) or message!=order[state['next']] or wparam!=0 or lparam!=expected_pointer[message]:
                raise ContextFault('unsupported window creation message/order/payload')
            for pointer,size in ((lease.create_struct,48),(lease.minmax_info,40),(lease.window_rect,16)):
                if self.spans.get(pointer)!=size:
                    raise ContextFault('creation transient storage retired or replaced')
            if self.read(lease.create_struct,48)!=state['create_bytes']:
                raise ContextFault('CREATESTRUCT identity changed')
            previous_backend=self.backend
            if previous_backend=='native':
                self.machine.write(HEAP_BASE,bytes(self._heap))
                self.machine.write(self.program.data_start,bytes(self._image)[self.data_offset:])
                self.machine.write(STACK_BASE,bytes(self._stack))
            elif previous_backend!='machine':
                raise ContextFault('window callback requires live backing')
            arguments=(lease.hwnd,message,wparam,lparam)
            record=dict(target=c.target,arguments=arguments,entered=False,returned=False)
            self.callback_executions.append(record);self.backend='machine'
            try:
                result=self.machine._call_physical_callback(c.target,request.source_context,arguments,frame,
                                                            lambda:record.__setitem__('entered',True))
                record.update(returned=True,eax=result.eax)
            finally:
                self.backend=previous_backend
                if previous_backend=='native':
                    C.memmove(self._heap,self.machine.read(HEAP_BASE,self.heap_bytes),self.heap_bytes)
                    data=self.machine.read(self.program.data_start,self.program.size-self.data_offset)
                    C.memmove(C.addressof(self._image)+self.data_offset,data,len(data))
                    C.memmove(self._stack,self.machine.read(STACK_BASE,STACK_SIZE),STACK_SIZE)
            if self.read(lease.create_struct,48)!=state['create_bytes']:
                raise ContextFault('callback changed immutable CREATESTRUCT')
            if (message in (0x24,0x83) and result.eax!=0) or (message==1 and result.eax not in (0,0xffffffff)):
                raise ContextFault('unsupported creation message result')
            state['next']+=1
            state['rejected']=(message==0x81 and result.eax==0) or (message==1 and result.eax==0xffffffff)
            self.window_history.append(('message',lease.hwnd,message,result.eax))
            return result.eax

    def _finish_window_request(self, request, value):
        elected=self._window_contracts.get((request.function,request.source_return_pc))
        if elected is None:return
        c,site,*_=elected
        if type(value) is not int or not 0<=value<=0xffffffff:
            raise ContextFault('window physical result requires uint32')
        pending=self._window_pending.get(id(request))
        if pending is None:
            if value!=0:raise ContextFault('window success lacks registered physical authority')
            return  # physical failure before registration/creation began
        if pending[0] is not request:raise ContextFault('window pending request identity changed')
        if site==c.register_site:
            self._window_request(request,'register');r=pending[1]
            if value!=r.atom:raise ContextFault('RegisterClass result differs from staged ATOM')
            self._window_classes[(r.module,r.name)]=r
            self.window_history.append(('registered',r.module,r.name,r.atom))
        else:
            self._window_request(request,'create');s=pending[1];lease=s['lease']
            if not s['closed'] or (value==0 and s['next'] and not s['rejected']) or (
                value!=0 and (value!=lease.hwnd or s['next']!=4 or s['rejected'])):
                raise ContextFault('CreateWindow result differs from actual callback disposition')
            for pointer,size in ((lease.create_struct,48),(lease.minmax_info,40),(lease.window_rect,16)):
                if self.spans.get(pointer)!=size:raise ContextFault('creation storage lifetime changed')
            for pointer in (lease.create_struct,lease.minmax_info,lease.window_rect):self.release(pointer)
            if value==0:del self._window_handles[lease.hwnd]
            else:s['live']=True
            self.window_history.append(('live' if value else 'failed',lease.hwnd))
        del self._window_pending[id(request)]

    def window_show_callback(self, contract):
        """Elect only first ShowWindow(1) and its synchronous default descendants."""
        if self.backend!='initial' or type(contract) is not WindowShowContract:
            raise ContextFault('show declaration requires setup and typed contract')
        c=contract;w=c.window
        if (type(w) is not WindowCallbackContract or
            self._window_contracts.get((w.create_site[0],w.create_site[2]),(None,))[0] is not w or
            type(c.default_sites) is not tuple or not c.default_sites or len(c.default_sites)>2):
            raise ContextFault('show requires the elected registration contract')
        from .program import CLAW_SHA256
        if self.program.name=='claw-v1.0' or self.program.sha256==CLAW_SHA256:
            if (c.show_site!=(0x546b54,0x4b84b0,0x4b84b6) or
                c.default_sites!=((0x546bf4,0x4b8521,0x4b8527),(0x546bf4,0x4b87d5,0x4b87db))):
                raise ContextFault('show/default sites differ from original Claw')
        pending=[]
        for site,name,argc in ((c.show_site,'showwindow',2),*((s,'defwindowproca',4) for s in c.default_sites)):
            if type(site) is not tuple or len(site)!=3 or any(type(v) is not int for v in site):
                raise ContextFault('invalid show/default site')
            iat,pc,rpc=site;found=self._lookup(iat)
            if (self.program.imports.get(iat,'').lower()!='user32.dll!'+name or
                not self.program.in_text(pc) or not self.program.in_text(rpc) or rpc!=pc+6 or
                self.pristine_image[pc-self.program.base:rpc-self.program.base]!=b'\xff\x15'+struct.pack('<I',iat) or
                not found or found[0].convention!='stdcall' or found[0].argc!=argc or
                (iat,rpc) in self._window_show_contracts or any(x[0]==(iat,rpc) for x in pending)):
                raise ContextFault('invalid or duplicate show/default physical site')
            pending.append(((iat,rpc),(c,site,found[0],self.machine,self.program)))
        self._window_show_contracts.update(pending)

    def _window_show_request(self, request, default=False):
        if not self.machine._physical_pump or not self._source_graph or not self._physical_requests:
            raise ContextFault('show/default has no live physical request')
        active,signature,generation,witness=self._physical_requests[-1]
        elected=self._window_show_contracts.get((request.function,request.source_return_pc))
        if active is not request or generation is not self._callback_generation or elected is None:
            raise ContextFault('copied, retired or undeclared show/default request')
        c,site,owner,vm,program=elected;w=c.window;argc=4 if default else 2
        if (site not in c.default_sites if default else site!=c.show_site):
            raise ContextFault('wrong show/default request kind')
        if (owner is not signature or vm is not self.machine or program is not self.program or
            signature.convention!='stdcall' or signature.argc!=argc or len(request.arguments)!=argc or
            request.source_context is None or bytes(request.source_context)!=witness or
            request.source_context.inputMask!=CONTEXT_ALL or request.source_context.esp!=request.stack_pointer or
            request.source_context.eip!=site[0] or self.machine._owned_scope is not None or
            w.program_sha256!=self.program.sha256 or self._lookup(w.target) or
            w.target in self.compiler_callees or w.target in self.x87_callees or
            (self.side=='native' and w.target==self._native_source_entry)):
            raise ContextFault('show/default ownership, ABI or source identity mismatch')
        validate_source(request.source_context,site[0],site[2],self.program)
        frame=struct.pack(f'<{argc+1}I',site[2],*request.arguments)
        if self.read(request.stack_pointer,len(frame))!=frame:
            raise ContextFault('show/default request frame changed')
        for read in (self.read,self.machine.read):
            if (any(read(s[1],6)!=b'\xff\x15'+struct.pack('<I',s[0]) for s in
                    (w.register_site,w.create_site,c.show_site,*c.default_sites)) or
                hashlib.sha256(read(w.target,w.body_end-w.target)).hexdigest()!=w.body_sha256):
                raise ContextFault('show/default executable identity changed')
        return c,frame

    def _window_show_handle(self, hwnd, contract):
        state=self._window_handles.get(hwnd)
        if state is None or not state.get('live'):
            raise ContextFault('show/default handle is not a committed live incarnation')
        r=state['registration']
        if (r.contract is not contract.window or r.generation is not self._callback_generation or
            self._window_classes.get((r.module,r.name)) is not r):
            raise ContextFault('show/default registration retired or changed')
        return state

    @contextmanager
    def window_show(self, request, profile):
        with self._window_guard():
            c,_=self._window_show_request(request);hwnd,command=request.arguments
            state=self._window_show_handle(hwnd,c)
            if (command!=1 or state.get('shown') or state.get('showing') or
                id(request) in self._window_show_pending or type(profile) is not WindowShowProfile or
                type(profile.rect) is not tuple or len(profile.rect)!=4 or
                any(type(v) is not int for v in profile.rect) or
                any(not -32768<=v<=32767 for v in profile.rect[:2]) or
                any(not 0<v<=32767 for v in profile.rect[2:]) or
                type(profile.flags) is not int or profile.flags&~0x67 or not profile.flags&0x40):
                raise ContextFault('unsupported first-show request/profile')
            a=state['request'].arguments;old=tuple(v if v<0x80000000 else v-0x100000000 for v in a[4:8])
            if a[0]!=0x40008 or a[3]!=0x80080000 or (profile.flags&1 and profile.rect[2:]!=old[2:]) or (profile.flags&2 and profile.rect[:2]!=old[:2]):
                raise ContextFault('show flags/style disagree with explicit popup geometry')
            x,y,width,height=profile.rect
            position=struct.pack('<IIiiiiI',hwnd,0,x,y,width,height,profile.flags)
            wp=self.object(28,data=position)
            # NCCALCSIZE(TRUE): three RECTs plus a WINDOWPOS pointer (52 bytes).
            rect=struct.pack('<4i',x,y,x+width,y+height)
            ox,oy,ow,oh=old;oldrect=struct.pack('<4i',ox,oy,ox+ow,oy+oh)
            nc=self.object(52,data=rect+oldrect+oldrect+struct.pack('<I',wp))
            plan=[(0x46,0,wp)]
            if not profile.flags&1 or profile.flags&0x20:plan.append((0x83,1,nc))
            plan.extend(((0x47,0,wp),(0x1c,1,0),(0x86,1,0),(6,1,0)))
            lease=WindowMessageLease(hwnd,self._callback_generation,object())
            scope=dict(request=request,lease=lease,handle=state,contract=c,plan=tuple(plan),next=0,closed=False,
                       pointers=((wp,28),(nc,52)),position=position,profile=profile,nc=nc,wp=wp,client=rect,nc_tail=oldrect+oldrect+struct.pack('<I',wp),kind='show')
            state['showing']=True
            self._window_show_pending[id(request)]=(request,scope);self._window_message_sessions.append(scope)
            self.window_history.append(('showing',hwnd,profile.rect,profile.flags))
            try:
                yield lease
                self._check_physical_failure()
                if scope['next']!=len(scope['plan']):raise ContextFault('show omitted required profile messages')
                scope['closed']=True
            finally:
                if not self._window_message_sessions or self._window_message_sessions[-1] is not scope:
                    raise ContextFault('show scope corrupted')
                self._window_message_sessions.pop()

    def window_messages(self, request, lease):
        """Read-only exact payload plan for an authenticated current lease."""
        with self._window_guard():
            scope,_=self._window_message_scope(request,lease)
            return scope['plan']

    def _window_message_scope(self, request, lease):
        if not self._window_message_sessions:raise ContextFault('no active message lease')
        scope=self._window_message_sessions[-1];c,frame=self._window_show_request(request,scope['kind']=='default')
        if (scope['request'] is not request or scope['lease'] is not lease or scope['closed'] or
            lease.generation is not self._callback_generation or scope['contract'] is not c or
            self._window_show_handle(lease.hwnd,c) is not scope['handle']):
            raise ContextFault('copied, retired or mismatched message lease/incarnation')
        root=scope.get('root',scope)
        for p,n in root['pointers']:
            if self.spans.get(p)!=n:raise ContextFault('show transient retired or replaced')
        if self.read(root['wp'],28)!=root['position'] or self.read(root['nc']+16,36)!=root['nc_tail']:
            raise ContextFault('show WINDOWPOS/schema changed')
        return scope,frame

    @contextmanager
    def window_default(self, request):
        """Authority derives from the currently suspended original WNDPROC call."""
        with self._window_guard():
            c,_=self._window_show_request(request,True)
            if not self._window_callback_lineage or id(request) in self._window_show_pending:
                raise ContextFault('default lacks current original callback lineage')
            lineage=self._window_callback_lineage[-1];parent=lineage['scope'];args=lineage['arguments']
            if (parent['contract'] is not c or request.arguments!=args or lineage['default_started'] or
                not self._window_message_sessions or self._window_message_sessions[-1] is not parent):
                raise ContextFault('default request differs from current callback lineage')
            # Parent request is suspended. Authenticate this current physical request,
            # never substitute the outer ShowWindow CPU/frame for nested callbacks.
            state=self._window_show_handle(args[0],c)
            if state is not parent['handle']:raise ContextFault('default handle incarnation changed')
            root=parent.get('root',parent);msg=args[1];plan=[]
            if msg==0x47:
                flags=root['profile'].flags;x,y,width,height=root['profile'].rect
                if not flags&1:plan.append((5,0,(height<<16)|width))
                if not flags&2:plan.append((3,0,((y&0xffff)<<16)|(x&0xffff)))
            elif msg==6:
                if args[2]!=1 or args[3]!=0:raise ContextFault('unsupported activation default')
                plan.append((7,0,0))
            elif msg not in (0x46,0x83,0x86,0x1c,3,5,7):
                raise ContextFault('unsupported synchronous default message')
            lineage['default_started']=True
            lease=WindowMessageLease(args[0],self._callback_generation,object())
            scope=dict(request=request,lease=lease,handle=state,contract=c,plan=tuple(plan),next=0,
                       closed=False,kind='default',root=root,lineage=lineage,result=1 if msg==0x86 else 0)
            self._window_show_pending[id(request)]=(request,scope);self._window_message_sessions.append(scope)
            try:
                yield lease
                self._check_physical_failure()
                if scope['next']!=len(scope['plan']):raise ContextFault('default omitted required synchronous children')
                scope['closed']=True
            finally:
                if not self._window_message_sessions or self._window_message_sessions[-1] is not scope:
                    raise ContextFault('default scope corrupted')
                self._window_message_sessions.pop()

    def invoke_window_message(self, request, lease, message, wparam, lparam):
        with self._window_guard():
            scope,frame=self._window_message_scope(request,lease)
            if (any(type(v) is not int or not 0<=v<=0xffffffff for v in (message,wparam,lparam)) or
                scope['next']>=len(scope['plan']) or (message,wparam,lparam)!=scope['plan'][scope['next']]):
                raise ContextFault('unsupported message/order/payload')
            c=scope['contract'];previous_backend=self.backend
            if previous_backend=='native':
                self.machine.write(HEAP_BASE,bytes(self._heap))
                self.machine.write(self.program.data_start,bytes(self._image)[self.data_offset:])
                self.machine.write(STACK_BASE,bytes(self._stack))
            elif previous_backend!='machine':raise ContextFault('message requires live backing')
            arguments=(lease.hwnd,message,wparam,lparam)
            lineage=dict(scope=scope,arguments=arguments,default_started=False,default_done=False)
            self._window_callback_lineage.append(lineage)
            record=dict(target=c.window.target,arguments=arguments,entered=False,returned=False)
            self.callback_executions.append(record);self.backend='machine'
            try:
                result=self.machine._call_physical_callback(c.window.target,request.source_context,arguments,frame,
                                                            lambda:record.__setitem__('entered',True))
                record.update(returned=True,eax=result.eax)
            finally:
                self.backend=previous_backend
                if previous_backend=='native':
                    C.memmove(self._heap,self.machine.read(HEAP_BASE,self.heap_bytes),self.heap_bytes)
                    data=self.machine.read(self.program.data_start,self.program.size-self.data_offset)
                    C.memmove(C.addressof(self._image)+self.data_offset,data,len(data))
                    C.memmove(self._stack,self.machine.read(STACK_BASE,STACK_SIZE),STACK_SIZE)
                if not self._window_callback_lineage or self._window_callback_lineage[-1] is not lineage:
                    raise ContextFault('callback lineage corrupted')
                self._window_callback_lineage.pop()
            self._window_message_scope(request,lease)
            if lineage['default_started'] and not lineage['default_done']:
                raise ContextFault('callback default did not commit normally')
            # A handler may consume a message without calling DefWindowProc. Only
            # an actual default request obligates its derived SIZE/MOVE/focus calls.
            if result.eax!=(1 if message==0x86 and lineage['default_done'] else 0):
                raise ContextFault('unsupported show message result')
            root=scope.get('root',scope)
            if message==0x83:
                expected=root['client']
                if self.read(root['nc'],16)!=expected:raise ContextFault('unsupported popup client geometry')
            scope['next']+=1;self.window_history.append(('show_message',lease.hwnd,message,result.eax))
            return result.eax

    def _finish_window_show_request(self, request, value):
        elected=self._window_show_contracts.get((request.function,request.source_return_pc))
        if elected is None:return
        c,site,*_=elected
        # Existing creation callbacks retain their original physical fixture contract.
        if site in c.default_sites and not self._window_callback_lineage:
            if not self._window_sessions:raise ContextFault('default outside supported callback lifetime')
            return
        pending=self._window_show_pending.get(id(request))
        if pending is None or pending[0] is not request:
            raise ContextFault('show/default result lacks active authority')
        scope=pending[1];self._window_show_request(request,scope['kind']=='default')
        if type(value) is not int or value!=(0 if scope['kind']=='show' else scope['result']) or not scope['closed']:
            raise ContextFault('show/default result differs from normal physical disposition')
        if scope['kind']=='default':scope['lineage']['default_done']=True
        else:
            for p,n in scope['pointers']:
                if self.spans.get(p)!=n:raise ContextFault('show transient lifetime changed')
            for p,_ in scope['pointers']:self.release(p)
            scope['handle']['shown']=True;scope['handle']['showing']=False
            scope['handle']['client_paint_pending']=True
            self.window_history.append(('shown',scope['lease'].hwnd))
        del self._window_show_pending[id(request)]

    def dialog_callback(self, contract):
        """Elect a typed synchronous original DIALOGPROC boundary during setup."""
        if self.backend != 'initial' or type(contract) is not DialogCallbackContract:
            raise ContextFault('dialog callback declaration requires setup and typed contract')
        c = contract
        if (c.program_sha256 != self.program.sha256 or
                self.program.imports.get(c.service, '').lower() != 'user32.dll!dialogboxparama' or
                any(type(v) is not int for v in (c.service,c.call_pc,c.return_pc,c.target,c.body_end)) or
                not self.program.in_text(c.target) or not self.program.in_text(c.body_end-1) or
                not c.target < c.body_end <= c.target+4096 or not self.program.in_text(c.call_pc) or
                not self.program.in_text(c.return_pc) or c.return_pc != c.call_pc+6):
            raise ContextFault('invalid synchronous dialog callback identity')
        from .program import CLAW_SHA256
        if type(c.native_owned) is not bool or type(c.end_service) is not int:
            raise ContextFault('invalid dialog ownership or EndDialog declaration')
        if self.program.name == 'claw-v1.0' or self.program.sha256 == CLAW_SHA256:
            pinned = {
                (0x453989,0x45398f,0x453a10,0x453b0f):
                    'a5b7da2f873d90e9678dbb766107776d4c76a3ce05f4eea3835dac10d1832c16',
                (0x42bb7b,0x42bb81,0x49b730,0x49b83d):
                    '253fb62a4a33e89b2b6e3ac0ec33fbbf7f7ca536159e99bd4db6a61d22fc71e3',
                (0x42bb7b,0x42bb81,0x49b160,0x49b393):
                    'e9c3e3f6220163984476c7b77733d431504b22d871fc674565c7ff2016d4153e',
                (0x42bb7b,0x42bb81,0x49b630,0x49b72b):
                    'd8d4f3f1cf5f6ec2f6becf08c4f3fe2830cffe71da5e10116db49105bf88ad6d',
            }
            if (c.program_sha256 != CLAW_SHA256 or c.service != 0x546d2c or
                    pinned.get((c.call_pc,c.return_pc,c.target,c.body_end)) != c.body_sha256 or
                    c.native_owned != (c.target == 0x49b730) or c.end_service != 0x546d34):
                raise ContextFault('Claw dialog callback differs from the pinned original boundary')
        if c.end_service:
            end = self._lookup(c.end_service)
            if (self.program.imports.get(c.end_service, '').lower() != 'user32.dll!enddialog' or
                    not end or end[0].convention != 'stdcall' or end[0].argc != 2):
                raise ContextFault('dialog EndDialog service must be declared stdcall2')
        code = self.pristine_image[c.call_pc-self.program.base:c.return_pc-self.program.base]
        body = self.pristine_image[c.target-self.program.base:c.body_end-self.program.base]
        if code != b'\xff\x15'+struct.pack('<I',c.service) or hashlib.sha256(body).hexdigest() != c.body_sha256:
            raise ContextFault('dialog CALL or callback body hash mismatch')
        if self._lookup(c.target) is not None or c.target in self.compiler_callees or c.target in self.x87_callees:
            raise ContextFault('dialog callback must execute unchanged original code')
        found = self._lookup(c.service)
        if not found or found[0].convention != 'stdcall' or found[0].argc != 5:
            raise ContextFault('dialog physical service must be declared stdcall5')
        key=(c.service,c.return_pc,c.target)
        if key in self._dialog_contracts:
            raise ContextFault('dialog callback site already declared')
        self._dialog_contracts[key] = c
        self._dialog_owners[key] = (self.machine,self.program,found[0],c,
                                    self._lookup(c.end_service)[0] if c.end_service else None)
        if not hasattr(self, '_dialog_hooks'):
            self._dialog_hooks = set()
        if c.native_owned and c.target not in self._dialog_hooks:
            def reject_original_owner(machine, address):
                if (self.side == 'native' and self.machine._physical_pump and
                        any(d.native_owned and d.target == address for d in self._dialog_contracts.values())):
                    raise ContextFault('selected native dialog owner reached original instructions')
            self.machine.observe(c.target, reject_original_owner)
            self._dialog_hooks.add(c.target)

    def _begin_dialog_request(self, call):
        if self._dialog_sessions and any(c.service == call.function for c in self._dialog_contracts.values()):
            raise ContextFault('reentrant modal dialog is not supported')
        key = (call.function, call.source_return_pc, call.arguments[3] if len(call.arguments) == 5 else None)
        c = self._dialog_contracts.get(key)
        if c is None:
            if any(k[:2] == key[:2] for k in self._dialog_contracts):
                raise ContextFault('dialog request has an unelected callback operand')
            return None
        owner = self._dialog_owners.get(key)
        if owner is None or owner[3] is not c:
            raise ContextFault('dialog declaration changed after setup')
        if not c.end_service:
            return None
        state = dict(request=call, contract=c, hwnd=None, invoking=False, ended=False, count=0, result=None)
        self._dialog_sessions.append(state)
        return state

    def _dialog_end_request(self, call):
        if not self._dialog_sessions:
            return None
        state = self._dialog_sessions[-1]
        if call.function != state['contract'].end_service:
            return None
        c = state['contract']
        owner = self._dialog_owners[(c.service,c.return_pc,c.target)]
        if (not state['invoking'] or state['ended'] or len(call.arguments) != 2 or
                call.arguments[0] != state['hwnd'] or self._lookup(c.end_service)[0] is not owner[4]):
            raise ContextFault('EndDialog lacks a live matching callback HWND')
        return state

    def _finish_dialog_request(self, state, value):
        if state is not None and not (
                state['count'] == 0 and ((value or 0) & 0xffffffff) == 0xffffffff or
                state['count'] > 0 and state['ended'] and ((value or 0) & 0xffffffff) == state['result']):
            raise ContextFault('modal result requires actual callback EndDialog disposition')

    def _begin_physical_graph(self):
        if not (self._dialog_contracts or self._window_contracts):
            return
        if not self._source_graph or getattr(self,'_guest_adapter',None) is not None:
            raise ContextFault('dialog callback requires an ordinary source graph without guest EH')
        self.machine.begin_physical_callbacks(self._consume_physical_operation, self.callback_timeout_seconds)

    def _end_physical_graph(self):
        self.machine.end_physical_callbacks()
        self._enumeration_graph = False
        self._enumeration_entry = None
        self._window_classes.clear(); self._window_handles.clear(); self._window_pending.clear()
        self._window_sessions.clear()
        self._dialog_sessions.clear()
        self._dialog_entry = None
        self._window_show_pending.clear(); self._window_message_sessions.clear(); self._window_callback_lineage.clear()
        self._physical_requests.clear()
        self._callback_generation = object()

    def _consume_physical_operation(self):
        if not self._source_budget.value:
            raise SourceBudgetFault('source graph operations exhausted')
        self._source_budget.value -= 1

    def invoke_dialog_callback(self, request, arguments):
        """Invoke only the active request; callback failure poisons this graph."""
        if not self.machine._physical_pump or not self._source_graph or not self._physical_requests:
            raise ContextFault('dialog callback has no live physical request')
        try:
            if self._physical_failure is not None:
                raise self._physical_failure
            return self._invoke_dialog_callback(request,arguments)
        except BaseException as error:
            if self._source_graph and self._physical_requests:
                self._physical_failure = self._physical_failure or error
            raise

    def _invoke_dialog_callback(self, request, arguments):
        """Invoke the actual arg-3 DIALOGPROC of this live physical request.

        Four uint32 message operands; no entry, frame, CPU or return-PC override.
        This capability ends when its synchronous DialogBox effect exits.
        """
        if not self.machine._physical_pump or not self._source_graph or not self._physical_requests:
            raise ContextFault('dialog callback has no live physical request')
        active, signature, generation, witness = self._physical_requests[-1]
        if active is not request or generation is not self._callback_generation:
            raise ContextFault('dialog callback request is copied, retired or belongs to another graph')
        key = (request.function,request.source_return_pc,request.arguments[3] if len(request.arguments) == 5 else None)
        contract = self._dialog_contracts.get(key)
        if contract is None or request.source_context is None or bytes(request.source_context) != witness:
            raise ContextFault('dialog callback request lacks its immutable source contract')
        c = contract
        owner = self._dialog_owners.get(key)
        if (owner is None or owner[0] is not self.machine or owner[1] is not self.program or
                owner[2] is not signature or owner[3] is not c):
            raise ContextFault('dialog callback belongs to another VM, program or physical registration')
        if (signature.convention != 'stdcall' or signature.argc != 5 or len(request.arguments) != 5 or
                request.arguments[3] != c.target or self._lookup(c.target) is not None or
                c.program_sha256 != self.program.sha256 or request.source_context.inputMask != CONTEXT_ALL or
                request.source_context.esp != request.stack_pointer or request.source_context.eip != c.service or
                self.machine._owned_scope is not None or
                (self.side == 'native' and c.target == self._native_source_entry)):
            raise ContextFault('dialog callback target, source input or ABI mismatch')
        validate_source(request.source_context,c.service,c.return_pc,self.program)
        if (type(arguments) is not tuple or len(arguments) != 4 or
                any(type(v) is not int or not 0 <= v <= 0xffffffff for v in arguments)):
            raise ContextFault('dialog callback requires exactly four uint32 operands')
        frame=struct.pack('<6I',c.return_pc,*request.arguments)
        if self.read(request.stack_pointer,len(frame)) != frame:
            raise ContextFault('dialog physical request frame changed')
        if any(read(c.call_pc,6) != b'\xff\x15'+struct.pack('<I',c.service) or
               hashlib.sha256(read(c.target,c.body_end-c.target)).hexdigest() != c.body_sha256
               for read in (self.read,self.machine.read)):
            raise ContextFault('dialog executable identity changed')
        state = self._dialog_sessions[-1] if self._dialog_sessions else None
        if c.end_service:
            if (state is None or state['request'] is not request or state['contract'] is not c or
                    state['invoking'] or state['ended'] or not arguments[0] or
                    (state['count'] == 0 and (arguments[1] != 0x110 or arguments[3] != request.arguments[4])) or
                    (state['count'] > 0 and (arguments[0] != state['hwnd'] or arguments[1] == 0x110))):
                raise ContextFault('dialog message violates active modal lifetime')
            state['hwnd'] = arguments[0]
            state['invoking'] = True
        previous_backend = self.backend
        if previous_backend == 'native':
            self.machine.write(HEAP_BASE,bytes(self._heap))
            self.machine.write(self.program.data_start,bytes(self._image)[self.data_offset:])
            self.machine.write(STACK_BASE,bytes(self._stack))
        elif previous_backend != 'machine':
            raise ContextFault('dialog callback requires live native or machine backing')
        self.backend='machine'
        self.callback_executions.append(dict(target=c.target,arguments=arguments,entered=False,returned=False))
        record = self.callback_executions[-1]
        try:
            result = self.machine._call_physical_callback(c.target,request.source_context,arguments,frame,
                lambda:record.__setitem__('entered',True),
                native_dispatch=(lambda sp: self._dispatch_native_dialog(c, arguments, sp))
                    if c.native_owned and self.side == 'native' else None)
            if state is not None:
                state['count'] += 1
            record['returned']=True
            record['eax']=result.eax
            return result.eax
        finally:
            if state is not None:
                state['invoking'] = False
            self.backend=previous_backend
            if previous_backend == 'native':
                C.memmove(self._heap,self.machine.read(HEAP_BASE,self.heap_bytes),self.heap_bytes)
                data=self.machine.read(self.program.data_start,self.program.size-self.data_offset)
                C.memmove(C.addressof(self._image)+self.data_offset,data,len(data))
                C.memmove(self._stack,self.machine.read(STACK_BASE,STACK_SIZE),STACK_SIZE)

    def _dispatch_native_dialog(self, contract, arguments, frame):
        """Borrow the selected ordinary module for an owned stdcall4 callback.

        Suspend source-entry authority. The separate host-issued CPU lease
        permits descendants at real game continuations, never an OS source RET.
        """
        if self._dialog_entry is None or self.backend != 'machine' or self._dialog_native_frame:
            raise ContextFault('dialog has no available selected native callback owner')
        self._consume_physical_operation()
        if time.monotonic() >= self.machine._physical_deadline:
            raise ContextFault('physical callback graph deadline exhausted')
        self._copy_machine_to_native()
        saved_host = NativeHost.from_buffer_copy(self._host)
        cpu = NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL)
        for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS):
            setattr(cpu, name, self.machine.register(register))
        cpu.eip, cpu.esp, cpu.fsHead, cpu.preserveMask = contract.target, frame, self.machine.fs_head, 0x472
        lease = NativeCallbackCPU(C.sizeof(NativeCallbackCPU), 1, contract.target, frame,
                                  next(_callback_activations), cpu)
        request = self._physical_requests[-1]
        self._dialog_cpu_scope = (lease, bytes(lease)[:24], self.machine, self.program,
                                  self._callback_generation, contract, request)
        self._host.entryStackPointer = frame
        self._host.sourceContext = None
        self._host.sourceReturnPC = 0
        self._host.callbackCPU = C.pointer(lease)
        self._dialog_native_frame = frame
        self.backend = 'native'
        result = U32()
        try:
            words = (U32 * 4)(*arguments)
            completed = self._dialog_entry(contract.target, 0, words, 4, C.byref(self._host), C.byref(result))
            self._validate_dialog_cpu()
            self._check_physical_failure()
            if time.monotonic() >= self.machine._physical_deadline:
                raise ContextFault('physical callback graph deadline exhausted')
            if self._host.fault == 2:
                raise Halt()
            if not completed or self._host.fault:
                raise ContextFault('selected native dialog callback did not return')
            if (self._host.entryStackPointer != frame or self._host.sourceContext or
                    self._host.sourceReturnPC or self._host.compilerContext or self._host.guestSession or
                    C.cast(self._host.remainingOperations, C.c_void_p).value !=
                    C.cast(saved_host.remainingOperations, C.c_void_p).value or
                    self.get(frame) != PHYSICAL_CALLBACK_RETURN):
                raise ContextFault('native dialog changed borrowed ABI scope or return word')
            if lease.cpu.esp != frame:
                raise ContextFault('native callback did not restore its live CPU frame')
            lease.cpu.eax = result.value
            for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS):
                self.machine.uc.reg_write(register, getattr(lease.cpu, name))
            self.machine.fs_head = lease.cpu.fsHead
            return result.value
        finally:
            if self._source_stop is not None:
                stop = self._source_stop
                proof = (self._callback_generation, stop['function'], stop['return_pc'],
                         tuple(stop['registers'][n] for n in CONTEXT_FIELDS))
                if proof == self._source_stop_proof:
                    for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS):
                        self.machine.uc.reg_write(register, stop['registers'][name])
                    self.machine.fs_head = stop['registers']['fsHead']
            self.machine.write(HEAP_BASE, bytes(self._heap))
            self.machine.write(self.program.data_start, bytes(self._image)[self.data_offset:])
            self.machine.write(STACK_BASE, bytes(self._stack))
            self.backend = 'machine'
            self._dialog_native_frame = 0
            self._dialog_cpu_scope = None
            self._host.entryStackPointer = saved_host.entryStackPointer
            self._host.sourceContext = saved_host.sourceContext
            self._host.sourceReturnPC = saved_host.sourceReturnPC
            self._host.compilerContext = saved_host.compilerContext
            self._host.remainingOperations = saved_host.remainingOperations
            self._host.guestSession = saved_host.guestSession
            self._host.callbackCPU = saved_host.callbackCPU

    def _validate_dialog_cpu(self, raw=None):
        scope = self._dialog_cpu_scope
        if scope is None:
            if self._host.callbackCPU or (raw is not None and (raw.callbackCPU or raw.callbackActivation)):
                raise ContextFault('callback CPU has no live owner')
            return
        lease, header, machine, program, generation, contract, request = scope
        key = (contract.service, contract.return_pc, contract.target)
        owner = self._dialog_owners.get(key)
        service = self._lookup(contract.service)
        if (not self._source_graph or not self.machine._physical_pump or self.side != 'native' or
                self.backend != 'native' or owner is None or service is None or
                owner[0] is not machine or owner[1] is not program or owner[2] is not request[1] or
                owner[3] is not contract or service[0] is not request[1] or
                C.cast(self._host.callbackCPU, C.c_void_p).value != C.addressof(lease) or
                bytes(lease)[:24] != header or machine is not self.machine or program is not self.program or
                generation is not self._callback_generation or not any(r is request for r in self._physical_requests) or
                self._dialog_contracts.get((contract.service, contract.return_pc, contract.target)) is not contract or
                self._host.entryStackPointer != lease.entryStackPointer or
                self._dialog_native_frame != lease.entryStackPointer or self._host.sourceContext or
                self._host.sourceReturnPC or self._host.compilerContext or self._host.guestSession):
            raise ContextFault('callback CPU owner, target or lifetime changed')
        cpu = lease.cpu
        if (cpu.size, cpu.version, cpu.inputMask, cpu.outputMask, cpu.preserveMask,
                cpu.reserved0, cpu.reserved1) != (72, 1, CONTEXT_ALL, CONTEXT_ALL, 0x472, 0, 0):
            raise ContextFault('malformed callback CPU header')
        # Validate CPU data without treating the synthetic OS continuation as a
        # source capability. Only descendant CALLs have real return PCs.
        checked = NativeSourceContext.from_buffer_copy(cpu)
        checked.eip = contract.target
        validate_source(checked, contract.target, contract.return_pc, self.program)
        if raw is not None and (raw.compilerContext or raw.x87ArgumentCount or raw.x87State or
                                raw.x87Operation or raw.sourceTransferKind):
            raise ContextFault('callback CPU cannot grant compiler, x87 or tail authority')
        if raw is not None and (raw.sourceContext or raw.callbackCPU or raw.callbackActivation):
            if (C.cast(raw.callbackCPU, C.c_void_p).value != C.addressof(lease) or
                    raw.callbackActivation != lease.activation or not raw.sourceContext or
                    raw.compilerContext or raw.x87ArgumentCount or raw.sourceTransferKind or
                    C.cast(raw.sourceContext, C.c_void_p).value == C.addressof(lease.cpu) or
                    any(getattr(raw.sourceContext.contents, n) != getattr(cpu, n) for n in CONTEXT_FIELDS)):
                raise ContextFault('callback CPU request is copied, stale or differs from live CPU')

    def source_tail_edge(self, caller, site, target):
        """Elect one original direct JMP, retaining its real caller frame."""
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        from capstone.x86 import X86_OP_IMM
        if (self.backend != 'initial' or any(type(v) is not int for v in (caller, site, target)) or
                not self.program.in_text(caller) or not caller <= site < caller + 0x1000 or
                not self.program.in_text(site) or not self.program.in_text(target)):
            raise ContextFault('source tail requires bounded original integer sites during setup')
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
        decoded = {i.address: i for i in md.disasm(
            self.pristine_image[caller-self.program.base:site-self.program.base+15], caller)}
        jump = decoded.get(site)
        if (jump is None or jump.mnemonic != 'jmp' or len(jump.operands) != 1 or
                jump.operands[0].type != X86_OP_IMM or jump.operands[0].imm != target):
            raise ContextFault('source tail requires the exact original direct JMP target')
        if (caller, site) in self._tail_specs or site in self._boundary_sites:
            raise ContextFault('ambiguous source tail site')
        self._tail_specs[(caller, site)] = target
        self._boundary_sites[site] = (caller, 'tail')
        if site not in self._boundary_hooks:
            self.machine.observe(site, self._observe_original_boundary)
            self._boundary_hooks.add(site)

    def observe_source_boundary(self, entry, call_pc, callee_return_pc, ret_pc):
        """Opt in to original CALL/RET CPU observations for one source caller.

        Site metadata is decoded from pristine original code. Observations are
        read-only; they neither execute a dependency nor repair a source frame.
        """
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        from capstone.x86 import X86_OP_IMM
        if self.backend != 'initial' or any(type(v) is not int for v in (entry,call_pc,callee_return_pc,ret_pc)):
            raise ContextFault('source boundary observations require case setup and integer sites')
        if not self.program.in_text(entry) or not entry <= call_pc < callee_return_pc <= ret_pc < entry + 0x1000 or not self.program.in_text(ret_pc):
            raise ContextFault('invalid bounded source caller observation sites')
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
        code = self.pristine_image[entry-self.program.base:ret_pc-self.program.base+3]
        decoded = {i.address:i for i in md.disasm(code, entry)}
        call, ret = decoded.get(call_pc), decoded.get(ret_pc)
        if (call is None or call.mnemonic != 'call' or call.address + call.size != callee_return_pc or
                call.operands[0].type != X86_OP_IMM or ret is None or ret.mnemonic != 'ret' or ret.operands):
            raise ContextFault('source observations require original direct CALL and plain RET')
        if entry in self._boundary_specs or any(pc in self._boundary_sites for pc in (call_pc,ret_pc)):
            raise ContextFault('ambiguous source caller observation')
        self._boundary_specs[entry] = (call_pc,callee_return_pc,ret_pc,call.operands[0].imm)
        for pc, phase in ((call_pc,'call'),(ret_pc,'ret')):
            self._boundary_sites[pc] = (entry,phase)
            if pc not in self._boundary_hooks:
                self.machine.observe(pc,self._observe_original_boundary)
                self._boundary_hooks.add(pc)
        self._host.bytes = C.cast(self._bytes_callback,C.c_void_p)

    def _source_boundary(self, entry, phase, context):
        record = (entry,phase,tuple(getattr(context,n) for n in CONTEXT_FIELDS),self._digest())
        if phase in ('tail','tail-return'):
            # A preceding CALL's inactive return word may be overwritten by
            # the tail target. Observe it while the original JMP frame is live.
            record += (hashlib.sha256(self.read(STACK_BASE,STACK_SIZE)).digest(),)
        self.source_boundaries.append(record)

    def _observe_original_boundary(self, machine, pc):
        site = self._boundary_sites.get(pc)
        if self.side == 'original' and self._source_graph and site and not machine._source_return_boundary(pc):
            context = NativeSourceContext()
            for name,register in zip(CONTEXT_FIELDS,CONTEXT_REGISTERS):
                setattr(context,name,machine.register(register))
            context.fsHead = machine.fs_head
            self._source_boundary(*site,context)
            if site[1] == 'tail': self._tail_taken.add(site[0])

    def _observe_native_bytes(self, user, token, count):
        try:
            entry = self._native_source_entry
            if (self._source_graph and self._host.sourceContext and entry in self._boundary_called and
                    entry not in self._boundary_returned and token == self._host.entryStackPointer and count == 4):
                context = self._host.sourceContext.contents
                if context.esp == token:
                    self._source_boundary(entry,'ret',context)
                    self._boundary_returned.add(entry)
            return self._arena_bytes(user,token,count)
        except BaseException as error:
            self.errors.append(error)
            self._host.fault = self._host.fault or 5
            return None

    def stub(self, name, convention, argc, effect, arguments=()):
        """A fresh fake function address, for vtable slots and callbacks a case supplies."""
        address = self._next_stub
        if address >= STUB_BASE + STUB_SIZE:
            raise HarnessError("out of stub addresses")
        self._next_stub += 1
        self._case_fixtures[address] = (Signature(address, name, convention, argc, tuple(arguments)), effect)
        self._source_fixture_capabilities[address] = SourceFixtureCapability(
            address, self._case_fixtures[address], self._case_fixtures)
        return address

    def override(self, address, effect):
        """Replace the effect of a family fixture for this case only."""
        if address not in self.fixtures:
            raise HarnessError(f"{address:#x} is not a declared fixture")
        self._case_overrides[address] = effect

    def _check_physical_failure(self):
        # Once a callback stops, public effects cannot mutate its captured prefix.
        if (self._source_graph or self._enumeration_graph) and self._physical_failure is not None:
            raise self._physical_failure

    def object(self, size, name=None, words=None, data=None, fill=None):
        """A new live heap object. Returns its token."""
        self._check_physical_failure()
        token = self._bump
        self._bump = (token + max(size, 1) + 31) & ~15  # at least 16 bytes of dead space between objects
        if self._bump > HEAP_BASE + self.heap_bytes:
            raise HarnessError("heap exhausted; raise heap_bytes in the family's oracle section")
        self.spans[token] = size
        if name:
            self.names[token] = name
        if fill is not None:
            self.write(token, bytes([fill]) * size)
        if words:
            self.put(token, *words)
        if data:
            self.write(token, data)
        self._spans_changed()
        return token

    def release(self, token):
        self._check_physical_failure()
        if token not in self.spans:
            raise HarnessError(f"release of {token:#x}, which is not a live object")
        del self.spans[token]
        self.freed.append(token)
        self._spans_changed()

    def calls_so_far(self, function):
        """How many times this side has called `function`, counting the call being served."""
        return sum(1 for event in self.events if event[0] == function)

    # ---- Memory, on whichever side is current -----------------------------------
    def _locate(self, address, count):
        if HEAP_BASE <= address and address + count <= HEAP_BASE + self.heap_bytes:
            return "heap", address - HEAP_BASE
        if self.program.base <= address and address + count <= self.program.base + self.program.size:
            return "image", address - self.program.base
        if STACK_BASE <= address and address + count <= STACK_BASE + STACK_SIZE:
            return "stack", address - STACK_BASE
        raise HarnessError(f"{address:#x}+{count} is outside the heap, the image and the stack")

    def read(self, address, count):
        if self.backend == "machine":
            return self.machine.read(address, count)
        region, offset = self._locate(address, count)
        if self.backend == "native":
            buffer = {"heap": self._heap, "image": self._image, "stack": self._stack}[region]
            return C.string_at(C.addressof(buffer) + offset, count)
        return bytes(self._initial[region][offset:offset + count])

    def write(self, address, data):
        self._check_physical_failure()
        data = bytes(data)
        if self.backend == "machine":
            self.machine.write(address, data)
            return
        region, offset = self._locate(address, len(data))
        if self.backend == "native":
            buffer = {"heap": self._heap, "image": self._image, "stack": self._stack}[region]
            C.memmove(C.addressof(buffer) + offset, data, len(data))
        else:
            self._initial[region][offset:offset + len(data)] = data

    def get(self, address):
        return struct.unpack("<I", self.read(address, 4))[0]

    def put(self, address, *words):
        self.write(address, struct.pack(f"<{len(words)}I", *(w & 0xFFFFFFFF for w in words)))

    def cstr(self, address, limit=512):
        data = self.read(address, 1)
        while data[-1] and len(data) < limit:
            data += self.read(address + len(data), 1)
        return data.rstrip(b"\0")

    # ---- Names for messages ------------------------------------------------------
    def describe(self, address):
        if address in self._case_fixtures:
            return f"{address:#x} ({self._case_fixtures[address][0].name})"
        slot = self.stub_function.get(address, address)
        if slot in self.program.imports:
            return f"{slot:#x} ({self.program.imports[slot]})"
        if address in self.fixtures and self.fixtures[address][0].name:
            return f"{address:#x} ({self.fixtures[address][0].name})"
        symbol = self.symbols.get(address)
        if symbol:
            return f"{address:#x} ({symbol})"
        for token, size in self.spans.items():
            if token <= address < token + size:
                return f"{address:#x} ({self.names.get(token, 'object')}+{address - token:#x})"
        return f"{address:#x}"

    # ---- Case lifecycle ------------------------------------------------------------
    def _begin_case(self, random_source):
        if self._source_graph or getattr(self, '_enumeration_graph', False):
            raise ContextFault('cannot reset a live callback graph')
        heap = bytearray(random_source.randbytes(self.heap_bytes)) if random_source else bytearray(self.heap_bytes)
        self._initial = {"heap": heap, "image": bytearray(self.pristine_image), "stack": bytearray(STACK_SIZE)}
        self.spans, self.names, self.freed, self.events = {}, {}, [], []
        self.errors, self.bridged = [], []
        self._boundary_specs, self._boundary_sites, self._tail_specs = {}, {}, {}
        self._tail_taken = set()
        self.source_boundaries = []
        self._boundary_called, self._boundary_returned = set(), set()
        self._native_source_entry = None
        self._window_contracts = {}
        self._window_show_contracts = {}
        self._window_classes, self._window_handles, self._window_pending = {}, {}, {}
        self._window_sessions, self.window_history = [], []
        self._window_show_pending, self._window_message_sessions, self._window_callback_lineage = {}, [], []
        self._dialog_sessions = []
        self._dialog_entry = None
        self._dialog_native_frame = 0
        self._dialog_cpu_scope = None
        self._dialog_contracts = {}
        self._dialog_owners = {}
        self._enumeration_contracts = {}
        self._enumeration_graph = False
        self._enumeration_entry = None
        self._enumeration_depth = 0
        self._enumeration_frame = 0
        self._physical_requests = []
        self._callback_generation = object()
        self.callback_timeout_seconds = 30.0
        self.callback_executions = []
        self._physical_failure = None
        if hasattr(self,'_host'):
            self._host.bytes = C.cast(self._arena_bytes,C.c_void_p)
        self._bump = HEAP_BASE + 0x40
        # Retire capabilities before replacing the registry, including when a
        # new case reuses the same numeric stub addresses.
        if hasattr(self, '_case_fixtures'):
            self._case_fixtures.clear()
        self._case_fixtures, self._case_overrides = {}, {}
        self._source_fixture_capabilities = {}
        self._next_stub = self.machine.first_free_stub
        self.backend, self.side = "initial", "setup"
        self._stack_input = ()
        self._stack_input_frozen = False
        self._entry_ebp = None
        self._entry_x87_status = None
        self._entry_x87_profile = None

    def initial_stack(self, regions):
        """Opt-in ordinary local bytes, relative to entry ESP; never entry operands.

        Setup only. Copy the region list now and freeze it with the other inputs.
        Raw setup writes to stack retain their existing context-only semantics.
        """
        if self.backend != "initial" or self.side != "setup" or self._stack_input_frozen:
            raise HarnessError("initial stack input is only allowed during setup")
        if not isinstance(regions, (tuple, list)) or len(regions) > 256:
            raise HarnessError("initial stack input must be a sequence of at most 256 regions")
        checked = []
        for region in regions:
            if not isinstance(region, (tuple, list)) or len(region) != 2:
                raise HarnessError("initial stack region must be (offset, bytes)")
            offset, data = region
            if (type(offset) is not int or type(data) is not bytes or not data or
                    offset < STACK_BASE - STACK_TOP or offset >= 0 or offset + len(data) > 0):
                raise HarnessError("initial stack region must be nonempty bytes below entry ESP within stack bounds")
            if any(offset < old + len(payload) and old < offset + len(data) for old, payload in checked):
                raise HarnessError("initial stack regions overlap")
            checked.append((offset, data))
        self._stack_input = tuple(sorted(checked))

    def entry_x87_status(self, value):
        """Elect masked sticky exception flags (bits 0..5), once during setup.

        Both ordinary runs start with these flags, the program CW and an empty
        stack at TOP 0. Condition codes, stack faults, ES/B and unmasked exceptions
        are intentionally outside this bounded case-input profile.
        """
        if self.backend != 'initial' or self.side != 'setup' or self._stack_input_frozen:
            raise HarnessError('entry x87 status is only allowed during setup')
        if (type(value) is not int or not 0 <= value <= 0x3f or self._entry_x87_status is not None or
                self._entry_x87_profile is not None or
                self.machine.initial_control_word & 0x3f != 0x3f):
            raise HarnessError('entry x87 status must be one masked six-bit exception word per case')
        self._entry_x87_status = value

    def entry_x87(self, profile):
        """Elect one exact contiguous owned-entry stack; copy validated setup input."""
        if self.backend != 'initial' or self.side != 'setup' or self._stack_input_frozen:
            raise HarnessError('entry x87 profile is only allowed during setup')
        if self._entry_x87_profile is not None or self._entry_x87_status is not None:
            raise HarnessError('entry x87 setup may be elected only once per case')
        if type(profile) is not dict or set(profile) != {'control', 'status', 'slots'}:
            raise HarnessError('entry x87 profile requires exactly control, status and slots')
        control, status, slots = (profile[k] for k in ('control', 'status', 'slots'))
        if not supported_x87_control(control):
            raise HarnessError('unsupported entry x87 control word')
        if type(status) is not int or status < 0 or status & ~0x7f3f:
            raise HarnessError('entry x87 status supports sticky flags, condition codes and TOP only')
        if type(slots) not in (tuple, list) or len(slots) > 8:
            raise HarnessError('entry x87 slots must be a contiguous sequence of at most eight values')
        checked = []
        for slot in slots:
            if type(slot) not in (tuple, list) or len(slot) != 2:
                raise HarnessError('entry x87 slot requires significand and sign/exponent')
            significand, exponent = slot
            if (type(significand) is not int or not 0 <= significand < 1 << 64 or
                    type(exponent) is not int or not 0 <= exponent <= 0xffff or
                    bool(significand & (1 << 63)) != bool(exponent & 0x7fff)):
                raise HarnessError('entry x87 slot has an unsupported extended encoding')
            checked.append((significand, exponent))
        self._entry_x87_profile = (control, status, tuple(checked))

    def _check_entry_x87_profile(self, function):
        if (self._entry_x87_profile is not None and
                function not in self.x87_environments and function not in self.x87_results):
            raise HarnessError('entry x87 profile requires a declared owned x87 entry')
        if (self._entry_x87_profile is not None and function in self.x87_results and
                len(self._entry_x87_profile[2]) == 8):
            raise HarnessError('entry x87 result profile would overflow the live stack')

    def _reset_entry_x87(self):
        self.machine.reset_x87()
        if self._entry_x87_profile is not None:
            self.machine.set_x87_state(*self._entry_x87_profile)
        elif self._entry_x87_status is not None:
            self.machine.set_x87_state(self.machine.initial_control_word, self._entry_x87_status, ())

    def entry_frame_pointer(self, value):
        """Elect the caller's EBP at this case's ordinary outer entry; setup only.

        The original side enters the owned function with EBP = value and must return it
        unchanged. Native code never sees the value: a direct ordinary zero-argument CALL from
        the owned native entry to a declared compiler-context callee executes that unchanged
        original with EBP = value, as the original CALL that inherits its caller's EBP does.
        Sites reached after the original changes EBP keep explicit compiler-context transport.
        """
        if self.backend != "initial" or self.side != "setup" or self._stack_input_frozen:
            raise HarnessError("entry frame pointer is only allowed during setup")
        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF or self._entry_ebp is not None:
            raise HarnessError("entry frame pointer must be one 32-bit integer per case")
        self._entry_ebp = value

    def _native_entry_frame(self, raw):
        """Inherited caller EBP for a native ordinary CALL of a compiler callee, or a ContextFault."""
        declared = self.compiler_callees[raw.function]
        if (self._entry_ebp is None or self._frame_entry is None or self._bridge_depth or
                self._host.sourceContext or self._host.compilerContext or
                getattr(self, '_guest_adapter', None) is not None or
                raw.argumentCount or raw.receiver or raw.receiver2 or raw.stackPointer or raw.x87ArgumentCount or
                raw.x87State or raw.x87Operation or raw.callbackCPU or raw.callbackActivation or
                declared['input_mask'] != CONTEXT_REQUIRED or declared['output_mask'] != CONTEXT_REQUIRED):
            raise ContextFault(f'{raw.function:#x}: inherited entry EBP requires an elected entry frame pointer and a '
                               'direct zero-operand CALL of a minimal compiler callee from an ordinary outer entry')
        return self._entry_ebp

    def _ordinary_stack_input(self, frame):
        if (type(frame) is not int or frame & 3 or
                frame < STACK_BASE or frame + 4 > STACK_BASE + STACK_SIZE):
            raise HarnessError("ordinary incoming frame is unaligned or outside the bounded stack")
        for offset, data in self._frozen_stack_input:
            if frame + offset < STACK_BASE:
                raise HarnessError("initial stack input falls below bounded stack at this entry ESP")
        return self._frozen_stack_input

    def _freeze(self):
        self._frozen = (bytes(self._initial["heap"]), bytes(self._initial["image"]), dict(self.spans), self._bump,
                        dict(self.names))
        self._frozen_stack_input = self._stack_input
        self._stack_input_frozen = True

    def _reset_run(self):
        if self._enumeration_graph:
            raise ContextFault('cannot reset a live callback graph')
        heap, image, spans, bump, names = self._frozen
        self.spans, self.names, self._bump = dict(spans), dict(names), bump
        self.freed, self.events, self.errors, self.bridged = [], [], [], []
        self._window_classes, self._window_handles, self._window_pending = {}, {}, {}
        self._window_sessions, self.window_history = [], []
        self._window_show_pending, self._window_message_sessions, self._window_callback_lineage = {}, [], []
        self._dialog_sessions = []
        self._dialog_native_frame = 0
        self._dialog_cpu_scope = None
        self._source_stop = None
        self._source_stop_proof = None
        self._physical_requests = []
        self._callback_generation = object()
        self.callback_executions = []
        self._physical_failure = None
        self.source_boundaries = []
        self._boundary_called, self._boundary_returned = set(), set()
        self._tail_taken = set()

    def _spans_changed(self):
        if self.side != "native":
            return
        ordered = sorted(self.spans.items())
        self._span_array = (Span * max(len(ordered), 1))(*(Span(token, size) for token, size in ordered))
        self._arena.spans = C.cast(self._span_array, C.POINTER(Span))
        self._arena.spanCount = len(ordered)

    def _digest(self):
        state = hashlib.blake2b(digest_size=16)
        state.update(self.read(HEAP_BASE, self.heap_bytes))
        state.update(self.read(self.program.data_start, self.program.size - self.data_offset))
        return state.digest()

    # ---- Outside calls -------------------------------------------------------------
    def _lookup(self, function):
        if function in self._case_fixtures:
            return self._case_fixtures[function]
        if function in self.fixtures:
            signature, effect = self.fixtures[function]
            return signature, self._case_overrides.get(function, effect)
        return None

    def _capture(self, kind, value):
        try:
            if kind == "cstr":
                return self.cstr(value) if value else None
            if kind.startswith("ptr:"):
                return self.read(value, int(kind[4:])) if value else None
        except (HarnessError, UcError):
            return "unreadable"
        return None

    def _source_fixture(self, function, signature):
        registration = self._case_fixtures.get(function)
        if registration is None:
            return None
        capability = self._source_fixture_capabilities.get(function)
        if capability is None:
            raise ContextFault('source fixture was not registered by this case')
        capability.validate(function, signature)
        return capability

    def _serve(self, call, signature, effect, source_fixture=None):
        if call.source_context is not None and call.function in self._case_fixtures:
            source_fixture = source_fixture or self._source_fixture(call.function, signature)
            validate_source_fixture(call.source_context, call.function, call.source_return_pc,
                                    self.program, source_fixture, signature)
            validate_source_operands(call.source_context, signature.convention,
                                     call.receiver, call.receiver2, call.arguments)
            if len(call.arguments) != signature.argc or call.stack_pointer != call.source_context.esp:
                raise ContextFault('source fixture signature or frame mismatch')
            frame = struct.pack(f'<{1 + len(call.arguments)}I', call.source_return_pc, *call.arguments)
            if self.read(call.stack_pointer, len(frame)) != frame:
                raise ContextFault('source fixture physical operands mismatch')
        captured = tuple(self._capture(kind, value) for kind, value in zip(signature.arguments, call.arguments))
        self.events.append((call.function, call.receiver, call.receiver2, call.arguments, captured, (), self._digest()))
        if effect is None:
            raise HarnessError(f"{self.describe(call.function)} needs an effect from the case (env.override)")
        adapter = getattr(self, '_guest_adapter', None)
        guard = adapter if hasattr(adapter, 'before_physical_effect') else None
        remaining = guard.before_physical_effect() if guard else None
        scope=(call,signature,self._callback_generation,
               bytes(call.source_context) if call.source_context is not None else None)
        self._physical_requests.append(scope)
        dialog_state = None
        try:
            dialog_state = self._begin_dialog_request(call)
            end_state = self._dialog_end_request(call)
            value = effect(self, call) if callable(effect) else effect
            if self._physical_failure is not None:
                raise self._physical_failure
            if end_state is not None and value:
                end_state['ended'] = True
                end_state['result'] = call.arguments[1]
            self._finish_dialog_request(dialog_state, value)
            with self._window_guard():
                self._finish_window_request(call,value)
                self._finish_window_show_request(call,value)
        except Halt:
            if self._source_graph and self._source_stop is not None:
                stop = self._source_stop
                proof = (self._callback_generation,stop['function'],stop['return_pc'],
                         tuple(stop['registers'][n] for n in CONTEXT_FIELDS))
                if proof != self._source_stop_proof:
                    raise ContextFault('deep physical stop provenance changed')
            if self._source_graph and self._source_stop is None:
                context = call.source_context
                if context is None or context.inputMask != CONTEXT_ALL:
                    raise ContextFault('source physical halt requires every CPU input to be explicitly known')
                if source_fixture is not None:
                    validate_source_fixture(context, call.function, call.source_return_pc,
                                            self.program, source_fixture, signature)
                else:
                    validate_source(context, call.function, call.source_return_pc, self.program)
                self._source_stop = dict(function=call.function, return_pc=call.source_return_pc,
                                         registers={n: getattr(context, n) for n in CONTEXT_FIELDS})
                self._source_stop_proof = (self._callback_generation,call.function,call.source_return_pc,
                                          tuple(getattr(context,n) for n in CONTEXT_FIELDS))
            raise
        finally:
            if not self._physical_requests or self._physical_requests[-1] is not scope:
                raise ContextFault('physical request lifetime was corrupted')
            self._physical_requests.pop()
            if dialog_state is not None:
                if not self._dialog_sessions or self._dialog_sessions[-1] is not dialog_state:
                    raise ContextFault('dialog request lifetime was corrupted')
                self._dialog_sessions.pop()
            if guard:
                guard.after_physical_effect(remaining)
        return (value or 0) & 0xFFFFFFFF

    def _observe_x87(self, machine, address):
        signature = self.x87_callees[address]
        arguments = machine.words(machine.register(UC_X86_REG_ESP) + 4, signature.argc)
        captured = tuple(self._capture(kind, value) for kind, value in zip(signature.arguments, arguments))
        receiver = machine.register(UC_X86_REG_ECX) if signature.convention == "thiscall" else 0
        if address in self.x87_exact:
            state = machine.x87_state()
            if len(state[2]) < self.x87_exact[address]['pop']:
                raise HarnessError('original x87 stack underflow at declared boundary')
            if len(state[2]) - self.x87_exact[address]['pop'] + self.x87_exact[address]['push'] > 8:
                raise HarnessError('original x87 stack overflow at declared boundary')
            operands = ('extended-v1', *state)
        else:
            operands = (machine.x87_operand(),)
        self.events.append((address, receiver, 0, arguments, captured, operands, self._digest()))

    def _external(self, machine, address):
        """An intercepted call inside the emulated machine (the original side, or a bridged callee)."""
        function = self.stub_function.get(address, address)
        found = self._lookup(function)
        if found is None:
            raise HarnessError(f"execution reached {self.describe(function)}, which has no stand-in")
        signature, effect = found
        stack_pointer = machine.register(UC_X86_REG_ESP)
        arguments = machine.words(stack_pointer + 4, signature.argc)
        uses_ecx = signature.convention in ("thiscall", "fastcall")
        source = None
        return_pc = 0
        if self._source_graph:
            source = NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                       *(machine.register(r) for r in CONTEXT_REGISTERS), machine.fs_head, 0, 0, 0)
            source.eip = function
            return_pc = machine.words(stack_pointer, 1)[0]
        call = Call(function, machine.register(UC_X86_REG_ECX) if uses_ecx else 0,
                    machine.register(UC_X86_REG_EDX) if signature.convention == "fastcall" else 0, arguments,
                    stack_pointer, (), source, return_pc)
        value = self._serve(call, signature, effect)
        machine.return_from_external(value, 4 * signature.argc if signature.convention in CALLEE_POPS else 0)

    def _native_source_tail(self, raw):
        if getattr(self, '_tail_callback_active', False):
            raise ContextFault('source tail callback reentry is not authorized')
        self._tail_callback_active = True
        try:
            return self._serve_native_source_tail(raw)
        finally:
            self._tail_callback_active = False

    def _serve_native_source_tail(self, raw):
        """Execute an elected original target on the inherited physical frame."""
        parent_pointer = self._host.sourceContext
        if (not self._source_graph or not parent_pointer or self._host.compilerContext or
                self._host.guestSession or raw.compilerContext or not raw.sourceContext or
                not raw.sourceDisposition or raw.sourceTransferVersion != 1 or
                raw.sourceTransferKind != 1 or raw.argumentCount or raw.receiver2 or raw.x87ArgumentCount or
                raw.sourceCallerFunction != self._native_source_entry or
                self._tail_specs.get((raw.sourceCallerFunction, raw.sourceTransferSite)) != raw.function):
            raise ContextFault('source tail lacks a live elected direct-JMP edge')
        parent, child = parent_pointer.contents, raw.sourceContext.contents
        header = ('size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1')
        if tuple(getattr(parent,n) for n in header) != self._native_source_header:
            raise ContextFault('source tail parent header differs from its active entry')
        if C.addressof(parent) == C.addressof(child):
            raise ContextFault('source tail requires a separate immutable child header')
        declared = self.source_callees.get(raw.function)
        if (not declared or declared.get('kind') != 'whole' or declared.get('argc') != 0 or
                declared.get('convention') not in ('cdecl', 'thiscall') or self._lookup(raw.function) is not None):
            raise ContextFault('source tail requires a genuine zero-argument original target')
        validate_source(child, raw.function, raw.sourceReturnPC, self.program)
        self._check_source_masks(child, declared['source_context'])
        validate_source_operands(child, declared['convention'], raw.receiver, 0, ())
        if (parent.inputMask != CONTEXT_ALL or parent.outputMask != CONTEXT_ALL or
                child.inputMask != CONTEXT_ALL or child.outputMask != CONTEXT_ALL or
                parent.eip != raw.sourceTransferSite or parent.esp != self._host.entryStackPointer or
                child.esp != parent.esp or raw.stackPointer != parent.esp or
                raw.sourceReturnPC != self._host.sourceReturnPC or
                self.read(parent.esp, 4) != struct.pack('<I', raw.sourceReturnPC) or
                any(getattr(parent, n) != getattr(child, n) for n in CONTEXT_FIELDS if n != 'eip')):
            raise ContextFault('source tail CPU or inherited frame disagrees with its live caller')
        receipt = raw.sourceDisposition.contents
        if (any(getattr(receipt,n) for n in ('size','version','disposition','callerFunction','sourceSite',
                    'targetFunction','entryStackPointer','returnPC')) or receipt.request):
            raise ContextFault('source tail disposition was already used or malformed')
        request_before, parent_before, receipt_before = bytes(raw), bytes(parent), bytes(receipt)
        authority = (C.cast(parent_pointer,C.c_void_p).value, self._host.sourceReturnPC,
                     self._host.entryStackPointer, self._host.guestSession)
        self._source_boundary(raw.sourceCallerFunction, 'tail', parent)
        self._tail_taken.add(raw.sourceCallerFunction)
        call = Call(raw.function, raw.receiver, 0, (), child.esp, (), child, raw.sourceReturnPC)
        value = self._bridge(call, source=child, source_convention=declared['convention'], preserve_failure_prefix=True)
        if (self._host.fault or bytes(raw) != request_before or bytes(parent) != parent_before or
                bytes(receipt) != receipt_before or authority != (
                    C.cast(self._host.sourceContext,C.c_void_p).value, self._host.sourceReturnPC,
                    self._host.entryStackPointer, self._host.guestSession)):
            raise ContextFault('source tail authority changed before completion publication')
        self._source_boundary(raw.sourceCallerFunction, 'tail-return', child)
        receipt.size, receipt.version = C.sizeof(NativeSourceDisposition), 1
        receipt.callerFunction = raw.sourceCallerFunction
        receipt.sourceSite, receipt.targetFunction = raw.sourceTransferSite, raw.function
        receipt.entryStackPointer, receipt.returnPC = raw.stackPointer, raw.sourceReturnPC
        receipt.request = C.pointer(raw)
        receipt.disposition = 1
        return value

    def _native_source_call(self, raw):
        if (not self._source_graph or not raw.sourceContext or raw.compilerContext or raw.x87ArgumentCount or
                not (self._host.sourceContext or self._host.compilerContext or self._dialog_cpu_scope)):
            raise ContextFault('source call lacks a live explicit source graph')
        context = raw.sourceContext.contents
        function = self.stub_function.get(raw.function, raw.function)
        # A cached IAT token is executable only in this Machine. Require the
        # caller's exact raw identity before validating a separate logical view;
        # keep its borrowed context and immutable header intact for output.
        checked = NativeSourceContext.from_buffer_copy(context)
        if raw.function in self.stub_function:
            if context.eip != raw.function:
                raise ContextFault('cached source import identity disagrees with context')
            checked.eip = function
        address = function
        if context.esp != raw.stackPointer:
            raise ContextFault('source call stack pointer disagrees with context')
        found = self._lookup(function)
        declared = self.source_callees.get(function)
        if declared is not None and found is not None:
            raise ContextFault('declared original source dependency cannot become a physical fixture')
        if found:
            signature, effect = found
        elif declared is not None:
            signature = Signature(function, declared.get('name', ''), declared['convention'], declared['argc'])
            effect = None
        else:
            raise ContextFault('ordinary source dependency requires an explicit signature')
        source_fixture = self._source_fixture(function, signature) if found else None
        if source_fixture is not None:
            validate_source_fixture(checked, address, raw.sourceReturnPC, self.program, source_fixture, signature)
        else:
            validate_source(checked, address, raw.sourceReturnPC, self.program)
        arguments = tuple(raw.arguments[:raw.argumentCount])
        if signature.argc != len(arguments):
            raise ContextFault('ordinary source argument count mismatch')
        validate_source_operands(context, signature.convention, raw.receiver, raw.receiver2, arguments)
        if declared and 'source_context' in declared:
            self._check_source_masks(context, declared['source_context'])
        # Nested source frames belong to the translated caller. Copied call
        # metadata is a witness, never permission to repair missing PUSH stores.
        frame = struct.pack(f'<{1 + len(arguments)}I', raw.sourceReturnPC, *arguments)
        if self.read(context.esp, len(frame)) != frame:
            raise ContextFault('source call physical frame disagrees with copied operands')
        entry = self._native_source_entry
        spec = self._boundary_specs.get(entry)
        if spec and raw.sourceReturnPC == spec[1] and self._host.sourceContext:
            if function != spec[3]:
                raise ContextFault('observed caller selected a different original direct child')
            self._source_boundary(entry,'call',self._host.sourceContext.contents)
            self._boundary_called.add(entry)
        before = NativeSourceContext.from_buffer_copy(context)
        call = Call(function, raw.receiver, raw.receiver2, arguments, context.esp, (), context, raw.sourceReturnPC)
        if effect is None:
            return self._bridge(call, source=context, source_convention=signature.convention)
        # Physical services observe the effective CPU inputs, not garbage in
        # undeclared fields. They do not gain native memory permissions.
        effective = NativeSourceContext.from_buffer_copy(checked)
        # The physical observation has no return-preservation contract, matching
        # _external. The borrowed caller's preservation mask remains in before
        # and context and is still enforced by validate_source_output below.
        effective.preserveMask = 0
        for i, name in enumerate(CONTEXT_FIELDS):
            if not effective.inputMask & (1 << i):
                setattr(effective, name, 2 if name == 'eflags' else 0)
        call = Call(function, raw.receiver, raw.receiver2, arguments, context.esp, (), effective, raw.sourceReturnPC)
        value = self._serve(call, signature, effect, source_fixture)
        for i, name in enumerate(CONTEXT_FIELDS):
            if before.outputMask & (1 << i):
                setattr(context, name, getattr(effective, name))
        pops = 4 * len(arguments) if signature.convention in CALLEE_POPS else 0
        context.eax, context.eip, context.esp = value, raw.sourceReturnPC, before.esp + 4 + pops
        if source_fixture is not None:
            validate_source_fixture_output(context, before, address, raw.sourceReturnPC, pops,
                                           self.program, source_fixture, signature)
        else:
            validate_source_output(context, before, address, raw.sourceReturnPC, pops, self.program)
        return value

    @staticmethod
    def _check_source_masks(context, declared):
        if (context.inputMask != declared['input_mask'] or context.outputMask != declared['output_mask'] or
                context.preserveMask != declared['preserve_mask']):
            raise ContextFault('ordinary source context masks disagree with declaration')

    def _native_x87_step(self, raw):
        from .kernel import X87_STEPS
        if (raw.x87ArgumentCount != 3 or not raw.x87State or raw.x87Argument or raw.function or
                raw.receiver or raw.receiver2 or raw.stackPointer or raw.compilerContext or raw.sourceContext or
                raw.sourceReturnPC or raw.sourceTransferKind or raw.sourceTransferVersion or raw.sourceTransferSite or
                raw.sourceCallerFunction or raw.sourceDisposition or self._host.compilerContext or
                self._host.sourceContext or self._host.guestSession or raw.x87Operation not in X87_STEPS):
            raise ContextFault('malformed or mixed x87 primitive capability')
        code, argc, pop, push, minimum, stores = X87_STEPS[raw.x87Operation]
        s = raw.x87State.contents
        self._validate_x87_state(s, push_limit=8)
        if (not supported_x87_control(s.control) or raw.argumentCount != argc or s.count < minimum or s.count - pop + push > 8 or
                s.popCount != pop or s.pushCount != push or s.returned or s.eax or s.edx):
            raise ContextFault('invalid x87 primitive operands')
        control, status, slots = self.machine.x87_step(raw.x87Operation,
            (s.control, s.status, tuple((v.significand, v.signExponent) for v in s.slots[:s.count])),
            tuple(raw.arguments[:raw.argumentCount]))
        if (control != s.control or len(slots) != s.count - pop + push or
                slots[push:] != tuple((v.significand, v.signExponent) for v in s.slots[pop:s.count]) or
                (status >> 11) & 7 != (((s.status >> 11) + pop - push) & 7)):
            raise ContextFault('x87 primitive violated its stack contract')
        s.control, s.status, s.count = control, status, len(slots)
        for i in range(8):
            s.slots[i] = NativeX87Value(*(slots[i] if i < len(slots) else (0, 0)), 0)
        # FST/FSTP m64 publish the stored binary64 bits as EDX:EAX; others zero.
        stored = self.machine.x87_stored if stores else 0
        s.eax, s.edx = stored & 0xffffffff, stored >> 32
        s.returned = 1
        return s.eax

    def _native_x87_exact(self, raw):
        if (raw.x87ArgumentCount != 2 or not raw.x87State or raw.x87Argument or raw.x87Operation or
                raw.compilerContext or raw.sourceContext or raw.sourceReturnPC or raw.sourceTransferKind or
                raw.sourceTransferVersion or raw.sourceTransferSite or raw.sourceCallerFunction or
                raw.sourceDisposition or self._host.compilerContext or self._host.sourceContext or
                self._host.guestSession or raw.receiver2 or raw.argumentCount > CALL_ARGUMENT_CAPACITY):
            raise ContextFault('exact x87 transport mixed with another capability')
        contract, signature = self.x87_exact.get(raw.function), self.x87_callees.get(raw.function)
        if (contract is None or signature is None or self._lookup(raw.function) is not None or
                raw.argumentCount != signature.argc or (signature.convention != 'thiscall' and raw.receiver)):
            raise ContextFault('undeclared exact x87 original boundary or signature mismatch')
        state = raw.x87State.contents
        before = NativeX87State.from_buffer_copy(state)
        self._validate_x87_state(before)
        if (before.returned or before.eax or before.edx or before.popCount != contract['pop'] or
                before.pushCount != contract['push'] or before.count < before.popCount or
                before.count - before.popCount + before.pushCount > 8):
            raise ContextFault('invalid exact x87 input or callee stack effect')
        call = Call(raw.function, raw.receiver, 0, tuple(raw.arguments[:raw.argumentCount]), raw.stackPointer)
        value = self._bridge(call, x87=state)
        # _bridge publishes only after an actual completed original return.
        return value

    @staticmethod
    def _validate_x87_state(state, push_limit=1):
        # Calls push at most one result; register-indexed primitives may
        # replace up to eight slots (pop k/push k).
        if (state.size != C.sizeof(NativeX87State) or state.version != 1 or state.reserved0 or state.reserved1 or
                state.control > 0xffff or state.status > 0xffff or state.control & 0x3f != 0x3f or
                state.control & ~0x1f7f or state.control & 0x300 == 0x100 or state.count > 8 or
                not 0 <= state.popCount <= 8 or state.pushCount > push_limit):
            raise ContextFault('malformed exact x87 state')
        for i, slot in enumerate(state.slots):
            if (slot.reserved or slot.signExponent > 0xffff or
                    (i >= state.count and (slot.significand or slot.signExponent))):
                raise ContextFault('malformed exact x87 slot')

    def _native_call(self, user, pointer):
        """ClawHost::call from the native module."""
        adapter = getattr(self, '_guest_adapter', None)
        entered = False
        callback_witness = None
        try:
            self._check_physical_failure()
            if getattr(self, '_tail_callback_active', False):
                raise ContextFault('native callback reentry during source tail execution')
            if adapter is not None:
                adapter.enter_callback(pointer)
                entered = True
            raw = pointer.contents
            self._validate_dialog_cpu(raw)
            if raw.callbackCPU:
                lease = self._dialog_cpu_scope[0]
                callback_witness = (lease, bytes(lease), self._dialog_cpu_scope)
            if raw.argumentCount > CALL_ARGUMENT_CAPACITY:
                raise ContextFault("native call operand count exceeds the canonical ABI")
            if self._x87_outer is not None and self._x87_outer['result'] is not None:
                raise ContextFault('owned x87 result must be the entry\'s last outside call')
            if raw.x87ArgumentCount in (4, 5) and raw.x87State:
                return self._native_x87_outer(raw)
            if raw.x87Operation or raw.x87ArgumentCount == 3:
                return self._native_x87_step(raw)
            if raw.x87State or raw.x87ArgumentCount == 2:
                return self._native_x87_exact(raw)
            if raw.function in self.x87_exact:
                raise ContextFault('exact x87 callee requires exact transport')
            caller_ebp = self._native_caller_frame(raw) if raw.function in self.caller_frames else None
            inherited = (raw.function in self.compiler_callees and not raw.compilerContext and
                         not raw.sourceContext and not raw.sourceReturnPC and not raw.sourceTransferKind)
            if inherited:
                caller_ebp = self._native_entry_frame(raw)
            if raw.sourceTransferKind:
                return self._native_source_tail(raw)
            if (raw.sourceTransferVersion or raw.sourceTransferSite or raw.sourceCallerFunction or raw.sourceDisposition):
                raise ContextFault('ordinary CALL cannot carry a tail transfer receipt')
            if raw.x87ArgumentCount > 1:
                raise HarnessError("native call operand count exceeds the canonical ABI")
            if raw.sourceContext or raw.sourceReturnPC:
                return self._native_source_call(raw)
            if raw.compilerContext:
                if raw.argumentCount or raw.receiver or raw.receiver2 or raw.stackPointer or raw.x87ArgumentCount:
                    raise ContextFault('compiler call mixed with ordinary operands')
                context = raw.compilerContext.contents
                if self._host.sourceContext:
                    declared = self.compiler_callees.get(raw.function)
                    if (not declared or context.inputMask != declared['input_mask'] or
                            context.outputMask != declared['output_mask']):
                        raise ContextFault('source parent requires a declared original compiler dependency')
                validate_context(context, raw.function, self.program)
                if self._lookup(raw.function) is not None or raw.function in self.x87_callees:
                    raise ContextFault('compiler callee must execute unchanged original instructions')
                call = Call(raw.function, 0, 0, (), 0)
                return self._bridge(call, context)
            declared = self.source_callees.get(raw.function)
            optional = (declared is not None and declared.get('kind') == 'whole' and
                        declared.get('convention') in ('cdecl', 'stdcall', 'thiscall') and
                        declared.get('source_context', {}).get('optional') is True)
            if (self._host.sourceContext or (raw.function in self.compiler_callees and not inherited) or
                    (declared is not None and not optional)):
                raise ContextFault('declared context dependency requires explicit transport')
            if optional:
                if (self._lookup(raw.function) is not None or not self.program.in_text(raw.function) or
                        raw.argumentCount != declared['argc'] or raw.receiver2 or raw.x87ArgumentCount or
                        (declared['convention'] != 'thiscall' and raw.receiver)):
                    raise ContextFault('optional original dependency ordinary signature mismatch')
            # A source register can cache an IAT target and call it directly.
            # Resolve only this machine's known physical import stub identities,
            # exactly as _external does; declaration/signature checks stay below.
            function = self.stub_function.get(raw.function, raw.function)
            call = Call(function, raw.receiver, raw.receiver2, tuple(raw.arguments[:raw.argumentCount]),
                        raw.stackPointer, (raw.x87Argument,) if raw.x87ArgumentCount else ())
            x87_signature = self.x87_callees.get(call.function)
            if bool(x87_signature) != bool(call.x87_arguments):
                raise HarnessError(f"{self.describe(call.function)}: missing or undeclared x87 operand")
            if x87_signature and (len(call.arguments) != x87_signature.argc or call.receiver2 or
                                  (x87_signature.convention != "thiscall" and call.receiver)):
                raise HarnessError(f"{self.describe(call.function)}: native x87 call signature mismatch")
            found = self._lookup(call.function)
            if found is not None:
                signature, effect = found
                if signature.argc != len(call.arguments):
                    raise HarnessError(f"native code called {self.describe(call.function)} with "
                                       f"{len(call.arguments)} arguments; it takes {signature.argc}")
                uses_ecx = signature.convention in ("thiscall", "fastcall")
                if not uses_ecx and call.receiver:
                    raise HarnessError(f"native code passed a receiver to {self.describe(call.function)}, "
                                       f"which is {signature.convention}")
                return self._serve(call, signature, effect)
            if self.program.in_text(call.function):
                return self._bridge(call, caller_ebp=caller_ebp)
            raise HarnessError(f"native code called {self.describe(call.function)}, which has no stand-in")
        except NativeGuestTransfer:
            if adapter is None or not adapter.pending:
                self._host.fault = self._host.fault or 5
            return 0
        except SourceBudgetFault as error:
            self.errors.append(error)
            self._host.fault = self._host.fault or 3
            return 0
        except ContextFault as error:
            self.errors.append(error)
            self._host.fault = self._host.fault or 5
            self._host.faultAddress = pointer.contents.function
            return 0
        except Halt:
            self._host.fault = self._host.fault or 2
            return 0
        except BaseException as error:
            self.errors.append(error)
            self._host.fault = self._host.fault or 6
            return 0
        finally:
            if callback_witness is not None:
                lease, witness, scope = callback_witness
                try:
                    self._validate_dialog_cpu()
                    if self._dialog_cpu_scope is not scope or bytes(lease) != witness:
                        raise ContextFault('borrowed callback CPU changed during descendant execution')
                except ContextFault as error:
                    self.errors.append(error)
                    self._host.fault = 5
            if entered:
                adapter.leave_callback()

    def _bridge(self, call, context=None, source=None, source_convention="cdecl", *, preserve_failure_prefix=False, x87=None,
                caller_ebp=None):
        """Run an original callee on behalf of native code, over the native side's memory."""
        if any(c.native_owned and c.target == call.function for c in self._dialog_contracts.values()):
            raise ContextFault('owned dialog callback cannot bridge to original code')
        if self._enumeration_graph and any(c.target == call.function for c, _ in self._enumeration_contracts.values()):
            raise ContextFault('owned enumeration callback cannot bridge to original code')
        if self._bridge_depth >= 64:
            raise ContextFault('source graph depth exceeded')
        self.bridged.append(call.function)
        self.machine.write(HEAP_BASE, bytes(self._heap))
        self.machine.write(self.program.data_start, bytes(self._image)[self.data_offset:])
        self.machine.write(STACK_BASE, bytes(self._stack))
        previous_backend = self.backend
        active = (self._host.compilerContext.contents if self._host.compilerContext else
                  self._host.sourceContext.contents if self._host.sourceContext else None)
        saved_registers = self.machine.uc.context_save() if context is not None or source is not None or active is not None or self._enumeration_graph or self._dialog_native_frame else None
        saved_fs = self.machine.fs_head
        if active is not None:
            self.machine.fs_head = active.fsHead
        self.backend = "machine"
        self._bridge_depth += 1
        budget_hook = None
        adapter = getattr(self, '_guest_adapter', None)
        transferred = False
        returned_normally = False
        x87_before = NativeX87State.from_buffer_copy(x87) if x87 is not None else None
        if self._source_graph and adapter is None and not self.machine._physical_pump:
            def consume(uc, pc, size, user):
                if not self._source_budget.value:
                    raise SourceBudgetFault('source graph operations exhausted')
                self._source_budget.value -= 1
            budget_hook = self.machine.uc.hook_add(UC_HOOK_CODE, consume)
        try:
            if x87 is not None:
                self.machine.set_x87_state(x87.control, x87.status,
                    tuple((v.significand, v.signExponent) for v in x87.slots[:x87.count]))
            for value in reversed(call.x87_arguments):
                self.machine.push_x87(value)
            if source is not None:
                returned = self.machine.call_source(call.function, source, call.source_return_pc, source_convention,
                                                    call.receiver, call.receiver2, call.arguments, prepare_frame=False)
            elif context is not None:
                returned = self.machine.call_context(call.function, context)
            else:
                bridge_frame = call.stack_pointer or min(BRIDGE_STACK,
                    (self._enumeration_frame or STACK_TOP) - 0x1000,
                    (self._dialog_native_frame or STACK_TOP) - 0x1000)
                saved_ebp = self.machine.register(UC_X86_REG_EBP)
                if caller_ebp is not None:
                    self.machine.uc.reg_write(UC_X86_REG_EBP, caller_ebp)
                try:
                    returned = self.machine.call(call.function, call.receiver, call.receiver2, call.arguments,
                                                 stack_pointer=bridge_frame, reset_thread=False)
                finally:
                    if caller_ebp is not None:
                        self.machine.uc.reg_write(UC_X86_REG_EBP, saved_ebp)
            returned_normally = returned.completed
            if x87 is not None and returned_normally:
                control, status, slots = self.machine.x87_state()
                b = x87_before
                signature = self.x87_callees[call.function]
                expected_sp = (call.stack_pointer or BRIDGE_STACK) + 4 + (4 * signature.argc
                    if signature.convention in CALLEE_POPS else 0)
                if returned.stack_pointer != expected_sp:
                    raise ContextFault('original x87 callee returned with wrong stack cleanup')
                lower = tuple((v.significand, v.signExponent) for v in b.slots[b.popCount:b.count])
                if (control != b.control or len(slots) != b.count - b.popCount + b.pushCount or
                        slots[b.pushCount:] != lower or
                        (status >> 11) & 7 != (((b.status >> 11) + b.popCount - b.pushCount) & 7)):
                    raise ContextFault('original x87 return violates stack effect or live-slot preservation')
                result = NativeX87State.from_buffer_copy(b)
                result.control, result.status, result.count = control, status, len(slots)
                for i in range(8):
                    result.slots[i] = NativeX87Value(*(slots[i] if i < len(slots) else (0, 0)), 0)
                result.eax, result.edx = returned.eax, self.machine.register(UC_X86_REG_EDX)
                result.returned = 1
                C.memmove(C.addressof(x87), C.addressof(result), C.sizeof(result))
        except PhysicalTransfer as stop:
            if adapter is None or source is None:
                raise ContextFault('physical transfer requires an opted-in original source bridge') from None
            # Capture owns CPU, FS and all mirrored memory before parent restoration.
            adapter.capture_original(stop.event, call)
            transferred = True
            raise NativeGuestTransfer() from None
        except BaseException:
            if preserve_failure_prefix and source is not None:
                # Capture before restoring the suspended parent's emulator
                # registers. A stopped tail has no ordinary returned receipt.
                for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS):
                    setattr(source, name, self.machine.register(register))
                source.fsHead = self.machine.fs_head
            raise
        finally:
            self._bridge_depth -= 1
            if budget_hook is not None:
                self.machine.uc.hook_del(budget_hook)
            if active is not None and self._host.compilerContext:
                active.fsHead = self.machine.fs_head
            if saved_registers is not None and (returned_normally or not self.machine._physical_pump or self._enumeration_graph):
                self.machine.uc.context_restore(saved_registers)
            if adapter is not None or self._enumeration_graph:
                self.machine.fs_head = saved_fs
            self.backend = previous_backend
            if not transferred:
                C.memmove(self._heap, self.machine.read(HEAP_BASE, self.heap_bytes), self.heap_bytes)
                data = self.machine.read(self.program.data_start, self.program.size - self.data_offset)
                C.memmove(C.addressof(self._image) + self.data_offset, data, len(data))
                C.memmove(self._stack, self.machine.read(STACK_BASE, STACK_SIZE), STACK_SIZE)
        if not returned.completed:
            raise HarnessError(f"original callee {self.describe(call.function)} did not return")
        return returned.eax

    # ---- The two runs ----------------------------------------------------------------
    def run_native(self, entry, function, receiver, arguments, *, entry_stack_pointer=0, compiler_context=None,
                   source_context=None, source_return_pc=0, source_convention="cdecl", receiver2=0):
        if len(arguments) > CALL_ARGUMENT_CAPACITY:
            raise HarnessError("native incoming arguments exceed the canonical ABI")
        if self._source_graph or self._enumeration_graph:
            raise ContextFault('cannot reuse a live source graph as another outer entry')
        if self._enumeration_contracts and (compiler_context is not None or source_context is not None):
            raise ContextFault('enumeration callbacks require ordinary roots')
        if (self._dialog_contracts or self._window_contracts) and source_context is None:
            raise ContextFault('dialog callbacks require a source-capable root')
        if not isinstance(entry_stack_pointer, int) or isinstance(entry_stack_pointer, bool):
            raise HarnessError("native incoming frame must be an integer address")
        if self._entry_ebp is not None and (compiler_context is not None or source_context is not None or
                                            getattr(self, '_guest_adapter', None) is not None):
            raise HarnessError('an entry frame pointer applies only to ordinary outer entries')
        self._check_entry_x87_profile(function)
        if ((self._entry_x87_status is not None or self._entry_x87_profile is not None) and
                (compiler_context is not None or source_context is not None or
                 getattr(self, '_guest_adapter', None) is not None)):
            raise HarnessError('entry x87 environment applies only to ordinary outer entries')
        if compiler_context is not None:
            validate_context(compiler_context, function, self.program)
            if receiver or arguments or entry_stack_pointer:
                raise HarnessError('compiler entry mixed with ordinary operands')
        if source_context is not None:
            if compiler_context is not None or entry_stack_pointer:
                raise ContextFault('source and compiler entry channels are exclusive')
            validate_source(source_context, function, source_return_pc, self.program)
            validate_source_operands(source_context, source_convention, receiver, receiver2, arguments)
        elif source_return_pc:
            raise ContextFault('source return PC requires explicit source capability')
        frame = source_context.esp if source_context is not None else compiler_context.esp if compiler_context is not None else entry_stack_pointer or STACK_TOP
        frame_bytes = 4 * (1 + len(arguments))
        if (not isinstance(frame, int) or isinstance(frame, bool) or frame & 3 or
                frame < STACK_BASE or frame + frame_bytes > STACK_BASE + STACK_SIZE):
            raise HarnessError("native incoming frame is unaligned or outside the bounded stack")
        heap, image, _, _, _ = self._frozen
        self.side, self.backend = "native", "native"
        C.memmove(self._heap, heap, len(heap))
        C.memmove(self._image, image, len(image))
        if compiler_context is not None or source_context is not None:
            if self._frozen_stack_input:
                raise HarnessError("ordinary initial stack input cannot be mixed with a context entry")
            C.memmove(self._stack, bytes(self._initial['stack']), STACK_SIZE)
        else:
            regions = self._ordinary_stack_input(frame)
            C.memset(self._stack, 0, STACK_SIZE)
            for offset, data in regions:
                C.memmove(C.addressof(self._stack) + frame + offset - STACK_BASE, data, len(data))
        # Match Machine.call and the shipping host: copied operands are also
        # materialized in guest stack slots. Guest writes may change a later
        # source reload without mutating the separate native argument array.
        incoming = struct.pack(f"<{1 + len(arguments)}I", source_return_pc or STOP, *(a & 0xFFFFFFFF for a in arguments))
        if compiler_context is None:
            C.memmove(C.addressof(self._stack) + frame - STACK_BASE, incoming, frame_bytes)
        self._reset_run()
        self._reset_entry_x87()
        self._spans_changed()
        self._host.fault, self._host.faultAddress = 0, 0
        self._host.maximumOperations = self.maximum_operations
        self._host.entryStackPointer = frame
        self._host.compilerContext = C.pointer(compiler_context) if compiler_context is not None else None
        self._host.sourceContext = C.pointer(source_context) if source_context is not None else None
        self._host.sourceReturnPC = source_return_pc
        self._source_graph = source_context is not None
        self._native_source_entry = function if self._source_graph else None
        self.machine.fs_head = (source_context.fsHead if source_context is not None else
                                compiler_context.fsHead if compiler_context is not None else 0xffffffff)
        self._source_budget = C.c_uint64(self.maximum_operations or 200000000)
        self._host.remainingOperations = C.pointer(self._source_budget) if self._source_graph or self._enumeration_contracts else None
        words = (U32 * len(arguments))(*arguments) if arguments else None
        result = U32(0)
        source_before = NativeSourceContext.from_buffer_copy(source_context) if source_context is not None else None
        self._native_source_header = tuple(getattr(source_before,n) for n in (
            'size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1')) if source_before else None
        self._frame_entry = ((function, receiver & 0xFFFFFFFF, tuple(a & 0xFFFFFFFF for a in arguments), frame)
                             if compiler_context is None and source_context is None else None)
        owned_x87 = function in self.x87_results or function in self.x87_environments
        if owned_x87 and (compiler_context is not None or source_context is not None or
                          getattr(self, '_guest_adapter', None) is not None):
            raise HarnessError('owned x87 entries are ordinary entries only')
        self._x87_outer = (dict(function=function, entry=self.machine.x87_state(), queried=False, result=None,
                               push=0 if function in self.x87_environments else 1)
                           if owned_x87 else None)
        try:
            self._dialog_entry = entry
            self._begin_enumeration_graph(entry)
            self._begin_physical_graph()
            completed = entry(function, receiver, words, len(arguments), C.byref(self._host), C.byref(result))
            if source_before is not None:
                header = ('size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1')
                if (any(getattr(source_context, n) != getattr(source_before, n) for n in header) or
                        C.cast(self._host.sourceContext, C.c_void_p).value != C.addressof(source_context) or
                        self._host.sourceReturnPC != source_return_pc):
                    self.errors.append(ContextFault('source entry changed immutable header or borrowed host scope'))
                    self._host.fault = self._host.fault or 5
                    completed = False
            if compiler_context is not None and completed:
                validate_context(compiler_context, function, self.program, returned=True)
            outer = self._x87_outer
            if outer is not None and completed and outer['result'] is None:
                self.errors.append(ContextFault('owned x87 entry returned without publishing its final environment'))
                self._host.fault = self._host.fault or 5
                completed = False
        finally:
            outer, self._x87_outer = self._x87_outer, None
            self._frame_entry = None
            self._end_physical_graph()
            self._host.compilerContext = None
            self._host.sourceContext = None
            self._host.sourceReturnPC = 0
            self._host.remainingOperations = None
            self._source_graph = False
        return Side(completed=bool(completed), halted=self._host.fault == 2, eax=result.value, fault=self._host.fault,
                    fault_address=self._host.faultAddress, events=self.events, heap=bytes(self._heap),
                    image=bytes(self._image)[self.data_offset:], spans=dict(self.spans), freed=list(self.freed),
                    errors=list(self.errors), bridged=list(self.bridged), source_stop=self._source_stop,
                    source_boundaries=list(self.source_boundaries),
                    x87=outer['result'] if outer is not None and completed else None,
                    compiler_context={n: getattr(compiler_context, n) for n in CONTEXT_FIELDS}
                    if compiler_context is not None else {})

    def _stray_access(self, address, size, is_write, instruction):
        """Called for each heap access of the original while cases are being checked."""
        if len(self._strays) >= 3:
            return
        if not any(token <= address and address + size <= token + length for token, length in self.spans.items()):
            self._strays.append(f"{'wrote' if is_write else 'read'} {size} byte(s) at {self.describe(address)} from "
                                f"instruction {instruction:#x}")

    def run_original(self, function, receiver, arguments, trace=False, check_objects=False, *, stack_pointer=STACK_TOP):
        self._check_entry_x87_profile(function)
        if self._source_graph or self._enumeration_graph:
            raise ContextFault('cannot reset a live callback graph as another outer entry')
        if self._dialog_contracts or self._window_contracts:
            raise ContextFault('dialog callbacks require a source-capable root')
        heap, image, _, _, _ = self._frozen
        self._strays = []
        self.machine.watch_heap(self._stray_access if check_objects else None)
        self.side, self.backend = "original", "machine"
        self.machine.write(HEAP_BASE, heap)
        self.machine.write(self.program.data_start, image[self.data_offset:])
        self.machine.write(STACK_BASE, bytes(STACK_SIZE))
        for offset, data in self._ordinary_stack_input(stack_pointer):
            self.machine.write(stack_pointer + offset, data)
        self._reset_run()
        self._reset_entry_x87()
        self.machine.trace_blocks(trace)
        side = Side()
        self._source_budget = C.c_uint64(self.maximum_operations or 200000000)
        self._frame_entry = (function, receiver & 0xFFFFFFFF, tuple(a & 0xFFFFFFFF for a in arguments), stack_pointer)
        try:
            self._begin_enumeration_graph()
            entry_x87 = (self.machine.x87_state() if function in self.x87_results or
                         function in self.x87_environments else None)
            if self._entry_ebp is not None:
                saved_ebp = self.machine.register(UC_X86_REG_EBP)
                self.machine.uc.reg_write(UC_X86_REG_EBP, self._entry_ebp)
            try:
                returned = self.machine.call(function, receiver, 0, arguments, stack_pointer=stack_pointer)
                returned_ebp = self.machine.register(UC_X86_REG_EBP)
            finally:
                if self._entry_ebp is not None:
                    self.machine.uc.reg_write(UC_X86_REG_EBP, saved_ebp)
            side.completed, side.eax, side.stack_pointer = returned.completed, returned.eax, returned.stack_pointer
            if not returned.completed:
                side.errors.append(HarnessError("original did not return within the time limit"))
            elif self._entry_ebp is not None and returned_ebp != self._entry_ebp:
                side.errors.append(HarnessError(f"original {self.describe(function)} returned EBP {returned_ebp:#x}; "
                                                f"its caller's elected EBP was {self._entry_ebp:#x}"))
            elif entry_x87 is not None:
                side.x87 = self.machine.x87_state()
                control, status, slots = side.x87
                push = 0 if function in self.x87_environments else 1
                if (control != entry_x87[0] or len(slots) != len(entry_x87[2]) + push or slots[push:] != entry_x87[2] or
                        (status >> 11) & 7 != ((entry_x87[1] >> 11) - push) & 7):
                    declaration = 'x87_environment' if push == 0 else 'x87_result'
                    side.errors.append(HarnessError(
                        f"original {self.describe(function)} violated its {declaration} stack/CW contract"))
        except Halt:
            side.halted = True
        except (HarnessError, UcError, EmulationFault, SourceBudgetFault) as error:
            side.errors.append(error)
        finally:
            self._frame_entry = None
            try:
                self._end_physical_graph()
            finally:
                # Original helpers also run for native comparisons. Their
                # execution must not leak into the next original coverage set.
                self.machine.trace_blocks(False)
        if self._strays:
            side.errors.append(HarnessError(
                "the original touched heap memory outside every live object, so this case's objects are too small "
                "or one of its pointers is wrong: " + "; ".join(self._strays)))
        if trace:
            self.coverage |= self.machine.blocks
            self.machine.blocks.clear()
        side.events, side.spans, side.freed = self.events, dict(self.spans), list(self.freed)
        side.heap = self.machine.read(HEAP_BASE, self.heap_bytes)
        side.image = self.machine.read(self.program.data_start, self.program.size - self.data_offset)
        return side

    def run_original_context(self, function, context, trace=False, check_objects=False, *,
                             source_return_pc=0, source_convention="cdecl", receiver=0, receiver2=0, arguments=()):
        """Explicit context execution with the same coverage/object checks as ordinary cases."""
        if self._entry_x87_status is not None or self._entry_x87_profile is not None or function in self.x87_environments:
            raise HarnessError('entry x87 environment applies only to ordinary outer entries')
        if self._entry_ebp is not None:
            raise HarnessError('an entry frame pointer applies only to ordinary outer entries')
        if self._frozen_stack_input:
            raise HarnessError("ordinary initial stack input cannot be mixed with a context entry")
        if self._source_graph or self._enumeration_graph:
            raise ContextFault('cannot reuse a live source graph as another outer entry')
        if self._enumeration_contracts:
            raise ContextFault('enumeration callbacks require ordinary roots')
        is_source = isinstance(context, NativeSourceContext)
        if (self._dialog_contracts or self._window_contracts) and not is_source:
            raise ContextFault('dialog callbacks require ordinary source root')
        if is_source:
            validate_source(context, function, source_return_pc, self.program)
        else:
            validate_context(context, function, self.program)
        self._source_graph = is_source
        continuation = source_return_pc if is_source else context.continuation
        heap, image, _, _, _ = self._frozen
        self._strays = []
        self.machine.watch_heap(self._stray_access if check_objects else None)
        self.side, self.backend = 'original', 'machine'
        self.machine.write(HEAP_BASE, heap)
        self.machine.write(self.program.data_start, image[self.data_offset:])
        self.machine.write(STACK_BASE, self._initial['stack'])
        self._reset_run()
        self.machine.reset_x87()
        # A compiler continuation can cut a translated basic block. Count only
        # instructions entered before the exact continuation, never its tail.
        self.machine.trace_blocks(False)
        executed = set()
        def instruction(uc, address, size, user):
            if address != continuation or (is_source and not self.machine._source_return_boundary(address)):
                executed.add((address, size))
        hook = self.machine.uc.hook_add(UC_HOOK_CODE, instruction) if trace else None
        side = Side()
        try:
            self._source_budget = C.c_uint64(self.maximum_operations or 200000000)
            self._begin_physical_graph()
            result = (self.machine.call_source(function, context, source_return_pc, source_convention,
                                                receiver, receiver2, arguments) if is_source else
                      self.machine.call_context(function, context))
            side.completed, side.eax, side.stack_pointer = result.completed, result.eax, result.stack_pointer
            if is_source and result.completed and function in self._tail_taken:
                self._source_boundary(function, 'tail-return', context)
        except Halt:
            side.halted = True
        except (HarnessError, UcError, EmulationFault, SourceBudgetFault) as error:
            side.errors.append(error)
        finally:
            self._end_physical_graph()
            self._source_graph = False
            if hook is not None:
                self.machine.uc.hook_del(hook)
        if self._strays:
            side.errors.append(HarnessError(
                "the original touched heap memory outside every live object: " + "; ".join(self._strays)))
        if trace:
            self.coverage |= executed
        side.events, side.spans, side.freed = self.events, dict(self.spans), list(self.freed)
        side.heap = self.machine.read(HEAP_BASE, self.heap_bytes)
        side.image = self.machine.read(self.program.data_start, self.program.size - self.data_offset)
        side.source_stop = self._source_stop
        side.source_boundaries = list(self.source_boundaries)
        side.compiler_context = {n: getattr(context, n) for n in CONTEXT_FIELDS}
        return side

    # ---- Comparison ---------------------------------------------------------------------
    def _event_text(self, event):
        function, receiver, receiver2, arguments, captured, x87, _ = event
        text = f"{self.describe(function)} receiver={receiver:#x} args=[{', '.join(f'{a:#x}' for a in arguments)}]"
        shown = [c.hex() if isinstance(c, bytes) else str(c) for c in captured if c is not None]
        return text + (f" pointed=[{', '.join(shown)}]" if shown else "") + (f" x87={x87!r}" if x87 else "")

    def _word_differences(self, base, ours, theirs, limit=12):
        found = []
        for offset in range(0, min(len(ours), len(theirs)) - 3, 4):
            if ours[offset:offset + 4] != theirs[offset:offset + 4]:
                found.append({"at": self.describe(base + offset), "native": ours[offset:offset + 4].hex(),
                              "original": theirs[offset:offset + 4].hex()})
                if len(found) == limit:
                    break
        return found

    def compare(self, native, original, compare_eax, expected_stack_pointer):
        """Returns None when the two sides agree, else {"kind": ..., "detail": ...}."""
        if (native.fault == 5 and native.errors and all(isinstance(e,ContextFault) for e in native.errors)
                and not original.errors and not original.fault and (original.completed or original.halted)):
            return {'kind':'native-fault','detail':'native ABI violation on valid original input: ' +
                    '; '.join(str(e) for e in native.errors)}
        problems = list(dict.fromkeys(f"{type(e).__name__}: {e}" for e in native.errors + original.errors))
        if problems:
            return {"kind": "harness", "detail": "; ".join(problems)}
        if native.halted != original.halted:
            return {"kind": "halt", "detail": f"native halted={native.halted}, original halted={original.halted}"}
        if native.fault and not native.halted:
            name = FAULT_NAMES.get(native.fault, str(native.fault))
            return {"kind": "native-fault", "detail": f"fault {name} at {self.describe(native.fault_address)}; "
                    f"native made {len(native.events)} outside calls, original made {len(original.events)}"}
        if native.source_boundaries != original.source_boundaries:
            return {'kind':'source-boundary','detail':f'native: {native.source_boundaries!r} | original: {original.source_boundaries!r}'}
        for index, (ours, theirs) in enumerate(zip(native.events, original.events)):
            if ours != theirs:
                same_call = ours[:6] == theirs[:6]
                return {"kind": "event-memory" if same_call else "event", "index": index,
                        "detail": ("same call, memory differs at the moment of the call: " if same_call else "")
                        + f"native: {self._event_text(ours)} | original: {self._event_text(theirs)}"}
        if len(native.events) != len(original.events):
            longer, name = (native, "native") if len(native.events) > len(original.events) else (original, "original")
            extra = longer.events[min(len(native.events), len(original.events))]
            return {"kind": "event-count", "detail": f"native made {len(native.events)} outside calls, original "
                    f"{len(original.events)}; first extra on {name}: {self._event_text(extra)}"}
        if native.heap != original.heap:
            return {"kind": "heap", "detail": self._word_differences(HEAP_BASE, native.heap, original.heap)}
        if native.image != original.image:
            return {"kind": "globals",
                    "detail": self._word_differences(self.program.data_start, native.image, original.image)}
        if native.spans != original.spans or native.freed != original.freed:
            return {"kind": "ownership", "detail": f"live objects or frees differ: native freed "
                    f"{[hex(t) for t in native.freed]}, original freed {[hex(t) for t in original.freed]}"}
        if original.halted:
            return None
        if original.stack_pointer != expected_stack_pointer:
            return {"kind": "specification", "detail": f"original returned with stack pointer "
                    f"{original.stack_pointer:#x}, the declared convention and argument count predict "
                    f"{expected_stack_pointer:#x}"}
        if native.x87 != original.x87:
            def text(x87):
                return None if x87 is None else {"cw": f"{x87[0]:#06x}", "sw": f"{x87[1]:#06x}",
                    "slots": [f"{e:04x}:{s:016x}" for s, e in x87[2]]}
            return {"kind": "x87-result", "detail": f"native {text(native.x87)}, original {text(original.x87)}"}
        if compare_eax and native.eax != original.eax:
            return {"kind": "return-value", "detail": f"native {native.eax:#x}, original {original.eax:#x}"}
        return None
