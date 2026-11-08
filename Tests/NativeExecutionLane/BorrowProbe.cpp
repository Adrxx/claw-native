#include "Bridge.h"
#include <algorithm>
#include <cassert>
#include <pthread.h>

namespace {
struct Scope {
    int &alive, &destroyed;
    Scope(int &a, int &d) : alive(a), destroyed(d) { ++alive; }
    ~Scope() { --alive; ++destroyed; }
};
void nested(void *user, LaneBorrowCallback callback, int32_t expected,
            uint8_t *outer, int &alive, int &destroyed) {
    Scope guard(alive, destroyed);
    uint8_t inner[13];
    std::fill_n(inner, 13, uint8_t(0xa7));
    LaneBorrowedCall call{};
    for (uint32_t i = 0; i != 40; ++i) call.arguments[i] = 0x71000000 + i;
    call.localMask = (uint64_t(1) << 39) | 3;
    call.outer = outer; call.inner = inner; call.alias = inner + 3;
    call.outerBytes = 21; call.innerBytes = 13;
    const auto owner = pthread_self();
    const auto descriptorAddress = &call;
    assert(alive == 2 && destroyed == 0);
    const int32_t status = callback(user, &call);
    assert(status == expected && pthread_equal(owner, pthread_self()));
    assert(&call == descriptorAddress && call.alias == inner + 3);
    assert(alive == 2 && destroyed == 0);
    assert(call.arguments[39] == 0x71000027 && call.localMask == ((uint64_t(1) << 39) | 3));
    assert(inner[0] == 0xa7 && inner[12] == 0xa7 && outer[0] == 0x91 && outer[20] == 0x91);
    for (int i = 1; i < 12; ++i) assert(inner[i] == (status == 1 ? 0x40 + i : 0xa7));
    for (int i = 1; i < 20; ++i) assert(outer[i] == (status == 1 ? 0x20 + i : 0x91));
}
}
extern "C" uint32_t lane_borrow_probe(void *user, LaneBorrowCallback callback, int32_t expected) {
    int alive = 0, destroyed = 0;
    {
        Scope outerScope(alive, destroyed);
        uint8_t outer[21];
        std::fill_n(outer, 21, uint8_t(0x91));
        nested(user, callback, expected, outer, alive, destroyed);
        assert(alive == 1 && destroyed == 1);
    }
    assert(alive == 0 && destroyed == 2);
    return 2;
}
