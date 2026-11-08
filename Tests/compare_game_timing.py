#!/usr/bin/env python3
"""Original v1.0 clock instructions against native source, with an explicit
timeGetTime adapter. The original busy wait itself is never replaced."""
import ctypes as C
from pathlib import Path
import random
import struct
import subprocess
import sys
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP
from original_v10 import OriginalV10

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/timing-agent'
WORK.mkdir(parents=True, exist_ok=True)
subprocess.run(['clang++', '-std=c++17', '-O2', '-dynamiclib',
                str(ROOT/'Sources/GameTiming.cpp'), '-o', str(WORK/'libGameTiming.dylib')], check=True)
lib = C.CDLL(str(WORK/'libGameTiming.dylib'))

class Manager(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ['rate', 'pacing', 'count', 'countStart', 'interval']]
class Clock(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ['now', 'delta', 'paced', 'countdown', 'reload']]
class Frame(C.Structure):
    _fields_ = [('now', C.c_uint32), ('delta', C.c_uint32)]
Read = C.CFUNCTYPE(C.c_uint32, C.c_void_p)
Observe = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32)
class Host(C.Structure):
    _fields_ = [('context', C.c_void_p), ('read', Read), ('observe', Observe)]
lib.claw_timing_update.argtypes = [C.POINTER(Manager), C.POINTER(Clock), Host]
lib.claw_timing_update.restype = C.c_uint32
lib.claw_timing_initialize.argtypes = [C.POINTER(Manager), C.POINTER(Clock), Host]
lib.claw_timing_wait.argtypes = [C.c_uint32, Host]
lib.claw_timing_reset_rate.argtypes = [C.POINTER(Manager), C.c_uint32, Host]
lib.claw_timing_reset_clock.argtypes = [C.POINTER(Clock), Host]
lib.claw_timing_update_animation.argtypes = [C.POINTER(Frame), C.c_uint32, Host]
lib.claw_timing_publish_stage.argtypes = [C.POINTER(Clock), C.POINTER(Frame), C.POINTER(C.c_uint32)]
lib.claw_timing_set_replay.argtypes = [C.POINTER(Frame), C.POINTER(C.c_uint32), C.POINTER(Frame), C.c_uint32, C.c_uint32, C.c_uint32]

def words(value):
    return list(struct.unpack('<'+'I'*(C.sizeof(value)//4), bytes(value)))

class ClockAdapter:
    def __init__(self, samples):
        self.samples = samples
        self.index = 0
        self.reads = []
        self.waits = []
        self.snapshot = None
        self.sample_states = []
        self.native_read = Read(self.read)
        self.native_observe = Observe(lambda _, n: self.waits.append(n))
        self.host = Host(None, self.native_read, self.native_observe)

    def read(self, _=None):
        if self.snapshot:
            self.sample_states.append(self.snapshot())
        if self.index >= len(self.samples):
            # ctypes cannot propagate callback exceptions; record failure and
            # advance to a guaranteed terminating value for ordinary deadlines.
            self.reads.append(('EXHAUSTED', self.index))
            return 0xffffffff
        v = self.samples[self.index] & 0xffffffff
        self.index += 1
        self.reads.append(v)
        return v

class OriginalTiming(OriginalV10):
    receiver = 0x1001000
    stub = 0x10ff800
    def __init__(self):
        super().__init__(ROOT/'Original/claw10/CLAW.EXE')
        self.adapter = None
        self.u.mem_write(self.stub, b'\xc3')
        self.write_words(0x546df0, [self.stub])
        self.u.hook_add(UC_HOOK_CODE, self.clock_hook)
    def clock_hook(self, uc, address, size, _):
        if address == self.stub:
            uc.reg_write(UC_X86_REG_EAX, self.adapter.read())
        elif address == 0x4b83f0:
            self.adapter.waits.append(self.read_words(uc.reg_read(UC_X86_REG_ESP)+4,1)[0])

original = OriginalTiming()
rng = random.Random(0x4b82f0)
prefix = [rng.getrandbits(32) for _ in range(6)]
def run_pair(entry, manager, clock, samples, native, args=b''):
    original.write_words(original.receiver, prefix + words(manager))
    original.write_words(0x541328, words(clock))
    oa, na = ClockAdapter(samples), ClockAdapter(samples)
    oa.snapshot = lambda: (original.read_words(original.receiver+0x18,5),original.read_words(0x541328,5))
    na.snapshot = lambda: (words(manager),words(clock))
    original.adapter = oa
    returned = original.call(entry, original.receiver, args)
    native_returned = native(na.host)
    assert original.read_words(original.receiver,11) == prefix + words(manager)
    assert original.read_words(0x541328,5) == words(clock)
    assert oa.reads == na.reads and oa.waits == na.waits, (hex(entry), oa.reads, na.reads, oa.waits, na.waits)
    assert oa.sample_states == na.sample_states, (hex(entry),oa.sample_states,na.sample_states)
    assert not any(isinstance(v,tuple) for v in na.reads)
    if entry == 0x4b82f0:
        assert returned == native_returned == 1

for i in range(6000):
    base = rng.getrandbits(32)
    elapsed = rng.choice([0,1,32,33,1999,2000,2001,rng.getrandbits(32)])
    first = (base + elapsed) & 0xffffffff
    manager = Manager(rng.getrandbits(32),rng.choice([0,1,2,0x7fffffff,0x80000000,0xffffffff]),
                      rng.choice([0,1,0xffffffff,rng.getrandbits(32)]),
                      (first-rng.choice([0,1999,2000,2001,0xffffffff]))&0xffffffff,
                      rng.choice([0,1,16,33,100,0x7fffffff,0xffffffff]))
    clock = Clock(base,rng.getrandbits(32),rng.choice([0,first,(first-10)&0xffffffff,rng.getrandbits(32)]),
                  rng.choice([0,1,32,elapsed,rng.getrandbits(32)]),rng.choice([0,33,100,rng.getrandbits(32)]))
    # A finite clock sequence that exercises wait equality and wrapping while
    # always crossing any actual deadline. The final max value cannot terminate
    # a deadline of max, so dynamically choose a wrapping initial wait sample.
    samples = [first, (first+3)&0xffffffff, 0xfffffffe, 0xffffffff, 0, 1,
               0xffffffff, 0, 0xffffffff, 0xffffffff]
    run_pair(0x4b82f0, manager, clock, samples,
             lambda host: lib.claw_timing_update(C.byref(manager),C.byref(clock),host))
print('PASS 6,000 clock updates: state, return, exact clock reads and wait requests')

for i in range(1500):
    manager = Manager(*(rng.getrandbits(32) for _ in range(5)))
    clock = Clock(*(rng.getrandbits(32) for _ in range(5)))
    clear = rng.choice([0,1,0x80000000,0xffffffff])
    run_pair(0x4b83a0, manager,clock,[rng.getrandbits(32)],
             lambda host: lib.claw_timing_reset_rate(C.byref(manager),clear,host), struct.pack('<I',clear))
    run_pair(0x4b83d0, manager,clock,[rng.getrandbits(32)],
             lambda host: lib.claw_timing_reset_clock(C.byref(clock),host))
print('PASS 1,500 rate resets and 1,500 clock resets')

for i in range(500):
    manager = Manager(*(rng.getrandbits(32) for _ in range(5)))
    clock = Clock(*(rng.getrandbits(32) for _ in range(5)))
    original.write_words(original.receiver,prefix+words(manager))
    original.write_words(0x541328,words(clock))
    samples=[rng.getrandbits(32),rng.getrandbits(32)]
    oa,na=ClockAdapter(samples),ClockAdapter(samples)
    original.adapter=oa
    original.call(0x4b8240,original.receiver)
    lib.claw_timing_initialize(C.byref(manager),C.byref(clock),na.host)
    assert original.read_words(original.receiver+0x18,5)==words(manager)
    assert original.read_words(0x541328,5)==words(clock)
    assert oa.reads==na.reads and oa.waits==na.waits
print('PASS 500 complete original constructors versus portable timing initialization')

# Long histories use an advancing clock with repeated samples, exercising
# ordinary wait loops rather than jumping over deadlines as generated tests do.
class AdvancingClock(ClockAdapter):
    def __init__(self,initial):
        super().__init__([])
        self.tick=initial
    def read(self,_=None):
        v=self.tick
        self.tick=(self.tick+(1 if self.index%3 else 0))&0xffffffff
        self.index+=1
        self.reads.append(v)
        return v

for history in range(24):
    manager=Manager(0xffffffff,1,0,0,33)
    clock=Clock(0,0,0,100,33)
    start=rng.choice([0,1000,0xfffff000])
    oa,na=AdvancingClock(start),AdvancingClock(start)
    original.adapter=oa
    original.write_words(original.receiver,prefix+words(manager))
    original.write_words(0x541328,words(clock))
    for frame_index in range(500):
        manager.pacing=0 if frame_index%71==0 else 1
        manager.interval=[0,1,16,33][frame_index//125]
        original.write_words(original.receiver+0x1c,[manager.pacing])
        original.write_words(original.receiver+0x28,[manager.interval])
        original.call(0x4b82f0,original.receiver)
        lib.claw_timing_update(C.byref(manager),C.byref(clock),na.host)
        assert original.read_words(original.receiver,11)==prefix+words(manager)
        assert original.read_words(0x541328,5)==words(clock)
        assert oa.reads==na.reads and oa.waits==na.waits
print('PASS 12,000 chained paced frames with repeated clock samples and uptime wrap')

for duration, samples in [(0,[20,20,20,21]),(1,[20,21,21,22]),(33,[20,30,53,54]),
                           (1,[0xffffffff]),(2,[0xfffffffe]),(0xffffffff,[20]),
                           (0x80000000,[0x80000000]),(0,[0xfffffffe,0xffffffff])]:
    oa, na = ClockAdapter(samples),ClockAdapter(samples)
    original.adapter = oa
    original.call(0x4b83f0,original.receiver,struct.pack('<I',duration))
    lib.claw_timing_wait(duration,na.host)
    assert oa.reads == na.reads == samples and oa.waits == na.waits == [duration]
print('PASS inclusive wait boundaries, zero duration, and wrapped deadlines')

# Full original 0x4c8fc0 runs with already-initialized empty actor/deletion/reorder
# lists. Its collection helpers execute; only timeGetTime is adapted.
original.u.mem_write(0x5430d0,b'\x03')
original.write_words(0x5430d8,[0]*6)
original.write_words(0x5430f0,[0]*6)
for i in range(1500):
    frame = Frame(rng.getrandbits(32),rng.getrandbits(32))
    original.write_words(0x5430c8,[frame.now])
    original.write_words(0x5430c4,[frame.delta])
    original.write_words(original.receiver,[0]*16)
    refresh = rng.choice([0,1,0xffffffff])
    samples = [rng.getrandbits(32)]
    oa,na = ClockAdapter(samples),ClockAdapter(samples)
    original.adapter = oa
    original.call(0x4c8fc0,original.receiver,struct.pack('<I',refresh))
    lib.claw_timing_update_animation(C.byref(frame),refresh,na.host)
    assert [original.read_words(0x5430c8,1)[0],original.read_words(0x5430c4,1)[0]] == words(frame)
    assert oa.reads == na.reads and not oa.waits
print('PASS 1,500 animation clock samples through full original empty-list dispatcher')

for i in range(1500):
    manager = Manager(*(rng.getrandbits(32) for _ in range(5)))
    manager.pacing = 0
    clock = Clock(*(rng.getrandbits(32) for _ in range(5)))
    stage = Frame(rng.getrandbits(32),rng.getrandbits(32))
    accumulated = C.c_uint32(rng.getrandbits(32))
    original.write_words(original.receiver,[0]*48)
    original.write_words(original.receiver+0x18,words(manager))
    original.write_words(original.receiver+0xb0,[1]) # pause callback only
    original.write_words(0x541328,words(clock))
    original.write_words(0x537208,[stage.now,stage.delta,accumulated.value])
    samples=[rng.getrandbits(32),rng.getrandbits(32)]
    oa,na=ClockAdapter(samples),ClockAdapter(samples)
    original.adapter=oa
    assert original.call(0x428b60,original.receiver)==0
    lib.claw_timing_update(C.byref(manager),C.byref(clock),na.host)
    lib.claw_timing_publish_stage(C.byref(clock),C.byref(stage),C.byref(accumulated))
    assert original.read_words(0x537208,3)==[stage.now,stage.delta,accumulated.value]
    assert original.read_words(0x541328,5)==words(clock)
    assert oa.reads==na.reads
    now,delta,total=(rng.getrandbits(32) for _ in range(3))
    animation=Frame(0,0)
    original.call(0x42ae40,0,struct.pack('<III',now,delta,total))
    lib.claw_timing_set_replay(C.byref(stage),C.byref(accumulated),C.byref(animation),now,delta,total)
    assert original.read_words(0x537208,3)==[stage.now,stage.delta,accumulated.value]
    assert [original.read_words(0x5430c8,1)[0],original.read_words(0x5430c4,1)[0]]==words(animation)
print('PASS 1,500 paused stage publications and 1,500 replay clock assignments')
print(f'Original instruction addresses reached: {len(original.executed)}; only timeGetTime is adapted')
