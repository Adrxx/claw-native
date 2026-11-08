"""Private original-instruction PCM harness. OS/COM/allocator boundaries only."""
import struct
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_GDTR,UC_X86_REG_FS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_CS
from original_v10 import OriginalV10
M,SOUND,SCENE,FILE,ARCHIVE,STREAM,STREAMVT,BUF,VT,DEVICE,DVT=[0x1000000+i*0x1000 for i in range(11)]
SOURCE,FIRST,SECOND,CACHE=0x1070000,0x1080000,0x1084000,0x1090000
TEB,GDT=0x10ed000,0x10ee000
GETS={0x10f0200:0x20,0x10f01c0:0x1c,0x10f0180:0x18}
CREATE,LOCK,UNLOCK,RELEASE,RETRY=0x10f0800,0x10f0820,0x10f0830,0x10f0840,0x10f0900
MASK=0xffffffff
def packed(*v):return struct.pack('<'+'I'*len(v),*(x&MASK for x in v))
class OriginalPCM(OriginalV10):
    def __init__(self,path):
        self.events=[];self.snapshots=[];self.objects={};self.byteSpans={};self.allocPlan=[];self.allocIndex=0;self.frees=[]
        self.createResult=0;self.createdBuffer=BUF;self.getResults={};self.values={0x20:22050,0x1c:0,0x18:0}
        self.seekResults=[];self.readResults=[];self.retryResults=[];self.seekIndex=self.readIndex=self.retryIndex=0
        self.fileData=b'';self.lockResult=0;self.unlockResult=0;self.regions=[FIRST,0,SECOND,0]
        super().__init__(path)
        for index,base,access in((8,0,0x9b),(0x10,0,0x93),(0x18,TEB,0x93)):
            self.u.mem_write(GDT+index,struct.pack('<HHBBBB',0xffff,base&0xffff,(base>>16)&255,access,0xcf,(base>>24)&255))
        self.u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
        for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):self.u.reg_write(reg,0x10)
        self.u.reg_write(UC_X86_REG_CS,8);self.u.reg_write(UC_X86_REG_FS,0x18);self.write_words(TEB,[0xdeadbeef])
        for b in range(BUF,BUF+0x100,4):self.write_words(b,[VT])
        for address,method in GETS.items():self.write_words(VT+method,[address])
        for method,address in((8,RELEASE),(0x2c,LOCK),(0x4c,UNLOCK)):self.write_words(VT+method,[address])
        self.write_words(DEVICE,[DVT]);self.write_words(DVT+0xc,[CREATE]);self.write_words(STREAMVT+8,[RETRY])
    def next(self,kind,default):
        index=getattr(self,kind+'Index');values=getattr(self,kind+'Results');setattr(self,kind+'Index',index+1)
        return values[index]if index<len(values)else default
    def hook(self,u,address,size,user):
        super().hook(u,address,size,user)
        if address not in GETS and address not in(CREATE,LOCK,UNLOCK,RELEASE,RETRY,0x4f63ec,0x4f6428,0x4b4ed0,0x4a7840,0x4a7260):return
        sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
        n=2 if address in GETS else {CREATE:4,LOCK:8,UNLOCK:5,RELEASE:1,RETRY:0,0x4f63ec:1,0x4f6428:1,0x4b4ed0:3,0x4a7840:3,0x4a7260:4}[address]
        a=self.read_words(sp+4,n);ret=0
        pcm=(bytes(u.mem_read(a[1],a[2]))if a[2]else b'',bytes(u.mem_read(a[3],a[4]))if a[4]else b'')if address==UNLOCK else None
        self.snapshots.append(({token:self.read_words(token,14)for token in self.objects},self.read_words(M,32),pcm))
        if address in GETS:
            method=GETS[address];self.events.append(('get',a[0],method));self.write_words(a[1],[self.values[method]]);ret=self.getResults.get(method,0)
        elif address==CREATE:
            desc=self.read_words(a[1],5);assert desc[:2]==[20,0xe0]and desc[3]==0 and a[3]==0
            self.events.append(('create',a[0],bytes(u.mem_read(desc[4],18)),desc[2]));self.write_words(a[2],[self.createdBuffer]);ret=self.createResult
        elif address==LOCK:
            self.events.append(('lock',a[0],a[1],a[2],a[7]));ret=self.lockResult
            for dst,value in zip(a[3:7],self.regions):self.write_words(dst,[value])
        elif address==UNLOCK:self.events.append(('unlock',*a));ret=self.unlockResult
        elif address==RELEASE:self.events.append(('release',a[0]));ret=1
        elif address==RETRY:
            self.events.append(('retry',receiver));ret=self.next('retry',0)
            if ret:self.write_words(receiver+0xc,[self.read_words(receiver+0xc,1)[0]+1])
        elif address==0x4f63ec:
            self.events.append(('allocate',a[0]));assert self.allocIndex<len(self.allocPlan)
            token,size,contents,kind=self.allocPlan[self.allocIndex];self.allocIndex+=1;assert a[0]==size
            ret=token
            if token:
                if kind=='object':self.write_words(token,contents);self.objects[token]=True
                else:u.mem_write(token,contents);self.byteSpans[token]=len(contents)
        elif address==0x4f6428:self.events.append(('free',a[0]));self.frees.append(a[0])
        elif address==0x4a7840:self.events.append(('seek',*a));ret=self.next('seek',0)
        elif address==0x4a7260:
            self.events.append(('read',*a));ret=self.next('read',a[2]);assert a[1]==1 and 0<=ret<=a[2]
            if ret:u.mem_write(a[0],self.fileData[:ret])
        else:assert a[0]==0x53228c;self.events.append(('report',a[1],a[2]))
        cdecl=address in(0x4f63ec,0x4f6428,0x4b4ed0,0x4a7840,0x4a7260)
        u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_EIP,self.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if cdecl else n*4))
