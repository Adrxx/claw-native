#include "V13Contact.h"
#include "ClawRuntime.h"
#include <cstring>
#include <vector>
extern "C" uint32_t claw_v13_contact_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_v13_contact_dispatch_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
constexpr uint32_t base=0x10000000,manager=base,scene=base+0x100,collection=base+0x200;
constexpr uint32_t map=base+0x300,callback=base+0x400,tileVtable=base+0x500;
constexpr uint32_t actorBase=base+0x1000,stride=0x200,callbackEntry=0x71000000,tileEntry=0x72000000;
struct Adapter {
    const ClawCollisionWorld &world;
    ClawV13ContactActor *actors;
    uint32_t count;
    ClawV13BumpCallback bump;
    void *user;
    std::vector<uint32_t> foreignPeers;
    std::vector<uint8_t> memory,stack=std::vector<uint8_t>(CLAW_STACK_END-CLAW_STACK_BASE);
    uint32_t next;
    ClawHost host{};
    Adapter(const ClawCollisionWorld &w,ClawV13ContactActor *a,uint32_t n,ClawV13BumpCallback b,void *u)
        :world(w),actors(a),count(n),bump(b),user(u),next(actorBase+stride*n) {
        const uint32_t columns=((uint32_t(w.width)-1)>>w.shiftX)+1;
        const uint32_t rows=((uint32_t(w.height)-1)>>w.shiftY)+1;
        const uint32_t cells=w.rowOffsets[rows-1]+columns;
        memory.resize(next-base+4*(uint64_t(cells)+rows+2*w.descriptionCount+3*count)+256);
        host.user=this;host.bytes=bytes;host.call=call;
        put(manager+0x0c,scene);put(scene+8,collection);put(manager+0x5c,map);
        put(callback+0x10,callbackEntry);put(tileVtable+0x18,tileEntry);
        const uint32_t cellData=allocate(cells*4),rowData=allocate(rows*4),tileData=allocate(w.descriptionCount*4);
        std::memcpy(bytes(this,cellData,cells*4),w.cells,cells*4);
        std::memcpy(bytes(this,rowData,rows*4),w.rowOffsets,rows*4);
        put(map+0x20,cellData);put(map+0x24,rowData);put(map+0x30,w.width);put(map+0x34,w.height);
        put(map+0x8c,w.shiftX);put(map+0x90,w.shiftY);put(manager+0x4c,tileData);
        for(uint32_t i=0;i<w.descriptionCount;++i) {
            uint32_t tile=allocate(4);put(tile,tileVtable);put(tileData+4*i,tile);
        }
        const uint32_t nodes=allocate(n*12);put(collection+0x14,n?nodes:0);
        for(uint32_t i=0;i<n;++i) {
            put(nodes+i*12,i+1<n?nodes+(i+1)*12:0);put(nodes+i*12+8,token(i));publish(i);
        }
    }
    uint32_t allocate(uint32_t n) {uint32_t result=next;next+=n;return result;}
    uint32_t token(uint32_t i) const {return actorBase+i*stride;}
    uint32_t get(uint32_t t) {uint32_t v=0;auto p=bytes(this,t,4);if(p)std::memcpy(&v,p,4);return v;}
    void put(uint32_t t,uint32_t v) {auto p=bytes(this,t,4);if(p)std::memcpy(p,&v,4);}
    static uint8_t *bytes(void *u,uint32_t t,uint32_t n) {
        auto &s=*static_cast<Adapter*>(u);
        if(t>=base&&uint64_t(t-base)+n<=s.memory.size())return s.memory.data()+t-base;
        if(t>=CLAW_STACK_BASE&&uint64_t(t-CLAW_STACK_BASE)+n<=s.stack.size())return s.stack.data()+t-CLAW_STACK_BASE;
        return nullptr;
    }
    uint32_t peerToken(uint32_t t) {
        for(uint32_t i=0;i<count;++i)if(token(i)==t)return actors[i].actor.token;
        if(t>=0x73000000 && (t-0x73000000)%4==0 && (t-0x73000000)/4<foreignPeers.size())
            return foreignPeers[(t-0x73000000)/4];
        return t;
    }
    uint32_t guestPeer(uint32_t t) {
        if(!t)return 0;
        for(uint32_t i=0;i<count;++i)if(actors[i].actor.token==t)return token(i);
        // Preserve opaque peer identities even when their numeric value equals
        // one of this invocation's private actor addresses.
        for(uint32_t i=0;i<foreignPeers.size();++i)if(foreignPeers[i]==t)return 0x73000000+i*4;
        foreignPeers.push_back(t);
        return 0x73000000+uint32_t(foreignPeers.size()-1)*4;
    }
    void publish(uint32_t i) {
        auto &r=actors[i];auto &a=r.actor;uint32_t t=token(i);
        put(t+8,a.flags);put(t+0x5c,a.x);put(t+0x60,a.y);put(t+0xe4,a.mode);
        put(t+0xe8,a.type);put(t+0xf4,r.mask);put(t+0xf8,a.stepX);put(t+0xfc,a.stepY);
        put(t+0x90,r.hasCallback?callback:0);
        put(t+0x94,guestPeer(r.otherToken));
        put(t+0x134,a.moveRect.left);put(t+0x138,a.moveRect.top);put(t+0x13c,a.moveRect.right);put(t+0x140,a.moveRect.bottom);
    }
    void collect(uint32_t i) {
        auto &r=actors[i];auto &a=r.actor;uint32_t t=token(i);
        a.flags=get(t+8);a.x=get(t+0x5c);a.y=get(t+0x60);a.mode=get(t+0xe4);
        a.type=get(t+0xe8);r.mask=get(t+0xf4);r.otherToken=peerToken(get(t+0x94));
    }
    static uint32_t call(void *u,const ClawCall *c) {
        auto &s=*static_cast<Adapter*>(u);
        if(c->function==0x4d7860 && c->argumentCount==4) {
            uint32_t result=0;
            claw_v13_contact_entry(c->function,c->receiver,c->arguments,4,&s.host,&result);
            return result;
        }
        if((c->function==0x4cca90 || c->function==0x4ccc60 || c->function==0x4cce20 || c->function==0x4ccf20)
           && c->argumentCount==4 && c->arguments[0]>=actorBase) {
            uint32_t i=(c->arguments[0]-actorBase)/stride;
            if(i<s.count && s.token(i)==c->arguments[0]) {
                s.collect(i);
                uint32_t result=claw_collision_response_helper(c->function,&s.world,&s.actors[i].actor,
                    c->arguments[1],c->arguments[2],c->arguments[3]);
                s.publish(i);
                return result;
            }
        }
        if(c->function==0x421ad0&&c->argumentCount==2)
            return claw_world_point_attribute(s.world.cells,s.world.rowOffsets,s.world.width,s.world.height,
                s.world.shiftX,s.world.shiftY,s.world.descriptions,s.world.descriptionCount,c->arguments[0],c->arguments[1],0,0);
        if(c->function==tileEntry&&c->argumentCount==2) {
            uint32_t tileData=s.get(manager+0x4c);
            for(uint32_t i=0;i<s.world.descriptionCount;++i)
                if(s.get(tileData+4*i)==c->receiver)return claw_tile_attribute(s.world.descriptions+i,int32_t(c->arguments[0]),int32_t(c->arguments[1]));
        }
        if(c->function==callbackEntry&&c->argumentCount==1&&c->arguments[0]>=actorBase) {
            uint32_t i=(c->arguments[0]-actorBase)/stride;
            if(i<s.count&&s.token(i)==c->arguments[0]) {
                for(uint32_t j=0;j<s.count;++j)s.collect(j);
                uint32_t result=s.bump?s.bump(s.actors,s.count,i,s.user):1;
                for(uint32_t j=0;j<s.count;++j)s.publish(j);
                return result;
            }
        }
        s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=c->function;return 0;
    }
};
}
extern "C" uint32_t claw_v13_contact_resolve(const ClawCollisionWorld *world,ClawV13ContactActor *actors,uint32_t count,
    uint32_t mover,uint32_t x,uint32_t y,uint32_t options,ClawV13BumpCallback callback,void *user,uint32_t *fault) {
    return claw_v13_collision_resolve(world,4,actors,count,mover,x,y,options,callback,user,fault);
}
extern "C" uint32_t claw_v13_collision_resolve(const ClawCollisionWorld *world,uint32_t managerFlags,
    ClawV13ContactActor *actors,uint32_t count,uint32_t mover,uint32_t x,uint32_t y,uint32_t options,
    ClawV13BumpCallback callback,void *user,uint32_t *fault) {
    if(fault)*fault=0;
    if(!world||!actors||!count||mover>=count||count>65536||!world->cells||!world->rowOffsets||!world->descriptions||
       world->width<1||world->height<1||world->shiftX>30||world->shiftY>30||!world->descriptionCount) {
        if(fault)*fault=CLAW_FAULT_ABI;return 0;
    }
    Adapter adapter(*world,actors,count,callback,user);
    adapter.put(manager+8,managerFlags);
    uint32_t args[]={adapter.token(mover),x,y,options},result=0;
    if(!claw_v13_contact_dispatch_entry(0x4cc920,manager,args,4,&adapter.host,&result)) {
        if(fault)*fault=adapter.host.fault?adapter.host.fault:CLAW_FAULT_ABI;
        return 0;
    }
    for(uint32_t i=0;i<count;++i)adapter.collect(i);
    return result;
}
extern "C" uint32_t claw_v13_collision_move(const ClawCollisionWorld *world,uint32_t managerFlags,
    ClawV13ContactActor *actors,uint32_t count,uint32_t mover,uint32_t x,uint32_t y,uint32_t options,
    ClawV13BumpCallback callback,void *user,uint32_t *fault) {
    uint32_t localFault=0;
    if(!fault)fault=&localFault;
    if(fault)*fault=0;
    if(!world || !actors || mover>=count) {if(fault)*fault=CLAW_FAULT_ABI;return 0;}
    struct Context {
        uint32_t flags,count,mover;
        ClawV13ContactActor *actors;
        ClawV13BumpCallback callback;
        void *user;
        uint32_t *fault;
    } context{managerFlags,count,mover,actors,callback,user,fault};
    return claw_collision_move_with_resolver(world,&actors[mover].actor,x,y,options,
        [](const ClawCollisionWorld *w,ClawCollisionActor *,uint32_t px,uint32_t py,uint32_t flags,void *u) {
            auto &c=*static_cast<Context*>(u);
            auto result=claw_v13_collision_resolve(w,c.flags,c.actors,c.count,c.mover,px,py,flags,c.callback,c.user,c.fault);
            return c.fault && *c.fault ? result|0x400000 : result;
        },&context);
}
