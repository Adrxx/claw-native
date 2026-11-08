// Bounded named-creation join. Gameplay always enters elected native sources.
#include "ClawRuntime.h"
#include "SceneActorRuntime.h"
#include <cmath>
#include <cstring>
#include <vector>
extern "C" uint32_t claw_boss_health_meter_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_boss_scene_services_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_pickup_points_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_surface_blit_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
constexpr uint32_t CONTAINER=0x1000000, WORLD=0x1001000, ENTRY=0x1003000, COLLECTION=0x1005000;
constexpr uint32_t ACTOR=0x1100000, PIXELS=0x1200000, FILL=0x68000100;
struct Event { uint32_t words[8]; };
struct Graph {
    uint8_t *memory; uint32_t size, missing, allocations=0, actor=0;
    ClawHost host{}; std::vector<Event> events;
    uint32_t get(uint32_t a) { uint32_t v=0; auto *p=bytes(this,a,4); if(p)std::memcpy(&v,p,4);return v; }
    void put(uint32_t a,uint32_t v) { auto *p=bytes(this,a,4); if(p)std::memcpy(p,&v,4); }
    void fault(uint32_t a) { if(!host.fault){host.fault=CLAW_FAULT_UNIMPLEMENTED;host.faultAddress=a;} }
    static uint8_t *bytes(void *u,uint32_t a,uint32_t n) { auto &g=*(Graph*)u;
        if(a>g.size || n>g.size-a){g.host.fault=CLAW_FAULT_MEMORY;g.host.faultAddress=a;return nullptr;}
        return g.memory+a;
    }
    uint32_t entry(ClawEntry fn,uint32_t f,uint32_t r,const uint32_t *a,uint32_t n,uint32_t frame) {
        if(missing==f){fault(f);return 0;} auto saved=host.entryStackPointer;host.entryStackPointer=frame;
        uint32_t v=0; auto handled=fn(f,r,a,n,&host,&v);host.entryStackPointer=saved;
        if(!handled&&!host.fault)fault(f);return v;
    }
    uint32_t lookupName(uint32_t receiver,uint32_t name) {
        const char *s=(const char*)bytes(this,name,32); if(!s)return 0;
        if(receiver==get(WORLD+0x14)+16 && !std::strcmp(s,"BossHealthMeter"))
            return missing==0x522280 ? 0 : ENTRY;
        if(receiver==get(WORLD+0x10)+16 && !std::strcmp(s,"GAME_BOSSBAR"))
            return missing==0x52c8c8 ? 0 : COLLECTION;
        fault(0x4f6286);return 0;
    }
    static uint32_t call(void *u,const ClawCall *c) {
        auto &g=*(Graph*)u; auto a=c->arguments;uint32_t f=c->function;
        if(g.missing==f){g.fault(f);return 0;}
        switch(f){
        case 0x491fa0: case 0x4b9830:
            return g.entry(claw_boss_health_meter_entry,f,c->receiver,a,c->argumentCount,c->stackPointer);
        case 0x42a450:
            return g.entry(claw_boss_scene_services_entry,f,c->receiver,a,c->argumentCount,c->stackPointer);
        case 0x4c7970:
            return g.entry(claw_pickup_points_canonical_entry,f,c->receiver,a,c->argumentCount,c->stackPointer);
        case 0x4b9ce0:
            return g.entry(claw_surface_blit_canonical_entry,f,c->receiver,a,c->argumentCount,c->stackPointer);
        case 0x4f6286:{
            if(c->argumentCount!=2){g.fault(f);return 0;}
            auto v=g.lookupName(c->receiver,a[0]);g.put(a[1],v);return v!=0; }
        case 0x546d5c:
            if(c->argumentCount!=5){g.fault(f);return 0;}
            for(int i=0;i<4;i++)g.put(a[0]+i*4,a[i+1]);return 1;
        case 0x4a30e0:
            if(c->x87ArgumentCount!=1){g.fault(f);return 0;}
            return std::isfinite(c->x87Argument) && c->x87Argument>=-2147483648.0 && c->x87Argument<2147483648.0
                ? uint32_t(int32_t(std::trunc(c->x87Argument))) : 0x80000000u;
        case FILL:{
            if(c->argumentCount!=6 || a[0]!=0x1009000 || a[2] || a[3] || a[4]!=0x1000400 || g.get(a[5])!=100){g.fault(f);return 0;}
            Event e{{3,g.get(a[1]),g.get(a[1]+4),g.get(a[1]+8),g.get(a[1]+12),g.get(a[5]+80),0,0}};
            g.events.push_back(e);
            for(int32_t y=int32_t(e.words[2]);y<int32_t(e.words[4]);y++)for(int32_t x=int32_t(e.words[1]);x<int32_t(e.words[3]);x++){
                if(x<0 || x>=320 || y<0 || y>=64){g.fault(f);return 0;}
                g.put(PIXELS+(y*320+x)*4,e.words[5]);
            }
            return 0; }
        default:g.fault(f);return 0;
        }
    }
    static uint32_t *lookup(void *u,uint32_t t,uint32_t n){return (uint32_t*)bytes(u,t,n*4);}
    static uint32_t allocate(void *u,uint32_t bytes){auto &g=*(Graph*)u;
        if(g.allocations>1 || bytes!=(g.allocations?0x174:0x1b4)){g.fault(0x4f63ec);return 0;}
        auto t=ACTOR+g.allocations++*0x1000;g.events.push_back({{1,t,bytes,0,0,0,0,0}});return t;}
    static void free(void *u,uint32_t){((Graph*)u)->fault(0x4f6428);}
    static uint32_t sceneCall(void *u,ClawSceneActorCall c){auto &g=*(Graph*)u;
        if(c.function==0x4f6286)return g.lookupName(c.receiver,c.arguments[0]);
        if(c.function!=0x491fa0){g.fault(c.function);return 0;}
        uint32_t actor=c.arguments[0], node=g.get(actor+0x68);
        g.events.push_back({{2,actor,node,g.get(CONTAINER+0x1c),g.get(node+8),g.get(g.get(actor+0x6c)+0x1c),0,0}});
        return g.entry(claw_boss_health_meter_entry,c.function,0,c.arguments,1,CLAW_STACK_TOP-80);
    }
};
Graph *active=nullptr;
}
extern "C" void join_start(uint8_t *memory,uint32_t size,uint32_t missing){
    delete active;active=new Graph{memory,size,missing};active->host.user=active;
    active->host.bytes=Graph::bytes;active->host.call=Graph::call;
}
extern "C" uint32_t join_step(uint32_t phase){auto &g=*active;if(g.host.fault)return 0;
    if(!phase){uint32_t fault=0;ClawSceneActorHost h{&g,Graph::lookup,Graph::allocate,Graph::free,Graph::sceneCall,nullptr};
        g.actor=claw_scene_actor_create_named(CONTAINER,{0,0,0,0,0,0x200000},0x522280,h,&fault);
        if(fault&&!g.host.fault){g.host.fault=CLAW_FAULT_HOST;g.host.faultAddress=fault;}return g.actor;}
    return g.entry(claw_boss_health_meter_entry,0x491fa0,0,&g.actor,1,CLAW_STACK_TOP);
}
extern "C" uint32_t join_fault(){return active->host.fault;}
extern "C" uint32_t join_fault_address(){return active->host.faultAddress;}
extern "C" uint32_t join_event_count(){return uint32_t(active->events.size());}
extern "C" const Event *join_events(){return active->events.data();}
