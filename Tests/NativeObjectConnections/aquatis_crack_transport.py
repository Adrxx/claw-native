"""Original/native AquatisCrack owner comparison. No game-body fixtures."""
from __future__ import annotations
import argparse
import json
import struct
import subprocess
from pathlib import Path
from Tests.clawparity.program import claw
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX

ROOT=Path(__file__).resolve().parents[2]
ACTOR,LOGIC,WORLD=0x30000000,0x30000400,0x30001000
REGISTRY,IMAGES,SOUNDS,CYCLES=0x30002000,0x30002100,0x30002200,0x30002300
HIT,ATTACK,IMAGE,FRAMES,FRAME=0x30003000,0x30003100,0x30005000,0x30005100,0x30005200
GLOW,QUAKE1,QUAKE2,QUAKE3,QUAKE4,QUAKE5=0x30004000,0x30004100,0x30004200,0x30004300,0x30004400,0x30004500
SEQUENCE_TABLE,RECORD,STRING,DELAY_STRING,NAME_NODE,BOSS=0x30004600,0x30004700,0x30006000,0x30006100,0x30006600,0x30007000
HEAP,STACK,STOP=0x62000000,0x02008000,0x0200f000
HASH='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
# Cdecl/stdcall have no receiver. Normalize only stack output cell tokens.
NO_RECEIVER={0x4f63ec,0x4dc870,0x4c9e30,0x4f6428}
ARITIES={0x4f63ec:1,0x4068f0:1,0x4c96b0:0,0x4dc870:1,0x4c9e30:1,0x406520:1,0x4041b0:1,0x484d90:1,0x4f6428:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x406290:0,0x4dba00:1,0x4f6286:2,0x4f6974:1,0x4061b0:1,0x406240:0,0x458530:0,0x4c8220:1,0x4c82a0:1,0x406b10:0,0x406c40:0}
OBSERVED={0x4f63ec,0x4068f0,0x4c96b0,0x4dc870,0x4c9e30,0x406520,0x4041b0,0x484d90,0x4f6428,0x4c7fa0,0x4c8060,0x4c7970,0x406290,0x4dba00,0x4f6286,0x4f6974,0x4061b0,0x406240,0x458530,0x4c8220,0x4c82a0,0x406b10,0x406c40}

def fixture():
    p=claw();assert p.sha256==HASH
    image=bytearray(p.size)
    for section in p.sections:image[section.address-p.base:section.address-p.base+len(section.data)]=section.data
    for site,target,continuation in [(0x406435,0x4f63ec,0x40643a),(0x406450,0x4068f0,0x406455),(0x406489,0x4dc870,0x40648e)]:
        assert image[site-p.base]==0xe8 and site+5==continuation
        assert continuation+struct.unpack_from('<i',image,site-p.base+1)[0]==target
    expected_slots=[0x484d90,0x4c9e30,0x406520,0x4041b0,0x4c96b0,0x406cb0,0x4bb030,0x4c96b0,0x4c96b0]
    assert list(struct.unpack_from('<9I',image,0x50b21c-p.base))==expected_slots
    data=bytearray(0x8000)
    def put(address,value):
        region,offset=(image,address-p.base) if p.base<=address<p.base+p.size else (data,address-ACTOR)
        struct.pack_into('<I',region,offset,value)
    values={ACTOR+0xc:WORLD,ACTOR+0x6c:LOGIC,ACTOR+0x18c:ACTOR,LOGIC+0x10:0x406400,
        WORLD+0x10:IMAGES,WORLD+0x14:REGISTRY,WORLD+0x28:SOUNDS,WORLD+0x2c:CYCLES,
        HIT+0x10:0x4dc830,ATTACK+0x10:0x4dc850,IMAGE+0x14:FRAMES,FRAMES:FRAME,
        FRAME+0x18:3,FRAME+0x1c:5,FRAME+0x20:32,FRAME+0x24:48,
        ACTOR+0x4c:280,ACTOR+0x148:175,GLOW+0xc:SEQUENCE_TABLE,GLOW+0x10:1,
        SEQUENCE_TABLE:RECORD,RECORD+0x18:200,RECORD+0x1c:42,
        0x534874:BOSS,0x537668+0x18:NAME_NODE,NAME_NODE:NAME_NODE,NAME_NODE+4:NAME_NODE,
        NAME_NODE+8:0,NAME_NODE+0xc:0x523148,NAME_NODE+0x10:1001,
        0x5376a0:0,0x5376a4:1100,0x5376a8:0x30008000,0x5376b0:4,
        0x534890:0,0x534894:1100,0x534898:0x3000a000,0x5348a0:4,
        0x537210:1234,0x5430c4:16,0x510020:0xffffffff,
        STRING:1,STRING+4:7,STRING+8:32}
    for a,v in values.items():put(a,v)
    data[STRING+12-ACTOR:STRING+20-ACTOR]=b'ES_IDLE\0'
    delay_name=bytes(image[0x5234fc-p.base:]).split(b'\0',1)[0]
    for a,v in [(DELAY_STRING,1),(DELAY_STRING+4,len(delay_name)),(DELAY_STRING+8,48)]:put(a,v)
    data[DELAY_STRING+12-ACTOR:DELAY_STRING+13+len(delay_name)-ACTOR]=delay_name+b'\0'
    lifecycle=bytearray(1101*4);dispatch=bytearray(1101*4)
    struct.pack_into('<I',lifecycle,1001*4,STRING+12)
    struct.pack_into('<I',dispatch,1001*4,0x406b10)
    struct.pack_into('<I',lifecycle,1002*4,DELAY_STRING+12)
    struct.pack_into('<I',dispatch,1002*4,0x406c40)
    spans=[(ACTOR,0x1b4),(LOGIC,0x174),(WORLD,0x30),(REGISTRY,0x14),(IMAGES,0x14),
        (SOUNDS,0x14),(CYCLES,0x14),(HIT,0x14),(ATTACK,0x14),(IMAGE,0x6c),(FRAMES,4),
        (FRAME,0x28),(GLOW,0x14),(QUAKE1,0x14),(QUAKE2,0x14),(QUAKE3,0x14),(QUAKE4,0x14),
        (QUAKE5,0x14),(SEQUENCE_TABLE,4),(RECORD,48),(STRING,48),(DELAY_STRING,64),(NAME_NODE,0x14),(BOSS,0x500)]
    regions=[{'token':p.base,'bytes':list(image)}]+[{'token':token,'bytes':list(data[token-ACTOR:token-ACTOR+count])} for token,count in spans]
    regions += [{'token':0x30008000,'bytes':list(lifecycle)},{'token':0x3000a000,'bytes':list(dispatch)}]
    return {'sha256':HASH,'regions':regions,'commands':[0,1000,29,30,1001,1002,1002,1001],'allocator_fill':0xcc}

class Original:
    def __init__(self,inputs):
        self.uc=Uc(UC_ARCH_X86,UC_MODE_32);self.uc.mem_map(0,4096);self.uc.mem_write(0,struct.pack('<I',0xffffffff));self.uc.mem_map(0x01ff0000,0x21000)
        mapped=set()
        for region in inputs['regions']:
            token,blob=region['token'],bytes(region['bytes']);start,end=token&~4095,(token+len(blob)+4095)&~4095
            for page in range(start,end,4096):
                if page not in mapped:self.uc.mem_map(page,4096);mapped.add(page)
            self.uc.mem_write(token,blob)
        self.uc.mem_map(HEAP,0x10000);self.uc.mem_map(0x3000c000,0x1000)
        self.fill=inputs['allocator_fill'];self.next=HEAP;self.calls=[];self.allocations=[];self.freed=[];self.uc.hook_add(UC_HOOK_CODE,self.step)
    def word(self,a):return struct.unpack('<I',self.uc.mem_read(a,4))[0]
    def put(self,a,v):self.uc.mem_write(a,struct.pack('<I',v))
    def returning(self,v,pop):
        sp=self.uc.reg_read(UC_X86_REG_ESP);self.uc.reg_write(UC_X86_REG_EAX,v);self.uc.reg_write(UC_X86_REG_ESP,sp+4+pop);self.uc.reg_write(UC_X86_REG_EIP,self.word(sp))
    def step(self,uc,address,size,user):
        if address==STOP:uc.emu_stop();return
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address in OBSERVED:
            arguments=[self.word(sp+4+4*i) for i in range(ARITIES[address])]
            if address==0x4f6286:arguments[1]=0xffffffff
            self.calls.append({'function':address,'receiver':0 if address in NO_RECEIVER else uc.reg_read(UC_X86_REG_ECX),'arguments':arguments})
        if address==0x4a48e0:
            count=self.word(sp+4);token=self.next;self.next+=(count+15)&~15;self.allocations.append([token,count]);self.uc.mem_write(token,bytes([self.fill])*count);self.returning(token,0)
        elif address==0x4f6286:
            key,out=self.word(sp+4),self.word(sp+8);value={0x522d54:HIT,0x522d48:ATTACK,0x523598:IMAGE,0x523588:GLOW,0x523574:QUAKE1,0x523560:QUAKE2,0x52354c:QUAKE3,0x523538:QUAKE4,0x523524:QUAKE5}[key];self.put(out,value);self.calls[-1]['output']=self.word(out);self.returning(1,8)
        elif address==0x4f6974:
            slot=uc.reg_read(UC_X86_REG_ECX)
            self.returning(self.word(slot),4)
        elif address==0x4f6428:self.freed.append(self.word(sp+4));self.returning(0,0)
    def invoke(self,function,receiver,args):
        self.uc.reg_write(UC_X86_REG_ESP,STACK);self.uc.reg_write(UC_X86_REG_ECX,receiver);self.uc.mem_write(STACK,struct.pack('<'+'I'*(len(args)+1),STOP,*args));self.uc.emu_start(function,STOP,count=2000000)
        if self.uc.reg_read(UC_X86_REG_EIP)!=STOP:raise AssertionError('original instruction budget')
    def snapshot(self):
        return {'boss':list(self.uc.mem_read(BOSS,0x500)),'actor':list(self.uc.mem_read(ACTOR,0x1b4)),'logic':list(self.uc.mem_read(LOGIC,0x174)),'allocations':[[t,c,list(self.uc.mem_read(t,c))] for t,c in self.allocations],'globals':[[a,self.word(a)] for a in [0x537684,0x537688,0x53768c,0x537690,0x5376b8,0x5348a8]],'calls':self.calls.copy()}
    def run(self,commands):
        output=[]
        for index,command in enumerate(commands):
            if index==5:
                helper=self.word(LOGIC+0x18);self.put(helper+0x60,1234);self.put(helper+0x64,4000)
            if index==6:self.put(0x537210,5234)
            if index==7:self.put(BOSS+0x4ec,2)
            self.put(LOGIC+0x1c,command);self.calls=[];self.invoke(0x406400,0,[ACTOR]);output.append(self.snapshot())
        helper=self.word(LOGIC+0x18);self.calls=[];self.invoke(0x484d90,helper,[1]);self.put(LOGIC+0x18,0);retired=self.snapshot();self.put(LOGIC+0x1c,0);self.calls=[];self.invoke(0x406400,0,[ACTOR]);return {'steps':output,'retired':retired,'reallocated':self.snapshot()}

def compare(expected,actual,path):
    if type(expected) is not type(actual):raise AssertionError(f'{path}: type differs')
    if isinstance(expected,dict):
        if expected.keys()!=actual.keys():raise AssertionError(f'{path}: keys differ')
        for key in expected:compare(expected[key],actual[key],f'{path}.{key}')
    elif isinstance(expected,list):
        if len(expected)!=len(actual):raise AssertionError(f'{path}: length {len(expected)} != {len(actual)}')
        for index,(left,right) in enumerate(zip(expected,actual)):compare(left,right,f'{path}[{index}]')
    elif expected!=actual:raise AssertionError(f'{path}: original {expected} != native {actual}')

def main():
    p=argparse.ArgumentParser();p.add_argument('--native');p.add_argument('--out',default='work/native-object-connections/aquatis_crack/transport');a=p.parse_args();out=ROOT/a.out;out.mkdir(parents=True,exist_ok=True)
    inputs=fixture();(out/'inputs.json').write_text(json.dumps(inputs));original=Original(inputs).run(inputs['commands']);(out/'original.json').write_text(json.dumps(original,indent=2))
    if a.native:
        run=subprocess.run([a.native,str(out/'inputs.json')],text=True,capture_output=True)
        if run.returncode:raise AssertionError('native check failed: '+run.stderr[-7000:])
        native=json.loads(run.stdout);(out/'native.json').write_text(json.dumps(native,indent=2));compare(original['steps'],native['steps'],'steps');compare(original['retired'],native['retired'],'retired');compare(original['reallocated'],native['reallocated'],'reallocated');assert all(native['controls'].values()),native['controls'];print(json.dumps({'status':'pass','comparisons':len(original['steps'])+2,'controls':native['controls'],'sha256':HASH}))
    else:print(json.dumps({'status':'original-captured','snapshots':len(original['steps'])+2}))
if __name__=='__main__':main()
