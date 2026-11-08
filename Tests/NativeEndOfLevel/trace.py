"""Read-only original discovery from Level 1 through level completion,
the results screen, Level 2 loading and the first seconds of Level 2 play.

Run with work/test-env/bin/python -m Tests.NativeEndOfLevel.trace.
Derived output stays in ignored work/. Exit 2 retains an exact incomplete trace.

Route: the unchanged New Game path of Tests/NativeLevelOne/trace.py loads
Level 1. After a short standing period, the original cheat manager receives
the typed code MPSCULLY through the single-player state's own key-down
method (vtable slot 0x30, 0x46bb30 -> 0x422e00). The original then posts its
own level-complete command 0x800e, the same command player code posts after
the end-of-level gem sequence (0x41f04f). No game memory is written by the
harness; only physical keys, time and window-message delivery are supplied.
After results the original continues into Level 2 on its own (owner decision
2026-10-21: follow it there instead of leaving through the in-game menu); the
trace then plays a few seconds of Level 2 with scripted physical keys.
"""
import argparse
from Tests.NativeLevels.storage import EventLog, exists, fingerprint, load_checkpoint, restore_memory, save_checkpoint, write_trace
import hashlib
import json
import struct
import time
from pathlib import Path

from unicorn import UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW,
    UC_X86_REG_FPSW, UC_X86_REG_FPTAG, UC_X86_REG_FP0)
from Tests.NativeMenuBase.trace import Blocked, ROOT, REZ_PATH, REZ_SHA256
from Tests.NativeLevelOne.trace import LevelOneTrace

MENU_VTABLE = 0x50c1e4
SINGLE_PLAYER_VTABLE = 0x50c264
# Scripted physical keys for the first seconds of Level 2 (bound keys from
# the original controller: right 0x27, jump 0x20).
LEVEL_TWO_PLAN = (
    dict(start_ms=0, end_ms=1000, action='stand', keys=[]),
    dict(start_ms=1000, end_ms=2500, action='walk-right', keys=[0x27]),
    dict(start_ms=2500, end_ms=2900, action='jump-right', keys=[0x27, 0x20]),
    dict(start_ms=2900, end_ms=4000, action='walk-right', keys=[0x27]),
    dict(start_ms=4000, end_ms=5000, action='stand', keys=[]),
)
# Virtual keys and set-1 scan codes for the typed letters.
LETTERS = {'M': (0x4d, 0x32), 'P': (0x50, 0x19), 'S': (0x53, 0x1f), 'C': (0x43, 0x2e),
           'U': (0x55, 0x16), 'L': (0x4c, 0x26), 'Y': (0x59, 0x15)}
CHEAT = 'MPSCULLY'
WALL_CLOCK = 1792497600  # 2026-10-20 12:00:00 UTC, elected physical clock


class EndOfLevelTrace(LevelOneTrace):
    def __init__(self, *args, standing_ms=1000, results_limit_ms=120000, level_two_ms=5000, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_fingerprint = fingerprint(Path(__file__).parents[1]/'NativeLevels/storage.py')
        self.end_tracer_fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.level_tracer_fingerprint = hashlib.sha256((ROOT/'Tests/NativeLevelOne/trace.py').read_bytes()).hexdigest()
        self.physical_events = EventLog(self.physical_events)
        self.math_events = EventLog(self.math_events)
        self.standing_ms = standing_ms
        self.results_limit_ms = results_limit_ms
        self.level_checkpoint = None
        self.level_start_checkpoint = False
        self.cheat_keys = []
        self.state_transitions = []
        self.sent_messages = []
        self.key_deliveries = []
        self.level_complete_posted = False
        self.level_two_ms = level_two_ms
        self.level_two_loaded = False
        self.level_two_frames = []
        self.level_two_played_ms = 0
        self.level_two_game_ms = 0
        self.startup_profile = dict(paper=self.startup_paper,
            query_ms=1 if self.startup_paper else 0)
        self.startup_queries = dict(count=0, increments={}, first=[])
        self.startup_objects = None
        self.parent_checkpoint = None

    def execute_frames(self, application):
        # Capture actual objects and timer deliveries before the first menu frame.
        self.startup_objects = {hex(o): hex(self.word(application+o)) for o in (0x44, 0x58)}
        super().execute_frames(application)

    def validate_checkpoint_profile(self, state):
        if bool(state.get('startup_paper', False)) != self.startup_paper:
            raise Blocked('Checkpoint startup profile mismatch')
        if self.startup_paper:
            queries = state.get('startup_queries', {})
            objects = state.get('startup_objects') or {}
            bindings = {e.get('binding') for e in state.get('startup_evidence', [])}
            if (state.get('startup_profile') != self.startup_profile
                    or not queries.get('count') or queries.get('increments') != {1: queries['count']}
                    or any(objects.get(hex(o), '0x0') == '0x0' for o in (0x44, 0x58))
                    or not {'application+0x44', 'application+0x58'} <= bindings):
                raise Blocked('Checkpoint lacks original paper startup evidence')

    # Window-message delivery. SendMessageA is synchronous: the window's
    # command virtual (application vtable +0x14, the same target queued
    # PostMessageA deliveries use) runs in place of the call and returns to
    # the original caller with SendMessageA's four-argument stack cleanup.
    def fixture(self, address):
        api = self.imports.get(address, (None, ''))[1].split('!')[-1]
        if api in ('timeGetTime', 'GetTickCount') and self.startup_objects is None:
            before = self.milliseconds
            result = super().fixture(address)
            increment = self.milliseconds-before
            evidence = self.startup_queries
            evidence['count'] += 1
            evidence['increments'][increment] = evidence['increments'].get(increment, 0)+1
            if len(evidence['first']) < 8:
                evidence['first'].append(dict(service=api, phase=self.phase,
                    before_ms=before, after_ms=self.milliseconds, increment_ms=increment))
            return result
        if api == 'SendMessageA':
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            hwnd, message, wparam, lparam = (self.word(sp+4*i) for i in range(1, 5))
            if hwnd != 1 or message != 0x111:
                return super().fixture(address)
            self.platform_call(address, self.imports[address][1])
            application = self.application
            target = self.word(self.word(application)+0x14)
            self.sent_messages.append(dict(phase=self.phase, milliseconds=self.milliseconds,
                message=message, wparam=wparam, lparam=lparam, target=hex(target),
                caller=hex(self.word(sp))))
            self.physical_events.append(dict(service=api, window=hwnd, message=message,
                wparam=wparam, lparam=lparam, delivery='synchronous window command virtual'))
            self.put(sp+4, self.word(sp))
            self.machine.reg_write(UC_X86_REG_ESP, sp+4)
            self.machine.reg_write(UC_X86_REG_ECX, application)
            self.machine.reg_write(UC_X86_REG_EIP, target)
            self.pending = (address, 'platform_callback')
            return
        if address == 0x4a4450 and self.word(self.machine.reg_read(UC_X86_REG_ESP)+12) > 4096:
            # Level teardown destroys the same large spatial-grid vector the
            # Level 1 tracer constructs; elements are destroyed last to first.
            self.platform_call(address, 'CRT vector destructor iterator')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            base, stride, count, destructor = (self.word(sp+4*i) for i in range(1, 5))
            if (stride, destructor) != (8, 0x4c96b0) or count > 65536 or not any(
                    start <= base and base+stride*count <= start+length for start, length in self.allocations.items()):
                raise Blocked('Unsupported or unallocated large grid vector destruction')
            event = dict(service='CRT vector destructor iterator', base=hex(base), stride=stride, count=count,
                constructor=hex(destructor), destructor=hex(destructor), completed=0)
            self.physical_events.append(event)
            frame = dict(context=self.machine.context_save(), fs=self.word(0), sp=sp, cpu=self.cpu_state(),
                base=base+(count-1)*stride, stride=-stride, count=count, constructor=destructor, index=0,
                event=event, pop=16, service=address)
            self.array_callbacks.append(frame)
            self.start_array_element(frame)
            return
        if address == 0x4f565f:
            # MFC CPtrList destructor: RemoveAll on the native list, then the
            # CObject vtable. Same validation as the base RemoveAll fixture.
            self.platform_call(address, 'MFC CPtrList destructor')
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            if not receiver or self.word(receiver) != 0x5107bc:
                raise Blocked('CPtrList destructor on an unknown receiver')
            current, seen = self.word(receiver+4), set()
            while current:
                if current in seen or current not in self.allocations or len(seen) >= 4096:
                    raise Blocked('Invalid native list ownership during destruction')
                seen.add(current)
                current = self.word(current)
            if len(seen) != self.word(receiver+12):
                raise Blocked('Invalid native list count during destruction')
            for node in seen:
                self.allocations.pop(node)
            for offset in (4, 8, 12, 16, 20):
                self.put(receiver+offset, 0)
            self.put(receiver, 0x50becc)
            self.physical_events.append(dict(service='CPtrList destructor', receiver=hex(receiver), removed=len(seen)))
            self.returned(0)
            return
        if address in (0x4f695c, 0x4f6920):
            # MFC CString operator+= (CString& / LPCSTR), copy semantics like
            # the base CString fixtures; storage stays allocated.
            name = 'CString append CString' if address == 0x4f695c else 'CString append text'
            self.platform_call(address, 'MFC '+name)
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            source = self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            if not receiver or not source:
                raise Blocked('Null CString append operand')
            added = self.bytestring(self.word(source) if address == 0x4f695c else source)
            self.put(receiver, self.cstring(self.bytestring(self.word(receiver))+added))
            self.returned(receiver, 4)
            return
        if address == 0x4a4630:
            # CRT div(numerator, denominator): div_t returned in EAX:EDX,
            # truncating toward zero.
            self.platform_call(address, 'CRT div')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            signed = lambda v: v-0x100000000 if v >= 0x80000000 else v
            numerator, denominator = signed(self.word(sp+4)), signed(self.word(sp+8))
            if denominator == 0 or (numerator, denominator) == (-0x80000000, -1):
                raise Blocked('CRT div faults for this operand pair')
            quotient = abs(numerator)//abs(denominator)*(1 if (numerator < 0) == (denominator < 0) else -1)
            self.machine.reg_write(UC_X86_REG_EDX, (numerator-quotient*denominator) & 0xffffffff)
            self.returned(quotient)
            return
        if address == 0x4f55e9:
            # MFC CPtrArray::RemoveAt(index, count): shift the tail down.
            self.platform_call(address, 'MFC CPtrArray RemoveAt')
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            index, count = self.word(sp+4), self.word(sp+8)
            data, size = self.word(receiver+4), self.word(receiver+8)
            if self.word(receiver) != 0x51079c or index+count > size or size > 0x100000:
                raise Blocked('Invalid native pointer-array RemoveAt')
            tail = size-index-count
            if tail:
                self.machine.mem_write(data+4*index, bytes(self.machine.mem_read(data+4*(index+count), 4*tail)))
            self.put(receiver+8, size-count)
            self.physical_events.append(dict(service='CPtrArray RemoveAt', receiver=hex(receiver), index=index, count=count))
            self.returned(0, 8)
            return
        if address == 0x4a3ae0:
            # CRT _chkstk: EAX bytes of caller stack; returns with ESP lowered.
            self.platform_call(address, 'CRT _chkstk')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            size = self.machine.reg_read(UC_X86_REG_EAX)
            ret = self.word(sp)
            new_sp = sp+4-size
            if size > 0x100000 or new_sp < 0x01ff1000:
                raise Blocked('Stack probe exceeds the physical stack')
            self.machine.reg_write(UC_X86_REG_ESP, new_sp)
            self.machine.reg_write(UC_X86_REG_EAX, ret)
            self.machine.reg_write(UC_X86_REG_EIP, ret)
            return
        if address == 0x4f504f:
            # MFC CTime::GetCurrentTime(out): elected fixed physical wall clock.
            self.platform_call(address, 'MFC CTime GetCurrentTime')
            out = self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            if not out:
                raise Blocked('CTime result storage is null')
            self.put(out, WALL_CLOCK)
            self.physical_events.append(dict(service='CTime GetCurrentTime', value=WALL_CLOCK,
                profile='elected fixed UTC wall clock '+time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(WALL_CLOCK))))
            self.returned(out, 4)
            return
        if address == 0x4f5062:
            # MFC CTime::GetLocalTm(ptm), thiscall; ptm null returns the CRT
            # static struct tm. The elected local zone is UTC.
            self.platform_call(address, 'MFC CTime GetLocalTm')
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            target = self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            value = self.word(receiver)
            if value >= 0x80000000:
                raise Blocked('Negative CTime value')
            t = time.gmtime(value)
            fields = (t.tm_sec, t.tm_min, t.tm_hour, t.tm_mday, t.tm_mon-1, t.tm_year-1900,
                      (t.tm_wday+1) % 7, t.tm_yday-1, 0)
            if not target:
                if not getattr(self, 'static_tm', None):
                    self.static_tm = self.allocate(36)
                target = self.static_tm
            self.machine.mem_write(target, struct.pack('<9i', *fields))
            self.physical_events.append(dict(service='CTime GetLocalTm', value=value, tm=list(fields)))
            self.returned(target, 4)
            return
        if api == 'PostMessageA':
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            if self.word(sp+8) == 0x111 and self.word(sp+12) == 0x800e:
                self.level_complete_posted = True
        return super().fixture(address)

    def state_snapshot(self, application, label):
        state = self.word(application+0x2c)
        vtable = self.word(state)
        entry = dict(label=label, milliseconds=self.milliseconds, object=hex(state), vtable=hex(vtable))
        if vtable == MENU_VTABLE:
            entry.update(menu_id=self.word(state+0x29c))
        elif vtable == SINGLE_PLAYER_VTABLE:
            entry.update(level=self.word(state+0x14))
        last = self.state_transitions[-1] if self.state_transitions else None
        if not last or (last['object'], last['vtable'], last.get('menu_id')) != (entry['object'], entry['vtable'], entry.get('menu_id')):
            self.state_transitions.append(entry)
            print(json.dumps(dict(event='state', **entry)), flush=True)
        return entry

    def deliver_key(self, application, vk, scan, phase):
        state = self.word(application+0x2c)
        target = self.word(self.word(state)+0x30)
        self.key_deliveries.append(dict(phase=phase, key=vk, scan=scan, target=hex(target),
            receiver=hex(state), vtable=hex(self.word(state)), milliseconds=self.milliseconds))
        self.run(target, state, (vk, (scan << 16) | 1), phase=phase)

    def play(self, application):
        if self.level_checkpoint is not None and not self.resumed_checkpoint:
            self.level_start_checkpoint = True
            self.checkpoint_path = self.level_checkpoint
            self.save_checkpoint()
            self.checkpoint_path = None
        self.end_of_level(application)

    def end_of_level(self, application):
        self.clock_step = 0
        self.play_frames = []
        start = self.milliseconds
        self.state_snapshot(application, 'level-one-loaded')
        self.play_frames.append(dict(elapsed_ms=0, action='loaded', player=self.player_snapshot(application)))
        while self.milliseconds-start < self.standing_ms:
            self.frame(application, 'play-stand')
            self.play_frames.append(dict(elapsed_ms=self.milliseconds-start, action='stand',
                player=self.player_snapshot(application)))
        self.completed_play_ms = self.milliseconds-start
        # Level completion and results run timed palette fades that poll the
        # physical timer; as in menu navigation, each query advances 1 ms.
        self.clock_step = 1
        for index, letter in enumerate(CHEAT):
            vk, scan = LETTERS[letter]
            self.deliver_key(application, vk, scan, f'cheat-key-{index}-{letter}')
            self.cheat_keys.append(dict(letter=letter, key=vk, milliseconds=self.milliseconds,
                game_ms=self.word(0x537208)))
            self.frame(application, f'cheat-frame-{index}')
        if not self.level_complete_posted:
            raise Blocked('Original cheat manager did not post the level-complete command')
        self.state_snapshot(application, 'after-level-complete-command')
        self.results_start = self.milliseconds
        self.results(application)

    def results(self, application):
        while self.milliseconds-self.results_start < self.results_limit_ms:
            entry = self.state_snapshot(application, 'results')
            if entry['vtable'] == hex(SINGLE_PLAYER_VTABLE) and entry.get('level') != 1:
                # The original continues into the next level after results.
                if entry.get('level') != 2:
                    raise Blocked('Results continued into an unexpected level')
                self.level_two(application)
                return
            # A state that stays unchanged for 12000 ms is waiting for the
            # player: deliver one physical Return through its own key-down
            # virtual, then wait again. Bounded by results_limit_ms.
            if entry['object'] != getattr(self, 'waiting_object', None):
                self.waiting_object, self.waiting_since = entry['object'], self.milliseconds
            elif self.milliseconds-self.waiting_since >= 12000:
                self.deliver_key(application, 13, 0x1c, 'results-key-return-'+entry['vtable'])
                self.waiting_since = self.milliseconds
            self.frame(application, 'results-'+entry['vtable'])
        raise Blocked('Results did not continue into Level 2 within the bounded frame budget')

    def level_two(self, application):
        # Gameplay frames as in Level 1 play: the frame step is the only
        # physical clock advance.
        self.clock_step = 0
        self.level_two_loaded = True
        start = self.milliseconds
        first = self.player_snapshot(application)
        self.level_two_frames.append(dict(elapsed_ms=0, action='loaded', player=first))
        while self.milliseconds-start < self.level_two_ms:
            elapsed = self.milliseconds-start
            action = next(a for a in LEVEL_TWO_PLAN if a['start_ms'] <= elapsed < a['end_ms'])
            self.frame(application, 'level-two-'+action['action'], action['keys'])
            state = self.word(application+0x2c)
            if self.word(state) != SINGLE_PLAYER_VTABLE or self.word(state+0x14) != 2:
                raise Blocked('Original Level 2 play left the single-player Level 2 state')
            self.level_two_played_ms = self.milliseconds-start
            self.level_two_frames.append(dict(elapsed_ms=self.level_two_played_ms, action=action['action'],
                player=self.player_snapshot(application)))
            if len(self.level_two_frames) % 60 == 0:
                print(json.dumps(dict(event='level-two', **self.level_two_frames[-1])), flush=True)
        self.level_two_game_ms = (self.level_two_frames[-1]['player']['game_ms']-first['game_ms']) & 0xffffffff
        self.state_snapshot(application, 'level-two-played')

    def save_checkpoint(self):
        if self.checkpoint_path is None:
            return
        excluded = {'machine', 'program', 'decoder', 'font', 'files', 'factory_context', 'checkpoint_path',
                    'level_checkpoint'}
        state = {k: v for k, v in self.__dict__.items() if k not in excluded}
        payload = dict(version=3, parent_sha256=hashlib.sha256((ROOT/'Tests/NativeMenuBase/trace.py').read_bytes()).hexdigest(),
            level_sha256=self.level_tracer_fingerprint,
            storage_sha256=self.storage_fingerprint, state=state, cpu=self.cpu_state(),
            files={k: (str(v.name), v.tell()) for k, v in self.files.items()})
        save_checkpoint(self.checkpoint_path, payload, self.machine)

    def resume_level_checkpoint(self, path):
        # Local diagnostic cache only; the final retained run is fresh.
        payload = load_checkpoint(path)
        self.validate_checkpoint_profile(payload['state'])
        if payload.get('storage_sha256') != self.storage_fingerprint:
            raise Blocked('Stale checkpoint storage implementation')
        if (payload['version'] != 3 or payload.get('level_sha256') != self.level_tracer_fingerprint
                or payload['parent_sha256'] != hashlib.sha256((ROOT/'Tests/NativeMenuBase/trace.py').read_bytes()).hexdigest()):
            raise Blocked('Stale Level 1 checkpoint')
        if not payload['state'].get('level_start_checkpoint'):
            raise Blocked('Checkpoint was not taken at Level 1 start')
        with REZ_PATH.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != REZ_SHA256:
                raise Blocked('Original archive hash mismatch')
        keep = {k: getattr(self, k) for k in ('instruction_limit', 'deny_platform', 'tracer_fingerprint',
            'parent_fingerprint', 'end_tracer_fingerprint', 'level_tracer_fingerprint', 'standing_ms',
            'results_limit_ms', 'level_two_ms')}
        self.__dict__.update(payload['state'])
        self.__dict__.update(keep)
        self.resumed_checkpoint = True
        self.parent_checkpoint = dict(path=str(path), sha256=fingerprint(path),
            startup_profile=self.startup_profile)
        restore_memory(path, self.machine)
        registers = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
            UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
            UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG)
        for r, v in zip(registers, payload['cpu']):
            self.machine.reg_write(r, v)
        for i, v in enumerate(payload['cpu'][len(registers):]):
            self.machine.reg_write(UC_X86_REG_FP0+i, v)
        for handle, (name, position) in payload['files'].items():
            if Path(name).resolve() != REZ_PATH.resolve():
                raise Blocked('Unexpected checkpoint file')
            self.files[handle] = open(name, 'rb')
            self.files[handle].seek(position)
        self.end_of_level(self.application)

    def report(self):
        result = super().report()
        result.update(end_tracer_sha256=self.end_tracer_fingerprint,
            startup_profile=self.startup_profile, startup_queries=self.startup_queries,
            startup_objects=self.startup_objects, parent_checkpoint=self.parent_checkpoint,
            storage_sha256=self.storage_fingerprint,
            level_tracer_sha256=self.level_tracer_fingerprint,
            status='blocked',
            scope='Original Level 1 completion through results, Level 2 loading and the first seconds of Level 2 play; discovery only, no native parity or admission claim',
            route=dict(kind='original cheat code', code=CHEAT, delivery='single-player key-down 0x46bb30 -> cheat manager 0x422e00',
                posted_command='0x800e', same_command_as='player end-of-level gem sequence post at 0x41f04f',
                standing_ms=self.standing_ms),
            not_covered=['Return to the main menu through the in-game menu (vtable 0x50c044): not required by the owner decision of 2026-10-21; after results the original continues into Level 2, which this trace follows.',
                'End-of-level gem touch and the player victory sequence before 0x41f04f: the owner chose the MPSCULLY route on 2026-10-21 (Level 1 offers no original warp to the gem; its boss-warp fields stay zero in 0x452c50, so MPSKINNER does nothing).',
                'Typed cheats set cheat-manager +0x128, so an end-of-level save takes the refusal branch instead of writing a save.'],
            cheat_keys=self.cheat_keys, key_deliveries=self.key_deliveries,
            sent_messages=self.sent_messages, state_transitions=self.state_transitions,
            level_complete_posted=self.level_complete_posted, level_two_loaded=self.level_two_loaded,
            level_two_plan=list(LEVEL_TWO_PLAN), level_two_requested_ms=self.level_two_ms,
            level_two_played_ms=self.level_two_played_ms, level_two_game_ms=self.level_two_game_ms,
            level_two_frames=self.level_two_frames)
        result['limitations'] = result['limitations']+['Level completion is reached through the original MPSCULLY cheat command, not the gem touch.']
        if (self.stop is None and self.level_one_loaded and self.level_two_loaded
                and self.level_two_played_ms >= self.level_two_ms):
            result['status'] = 'pass'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/end-of-level-map/trace.json')
    parser.add_argument('--instruction-limit', type=int, default=3_000_000_000)
    parser.add_argument('--level-checkpoint', type=Path,
        help='Local Level 1 start cache under work/; resumed when present, written when absent')
    parser.add_argument('--standing-ms', type=int, default=1000)
    parser.add_argument('--paper-startup', action='store_true',
        help='Construct startup fader/palette and advance timer queries 1 ms from initialization')
    parser.add_argument('--level-two-ms', type=int, default=5000)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived output must stay under ignored work/')
    trace = EndOfLevelTrace(args.instruction_limit, None, standing_ms=args.standing_ms,
        level_two_ms=args.level_two_ms, startup_paper=args.paper_startup)
    try:
        if args.level_checkpoint:
            checkpoint = args.level_checkpoint.resolve()
            if not checkpoint.is_relative_to((ROOT/'work').resolve()):
                parser.error('Checkpoint must stay under work/')
            if exists(checkpoint):
                trace.resume_level_checkpoint(checkpoint)
            else:
                trace.level_checkpoint = checkpoint
                trace.execute()
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output = write_trace(output, report)
    print(json.dumps(dict(status=report['status'], counts=report['counts'], stop=report['stop'],
        state_transitions=report['state_transitions'], output=str(output))), flush=True)
    return 0 if report['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
