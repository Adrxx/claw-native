#include "SurfaceBlitRuntime.h"
#include <CommonCrypto/CommonDigest.h>
#include <zlib.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <vector>
namespace {
constexpr uint32_t base=0x3000000,dr=base+0x5000,sr=base+0x5100,pair=base+0x5200;
void take(gzFile f,void*p,uint32_t n){assert(gzread(f,p,n)==int(n));}
struct Effect{uint32_t f,t,mask,value;std::vector<uint32_t>a;std::array<uint8_t,32>digest;std::vector<std::array<uint32_t,2>>patches;std::vector<std::vector<uint8_t>>buffers,outputs;};
struct Replay{
 uint32_t imageStart=0;std::vector<uint8_t>heap,image;std::map<uint32_t,std::vector<uint32_t>>objects;std::vector<Effect>effects;size_t next=0;
 ClawSurfaceBlitContext c{};ClawPCXImageContext pcx{};ClawGameImageGlobals images{};
 uint32_t*span(uint32_t t,uint32_t n){if(t&3)return nullptr;uint64_t end=uint64_t(t)+4ull*n;for(auto&[begin,v]:objects)if(t>=begin&&t<uint64_t(begin)+4*v.size())return end<=uint64_t(begin)+4*v.size()?v.data()+(t-begin)/4:nullptr;if(t>=base&&end<=base+heap.size())return reinterpret_cast<uint32_t*>(heap.data()+t-base);if(t>=imageStart&&end<=imageStart+image.size())return reinterpret_cast<uint32_t*>(image.data()+t-imageStart);return nullptr;}
 void refresh(){for(auto&[t,v]:objects)std::memcpy(v.data(),heap.data()+t-base,4*v.size());}
 std::vector<uint8_t>raw(){for(auto&[t,v]:objects)std::memcpy(heap.data()+t-base,v.data(),4*v.size());auto b=heap;b.insert(b.end(),image.begin(),image.end());return b;}
 uint32_t service(const ClawSurfaceBlitCall&q){assert(next<effects.size());auto&e=effects[next++];assert(q.function==e.f&&q.receiver==e.t&&q.argumentCount==e.a.size()&&q.localMask==e.mask&&q.bufferCount==e.buffers.size());assert(std::equal(e.a.begin(),e.a.end(),q.arguments));auto b=raw();std::array<uint8_t,32>digest{};CC_SHA256(b.data(),CC_LONG(b.size()),digest.data());assert(digest==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
  for(auto p:e.patches){if(p[0]<heap.size())heap[p[0]]=uint8_t(p[1]);else image[p[0]-heap.size()]=uint8_t(p[1]);}refresh();for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());return e.value;}
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}uint32_t dependency(ClawSurfaceBlitContext*,const ClawSurfaceBlitCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
}
int main(int argc,char**argv){assert(argc==2);gzFile f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"SBLT",4));uint32_t dims[5];take(f,dims,20);Replay r;r.heap.resize(dims[0]);r.imageStart=dims[1];r.image.resize(dims[2]);for(uint32_t i=0;i<dims[4];++i){uint32_t row[2];take(f,row,8);assert(row[1]&&!(row[1]&3));r.objects[row[0]]=std::vector<uint32_t>(row[1]/4);}size_t snapshots=0;
 for(uint32_t i=0;i<dims[3];++i){uint32_t h[7];take(f,h,28);ClawSurfaceBlitArguments a{};take(f,a.words,20);a.count=h[2];take(f,r.heap.data(),dims[0]);take(f,r.image.data(),dims[2]);r.refresh();r.effects.clear();r.next=0;r.images={};r.pcx={};r.c={};r.c.scene={&r,lookup,nullptr,nullptr,nullptr,nullptr};r.pcx.scene=r.c.scene;r.pcx.image=&r.images;r.pcx.composeImage=1;r.pcx.maximumOperations=65536;r.c.pcx=&r.pcx;r.c.image=&r.images;r.c.maximumOperations=65536;
  if(h[3]&1)a.destination=r.span(dr,4);if(h[3]&(h[0]==0x4b9ce0?4u:h[0]==0x4b9d80?8u:2u))a.source=r.span(h[0]==0x4b9950?pair:sr,h[0]==0x4b9950?2:4);
  for(uint32_t j=0;j<h[6];++j){uint32_t row[7];take(f,row,28);Effect e{};e.f=row[0];e.t=row[1];e.mask=row[3];e.value=row[4];e.a.resize(row[2]);take(f,e.a.data(),row[2]*4);take(f,e.digest.data(),32);for(uint32_t k=0;k<row[5];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),v(n);take(f,b.data(),n);take(f,v.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(v));}e.patches.resize(row[6]);for(auto&p:e.patches)take(f,p.data(),8);r.effects.push_back(std::move(e));}
  std::vector<uint8_t>expected(dims[0]+dims[2]);take(f,expected.data(),uint32_t(expected.size()));auto originalPCX=r.pcx;auto originalHost=r.c.scene;uint32_t out=0;assert(claw_surface_blit_entry(h[0],h[1],a,&r.c,dependency,&r,&out)&&!r.c.fault);assert(r.next==r.effects.size());if(h[5])assert(out==h[4]);assert(r.raw()==expected);assert(!std::memcmp(&originalPCX,&r.pcx,sizeof(r.pcx)));assert(!std::memcmp(&originalHost,&r.c.scene,sizeof(originalHost)));snapshots+=r.next;
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u exact-sized surface blit calls /%zu callback snapshots ASAN/UBSAN\n",dims[3],snapshots);
}
