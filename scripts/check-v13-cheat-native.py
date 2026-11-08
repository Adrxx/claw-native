"""Focused app-layout checks for v1.3 attack and peg composition."""
import ctypes as C
import importlib.util
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/v13/cheat-native';OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('host',ROOT/'scripts/check-v13-enemy-death-sound.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
ENTRY='claw_v13_cheat_native_entry'
class Host(host.Host):
    def __init__(self,lib):
        super().__init__(lib)
        self.regions.append((0x58010000,C.create_string_buffer(0x400)))
    def call(self,user,p):
        q=p.contents;f=q.function;a=tuple(q.arguments[:q.argumentCount])
        if f in (0x4c79e0,0x4c82a0,0x4c8220,0x48c8a0):
            self.calls.append((f,q.receiver,a));return 1
        if f==0x41d750:return 1000
        if f in (0x49e470,0x49e4b0):return self.invoke('claw_level_one_batch_pegs_and_elevators_01_entry',f,q.receiver,*a)
        if f==0x42af70:
            self.calls.append((f,q.receiver,a));return 1
        return super().call(user,p)

def attack(lib):
    count=0
    for code in range(20):
      for facing in (0,1):
       for stale in (0x80000000,0x123,0x7fffffff):
        results=[]
        for enabled in (0,1):
            h=Host(lib);actor=h.alloc(0x400);logic=h.alloc(0x200);state=h.alloc(0x200)
            owner=h.alloc(0x100);animations=h.alloc(0x100)
            h.put(0x537204,h.alloc(0x100))
            h.put(actor+0xc,owner);h.put(owner+0x2c,animations);h.put(owner+0x24,h.alloc(0x200));h.put(owner+8,h.alloc(0x100))
            h.put(actor+0x6c,logic);h.put(logic+0x14,state)
            h.put(actor+0x138,stale,23,0x7fffff80,47);h.put(state,facing);h.put(0x58010000,enabled)
            try:h.invoke(ENTRY,0x41de90,0,actor,logic,state,code)
            except AssertionError as e:raise AssertionError((code,facing,hex(stale),enabled,h.calls[-5:])) from e
            results.append([h.get(actor+0x138+i*4) for i in range(4)])
        old,new=results
        # Melee arms replace the stale left bound; other arms retain it.
        mirrors=facing==0 and (code in (1,3,4,7,8,13) or stale!=0x80000000)
        expected=old.copy();index=0 if mirrors else 2
        expected[index]=(expected[index]+(-320 if mirrors else 320))&0xffffffff
        assert new==expected,(code,facing,stale,old,new,expected)
        count+=1
    return count

def pegs(lib):
    count=0
    for function in (0x49d330,0x49d620,0x49d860,0x49e4e0):
      for cheat in (0,1):
       for profile in (0,1):
        h=Host(lib);actor=h.alloc(0x400);logic=h.alloc(0x200);player=h.alloc(0x400);owner=h.alloc(0x100);manager=h.alloc(0x100)
        h.put(actor+0xc,owner);h.put(owner+0x28,manager);h.put(manager+0x30,1)
        h.put(actor+0x6c,logic);h.put(0x537e88,player);h.put(player+8,16);h.put(player+0x80,actor)
        h.put(0x58010004,cheat);h.put(0x53725c,profile)
        state=1005 if function in (0x49d330,0x49e4e0) else 5
        h.put(logic+0x1c,state);h.put(actor+0x1a4,1);h.put(actor+0x148,25)
        assert h.invoke(ENTRY,function,0,actor)==1
        if cheat:assert h.get(logic+0x1c)==state,(function,cheat,profile)
        else:assert h.get(logic+0x1c)==(1006 if function==0x49e4e0 else 1004 if function==0x49d330 else 1002),(function,h.get(logic+0x1c))
        if function in (0x49d330,0x49e4e0):assert h.get(actor+0xd0)==0x80
        count+=1
        # Fresh source initialization also traverses the field-layout and
        # shared timing-helper boundary, independently of the cheat guard.
        h.put(0x537960,h.alloc(0x100));h.put(logic+0x1c,0)
        h.put(logic+0x10,0x49e7b0)
        assert h.invoke(ENTRY,function,0,actor)==1
        expected=1004 if function==0x49d330 else (5 if profile else 1006) if function==0x49e4e0 else 5
        assert h.get(logic+0x1c)==expected,(function,profile,h.get(logic+0x1c))
        if function==0x49e4e0:assert h.get(logic+0xbc)==750
        count+=1
    return count

def bounce(lib):
    h=Host(lib);enemy=h.alloc(0x500);owner=h.alloc(0x200);record=h.alloc(0x100);sprite=h.alloc(0x300)
    h.put(enemy+0xc,owner,record);h.put(enemy+0x12c,sprite);h.put(enemy+0x2fc,32,0x11)
    h.put(0x5801000c,1)
    for i in range(2):
        h.invoke(ENTRY,0x43f120,enemy,0)
        assert [h.get(0x58010000+j) for j in (16,20,24)]==[i+1]*3
        assert h.get(enemy+0x300)==0x10
    return 2

load=float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]);assert load<16,load
sources=['V13CheatNativeAdapter.cpp','LevelOnePlayerActions02Runtime.cpp','LevelOneClawStates01Runtime.cpp','LevelOnePlayerActions03Runtime.cpp','V13CheatPegsRuntime.cpp','LevelOneBatchPegsAndElevators01Runtime.cpp','LevelOneBatchEnemyCallee03Runtime.cpp']
path=OUT/'cheats.dylib'
subprocess.run(['clang++','-std=c++17','-O2','-ffp-contract=off','-dynamiclib','-I',str(ROOT/'Sources'),*[str(ROOT/'Sources'/s) for s in sources],'-o',str(path)],check=True)
lib=C.CDLL(str(path))
result={'status':'pass','check':'v13-cheat-native','attack_pairs':attack(lib),'peg_cases':pegs(lib),'bounce_calls':bounce(lib)}
(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
