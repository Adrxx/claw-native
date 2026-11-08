#include "CArrayRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawCArrayContext *c;
    ClawCArrayDependency d;
    void *user;
};
int32_t si(uint32_t x) {
    int32_t i;
    std::memcpy(&i, &x, 4);
    return i;
}
uint32_t *words(Run &r, uint32_t t, uint32_t n) {
    if (!r.c->scene.lookup) {
        r.c->fault = 1;
        return nullptr;
    }
    auto *p = r.c->scene.lookup(r.c->scene.context, t, n);
    if (!p)
        r.c->fault = 1;
    return p;
}
uint8_t *bytes(Run &r, uint32_t t, uint32_t n) {
    if (!n)
        return nullptr;
    if (!t) {
        r.c->fault = 2;
        return nullptr;
    }
    const uint64_t count = (uint64_t(t & 3u) + n + 3) / 4;
    if (count > 0xffffffff) {
        r.c->fault = 2;
        return nullptr;
    }
    auto *p = words(r, t & ~3u, uint32_t(count));
    return p ? reinterpret_cast<uint8_t *>(p) + (t & 3u) : nullptr;
}
uint32_t call(Run &r, uint32_t f, std::initializer_list<uint32_t> args = {}) {
    ClawCArrayCall e{};
    e.function = f;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    if (r.d)
        return r.d(r.c, &e, r.user);
    if (r.c->scene.call) {
        ClawSceneActorCall s{};
        s.function = f;
        s.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, s.arguments);
        return r.c->scene.call(r.c->scene.context, s);
    }
    r.c->fault = 1;
    return 0;
}
uint32_t fill(Run &r, uint32_t dst, uint32_t value, uint32_t count) {
    if (!count)
        return dst;
    auto *p = bytes(r, dst, count);
    if (p)
        std::memset(p, int(value & 255), count);
    return dst;
}
uint32_t copy(Run &r, uint32_t dst, uint32_t src, uint32_t count) {
    if (!count)
        return dst;
    auto *a = bytes(r, dst, count);
    auto *b = bytes(r, src, count);
    if (a && b)
        std::memmove(a, b, count);
    return dst;
}
uint32_t physical(Run &r, uint32_t count) {
    const uint32_t rounded = (count + 15) & ~15u;
    if (rounded <= r.c->smallBlockThreshold) {
        call(r, 0x4a7bc0, {9});
        if (r.c->fault)
            return 0;
        const uint32_t small = call(r, 0x4ab4c0, {rounded >> 4});
        if (r.c->fault)
            return 0;
        call(r, 0x4a7c40, {9});
        if (r.c->fault || small)
            return small;
    }
    if (!r.c->heapAllocFunction) {
        r.c->fault = 1;
        return 0;
    }
    return call(r, r.c->heapAllocFunction, {r.c->heapHandle, 0, rounded});
}
uint32_t mallocCore(Run &r, uint32_t count, uint32_t mode) {
    if (count > 0xffffffe0)
        return 0;
    if (!count)
        count = 1;
    for (uint32_t attempts = 0; attempts < 1000000; ++attempts) {
        const uint32_t allocation = count <= 0xffffffe0 ? physical(r, count) : 0;
        if (r.c->fault || allocation)
            return allocation;
        if (!mode || !call(r, 0x4ad350, {count}) || r.c->fault)
            return 0;
    }
    r.c->fault = 2;
    return 0;
}
uint32_t allocate(Run &r, uint32_t count) {
    if (!r.c->composeAllocator)
        return call(r, 0x4f63ec, {count});
    uint32_t handler = r.c->globalNewHandler;
    for (uint32_t attempts = 0; attempts < 1000000; ++attempts) {
        const uint32_t allocation =
            r.c->composeAllocator == 2 ? mallocCore(r, count, r.c->crtNewMode) : call(r, 0x4a48e0, {count});
        if (r.c->fault || allocation)
            return allocation;
        if (handler == r.c->globalNewHandler) {
            const uint32_t state = call(r, 0x5022b5);
            if (r.c->fault)
                return 0;
            auto *p = words(r, state + 0x28, 1);
            if (!p)
                return 0;
            handler = *p;
        }
        if (!handler)
            return 0;
        if (!call(r, handler, {count}) || r.c->fault)
            return 0;
    }
    r.c->fault = 2;
    return 0;
}
uint32_t release(Run &r, uint32_t p) {
    return call(r, r.c->composeAllocator ? 0x4a49b0 : 0x4f6428, {p});
}
uint32_t resize(Run &r, uint32_t receiver, uint32_t size, uint32_t grow) {
    auto *p = words(r, receiver, 5);
    if (!p)
        return 0;
    uint32_t eax = grow;
    if (grow != 0xffffffff)
        p[4] = grow;
    if (!size) {
        eax = release(r, p[1]);
        if (r.c->fault)
            return eax;
        p[1] = p[3] = p[2] = 0;
        return eax;
    }
    if (!p[1]) {
        const uint32_t count = size * 4;
        const uint32_t allocation = allocate(r, count);
        if (r.c->fault)
            return allocation;
        p[1] = allocation;
        eax = fill(r, allocation, 0, count);
        if (r.c->fault)
            return eax;
        p[3] = size;
        p[2] = size;
        return eax;
    }
    if (si(size) <= si(p[3])) {
        const uint32_t old = p[2];
        eax = old;
        if (si(size) > si(old)) {
            const uint32_t start = p[1] + old * 4;
            eax = fill(r, start, 0, (size - old) * 4);
            if (r.c->fault)
                return eax;
        }
        p[2] = size;
        return eax;
    }
    uint32_t delta = p[4];
    if (!delta) {
        int32_t n = si(p[2]) / 8;
        delta = uint32_t(std::max(4, std::min(n, 1024)));
    }
    const uint32_t candidate = p[3] + delta;
    const uint32_t capacity = si(size) < si(candidate) ? candidate : size;
    const uint32_t allocation = allocate(r, capacity * 4);
    if (r.c->fault)
        return allocation;
    copy(r, allocation, p[1], p[2] * 4);
    if (r.c->fault)
        return allocation;
    fill(r, allocation + p[2] * 4, 0, (size - p[2]) * 4);
    if (r.c->fault)
        return allocation;
    release(r, p[1]);
    if (r.c->fault)
        return allocation;
    p[1] = allocation;
    p[2] = size;
    p[3] = capacity;
    return capacity;
}
} // namespace
void claw_carray_defaults(ClawCArrayContext *c) {
    if (c) {
        c->globalNewHandler = 0xffffffff;
        c->crtNewMode = 0;
        c->smallBlockThreshold = 480;
    }
}
uint32_t claw_carray_entry(uint32_t function, uint32_t receiver, uint32_t a, uint32_t b, uint32_t c,
                           ClawCArrayContext *context, ClawCArrayDependency d, void *user, uint32_t *result) {
    if (!context)
        return 0;
    Run r{context, d, user};
    uint32_t value = 0;
    switch (function) {
    case 0x4f58ab: {
        auto *p = words(r, receiver, 5);
        if (p) {
            p[0] = 0x5108fc;
            p[1] = p[4] = p[3] = p[2] = 0;
            value = receiver;
        }
        break;
    }
    case 0x4f582f: {
        auto *p = words(r, receiver, 5);
        if (!p)
            break;
        if (si(a) >= si(p[2]))
            resize(r, receiver, a + 1, 0xffffffff);
        if (context->fault)
            break;
        value = p[1];
        auto *target = words(r, value + a * 4, 1);
        if (target)
            *target = b;
        break;
    }
    case 0x4f5915:
        value = resize(r, receiver, a, b);
        break;
    case 0x4f63ec:
        value = allocate(r, a);
        break;
    case 0x4f6428:
        value = release(r, a);
        break;
    case 0x4a4a20:
        value = fill(r, a, b, c);
        break;
    case 0x4a4a80:
        value = copy(r, a, b, c);
        break;
    case 0x4a48e0:
        value = mallocCore(r, a, context->crtNewMode);
        break;
    case 0x4a4900:
        value = mallocCore(r, a, b);
        break;
    case 0x4a4950:
        value = physical(r, a);
        break;
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
