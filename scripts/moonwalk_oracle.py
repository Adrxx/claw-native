"""Focused original-v1.0 facing/locomotion oracle for the checkpoint app check.

This executes the pinned executable's turn and walk-entry routines. Animation selection/stepping are explicit inert fixtures; an empty-air
collision fixture publishes position and retains airborne mode. No fixture
sets facing, horizontal velocity, logic state, or collision rectangles. This is an app regression oracle, not a family
admission or a full gameplay/input-dispatch comparison.
"""
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP

# Explicit app-oracle fixtures. All turn, rectangle mirroring, walk-entry,
# fall direction selection and physics instructions execute from the original.
FIXTURES = {
    0x4C79E0: {"name": "select-animation", "convention": "thiscall", "argc": 2},
    0x4C82A0: {"name": "step-animation", "convention": "thiscall", "argc": 1},
    0x4CBB60: {"name": "empty-air-collision", "convention": "thiscall", "argc": 4},
}
ACTOR, LOGIC, PRIVATE, INPUT = (0x1000000 + i * 0x1000 for i in range(4))
TURN = {0: 0x418120, 2: 0x418080}
WALK = {"left": 0x417DD0, "right": 0x417F20}


def signed(word):
    return word - 0x100000000 if word & 0x80000000 else word


class FacingOracle:
    def __init__(self, initial=None):
        self.program = claw()
        self.machine = Machine(self.program, ACTOR, 0x10000)
        self.events = []
        self.machine.on_external = self._fixture
        for address in FIXTURES:
            self.machine.intercept(address)
        self.put(0x537204, INPUT)
        self.put(ACTOR + 0x6c, LOGIC)
        self.put(LOGIC + 0x14, PRIVATE)
        self.put(LOGIC + 0x1c, 24)
        self.put(ACTOR + 0xcc, 1)
        self.put(PRIVATE, 1)
        self.put(PRIVATE + 0x114, 1500)
        rectangles = [[-16, -52, 16, 60], [-22, -45, 15, 52], [-2147483648, 0, 0, 0]]
        if initial:
            self.put(ACTOR + 0x40, initial['render_flags'])
            self.put(PRIVATE, initial.get('player_state', initial.get('private_facing')))
            rectangles = initial.get('facing_rectangles', rectangles)
        for offset, rectangle in zip((0x118, 0x128, 0x138), rectangles):
            self.put(ACTOR + offset, *rectangle)

    def put(self, address, *words):
        self.machine.write(address, struct.pack('<' + 'I' * len(words), *(w & 0xffffffff for w in words)))

    def get(self, address):
        return self.machine.words(address, 1)[0]

    def _fixture(self, machine, address):
        if address not in FIXTURES:
            raise AssertionError(f'Undeclared original dependency {address:#x}')
        spec = FIXTURES[address]
        sp = machine.register(UC_X86_REG_ESP)
        arguments = list(machine.words(sp + 4, spec['argc']))
        if address == 0x4CBB60:
            actor, x, y, options = arguments
            self.put(actor + 0x4c, x, y)
            self.put(actor + 0xcc, 4)
        self.events.append({'function': hex(address), 'name': spec['name'],
                            'receiver': machine.register(UC_X86_REG_ECX),
                            'arguments': arguments})
        machine.return_from_external(0, spec['argc'] * 4)

    def call(self, entry):
        result = self.machine.call(entry, arguments=(ACTOR, LOGIC, PRIVATE), timeout_seconds=2)
        if not result.completed:
            raise AssertionError(f'Original {entry:#x} did not return: {result}')
        return self.snapshot()

    def snapshot(self):
        return {'render_flags': self.get(ACTOR + 0x40),
                'private_facing': self.get(PRIVATE),
                'vx': signed(self.get(ACTOR + 0x148)),
                'logic_state': self.get(LOGIC + 0x1c),
                'facing_rectangles': [[signed(v) for v in self.machine.words(ACTOR + offset, 4)]
                                      for offset in (0x118, 0x128, 0x138)]}

    def restore(self, saved_facing, sprite_only=False):
        if saved_facing not in TURN:
            raise ValueError('saved_facing must be sprite mirror bit 0 or 2')
        if sprite_only:
            self.put(ACTOR + 0x40, (self.get(ACTOR + 0x40) & ~2) | saved_facing)
            return self.snapshot()
        return self.call(TURN[saved_facing])

    def walk(self, direction):
        return self.call(WALK[direction])

    def airborne(self, held_mask):
        # Execute a complete original fall update over declared empty air.
        # This directly exercises the original Left/Right held-bit priority.
        scene, world = ACTOR + 0x4000, ACTOR + 0x5000
        self.put(ACTOR + 0xc, scene)
        self.put(scene + 0x24, world)
        self.put(ACTOR + 0xcc, 4)
        self.put(LOGIC + 0x1c, 25)
        self.put(INPUT + 8, held_mask)
        self.put(0x53720c, 17)
        self.put(0x5430c4, 17)
        result = self.machine.call(0x415AB0, timeout_seconds=2)
        if not result.completed:
            raise AssertionError('Original physics constructor did not return')
        return self.call(0x418B40)


def original_restore(saved_facing, *, sprite_only=False, initial=None):
    oracle = FacingOracle(initial)
    return oracle.restore(saved_facing, sprite_only)


def original_walk(saved_facing, direction, *, sprite_only=False, initial=None):
    oracle = FacingOracle(initial)
    oracle.restore(saved_facing, sprite_only)
    return oracle.walk(direction)


def original_airborne(saved_facing, held_mask, *, sprite_only=False, initial=None):
    oracle = FacingOracle(initial)
    oracle.restore(saved_facing, sprite_only)
    return oracle.airborne(held_mask)


def original_evidence():
    rows = []
    for saved_facing in (0, 2):
        for direction in ('left', 'right'):
            oracle = FacingOracle()
            restored = oracle.restore(saved_facing)
            walked = oracle.walk(direction)
            rows.append({'saved_facing': saved_facing, 'direction': direction,
                         'restored': restored, 'walked': walked, 'fixtures': oracle.events})
            assert walked['private_facing'] == (direction == 'right')
            assert bool(walked['render_flags'] & 2) == (direction == 'left')
            assert walked['vx'] == (-225 if direction == 'left' else 225)
    broken = original_walk(2, 'right', sprite_only=True)
    fixed = original_walk(2, 'right')
    assert broken['render_flags'] & 2 and broken['private_facing'] == 1 and broken['vx'] == 225
    assert fixed['render_flags'] & 2 == 0 and fixed['private_facing'] == 1 and fixed['vx'] == 225
    airborne = []
    for saved_facing in (0, 2):
        for held in (0, 0x1000000, 0x2000000, 0x3000000):
            oracle = FacingOracle()
            oracle.restore(saved_facing)
            state = oracle.airborne(held)
            airborne.append({'saved_facing': saved_facing, 'held_mask': held,
                             'state': state, 'fixtures': oracle.events})
            expected_vx = 225 if held & 0x2000000 else -225 if held & 0x1000000 else 0
            assert state['vx'] == expected_vx
            if expected_vx:
                assert state['private_facing'] == (expected_vx > 0)
                assert bool(state['render_flags'] & 2) == (expected_vx < 0)
    return {'program_sha256': claw().sha256, 'scope': __doc__, 'cases': rows,
            'airborne_cases': airborne,
            'sprite_only_restore_control': broken, 'original_turn_restore_control': fixed}


if __name__ == '__main__':
    import json
    print(json.dumps({'check': 'moonwalk-original-facing', 'status': 'pass', **original_evidence()}, indent=2))
