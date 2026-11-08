#include "PlayerCarryDispatchRuntime.h"
#include <algorithm>
#include <cstring>
namespace {
struct Failure {};
struct Run {
    ClawPlayerLocomotion &s;
    ClawPlayerInputContext &i;
    ClawPlayerCarryDispatchContext &c;
    ClawLiftThrowDependency liftDependency;
    ClawPlayerCarryDispatchDependency dependency;
    void *u;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto &h = c.lift->scene;
        auto p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t t, uint32_t off = 0) {
        return *span(t + off);
    }
    void put(uint32_t t, uint32_t off, uint32_t v) {
        *span(t + off) = v;
    }
    void push() {
        std::copy_n(s.actor, 128, span(c.actorToken, 128));
        std::copy_n(s.privateWords, 78, span(c.privateToken, 78));
        put(c.primaryToken, 28, s.logicState);
        put(c.primaryToken, 0x130, i.invulnerabilityTimer);
        auto b = span(c.primaryToken + 0x2c, 4);
        b[0] = i.minimumX;
        b[1] = i.maximumX;
        b[2] = i.minimumY;
        b[3] = i.maximumY;
        auto &g = *c.lift->globals;
        put(g.inputToken, 4, i.pressed);
        put(g.inputToken, 8, s.inputHeld);
        put(g.inputToken, 12, s.inputLatched);
        g.stageDelta = s.stageDelta;
        g.animationDelta = s.animationDelta;
        g.powerup = s.powerup;
        g.pixelScratch = s.pixelScratch;
        *c.lift->playerPhysics = s.physics;
    }
    void pull() {
        std::copy_n(span(c.actorToken, 128), 128, s.actor);
        std::copy_n(span(c.privateToken, 78), 78, s.privateWords);
        s.logicState = get(c.primaryToken, 28);
        i.invulnerabilityTimer = get(c.primaryToken, 0x130);
        auto b = span(c.primaryToken + 0x2c, 4);
        i.minimumX = b[0];
        i.maximumX = b[1];
        i.minimumY = b[2];
        i.maximumY = b[3];
        auto &g = *c.lift->globals;
        i.pressed = get(g.inputToken, 4);
        s.inputHeld = get(g.inputToken, 8);
        s.inputLatched = get(g.inputToken, 12);
        s.stageDelta = g.stageDelta;
        s.animationDelta = g.animationDelta;
        s.powerup = g.powerup;
        s.pixelScratch = g.pixelScratch;
        s.physics = *c.lift->playerPhysics;
        i.ignoreHazards = c.ignoreHazards;
        i.cheat = c.cheat;
    }
    static uint32_t epilogue(ClawPlayerLocomotion *, uint32_t fn, uint32_t a, uint32_t, uint32_t, void *v) {
        auto &r = *static_cast<Run *>(v);
        r.push();
        ClawPlayerCarryDispatchCall e{};
        e.function = fn;
        switch (fn) {
        case 0x420910:
            e.receiver = r.get(r.get(r.c.actorToken, 12), 0x28);
            e.argumentCount = 1;
            e.arguments[0] = a;
            break;
        case 0x41fc30:
            e.argumentCount = 4;
            e.arguments[0] = r.c.actorToken;
            e.arguments[1] = r.c.primaryToken;
            e.arguments[2] = r.c.privateToken;
            e.arguments[3] = a;
            break;
        case 0x4cd740:
            e.receiver = r.get(r.get(r.c.actorToken, 12), 0x24);
            e.argumentCount = 2;
            e.arguments[0] = r.c.actorToken;
            e.arguments[1] = a;
            break;
        case 0x417c50:
            e.argumentCount = 3;
            e.arguments[0] = r.c.actorToken;
            e.arguments[1] = r.c.primaryToken;
            e.arguments[2] = r.c.privateToken;
            break;
        default:
            r.c.fault = 1;
            throw Failure{};
        }
        uint32_t result = 0;
        if (r.dependency)
            result = r.dependency(&r.c, &e, r.u);
        else if (r.c.lift->scene.call) {
            ClawSceneActorCall q{};
            q.function = e.function;
            q.receiver = e.receiver;
            q.argumentCount = e.argumentCount;
            std::copy_n(e.arguments, e.argumentCount, q.arguments);
            result = r.c.lift->scene.call(r.c.lift->scene.context, q);
        } else {
            r.c.fault = 1;
            throw Failure{};
        }
        r.pull();
        if (r.c.fault)
            throw Failure{};
        return result;
    }
};
} // namespace
extern "C" uint32_t claw_player_dispatch_carry(ClawPlayerLocomotion *s, ClawPlayerInputContext *i,
                                               ClawPlayerCarryDispatchContext *c, ClawLiftThrowDependency ld,
                                               ClawPlayerCarryDispatchDependency d, void *u) {
    if (!s || !i || !c || !c->lift || !c->lift->globals || !c->lift->playerPhysics)
        return 0;
    if (s->logicState != 5000 && s->logicState != 5001)
        return 0;
    c->fault = 0;
    c->lift->fault = 0;
    Run r{*s, *i, *c, ld, d, u};
    const uint32_t initial = s->logicState;
    c->ignoreHazards = i->ignoreHazards;
    c->cheat = i->cheat;
    try {
        if (s->actor[0x6c / 4] != c->primaryToken || r.get(c->primaryToken, 0x14) != c->privateToken) {
            c->fault = 1;
            return 1;
        }
        r.push();
        uint32_t args[] = {c->actorToken, c->primaryToken, c->privateToken}, result = 0;
        if (!claw_lift_throw_entry(initial == 5000 ? 0x41a850 : 0x41b280, 0, args, 3, c->lift, ld, u, &result)) {
            c->fault = c->lift->fault ? c->lift->fault : 1;
            r.pull();
            return 1;
        }
        r.pull();
        claw_player_input_epilogue(s, i, Run::epilogue, &r);
        r.push();
    } catch (Failure &) {
    }
    return 1;
}
