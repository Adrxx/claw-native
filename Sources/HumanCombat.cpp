#include "HumanCombat.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Invocation {
    ClawHumanCombatContext *x;
    ClawGenericEnemyDependency dependency;
    void *user;
};
uint32_t run(ClawHumanEnemy *, Invocation &, uint32_t, uint32_t, uint32_t *);
uint64_t call(ClawHumanEnemy *s, Invocation &i, uint32_t f, uint32_t receiver,
              std::initializer_list<uint32_t> args = {}, const char *name = nullptr) {
    ClawGenericEnemyCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    c.name = name;
    std::copy(args.begin(), args.end(), c.arguments);
    return i.dependency ? i.dependency(s, i.x->human->generic, &c, i.user) : 0;
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *g, const ClawGenericEnemyCall *c, void *user) {
    auto &i = *static_cast<Invocation *>(user);
    uint32_t result = 0;
    if (c->receiver == g->enemyToken && run(s, i, c->function, c->argumentCount ? c->arguments[0] : 0, &result))
        return result;
    return i.dependency ? i.dependency(s, g, c, i.user) : 0;
}
void invoke(ClawHumanEnemy *s, Invocation &i, uint32_t f, uint32_t arg = 0, bool hasArg = false) {
    uint32_t result = 0;
    auto *h = i.x->human;
    auto *g = h->generic;
    if (run(s, i, f, arg, &result))
        return;
    if (claw_human_enemy_entry(s, h, f, arg, bridge, &i, &result))
        return;
    if (claw_generic_enemy_state_entry(s, g, h->sharedStates, f, arg, bridge, &i))
        return;
    if (claw_generic_enemy_entry(s, g, f, arg, bridge, &i))
        return;
    if (hasArg)
        call(s, i, f, g->enemyToken, {arg});
    else
        call(s, i, f, g->enemyToken);
}
void virt(ClawHumanEnemy *s, Invocation &i, uint32_t slot, uint32_t arg = 0, bool hasArg = false) {
    invoke(s, i, i.x->human->generic->virtualFunctions[slot / 4], arg, hasArg);
}
bool currentName(ClawHumanEnemy *s, Invocation &i, const char *name) {
    auto *g = i.x->human->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (uint32_t(g->states[n].state) == s->primary[7]) {
            return g->states[n].name && std::strcmp(g->states[n].name, name) == 0;
        }
    i.x->fault = 1;
    return false;
}
bool transition(ClawHumanEnemy *s, Invocation &i, const char *name) {
    auto *g = i.x->human->generic;
    if (i.dependency) {
        s->primary[7] = uint32_t(call(s, i, 0x4dba00, 0x537668, {}, name));
        return true;
    }
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name)) {
            s->primary[7] = uint32_t(g->states[n].state);
            return true;
        }
    i.x->fault = 1;
    return false;
}
void audio(ClawHumanEnemy *s, Invocation &i, uint32_t offset) {
    const uint32_t token = s->enemy[offset / 4];
    auto *x = i.x->human->sharedStates;
    if (!token || !x->audioEnabled)
        return;
    for (size_t n = 0; n < x->resourceCount; ++n)
        if (x->resources[n].token == token) {
            call(s, i, 0x4b45f0, x->resources[n].controllerToken, {x->audioPosition, 0, 0, 0});
            return;
        }
    i.x->fault = 1;
}
void hit(ClawHumanEnemy *s, Invocation &i, bool high) {
    s->enemy[8] = 1;
    s->enemy[9] = s->primary[7];
    if (!transition(s, i, high ? "LS_HITHIGH" : "LS_HITLOW"))
        return;
    s->enemy[0x134 / 4] = s->actor[0x190 / 4];
    call(s, i, 0x4c8220, i.x->human->generic->actorToken + 0x188, {s->enemy[(high ? 0x338 : 0x334) / 4]});
    audio(s, i, high ? 0x418 : 0x414);
    if (high) {
        const int32_t n = int32_t(call(s, i, 0x4a3050, 0)) % 4;
        if (n >= 0)
            audio(s, i, 0x390 + uint32_t(n) * 4);
    } else
        audio(s, i, 0x41c);
    s->enemy[0x50 / 4] = 0;
    s->enemy[0x54 / 4] = s->enemy[0x18c / 4] == 3 ? 0x40690000 : 0xc0690000;
}
void swordEffect(ClawHumanEnemy *s, Invocation &i) {
    auto *h = i.x->human;
    auto *g = h->generic;
    if (claw_human_enemy_private_word(s, h, 0x44c))
        return;
    const uint32_t element = g->levelWord - 0x26b8;
    if (element > 2)
        return;
    const char *images[] = {"GAME_EXPLOS_FIRE", "GAME_EXPLOS_LIGHTNING", "GAME_EXPLOS_ICE"};
    const char *sequences[] = {"GAME_FIRESWORDEXPLOSION", "GAME_LIGHTNINGEXPLOSION", "GAME_ICESWORDEXPLOSION"};
    uint32_t token;
    if (i.x->scene.lookup) {
        ClawSceneActorCreate args{0, s->actor[0x4c / 4], s->actor[0x50 / 4], s->actor[0x64 / 4] + 0x2135, 0, 0x40000};
        uint32_t fault = 0;
        token = claw_scene_actor_create_named(i.x->actorContainerToken, args, 0x522648, i.x->scene, &fault);
        if (fault)
            i.x->fault = 2;
    } else
        token =
            uint32_t(call(s, i, 0x4c8da0, i.x->actorContainerToken,
                          {0, s->actor[0x4c / 4], s->actor[0x50 / 4], s->actor[0x64 / 4] + 0x2135, 0x522648, 0x40000}));
    claw_human_enemy_set_private_word(s, h, 0x44c, token);
    h->effectToken = token;
    if (i.x->scene.lookup)
        h->effectActor = i.x->scene.lookup(i.x->scene.context, token, 128);
    if (!token) {
        i.x->fault = 2;
        return;
    }
    call(s, i, 0x4c7970, token, {}, images[element]);
    call(s, i, 0x4c79e0, claw_human_enemy_private_word(s, h, 0x44c), {0}, sequences[element]);
    const uint32_t live = claw_human_enemy_private_word(s, h, 0x44c);
    uint32_t *actor = i.x->scene.lookup        ? i.x->scene.lookup(i.x->scene.context, live, 128)
                      : live == h->effectToken ? h->effectActor
                                               : nullptr;
    if (!actor) {
        i.x->fault = 2;
        return;
    }
    actor[2] |= 2;
}
uint32_t run(ClawHumanEnemy *s, Invocation &i, uint32_t f, uint32_t arg, uint32_t *result) {
    if (result)
        *result = 0;
    if (f == 0x44f3c0 || f == 0x44f510) {
        hit(s, i, f == 0x44f510);
        return 1;
    }
    if (f != 0x44d460 && f != 0x44d570 && f != 0x44d5a0 && f != 0x44d700 && f != 0x44d730)
        return 0;
    if (f == 0x44d460) {
        if (currentName(s, i, "LS_HITLOW") || currentName(s, i, "LS_HITHIGH")) {
            virt(s, i, 0x44);
            return 1;
        }
        if (i.x->fault)
            return 1;
    }
    virt(s, i, 0x28, arg, true);
    invoke(s, i, 0x440e20, arg, true);
    if (f == 0x44d460)
        invoke(s, i, 0x43e9c0, 300, true);
    if (f == 0x44d730)
        invoke(s, i, 0x43e9c0, 2000, true);
    if (f == 0x44d570)
        i.x->human->sharedStates->attackerActor[2] |= 0x10000;
    hit(s, i, f == 0x44d460 && i.x->human->sharedStates->playerPrivate[5] != 0);
    if (f == 0x44d5a0)
        swordEffect(s, i);
    return 1;
}
} // namespace
extern "C" uint32_t claw_human_combat_entry(ClawHumanEnemy *s, ClawHumanCombatContext *x, uint32_t function,
                                            uint32_t attacker, ClawGenericEnemyDependency dependency, void *user,
                                            uint32_t *result) {
    if (!s || !x || !x->human || !x->human->generic || !x->human->sharedStates || !x->human->privateTail)
        return 0;
    Invocation i{x, dependency, user};
    return run(s, i, function, attacker, result);
}
