"""Runs original instructions under emulation.

One Machine holds the mapped program, a heap and a stack. Calls to functions
that cannot run (imports, declared stand-ins) are intercepted and handed to the
owner of the machine; everything else executes as the original wrote it.
"""
import re
import struct
import time
from .abi import CALL_ARGUMENT_CAPACITY

from dataclasses import dataclass
from contextlib import contextmanager

from unicorn import (UC_ARCH_X86, UC_HOOK_BLOCK, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_32, Uc,
                     UcError)
from unicorn import UC_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EIP, UC_X86_REG_ESP,
                               UC_X86_REG_EBP, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EFLAGS,
                               UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG, UC_X86_REG_FP0)

STACK_BASE = 0x1FF0000
STACK_SIZE = 0x20000   # grow down only: keep the upper bound and absolute frame anchors unchanged
STACK_TOP = 0x2008000   # must equal CLAW_STACK_TOP in Sources/ClawRuntime.h
STOP = 0x200F000        # return address of the outermost call; never executed
STUB_BASE = 0x710000    # one byte per stand-in for an import or a test-supplied function pointer
STUB_SIZE = 0x1000
PHYSICAL_CALLBACK_RETURN = 0x720000  # scoped synthetic OS dispatcher return, never a source PC
THREAD_BLOCK = 0x0  # stands in for the Windows thread information block; the emulator's FS base is 0


def supported_x87_control(control):
    """Masked exceptions, PC 24/53/64, all RC modes; no legacy/reserved bits."""
    return (type(control) is int and 0 <= control <= 0xffff and
            control & 0x3f == 0x3f and not control & ~0x0f3f and control & 0x300 != 0x100)


# The FLD m32/m64 signaling-NaN correction below needs a Python code hook on
# every instruction that can be such a load and on the instruction after it.
# A global per-instruction hook runs original code at about one million
# instructions a second, so long x87-free loops (0x4c6d90 executes about 370
# million instructions) cannot return within a case. The hook therefore covers
# an exact superset instead: every address outside program text, and inside
# text every byte offset whose bytes, after the prefixes the correction accepts,
# decode as D9 /0 or DD /0 with a memory operand, plus the 15 bytes after it,
# which contain the fall-through PC. The handler still decodes and checks each
# instruction itself, so the correction is unchanged; only instructions that
# cannot be or follow such a load run without it. A write into program text
# restores the global hook (Machine._text_written).
X87_LOAD_PREFIXES = bytes((0x66, 0x67, 0x26, 0x2e, 0x36, 0x3e, 0x64, 0x65))
X87_LOAD_PATTERN = re.compile(rb'(?=[\xd9\xdd][\x00-\x07\x40-\x47\x80-\x87])')
X87_LOAD_REACH = 15        # longest x86 instruction; the fall-through PC lies within it
X87_LOAD_MERGE_GAP = 256   # merging nearby windows bounds the number of Unicorn hooks


def x87_load_ranges(text_base, code, gap=X87_LOAD_MERGE_GAP):
    """Inclusive [first, last] text ranges that contain every possible FLD m32/m64 start and its fall-through."""
    ranges = []
    for match in X87_LOAD_PATTERN.finditer(code):
        start = match.start()
        while start and code[start - 1] in X87_LOAD_PREFIXES:
            start -= 1
        first, last = text_base + start, text_base + match.start() + 1 + X87_LOAD_REACH
        if ranges and first <= ranges[-1][1] + gap:
            ranges[-1][1] = max(ranges[-1][1], last)
        else:
            ranges.append([first, last])
    return [(first, last) for first, last in ranges]


# Independent, hand-written architectural primitives. No original instructions
# or addresses are copied into this program, and no guest body can be selected.
# bytes, stack-word operands, consumed, produced, minimum live depth, stores m64
X87_STEPS = {
    1: (bytes.fromhex('d9ed'), 0, 0, 1, 0, False),
    2: (bytes.fromhex('db0500204000'), 1, 0, 1, 0, False),
    3: (bytes.fromhex('dd0500204000'), 2, 0, 1, 0, False),
    4: (bytes.fromhex('d9f1'), 0, 2, 1, 2, False),
    5: (bytes.fromhex('d8f1'), 0, 1, 1, 2, False),
    6: (bytes.fromhex('ddd8'), 0, 1, 0, 1, False),
    7: (bytes.fromhex('d9e0'), 0, 1, 1, 1, False),  # FCHS
    8: (bytes.fromhex('dc2d00204000'), 2, 1, 1, 1, False),  # FSUBR m64
    9: (bytes.fromhex('dc0d00204000'), 2, 1, 1, 1, False),  # FMUL m64
    10: (bytes.fromhex('dd1d00204000 dd0500204000'), 0, 1, 1, 1, False),  # FSTP/FLD m64
    11: (bytes.fromhex('dc3500204000'), 2, 1, 1, 1, False),  # FDIV m64
    12: (bytes.fromhex('d8c1'), 0, 1, 1, 2, False),  # FADD ST(0), ST(1), no pop
    13: (bytes.fromhex('dc0500204000'), 2, 1, 1, 1, False),  # FADD m64
    14: (bytes.fromhex('ded9'), 0, 2, 0, 2, False),  # FCOMPP
    15: (bytes.fromhex('d9fa'), 0, 1, 1, 1, False),  # FSQRT
    16: (bytes.fromhex('d9e1'), 0, 1, 1, 1, False),  # FABS
    17: (bytes.fromhex('dc1500204000'), 2, 0, 0, 1, False),  # FCOM m64
    18: (bytes.fromhex('dc1d00204000'), 2, 1, 0, 1, False),  # FCOMP m64
    19: (bytes.fromhex('dc2500204000'), 2, 1, 1, 1, False),  # FSUB m64
    20: (bytes.fromhex('dd1500204000'), 0, 1, 1, 1, True),  # FST m64, bits in EDX:EAX
    21: (bytes.fromhex('dd1d00204000'), 0, 1, 0, 1, True),  # FSTP m64, bits in EDX:EAX
    22: (bytes.fromhex('d9fe'), 0, 1, 1, 1, False),  # FSIN, including C2 range behavior
    23: (bytes.fromhex('d9ff'), 0, 1, 1, 1, False),  # FCOS, including C2 range behavior
}
# Register-indexed forms: operation base + i selects ST(i), i = 0..7.
# base: (opcode, modrm base, stack effect). Effects with k = i + 1 live
# slots touched: 'load' pop 0/push 1, 'compare' 0/0, 'compare_pop' 1/0,
# 'top' 1/1 (ST(0) replaced), 'pair' k/k (ST(0)..ST(i) replaced),
# 'pair_pop' k/k-1 (ST(i) replaced, then popped).
X87_REGISTER_FORMS = {
    0x100: (0xd9, 0xc0, 'load'),         # FLD ST(i)
    0x108: (0xd9, 0xc8, 'pair'),         # FXCH ST(i)
    0x110: (0xdd, 0xd0, 'pair'),         # FST ST(i)
    0x118: (0xdd, 0xd8, 'pair_pop'),     # FSTP ST(i)
    0x120: (0xd8, 0xd0, 'compare'),      # FCOM ST(i)
    0x128: (0xd8, 0xd8, 'compare_pop'),  # FCOMP ST(i)
    0x130: (0xd8, 0xc0, 'top'),          # FADD ST(0), ST(i)
    0x138: (0xd8, 0xc8, 'top'),          # FMUL ST(0), ST(i)
    0x140: (0xd8, 0xe0, 'top'),          # FSUB ST(0), ST(i)
    0x148: (0xd8, 0xe8, 'top'),          # FSUBR ST(0), ST(i)
    0x150: (0xd8, 0xf0, 'top'),          # FDIV ST(0), ST(i)
    0x158: (0xd8, 0xf8, 'top'),          # FDIVR ST(0), ST(i)
    0x160: (0xdc, 0xc0, 'pair'),         # FADD ST(i), ST(0)
    0x168: (0xdc, 0xc8, 'pair'),         # FMUL ST(i), ST(0)
    0x170: (0xdc, 0xe0, 'pair'),         # FSUBR ST(i), ST(0)
    0x178: (0xdc, 0xe8, 'pair'),         # FSUB ST(i), ST(0)
    0x180: (0xdc, 0xf0, 'pair'),         # FDIVR ST(i), ST(0)
    0x188: (0xdc, 0xf8, 'pair'),         # FDIV ST(i), ST(0)
    0x190: (0xde, 0xc0, 'pair_pop'),     # FADDP ST(i), ST(0)
    0x198: (0xde, 0xc8, 'pair_pop'),     # FMULP ST(i), ST(0)
    0x1a0: (0xde, 0xe0, 'pair_pop'),     # FSUBRP ST(i), ST(0)
    0x1a8: (0xde, 0xe8, 'pair_pop'),     # FSUBP ST(i), ST(0)
    0x1b0: (0xde, 0xf0, 'pair_pop'),     # FDIVRP ST(i), ST(0)
    0x1b8: (0xde, 0xf8, 'pair_pop'),     # FDIVP ST(i), ST(0)
}
for _base, (_opcode, _modrm, _effect) in X87_REGISTER_FORMS.items():
    for _i in range(8):
        _k = _i + 1
        _pop, _push = {'load': (0, 1), 'compare': (0, 0), 'compare_pop': (1, 0), 'top': (1, 1),
                       'pair': (_k, _k), 'pair_pop': (_k, _k - 1)}[_effect]
        X87_STEPS[_base + _i] = (bytes((_opcode, _modrm + _i)), 0, _pop, _push, _k, False)
del _base, _opcode, _modrm, _effect, _i, _k, _pop, _push
X87_STEP_SLOTS = {op: index + 1 for index, op in enumerate(sorted(X87_STEPS))}
assert 16 * (len(X87_STEPS) + 1) <= 0x1000


class EmulationFault(Exception):
    """The original instructions faulted: a bad memory access or an unmapped jump."""


CONTEXT_FIELDS = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp', 'eip', 'eflags', 'fsHead')
CONTEXT_REGISTERS = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                     UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
                     UC_X86_REG_EIP, UC_X86_REG_EFLAGS)
CONTEXT_ALL = (1 << 11) - 1
CONTEXT_REQUIRED = sum(1 << CONTEXT_FIELDS.index(n) for n in ('eax', 'ebp', 'esp', 'eip', 'fsHead'))


class ContextFault(EmulationFault):
    """Malformed compiler transport; never a guest exception."""


class OwnedEntryStop(Exception):
    """Stopped before an owned instruction; handled outside Unicorn execution."""
    def __init__(self, invocation):
        self.invocation = invocation


def validate_context(context, address, program, returned=False):
    names = ('size', 'version', 'inputMask', 'outputMask', *CONTEXT_FIELDS,
             'continuation', 'reserved0', 'reserved1')
    if any(type(getattr(context, name)) is not int or not 0 <= getattr(context, name) <= 0xffffffff
           for name in names):
        raise ContextFault('compiler context requires uint32 fields')
    if (context.size != 72 or context.version != 1 or context.reserved0 or context.reserved1 or
            context.inputMask & ~CONTEXT_ALL or context.outputMask & ~CONTEXT_ALL or
            context.inputMask & CONTEXT_REQUIRED != CONTEXT_REQUIRED or
            context.outputMask & CONTEXT_REQUIRED != CONTEXT_REQUIRED or
            not program.in_text(address) or not program.in_text(context.continuation) or
            context.continuation == STOP or context.eip != (context.continuation if returned else address) or
            context.esp & 3 or
            not STACK_BASE <= context.esp <= STACK_BASE + STACK_SIZE - (0 if returned else 4) or
            (context.fsHead != 0xffffffff and
             (context.fsHead & 3 or not STACK_BASE <= context.fsHead <= STACK_BASE + STACK_SIZE - 12)) or
            ((context.inputMask | context.outputMask) & (1 << 9) and
             (context.eflags & ~0x8d7 or not context.eflags & 2))):
        raise ContextFault('invalid compiler context masks, code identity, flags or bounded frame')


SOURCE_INPUT_REQUIRED = 0x5c0
SOURCE_OUTPUT_REQUIRED = 0x581
SOURCE_PRESERVABLE = 0x472


@dataclass(frozen=True)
class SourceFixtureCapability:
    """One case's exact registered stand-in, never permission to execute code."""
    address: int
    registration: tuple
    registry: dict

    def validate(self, address, signature):
        if (address != self.address or not STUB_BASE <= address < STUB_BASE + STUB_SIZE or
                self.registry.get(address) is not self.registration or
                self.registration[0] is not signature or signature.address != address or
                signature.convention not in ('cdecl', 'stdcall', 'thiscall', 'fastcall') or
                type(signature.argc) is not int or not 0 <= signature.argc <= CALL_ARGUMENT_CAPACITY or
                self.registration[1] is None):
            raise ContextFault('unknown, retired or mismatched source fixture capability')


def validate_source(context, address, return_pc, program, returned=False):
    _validate_source_state(context, address, return_pc, program, returned,
                           program.in_text(address) or address in program.imports)


def validate_source_fixture(context, address, return_pc, program, capability, signature, returned=False):
    capability.validate(address, signature)
    _validate_source_state(context, address, return_pc, program, returned, True)


def _validate_source_state(context, address, return_pc, program, returned, target_valid):
    names = ('size', 'version', 'inputMask', 'outputMask', *CONTEXT_FIELDS,
             'preserveMask', 'reserved0', 'reserved1')
    if any(type(getattr(context, n)) is not int or not 0 <= getattr(context, n) <= 0xffffffff for n in names):
        raise ContextFault('source context requires uint32 fields')
    if (context.size != 72 or context.version != 1 or context.reserved0 or context.reserved1 or
            context.inputMask & ~CONTEXT_ALL or context.outputMask & ~CONTEXT_ALL or
            context.inputMask & SOURCE_INPUT_REQUIRED != SOURCE_INPUT_REQUIRED or
            context.outputMask & SOURCE_OUTPUT_REQUIRED != SOURCE_OUTPUT_REQUIRED or
            context.preserveMask & ~SOURCE_PRESERVABLE or
            context.preserveMask & context.inputMask != context.preserveMask or
            context.preserveMask & context.outputMask != context.preserveMask or
            not target_valid or type(return_pc) is not int or not program.in_text(return_pc) or
            return_pc == STOP or context.eip != (return_pc if returned else address) or context.esp & 3 or
            not STACK_BASE <= context.esp <= STACK_BASE + STACK_SIZE - (0 if returned else 4) or
            (context.fsHead != 0xffffffff and
             (context.fsHead & 3 or not STACK_BASE <= context.fsHead <= STACK_BASE + STACK_SIZE - 12)) or
            ((context.inputMask | context.outputMask) & (1 << 9) and
             (context.eflags & ~0x8d7 or not context.eflags & 2))):
        raise ContextFault('invalid ordinary source capability, masks, code identity, flags or frame')


def validate_source_operands(context, convention, ecx, edx, arguments):
    if convention not in ('cdecl', 'stdcall', 'thiscall', 'fastcall') or len(arguments) > CALL_ARGUMENT_CAPACITY:
        raise ContextFault('unsupported source ordinary signature')
    if (context.esp + 4 * (1 + len(arguments)) > STACK_BASE + STACK_SIZE or
            (convention not in ('thiscall', 'fastcall') and ecx) or (convention != 'fastcall' and edx) or
            (convention in ('thiscall', 'fastcall') and (not context.inputMask & 4 or context.ecx != ecx)) or
            (convention == 'fastcall' and (not context.inputMask & 8 or context.edx != edx))):
        raise ContextFault('source ordinary operands disagree with register state or frame')


def validate_source_output(context, before, address, return_pc, pop_bytes, program):
    validate_source(context, address, return_pc, program, True)
    _validate_source_result(context, before, pop_bytes)


def validate_source_fixture_output(context, before, address, return_pc, pop_bytes, program, capability, signature):
    validate_source_fixture(context, address, return_pc, program, capability, signature, True)
    _validate_source_result(context, before, pop_bytes)


def _validate_source_result(context, before, pop_bytes):
    for n in ('size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1'):
        if getattr(context, n) != getattr(before, n):
            raise ContextFault('source context immutable header changed')
    if context.esp != before.esp + 4 + pop_bytes:
        raise ContextFault('source ordinary return pop mismatch')
    for i, n in enumerate(CONTEXT_FIELDS):
        if (not before.outputMask & (1 << i) or before.preserveMask & (1 << i)) and getattr(context, n) != getattr(before, n):
            raise ContextFault('source ordinary preserved or unselected register changed: ' + n)


@dataclass
class Returned:
    eax: int
    stack_pointer: int
    completed: bool


class Machine:
    def __init__(self, program, heap_base, heap_size):
        self.program = program
        self.heap_base, self.heap_size = heap_base, heap_size
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(program.base, program.size)
        for section in program.sections:
            if section.data:
                self.uc.mem_write(section.address, section.data)
        self.uc.mem_map(heap_base, heap_size)
        self.uc.mem_map(STACK_BASE, STACK_SIZE)
        self.uc.mem_map(STUB_BASE, STUB_SIZE)
        self.uc.mem_write(STUB_BASE, b"\xC3" * STUB_SIZE)
        self.uc.reg_write(UC_X86_REG_FPCW, 0x37F)
        self.uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
        self._map_thread_block()
        self.on_external = None   # callable(machine, address) installed by the owner
        self.guest_exceptions = None  # opt-in scoped physical exception driver
        self._intercepted = {}
        self._pending = None
        self._execution_depth = 0
        self._physical_pump = False
        self._deferred_external = None
        self._active_emulations = 0
        self.maximum_active_emulations = 0
        self._callback_returns = []
        self._callback_entries = []
        self._source_returns = []
        self._owned_scope = None
        self.blocks = None        # a set of (address, size) while coverage is being traced
        self._block_hook = None
        # Install before observers: they must see the architectural FLD result.
        self._x87_loaded = None
        self._install_x87_load_hooks()
        self.uc.hook_add(UC_HOOK_CODE, self._external, begin=STUB_BASE, end=STUB_BASE + STUB_SIZE - 1)
        for address in program.startup_calls:
            if not self.call(address).completed:
                raise RuntimeError(f"startup call {address:#x} did not return")
        if program.control_word:
            mask, value = program.control_word
            found = self.uc.reg_read(UC_X86_REG_FPCW)
            if found & mask != value:
                raise RuntimeError(f"x87 control word {found:#x} does not match the original's precision setting")
        # Each import slot gets its own stand-in address so that an import call
        # is recognisable. The slot values are part of the compared image.
        self.import_stub = {}
        for index, slot in enumerate(sorted(program.imports)):
            self.import_stub[slot] = STUB_BASE + index
            self.write(slot, struct.pack("<I", STUB_BASE + index))
        self.first_free_stub = STUB_BASE + len(program.imports)
        self.initial_control_word = self.register(UC_X86_REG_FPCW)

    def _install_x87_load_hooks(self):
        """Hook every address outside text and each possible FLD m32/m64 window inside it (see X87_LOAD_PATTERN)."""
        low, high = self.program.text
        code = bytes(self.uc.mem_read(low, high - low)) if high > low else b''
        ranges = [(0, low - 1)] if low else []
        ranges += x87_load_ranges(low, code)
        ranges.append((high, 0xFFFFFFFF))
        self._x87_load_hooks = [self.uc.hook_add(UC_HOOK_CODE, self._x87_load_instruction, begin=first, end=last)
                                for first, last in ranges if first <= last]
        self.x87_load_ranges = ranges
        # Live text that no longer matches the scanned bytes falls back to the
        # global hook. Unicorn invalidates translations of written code itself.
        self._text_written = False
        if high > low:
            self.uc.hook_add(UC_HOOK_MEM_WRITE, self._text_write, begin=low, end=high - 1)

    def _text_write(self, uc, kind, address, size, value, user):
        self._global_x87_load_hook()

    def _global_x87_load_hook(self):
        if self._text_written:
            return
        self._text_written = True
        for hook in self._x87_load_hooks:
            self.uc.hook_del(hook)
        self._x87_load_hooks = [self.uc.hook_add(UC_HOOK_CODE, self._x87_load_instruction)]
        self.x87_load_ranges = [(0, 0xFFFFFFFF)]
        self.uc.ctl_remove_cache(*self.program.text)

    def _finish_x87_load(self):
        """Correct only a successfully executed, masked FLD m32/m64 signaling NaN.

        Unicorn preserves the signaling bit and omits IE on this conversion.
        Intel SDM vol. 1 section 4.8.3.5 and vol. 2 FLD require quieting and IE.
        Wait until after the actual load: Unicorn retains address translation,
        memory faults, stack checks, tags, TOP and all non-signaling values.
        No guest input bytes or stored results are patched.
        """
        pending, self._x87_loaded = self._x87_loaded, None
        if pending is None:
            return
        next_pc, top = pending
        status = self.register(UC_X86_REG_FPSW)
        if (self.register(UC_X86_REG_EIP) != next_pc or
                (status >> 11) & 7 != top or
                (self.register(UC_X86_REG_FPTAG) >> (2 * top)) & 3 == 3):
            return
        significand, exponent = self.register(UC_X86_REG_FP0 + top)
        if (exponent & 0x7fff == 0x7fff and significand & (1 << 63) and
                significand & ((1 << 62) - 1) and not significand & (1 << 62)):
            self.uc.reg_write(UC_X86_REG_FP0 + top, (significand | (1 << 62), exponent))
            self.uc.reg_write(UC_X86_REG_FPSW, status | 1)

    def _x87_load_instruction(self, uc, address, size, user):
        self._finish_x87_load()
        if not 2 <= size <= 15:
            return
        code = bytes(uc.mem_read(address, size))
        offset = 0
        # Operand/address-size and segment overrides do not change FLD's format.
        # LOCK/REP are deliberately not accepted by this bounded correction.
        while offset < len(code) and code[offset] in (0x66, 0x67, 0x26, 0x2e, 0x36, 0x3e, 0x64, 0x65):
            offset += 1
        if offset + 1 >= len(code) or code[offset] not in (0xd9, 0xdd):
            return
        modrm = code[offset + 1]
        if modrm & 0xc0 == 0xc0 or modrm & 0x38:  # D9 /0 or DD /0 memory only
            return
        if not self.register(UC_X86_REG_FPCW) & 1:
            return
        top = ((self.register(UC_X86_REG_FPSW) >> 11) - 1) & 7
        if (self.register(UC_X86_REG_FPTAG) >> (2 * top)) & 3 != 3:
            return  # Stack overflow belongs to Unicorn, not this correction.
        self._x87_loaded = ((address + size) & 0xffffffff, top)

    def reset_x87(self):
        """Each comparison side starts with the program's precision and an empty stack."""
        self.uc.reg_write(UC_X86_REG_FPCW, self.initial_control_word)
        self.uc.reg_write(UC_X86_REG_FPSW, 0)
        self.uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)

    @staticmethod
    def extended(value):
        """Exact IEEE binary64 -> x87 register bits, without host long-double assumptions."""
        bits = struct.unpack("<Q", struct.pack("<d", value))[0]
        sign, exponent, fraction = bits >> 63, (bits >> 52) & 0x7FF, bits & ((1 << 52) - 1)
        if exponent == 0x7FF:
            return ((1 << 63) | (fraction << 11), (sign << 15) | 0x7FFF)
        if exponent:
            return (((1 << 52) | fraction) << 11, (sign << 15) | (exponent - 1023 + 16383))
        if not fraction:
            return (0, sign << 15)
        leading = fraction.bit_length() - 1
        return (fraction << (63 - leading), (sign << 15) | (leading - 1074 + 16383))

    def push_x87(self, value):
        top = ((self.register(UC_X86_REG_FPSW) >> 11) - 1) & 7
        tags = self.register(UC_X86_REG_FPTAG)
        if (tags >> (2 * top)) & 3 != 3:
            raise EmulationFault("x87 operand transfer would overwrite a live register")
        significand, exponent = self.extended(value)
        tag = 1 if significand == 0 else (2 if exponent & 0x7FFF == 0x7FFF else 0)
        self.uc.reg_write(UC_X86_REG_FP0 + top, (significand, exponent))
        self.uc.reg_write(UC_X86_REG_FPTAG, (tags & ~(3 << (2 * top))) | (tag << (2 * top)))
        self.uc.reg_write(UC_X86_REG_FPSW, (self.register(UC_X86_REG_FPSW) & ~(7 << 11)) | (top << 11))

    def x87_step(self, operation, state, operands=()):
        """One bounded numerical primitive in an isolated interpreter.

        Never runs guest code, shares memory, or uses the host's double math.
        This is comparison infrastructure, not an app math implementation.
        """
        if operation not in X87_STEPS:
            raise ContextFault('unknown x87 primitive')
        code, argc, pop, push, minimum, stores = X87_STEPS[operation]
        if not supported_x87_control(state[0]) or len(operands) != argc or len(state[2]) < minimum or len(state[2]) - pop + push > 8:
            raise ContextFault('invalid x87 primitive arity or depth')
        if not hasattr(self, '_x87_arithmetic'):
            from .program import Program, Section
            text = bytearray(0x1000)
            for op, (instructions, *_) in X87_STEPS.items():
                slot = 16 * X87_STEP_SLOTS[op]
                text[slot:slot + len(instructions) + 1] = instructions + b'\xc3'
            program = Program('x87-primitives', '', 0x400000, 0x3000,
                [Section('.text', 0x401000, len(text), bytes(text)),
                 Section('.data', 0x402000, 0x1000, bytes(0x1000))], (0x401000, 0x402000), {})
            self._x87_arithmetic = Machine(program, 0x3000000, 0x1000)
        arithmetic = self._x87_arithmetic
        arithmetic.set_x87_state(*state)
        arithmetic.write(0x402000, struct.pack('<2I', *(tuple(operands) + (0,) * (2-len(operands)))))
        if not arithmetic.call(0x401000 + 16 * X87_STEP_SLOTS[operation]).completed:
            raise ContextFault('x87 primitive did not complete')
        # A store primitive's binary64 bits; zero for every other primitive.
        self.x87_stored = struct.unpack('<Q', arithmetic.read(0x402000, 8))[0] if stores else 0
        return arithmetic.x87_state()

    def x87_state(self):
        """Exact contiguous logical stack, including live values below arguments."""
        status, tags = self.register(UC_X86_REG_FPSW), self.register(UC_X86_REG_FPTAG)
        top, slots, empty = (status >> 11) & 7, [], False
        for i in range(8):
            physical = (top + i) & 7
            if (tags >> (2 * physical)) & 3 == 3:
                empty = True
            elif empty:
                raise EmulationFault('exact x87 boundary requires a contiguous live stack')
            else:
                slots.append(self.register(UC_X86_REG_FP0 + physical))
        return self.register(UC_X86_REG_FPCW), status, tuple(slots)

    def set_x87_state(self, control, status, slots):
        """Install exact register bits, never round through a host float."""
        if len(slots) > 8:
            raise EmulationFault('x87 stack overflow')
        top, tags = (status >> 11) & 7, 0xffff
        for i, (significand, exponent) in enumerate(slots):
            physical = (top + i) & 7
            tag = (1 if significand == 0 and exponent & 0x7fff == 0 else
                   2 if exponent & 0x7fff in (0, 0x7fff) or not significand & (1 << 63) else 0)
            self.uc.reg_write(UC_X86_REG_FP0 + physical, (significand, exponent))
            tags = (tags & ~(3 << (2 * physical))) | (tag << (2 * physical))
        self.uc.reg_write(UC_X86_REG_FPCW, control)
        self.uc.reg_write(UC_X86_REG_FPSW, status)
        self.uc.reg_write(UC_X86_REG_FPTAG, tags)

    def x87_operand(self):
        top = (self.register(UC_X86_REG_FPSW) >> 11) & 7
        tags = self.register(UC_X86_REG_FPTAG)
        if (tags >> (2 * top)) & 3 == 3:
            raise EmulationFault("declared x87 callee has an empty ST(0)")
        if tags | (3 << (2 * top)) != 0xFFFF:
            raise EmulationFault("x87 boundary supports only one live register operand")
        return self.register(UC_X86_REG_FP0 + top)

    def observe(self, address, observer):
        """Observe entry without replacing or skipping any original instruction."""
        def entered(uc, address, size, user):
            try:
                observer(self, address)
            except BaseException as error:
                self._pending = error
                uc.emu_stop()
        self.uc.hook_add(UC_HOOK_CODE, entered, begin=address, end=address)

    def _map_thread_block(self):
        """Functions with an exception frame read and write fs:[0]. Give them a block to do it in.

        The emulator's FS base is 0, so the block is the page at address 0. Only instructions with an FS prefix
        may touch that page; any other access is a null pointer and stops the run. Compiler-context bridges explicitly transfer the FS head; ordinary outer calls
        initialize it once. This does not implement exception dispatch.
        """
        self.uc.mem_map(THREAD_BLOCK, 0x1000)
        self.uc.mem_write(THREAD_BLOCK, struct.pack("<I", 0xFFFFFFFF))  # end of the exception chain

        def access(uc, kind, address, size, value, user):
            where = uc.reg_read(UC_X86_REG_EIP)
            if 0x64 not in bytes(uc.mem_read(where, 3)):
                self._pending = EmulationFault(f"null pointer access at {address:#x} from instruction {where:#x}")
                uc.emu_stop()

        self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, access, begin=THREAD_BLOCK, end=THREAD_BLOCK + 0xFFF)

    # Memory and registers
    def read(self, address, count):
        return bytes(self.uc.mem_read(address, count))

    def write(self, address, data):
        data = bytes(data)
        low, high = self.program.text
        if not getattr(self, '_text_written', True) and address < high and address + len(data) > low:
            first, last = max(address, low), min(address + len(data), high)
            if bytes(self.uc.mem_read(first, last - first)) != data[first - address:last - address]:
                self._global_x87_load_hook()
        self.uc.mem_write(address, data)

    def words(self, address, count):
        return struct.unpack(f"<{count}I", self.read(address, 4 * count)) if count else ()

    def register(self, which):
        return self.uc.reg_read(which)

    # Interception
    def intercept(self, address):
        """Hand calls that reach `address` (inside the program) to on_external instead of executing it."""
        if address not in self._intercepted:
            self._intercepted[address] = self.uc.hook_add(UC_HOOK_CODE, self._external, begin=address, end=address)

    def release_intercepts(self):
        for handle in self._intercepted.values():
            self.uc.hook_del(handle)
        self._intercepted = {}

    @contextmanager
    def stop_owned_entries(self, ranges, capture):
        """Scope a pre-instruction stop; capture may only inspect guest state."""
        if self._owned_scope is not None:
            raise ContextFault('owned entry scope already active')
        if not ranges or any(type(lo) is not int or type(hi) is not int or lo >= hi or
                             not self.program.in_text(lo) or not self.program.in_text(hi - 1)
                             for lo, hi in ranges):
            raise ContextFault('invalid owned instruction ranges')
        self._owned_scope = (tuple(ranges), capture)
        hooks = []
        def stop(uc, address, size, user):
            if self._source_return_boundary(address):
                return
            if self._pending is not None:
                uc.emu_stop()
                return
            try:
                self._pending = OwnedEntryStop(capture(address))
            except BaseException as error:
                self._pending = error
            uc.emu_stop()
        try:
            for lo, hi in ranges:
                hooks.append(self.uc.hook_add(UC_HOOK_CODE, stop, begin=lo, end=hi - 1))
            self.uc.ctl_remove_cache(*self.program.text)
            yield
        finally:
            for hook in hooks:
                self.uc.hook_del(hook)
            self.uc.ctl_remove_cache(*self.program.text)
            self._owned_scope = None

    def _source_return_boundary(self, address):
        """True at a scoped source return, before the continuation executes."""
        frame = self.register(UC_X86_REG_ESP)
        return any(address == pc and frame > entry for pc, entry in self._source_returns)

    def _external(self, uc, address, size, user):
        if self._source_return_boundary(address):
            return
        if self._pending is not None:
            uc.emu_stop()
            return
        try:
            if self._owned_scope is not None:
                ranges, capture = self._owned_scope
                if any(lo <= address < hi for lo, hi in ranges):
                    raise OwnedEntryStop(capture(address))
            if self.guest_exceptions is not None:
                self.guest_exceptions.capture(address)
            if self._physical_pump:
                if self._deferred_external is not None:
                    raise ContextFault('physical request already pending')
                self._deferred_external = address
                uc.emu_stop()
            else:
                self.on_external(self, address)
        except BaseException as error:  # surfaces after emulation stops
            self._pending = error
            uc.emu_stop()

    def return_from_external(self, value, argument_bytes):
        """Finish an intercepted call: set EAX, drop the return address and callee-popped arguments, resume the caller."""
        stack_pointer = self.register(UC_X86_REG_ESP)
        return_address = self.words(stack_pointer, 1)[0]
        self.uc.reg_write(UC_X86_REG_EAX, value & 0xFFFFFFFF)
        self.uc.reg_write(UC_X86_REG_ESP, stack_pointer + 4 + argument_bytes)
        self.uc.reg_write(UC_X86_REG_EIP, return_address)

    # Coverage
    def trace_blocks(self, enabled):
        if bool(enabled) == (self._block_hook is not None):
            return
        if enabled and self._block_hook is None:
            self.blocks = set()
            low, high = self.program.text
            self._block_hook = self.uc.hook_add(UC_HOOK_BLOCK, self._block, begin=low, end=high - 1)
        elif not enabled and self._block_hook is not None:
            self.uc.hook_del(self._block_hook)
            self._block_hook = None
        # Unicorn's translated blocks retain the instrumentation present when
        # they were compiled. Native-side original helpers may have warmed even
        # owned code before tracing starts; rebuild it on either hook change.
        self.uc.ctl_remove_cache(*self.program.text)

    def _block(self, uc, address, size, user):
        self.blocks.add((address, size))

    # Heap watching
    def watch_heap(self, observer):
        """Report every heap access to observer(address, size, is_write, instruction_address), or stop when None."""
        if getattr(self, "_heap_hook", None) is not None:
            self.uc.hook_del(self._heap_hook)
            self._heap_hook = None
        if observer is not None:
            def access(uc, kind, address, size, value, user):
                observer(address, size, kind == UC_MEM_WRITE, uc.reg_read(UC_X86_REG_EIP))
            self._heap_hook = self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, access, begin=self.heap_base,
                                               end=self.heap_base + self.heap_size - 1)

    # Calls
    def call(self, address, ecx=0, edx=0, arguments=(), stack_pointer=STACK_TOP, timeout_seconds=30.0,
             *, reset_thread=True):
        """Call at callee-entry ESP: return word at SP and arguments at SP+4.

        STOP is an execution sentinel, not an original return-site identity.
        Raises whatever an interception raised.
        """
        if (type(stack_pointer) is not int or stack_pointer & 3 or stack_pointer < STACK_BASE or
                stack_pointer + 4 * (1 + len(arguments)) > STACK_BASE + STACK_SIZE):
            raise EmulationFault("ordinary call frame outside bounded stack")
        self.write(stack_pointer, struct.pack(f"<{1 + len(arguments)}I", STOP, *(a & 0xFFFFFFFF for a in arguments)))
        self.uc.reg_write(UC_X86_REG_ESP, stack_pointer)
        self.uc.reg_write(UC_X86_REG_ECX, ecx & 0xFFFFFFFF)
        self.uc.reg_write(UC_X86_REG_EDX, edx & 0xFFFFFFFF)
        self._pending = None
        if reset_thread:
            self.fs_head = 0xffffffff
        return self._execute(address, STOP, timeout_seconds)

    @property
    def fs_head(self):
        return self.words(THREAD_BLOCK, 1)[0]

    @fs_head.setter
    def fs_head(self, value):
        self.write(THREAD_BLOCK, struct.pack('<I', value))

    def call_context(self, address, context, timeout_seconds=30.0):
        """Execute supplied compiler frame up to its genuine continuation PC.

        No return slot is rewritten. STOP remains a distinct forbidden target.
        Unselected register inputs start deterministically at zero (EFLAGS=2);
        unselected output fields remain untouched. Guest stack and FS writes persist.
        """
        validate_context(context, address, self.program)
        for index, (name, register) in enumerate(zip(CONTEXT_FIELDS, CONTEXT_REGISTERS)):
            value = getattr(context, name) if context.inputMask & (1 << index) else (2 if name == 'eflags' else 0)
            self.uc.reg_write(register, value)
        self.fs_head = context.fsHead
        self._pending = None
        # A continuation can lie inside an already translated basic block.
        # An exact code hook makes stopping independent of Unicorn's cache.
        hook = self.uc.hook_add(UC_HOOK_CODE, lambda uc, pc, size, user: uc.emu_stop(),
                                begin=context.continuation, end=context.continuation)
        self.uc.ctl_remove_cache(*self.program.text)
        try:
            result = self._execute(address, context.continuation, timeout_seconds)
        finally:
            self.uc.hook_del(hook)
            self.uc.ctl_remove_cache(*self.program.text)
        if not result.completed:
            raise ContextFault('compiler callee failed to reach continuation')
        for index, (name, register) in enumerate(zip(CONTEXT_FIELDS, CONTEXT_REGISTERS)):
            if context.outputMask & (1 << index):
                setattr(context, name, self.register(register))
        context.fsHead = self.fs_head
        validate_context(context, address, self.program, returned=True)
        return result

    def call_source(self, address, context, return_pc, convention='cdecl', ecx=0, edx=0,
                    arguments=(), timeout_seconds=30.0, *, prepare_frame=True):
        """Ordinary ABI at its physical source frame, stopping at the real return PC."""
        validate_source(context, address, return_pc, self.program)
        validate_source_operands(context, convention, ecx, edx, arguments)
        frame = struct.pack(f'<{1 + len(arguments)}I', return_pc, *arguments)
        if not prepare_frame and self.read(context.esp, len(frame)) != frame:
            raise ContextFault('source call physical frame disagrees with copied operands')
        before = type(context).from_buffer_copy(context)
        for i, (name, register) in enumerate(zip(CONTEXT_FIELDS, CONTEXT_REGISTERS)):
            self.uc.reg_write(register, getattr(context, name) if context.inputMask & (1 << i)
                              else (2 if name == 'eflags' else 0))
        self.fs_head = context.fsHead
        if prepare_frame:
            self.write(context.esp, frame)
        self._pending = None
        # A nested call may legitimately visit this same original continuation.
        # Its stack still lies within the outer frame. Stop only after that
        # frame has been left; validate_source_output below checks the exact
        # conventional pop and continues to diagnose incorrect RET immediates.
        def returned_to_caller(uc, pc, size, user):
            if uc.reg_read(UC_X86_REG_ESP) > before.esp:
                uc.emu_stop()
        self._source_returns.append((return_pc, before.esp))
        hook = self.uc.hook_add(UC_HOOK_CODE, returned_to_caller, begin=return_pc, end=return_pc)
        self.uc.ctl_remove_cache(*self.program.text)
        try:
            result = self._execute(address, return_pc, timeout_seconds, execution_stop=0)
        finally:
            self.uc.hook_del(hook)
            self._source_returns.pop()
            self.uc.ctl_remove_cache(*self.program.text)
        if not result.completed:
            raise ContextFault('ordinary source callee failed to reach real continuation')
        for i, (name, register) in enumerate(zip(CONTEXT_FIELDS, CONTEXT_REGISTERS)):
            if context.outputMask & (1 << i):
                setattr(context, name, self.register(register))
        context.fsHead = self.fs_head
        pops = 4 * len(arguments) if convention in ('stdcall', 'thiscall', 'fastcall') else 0
        validate_source_output(context, before, address, return_pc, pops, self.program)
        return result

    def _execute(self, address, stop, timeout_seconds, *, execution_stop=None):
        self._execution_depth += 1
        try:
            if self._physical_pump and self._execution_depth > 32:
                raise ContextFault('physical callback graph depth exceeded')
            while True:
                if self._physical_pump and self._active_emulations:
                    raise ContextFault('physical callback attempted simultaneous Unicorn execution')
                self._active_emulations += 1
                self.maximum_active_emulations = max(self.maximum_active_emulations, self._active_emulations)
                try:
                    self.uc.emu_start(address, stop if execution_stop is None else execution_stop,
                                      timeout=0 if self._physical_pump else int(timeout_seconds * 1_000_000))
                finally:
                    # A stop/timeout immediately after FLD has no next code hook.
                    # A fault at FLD leaves EIP unchanged and cannot be corrected.
                    self._finish_x87_load()
                    self._active_emulations -= 1
                if self._pending is not None or not self._physical_pump or self._deferred_external is None:
                    break
                request, self._deferred_external = self._deferred_external, None
                # A physical effect and any callback run only after emu_start has
                # returned. Resume this same live VM; never replay initial state.
                self.on_external(self, request)
                address = self.register(UC_X86_REG_EIP)
        except UcError as error:
            where = self.register(UC_X86_REG_EIP)
            try:
                caller = f"{self.words(self.register(UC_X86_REG_ESP), 1)[0]:#x}"
            except UcError:
                caller = "unreadable"
            raise EmulationFault(f"{error} with EIP {where:#x}; top of stack {caller}") from None
        finally:
            self._execution_depth -= 1
        if self._pending is not None:
            error, self._pending = self._pending, None
            raise error
        completed = self.register(UC_X86_REG_EIP) == stop
        return Returned(self.register(UC_X86_REG_EAX), self.register(UC_X86_REG_ESP), completed)


    def begin_physical_callbacks(self, consume, timeout_seconds=30.0):
        """Opt-in pump; Env owns authority, budget and synchronous request lifetime."""
        if self._physical_pump or self._active_emulations or self.guest_exceptions is not None:
            raise ContextFault('physical callback pump requires a fresh non-EH graph')
        if not 0 < timeout_seconds <= 30.0:
            raise ContextFault('physical callback deadline must be bounded')
        self.uc.mem_map(PHYSICAL_CALLBACK_RETURN, 0x1000)
        self._physical_pump = True
        self._deferred_external = None
        self.maximum_active_emulations = 0
        self._physical_deadline = time.monotonic() + timeout_seconds
        self._physical_last_instruction = None
        def guard(uc, pc, size, user):
            try:
                if time.monotonic() >= self._physical_deadline:
                    raise ContextFault('physical callback graph deadline exhausted')
                consume()
                if self._callback_entries and pc == self._callback_entries[-1][0]:
                    self._callback_entries[-1][1]()
                if pc == PHYSICAL_CALLBACK_RETURN:
                    if not self._callback_returns or self.register(UC_X86_REG_ESP) != self._callback_returns[-1][0]:
                        raise ContextFault('unknown or malformed physical callback return')
                    end, argument_bytes = self._callback_returns[-1]
                    previous = self._physical_last_instruction
                    if (previous is None or self.read(previous[0],previous[1]) != b'\xc2'+struct.pack('<H', argument_bytes) or
                            previous[2] != end-argument_bytes-4):
                        raise ContextFault('physical callback return did not execute declared stdcall RET')
                    uc.emu_stop()
                self._physical_last_instruction = (pc,size,self.register(UC_X86_REG_ESP))
            except BaseException as error:
                self._pending = self._pending or error
                uc.emu_stop()
        self._physical_guard = self.uc.hook_add(UC_HOOK_CODE, guard)

    def end_physical_callbacks(self):
        if self._physical_pump:
            self.uc.hook_del(self._physical_guard)
            self.uc.mem_unmap(PHYSICAL_CALLBACK_RETURN, 0x1000)
        self._physical_pump = False
        self._deferred_external = None
        self._callback_returns.clear()
        self._callback_entries.clear()

    def _call_physical_callback(self, entry, parent, arguments, physical_frame, on_entry, *, enumeration_frame=None,
                                native_dispatch=None):
        """Private typed stdcall4 (or elected enumeration stdcall2) execution.

        The dispatcher frame/return token are synthetic OS transport. They do
        not claim a game CALL site. All guest writes remain in the shared VM.
        """
        argc = 2 if enumeration_frame is not None else 4
        if not self._physical_pump or self._active_emulations or len(arguments) != argc:
            raise ContextFault('physical callback requires the suspended pump and declared stdcall ABI')
        if len(self._callback_returns) >= 16:
            raise ContextFault('physical callback depth exceeded')
        frame_bytes = 4 * (argc + 1)
        frame = enumeration_frame if enumeration_frame is not None else parent.esp - 64 - frame_bytes
        if (frame < STACK_BASE or frame & 3 or frame + frame_bytes > parent.esp or
                parent.esp > STACK_BASE + STACK_SIZE - len(physical_frame)):
            raise ContextFault('physical callback dispatcher frame outside stack')
        if parent.fsHead != 0xffffffff and frame < parent.fsHead+12 and parent.fsHead < parent.esp:
            raise ContextFault('physical callback dispatcher overlaps parent FS registration')
        saved = self.uc.context_save()
        saved_fs = self.fs_head
        registration = self.read(parent.fsHead,12) if parent.fsHead != 0xffffffff else None
        before = {n: getattr(parent,n) for n in ('ebx','esi','edi','ebp','fsHead')}
        for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS):
            self.uc.reg_write(register, getattr(parent,name))
        self.fs_head = parent.fsHead
        self.write(frame, struct.pack(f'<{argc+1}I', PHYSICAL_CALLBACK_RETURN, *arguments))
        self.uc.reg_write(UC_X86_REG_ESP, frame)
        self._callback_returns.append((frame + frame_bytes, 4 * argc))
        self._callback_entries.append((entry,on_entry))
        self._pending = None
        try:
            if native_dispatch is None:
                result = self._execute(entry, PHYSICAL_CALLBACK_RETURN, 30.0, execution_stop=0)
            else:
                # An ordinary selected native module returns through its host
                # ABI, not a guest RET. The physical dispatcher owns this pop.
                on_entry()
                value = native_dispatch(frame)
                self.uc.reg_write(UC_X86_REG_EAX, value)
                self.uc.reg_write(UC_X86_REG_ESP, frame + frame_bytes)
                result = Returned(value, frame + frame_bytes, True)
            if not result.completed or result.stack_pointer != frame + frame_bytes:
                raise ContextFault('physical callback did not perform declared stdcall return')
            for name, register in zip(CONTEXT_FIELDS, CONTEXT_REGISTERS):
                if name in before and self.register(register) != before[name]:
                    raise ContextFault('physical callback changed nonvolatile register: '+name)
            if self.fs_head != before['fsHead']:
                raise ContextFault('physical callback changed FS registration head')
            if registration is not None and self.read(parent.fsHead,12) != registration:
                raise ContextFault('physical callback changed parent FS registration')
            if self.read(parent.esp,len(physical_frame)) != physical_frame:
                raise ContextFault('physical callback changed suspended physical frame')
        finally:
            self._callback_returns.pop()
            self._callback_entries.pop()
        # Only a genuine normal callback return restores suspended parent CPU.
        # Fault/Halt keeps deepest state for the source graph's prefix capture.
        self.uc.context_restore(saved)
        self.fs_head = saved_fs
        return result
