#include "InterfaceReadCompositionRuntime.h"
#include <CommonCrypto/CommonDigest.h>
#include <zlib.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <memory>
#include <vector>
namespace {
constexpr uint32_t base=0x3000000,file=base+0x8000,archive=base+0x8100,scratch=base+0x8200;
void take(gzFile f,void*p,uint32_t n){assert(gzread(f,p,n)==int(n));}
struct Object{uint32_t size;std::unique_ptr<uint8_t[]>bytes;};
struct Effect{uint32_t f,t,mask,value;std::vector<uint32_t>args;std::array<uint8_t,32>digest;std::vector<std::array<uint32_t,2>>patches;std::vector<std::vector<uint8_t>>buffers,outputs;};
struct Replay{
 std::vector<uint8_t>heap,image;std::map<uint32_t,Object>objects;std::vector<Effect>effects;size_t next=0;uint32_t imageStart=0,function=0;ClawInterfaceFileContext c{};
 void object(uint32_t t,uint32_t n){if(!n)n=1;Object o{n,std::make_unique<uint8_t[]>(n)};std::memcpy(o.bytes.get(),heap.data()+t-base,n);objects[t]=std::move(o);}
 void commit(){for(auto&[t,o]:objects)std::memcpy(heap.data()+t-base,o.bytes.get(),o.size);}
 void refresh(){for(auto&[t,o]:objects)std::memcpy(o.bytes.get(),heap.data()+t-base,o.size);}
 uint32_t*span(uint32_t t,uint32_t n){if(t%4)return nullptr;uint64_t end=uint64_t(t)+uint64_t(n)*4;for(auto&[begin,o]:objects)if(t>=begin&&t<uint64_t(begin)+o.size)return end<=uint64_t(begin)+((o.size+3)&~3u)?reinterpret_cast<uint32_t*>(o.bytes.get()+t-begin):nullptr;if(t>=base&&end<=base+heap.size())return reinterpret_cast<uint32_t*>(heap.data()+t-base);if(t>=imageStart&&end<=imageStart+image.size())return reinterpret_cast<uint32_t*>(image.data()+t-imageStart);return nullptr;}
 std::vector<uint8_t>raw(){commit();auto b=heap;std::fill_n(b.begin()+scratch-base,4,0);if(function==0x4dcdf0||function==0x4dcd10)for(auto[t,n]:{std::pair<uint32_t,uint32_t>{file,40},{archive,68}})std::fill_n(b.begin()+t-base,n,0);b.insert(b.end(),image.begin()+0x520000-imageStart,image.begin()+0x550000-imageStart);return b;}
 uint32_t service(const ClawInterfaceFileCall&q){assert(next<effects.size());auto&e=effects[next++];assert(q.function==e.f&&q.receiver==e.t&&q.argumentCount==e.args.size()&&q.localMask==e.mask&&q.bufferCount==e.buffers.size());assert(std::equal(e.args.begin(),e.args.end(),q.arguments));auto b=raw();std::array<uint8_t,32>digest{};CC_SHA256(b.data(),CC_LONG(b.size()),digest.data());assert(digest==e.digest);for(size_t i=0;i<e.buffers.size();++i){assert(q.bufferBytes[i]==e.buffers[i].size());assert(!std::memcmp(q.buffers[i],e.buffers[i].data(),e.buffers[i].size()));}
  for(auto p:e.patches){uint32_t off=p[0];if(off<heap.size())heap[off]=uint8_t(p[1]);else image[0x520000-imageStart+off-heap.size()]=uint8_t(p[1]);}if(q.function==0x4f63ec&&e.value)object(e.value,q.arguments[0]);refresh();for(size_t i=0;i<e.outputs.size();++i)std::memcpy(q.buffers[i],e.outputs[i].data(),e.outputs[i].size());return e.value;
 }
};
uint32_t*lookup(void*u,uint32_t t,uint32_t n){return static_cast<Replay*>(u)->span(t,n);}
uint32_t dependency(ClawInterfaceFileContext*,const ClawInterfaceFileCall*q,void*u){return static_cast<Replay*>(u)->service(*q);}
}
int main(int argc,char**argv){assert(argc==2);auto f=gzopen(argv[1],"rb");assert(f);char magic[4];take(f,magic,4);assert(!std::memcmp(magic,"IFCR",4));uint32_t dims[4];take(f,dims,16);Replay r;r.imageStart=dims[0];std::vector<uint8_t>seed(dims[1]);take(f,seed.data(),dims[1]);r.heap.resize(dims[2]);size_t snapshots=0;
 for(uint32_t i=0;i<dims[3];++i){uint32_t h[7];take(f,h,28);std::vector<uint32_t>a(h[2]);take(f,a.data(),h[2]*4);r.function=h[0];r.image=seed;take(f,r.heap.data(),dims[2]);take(f,r.image.data()+0x520000-r.imageStart,0x30000);r.objects.clear();for(uint32_t j=0;j<h[5];++j){uint32_t row[2];take(f,row,8);r.object(row[0],row[1]);}r.c={};r.c.scene={&r,lookup,nullptr,nullptr,nullptr,nullptr};r.c.memoryFileToken=file;r.c.archiveToken=archive;r.c.stringScratchToken=scratch;r.c.maximumOperations=2000000;r.next=0;r.effects.clear();
  for(uint32_t j=0;j<h[6];++j){uint32_t row[7];take(f,row,28);Effect e{};e.f=row[0];e.t=row[1];e.mask=row[3];e.value=row[4];e.args.resize(row[2]);take(f,e.args.data(),row[2]*4);take(f,e.digest.data(),32);e.patches.resize(row[5]);for(auto&p:e.patches)take(f,p.data(),8);for(uint32_t k=0;k<row[6];++k){uint32_t n;take(f,&n,4);std::vector<uint8_t>b(n),v(n);take(f,b.data(),n);take(f,v.data(),n);e.buffers.push_back(std::move(b));e.outputs.push_back(std::move(v));}r.effects.push_back(std::move(e));}
  std::vector<uint8_t>expected(r.heap.size()+0x30000);take(f,expected.data(),uint32_t(expected.size()));uint8_t finalFile[40],finalArchive[68];take(f,finalFile,40);take(f,finalArchive,68);uint32_t value=0;uint32_t completed=0;if(h[0]==0x4dcdf0){ClawInterfaceMemoryLoad p{a[0],a[1],a[2],a[3],{a[4],a[5],a[6]}};completed=claw_interface_read_memory(h[1],&p,&r.c,dependency,&r,&value);}else completed=claw_interface_read_composition_entry(h[0],h[1],a.data(),uint32_t(a.size()),&r.c,dependency,&r,&value);assert(completed&&!r.c.fault);assert(r.next==r.effects.size());if(h[4])assert(value==h[3]);assert(r.raw()==expected);assert(!std::memcmp(r.span(file,10),finalFile,40)&&!std::memcmp(r.span(archive,17),finalArchive,68));snapshots+=r.next;
 }assert(gzgetc(f)==-1);gzclose(f);std::printf("PASS %u exact-sized IFC replays /%zu callback snapshots ASAN/UBSAN\n",dims[3],snapshots);
}
