"""Elected ASCII/C-locale CRT comparison services for later-level observers.

This is a native platform replacement, not recovered game code. Original CRT
bodies run only in the independent comparison check. Existing checkpoint input
files remain unchanged; replay reports fingerprint this additive adapter.
"""
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EFLAGS
from Tests.NativeMenuBase.trace import Blocked

ENTRY = 0x4a3dc0
COMPARE = 0x4a3cf0
MAX_STRING = 4096
SERVICES = {ENTRY: 'CRT _mbsicmp (ASCII/C locale)',
            COMPARE: 'CRT _stricmp (ASCII/C locale)'}
ARITHMETIC_FLAGS = 0x8d5


def add_flags(left, right):
    result = (left + right) & 0xffffffff
    return (int(left + right > 0xffffffff)
            | (int((result & 255).bit_count() % 2 == 0) << 2)
            | ((left ^ right ^ result) & 16)
            | (int(result == 0) << 6) | (result & 0x80000000) >> 24
            | ((~(left ^ right) & (left ^ result) & 0x80000000) >> 20))


class StringCompareFixture:
    def comparison_string(self, pointer):
        if pointer < 0x1000 or pointer + MAX_STRING > 0x100000000:
            raise Blocked('CRT comparison requires a bounded non-null string pointer')
        result = bytearray()
        for offset in range(MAX_STRING):
            try:
                value = self.machine.mem_read(pointer + offset, 1)[0]
            except UcError as error:
                raise Blocked('CRT comparison string is unmapped') from error
            if not value:
                return bytes(result)
            if value >= 128:
                raise Blocked('CRT comparison rejects non-ASCII/multibyte input')
            result.append(value)
        raise Blocked('CRT comparison string has no terminator within its bound')

    def fixture(self, address):
        if address not in SERVICES:
            return super().fixture(address)
        self.platform_call(address, SERVICES[address])
        machine = self.machine
        sp = machine.reg_read(UC_X86_REG_ESP)
        try:
            if self.word(0x540e00) or self.word(0x540e88):
                raise Blocked('CRT comparison requires zero multibyte mode and C locale')
            continuation, left_pointer, right_pointer = (self.word(sp + i * 4) for i in range(3))
        except UcError as error:
            raise Blocked('CRT comparison frame or locale state is unmapped') from error
        left, right = self.comparison_string(left_pointer), self.comparison_string(right_pointer)
        folded_left, folded_right = left.lower(), right.lower()
        result = (folded_left > folded_right) - (folded_left < folded_right)
        flags = machine.reg_read(UC_X86_REG_EFLAGS)
        if address == ENTRY:
            # The wrapper preserves ECX; its cdecl argument cleanup determines
            # the observable arithmetic flags, independently of the comparison.
            arithmetic = add_flags((sp - 28) & 0xffffffff, 8)
        else:
            # The C-locale comparison touches only CL when raw bytes differ.
            # Preserve the upper bytes and the last such ASCII fold's CL.
            cl = None
            for a, b in zip(left + b'\0', right + b'\0'):
                if a != b:
                    cl = 0x20 if 65 <= a <= 90 else 0
                if bytes([a]).lower() != bytes([b]).lower():
                    break
            if cl is not None:
                machine.reg_write(UC_X86_REG_ECX,
                    (machine.reg_read(UC_X86_REG_ECX) & 0xffffff00) | cl)
            # Equal finishes on a zero-byte test; unequal returns signed unit
            # order via byte subtraction. These are the defined output flags.
            arithmetic = 0x44 if result == 0 else 0x95 if result < 0 else 0x11
        self.returned(result)
        machine.reg_write(UC_X86_REG_EFLAGS, (flags & ~ARITHMETIC_FLAGS) | arithmetic)
        event = dict(service=SERVICES[address], entry=hex(address), phase=self.phase,
            continuation=hex(continuation), left_pointer=hex(left_pointer),
            right_pointer=hex(right_pointer), left=left.decode('ascii'),
            right=right.decode('ascii'), result=result, entry_stack=hex(sp),
            return_stack=hex(sp + 4), domain='ASCII/C locale',
            retired_stack='callee scratch below entry ESP is not an ABI output')
        self.physical_events.append(event)
        if hasattr(self, 'string_comparisons'):
            self.string_comparisons.append(event)
