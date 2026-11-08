"""Blind whole-source registry cases, with original-created prepared unit state."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt, HarnessError, HEAP_BASE
from clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP

INIT, APPEND, ATEXIT, LOCK, UNLOCK = 0x4a3610, 0x4a3560, 0x4a35f0, 0x4a5860, 0x4a5870
PCS = {INIT: 0x4a5896, APPEND: 0x4a35fa, ATEXIT: 0x42520a, LOCK: 0x4a3566, UNLOCK: 0x4a35eb}
CALLBACKS = (0x425210, 0x4ad7e0, 0x4a5780)


def prepared(random_source, root, count=0, mode='move', fail=False, held=0, fatal=False, module_name=True, retry=False):
    stack_pattern = random_source.randbytes(1024)
    registers = [random_source.getrandbits(32) for _ in range(7)]
    frame = STACK_TOP - random_source.choice((0, 0x1000, 0x3000))
    flags = 2 | random_source.choice((0, 1, 4, 0x10, 0x40, 0x80, 0x800, 0x8d5))
    def setup(env):
        ledger = env.object(4096, 'memory-service-v1-ledger', fill=0)
        locks = env.object(256, 'physical-section-ledger', fill=0)
        # Ledger stores active identity, usable capacity, requested size and counters.
        def malloc(e, call):
            size = call.arguments[0]
            e.put(ledger+12, e.get(ledger+12)+1)
            if e.get(ledger+20):
                e.put(ledger+20, 0)
                return 0
            cap = (size+15)&~15
            base = e.object(2048, 'CRT-memory-reserved-backing', fill=0xa7)
            e.put(ledger, base, cap, size)
            return base
        def capacity(e, call):
            base = call.arguments[0]
            if base != e.get(ledger) or base not in e.spans:
                raise HarnessError('capacity requires live exact owner base')
            e.put(ledger+16, e.get(ledger+16)+1)
            return e.get(ledger+4)
        def resize(e, call):
            base, size = call.arguments
            if base != e.get(ledger) or base not in e.spans or size > 2048:
                raise HarnessError('resize requires bounded live owner')
            e.put(ledger+24, e.get(ledger+24)+1)
            if e.get(ledger+28):
                e.put(ledger+28, 0)
                return 0
            cap = (size+15)&~15
            if mode == 'move':
                new = e.object(2048, 'CRT-resize-reserved-backing', fill=0xb9)
                e.write(new, e.read(base, min(e.get(ledger+4), cap)))
                e.release(base)
            else:
                new = base
            e.put(ledger, new, cap, size)
            return new
        def free(e, call):
            base = call.arguments[0]
            if base:
                if base != e.get(ledger):
                    raise HarnessError('free requires owner base')
                e.release(base)
                e.put(ledger, 0, 0, 0)
            return 0
        def section_slot(ptr):
            pointers = (0x540e38, 0x540e68, 0x540e50, 0x540e20)
            if ptr not in pointers:
                raise HarnessError('unsupported physical section identity')
            return locks+16*pointers.index(ptr)
        def initialize(e, call):
            slot = section_slot(call.arguments[0])
            if e.get(slot):
                raise HarnessError('duplicate section initialization')
            e.put(slot, 1, 0, 0)
            return 0
        def enter(e, call):
            slot = section_slot(call.arguments[0])
            if not e.get(slot):
                raise HarnessError('enter uninitialized section')
            e.put(slot+4, 1, e.get(slot+8)+1)
            return 0
        def leave(e, call):
            slot = section_slot(call.arguments[0])
            depth = e.get(slot+8)
            if not depth or e.get(slot+4) != 1:
                raise HarnessError('release without ownership')
            e.put(slot+4, int(depth>1), depth-1)
            return 0
        def filename(e, call):
            if not module_name:
                return 0
            name = b'C:\\CaptainClaw\\CLAW.EXE\0'
            amount = min(len(name), call.arguments[2])
            e.write(call.arguments[1], name[:amount])
            return amount-1
        def filter_change(e, call):
            old = e.get(locks+80)
            e.put(locks+80, call.arguments[0])
            return old
        def exit_process(e, call):
            e.put(locks+84, call.arguments[0], e.get(locks+16+8))
            raise Halt()
        for address, effect in ((0x4a48e0,malloc),(0x4a49b0,free),(0x4a6560,capacity),(0x4a9070,resize),
            (0x546aa4,initialize),(0x546aac,enter),(0x546a9c,leave),(0x5469f4,filename),
            (0x546a14,lambda e,c:0),(0x546980,filter_change),(0x546998,exit_process)):
            env.override(address,effect)
        # Run original initialization/registrations to build prior unit state.
        # Copy actual execution memory back to setup, never emulate source publications.
        env.machine.write(HEAP_BASE, env.read(HEAP_BASE, env.heap_bytes))
        env.machine.write(env.program.data_start, env.read(env.program.data_start,env.program.size-env.data_offset))
        env.backend = 'machine'
        env.machine.call(0x4a7b90, 0, 0, ())
        if root != INIT or count:
            env.machine.call(INIT, 0, 0, ())
            for index in range(count):
                env.machine.call(APPEND, 0, 0, (CALLBACKS[index%len(CALLBACKS)],))
        if retry:
            env.put(ledger+28,1)
            env.machine.call(APPEND,0,0,(CALLBACKS[0],))
        for _ in range(held):
            env.machine.call(LOCK,0,0,())
        heap = env.read(HEAP_BASE,env.heap_bytes)
        image = env.read(env.program.data_start,env.program.size-env.data_offset)
        env.backend = 'initial'
        env.write(HEAP_BASE,heap)
        env.write(env.program.data_start,image)
        env.put(ledger+28,int(fail))
        env.put(ledger+20,int(fatal))
        env.put(locks+80,0x425210)
        env.write(STACK_BASE, stack_pattern*(STACK_SIZE//len(stack_pattern)))
        # Two intact nested FS records outside all active call/restoration slots.
        fs = STACK_BASE+0x100
        env.put(fs,fs+0x20,0x4ad7e0,0x76543210,0x12345678)
        env.put(fs+0x20,0xffffffff,0x425210,0x89abcdef,0x10203040)
        source = NativeSourceContext()
        source.size,source.version = 72,1
        source.inputMask=source.outputMask=0x7ff
        source.preserveMask=0x472
        for name,value in zip(('eax','ebx','ecx','edx','esi','edi','ebp'),registers):
            setattr(source,name,value)
        source.esp,source.eip,source.eflags,source.fsHead=frame,root,flags,fs
        return {'source':source}
    return setup


def cases(random_source):
    def case(label,root,callback=0x425210,**options):
        return Case(label,root,prepared(random_source,root,**options),
            arguments=(callback,) if root in (APPEND,ATEXIT) else (),
            source_context=lambda tokens:tokens['source'],source_return_pc=PCS[root],
            expect='halt' if options.get('fatal') else 'return')
    for index in range(16):
        yield case(f'initializer full CPU {index}',INIT)
        yield case(f'lock nested depth {index}',LOCK,held=index%4)
        yield case(f'unlock nested depth {index}',UNLOCK,held=1+index%4)
    for root in (APPEND,ATEXIT):
        for count in (0,1,2,7,15,30,31,32,33,35,36,63,64,65,125,126):
            for mode in ('move','inplace'):
                for callback in (0,*CALLBACKS):
                    yield case(f'prepared-unit {root:x} count{count} {mode} callback{callback:x}',root,
                        callback,count=count,mode=mode,held=count%3)
        for count in (32,36,64,128):
            for mode in ('move','inplace'):
                yield case(f'resize fail {root:x} count{count} {mode}',root,count=count,mode=mode,fail=True)
                yield case(f'prepared failed resize then retry {root:x} count{count} {mode}',root,count=count,mode=mode,retry=True)
    for module_name in (False,True):
        for held in (0,1,3):
            yield case(f'initial malloc fatal GUI library unavailable filename{module_name} held{held}',INIT,
                fatal=True,module_name=module_name,held=held,count=32 if held else 0)
