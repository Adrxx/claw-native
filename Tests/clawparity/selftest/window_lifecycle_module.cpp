// Independent synthetic registration/create caller; no native game implementation.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t f) { return f==0x401000 || f==0x401300 ? 0 : -1; }
ClawSourceContract contract(uint32_t) { return {0x7ff,0x7ff,0x472,0}; }
uint32_t body(claw::Run &run,uint32_t f,uint32_t,const uint32_t *) {
 auto &s=run.source(); ClawSourceContext child=s; uint32_t value;
 if(f==0x401300) {
  child.esp-=4;child.eip=0x401000;run.put(child.esp,0x401305);
  value=run.source_call(0x401000,0,0x401305,child);
 } else {
  const uint32_t descriptor[]={8,0x401400,0,0,0x51,0x111,0x222,0x333,0,0x402200};
  for(unsigned i=0;i<10;++i)run.put(0x402100+4*i,descriptor[i]);
  child.esp-=8;child.eip=0x402000;run.put(child.esp,0x40106f);run.put(child.esp+4,0x402100);
  run.source_call(0x402000,0,0x40106f,child,{0x402100},0,4);
  const uint32_t args[]={0x40008,0x402200,0x402220,0x80080000,0,0,640,480,0,0,0x51,0};
  child.esp-=52;child.eip=0x402004;run.put(child.esp,0x4010b1);
  for(unsigned i=0;i<12;++i)run.put(child.esp+4+4*i,args[i]);
  value=run.source_call(0x402004,0,0x4010b1,child,{0x40008,0x402200,0x402220,0x80080000,0,0,640,480,0,0,0x51,0},0,48);
  run.put(0x402050,value);
  child.esp-=12;child.eip=0x40200c;run.put(child.esp,0x4010bf);run.put(child.esp+4,value);run.put(child.esp+8,1);
  run.source_call(0x40200c,0,0x4010bf,child,{value,1},0,8);
  value=0x99;child.eax=value;
 }
 std::memcpy(&s.eax,&child.eax,11*sizeof(uint32_t));return value;
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_window_lifecycle_entry,owned,contract,body)
