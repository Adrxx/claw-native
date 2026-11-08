"""Focused RedTailSpikes source/native join. No guest code on native side."""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

ACTOR, LOGIC, WORLD, REGISTRY = 0x61000000, 0x61000200, 0x61000400, 0x61000500
HIT, ATTACK, NODE, SLOTS, DESCRIPTOR = 0x61000600, 0x61000640, 0x61000680, 0x61000700, 0x61000800
IDLE = 7
# Observe shared module boundaries, excluding inlined constructor prefixes.
EDGES = [0x4f63ec,0x484680,0x4c7fa0,0x4c8060,0x432c20,0x4dba00,0x4c96b0,0x4dc870,0x4c9e30,0x4843d0,0x42a680,0x4041b0,0x484d90,0x4f6286,0x4f6974,0x4a30e0]

def reviewed_boundary():
    p=claw()
    def read(a,n):
        section=next(s for s in p.sections if s.address<=a and a+n<=s.address+len(s.data))
        return section.data[a-section.address:a-section.address+n]
    direct=[(0x4842e5,0x4842ea,0x4f63ec),(0x484300,0x484305,0x484680),(0x484339,0x48433e,0x4dc870)]
    for pc,continuation,target in direct:
        code=read(pc,5)
        assert code[0]==0xe8 and pc+5==continuation
        assert (continuation+struct.unpack('<i',code[1:])[0]) & 0xffffffff==target
    for pc,slot in [(0x484317,0x10),(0x484324,0x20),(0x484348,0x1c)]:
        code=read(pc,3)
        assert code[0]==0xff and (code[1]>>3)&7==2 and code[2]==slot
    for slot,target in [(0,0x484d90),(4,0x4c9e30),(8,0x4843d0),(12,0x4041b0),(16,0x4c96b0),(28,0x4c96b0),(32,0x4c96b0)]:
        assert struct.unpack('<I',read(0x50f444+slot,4))[0]==target
    return [dict(call=hex(pc),continuation=hex(cont),target=hex(target)) for pc,cont,target in direct]

def inputs(bounds, scale):
    p = claw()
    spans = [(s.address, s.data + bytes(max(0,s.size-len(s.data)))) for s in p.sections if s.name != '.text']
    b = bytearray(0x1000)
    def put(a,v): struct.pack_into('<I',b,a-ACTOR,v & 0xffffffff)
    for a,v in [(ACTOR+4,19),(ACTOR+12,WORLD),(ACTOR+0x6c,LOGIC),(LOGIC+0x10,0x4842b0),(WORLD+0x14,REGISTRY),(HIT+0x10,0x4dc830),(ATTACK+0x10,0x4dc850),(NODE,NODE),(NODE+4,NODE),(NODE+8,0),(NODE+12,0x523604),(NODE+16,IDLE),(SLOTS,DESCRIPTOR)]: put(a,v)
    if bounds:
        put(ACTOR+0x174,ACTOR+0x900)
        for off,v in [(0x18,-9),(0x1c,-11),(0x20,15),(0x24,28)]: put(ACTOR+0x900+off,v)
    spans.append((ACTOR,bytes(b)))
    # Overlay original image data in place before transferring it to either runner.
    patches={0x510020:struct.pack('<I',0xffffffff),0x5262b0:struct.pack('<f',scale),0x537680:struct.pack('<I',NODE),0x53c1e0:struct.pack('<IIIIIII',IDLE,IDLE,SLOTS+4,0,4,0,0),0x5376a0:struct.pack('<IIIIIII',IDLE,IDLE,SLOTS,0,4,0,0)}
    # Declared Memory import bindings; shared by the original physical image
    # and the native owner. None replace game code or constructor returns.
    import_slots=[0x546a90,0x546a7c,0x546a84,0x546aa4,0x546aac,0x546a9c,0x546aa0,0x546b1c,0x546a8c,0x5469c8,0x546a88,0x5469c4,0x546ac0,0x546aa8,0x546a80,0x5469d8]
    patches.update({a:struct.pack('<I',0x710000+i*4) for i,a in enumerate(sorted(import_slots))})
    # SLOTS resides inside the actor's 4 KiB owned setup allocation.
    for i,(a,data) in enumerate(spans):
        data=bytearray(data)
        for at,value in patches.items():
            if a<=at and at+len(value)<=a+len(data): data[at-a:at-a+len(value)]=value
        if a==ACTOR: struct.pack_into('<I',data,SLOTS+4-ACTOR,0x42a680)
        spans[i]=(a,bytes(data))
    actor_span=spans.pop()
    assert actor_span[0]==ACTOR
    for a,n in [(ACTOR,0x1b4),(LOGIC,0x174),(WORLD,0x30),(REGISTRY,0x14),(HIT,0x14),(ATTACK,0x14),(NODE,0x14),(SLOTS,8),(DESCRIPTOR,0x20),(ACTOR+0x900,0x28)]:
        spans.append((a,actor_span[1][a-ACTOR:a-ACTOR+n]))
    return spans

def original(spans):
    p=claw(); u=Uc(UC_ARCH_X86,UC_MODE_32)
    u.mem_map(0,0x1000);u.mem_write(0,struct.pack('<I',0xffffffff))
    u.mem_map(0x400000,0x200000)
    for s in p.sections: u.mem_write(s.address,s.data)
    u.mem_map(ACTOR,0x10000);u.mem_map(0x62000000,0x100000)
    u.mem_map(0x70000000,0x20000)
    for a,b in spans: u.mem_write(a,b)
    u.reg_write(UC_X86_REG_FPCW,0x23f)
    cursor=0x62000000; allocations={};trace=[];snapshots=[]
    def word(a): return struct.unpack('<I',u.mem_read(a,4))[0]
    def put(a,v): u.mem_write(a,struct.pack('<I',v))
    def ret(value,pop):
        sp=u.reg_read(UC_X86_REG_ESP);pc=word(sp)
        u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,pc)
    def hook(uc,pc,size,unused):
        nonlocal cursor
        sp=u.reg_read(UC_X86_REG_ESP)
        if pc in EDGES:
            counts={0x4f63ec:1,0x484680:1,0x4c7fa0:1,0x4c8060:1,0x4dba00:1,0x4dc870:1,0x4c9e30:1,0x4843d0:1,0x4041b0:1,0x484d90:1,0x4f6286:2,0x4f6974:1}
            args=[word(sp+4+i*4) for i in range(counts.get(pc,0))]
            if pc==0x4f6286: args[1]=0  # Synchronous stack-local output address.
            receiver=0 if pc in (0x4f63ec,0x4dc870,0x4a30e0) else u.reg_read(UC_X86_REG_ECX)
            trace.append([pc,receiver,*args])
        if pc==0x4a48e0:
            n=word(sp+4);token=cursor;cursor=(cursor+n+15)&~15
            allocations[token]=n;u.mem_write(token,bytes([0xcc])*n);ret(token,0)
        elif pc==0x4f6286:
            name,out=word(sp+4),word(sp+8)
            assert u.reg_read(UC_X86_REG_ECX)==REGISTRY+16
            assert name in (0x522d54,0x522d48)
            put(out,HIT if name==0x522d54 else ATTACK);ret(1,8)
        elif pc==0x4f6974:
            assert u.reg_read(UC_X86_REG_ECX)==SLOTS and word(sp+4)==0
            ret(word(SLOTS),4)
        elif pc==0x4f6428:
            token=word(sp+4);assert token in allocations;del allocations[token];ret(0,0)
    u.hook_add(UC_HOOK_CODE,hook)
    def run(pc,receiver,args):
        sp=0x70010000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x7001f000,*args))
        u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,receiver)
        u.emu_start(pc,0x7001f000,count=100000)
        assert u.reg_read(UC_X86_REG_EIP)==0x7001f000,hex(u.reg_read(UC_X86_REG_EIP))
    def snapshot(label):
        snapshots.append(dict(label=label,actor=bytes(u.mem_read(ACTOR,0x1b4)).hex(),logic=bytes(u.mem_read(LOGIC,0x174)).hex(),allocations={str(a):bytes(u.mem_read(a,n)).hex() for a,n in allocations.items()},globals={str(a):bytes(u.mem_read(a,n)).hex() for a,n in [(0x537668,0x2c),(0x53c1d8,0x24),(0x537698,0x24)]},trace=list(trace)))
    for cycle in range(2):
        for command in [0,1000,29,30,IDLE]:
            put(LOGIC+0x1c,command);run(0x4842b0,0,[ACTOR]);snapshot(f'{cycle}:{command}')
        helper=word(LOGIC+0x18);run(0x484d90,helper,[1]);put(LOGIC+0x18,0);snapshot(f'{cycle}:retire')
    return snapshots

def main():
    mode,directory=sys.argv[1:];out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    if mode=='prepare':
        (out/'reviewed-boundary.json').write_text(json.dumps(reviewed_boundary(),indent=2))
        profiles=[]
        for i,(bounds,scale) in enumerate([(False,1.25),(True,0.125),(True,1.0/3)]):
            spans=inputs(bounds,scale);profiles.append(dict(spans=[dict(address=a,hex=b.hex()) for a,b in spans]))
            (out/f'original-{i}.json').write_text(json.dumps(original(spans)))
        (out/'inputs.json').write_text(json.dumps(profiles)); print(json.dumps(dict(original_profiles=len(profiles),original_sha256=claw().sha256)))
    else:
        total=0
        for i in range(3):
            expected=json.loads((out/f'original-{i}.json').read_text());actual=json.loads((out/f'native-{i}.json').read_text())
            for e,a in zip(expected,actual,strict=True):
                for field in e:
                    assert e[field]==a[field],f'profile {i} {e["label"]} {field}: original={str(e[field])[:300]} native={str(a[field])[:300]}'
                total+=1
        print(json.dumps(dict(status='pass',comparisons=total,edges=[hex(a) for a in EDGES],unresolved_dependencies=0,canonical_shadow=False,scene_attachment=False)))
if __name__=='__main__':main()
