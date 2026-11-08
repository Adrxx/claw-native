#include "SaveLoadRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include "CheckpointLogicRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Run {
    ClawSaveLoadContext *c;
    ClawSaveLoadDependency d;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n = 1) {
    if (bad(r))
        return nullptr;
    auto &h = r.c->save.scene;
    auto *p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint8_t *bytes(Run &r, uint32_t t, uint32_t n = 1) {
    if (bad(r))
        return nullptr;
    auto *p = r.c->save.lookupBytes ? r.c->save.lookupBytes(r.c->save.scene.context, t, n)
                                    : reinterpret_cast<uint8_t *>(span(r, t, (n + 3) / 4));
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = span(r, t);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    auto *p = span(r, t);
    if (p)
        *p = v;
}
uint32_t call(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    if (bad(r))
        return 0;
    if (!f || !r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawSaveLoadCall e{};
    e.function = f;
    e.receiver = t;
    e.argumentCount = uint32_t(a.size());
    std::copy(a.begin(), a.end(), e.arguments);
    return r.d(r.c, &e, r.user);
}
bool step(Run &r, uint32_t &n) {
    if (n++ >= (r.c->maximumTraversal ? r.c->maximumTraversal : 65536)) {
        r.c->fault = 4;
        return false;
    }
    return !bad(r);
}
uint32_t alloc(Run &r, uint32_t n) {
    auto &h = r.c->save.scene;
    if (bad(r))
        return 0;
    if (!h.allocate) {
        r.c->fault = 1;
        return 0;
    }
    return h.allocate(h.context, n);
}
void free(Run &r, uint32_t t) {
    auto &h = r.c->save.scene;
    if (bad(r))
        return;
    if (h.free)
        h.free(h.context, t);
    else
        r.c->fault = 1;
}
uint32_t bridgeSave(ClawSaveFileContext *c, const ClawSaveFileCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.d) {
        c->fault = r.c->fault = 1;
        return 0;
    }
    uint32_t v = r.d(r.c, e, r.user);
    if (r.c->fault)
        c->fault = r.c->fault;
    return v;
}
uint32_t bridgeList(ClawAmbientAudioBackendContext *c, const ClawAmbientAudioBackendCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    ClawSaveLoadCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, q.argumentCount, q.arguments);
    if (!r.d) {
        c->fault = r.c->fault = 1;
        return 0;
    }
    uint32_t v = r.d(r.c, &q, r.user);
    if (r.c->fault)
        c->fault = r.c->fault;
    return v;
}
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *, uint32_t, uint32_t *);
uint32_t invoke(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    if (bad(r))
        return 0;
    uint32_t v = 0;
    if (entry(r, f, t, a.begin(), uint32_t(a.size()), &v))
        return v;
    if (claw_save_file_entry(f, t, a.begin(), uint32_t(a.size()), &r.c->save, bridgeSave, &r, &v))
        return v;
    if (r.c->save.fault) {
        r.c->fault = r.c->save.fault;
        return 0;
    }
    if (f == 0x4f51c5 || f == 0x4f5212 || f == 0x4f5172) {
        ClawAmbientAudioBackendContext c{r.c->save.scene, r.c->maximumTraversal, 0};
        claw_ambient_audio_backend_entry(f, t, a.begin(), uint32_t(a.size()), &c, bridgeList, &r, &v);
        if (c.fault)
            r.c->fault = c.fault;
        return v;
    }
    if (f == 0x49a720) {
        ClawCheckpointGlobals g{};
        ClawCheckpointContext c{};
        c.scene = r.c->save.scene;
        c.globals = &g;
        claw_checkpoint_entry(f, t, a.begin(), uint32_t(a.size()), &c, nullptr, nullptr, &v);
        if (c.fault)
            r.c->fault = c.fault;
        return v;
    }
    return call(r, f, t, a);
}
uint32_t method(Run &r, uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
    const uint32_t f = rd(r, rd(r, t) + slot);
    return bad(r) ? 0 : invoke(r, f, t, a);
}
uint32_t length(Run &r, uint32_t t) {
    uint32_t n = 0;
    while (!bad(r)) {
        if (!step(r, n))
            return 0;
        auto *b = bytes(r, t + n - 1);
        if (!b)
            return 0;
        if (!*b)
            return n - 1;
    }
    return 0;
}
void zero(Run &r, uint32_t t, uint32_t n) {
    for (uint32_t i = 0; i < n && !bad(r); ++i)
        wr(r, t + 4 * i, 0);
}
void copy(Run &r, uint32_t to, uint32_t from, uint32_t n) {
    auto *s = span(r, from, n);
    auto *d = span(r, to, n);
    if (!s || !d)
        return;
    for (uint32_t i = 0; i < n; ++i)
        static_cast<volatile uint32_t *>(d)[i] = static_cast<volatile uint32_t *>(s)[i];
}
void stringCopy(Run &r, uint32_t to, uint32_t from) {
    uint32_t n = length(r, from) + 1;
    uint32_t words = n / 4;
    for (uint32_t i = 0; i < words && !bad(r); ++i) {
        auto *s = bytes(r, from + 4 * i, 4);
        auto *d = bytes(r, to + 4 * i, 4);
        if (!s || !d)
            return;
        uint32_t value = uint32_t(s[0]) | uint32_t(s[1]) << 8 | uint32_t(s[2]) << 16 | uint32_t(s[3]) << 24;
        for (uint32_t k = 0; k < 4; ++k)
            d[k] = uint8_t(value >> (8 * k));
    }
    for (uint32_t i = words * 4; i < n && !bad(r); ++i) {
        auto *s = bytes(r, from + i);
        auto *d = bytes(r, to + i);
        if (s && d)
            *d = *s;
    }
}
void bindings(Run &r, uint32_t t, bool key) {
    static const uint32_t keys[17] = {0, 0x25, 0x27, 0x26, 0x28, 0x20, 0x11, 0x12, 0x10,
                                      0, 0x5a, 0x31, 0x32, 0x33, 0x34, 0,    0};
    static const uint32_t bits[17] = {0, 0, 0, 0, 0, 1, 2, 4, 8, 0, 0x10, 0x20, 0x40, 0x80, 0, 0, 0};
    const auto *values = key ? keys : bits;
    const uint32_t offset = key ? 0x25c0 : 0x2604;
    for (uint32_t i = 0; i < 17; ++i)
        wr(r, t + offset + 4 * i, values[i]);
}
uint32_t initializeRecord(Run &r, uint32_t t, const uint32_t *a) {
    if (!a[0])
        return 0;
    const uint32_t n = length(r, a[0]);
    if (bad(r) || n >= 32)
        return 0;
    if (a[1] && length(r, a[0]) >= 80)
        return 0;
    if (a[2] && length(r, a[0]) >= 80)
        return 0;
    zero(r, t + 4, 0x991);
    bindings(r, t, false);
    bindings(r, t, true);
    stringCopy(r, t + 0x14, a[0]);
    if (a[1])
        stringCopy(r, t + 0x36, a[1]);
    if (a[2])
        stringCopy(r, t + 0x88, a[2]);
    if (a[3] & 4)
        wr(r, t + 4, rd(r, t + 4) | 4);
    wr(r, t + 8, 1);
    return !bad(r);
}
uint32_t score(Run &r, uint32_t t) {
    if (!t)
        return 0;
    static const uint32_t weights[10] = {100, 500, 1500, 2500, 5000, 7500, 10000, 15000, 25000, 0};
    uint32_t sum = 0;
    for (uint32_t i = 0; i < 10; ++i)
        sum += rd(r, t + 0x1c + 4 * i) * weights[i];
    return sum == rd(r, t + 4);
}
uint32_t validate(Run &r, uint32_t t) {
    if (rd(r, t + 8) != 1 || bad(r))
        return 0;
    for (uint32_t i = 0; i < 15 && !bad(r); ++i) {
        if (!score(r, t + 0x21c4 + i * 0x44) || !score(r, t + 0x1780 + i * 0xb0) || !score(r, t + 0x17c4 + i * 0xb0)) {
            invoke(r, 0x49a720, t);
            return 0;
        }
    }
    return !bad(r);
}
uint32_t loadRecord(Run &r, uint32_t t, uint32_t data) {
    if (!data)
        return 0;
    uint32_t n = length(r, data + 0x10);
    if (bad(r) || !n || n >= 32)
        return 0;
    copy(r, t + 4, data, 0x991);
    validate(r, t);
    return !bad(r);
}
uint32_t find(Run &r, uint32_t t, uint32_t name) {
    if (!name)
        return 0;
    uint32_t node = rd(r, t + 4), n = 0;
    while (node && !bad(r)) {
        if (!step(r, n))
            return 0;
        const uint32_t next = rd(r, node), data = rd(r, node + 8);
        if (data + 0x14 && !call(r, 0x4a3cf0, 0, {data + 0x14, name}))
            return data;
        node = next;
    }
    return 0;
}
uint32_t create(Run &r, uint32_t t, const uint32_t *a, bool raw) {
    if (!a[0])
        return 0;
    if (find(r, t, a[0] + (raw ? 0x10 : 0)) || bad(r))
        return 0;
    uint32_t record = alloc(r, 0x2648);
    if (record) {
        wr(r, record, 0x50feac);
        zero(r, record + 4, 0x991);
    }
    uint32_t ok = raw ? loadRecord(r, record, a[0]) : initializeRecord(r, record, a);
    if (bad(r))
        return 0;
    if (!ok) {
        if (record)
            method(r, record, 4, {1});
        return 0;
    }
    invoke(r, 0x4f51c5, t, {record});
    return record;
}
void clear(Run &r, uint32_t t) {
    uint32_t node = rd(r, t + 4), n = 0;
    while (node && !bad(r)) {
        if (!step(r, n))
            return;
        uint32_t next = rd(r, node), data = rd(r, node + 8);
        if (data)
            method(r, data, 4, {1});
        node = next;
    }
    invoke(r, 0x4f5172, t);
}
uint32_t readFile(Run &r, uint32_t t, uint32_t data, uint32_t size) {
    if (!size)
        return 0;
    wr(r, r.c->save.countScratchToken, size);
    uint32_t ok = call(r, 0x546afc, 0, {rd(r, t + 4), data, size, r.c->save.countScratchToken, 0});
    if (!ok && !bad(r)) {
        const uint32_t e = call(r, 0x546b0c, 0);
        call(r, 0x4fc242, 0, {e, 0});
    }
    return rd(r, r.c->save.countScratchToken);
}
uint32_t seek(Run &r, uint32_t t, uint32_t distance, uint32_t origin) {
    uint32_t v = call(r, 0x546af4, 0, {rd(r, t + 4), distance, 0, origin});
    if (v == 0xffffffff && !bad(r)) {
        const uint32_t e = call(r, 0x546b0c, 0);
        call(r, 0x4fc242, 0, {e, 0});
    }
    return v;
}
uint32_t size(Run &r, uint32_t t) {
    const uint32_t pos = method(r, t, 0x30, {0, 1}), result = method(r, t, 0x30, {0, 2});
    method(r, t, 0x30, {pos, 0});
    return result;
}
uint32_t load(Run &r, uint32_t t) {
    uint32_t file = r.c->save.fileScratchToken;
    invoke(r, 0x4f72c9, file);
    if (!invoke(r, 0x4f7448, file, {rd(r, t + 0x1c), 0, 0})) {
        if (!bad(r))
            invoke(r, 0x4f7369, file);
        return 0;
    }
    uint32_t total = size(r, file);
    if (bad(r))
        return 0;
    if (total <= 32) {
        invoke(r, 0x4f7369, file);
        return 0;
    }
    if (!readFile(r, file, t + 0x20, 32)) {
        if (!bad(r))
            invoke(r, 0x4f7369, file);
        return 0;
    }
    invoke(r, 0x49c070, t, {t + 0x20, 32});
    uint32_t amount = total - 32, buffer = alloc(r, amount);
    if (bad(r))
        return 0;
    if (!buffer) {
        invoke(r, 0x4f7369, file);
        return 0;
    }
    bool success = false;
    uint32_t count = 0;
    if (readFile(r, file, buffer, amount)) {
        invoke(r, 0x49c070, t, {buffer, amount});
        uint32_t sum = invoke(r, 0x49bf70, t, {buffer, amount});
        if (!bad(r) && sum == rd(r, t + 0x24) && amount % 0x2644 == 0) {
            count = amount / 0x2644;
            const uint32_t declared = rd(r, t + 0x2c);
            if (declared < count)
                count = declared;
            success = true;
            if (int32_t(count) > 0) {
                uint32_t n = 0;
                for (uint32_t i = 0; i < count && !bad(r); ++i) {
                    if (!step(r, n))
                        return 0;
                    const uint32_t a[] = {buffer + i * 0x2644};
                    if (!create(r, t, a, true)) {
                        success = false;
                        break;
                    }
                }
            }
        }
    }
    if (bad(r))
        return 0;
    free(r, buffer);
    if (success && rd(r, t + 0x28) != rd(r, t + 0x40))
        wr(r, t + 0x28, rd(r, t + 0x40));
    invoke(r, 0x4f7369, file);
    return success ? count : 0;
}
uint32_t startup(Run &r, uint32_t t, uint32_t name) {
    invoke(r, 0x4f650f, t + 0x1c);
    const uint32_t dir = r.c->directoryScratchToken;
    auto *b = bytes(r, dir);
    if (b)
        *b = 0;
    uint32_t result = call(r, 0x546a28, 0, {254, dir});
    if (result)
        call(r, 0x4f4f58, 0, {t + 0x1c, 0x525f78, dir, name});
    b = bytes(r, dir + 3);
    if (b)
        *b = 0;
    if (call(r, 0x546a2c, 0, {dir}) == 5)
        invoke(r, 0x4f650f, t + 0x1c);
    if (!rd(r, rd(r, t + 0x1c) - 8) && !bad(r)) {
        result = call(r, 0x546a10, 0, {dir, 254});
        if (result)
            call(r, 0x4f4f58, 0, {t + 0x1c, 0x525f78, dir, name});
    }
    if (!rd(r, rd(r, t + 0x1c) - 8) || bad(r))
        return 0;
    zero(r, t + 0x20, 8);
    uint32_t loaded = load(r, t);
    if (bad(r))
        return 0;
    if (int32_t(loaded) > 0 && find(r, t, 0x5255e8))
        return 1;
    const uint32_t a[] = {0x5255e8, 0x534938, 0x534938, 0};
    return create(r, t, a, false) != 0;
}
uint32_t entry(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t *out) {
    if (out)
        *out = 0;
    uint32_t want = 0;
    switch (f) {
    case 0x49b840:
    case 0x49be50:
    case 0x49bee0:
    case 0x49bf30:
    case 0x49a6d0:
    case 0x49a990:
    case 0x4d5330:
        want = 1;
        break;
    case 0x49bdb0:
    case 0x49a5a0:
        want = 4;
        break;
    case 0x4f7570:
    case 0x4f75f5:
        want = 2;
        break;
    case 0x49b9a0:
    case 0x49b950:
    case 0x49b970:
    case 0x49a8f0:
    case 0x49ad50:
    case 0x49adc0:
    case 0x423f00:
    case 0x4f774d:
        break;
    default:
        return 0;
    }
    if (want != n || (n && !a)) {
        r.c->fault = 2;
        return 0;
    }
    uint32_t v = 0;
    switch (f) {
    case 0x49b840:
        v = startup(r, t, a[0]);
        break;
    case 0x49b9a0:
        v = load(r, t);
        break;
    case 0x49b950:
        clear(r, t);
        invoke(r, 0x4f650f, t + 0x1c);
        break;
    case 0x49b970:
        clear(r, t);
        break;
    case 0x49bdb0:
        v = create(r, t, a, false);
        break;
    case 0x49be50:
        v = create(r, t, a, true);
        break;
    case 0x49bee0:
        v = find(r, t, a[0]);
        break;
    case 0x49bf30: {
        if (!a[0])
            break;
        uint32_t node = rd(r, t + 4), loops = 0;
        while (node && !bad(r)) {
            if (!step(r, loops))
                break;
            uint32_t next = rd(r, node);
            if (rd(r, node + 8) == a[0]) {
                invoke(r, 0x4f5212, t, {node});
                method(r, a[0], 4, {1});
                break;
            }
            node = next;
        }
        break;
    }
    case 0x49a5a0:
        v = initializeRecord(r, t, a);
        break;
    case 0x49a6d0:
        v = loadRecord(r, t, a[0]);
        break;
    case 0x49a8f0:
        v = validate(r, t);
        break;
    case 0x49ad50:
        bindings(r, t, false);
        break;
    case 0x49adc0:
        bindings(r, t, true);
        break;
    case 0x49a990:
        v = score(r, a[0]);
        break;
    case 0x423f00:
        wr(r, t, 0x50becc);
        break;
    case 0x4d5330:
        wr(r, t, 0x50becc);
        if (a[0] & 1)
            free(r, t);
        v = t;
        break;
    case 0x4f7570:
        v = readFile(r, t, a[0], a[1]);
        break;
    case 0x4f75f5:
        v = seek(r, t, a[0], a[1]);
        break;
    case 0x4f774d:
        v = size(r, t);
        break;
    }
    if (out)
        *out = v;
    return 1;
}
} // namespace
uint32_t claw_save_load_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawSaveLoadContext *c,
                              ClawSaveLoadDependency d, void *u, uint32_t *out) {
    if (out)
        *out = 0;
    if (!c)
        return 0;
    c->fault = 0;
    c->save.fault = 0;
    Run r{c, d, u};
    return entry(r, f, t, a, n, out) && !bad(r);
}
