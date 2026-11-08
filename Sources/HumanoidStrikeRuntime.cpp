#include "HumanoidStrikeRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawGenericEnemy *s;
    ClawHumanoidStrikeContext *c;
    ClawGenericEnemyDependency d;
    void *user;
};
bool bad(const Run &r) {
    return r.c->fault != 0;
}
uint32_t *part(uint32_t t, uint32_t n, uint32_t base, uint32_t count, uint32_t *p) {
    const uint64_t end = uint64_t(t) + uint64_t(n) * 4;
    if (p && base && t >= base && end <= uint64_t(base) + uint64_t(count) * 4 && (t - base) % 4 == 0)
        return p + (t - base) / 4;
    return nullptr;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto *h = r.c->human;
    auto *g = h->generic;
    uint32_t *p = nullptr;
    if ((p = part(t, n, g->enemyToken, 264, r.s->enemy)) ||
        (p = part(t, n, g->enemyToken + 0x420, 20, h->privateTail)) ||
        (p = part(t, n, g->actorToken, 128, r.s->actor)) || (p = part(t, n, g->primaryToken, 93, r.s->primary)) ||
        (p = part(t, n, g->secondaryToken, 93, r.s->secondary)) ||
        (p = part(t, n, g->contactToken, 93, r.s->contact)) || (p = part(t, n, g->playerToken, 128, g->playerActor)))
        return p;
    if ((p = part(t, n, h->otherActorToken, 128, h->otherActor)))
        return p;
    if (h->otherActor && (p = part(t, n, h->otherActor[0x6c / 4], 93, h->otherPrimary)))
        return p;
    if ((p = part(t, n, h->effectToken, 128, h->effectActor)))
        return p;
    if (h->effectActor && (p = part(t, n, h->effectActor[0x6c / 4], 93, h->effectPrimary)))
        return p;
    p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t read(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
void write(Run &r, uint32_t t, uint32_t v) {
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}
uint64_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawGenericEnemyCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.name = name;
    std::copy(args.begin(), args.end(), e.arguments);
    return r.d(r.s, r.c->human->generic, &e, r.user);
}
uint32_t *hostLookup(void *u, uint32_t t, uint32_t n) {
    return span(*static_cast<Run *>(u), t, n);
}
uint32_t hostCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    if (e.argumentCount == 4)
        return uint32_t(
            call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]}));
    if (e.argumentCount == 2)
        return uint32_t(call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1]}));
    if (e.argumentCount == 1)
        return uint32_t(call(r, e.function, e.receiver, {e.arguments[0]}));
    return uint32_t(call(r, e.function, e.receiver));
}
uint32_t animate(Run &r, uint32_t f, uint32_t actor, uint32_t arg) {
    auto *h = r.c->human;
    auto *g = h->generic;
    if (!r.c->composeAnimation)
        return uint32_t(call(r, f, actor, {arg}));
    ClawActorAnimationGlobals globals{g->animationDelta, h->sharedStates->audioPosition};
    ClawSceneActorHost host{};
    host.context = &r;
    host.lookup = hostLookup;
    host.call = hostCall;
    uint32_t fault = 0, result = 0;
    if (!claw_actor_animation_entry(f, actor, arg, 0, &globals, host, &fault, &result) || fault)
        r.c->fault = 2;
    return result;
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *g, const ClawGenericEnemyCall *e, void *p) {
    auto &r = *static_cast<Run *>(p);
    if ((e->function == 0x4c8220 || e->function == 0x4c82a0) && e->argumentCount == 1 && r.c->composeAnimation)
        return animate(r, e->function, e->receiver, e->arguments[0]);
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    return r.d(s, g, e, r.user);
}
uint32_t lookup(Run &r, uint32_t offset, uint32_t name, const char *text) {
    const uint32_t actor = read(r, r.c->human->generic->enemyToken + 0x12c), scene = read(r, actor + 0xc),
                   registry = read(r, scene + offset) + 16;
    return bad(r) ? 0 : uint32_t(call(r, 0x4f6286, registry, {name}, text));
}
} // namespace
extern "C" uint32_t claw_humanoid_strike_entry(ClawGenericEnemy *s, ClawHumanoidStrikeContext *c, uint32_t f,
                                               const uint32_t *args, uint32_t n, ClawGenericEnemyDependency d,
                                               void *user, uint32_t *result) {
    if (!s || !c || !c->human || !c->human->generic || !c->human->sharedStates)
        return 0;
    uint32_t required = f == 0x43ee10 ? 2 : f == 0x43eee0 ? 3 : 0;
    if (f != 0x43ee10 && f != 0x43eee0 && f != 0x43efe0 && f != 0x43f030)
        return 0;
    if (n != required || (n && !args)) {
        c->fault = 2;
        return 0;
    }
    Run r{s, c, d, user};
    auto *h = c->human;
    auto *g = h->generic;
    if (bad(r))
        return 0;
    if (f == 0x43efe0) {
        const uint32_t status = claw_common_enemy_entry(s, h, f, 0, bridge, &r, result);
        if (h->fault)
            c->fault = 1;
        return status;
    }
    if (f == 0x43f030) {
        const uint32_t status = claw_generic_enemy_state_entry(s, g, h->sharedStates, f, 0, bridge, &r);
        if (!status)
            c->fault = 1;
        if (result)
            *result = 0;
        return status;
    }
    const uint32_t enemy = g->enemyToken;
    write(r, enemy + 0x20, 1);
    const uint32_t previous = read(r, read(r, enemy + 0x10) + 0x1c);
    if (bad(r))
        return 1;
    write(r, enemy + 0x24, previous);
    const uint32_t state = uint32_t(call(r, 0x4dba00, 0x537668, {0x52720c}, "LS_STRIKE"));
    if (bad(r))
        return 1;
    write(r, read(r, enemy + 0x10) + 0x1c, state);
    // Original copies each DWORD in order. Aliasing input with an interior of
    // destination220 must observe earlier stores, rather than a shadow memcpy.
    for (uint32_t i = 0; i < 4 && !bad(r); ++i) {
        const uint32_t value = read(r, args[1] + i * 4);
        if (bad(r))
            break;
        write(r, enemy + 0x220 + i * 4, value);
    }
    if (bad(r))
        return 1;
    uint32_t sequence = lookup(r, 0x2c, args[0], c->sequenceName);
    if (!sequence && !bad(r))
        sequence = lookup(r, 0x2c, 0x5234b4, "GAME_NULL");
    if (bad(r))
        return 1;
    write(r, enemy + 0x310, sequence);
    const uint32_t actor = read(r, enemy + 0x12c), old = read(r, actor + 0x190);
    if (bad(r))
        return 1;
    write(r, enemy + 0x134, old);
    if (bad(r))
        return 1;
    animate(r, 0x4c8220, actor + 0x188, sequence);
    if (f == 0x43eee0 && !bad(r)) {
        const uint32_t sound = lookup(r, 0x28, args[2], c->soundName);
        if (!bad(r))
            write(r, enemy + 0x3a0, sound);
    }
    if (result)
        *result = 0;
    return 1;
}
