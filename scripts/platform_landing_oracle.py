"""Execute pinned v1.0 collision code against unchanged retail tile attributes.

Only the tile object's virtual attribute service is a fixture. The original
step splitter, movement dispatch, support/floor scans and coordinate publication
all execute in CLAW.EXE. No family cases or shared harness are changed.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from tools.claw.test_level import entries, unpack_world, collision_descriptions, word
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP


class LandingOracle:
    MANAGER, ACTOR, PLANE, TABLE = (0x1000000 + i * 0x10000 for i in range(4))
    CELLS, ROWS = 0x1200000, 0x1600000
    TYPES, VTABLE, ATTRIBUTE = 0x1100000, 0x1110000, 0x1110100

    def __init__(self, level=1):
        self.program = claw()
        self.machine = Machine(self.program, self.MANAGER, 0x700000)
        self.raw, planes = unpack_world(next(data for name, data in entries()
                                            if name == f'LEVEL{level}/WORLDS/WORLD.WWD'))
        plane = next(p for p in planes if p['flags'] & 1)
        self.descriptions = collision_descriptions(self.raw)
        self.tw, self.th, width, height = struct.unpack_from('<4I', self.raw, plane['header']+88)
        tiles = self.raw[word(self.raw, plane['header']+132):][:width*height*4]
        assert len(tiles) == width*height*4 and self.CELLS+len(tiles) <= self.ROWS
        self.machine.write(self.CELLS, bytes(tiles))
        self.put(self.ROWS, *(i*width for i in range(height)))
        self.put(self.MANAGER+0x4c, self.TABLE)
        self.put(self.MANAGER+0x5c, self.PLANE)
        self.put(self.MANAGER+0xc, self.MANAGER+0x1000)
        self.put(self.MANAGER+0x1008, self.MANAGER+0x2000)  # empty platform list
        self.put(self.PLANE+0x20, self.CELLS, self.ROWS)
        self.put(self.PLANE+0x30, width*self.tw, height*self.th)
        self.put(self.PLANE+0x8c, self.tw.bit_length()-1, self.th.bit_length()-1)
        for i in range(len(self.descriptions)):
            self.put(self.TABLE+4*i, self.TYPES+8*i)
            self.put(self.TYPES+8*i, self.VTABLE, i)
        self.put(self.VTABLE+0x20, self.ATTRIBUTE)
        self.machine.intercept(self.ATTRIBUTE)
        self.machine.on_external = self.attribute
        # Original 0x42ce90, at 0x42cfaf, installs decimal 14 in both limits.
        assert self.machine.read(0x42cfaf, 11) == bytes.fromhex('b90e000000894864894868')

    def put(self, address, *values):
        self.machine.write(address, struct.pack('<'+'I'*len(values), *(v & 0xffffffff for v in values)))

    def attribute(self, machine, address):
        assert address == self.ATTRIBUTE, hex(address)
        tile = machine.words(machine.register(UC_X86_REG_ECX)+4, 1)[0]
        x, y = machine.words(machine.register(UC_X86_REG_ESP)+4, 2)
        desc = self.descriptions[tile]
        if desc[0] == 1:
            value = desc[1]
        else:
            _, outside, inside, left, top, right, bottom = desc
            value = inside if left <= x <= right and top <= y <= bottom else outside
        machine.return_from_external(value, 8)

    def move(self, x, old_y, target_y, *, step=14, bottom=60, mode=4, record=None):
        record = record or {}
        self.put(self.MANAGER+0x64, step, step)
        self.put(self.ACTOR+8, record.get('flags', 0x100))
        self.put(self.ACTOR+0x4c, x, old_y)
        self.put(self.ACTOR+0xcc, mode)
        self.put(self.ACTOR+0xdc, record.get('step_x', 8), record.get('step_y', 8))
        self.put(self.ACTOR+0x118, *record.get('rectangle', [-16, -52, 16, bottom]))
        result = self.machine.call(0x4cbb60, ecx=self.MANAGER,
                                   arguments=(self.ACTOR, record.get('target_x', x), target_y, record.get('options', 0)), timeout_seconds=2)
        assert result.completed, result
        return dict(x=self.machine.words(self.ACTOR+0x4c, 1)[0],
                    y=self.machine.words(self.ACTOR+0x50, 1)[0],
                    mode=self.machine.words(self.ACTOR+0xcc, 1)[0])
