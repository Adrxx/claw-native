"""Original Level 2 loading and sixty seconds of physical input; discovery only."""
import argparse
from Tests.NativeLevels.storage import exists, fingerprint, load_checkpoint, restore_memory, save_checkpoint, write_trace
import hashlib
import json
import math
import struct
from Tests.NativeEndOfLevel import trace as end_trace
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_FPSW
from Tests.NativeMenuBase.trace import ROOT, Blocked
from Tests.NativeEndOfLevel.trace import EndOfLevelTrace, SINGLE_PLAYER_VTABLE

# Alternate movement and released attack keys; repeated jumps explore the route
# without modifying position, health, inventory, or any game decision.
PLAN = [dict(start_ms=0, end_ms=1000, action='stand', keys=[]),
        dict(start_ms=1000, end_ms=1500, action='walk-right', keys=[0x27]),
        dict(start_ms=1500, end_ms=3500, action='jump-up-to-ladder', keys=[0x20,0x26]),
        dict(start_ms=3500, end_ms=8000, action='climb-up', keys=[0x26])]
for start in range(8000, 60000, 5000):
    for lo, hi, action, keys in (
        (0, 1500, 'walk-right', [0x27]),
        (1500, 2000, 'attack', [0x11]),
        (2000, 3500, 'jump-right', [0x27, 0x20]),
        (3500, 4000, 'attack', [0x11]),
        (4000, 5000, 'walk-right', [0x27]),
    ):
        if start+lo < 60000:
            PLAN.append(dict(start_ms=start+lo, end_ms=min(start+hi,60000), action=action, keys=keys))


class LevelTwoTrace(EndOfLevelTrace):
    def math_fixture(self, address):
        # Opt in only for the four square-distance calls made by the paper
        # fader. Other callers keep the inherited scene/audio math profile.
        if address != 0x4f1b30:
            return super().math_fixture(address)
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        caller = self.word(sp)
        bounds = {0x4ee6cf: 640, 0x4ee6eb: 480,
                  0x4ee718: 480, 0x4ee738: 640}
        if caller not in bounds:
            return super().math_fixture(address)
        before = self.x87_state()
        exponent, base = self.x87_value(0), self.x87_value(1)
        if (not self.startup_paper or before['control'] != 0x027f
                or exponent != 2 or base != math.trunc(base)
                or abs(base) > bounds[caller]):
            raise Blocked('Power operands outside the paper-fader geometry profile')
        # The elected emulator's CRT power path rounds log2 and its scaled
        # exponent separately. Squaring directly changes the returned bits
        # (350 produces 122500.00000000003). Keep that platform math profile.
        if base == 0:
            result = 0.0
        else:
            logarithm = exponent * (math.log(abs(base)) / math.log(2.0))
            integral = round(logarithm)
            result = math.ldexp(math.exp2(logarithm-integral), integral)
        self.x87_result(2, result)
        if base <= 0:
            # The original's zero/negative-base classification sets C3 and
            # clears C0/C2; C1 and sticky exception flags survive.
            status = self.machine.reg_read(UC_X86_REG_FPSW)
            self.machine.reg_write(UC_X86_REG_FPSW, (status & ~0x0500) | 0x4000)
        self.math_events.append(dict(address=hex(address), caller=hex(caller),
            profile='paper-fader', operands=[exponent, base], result=result,
            before=before, after=self.x87_state()))
        self.returned(self.machine.reg_read(UC_X86_REG_EAX))

    def fixture(self, address):
        api = self.imports.get(address, (None, ''))[1].split('!')[-1]
        if (self.startup_paper and self.phase == 'command-803a'
                and self.clock_step == 0 and api in ('timeGetTime', 'GetTickCount')):
            # Respawn's paper fade polls the physical timer synchronously,
            # just like completion/results. Gameplay frames keep their fixed
            # 17 ms clock; only queries inside this window command advance.
            self.clock_step = 1
            try:
                return super().fixture(address)
            finally:
                self.clock_step = 0
        if address != 0x4a3810:
            return super().fixture(address)
        # CRT multibyte string comparison. The elected original process uses
        # code page zero (single-byte strings); reject other locale profiles.
        if self.word(0x540e00) != 0:
            raise Blocked('Multibyte comparison requires the elected SBCS code page')
        sp = self.machine.reg_read(end_trace.UC_X86_REG_ESP)
        left, right = self.bytestring(self.word(sp+4)), self.bytestring(self.word(sp+8))
        self.platform_call(address,'CRT multibyte string comparison, SBCS')
        result = (left>right)-(left<right)
        self.physical_events.append(dict(service='CRT multibyte string comparison',phase=self.phase,
            code_page=0,left_sha256=hashlib.sha256(left).hexdigest(),right_sha256=hashlib.sha256(right).hexdigest(),result=result))
        self.returned(result)

    def com_fixture(self, address):
        kind, method = self.com_methods[address]
        sp = self.machine.reg_read(end_trace.UC_X86_REG_ESP)
        arg = lambda i: self.word(sp+4*i)
        if (kind,method) != ('IDirectDrawSurface','Blt') or not arg(5)&0x800:
            return super().com_fixture(address)
        # DDBLT_DDFX selects dwDDFX; mirror bits are left/right=2 and
        # up/down=4. Other DDBLTFX members are inactive for these flags.
        # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/ns-ddraw-ddbltfx
        # https://learn.microsoft.com/en-us/windows/win32/api/ddraw/nf-ddraw-idirectdrawsurface7-blt
        obj, source = self.com_objects.get(arg(1)), self.com_objects.get(arg(3))
        fx, flags = arg(6), arg(5)
        if (not obj or not source or not fx or self.word(fx)!=100
                or flags & ~0x1008800 or self.word(fx+4)&~6
                or any(s['kind']!=kind or not s['references'] or s['lost'] or s['locked'] for s in (obj,source))):
            raise Blocked(f'Invalid mirrored physical Blt descriptor: flags={flags:#x}, fx={self.word(fx+4) if fx else None}')
        def rect(pointer,surface):
            return struct.unpack('<4i',self.machine.mem_read(pointer,16)) if pointer else (0,0,surface['width'],surface['height'])
        dst, src = rect(arg(2),obj), rect(arg(4),source)
        if (any(not (0<=r[0]<r[2]<=surface['width'] and 0<=r[1]<r[3]<=surface['height'])
                for r,surface in ((dst,obj),(src,source)))
                or (dst[2]-dst[0],dst[3]-dst[1]) != (src[2]-src[0],src[3]-src[1])):
            raise Blocked(f'Mirrored Blt requires equal in-bounds rectangles: {src} -> {dst}')
        key = source.get('color_key') if flags&0x8000 else None
        if flags&0x8000 and key is None:
            raise Blocked('Mirrored Blt source color key was not set')
        effects = self.word(fx+4)
        rows = [bytes(self.machine.mem_read(source['pixels']+y*source['pitch']+src[0],src[2]-src[0])) for y in range(src[1],src[3])]
        if effects&4: rows.reverse()
        self.platform_call(address,'IDirectDrawSurface::Blt')
        for y,pixels in enumerate(rows):
            if effects&2: pixels=pixels[::-1]
            target=obj['pixels']+(dst[1]+y)*obj['pitch']+dst[0]
            if key:
                old=bytes(self.machine.mem_read(target,len(pixels)))
                pixels=bytes(a if key[0]<=b<=key[1] else b for a,b in zip(old,pixels))
            self.machine.mem_write(target,pixels)
        self.physical_events.append(dict(service='IDirectDrawSurface::Blt',object=hex(arg(1)),source=hex(arg(3)),
            phase=self.phase,milliseconds=self.milliseconds,source_rectangle=src,destination_rectangle=dst,flags=flags,mirror=effects))
        self.returned(0,24)

    def level_two(self, application):
        checkpoint = getattr(self, 'level_two_checkpoint', None)
        if checkpoint and not self.resumed_checkpoint:
            self.checkpoint_path = checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        self.clock_step = 0
        self.level_two_loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.level_two_frames = [dict(elapsed_ms=0, action='loaded', player=first)]
        while self.milliseconds-start < self.level_two_ms:
            elapsed = self.milliseconds-start
            action = next(a for a in PLAN if a['start_ms'] <= elapsed < a['end_ms'])
            self.frame(application, 'level-two-'+action['action'], action['keys'])
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != 2:
                raise Blocked('Original Level 2 play left the single-player Level 2 state')
            self.level_two_played_ms = self.milliseconds-start
            self.level_two_frames.append(dict(elapsed_ms=self.level_two_played_ms, action=action['action'],
                player=self.player_snapshot(application)))
            if len(self.level_two_frames) % 120 == 0:
                print(json.dumps(dict(event='level-two', **self.level_two_frames[-1])), flush=True)
        self.level_two_game_ms = (self.level_two_frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, 'level-two-played')
        if not any(e['increment'] > 0 and e['phase'].startswith('level-two-') for e in self.pickup_events):
            raise Blocked('Sixty seconds completed without observed original Level 2 treasure pickup')

    def resume_two_checkpoint(self, path):
        # Local discovery cache: original CPU, memory, files and prefix census.
        payload = load_checkpoint(path)
        self.validate_checkpoint_profile(payload['state'])
        if payload.get('storage_sha256') != self.storage_fingerprint:
            raise Blocked('Stale checkpoint storage implementation')
        if (payload['version'] != 3 or payload.get('level_sha256') != self.level_tracer_fingerprint
                or payload['parent_sha256'] != hashlib.sha256((ROOT/'Tests/NativeMenuBase/trace.py').read_bytes()).hexdigest()):
            raise Blocked('Stale Level 2 checkpoint')
        if payload['state']['level_two_played_ms'] != 0 or payload['state']['state_transitions'][-1].get('level') != 2:
            raise Blocked('Checkpoint was not taken at Level 2 start')
        with end_trace.REZ_PATH.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != end_trace.REZ_SHA256:
                raise Blocked('Original archive hash mismatch')
        keep = {k: getattr(self, k) for k in ('instruction_limit', 'deny_platform', 'tracer_fingerprint',
            'parent_fingerprint', 'end_tracer_fingerprint', 'level_tracer_fingerprint', 'standing_ms',
            'results_limit_ms', 'level_two_ms')}
        self.__dict__.update(payload['state'])
        self.__dict__.update(keep)
        self.resumed_checkpoint = True
        restore_memory(path, self.machine)
        registers = (end_trace.UC_X86_REG_EAX, end_trace.UC_X86_REG_EBX, end_trace.UC_X86_REG_ECX, end_trace.UC_X86_REG_EDX,
            end_trace.UC_X86_REG_ESI, end_trace.UC_X86_REG_EDI, end_trace.UC_X86_REG_EBP, end_trace.UC_X86_REG_ESP,
            end_trace.UC_X86_REG_EIP, end_trace.UC_X86_REG_EFLAGS, end_trace.UC_X86_REG_FPCW, end_trace.UC_X86_REG_FPSW, end_trace.UC_X86_REG_FPTAG)
        for r, v in zip(registers, payload['cpu']):
            self.machine.reg_write(r, v)
        for i, v in enumerate(payload['cpu'][len(registers):]):
            self.machine.reg_write(end_trace.UC_X86_REG_FP0+i, v)
        for handle, (name, position) in payload['files'].items():
            if Path(name).resolve() != end_trace.REZ_PATH.resolve():
                raise Blocked('Unexpected checkpoint file')
            self.files[handle] = open(name, 'rb')
            self.files[handle].seek(position)
        self.prefix_checkpoint_sha256 = fingerprint(path)
        self.parent_checkpoint = dict(path=str(path), sha256=self.prefix_checkpoint_sha256,
            startup_profile=self.startup_profile)
        self.level_two(self.application)

    def report(self):
        result = super().report()
        pickup = any(e['increment'] > 0 and e['phase'].startswith('level-two-') for e in self.pickup_events)
        result.update(level_two_tracer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            scope='Original Level 2 loading and 60000 ms physical input census; no native parity or admission claim',
            level_two_plan=PLAN, level_two_treasure_pickup_observed=pickup,
            prefix_checkpoint_sha256=getattr(self,'prefix_checkpoint_sha256',None))
        result['status'] = 'pass' if self.stop is None and self.level_two_played_ms >= 60000 and pickup else 'blocked'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/level-two-map/trace.json')
    parser.add_argument('--checkpoint', type=Path, help='Optional Level 2 start cache under work/')
    parser.add_argument('--resume-level-two', action='store_true', help='Reuse the local discovery checkpoint; final evidence can run fresh')
    parser.add_argument('--instruction-limit', type=int, default=10_000_000_000)
    parser.add_argument('--paper-startup', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived output must stay under ignored work/')
    trace = LevelTwoTrace(args.instruction_limit, None, level_two_ms=60000, startup_paper=args.paper_startup)
    checkpoint = args.checkpoint or (ROOT/'work/level-two-map/level-two-start.pkl' if args.resume_level_two else None)
    if checkpoint and not checkpoint.resolve().is_relative_to((ROOT/'work').resolve()):
        parser.error('Checkpoint must stay under work/')
    trace.level_two_checkpoint = checkpoint
    try:
        if checkpoint and exists(checkpoint):
            trace.resume_two_checkpoint(checkpoint)
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    result = trace.report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(output, result)
    print(json.dumps(dict(status=result['status'], counts=result['counts'], stop=result['stop'],
        played_ms=result['level_two_played_ms'], treasure=result['level_two_treasure_pickup_observed'], output=str(output))), flush=True)
    return 0 if result['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
