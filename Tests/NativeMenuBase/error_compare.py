"""Check Swift native shutdown against the actual original error virtual."""
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
from Tests.clawparity.program import claw
import struct


def compare(profiles):
    program=claw()
    for row in profiles:
        m=Uc(UC_ARCH_X86,UC_MODE_32)
        m.mem_map(program.base,(program.size+4095)&~4095)
        for s in program.sections:m.mem_write(s.address,s.data)
        m.mem_map(0x61010000,0x4000);m.mem_map(0x02000000,0x10000);m.mem_map(0x70000000,0x1000)
        word=lambda a:struct.unpack('<I',m.mem_read(a,4))[0]
        def put(a,v):m.mem_write(a,struct.pack('<I',v))
        receiver=row['receiver'];posts=[]
        m.mem_write(receiver,bytes(row['before']))
        put(row['application']+8,receiver);put(row['vtable']+28,0x4b90b0)
        put(row['windowRecord']+4,row['window']);put(row['windowRecord']+12,int(row['windowKind']==2))
        put(0x546d50,0x70000010)
        def hook(machine,address,size,user):
            if address!=0x70000010:return
            sp=machine.reg_read(UC_X86_REG_ESP)
            assert [word(sp+i) for i in (8,12,16)]==[0x10,0,0]
            posts.append(dict(window=word(sp+4),state=list(machine.mem_read(receiver,0x254))))
            machine.reg_write(UC_X86_REG_EAX,1);machine.reg_write(UC_X86_REG_EIP,word(sp));machine.reg_write(UC_X86_REG_ESP,sp+20)
        m.hook_add(UC_HOOK_CODE,hook)
        for code,detail in ((0x8008,0x403),(0x1234,0x5678)):
            for i,value in enumerate((0x70000080,code,detail)):put(0x02008000+4*i,value)
            m.reg_write(UC_X86_REG_ESP,0x02008000);m.reg_write(UC_X86_REG_ECX,row['application'])
            m.emu_start(0x429e10,0x70000080)
            assert list(m.mem_read(receiver,0x254))==row['after']
            assert posts==row['posts']
    print(f'PASS original/Swift application error boundary: {len(profiles)} first-error/window profiles, repeated reports, exact receiver/code/detail and close publication order')
