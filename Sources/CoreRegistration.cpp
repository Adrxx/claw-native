#include "CoreRegistration.h"
#include <cstring>
#include <initializer_list>
namespace {
constexpr uint32_t globalBase = 0x544b14, rowsOffset = 0x84 / 4, countOffset = 129;
struct Run {
    ClawCoreRegistrationGlobals *g;
    ClawSceneActorHost h;
    uint32_t *fault;
};
void fail(Run &r, uint32_t value = 1) {
    if (r.fault)
        *r.fault = value;
}
bool bad(Run &r) {
    return r.fault && *r.fault;
}
uint32_t *span(Run &r, uint32_t token, uint32_t words) {
    if (token >= globalBase && uint64_t(token - globalBase) + uint64_t(words) * 4 <= sizeof r.g->words &&
        (token & 3) == 0)
        return r.g->words + (token - globalBase) / 4;
    if (!r.h.lookup) {
        fail(r);
        return nullptr;
    }
    auto *p = r.h.lookup(r.h.context, token, words);
    if (!p)
        fail(r);
    return p;
}
uint32_t call(Run &r, uint32_t fn, uint32_t receiver, std::initializer_list<uint32_t> args) {
    if (!r.h.call) {
        fail(r);
        return 0;
    }
    ClawSceneActorCall e{};
    e.function = fn;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    uint32_t n = 0;
    for (auto a : args)
        e.arguments[n++] = a;
    return r.h.call(r.h.context, e);
}
void messages(Run &r) {
    auto *g = r.g->words;
    if (g[14])
        return;
    g[14] = 0x533418;
    g[7] = 0x5333fc;
    g[8] = 0x5333f0;
    g[13] = 0x5333d0;
    g[9] = 0x5333c0;
    g[11] = 0x5333a8;
    g[10] = 0x533390;
    g[12] = 0x53337c;
}
uint32_t search(Run &r, uint32_t receiver, uint32_t key) {
    auto *handler = span(r, receiver, 2);
    if (!handler)
        return 0xffffffff;
    const uint32_t count = r.g->words[countOffset];
    if (count > 32) {
        fail(r, 2);
        return 0xffffffff;
    }
    int32_t high = int32_t(count) - 1, low = 0;
    while (high >= low) {
        const int32_t mid = (high + low) / 2;
        handler[1] = uint32_t(mid);
        const uint32_t object = r.g->words[rowsOffset + uint32_t(mid) * 3];
        const int32_t difference = int32_t(object - key);
        if (difference < 0)
            low = mid + 1;
        else if (!difference)
            return uint32_t(mid);
        else
            high = mid - 1;
    }
    handler[1] = uint32_t(high + 1);
    return 0xffffffff;
}
uint32_t registration(Run &r, uint32_t receiver, uint32_t object, uint32_t function) {
    uint32_t count = r.g->words[countOffset];
    if (function && int32_t(count) >= 32)
        return 0;
    if (count > 32) {
        fail(r, 2);
        return 0;
    }
    const uint32_t found = count ? search(r, receiver, object) : 0xffffffff;
    if (bad(r))
        return 0;
    if (found == 0xffffffff) {
        if (!function)
            return 0;
        auto *handler = span(r, receiver, 2);
        if (!handler)
            return 0;
        const uint32_t index = handler[1];
        if (index >= 32 || (count && index > count)) {
            fail(r, 2);
            return 0;
        }
        auto *row = r.g->words + rowsOffset + index * 3;
        if (count)
            std::memmove(row + 3, row, (count - index) * 12);
        row[1] = function;
        row[0] = object;
        r.g->words[countOffset] = count + 1;
        row[2] &= 0xffff0000u;
        return 0;
    }
    auto *row = r.g->words + rowsOffset + found * 3;
    const uint32_t previous = row[1];
    if (function) {
        row[1] = function;
        return previous;
    }
    auto *handler = span(r, receiver, 2);
    if (!handler)
        return 0;
    const uint32_t index = handler[1];
    if (index >= count) {
        fail(r, 2);
        return 0;
    }
    row = r.g->words + rowsOffset + index * 3;
    std::memmove(row, row + 3, (count - index - 1) * 12);
    r.g->words[countOffset] = count - 1;
    return previous;
}
void baseConstruct(Run &r, uint32_t receiver, uint32_t handler) {
    auto *p = span(r, receiver, 2);
    if (!p)
        return;
    p[1] = handler ? handler : 0x544b18;
    p[0] = 0x513e28;
    messages(r);
}
void handlerConstruct(Run &r, uint32_t receiver, uint32_t prefix) {
    auto *p = span(r, receiver, 6);
    if (!p)
        return;
    p[3] = p[4] = 2;
    p[0] = 0x4dc420;
    p[2] &= 0xffff0000u;
    p[5] = prefix;
}
uint32_t bitInitialize(Run &r, uint32_t receiver, uint32_t count) {
    auto *p = span(r, receiver, 4);
    if (!p)
        return 0;
    if (count <= 32) {
        p[3] = 0;
        p[2] = 32;
        return 1;
    }
    const uint32_t words = (count >> 5) + ((count & 31) != 0);
    p[2] = words;
    if (!r.h.allocate) {
        fail(r);
        return 0;
    }
    const uint32_t token = r.h.allocate(r.h.context, words * 4);
    p[3] = token;
    if (!token)
        return 0;
    auto *data = span(r, token, words);
    if (!data)
        return 0;
    std::memset(data, 0, size_t(words) * 4);
    p[2] <<= 5;
    return 1;
}
void diagnostic(Run &r, uint32_t receiver, uint32_t message, uint32_t code) {
    auto *p = span(r, receiver, 2);
    if (!p)
        return;
    r.g->words[0] = r.g->errorLocation;
    call(r, 0x4db4d0, p[1], {receiver, message, code});
}
uint32_t bitConstruct(Run &r, uint32_t receiver, uint32_t count) {
    baseConstruct(r, receiver, 0x544b68);
    auto *p = span(r, receiver, 4);
    if (!p)
        return receiver;
    p[0] = 0x513e34;
    if (!bitInitialize(r, receiver, count) && !bad(r))
        diagnostic(r, receiver, r.g->words[14], 12);
    return receiver;
}
void backingFree(Run &r, uint32_t receiver, uint32_t token) {
    if (!token)
        return;
    auto *first = span(r, r.g->freeScratchTokens[0], 1);
    auto *second = span(r, r.g->freeScratchTokens[1], 1);
    if (!first || !second)
        return;
    *first = receiver;
    *second = token;
    call(r, 0x4a7bc0, 0, {9});
    if (bad(r))
        return;
    const uint32_t block = call(r, 0x4ab400, 0, {token, r.g->freeScratchTokens[0], r.g->freeScratchTokens[1]});
    if (bad(r))
        return;
    if (block) {
        call(r, 0x4ab460, 0, {*first, *second, block});
        if (bad(r))
            return;
        call(r, 0x4a7c40, 0, {9});
    } else {
        call(r, 0x4a7c40, 0, {9});
        if (bad(r))
            return;
        if (!r.g->heapFreeFunction) {
            fail(r);
            return;
        }
        call(r, r.g->heapFreeFunction, 0, {r.g->heapHandle, 0, token});
    }
}
uint32_t entry(Run &r, uint32_t fn, uint32_t receiver, uint32_t a, uint32_t b, uint32_t *out) {
    uint32_t result = 0;
    switch (fn) {
    case 0x4dc3a0:
        handlerConstruct(r, receiver, a);
        break;
    case 0x4dc3d0:
        result = search(r, receiver, a);
        break;
    case 0x4dc560:
        result = registration(r, receiver, a, b);
        break;
    case 0x4db620:
        baseConstruct(r, receiver, a);
        result = receiver;
        break;
    case 0x4db6c0: {
        auto *p = span(r, receiver, 2);
        if (!p)
            break;
        p[0] = 0x513e28;
        registration(r, p[1], receiver, 0);
        break;
    }
    case 0x4dc7b0:
        result = bitInitialize(r, receiver, a);
        break;
    case 0x4dc180:
        result = bitConstruct(r, receiver, r.g->defaultBitCount);
        break;
    case 0x4dbe10: {
        if (!a) {
            baseConstruct(r, receiver, 0x544b68);
            auto *object = span(r, receiver, 4);
            if (object)
                object[0] = 0x513e34;
            diagnostic(r, receiver, r.g->words[10], 22);
            result = receiver;
            break;
        }
        auto *p = span(r, a, 1);
        if (!p)
            break;
        if (uint8_t(*p) != 0)
            return 0;
        result = bitConstruct(r, receiver, b ? b : r.g->defaultBitCount);
        break;
    }
    case 0x4db600:
    case 0x4db610:
        handlerConstruct(r, 0x544b18, 0x53336c);
        break;
    case 0x4dbb70:
    case 0x4dbb80:
        handlerConstruct(r, 0x544b50, 0x533448);
        break;
    case 0x4dc160:
    case 0x4dc170:
        handlerConstruct(r, 0x544b68, 0x533474);
        break;
    case 0x4dc260:
    case 0x4dc270:
        handlerConstruct(r, 0x544b80, 0x533480);
        break;
    case 0x4dc380:
    case 0x4dc390:
        break;
    case 0x4f6428:
    case 0x4a49b0:
        backingFree(r, receiver, a);
        break;
    default:
        return 0;
    }
    if (out)
        *out = result;
    return 1;
}
} // namespace
void claw_core_registration_defaults(ClawCoreRegistrationGlobals *g) {
    if (g)
        g->defaultBitCount = 32;
}
uint32_t claw_core_registration_initialize(ClawCoreRegistrationGlobals *g, ClawSceneActorHost host, uint32_t *fault) {
    if (!g) {
        if (fault)
            *fault = 1;
        return 0;
    }
    Run r{g, host, fault};
    for (auto fn : {0x4db600u, 0x4dbb70u, 0x4dc160u, 0x4dc260u, 0x4dc380u}) {
        entry(r, fn, 0, 0, 0, nullptr);
        if (bad(r))
            return 0;
    }
    return 1;
}
uint32_t claw_core_registration_entry(uint32_t fn, uint32_t receiver, uint32_t a, uint32_t b,
                                      ClawCoreRegistrationGlobals *g, ClawSceneActorHost host, uint32_t *fault,
                                      uint32_t *result) {
    if (!g) {
        if (fault)
            *fault = 1;
        return 0;
    }
    Run r{g, host, fault};
    return entry(r, fn, receiver, a, b, result);
}
