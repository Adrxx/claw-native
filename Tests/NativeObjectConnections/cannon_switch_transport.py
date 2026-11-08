"""Finite shared-host CannonSwitch transport comparison, using the original PE.

Native game bodies are never replaced. The original's physical string/resource
maps and malloc are controlled inputs; both executions receive identical bytes.
"""
from __future__ import annotations
import argparse, json, pathlib, struct, subprocess
from Tests.clawparity.program import claw

ROOT=pathlib.Path(__file__).resolve().parents[2]
ACTOR=0x03000000; LOGIC=0x03001000; WORLD=0x03002000
HIT=0x03003000; ATTACK=0x03003100; IMAGE=0x03004000
FRAMES=0x03004100; FRAME=0x03004200; ANIMATION=0x03005000
RECORDS=0x03005100; RECORD=0x03005200; SOUND=0x03006000
LIFECYCLE=0x03007000; STATES=0x03007100; NODE=0x03008000
CALLBACK=0x415350; HELPER=0x62000000
# Nested inlined helpers have no independent native host boundary. Compare the
# actual shared edges, including all physical lookups, in their original order.
OBSERVED={0x4f63ec,0x4a48e0,0x415840,0x4c7fa0,0x4c8060,0x4c8160,
          0x4c81b0,0x4c7970,0x4f6286,0x465450,0x4dba00,0x4dc870,
          0x4f6974,0x4c9e30,0x415470,0x4159b0,0x415a60,
          0x4c8220,0x4c82a0,0x4c96b0,0x4041b0,0x484d90,0x4f6428}
# (stack argument count, whether ECX is a semantic receiver). The lifecycle
# stdcall no-op has its independently reviewed receiver-bearing exception.
ABI={a:(1,True) for a in [0x415840,0x4c7fa0,0x4c8060,0x4c7970,0x4dba00,
                          0x4f6974,0x4c9e30,0x415470,0x4c8220,0x4c82a0,0x4041b0,0x484d90]}
ABI.update({a:(0,True) for a in [0x4c81b0,0x465450,0x4159b0,0x415a60,0x4c96b0]})
ABI.update({0x4c8160:(2,True),0x4f6286:(2,True)})
ABI.update({a:(1,False) for a in [0x4f63ec,0x4a48e0,0x4dc870,0x4f6428]})
assert set(ABI)==OBSERVED
IMPORTS=[0x546a90,0x546a7c,0x546a84,0x546aa4,0x546aac,0x546a9c,0x546aa0,
         0x546b1c,0x546a8c,0x5469c8,0x546a88,0x5469c4,0x546ac0,0x546aa8,
         0x546a80,0x5469d8]

def validate_metadata():
    p=claw()
    def read(a,n):
        section=next(s for s in p.sections if s.address<=a and a+n<=s.address+s.size)
        return section.data[a-section.address:a-section.address+n]
    direct=[(0x415385,0x41538a,0x4f63ec),(0x4153a0,0x4153a5,0x415840),
            (0x4153d9,0x4153de,0x4dc870),(0x41598b,0x415990,0x465450)]
    for site,continuation,target in direct:
        instruction=read(site,5)
        assert instruction[0]==0xe8 and site+5==continuation
        assert (continuation+struct.unpack('<i',instruction[1:])[0])&0xffffffff==target
    virtual=[(0x4153b7,0x4153ba,0x10),(0x4153c4,0x4153c7,0x20),(0x4153e8,0x4153eb,0x1c)]
    for site,continuation,slot in virtual:
        instruction=read(site,3)
        assert continuation==site+3 and instruction[0]==0xff and instruction[1]&0x38==0x10 and instruction[2]==slot
    table=list(struct.unpack('<9I',read(0x50ba64,36)))
    assert table==[0x484d90,0x4c9e30,0x415470,0x4041b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0]
    # The original registers idle/tick; activation 4159f0 is internal to idle.
    assert struct.pack('<I',0x4159b0) in read(0x4156d0,24)
    assert struct.pack('<I',0x415a60) in read(0x4157d0,24)
    return {'sha256':p.sha256,'direct':direct,'virtual':virtual,'vtable':table,
            'state_methods':[0x4159b0,0x415a60]}

def fixture():
    p=claw(); segments=[]
    for s in p.sections:
        if s.name in ('.rdata','.data','.idata'):
            segments.append({'address':s.address,'bytes':list(s.data.ljust(s.size,b'\0'))})
    def add(a,n):
        segments.append({'address':a,'bytes':[0]*n})
    for a,n in [(ACTOR,0x1b4),(LOGIC,0x174),(WORLD,0x80),(HIT,0x14),(ATTACK,0x14),
                (IMAGE,0x6c),(FRAMES,12),(FRAME,0x30),(ANIMATION,0x14),
                (RECORDS,4),(RECORD,0x30),(SOUND,0x14),(LIFECYCLE,8),
                (STATES,8),(NODE,0x60),(0x03009000,0x524)]:add(a,n)
    for a in [0x0300a000,0x0300a100,0x0300a200,0x0300a300]:add(a,0x14)
    def put(a,v):
        for s in segments:
            if s['address']<=a and a+4<=s['address']+len(s['bytes']):
                s['bytes'][a-s['address']:a-s['address']+4]=list(struct.pack('<I',v));return
        raise AssertionError(hex(a))
    for a,v in [(ACTOR+0xc,WORLD),(ACTOR+0x18c,ACTOR),(ACTOR+0x6c,LOGIC),(LOGIC+0x10,CALLBACK),
                (WORLD+0x10,0x0300a000),(WORLD+0x14,0x0300a100),
                (WORLD+0x28,0x0300a200),(WORLD+0x2c,0x0300a300),
                (HIT+0x10,0x4dc830),(ATTACK+0x10,0x4dc850),
                (IMAGE+0x14,FRAMES),(IMAGE+0x64,0),(IMAGE+0x68,2),
                (FRAMES,FRAME),(FRAMES+4,FRAME),(FRAMES+8,FRAME),
                (FRAME+0x18,7),(FRAME+0x1c,9),(FRAME+0x20,19),(FRAME+0x24,23),
                (ANIMATION+0xc,RECORDS),(ANIMATION+0x10,1),(RECORDS,RECORD),
                (RECORD+0x8,3),(RECORD+0xc,0),(RECORD+0x10,0),(RECORD+0x14,0),
                (SOUND+0x10,0x0300b000),(0x53774c,0x03009000),
                (0x537668+0x18,NODE),(NODE,NODE+0x20),(NODE+4,NODE+0x40),(NODE+8,25),
                (NODE+0x20+8,0),(NODE+0x20+0xc,0x523148),(NODE+0x20+0x10,1),
                (NODE+0x40+8,0),(NODE+0x40+0xc,0x524604),(NODE+0x40+0x10,2),
                (0x5376a0,1),(0x5376a4,2),(0x5376a8,LIFECYCLE),(0x5376b0,4),
                (LIFECYCLE,0x523148),(LIFECYCLE+4,0x524604),
                (0x534c60,1),(0x534c64,2),(0x534c68,STATES),(0x534c70,4),
                (STATES,0x4159b0),(STATES+4,0x415a60),
                (0x510020,0xffffffff),(0x537210,0),(0x532c0c,0),(0x532c10,80)]:put(a,v)
    for i,a in enumerate(IMPORTS):put(a,0x710000+i*8)
    actions=[{'command':0,'boss':0,'delta':0,'done':0},
             {'command':1000,'boss':0,'delta':1,'done':0},
             {'command':29,'boss':0,'delta':0,'done':0},
             {'command':30,'boss':0,'delta':0,'done':0},
             {'command':1,'boss':0,'delta':1,'done':0},
             {'command':1,'boss':1,'delta':1,'done':0},
             {'command':2,'boss':0,'delta':1,'done':0},
             {'command':2,'boss':0,'delta':100,'done':1}]
    return {'segments':segments,'actions':actions,'imports':{str(a):0x710000+i*8 for i,a in enumerate(IMPORTS)}}


def original(data, allocation_failure=False):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_FS_BASE
    p=claw();u=Uc(UC_ARCH_X86,UC_MODE_32);pages=set()
    def map_span(a,n):
        for q in range(a&~4095,(a+n+4095)&~4095,4096):
            if q not in pages:u.mem_map(q,4096);pages.add(q)
    for s in p.sections:map_span(s.address,s.size);u.mem_write(s.address,s.data)
    map_span(0,4096);map_span(0x01ff0000,0x21000);map_span(HELPER,0x10000)
    for s in data['segments']:map_span(s['address'],len(s['bytes']));u.mem_write(s['address'],bytes(s['bytes']))
    def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
    put(0,0xffffffff);alloc=[];calls=[];envelopes=[];cursor=HELPER
    resources={0x522d54:HIT,0x522d48:ATTACK,0x524664:IMAGE,0x524648:ANIMATION,0x52462c:SOUND}
    def ret(v,pop=0):
        sp=u.reg_read(UC_X86_REG_ESP);pc=get(sp);u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,pc)
    def hook(_u,address,size,_):
        nonlocal cursor
        if allocation_failure and address==0x5022b5:
            u.emu_stop();return
        sp=u.reg_read(UC_X86_REG_ESP)
        if address in OBSERVED:
            calls.append(address);argc,receiver=ABI[address]
            arguments=[get(sp+4+4*i) for i in range(argc)]
            envelope={'function':address,'receiver':u.reg_read(UC_X86_REG_ECX) if receiver else 0,
                      'argumentCount':argc,'arguments':arguments}
            if address==0x4f6286:
                envelope['outputCellBefore']=get(arguments[1])
                arguments[1]=0 # synchronous borrowed output cell, normalized
            envelopes.append(envelope)
        if address==0x4a48e0:
            if allocation_failure:ret(0);return
            n=get(sp+4);token=cursor;cursor=(cursor+n+15)&~15;alloc.append((token,n));u.mem_write(token,b'\xcc'*n);ret(token)
        elif address==0x4f6286:
            key=get(sp+4);out=get(sp+8)
            if key not in resources:raise AssertionError(('resource',hex(key)))
            put(out,resources[key]);ret(1,8)
        elif address==0x4f6974:ret(get(u.reg_read(UC_X86_REG_ECX)),4)
        elif address==0x4f6428:
            token=get(sp+4);alloc[:]=[(a,n) for a,n in alloc if a!=token];ret(0)
    u.hook_add(UC_HOOK_CODE,hook)
    def invoke(a,receiver=0,args=()):
        put(0x02008000,0x0200f000)
        for i,v in enumerate(args):put(0x02008004+4*i,v)
        u.reg_write(UC_X86_REG_ESP,0x02008000);u.reg_write(UC_X86_REG_ECX,receiver)
        u.emu_start(a,0x0200f000,count=200000)
        assert u.reg_read(UC_X86_REG_EIP)==(0x5022b5 if allocation_failure else 0x0200f000),hex(u.reg_read(UC_X86_REG_EIP))
    def snapshot():
        spans=[(ACTOR,0x1b4),(LOGIC,0x174),(0x537668,0x2c),(0x534c58,0x24),(0x537698,0x24),(0x03009000,0x524),(0x5430c4,4),(0x532c0c,8),(0x53774c,4)]
        spans+=alloc
        return {'bytes':{str(a):list(u.mem_read(a,n)) for a,n in spans},'helper':get(LOGIC+0x18),'calls':list(calls),'envelopes':list(envelopes)}
    results=[]
    for action in data['actions']:
        put(LOGIC+0x1c,action['command']);put(0x5430c4,action['delta']);put(0x03009000+0x518,action['boss'])
        if action['done']:put(ACTOR+0x1a4,1);put(ACTOR+0x19c,0)
        calls.clear();envelopes.clear();invoke(CALLBACK,args=(ACTOR,))
        if allocation_failure:return {'address':u.reg_read(UC_X86_REG_EIP),'command':get(LOGIC+0x1c),'helper':get(LOGIC+0x18)}
        results.append(snapshot())
    calls.clear();envelopes.clear();invoke(0x484d90,get(LOGIC+0x18),(1,));put(LOGIC+0x18,0);results.append(snapshot());put(LOGIC+0x1c,0)
    # The helper-only owner preserves the actor's real secondary allocations.
    # Recreate therefore exercises their reset/bind bodies, not replacements.
    calls.clear();envelopes.clear();invoke(CALLBACK,args=(ACTOR,));results.append(snapshot())
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native');parser.add_argument('--emit-input');parser.add_argument('--output',default='work/native-object-connections/cannon-switch-transport')
    args=parser.parse_args();metadata=validate_metadata();data=fixture();out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2))
    path=pathlib.Path(args.emit_input) if args.emit_input else out/'input.json';path.write_text(json.dumps(data))
    if not args.native:return
    expected=original(data);failure=original(data,True);(out/'original.json').write_text(json.dumps(expected));(out/'original-allocation-failure.json').write_text(json.dumps(failure))
    run=subprocess.run([args.native,str(path)],check=True,text=True,capture_output=True);actual=json.loads(run.stdout);(out/'native.json').write_text(json.dumps(actual))
    assert actual['fault'] is None,actual['fault']
    assert actual['allocationFailure']==failure,('allocation failure',actual.get('allocationFailure'),failure)
    assert len(actual['snapshots'])==len(expected),('snapshot count',len(actual['snapshots']),len(expected))
    for i,(got,want) in enumerate(zip(actual['snapshots'],expected)):
        assert got['helper']==want['helper'],('helper',i,hex(got['helper']),hex(want['helper']))
        assert got['calls']==want['calls'],('calls',i,[hex(a) for a in got['calls']],[hex(a) for a in want['calls']])
        assert got['envelopes']==want['envelopes'],('call envelopes',i,got['envelopes'],want['envelopes'])
        assert got['bytes'].keys()==want['bytes'].keys(),('allocation identities',i,sorted(got['bytes']),sorted(want['bytes']))
        for address in want['bytes']:
            g,w=got['bytes'][address],want['bytes'][address]
            if g!=w:
                offset=next((j for j,(a,b) in enumerate(zip(g,w)) if a!=b),min(len(g),len(w)))
                raise AssertionError(('bytes',i,hex(int(address)),hex(offset),g[offset:offset+12],w[offset:offset+12]))
    assert all(actual['controls'].values()),actual['controls']
    result={'status':'pass','comparisons':len(expected),'controls':actual['controls'],'faults':0,'unresolved_dependencies':0}
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':main()
