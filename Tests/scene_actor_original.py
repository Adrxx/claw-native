"""Private scene dispatcher harness; heap/gameplay/registry/destructor services."""
from pathlib import Path
import random,struct
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_GDTR,UC_X86_REG_FS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_CS
from original_v10 import OriginalV10
CONTAINER,PARENT,ENTRY,REGISTRY,OWNER,MAP,PLANE,IMAGE,FRAMES=[0x1000000+i*0x1000 for i in range(9)]
ACTOR_BASE,LOGIC_BASE,HEAP=0x1010000,0x1030000,0x1060000
CALLBACK=0x10f1000;CLOCK=0x10f1200;TEB,GDT=0x10ed000,0x10ee000
SPAWNFLAG=0x10eb000
MASK=0xffffffff
def packed(*v):return struct.pack('<'+'I'*len(v),*(x&MASK for x in v))
class OriginalScene(OriginalV10):
    def __init__(self,path):
        self.events=[];self.snapshots=[];self.allocations=[];self.heap=HEAP;self.found=True;self.clock=0;self.clockReads=0
        self.memory={};self.callbackMode=0;self.rng=random.Random(0x4c8be0);self.interactionCalls=0;self.failAllocation=None
        super().__init__(path)
        for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):
            self.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
        self.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
        for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):self.u.reg_write(reg,0x10)
        self.u.reg_write(UC_X86_REG_CS,8);self.u.reg_write(UC_X86_REG_FS,0x18);self.write_words(TEB,[0xdeadbeef])
        self.write_words(0x546df0,[CLOCK])
        self.write_words(SPAWNFLAG,[0])
        # External gameplay adapter which makes one genuine nested creator
        # call. The shim is synthetic; every scene instruction stays original.
        code=b'\x83\x3d'+packed(SPAWNFLAG)+b'\x00'+b'\x75\x2d'
        code+=b'\xc7\x05'+packed(SPAWNFLAG,1)+b'\x60'
        code+=b'\x6a\x00\x68'+packed(ENTRY)+b'\x6a\x64\x68'+packed(350)+b'\x68'+packed(320)+b'\x6a\x63'
        code+=b'\xb9'+packed(CONTAINER)+b'\xb8'+packed(0x4c8be0)+b'\xff\xd0\x61\xb8\x01\x00\x00\x00\xc3'
        self.u.mem_write(CALLBACK,code)
    def mutate(self,actor):
        a=self.read_words(actor,128);logic=a[0x6c//4];l=self.read_words(logic,93)
        l[0x44//4]=(l[0x44//4]+1)&MASK
        if self.callbackMode==1:
            a[2]|=0x10000
        elif self.callbackMode==2:
            a[2]|=0x20000;a[0x64//4]=(a[0x64//4]-13)&MASK
        elif self.callbackMode==3 and l[7]!=29:
            a[2]|=0x90000
        self.write_words(actor,a);self.write_words(logic,l)
    def hook(self,u,address,size,user):
        super().hook(u,address,size,user)
        if address not in(0x4f63ec,0x4f6428,0x4f6286,0x4c9be0,0x4a35f0,CALLBACK,CLOCK,0x46c860,0x4d1fd0,0x4d2000,0x4c9390):return
        self.snapshots.append(({t:self.read_words(t,n)for t,n in self.memory.items()},self.read_words(0x5430d0,1),self.read_words(0x5430f0,5),self.read_words(0x5430d8,5),self.read_words(0x5430c8,1),self.read_words(0x5430c4,1),self.read_words(0x537208,3)))
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
        n={0x4f63ec:1,0x4f6428:1,0x4f6286:2,0x4c9be0:1,0x4a35f0:1,CALLBACK:1}.get(address,0)
        a=self.read_words(sp+4,n);ret=0
        if address==0x4f63ec:
            count=a[0];token=0 if len(self.allocations)==self.failAllocation else self.heap;self.heap+=(max(count,512)+255)&~255
            capacity=128 if count==0x1b4 else (count+3)//4
            seed=[self.rng.getrandbits(32)for _ in range(capacity)]
            self.events.append(('allocate',count));self.allocations.append((token,count,seed));ret=token
            if token:self.write_words(token,seed);self.memory[token]=capacity
        elif address==0x4f6428:self.events.append(('free',a[0]))
        elif address==0x4f6286:
            self.events.append(('call',address,receiver,(a[0],)));self.write_words(a[1],[ENTRY if self.found else 0]);ret=int(self.found)
        elif address==CLOCK:self.events.append(('clock',));self.clockReads+=1;ret=self.clock
        else:
            logicalReceiver=0 if address==CALLBACK else receiver
            self.events.append(('call',address,logicalReceiver,tuple(a)))
            if address==CALLBACK:
                self.mutate(a[0]);ret=1
                if self.callbackMode==4:return
            elif address==0x4c9be0:self.write_words(receiver+0x168,[0xfedcba98]);ret=receiver
            elif address==0x4c9390:
                # Actual pair body executes in scheduling tests; the observer
                # only logs its invocation. Rectangles/masks are bounded below.
                self.interactionCalls+=1;return
        cdecl=address in(0x4f63ec,0x4f6428,0x4a35f0,CALLBACK,CLOCK)
        u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if cdecl else n*4))
