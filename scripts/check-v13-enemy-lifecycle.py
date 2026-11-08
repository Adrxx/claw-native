#!/usr/bin/env python3
"""Exercise native lifecycle composition; original admission is separate."""
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/v13-enemy-lifecycle-check'
SOURCE=r'''
#include "ClawRuntime.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <vector>
extern "C" uint32_t claw_v13_enemy_lifecycle_compat_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
// This v1.3 composition check never exercises the adapter's v1.0 fallback.
// Keep that link dependency fail-closed instead of pulling in unrelated AI.
extern "C" uint32_t claw_cut_throat_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*) {
 std::abort();
}
struct Row {uint32_t root,ctor,table,size;};
const Row rows[]={ROWS};
constexpr uint32_t actor=0x10000000,logic=actor+0x300,instance=actor+0x600;
struct Host {
 ClawHost host{};Row row;
 std::vector<uint8_t> arena=std::vector<uint8_t>(0x2000),image=std::vector<uint8_t>(0x20000),stack=std::vector<uint8_t>(CLAW_STACK_END-CLAW_STACK_BASE);
 std::vector<uint32_t> calls;bool allocationFailure=false,serviceFailure=false,redirect=false;
 explicit Host(Row r):row(r) {
  host.user=this;host.bytes=bytes;host.call=call;
  put(actor+0x6c,logic);put(actor+0x7c,0xdeadbeef);put(logic+0x18,instance);put(instance,row.table);
  put(row.table+0x10,0x71000010);put(row.table+0x1c,0x7100001c);put(row.table+0x20,0x71000020);
 }
 static uint8_t *bytes(void *u,uint32_t a,uint32_t n) {
  auto &s=*(Host*)u;
  if(a>=actor && uint64_t(a-actor)+n<=s.arena.size())return s.arena.data()+a-actor;
  if(a>=0x500000 && uint64_t(a-0x500000)+n<=s.image.size())return s.image.data()+a-0x500000;
  if(a>=CLAW_STACK_BASE && uint64_t(a-CLAW_STACK_BASE)+n<=s.stack.size())return s.stack.data()+a-CLAW_STACK_BASE;
  return nullptr;
 }
 uint32_t get(uint32_t a) {uint32_t v;auto *p=bytes(this,a,4);assert(p);std::memcpy(&v,p,4);return v;}
 void put(uint32_t a,uint32_t v) {auto *p=bytes(this,a,4);assert(p);std::memcpy(p,&v,4);}
 static uint32_t call(void *u,const ClawCall *c) {
  auto &s=*(Host*)u;s.calls.push_back(c->function);
  if(s.serviceFailure) {s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=c->function;return 0;}
  if(c->function==0x4f63ec) {
   assert(c->argumentCount==1 && c->arguments[0]==s.row.size);
   assert(s.get(logic+0x1c)==1000 && s.get(logic+0x18)==0x12345678);
   if(s.redirect)s.put(actor+0x6c,logic+0x100);
   return s.allocationFailure?0:instance;
  }
  if(c->function==s.row.ctor) {
   assert(c->receiver==instance && c->argumentCount==1 && c->arguments[0]==actor);
   assert(s.get(logic+0x18)==0x12345678);s.put(instance,s.row.table);return instance;
  }
  if(c->function==0x71000010) {
   assert(c->receiver==instance && c->argumentCount==0 && s.get(logic+0x18)==0x12345678);return 17;
  }
  if(c->function==0x7100001c || c->function==0x71000020) {assert(c->receiver==instance && !c->argumentCount);return 0;}
  if(c->function==0x4dc870) {assert(!c->receiver && c->argumentCount==1 && c->arguments[0]==instance);return 0;}
  assert(false);return 0;
 }
 uint32_t run(uint32_t event) {
  put(logic+0x1c,event);uint32_t a[]={actor},result=0;
  uint32_t accepted=claw_v13_enemy_lifecycle_compat_entry(row.root,0,a,1,&host,&result);
  assert(accepted==(host.fault?0u:1u));return result;
 }
};
int main() {
 for(auto row:rows) {
  for(unsigned redirect=0;redirect<2;++redirect) {
   Host s(row);s.redirect=redirect;s.put(logic+0x18,0x12345678);
   assert(s.run(0)==1 && !s.host.fault && s.get(logic+0x18)==instance);
   assert((s.calls==std::vector<uint32_t>{0x4f63ec,row.ctor,0x71000010}));
   if(redirect)assert(s.get(logic+0x118)==0);
  }
  for(uint32_t event:{29u,30u,80u,81u,82u,83u,1000u,84u,0xffffffffu}) {
   Host s(row);assert(s.run(event)==1 && !s.host.fault && s.get(logic+0x1c)==event);
   if(event==29)assert((s.calls==std::vector<uint32_t>{0x71000020}));
   else if(event==30)assert((s.calls==std::vector<uint32_t>{0x7100001c}));
   else if(event==84 || event==0xffffffff)assert((s.calls==std::vector<uint32_t>{0x4dc870}));
   else assert(s.calls.empty());
  }
  Host failed(row);failed.put(logic+0x18,0x12345678);failed.allocationFailure=true;
  failed.run(0);assert(failed.host.fault && failed.get(logic+0x18)==0x12345678 && failed.calls.size()==1);
  Host fault(row);fault.serviceFailure=true;fault.run(29);
  assert(fault.host.fault==CLAW_FAULT_HOST && fault.host.faultAddress==0x71000020);
 }
}
'''
def main():
    if float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])>=16:
        raise SystemExit('Wait until load is below 16')
    pairs=json.loads((ROOT/'work/v13/enemy-body-review.json').read_text())['pairs']
    rows=['{'+','.join([p['v10'],p['bodies']['v10']['constructor'],p['constructor_vtables']['v10'],p['bodies']['v13']['allocation_size']])+'}' for p in pairs]
    OUT.mkdir(parents=True,exist_ok=True);source=OUT/'check.cpp';source.write_text(SOURCE.replace('ROWS',','.join(rows)));binary=OUT/'check'
    subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'Sources'),str(source),*[str(ROOT/'Sources'/p) for p in ['V13EnemyLifecycleAdapter.cpp','V13EnemyLifecycleRuntime.cpp','V13RawLifecycleRuntime.cpp']],'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True,env={**os.environ,'CLAW_LIVES_BOSS_PROFILE':'claw-v1.3'})
    result={'status':'pass','check':'v13_enemy_lifecycle_native_join','classes':len(pairs),'checks':len(pairs)*13,'scope':'Native layout/physical-service composition; original family admission is separate.'}
    (OUT/'check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
