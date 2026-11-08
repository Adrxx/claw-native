"""Original-backed class and table contracts shared by planning and validation."""
import json
import re
import struct
from collections import defaultdict
from Tests.NativeLevels import ROOT
from Tests.clawparity.program import claw
from tools.claw.progress_page import class_addresses


CREATED = {
    7: {'CrabBomb', 'HermitCrab'},
    8: {'GabrielBomb', 'GroundCannon', 'CannonBall', 'RedTailPirate', 'BossHealthMeter'},
    9: {'Bullet', 'FireBullet', 'Splash'},
    10: {'BossHealthMeter', 'BossStagerAttack', 'EndLevelGem'},
    11: {'SirenBullet', 'TridentBullet', 'Splash'},
    13: {'RedTailKnife', 'RedTailBullet', 'WindDebris', 'BossHealthMeter',
         'BossStagerAttack', 'EndLevelGem'},
    14: {'OmarBullet', 'OmarShield', 'LavaHandProjectile', 'BossHealthMeter',
         'BossStagerAttack', 'EndLevelGem'},
    12: {'SirenBullet', 'TridentBullet', 'Splash', 'BossHealthMeter',
         'BossStagerAttack', 'EndLevelGem'},
}
# Reviewed original constructor tables: enemy and boss projectiles, boss
# bodies and unique mechanism objects. Entries are checked against CLAW.EXE.
TABLES = {
    13: {0x50b95c: 12, 0x50b994: 12, 0x50bb2c: 43, 0x50f264: 45,
         0x50f444: 9, 0x50f46c: 9, 0x50feec: 10},
    14: {0x50b8b4: 12, 0x50bb2c: 43, 0x50e4b4: 9, 0x50e4dc: 9,
         0x50e504: 16, 0x50e6d4: 9, 0x50eafc: 45, 0x50ebb4: 9,
         0x50f9b4: 43},
    11: {0x50b8ec: 12, 0x50b924: 12},
    12: {0x50b8ec: 12, 0x50b924: 12, 0x50b0b4: 45, 0x50b21c: 9,
         0x50b244: 9, 0x50b26c: 10, 0x50db2c: 10, 0x50f8a4: 10,
         0x50f8e4: 42},
}


def class_bindings():
    source = (ROOT/'Sources/LogicStateRegistry.cpp').read_text()
    body = source.split('const Binding bootstrap[] = {', 1)[1].split('};', 1)[0]
    states, current = defaultdict(list), None
    for kind, _token, _literal, function, _flags, name in re.findall(
            r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), (0x[0-9a-f]+), (0x[0-9a-f]+), (0x[0-9a-f]+), "([^"]*)"\}', body):
        if kind == '0x0':
            current = name
        else:
            states[current].append(int(function, 16))
    return class_addresses(), states


def validate_later_closure(closure, *, trace=None, retained_plan=None):
    """Static discovery is allowed; complete discovery also needs its real plan."""
    level = closure['level']
    assert level in CREATED
    inventory = json.loads((ROOT/'work/parity/inventory.json').read_text())
    item = next(i for i in inventory['items'] if i['id'] == f'level:{level}')
    placed = {c['name']: c for c in closure['placed_classes']}
    assert len(placed) == len(closure['placed_classes']), 'Duplicate placed class'
    assert {n:c['placed'] for n,c in placed.items() if n != 'CaptainClaw'} == item['classes'], 'Placed census differs'
    assert sum(item['classes'].values()) == item['objects']
    names, states = class_bindings()
    functions = {r['address'] for r in closure['functions']}
    roots = {r['address'] for r in closure['functions'] if r['root']}
    for name, row in placed.items():
        if name not in names:
            from Tests.NativeLevels.object_loading import validate_unregistered
            validate_unregistered(level, row, closure)
            continue
        assert row['callback'] == hex(names[name]), f'Fabricated class mapping: {name}'
        assert row['states'] == [hex(a) for a in states[name]], f'Changed states: {name}'
        assert row['callback'] in roots, f'Missing placed surface: {name}'
        assert set(row['states']) <= roots, f'Missing placed states: {name}'
    assert CREATED[level] <= set(closure['created_classes']), 'Missing created-object closure'
    for name in CREATED[level]:
        assert hex(names[name]) in functions, f'Missing created callback: {name}'
        assert {hex(a) for a in states[name]} <= functions, f'Missing created states: {name}'
    if level in TABLES:
        program = claw()
        tables = {t['address']:t for t in closure['tables']}
        for address, count in TABLES[level].items():
            table = tables.get(hex(address))
            assert table is not None, f'Missing created/mechanism vtable: {address:#x}'
            section = next(s for s in program.sections if s.address <= address < s.address+len(s.data))
            expected = [hex(a) for a in struct.unpack_from(f'<{count}I', section.data, address-section.address)]
            assert table['entries'] == expected, f'Changed original vtable: {address:#x}'
            assert set(expected) <= functions, f'Missing vtable functions: {address:#x}'
    if trace is not None:
        assert retained_plan is not None and trace['plan'] == retained_plan, 'Retain the actual input schedule'
    return item
