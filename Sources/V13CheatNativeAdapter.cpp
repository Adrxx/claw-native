// Native composition over the retained app layout. Original v1.0 exports stay
// untouched; the separate v1.3 admissions establish these selected deltas.
#include "ClawRuntime.hpp"
#include <cstdio>
extern "C" {
uint32_t claw_level_one_claw_states_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_v13_enemy_death_compat_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_one_player_actions_02_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_one_player_actions_03_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_v13_cheat_pegs_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
}
namespace {
constexpr uint32_t modes=0x58010000; // long range, easy, turbo, bounce, total, current, maximum
uint32_t read(ClawHost &h,uint32_t a) {uint32_t v=0;auto p=h.bytes(h.user,a,4);if(p)std::memcpy(&v,p,4);return v;}
void write(ClawHost &h,uint32_t a,uint32_t v) {auto p=h.bytes(h.user,a,4);if(p)std::memcpy(p,&v,4);}
struct View {
    ClawHost &parent;ClawHost host;
    uint32_t root,actor,record,state,adjusted=0,lastLeft=0;
    bool pegs;uint32_t enemy=0,lengthReads=0;
    View(ClawHost &h,uint32_t f,uint32_t a,bool p):parent(h),host(h),root(f),actor(a),pegs(p) {
        record=read(h,a+0x6c);state=record?read(h,record+0x14):0;
        host.user=this;host.bytes=bytes;host.call=call;
    }
    uint32_t pointer(uint32_t a) {
        // Only game-object fields move. Animation, logic, level/default and
        // manager records retain their own layouts.
        if(pegs) {
            uint32_t player=read(parent,0x537e88);
            for(uint32_t object:{actor,player}) if(object && a>=object && a<object+0x200) {
                switch(a-object) {
                case 0x5c:return object+0x4c;case 0x60:return object+0x50;
                case 0x74:return object+0x64;case 0x7c:return object+0x6c;
                case 0x98:return object+0x80;case 0xe8:return object+0xd0;
                case 0x124:return object+0x108;case 0x12c:return object+0x110;
                case 0x144:return object+0x128;case 0x148:return object+0x12c;
                case 0x14c:return object+0x130;case 0x150:return object+0x134;
                case 0x164:return object+0x148;case 0x168:return object+0x14c;
                case 0x174:return object+0x158;case 0x178:return object+0x15c;
                case 0x180:return object+0x164;case 0x190:return object+0x16c;
                case 0x194:return object+0x170;case 0x198:return object+0x174;
                case 0x1a0:return object+0x188;case 0x1c0:return object+0x19c;
                case 0x1c8:return object+0x1a4;
                default:return a;
                }
            }
            switch(a) {
            case 0x535950:return modes+4;case 0x535990:return 0x53725c;
            case 0x5365d4:return 0x537e88;case 0x5360a8:return 0x537960;
            case 0x535928:return 0x537210;case 0x530990:return 0x532c10;
            case 0x5aafd8:return 0x5430c4;
            }
        }
        return a;
    }
    static uint8_t *bytes(void *u,uint32_t a,uint32_t n) {
        auto &s=*static_cast<View*>(u);
        if(s.pegs && a==s.record+0x10 && n==4) {
            uint32_t callback=read(s.parent,a);
            if(callback==0x49e7b0 || callback==0x49e7d0 || callback==0x49e7f0) {
                s.adjusted=callback==0x49e7b0?0x4a2350:callback==0x49e7d0?0x4a2370:0x4a2390;
                return reinterpret_cast<uint8_t*>(&s.adjusted);
            }
        }
        // The second length read is the common bit-4 publication tail. The
        // v1.3 bounce readout belongs just before that retained publication.
        if(s.enemy && a==s.enemy+0x2fc && n==4 && ++s.lengthReads==2 && read(s.parent,modes+12)) {
            uint32_t count=read(s.parent,a),bits=count<=32?s.enemy+0x300:read(s.parent,s.enemy+0x300);
            if(count>4 && (read(s.parent,bits)&16)) {
                uint32_t current=read(s.parent,modes+20)+1,total=read(s.parent,modes+16)+1;
                uint32_t maximum=read(s.parent,modes+24);
                if(int32_t(current)>int32_t(maximum))maximum=current;
                write(s.parent,modes+20,current);write(s.parent,modes+24,maximum);write(s.parent,modes+16,total);
                auto buffer=s.parent.bytes(s.parent.user,0x58010100,128);
                if(buffer) {
                    std::snprintf(reinterpret_cast<char*>(buffer),128,"Enemy Bounces = %i, Max Bounces = %i, Total Bounces = %i",int32_t(current),int32_t(maximum),int32_t(total));
                    ClawCall q{};q.function=0x42af70;q.receiver=read(s.parent,0x5371fc);q.argumentCount=1;q.arguments[0]=0x58010100;
                    s.parent.call(s.parent.user,&q);
                }
            } else write(s.parent,modes+20,0);
        }
        if(!s.pegs && n==4) {
            // The retained speed selection has already saturated its timer
            // and selected its animation rate. Substitute only its base-speed
            // contribution at the final adjustment read, before physics.
            if(s.state && a==s.state+0x84 && read(s.parent,modes+8)) {
                uint32_t id=read(s.parent,s.record+0x1c);
                if(id==8 || id==9) {
                    uint32_t base=read(s.parent,0x534eac)==0x26bc?300:read(s.parent,s.state+0x114)?225:285;
                    s.adjusted=read(s.parent,a)+(id==8?450-base:base-450);
                    return reinterpret_cast<uint8_t*>(&s.adjusted);
                }
            }
            if(s.root==0x41de90 && a==s.actor+0x138)s.lastLeft=read(s.parent,a);
        }
        return s.parent.bytes(s.parent.user,s.pointer(a),n);
    }
    static uint32_t call(void *u,const ClawCall *q) {
        auto &s=*static_cast<View*>(u);ClawCall c=*q;
        if(s.pegs) {
            c.receiver=s.pointer(c.receiver);
            switch(c.function) {
            case 0x4a2010:c.function=0x49e470;break;
            case 0x4a2050:c.function=0x49e4b0;break;
            case 0x40fbe0:c.function=0x40f680;break;
            case 0x4c6e40:c.function=0x4c79e0;break;
            case 0x4c8550:c.function=0x4c82a0;break;
            case 0x4cb050:c.function=0x4ca610;break;
            case 0x4a595b:c.function=0x4a3050;break;
            case 0x4fc6b4:c.function=0x4f6286;break;
            case 0x421bb0:c.function=0x4208e0;break;
            }
            for(uint32_t i=0;i<c.argumentCount;++i) switch(c.arguments[i]) {
            case 0x52c1ac:c.arguments[i]=0x52dd04;break;
            case 0x52c1bc:c.arguments[i]=0x52dd14;break;
            case 0x52c1cc:c.arguments[i]=0x52dd24;break;
            case 0x526d84:c.arguments[i]=0x528a3c;break;
            }
        }
        uint32_t result=s.parent.call(s.parent.user,&c);
        if(s.parent.fault){s.host.fault=s.parent.fault;s.host.faultAddress=s.parent.faultAddress;}
        return result;
    }
};
}
extern "C" uint32_t claw_v13_cheat_native_entry(uint32_t f,uint32_t r,const uint32_t *a,uint32_t n,ClawHost *h,uint32_t *out) {
    if(!h || !a)return 0;
    bool peg=f==0x49d330 || f==0x49d620 || f==0x49d860 || f==0x49e4e0 || f==0x49e7b0 || f==0x49e7d0 || f==0x49e7f0;
    if(!peg && f!=0x415df0 && f!=0x4183e0 && f!=0x418790 && f!=0x41de90 && f!=0x43f120)return 0;
    View v(*h,f,a[0],peg);uint32_t accepted=0;
    if(peg) {
        uint32_t target=f==0x49d330?0x4a0f30:f==0x49d620?0x4a1230:f==0x49d860?0x4a1430:0x4a2080;
        accepted=claw_v13_cheat_pegs_entry(target,r,a,n,&v.host,out);
    } else if(f==0x43f120) {
        if(a[0]==0)v.enemy=r;
        accepted=claw_v13_enemy_death_compat_entry(f,r,a,n,&v.host,out);
    } else if(f==0x41de90) {
        v.state=a[2];
        accepted=claw_level_one_player_actions_03_entry(f,r,a,n,&v.host,out);
        if(accepted && !v.host.fault && read(*h,modes)) {
            uint32_t field=read(*h,a[2])==0 && v.lastLeft!=0x80000000?a[0]+0x138:a[0]+0x140;
            write(*h,field,read(*h,field)+(field==a[0]+0x138?uint32_t(-320):320));
        }
    } else {
        if(n==3){v.record=a[1];v.state=a[2];}
        auto entry=f==0x418790?claw_level_one_claw_states_01_entry:claw_level_one_player_actions_02_entry;
        accepted=entry(f,r,a,n,&v.host,out);
    }
    if(v.host.fault){h->fault=v.host.fault;h->faultAddress=v.host.faultAddress;}
    return accepted;
}
