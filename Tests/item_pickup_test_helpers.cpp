// Test-only composition of frozen Goodie and WorldLoot with item award runtime.
#include "../Sources/ItemPickupRuntime.h"
#include "../Sources/BouncingGoodieLogic.h"
#include <algorithm>
#include <cstring>
namespace {
struct Test {ClawItemPickupContext* x;ClawItemPickupDependency d;void* user;uint32_t body;ClawGenericEnemy s;};
uint32_t* raw(Test& t,uint32_t token,uint32_t n){return t.x->scene.lookup(t.x->scene.context,token,n);}
void sync(Test& t,bool out){auto* a=raw(t,t.x->playerToken,128);(void)a;auto* actor=raw(t,0x3002000,128);auto* logic=raw(t,0x3001000,93);auto* body=raw(t,t.body,104);if(out){std::copy(t.s.actor,t.s.actor+128,actor);std::copy(t.s.primary,t.s.primary+93,logic);std::copy(t.s.enemy,t.s.enemy+104,body);}else{std::copy(actor,actor+128,t.s.actor);std::copy(logic,logic+93,t.s.primary);std::copy(body,body+104,t.s.enemy);}}
uint32_t callback(ClawWorldLootGlobals*,ClawWorldLootContext*,const ClawWorldLootCall* c,void* user){auto& t=*static_cast<Test*>(user);uint32_t result=0;if(claw_item_pickup_entry(c->function,c->receiver,c->arguments,c->argumentCount,t.x,t.d,t.user,&result))return result;t.x->fault=2;return 0;}
uint32_t literal(const char* name){if(!std::strcmp(name,"LogicHit"))return 0x522d54;if(!std::strcmp(name,"LogicAttack"))return 0x522d48;if(!std::strcmp(name,"GAME_CYCLE100"))return 0x5240d8;if(!std::strcmp(name,"GAME_PUBOUNCE1"))return 0x5240c8;if(!std::strcmp(name,"LS_FALLING"))return 0x5236fc;if(!std::strcmp(name,"LS_BOUNCE"))return 0x5240e8;if(!std::strcmp(name,"LS_DEAD"))return 0x5234f4;return 0;}
uint64_t dependency(ClawGenericEnemy*,ClawGenericEnemyContext*,const ClawGenericEnemyCall* c,void* user){auto& t=*static_cast<Test*>(user);sync(t,true);uint32_t result;
 if(c->function==0x473660){ClawWorldLootContext x{t.x->scene,0,0};result=claw_world_loot_rebind_actor(c->arguments[0],int32_t(c->arguments[1]),t.x->loot,&x,callback,&t);if(x.fault)t.x->fault=x.fault;}
 else{ClawItemPickupCall event{};event.function=c->function;event.receiver=c->receiver;event.argumentCount=c->argumentCount;std::copy(c->arguments,c->arguments+c->argumentCount,event.arguments);if(c->name){event.argumentCount=1;event.arguments[0]=literal(c->name);}result=t.d(t.x,&event,t.user);}
 sync(t,false);return result;}
}
extern "C" uint32_t claw_item_test_goodie(uint32_t body,ClawItemPickupContext* x,ClawItemPickupDependency d,void* user){Test t{x,d,user,body,{}};sync(t,false);ClawGenericEnemyContext g{};claw_generic_enemy_context_defaults(&g);g.actorToken=0x3002000;g.primaryToken=0x3001000;g.enemyToken=body;g.sceneToken=0x3004000;g.tileManagerToken=0x3075000;g.soundRegistryToken=0x3008010;g.tick=x->tick;g.animationDelta=x->animationDelta;g.emptyStringToken=0x52e1c4;std::copy(x->player->actor,x->player->actor+128,g.playerActor);
 const ClawGenericEnemyState names[]={{2001,0x40f010,0x307e000,"LS_FALLING"},{2008,0x40f200,0x307e040,"LS_BOUNCE"},{2004,0x40f400,0x307e080,"LS_DEAD"}};g.states=names;g.stateCount=3;ClawGenericEnemyStatesContext shared{};shared.audioEnabled=x->audioEnabled;shared.audioPosition=x->masterVolume;ClawBouncingGoodieContext c{};c.generic=&g;c.shared=&shared;c.sequenceRegistryToken=0x3007010;c.loot=x->loot;c.states=names;c.stateCount=3;std::copy(raw(t,0x3078000,16),raw(t,0x3078000,16)+16,c.imageHeader);claw_bouncing_goodie_context_defaults(&c);uint32_t result=claw_bouncing_goodie_callback(&t.s,&c,dependency,&t);sync(t,true);if(c.fault)x->fault=c.fault;return result;}
extern "C" uint32_t claw_item_test_rebind(uint32_t actor,int32_t item,ClawItemPickupContext* x,ClawItemPickupDependency d,void* user){Test t{x,d,user,0,{}};ClawWorldLootContext c{x->scene,0,0};uint32_t result=claw_world_loot_rebind_actor(actor,item,x->loot,&c,callback,&t);if(c.fault)x->fault=c.fault;return result;}
