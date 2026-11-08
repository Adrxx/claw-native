#include "RopeRuntime.h"
#include "ActorWrapperRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include "PlayerProjectileRuntime.h"
#include "PlayerEngine.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
int32_t signedWord(uint32_t v) {
    int32_t result;
    std::memcpy(&result, &v, 4);
    return result;
}
double multiply(double a, double b) {
    volatile double result = a * b;
    return result;
}
double subtract(double a, double b) {
    volatile double result = a - b;
    return result;
}
uint32_t ftolLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    int e = int((bits >> 52) & 0x7ff) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t n = (bits & 0xfffffffffffffULL) | 0x10000000000000ULL;
    n = e >= 52 ? n << (e - 52) : n >> (52 - e);
    return bits >> 63 ? 0u - uint32_t(n) : uint32_t(n);
}
const uint32_t points[122] = {64,  0,   40,  177, 40,  178, 41,  179, 41,  181, 42,  184, 43,  186, 45,  188, 46,  191,
                              48,  194, 50,  197, 53,  200, 57,  204, 63,  209, 70,  212, 76,  216, 84,  219, 91,  223,
                              100, 225, 119, 228, 119, 230, 128, 232, 137, 234, 148, 235, 157, 236, 168, 237, 178, 237,
                              188, 237, 198, 237, 208, 237, 218, 235, 229, 234, 237, 233, 246, 231, 255, 229, 265, 226,
                              275, 223, 282, 219, 290, 215, 297, 211, 305, 206, 311, 200, 314, 196, 316, 193, 320, 190,
                              322, 184, 324, 175, 324, 175, 324, 176, 324, 176, 323, 176, 323, 176, 323, 176, 322, 176,
                              322, 176, 322, 176, 321, 176, 321, 176, 320, 176, 320, 176, 319, 176};
struct Run {
    ClawRopeContext &c;
    ClawRopeDependency dependency;
    void *user;
    [[noreturn]] void fail(uint32_t code = 1) {
        if (!c.fault)
            c.fault = code;
        throw Failure{};
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t read(uint32_t t) {
        return *span(t);
    }
    void write(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    double number(uint32_t t) {
        double v;
        std::memcpy(&v, span(t, 2), 8);
        return v;
    }
    void number(uint32_t t, double v) {
        std::memcpy(span(t, 2), &v, 8);
    }
    uint32_t call(uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
        if (c.fault)
            throw Failure{};
        if (a.size() > 6)
            fail(2);
        if (!name && a.size()) {
            switch (*a.begin()) {
            case 0x524d2c:
                name = "CLAW_SWING";
                break;
            case 0x5246a8:
                name = "CLAW_JUMP";
                break;
            default:
                break;
            }
        }
        ClawRopeCall e{};
        e.function = f;
        e.receiver = receiver;
        e.argumentCount = uint32_t(a.size());
        e.name = name;
        std::copy(a.begin(), a.end(), e.arguments);
        uint32_t out;
        if (dependency)
            out = dependency(&c, &e, user);
        else if (c.scene.call && a.size() <= 4) {
            ClawSceneActorCall q{};
            q.function = f;
            q.receiver = receiver;
            q.argumentCount = e.argumentCount;
            std::copy(a.begin(), a.end(), q.arguments);
            out = c.scene.call(c.scene.context, q);
        } else
            fail();
        if (c.fault)
            throw Failure{};
        return out;
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {}, const char * = nullptr);
    uint32_t input() {
        if (!c.powerups)
            fail(3);
        return c.powerups->inputToken;
    }
    uint32_t delta() {
        if (!c.powerups || !c.powerups->animation)
            fail(3);
        return c.powerups->animation->animationDelta;
    }
    uint32_t powerup() {
        if (!c.powerups || !c.powerups->powerups || !c.powerups->powerups->globals)
            fail(3);
        return c.powerups->powerups->globals->powerup;
    }
    ClawPlayerPhysics &physics() {
        if (!c.powerups || !c.powerups->physics)
            fail(3);
        return *c.powerups->physics;
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(u);
        return r.span(t, n);
    }
    static uint32_t sceneCall(void *u, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(u);
        switch (e.argumentCount) {
        case 0:
            return r.invoke(e.function, e.receiver);
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
    static uint32_t allocate(void *u, uint32_t n) {
        auto &r = *static_cast<Run *>(u);
        return r.call(0x4f63ec, 0, {n});
    }
    static void release(void *u, uint32_t t) {
        auto &r = *static_cast<Run *>(u);
        r.call(0x4f6428, 0, {t});
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, sceneCall, nullptr};
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
bool owned(uint32_t f) {
    switch (f) {
    case 0x403100:
    case 0x4031c0:
    case 0x4035a0:
    case 0x403850:
    case 0x4038d0:
    case 0x465450:
    case 0x403ab0:
    case 0x403ac0:
    case 0x4181c0:
    case 0x41ce80:
    case 0x41ee60:
    case 0x415df0:
    case 0x4dc870:
    case 0x418080:
    case 0x418120:
    case 0x484d90:
    case 0x456030:
    case 0x4041a0:
    case 0x4041b0:
    case 0x4c9e30:
    case 0x4c96b0:
    case 0x4bb030:
        return true;
    default:
        return false;
    }
}
uint32_t forward(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t count, const char *name) {
    switch (count) {
    case 0:
        return r.invoke(f, t, {}, name);
    case 1:
        return r.invoke(f, t, {a[0]}, name);
    case 2:
        return r.invoke(f, t, {a[0], a[1]}, name);
    case 3:
        return r.invoke(f, t, {a[0], a[1], a[2]}, name);
    case 4:
        return r.invoke(f, t, {a[0], a[1], a[2], a[3]}, name);
    case 5:
        return r.invoke(f, t, {a[0], a[1], a[2], a[3], a[4]}, name);
    case 6:
        return r.invoke(f, t, {a[0], a[1], a[2], a[3], a[4], a[5]}, name);
    default:
        r.fail(2);
    }
}
struct ScopedHost {
    ClawSceneActorHost &target;
    ClawSceneActorHost old;
    ScopedHost(ClawSceneActorHost &t, ClawSceneActorHost value) : target(t), old(t) {
        t = value;
    }
    ~ScopedHost() {
        target = old;
    }
};
uint32_t playerPowerupService(ClawPlayerPowerupRuntimeContext *, const ClawPlayerPowerupCall *e, void *u) {
    return forward(*static_cast<Run *>(u), e->function, e->receiver, e->arguments, e->argumentCount, e->name);
}
uint32_t selectorService(ClawPowerupObjectContext *, const ClawPowerupObjectCall *e, void *u) {
    return forward(*static_cast<Run *>(u), e->function, e->receiver, e->arguments, e->argumentCount, e->name);
}
void liftAliases(Run &r, ClawLiftThrowGlobals &g, bool intoLift) {
    if (intoLift) {
        g.playerToken = r.c.globals->playerToken;
        g.inputToken = r.input();
        g.stageDelta = r.c.globals->stageDelta;
        g.animationDelta = r.delta();
        g.powerup = r.powerup();
        g.pixelScratch = r.c.globals->pixelScratch;
        g.tick = r.c.globals->tick;
    } else {
        r.c.globals->playerToken = g.playerToken;
        r.c.powerups->inputToken = g.inputToken;
        r.c.globals->stageDelta = g.stageDelta;
        r.c.powerups->animation->animationDelta = g.animationDelta;
        r.c.powerups->powerups->globals->powerup = g.powerup;
        r.c.globals->pixelScratch = g.pixelScratch;
        r.c.globals->tick = g.tick;
    }
}
uint64_t liftService(ClawLiftThrowContext *l, const ClawLiftThrowCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    liftAliases(r, *l->globals, false);
    auto out = forward(r, e->function, e->receiver, e->arguments, e->argumentCount, e->name);
    liftAliases(r, *l->globals, true);
    return out;
}
uint64_t dispatcherService(ClawPlayerProjectileContext *, const ClawPlayerProjectileCall *e, void *u) {
    return forward(*static_cast<Run *>(u), e->function, e->receiver, e->arguments, e->argumentCount, e->name);
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a, const char *name) {
    uint32_t args[6]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, t, args);
    if (f == 0x41fc30) {
        if (!c.powerups || !c.powerups->powerups)
            fail(3);
        auto *p = c.powerups->powerups;
        ScopedHost borrowed(p->scene, host());
        p->fault = 0;
        uint32_t out = 0;
        if (!claw_player_powerup_entry(f, t, args, uint32_t(a.size()), p, playerPowerupService, this, &out) || p->fault)
            fail(p->fault ? p->fault : 3);
        return out;
    }
    if (f == 0x417050 || f == 0x4170b0) {
        if (!c.powerups)
            fail(3);
        ScopedHost borrowed(c.powerups->scene, host());
        c.powerups->fault = 0;
        uint32_t out = 0;
        uint32_t n = f == 0x4170b0 ? 1 : uint32_t(a.size());
        if (!claw_powerup_object_entry(f, t, {{args[0], args[1], args[2], args[3], args[4], args[5]}, n}, c.powerups,
                                       selectorService, this, &out) ||
            c.powerups->fault)
            fail(c.powerups->fault ? c.powerups->fault : 3);
        return out;
    }
    if ((f == 0x421010 || f == 0x420fc0 || f == 0x41c4e0) && c.lift) {
        auto *l = c.lift;
        if (!l->globals)
            fail(3);
        ScopedHost borrowed(l->scene, host());
        liftAliases(*this, *l->globals, true);
        l->playerPhysics = &physics();
        l->fault = 0;
        uint32_t out = 0;
        if (!claw_lift_throw_entry(f, t, args, uint32_t(a.size()), l, liftService, this, &out) || l->fault)
            fail(l->fault ? l->fault : 3);
        liftAliases(*this, *l->globals, false);
        return out;
    }
    if (c.composeAnimation && (f == 0x4c79e0 || f == 0x4c8220 || f == 0x4c82a0 || f == 0x420a10)) {
        if (!c.powerups || !c.powerups->animation)
            fail(3);
        uint32_t fault = 0, out = 0;
        if (!claw_actor_animation_entry(f, t, args[0], args[1], c.powerups->animation, host(), &fault, &out) || fault)
            fail(fault ? fault : 3);
        return out;
    }
    return call(f, t, a, name);
}
void face(Run &r, uint32_t actor, uint32_t priv, bool right) {
    auto *a = r.span(actor, 128), *p = r.span(priv, 78);
    ClawPlayerBody b{};
    b.renderFlags = a[0x40 / 4];
    std::memcpy(&b.moveRect, a + 0x118 / 4, 16);
    std::memcpy(&b.hitRect, a + 0x128 / 4, 16);
    std::memcpy(&b.attackRect, a + 0x138 / 4, 16);
    ClawPlayerDirection d{p[0], p[69]};
    if (right)
        claw_player_face_right(&b, &d);
    else
        claw_player_face_left(&b, &d);
    a[0x40 / 4] = b.renderFlags;
    std::memcpy(a + 0x118 / 4, &b.moveRect, 16);
    std::memcpy(a + 0x128 / 4, &b.hitRect, 16);
    std::memcpy(a + 0x138 / 4, &b.attackRect, 16);
    p[0] = d.facing;
    p[69] = d.idleTimer;
}
uint32_t select(Run &r, uint32_t table, uint32_t state) {
    r.write(table + 32, 0);
    auto low = r.read(table + 8);
    if (signedWord(state) >= signedWord(low) && signedWord(state) <= signedWord(r.read(table + 12)))
        return r.read(table + 16) + (state - low) * r.read(table + 24);
    auto found = r.invoke(0x4db6e0, table, {state, 0});
    if (found)
        return r.read(table + 16) + (state - r.read(table + 8)) * r.read(table + 24);
    auto message = r.read(0x544b4c);
    r.write(0x544b14, r.invoke(0x4db5f0, 0));
    r.invoke(0x4db4d0, r.read(table + 4), {table, message, 12});
    return r.read(table + 20);
}
uint32_t constructor(Run &r, uint32_t t, uint32_t actor) {
    r.write(t, 0x50b064);
    r.write(t + 8, actor);
    r.write(t + 12, actor);
    r.write(t + 16, r.read(actor + 0x6c));
    r.write(t + 4, 0);
    r.invoke(0x4c7fa0, actor, {0x522d54}, "LogicHit");
    r.invoke(0x4c8060, r.read(t + 12), {0x522d48}, "LogicAttack");
    r.write(t + 20, 0);
    r.write(t + 24, 0);
    r.write(t + 28, 1001);
    r.write(t + 32, 2);
    r.write(t + 40, actor);
    r.write(t + 44, actor);
    r.write(t + 48, r.read(actor + 0x6c));
    ClawPlayerPhysics p;
    std::memcpy(&p, r.span(t + 0x48, 60), sizeof p);
    claw_physics_construct(&p);
    double minimum, maximum;
    std::memcpy(&minimum, r.c.globals->physicsDefaults, 8);
    std::memcpy(&maximum, r.c.globals->physicsDefaults + 2, 8);
    for (uint32_t axis = 0; axis < 3; ++axis) {
        p.minimum[axis] = minimum;
        p.maximum[axis] = p.maximumDelta[axis] = p.maximumVelocity[axis] = maximum;
    }
    std::memcpy(r.span(t + 0x48, 60), &p, sizeof p);
    r.write(t, 0x50b03c);
    r.invoke(0x4c7970, r.read(t + 44), {0x52313c}, "LEVEL_ROPE");
    auto a = r.read(t + 12);
    if (!r.read(a + 100)) {
        r.write(a + 100, 3990);
        r.write(a + 8, r.read(a + 8) | 0x20000);
    }
    r.write(t + 0x138, 0);
    a = r.read(t + 12);
    if (!r.read(a + 0x148))
        r.write(a + 0x148, 1500);
    r.write(r.read(t + 44) + 0xd0, 0x100);
    r.write(r.read(t + 12) + 0xfc, 0x26af);
    for (uint32_t axis = 0; axis < 3; ++axis) {
        r.write(t + 0x108 + axis * 8, r.c.globals->physicsDefaults[2]);
        r.write(t + 0x10c + axis * 8, r.c.globals->physicsDefaults[3]);
    }
    int32_t period = signedWord(r.read(r.read(t + 12) + 0x148));
    if (!period)
        r.fail(2);
    int32_t rate = 60000 / period;
    auto phase = r.read(r.read(t + 16) + 0xbc);
    for (uint32_t offset : {0x90u, 0x98u, 0x78u, 0x80u, 0x58u, 0x60u, 0x68u, 0x48u, 0x50u, 0x94u, 0x9cu, 0x7cu, 0x84u,
                            0x5cu, 0x64u, 0x6cu, 0x4cu, 0x54u})
        r.write(t + offset, 0);
    r.number(t + 0x88, double(signedWord(phase * uint32_t(rate)) / 1000));
    r.number(t + 0x70, double(rate));
    r.invoke(0x465450, t);
    return t;
}
uint32_t geometry(Run &r, uint32_t t) {
    int32_t frame = signedWord(ftolLow(r.number(t + 0x88))) % 120 + 1;
    r.write(t + 0x138, uint32_t(frame));
    bool left = frame > 60;
    uint32_t index = uint32_t(left ? frame - 60 : frame);
    r.write(t + 0x13c, index);
    if (signedWord(index) < 0 || index > 60)
        r.fail(2);
    uint32_t x = points[index * 2], y = points[index * 2 + 1], a = r.read(t + 44);
    if (left) {
        r.write(a + 0x138, 167 - x);
        r.write(a + 0x13c, y - 158);
        r.write(a + 0x140, 193 - x);
        r.write(a + 0x144, y - 125);
        r.write(t + 0x140, 180 - x);
    } else {
        r.write(a + 0x138, x - 193);
        r.write(a + 0x13c, y - 158);
        r.write(a + 0x140, x - 167);
        r.write(a + 0x144, y - 125);
        r.write(t + 0x140, x - 180);
    }
    r.write(t + 0x144, y - 150);
    uint32_t player = r.c.globals->playerToken, primary = r.read(player + 0x6c), priv = r.read(primary + 20);
    if (r.read(priv + 0x134) == r.read(t + 12) && r.read(primary + 28) == 5007)
        r.invoke(left ? 0x418080 : 0x418120, 0, {player, primary, priv});
    a = r.read(t + 44);
    uint32_t image = uint32_t(frame), out = 0;
    ClawActorWrapperContext wrapper{r.c.scene, 0};
    if (!claw_actor_wrapper_entry(0x4209d0, a, &image, 1, &wrapper, nullptr, nullptr, &out) || wrapper.fault)
        r.fail(wrapper.fault ? wrapper.fault : 3);
    return 0;
}
void playerUpdate(Run &r, uint32_t actor, uint32_t primary, uint32_t priv) {
    r.invoke(0x4c82a0, actor + 0x188, {r.delta()});
    uint32_t rope = r.read(priv + 0x134), object = r.read(r.read(rope + 0x6c) + 24);
    uint32_t x = r.invoke(0x403ab0, object);
    r.write(actor + 76, x + (r.read(priv) ? 8 : 0u - 8));
    object = r.read(r.read(r.read(priv + 0x134) + 0x6c) + 24);
    r.write(actor + 80, r.invoke(0x403ac0, object) + 20);
    if (!(r.read(r.input() + 4) & 1))
        return;
    r.write(priv + 0x11c, 500);
    auto input = r.input();
    r.write(input + 12, r.read(input + 12) & 0xfdffffff);
    input = r.input();
    r.write(input + 12, r.read(input + 12) & 0xfeffffff);
    if (auto target = r.read(priv + 0x12c)) {
        uint32_t e = r.read(r.read(target + 0x6c) + 24);
        r.invoke(0x421010, e, {0x4207a0, 1});
        r.invoke(0x420fc0, e + 0x2f4, {0});
        r.write(priv + 0x12c, 0);
    }
    r.write(priv + 60, 0);
    r.write(priv + 32, 1);
    if (r.read(priv + 4)) {
        r.write(priv + 4, 0);
        r.invoke(0x420a10, actor, {r.read(priv + 0x124), 0});
        r.write(actor + 8, r.read(actor + 8) | 0x80);
    }
    r.write(primary + 28, 4);
    r.invoke(0x4c79e0, actor, {0x5246a8, 0}, "CLAW_JUMP");
    r.write(actor + 0xcc, 3);
    r.write(actor + 0x148, 0);
    r.write(actor + 0x14c, 0);
    r.write(actor + 8, r.read(actor + 8) & ~0x10u);
    r.invoke(0x417050, 0, {actor, priv});
    r.invoke(0x4170b0, 0, {actor, priv});
    auto &p = r.physics();
    p.velocity[1] = r.powerup() == 0x26bc || !r.read(priv + 0x114) ? -500 : -425;
    r.write(priv + 0x118, 250);
    r.write(priv + 0x5c, 0);
    r.write(priv + 0x60, r.read(actor + 80));
    r.write(priv + 0x10c, 0);
    r.write(priv + 0x64, r.read(actor + 80) - 45);
    p.acceleration[1] = 2250;
    p.position[0] = double(signedWord(r.read(actor + 76)));
    p.position[1] = double(signedWord(r.read(actor + 80)));
    claw_physics_retarget(&p, p.position[0], double(signedWord(r.read(priv + 0x64))), 0);
}
struct Epilogue {
    Run &r;
    ClawPlayerLocomotion state{};
    ClawPlayerInputContext input{};
    uint32_t actor, primary, priv;
};
void exchange(Epilogue &e, bool output) {
    auto &r = e.r;
    auto &s = e.state;
    auto &i = e.input;
    if (output) {
        std::copy_n(s.actor, 128, r.span(e.actor, 128));
        std::copy_n(s.privateWords, 78, r.span(e.priv, 78));
        r.write(e.primary + 28, s.logicState);
        r.write(e.primary + 0x130, i.invulnerabilityTimer);
        const uint32_t bounds[] = {i.minimumX, i.maximumX, i.minimumY, i.maximumY};
        for (uint32_t n = 0; n < 4; ++n)
            r.write(e.primary + 0x2c + n * 4, bounds[n]);
        r.write(r.input() + 4, i.pressed);
        r.write(r.input() + 8, s.inputHeld);
        r.write(r.input() + 12, s.inputLatched);
        r.c.globals->stageDelta = s.stageDelta;
        r.c.globals->pixelScratch = s.pixelScratch;
        r.c.globals->ignoreHazards = i.ignoreHazards;
        r.c.globals->cheat = i.cheat;
        r.c.powerups->animation->animationDelta = s.animationDelta;
        r.c.powerups->powerups->globals->powerup = s.powerup;
        r.physics() = s.physics;
    } else {
        std::copy_n(r.span(e.actor, 128), 128, s.actor);
        std::copy_n(r.span(e.priv, 78), 78, s.privateWords);
        s.logicState = r.read(e.primary + 28);
        i.invulnerabilityTimer = r.read(e.primary + 0x130);
        i.minimumX = r.read(e.primary + 0x2c);
        i.maximumX = r.read(e.primary + 0x30);
        i.minimumY = r.read(e.primary + 0x34);
        i.maximumY = r.read(e.primary + 0x38);
        i.pressed = r.read(r.input() + 4);
        s.inputHeld = r.read(r.input() + 8);
        s.inputLatched = r.read(r.input() + 12);
        s.stageDelta = r.c.globals->stageDelta;
        s.pixelScratch = r.c.globals->pixelScratch;
        i.ignoreHazards = r.c.globals->ignoreHazards;
        i.cheat = r.c.globals->cheat;
        s.animationDelta = r.delta();
        s.powerup = r.powerup();
        s.physics = r.physics();
    }
}
uint32_t epilogueService(ClawPlayerLocomotion *, uint32_t f, uint32_t a, uint32_t, uint32_t, void *u) {
    auto &e = *static_cast<Epilogue *>(u);
    exchange(e, true);
    auto &r = e.r;
    uint32_t value = 0;
    switch (f) {
    case 0x420910:
        value = r.invoke(f, r.read(r.read(e.actor + 12) + 40), {a});
        break;
    case 0x41fc30:
        value = r.invoke(f, 0, {e.actor, e.primary, e.priv, a});
        break;
    case 0x4cd740:
        value = r.invoke(f, r.read(r.read(e.actor + 12) + 36), {e.actor, a});
        break;
    case 0x417c50:
        value = r.invoke(f, 0, {e.actor, e.primary, e.priv});
        break;
    default:
        r.fail(3);
    }
    exchange(e, false);
    return value;
}
uint32_t body(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    switch (f) {
    case 0x403100: {
        uint32_t actor = a[0], primary = r.read(actor + 0x6c), state = r.read(primary + 28);
        if (!state) {
            r.write(primary + 28, 1000);
            uint32_t e = r.invoke(0x4f63ec, 0, {0x148});
            if (e)
                e = r.invoke(0x4031c0, e, {actor});
            uint32_t v = r.read(e);
            r.invoke(r.read(v + 16), e);
            r.write(primary + 24, e);
        } else if (state == 29 || state == 30) {
            uint32_t e = r.read(primary + 24);
            r.invoke(r.read(r.read(e) + (state == 29 ? 32 : 28)), e);
        } else if (state != 1000)
            r.invoke(0x4dc870, 0, {r.read(primary + 24)});
        return 1;
    }
    case 0x4031c0:
        return constructor(r, t, a[0]);
    case 0x4035a0: {
        uint32_t cell = select(r, 0x534820, a[0]);
        if (r.read(cell)) {
            cell = select(r, 0x534820, a[0]);
            r.invoke(r.read(cell), t);
        } else
            r.invoke(0x4a36f0, 0, {t});
        return 0;
    }
    case 0x403850: {
        uint32_t out = 0, unused = 0;
        ClawStackedActorLifecycleContext x{r.host(), 0};
        if (!claw_stacked_actor_lifecycle_entry(0x4041b0, t, &unused, 1, &x, &out) || x.fault)
            r.fail(x.fault ? x.fault : 3);
        ClawPlayerPhysics p;
        std::memcpy(&p, r.span(t + 0x48, 60), sizeof p);
        double dt = subtract(multiply(double(uint64_t(r.c.globals->tick)), .001), p.elapsed);
        claw_physics_update(&p, dt);
        std::memcpy(r.span(t + 0x48, 60), &p, sizeof p);
        return 0;
    }
    case 0x4038d0:
        return geometry(r, t);
    case 0x465450:
        r.write(t + 36, r.read(r.read(t + 16) + 28));
        r.write(r.read(t + 16) + 28, r.invoke(0x4dba00, 0x537668, {0x523148}, "LS_IDLE"));
        return 0;
    case 0x403ab0:
        return r.read(r.read(t + 12) + 76) + r.read(t + 0x140);
    case 0x403ac0:
        return r.read(r.read(t + 12) + 80) + r.read(t + 0x144);
    case 0x4181c0:
        playerUpdate(r, a[0], a[1], a[2]);
        return 0;
    case 0x41ce80: {
        uint32_t actor = a[0], item = r.read(actor + 0x74);
        if (!item)
            return 0;
        if (!r.c.powerups || !r.c.powerups->items)
            r.fail(3);
        auto *items = r.c.powerups->items;
        items->playerToken = actor;
        items->playerPrimaryToken = r.read(actor + 0x6c);
        items->playerPrivateToken = r.read(items->playerPrimaryToken + 20);
        ScopedHost borrowed(r.c.powerups->scene, r.host());
        r.c.powerups->fault = 0;
        uint32_t out = 0;
        if (!claw_powerup_object_award(item, r.c.powerups, selectorService, &r, &out) || r.c.powerups->fault)
            r.fail(r.c.powerups->fault ? r.c.powerups->fault : 3);
        return out;
    }
    case 0x41ee60: {
        if (!r.c.powerups)
            r.fail(3);
        ScopedHost borrowed(r.c.powerups->scene, r.host());
        r.c.powerups->fault = 0;
        uint32_t out = 0;
        if (!claw_powerup_object_entry(f, t, {{a[0], a[1], a[2], a[3], 0, 0}, 4}, r.c.powerups, selectorService, &r,
                                       &out) ||
            r.c.powerups->fault)
            r.fail(r.c.powerups->fault ? r.c.powerups->fault : 3);
        return out;
    }
    case 0x415df0: {
        uint32_t actor = a[0], primary = r.read(actor + 0x6c), priv = r.read(primary + 20);
        if (r.read(primary + 28) != 5007)
            return 0;
        r.invoke(0x4181c0, 0, {actor, primary, priv});
        Epilogue e{r, {}, {}, actor, primary, priv};
        exchange(e, false);
        claw_player_input_epilogue(&e.state, &e.input, epilogueService, &e);
        exchange(e, true);
        return 1;
    }
    case 0x4dc870: {
        ClawPlayerProjectileGlobals g{};
        ClawPlayerProjectileContext x{r.host(), &g, nullptr, 0, 0};
        uint32_t out = 0;
        const uint32_t args[] = {a[0]};
        if (!claw_player_projectile_entry(f, args[0], nullptr, 0, &x, dispatcherService, &r, &out) || x.fault)
            r.fail(x.fault ? x.fault : 3);
        return out;
    }
    case 0x418080:
    case 0x418120:
        face(r, a[0], a[2], f == 0x418120);
        return 0;
    case 0x484d90:
    case 0x456030:
    case 0x4041a0:
    case 0x4041b0:
    case 0x4c9e30:
    case 0x4c96b0:
    case 0x4bb030: {
        ClawStackedActorLifecycleContext x{r.host(), 0};
        uint32_t out = 0;
        uint32_t n = f == 0x484d90 || f == 0x4041a0 || f == 0x4041b0 || f == 0x4c9e30 ? 1 : 0;
        if (!claw_stacked_actor_lifecycle_entry(f, t, a, n, &x, &out) || x.fault)
            r.fail(x.fault ? x.fault : 3);
        return out;
    }
    default:
        r.fail(3);
    }
}
} // namespace
extern "C" void claw_rope_defaults(ClawRopeGlobals *g) {
    if (g) {
        const uint32_t values[] = {0xffc00000, 0xc1dfffff, 0xff800000, 0x41dfffff};
        std::copy_n(values, 4, g->physicsDefaults);
    }
}
extern "C" uint32_t claw_rope_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawRopeContext *c,
                                    ClawRopeDependency d, void *u, uint32_t *out) {
    if (!owned(f) || !c || !c->globals)
        return 0;
    uint32_t count = 0;
    switch (f) {
    case 0x403100:
    case 0x4031c0:
    case 0x4035a0:
    case 0x403850:
    case 0x415df0:
    case 0x41ce80:
    case 0x4dc870:
    case 0x484d90:
    case 0x4041a0:
    case 0x4041b0:
    case 0x4c9e30:
        count = 1;
        break;
    case 0x4181c0:
    case 0x418080:
    case 0x418120:
        count = 3;
        break;
    case 0x41ee60:
        count = 4;
        break;
    default:
        break;
    }
    if (n != count || (n && !a)) {
        c->fault = 2;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        if (f == 0x415df0 && r.read(r.read(a[0] + 0x6c) + 28) != 5007)
            return 0;
        if (f == 0x41ee60 && a[3] && r.read(a[3] + 0xfc) != 0x26af)
            return 0;
        if (f == 0x41ce80) {
            uint32_t item = r.read(a[0] + 0x74);
            if (item && (r.read(item + 0xd0) != 0x100 || r.read(item + 0xfc) != 0x26af))
                return 0;
        }
        uint32_t value = body(r, f, t, a);
        if (out)
            *out = value;
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
