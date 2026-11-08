#include "SceneStartupCompositionRuntime.h"
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
constexpr uint32_t baseToken=0x3000000;
void take(gzFile f,void*p,uint32_t n){assert(gzread(f,p,n)==int(n));}
struct Effect{uint32_t f,t,mask,value;std::vector<uint32_t>args;std::array<uint8_t,32>digest;std::vector<std::array<uint32_t,2>>patches;std::vector<std::vector<uint8_t>>buffers,outputs;};
struct Replay {
 uint32_t imageStart=0;std::vector<uint8_t>heap,image;std::map<uint32_t,std::vector<uint32_t>>objects;std::vector<Effect>effects;size_t next=0;
 ClawSceneStartupCompositionContext c{};ClawSinglePlayerSceneContext startup{};ClawSinglePlayerSceneGlobals sg{};ClawSceneCameraGlobals cg{};ClawSceneLifecycleContext life{};ClawSceneDisplayContext display{};ClawGraphicsManagerLifecycleContext graphics{};ClawGraphicsManagerLifecycleGlobals gg{};ClawPaletteResourceContext palette{};ClawPaletteResourceGlobals pg{};ClawAudioManagerLifecycleContext audio{};ClawWorldFileContext world{};ClawImageRegistryContext registry{};ClawGameImageGlobals images{};ClawBootyResultsContext collections{};
 void object(uint32_t t,uint32_t n){assert(n&&!(n&3));objects[t]=std::vector<uint32_t>(n/4);std::memcpy(objects[t].data(),heap.data()+t-baseToken,n);}
 void commit(){for(auto&[t,v]:objects)std::memcpy(heap.data()+t-baseToken,v.data(),v.size()*4);}void refresh(){for(auto&[t,v]:objects)std::memcpy(v.data(),heap.data()+t-baseToken,v.size()*4);}
 uint32_t*span(uint32_t t,uint32_t n){if(t&3)return nullptr;uint64_t end=uint64_t(t)+4ull*n;for(auto&[begin,v]:objects)if(t>=begin&&t<uint64_t(begin)+v.size()*4)return end<=uint64_t(begin)+v.size()*4?v.data()+(t-begin)/4:nullptr;if(t>=baseToken&&end<=baseToken+heap.size())return reinterpret_cast<uint32_t*>(heap.data()+t-baseToken);if(t>=imageStart&&end<=imageStart+image.size())return reinterpret_cast<uint32_t*>(image.data()+t-imageStart);return nullptr;}
 std::vector<uint8_t>raw(){commit();auto b=heap;b.insert(b.end(),image.begin(),image.end());return b;}
 uint32_t service(const ClawSceneStartupCompositionCall&q){assert(next<effects.size());auto&e=effects[next++];assert(q.function==e.f&&q.receiver==e.t&&q.argumentCount==e.args.size()&&q.localMask==e.mask&&q.bufferCount==e.buffers.size());assert(std::equal(e.args.begin(),e.args.end(),q.arguments));auto b=raw();std::array<uint8_t,32>digest{};CC_SHA256(b.data(),CC_LONG(b.size()),digest.data());assert(digest==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
  for(auto p:e.patches){auto off=p[0];if(off<heap.size())heap[off]=uint8_t(p[1]);else image[off-heap.size()]=uint8_t(p[1]);}if(q.function==0x4f63ec&&e.value)object(e.value,q.arguments[0]);refresh();for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());return e.value;
 }
 void context(ClawSceneActorHost h){c={};startup={};life={};display={};graphics={};palette={};audio={};world={};registry={};collections={};sg={};cg={};gg={};pg={};images={};startup.host=h;startup.globals=&sg;startup.camera=&cg;claw_single_player_scene_defaults(&startup);graphics.scene=h;graphics.globals=&gg;graphics.maximumOperations=1000000;display.scene=h;display.graphics=&graphics;display.image=&images;display.maximumOperations=1000000;palette.scene=h;palette.globals=&pg;palette.systemPaletteScratchToken=baseToken+0xa000;claw_palette_resource_defaults(&palette);audio.scene=h;audio.maximumTraversal=1000000;world.scene=h;world.composeSpatial=1;registry.scene=h;registry.images=&images;life.scene=h;life.display=&display;life.graphics=&graphics;life.palette=&palette;life.audio=&audio;life.world=&world;life.image=&images;life.maximumOperations=1000000;collections.scene=h;collections.composeNumbers=1;collections.maximumSteps=1000000;c.scene=h;c.startup=&startup;c.lifecycle=&life;c.display=&display;c.graphics=&graphics;c.palette=&palette;c.audio=&audio;c.world=&world;c.imageRegistry=&registry;c.images=&images;c.collections=&collections;c.maximumOperations=1000000;}
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}uint32_t clock(void*){return 1000;}uint32_t dependency(ClawSceneStartupCompositionContext*,const ClawSceneStartupCompositionCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
}
int main(int argc,char**argv){assert(argc==2);auto f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"SCMP",4));uint32_t dims[4];take(f,dims,16);Replay r;r.heap.resize(dims[0]);r.imageStart=dims[1];r.image.resize(dims[2]);size_t snapshots=0;
 for(uint32_t i=0;i<dims[3];++i){uint32_t h[7];take(f,h,28);std::vector<uint32_t>a(h[2]);take(f,a.data(),h[2]*4);take(f,r.heap.data(),dims[0]);take(f,r.image.data(),dims[2]);r.objects.clear();r.object(baseToken+0x1000,60);for(uint32_t token:{baseToken+0x2000,baseToken+0x4000,baseToken+0x6000})r.object(token,4);for(uint32_t token:{baseToken+0x3000,baseToken+0x5000,baseToken+0x7000})r.object(token,256);for(uint32_t j=0;j<h[5];++j){uint32_t row[2];take(f,row,8);r.object(row[0],row[1]);}r.context({&r,lookup,nullptr,nullptr,nullptr,clock});r.next=0;r.effects.clear();
  for(uint32_t j=0;j<h[6];++j){uint32_t row[7];take(f,row,28);Effect e{};e.f=row[0];e.t=row[1];e.mask=row[3];e.value=row[4];e.args.resize(row[2]);take(f,e.args.data(),row[2]*4);take(f,e.digest.data(),32);for(uint32_t k=0;k<row[5];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),v(n);take(f,b.data(),n);take(f,v.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(v));}e.patches.resize(row[6]);for(auto&p:e.patches)take(f,p.data(),8);r.effects.push_back(std::move(e));}
  std::vector<uint8_t>expected(dims[0]+dims[2]);take(f,expected.data(),uint32_t(expected.size()));uint32_t value=0;assert(claw_scene_startup_composition_entry(h[0],h[1],a.data(),uint32_t(a.size()),&r.c,dependency,&r,&value)&&!r.c.fault);assert(r.next==r.effects.size());if(h[4])assert(value==h[3]);assert(r.raw()==expected);snapshots+=r.next;
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u exact-sized scene startup replays /%zu callback snapshots ASAN/UBSAN\n",dims[3],snapshots);
}
