// Native composition: v1.3 callback decisions over the app's retained object
// layout. Constructors and AI keep their existing admitted v1.0 interfaces.
#include "ClawRuntime.h"
#include <cstdlib>
#include <cstring>

extern "C" uint32_t claw_cut_throat_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_v13_enemy_lifecycle_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_v13_raw_lifecycle_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
struct Route { uint32_t oldRoot,newRoot,oldConstructor,newConstructor,oldTable,size; };
constexpr Route routes[] = {
    {0x409860,0x40a020,0x409920,0x40a190,0x50b38c,0x4c8},
    {0x421200,0x422290,0x421710,0x422850,0x50bb2c,0x4b0},
    {0x434190,0x435ba0,0x434250,0x435d10,0x50c85c,0x4c0},
    {0x4379d0,0x439170,0x437a90,0x4392e0,0x50c934,0x4a8},
    {0x441be0,0x443020,0x4420e0,0x4435f0,0x50dc84,0x458},
    {0x449c40,0x44b500,0x44a380,0x44bce0,0x50e014,0x460},
    {0x45ff00,0x461e50,0x45ffc0,0x461fc0,0x50e954,0x508},
    {0x462350,0x464850,0x462410,0x4649c0,0x50ea0c,0x498},
    {0x465580,0x467ae0,0x465640,0x467c50,0x50ec6c,0x478},
    {0x4689b0,0x46ac10,0x468eb0,0x46b1e0,0x50ed1c,0x510},
    {0x474330,0x475e90,0x4743f0,0x476000,0x50eee4,0x438},
    {0x47c850,0x47f0c0,0x47c910,0x47f230,0x50f084,0x448},
};
struct View {
    ClawHost &parent;
    const Route &route;
    uint32_t actor;
    uint32_t noop=0x4ce9b0;
    ClawHost host;
    View(ClawHost &p,const Route &r,uint32_t a):parent(p),route(r),actor(a),host(p) {
        host.user=this;host.bytes=bytes;host.call=call;
    }
    static uint8_t *bytes(void *user,uint32_t address,uint32_t count) {
        auto &s=*static_cast<View*>(user);
        // The callback root reads only this actor field; its logic record's
        // event and instance slots retain their old offsets.
        if(address==s.actor+0x7c && count==4) address=s.actor+0x6c;
        if(count==4 && address>=s.route.oldTable && address<s.route.oldTable+0x40) {
            switch(address-s.route.oldTable) {
            case 0x18: address=s.route.oldTable+0x10;break;
            case 0x28: address=s.route.oldTable+0x1c;break;
            case 0x2c: address=s.route.oldTable+0x20;break;
            case 0x30: case 0x34: case 0x38: case 0x3c:
                // All four installed hooks for every listed shipped class
                // are the admitted one-byte no-op, not generic event dispatch.
                return reinterpret_cast<uint8_t*>(&s.noop);
            default: break;
            }
        }
        return s.parent.bytes?s.parent.bytes(s.parent.user,address,count):nullptr;
    }
    static uint32_t call(void *user,const ClawCall *request) {
        auto &s=*static_cast<View*>(user);
        ClawCall mapped=*request;
        if(mapped.function==0x4fcaea) {
            if(mapped.argumentCount!=1 || mapped.arguments[0]!=s.route.size) {
                s.host.fault=CLAW_FAULT_ABI;s.host.faultAddress=mapped.function;return 0;
            }
            mapped.function=0x4f63ec;
        } else if(mapped.function==s.route.newConstructor) {
            mapped.function=s.route.oldConstructor;
        } else if(mapped.function==0x4def40) {
            mapped.function=0x4dc870;
        } else if(mapped.function==0x4ce9b0) {
            uint32_t result=0;
            if(!claw_v13_raw_lifecycle_entry(0x4ce9b0,mapped.receiver,nullptr,0,&s.host,&result)) {
                s.host.fault=CLAW_FAULT_ABI;s.host.faultAddress=0x4ce9b0;
            }
            return result;
        }
        if(!s.parent.call) {s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=mapped.function;return 0;}
        uint32_t result=s.parent.call(s.parent.user,&mapped);
        if(s.parent.fault) {s.host.fault=s.parent.fault;s.host.faultAddress=s.parent.faultAddress;}
        return result;
    }
};
}
extern "C" uint32_t claw_v13_enemy_lifecycle_compat_entry(uint32_t function,uint32_t receiver,
    const uint32_t *arguments,uint32_t argumentCount,ClawHost *host,uint32_t *result) {
    // The v1.0 constructor comparison must retain the original callback's
    // allocation size and call sequence. Normal app dispatch stays on v1.3.
    const char *profile=std::getenv("CLAW_LIVES_BOSS_PROFILE");
    if(function==0x4379d0 && profile && std::strcmp(profile,"claw-v1.0")==0)
        return claw_cut_throat_entry(function,receiver,arguments,argumentCount,host,result);
    const Route *route=nullptr;
    for(const auto &candidate:routes) if(candidate.oldRoot==function) {route=&candidate;break;}
    if(!route)return 0;
    if(!host || !arguments || argumentCount!=1)return 0;
    View view(*host,*route,arguments[0]);
    uint32_t accepted=claw_v13_enemy_lifecycle_entry(route->newRoot,receiver,arguments,1,&view.host,result);
    if(view.host.fault) {host->fault=view.host.fault;host->faultAddress=view.host.faultAddress;}
    return accepted;
}
