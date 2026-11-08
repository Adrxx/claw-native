"""Focused original/native BossHealthMeter named-creation connection.

Run: work/test-env/bin/python Tests/BossHealthMeter/compare.py
Native side has no guest execution. The physical named registry and 320x64
pixel surface are deterministic in-memory resources, not shipped-asset decode.
"""
import ctypes
import fcntl
import os
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

SIZE = 0x2100000
C, W, APP, ENTRY = 0x1000000, 0x1001000, 0x1002000, 0x1003000
IMAGE_MANAGER, COLLECTION, TABLE, IMAGE = 0x1004000, 0x1005000, 0x1006000, 0x1007000
SURFACE, COM, VT, BOSS, NODE, REGISTRY = [0x1008000+i*0x1000 for i in range(6)]
ACTOR, LOGIC, PIXELS = 0x1100000, 0x1101000, 0x1200000
TOP, STOP, FILL, SETRECT = 0x2008000, 0x200f000, 0x68000100, 0x68000200
OWNERS = {
    '0x4c8da0': 'SceneActorRuntime.cpp claw_scene_actor_create_named',
    'construction': 'WorldObjectRuntime.cpp frozen construct/initialize',
    '0x491fa0': 'BossHealthMeterRuntime.cpp claw_boss_health_meter_entry',
    '0x4b9830': 'BossHealthMeterRuntime.cpp claw_boss_health_meter_entry',
    '0x42a450': 'BossSceneServicesRuntime.cpp claw_boss_scene_services_entry',
    '0x4c7970': 'PickupPointsCanonical.cpp claw_pickup_points_canonical_entry',
    '0x4b9ce0': 'SurfaceBlitCanonical.cpp claw_surface_blit_canonical_entry',
    '0x4f6286': 'physical native named registry (BossHealthMeter and GAME_BOSSBAR)',
    '0x4a30e0': 'native truncation of canonical floating-point input',
    '0x546d5c': 'native rectangle transport',
    'surface +0x14': 'native physical rectangle pixel fill',
}
SOURCES = ['Tests/BossHealthMeter/binding.cpp', 'Sources/SceneActorRuntime.cpp',
           'Sources/WorldObjectRuntime.cpp', 'Sources/GameTiming.cpp',
           'Sources/BossHealthMeterRuntime.cpp', 'Sources/BossSceneServicesRuntime.cpp',
           'Sources/PickupPointsCanonical.cpp', 'Sources/SurfaceBlitCanonical.cpp']


def initial(program, depth=8, boss=True):
    mem = bytearray(SIZE)
    for section in program.sections:
        mem[section.address:section.address+len(section.data)] = section.data
    def w(a, *words):
        struct.pack_into('<'+'I'*len(words), mem, a, *(x & 0xffffffff for x in words))
    w(C+12, W); w(C+32, NODE); w(C+40, 1)
    w(W+8, C, 0, IMAGE_MANAGER, REGISTRY); w(W+0x24, 3)
    w(ENTRY, 0, 0, 0, 0, 0x491fa0)
    w(APP+0x78, depth); w(APP+0x30, 0 if depth==8 else 0x100e000)
    w(0x100e000+0x24,0x100f000);w(0x100f000+0x10,20,10,819,619)
    w(0x5371fc, APP); w(0x5349dc, BOSS if boss else 0)
    w(BOSS+0x10c, 200)
    w(COLLECTION+0x14, TABLE); w(COLLECTION+0x64, 0, 0); w(TABLE, IMAGE)
    w(IMAGE+0x20, 4, 5, 0, SURFACE); w(SURFACE+8, COM); w(COM, VT); w(VT+0x14, FILL)
    w(0x54135c, 11, 5); w(0x541368, 3, 2, 3)
    w(0x52c6f0, 0xabba, 0xcddc); w(0x546d5c, SETRECT)
    w(0x54139c, 0, 0, 0, 0)
    assert mem[0x522280:0x522280+15] == b'BossHealthMeter'
    assert mem[0x52c8c8:0x52c8c8+12] == b'GAME_BOSSBAR'
    return mem


def snapshot(read, events, result):
    return {'result': result,
            'actor': list(struct.unpack('<128I', read(ACTOR, 512))),
            'logic': list(struct.unpack('<93I', read(LOGIC, 372))),
            'list': list(struct.unpack('<11I', read(C, 44))),
            'node': list(struct.unpack('<3I', read(NODE, 12))),
            'colors': list(struct.unpack('<2I', read(0x52c6f0, 8))),
            'boss_global': struct.unpack('<I', read(0x5349dc, 4))[0],
            'pixels': hashlib.sha256(read(PIXELS, 320*64*4)).hexdigest(),
            'events': list(events)}


class Original:
    def __init__(self, memory, missing=0):
        self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        self.u.mem_map(0, SIZE); self.u.mem_write(0, bytes(memory))
        self.u.mem_map(0x68000000, 0x1000)
        self.events, self.allocations, self.missing = [], 0, missing
        self.u.hook_add(UC_HOOK_CODE, self.hook)
    def get(self, a): return struct.unpack('<I', self.u.mem_read(a, 4))[0]
    def put(self, a, v): self.u.mem_write(a, struct.pack('<I', v & 0xffffffff))
    def ret(self, result, pop):
        sp=self.u.reg_read(UC_X86_REG_ESP); target=self.get(sp)
        self.u.reg_write(UC_X86_REG_EAX, result)
        self.u.reg_write(UC_X86_REG_ESP, sp+4+pop)
        self.u.reg_write(UC_X86_REG_EIP, target)
    def hook(self, u, pc, size, user):
        sp=u.reg_read(UC_X86_REG_ESP)
        def arg(i): return self.get(sp+4+4*i)
        if pc==0x491fa0 and self.get(LOGIC+0x1c)==0:
            actor=arg(0); node=self.get(actor+0x68)
            self.events.append([2,actor,node,self.get(C+0x1c),self.get(node+8),self.get(LOGIC+0x1c),0,0])
        if pc==0x4f63ec:
            count=arg(0); token=ACTOR+self.allocations*0x1000
            assert self.allocations<2 and count==(0x1b4 if not self.allocations else 0x174)
            self.allocations+=1;self.events.append([1,token,count,0,0,0,0,0]);self.ret(token,0)
        elif pc==0x4f6286:
            receiver=u.reg_read(UC_X86_REG_ECX); name=bytes(u.mem_read(arg(0),32)).split(b'\0')[0]
            if receiver==REGISTRY+16 and name==b'BossHealthMeter': value=0 if self.missing==0x522280 else ENTRY
            elif receiver==IMAGE_MANAGER+16 and name==b'GAME_BOSSBAR': value=0 if self.missing==0x52c8c8 else COLLECTION
            else: raise AssertionError(('unexpected registry request',hex(receiver),name))
            self.put(arg(1),value);self.ret(bool(value),8)
        elif pc==SETRECT:
            for i in range(4):self.put(arg(0)+i*4,arg(i+1))
            self.ret(1,20)
        elif pc==FILL:
            a=[arg(i) for i in range(6)]
            assert a[0]==COM and a[2:5]==[0,0,0x1000400] and self.get(a[5])==100
            rect=[self.get(a[1]+4*i) for i in range(4)];color=self.get(a[5]+80)
            self.events.append([3,*rect,color,0,0])
            for y in range(rect[1],rect[3]):
                for x in range(rect[0],rect[2]):
                    assert 0<=x<320 and 0<=y<64
                    self.put(PIXELS+(y*320+x)*4,color)
            self.ret(0,24)
        elif pc>=0x68000000: raise AssertionError(('unexpected physical service',hex(pc)))
    def invoke(self, f, receiver=0, args=()):
        self.put(TOP,STOP)
        for i,a in enumerate(args):self.put(TOP+4+4*i,a)
        self.u.reg_write(UC_X86_REG_ESP,TOP);self.u.reg_write(UC_X86_REG_ECX,receiver)
        self.u.emu_start(f,STOP,count=100000)
        assert self.u.reg_read(UC_X86_REG_EIP)==STOP
        return self.u.reg_read(UC_X86_REG_EAX)
    def step(self, phase):
        value=self.invoke(0x4c8da0,C,(0,0,0,0,0x522280,0x200000)) if not phase else self.invoke(0x491fa0,0,(ACTOR,))
        return snapshot(lambda a,n:bytes(self.u.mem_read(a,n)),self.events,value)


class Native:
    def __init__(self, library, memory, missing=0):
        self.lib=library;self.mem=(ctypes.c_ubyte*SIZE).from_buffer(memory)
        library.join_start(self.mem,SIZE,missing)
    def put(self,a,v): struct.pack_into('<I',self.mem,a,v & 0xffffffff)
    def step(self,phase):
        value=self.lib.join_step(phase)
        if self.lib.join_fault():
            raise RuntimeError(f'native fault {self.lib.join_fault()} at {self.lib.join_fault_address():#x}')
        n=self.lib.join_event_count(); raw=ctypes.string_at(self.lib.join_events(),n*32)
        events=[list(struct.unpack_from('<8I',raw,i*32)) for i in range(n)]
        return snapshot(lambda a,n:bytes(self.mem[a:a+n]),events,value)


def build():
    compiler = subprocess.check_output(['xcrun', '--find', 'clang++'], text=True).strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    headers = ['Sources/ClawRuntime.h', 'Sources/ClawRuntime.hpp', 'Sources/SceneActorRuntime.h',
               'Sources/WorldObjectRuntime.h', 'Sources/GameTiming.h']
    captured = {p: (ROOT / p).read_bytes() for p in SOURCES + headers}
    flags = ['-isysroot', sdk, '-std=c++17', '-O1', '-dynamiclib']
    digest = hashlib.sha256()
    for path, content in captured.items():
        digest.update(path.encode() + b'\0' + content)
    digest.update(json.dumps(flags).encode())
    digest.update(subprocess.check_output([compiler, '--version']))
    digest.update(subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-version']))
    key = digest.hexdigest()
    cache = ROOT / 'work/build/boss-health-meter-join' / key
    cache.mkdir(parents=True, exist_ok=True)
    library = cache / 'join.dylib'
    with (cache / 'build.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not library.exists():
            for path, content in captured.items():
                destination = cache / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            temporary = cache / 'join.tmp.dylib'
            subprocess.run([compiler, *flags, '-I', str(cache / 'Sources'),
                            *[str(cache / p) for p in SOURCES], '-o', str(temporary)], check=True)
            os.replace(temporary, library)
    lib = ctypes.CDLL(str(library))
    lib.join_start.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
    lib.join_events.restype = ctypes.c_void_p
    return lib, key


def compare(expected,actual,label):
    if expected != actual:
        differences={k:{'original':expected[k],'native':actual[k]} for k in expected if expected[k]!=actual[k]}
        raise AssertionError((label,differences))


def main():
    program=claw();folder=ROOT/'work/boss-health-meter-join';folder.mkdir(parents=True,exist_ok=True)
    original_only='--original-only' in sys.argv
    lib,key=(None,None) if original_only else build()
    profiles=[]
    for depth,initial_boss,missing in [(8,True,0),(16,True,0),(24,True,0),(32,True,0),(8,False,0),(8,True,0x52c8c8),(8,True,0x522280)]:
        mem=initial(program,depth,initial_boss);original=Original(mem,missing)
        original.invoke(0x4a7ef0)
        native=None if original_only else Native(lib,bytearray(mem),missing)
        for phase,health,boss in [(0,200,initial_boss),(1,200,True),(2,81,True),(3,0,True),(4,300,True),(5,-10,True),(6,50,False),(7,50,True)]:
            if phase and (missing==0x522280 or not initial_boss):break
            original.put(BOSS+0x10c,health);original.put(0x5349dc,BOSS if boss else 0)
            if native:native.put(BOSS+0x10c,health);native.put(0x5349dc,BOSS if boss else 0)
            if phase==7:
                original.put(IMAGE+0x2c,0)
                if native:native.put(IMAGE+0x2c,0)
            expected=original.step(phase)
            if phase==0 and missing!=0x522280:
                assert expected['events'][2]==[2,ACTOR,NODE,1,ACTOR,0,0,0]
                assert expected['logic'][7]==5 and expected['actor'][0x64//4]==0x2704
                assert expected['actor'][2]&0x20000
                assert expected['actor'][0x10c//4]==(200 if initial_boss else 0)
            if native:compare(expected,native.step(phase),f'{depth}/{initial_boss}/{missing:#x}/{phase}')
            profiles.append({'depth':depth,'initial_boss':initial_boss,'missing':hex(missing),'phase':phase,'result':expected['result'],'draws':sum(e[0]==3 for e in expected['events'])})
    controls=[]
    if lib:
        for missing in [0x491fa0,0x42a450,0x4c7970,0x4b9ce0,0x4f6286,0x546d5c,0x4a30e0,FILL]:
            native=Native(lib,initial(program),missing)
            try:
                native.step(0);native.step(1)
            except RuntimeError:
                assert lib.join_fault_address()==missing
                controls.append(hex(missing))
            else:raise AssertionError(('missing owner accepted',hex(missing)))
    report={'status':'original-pass' if original_only else 'pass','command':'work/test-env/bin/python Tests/BossHealthMeter/compare.py','reference_sha256':program.sha256,'source_digest':key,'paired_observations':len(profiles),'profiles':profiles,'missing_owner_faults':controls,'wire_object_boss_stager_owners':OWNERS,'scope':'Focused source join with in-memory physical resource; no app build, shipped resource decode, or device acceptance.'}
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
