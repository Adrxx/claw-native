"""Original/native AquatisDynamite owner comparison. No game-body fixtures."""
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
STRING,NAME_NODE,BOSS=0x30006000,0x30006600,0x30007000
FACTORY,NODES,AMMO,SCENE,SCENE_LOGIC,PLAYER=0x30000a00,0x30000c00,0x30003200,0x30009000,0x30009400,0x30009800
HEAP,STACK,STOP=0x62000000,0x02008000,0x0200f000
HASH='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
# Cdecl/stdcall have no receiver. Normalize only stack output cell tokens.
NO_RECEIVER={0x4f63ec,0x4dc870,0x4c9e30,0x4f6428}
ARITIES={0x4f63ec:1,0x4071a0:1,0x4c96b0:0,0x4dc870:1,0x4c9e30:1,0x406ef0:1,0x4041b0:1,0x484d90:1,0x4f6428:1,0x4c7fa0:1,0x4c8060:1,0x4c7970:1,0x465450:0,0x4dba00:1,0x4f6286:2,0x4f6974:1,0x458570:0,0x4c82a0:1,0x407310:0,0x4c8da0:6,0x4f51c5:1,0x68001000:5}
OBSERVED=set(ARITIES)
NO_RECEIVER.add(0x68001000)

def fixture():
    p=claw();assert p.sha256==HASH
    image=bytearray(p.size)
    for section in p.sections:image[section.address-p.base:section.address-p.base+len(section.data)]=section.data
    for site,target,continuation in [(0x406e05,0x4f63ec,0x406e0a),(0x406e20,0x4071a0,0x406e25),(0x406e59,0x4dc870,0x406e5e)]:
        assert image[site-p.base]==0xe8 and site+5==continuation
        assert continuation+struct.unpack_from('<i',image,site-p.base+1)[0]==target
    expected_slots=[0x484d90,0x4c9e30,0x406ef0,0x4041b0,0x4c96b0,0x407310,0x4bb030,0x4c96b0,0x4c96b0]
    assert list(struct.unpack_from('<9I',image,0x50b244-p.base))==expected_slots
    for site,modrm,slot,continuation in [(0x406e37,0x50,0x10,0x406e3a),(0x406e44,0x52,0x20,0x406e47),(0x406e68,0x52,0x1c,0x406e6b)]:
        assert image[site-p.base:site-p.base+3]==bytes([0xff,modrm,slot]) and site+3==continuation
    # Original scene initialization registers AmmoPowerup -> 471100.
    assert image[0x401ad2-p.base]==0x68 and struct.unpack_from('<I',image,0x401ad3-p.base)[0]==0x522894
    assert image[0x401ad7-p.base]==0x68 and struct.unpack_from('<I',image,0x401ad8-p.base)[0]==0x471100
    # Original Aquatis dynamite state registration stores the genuine idle body.
    for site in [0x40712c,0x40715e,0x407192]:
        assert image[site-p.base:site-p.base+2]==bytes([0xc7,0x07]) and struct.unpack_from('<I',image,site-p.base+2)[0]==0x458570
    # Genuine operator-new exhaustion calls the original handler lookup.
    site=0x4f640e
    assert image[site-p.base]==0xe8 and site+5+struct.unpack_from('<i',image,site-p.base+1)[0]==0x5022b5
    data=bytearray(0xc000)
    def put(address,value):
        region,offset=(image,address-p.base) if p.base<=address<p.base+p.size else (data,address-ACTOR)
        struct.pack_into('<I',region,offset,value)
    values={ACTOR+0xc:WORLD,ACTOR+0x6c:LOGIC,ACTOR+0x18c:ACTOR,LOGIC+0x10:0x406dd0,
        LOGIC+0xc:WORLD,LOGIC+0x2c:20,LOGIC+0x30:250,LOGIC+0x34:30,LOGIC+0x38:180,
        WORLD+8:FACTORY,FACTORY+0xc:WORLD,FACTORY+0x28:1,AMMO+0x10:0x471100,
        0x537e88:SCENE,SCENE+0x6c:SCENE_LOGIC,SCENE_LOGIC+0x14:PLAYER,PLAYER+0x78:80,0x546d5c:0x68001000,
        WORLD+0x10:IMAGES,WORLD+0x14:REGISTRY,WORLD+0x28:SOUNDS,WORLD+0x2c:CYCLES,
        HIT+0x10:0x4dc830,ATTACK+0x10:0x4dc850,IMAGE+0x14:FRAMES,FRAMES:FRAME,
        FRAME+0x18:3,FRAME+0x1c:5,FRAME+0x20:32,FRAME+0x24:48,
        ACTOR+0x4c:280,ACTOR+0x50:175,
        0x534874:BOSS,BOSS+0x4b8:1,0x537668+0x18:NAME_NODE,NAME_NODE:NAME_NODE,NAME_NODE+4:NAME_NODE,
        NAME_NODE+8:0,NAME_NODE+0xc:0x523148,NAME_NODE+0x10:1001,
        0x5376a0:0,0x5376a4:1100,0x5376a8:0x3000d000,0x5376b0:4,
        0x5348c0:0,0x5348c4:1100,0x5348c8:0x3000f000,0x5348d0:4,
        0x537210:1234,0x5430c4:16,0x510020:0xffffffff,
        STRING:1,STRING+4:7,STRING+8:32}
    for a,v in values.items():put(a,v)
    data[STRING+12-ACTOR:STRING+20-ACTOR]=b'LS_IDLE\0'
    lifecycle=bytearray(1101*4);dispatch=bytearray(1101*4)
    struct.pack_into('<I',lifecycle,1001*4,STRING+12)
    struct.pack_into('<I',dispatch,1001*4,0x458570)
    
    spans=[(ACTOR,0x1b4),(LOGIC,0x174),(WORLD,0x30),(REGISTRY,0x14),(IMAGES,0x14),
        (SOUNDS,0x14),(CYCLES,0x14),(HIT,0x14),(ATTACK,0x14),(IMAGE,0x6c),(FRAMES,4),
        (FRAME,0x28),(STRING,48),(NAME_NODE,0x14),(BOSS,0x500),(FACTORY,0x30),(NODES,0x100),(AMMO,0x14),(SCENE,0x1b4),(SCENE_LOGIC,0x174),(PLAYER,0x100)]
    regions=[{'token':p.base,'bytes':list(image)}]+[{'token':token,'bytes':list(data[token-ACTOR:token-ACTOR+count])} for token,count in spans]
    regions += [{'token':0x3000d000,'bytes':list(lifecycle)},{'token':0x3000f000,'bytes':list(dispatch)}]
    return {'sha256':HASH,'regions':regions,'commands':[0,1000,29,30,1001],'allocator_fill':0xcc}

class Original:
    def __init__(self,inputs,exhaust=False):
        self.uc=Uc(UC_ARCH_X86,UC_MODE_32);self.uc.mem_map(0,4096);self.uc.mem_write(0,struct.pack('<I',0xffffffff));self.uc.mem_map(0x01ff0000,0x21000)
        mapped=set()
        for region in inputs['regions']:
            token,blob=region['token'],bytes(region['bytes']);start,end=token&~4095,(token+len(blob)+4095)&~4095
            for page in range(start,end,4096):
                if page not in mapped:self.uc.mem_map(page,4096);mapped.add(page)
            self.uc.mem_write(token,blob)
        self.uc.mem_map(HEAP,0x10000);self.uc.mem_map(0x68001000,0x1000);self.uc.mem_map(0x3000c000,0x1000)
        self.exhaust=exhaust;self.exhaustion_malloc=False;self.exhaustion_handler=False;self.fill=inputs['allocator_fill'];self.next=HEAP;self.calls=[];self.allocations=[];self.freed=[];self.nodes=[];self.uc.hook_add(UC_HOOK_CODE,self.step)
    def word(self,a):return struct.unpack('<I',self.uc.mem_read(a,4))[0]
    def put(self,a,v):self.uc.mem_write(a,struct.pack('<I',v))
    def returning(self,v,pop):
        sp=self.uc.reg_read(UC_X86_REG_ESP);self.uc.reg_write(UC_X86_REG_EAX,v);self.uc.reg_write(UC_X86_REG_ESP,sp+4+pop);self.uc.reg_write(UC_X86_REG_EIP,self.word(sp))
    def step(self,uc,address,size,user):
        if address==STOP:uc.emu_stop();return
        if self.exhaust and address==0x5022b5:
            self.exhaustion_handler=True;uc.emu_stop();return
        sp=uc.reg_read(UC_X86_REG_ESP)
        if address in OBSERVED:
            arguments=[self.word(sp+4+4*i) for i in range(ARITIES[address])]
            if address==0x4f6286:arguments[1]=0xffffffff
            if address==0x68001000:arguments[0]=0xffffffff
            self.calls.append({'function':0x546d5c if address==0x68001000 else address,'receiver':0 if address in NO_RECEIVER else uc.reg_read(UC_X86_REG_ECX),'arguments':arguments})
        if address==0x4a48e0 and self.exhaust:
            assert self.word(sp+4)==0x54
            self.exhaustion_malloc=True;self.returning(0,0)
        elif address==0x4a48e0:
            count=self.word(sp+4);token=self.next;self.next+=((512 if count==0x1b4 else count)+15)&~15;self.allocations.append([token,count]);self.uc.mem_write(token,bytes([self.fill])*count);self.returning(token,0)
        elif address==0x4f6286:
            key,out=self.word(sp+4),self.word(sp+8);value={0x522d54:HIT,0x522d48:ATTACK,0x5235d0:IMAGE,0x522894:AMMO}[key];self.put(out,value);self.calls[-1]['output']=self.word(out);self.returning(1,8)
        elif address==0x4f51c5:
            assert uc.reg_read(UC_X86_REG_ECX)==FACTORY+0x10
            node=NODES+len(self.nodes)*0x10;tail=self.word(FACTORY+0x18)
            self.put(node,0);self.put(node+4,tail);self.put(node+8,self.word(sp+4))
            if tail:self.put(tail,node)
            else:self.put(FACTORY+0x14,node)
            self.put(FACTORY+0x18,node);self.put(FACTORY+0x1c,self.word(FACTORY+0x1c)+1)
            self.nodes.append(node);self.returning(node,4)
        elif address==0x68001000:
            values=[self.word(sp+4+i*4) for i in range(5)]
            for i,v in enumerate(values[1:]):self.put(values[0]+i*4,v)
            self.returning(1,20)
        elif address==0x4f6974:
            slot=uc.reg_read(UC_X86_REG_ECX)
            self.returning(self.word(slot),4)
        elif address==0x4f6428:self.freed.append(self.word(sp+4));self.returning(0,0)
    def invoke(self,function,receiver,args):
        self.uc.reg_write(UC_X86_REG_ESP,STACK);self.uc.reg_write(UC_X86_REG_ECX,receiver);self.uc.mem_write(STACK,struct.pack('<'+'I'*(len(args)+1),STOP,*args));self.uc.emu_start(function,STOP,count=2000000)
        if self.uc.reg_read(UC_X86_REG_EIP)!=STOP:raise AssertionError('original instruction budget')
    def snapshot(self):
        return {'boss':list(self.uc.mem_read(BOSS,0x500)),'actor':list(self.uc.mem_read(ACTOR,0x1b4)),'logic':list(self.uc.mem_read(LOGIC,0x174)),'allocations':[[t,c,list(self.uc.mem_read(t,c))] for t,c in self.allocations],'factory':list(self.uc.mem_read(FACTORY,0x30)),'nodes':[[n,list(self.uc.mem_read(n,12))] for n in self.nodes],'globals':[[a,self.word(a)] for a in [0x5376b8,0x5348d8]],'calls':self.calls.copy()}
    def check_exhaustion(self):
        self.uc.reg_write(UC_X86_REG_ESP,STACK);self.uc.reg_write(UC_X86_REG_ECX,0)
        self.uc.mem_write(STACK,struct.pack('<II',STOP,ACTOR));self.uc.emu_start(0x406dd0,STOP,count=200000)
        assert self.exhaustion_malloc and self.exhaustion_handler and not self.allocations
        assert self.uc.reg_read(UC_X86_REG_EIP)==0x5022b5
    def run(self,commands):
        output=[]
        for command in commands:
            self.put(LOGIC+0x1c,command);self.calls=[];self.invoke(0x406dd0,0,[ACTOR]);output.append(self.snapshot())
        timed=[]
        for now,active,health in [(1234,1,80),(1400,0,80),(1984,0,80),(2734,0,81)]:
            self.put(0x537210,now);self.put(BOSS+0x4c8,active);self.put(PLAYER+0x78,health);self.calls=[]
            helper=self.word(LOGIC+0x18);self.invoke(self.word(self.word(helper)+0x14),helper,[]);timed.append(self.snapshot())
        helper=self.word(LOGIC+0x18);self.calls=[];self.invoke(0x484d90,helper,[1]);self.put(LOGIC+0x18,0);retired=self.snapshot();self.put(LOGIC+0x1c,0);self.calls=[];self.invoke(0x406dd0,0,[ACTOR]);return {'steps':output,'timed':timed,'retired':retired,'reallocated':self.snapshot()}

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
    p=argparse.ArgumentParser();p.add_argument('--native');p.add_argument('--out',default='work/native-object-connections/aquatis_dynamite/transport');a=p.parse_args();out=ROOT/a.out;out.mkdir(parents=True,exist_ok=True)
    inputs=fixture();Original(inputs,exhaust=True).check_exhaustion();(out/'inputs.json').write_text(json.dumps(inputs));original=Original(inputs).run(inputs['commands']);(out/'original.json').write_text(json.dumps(original,indent=2))
    if a.native:
        run=subprocess.run([a.native,str(out/'inputs.json')],text=True,capture_output=True)
        if run.returncode:raise AssertionError('native check failed: '+run.stderr[-7000:])
        native=json.loads(run.stdout);(out/'native.json').write_text(json.dumps(native,indent=2));compare(original['steps'],native['steps'],'steps');compare(original['timed'],native['timed'],'timed');compare(original['retired'],native['retired'],'retired');compare(original['reallocated'],native['reallocated'],'reallocated');assert all(native['controls'].values()),native['controls']
        result={'status':'pass','comparisons':len(original['steps'])+len(original['timed'])+2,
                'controls':native['controls'],'sha256':HASH,
                'callback_commands':inputs['commands'],
                'timed_boundary':'separate original virtual +0x14 -> 0x407310; LS_IDLE dispatches 0x458570'}
        (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    else:print(json.dumps({'status':'original-captured','snapshots':len(original['steps'])+2}))
if __name__=='__main__':main()
