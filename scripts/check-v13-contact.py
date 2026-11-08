#!/usr/bin/env python3
"""Check typed native contact storage and callback joins, separate from admission."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/v13-contact-check'
SOURCE=r'''
#include "V13Contact.h"
#include <cassert>
#include <initializer_list>
#include <cstring>
struct Calls {unsigned count=0,reject=0,clear=0;};
uint32_t bump(ClawV13ContactActor *a,uint32_t n,uint32_t i,void *u) {
 auto &c=*(Calls*)u;++c.count;assert(n==2);assert(a[i].otherToken==a[1-i].actor.token);
 if(c.clear)a[0].mask=0;return c.reject?0:7;
}
ClawV13ContactActor actor(uint32_t token,uint32_t x,uint32_t y) {
 ClawV13ContactActor a{};a.actor.token=token;a.actor.flags=0x100;a.actor.x=x;a.actor.y=y;
 a.actor.mode=1;a.actor.type=2;a.actor.stepX=3;a.actor.stepY=5;
 a.actor.moveRect={uint32_t(-2),uint32_t(-2),2,2};a.mask=2;a.otherToken=0x12345678;a.hasCallback=1;return a;
}
int main() {
 uint32_t cells[16]{},rows[]={0,4,8,12};ClawTileDescription tile{};tile.type=1;tile.width=tile.height=16;
 ClawCollisionWorld w{cells,rows,64,64,4,4,&tile,1,nullptr,0,14,14};uint32_t fault=99;
 for(unsigned d=0;d<4;++d) {
  uint32_t x=d==0?32:d==1?8:20,y=d==2?32:d==3?8:20;
  ClawV13ContactActor a[]={actor(0x1234,20,20),actor(0x5678,x,y)};a[1].mask=0;Calls c;
  uint32_t masks[]={0x22000000,0x82000000,0x42000000,0x12000000};
  auto r=claw_v13_contact_resolve(&w,a,2,0,x,y,0,bump,&c,&fault);
  assert(!fault&&r==(masks[d]|0x400000)&&c.count==2);
  assert(a[0].actor.x==20&&a[0].actor.y==20&&a[0].otherToken==0x5678&&a[1].otherToken==0x1234);
 }
 for(unsigned mode=0;mode<4;++mode) {
  ClawV13ContactActor a[]={actor(10,20,20),actor(20,mode==3?24:32,20)};Calls c;
  c.reject=mode==0;c.clear=mode==1;if(mode==2)a[0].hasCallback=0;
  auto r=claw_v13_contact_resolve(&w,a,2,0,32,20,0,bump,&c,&fault);
  assert(!fault&&r==((mode==0||mode==3)?0u:0x22400000u));
  assert(c.count==(mode==3?0u:1u));
  if(mode==0||mode==3)assert(a[0].actor.x==32);
  if(mode==2)assert(a[0].otherToken==0x12345678);
 }
 tile.insideAttribute=1;auto a=actor(10,20,20);
 assert(claw_v13_contact_resolve(&w,&a,1,0,32,20,0,nullptr,nullptr,&fault)==0x470000);
 assert(!fault&&a.actor.x==20);a.actor.mode=7;
 assert(claw_v13_contact_resolve(&w,&a,1,0,32,30,0,nullptr,nullptr,&fault)==0);
 assert(!fault&&a.actor.x==32&&a.actor.y==30);
 for(uint32_t peer:{0x10001000u,0x10001200u,0x73000000u,0u}) {
  auto foreign=actor(0x1234,20,20);foreign.actor.mode=7;foreign.otherToken=peer;
  assert(claw_v13_contact_resolve(&w,&foreign,1,0,32,30,0,nullptr,nullptr,&fault)==0);
  assert(!fault&&foreign.otherToken==peer);
 }
 // The default v1.3 route must preserve every retained movement mode,
 // including mode transitions and the shared split-displacement wrapper.
 for(uint32_t mode=0;mode<=9;++mode)for(uint32_t attribute=0;attribute<4;++attribute)
 for(uint32_t options=0;options<4;++options)for(uint32_t flags:{0x100u,0x400110u}) {
  tile.insideAttribute=attribute;
  for(uint32_t y:{8u,20u,40u}) {
   auto current=actor(10,20,20);current.actor.mode=mode;current.actor.flags=flags;
   auto expected=current.actor;
   auto oldResult=claw_collision_resolve(&w,&expected,32,y,options);
   auto result=claw_v13_collision_resolve(&w,0,&current,1,0,32,y,options,nullptr,nullptr,&fault);
   assert(!fault && result==oldResult && !std::memcmp(&expected,&current.actor,sizeof(expected)));
   current=actor(10,20,20);current.actor.mode=mode;current.actor.flags=flags;expected=current.actor;
   oldResult=claw_collision_move(&w,&expected,40,y,options);
   result=claw_v13_collision_move(&w,0,&current,1,0,40,y,options,nullptr,nullptr,&fault);
   assert(!fault && result==oldResult && !std::memcmp(&expected,&current.actor,sizeof(expected)));
  }
 }
 tile.insideAttribute=0;
 ClawV13ContactActor split[]={actor(10,20,20),actor(20,48,20)};Calls calls;
 auto blocked=claw_v13_collision_move(&w,4,split,2,0,48,20,0,bump,&calls,&fault);
 assert(!fault && blocked==0x22400000 && split[0].actor.x==34 && calls.count==2);
 assert(!claw_v13_contact_resolve(nullptr,nullptr,0,0,0,0,0,nullptr,nullptr,&fault)&&fault);
 auto binding=claw_v13_bump_create(123,456,&fault);
 assert(binding && !fault);
 assert(claw_v13_bump_invoke(binding,&fault)==1 && !fault);
 claw_v13_bump_destroy(binding);
 auto invalid=w;invalid.width=0;auto badActor=actor(10,20,20);
 assert(claw_v13_collision_move(&invalid,4,&badActor,1,0,48,20,0,nullptr,nullptr,nullptr)==0x400000);
}
'''
SWIFT = r'''
import Foundation
// This standalone host exercises v1.3; the app provides its version selector.
func claw_native_v13_enabled() -> UInt32 { 1 }
enum AssetError: Error { case invalid(String) }
enum ClawSnapshotError: Error { case invalidState }
struct ClawWorld {
 struct Plane { let flags=1,tileWidth=16,tileHeight=16,width=4,height=4;let tiles=Array(repeating:0,count:16) }
 struct Tile { let native:ClawTileDescription }
 let planes=[Plane()]
 let tileDescriptions:[Tile]
}
var tile=ClawTileDescription();tile.type=1;tile.width=16;tile.height=16
var map=try ClawCollisionMap(world:ClawWorld(tileDescriptions:[.init(native:tile)]))
map.setGameStageSteps()
var mover=ClawCollisionActor();mover.token=10;mover.flags=0x100;mover.x=20;mover.y=20
mover.mode=1;mover.type=2;mover.stepX=3;mover.stepY=5
mover.moveRect=ClawPlayerRect(left:UInt32.max-1,top:UInt32.max-1,right:2,bottom:2)
var peer=mover;peer.token=20;peer.x=48
let initial=mover
let supplied=[ClawV13ContactActor(actor:mover,mask:2,otherToken:0,hasCallback:1),
              ClawV13ContactActor(actor:peer,mask:0,otherToken:0,hasCallback:1)]
var published:[ClawV13ContactActor]=[]
var callbackCount=0
map.contactActors={supplied}
map.contactCallback={pointer,count,index,_ in
 precondition(count==2)
 let records=pointer!
 precondition(records[Int(index)].otherToken==records[1-Int(index)].actor.token)
 callbackCount += 1
 return 1
}
map.publishContacts={published=$0}
_ = map.move(actor:&mover,x:48,y:20,options:0,otherActors:[peer])
precondition(callbackCount==0 && published.isEmpty)
mover=initial;map.contactManagerFlags=4
let result=map.move(actor:&mover,x:48,y:20,options:0,otherActors:[peer])
precondition(result==0x22400000 && mover.x==34 && callbackCount==2)
precondition(published[0].otherToken==20 && published[1].otherToken==10)
print("Swift collision map: default and enabled contact paths passed")
'''
def main():
    if float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])>=16:
        raise SystemExit('Wait until load is below16')
    OUT.mkdir(parents=True,exist_ok=True)
    source=OUT/'check.cpp';source.write_text(SOURCE);binary=OUT/'check'
    subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'Sources'),str(source),
        str(ROOT/'Sources/V13ContactAdapter.cpp'),str(ROOT/'Sources/V13ContactRuntime.cpp'),
        str(ROOT/'Sources/V13ContactDispatchRuntime.cpp'),str(ROOT/'Sources/CollisionResponse.cpp'),
        str(ROOT/'Sources/V13ContactBindingAdapter.cpp'),str(ROOT/'Sources/V13ContactBindingsRuntime.cpp'),
        str(ROOT/'Sources/TileCollision.cpp'),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
    swift=OUT/'main.swift';swift.write_text(SWIFT)
    objects=[]
    for name in ('V13ContactAdapter','V13ContactRuntime','V13ContactDispatchRuntime','V13ContactBindingAdapter','V13ContactBindingsRuntime','CollisionResponse','TileCollision'):
        obj=OUT/(name+'.o');objects.append(str(obj))
        subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'Sources'),'-c',str(ROOT/'Sources'/(name+'.cpp')),'-o',str(obj)],check=True)
    subprocess.run(['xcrun','swiftc','-import-objc-header',str(ROOT/'Sources/V13Contact.h'),
                    str(ROOT/'Sources/ClawCollision.swift'),str(swift),*objects,'-lc++','-o',str(OUT/'swift-check')],check=True)
    subprocess.run([str(OUT/'swift-check')],check=True)
    r={'status':'pass','checks':['direction-masks','peer-identities','one-way-mask','rejection','callback-mask-write',
       'absent-callback','current-overlap','tile-backtracking','free-mode','foreign-peer-identity',
       'default-dispatch-all-modes','split-displacement-contact','swift-app-contact-path','source-LogicBump-binding','native-invalid-input']}
    (OUT/'check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
