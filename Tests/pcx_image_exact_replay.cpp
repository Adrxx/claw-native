#include "PCXImageRuntime.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <string>
#include <vector>

namespace {
struct Heap {
    std::map<uint32_t,std::vector<uint8_t>> spans;
    uint32_t next=0x3100000,pixels=0,locks=0,unlocks=0;
};
uint32_t allocate(Heap& h,uint32_t size) {
    uint32_t token=h.next; h.next+=(size+15)&~15u;
    h.spans[token]=std::vector<uint8_t>(size,0xa5); return token;
}
uint8_t* bytes(void* user,uint32_t token,uint32_t count) {
    auto& h=*static_cast<Heap*>(user); auto i=h.spans.upper_bound(token);
    if(i==h.spans.begin()) return nullptr;
    --i; uint64_t offset=uint64_t(token)-i->first;
    if(offset+count>i->second.size()) return nullptr;
    return i->second.data()+offset;
}
uint32_t* words(void* user,uint32_t token,uint32_t count) {
    return token%4?nullptr:reinterpret_cast<uint32_t*>(bytes(user,token,count*4));
}
void put(Heap& h,uint32_t token,uint32_t value) {
    auto* p=words(&h,token,1); assert(p); *p=value;
}
uint32_t dependency(ClawPCXImageContext* c,const ClawPCXImageCall* q,void*) {
    auto& h=*static_cast<Heap*>(c->byteContext);
    switch(q->function) {
    case 0x700064:
        assert(q->argumentCount==5); put(h,q->arguments[2]+36,h.pixels);
        ++h.locks; return 0;
    case 0x700080: ++h.unlocks; return 0;
    default: assert(false); return 0;
    }
}
std::vector<uint8_t> file(const std::string& path) {
    std::ifstream f(path,std::ios::binary); assert(f);
    return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
}

int main(int argc,char** argv) {
    assert(argc==2); std::string root=argv[1];
    std::ifstream manifest(root+"/replay-manifest.txt"); assert(manifest);
    uint32_t index,width,height,planes,padding,fileBytes,inputBytes,surfaceBytes;
    uint32_t whole=0,prefixes=0;
    while(manifest>>index>>width>>height>>planes>>padding>>fileBytes>>inputBytes>>surfaceBytes) {
        Heap h; ClawGameImageGlobals globals{}; ClawPCXImageContext context{};
        context.scene={&h,words,nullptr,nullptr,nullptr,nullptr};
        context.byteContext=&h; context.bytes=bytes; context.image=&globals; context.composeImage=1;
        uint32_t surface=allocate(h,188),manager=allocate(h,2180);
        uint32_t dd=allocate(h,4),vt=allocate(h,132);
        auto prefix=root+"/"+std::to_string(index);
        auto raw=file(prefix+".input"),expected=file(prefix+".surface");
        auto initial=file(prefix+".before.surface");
        assert(raw.size()==inputBytes&&expected.size()==surfaceBytes&&initial.size()==surfaceBytes);
        h.pixels=allocate(h,surfaceBytes); h.spans[h.pixels]=initial;
        uint32_t data=allocate(h,inputBytes); h.spans[data]=raw;
        put(h,surface+8,dd); put(h,dd,vt);
        put(h,vt+0x64,0x700064); put(h,vt+0x80,0x700080);
        put(h,surface+20,height); put(h,surface+24,width);
        put(h,surface+28,width*planes+padding); put(h,surface+164,planes*8);
        put(h,manager+0x474,planes*8);
        uint32_t args[]={manager,data,fileBytes},out=0;
        assert(claw_pcx_image_entry(0x4bebc0,surface,args,3,&context,dependency,nullptr,&out)&&out==1);
        assert(h.spans[h.pixels]==expected&&h.locks==1&&h.unlocks==1);
        assert(claw_pcx_image_entry(0x4bebc0,surface,args,3,&context,dependency,nullptr,&out)&&out==1);
        assert(h.spans[h.pixels]==expected&&h.locks==2&&h.unlocks==2);
        ++whole;
        if(inputBytes>fileBytes) {
            h.spans[data].resize(fileBytes); h.spans[h.pixels]=initial;
            context.fault=0; h.locks=h.unlocks=0;
            assert(!claw_pcx_image_entry(0x4bebc0,surface,args,3,&context,dependency,nullptr,&out));
            assert(context.fault==1&&h.locks==1&&h.unlocks==0);
            assert(h.spans[h.pixels]==file(prefix+".prefix.surface")); ++prefixes;
        }
    }
    assert(whole==469);
    std::cout<<"PASS "<<whole<<" exact-span original-captured PCX profiles/repeated calls and "
             <<prefixes<<" tight-file source prefixes; ASAN/UBSAN\n";
}
