#!/usr/bin/env python3
"""Native composition checks, separate from original-binary v1.3 admission.

Startup, save restoration, score progression and the legacy typed HUD execute
the actual app sources. Contact/bomb controls isolate adapter routing; actual
retained magic/knife bodies check child publication. Neither replaces the
separate v1.3 original-binary admissions.
"""
import ctypes as C
import importlib.util
import json
import os
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('overlay_checks', ROOT / 'scripts/check-v13-enemy-death-sound.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Host, U32 = module.Host, module.U32
WORK = ROOT / 'work/v13-lives-boss-check'
START = 'claw_v13_player_startup_compat_entry'
BOSS = 'claw_v13_lives_boss_compat_entry'
SCORE = 'claw_v13_score_compat_entry'

BRIDGE = r'''
#include "V13LivesBoss.h"
#include <cstring>
#include <vector>
// Controlled retained entries, deliberately not certified original bodies.
static uint32_t controlled(uint32_t f,uint32_t r,const uint32_t*a,uint32_t n,ClawHost*h,uint32_t*out,uint32_t id) {
    auto get=[&](uint32_t t){uint32_t v;std::memcpy(&v,h->bytes(h->user,t,4),4);return v;};
    auto put=[&](uint32_t t,uint32_t v){std::memcpy(h->bytes(h->user,t,4),&v,4);};
    if(id>=6) {
        // Receiver points to a child chosen by the fixture. This models the
        // retained parent's physical initializer callback, including ABI.
        uint32_t child=get(r), logic=get(child+0x6c), callback=get(logic+0x10);
        put(child+0x104,31);
        ClawCall call{}; call.function=callback;call.receiver=0;call.arguments[0]=child;call.argumentCount=1;
        h->call(h->user,&call);
        // A non-initializer callback must not have its damage overwritten.
        put(child+0x104,23);call.function=0x76543;h->call(h->user,&call);
    } else {
        bool ctor=f==0x47e2d0||f==0x453df0||f==0x49fbf0||f==0x404990||f==0x445ef0;
        uint32_t actor=a[0];
        if(ctor) put(r+0xc,actor);
        if(ctor||!get(get(actor+0x6c)+0x1c)) put(actor+0x104,31);
    }
    *out=0xabc000+id;return n==(id>=6?0u:1u);
}
#define CONTROL(name,id) extern "C" uint32_t name(uint32_t f,uint32_t r,const uint32_t*a,uint32_t n,ClawHost*h,uint32_t*out){return controlled(f,r,a,n,h,out,id);}
CONTROL(claw_level_two_raux_core_entry,1)
CONTROL(claw_level_four_katherine_core_springboard_01_entry,2)
CONTROL(claw_level_six_wolvington_core_01_entry,3)
CONTROL(claw_level_twelve_aquatis_core_01_entry,4)
CONTROL(claw_level_eight_gabriel_bomb_01_entry,5)
CONTROL(claw_level_six_wolvington_states_01_entry,6)
CONTROL(claw_level_thirteen_red_tail_attacks_01_entry,7)

struct HUD {
    std::vector<uint32_t> words=std::vector<uint32_t>(0x10000);
    uint32_t next=0x4000,bad=0,sounds=0;
    ClawCheckpointTimerGlobals globals{};ClawCheckpointTimerContext shared{};
    ClawPlayerHUDGlobals extra{};ClawPlayerHUDContext context{};
    static uint32_t*lookup(void*u,uint32_t t,uint32_t n){auto&h=*(HUD*)u;return t%4==0&&t/4+n<=h.words.size()?h.words.data()+t/4:nullptr;}
    uint32_t&at(uint32_t t){return words.at(t/4);}
    static uint32_t dep(ClawPlayerHUDContext*,const ClawPlayerHUDCall*c,void*u){
        auto&h=*(HUD*)u;
        switch(c->function){
        case 0x4f63ec:{uint32_t p=h.next;h.next+=c->arguments[0]+16;return p;}
        case 0x490590: h.at(c->receiver+4)=c->arguments[2];return 0;
        case 0x4c7970:case 0x4c79e0:case 0x490c40:case 0x490760:case 0x4c82a0:return 0;
        case 0x4f6286:return 0x3000;
        case 0x4b45f0:++h.sounds;return 1;
        default:h.bad=c->function;return 0;
        }
    }
    HUD(){shared.globals=&globals;context.scene.context=this;context.scene.lookup=lookup;
        context.shared=&shared;context.globals=&extra;context.composeFormatting=1;
        globals.managerToken=0x100;globals.playerToken=0x200;extra.audioEnabled=1;
        at(0x200+0x6c)=0x500;at(0x500+0x14)=0x800;
        at(0x1000+0x6c)=0x1800;at(0x1000+12)=0x2000;at(0x2000+0x28)=0x2800;
        at(0x3000+16)=0x3070;
    }
    bool run(uint32_t f){uint32_t a=0x1000,out=0;return claw_v13_player_hud_entry(f,0,&a,1,&context,dep,this,&out)&&out==1&&!bad;}
};
extern "C" uint32_t check_typed_hud(){
    for(uint32_t easy=0;easy<2;++easy){
        ClawPlayerLocomotion p{};ClawPlayerInitializationContext init{};init.difficulty=easy;
        claw_v13_player_construct_defaults(&p,&init);
        if(init.defaults[31]!=(easy?9u:7u)||init.defaults[18]!=100||init.defaults[28]!=(easy?50u:10u)||init.defaults[29]!=(easy?40u:5u)||init.defaults[30]!=(easy?20u:3u)||init.defaults[59]!=500000)return 1;
        HUD h;h.at(0x800+0x7c)=init.defaults[31];
        h.at(0x1800+28)=5;h.at(0x1800+0x18)=0x3800;
        if(!h.run(0x4912a0)||h.at(0x3800+0x2c)!=(easy?8u:6u))return 2;
    }
    for(uint32_t initial:{0u,499999u,500000u,1499999u}){
        HUD h;h.extra.initialScore=initial;
        if(!h.run(0x4908b0)||h.at(0x1000+0xfc)!=(initial/500000+1)*500000)return 3;
    }
    HUD h;h.at(0x1800+28)=5;h.at(0x1800+0x18)=0x3800;
    h.at(0x1000+0xfc)=500000;h.at(0x200+0xf8)=1500000;h.at(0x800+0x7c)=7;
    for(uint32_t i=0;i<3;++i){if(!h.run(0x4908b0)||h.at(0x800+0x7c)!=8+i||h.at(0x1000+0xfc)!=1000000+i*500000||h.sounds!=i+1)return 4;}
    h.at(0x200+0xf8)=2000000;
    if(!h.run(0x4908b0)||h.at(0x800+0x7c)!=10||h.at(0x1000+0xfc)!=2500000||h.sounds!=3)return 5;
    return 0;
}
extern "C" uint32_t check_legacy_defaults(){
    for(uint32_t easy:{0u,1u,4u}){
        ClawPlayerLocomotion actual{},original{};
        ClawPlayerInitializationContext a{},o{};a.difficulty=o.difficulty=easy;
        claw_v13_player_construct_defaults(&actual,&a);
        claw_player_construct_defaults(&original,&o);
        if(std::memcmp(a.defaults,o.defaults,sizeof(a.defaults)))return 1;
    }
    return 0;
}
'''


class LivesHost(Host):
    def call(self, user, pointer):
        call = pointer.contents
        args = tuple(call.arguments[:call.argumentCount])
        self.calls.append((call.function, call.receiver, args))
        try:
            if call.function == 0x49ae60:
                return self.record
            if call.function == 0x4f63ec:
                return self.alloc(args[0])
            if call.function == 0x4d3e50:
                actor, logic = self.alloc(0x300), self.alloc(0x100)
                self.put(actor+0x6c, logic)
                return actor
            if call.function in (0x4c7970, 0x4c79e0):
                return 0
            if call.function == 0x4c82a0:
                return 0
            if call.function == 0x4a3920:
                data = f'{args[2]:010d}'.encode() + b'\0'
                C.memmove(self.bytes(None, args[0], len(data)), data, len(data))
                return len(data)-1
            if call.function == 0x4f6286:
                self.put(args[1], self.sound_token)
                return 1
            if call.function == 0x4b45f0:
                return 1
            if call.function in (0x76542, 0x76543):
                assert self.get(args[0]+0x104) == (5 if call.function == 0x76542 else 23)
                return 1
            raise AssertionError(f'unexpected boundary {call.function:x}')
        except Exception as error:
            self.callback_error = repr(error)
            self.host.fault = 6
            return 0


def check_startup(library, legacy=False):
    interval = 1000000 if legacy else 500000
    for easy in (0, 1, 4):
        h = LivesHost(library)
        h.put(0x53725c, easy)
        h.invoke(START, 0x415ce0, 0)
        assert [h.get(t) for t in (0x534cc8, 0x534cf0, 0x534cf4, 0x534cf8, 0x534cfc, 0x534d6c)] == [100, 50 if easy else 10, 40 if easy else 5, 20 if easy else 3, 9 if easy else (3 if legacy else 7), interval]
    for score in (0, 499999, 500000, 1499999, 1500000):
        h = LivesHost(library)
        receiver, app, cache, h.record = [h.alloc(0x300) for _ in range(4)]
        h.put(receiver+4, app); h.put(receiver+0x14, 2)
        h.put(app+0x64, cache); h.put(app+0xa8, 1); h.put(app+0xd8, 1)
        h.put(h.record, 2); h.put(h.record+0x10, score)
        for offset, value in zip((0x94,0x98,0x9c,0xa0,0xa4),(83,23,12,8,6)):
            h.put(h.record+offset,value)
        assert h.invoke(START, 0x46d8e0, receiver) == 1
        assert h.get(0x534d6c) == (score//interval+1)*interval
        assert [h.get(t) for t in (0x534cc4,0x534cc8,0x534cf0,0x534cf4,0x534cf8,0x534cfc)] == [score,83,23,12,8,6]
        assert h.invoke(START, 0x46d8e0, receiver) == 0


def check_canonical_score(library, legacy=False):
    interval = 1000000 if legacy else 500000
    for initial in (0,499999,500000,1499999):
        h=LivesHost(library);actor,logic,state=[h.alloc(0x300) for _ in range(3)]
        h.put(actor+0x6c,logic);h.put(0x5371fc,state);h.put(state+0x68,100)
        h.put(0x534cc4,initial)
        assert h.invoke(SCORE,0x4908b0,0,actor)==1
        assert h.get(actor+0xfc)==(initial//interval+1)*interval
        assert h.get(logic+0x1c)==5
    h = LivesHost(library)
    actor, logic, group, player, plogic, stats, state, owner, sounds, h.sound_token = [h.alloc(0x300) for _ in range(10)]
    h.put(actor+0x6c,logic);h.put(logic+0x1c,5);h.put(logic+0x18,group)
    h.put(player+0x6c,plogic);h.put(plogic+0x14,stats)
    h.put(0x5371fc,state);h.put(0x537e88,player)
    h.put(actor+12,owner);h.put(owner+0x28,sounds)
    h.put(0x532c0c,1);h.put(h.sound_token+16,0xabc0)
    h.put(actor+0xfc,interval);h.put(player+0xf8,3*interval);h.put(stats+0x7c,7)
    assert h.invoke('claw_level_one_hud_timers_01_entry',0x4912a0,0,actor)==1
    assert h.get(group+0x2c)==6
    for i in range(3):
        assert h.invoke(SCORE,0x4908b0,0,actor)==1
        assert h.get(stats+0x7c)==8+i and h.get(actor+0xfc)==(2+i)*interval
        assert len([c for c in h.calls if c[0]==0x4b45f0])==i+1
    h.put(player+0xf8,4*interval)
    assert h.invoke(SCORE,0x4908b0,0,actor)==1
    assert h.get(stats+0x7c)==10 and h.get(actor+0xfc)==5*interval
    assert len([c for c in h.calls if c[0]==0x4b45f0])==3
    assert h.invoke(SCORE,0x4908b0,0,actor)==1 and h.get(actor+0xfc)==5*interval


def check_boss_composition(library):
    rows=((0x47e210,0x47e2d0,5),(0x453d30,0x453df0,5),(0x49fb30,0x49fbf0,5),(0x4041f0,0x404990,10),(0x4459d0,0x445ef0,5))
    for ident,(callback,constructor,damage) in enumerate(rows,1):
        for function in (callback,constructor):
            for supplied in (0,17):
                for scale in (1.0,1.5):
                    h=LivesHost(library);actor,logic,receiver=[h.alloc(0x300) for _ in range(3)]
                    h.put(actor+0x6c,logic);h.put(receiver+12,0xdeadbeef);h.put(actor+0x104,supplied)
                    h.put(0x5262b0,struct.unpack('<I',struct.pack('<f',scale))[0])
                    assert h.invoke(BOSS,function,receiver,actor)==0xabc000+ident
                    expected=(supplied or damage) if ident==5 else int(damage*scale)
                    assert h.get(actor+0x104)==expected
                    # Existing-state callbacks retain the controlled original damage.
                    if function==callback:
                        h.put(logic+0x1c,5);h.put(actor+0x104,23)
                        h.invoke(BOSS,function,receiver,actor)
                        assert h.get(actor+0x104)==23
    for function in (0x4a0cf0,0x480c40):
        h=LivesHost(library);actor,logic,receiver=[h.alloc(0x300) for _ in range(3)]
        h.put(actor+0x6c,logic);h.put(logic+0x10,0x76542);h.put(receiver,actor)
        h.invoke(BOSS,function,receiver)
        assert h.get(actor+0x104)==23
        assert [c[0] for c in h.calls]==[0x76542,0x76543]
    damage=library.claw_v13_boss_damage;damage.argtypes=[U32,U32,U32];damage.restype=U32
    for supplied in (0,7,99,0xffffffff):
        assert damage(0x12345,supplied,0)==supplied
        assert damage(0x4474f1,supplied,0)==(supplied or 5)


def check_registry():
    text=(ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
    for address,symbol in ((0x415ce0,START),(0x46d8e0,START),(0x4908b0,SCORE),*((a,BOSS) for a in (0x47e210,0x47e2d0,0x453d30,0x453df0,0x49fb30,0x49fbf0,0x4041f0,0x404990,0x4459d0,0x445ef0,0x4a0cf0,0x480c40))):
        row=re.search(r'\{0x0*'+f'{address:x}'+r'u,[^\n]+',text)
        assert row and symbol in row.group(0), f'dispatch {address:x} does not elect {symbol}'


class ProjectileHost(Host):
    """Native resource/animation boundaries around actual retained attack bodies."""
    def call(self, user, pointer):
        call = pointer.contents
        args = tuple(call.arguments[:call.argumentCount])
        self.calls.append((call.function, call.receiver, args))
        try:
            if call.function in (0x406310, 0x76544):
                return 0
            if call.function == 0x4c82a0:
                return 1
            if call.function == 0x4c8da0:
                actor, data, logic, sprite = [self.alloc(0x600) for _ in range(4)]
                self.put(actor + 0x6c, data)
                self.put(data + 0x10, 0x76542, 0, logic)
                self.put(logic + 0x12c, sprite)
                self.children.append(actor)
                return actor
            if call.function == 0x76542:
                # Observe the exact value consumed by the physical child
                # initializer, before it can copy damage to private state.
                self.consumed.append(self.get(args[0] + 0x104))
                return 1
            raise AssertionError(f'unexpected projectile boundary {call.function:x}')
        except Exception as error:
            self.callback_error = repr(error)
            self.host.fault = 6
            return 0


def check_actual_projectiles(library, legacy=False):
    for function, retained, count in ((0x4a0cf0, 'claw_level_six_wolvington_states_01_entry', 1),
                                      (0x480c40, 'claw_level_thirteen_red_tail_attacks_01_entry', 3)):
        old_damage = 15 if count == 1 else 10
        for symbol, expected in ((retained, old_damage), (BOSS, old_damage if legacy else 5)):
            h = ProjectileHost(library)
            h.children, h.consumed = [], []
            receiver, sprite, owner, world, manager, table = [h.alloc(0x600) for _ in range(6)]
            h.put(receiver, table)
            h.put(table + 0x44, 0x76544)
            h.put(receiver + 0x12c, sprite, owner)
            h.put(owner + 0xc, world)
            h.put(world + 8, manager)
            h.put(receiver + 0x470, 200)
            h.put(receiver + 0x4fc, 250)
            h.put(sprite + 0x1a4, int(count == 3))
            h.invoke(symbol, function, receiver)
            assert h.consumed == [expected] * count, (hex(function), symbol, h.consumed)
            assert [h.get(child + 0x104) for child in h.children] == [expected] * count


def main():
    result={'check':'v13-lives-boss','status':'fail','errors':[]}
    previous_profile = os.environ.pop('CLAW_LIVES_BOSS_PROFILE', None)
    try:
        load=subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True)
        assert float(load.strip('{} ').split()[0])<16,'load is at least 16; retry after it drops'
        WORK.mkdir(parents=True,exist_ok=True)
        bridge=WORK/'bridge.cpp';bridge.write_text(BRIDGE)
        library_path=WORK/'check.dylib'
        sources=['V13LivesBossAdapter.cpp','V13LivesScoreRuntime.cpp','V13BossDamageRuntime.cpp','V13PlayerHUD.cpp','PlayerInitialization.cpp','ActorAnimationRuntime.cpp','ClawMenuPlayerStartupOwner.cpp','LevelOneHudTimers01Runtime.cpp']
        sources += ['ActorResourceBindings.cpp','ActorWrapperRuntime.cpp','AnimationOperations.cpp','AnimationEngine.cpp','CheckpointTimerRuntime.cpp','PlayerPhysics.cpp','PickupPointsRuntime.cpp','PlayerLocomotion.cpp','PlayerEngine.cpp','PlayerPowerupRuntime.cpp']
        sources += ['ActorDestruction.cpp','PlayerInputDispatch.cpp','SceneActorRuntime.cpp','SpriteGeometry.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']
        subprocess.run(['clang++','-std=c++17','-O1','-dynamiclib','-undefined','dynamic_lookup','-I',str(ROOT/'Sources'),*(str(ROOT/'Sources'/s) for s in sources),str(bridge),'-o',str(library_path)],check=True)
        library=C.CDLL(str(library_path),mode=1)
        check_startup(library);check_canonical_score(library)
        library.check_typed_hud.restype=U32
        code=library.check_typed_hud();assert code==0,f'typed HUD check {code}'
        check_boss_composition(library);check_registry()
        actual_bridge = WORK/'actual-projectiles.cpp'
        actual_bridge.write_text(BRIDGE.replace('CONTROL(claw_level_six_wolvington_states_01_entry,6)', '').replace('CONTROL(claw_level_thirteen_red_tail_attacks_01_entry,7)', ''))
        actual_path = WORK/'actual-projectiles.dylib'
        actual_sources = sources + ['LevelSixWolvingtonStates01Runtime.cpp', 'LevelThirteenRedTailAttacks01Runtime.cpp']
        subprocess.run(['clang++','-std=c++17','-O1','-dynamiclib','-undefined','dynamic_lookup','-I',str(ROOT/'Sources'),*(str(ROOT/'Sources'/s) for s in actual_sources),str(actual_bridge),'-o',str(actual_path)],check=True)
        actual_library = C.CDLL(str(actual_path), mode=1)
        check_actual_projectiles(actual_library)
        # The daily baseline must execute the retained bodies, including saved
        # score restoration and physical child initialization, under v1.0.
        os.environ['CLAW_LIVES_BOSS_PROFILE'] = 'claw-v1.0'
        assert library.claw_v13_lives_boss_enabled() == 0
        assert library.check_legacy_defaults() == 0
        check_startup(library, legacy=True)
        check_canonical_score(library, legacy=True)
        check_actual_projectiles(actual_library, legacy=True)
        for ident, functions in enumerate(((0x47e210,0x47e2d0),(0x453d30,0x453df0),
                                           (0x49fb30,0x49fbf0),(0x4041f0,0x404990),
                                           (0x4459d0,0x445ef0)), 1):
            for function in functions:
                h=LivesHost(library);actor,logic,receiver=[h.alloc(0x300) for _ in range(3)]
                h.put(actor+0x6c,logic);h.put(actor+0x104,17)
                assert h.invoke(BOSS,function,receiver,actor)==0xabc000+ident
                assert h.get(actor+0x104)==31  # Controlled retained entry, unchanged by the adapter.
        for initial in (0, 499999, 500000, 999999, 1000000, 1499999):
            h=LivesHost(library);actor,logic,state=[h.alloc(0x300) for _ in range(3)]
            h.put(actor+0x6c,logic);h.put(0x5371fc,state);h.put(state+0x68,100)
            h.put(0x534cc4,initial)
            assert h.invoke(SCORE,0x4908b0,0,actor)==1
            assert h.get(actor+0xfc)==(initial//1000000+1)*1000000
        os.environ.pop('CLAW_LIVES_BOSS_PROFILE')
        assert library.claw_v13_lives_boss_enabled() == 1
        check_startup(library)
        result.update(status='pass',checked=['actual-canonical-startup-inventory','actual-saved-restoration','actual-canonical-score-one-award-per-callback-and-cap10','actual-typed-defaults-and-HUD6','actual-typed-score-initialization-and-progression','controlled-boss-adapter-seven-routes','actual-Wolvington-magic-and-RedTail-three-knife-publication','retained-v10-projectile-values','Gabriel-supplied-damage','unchanged-active-attacks-and-unowned-sites','registry-election','selected-v10-defaults-save-restore-score-awards-and-projectiles','v13-selection-restored'],limitation='Contact/bomb controls isolate routing; actual projectile bodies check child publication. Separate v1.3 gates prove original parity. No app/device acceptance.')
    except Exception as error:
        result['errors'].append(str(error))
    finally:
        if previous_profile is None:
            os.environ.pop('CLAW_LIVES_BOSS_PROFILE', None)
        else:
            os.environ['CLAW_LIVES_BOSS_PROFILE'] = previous_profile
    print(json.dumps(result));return int(result['status']!='pass')


if __name__=='__main__':
    raise SystemExit(main())
