#include "PlayerMenuManagementRuntime.h"
#ifdef CLAW_TEST_MENU_ASSIGNMENT_PROBE
extern "C" uint32_t claw_test_menu_assignment_probe(uint32_t,uint32_t,ClawPlayerMenuManagementContext*,ClawPlayerMenuManagementDependency,void*,uint32_t*);
#endif
#include <CommonCrypto/CommonDigest.h>
#include <zlib.h>
#include <cassert>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <vector>
#include <cstring>
#include <cstdio>
namespace {
constexpr uint32_t base=0x3000000;
void take(gzFile f,void*p,uint32_t n){assert(gzread(f,p,n)==int(n));}
struct Effect{std::array<uint32_t,48>w{};std::array<uint8_t,32>digest{};std::vector<uint8_t>name;std::vector<std::array<uint32_t,2>>patches;std::vector<std::vector<uint8_t>>buffers,outputs;};
struct Replay{struct ByteCookie{Replay*owner;uint32_t magic;};ByteCookie saveCookie{this,0xc00c1e};uint32_t imageStart=0;std::vector<uint8_t>heap,image;ClawPlayerMenuManagementContext c{};ClawPlayerCacheApplicationContext cache{};ClawCStringAssignmentContext strings{};ClawPlayerFadeContext fade{};ClawPlayerFadeBlendContext blend{};ClawPlayerStartupContext startup{};ClawSaveLoadContext saved{};std::vector<Effect>effects;size_t next=0;std::map<uint32_t,std::vector<uint8_t>>objects;std::set<uint32_t>dead;
 void commit(){for(auto&[t,v]:objects)std::memcpy(heap.data()+t-base,v.data(),v.size());}void refresh(){for(auto&[t,v]:objects)std::memcpy(v.data(),heap.data()+t-base,v.size());}
 uint32_t word(uint32_t t){uint32_t v;std::memcpy(&v,heap.data()+t-base,4);return v;}
 void object(uint32_t t,uint32_t n){if(!t||objects.count(t))return;auto&v=objects[t];v.resize(n*4);std::memcpy(v.data(),heap.data()+t-base,n*4);}
 void prepare(){objects.clear();dead.clear();object(base+0x1000,22);object(base+0x2000,4);object(base+0x3000,65);object(base+0x4000,3);object(base+0x5000,1);object(base+0xb000,65);object(base+0x9000,64);for(uint32_t i=0;i<3;++i)object(base+0x10000+i*0x3000,2450);object(base+0x20000,77);object(base+0x21000,4);object(base+0x22000,15);object(base+0x23000,7);object(base+0x24000,47);object(base+0x25000,1);object(base+0x26000,11);object(base+0x27000,36);object(base+0x28000,8);object(base+0x29000,76);object(base+0x2a000,32);object(base+0x2a080,64);object(base+0x2a180,1);object(base+0x2a184,1);object(base+0x2a188,16);object(base+0x2b000,1);for(uint32_t i=0;i<3;++i)object(base+0xa000+i*16,3);}



 uint32_t*span(uint32_t t,uint32_t n){auto end=uint64_t(t)+uint64_t(n)*4;if(t%4)return nullptr;for(auto&[begin,v]:objects)if(t>=begin&&t<begin+v.size()){if(dead.count(begin)||end>uint64_t(begin)+v.size()){return nullptr;}return reinterpret_cast<uint32_t*>(v.data()+t-begin);}if(t>=imageStart&&end<=imageStart+image.size())return reinterpret_cast<uint32_t*>(image.data()+t-imageStart);return nullptr;}
 std::vector<uint8_t>raw(){commit();auto v=heap;v.insert(v.end(),image.begin()+0x520000-imageStart,image.begin()+0x550000-imageStart);return v;}
 std::vector<uint8_t>canonical(){auto v=raw();for(auto off:{0x3000u,0x4000u,0x5000u,0xb000u})std::fill_n(v.begin()+off,off==0x4000?12u:off==0x5000?4u:260u,0);std::fill_n(v.begin()+0x2a000,456,0);return v;}
 uint8_t*bytes(uint32_t t,uint32_t n){auto end=uint64_t(t)+n;for(auto&[begin,v]:objects)if(t>=begin&&t<begin+v.size()){if(dead.count(begin)||end>uint64_t(begin)+v.size())return nullptr;return v.data()+t-begin;}if(t>=imageStart&&end<=imageStart+image.size())return image.data()+t-imageStart;return nullptr;}
 uint32_t service(const ClawPlayerMenuManagementCall&q){assert(next<effects.size());auto&e=effects[next++];if(q.function!=e.w[0]||q.receiver!=e.w[1]||q.argumentCount!=e.w[2]){std::fprintf(stderr,"event %zu expected%x got%x receiver%x/%x\n",next,e.w[0],q.function,e.w[1],q.receiver);std::abort();}assert(std::equal(q.arguments,q.arguments+q.argumentCount,e.w.begin()+3));assert(q.localMask==e.w[43]);assert(q.bufferCount==e.w[47]);const char*name=q.name;assert(e.name.size()==(name?std::strlen(name):0));if(name)assert(std::equal(e.name.begin(),e.name.end(),name));auto v=canonical();std::array<uint8_t,32>d{};CC_SHA256(v.data(),CC_LONG(v.size()),d.data());assert(d==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
 for(auto p:e.patches){auto t=p[0]*4;if(t<heap.size())std::memcpy(heap.data()+t,&p[1],4);else std::memcpy(image.data()+0x520000-imageStart+t-heap.size(),&p[1],4);}refresh();if(q.function==0x4f63ec&&e.w[44]){auto&v=objects[e.w[44]];v.resize(q.arguments[0]);std::memcpy(v.data(),heap.data()+e.w[44]-base,v.size());}if(q.function==0x4c8da0&&e.w[44]){object(e.w[44],109);}for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());if(q.function==0x4f6428&&q.argumentCount)dead.insert(q.arguments[0]);if((q.function==0x429510||q.function==0x45fe40)&&q.argumentCount&&(q.arguments[0]&1))dead.insert(q.receiver);return e.w[44];}
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}
uint8_t*byteLookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->bytes(t,n);}
uint8_t*saveByteLookup(void*u,uint32_t t,uint32_t n){auto*c=static_cast<Replay::ByteCookie*>(u);assert(c&&c->magic==0xc00c1e&&c->owner);return c->owner->bytes(t,n);}
uint32_t dependency(ClawPlayerMenuManagementContext*,const ClawPlayerMenuManagementCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
}
int main(int argc,char**argv){assert(argc==2);auto f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"PMMG",4));std::array<uint32_t,4>dims{};take(f,dims.data(),16);Replay r;r.imageStart=dims[0];std::vector<uint8_t>seed(dims[1]);take(f,seed.data(),dims[1]);r.heap.resize(dims[2]);uint32_t count=0;
 for(uint32_t i=0;i<dims[3];++i){std::array<uint32_t,12>h{};take(f,h.data(),sizeof h);r.image=seed;take(f,r.heap.data(),dims[2]);take(f,r.image.data()+0x520000-r.imageStart,0x30000);r.prepare();for(uint32_t j=0;j<h[11];++j){std::array<uint32_t,3>pair{};take(f,pair.data(),12);auto &v=r.objects[pair[0]];v.resize(pair[1]);std::memcpy(v.data(),r.heap.data()+pair[0]-base,pair[1]);if(!pair[2])r.dead.insert(pair[0]);}r.c={};r.c.scene={&r,lookup,nullptr,nullptr,nullptr,nullptr};r.saved={};r.saved.save.scene=r.c.scene;r.saved.save.lookupBytes=byteLookup;r.saved.save.emptyStringToken=0x52e1c4;r.saved.save.fileScratchToken=base+0x2000;r.saved.save.pathScratchToken=base+0x3000;r.saved.save.securityScratchToken=base+0x4000;r.saved.save.countScratchToken=base+0x5000;r.saved.save.maximumTraversal=r.saved.save.maximumSteps=100000;r.saved.directoryScratchToken=base+0xb000;r.saved.maximumTraversal=100000;r.cache={};r.cache.scene=r.c.scene;r.cache.saveLoad=&r.saved;r.cache.automaticToken=base+0x29000;r.cache.composeSaveLoad=1;r.cache.maximumOperations=100000;r.c.playerCache=&r.cache;r.c.automaticToken=base+0x2a000;r.c.maximumOperations=100000;r.fade={};r.fade.scene=r.c.scene;r.blend={};r.blend.fade=&r.fade;r.strings={};r.strings.scene=r.c.scene;r.strings.byteContext=&r;r.strings.bytes=byteLookup;r.strings.allocation=&r.blend;r.strings.maximumOperations=100000;r.c.strings=&r.strings;r.c.composeStrings=1;r.startup={};r.startup.scene=r.c.scene;r.startup.composeCache=1;r.c.startup=&r.startup;if(h[8]&2){r.strings.bytes=nullptr;r.saved.save.scene.context=&r.saveCookie;r.saved.save.lookupBytes=saveByteLookup;}r.effects.clear();r.next=0;
 for(uint32_t j=0;j<h[10];++j){Effect e;take(f,e.w.data(),sizeof e.w);take(f,e.digest.data(),32);e.name.resize(e.w[45]);if(e.w[45])take(f,e.name.data(),e.w[45]);e.patches.resize(e.w[46]);for(auto&p:e.patches)take(f,p.data(),8);for(uint32_t k=0;k<e.w[47];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),a(n);take(f,b.data(),n);take(f,a.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(a));}r.effects.push_back(std::move(e));}
 std::vector<uint8_t>expected(r.heap.size()+0x30000);take(f,expected.data(),uint32_t(expected.size()));uint32_t out=0;uint32_t ok=0;
#ifdef CLAW_TEST_MENU_ASSIGNMENT_PROBE
 if(h[0]==0x4f66cc){ok=claw_test_menu_assignment_probe(h[1],h[3],&r.c,dependency,&r,&out);}else{ok=claw_player_menu_management_entry(h[0],h[1],h.data()+3,h[2],&r.c,dependency,&r,&out);}
#else
 ok=claw_player_menu_management_entry(h[0],h[1],h.data()+3,h[2],&r.c,dependency,&r,&out);
#endif
 if(!ok||r.c.fault)std::fprintf(stderr,"case%u f%x fault%u\n",i,h[0],r.c.fault);assert(ok&&!r.c.fault);assert(r.next==r.effects.size());if(h[8])assert(out==h[9]);auto finalRaw=r.canonical();if(finalRaw!=expected){for(size_t k=0;k<finalRaw.size();++k)if(finalRaw[k]!=expected[k]){std::fprintf(stderr,"case%u byte%zx got%x expected%x\n",i,k,finalRaw[k],expected[k]);break;}}assert(finalRaw==expected);count+=uint32_t(r.next);
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u source-matched exact-sized player-menu replays/%u full snapshots ASAN/UBSAN\n",dims[3],count);
}
