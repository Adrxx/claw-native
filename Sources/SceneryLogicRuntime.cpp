#include "SceneryLogicRuntime.h"
#include <cstring>
namespace {
struct Run {
    ClawSceneryLogicContext *context;
    uint32_t word(uint32_t token) {
        if (context->fault)
            return 0;
        auto *p = context->scene.lookup
                      ? context->scene.lookup(context->scene.context, token & ~3u, ((token & 3u) + 7u) / 4u)
                      : nullptr;
        if (!p) {
            context->fault = 1;
            return 0;
        }
        uint32_t v;
        std::memcpy(&v, reinterpret_cast<uint8_t *>(p) + (token & 3u), 4);
        return v;
    }
    void put(uint32_t token, uint32_t value) {
        if (context->fault)
            return;
        auto *p = context->scene.lookup
                      ? context->scene.lookup(context->scene.context, token & ~3u, ((token & 3u) + 7u) / 4u)
                      : nullptr;
        if (!p) {
            context->fault = 1;
            return;
        }
        std::memcpy(reinterpret_cast<uint8_t *>(p) + (token & 3u), &value, 4);
    }
    void flags(uint32_t actor, uint32_t bits) {
        put(actor + 8, word(actor + 8) | bits);
    }
    void animation(uint32_t function, uint32_t receiver, uint32_t a, uint32_t b = 0) {
        if (context->fault)
            return;
        if (context->composeAnimation) {
            uint32_t result = 0;
            if (!claw_actor_animation_entry(function, receiver, a, b, &context->animation, context->scene,
                                            &context->fault, &result) &&
                !context->fault)
                context->fault = 2;
        } else if (context->scene.call)
            context->scene.call(context->scene.context,
                                {function, receiver, {a, b, 0, 0}, function == 0x4c79e0 ? 2u : 1u});
        else
            context->fault = 1;
    }
};
} // namespace
extern "C" uint32_t claw_scenery_logic_entry(uint32_t function, uint32_t actor, ClawSceneryLogicContext *context,
                                             uint32_t *result) {
    if (!context)
        return 0;
    if (function != 0x461730 && function != 0x461750 && function != 0x461770 && function != 0x4617d0 &&
        function != 0x461830 && function != 0x461870 && function != 0x4618e0 && function != 0x461970)
        return 0;
    Run r{context};
    if (function == 0x461730 || function == 0x461750)
        r.flags(actor, 1);
    else {
        const uint32_t logic = r.word(actor + 0x6c), state = r.word(logic + 0x1c);
        const bool animated = function == 0x461870 || function == 0x4618e0 || function == 0x461970;
        if (!state) {
            r.flags(actor, 1);
            r.put(logic + 0x1c, 5);
            if (animated && !r.word(actor + 0x190))
                r.animation(0x4c79e0, actor, 0x5240d8, 0);
            if (!r.word(actor + 0x64)) {
                const uint32_t z = function == 0x461770 || function == 0x4618e0   ? 5100u
                                   : function == 0x4617d0 || function == 0x461970 ? 990u
                                   : function == 0x461830                         ? 8010u
                                                                                  : 8000u;
                r.put(actor + 0x64, z);
                r.flags(actor, 0x20000);
            }
            if (function != 0x461830 && function != 0x461870 && !r.word(context->settingsToken + 0x124))
                r.flags(actor, 0x10000);
        } else if (animated)
            r.animation(0x4c82a0, actor + 0x188, context->animation.animationDelta);
    }
    if (result)
        *result = function == 0x461750 ? 2 : 1;
    return context->fault ? 0 : 1;
}
