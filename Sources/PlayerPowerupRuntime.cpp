#include "PlayerPowerupRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>

namespace {
struct Run {
    ClawPlayerPowerupRuntimeContext *c;
    ClawPlayerPowerupDependency dependency;
    void *user;
};
bool bad(const Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t token, uint32_t count) {
    auto &host = r.c->scene;
    auto *p = host.lookup ? host.lookup(host.context, token, count) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t word(Run &r, uint32_t token) {
    auto *p = span(r, token, 1);
    return p ? *p : 0;
}
void store(Run &r, uint32_t token, uint32_t value) {
    auto *p = span(r, token, 1);
    if (p)
        *p = value;
}
uint32_t service(Run &r, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments,
                 const char *name = nullptr) {
    if (bad(r))
        return 0;
    ClawPlayerPowerupCall call{};
    call.function = function;
    call.receiver = receiver;
    call.argumentCount = uint32_t(arguments.size());
    call.name = name;
    std::copy(arguments.begin(), arguments.end(), call.arguments);
    if (r.dependency)
        return r.dependency(r.c, &call, r.user);
    if (r.c->scene.call && arguments.size() <= 4) {
        ClawSceneActorCall common{};
        common.function = function;
        common.receiver = receiver;
        common.argumentCount = call.argumentCount;
        std::copy_n(call.arguments, call.argumentCount, common.arguments);
        return r.c->scene.call(r.c->scene.context, common);
    }
    r.c->fault = 1;
    return 0;
}
uint32_t virtualCall(Run &r, uint32_t receiver, uint32_t offset, std::initializer_list<uint32_t> args) {
    const uint32_t table = word(r, receiver), function = word(r, table + offset);
    return bad(r) ? 0 : service(r, function, receiver, args);
}
uint32_t musicManager(Run &r) {
    return word(r, r.c->globals->managerToken + 0x50);
}
uint32_t imagesEffect(Run &r, uint32_t receiver, uint32_t effect) {
    int32_t index = int32_t(word(r, receiver + 0x64));
    uint32_t count = 0, iterations = 0;
    while (!bad(r) && index <= int32_t(word(r, receiver + 0x68))) {
        if (++iterations > 1000000) {
            r.c->fault = 2;
            break;
        }
        uint32_t image = 0;
        if (index >= int32_t(word(r, receiver + 0x64)) && index <= int32_t(word(r, receiver + 0x68)))
            image = word(r, word(r, receiver + 0x14) + uint32_t(index) * 4);
        if (image) {
            const uint32_t compressed = word(r, image + 0x30);
            if (compressed) {
                service(r, 0x4c6130, compressed, {effect, 0});
                ++count;
            }
        }
        index = int32_t(uint32_t(index) + 1);
    }
    return count;
}
uint32_t glitter(Run &r, uint32_t actor) {
    if (!actor)
        return 0;
    const uint32_t parent = word(r, actor + 0xc), container = word(r, parent + 8);
    const uint32_t created = service(r, 0x4c8da0, container, {1, 100, 100, 0, 0x5225a0, 0}, "GlitterMother");
    if (created)
        store(r, word(r, created + 0x6c) + 0x170, actor);
    return created;
}
uint32_t select(Run &r, uint32_t actor, uint32_t privateToken, uint32_t type, uint32_t duration) {
    auto &g = *r.c->globals;
    if (word(r, g.managerToken + 0x14) && !g.musicDisabled) {
        if (duration && type) {
            if (g.powerup != type) {
                const uint32_t level = service(r, 0x4b54a0, musicManager(r), {0x524d80}, "LEVEL");
                if (level && service(r, 0x4b5bd0, level, {}))
                    virtualCall(r, level, 0x28, {});
                const uint32_t power = service(r, 0x4b54a0, musicManager(r), {0x524d78}, "POWERUP");
                if (power) {
                    store(r, musicManager(r) + 0x1c, power);
                    service(r, 0x4b5570, musicManager(r), {1});
                }
            }
        } else {
            const uint32_t manager = musicManager(r), previous = word(r, manager + 0x1c);
            const uint32_t power = service(r, 0x4b54a0, manager, {0x524d78}, "POWERUP");
            if (previous == power && power && service(r, 0x4b5bd0, power, {}))
                virtualCall(r, power, 0x30, {});
            const uint32_t level = service(r, 0x4b54a0, musicManager(r), {0x524d80}, "LEVEL");
            if (level && previous != level) {
                store(r, musicManager(r) + 0x1c, level);
                if (!service(r, 0x4b5bd0, level, {}))
                    virtualCall(r, level, 0x2c, {0});
            }
        }
    }
    if (bad(r))
        return 0;
    if (g.powerup == type) {
        const uint32_t sum = g.remaining + duration;
        g.remaining = sum > 999000 ? 999000 : sum;
        return 1;
    }
    //Positive selection calls4bc110, whose complete original body is RET.
    if (g.powerup == 0x26bd) {
        store(r, actor + 0xd4, word(r, actor + 0xd4) | 0x01000044);
        const uint32_t images = word(r, actor + 0x170);
        if (images)
            imagesEffect(r, images, 1);
    } else if (g.powerup == 0x26b7) {
        const uint32_t images = word(r, actor + 0x170);
        if (images)
            imagesEffect(r, images, 1);
    } else if (g.powerup == 0x26bc) {
        const uint32_t effect = word(r, privateToken + 0x130);
        if (effect) {
            store(r, effect + 8, word(r, effect + 8) | 0x10000);
            store(r, privateToken + 0x130, 0);
        }
    }
    if (bad(r))
        return 0;
    g.powerup = type;
    g.remaining = duration;
    switch (type) {
    case 0x26b7:
    case 0x26bd:
        service(r, 0x48c8a0, 0, {0x524d68, 0}, "CLAW_1110064");
        break;
    case 0x26b8:
        service(r, 0x48c8a0, 0, {0x524d58, 0}, "CLAW_1110001");
        break;
    case 0x26b9:
        service(r, 0x48c8a0, 0, {0x524d48, 0}, "CLAW_1110022");
        break;
    case 0x26ba:
        service(r, 0x48c8a0, 0, {0x524d38, 0}, "CLAW_1110012");
        break;
    case 0x26bc:
        store(r, privateToken + 0x130, glitter(r, actor));
        break;
    default:
        break;
    }
    return 1;
}
void cycle(Run &r, uint32_t actor, uint32_t delta) {
    if (!actor)
        return;
    auto &g = *r.c->globals;
    g.cycleRemaining = delta < g.cycleRemaining ? g.cycleRemaining - delta : 0;
    if (!g.cycleRemaining) {
        g.cycleRemaining = 100;
        switch (g.cycleIndex) {
        case 0x34:
            g.cycleIndex = 0x35;
            break;
        case 0x35:
            g.cycleIndex = 0x36;
            break;
        case 0x36:
            g.cycleIndex = 0x37;
            break;
        case 0x65:
            g.cycleIndex = 0x34;
            break;
        default:
            g.cycleIndex = 0x65;
            break;
        }
    }
    const uint32_t image = word(r, actor + 0x174);
    if (image) {
        const uint32_t compressed = word(r, image + 0x30);
        if (compressed) {
            service(r, 0x4c6130, compressed, {4, 0});
            const uint32_t after = word(r, image + 0x30);
            if (after)
                store(r, after + 0x18, g.cycleIndex);
        }
    }
}
struct TimerBridge {
    Run *run;
    uint32_t actor, privateToken;
    ClawPlayerPowerupContext *timer;
};
void loadTimer(TimerBridge &bridge, ClawPlayerLocomotion &state, bool readOverlay = false) {
    auto &r = *bridge.run;
    auto *actor = span(r, bridge.actor, 128), *priv = span(r, bridge.privateToken, 78);
    if (bad(r))
        return;
    std::copy_n(actor, 128, state.actor);
    std::copy_n(priv, 78, state.privateWords);
    auto &g = *r.c->globals;
    state.powerup = g.powerup;
    bridge.timer->remaining = g.remaining;
    bridge.timer->expired = g.expired;
    if (readOverlay)
        bridge.timer->overlaySequenceToken = state.actor[0x174 / 4] ? word(r, state.actor[0x174 / 4] + 0x30) : 0;
}
void storeTimer(TimerBridge &bridge, const ClawPlayerLocomotion &state) {
    auto &r = *bridge.run;
    auto *actor = span(r, bridge.actor, 128), *priv = span(r, bridge.privateToken, 78);
    if (bad(r))
        return;
    std::copy_n(state.actor, 128, actor);
    std::copy_n(state.privateWords, 78, priv);
    auto &g = *r.c->globals;
    g.powerup = state.powerup;
    g.remaining = bridge.timer->remaining;
    g.expired = bridge.timer->expired;
}
uint32_t timerDependency(ClawPlayerLocomotion *state, uint32_t function, uint32_t a, uint32_t b, uint32_t, void *user) {
    auto &bridge = *static_cast<TimerBridge *>(user);
    auto &r = *bridge.run;
    storeTimer(bridge, *state);
    if (bad(r))
        return 0;
    uint32_t result = 0;
    switch (function) {
    case 0x41f990:
        result = select(r, bridge.actor, bridge.privateToken, a, b);
        break;
    case 0x4bc110:
        break;
    case 0x420070:
        cycle(r, bridge.actor, a);
        break;
    case 0x4c6130:
        result = service(r, function, a, {b, 0});
        break;
    default:
        r.c->fault = 2;
        break;
    }
    loadTimer(bridge, *state);
    return result;
}
uint32_t timer(Run &r, const uint32_t *args) {
    ClawPlayerLocomotion state{};
    ClawPlayerPowerupContext powerup{};
    TimerBridge bridge{&r, args[0], args[2], &powerup};
    const auto &g = *r.c->globals;
    loadTimer(bridge, state, g.powerup == 0x26b7 && args[3] < g.remaining);
    if (bad(r))
        return 0;
    claw_player_update_powerup_timer(&state, &powerup, args[3], timerDependency, &bridge);
    storeTimer(bridge, state);
    return 0;
}
} // namespace
extern "C" uint32_t claw_player_powerup_entry(uint32_t function, uint32_t receiver, const uint32_t *args,
                                              uint32_t count, ClawPlayerPowerupRuntimeContext *context,
                                              ClawPlayerPowerupDependency dependency, void *user, uint32_t *result) {
    if (result)
        *result = 0;
    if (!context || !context->globals)
        return 0;
    Run r{context, dependency, user};
    uint32_t required;
    switch (function) {
    case 0x41f990:
        required = 5;
        break;
    case 0x41fc00:
    case 0x420070:
        required = 2;
        break;
    case 0x41fc30:
        required = 4;
        break;
    case 0x4ce7b0:
    case 0x448400:
        required = 1;
        break;
    case 0x4bc110:
        required = 0;
        break;
    default:
        return 0;
    }
    if (count != required || (count && !args)) {
        context->fault = 2;
        return 0;
    }
    if (bad(r))
        return 0;
    uint32_t value = 0;
    switch (function) {
    case 0x41f990:
        value = select(r, args[0], args[2], args[3], args[4]);
        break;
    case 0x41fc00: {
        const uint32_t actor = context->globals->playerToken;
        if (actor) {
            const uint32_t primary = word(r, actor + 0x6c);
            value = select(r, actor, word(r, primary + 0x14), args[0], args[1]);
        }
        break;
    }
    case 0x4ce7b0:
        value = imagesEffect(r, receiver, args[0]);
        break;
    case 0x448400:
        value = glitter(r, args[0]);
        break;
    case 0x420070:
        cycle(r, args[0], args[1]);
        break;
    case 0x41fc30:
        value = timer(r, args);
        break;
    default:
        break;
    }
    if (result)
        *result = value;
    return !bad(r);
}
