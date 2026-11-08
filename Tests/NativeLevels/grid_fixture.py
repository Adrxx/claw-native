"""Shared bounded CRT vector adapter for later-level original grid storage.

Only the platform iterator is supplied here. Each element callback executes
original game code through MenuTrace's checked callback return path.
"""
from unicorn.x86_const import UC_X86_REG_ESP
from Tests.NativeMenuBase.trace import Blocked


class LargeGridFixture:
    def fixture(self, address):
        if address not in (0x4a4590, 0x4a4450):
            return super().fixture(address)
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        if self.word(sp+12) <= 65536:
            return super().fixture(address)
        base, stride, count, callback = (self.word(sp+4*i) for i in range(1,5))
        construct = address == 0x4a4590
        destructor = self.word(sp+20) if construct else callback
        # Level 3's original grid is 0x12000 cells. Preserve callback execution,
        # stride, ordering and allocation validation; only widen the physical
        # adapter's discovery bound, without replacing any game callback.
        if (stride != 8 or callback != (0x4f4a90 if construct else 0x4c96b0)
                or destructor != 0x4c96b0 or count > 0x100000
                or base+stride*count > 0x100000000
                or not any(start <= base and base+stride*count <= start+length
                           for start,length in self.allocations.items())):
            raise Blocked('Unsupported or unallocated later-level grid vector')
        service = 'CRT vector '+('constructor' if construct else 'destructor')+' iterator'
        self.platform_call(address, service)
        event = dict(service=service,phase=self.phase,base=hex(base),stride=stride,count=count,
                     constructor=hex(callback),destructor=hex(destructor),completed=0)
        self.physical_events.append(event)
        frame = dict(context=self.machine.context_save(),fs=self.word(0),sp=sp,cpu=self.cpu_state(),
                     base=base if construct else base+(count-1)*stride,
                     stride=stride if construct else -stride,count=count,constructor=callback,index=0,
                     event=event,pop=20 if construct else 16,service=address)
        self.array_callbacks.append(frame)
        self.start_array_element(frame)

