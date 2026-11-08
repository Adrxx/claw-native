// Native safety controls supplement the independent original-entry comparison.
#include "PIDBlitter.h"
#include "ClawRuntime.h"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
#include <vector>

namespace {
constexpr uint32_t image=0x10000, surface=0x20000, dst=0x30000, src=0x40000;
constexpr uint32_t payload=0x50000, pixels=0x60000, dd=0x70000, vt=0x80000;
constexpr uint32_t unlock=0x90000;
struct Object { uint32_t token; std::vector<uint8_t> bytes; };
struct Test {
    std::vector<Object> objects;
    ClawHost host{};
    std::vector<uint32_t> calls;
    std::vector<std::array<uint32_t,2>> spans;
    bool missingLock=false, missingUnlock=false;
    uint32_t lockPixels=pixels;
    Test() {
        for(auto p: {std::pair{image,40u}, {surface,64u}, {dst,16u}, {src,16u},
                     {payload,5u}, {pixels,64u}, {dd,4u}, {vt,132u}})
            objects.push_back({p.first,std::vector<uint8_t>(p.second)});
        put(image+4,4);put(image+8,1);put(image+12,payload);put(image+16,5);put(image+36,1);
        put(surface+8,dd);put(surface+28,8);put(dd,vt);put(vt+128,unlock);
        put(src+8,3);put(dst,2);put(dst+4,1);
        const uint8_t encoded[]={4,31,42,53,64};
        std::memcpy(get(payload,5),encoded,5);
        std::memset(get(pixels,64),0xa7,64);
        host.user=this;host.bytes=bytes;host.call=call;
    }
    uint8_t *get(uint32_t token,uint32_t count) {
        for(auto &o:objects)
            if(token>=o.token && uint64_t(token)+count<=uint64_t(o.token)+o.bytes.size())
                return o.bytes.data()+token-o.token;
        return nullptr;
    }
    void put(uint32_t token,uint32_t value) {auto p=get(token,4);assert(p);std::memcpy(p,&value,4);}
    static uint8_t *bytes(void *p,uint32_t token,uint32_t count) {
        auto &t=*static_cast<Test*>(p);t.spans.push_back({token,count});return t.get(token,count);
    }
    static uint32_t call(void *p,const ClawCall *c) {
        auto &t=*static_cast<Test*>(p);t.calls.push_back(c->function);
        if(c->function==0x4b9730 && !t.missingLock) {
            assert(c->receiver==surface && c->argumentCount==1 && c->arguments[0]==0);
            return t.lockPixels;
        }
        if(c->function==unlock && !t.missingUnlock) {
            assert(c->receiver==0 && c->argumentCount==2 && c->arguments[0]==dd && c->arguments[1]==0);
            assert(t.get(pixels,64)[10]==31 && t.get(pixels,64)[13]==64);
            return 0x88760001;
        }
        t.host.fault=CLAW_FAULT_HOST;t.host.faultAddress=c->function;return 0;
    }
    uint32_t run() {
        const uint32_t args[]={dst,surface,src};uint32_t result=0xdeadbeef;
        return claw_pid_blitter_entry(0x4c00b0,image,args,3,&host,&result);
    }
    void fails(bool afterWrites=false) {
        assert(run()==0 && host.fault!=0);
        if(!afterWrites) for(uint8_t b:objects[5].bytes) assert(b==0xa7);
        assert(calls.size()<=2);
    }
};
}
int main() {
    {Test t;assert(t.run()==1 && t.host.fault==0);assert((t.calls==std::vector<uint32_t>{0x4b9730,unlock}));
        bool d=false,s=false;for(auto p:t.spans){d|=p==std::array<uint32_t,2>{dst,16};s|=p==std::array<uint32_t,2>{src,16};}assert(d&&s);}
    {Test t;t.missingLock=true;t.fails();assert(t.calls.size()==1);}
    {Test t;t.missingUnlock=true;t.fails(true);assert(t.calls.size()==2);}
    {Test t;t.host.call=nullptr;t.fails();}
    {Test t;t.host.bytes=nullptr;t.fails();}
    for(uint32_t depth:{0u,2u,3u,4u,255u}) {Test t;t.put(image+36,depth);t.fails();}
    {Test t;t.get(payload,5)[0]=0;t.fails();}
    {Test t;t.get(payload,5)[0]=128;t.fails();}
    {Test t;t.get(payload,5)[0]=5;t.fails();}
    {Test t;t.put(image+16,4);t.fails();}
    {Test t;t.put(image+16,0);t.fails();}
    {Test t;t.put(image+4,0);t.fails();}
    {Test t;t.put(image+8,0);t.fails();}
    {Test t;t.put(image+4,4097);t.fails();}
    {Test t;t.put(surface+28,0);t.fails();}
    {Test t;t.put(dst+4,1000);t.fails();}
    {Test t;t.lockPixels=0;t.fails();}
    {Test t;t.put(image+12,0xfffffffdu);t.fails();}
    {Test t;t.put(src,0xffffffff);t.fails();}
    {Test t;t.lockPixels=payload;t.fails();}
    {Test t;t.lockPixels=surface;t.fails();}
    {Test t;t.lockPixels=image;t.fails();}
    {Test t;t.lockPixels=src;t.fails();}
    {Test t;t.lockPixels=dst;t.fails();}
    {Test t;t.lockPixels=vt;t.fails();}
    std::cout << "PASS raw PID native controls: missing services, ignored HRESULT, exact rectangle spans, depth, malformed streams, unsafe bounds and aliasing\n";
}
