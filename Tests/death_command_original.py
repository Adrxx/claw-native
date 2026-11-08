"""Private original command harness. Controller/list/clock instructions execute."""
import random,struct
from original_v10 import OriginalV10
from unicorn.x86_const import *
APP,OWNER,PARENT,MAP,PLANE,PLAYER,LOGIC,PRIVATE,CONTAINER,RENDER,WINDOW,KEYBOARD,MOUSE,SOUND,MUSIC,TREE=[0x1000000+i*0x1000 for i in range(16)]
OLDVT,FRAMEVT,RENDERVT=0x10e0000,0x10e0100,0x10e0200
QUERY,DESTRUCT,LEAVE,PRIMARY,FRAME,RENDERFN=[0x10f0000+i*0x100 for i in range(6)]
CLOCK,SETRECT=0x10f1000,0x10f1100
WMPRE,COMMANDPRE,COMMANDHOOK=0x10f2000,0x10f2100,0x10f2200
HEAP,TEB,GDT=0x1050000,0x10ed000,0x10ee000
MASK=0xffffffff
def packed(*v):return struct.pack('<'+'I'*len(v),*(x&MASK for x in v))
COUNTS={QUERY:0,DESTRUCT:1,LEAVE:1,PRIMARY:1,FRAME:1,RENDERFN:2,
WMPRE:3,COMMANDPRE:3,COMMANDHOOK:3,
0x4b55a0:0,0x4b55b0:1,0x4061b0:1,0x4208e0:4,0x48fae0:4,0x48fbe0:4,
0x4d2000:0,0x4d1fd0:0,0x4cb9b0:2,0x4d51f0:1,0x40b5c0:0,0x4dcc40:2,
0x4f5cbd:1,0x429980:0,0x4296f0:4,0x431300:0,0x4b3ab0:0,0x429e10:2,
0x429510:1,0x45ace0:3,0x45b3f0:1,0x45b540:1,0x4298d0:1,0x446ef0:3,0x447050:1,0x447260:1,0x40af60:1}
CDECL={PRIMARY}
class OriginalDeath(OriginalV10):
    def __init__(self,path):
        self.memory={};self.events=[];self.snapshots=[];self.allocations=[];self.heap=HEAP
        self.types=[3];self.queryIndex=0;self.initSuccess=True;self.soundFound=True;self.failAllocation=None
        self.callbackMutation=True;self.frameCalls=0;self.clockReads=0;self.clock=0;self.rng=random.Random(0x803a)
        super().__init__(path)
        for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):
            self.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&65535,(base>>16)&255,access,0xcf,(base>>24)&255))
        self.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
        for r in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):self.u.reg_write(r,0x10)
        self.u.reg_write(UC_X86_REG_CS,8);self.u.reg_write(UC_X86_REG_FS,0x18);self.write_words(TEB,[0xdeadbeef])
        self.write_words(0x546df0,[CLOCK]);self.write_words(0x546d5c,[SETRECT])
    def globals(self):
        return self.read_words(0x537e88,1)+self.read_words(0x532c10,1)+self.read_words(0x537204,1)+self.read_words(0x537200,1)+self.read_words(0x541328,5)+self.read_words(0x537208,2)+self.read_words(0x5430c8,1)+self.read_words(0x5430c4,1)
    def snapshot(self):return ({t:self.read_words(t,n)for t,n in self.memory.items()},self.globals())
    def hook(self,u,address,size,user):
        super().hook(u,address,size,user)
        if address not in COUNTS and address not in(0x4f63ec,0x4f6428,CLOCK,SETRECT):return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX);ret=0;n=COUNTS.get(address,1 if address in(0x4f63ec,0x4f6428)else 0)
        if address==SETRECT:n=5
        args=self.read_words(sp+4,n)
        self.snapshots.append(self.snapshot())
        if address==0x4f63ec:
            self.events.append(('allocate',args[0]));ret=0 if self.failAllocation=='state' and args[0] in(0x154,0x2c8) or len(self.allocations)==self.failAllocation else self.heap
            self.heap+=(max(1024,args[0])+255)&~255;seed=[self.rng.getrandbits(32)for _ in range((args[0]+3)//4)]
            self.allocations.append((ret,args[0],seed))
            if ret:self.write_words(ret,seed);self.memory[ret]=len(seed)
        elif address==0x4f6428:self.events.append(('free',args[0]))
        elif address==CLOCK:self.events.append(('clock',));self.clockReads+=1;ret=(self.clock+self.clockReads*17)&MASK
        else:
            normReceiver=0 if address in CDECL else receiver
            normArgs=args
            if address==SETRECT:normReceiver=args[0];normArgs=args[1:];fn=0x546d5c
            else:fn=address
            self.events.append(('call',fn,normReceiver,tuple(normArgs)))
            ret=self.service(fn,normReceiver,normArgs)
        cdecl=address in CDECL or address in(0x4f63ec,0x4f6428)
        u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if cdecl else n*4))
    def service(self,fn,receiver,args):
        read=self.read_words;write=self.write_words;ret=1
        if fn==QUERY:
            ret=self.types[min(self.queryIndex,len(self.types)-1)];self.queryIndex+=1
        elif fn in(WMPRE,COMMANDPRE,COMMANDHOOK):ret=0
        elif fn==0x4061b0:ret=SOUND if self.soundFound else 0
        elif fn==PRIMARY and self.callbackMutation:
            actor=args[0];write(actor+0x4c,[1000]);write(actor+0x50,[750]);write(read(actor+0x6c,1)[0]+0x1c,[2]);write(PRIVATE+0x18,[0])
        elif fn==FRAME:
            self.frameCalls+=1
            if self.callbackMutation:write(PLAYER+0x4c,[(read(PLAYER+0x4c,1)[0]+7)&MASK])
        elif fn in(0x45ace0,0x446ef0):ret=int(self.initSuccess);write(receiver+0x250,[args[2]])
        elif fn==0x40b5c0:
            write(receiver+4,[0,0,0]);write(receiver+0x38,[0]);ret=receiver
        elif fn in(0x4dcc40,0x429980):write(receiver+8,[0x13579bdf]);ret=receiver
        elif fn==0x4f5cbd:write(receiver,[0x510054,0,0x11,0,0,0,args[0]]);ret=receiver
        elif fn==0x546d5c:write(receiver,args);ret=1
        elif fn==0x4296f0:write(receiver,args)
        elif fn==DESTRUCT or fn in(0x429510,0x4298d0,0x40af60):write(receiver+0x34,[0xdeadcafe]);ret=receiver
        elif fn==0x431300:write(receiver+4,[0x12345678])
        elif fn==0x4b3ab0:write(receiver+4,[0xabcdef12])
        return ret
