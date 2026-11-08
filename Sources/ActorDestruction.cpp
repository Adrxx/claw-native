#include "ActorDestruction.h"
#include <initializer_list>
namespace {
struct Run {
    ClawActorDestructionGlobals *g;
    ClawSceneActorHost h;
    uint32_t *fault;
};
bool bad(const Run &r) {
    return r.fault && *r.fault;
}
void fail(Run &r) {
    if (r.fault)
        *r.fault = 1;
}
uint32_t *span(Run &r, uint32_t token, uint32_t words) {
    if (!r.h.lookup) {
        fail(r);
        return nullptr;
    }
    auto *p = r.h.lookup(r.h.context, token, words);
    if (!p)
        fail(r);
    return p;
}
uint32_t entry(Run &, uint32_t, uint32_t, uint32_t, uint32_t *);
uint32_t invoke(Run &r, uint32_t fn, uint32_t receiver, uint32_t a = 0, uint32_t b = 0, uint32_t count = 0) {
    uint32_t result = 0;
    if (entry(r, fn, receiver, a, &result))
        return result;
    if (!r.h.call) {
        fail(r);
        return 0;
    }
    return r.h.call(r.h.context, {fn, receiver, {a, b, 0, 0}, count});
}
void release(Run &r, uint32_t token) {
    if (!r.h.free) {
        fail(r);
        return;
    }
    r.h.free(r.h.context, token);
}
void cleanLogic(Run &r, uint32_t token, uint32_t *a) {
    for (uint32_t offset : {0x6cu, 0x70u, 0x78u}) {
        const uint32_t logic = a[offset / 4];
        if (logic) {
            auto *l = span(r, logic, 1);
            if (!l)
                return;
            auto *v = span(r, l[0] + 4, 1);
            if (!v)
                return;
            invoke(r, *v, logic, 1, 0, 1);
            if (bad(r))
                return;
            a[offset / 4] = 0;
        }
    }
    (void)token;
}
void resetGeometry(uint32_t *a) {
    a[0xac / 4] = a[0x20 / 4] = a[0x4c / 4] = 0x80000000;
    a[0xc4 / 4] = a[0x38 / 4] = 0xffffffff;
}
uint32_t entry(Run &r, uint32_t fn, uint32_t receiver, uint32_t argument, uint32_t *result) {
    uint32_t ret = 0;
    uint32_t *p = nullptr;
    switch (fn) {
    case 0x4c9be0:
    case 0x4c99a0:
    case 0x4c80c0:
    case 0x4c9b30:
    case 0x47cc80:
    case 0x4c9e60: {
        const uint32_t body = fn == 0x4c9be0   ? 0x4c9c00
                              : fn == 0x4c99a0 ? 0x4c99c0
                              : fn == 0x4c80c0 ? 0x4c80e0
                              : fn == 0x4c9b30 ? 0x4c9b50
                              : fn == 0x4c9e60 ? 0x4c9e80
                                               : 0x47cca0;
        entry(r, body, receiver, 0, nullptr);
        if (bad(r))
            break;
        if (argument & 1)
            release(r, receiver);
        ret = receiver;
        break;
    }
    case 0x4c9e80:
        p = span(r, receiver, 128);
        if (!p)
            break;
        p[0] = 0x5137b0;
        cleanLogic(r, receiver, p);
        if (bad(r))
            break;
        resetGeometry(p);
        entry(r, 0x4c99c0, receiver, 0, nullptr);
        break;
    case 0x4c9c00:
        p = span(r, receiver, 128);
        if (!p)
            break;
        p[0] = 0x5137f0;
        p[0x168 / 4] = p[0x16c / 4] = 0xffffffff;
        p[0x170 / 4] = p[0x174 / 4] = 0;
        cleanLogic(r, receiver, p);
        if (bad(r))
            break;
        resetGeometry(p);
        p[0x188 / 4] = 0x513870;
        entry(r, 0x4c8210, receiver + 0x188, 0, nullptr);
        p[0x188 / 4] = 0x50becc;
        // Original inlines the base destructor after animation teardown, including
        // a second pointer pass if a callback rebound one of the earlier fields.
        entry(r, 0x4c99c0, receiver, 0, nullptr);
        break;
    case 0x4c99c0:
        p = span(r, receiver, 128);
        if (!p)
            break;
        p[0] = 0x513770;
        cleanLogic(r, receiver, p);
        if (bad(r))
            break;
        resetGeometry(p);
        p[1] = 0xffffffff;
        p[2] = p[3] = 0;
        p[0] = 0x50becc;
        break;
    case 0x4c9a70:
        p = span(r, receiver, 128);
        if (!p)
            break;
        cleanLogic(r, receiver, p);
        if (!bad(r))
            resetGeometry(p);
        break;
    case 0x4c80e0:
        p = span(r, receiver, 93);
        if (!p)
            break;
        p[0] = 0x513740;
        p[0x10 / 4] = 0;
        if (p[0x14 / 4]) {
            release(r, p[0x14 / 4]);
            if (bad(r))
                break;
            p[0x14 / 4] = 0;
        }
        if (p[0x18 / 4]) {
            const uint32_t object = p[0x18 / 4];
            auto *e = span(r, object, 1);
            if (!e)
                break;
            auto *v = span(r, e[0], 1);
            if (!v)
                break;
            invoke(r, *v, object, 1, 0, 1);
            if (bad(r))
                break;
            p[0x18 / 4] = 0;
        }
        p[2] = p[3] = 0;
        p[1] = 0xffffffff;
        p[0] = 0x50becc;
        break;
    case 0x4c9b50:
        p = span(r, receiver, 4);
        if (!p)
            break;
        p[0] = 0x513870;
        entry(r, 0x4c8210, receiver, 0, nullptr);
        p[0] = 0x50becc;
        break;
    case 0x4c8210:
        p = span(r, receiver, 4);
        if (p)
            p[1] = p[2] = p[3] = 0;
        break;
    case 0x47cca0:
        p = span(r, receiver, 264);
        if (!p)
            break;
        p[0] = 0x50b16c;
        entry(r, 0x4dbcd0, receiver + 0x2f4, 0, nullptr);
        if (bad(r))
            break;
        entry(r, 0x4f6584, receiver + 0x1a8, 0, nullptr);
        if (bad(r))
            break;
        entry(r, 0x4f6584, receiver + 0x1a4, 0, nullptr);
        if (!bad(r))
            p[0] = 0x50b014;
        break;
    case 0x4dbcd0:
        p = span(r, receiver, 4);
        if (!p)
            break;
        p[0] = 0x513e34;
        if (p[2] > 32) {
            if (!r.h.call) {
                fail(r);
                break;
            }
            r.h.call(r.h.context, {0x4a49b0, 0, {p[3], 0, 0, 0}, 1});
        }
        p[0] = 0x513e28;
        if (!r.h.call) {
            fail(r);
            break;
        }
        r.h.call(r.h.context, {0x4dc560, p[1], {receiver, 0, 0, 0}, 2});
        break;
    case 0x4f6584:
        p = span(r, receiver, 1);
        if (!p)
            break;
        if (p[0] == r.g->emptyStringToken)
            break;
        {
            const uint32_t header = p[0] - 12;
            auto *refs = span(r, header, 1);
            if (!refs)
                break;
            *refs -= 1;
            if ((*refs & 0x80000000) || !*refs)
                release(r, header);
        }
        break;
    case 0x48cf50:
        if (r.g->holderActorToken && argument == r.g->heldActorToken) {
            p = span(r, r.g->holderActorToken, 128);
            if (!p)
                break;
            if (p[0x6c / 4]) {
                auto *l = span(r, p[0x6c / 4], 93);
                if (!l)
                    break;
                if (l[0x1c / 4] == 15) {
                    l[0x130 / 4] = 0;
                    r.g->heldActorToken = 0;
                }
            }
        }
        break;
    default:
        return 0;
    }
    if (result)
        *result = ret;
    return 1;
}
} // namespace
uint32_t claw_actor_destruction_entry(uint32_t fn, uint32_t receiver, uint32_t arg,
                                      ClawActorDestructionGlobals *globals, ClawSceneActorHost host, uint32_t *fault,
                                      uint32_t *result) {
    if (!globals) {
        if (fault)
            *fault = 1;
        return 0;
    }
    Run r{globals, host, fault};
    return entry(r, fn, receiver, arg, result);
}
uint32_t claw_actor_destroy(uint32_t actor, uint32_t flag, ClawActorDestructionGlobals *globals,
                            ClawSceneActorHost host, uint32_t *fault) {
    if (!globals) {
        if (fault)
            *fault = 1;
        return 0;
    }
    Run r{globals, host, fault};
    auto *a = span(r, actor, 1);
    if (!a)
        return 0;
    auto *v = span(r, a[0] + 4, 1);
    if (!v)
        return 0;
    invoke(r, *v, actor, flag, 0, 1);
    return !bad(r);
}
