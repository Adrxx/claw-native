#ifndef CLAW_MOVIE_STATE_CLEANUP_BRIDGE_H
#define CLAW_MOVIE_STATE_CLEANUP_BRIDGE_H
#include "MovieStateCleanupRuntime.h"
/* Borrow the caller's memory and physical dependency route. Never dispatch the
   array through a recovered MFC family, or turn a provider fault into EAX. */
template <class Caller>
uint32_t clawMovieStateCleanup(Caller &caller, uint32_t function, uint32_t receiver) {
    ClawHost host{};
    struct Service {
        Caller &caller;
        ClawHost &host;
    };
    Service service{caller, host};
    // Both callbacks borrow the same stack-scoped adapter.
    host.user = &service;
    host.bytes = [](void *user, uint32_t token, uint32_t count) -> uint8_t * {
        auto &s = *static_cast<Service *>(user);
        uint64_t extent = uint64_t(token & 3) + count;
        if (extent > 0xfffffffc || uint64_t(token) + count > 0x100000000ull)
            return nullptr;
        auto words = s.caller.span(token & ~3u, uint32_t((extent + 3) / 4));
        return reinterpret_cast<uint8_t *>(words) + (token & 3);
    };
    host.call = [](void *user, const ClawCall *call) -> uint32_t {
        auto &s = *static_cast<Service *>(user);
        auto value = s.caller.call(call->function, call->receiver, call->arguments, call->argumentCount);
        if (s.caller.c.fault) {
            s.host.fault = CLAW_FAULT_HOST;
            s.host.faultAddress = call->function;
        }
        return value;
    };
    uint32_t result = 0;
    if (!claw_movie_state_cleanup_entry(function, receiver, nullptr, 0, &host, &result)) {
        if (!caller.c.fault)
            caller.c.fault = 1;
    }
    return result;
}
#endif
