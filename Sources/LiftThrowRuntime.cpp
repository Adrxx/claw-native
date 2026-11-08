#include "LiftThrowRuntime.h"
#include "EnemyMotionAux.h"
#include "CommonEnemyEntries.h"
#include "ActorAnimationRuntime.h"
#include "PlayerStanding.h"
#include "PlayerEngine.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
int32_t si(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
struct Run {
    ClawLiftThrowContext *c;
    ClawLiftThrowDependency d;
    void *u;
    void fail(uint32_t n = 1) {
        if (!c->fault)
            c->fault = n;
    }
    uint32_t *span(uint32_t t, uint32_t n) {
        if (c->fault)
            return nullptr;
        auto *p = c->scene.lookup ? c->scene.lookup(c->scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t rd(uint32_t t) {
        auto *p = span(t, 1);
        return p ? *p : 0;
    }
    void wr(uint32_t t, uint32_t v) {
        if (auto *p = span(t, 1))
            *p = v;
    }
    void number(uint32_t t, double v) {
        if (auto *p = span(t, 2))
            std::memcpy(p, &v, 8);
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, const char *n = nullptr) {
        if (c->fault)
            return 0;
        if (!d || a.size() > 12) {
            fail();
            return 0;
        }
        ClawLiftThrowCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        e.name = n;
        std::copy(a.begin(), a.end(), e.arguments);
        return uint32_t(d(c, &e, u));
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {}, const char * = nullptr);
    uint32_t enemy(uint32_t actor) {
        return rd(rd(actor + 0x6c) + 24);
    }
    void copy(uint32_t dst, uint32_t src, uint32_t n) {
        auto *s = span(src, n), *p = span(dst, n);
        if (s && p)
            std::memmove(p, s, n * 4);
    }
};
bool known(uint32_t f) {
    switch (f) {
    case 0x440420:
    case 0x440120:
    case 0x440710:
    case 0x440350:
    case 0x4407d0:
    case 0x4409d0:
    case 0x440410:
    case 0x4405b0:
    case 0x440260:
    case 0x440870:
    case 0x440a50:
    case 0x440b20:
    case 0x440c90:
    case 0x404e00:
    case 0x4207a0:
    case 0x421010:
    case 0x420fc0:
    case 0x4dbd20:
    case 0x4dc6d0:
    case 0x41dc50:
    case 0x41a850:
    case 0x41b1f0:
    case 0x41b280:
    case 0x41c4e0:
    case 0x4171d0:
    case 0x41d850:
        return true;
    default:
        return false;
    }
}
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t *sceneLookup(void *u, uint32_t t, uint32_t n) {
    return static_cast<Run *>(u)->span(t, n);
}
uint32_t sceneCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    switch (e.argumentCount) {
    case 0:
        return r.invoke(e.function, e.receiver, {});
    case 1:
        return r.invoke(e.function, e.receiver, {e.arguments[0]});
    case 2:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1]});
    case 3:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2]});
    default:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
    }
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a, const char *n) {
    if (c->fault)
        return 0;
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    if (known(f))
        return body(*this, f, t, args);
    if (c->composeAnimation && (f == 0x4c79e0 || f == 0x4c8220 || f == 0x4c82a0 || f == 0x420a10)) {
        ClawActorAnimationGlobals g{c->globals->animationDelta, c->globals->masterVolume};
        uint32_t result = 0, fault = 0;
        ClawSceneActorHost h{this, sceneLookup, nullptr, nullptr, sceneCall, nullptr};
        if (!claw_actor_animation_entry(f, t, args[0], args[1], &g, h, &fault, &result) || fault)
            fail(fault ? fault : 2);
        return result;
    }
    return call(f, t, a, n);
}
struct Enemy {
    Run *r;
    ClawGenericEnemy *s;
    ClawGenericEnemyContext *g;
    ClawGenericEnemyStatesContext *x;
    ClawEnemyMotionAuxContext *aux;
    uint32_t token, words;
};
void exchange(Enemy &b, bool output) {
    auto &r = *b.r;
    uint32_t *raw[] = {r.span(b.g->actorToken, 128), r.span(b.g->primaryToken, 93), r.span(b.token, b.words)};
    uint32_t *values[] = {b.s->actor, b.s->primary, b.s->enemy};
    uint32_t counts[] = {128, 93, b.words};
    for (uint32_t i = 0; i < 3; ++i)
        if (raw[i]) {
            if (output)
                std::copy_n(values[i], counts[i], raw[i]);
            else
                std::copy_n(raw[i], counts[i], values[i]);
        }
    if (!output) {
        b.g->tick = r.c->globals->tick;
        b.g->animationDelta = r.c->globals->animationDelta;
        std::copy_n(r.c->globals->physicsDefaults, 24, b.g->defaults);
        b.aux->strongThrow = r.c->globals->strongThrow;
        auto *p = r.span(r.c->globals->playerToken, 128);
        if (p)
            std::copy_n(p, 128, b.g->playerActor);
        uint32_t privateToken = r.rd(r.rd(r.c->globals->playerToken + 108) + 20);
        if (auto *v = r.span(privateToken, 78))
            std::copy_n(v, 78, b.x->playerPrivate);
    }
}
uint32_t literal(const char *n) {
    if (!n)
        return 0;
    if (!std::strcmp(n, "LS_BLOCKHIGH"))
        return 0x527188;
    if (!std::strcmp(n, "LS_BLOCKLOW"))
        return 0x52717c;
    if (!std::strcmp(n, "LS_HOME"))
        return 0x5234ec;
    if (!std::strcmp(n, "LS_IDLE"))
        return 0x523148;
    if (!std::strcmp(n, "LS_LIFTED"))
        return 0x5271d8;
    if (!std::strcmp(n, "LS_THROWN"))
        return 0x5271cc;
    if (!std::strcmp(n, "LS_FLAILING"))
        return 0x527170;
    if (!std::strcmp(n, "LS_DROPPED"))
        return 0x5271b4;
    return 0;
}
uint64_t enemyDependency(ClawGenericEnemy *, ClawGenericEnemyContext *, const ClawGenericEnemyCall *e, void *u) {
    auto &b = *static_cast<Enemy *>(u);
    exchange(b, true);
    uint32_t v = 0;
    if (e->function == 0x4dba00 && e->name) {
        uint32_t name = literal(e->name);
        if (!name)
            b.r->fail(2);
        else
            v = b.r->invoke(e->function, e->receiver, {name}, e->name);
    } else {
        uint32_t args[12]{};
        std::copy_n(e->arguments, e->argumentCount, args);
        if (known(e->function))
            v = body(*b.r, e->function, e->receiver, args);
        else if (e->function == 0x4c8220 || e->function == 0x4c82a0)
            v = b.r->invoke(e->function, e->receiver, {args[0]});
        else {
            ClawLiftThrowCall call{};
            call.function = e->function;
            call.receiver = e->receiver;
            call.argumentCount = e->argumentCount;
            call.name = e->name;
            std::copy_n(e->arguments, e->argumentCount, call.arguments);
            if (!b.r->d)
                b.r->fail();
            else
                v = uint32_t(b.r->d(b.r->c, &call, b.r->u));
        }
    }
    exchange(b, false);
    return v;
}
uint32_t inherited(Run &r, uint32_t f, uint32_t token, uint32_t argument = 0) {
    ClawGenericEnemy s{};
    ClawGenericEnemyContext g{};
    claw_generic_enemy_context_defaults(&g);
    g.enemyToken = token;
    g.actorToken = r.rd(token + 12);
    g.primaryToken = r.rd(token + 16);
    if (r.rd(token + 0x12c) != g.actorToken) {
        r.fail(2);
        return 0;
    }
    g.playerToken = r.c->globals->playerToken;
    g.virtualFunctions[0x44 / 4] = r.rd(r.rd(token) + 0x44);
    g.virtualFunctions[0x8c / 4] = r.rd(r.rd(token) + 0x8c);
    ClawGenericEnemyStatesContext x{};
    x.audioEnabled = r.c->globals->audioEnabled;
    x.audioPosition = r.c->globals->masterVolume;
    ClawGenericEnemyStateResource sound{};
    if ((f == 0x440b20 || f == 0x440c90) && x.audioEnabled) {
        sound.token = r.rd(token + (f == 0x440b20 ? 0x3c0 : 0x3bc));
        if (sound.token) {
            sound.controllerToken = r.rd(sound.token + 16);
            x.resources = &sound;
            x.resourceCount = 1;
        }
    }
    uint32_t unusedTail[20]{};
    ClawHumanEnemyContext human{};
    human.privateTail = unusedTail;
    human.generic = &g;
    human.sharedStates = &x;
    ClawEnemyMotionAuxContext aux{&human, nullptr, r.c->globals->strongThrow, 0};
    uint32_t words = std::min(r.c->enemyWordCount, 264u);
    if (words < 260) {
        r.fail(2);
        return 0;
    }
    Enemy b{&r, &s, &g, &x, &aux, token, words};
    exchange(b, false);
    if (s.enemy[0x2fc / 4] > 32) {
        g.bitWordCount = (uint64_t(s.enemy[0x2fc / 4]) + 31) / 32;
        if (g.bitWordCount > 1000000) {
            r.fail(2);
            return 0;
        }
        g.bitWords = r.span(s.enemy[0x300 / 4], uint32_t(g.bitWordCount));
    }
    uint32_t result = 0;
    uint32_t ok = claw_enemy_motion_aux_entry(&s, &aux, f, argument, enemyDependency, &b, &result);
    if (!ok)
        ok = claw_common_enemy_entry(&s, &human, f, argument, enemyDependency, &b, &result);
    if (!ok || aux.fault)
        r.fail(aux.fault ? aux.fault : 2);
    exchange(b, true);
    return result;
}
struct Player {
    Run *r;
    ClawPlayerLocomotion *s;
    uint32_t actor, logic, priv;
};
void playerExchange(Player &b, bool output) {
    auto &r = *b.r;
    auto *a = r.span(b.actor, 128), *p = r.span(b.priv, 78);
    if (!a || !p)
        return;
    auto *g = r.c->globals;
    if (output) {
        std::copy_n(b.s->actor, 128, a);
        std::copy_n(b.s->privateWords, 78, p);
        r.wr(b.logic + 28, b.s->logicState);
        r.wr(g->inputToken + 12, b.s->inputLatched);
        if (r.c->playerPhysics)
            *r.c->playerPhysics = b.s->physics;
        g->pixelScratch = b.s->pixelScratch;
        g->powerup = b.s->powerup;
        uint32_t held = b.s->privateWords[75];
        if (held) {
            uint32_t e = r.enemy(held);
            r.wr(e + 20, b.s->weaponLogicCallback);
            if (b.s->weaponDeleteCount) {
                uint32_t backing = b.s->weaponDeleteCount < 33 ? e + 0x300 : r.rd(e + 0x300);
                r.wr(backing, b.s->weaponDeleteFlags);
            }
        }
    } else {
        std::copy_n(a, 128, b.s->actor);
        std::copy_n(p, 78, b.s->privateWords);
        b.s->logicState = r.rd(b.logic + 28);
        b.s->inputLatched = r.rd(g->inputToken + 12);
        b.s->inputHeld = r.rd(g->inputToken + 8);
        b.s->stageDelta = g->stageDelta;
        b.s->animationDelta = g->animationDelta;
        b.s->powerup = g->powerup;
        b.s->pixelScratch = g->pixelScratch;
        if (r.c->playerPhysics)
            b.s->physics = *r.c->playerPhysics;
        uint32_t held = b.s->privateWords[75];
        if (held) {
            uint32_t e = r.enemy(held);
            b.s->weaponLogicStatus = si(r.rd(e + 32));
            b.s->weaponLogicCallback = r.rd(e + 20);
            b.s->weaponDeleteCount = r.rd(e + 0x2fc);
            if (b.s->weaponDeleteCount)
                b.s->weaponDeleteFlags = r.rd(b.s->weaponDeleteCount < 33 ? e + 0x300 : r.rd(e + 0x300));
        }
    }
}
uint32_t playerDependency(ClawPlayerLocomotion *, uint32_t f, uint32_t a, uint32_t b, uint32_t c, void *u) {
    auto &p = *static_cast<Player *>(u);
    auto &r = *p.r;
    playerExchange(p, true);
    uint32_t result = 0;
    if (f == 0x41dc50)
        result = r.invoke(f, 0, {p.actor, p.logic, p.priv, a});
    else if (f == 0x41d750)
        result = r.invoke(f, 0, {p.actor, p.logic, p.priv}, "target output in context.attack");
    else if (f == 0x4c79e0 || f == 0x420a10)
        result = r.invoke(f, p.actor, {a, b});
    else if (f == 0x4c8220 || f == 0x4c82a0 || f == 0x420970)
        result = r.invoke(f, p.actor + 0x188, {a});
    else if (f == 0x4f6286)
        result = r.invoke(f, r.rd(r.rd(p.actor + 12) + 44) + 16, {a});
    else if (f == 0x421010)
        result = r.invoke(f, r.enemy(a), {b, c});
    else if (f == 0x420fc0 || f == 0x4dbd20)
        result = r.invoke(f, r.enemy(a) + 0x2f4, {b});
    else if (f == 0x48c8a0)
        result = r.invoke(f, 0, {a, b});
    else if (f == 0x4a3050)
        result = r.invoke(f, 0, {});
    else
        result = r.invoke(f, 0, {a, b, c});
    playerExchange(p, false);
    if (r.c->attack && r.c->attack->targetToken) {
        if (auto *target = r.span(r.c->attack->targetToken, 128))
            std::copy_n(target, 128, r.c->attack->targetActor);
    }
    return result;
}
uint32_t playerSource(Run &r, uint32_t f, const uint32_t *a) {
    if (!r.c->playerPhysics) {
        r.fail();
        return 0;
    }
    ClawPlayerLocomotion s{};
    Player b{&r, &s, a[0], a[1], a[2]};
    playerExchange(b, false);
    uint32_t value = 0;
    if (f == 0x4171d0)
        value = claw_player_enter_stand(&s, playerDependency, &b);
    else {
        if (!r.c->attack) {
            r.fail();
            return 0;
        }
        r.c->attack->pressed = r.rd(r.c->globals->inputToken + 4);
        value = claw_player_select_attack(&s, r.c->attack, playerDependency, &b);
    }
    playerExchange(b, true);
    return value;
}
void bit(Run &r, uint32_t t, uint32_t index, bool toggle = false) {
    uint32_t count = r.rd(t + 8);
    if (count <= index) {
        r.invoke(0x4dbd20, t, {index});
        return;
    }
    uint32_t backing = count < 33 ? t + 12 : r.rd(t + 12), word = backing + (index >> 5) * 4, mask = 1u << (index & 31);
    r.wr(word, toggle ? r.rd(word) ^ mask : r.rd(word) | mask);
}
void cleanup(Run &r, uint32_t actor, uint32_t priv) {
    uint32_t input = r.c->globals->inputToken;
    r.wr(input + 12, r.rd(input + 12) & 0xfcffffff);
    uint32_t held = r.rd(priv + 300);
    if (held) {
        uint32_t e = r.enemy(held);
        if (si(r.rd(e + 32)) > 0)
            r.wr(e + 20, 0x4207a0);
        bit(r, e + 0x2f4, 0);
        r.wr(priv + 300, 0);
    }
    r.wr(priv + 60, 0);
    r.wr(priv + 32, 1);
    if (r.rd(priv + 4)) {
        r.wr(priv + 4, 0);
        r.invoke(0x4c8220, actor + 0x188, {r.rd(priv + 0x124)});
        r.wr(actor + 8, r.rd(actor + 8) | 0x80);
    }
}
void rectangles(Run &r, uint32_t actor, uint32_t priv) {
    bool right = r.rd(priv) != 0;
    r.wr(actor + 0x128, right ? 0xffffffea : 0xfffffff1);
    r.wr(actor + 0x12c, 0xffffffd3);
    r.wr(actor + 0x130, right ? 15 : 22);
    r.wr(actor + 0x134, 52);
    r.wr(actor + 0x118, 0xfffffff0);
    r.wr(actor + 0x11c, 0xffffffcc);
    r.wr(actor + 0x120, 16);
    r.wr(actor + 0x124, 60);
}
void mirror(Run &r, uint32_t actor) {
    for (uint32_t o : {0x118u, 0x128u, 0x138u})
        if (r.rd(actor + o) != 0x80000000) {
            uint32_t left = r.rd(actor + o);
            r.wr(actor + o, 0u - r.rd(actor + o + 8));
            r.wr(actor + o + 8, 0u - left);
        }
}
void facing(Run &r, uint32_t actor, uint32_t priv, bool right) {
    uint32_t current = r.rd(priv);
    if ((right && !current) || (!right && current)) {
        r.wr(actor + 0x40, right ? r.rd(actor + 0x40) & ~2u : r.rd(actor + 0x40) | 2);
        mirror(r, actor);
        r.wr(priv, right ? 1 : 0);
        r.wr(priv + 0x114, 1500);
    }
}
void fall(Run &r, uint32_t actor, uint32_t logic, uint32_t priv, bool lookup) {
    uint32_t status = r.rd(priv + 60);
    if (status == 8 || status == 9 || status == 10 || status == 18) {
        uint32_t registry = r.rd(r.rd(actor + 12) + 44);
        uint32_t seq =
            r.invoke(lookup ? 0x4f6286 : 0x4061b0, lookup ? registry + 16 : registry, {0x5246dc}, "CLAW_FALL");
        r.wr(priv + 0x124, seq);
    } else {
        cleanup(r, actor, priv);
        r.invoke(0x4c79e0, actor, {0x5246dc, 0});
    }
    r.wr(logic + 28, 25);
    r.wr(actor + 0xcc, 4);
    r.wr(actor + 0x148, 0);
    r.wr(actor + 0x14c, 0);
    r.wr(actor + 8, r.rd(actor + 8) & ~0x10u);
    rectangles(r, actor, priv);
    r.wr(priv + 64, 0);
    r.c->playerPhysics->velocity[1] = 0;
    r.c->playerPhysics->acceleration[1] = 2250;
}
void standing(Run &r, uint32_t actor, uint32_t logic, uint32_t priv) {
    cleanup(r, actor, priv);
    r.wr(logic + 28, 24);
    r.invoke(0x4c79e0, actor, {0x5246d0, 1});
    r.wr(actor + 0xcc, 1);
    r.wr(actor + 0x148, 0);
    r.wr(actor + 0x14c, 0);
    r.wr(actor + 0x104, 0);
    r.wr(actor + 8, r.rd(actor + 8) | 0x80);
    rectangles(r, actor, priv);
    r.wr(priv + 0xfc, 650);
    r.wr(priv + 0x114, 1500);
    r.wr(priv + 0x120, 15000);
    r.wr(priv + 0x118, 0);
    for (double &v : r.c->playerPhysics->remainder)
        v = 0;
    r.wr(actor + 0x1b0, 0x3f800000);
}
void platform(Run &r, uint32_t actor, uint32_t &x, uint32_t &y) {
    if ((r.rd(actor + 8) & 0x10) && r.rd(actor + 0x80)) {
        uint32_t p = r.rd(actor + 0x80);
        x += r.rd(p + 0x158);
        y += r.rd(p + 0x15c);
    }
}
uint32_t body(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    auto *g = r.c->globals;
    switch (f) {
    case 0x440420:
    case 0x440120:
    case 0x440710:
    case 0x440350:
    case 0x4407d0:
    case 0x4409d0:
    case 0x440410:
    case 0x4405b0:
    case 0x440260:
    case 0x440870:
    case 0x440a50:
    case 0x440b20:
    case 0x440c90:
    case 0x404e00:
        return inherited(r, f, t, f == 0x404e00 ? a[0] : 0);
    case 0x421010:
        if (si(a[1]) <= si(r.rd(t + 32)))
            r.wr(t + 20, a[0]);
        return 0;
    case 0x420fc0:
        bit(r, t, a[0]);
        return 0;
    case 0x4dbd20:
        if (r.invoke(0x4dc6d0, t, {a[0] + 1})) {
            uint32_t backing = r.rd(t + 8) < 33 ? t + 12 : r.rd(t + 12), word = backing + (a[0] >> 5) * 4;
            r.wr(word, r.rd(word) | (1u << (a[0] & 31)));
        }
        return t;
    case 0x4dc6d0: {
        uint32_t words = (a[0] >> 5) + ((a[0] & 31) != 0), count = r.rd(t + 8), backing = 0;
        if (words > 1000000) {
            r.fail(2);
            return 0;
        }
        if (count < 33) {
            backing = r.invoke(0x4a48e0, 0, {words * 4});
            if (backing) {
                if (auto *p = r.span(backing, words))
                    std::fill_n(p, words, 0);
                r.copy(backing, t + 12, 1);
            }
        } else {
            backing = r.invoke(0x4a9070, 0, {r.rd(t + 12), words * 4});
            if (backing) {
                uint32_t oldWords = count >> 5, clear = (words - oldWords) & 0x3fffffff;
                if (clear > 1000000) {
                    r.fail(2);
                    return 0;
                }
                if (auto *p = r.span(backing + oldWords * 4, clear))
                    std::fill_n(p, clear, 0);
            }
        }
        if (!backing) {
            if (!r.c->core) {
                r.fail();
                return 0;
            }
            uint32_t address = words + 4, aligned = address & ~3u, shift = (address & 3u) * 8, value = r.rd(aligned);
            if (shift)
                value = (value >> shift) | (r.rd(aligned + 4) << (32 - shift));
            if (r.c->fault)
                return 0;
            r.c->core->words[0] = value;
            r.invoke(0x4db4d0, r.rd(t + 4), {t, r.c->core->words[14], 12});
            return 0;
        }
        r.wr(t + 12, backing);
        r.wr(t + 8, words * 32);
        return 1;
    }
    case 0x4207a0:
        return r.invoke(r.rd(r.rd(t) + 0x94), t, {});
    case 0x41c4e0:
        cleanup(r, a[0], a[2]);
        return 0;
    case 0x4171d0:
    case 0x41d850:
        return playerSource(r, f, a);
    case 0x41dc50: {
        uint32_t actor = a[0], logic = a[1], priv = a[2], target = a[3];
        if (!r.c->playerPhysics) {
            r.fail();
            return 0;
        }
        r.wr(logic + 28, 5000);
        r.invoke(0x4c79e0, actor, {r.rd(target + 0x164) & 4 ? 0x524888u : 0x52487cu, 0});
        r.wr(actor + 0xcc, 1);
        r.wr(actor + 0x148, 0);
        r.wr(actor + 0x14c, 0);
        r.wr(priv + 8, 0);
        r.wr(priv + 12, 0);
        r.wr(priv + 300, target);
        r.wr(priv + 0xf0, 100000);
        r.wr(priv + 0xf4, 0);
        uint32_t e = r.enemy(target), count = r.rd(e + 0x2fc);
        if (count)
            bit(r, e + 0x2f4, 0, true);
        uint32_t owner = r.rd(e + 12), z = r.rd(actor + 100) + 1;
        if (r.rd(owner + 100) != z) {
            r.wr(owner + 100, z);
            r.wr(owner + 8, r.rd(owner + 8) | 0x20000);
        }
        r.invoke(r.rd(r.rd(e) + 0x88), e, {});
        r.copy(priv + 0xd8, actor + 0x118, 4);
        r.wr(actor + 0x11c, r.rd(actor + 0x11c) - 25);
        for (double &v : r.c->playerPhysics->remainder)
            v = 0;
        return 0;
    }
    case 0x41b1f0: {
        uint32_t actor = a[0], logic = a[1], priv = a[2];
        r.wr(logic + 28, 5001);
        r.invoke(0x4c79e0, actor, {0x524774, 0});
        r.wr(actor + 0xcc, 1);
        r.wr(actor + 0x148, 0);
        r.wr(actor + 0x14c, 0);
        uint32_t root = r.rd(actor + 0x170);
        if (root) {
            uint32_t image =
                si(r.rd(root + 100)) < 45 && si(r.rd(root + 104)) > 43 ? r.rd(r.rd(root + 20) + 44 * 4) : 0;
            r.wr(actor + 0x174, image);
            r.wr(actor + 0x16c, 44);
        }
        uint32_t e = r.enemy(r.rd(priv + 300));
        r.invoke(r.rd(r.rd(e) + 0xa0), e, {});
        return 0;
    }
    case 0x41a850: {
        uint32_t actor = a[0], logic = a[1], priv = a[2];
        if (!r.c->playerPhysics) {
            r.fail();
            return 0;
        }
        auto *p = r.c->playerPhysics;
        uint32_t x = r.rd(actor + 76), y = r.rd(actor + 80), held = r.rd(g->inputToken + 8);
        if ((held & 0x1000000) && r.rd(priv + 8)) {
            facing(r, actor, priv, false);
            if (r.rd(priv + 12) || p->velocity[0] == 30) {
                r.invoke(0x4c79e0, actor, {0x524758, 0});
                p->velocity[0] = -30;
                r.wr(priv + 12, 0);
            }
        } else if ((held & 0x2000000) && r.rd(priv + 8)) {
            facing(r, actor, priv, true);
            if (r.rd(priv + 12) || p->velocity[0] == -30) {
                r.invoke(0x4c79e0, actor, {0x524758, 0});
                p->velocity[0] = 30;
                r.wr(priv + 12, 0);
            }
        } else
            p->velocity[0] = 0;
        if (r.invoke(0x4c82a0, actor + 0x188, {g->animationDelta}) != 1) {
            volatile double seconds = double(g->stageDelta) * .001;
            claw_physics_update(p, seconds);
            x += claw_physics_pixel_x(p, &g->pixelScratch);
        }
        platform(r, actor, x, y);
        r.invoke(0x4cbb60, r.rd(r.rd(actor + 12) + 36), {actor, x, y, 24});
        if (r.rd(actor + 0xcc) != 4) {
            if ((r.rd(actor + 0x1a4) && !r.rd(actor + 0x19c) && !r.rd(priv + 8)) ||
                (r.rd(priv + 8) && p->velocity[0] == 0)) {
                r.invoke(0x4c79e0, actor, {0x52474c, 0});
                r.wr(priv + 8, 1);
                r.wr(priv + 12, 1);
            }
            if (r.rd(priv + 8) && (r.rd(g->inputToken + 4) & 0x22)) {
                r.copy(actor + 0x118, priv + 0xd8, 4);
                r.invoke(0x41b1f0, 0, {actor, logic, priv});
            }
            uint32_t timer = r.rd(priv + 0xf0);
            if (g->animationDelta < timer) {
                r.wr(priv + 0xf0, timer - g->animationDelta);
                return 0;
            }
            uint32_t e = r.enemy(r.rd(priv + 300));
            r.invoke(0x421010, e, {0x4207a0, 1});
            r.invoke(0x420fc0, e + 0x2f4, {0});
            r.wr(priv + 300, 0);
            r.copy(actor + 0x118, priv + 0xd8, 4);
            r.invoke(0x4171d0, 0, {actor, logic, priv});
            return 0;
        }
        uint32_t e = r.enemy(r.rd(priv + 300));
        if (si(r.rd(e + 32)) > 0)
            r.wr(e + 20, 0x4207a0);
        r.number(e + 0x50, p->velocity[0] > 0 ? 225 : p->velocity[0] < 0 ? -225 : 0);
        bit(r, e + 0x2f4, 0);
        r.wr(priv + 300, 0);
        r.copy(actor + 0x118, priv + 0xd8, 4);
        fall(r, actor, logic, priv, false);
        return 0;
    }
    case 0x41b280: {
        uint32_t actor = a[0], logic = a[1], priv = a[2];
        if (!r.c->playerPhysics) {
            r.fail();
            return 0;
        }
        uint32_t x = r.rd(actor + 76), y = r.rd(actor + 80);
        r.wr(actor + 0x148, 0);
        r.wr(actor + 0x14c, 0);
        platform(r, actor, x, y);
        uint32_t held = r.rd(g->inputToken + 8);
        if ((held & 0x1000000) && r.rd(priv))
            facing(r, actor, priv, false);
        else if ((held & 0x2000000) && !r.rd(priv))
            facing(r, actor, priv, true);
        r.invoke(0x4cbb60, r.rd(r.rd(actor + 12) + 36), {actor, x, y, 24});
        if (r.rd(actor + 0xcc) == 4) {
            r.wr(priv + 300, 0);
            fall(r, actor, logic, priv, true);
            return 0;
        }
        uint32_t charge = r.rd(priv + 0xf4);
        if ((r.rd(g->inputToken + 8) & 0x22) && charge < 3000) {
            r.wr(priv + 0xf4, g->animationDelta + charge);
            return 0;
        }
        if (r.invoke(0x4c82a0, actor + 0x188, {g->animationDelta}) == 1 && r.rd(priv + 300)) {
            uint32_t e = r.enemy(r.rd(priv + 300)), power = r.rd(priv + 0xf4);
            bit(r, e + 0x2f4, 0);
            r.invoke(r.rd(r.rd(e) + 0x80), e, {(power * 100) / 3000});
            r.invoke(r.rd(r.rd(e) + 0x84), e, {});
            r.wr(priv + 300, 0);
            uint32_t reg = r.rd(r.rd(actor + 12) + 40);
            if (!r.rd(reg + 48)) {
                uint32_t sound = r.invoke(0x4f6286, reg + 16, {0x524780}, "CLAW_GRUNTTHROW");
                if (sound && g->audioEnabled)
                    r.invoke(0x4b45f0, r.rd(sound + 16), {g->masterVolume, 0, 0, 0});
            }
        }
        if (r.rd(actor + 0x1a4) && !r.rd(actor + 0x19c)) {
            r.wr(priv + 300, 0);
            standing(r, actor, logic, priv);
        }
        return 0;
    }

    default:
        r.fail(2);
        return 0;
    }
}
} // namespace
extern "C" void claw_lift_throw_defaults(ClawLiftThrowGlobals *g) {
    if (!g)
        return;
    ClawGenericEnemyContext c{};
    claw_generic_enemy_context_defaults(&c);
    std::copy_n(c.defaults, 24, g->physicsDefaults);
}
extern "C" uint32_t claw_lift_throw_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                          ClawLiftThrowContext *c, ClawLiftThrowDependency d, void *u,
                                          uint32_t *result) {
    if (!known(f))
        return 0;
    if (!c || !c->globals)
        return 0;
    uint32_t count = 0;
    switch (f) {
    case 0x41dc50:
        count = 4;
        break;
    case 0x41a850:
    case 0x41b1f0:
    case 0x41b280:
    case 0x41c4e0:
    case 0x4171d0:
    case 0x41d850:
        count = 3;
        break;
    case 0x421010:
        count = 2;
        break;
    case 0x420fc0:
    case 0x4dbd20:
    case 0x4dc6d0:
    case 0x404e00:
        count = 1;
        break;
    default:
        break;
    }
    if (n != count || (!a && n)) {
        c->fault = 2;
        return 0;
    }
    Run r{c, d, u};
    uint32_t value = body(r, f, t, a);
    if (result)
        *result = value;
    return c->fault ? 0 : 1;
}
