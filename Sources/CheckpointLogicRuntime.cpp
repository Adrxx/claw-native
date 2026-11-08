#include "CheckpointLogicRuntime.h"
#include "ActorResourceBindings.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawCheckpointContext *c;
    ClawCheckpointDependency dependency;
    void *user;
    uint32_t *packet = nullptr;
};
bool bad(const Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    if (bad(r))
        return nullptr;
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, n) : nullptr;
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
int32_t signedWord(uint32_t v) {
    int32_t out;
    std::memcpy(&out, &v, 4);
    return out;
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x522838:
        return "CheckpointAttack";
    case 0x5227e0:
        return "SuperCheckpointAttack";
    case 0x525378:
        return "GAME_CHECKPOINT_WAVE";
    case 0x525390:
        return "GAME_CHECKPOINT_RISE";
    case 0x5253c4:
        return "Your game was not saved because you cheated!";
    case 0x5253a8:
        return "Your game has been saved";
    default:
        return nullptr;
    }
}
uint32_t invoke(Run &r, ClawCheckpointCall e) {
    if (bad(r))
        return 0;
    if (r.dependency)
        return r.dependency(r.c, &e, r.user);
    if (!e.bufferCount && r.c->scene.call) {
        ClawSceneActorCall a{e.function, e.receiver, {0, 0, 0, 0}, e.argumentCount};
        std::copy_n(e.arguments, e.argumentCount, a.arguments);
        return r.c->scene.call(r.c->scene.context, a);
    }
    r.c->fault = 1;
    return 0;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    ClawCheckpointCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    if (args.size())
        e.name = label(e.arguments[0]);
    return invoke(r, e);
}
uint32_t *aniLookup(void *u, uint32_t t, uint32_t n) {
    return span(*static_cast<Run *>(u), t, n);
}
uint32_t aniCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    ClawCheckpointCall v{};
    v.function = e.function;
    v.receiver = e.receiver;
    v.argumentCount = e.argumentCount;
    std::copy_n(e.arguments, e.argumentCount, v.arguments);
    if (e.argumentCount)
        v.name = label(e.arguments[0]);
    return invoke(r, v);
}
void animation(Run &r, uint32_t f, uint32_t actor, uint32_t a) {
    if (bad(r))
        return;
    if (!r.c->composeAnimation) {
        if (f == 0x4c79e0)
            call(r, f, actor, {a, 0});
        else
            call(r, f, actor + 0x188, {a});
        return;
    }
    auto h = r.c->scene;
    h.context = &r;
    h.lookup = aniLookup;
    h.call = aniCall;
    ClawActorAnimationGlobals g{r.c->globals->animationDelta, r.c->globals->audioPosition};
    uint32_t result = 0, fault = 0;
    if (!claw_actor_animation_entry(f, f == 0x4c79e0 ? actor : actor + 0x188, a, 0, &g, h, &fault, &result))
        fault = 3;
    if (fault)
        r.c->fault = fault;
}
struct Binding {
    Run *run;
    uint32_t actor, token;
};
void commit(Binding &b, ClawActorResourceBindings *s) {
    auto &r = *b.run;
    auto *actor = span(r, b.actor, 128);
    if (actor)
        std::copy_n(s->actor, 128, actor);
    if (b.token) {
        auto *logic = span(r, b.token, 93);
        if (logic)
            std::copy_n(s->secondary, 93, logic);
    }
}
void reload(Binding &b, ClawActorResourceBindings *s) {
    auto &r = *b.run;
    auto *actor = span(r, b.actor, 128);
    if (actor)
        std::copy_n(actor, 128, s->actor);
    if (b.token) {
        auto *logic = span(r, b.token, 93);
        if (logic)
            std::copy_n(logic, 93, s->secondary);
    }
}
uint32_t bindingCall(ClawActorResourceBindings *s, ClawActorBindingContext *c, const ClawActorBindingCall *e,
                     void *user) {
    auto &b = *static_cast<Binding *>(user);
    auto &r = *b.run;
    commit(b, s);
    const uint32_t value = call(r, e->function, e->receiver, {e->argument});
    if (e->function == 0x4f63ec)
        b.token = value;
    reload(b, s);
    if (e->function != 0x4f63ec && s->actor[0x78 / 4] != b.token)
        r.c->fault = 3;
    if (!bad(r)) {
        c->metadataCallback = read(r, c->metadataToken + 16);
        if (e->function != 0x4f63ec && s->secondary[6])
            c->associatedDestructor = read(r, read(r, s->secondary[6]));
    }
    return value;
}
void bindContact(Run &r, uint32_t actor, uint32_t name) {
    if (bad(r))
        return;
    if (!r.c->composeContactBinding) {
        call(r, 0x4c8060, actor, {name});
        return;
    }
    const uint32_t registry = read(r, read(r, actor + 0xc) + 0x14) + 16, meta = call(r, 0x4f6286, registry, {name});
    if (!meta || bad(r))
        return;
    auto *metadata = span(r, meta, 5);
    auto *a = span(r, actor, 128);
    if (!metadata || !a)
        return;
    ClawActorBindingContext c{};
    c.metadataToken = meta;
    c.metadataCallback = metadata[4];
    c.metadataFlags = metadata[3];
    ClawActorResourceBindings state{};
    std::copy_n(a, 128, state.actor);
    Binding b{&r, actor, state.actor[0x78 / 4]};
    if (b.token) {
        auto *s = span(r, b.token, 93);
        if (!s)
            return;
        std::copy_n(s, 93, state.secondary);
        if (s[0] != 0x513740) {
            r.c->fault = 3;
            return;
        }
        if (s[6])
            c.associatedDestructor = read(r, read(r, s[6]));
    }
    claw_actor_bind_contact_logic(&state, &c, bindingCall, &b);
    commit(b, &state);
}
uint32_t seal(Run &r, uint32_t *out, uint32_t token) {
    if (!out)
        return 0;
    uint32_t time = token;
    ClawCheckpointCall e{};
    e.function = 0x4a3b10;
    e.argumentCount = 1;
    e.localMask = 0;
    e.bufferCount = 2;
    e.buffers[0] = &time;
    e.bufferWords[0] = 1;
    e.buffers[1] = r.packet ? r.packet : out;
    e.bufferWords[1] = r.packet ? 44 : 17;
    time = invoke(r, e);
    e.function = 0x4a5c60;
    e.argumentCount = 1;
    e.localMask = 1;
    uint32_t tm = invoke(r, e);
    out[3] = read(r, tm + 16) + 1;
    if (bad(r))
        return 0;
    tm = invoke(r, e);
    out[4] = read(r, tm + 12);
    if (bad(r))
        return 0;
    tm = invoke(r, e);
    out[5] = read(r, tm + 20) + 1900;
    return bad(r) ? 0 : 1;
}
uint32_t pack(Run &r, uint32_t *out, uint32_t outToken, const uint32_t *counts, uint32_t time) {
    if (!out || !counts)
        return 0;
    out[2] = time;
    for (uint32_t i = 0; i < 10; ++i)
        out[7 + i] = counts[i];
    const uint32_t weights[10] = {100, 500, 1500, 2500, 5000, 7500, 10000, 15000, 25000, 0};
    uint32_t sum = 0;
    for (uint32_t i = 0; i < 10; ++i)
        sum += out[7 + i] * weights[i];
    out[1] = sum;
    seal(r, out, outToken);
    return 1;
}
uint32_t cacheRecord(uint32_t receiver, uint32_t level, uint32_t kind) {
    if (signedWord(level) < 0 || level >= 15 || kind < 1 || kind > 3)
        return 0;
    const uint32_t offsets[3] = {0x2d4, 0xd24, 0x1774};
    return receiver + offsets[kind - 1] + level * 176;
}
uint32_t cacheWrite(Run &r, uint32_t receiver, uint32_t level, const uint32_t *source, uint32_t kind) {
    if (signedWord(level) < 0 || level >= 15 || !source || kind < 1 || kind > 3)
        return 0;
    const uint32_t target = cacheRecord(receiver, level, kind);
    if (!target)
        return 0;
    auto *out = span(r, target, 44);
    if (!out)
        return 0;
    for (uint32_t i = 0; i < 44; ++i)
        out[i] = source[i];
    out[0] = (out[0] & 0xffffff8f) | 2;
    out[0] |= uint32_t(8) << kind;
    return 1;
}
uint32_t cacheBest(Run &r, uint32_t receiver, uint32_t level, const uint32_t *source) {
    if (signedWord(level) < 0 || level >= 15 || !source)
        return 0;
    const uint32_t target = receiver + 0x21c4 + level * 68;
    if (!target)
        return 0;
    auto *out = span(r, target, 17);
    if (!out)
        return 0;
    if (out[1] > source[1] || (out[1] == source[1] && out[2] < source[2]))
        return 0;
    for (uint32_t i = 0; i < 17; ++i)
        out[i] = source[i];
    return 1;
}
void cacheReset(Run &r, uint32_t receiver) {
    for (uint32_t level = 0; level < 15 && !bad(r); ++level) {
        for (uint32_t kind = 1; kind <= 3 && !bad(r); ++kind) {
            auto *p = span(r, cacheRecord(receiver, level, kind), 44);
            if (!p)
                break;
            const uint32_t keep = p[0] & 1;
            std::fill_n(p, 44, 0);
            p[0] = keep | (uint32_t(8) << kind);
        }
        auto *best = span(r, receiver + 0x21c4 + level * 68, 17);
        if (best)
            std::fill_n(best, 17, 0);
    }
}
uint32_t save(Run &r, uint32_t owner, uint32_t x, uint32_t y, uint32_t kind) {
    auto &g = *r.c->globals;
    if (read(r, owner + 0x258) || bad(r))
        return 0;
    const bool position = !(signedWord(x) < 1 && signedWord(y) < 1);
    if (!position)
        kind = 3;
    else if (!g.playerToken || (kind != 1 && kind != 2))
        return 0;
    if (position) {
        if (read(r, owner + 0x168) & 1 || bad(r))
            return 0;
        const uint32_t cheat = read(r, read(r, read(r, owner + 4) + 0x48) + 0x128);
        if (cheat || bad(r))
            return 0;
    }
    const uint32_t store = read(r, read(r, owner + 4) + 100);
    if (!store || bad(r))
        return 0;
    uint32_t data[44]{};
    auto *old = r.packet;
    r.packet = data;
    uint32_t duration = 0;
    if (position) {
        const uint32_t priv = read(r, read(r, g.playerToken + 0x6c) + 0x14);
        if (!priv || bad(r)) {
            r.packet = old;
            return 0;
        }
        data[1] = x;
        data[2] = y;
        data[37] = read(r, g.playerToken + 0x10c);
        for (uint32_t i = 0; i < 4; ++i)
            data[38 + i] = read(r, priv + 0x70 + i * 4);
        duration = read(r, owner + 0x164) + g.tick;
        pack(r, data + 20, 0, span(r, priv + 0x88, 10), g.tick);
        pack(r, data + 3, 0, span(r, priv + 0xb0, 10), duration);
    } else {
        data[0] |= 1;
        data[37] = g.defaultHealth;
        std::copy_n(g.defaultAmmo, 4, data + 38);
        duration = read(r, owner + 0x164);
        pack(r, data + 20, 0, g.levelTreasures, read(r, owner + 0x164 + read(r, owner + 0x14) * 16));
        pack(r, data + 3, 0, g.totalTreasures, duration);
    }
    if (!bad(r)) {
        const uint32_t level = read(r, owner + 0x14);
        if (!(read(r, owner + 0x168) & 1)) {
            ClawCheckpointCall e{};
            e.function = 0x49a860;
            e.receiver = store;
            e.argumentCount = 3;
            e.arguments[0] = level;
            e.arguments[2] = kind;
            e.localMask = 2;
            e.bufferCount = 1;
            e.buffers[0] = data;
            e.bufferWords[0] = 44;
            if (r.c->composeSaveCache)
                cacheWrite(r, store, level, data, kind);
            else
                invoke(r, e);
            if (!position && !bad(r)) {
                e.function = 0x49a800;
                e.argumentCount = 2;
                e.arguments[0] = read(r, owner + 0x14);
                e.buffers[0] = data + 20;
                e.bufferWords[0] = 17;
                if (r.c->composeSaveCache)
                    cacheBest(r, store, e.arguments[0], data + 20);
                else
                    invoke(r, e);
                e.arguments[0] = 0;
                e.buffers[0] = data + 3;
                if (r.c->composeSaveCache)
                    cacheBest(r, store, 0, data + 3);
                else
                    invoke(r, e);
            }
        } else if (!position) {
            const uint32_t record =
                r.c->composeSaveCache ? cacheRecord(store, level, kind) : call(r, 0x49ae60, store, {level, kind});
            if (record)
                write(r, record, read(r, record) | 1);
        }
    }
    r.packet = old;
    return 1;
}
void contact(Run &r, uint32_t actor) {
    const uint32_t p = read(r, actor + 0x6c);
    auto &g = *r.c->globals;
    write(r, read(r, g.managerToken + 0x2c) + 0x44, read(r, actor + 0x4c));
    write(r, read(r, g.managerToken + 0x2c) + 0x48, read(r, actor + 0x50) - 32);
    animation(r, 0x4c79e0, actor, 0x525390);
    write(r, actor + 8, read(r, actor + 8) | 1);
    write(r, p + 0x1c, 6);
    if (!bad(r))
        g.timerRemaining += g.timerBonus;
}
void superContact(Run &r, uint32_t actor) {
    contact(r, actor);
    auto &g = *r.c->globals;
    uint32_t owner = read(r, g.managerToken + 0x2c), f = read(r, read(r, owner) + 0x10);
    uint32_t mode = f == 0x40af90 ? 3 : call(r, f, owner);
    if (bad(r) || mode != 3)
        return;
    if (read(r, read(r, g.managerToken + 0xc0) - 8) || bad(r))
        return;
    const uint32_t cb = read(r, read(r, actor + 0x6c) + 0x10);
    uint32_t kind = cb == 0x4232c0 ? 1 : cb == 0x4232e0 ? 2 : 0;
    if (!kind || bad(r))
        return;
    if (read(r, read(r, g.managerToken + 0x48) + 0x128)) {
        call(r, 0x42af70, g.managerToken, {0x5253c4});
        return;
    }
    owner = read(r, g.managerToken + 0x2c);
    const uint32_t x = read(r, g.playerToken + 0x4c), y = read(r, g.playerToken + 0x50);
    const uint32_t ok = r.c->composeSave ? save(r, owner, x, y, kind) : call(r, 0x46d620, owner, {x, y, kind});
    if (ok && !bad(r)) {
        call(r, 0x49bbc0, read(r, g.managerToken + 0x60));
        call(r, 0x42af70, g.managerToken, {0x5253a8});
        call(r, 0x42abf0, g.managerToken);
    }
}
void update(Run &r, uint32_t actor, bool super) {
    const uint32_t p = read(r, actor + 0x6c), state = read(r, p + 0x1c);
    if (bad(r))
        return;
    if (!state) {
        if (super && r.c->globals->skipNextSuper) {
            r.c->globals->skipNextSuper = 0;
            write(r, p + 0x1c, 5);
            write(r, actor + 8, read(r, actor + 8) | 0x10000);
            return;
        }
        const uint32_t image = read(r, actor + 0x174);
        write(r, actor + 0xd0, 0x800);
        write(r, actor + 8, read(r, actor + 8) | 4);
        write(r, actor + 0xd8, 2);
        if (image) {
            write(r, actor + 0x138, read(r, image + 0x20) - read(r, image + 0x18));
            write(r, actor + 0x13c, read(r, image + 0x24) - read(r, image + 0x1c));
            write(r, actor + 0x140, read(r, image + 0x20) + read(r, image + 0x18) - 1);
            write(r, actor + 0x144, read(r, image + 0x24) + read(r, image + 0x1c) - 1);
        }
        bindContact(r, actor, super ? 0x5227e0 : 0x522838);
        if (super)
            write(r, actor + 0x13c, read(r, actor + 0x13c) - 64);
        write(r, p + 0x1c, 5);
    } else if (state == 1 || state == 6) {
        animation(r, 0x4c82a0, actor, r.c->globals->animationDelta);
        if (state == 6 && read(r, actor + 0x1a4) && !read(r, actor + 0x19c) && !bad(r)) {
            animation(r, 0x4c79e0, actor, 0x525378);
            write(r, p + 0x1c, 1);
        }
    }
}
} // namespace
extern "C" uint32_t claw_checkpoint_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n,
                                          ClawCheckpointContext *c, ClawCheckpointDependency dependency, void *user,
                                          uint32_t *result) {
    if (!c || !c->globals)
        return 0;
    uint32_t count = 1;
    switch (f) {
    case 0x422ef0:
    case 0x422ff0:
    case 0x423060:
    case 0x4231a0:
    case 0x4232c0:
    case 0x4232e0:
    case 0x49aa40:
        break;
    case 0x46d620:
    case 0x49a9d0:
    case 0x49a860:
        count = 3;
        break;
    case 0x49a800:
    case 0x49ae60:
        count = 2;
        break;
    case 0x49a720:
    case 0x40af90:
        count = 0;
        break;
    default:
        return 0;
    }
    if (n != count || (count && !args)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{c, dependency, user};
    uint32_t value = 1;
    switch (f) {
    case 0x422ff0:
        contact(r, args[0]);
        value = 0;
        break;
    case 0x4231a0:
        superContact(r, args[0]);
        break;
    case 0x46d620:
        value = save(r, receiver, args[0], args[1], args[2]);
        break;
    case 0x49a9d0:
        value = args[0] && args[1] ? pack(r, span(r, args[0], 17), args[0], span(r, args[1], 10), args[2]) : 0;
        break;
    case 0x49aa40:
        value = seal(r, args[0] ? span(r, args[0], 17) : nullptr, args[0]);
        break;
    case 0x40af90:
        value = 3;
        break;
    case 0x49a720:
        cacheReset(r, receiver);
        value = 0;
        break;
    case 0x49ae60:
        value = cacheRecord(receiver, args[0], args[1]);
        break;
    case 0x49a860:
        value = args[1] && signedWord(args[0]) >= 0 && args[0] < 15 && args[2] >= 1 && args[2] <= 3
                    ? cacheWrite(r, receiver, args[0], span(r, args[1], 44), args[2])
                    : 0;
        break;
    case 0x49a800:
        value = args[1] && signedWord(args[0]) >= 0 && args[0] < 15
                    ? cacheBest(r, receiver, args[0], span(r, args[1], 17))
                    : 0;
        break;
    default:
        if (f == 0x4232c0)
            c->globals->superKind = 1;
        else if (f == 0x4232e0)
            c->globals->superKind = 2;
        update(r, args[0], f != 0x422ef0);
        break;
    }
    if (result)
        *result = value;
    return 1;
}
