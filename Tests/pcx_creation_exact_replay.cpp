#include "PCXCreationRuntime.h"
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
    uint32_t next=0x3100000,pixels=0,locks=0,unlocks=0,dd=0,pitch=0,temporaryAllocations=0,frees=0;
    std::vector<uint32_t> descriptor;
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
    case 0x4f63ec: ++h.temporaryAllocations;return allocate(h,q->arguments[0]);
    case 0x4f6428: assert(h.spans.erase(q->arguments[0]));++h.frees;return 0;
    case 0x700018: {
        auto* request=words(&h,q->arguments[1],27); assert(request);
        h.descriptor.assign(27,0);h.descriptor[0]=108;h.descriptor[1]=7;
        h.descriptor[2]=request[2];h.descriptor[3]=request[3];
        h.descriptor[4]=h.pitch;h.descriptor[9]=h.pixels;
        h.descriptor[21]=*words(&h,q->arguments[0]+0x100,1);
        put(h,q->arguments[2],h.dd);return 0;
    }
    case 0x700058:
        std::memcpy(words(&h,q->arguments[1],27),h.descriptor.data(),108);return 0;
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
    assert(argc==3); std::string root=argv[1],generated=argv[2];
    std::ifstream manifest(root+"/replay-manifest.txt"); assert(manifest);
    uint32_t index,width,height,planes,padding,fileBytes,inputBytes,surfaceBytes;
    uint32_t whole=0,prefixes=0;
    while(manifest>>index>>width>>height>>planes>>padding>>fileBytes>>inputBytes>>surfaceBytes) {
        Heap h; ClawGameImageGlobals globals{}; ClawPCXImageContext context{};
        context.scene={&h,words,nullptr,nullptr,nullptr,nullptr};
        context.byteContext=&h; context.bytes=bytes; context.image=&globals; context.composeImage=1;
        uint32_t surface=allocate(h,188),manager=allocate(h,2180);
        uint32_t dd=allocate(h,260),vt=allocate(h,132);h.dd=dd;h.pitch=width*planes+padding;put(h,dd+0x100,planes*8);
        auto prefix=root+"/"+std::to_string(index);
        auto raw=file(prefix+".input"),expected=file(prefix+".surface");
        auto initial=file(prefix+".before.surface");
        assert(raw.size()==inputBytes&&expected.size()==surfaceBytes&&initial.size()==surfaceBytes);
        h.pixels=allocate(h,surfaceBytes); h.spans[h.pixels]=initial;
        uint32_t data=allocate(h,inputBytes); h.spans[data]=raw;
        h.spans[0x513690]=std::vector<uint8_t>(36);
        put(h,surface,0x513690);put(h,0x513690+12,0x4b9180);put(h,0x513690+32,0x4b9380);
        put(h,surface+8,dd); put(h,dd,vt);put(h,manager,dd);
        put(h,vt+0x18,0x700018);put(h,vt+0x58,0x700058);
        put(h,vt+0x64,0x700064); put(h,vt+0x80,0x700080);
        put(h,surface+20,height); put(h,surface+24,width);
        put(h,surface+28,width*planes+padding); put(h,surface+164,planes*8);
        put(h,manager+0x474,planes*8);
        uint32_t args[]={manager,data,fileBytes,0x40},out=0;
        assert(claw_pcx_creation_entry(surface,args,4,&context,dependency,nullptr,&out)&&out==1);
        assert(h.spans[h.pixels]==expected&&h.locks==1&&h.unlocks==1);
        assert(claw_pcx_creation_entry(surface,args,4,&context,dependency,nullptr,&out)&&out==1);
        assert(h.spans[h.pixels]==expected&&h.locks==2&&h.unlocks==2);
        ++whole;
        if(inputBytes>fileBytes) {
            h.spans[data].resize(fileBytes); h.spans[h.pixels]=initial;
            context.fault=0; h.locks=h.unlocks=0;
            assert(!claw_pcx_creation_entry(surface,args,4,&context,dependency,nullptr,&out));
            assert(context.fault==1&&h.locks==1&&h.unlocks==0);
            assert(h.spans[h.pixels]==file(prefix+".prefix.surface")); ++prefixes;
        }
    }
    assert(whole==469);
    std::ifstream extra(generated+"/generated-manifest.txt");assert(extra);
    uint32_t target,generatedCount=0;
    while(extra>>index>>width>>height>>planes>>target>>padding>>fileBytes>>surfaceBytes) {
        Heap h;ClawGameImageGlobals globals{};ClawPCXImageContext context{};
        context.scene={&h,words,nullptr,nullptr,nullptr,nullptr};context.byteContext=&h;
        context.bytes=bytes;context.image=&globals;context.composeImage=1;
        auto prefix=generated+"/generated-"+std::to_string(index);
        auto raw=file(prefix+".input"),expected=file(prefix+".surface"),initial=file(prefix+".before"),palette=file(prefix+".palette");
        uint32_t surface=allocate(h,188),manager=allocate(h,2180),dd=allocate(h,260),vt=allocate(h,132);
        h.dd=dd;h.pitch=width*(target==8?1:3)+padding;put(h,dd+0x100,target);
        h.pixels=allocate(h,surfaceBytes);h.spans[h.pixels]=initial;
        uint32_t data=allocate(h,fileBytes);h.spans[data]=raw;
        h.spans[0x513690]=std::vector<uint8_t>(36);h.spans[0x541fb0]=std::vector<uint8_t>(1024);
        put(h,surface,0x513690);put(h,0x513690+12,0x4b9180);put(h,0x513690+32,0x4b9380);
        put(h,manager,dd);put(h,dd,vt);put(h,vt+0x18,0x700018);put(h,vt+0x58,0x700058);
        put(h,vt+0x64,0x700064);put(h,vt+0x80,0x700080);put(h,manager+0x474,target);put(h,manager+0x878,1);
        assert(palette.size()==1024);std::memcpy(bytes(&h,manager+0x478,1024),palette.data(),1024);
        uint32_t args[]={manager,data,fileBytes,0x40},out=0;
        assert(claw_pcx_creation_entry(surface,args,4,&context,dependency,nullptr,&out)&&out==1);
        assert(h.spans[h.pixels]==expected&&h.temporaryAllocations==1&&h.frees==1&&h.locks==1&&h.unlocks==1);
        ++generatedCount;
    }
    assert(generatedCount==16);
    std::cout<<"PASS "<<whole<<" exact-span original-captured PCX creation profiles/repeated calls and "
             <<prefixes<<" tight-file source prefixes plus "<<generatedCount<<" exact-size changed-depth allocations/conversions; ASAN/UBSAN\n";
}
