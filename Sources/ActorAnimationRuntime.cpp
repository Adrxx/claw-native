#include "ActorAnimationRuntime.h"
#include <algorithm>
#include <cstring>
#include <vector>
extern "C" uint32_t claw_animation_delay(uint32_t *, uint32_t, uint32_t *);
namespace {
struct Run {
    ClawActorAnimationGlobals *g;
    ClawSceneActorHost h;
    uint32_t *fault;
};
void fail(Run &r, uint32_t value = 1) {
    if (r.fault)
        *r.fault = value;
}
bool bad(const Run &r) {
    return r.fault && *r.fault;
}
uint32_t *span(Run &r, uint32_t token, uint32_t count) {
    if (!r.h.lookup) {
        fail(r);
        return nullptr;
    }
    auto *p = r.h.lookup(r.h.context, token, count);
    if (!p)
        fail(r);
    return p;
}
uint32_t invoke(Run &r, uint32_t f, uint32_t recv, uint32_t a, uint32_t b = 0, uint32_t n = 1) {
    if (!r.h.call) {
        fail(r);
        return 0;
    }
    return r.h.call(r.h.context, {f, recv, {a, b, 0, 0}, n});
}
uint32_t firstRecord(Run &r, uint32_t sequence) {
    auto *seq = span(r, sequence, 5);
    if (!seq)
        return 0;
    if (int32_t(seq[4]) <= 0) {
        fail(r, 2);
        return 0;
    }
    auto *table = span(r, seq[3], 1);
    return table ? *table : 0;
}
void select(Run &r, uint32_t *p, uint32_t sequence, bool resetOnly, uint32_t clearDelay) {
    if (!resetOnly)
        p[2] = sequence;
    if (!sequence)
        return;
    p[4] = 0;
    const uint32_t record = firstRecord(r, sequence);
    if (bad(r))
        return;
    p[3] = record;
    auto *rec = span(r, record, 12);
    if (!rec)
        return;
    if (!resetOnly || clearDelay)
        p[5] = 0;
    p[7] = 0;
    p[8] = p[9] = rec[7];
    p[10] = 0x3f800000;
}
ClawAnimationState state(uint32_t *p) {
    ClawAnimationState s{};
    s.recordIndex = int32_t(p[4]);
    s.remaining = p[5];
    s.timed = p[6];
    s.stopped = p[7];
    s.code = p[8];
    s.previousCode = p[9];
    std::memcpy(&s.rate, p + 10, 4);
    s.hasSequence = bool(p[2]);
    return s;
}
void putState(uint32_t *p, const ClawAnimationState &s, const std::vector<uint32_t> &pointers) {
    p[4] = uint32_t(s.recordIndex);
    p[3] = s.recordIndex >= 0 && uint32_t(s.recordIndex) < pointers.size() ? pointers[uint32_t(s.recordIndex)] : 0;
    p[5] = s.remaining;
    p[6] = s.timed;
    p[7] = s.stopped;
    p[8] = s.code;
    p[9] = s.previousCode;
    std::memcpy(p + 10, &s.rate, 4);
}
ClawAnimationActor actor(uint32_t *a) {
    return {a[0x16c / 4], a[0x174 / 4], a[0x40 / 4], a[0x4c / 4], a[0x50 / 4], a[0x10 / 4], a[0x14 / 4]};
}
void putActor(uint32_t *a, const ClawAnimationActor &out) {
    a[0x16c / 4] = out.imageID;
    a[0x174 / 4] = out.imageToken;
    a[0x40 / 4] = out.flags;
    a[0x4c / 4] = out.x;
    a[0x50 / 4] = out.y;
    a[0x10 / 4] = out.moveX;
    a[0x14 / 4] = out.moveY;
}
uint32_t update(Run &r, uint32_t *p, uint32_t delta) {
    const ClawAnimationState before = state(p);
    uint32_t ready = 0;
    const uint32_t prefix = claw_animation_delay(p, delta, &ready);
    if (!ready)
        return prefix;
    if (p[7])
        return p[8];
    auto *seq = span(r, p[2], 5);
    if (!seq)
        return 0;
    const int32_t count = int32_t(seq[4]);
    if (count <= 0 || count > 10000 || before.recordIndex < 0 || before.recordIndex >= count) {
        fail(r, 2);
        return 0;
    }
    auto *table = span(r, seq[3], uint32_t(count));
    if (!table)
        return 0;
    std::vector<uint32_t> pointers(table, table + count);
    if (p[3] != pointers[uint32_t(before.recordIndex)]) {
        fail(r, 2);
        return 0;
    }
    std::vector<ClawAnimationRecord> records;
    std::vector<uint32_t> rawRecords;
    records.reserve(size_t(count));
    rawRecords.reserve(size_t(count) * 12);
    for (auto token : pointers) {
        auto *rec = span(r, token, 12);
        if (!rec)
            return 0;
        records.push_back({rec[1] & 0xffff, rec[2], rec[3], rec[4], rec[5], rec[6], rec[7], rec[8], rec[9], rec[11]});
        rawRecords.insert(rawRecords.end(), rec, rec + 12);
    }
    auto *a = span(r, p[1], 128);
    if (!a)
        return 0;
    std::vector<uint32_t> images;
    uint32_t *imageManager = nullptr;
    uint32_t *imageTable = nullptr;
    uint32_t savedManager[27]{};
    int32_t first = 0, last = -1;
    if (a[0x170 / 4]) {
        auto *manager = span(r, a[0x170 / 4], 27);
        if (!manager)
            return 0;
        first = int32_t(manager[25]);
        last = int32_t(manager[26]);
        if (first < 0 || last < first || last > 1000000) {
            fail(r, 2);
            return 0;
        }
        auto *values = span(r, manager[5], uint32_t(last) + 1);
        if (!values)
            return 0;
        images.assign(values, values + last + 1);
        imageManager = manager;
        imageTable = values;
        std::copy_n(manager, 27, savedManager);
    } else if ((records[size_t(before.recordIndex)].controlCommand & 0xffff) >= 2 &&
               (records[size_t(before.recordIndex)].controlCommand & 0xffff) <= 5) {
        fail(r, 2);
        return 0;
    }
    auto next = before;
    auto nextActor = actor(a);
    ClawAnimationEvent event{};
    const uint32_t result =
        claw_animation_update(&next, &nextActor, records.data(), uint32_t(count),
                              images.empty() ? nullptr : images.data(), first, last, delta, r.g->audioPosition, &event);
    // Frozen engine computes a complete update on shadows. Commit only actor
    // image/movement before the external sound call; original delay prefix is
    // already visible. Timer/control/record stores commit after the sound call.
    putActor(a, nextActor);
    if (event.dispatched) {
        uint32_t savedActor[128], savedState[11], savedSequence[5];
        std::copy_n(a, 128, savedActor);
        std::copy_n(p, 11, savedState);
        std::copy_n(seq, 5, savedSequence);
        if (!r.h.call) {
            fail(r);
            return 0;
        }
        r.h.call(r.h.context, {event.spatial ? 0x4c88e0u : 0x4208e0u, event.event, {event.position, 0, 0, 0}, 4});
        if (std::memcmp(a, savedActor, sizeof savedActor) || std::memcmp(p, savedState, sizeof savedState) ||
            std::memcmp(seq, savedSequence, sizeof savedSequence)) {
            fail(r, 3);
            return 0;
        }
        if (std::memcmp(table, pointers.data(), pointers.size() * 4) ||
            (imageManager && (std::memcmp(imageManager, savedManager, sizeof savedManager) ||
                              std::memcmp(imageTable, images.data(), images.size() * 4)))) {
            fail(r, 3);
            return 0;
        }
        for (size_t n = 0; n < pointers.size(); ++n) {
            auto *rec = span(r, pointers[n], 12);
            if (!rec)
                return 0;
            if (std::memcmp(rec, rawRecords.data() + n * 12, 48)) {
                fail(r, 3);
                return 0;
            }
        }
    }
    putState(p, next, pointers);
    return result;
}
} // namespace
uint32_t claw_actor_animation_entry(uint32_t f, uint32_t receiver, uint32_t a, uint32_t b,
                                    ClawActorAnimationGlobals *globals, ClawSceneActorHost host, uint32_t *fault,
                                    uint32_t *result) {
    if (!globals) {
        if (fault)
            *fault = 1;
        return 0;
    }
    Run r{globals, host, fault};
    uint32_t value = 0;
    uint32_t *p = nullptr;
    switch (f) {
    case 0x4c8210:
        p = span(r, receiver, 4);
        if (p)
            p[1] = p[2] = p[3] = 0;
        break;
    case 0x4c8220:
        p = span(r, receiver, 11);
        if (p)
            select(r, p, a, false, 1);
        break;
    case 0x4c8260:
        p = span(r, receiver, 11);
        if (p)
            select(r, p, p[2], true, a);
        break;
    case 0x4c82a0:
        p = span(r, receiver, 11);
        if (p)
            value = update(r, p, a);
        break;
    case 0x420970: {
        p = span(r, receiver, 11);
        if (!p)
            break;
        p[4] = a;
        auto *seq = span(r, p[2], 5);
        if (!seq)
            break;
        uint32_t record = 0;
        if (int32_t(a) >= 0 && int32_t(a) < int32_t(seq[4])) {
            auto *item = span(r, seq[3] + a * 4, 1);
            if (!item)
                break;
            record = *item;
        }
        p[3] = record;
        if (!record) {
            p[4] = 0;
            if (int32_t(seq[4]) > 0) {
                auto *item = span(r, seq[3], 1);
                if (!item)
                    break;
                record = *item;
            }
            p[3] = record;
        }
        if (record) {
            auto *rec = span(r, record, 8);
            if (!rec)
                break;
            p[7] = 0;
            p[5] = 0;
            p[9] = p[8];
            value = rec[7];
            p[8] = value;
        }
        break;
    }

    case 0x4c79e0:
    case 0x4c7a40: {
        p = span(r, receiver, 128);
        if (!p)
            break;
        auto *scene = span(r, p[3], 12);
        if (!scene)
            break;
        const uint32_t registry = scene[(f == 0x4c79e0 ? 0x2c : 0x28) / 4] + 16;
        const uint32_t token = invoke(r, 0x4f6286, registry, a);
        if (bad(r) || !token)
            break;
        if (f == 0x4c7a40)
            p[0x184 / 4] = token;
        else {
            select(r, p + 0x188 / 4, token, false, 1);
            if (!bad(r) && b)
                update(r, p + 0x188 / 4, globals->animationDelta);
        }
        value = 1;
        break;
    }
    case 0x420a10:
        p = span(r, receiver, 128);
        if (p) {
            select(r, p + 0x188 / 4, a, false, 1);
            if (!bad(r) && b)
                update(r, p + 0x188 / 4, globals->animationDelta);
        }
        break;
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
