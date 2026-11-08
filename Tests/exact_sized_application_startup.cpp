#include "ApplicationStartupRuntime.h"
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
constexpr uint32_t base=0x3000000,app=base+0x100,automatic=base+0x800,command=base+0x500;
void take(gzFile f,void*p,uint32_t n){assert(gzread(f,p,n)==int(n));}
struct Effect{uint32_t f,t,value,mask;std::vector<uint32_t>a;std::array<uint8_t,32>digest;std::vector<std::pair<uint32_t,uint8_t>>patches;std::vector<std::vector<uint8_t>>buffers,outputs;};
struct Replay{
 uint32_t imageStart=0;std::vector<uint8_t>heap,image;std::map<uint32_t,std::vector<uint8_t>>objects;std::vector<Effect>effects;size_t next=0;
 ClawApplicationStartupContext c{};ClawPlayerCacheApplicationContext players{};ClawSaveLoadContext load{};ClawResourceTableConstructionContext table{};ClawResourceArchiveLoadingContext archive{};ClawMusicContext music{};ClawMusicGlobals musicGlobals{};
 void object(uint32_t t,uint32_t n){assert(n);objects[t]=std::vector<uint8_t>(n);std::memcpy(objects[t].data(),heap.data()+t-base,n);}
 uint8_t*bytes(uint32_t t,uint32_t n){uint64_t end=uint64_t(t)+n;for(auto&[begin,v]:objects)if(t>=begin&&t<uint64_t(begin)+v.size())return end<=uint64_t(begin)+v.size()?v.data()+t-begin:nullptr;if(t>=imageStart&&end<=imageStart+image.size())return image.data()+t-imageStart;return nullptr;}
 uint32_t*span(uint32_t t,uint32_t n){return t&3?nullptr:reinterpret_cast<uint32_t*>(bytes(t,4*n));}
 void refresh(){for(auto&[t,v]:objects)std::memcpy(v.data(),heap.data()+t-base,v.size());}
 std::vector<uint8_t>raw(){for(auto&[t,v]:objects)std::memcpy(heap.data()+t-base,v.data(),v.size());auto b=heap;std::fill_n(b.data()+automatic-base,1200,0);b.insert(b.end(),image.begin(),image.end());return b;}
 uint32_t service(const ClawApplicationStartupCall&q){assert(next<effects.size());auto&e=effects[next++];assert(q.function==e.f&&q.receiver==e.t&&q.argumentCount==e.a.size()&&q.localMask==e.mask&&q.bufferCount==e.buffers.size());assert(std::equal(e.a.begin(),e.a.end(),q.arguments));auto b=raw();std::array<uint8_t,32>digest{};CC_SHA256(b.data(),CC_LONG(b.size()),digest.data());assert(digest==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
  for(auto p:e.patches){if(p.first<heap.size())heap[p.first]=p.second;else image[p.first-heap.size()]=p.second;}if(q.function==0x4f63ec&&e.value)object(e.value,q.arguments[0]);refresh();for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());if(q.function==0x4f6428)objects.erase(q.arguments[0]);return e.value;}
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}uint32_t dependency(ClawApplicationStartupContext*,const ClawApplicationStartupCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
uint8_t*byteLookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->bytes(t,n);}
}
int main(int argc,char**argv){assert(argc==2);gzFile f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"APST",4));uint32_t dims[5];take(f,dims,20);Replay r;r.heap.resize(dims[0]);r.imageStart=dims[1];r.image.resize(dims[2]);std::vector<std::array<uint32_t,2>>spans(dims[4]);for(auto&p:spans)take(f,p.data(),8);size_t snapshots=0;
 for(uint32_t i=0;i<dims[3];++i){uint32_t h[4];take(f,h,16);take(f,r.heap.data(),dims[0]);take(f,r.image.data(),dims[2]);r.objects.clear();for(auto p:spans)r.object(p[0],p[1]);for(uint32_t j=0;j<h[1];++j){uint32_t row[2];take(f,row,8);r.object(row[0],row[1]);}r.effects.clear();r.next=0;r.c={};r.players={};r.load={};r.table={};r.archive={};r.music={};r.musicGlobals={};r.c.scene={&r,lookup,nullptr,nullptr,nullptr,nullptr};r.c.players=&r.players;r.c.automaticToken=automatic;r.c.maximumOperations=1000000;r.c.byteContext=&r;r.c.bytes=byteLookup;r.players.scene=r.c.scene;r.players.saveLoad=&r.load;r.players.maximumOperations=1000000;r.table.scene=r.c.scene;r.table.maximumOperations=1000000;r.archive.table=&r.table;r.archive.headerToken=base+0x4c00;r.archive.maximumOperations=1000000;if(h[3]&1)r.c.archive=&r.archive;r.music.scene=r.c.scene;r.music.lookupBytes=byteLookup;r.music.globals=&r.musicGlobals;r.music.maximumTraversal=1000000;if(h[3]&2)r.c.music=&r.music;
  for(uint32_t j=0;j<h[2];++j){uint32_t row[7];take(f,row,28);Effect e{};e.f=row[0];e.t=row[1];e.value=row[3];e.mask=row[4];e.a.resize(row[2]);take(f,e.a.data(),row[2]*4);take(f,e.digest.data(),32);for(uint32_t k=0;k<row[5];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),v(n);take(f,b.data(),n);take(f,v.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(v));}for(uint32_t k=0;k<row[6];++k){uint32_t off;uint8_t value;take(f,&off,4);take(f,&value,1);e.patches.emplace_back(off,value);}r.effects.push_back(std::move(e));}
  std::vector<uint8_t>expected(dims[0]+dims[2]);take(f,expected.data(),uint32_t(expected.size()));auto originalPlayers=r.players;auto originalLoad=r.load;auto originalHost=r.c.scene;uint32_t out=0,a[]={base+0x400,command};assert(claw_application_startup_entry(0x425730,app,a,2,&r.c,dependency,&r,&out)&&!r.c.fault);assert(out==h[0]);assert(r.next==r.effects.size());assert(r.raw()==expected);assert(!std::memcmp(&originalPlayers,&r.players,sizeof(r.players)));assert(!std::memcmp(&originalLoad,&r.load,sizeof(r.load)));assert(!std::memcmp(&originalHost,&r.c.scene,sizeof(originalHost)));snapshots+=r.next;
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u exact-sized whole application startup calls /%zu callback snapshots ASAN/UBSAN\n",dims[3],snapshots);
}
