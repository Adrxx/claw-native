#include "V13Profiles.h"
#include "ClawRuntime.h"
#include <cstring>
extern "C" uint32_t claw_v13_profiles_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
struct Close {
    uint32_t object=0x10000100,result=0,closed=0;
    uint32_t table[0x200/4]{};
    static uint8_t *bytes(void *user,uint32_t address,uint32_t count) {
        auto &s=*static_cast<Close*>(user);
        if(address==0x10000000 && count==4)return reinterpret_cast<uint8_t*>(&s.object);
        if(address==0x5234bc && count==4)return reinterpret_cast<uint8_t*>(&s.result);
        if(address>=0x10000100 && uint64_t(address-0x10000100)+count<=sizeof(s.table))
            return reinterpret_cast<uint8_t*>(s.table)+address-0x10000100;
        return nullptr;
    }
    static uint32_t call(void *user,const ClawCall *call) {
        auto &s=*static_cast<Close*>(user);
        if(call->function==0x71000000 && call->receiver==0x10000000 && !call->argumentCount)
            s.closed=s.result;
        return 0;
    }
};
}
extern "C" uint32_t claw_v13_profile_close_result(uint32_t cancelled) {
    Close state;
    state.table[0x1e8/4]=0x71000000;
    ClawHost host{};
    host.user=&state;host.bytes=Close::bytes;host.call=Close::call;
    uint32_t ignored=0;
    const auto accepted=claw_v13_profiles_entry(cancelled?0x425a40:0x425a20,0x10000000,nullptr,0,&host,&ignored);
    return accepted && !host.fault ? state.closed : 0;
}
