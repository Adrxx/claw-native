#include "bridge.h"
#include "BootyProgressionRuntime.h"
#include "ApplicationLevelProgressionRuntime.h"
#include <cstdlib>
#include <cstring>
namespace {
uint32_t *lookup(void *u, uint32_t token, uint32_t words) {
    auto h = static_cast<ClawHost *>(u);
    return reinterpret_cast<uint32_t *>(h->bytes(h->user, token, words * 4));
}
uint32_t dependency(ClawHost *h, const ClawBootyProgressionCall *q, uint32_t &fault) {
    ClawCall call{};
    call.function = q->function;
    call.receiver = q->receiver;
    if (q->argumentCount > 16) { fault = 3; return 0; }
    call.argumentCount = q->argumentCount;
    std::memcpy(call.arguments, q->arguments, q->argumentCount * 4);
    auto value = h->call(h->user, &call);
    if (h->fault) fault = 1;
    return value;
}
}
extern "C" uint32_t movie_test_caller(uint32_t kind, uint32_t receiver, uint32_t scratch,
                                      ClawHost *host, uint32_t *result) {
    ClawSceneActorHost scene{};
    scene.context = host;
    scene.lookup = lookup;
    if (kind == 0) {
        ClawApplicationLevelProgressionContext c{};
        c.scene = scene;
        // The caller's entry guard requires application aliases; cleanup does not read them.
        ClawPlayerDeathCommandGlobals globals{};
        c.application = &globals;
        return claw_application_level_progression_entry(0x42b520, receiver, nullptr, 0, &c,
            [](ClawApplicationLevelProgressionContext *c, const ClawApplicationLevelProgressionCall *q, void *u) {
                return dependency(static_cast<ClawHost *>(u), q, c->fault);
            }, host, result);
    }
    ClawBootyProgressionContext c{};
    ClawSpecialCommandGlobals globals{};
    c.scene = scene;
    c.globals = &globals;
    c.scratchToken = scratch;
    uint32_t level = 0xfffffffe;
    return claw_booty_progression_entry(0x42b140, receiver, &level, 1, &c,
        [](ClawBootyProgressionContext *c, const ClawBootyProgressionCall *q, void *u) {
            return dependency(static_cast<ClawHost *>(u), q, c->fault);
        }, host, result);
}
