#include "AudioManagerLifecycleRuntime.h"
#include "AudioEvents.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Run {
    ClawAudioManagerLifecycleContext *c;
    ClawAudioManagerLifecycleDependency d;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t token, uint32_t words) {
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, token, words) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    if (bad(r))
        return;
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}
uint32_t call(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> args = {}, uint32_t method = 0,
              uint32_t *out = nullptr) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawAudioManagerLifecycleCall e{};
    e.function = f;
    e.receiver = recv;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    e.deviceMethod = method;
    e.outputWord = out;
    return r.d(r.c, &e, r.user);
}
uint32_t com(Run &r, uint32_t object, uint32_t method, std::initializer_list<uint32_t> args) {
    const uint32_t vt = rd(r, object), fn = rd(r, vt + method);
    return call(r, fn, 0, args, method);
}
bool guard(Run &r, uint32_t &count) {
    const uint32_t limit = r.c->maximumTraversal ? r.c->maximumTraversal : 65536;
    if (count++ >= limit) {
        r.c->fault = 3;
        return false;
    }
    return !bad(r);
}
void table(Run &r) {
    if (bad(r))
        return;
    auto *p = span(r, 0x541178, 101);
    if (p)
        for (uint32_t i = 0; i <= 100; ++i)
            p[i] = uint32_t(claw_audio_volume_table(i));
}
void shutdown(Run &r, uint32_t manager) {
    if (rd(r, manager + 0x78)) {
        uint32_t n = 0, head = rd(r, manager + 4), pool = head ? head - 4 : 0;
        while (pool && !bad(r)) {
            if (!guard(r, n))
                return;
            call(r, 0x4b4ae0, manager, {pool});
            head = rd(r, manager + 4);
            pool = head ? head - 4 : 0;
        }
        if (bad(r))
            return;
        const uint32_t device = rd(r, manager + 0x14);
        com(r, device, 8, {device});
    }
    wr(r, manager + 0x78, 0);
}
void destroy(Run &r, uint32_t manager) {
    wr(r, manager, 0x513514);
    if (rd(r, manager + 0x78) && !bad(r))
        shutdown(r, manager);
}
uint32_t startup(Run &r, uint32_t manager, uint32_t hwnd, uint32_t level) {
    auto *output = span(r, manager + 0x14, 1);
    if (!output)
        return 0;
    if (call(r, 0x4f4480, 0, {0, manager + 0x14, 0}, 0, output))
        return 0;
    if (bad(r))
        return 0;
    uint32_t device = rd(r, manager + 0x14);
    const uint32_t error = com(r, device, 0x18, {device, hwnd, level}) != 0;
    if (bad(r))
        return 0;
    if (error) {
        call(r, 0x4b4ed0, 0, {0x53228c, 0x27d, error});
        device = rd(r, manager + 0x14);
        com(r, device, 8, {device});
        return 0;
    }
    wr(r, manager + 0x7c, 0);
    wr(r, manager + 0x78, 1);
    return 1;
}
void stopPool(Run &r, uint32_t pool) {
    const uint32_t manager = rd(r, pool + 0x10);
    if (!rd(r, manager + 0x78) || bad(r))
        return;
    uint32_t head = rd(r, pool + 0x30), voice = head ? head - 4 : 0, n = 0;
    while (voice && !bad(r)) {
        if (!guard(r, n))
            return;
        call(r, 0x4b3e30, voice);
        head = rd(r, voice + 4);
        voice = head ? head - 4 : 0;
    }
}
void stop(Run &r, uint32_t manager) {
    if (!rd(r, manager + 0x78) || bad(r))
        return;
    uint32_t head = rd(r, manager + 4), pool = head ? head - 4 : 0, n = 0;
    while (pool && !bad(r)) {
        if (!guard(r, n))
            return;
        call(r, 0x4b3e30, pool);
        stopPool(r, pool);
        head = rd(r, pool + 4);
        pool = head ? head - 4 : 0;
    }
}
} // namespace
extern "C" uint32_t claw_audio_manager_lifecycle_entry(uint32_t f, uint32_t receiver, const uint32_t *args,
                                                       uint32_t count, ClawAudioManagerLifecycleContext *c,
                                                       ClawAudioManagerLifecycleDependency d, void *user,
                                                       uint32_t *result) {
    if (result)
        *result = 0;
    if (!c)
        return 0;
    uint32_t required = 0;
    switch (f) {
    case 0x4b4710:
    case 0x4b4790:
    case 0x4b4860:
    case 0x4b4b40:
    case 0x4b4670:
    case 0x4b3c80:
        break;
    case 0x4b4770:
        required = 1;
        break;
    case 0x4b47e0:
        required = 2;
        break;
    default:
        return 0;
    }
    if (count != required || (count && !args)) {
        c->fault = 2;
        return 0;
    }
    Run r{c, d, user};
    if (bad(r))
        return 0;
    uint32_t out = 0;
    switch (f) {
    case 0x4b4710:
        wr(r, receiver + 4, 0);
        wr(r, receiver + 8, 0);
        wr(r, receiver + 0xc, 0);
        wr(r, receiver + 0x10, 0);
        wr(r, receiver, 0x513514);
        wr(r, receiver + 0x78, 0);
        table(r);
        out = receiver;
        break;
    case 0x4b3c80:
        table(r);
        break;
    case 0x4b47e0:
        out = startup(r, receiver, args[0], args[1]);
        break;
    case 0x4b4860:
        shutdown(r, receiver);
        break;
    case 0x4b4790:
        destroy(r, receiver);
        break;
    case 0x4b4770:
        destroy(r, receiver);
        if (!bad(r) && (args[0] & 1)) {
            if (!c->scene.free)
                c->fault = 1;
            else
                c->scene.free(c->scene.context, receiver);
        }
        out = receiver;
        break;
    case 0x4b4b40:
        stop(r, receiver);
        break;
    case 0x4b4670:
        stopPool(r, receiver);
        break;
    default:
        break;
    }
    if (result)
        *result = out;
    return !bad(r);
}
