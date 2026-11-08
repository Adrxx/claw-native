"""Controls for the Level 13 observer's sparse, non-mutating hook transport."""
import struct
import unittest
from unicorn import UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP
from Tests.NativeLevels.level_thirteen_join import BoundaryMachine


class ObserverTests(unittest.TestCase):
    def machine(self):
        machine = BoundaryMachine(UC_ARCH_X86, UC_MODE_32)
        machine.mem_map(0x1000, 0x4000)
        return machine

    def test_mid_block_receipt_stops_before_store(self):
        machine = self.machine()
        # Hand-authored MOV, ADD, store, HLT; these are not reference game bytes.
        machine.mem_write(0x1000, bytes.fromhex('b8 01000000 83c002 a3 00200000 f4'))
        visits = []
        def observe(uc, address, size, user):
            visits.append(address)
            if address == 0x1008 and visits.count(address) == 1:
                uc.emu_stop()
        machine.hook_add(UC_HOOK_CODE, observe)
        machine.watch(0x1008)
        machine.emu_start(0x1000, 0x100e)
        self.assertEqual(visits, [0x1000, 0x1008])
        self.assertEqual(machine.reg_read(UC_X86_REG_EAX), 3)
        self.assertEqual(machine.mem_read(0x2000, 4), b'\0'*4)
        machine.emu_start(0x1008, 0x100e)
        self.assertEqual(visits, [0x1000, 0x1008, 0x1008])
        self.assertEqual(machine.mem_read(0x2000, 4), struct.pack('<I', 3))

    def test_service_redirect_at_block_entry(self):
        machine = self.machine()
        machine.mem_write(0x1000, bytes.fromhex('e8 fb1f0000 83c005 f4'))
        machine.mem_write(0x3000, bytes.fromhex('b8 63000000 c3'))
        machine.reg_write(UC_X86_REG_ESP, 0x5000)
        visits = []
        def observe(uc, address, size, user):
            visits.append(address)
            if address == 0x3000:
                sp = uc.reg_read(UC_X86_REG_ESP)
                continuation = struct.unpack('<I', uc.mem_read(sp, 4))[0]
                uc.reg_write(UC_X86_REG_EAX, 7)
                uc.reg_write(UC_X86_REG_ESP, sp+4)
                uc.reg_write(UC_X86_REG_EIP, continuation)
        machine.hook_add(UC_HOOK_CODE, observe)
        machine.watch(0x3000)
        machine.emu_start(0x1000, 0x1009)
        self.assertEqual(visits.count(0x3000), 1)
        self.assertEqual(machine.reg_read(UC_X86_REG_EAX), 12)
        self.assertEqual(machine.reg_read(UC_X86_REG_ESP), 0x5000)


if __name__ == '__main__':
    unittest.main()
