"""Private original registry harness; real factory, map hash/equality and lookup."""
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10

def packed(*x):return struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x))
class RegistryHarness:
    scene,registry,buckets,nodes,strings,objects,query,output=0x1000000,0x1001000,0x1010000,0x1020000,0x1060000,0x1080000,0x1002000,0x1003000
    def __init__(self,exe):
        self.machine=OriginalV10(exe);self.u=self.machine.u;self.u.mem_map(0,4096)
        self.machine.write_words(self.scene+0x14,[self.registry])
        self.machine.write_words(self.registry,[0x513b60]);self.machine.write_words(self.registry+0xc,[self.scene])
        # Initialized empty hash bucket array + free associations substitute only
        # backing allocations. Original map node construction/insertion executes.
        self.machine.write_words(self.registry+0x10+4,[self.buckets,17,0,self.nodes,0,512])
        self.u.mem_write(self.buckets,bytes(17*4))
        for i in range(512):self.machine.write_words(self.nodes+i*16,[self.nodes+(i+1)*16 if i<511 else 0,0,0,0])
        self.object_cursor=self.objects;self.string_cursor=self.strings;self.entries=[];self.side_calls=[];self.destroyed=[]
        instructions=Cs(CS_ARCH_X86,CS_MODE_32).disasm(bytes(self.u.mem_read(0x401000,0x123b)),0x401000)
        self.side_entries={int(i.op_str,16)for i in instructions if i.mnemonic=='call' and i.op_str.startswith('0x')}
        self.u.hook_add(UC_HOOK_CODE,self.host)
    def text(self,address):return bytes(self.u.mem_read(address,1024)).split(b'\0',1)[0]
    def returned(self,pop,result):
        u=self.u;m=self.machine;sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
        u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
    def host(self,u,address,size,user):
        m=self.machine;sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
        if address==0x4d6340:
            callback,name,flags=m.read_words(sp+4,3)
            self.entries.append(dict(callback=callback,nameAddress=name,name=self.text(name).decode('ascii'),flags=flags,
                                     entryAddress=self.object_cursor,metadataId=m.read_words(self.registry+0x1c,1)[0]))
        elif address==0x4f63ec:
            amount=m.read_words(sp+4,1)[0];assert amount==0x174,hex(amount)
            result=self.object_cursor;self.object_cursor+=0x180;assert self.object_cursor<0x10ef000
            self.u.mem_write(result,bytes([0xa5])*0x174);self.returned(0,result)
        elif address==0x4f66cc:
            source=m.read_words(sp+4,1)[0];text=self.text(source);result=self.string_cursor+12
            m.write_words(result-12,[1,len(text),len(text)]);u.mem_write(result,text+b'\0');m.write_words(receiver,[result])
            self.string_cursor+=len(text)+32;assert self.string_cursor<self.objects;self.returned(4,receiver)
        elif address==0x4c80c0:
            self.destroyed.append((receiver,m.read_words(sp+4,1)[0]));self.returned(4,receiver)
        elif address in self.side_entries:
            self.side_calls.append((m.read_words(sp,1)[0]-5,address));self.returned(0,1)
    def populate(self):
        self.machine.call(0x401000,0,packed(self.scene));return self.entries
    def find(self,name,seed=0x99):
        if isinstance(name,str):name=name.encode()
        self.u.mem_write(self.query,name+b'\0');self.machine.write_words(self.output,[seed])
        result=self.machine.call(0x4f6286,self.registry+0x10,packed(self.query,self.output))
        return result,self.machine.read_words(self.output,1)[0]
    def register(self,name,callback,flags):
        if isinstance(name,str):name=name.encode()
        self.u.mem_write(self.query,name+b'\0')
        return self.machine.call(0x4d6340,self.registry,packed(callback,self.query,flags))
