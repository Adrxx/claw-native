#include "InterfaceFileRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <vector>
namespace {
struct Failure {};
struct Run {
    ClawInterfaceFileContext &c;
    ClawInterfaceFileDependency dependency;
    void *user;
    uint32_t operations = 0;
    void fail(uint32_t code) {
        c.fault = code;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        step();
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail(1);
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint8_t byte(uint32_t t) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3u];
    }
    void byte(uint32_t t, uint8_t v) {
        reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3u] = v;
    }
    static int32_t si(uint32_t v) {
        int32_t n;
        std::memcpy(&n, &v, 4);
        return n;
    }
    uint32_t scalar(uint32_t t, unsigned n) {
        uint32_t v = 0;
        for (unsigned i = 0; i < n; ++i)
            v |= uint32_t(byte(t + i)) << (8 * i);
        return v;
    }
    void copy(uint32_t dst, uint32_t src, uint32_t count) {
        std::vector<uint8_t> b(count);
        for (uint32_t i = 0; i < count; ++i)
            b[i] = byte(src + i);
        for (uint32_t i = 0; i < count; ++i)
            byte(dst + i, b[i]);
    }
    uint32_t localSize(uint32_t t) {
        if (t >= c.memoryFileToken && t < c.memoryFileToken + 40)
            return t == c.memoryFileToken ? 40 : 4;
        if (t >= c.archiveToken && t < c.archiveToken + 68)
            return t == c.archiveToken ? 68 : 4;
        if (t == c.stringScratchToken)
            return 4;
        return 0;
    }
    uint32_t service(ClawInterfaceFileCall &q) {
        step();
        if (!dependency)
            fail(1);
        auto value = dependency(&c, &q, user);
        if (c.fault)
            throw Failure{};
        return value;
    }
    uint32_t external(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawInterfaceFileCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        if (n > 10)
            fail(3);
        std::copy_n(a, n, q.arguments);
        auto add = [&](uint32_t token, uint32_t bit) {
            uint32_t bytes = localSize(token);
            if (!bytes)
                return false;
            if (q.bufferCount == 3)
                fail(3);
            q.localMask |= bit;
            q.buffers[q.bufferCount] = span(token, (bytes + 3) / 4);
            q.bufferBytes[q.bufferCount++] = bytes;
            return true;
        };
        if (add(t, 256))
            q.receiver = 0;
        for (uint32_t i = 0; i < n; ++i)
            if (add(a[i], 1u << i))
                q.arguments[i] = 0;
        return service(q);
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[10]{};
        std::copy(a.begin(), a.end(), args);
        if (owned(f))
            return entry(f, t, args, uint32_t(a.size()));
        return external(f, t, args, uint32_t(a.size()));
    }
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return invoke(get(get(t) + slot), t, a);
    }
    uint32_t allocate(uint32_t n) {
        return invoke(0x4f63ec, 0, {n});
    }
    void free(uint32_t t) {
        invoke(0x4f6428, 0, {t});
    }
    uint32_t empty() {
        return get(0x52e1cc);
    }
    void stringCtor(uint32_t t) {
        put(t, empty());
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static void release(void *u, uint32_t t) {
        static_cast<Run *>(u)->free(t);
    }
    static uint32_t callback(void *u, ClawSceneActorCall q) {
        auto &r = *static_cast<Run *>(u);
        return r.external(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    ClawSceneActorHost host() {
        return {this, lookup, nullptr, release, callback, nullptr};
    }
    void stringDestroy(uint32_t t) {
        ClawActorDestructionGlobals g{};
        if (c.destruction)
            g = *c.destruction;
        else
            g.emptyStringToken = get(0x52e1c8) + 12;
        uint32_t fault = 0, out = 0;
        if (!claw_actor_destruction_entry(0x4f6584, t, 0, &g, host(), &fault, &out) || fault)
            fail(fault ? fault : 1);
    }
    void stringRelease(uint32_t t) {
        if (get(t) - 12 == get(0x52e1c8))
            return;
        stringDestroy(t);
        put(t, empty());
    }
    void stringAllocate(uint32_t t, uint32_t n) {
        uint32_t data = empty();
        if (n) {
            auto p = allocate(n + 13);
            put(p, 1);
            byte(p + n + 12, 0);
            put(p + 4, n);
            put(p + 8, n);
            data = p + 12;
        }
        put(t, data);
    }
    void stringCopy(uint32_t t, uint32_t source) {
        uint32_t data = get(source);
        if (si(get(data - 12)) >= 0) {
            put(t, data);
            put(data - 12, get(data - 12) + 1);
        } else {
            stringCtor(t);
            auto n = get(data - 8);
            stringRelease(t);
            stringAllocate(t, n);
            copy(get(t), data, n);
        }
    }
    void stringAssign(uint32_t t, uint32_t source) {
        if (get(t) == get(source))
            return;
        uint32_t data = get(source), old = get(t) - 12;
        if ((si(get(old)) < 0 && old != get(0x52e1c8)) || si(get(data - 12)) < 0) {
            auto n = get(data - 8);
            stringRelease(t);
            stringAllocate(t, n);
            copy(get(t), data, n);
            return;
        }
        stringRelease(t);
        data = get(source);
        put(t, data);
        put(data - 12, get(data - 12) + 1);
    }
    void literal(uint32_t t, uint32_t text) {
        stringCtor(t);
        if (!text)
            return;
        if ((text >> 16) == 0) {
            invoke(0x4fb253, t, {text});
            return;
        }
        uint32_t n = 0;
        while (byte(text + n))
            ++n;
        if (n) {
            stringAllocate(t, n);
            copy(get(t), text, n);
        }
    }
    uint32_t stringBuffer(uint32_t t, uint32_t n) {
        uint32_t old = get(t);
        if (si(get(old - 12)) > 1 || si(get(old - 4)) < si(n)) {
            auto length = get(old - 8);
            if (si(n) < si(length))
                n = length;
            stringAllocate(t, n);
            copy(get(t), old, length + 1);
            put(get(t) - 8, length);
            if (old - 12 != get(0x52e1c8)) {
                put(old - 12, get(old - 12) - 1);
                if (si(get(old - 12)) <= 0)
                    free(old - 12);
            }
        }
        return get(t);
    }
    uint32_t stringLength(uint32_t t, uint32_t n) {
        stringBuffer(t, n);
        put(get(t) - 8, n);
        byte(get(t) + n, 0);
        return get(t);
    }
    static uint32_t arrayService(ClawCArrayContext *, const ClawCArrayCall *q, void *u) {
        return static_cast<Run *>(u)->external(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    void resize(uint32_t t, uint32_t n, uint32_t grow = 0xffffffff) {
        ClawCArrayContext x{};
        if (c.arrays)
            x = *c.arrays;
        x.scene = host();
        x.fault = 0;
        uint32_t out = 0;
        claw_carray_entry(0x4f5915, t, n, grow, 0, &x, arrayService, this, &out);
        if (x.fault)
            fail(x.fault);
    }
    void append(uint32_t t, uint32_t value) {
        auto n = get(t + 8);
        resize(t, n + 1);
        put(get(t + 4) + n * 4, value);
    }
    // Memory-file profiles compose actual borrowed GetBufferPtr/read/seek bodies.
    uint32_t memRead(uint32_t t, uint32_t dst, uint32_t count) {
        uint32_t pos = get(t + 20), length = get(t + 28);
        if (!count || pos > length)
            return 0;
        if (length < pos + count)
            count = length - pos;
        copy(dst, get(t + 32) + pos, count);
        put(t + 20, get(t + 20) + count);
        return count;
    }
    uint32_t memSeek(uint32_t t, uint32_t offset, uint32_t whence) {
        uint32_t pos = get(t + 20);
        if (whence) {
            if (whence == 2)
                pos = get(t + 28);
            else if (whence != 1)
                return 0xffffffff;
            offset += pos;
        }
        if (si(offset) < 0) {
            invoke(0x4fc303, 0);
            fail(2);
        }
        put(t + 20, offset);
        return offset;
    }
    uint32_t buffer(uint32_t t, const uint32_t *a) {
        if (a[0] == 3)
            return 1;
        if (a[0] == 2) {
            put(t + 20, get(t + 20) + a[1]);
            if (get(t + 28) < get(t + 20))
                put(t + 28, get(t + 20));
            return 0;
        }
        if (a[0] == 1 && get(t + 24) < get(t + 20) + a[1])
            virt(t, 108, {get(t + 20) + a[1]});
        put(a[2], get(t + 32) + get(t + 20));
        uint32_t end;
        if (a[0] == 1)
            end = std::min(get(t + 20) + a[1], get(t + 24));
        else {
            uint32_t count = a[1] == 0xffffffff ? get(t + 24) - get(t + 20) : a[1];
            end = std::min(get(t + 20) + count, get(t + 28));
        }
        put(a[3], get(t + 32) + end);
        if (a[0] != 1)
            put(t + 20, get(t + 20) + (get(a[3]) - get(a[2])));
        return get(a[3]) - get(a[2]);
    }
    void eof() {
        invoke(0x4fe675, 0, {3, 0});
        fail(2);
    }
    void fill(uint32_t ar, uint32_t needed) {
        uint32_t left = get(ar + 40) - get(ar + 36), required = needed + left, file = get(ar + 32);
        if (get(ar + 8)) {
            if (left)
                virt(file, 48, {0 - left, 1});
            virt(file, 88, {0, get(ar + 28), ar + 44, ar + 40});
            put(ar + 36, get(ar + 44));
        } else {
            uint32_t begin = get(ar + 44), current = get(ar + 36);
            if (begin < current) {
                if (si(left) > 0) {
                    copy(begin, current, left);
                    put(ar + 36, begin);
                    put(ar + 40, begin + left);
                }
                uint32_t remaining = get(ar + 28) - left, dst = begin + left;
                do {
                    auto n = virt(file, 60, {dst, remaining});
                    left += n;
                    dst += n;
                    remaining -= n;
                    if (!n || !remaining)
                        break;
                } while (left < needed);
                put(ar + 36, get(ar + 44));
                put(ar + 40, get(ar + 44) + left);
            }
        }
        if (get(ar + 40) - get(ar + 36) < required)
            eof();
    }
    uint32_t readScalar(uint32_t ar, uint32_t count) {
        uint32_t cur = get(ar + 36), end = get(ar + 40);
        if (end < cur + count)
            fill(ar, cur - end + count);
        cur = get(ar + 36);
        auto v = scalar(cur, count);
        put(ar + 36, cur + count);
        return v;
    }
    uint32_t archiveRead(uint32_t ar, uint32_t dst, uint32_t count) {
        if (!count)
            return 0;
        uint32_t have = std::min(count, get(ar + 40) - get(ar + 36));
        copy(dst, get(ar + 36), have);
        put(ar + 36, get(ar + 36) + have);
        dst += have;
        uint32_t missing = count - have;
        if (missing) {
            uint32_t block = get(ar + 28);
            if (!block)
                fail(2);
            uint32_t aligned = missing - missing % block, total = 0, remain = aligned;
            do {
                auto n = virt(get(ar + 32), 60, {dst, remain});
                dst += n;
                total += n;
                remain -= n;
                if (!n)
                    break;
            } while (remain);
            missing -= total;
            if (total == aligned) {
                uint32_t obtained = 0;
                if (!get(ar + 8)) {
                    uint32_t readCount = std::max(missing, get(ar + 28)), target = get(ar + 44);
                    do {
                        auto n = virt(get(ar + 32), 60, {target, readCount});
                        target += n;
                        readCount -= n;
                        obtained += n;
                        if (!n || !readCount)
                            break;
                    } while (obtained < missing);
                    put(ar + 36, get(ar + 44));
                    put(ar + 40, get(ar + 44) + obtained);
                } else {
                    virt(get(ar + 32), 88, {0, get(ar + 28), ar + 44, ar + 40});
                    put(ar + 36, get(ar + 44));
                }
                have = std::min(missing, get(ar + 40) - get(ar + 36));
                copy(dst, get(ar + 36), have);
                put(ar + 36, get(ar + 36) + have);
                missing -= have;
            }
        }
        return count - missing;
    }
    uint32_t encodedLength(uint32_t ar) {
        uint32_t n = readScalar(ar, 1);
        if (n != 255)
            return n;
        n = readScalar(ar, 2);
        if (n == 65534)
            return 0xffffffff;
        return n == 65535 ? readScalar(ar, 4) : n;
    }
    void readString(uint32_t ar, uint32_t field) {
        uint32_t n = encodedLength(ar);
        bool wide = n == 0xffffffff;
        if (wide)
            n = encodedLength(ar);
        uint32_t bytes = n * (wide ? 2 : 1), length = n ? bytes + (wide ? 1 : 0) : 0;
        stringLength(field, length);
        if (n) {
            if (archiveRead(ar, get(field), bytes) != bytes)
                eof();
            if (wide) {
                uint32_t p = get(field);
                byte(p + n * 2, 0);
                byte(p + n * 2 + 1, 0);
                put(field, empty());
                invoke(0x4f66f3, field, {p});
                free(p - 12);
            }
        }
    }
    void archiveCtor(uint32_t ar, const uint32_t *a) {
        virt(a[0], 32, {ar + 16});
        put(ar + 12, 0xffffffff);
        put(ar + 20, a[1]);
        put(ar + 32, a[0]);
        put(ar + 56, 0);
        put(ar + 52, 0);
        put(ar, 0);
        put(ar + 4, 1);
        put(ar + 60, a[1] & 1 ? 64 : 16);
        put(ar + 24, 1);
        put(ar + 44, a[3]);
        put(ar + 64, 137);
        put(ar + 8, 0);
        uint32_t size = a[2];
        if (si(size) < 128) {
            size = 128;
            put(ar + 44, 0);
        }
        put(ar + 28, size);
        if (!get(ar + 44)) {
            put(ar + 8, virt(a[0], 88, {3, 0, 0, 0}));
            if (!get(ar + 8)) {
                put(ar + 44, allocate(size));
                put(ar + 24, 0);
            } else
                size = 0;
        }
        uint32_t end = get(ar + 44) + size;
        put(ar + 40, end);
        put(ar + 36, a[1] & 1 ? end : get(ar + 44));
    }
    void archiveClose(uint32_t ar) {
        if (get(ar + 32) && !(get(ar + 20) & 2)) {
            if (get(ar + 20) & 1) {
                uint32_t left = get(ar + 40) - get(ar + 36);
                if (left)
                    virt(get(ar + 32), 48, {0 - left, 1});
                put(ar + 36, get(ar + 40));
            } else {
                invoke(0x4fdd43, ar);
            }
        }
        put(ar + 32, 0);
        if (!get(ar + 24)) {
            free(get(ar + 44));
            put(ar + 44, 0);
            put(ar + 36, 0);
        }
        for (uint32_t off : {56u, 52u}) {
            uint32_t p = get(ar + off);
            if (p)
                virt(p, 4, {1});
            put(ar + off, 0);
        }
        stringDestroy(ar + 16);
    }
    void componentCtor(uint32_t t) {
        put(t, 0x513ec0);
        for (uint32_t off : {4u, 16u, 12u, 8u})
            put(t + off, 0);
        for (uint32_t off = 24; off <= 52; off += 4)
            stringCtor(t + off);
        for (uint32_t off : {84u, 88u, 60u, 20u, 56u, 76u, 80u})
            put(t + off, 0);
        put(t + 68, 1);
        put(t + 100, 1);
        put(t + 104, 300);
    }
    void controllerBase(uint32_t t) {
        put(t + 8, 0x513ea8);
        for (uint32_t off : {12u, 24u, 20u, 16u, 4u, 28u, 36u, 32u})
            put(t + off, 0);
        put(t, 0x513e88);
        put(t + 52, 400);
        put(t + 40, 0xffffffff);
    }
    uint32_t nodeCtor(uint32_t t) {
        stringCtor(t + 12);
        stringCtor(t + 20);
        put(t + 24, 0x513ee8);
        for (uint32_t off : {28u, 40u, 36u, 32u})
            put(t + off, 0);
        componentCtor(t + 60);
        put(t, 0x513ed8);
        put(t + 44, 0);
        literal(c.stringScratchToken, 0x5334f0);
        stringAssign(t + 20, c.stringScratchToken);
        stringDestroy(c.stringScratchToken);
        put(t + 56, 9);
        put(t + 52, allocate(36));
        for (uint32_t off : {4u, 172u, 16u, 8u})
            put(t + off, 0);
        return t;
    }
    uint32_t child(uint32_t t, uint32_t kind) {
        if (kind) {
            fail(2);
        }
        uint32_t p = allocate(176);
        if (p)
            nodeCtor(p);
        uint32_t index = get(t + 32);
        resize(t + 24, index + 1);
        put(get(t + 28) + index * 4, p);
        put(p + 16, t);
        return p;
    }
    void serializeComponent(uint32_t t, uint32_t ar) {
        if (!(get(ar + 20) & 1)) {
            fail(2);
        }
        for (uint32_t off = 24; off <= 52; off += 4)
            readString(ar, t + off);
        put(t + 20, readScalar(ar, 4));
    }
    void serializeNode(uint32_t t, uint32_t ar) {
        if (!(get(ar + 20) & 1)) {
            fail(2);
        }
        put(t + 44, readScalar(ar, 4));
        readString(ar, t + 20);
        serializeComponent(t + 60, ar);
        int32_t count = static_cast<int16_t>(readScalar(ar, 2));
        uint32_t current = ar;
        for (int32_t i = 0; i < count; ++i) {
            step();
            uint32_t kind = readScalar(ar, 4);
            if (!kind)
                current = child(t, 0);
            virt(current, 8, {ar});
        }
    }
    void setMode(uint32_t t, uint32_t flags) {
        put(t + 68, flags);
        uint32_t index;
        if (flags & 32)
            index = flags & 4 ? (flags & 16 ? 7 : 6) : 5;
        else if (flags & 1)
            index = flags & 4 ? (flags & 16 ? 4 : 3) : 0;
        else if (flags & 2)
            index = flags & 16 ? 2 : 1;
        else
            return;
        put(t + 64, get(get(t + 4) + index * 4));
    }
    uint32_t componentInitialize(uint32_t t, const uint32_t *a) {
        if (!a[0])
            return 0;
        put(t + 72, a[0]);
        put(t + 76, a[2]);
        put(t + 80, a[3]);
        put(t + 60, a[1] ? 0 : 1);
        for (uint32_t off = 24; off <= 52; off += 4) {
            stringCopy(c.stringScratchToken, t + off);
            uint32_t data = get(c.stringScratchToken);
            if (!a[1])
                invoke(0x4de560, t, {data});
            else {
                uint32_t value = invoke(a[1], 0, {data});
                append(t, value);
            }
        }
        uint32_t images = get(t + 4);
        if (!get(images) || !get(images + 12))
            return 0;
        put(t + 56, allocate(get(t + 8) * 4));
        for (uint32_t i = 0; si(i) < si(get(t + 8)); ++i)
            put(get(t + 56) + i * 4, 1);
        auto fallback = [&](uint32_t index, uint32_t from) {
            uint32_t p = get(t + 4);
            if (!get(p + index * 4)) {
                put(p + index * 4, get(p + from * 4));
                put(get(t + 56) + index * 4, 0);
            }
        };
        fallback(1, 3);
        fallback(2, 1);
        fallback(4, 3);
        fallback(5, 0);
        fallback(6, 3);
        fallback(7, 6);
        setMode(t, 1);
        uint32_t width = 0, height = 0;
        for (uint32_t i = 0; si(i) < si(get(t + 8)); ++i) {
            uint32_t p = get(get(t + 4) + i * 4), w = get(p + 24), h = get(p + 20);
            if (si(w) > si(width))
                width = w;
            if (si(h) > si(height))
                height = h;
        }
        put(t + 92, width);
        put(t + 96, height);
        return 1;
    }
    uint32_t initializeNode(uint32_t t, const uint32_t *a) {
        for (uint32_t i = 0; si(i) < si(get(t + 32)); ++i) {
            if (!virt(get(get(t + 28) + i * 4), 0, {a[0], a[1], a[2], a[3], a[4]}))
                return 0;
        }
        put(t + 168, a[0]);
        uint32_t comp[] = {a[0], a[1], 0, 0};
        if (!componentInitialize(t + 60, comp))
            return 0;
        if (a[2]) {
            stringCopy(c.stringScratchToken, t + 20);
            invoke(0x4de830, t + 60, {get(c.stringScratchToken), a[3], a[4]});
        }
        put(t + 4, 1);
        return 1;
    }
    void clearComponent(uint32_t t) {
        if (!get(t + 72))
            return;
        if (get(t + 60)) {
            for (uint32_t i = 0; si(i) < si(get(t + 8)); ++i) {
                uint32_t p = get(get(t + 4) + i * 4);
                if (p) {
                    invoke(0x4bc4f0, get(t + 72), {p});
                    for (uint32_t j = 0; si(j) < si(get(t + 8)); ++j)
                        put(get(t + 4) + j * 4, 0);
                }
            }
        }
        for (uint32_t off : {56u, 4u}) {
            uint32_t p = get(t + off);
            if (p) {
                free(p);
                put(t + off, 0);
            }
        }
        put(t + 12, 0);
        put(t + 8, 0);
    }
    void componentDestroy(uint32_t t) {
        clearComponent(t);
        for (int32_t off = 52; off >= 24; off -= 4)
            stringDestroy(t + uint32_t(off));
        put(t, 0x513ec0);
        uint32_t p = get(t + 4);
        if (p)
            free(p);
        put(t, 0x50becc);
    }
    void clearNode(uint32_t t) {
        clearComponent(t + 60);
        for (uint32_t i = 0; si(i) < si(get(t + 32)); ++i) {
            uint32_t p = get(get(t + 28) + i * 4);
            virt(p, 4);
            p = get(get(t + 28) + i * 4);
            if (p) {
                destroyNode(p);
                free(p);
            }
        }
        if (get(t + 28)) {
            free(get(t + 28));
            put(t + 28, 0);
        }
        put(t + 36, 0);
        put(t + 32, 0);
        if (get(t + 52)) {
            free(get(t + 52));
            put(t + 52, 0);
        }
        put(t + 4, 0);
    }
    void destroyNode(uint32_t t) {
        put(t, 0x513ed8);
        if (get(t + 4))
            clearNode(t);
        componentDestroy(t + 60);
        put(t + 24, 0x513ee8);
        if (get(t + 28))
            free(get(t + 28));
        put(t + 24, 0x50becc);
        stringDestroy(t + 20);
        stringDestroy(t + 12);
    }
    void clearControllerArray(uint32_t t) {
        if (get(t + 12)) {
            free(get(t + 12));
            put(t + 12, 0);
        }
        put(t + 20, 0);
        put(t + 16, 0);
    }
    uint32_t item(uint32_t t, uint32_t index) {
        if (si(index) < 0 || si(index) > si(get(t + 16)) - 1)
            return 0;
        return get(get(t + 12) + index * 4);
    }
    void show(uint32_t t, uint32_t node, uint32_t center) {
        if (!node)
            return;
        put(t + 248, node);
        clearControllerArray(t);
        for (uint32_t i = 0; si(i) < si(get(get(t + 248) + 32)); ++i) {
            uint32_t p = get(get(get(t + 248) + 28) + i * 4);
            append(t + 8, p + 60);
        }
        if (center) {
            int32_t n = si(get(t + 16));
            uint32_t total = 0;
            for (int32_t i = 0; i < n; ++i)
                total += get(item(t, uint32_t(i)) + 96);
            uint32_t y = 0 - 10u * uint32_t(n) - uint32_t(si(total) / 2) + 10 + uint32_t(si(get(t + 64)) / 2);
            for (int32_t i = 0; i < n; ++i) {
                uint32_t p = item(t, uint32_t(i)), x = uint32_t(si(get(t + 60)) / 2 - si(get(p + 92)) / 2);
                put(p + 84, x);
                put(p + 88, y);
                y += 10 + get(p + 96);
            }
        }
    }
    uint32_t tick() {
        return invoke(get(0x546a24), 0);
    }
    void selectPointer(uint32_t t, uint32_t selected) {
        uint32_t index = 0;
        for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i) {
            uint32_t p = item(t, i);
            setMode(p, get(p + 68) & 32 ? 33 : 1);
            if (get(get(t + 12) + i * 4) == selected)
                index = i;
        }
        setMode(selected, get(selected + 68) & 32 ? 53 : 21);
        uint32_t now = tick();
        put(t + 28, index);
        put(t + 48, now);
        virt(t, 16);
    }
    void expire(uint32_t t) {
        if (!get(t + 16))
            return;
        if (get(t + 36)) {
            uint32_t p = item(t, get(t + 28));
            if (!p)
                return;
            uint32_t interval = get(p + 104), now = tick();
            if (interval < now - get(t + 44)) {
                put(t + 36, 0);
                uint32_t flags = get(p + 68);
                if (!(flags & 32))
                    setMode(p, flags & 16 ? 21 : 5);
                put(t + 48, tick());
                virt(t, 24);
            }
        }
        uint32_t now = tick();
        if (!get(t + 36) && get(t + 52) < now - get(t + 48)) {
            uint32_t p = item(t, get(t + 28));
            if (p) {
                uint32_t flags = get(p + 68);
                setMode(p, flags & 16 ? flags - 16 : flags | 16);
                put(t + 48, now);
            }
        }
    }
    void navigate(uint32_t t, bool forward, bool timed) {
        if (timed)
            expire(t);
        if (get(t + 36))
            return;
        uint32_t initial = get(t + 28), index = initial + (forward ? 1 : 0xffffffff);
        auto wrap = [&]() {
            if (forward) {
                if (si(get(t + 16) - 1) < si(index))
                    index = 0;
            } else if (si(index) < 0)
                index = get(t + 16) - 1;
        };
        if (!get(t + 32)) {
            wrap();
            select(t, index);
            return;
        }
        if (index == initial)
            return;
        for (;;) {
            step();
            wrap();
            uint32_t p = item(t, index);
            if (!(get(p + 68) & 32))
                break;
            index += forward ? 1 : 0xffffffff;
            if (index == initial)
                return;
        }
        select(t, index);
    }
    void press(uint32_t t) {
        expire(t);
        if (get(t + 36))
            return;
        uint32_t p = item(t, get(t + 28));
        if (p) {
            uint32_t flags = get(p + 68);
            if (!(flags & 32))
                setMode(p, flags & 16 ? 18 : 2);
            put(t + 36, 1);
            put(t + 40, get(t + 28));
            put(t + 44, tick());
        }
        virt(t, 20);
    }
    void activate(uint32_t t) {
        if (!get(t + 252))
            return;
        uint32_t p = item(t, get(t + 28)), id = get(p + 20);
        if (!(get(p + 68) & 32)) {
            uint32_t childToken = get(get(get(t + 248) + 28) + get(t + 28) * 4);
            if (si(get(childToken + 32)) > 0) {
                show(t, childToken, 1);
                select(t, 0);
            }
        }
        virt(t, 28, {id, (~get(p + 68) >> 5) & 1});
    }
    uint32_t rectangle(uint32_t t, uint32_t dst) {
        uint32_t selected = get(t + 64), width = get(selected + 24), height = get(selected + 20),
                 x = get(t + 84) + uint32_t(si(get(t + 92) - width) / 2),
                 y = get(t + 88) + uint32_t(si(get(t + 96) - height) / 2);
        put(dst + 12, y + height);
        put(dst + 4, y);
        put(dst + 8, x + width);
        put(dst, x);
        return dst;
    }
    void draw(uint32_t t, uint32_t target) {
        if (!get(t + 100))
            return;
        uint32_t selected = get(t + 64), w = get(selected + 24), h = get(selected + 20),
                 x = get(t + 84) + uint32_t(si(get(t + 92) - w) / 2),
                 y = get(t + 88) + uint32_t(si(get(t + 96) - h) / 2), dest[4] = {x, y, x + w, y + h},
                 src[4] = {0, 0, w, h};
        ClawInterfaceFileCall q{};
        q.function = 0x4b9ce0;
        q.receiver = target;
        q.argumentCount = 5;
        q.arguments[1] = selected;
        q.arguments[3] = 0x1008000;
        q.localMask = 5;
        q.bufferCount = 2;
        q.buffers[0] = dest;
        q.buffers[1] = src;
        q.bufferBytes[0] = q.bufferBytes[1] = 16;
        service(q);
    }
    void mouse(uint32_t t) {
        expire(t);
        if (get(t + 36))
            return;
        uint32_t point[2]{};
        ClawInterfaceFileCall q{};
        q.function = get(0x546cd0);
        q.argumentCount = 1;
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = point;
        q.bufferBytes[0] = 8;
        service(q);
        for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i) {
            uint32_t p = get(get(t + 12) + i * 4);
            if (!p)
                continue;
            uint32_t selected = get(p + 64), w = get(selected + 24), h = get(selected + 20),
                     x = get(p + 84) + uint32_t(si(get(p + 92) - w) / 2),
                     y = get(p + 88) + uint32_t(si(get(p + 96) - h) / 2), rect[4] = {x, y, x + w, y + h};
            q = {};
            q.function = get(0x546cd4);
            q.argumentCount = 3;
            q.arguments[1] = point[0];
            q.arguments[2] = point[1];
            q.localMask = 1;
            q.bufferCount = 1;
            q.buffers[0] = rect;
            q.bufferBytes[0] = 16;
            if (service(q)) {
                if (get(t + 32) && (get(p + 68) & 32))
                    return;
                select(t, i);
                press(t);
                return;
            }
        }
    }
    void select(uint32_t t, uint32_t index) {
        if (si(index) < 0 || si(index) > si(get(t + 16)) - 1)
            return;
        for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i) {
            uint32_t p = item(t, i);
            setMode(p, get(p + 68) & 32 ? 33 : 1);
        }
        uint32_t p = item(t, index);
        setMode(p, get(p + 68) & 32 ? 53 : 21);
        put(t + 48, invoke(get(0x546a24), 0));
        put(t + 28, index);
        virt(t, 16);
    }
    uint32_t find(uint32_t t, uint32_t id) {
        if (get(t + 80) == id)
            return t;
        for (uint32_t i = 0; si(i) < si(get(t + 32)); ++i) {
            auto p = find(get(get(t + 28) + i * 4), id);
            if (p)
                return p;
        }
        return 0;
    }
    void replaceImage(uint32_t t, uint32_t value, uint32_t index) {
        if (si(index) < 0 || index >= 8)
            return;
        uint32_t old = get(get(t + 4) + index * 4);
        if (get(t + 60))
            invoke(0x4bc4f0, get(t + 72), {old});
        for (uint32_t i = 0; si(i) < si(get(t + 8)); ++i)
            if (get(get(t + 4) + i * 4) == old)
                put(get(t + 4) + i * 4, value);
        uint32_t w = 0, h = 0;
        for (uint32_t i = 0; si(i) < si(get(t + 8)); ++i) {
            uint32_t p = get(get(t + 4) + i * 4), nw = get(p + 24), nh = get(p + 20);
            if (si(nw) > si(w))
                w = nw;
            if (si(nh) > si(h))
                h = nh;
        }
        put(t + 92, w);
        put(t + 96, h);
    }
    void distribute(uint32_t t, uint32_t axis, uint32_t first, uint32_t last) {
        if (axis > 1)
            return;
        uint32_t count = get(t + 16), offset = 84 + axis * 4, sizeOffset = 92 + axis * 4,
                 min = si(first) < si(last) ? first : last;
        if (count == 1) {
            put(item(t, 0) + offset, min);
            return;
        }
        uint32_t total = 0;
        for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i)
            total += get(item(t, i) + sizeOffset);
        uint32_t max = si(first) > si(last) ? first : last, x = min, div = count - 1, numerator = max - total - min;
        if (!div || (numerator == 0x80000000 && div == 0xffffffff)) {
            if (si(get(t + 16)) > 0)
                fail(2);
            return;
        }
        uint32_t spacing = uint32_t(si(numerator) / si(div));
        for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i) {
            uint32_t p = item(t, i);
            put(p + offset, x);
            x += get(p + sizeOffset) + spacing;
        }
    }
    void back(uint32_t t) {
        uint32_t page = get(t + 248);
        if (!page || !get(page + 16))
            return;
        show(t, get(page + 16), 1);
        for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i)
            if (get(item(t, i) + 68) & 4) {
                select(t, i);
                return;
            }
        select(t, 0);
    }
    void setArgument(uint32_t t, uint32_t a) {
        put(t + 164, a);
        for (uint32_t i = 0; si(i) < si(get(t + 32)); ++i)
            setArgument(get(get(t + 28) + i * 4), a);
    }
    uint32_t loadFile(uint32_t t, const uint32_t *a) {
        put(t + 56, a[0]);
        uint32_t arargs[] = {a[1], 1, 4096, 0};
        archiveCtor(c.archiveToken, arargs);
        virt(t + 72, 8, {c.archiveToken});
        uint32_t result = virt(t + 72, 0, {get(t + 56), a[2], a[3], a[4], a[5]});
        if (!result) {
            archiveClose(c.archiveToken);
            return 0;
        }
        show(t, t + 72, 1);
        select(t, 0);
        put(t + 68, 1);
        archiveClose(c.archiveToken);
        return 1;
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        auto need = [&](uint32_t v) {
            if (n != v || (v && !a))
                fail(3);
        };
        switch (f) {
        case 0x4ff79f:
            need(2);
            return memRead(t, a[0], a[1]);
        case 0x4ff822:
            need(2);
            return memSeek(t, a[0], a[1]);
        case 0x4ff8a8:
            need(4);
            return buffer(t, a);
        case 0x4dcc40:
            need(2);
            controllerBase(t);
            nodeCtor(t + 72);
            put(t + 64, a[1]);
            put(t + 60, a[0]);
            put(t + 28, 0);
            put(t + 248, 0);
            put(t + 68, 0);
            put(t, 0x513e68);
            put(t + 252, 1);
            return t;
        case 0x4dd180:
            need(0);
            controllerBase(t);
            return 0;
        case 0x4dd1c0:
            need(0);
            put(t, 0x513e88);
            if (get(t + 4)) {
                clearControllerArray(t);
                put(t + 4, 0);
            }
            put(t + 8, 0x513ea8);
            if (get(t + 12))
                free(get(t + 12));
            put(t + 8, 0x50becc);
            return 0;
        case 0x4dd240:
            need(0);
            clearControllerArray(t);
            put(t + 4, 0);
            return 0;
        case 0x4def70:
            need(0);
            return nodeCtor(t);
        case 0x4dde80:
            need(0);
            componentCtor(t);
            return t;
        case 0x4dcdf0:
            need(7);
            {
                uint32_t file = c.memoryFileToken;
                put(file, 0x510844);
                put(file + 12, empty());
                put(file + 4, 0xffffffff);
                put(file + 8, 0);
                put(file, 0x5142f4);
                put(file + 16, 1024);
                for (uint32_t off : {20u, 24u, 28u, 32u})
                    put(file + off, 0);
                put(file + 36, 1);
                put(file + 20, 0);
                put(file + 16, 0);
                put(file + 36, 0);
                put(file + 24, a[2]);
                put(file + 28, a[2]);
                put(file + 32, a[1]);
                uint32_t args[] = {a[0], file, a[3], a[4], a[5], a[6]};
                uint32_t result = loadFile(t, args);
                for (uint32_t off : {32u, 28u, 24u, 20u})
                    put(file + off, 0);
                put(file, 0x5142f4);
                put(file + 16, 0);
                put(file + 20, 0);
                put(file + 24, 0);
                put(file + 28, 0);
                put(file, 0x510844);
                stringDestroy(file + 12);
                put(file, 0x50becc);
                return result;
            }
        case 0x4dcd10:
            need(6);
            return loadFile(t, a);
        case 0x4dce90:
            need(0);
            if (get(t + 68)) {
                put(t + 68, 0);
                return virt(t + 72, 4);
            }
            return 0;
        case 0x4dccb0:
            need(0);
            put(t, 0x513e68);
            invoke(0x4dce90, t);
            destroyNode(t + 72);
            invoke(0x4dd1c0, t);
            return 0;
        case 0x4df490:
            need(1);
            serializeNode(t, a[0]);
            return 0;
        case 0x4deb50:
            need(1);
            serializeComponent(t, a[0]);
            return 0;
        case 0x4df2b0:
            need(1);
            return child(t, a[0]);
        case 0x4df0e0:
            need(5);
            return initializeNode(t, a);
        case 0x4de0e0:
            need(4);
            return componentInitialize(t, a);
        case 0x4de450:
            need(0);
            clearComponent(t);
            return 0;
        case 0x4df180:
            need(0);
            clearNode(t);
            return 0;
        case 0x4df040:
            need(0);
            destroyNode(t);
            return 0;
        case 0x4ddf70:
            need(0);
            componentDestroy(t);
            return 0;
        case 0x4df620:
            need(1);
            put(t + 16, a[0]);
            return a[0];
        case 0x4df480:
            need(0);
            return get(t + 32);
        case 0x4df260:
            need(1);
            return get(get(t + 28) + a[0] * 4);
        case 0x4df200:
            need(1);
            return find(t, a[0]);
        case 0x4df270:
            need(1);
            setArgument(t, a[0]);
            return 0;
        case 0x4dd0d0:
            need(1);
            setArgument(t + 72, a[0]);
            return 0;
        case 0x4dcf00:
            need(0);
            show(t, t + 72, 1);
            return 0;
        case 0x4dcf10:
            need(2);
            show(t, a[0], a[1]);
            return 0;
        case 0x4dd420:
            need(0);
            clearControllerArray(t);
            return 0;
        case 0x4dd2c0:
            need(1);
            if (!a[0])
                return 0;
            append(t + 8, a[0]);
            return 1;
        case 0x4dd450:
            need(1);
            return item(t, a[0]);
        case 0x4df630:
            need(0);
            return get(t + 16);
        case 0x4dd020:
            need(1);
            return find(t + 72, a[0]);
        case 0x4dd030:
            need(0);
            back(t);
            return 0;
        case 0x4dceb0:
            need(2);
            {
                uint32_t p = find(t + 72, a[0]);
                if (p) {
                    uint32_t flags = get(p + 128);
                    setMode(p + 60, a[1] ? (flags | 32) - 32 : flags | 32);
                }
                return 0;
            }
        case 0x4de4d0:
            need(2);
            replaceImage(t, a[0], a[1]);
            return 0;
        case 0x4df460:
            need(1);
            stringCopy(a[0], t + 20);
            return a[0];
        case 0x4dd800:
            need(3);
            distribute(t, a[0], a[1], a[2]);
            return 0;
        case 0x4ded20:
            need(1);
            put(a[0], get(t + 84));
            put(a[0] + 4, get(t + 88));
            return a[0];
        case 0x4dd0c0:
            need(0);
            return get(t + 248);
        case 0x4dd520:
            need(1);
            selectPointer(t, a[0]);
            return 0;
        case 0x4dda50:
            need(0);
            navigate(t, false, false);
            return 0;
        case 0x4ddb40:
            need(0);
            navigate(t, true, true);
            return 0;
        case 0x4ddac0:
            need(0);
            navigate(t, false, true);
            return 0;
        case 0x4ddbc0:
            need(0);
            press(t);
            return 0;
        case 0x4ddce0:
            need(0);
            expire(t);
            return 0;
        case 0x4dd0e0:
            need(0);
            activate(t);
            return 0;
        case 0x4ddc30:
            need(0);
            mouse(t);
            return 0;
        case 0x4dd270:
            need(1);
            expire(t);
            if (a[0])
                for (uint32_t i = 0; si(i) < si(get(t + 16)); ++i) {
                    uint32_t p = get(get(t + 12) + i * 4);
                    if (p)
                        invoke(0x4de790, p, {a[0]});
                }
            return 0;
        case 0x4de790:
            need(1);
            draw(t, a[0]);
            return 0;
        case 0x4ded40:
            need(1);
            return rectangle(t, a[0]);
        case 0x4e5b50:
            need(2);
            return 1;
        case 0x4dd480:
            need(0);
            return get(t + 28);
        case 0x4dd490:
            need(1);
            select(t, a[0]);
            return 0;
        case 0x4dec60:
            need(1);
            setMode(t, a[0]);
            return 0;
        case 0x4ed050:
            need(0);
            return get(t + 68);
        case 0x4dece0:
            need(1);
            put(a[0], get(t + 92));
            put(a[0] + 4, get(t + 96));
            return a[0];
        case 0x4ded00:
            need(2);
            put(t + 84, a[0]);
            put(t + 88, a[1]);
            return a[1];
        case 0x4bc110:
            need(0);
            return 0;
        default:
            fail(1);
        }
        return 0;
    }
    static bool owned(uint32_t f) {
        switch (f) {
        case 0x4dd020:
        case 0x4dd030:
        case 0x4dceb0:
        case 0x4de4d0:
        case 0x4df460:
        case 0x4dd800:
        case 0x4ded20:
        case 0x4de790:
        case 0x4dd1c0:
        case 0x4dd240:
        case 0x4dd0c0:
        case 0x4dd520:
        case 0x4dda50:
        case 0x4ddb40:
        case 0x4ddac0:
        case 0x4ddbc0:
        case 0x4ddce0:
        case 0x4dd0e0:
        case 0x4ddc30:
        case 0x4dd270:
        case 0x4ded40:
        case 0x4e5b50:
        case 0x4ff79f:
        case 0x4ff822:
        case 0x4ff8a8:
        case 0x4dcc40:
        case 0x4dd180:
        case 0x4def70:
        case 0x4dde80:
        case 0x4dcdf0:
        case 0x4dcd10:
        case 0x4dce90:
        case 0x4dccb0:
        case 0x4df490:
        case 0x4deb50:
        case 0x4df2b0:
        case 0x4df0e0:
        case 0x4de0e0:
        case 0x4de450:
        case 0x4df180:
        case 0x4df040:
        case 0x4ddf70:
        case 0x4df620:
        case 0x4df480:
        case 0x4df260:
        case 0x4df200:
        case 0x4df270:
        case 0x4dd0d0:
        case 0x4dcf00:
        case 0x4dcf10:
        case 0x4dd420:
        case 0x4dd2c0:
        case 0x4dd450:
        case 0x4df630:
        case 0x4dd480:
        case 0x4dd490:
        case 0x4dec60:
        case 0x4ed050:
        case 0x4dece0:
        case 0x4ded00:
        case 0x4bc110:
            return true;
        default:
            return false;
        }
    }
};
} // namespace
extern "C" uint32_t claw_interface_file_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                              ClawInterfaceFileContext *c, ClawInterfaceFileDependency d, void *u,
                                              uint32_t *r) {
    if (!c || !r || !Run::owned(f))
        return 0;
    try {
        Run run{*c, d, u};
        *r = run.entry(f, t, a, n);
        return 1;
    } catch (const Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_interface_file_function(uint32_t t, uint32_t slot) {
    if (slot & 3)
        return 0;
    if (t == 0x513ed8) {
        const uint32_t a[] = {0x4df0e0, 0x4df180, 0x4df490};
        return slot < 12 ? a[slot / 4] : 0;
    }
    if (t == 0x513e68 || t == 0x513e88 || t == 0x50c23c) {
        const uint32_t a[] = {0x4dda50, 0x4ddb40, 0x4ddac0, 0x4ddb40, 0x4bc110, 0x4bc110, 0x4dd0e0, 0x4e5b50};
        return slot < 32 ? (t == 0x50c23c && slot == 28   ? 0x45fa50
                            : t == 0x513e88 && slot == 24 ? 0x4dddc0
                                                          : a[slot / 4])
                         : 0;
    }
    return 0;
}
