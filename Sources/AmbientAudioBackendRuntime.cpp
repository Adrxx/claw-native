#include "AmbientAudioBackendRuntime.h"
#include "AudioEvents.h"
#include <algorithm>
#include <initializer_list>
#include <limits>
namespace {
struct Run {
    ClawAmbientAudioBackendContext *c;
    ClawAmbientAudioBackendDependency d;
    void *user;
    uint32_t visits = 0;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
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
bool step(Run &r) {
    if (bad(r))
        return false;
    if (++r.visits > (r.c->maximumTraversal ? r.c->maximumTraversal : 65536)) {
        r.c->fault = 3;
        return false;
    }
    return true;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}, uint32_t method = 0,
              uint32_t *output = nullptr) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawAmbientAudioBackendCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.bufferMethod = method;
    e.outputWord = output;
    std::copy(args.begin(), args.end(), e.arguments);
    return r.d(r.c, &e, r.user);
}
uint32_t alloc(Run &r, uint32_t n) {
    if (bad(r))
        return 0;
    if (r.c->scene.allocate)
        return r.c->scene.allocate(r.c->scene.context, n);
    return call(r, 0x4f63ec, 0, {n});
}
void free(Run &r, uint32_t t) {
    if (bad(r))
        return;
    if (r.c->scene.free)
        r.c->scene.free(r.c->scene.context, t);
    else
        call(r, 0x4f6428, 0, {t});
}
uint32_t clock(Run &r) {
    if (r.d)
        return call(r, 0x546df0, 0);
    if (r.c->scene.readClock)
        return r.c->scene.readClock(r.c->scene.context);
    r.c->fault = 1;
    return 0;
}
bool device(Run &r, uint32_t voice) {
    return rd(r, rd(r, voice + 0x10) + 0x78) != 0;
}
uint32_t ds(Run &r, uint32_t voice, uint32_t method, std::initializer_list<uint32_t> parameters = {},
            uint32_t *output = nullptr) {
    const uint32_t buffer = rd(r, voice + 0xc), fn = rd(r, rd(r, buffer) + method);
    if (bad(r))
        return 0;
    ClawAmbientAudioBackendCall e{};
    e.function = fn;
    e.arguments[0] = buffer;
    e.argumentCount = 1;
    e.bufferMethod = method;
    e.outputWord = output;
    std::copy(parameters.begin(), parameters.end(), e.arguments + 1);
    e.argumentCount += uint32_t(parameters.size());
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    return r.d(r.c, &e, r.user);
}
void report(Run &r, uint32_t line, uint32_t result) {
    call(r, 0x4b4ed0, 0, {0x53228c, line, result});
}
uint32_t setRaw(Run &r, uint32_t voice, uint32_t method, uint32_t value, uint32_t line) {
    if (!device(r, voice))
        return 0;
    uint32_t error = ds(r, voice, method, {value});
    if (error) {
        report(r, line, method == 0x44 ? error : 1);
        return 0;
    }
    if (method == 0x44)
        wr(r, voice + 0x24, value);
    return !bad(r);
}
uint32_t volume(Run &r, uint32_t voice, uint32_t value) {
    if (!device(r, voice))
        return 0;
    if (value > 100) {
        r.c->fault = 2;
        return 0;
    }
    return setRaw(r, voice, 0x3c, uint32_t(claw_audio_volume_table(value)), 0xaf);
}
uint32_t pan(Run &r, uint32_t voice, uint32_t value) {
    if (!device(r, voice))
        return 0;
    if (int32_t(value) < -100 || int32_t(value) > 100) {
        r.c->fault = 2;
        return 0;
    }
    uint32_t index = int32_t(value) < 0 ? 100 + value : 100 - value, mapped = uint32_t(claw_audio_volume_table(index));
    return setRaw(r, voice, 0x40, int32_t(value) < 0 ? mapped : 0u - mapped, 0xf6);
}
uint32_t pitch(Run &r, uint32_t voice, uint32_t value) {
    if (!device(r, voice))
        return 0;
    const uint32_t base = rd(r, voice + 0x18), scaled = value * base;
    uint32_t hz = uint32_t(int32_t(scaled) / 100) + base;
    if (hz > 99999)
        hz = 99999;
    if (hz < 101)
        hz = 101;
    return setRaw(r, voice, 0x44, hz, 0x12a);
}
void looping(Run &r, uint32_t voice, uint32_t value) {
    if (device(r, voice))
        wr(r, voice + 0x14, value ? rd(r, voice + 0x14) | 1 : rd(r, voice + 0x14) & ~1u);
}
uint32_t stop(Run &r, uint32_t voice) {
    if (!device(r, voice))
        return 0;
    uint32_t error = ds(r, voice, 0x48);
    if (error) {
        report(r, 0x7a, 1);
        return 0;
    }
    return !bad(r);
}
uint32_t play(Run &r, uint32_t voice) {
    if (!device(r, voice))
        return 0;
    uint32_t error = ds(r, voice, 0x30, {0, 0, rd(r, voice + 0x14)});
    if (error) {
        report(r, 0x5f, 1);
        return 0;
    }
    return !bad(r);
}
uint32_t get(Run &r, uint32_t voice, uint32_t method) {
    if (!device(r, voice))
        return 0;
    uint32_t out = voice;
    const uint32_t error = ds(r, voice, method, {}, &out);
    if (error) {
        report(r, method == 0x18 ? 0xc7 : 0x88, 1);
        return 0;
    }
    return method == 0x24 ? out & 1 : out;
}
uint32_t inverse(Run &r, uint32_t value) {
    // Captured integer outputs of full original4b3bf0/CRT pow/FTOL for the
    // finite DirectSound volume domain; generator and binary hash are private.
    static const uint32_t values[101] = {
        100, 93, 87, 81, 75, 70, 65, 61, 57, 53, 50, 46, 43, 40, 37, 35, 32, 30, 28, 26, 25, 23, 21, 20, 18, 17,
        16,  15, 14, 13, 12, 11, 10, 10, 9,  8,  8,  7,  7,  6,  6,  5,  5,  5,  4,  4,  4,  3,  3,  3,  3,  2,
        2,   2,  2,  2,  2,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0};
    if (!value)
        return 100;
    const int32_t quotient = int32_t(int32_t(value) < 0 ? 0u - value : value) / 100;
    if (quotient < 0 || quotient > 100) {
        r.c->fault = 2;
        return 0;
    }
    uint32_t result = values[quotient];
    return int32_t(value) < 0 ? result : 0u - result;
}
void blocksClear(Run &r, uint32_t block) {
    while (block && step(r)) {
        const uint32_t next = rd(r, block);
        free(r, block);
        block = next;
    }
}
void removeAll(Run &r, uint32_t list) {
    wr(r, list + 0xc, 0);
    wr(r, list + 0x10, 0);
    wr(r, list + 8, 0);
    wr(r, list + 4, 0);
    blocksClear(r, rd(r, list + 0x14));
    wr(r, list + 0x14, 0);
}
uint32_t plex(Run &r, uint32_t pointer, uint32_t n, uint32_t stride) {
    uint32_t block = alloc(r, n * stride + 4);
    wr(r, block, rd(r, pointer));
    wr(r, pointer, block);
    return block;
}
uint32_t newNode(Run &r, uint32_t list, uint32_t previous, uint32_t next) {
    if (!rd(r, list + 0x10)) {
        const uint32_t n = rd(r, list + 0x18);
        if (n > 65536) {
            r.c->fault = 2;
            return 0;
        }
        const uint32_t block = plex(r, list + 0x14, n, 12);
        if (bad(r))
            return 0;
        uint32_t at = block - 8 + n * 12;
        if (int32_t(n - 1) >= 0) {
            for (uint32_t left = n; left && step(r); --left) {
                wr(r, at, rd(r, list + 0x10));
                wr(r, list + 0x10, at);
                at -= 12;
            }
        }
    }
    uint32_t at = rd(r, list + 0x10);
    wr(r, list + 0x10, rd(r, at));
    wr(r, at + 4, previous);
    wr(r, at, next);
    wr(r, list + 0xc, rd(r, list + 0xc) + 1);
    wr(r, at + 8, 0);
    return at;
}
void freeNode(Run &r, uint32_t list, uint32_t node) {
    wr(r, node, rd(r, list + 0x10));
    wr(r, list + 0xc, rd(r, list + 0xc) - 1);
    wr(r, list + 0x10, node);
    if (!rd(r, list + 0xc))
        removeAll(r, list);
}
uint32_t addTail(Run &r, uint32_t list, uint32_t value) {
    uint32_t node = newNode(r, list, rd(r, list + 8), 0);
    wr(r, node + 8, value);
    const uint32_t tail = rd(r, list + 8);
    if (!tail)
        wr(r, list + 4, node);
    else
        wr(r, tail, node);
    wr(r, list + 8, node);
    return node;
}
void removeAt(Run &r, uint32_t list, uint32_t node) {
    if (node == rd(r, list + 4))
        wr(r, list + 4, rd(r, node));
    else
        wr(r, rd(r, node + 4), rd(r, node));
    if (node == rd(r, list + 8))
        wr(r, list + 8, rd(r, node + 4));
    else
        wr(r, rd(r, node) + 4, rd(r, node + 4));
    freeNode(r, list, node);
}
void insertControl(Run &r, uint32_t list, uint32_t node) {
    wr(r, node, rd(r, list));
    wr(r, node + 4, 0);
    if (rd(r, list))
        wr(r, rd(r, list) + 4, node);
    else
        wr(r, list + 4, node);
    wr(r, list, node);
}
void removeControl(Run &r, uint32_t list, uint32_t node) {
    if (!rd(r, node + 4))
        wr(r, list, rd(r, node));
    else
        wr(r, rd(r, node + 4), rd(r, node));
    if (rd(r, node))
        wr(r, rd(r, node) + 4, rd(r, node + 4));
    else
        wr(r, list + 4, rd(r, node + 4));
}
void destroyControl(Run &r, uint32_t list, uint32_t object) {
    removeControl(r, list, object + 4);
    wr(r, object, 0x513518);
    free(r, object);
}
uint32_t control(Run &r, uint32_t object, const uint32_t *a) {
    wr(r, object + 0xc, 1);
    wr(r, object + 0x10, a[3]);
    wr(r, object + 0x14, a[4]);
    wr(r, object, 0x513520);
    wr(r, object + 0x18, a[0]);
    wr(r, object + 0x1c, a[1]);
    wr(r, object + 0x20, a[2]);
    wr(r, object + 0x24, clock(r));
    return object;
}
void cancel(Run &r, uint32_t list, uint32_t voice, uint32_t kind) {
    uint32_t object = rd(r, list);
    object = object ? object - 4 : 0;
    while (object && step(r)) {
        const uint32_t nextNode = rd(r, object + 4), next = nextNode ? nextNode - 4 : 0;
        if (kind != 0xffff && rd(r, object + 0xc) != kind) {
            r.c->fault = 3;
            return;
        }
        if (rd(r, object + 0x10) == voice)
            destroyControl(r, list, object);
        object = next;
    }
}
uint32_t timed(Run &r, uint32_t voice, const uint32_t *a) {
    if (!device(r, voice))
        return 0;
    cancel(r, rd(r, voice + 0x10) + 0xc, voice, 1);
    if (bad(r))
        return 0;
    if (!a[1]) {
        volume(r, voice, a[0]);
        return !bad(r);
    }
    uint32_t object = alloc(r, 0x28);
    if (!object)
        return 0;
    uint32_t current = inverse(r, get(r, voice, 0x18));
    if (bad(r))
        return 0;
    uint32_t args[] = {a[0], current, a[1], voice, a[2]};
    control(r, object, args);
    insertControl(r, rd(r, voice + 0x10) + 0xc, object + 4);
    return !bad(r);
}
uint32_t tick(Run &r, uint32_t object, uint32_t now) {
    uint32_t elapsed = now - rd(r, object + 0x24), duration = rd(r, object + 0x20);
    bool ended = duration <= elapsed;
    if (ended)
        elapsed = duration;
    bool playing = get(r, rd(r, object + 0x10), 0x24) != 0;
    if (!playing)
        ended = true;
    else {
        uint32_t from = rd(r, object + 0x1c), numerator = (rd(r, object + 0x18) - from) * elapsed;
        if (!duration || (numerator == 0x80000000 && duration == 0xffffffff)) {
            r.c->fault = 2;
            return 0;
        }
        uint32_t v = uint32_t(int32_t(numerator) / int32_t(duration)) + from;
        volume(r, rd(r, object + 0x10), v);
    }
    if (ended && rd(r, object + 0x14))
        stop(r, rd(r, object + 0x10));
    return !ended;
}
uint32_t finish(Run &r, uint32_t object) {
    if (get(r, rd(r, object + 0x10), 0x24)) {
        if (rd(r, object + 0x14))
            stop(r, rd(r, object + 0x10));
        else
            volume(r, rd(r, object + 0x10), rd(r, object + 0x18));
    }
    return 1;
}
uint32_t controlCall(Run &r, uint32_t object, uint32_t slot, uint32_t now) {
    const uint32_t f = rd(r, rd(r, object) + slot);
    if (f == 0x4b4d80 && slot == 0)
        return tick(r, object, now);
    if (f == 0x4b4df0 && slot == 4)
        return finish(r, object);
    return slot == 0 ? call(r, f, object, {now}) : call(r, f, object);
}
uint32_t update(Run &r, uint32_t manager) {
    uint32_t object = rd(r, manager + 0xc);
    object = object ? object - 4 : 0;
    if (!object)
        return 0;
    uint32_t now = clock(r);
    if (rd(r, manager + 0x7c) < now) {
        wr(r, manager + 0x7c, now);
        while (object && step(r)) {
            uint32_t next = rd(r, object + 4);
            next = next ? next - 4 : 0;
            if (!controlCall(r, object, 0, now))
                destroyControl(r, manager + 0xc, object);
            object = next;
        }
    }
    return 1;
}
uint32_t stopManager(Run &r, uint32_t manager) {
    uint32_t object = rd(r, manager + 0xc);
    object = object ? object - 4 : 0;
    while (object && step(r)) {
        uint32_t next = rd(r, object + 4);
        next = next ? next - 4 : 0;
        controlCall(r, object, 4, 0);
        destroyControl(r, manager + 0xc, object);
        object = next;
    }
    return 1;
}
} // namespace
extern "C" uint32_t claw_ambient_audio_backend_entry(uint32_t f, uint32_t receiver, const uint32_t *a, uint32_t n,
                                                     ClawAmbientAudioBackendContext *c,
                                                     ClawAmbientAudioBackendDependency d, void *user,
                                                     uint32_t *result) {
    if (result)
        *result = 0;
    if (!c)
        return 0;
    uint32_t required;
    switch (f) {
    case 0x4b3dc0:
        required = 4;
        break;
    case 0x4b3fe0:
    case 0x4f5aa8:
        required = 3;
        break;
    case 0x4b4d00:
        required = 5;
        break;
    case 0x4b4c80:
    case 0x4f5692:
        required = 2;
        break;
    case 0x4f51c5:
    case 0x4f5212:
    case 0x4f56e7:
    case 0x4b3f40:
    case 0x4b4110:
    case 0x4b41b0:
    case 0x4b3ef0:
    case 0x4b40c0:
    case 0x4b4160:
    case 0x4b3ec0:
    case 0x4b3bf0:
    case 0x4b5210:
    case 0x4b5270:
    case 0x4b4d80:
        required = 1;
        break;
    case 0x4f5172:
    case 0x4f5ac8:
    case 0x4b3e30:
    case 0x4b3e70:
    case 0x4b3f70:
    case 0x4b3fc0:
    case 0x4b3d80:
    case 0x4b4b80:
    case 0x4b4c10:
    case 0x4b4df0:
        required = 0;
        break;
    default:
        return 0;
    }
    if (n != required || (n && !a)) {
        c->fault = 2;
        return 0;
    }
    Run r{c, d, user};
    if (bad(r))
        return 0;
    uint32_t v = 0;
    switch (f) {
    case 0x4f51c5:
        v = addTail(r, receiver, a[0]);
        break;
    case 0x4f5212:
        removeAt(r, receiver, a[0]);
        break;
    case 0x4f5172:
        removeAll(r, receiver);
        break;
    case 0x4f5692:
        v = newNode(r, receiver, a[0], a[1]);
        break;
    case 0x4f56e7:
        freeNode(r, receiver, a[0]);
        break;
    case 0x4f5ac8:
        blocksClear(r, receiver);
        break;
    case 0x4f5aa8:
        v = plex(r, a[0], a[1], a[2]);
        break;
    case 0x4b3dc0: {
        if (!device(r, receiver))
            break;
        uint32_t okV = volume(r, receiver, a[0]), okP = pan(r, receiver, a[1]), okF = pitch(r, receiver, a[2]);
        looping(r, receiver, a[3]);
        uint32_t okPlay = play(r, receiver);
        v = okV && okP && okF && okPlay;
        break;
    }
    case 0x4b3e30:
        v = stop(r, receiver);
        break;
    case 0x4b3d80:
        v = play(r, receiver);
        break;
    case 0x4b3f40:
        v = volume(r, receiver, a[0]);
        break;
    case 0x4b4110:
        v = pan(r, receiver, a[0]);
        break;
    case 0x4b41b0:
        v = pitch(r, receiver, a[0]);
        break;
    case 0x4b3ec0:
        looping(r, receiver, a[0]);
        break;
    case 0x4b3ef0:
        v = setRaw(r, receiver, 0x3c, a[0], 0xaf);
        break;
    case 0x4b40c0:
        v = setRaw(r, receiver, 0x40, a[0], 0xf6);
        break;
    case 0x4b4160:
        v = setRaw(r, receiver, 0x44, a[0], 0x12a);
        break;
    case 0x4b3f70:
        v = get(r, receiver, 0x18);
        break;
    case 0x4b3e70:
        v = get(r, receiver, 0x24);
        break;
    case 0x4b3bf0:
        v = inverse(r, a[0]);
        break;
    case 0x4b3fc0:
        if (device(r, receiver))
            v = inverse(r, get(r, receiver, 0x18));
        break;
    case 0x4b3fe0:
        v = timed(r, receiver, a);
        break;
    case 0x4b4c80:
        cancel(r, receiver, a[0], a[1]);
        break;
    case 0x4b4d00:
        v = control(r, receiver, a);
        break;
    case 0x4b4d80:
        v = tick(r, receiver, a[0]);
        break;
    case 0x4b4df0:
        v = finish(r, receiver);
        break;
    case 0x4b5210:
        insertControl(r, receiver, a[0]);
        break;
    case 0x4b5270:
        removeControl(r, receiver, a[0]);
        break;
    case 0x4b4b80:
        v = update(r, receiver);
        break;
    case 0x4b4c10:
        v = stopManager(r, receiver);
        break;
    default:
        break;
    }
    if (result)
        *result = v;
    return !bad(r);
}
