#include "V13Contact.h"
#include "ClawRuntime.h"
#include <array>
#include <cstring>
#include <memory>
#include <vector>
extern "C" uint32_t claw_v13_contact_bindings_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
constexpr uint32_t base=0x10000000,actor=base,scene=base+0x200,registry=base+0x300;
constexpr uint32_t table=base+0x400,metadata=base+0x500,logic=base+0x600,primary=base+0x800;
constexpr uint32_t instance=base+0xa00,instanceTable=base+0xb00,registerEntry=0x71000000;
struct Binding {
 std::array<uint8_t,0x1000> memory{};
 std::vector<uint8_t> stack=std::vector<uint8_t>(CLAW_STACK_END-CLAW_STACK_BASE);
 uint32_t methods[8]{0,0,0,0,0,0x4c8440,0,0x4c83f0};
 bool registered=false,allocated=false;
 ClawHost host{};
 Binding(uint32_t identity,uint32_t sceneIdentity) {
  host.user=this;host.bytes=bytes;host.call=call;
  put(actor+4,identity);put(actor+0xc,scene);put(scene+0x14,registry);put(scene+4,sceneIdentity);
  put(registry,table);put(table+0x1c,registerEntry);put(actor+0x7c,primary);
  put(primary+0x18,instance);put(instance,instanceTable);put(instanceTable+0x20,0x40b630);
 }
 uint32_t get(uint32_t p) {uint32_t v=0;auto b=bytes(this,p,4);if(b)std::memcpy(&v,b,4);return v;}
 void put(uint32_t p,uint32_t v) {auto b=bytes(this,p,4);if(b)std::memcpy(b,&v,4);}
 static uint8_t *bytes(void *u,uint32_t p,uint32_t n) {
  auto &s=*static_cast<Binding*>(u);
  if(p>=base && uint64_t(p-base)+n<=s.memory.size())return s.memory.data()+p-base;
  if(p>=CLAW_STACK_BASE && uint64_t(p-CLAW_STACK_BASE)+n<=s.stack.size())return s.stack.data()+p-CLAW_STACK_BASE;
  if(p>=0x513f68 && uint64_t(p-0x513f68)+n<=sizeof(s.methods))return reinterpret_cast<uint8_t*>(s.methods)+p-0x513f68;
  return nullptr;
 }
 static uint32_t call(void *u,const ClawCall *c) {
  auto &s=*static_cast<Binding*>(u);
  if(c->function==0x4fc6b4 && c->argumentCount==2 && c->receiver==registry+0x10) {
   // Native dictionary for the fixed names elected by this binding owner.
   bool found=c->arguments[0]==0x520d84 || c->arguments[0]==0x520d78 || (c->arguments[0]==0x521178 && s.registered);
   if(found)s.put(c->arguments[1],metadata);return found;
  }
  if(c->function==registerEntry && c->argumentCount==3 && c->receiver==registry &&
     c->arguments[0]==0x4def30 && c->arguments[1]==0x521178 && c->arguments[2]==2) {
   s.registered=true;s.put(metadata+0x10,c->arguments[0]);return metadata;
  }
  if(c->function==0x4fcaea && c->argumentCount==1 && c->arguments[0]==0x17c && !s.allocated) {s.allocated=true;return logic;}
  if(c->function==0x4c83f0 || c->function==0x4c8440 || c->function==0x40b630) {
   uint32_t result=0;claw_v13_contact_bindings_entry(c->function,c->receiver,c->arguments,c->argumentCount,&s.host,&result);return result;
  }
  s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=c->function;return 0;
 }
 uint32_t invoke(uint32_t f,uint32_t r,const uint32_t *a,uint32_t n) {
  uint32_t result=0;
  if(!claw_v13_contact_bindings_entry(f,r,a,n,&host,&result) && !host.fault)host.fault=CLAW_FAULT_ABI;
  return result;
 }
};
}
extern "C" void *claw_v13_bump_create(uint32_t identity,uint32_t sceneIdentity,uint32_t *fault) {
 auto binding=std::make_unique<Binding>(identity,sceneIdentity);uint32_t a=actor;
 binding->invoke(0x404400,0,&a,1);a=0x521178;binding->invoke(0x4c78f0,actor,&a,1);
 if(fault)*fault=binding->host.fault;
 if(binding->host.fault || binding->get(logic+0x10)!=0x4def30)return nullptr;
 return binding.release();
}
extern "C" void claw_v13_bump_destroy(void *p) {
 std::unique_ptr<Binding> binding(static_cast<Binding*>(p));if(binding)binding->invoke(0x4c8440,logic,nullptr,0);
}
extern "C" uint32_t claw_v13_bump_invoke(void *p,uint32_t *fault) {
 if(!p) {if(fault)*fault=CLAW_FAULT_ABI;return 0;}
 auto &binding=*static_cast<Binding*>(p);uint32_t a=actor;
 auto result=binding.invoke(0x4def30,0,&a,1);if(fault)*fault=binding.host.fault;return result;
}
