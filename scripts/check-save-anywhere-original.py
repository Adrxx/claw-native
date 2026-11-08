"""Original-only removed-placement contract for the save-anywhere mod.

Runs terminal enemy, treasure and crate callbacks, the real actor deletion pass,
and normal checkpoint respawn on the same original scene. Physical animation,
input suspension and UI refresh are declared fixtures. No imports are patched.
This is a focused app-boundary regression, not family admission.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tests'))
from clawparity.env import Env
from clawparity.fixtures import allocate, release, returns
from clawparity.program import claw


def main():
    program = claw()
    env = Env(program, heap_bytes=0x40000)
    # Physical allocator, animation, input suspension/resumption and HUD update.
    for address, convention, argc, effect in (
        (0x4f63ec, 'cdecl', 1, allocate()),
        (0x4f6428, 'cdecl', 1, release()),
        (0x4c82a0, 'thiscall', 1, returns(0)),
        (0x42d420, 'thiscall', 0, returns(0)),
        (0x42d440, 'thiscall', 0, returns(0)),
        (0x42abf0, 'thiscall', 0, returns(0)),
        (0x546df0, 'stdcall', 0, returns(1000)),
    ):
        env.fixture(address, convention, argc, effect)
    noop = env.stub('retained actor primary', 'cdecl', 1, returns(1))
    logic_delete = env.stub('logic physical disposal', 'thiscall', 1, returns(0))
    render = env.stub('physical render', 'thiscall', 2, returns(0))
    draw_actors = env.stub('physical actor drawing', 'thiscall', 1, returns(0))
    app = env.object(0x200, 'app', fill=0)
    state = env.object(0x800, 'game state', fill=0)
    scene = env.object(0x100, 'scene', fill=0)
    container = env.object(0x100, 'actor container', fill=0)
    world = env.object(0x200, 'world with no current render plane', fill=0)
    renderer = env.object(0x100, 'renderer', fill=0)
    renderer_vt = env.object(0x80, 'renderer vtable', fill=0)
    container_vt = env.object(0x80, 'actor container vtable', fill=0)
    logic_vt = env.object(0x80, 'logic vtable', fill=0)
    env.put(logic_vt+4, logic_delete)
    env.put(renderer, renderer_vt)
    env.put(renderer_vt+0x34, render)
    env.put(container, container_vt)
    env.put(container_vt+0x24, 0x4c8fc0, draw_actors)
    env.put(world+0x60, 0xffffffff)
    env.put(app+0x7c, 640, 480)
    env.put(state+4, app)
    env.put(state+0xc, scene)
    env.put(state+0x2c, 1)
    env.put(scene+4, app, container, renderer)
    env.put(scene+0x24, world)
    env.put(0x5430d0, 3)
    env.put(0x5430c4, 17)
    env.put(0x53720c, 17)
    env.put(0x537210, 2000)
    names = ('player', 'enemy', 'treasure', 'crate', 'untouched')
    actors, logics, nodes = {}, {}, []
    for index, name in enumerate(names):
        actor = env.object(0x200, name, fill=0)
        logic = env.object(0x200, name+' primary', fill=0)
        node = env.object(12, name+' list node', fill=0)
        actors[name], logics[name] = actor, logic
        nodes.append(node)
        env.put(actor, 0x5137f0, 101+index, 0, scene)
        env.put(actor+0x6c, logic)
        env.put(actor+0x68, node)
        env.put(logic, logic_vt, 101+index)
        env.put(logic+0x10, noop)
        env.put(node+8, actor)
    for index, node in enumerate(nodes):
        env.put(node, nodes[index+1] if index+1 < len(nodes) else 0,
                nodes[index-1] if index else 0)
    env.put(container+0x14, nodes[0], nodes[-1], len(nodes))
    env.put(0x537e88, actors['player'])
    enemy_state = env.object(0x500, 'enemy terminal state', fill=0)
    env.put(enemy_state+0x12c, actors['enemy'])
    env.put(enemy_state+0x304, 1)
    env.put(enemy_state+0x3d8, 1000, 100)
    env.put(logics['treasure']+0x1c, 9001)
    env.put(logics['treasure']+0x130, 1)
    env.put(logics['crate']+0x1c, 10)
    env.put(logics['crate']+0x64, 1)
    env._freeze()
    initial = env.run_original(0x43f450, enemy_state, (), trace=True, check_objects=True)
    assert initial.completed and not initial.errors, initial.errors
    machine = env.machine
    coverage = set(env.coverage)

    def call(address, receiver=0, args=()):
        machine.trace_blocks(True)
        result = machine.call(address, receiver, 0, args)
        coverage.update(machine.blocks)
        machine.blocks.clear()
        assert result.completed, hex(address)
        assert not env.errors, env.errors
        return result.eax

    def word(address):
        return machine.words(address, 1)[0]

    call(0x46fd10, 0, (actors['treasure'],))
    call(0x471530, 0, (actors['crate'],))
    removed = ('enemy', 'treasure', 'crate')
    assert all(word(actors[name]+8) & 0x10000 for name in removed)
    assert not word(actors['untouched']+8) & 0x10000
    call(0x4c8fc0, container, (0,))
    assert all(actors[name] in env.freed for name in removed), env.freed

    def present():
        found, node = set(), word(container+0x14)
        while node:
            assert len(found) < 20
            found.add(word(node+8))
            node = word(node)
        return found

    before = present()
    assert before == {actors['player'], actors['untouched']}, before
    assert call(0x46be40, state) == 1
    assert present() == before, (before, present())
    assert all(actors[name] in env.freed for name in removed)
    assert all(not start <= 0x4d1620 < start+size for start, size in coverage)
    # The restore host also detaches dormant placements through the source grid
    # owner. Exercise a middle member and retain both neighbors.
    layer = env.object(0x44, 'dormant layer', fill=0)
    cell = env.object(8, 'dormant cell', fill=0)
    members = [env.object(0x1c, 'dormant member', fill=0) for _ in range(3)]
    env.put(layer+8, 3)
    env.put(cell, members[0], members[2])
    for index, member in enumerate(members):
        env.put(member, members[index+1] if index < 2 else 0,
                members[index-1] if index else 0, 0, cell)
    call(0x4f4680, layer, (members[1],))
    assert word(layer+8) == 2 and word(members[1]+0xc) == 0
    assert word(members[0]) == members[2] and word(members[2]+4) == members[0]
    assert word(cell) == members[0] and word(cell+4) == members[2]
    report = {
        'check': 'save-anywhere-original-removal', 'status': 'pass',
        'program_sha256': program.sha256,
        'removed': list(removed), 'preserved': ['player', 'untouched'],
        'original_callbacks': ['0x43f450', '0x46fd10', '0x471530'],
        'original_deletion_pass': '0x4c8fc0', 'original_respawn': '0x46be40',
        'original_dormant_unlink': '0x4f4680',
        'rule': 'Terminal callbacks request deletion; the original scene removes actors and normal checkpoint respawn retains that same scene without reloading WWD placements.',
        'scope': 'Terminal callbacks and active-list deletion/respawn; render plane absent, animation/input/UI are explicit fixtures.',
        'original_instruction_blocks': len(coverage),
    }
    output = ROOT/'work/save-anywhere-original/result.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
