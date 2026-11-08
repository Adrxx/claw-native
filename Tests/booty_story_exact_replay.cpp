#include "BootyStoryRuntime.h"
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
struct Replay{uint32_t imageStart=0;std::vector<uint8_t>heap,image;ClawSpecialCommandGlobals g{};ClawSinglePlayerSceneGlobals bg{};ClawSinglePlayerSceneContext b{};ClawBootyProgressionContext progress{};ClawBootyStoryContext c{};ClawSceneDisplayContext display{};ClawCheckpointTimerGlobals ng{};ClawCheckpointTimerContext numbers{};ClawBootyResultsContext results{};std::vector<Effect>effects;size_t next=0;std::map<uint32_t,std::vector<uint32_t>>objects;
 void commit(){for(auto&[t,v]:objects)std::memcpy(heap.data()+t-base,v.data(),v.size()*4);}void refresh(){for(auto&[t,v]:objects)std::memcpy(v.data(),heap.data()+t-base,v.size()*4);}
 void object(uint32_t t,uint32_t n){objects[t]=std::vector<uint32_t>(n);std::memcpy(objects[t].data(),heap.data()+t-base,n*4);}
 void prepare(){objects.clear();for(auto [t,n]:{std::pair<uint32_t,uint32_t>{base+0x1000,0x134/4},{base+0x2000,0x160/4},{base+0x3000,364/4},{base+0x6000,15},{base+0x17000,109},{base+0x18000,93},{base+0x19000,109},{base+0x1a000,93}})object(t,n);}
 uint32_t*span(uint32_t t,uint32_t n){auto end=uint64_t(t)+uint64_t(n)*4;if(t%4)return nullptr;for(auto&[begin,v]:objects)if(t>=begin&&t<uint64_t(begin)+v.size()*4)return end<=uint64_t(begin)+v.size()*4?v.data()+(t-begin)/4:nullptr;if(t>=base&&end<=base+heap.size())return reinterpret_cast<uint32_t*>(heap.data()+t-base);if(t>=imageStart&&end<=imageStart+image.size())return reinterpret_cast<uint32_t*>(image.data()+t-imageStart);return nullptr;}
 std::vector<uint8_t>raw(){commit();auto v=heap;v.insert(v.end(),image.begin()+0x520000-imageStart,image.begin()+0x550000-imageStart);return v;}
 uint32_t service(const ClawBootyStoryCall&q){assert(next<effects.size());auto&e=effects[next++];assert(q.function==e.w[0]&&q.receiver==e.w[1]&&q.argumentCount==e.w[2]);assert(std::equal(q.arguments,q.arguments+q.argumentCount,e.w.begin()+3));assert(q.localMask==e.w[43]);assert(q.bufferCount==e.w[47]);const char*name=q.name;if(!name&&(q.function==0x4b7f20||q.function==0x4b7cd0||q.function==0x4f6286)){name=q.arguments[0]?reinterpret_cast<const char*>(span(q.arguments[0]&~3,1))+(q.arguments[0]&3):static_cast<const char*>(q.buffers[0]);}assert(e.name.size()==(name?std::strlen(name):0));if(name)assert(std::equal(e.name.begin(),e.name.end(),name));auto v=raw();std::array<uint8_t,32>d{};CC_SHA256(v.data(),CC_LONG(v.size()),d.data());assert(d==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
 for(auto p:e.patches){auto t=p[0]*4;if(t<heap.size())std::memcpy(heap.data()+t,&p[1],4);else std::memcpy(image.data()+0x520000-imageStart+t-heap.size(),&p[1],4);}if(q.function==0x4f63ec&&e.w[44])object(e.w[44],(q.arguments[0]+3)/4);refresh();for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());return e.w[44];}
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}uint32_t clock(void*u){ClawBootyStoryCall q{};q.function=0x546df0;return static_cast<Replay*>(u)->service(q);}
uint32_t dependency(ClawBootyStoryContext*,const ClawBootyStoryCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
}
int main(int argc,char**argv){assert(argc==2);auto f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"STRY",4));std::array<uint32_t,4>dims{};take(f,dims.data(),16);Replay r;r.imageStart=dims[0];std::vector<uint8_t>seed(dims[1]);take(f,seed.data(),dims[1]);r.heap.resize(dims[2]);uint32_t count=0;
 for(uint32_t i=0;i<dims[3];++i){std::array<uint32_t,24>h{};take(f,h.data(),sizeof h);r.image=seed;take(f,r.heap.data(),dims[2]);take(f,r.image.data()+0x520000-r.imageStart,0x30000);r.prepare();r.c={};r.c.scene={&r,lookup,nullptr,nullptr,nullptr,clock};r.c.composeProgression=h[8];r.c.composeAnimation=h[9];r.c.composeCreation=h[10];r.c.composeFrame=h[11];r.c.composeImages=h[12];r.c.maximumSteps=65536;r.progress={};r.progress.scene=r.c.scene;r.progress.globals=&r.g;r.progress.scratchToken=base+0x20000;r.progress.maximumSteps=65536;r.c.progression=&r.progress;r.display={};r.display.scene=r.c.scene;r.display.maximumOperations=65536;if(h[13])r.c.display=&r.display;r.numbers={};r.numbers.scene=r.c.scene;r.numbers.globals=&r.ng;r.numbers.composeHierarchy=1;r.results={};r.results.scene=r.c.scene;r.results.progression=&r.progress;r.results.numbers=&r.numbers;r.results.composeNumbers=1;r.results.maximumSteps=65536;if(h[14])r.c.results=&r.results;for(uint32_t j=0;j<h[18];++j){uint32_t row[2];take(f,row,8);r.object(row[0],row[1]);}r.effects.clear();r.next=0;
 for(uint32_t j=0;j<h[17];++j){Effect e;take(f,e.w.data(),sizeof e.w);take(f,e.digest.data(),32);e.name.resize(e.w[45]);if(e.w[45])take(f,e.name.data(),e.w[45]);e.patches.resize(e.w[46]);for(auto&p:e.patches)take(f,p.data(),8);for(uint32_t k=0;k<e.w[47];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),a(n);take(f,b.data(),n);take(f,a.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(a));}r.effects.push_back(std::move(e));}
 std::vector<uint8_t>expected(r.heap.size()+0x30000);take(f,expected.data(),uint32_t(expected.size()));uint32_t out=0;auto ok=claw_booty_story_entry(h[0],h[1],h.data()+3,h[2],&r.c,dependency,&r,&out);assert(ok&&!r.c.fault);assert(r.next==r.effects.size());if(h[16])assert(out==h[15]);assert(r.raw()==expected);count+=uint32_t(r.next);
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u source-matched exact-sized Story replays/%u full snapshots ASAN/UBSAN\n",dims[3],count);
}
