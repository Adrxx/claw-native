"""Blind original whole-factory cases; only physical allocation/exception fixtures."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.fixtures import halt
from clawparity.kernel import STACK_BASE,STACK_SIZE,STACK_TOP


def setup(function,frame,old_base,head,registers,flags,failure=False,pointer_low=None):
    def build(env):
        trace=env.object(1024,'physical allocation and exception CPU/frame witnesses',fill=0)
        env.put(frame-0x300,*[(0x91000000+i*0x10101)&0xffffffff for i in range(0xc0)])
        return_pc=0x5033be if function==0x502335 else 0x503450
        env.put(frame,return_pc,0x10203040,0x50607080)
        if head!=0xffffffff:
            env.put(head,head+0x20,0x508bf8,0xffffffff)
            env.put(head+0x20,head+0x40,0x508525,0xffffffff)
            env.put(head+0x40,0xffffffff,0x508539,0xffffffff)
        context=NativeSourceContext(72,1,0x7ff,0x7ff,*registers,
                                   old_base,frame,function,flags,head,0x472,0,0)
        def record(e,c,result):
            count=e.get(trace);where=trace+4+count*96;e.put(trace,count+1)
            source=c.source_context
            state=[getattr(source,k) for k in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead')] if source is not None else [0]*11
            args=list(c.arguments)+[0]*4
            e.put(where,c.function,c.stack_pointer,c.source_return_pc,len(c.arguments),*args[:4],int(source is not None),*state,result)
        def allocate(e,c):
            flags_,size=c.arguments
            pointer=0
            if not failure:
                backing=e.object(size+544,'bounded allocation with independent canaries',fill=0xa6)
                pointer=backing+16
                if pointer_low is not None:
                    pointer+=(pointer_low-pointer)&0xff
                if flags_&0x40:e.write(pointer,bytes(size))
            record(e,c,pointer)
            return pointer
        def raise_exception(e,c):
            record(e,c,0)
            e.write(trace+900,e.read(c.arguments[3],12))
            return halt()(e,c)
        env.override(0x546aa8,allocate)
        env.override(0x546958,raise_exception)
        return {'source':context,'return':return_pc}
    return build


def cases(random_source):
    for function in (0x502335,0x502369):
        for frame in (STACK_BASE+0x600,STACK_TOP,STACK_BASE+STACK_SIZE-0x200):
            for old_base in (0,1,0xffffffff,0x12345678,frame+0x41,frame+0x40,random_source.getrandbits(32)):
                for head in (0xffffffff,frame+0x40):
                    registers=[random_source.getrandbits(32) for _ in range(6)]
                    flags=2|(random_source.getrandbits(32)&0x8d5)
                    yield Case(f'normal {function:x} frame{frame:x} oldEBP{old_base:x} parent{head:x}',function,
                        setup(function,frame,old_base,head,registers,flags),source_context=lambda t:t['source'],source_return_pc=lambda t:t['return'])
        for old_base in (0,1,0xffffffff,0x12345678,STACK_TOP+0x80):
            for head in (0xffffffff,STACK_TOP+0x40):
                registers=[random_source.getrandbits(32) for _ in range(6)]
                yield Case(f'noncontinuable allocation prefix {function:x} oldEBP{old_base:x} parent{head:x}',function,
                    setup(function,STACK_TOP,old_base,head,registers,0x8d7,True),expect='halt',source_context=lambda t:t['source'],source_return_pc=lambda t:t['return'])

    # Every arithmetic-status combination is legal at the source boundary.
    # Vary allocation low bytes because the module constructor overwrites CL
    # after forming an interior pointer, retaining the pointer's upper bytes.
    status_bits=(1,4,0x10,0x40,0x80,0x800)
    raw_patterns=(0,1,0xffffffff,0x80000000,0x7fffffff,0xaaaaaaaa,
                  0x55555555,0x01010101,0xfefefefe,0x12345678,
                  0x87654321,0x000000ff,0xffffff00,0x00010000,
                  0xffff0000,0x80808080)
    low_bytes=(0,1,7,0x7f,0x80,0xef,0xf0,0xff)
    for function in (0x502335,0x502369):
        for combination in range(64):
            flags=2|sum(bit for index,bit in enumerate(status_bits)
                        if combination&(1<<index))
            frame=(STACK_BASE+0x1800,STACK_TOP-0x180,STACK_BASE+0x600)[combination%3]
            registers=[raw_patterns[(combination+index*3)%len(raw_patterns)] for index in range(6)]
            old_base=raw_patterns[(combination*7)%len(raw_patterns)]
            head=0xffffffff if combination&1 else frame+0x80
            for failure in (False,True):
                yield Case(f'full CPU {function:x} flags{flags:x} physicalFailure{int(failure)} low{low_bytes[combination%8]:x}',
                    function,setup(function,frame,old_base,head,registers,flags,failure,low_bytes[combination%8]),
                    expect='halt' if failure else 'return',
                    source_context=lambda t:t['source'],source_return_pc=lambda t:t['return'])
        # Isolate each register's raw pattern without coupling it to status bits.
        for index,pattern in enumerate(raw_patterns):
            registers=[pattern]*6
            frame=STACK_BASE+0x1000+index*4
            yield Case(f'raw CPU {function:x} pattern{pattern:x}',function,
                setup(function,frame,pattern,frame+0x44,registers,0x8d7,False,low_bytes[index%8]),
                source_context=lambda t:t['source'],source_return_pc=lambda t:t['return'])
