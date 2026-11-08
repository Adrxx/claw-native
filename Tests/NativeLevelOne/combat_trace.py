"""Bounded original Level 1 combat/HUD route; no game substitutes or admission claim.

The plan's diagnostic setup is mirrored by CLAW_COMBAT_HUD in the app. Ammo is
seeded explicitly; remaining_ms shortens an already active timer to exercise its
last frames. This verifies expiry boundaries, not normal full power-up durations.
All game instructions come from the hash-pinned original through LevelOneTrace.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP
from Tests.NativeLevelOne.trace import LevelOneTrace, Blocked, ROOT
from Tests.NativeMenuBase.trace import MenuTrace
from Tests.NativeLevelTwo.trace import LevelTwoTrace


class CombatTrace(LevelOneTrace):
    def __init__(self, plan, checkpoint=None):
        super().__init__(10_000_000_000, None)
        self.input_plan = plan
        self.combat_checkpoint = checkpoint
        self.combat_frames = []

    def com_fixture(self, address):
        # Reuse the existing physical mirrored-blit provider, independently of
        # Level 2's game route. It returns here for exactly this DDBLT_DDFX path.
        if self.com_methods[address] == ('IDirectDrawSurface', 'Blt') and self.word(self.machine.reg_read(UC_X86_REG_ESP)+20)&0x800:
            return LevelTwoTrace.com_fixture(self, address)
        return super().com_fixture(address)

    def fixture(self, address):
        if address == 0x4a3810:
            return LevelTwoTrace.fixture(self, address)
        # Reuse the shared physical CStringList provider; LevelOneTrace's older
        # empty-only override cannot clear a previous power-up status message.
        if address in (0x4f5249, 0x4f5382, 0x4f53b7, 0x4f53eb, 0x4f5288):
            return MenuTrace.fixture(self, address)
        return super().fixture(address)

    def navigate(self, application):
        if self.level_one_loaded:
            return self.play(application)
        return super().navigate(application)

    def player_snapshot(self, application):
        p = super().player_snapshot(application)
        actor, state = int(p['actor'], 16), int(p['private'], 16)
        p.update(ammo=[self.word(state+i) for i in (0x70, 0x74, 0x78)],
                 lives=self.word(state+0x7c), lives_lost=self.word(state+0x80),
                 combat={name:self.word(base+off) for name, base, off in (
                     ('weapon', state, 0x30), ('attack', state, 4), ('attack_code', state, 0x3c),
                     ('owner_tag', state, 0xe8), ('image_id', actor, 0x16c), ('animation_frame', actor, 0x198), ('flags', actor, 0xd4),
                     ('power_kind', 0x534eac, 0), ('power_ms', 0x534ea8, 0))})
        p["combat"]["carrying"] = int(self.word(state+0x12c) != 0)
        target = getattr(self, 'combat_target', 0)
        if not target:
            for a,size in self.allocations.items():
                if size >= 0x180 and self.word(a+0x4c) == 1092 and self.word(a+0x6c) and self.word(self.word(a+0x6c)+0x10) == 0x462350:
                    self.combat_target = target = a
                    break
        # LevelOneTrace.allocate uses a monotonic cursor, so a live base is
        # the same allocation identity; freed emulated bytes stay mapped.
        live = target in self.allocations
        p['combat']['target_live'] = int(live)
        if live:
            info = self.word(target+0x6c)
            if not any(a <= info and info+0x20 <= a+size for a,size in self.allocations.items()):
                raise Blocked('Live officer has no allocated logic record')
            p['combat'].update(target_health=self.word(target+0x10c), target_x=self.word(target+0x4c),
                               target_y=self.word(target+0x50), target_state=self.word(self.word(target+0x6c)+0x1c))
        return p

    def play(self, application):
        self.clock_step = 0
        if self.combat_checkpoint and not self.resumed_checkpoint:
            if hasattr(self, 'checkpoint_command'): del self.checkpoint_command
            self.checkpoint_path = self.combat_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        start = self.milliseconds
        loading = [p for p in self.presentations if p['phase'] == 'command-807f']
        if not loading or self.presentations[-len(loading):] != loading:
            raise Blocked('New Game loading is not a contiguous presentation prefix')
        self.combat_frames = [dict(elapsed_ms=0, action='loaded', player=self.player_snapshot(application), screens=[],
                                   loading_screens=[[p['pixels_sha256'][:16], p['palette_sha256'][:16]] for p in loading])]
        placed = set()
        while self.milliseconds-start < max(a['end_ms'] for a in self.input_plan):
            elapsed = self.milliseconds-start
            action = next(a for a in self.input_plan if a['start_ms'] <= elapsed < a['end_ms'])
            # The app increments the clock before applying this frame's setup.
            self.pressed_keys = set(action['keys'])
            self.advance_time(self.milliseconds+17)
            before = len(self.presentations)
            if action['start_ms'] not in placed:
                placed.add(action['start_ms'])
                actor = self.word(0x537e88)
                state = self.word(self.word(actor+0x6c)+0x14)
                if 'set_x' in action:
                    self.put(actor+0x4c, action['set_x']); self.put(actor+0x50, action['set_y'])
                setup = action.get('diagnostic', {})
                if 'ammo' in setup:
                    for off in (0x70, 0x74, 0x78): self.put(state+off, setup['ammo'])
                if 'near_target' in setup:
                    target = getattr(self, 'combat_target', 0)
                    if target not in self.allocations: raise Blocked('Melee setup has no live officer target')
                    self.put(actor+0x4c, self.word(target+0x4c)-setup['near_target'])
                    self.put(actor+0x50, self.word(target+0x50)-9)
                for name, base, off in [('health', actor, 0x10c), ('score', actor, 0xf8), ('lives', state, 0x7c)]:
                    if name in setup: self.put(base+off, setup[name])
                if 'remaining_ms' in setup: self.put(0x534ea8, setup['remaining_ms'])
                if 'key' in setup:
                    game = self.word(application+0x2c)
                    self.run(self.word(self.word(game)+0x30), game,
                             (setup['key'], ((setup['key']-0x2f)<<16)|1), phase='play-combat-key')
                    self.drain_messages(application)
                if 'command' in setup:
                    self.run(self.word(self.word(application)+0x14), application,
                             (0x111, setup['command'], 0), phase='combat-setup-command')
                    self.drain_messages(application)
            self.run(0x428b60, application, phase='play-combat-'+action['action'])
            self.drain_messages(application)
            self.completed_play_ms = self.milliseconds-start
            screens = [[p['pixels_sha256'][:16], p['palette_sha256'][:16]] for p in self.presentations[before:]]
            self.combat_frames.append(dict(elapsed_ms=self.completed_play_ms, action=action['action'],
                                          player=self.player_snapshot(application), screens=screens))
            if len(self.combat_frames)%120 == 0:
                print(json.dumps(dict(event='combat', elapsed_ms=self.completed_play_ms, action=action['action'], player=self.combat_frames[-1]['player'])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    args = parser.parse_args()
    for path in (args.output, args.checkpoint):
        if path and not path.resolve().is_relative_to((ROOT/'work').resolve()): parser.error('Derived data stays in work/')
    plan = json.loads(args.plan.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    t = CombatTrace(plan, args.checkpoint)
    try:
        if args.checkpoint and args.checkpoint.exists(): t.resume_checkpoint(args.checkpoint)
        else: t.execute()
    except (Blocked, UcError) as e:
        t.stop = dict(reason=str(e), phase=t.phase, address=hex(t.machine.reg_read(UC_X86_REG_EIP)), transfer=t.last_transfer)
    finally:
        for stream in t.files.values(): stream.close()
    result = dict(status='blocked' if t.stop else 'pass', stop=t.stop, plan=plan, frames=t.combat_frames,
                  plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                  tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  parent_sha256=t.tracer_fingerprint, menu_sha256=t.parent_fingerprint,
                  mirror_provider_sha256=hashlib.sha256((ROOT/'Tests/NativeLevelTwo/trace.py').read_bytes()).hexdigest(),
                  original_sha256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263',
                  limitations=['Synthetic ammo and remaining timer setup; not full duration or physical input verification.'])
    args.output.write_text(json.dumps(result))
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','plan')}), flush=True)
    return 2 if t.stop else 0


if __name__ == '__main__': raise SystemExit(main())
