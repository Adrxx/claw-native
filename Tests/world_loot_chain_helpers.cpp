#include "../Sources/HumanEnemy.h"
#include "../Sources/WorldLootRuntime.h"
#include <cstring>
struct LootChainBridge {
 ClawGenericEnemyContext* generic;ClawWorldLootGlobals* globals;
 ClawWorldLootContext* loot;ClawWorldLootDependency dependency;void* user;
};
static void transfer(ClawGenericEnemy* s,LootChainBridge* b,bool intoHeap){
 struct View {uint32_t token,count;uint32_t* words;};
 View views[]={{b->generic->actorToken,128,s->actor},{b->generic->primaryToken,93,s->primary},{b->generic->enemyToken,264,s->enemy}};
 for(auto v:views){auto* p=b->loot->scene.lookup(b->loot->scene.context,v.token,v.count);if(!p){b->loot->fault=1;return;}if(intoHeap)std::memcpy(p,v.words,v.count*4);else std::memcpy(v.words,p,v.count*4);}
}
static uint64_t bridge(ClawGenericEnemy* s,ClawGenericEnemyContext*,const ClawGenericEnemyCall* e,void* user){
 auto* b=static_cast<LootChainBridge*>(user);transfer(s,b,true);
 if(e->function==0x42df90){claw_world_loot_drop(e->receiver,b->globals,b->loot,b->dependency,b->user);transfer(s,b,false);return 0;}
 ClawWorldLootCall c{};c.function=e->function;c.receiver=e->receiver;c.argumentCount=e->argumentCount;c.name=e->name;
 for(uint32_t i=0;i<e->argumentCount;++i)c.arguments[i]=e->arguments[i];
 uint32_t value=b->dependency(b->globals,b->loot,&c,b->user);transfer(s,b,false);return value;
}
extern "C" uint32_t world_loot_test_enemy_chain(ClawGenericEnemy* s,
 ClawGenericEnemyContext* generic,ClawGenericEnemyStatesContext* extra,
 uint32_t function,uint32_t argument,ClawWorldLootGlobals* globals,
 ClawWorldLootContext* loot,ClawWorldLootDependency dependency,void* user){
 LootChainBridge b{generic,globals,loot,dependency,user};uint32_t tail[20]{};
 ClawHumanEnemyContext human{};human.generic=generic;human.sharedStates=extra;human.privateTail=tail;
 uint32_t result=0;uint32_t support=function==0x44e0c0?claw_human_enemy_entry(s,&human,function,argument,bridge,&b,&result):claw_generic_enemy_state_entry(s,generic,extra,function,argument,bridge,&b);
 transfer(s,&b,true);return support;
}
