"""Hash-pinned original-instruction harness for recovered gameplay routines."""
import hashlib
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_FPCW, UC_X86_REG_EIP

class OriginalV10:
    def __init__(self, path):
        b = path.read_bytes()
        assert hashlib.sha256(b).hexdigest() == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
        pe = struct.unpack_from('<I', b, 60)[0]
        n, opt = struct.unpack_from('<H', b, pe + 6)[0], struct.unpack_from('<H', b, pe + 20)[0]
        base, size = struct.unpack_from('<I', b, pe + 52)[0], struct.unpack_from('<I', b, pe + 80)[0]
        self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        self.u.mem_map(base, (size + 4095) & ~4095)
        for i in range(n):
            o = pe + 24 + opt + 40 * i
            _, va, rs, ro = struct.unpack_from('<4I', b, o + 8)
            if rs:
                self.u.mem_write(base + va, b[ro:ro + rs])
        self.u.mem_map(0x1000000, 0x100000)
        self.u.mem_map(0x2000000, 0x10000)
        self.stack, self.stop = 0x2008000, 0x200f000
        self.executed = set()
        self.u.hook_add(UC_HOOK_CODE, self.hook)
        self.u.reg_write(UC_X86_REG_FPCW, 0x37f)
        self.call(0x4a7ef0, 0)
        self.control_word = self.u.reg_read(UC_X86_REG_FPCW)
        assert self.control_word & 0x0f3f == 0x023f

    def hook(self, uc, address, size, user):
        self.executed.add(address)
        if address == self.stop:
            uc.emu_stop()

    def write_words(self, address, values):
        self.u.mem_write(address, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))

    def read_words(self, address, count):
        return list(struct.unpack('<' + 'I' * count, self.u.mem_read(address, count * 4)))

    def call(self, address, receiver, args=b'', *, max_instructions=500000):
        self.u.mem_write(self.stack, struct.pack('<I', self.stop) + args)
        self.u.reg_write(UC_X86_REG_ESP, self.stack)
        self.u.reg_write(UC_X86_REG_ECX, receiver)
        self.u.emu_start(address, self.stop, count=max_instructions)
        assert self.u.reg_read(UC_X86_REG_EIP) == self.stop, 'Original routine exceeded instruction bound'
        assert self.u.reg_read(UC_X86_REG_ESP) >= self.stack + 4, 'Original routine did not return'
        return self.u.reg_read(UC_X86_REG_EAX)

    def call_float(self, address, receiver, args=b''):
        self.call(address, receiver, args)
        # Capture the completed function's x87 return after it has returned.
        # This does not replace an original instruction or any callee.
        capture, result = 0x10ff000, 0x10ff100
        jump = self.stop - (capture + 11)
        self.u.mem_write(capture, b'\xdd\x1d' + struct.pack('<I', result) + b'\xe9' + struct.pack('<i', jump))
        self.u.emu_start(capture, self.stop, count=3)
        assert self.u.reg_read(UC_X86_REG_EIP) == self.stop
        return struct.unpack('<d', self.u.mem_read(result, 8))[0]
