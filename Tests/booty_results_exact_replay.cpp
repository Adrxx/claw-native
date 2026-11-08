#include "BootyResultsRuntime.h"
#include <CommonCrypto/CommonDigest.h>
#include <zlib.h>
#include <cassert>
#include <array>
#include <algorithm>
#include <map>
#include <vector>
#include <cstring>
#include <cstdio>
namespace {
constexpr uint32_t base=0x3000000;
void take(gzFile f,void*p,uint32_t n){assert(gzread(f,p,n)==int(n));}
struct Effect{std::array<uint32_t,48>w{};std::array<uint8_t,32>digest{};std::vector<uint8_t>name;std::vector<std::array<uint32_t,2>>patches;std::vector<std::vector<uint8_t>>buffers,outputs;};
struct Replay{uint32_t imageStart=0;std::vector<uint8_t>heap,image;ClawBootyResultsContext c{};ClawCheckpointTimerGlobals ng{};ClawCheckpointTimerContext nc{};std::vector<Effect>effects;size_t next=0;std::map<uint32_t,std::vector<uint32_t>>objects;
 void commit(){for(auto&[t,v]:objects)std::memcpy(heap.data()+t-base,v.data(),v.size()*4);}void refresh(){for(auto&[t,v]:objects)std::memcpy(v.data(),heap.data()+t-base,v.size()*4);}
 uint32_t word(uint32_t t){uint32_t v;std::memcpy(&v,heap.data()+t-base,4);return v;}
 void object(uint32_t t,uint32_t n){if(!t||objects.count(t))return;auto&v=objects[t];v.resize(n);std::memcpy(v.data(),heap.data()+t-base,n*4);}
 void prepare(){objects.clear();object(base+0x3000,97);object(base+0x11000,109);object(base+0x12000,93);object(base+0x13000,46);object(base+0x14000,13);object(base+0x1000,77);for(uint32_t i=0;i<9;++i){auto a=word(base+0x3000+348+i*4);if(a<base||a>=base+heap.size())continue;object(a,109);auto l=word(a+108);if(l>=base&&l<base+heap.size()){object(l,93);auto p=word(l+24);if(p>=base&&p<base+heap.size())object(p,46);}}}
 uint32_t*span(uint32_t t,uint32_t n){auto end=uint64_t(t)+uint64_t(n)*4;if(t%4)return nullptr;for(auto&[begin,v]:objects)if(t>=begin&&t<begin+v.size()*4)return end<=uint64_t(begin)+v.size()*4?v.data()+(t-begin)/4:nullptr;if(t>=base&&end<=base+heap.size())return reinterpret_cast<uint32_t*>(heap.data()+t-base);if(t>=imageStart&&end<=imageStart+image.size())return reinterpret_cast<uint32_t*>(image.data()+t-imageStart);return nullptr;}
 std::vector<uint8_t>raw(){commit();auto v=heap;v.insert(v.end(),image.begin()+0x520000-imageStart,image.begin()+0x550000-imageStart);return v;}
 uint32_t service(const ClawBootyResultsCall&q){assert(next<effects.size());auto&e=effects[next++];if(q.function!=e.w[0]||q.receiver!=e.w[1]||q.argumentCount!=e.w[2]){std::fprintf(stderr,"event %zu expected%x got%x receiver%x/%x\n",next,e.w[0],q.function,e.w[1],q.receiver);std::abort();}assert(std::equal(q.arguments,q.arguments+q.argumentCount,e.w.begin()+3));assert(q.localMask==e.w[43]);assert(q.bufferCount==e.w[47]);const char*name=q.name;assert(e.name.size()==(name?std::strlen(name):0));if(name)assert(std::equal(e.name.begin(),e.name.end(),name));auto v=raw();std::array<uint8_t,32>d{};CC_SHA256(v.data(),CC_LONG(v.size()),d.data());assert(d==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
 for(auto p:e.patches){auto t=p[0]*4;if(t<heap.size())std::memcpy(heap.data()+t,&p[1],4);else std::memcpy(image.data()+0x520000-imageStart+t-heap.size(),&p[1],4);}refresh();if(q.function==0x4f63ec&&e.w[44])object(e.w[44],(q.arguments[0]+3)/4);if(q.function==0x4c8da0&&e.w[44]){object(e.w[44],109);object(word(e.w[44]+108),93);}for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());return e.w[44];}
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}uint32_t dependency(ClawBootyResultsContext*,const ClawBootyResultsCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
}
int main(int argc,char**argv){assert(argc==2);auto f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"BREZ",4));std::array<uint32_t,4>dims{};take(f,dims.data(),16);Replay r;r.imageStart=dims[0];std::vector<uint8_t>seed(dims[1]);take(f,seed.data(),dims[1]);r.heap.resize(dims[2]);uint32_t count=0;
 for(uint32_t i=0;i<dims[3];++i){std::array<uint32_t,16>h{};take(f,h.data(),sizeof h);r.image=seed;take(f,r.heap.data(),dims[2]);take(f,r.image.data()+0x520000-r.imageStart,0x30000);r.prepare();r.c={};r.c.scene={&r,lookup,nullptr,nullptr,nullptr,nullptr};r.c.maximumSteps=100000;r.c.composeNumbers=h[10];r.c.composeAnimation=h[11];r.c.composeImages=h[12];r.ng={};r.ng.managerToken=base+0x1000;r.ng.right=640;r.ng.bottom=480;r.nc={};r.nc.scene=r.c.scene;r.nc.globals=&r.ng;r.c.numbers=&r.nc;r.effects.clear();r.next=0;
 for(uint32_t j=0;j<h[15];++j){Effect e;take(f,e.w.data(),sizeof e.w);take(f,e.digest.data(),32);e.name.resize(e.w[45]);if(e.w[45])take(f,e.name.data(),e.w[45]);e.patches.resize(e.w[46]);for(auto&p:e.patches)take(f,p.data(),8);for(uint32_t k=0;k<e.w[47];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),a(n);take(f,b.data(),n);take(f,a.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(a));}r.effects.push_back(std::move(e));}
 std::vector<uint8_t>expected(r.heap.size()+0x30000);take(f,expected.data(),uint32_t(expected.size()));uint32_t out=0;auto ok=claw_booty_results_entry(h[0],h[1],h.data()+3,h[2],&r.c,dependency,&r,&out);if(!ok||r.c.fault)std::fprintf(stderr,"case%u f%x fault%u\n",i,h[0],r.c.fault);assert(ok&&!r.c.fault);assert(r.next==r.effects.size());if(h[14])assert(out==h[13]);assert(r.raw()==expected);count+=uint32_t(r.next);
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u source-matched exact-sized Results replays/%u full snapshots ASAN/UBSAN\n",dims[3],count);
}
