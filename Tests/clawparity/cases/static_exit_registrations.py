"""Independent original-only static registration inputs, including both epilogues."""
import json
from pathlib import Path
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

# Only entry identities come from the public manifest. Callback values and
# instruction effects are observed through original execution, never predicted.
ENTRY_ROWS = json.loads(
    (Path(__file__).resolve().parents[2]/'families/static_exit_registrations.json').read_text())['owned']
ENTRIES = tuple(int(row['address'],16) for row in ENTRY_ROWS)
RETURN_INSTRUCTIONS = {int(row['address'],16):int(row['body_ranges'][0]['end'],16)-1
    for row in ENTRY_ROWS}
RETURN_PC = 0x4a5896  # actual indirect initialization-table CALL continuation


def prepared(random_source, root, mode, serial):
    registers = [random_source.getrandbits(32) for _ in range(7)]
    flags = 2 | random_source.choice((0,1,4,0x10,0x40,0x80,0x800,0x8d5))
    pattern = random_source.randbytes(1024)
    count = random_source.choice((0,1,3,7,31))
    capacity = 4*(count+(2 if mode=='spare' else 0))
    frame = STACK_TOP-random_source.choice((0,0x1000,0x3000))
    fixture_results = [random_source.getrandbits(32) for _ in range(2)]
    def setup(env):
        # Original decoded leaf boundaries: PUSH imm32, CALL rel32,
        # either ADD ESP4 or POP ECX, then the final plain RET.
        env.observe_source_boundary(root,root+5,root+10,RETURN_INSTRUCTIONS[root])
        table = env.object(1024,'registry-backing',data=random_source.randbytes(1024))
        section = env.object(24,'critical-section',fill=0x93)
        ledger = env.object(4096,'physical-observations',fill=0)
        env.put(0x545fd4,table)
        env.put(0x545fd0,table+4*count)
        env.put(0x52ed18+13*4,section)
        env.put(ledger,table,capacity,0,serial)
        def observe(e,c,slot):
            cpu=c.source_context
            e.put(ledger+slot,c.function,c.stack_pointer,c.source_return_pc,
                  c.arguments[0],cpu.ecx,cpu.edx,cpu.eflags,
                  e.get(c.stack_pointer),e.get(c.stack_pointer+4))
            # Capture source-produced caller/callee slots, including inactive
            # physical frames. No expected words or source instruction effects
            # are reconstructed here: the memory comparison decides.
            snapshot = ledger+256+((slot-32)//40)*768
            e.put(snapshot,*(getattr(cpu,name) for name in
                ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead')))
            e.write(snapshot+64,e.read(frame-512,640))
        def usable(e,c):
            observe(e,c,32)
            return e.get(ledger+4)
        def resize(e,c):
            observe(e,c,72)
            e.put(ledger+8,e.get(ledger+8)+1)
            base,size=c.arguments
            if mode=='failure':return 0
            if mode=='move':
                result=e.object(1024,'moved-registry',fill=0xb7)
                e.write(result,e.read(base,e.get(ledger+4)))
                e.release(base)
            else:result=base
            e.put(ledger,result,size)
            return result
        def enter(e,c):
            observe(e,c,112)
            e.put(ledger+12,e.get(ledger+12)+1)
            return fixture_results[0]
        def leave(e,c):
            observe(e,c,152)
            e.put(ledger+16,e.get(ledger+16)+1)
            return fixture_results[1]
        for address,effect in ((0x4a6560,usable),(0x4a9070,resize),(0x546aac,enter),(0x546a9c,leave)):
            env.override(address,effect)
        env.write(STACK_BASE,pattern*(STACK_SIZE//len(pattern)))
        fs=STACK_BASE+0x100
        env.put(fs,fs+0x20,0x4ad7e0,0x12345678)
        env.put(fs+0x20,0xffffffff,0x425210,0x87654321)
        context=NativeSourceContext(72,1,0x7ff,0x7ff,*registers,
            frame,root,flags,fs,0x472,0,0)
        env.put(frame,RETURN_PC)
        return {'source':context}
    return setup


def cases(random_source):
    for serial,root in enumerate(ENTRIES):
        for mode in ('spare','failure','move','inplace'):
            yield Case(f'static leaf {root:x} {mode}',root,
                prepared(random_source,root,mode,serial),
                source_context=lambda tokens:tokens['source'],source_return_pc=RETURN_PC)
