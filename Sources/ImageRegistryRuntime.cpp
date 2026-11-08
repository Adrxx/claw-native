#include "ImageRegistryRuntime.h"
#include "AnimationEngine.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <string>
#include <vector>
namespace {
struct Run {
    ClawImageRegistryContext *c;
    uint32_t visits = 0;
    void fail(uint32_t f = 1) {
        c->fault = f;
    }
    uint8_t *span(uint32_t t, uint32_t n) {
        if (c->fault)
            return nullptr;
        auto *p = c->scene.lookup ? c->scene.lookup(c->scene.context, t & ~3u, ((t & 3u) + n + 3) / 4) : nullptr;
        if (!p) {
            fail();
            return nullptr;
        }
        return reinterpret_cast<uint8_t *>(p) + (t & 3u);
    }
    uint32_t word(uint32_t t) {
        uint32_t v = 0;
        if (auto *p = span(t, 4))
            std::memcpy(&v, p, 4);
        return v;
    }
    uint32_t byte(uint32_t t) {
        auto *p = span(t, 1);
        return p ? *p : 0;
    }
    void put(uint32_t t, uint32_t v) {
        if (auto *p = span(t, 4))
            std::memcpy(p, &v, 4);
    }
    void putByte(uint32_t t, uint32_t v) {
        if (auto *p = span(t, 1))
            *p = uint8_t(v);
    }
    bool next() {
        if (++visits > 1000000)
            fail(3);
        return !c->fault;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        if (c->fault)
            return 0;
        if (!c->scene.call || a.size() > 4) {
            fail();
            return 0;
        }
        ClawSceneActorCall e{f, t, {0, 0, 0, 0}, uint32_t(a.size())};
        std::copy(a.begin(), a.end(), e.arguments);
        return c->scene.call(c->scene.context, e);
    }
    uint32_t alloc(uint32_t n) {
        if (c->fault)
            return 0;
        if (!c->scene.allocate) {
            fail();
            return 0;
        }
        return c->scene.allocate(c->scene.context, n);
    }
    void free(uint32_t t) {
        if (c->fault)
            return;
        if (!c->scene.free) {
            fail();
            return;
        }
        c->scene.free(c->scene.context, t);
    }
    std::string text(uint32_t t, uint32_t limit = 1024) {
        std::string v;
        if (!t) {
            fail(2);
            return v;
        }
        for (uint32_t i = 0; i < limit && !c->fault; ++i) {
            uint32_t b = byte(t + i);
            if (!b)
                return v;
            v.push_back(char(b));
        }
        if (!c->fault)
            fail(3);
        return v;
    }
    void name(uint32_t dest, uint32_t prefix, uint32_t separator, uint32_t leaf) {
        std::string s;
        if (prefix && byte(prefix)) {
            s = text(prefix) + text(separator) + text(leaf);
        } else
            s = text(leaf);
        if (c->fault)
            return;
        if (s.size() > 255) {
            fail(3);
            return;
        }
        auto *p = span(dest, uint32_t(s.size() + 1));
        if (p)
            std::memcpy(p, s.c_str(), s.size() + 1);
    }
    uint32_t function(uint32_t t, uint32_t slot) {
        uint32_t v = word(t), f = claw_image_registry_function(v, slot);
        return f ? f : word(v + slot);
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t>);
    uint32_t method(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return invoke(function(t, slot), t, a);
    }
    uint32_t array(uint32_t f, uint32_t t, uint32_t a = 0, uint32_t b = 0xffffffff);
    uint32_t createRoot(uint32_t controller, uint32_t nameToken) {
        uint32_t root = call(0x4f6286, controller + 16, {nameToken});
        if (root || c->fault)
            return root;
        root = alloc(108);
        if (!root) {
            fail(2);
            return 0;
        }
        put(root, 0x50e924);
        put(root + 4, word(controller + 0x1c));
        put(root + 8, 0);
        put(root + 12, word(controller + 12));
        array(0x4f58ab, root + 16);
        put(root, 0x513cf8);
        put(root + 100, 99999);
        put(root + 104, 0);
        if (!method(root, 0x24, {nameToken})) {
            method(root, 4, {1});
            return 0;
        }
        put(call(0x4f62a8, controller + 16, {nameToken}), root);
        return root;
    }
};
int32_t si(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
bool supported(uint32_t f) {
    switch (f) {
    case 0x4cff40:
    case 0x4d0120:
    case 0x4ce0d0:
    case 0x4cdff0:
    case 0x4ce5e0:
    case 0x4ce670:
    case 0x4ce770:
    case 0x4d0380:
    case 0x4cf080:
    case 0x4cf1f0:
    case 0x4cfaa0:
    case 0x4cfba0:
    case 0x4cfca0:
    case 0x4cfdb0:
    case 0x4cfec0:
    case 0x4cfee0:
    case 0x4cff00:
    case 0x4cff20:
    case 0x4ce320:
    case 0x4ce480:
    case 0x4ce530:
    case 0x4d2380:
    case 0x4d61b0:
    case 0x4d6070:
    case 0x4d76e0:
    case 0x4d6260:
    case 0x4d6210:
    case 0x4ce250:
    case 0x4ce270:
    case 0x4ce2d0:
    case 0x4d02f0:
    case 0x4d0310:
    case 0x4cf230:
        return true;
    default:
        return false;
    }
}
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (e->function == 0x4f63ec)
        return r.alloc(e->arguments[0]);
    if (e->function == 0x4f6428) {
        r.free(e->arguments[0]);
        return 0;
    }
    switch (e->argumentCount) {
    case 0:
        return r.call(e->function, e->receiver);
    case 1:
        return r.call(e->function, e->receiver, {e->arguments[0]});
    default:
        return r.call(e->function, e->receiver, {e->arguments[0], e->arguments[1]});
    }
}
uint32_t Run::array(uint32_t f, uint32_t t, uint32_t a, uint32_t b) {
    if (f == 0x4f58de) {
        put(t, 0x5108fc);
        free(word(t + 4));
        put(t, 0x50becc);
        return 0;
    }
    if (!c->arrays)
        return call(f, t, f == 0x4f58ab ? std::initializer_list<uint32_t>{} : std::initializer_list<uint32_t>{a, b});
    c->arrays->scene = c->scene;
    uint32_t result = 0;
    if (!claw_carray_entry(f, t, a, b, 0, c->arrays, arrayDependency, this, &result) && !c->fault)
        fail(2);
    if (c->arrays->fault)
        c->fault = c->arrays->fault;
    return result;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    uint32_t args[5]{};
    if (a.size() > 5) {
        fail(2);
        return 0;
    }
    std::copy(a.begin(), a.end(), args);
    if (supported(f))
        return entry(*this, f, t, args);
    bool imageSupported = f == 0x4ce3d0 || f == 0x4d2410 || f == 0x4d22f0;
    if (imageSupported && c->images && c->imageHost) {
        ClawGameImageArguments x{};
        x.count = uint32_t(a.size());
        std::copy(a.begin(), a.end(), x.words);
        uint32_t result = 0;
        if (!claw_game_image_entry(f, t, x, c->images, *c->imageHost, &c->fault, &result) && !c->fault)
            fail(2);
        return result;
    }
    return call(f, t, a);
}
uint32_t nameIndex(Run &r, uint32_t t) {
    while (r.next()) {
        uint32_t b = r.byte(t);
        if (!b)
            return 0;
        if (b >= '0' && b <= '9')
            break;
        ++t;
    }
    uint32_t n = 0;
    while (r.next()) {
        uint32_t b = r.byte(t++);
        if (b < '0' || b > '9')
            break;
        n = n * 10 + (b - '0');
    }
    return n;
}
uint32_t typeFormat(uint32_t type) {
    return type == 0x504944 ? 4 : type == 0x524944 ? 3 : type == 0x504358 ? 2 : type == 0x424d50 ? 1 : 0;
}
uint32_t newImage(Run &r, uint32_t t, const uint32_t *a, uint32_t f) {
    uint32_t id = f == 0x4ce320 ? a[1] : a[2];
    if (si(id) < si(r.word(t + 24)) && r.word(r.word(t + 20) + id * 4))
        return 0;
    uint32_t im = r.alloc(52);
    if (!im) {
        r.fail(2);
        return 0;
    }
    r.put(im + 4, id);
    r.put(im + 8, 0);
    r.put(im + 12, r.word(t + 12));
    r.put(im, 0x513a70);
    for (uint32_t off : {16u, 20u, 44u, 48u})
        r.put(im + off, 0);
    uint32_t ok = f == 0x4ce320   ? r.method(im, 0x2c, {a[0], a[2]})
                  : f == 0x4ce480 ? r.method(im, 0x28, {a[0], a[1], a[3], 1})
                                  : r.method(im, 0x24, {a[0], a[1], a[3]});
    if (!ok) {
        r.method(im, 4, {1});
        return 0;
    }
    r.array(0x4f582f, t + 16, id, im);
    if (si(id) < si(r.word(t + 100)))
        r.put(t + 100, id);
    if (si(r.word(t + 104)) < si(id))
        r.put(t + 104, id);
    return im;
}
uint32_t decodeRecord(Run &r, uint32_t t, uint32_t registry, uint32_t data) {
    auto *raw = r.span(data, 20);
    if (!raw)
        return 0;
    ClawAnimationRecord rec{};
    uint32_t eventLength = 0;
    if (!claw_animation_decode_record(raw, 20, 0, &rec,
                                      &eventLength)) { // optional event bytes need a complete native view
        uint32_t flags = r.byte(data) | r.byte(data + 1) << 8;
        if (!(flags & 2)) {
            r.fail(2);
            return 0;
        }
        std::string event = r.text(data + 20, 65536);
        if (r.c->fault)
            return 0;
        raw = r.span(data, uint32_t(21 + event.size()));
        if (!raw || !claw_animation_decode_record(raw, uint32_t(21 + event.size()), 0, &rec, &eventLength)) {
            r.fail(2);
            return 0;
        }
    }
    r.put(t + 4, (r.word(t + 4) & 0xffff0000) | (rec.flags & 0xffff));
    const uint32_t values[] = {rec.imageCommand,
                               rec.controlCommand,
                               rec.movementCommand,
                               rec.parameter,
                               rec.duration,
                               rec.code,
                               rec.dx,
                               rec.dy};
    for (uint32_t i = 0; i < 8; ++i)
        r.put(t + 8 + i * 4, values[i]);
    r.put(t + 0x2c, 0);
    auto *source = r.span(data + 18, 2);
    auto *dest = r.span(t + 0x28, 2);
    if (source && dest)
        std::memcpy(dest, source, 2);
    r.c->eventNameBytes = eventLength + ((rec.flags & 2) ? 1u : 0u);
    if ((rec.flags & 2) && registry)
        r.put(t + 0x2c, r.call(0x4f6286, registry + 16, {data + 20}));
    return r.c->fault ? 0 : 1;
}
uint32_t entry(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    if (f == 0x4cf080)
        return r.word(t + 12) && r.word(t + 4) != 0xffffffff ? 1 : 0;
    if (f == 0x4d0380) {
        bool ended = false;
        for (uint32_t i = 0; i < 63 && !r.c->fault; ++i) {
            uint32_t b = ended ? 0 : r.byte(a[0] + i);
            ended |= !b;
            r.putByte(t + 0x24 + i, b);
        }
        r.putByte(t + 99, 0);
        return 1;
    }
    if (f == 0x4cf1f0) {
        uint32_t controller = r.call(0x4b7540, a[0]);
        uint32_t group = r.call(0x4b68c0, controller, {a[1]});
        return group ? r.method(t, 0x48, {group, 0x534938, 0x523728}) : 0;
    }
    if (f == 0x4cf230) {
        uint32_t root = r.call(0x4f6286, t + 16, {a[0]});
        if (root) {
            r.call(0x4f5db6, t + 16, {a[0]});
            r.method(root, 4, {1});
        }
        return 0;
    }
    if (f == 0x4cfaa0 || f == 0x4cfba0 || f == 0x4cfca0 || f == 0x4cfdb0) {
        bool wide = f == 0x4cfca0 || f == 0x4cfdb0;
        uint32_t root = r.createRoot(t, a[wide ? 2 : 1]);
        if (!root)
            return 0;
        return wide ? r.method(root, f == 0x4cfca0 ? 0x30 : 0x2c, {a[0], a[1], a[3], a[4]})
                    : r.method(root, f == 0x4cfaa0 ? 0x38 : 0x34, {a[0], a[2], a[3]});
    }
    if (f == 0x4cfec0 || f == 0x4cfee0)
        return r.method(a[1], f == 0x4cfec0 ? 0x34 : 0x38, {a[0], a[2], a[3]});
    if (f == 0x4cff00 || f == 0x4cff20)
        return r.method(a[2], f == 0x4cff00 ? 0x30 : 0x2c, {a[0], a[1], a[3], a[4]});
    if (f == 0x4ce320 || f == 0x4ce480 || f == 0x4ce530)
        return newImage(r, t, a, f);
    if (f == 0x4d2380) {
        uint32_t type = typeFormat(r.call(0x4b61b0, a[0]));
        if (!type)
            return 0;
        uint32_t data = r.call(0x4b61c0, a[0]);
        if (!data)
            return 0;
        uint32_t ret = r.method(t, 0x28, {data, type, r.word(a[0] + 20), a[1]});
        r.call(0x4b6230, a[0]);
        return ret;
    }
    if (f == 0x4d61b0) {
        if (r.call(0x4b61b0, a[1]) != 0x414e49)
            return 0;
        r.put(t + 4, a[2]);
        uint32_t data = r.call(0x4b61c0, a[1]);
        if (!data)
            return 0;
        uint32_t ret = r.invoke(0x4d6070, t, {a[0], data, 0});
        r.call(0x4b6230, a[1]);
        return ret;
    }
    if (f == 0x4d76e0)
        return decodeRecord(r, t, a[0], a[1]);
    if (f == 0x4d6070) {
        uint32_t at = a[1] + 32;
        r.put(t + 4, a[2]);
        r.put(t + 4, r.word(a[1] + 8) | a[2]);
        uint32_t len = r.word(a[1] + 16);
        if (!len)
            r.put(t + 28, 0);
        else {
            uint32_t name = r.alloc(len + 2);
            r.put(t + 28, name);
            if (!name) {
                r.fail(2);
                return 0;
            }
            for (uint32_t i = 0; i < r.word(a[1] + 16) && r.next(); ++i)
                r.putByte(name + i, r.byte(at++));
            r.putByte(name + len, 0);
        }
        uint32_t i = 0;
        while (si(i) < si(r.word(a[1] + 12)) && r.next()) {
            uint32_t rec = r.alloc(48);
            if (!rec) {
                r.fail(2);
                return 0;
            }
            r.put(rec, 0x513df8);
            r.put(rec + 12, 0xffff);
            if (!decodeRecord(r, rec, a[0], at)) {
                r.method(rec, 4, {1});
                r.invoke(0x4d6210, t, {});
                return 0;
            }
            r.array(0x4f582f, t + 8, r.word(t + 16), rec);
            at += 20 + r.c->eventNameBytes;
            ++i;
        }
        return 1;
    }
    if (f == 0x4cdff0) {
        uint32_t seq = r.alloc(32);
        if (!seq)
            return 0;
        r.put(seq, 0x50becc);
        r.array(0x4f58ab, seq + 8);
        r.put(seq, 0x513a58);
        r.put(seq + 4, 0);
        r.put(seq + 28, 0);
        if (!r.invoke(0x4d61b0, seq, {r.word(r.word(t + 12) + 0x28), a[1], 0})) {
            r.method(seq, 4, {1});
            return 0;
        }
        r.put(r.call(0x4f62a8, t + 16, {a[0]}), seq);
        return seq;
    }
    if (f == 0x4ce5e0 || f == 0x4ce670) {
        uint32_t previous = 0, count = 0;
        if (f == 0x4ce670)
            for (uint32_t i = 0; si(i) < si(r.word(t + 24)) && r.next(); ++i)
                if (si(i) >= si(r.word(t + 100)) && si(i) <= si(r.word(t + 104)) && r.word(r.word(t + 20) + i * 4))
                    ++previous;
        for (uint32_t type = r.call(0x4b6920, a[0]); type && r.next(); type = r.call(0x4b6940, a[0], {type})) {
            for (uint32_t file = r.call(0x4b6960, a[0], {type}); file && r.next();
                 file = r.call(0x4b6980, a[0], {file})) {
                if (f == 0x4ce670 && !typeFormat(r.call(0x4b61b0, file)))
                    continue;
                uint32_t id = nameIndex(r, r.word(file));
                uint32_t ok = r.method(t, f == 0x4ce5e0 ? 0x38 : 0x40, {file, id, 1});
                if (f == 0x4ce670 && !ok)
                    return 0xffffffff;
                if (ok)
                    ++count;
            }
        }
        return f == 0x4ce670 && si(count) < si(previous) ? 0xffffffff : count;
    }
    if (f == 0x4ce770) {
        if (si(a[1]) < si(r.word(t + 100)) || si(a[1]) > si(r.word(t + 104)))
            return 0;
        uint32_t image = r.word(r.word(t + 20) + a[1] * 4);
        return image && r.method(image, 0x34, {a[0], a[2]}) ? 1 : 0;
    }
    if (f == 0x4cff40 || f == 0x4d0120 || f == 0x4ce0d0) {
        uint32_t buffer = r.alloc(256), count = 0;
        if (!buffer) {
            if (f == 0x4d0120)
                r.fail(2);
            return 0;
        }
        if (f != 0x4d0120)
            r.putByte(buffer, 0);
        for (uint32_t directory = r.call(0x4b68e0, a[0]); directory && r.next();
             directory = r.call(0x4b6900, a[0], {directory})) {
            r.name(buffer, a[1], a[2], r.word(directory));
            uint32_t added = f == 0x4ce0d0 ? r.invoke(f, t, {directory, buffer, a[2]})
                                           : r.method(t, f == 0x4cff40 ? 0x48 : 0x4c, {directory, buffer, a[2]});
            if (f == 0x4d0120 && si(added) < 0) {
                r.free(buffer);
                return 0xffffffff;
            }
            count += added;
        }
        if (f == 0x4ce0d0) {
            for (uint32_t type = r.call(0x4b6920, a[0]); type && r.next(); type = r.call(0x4b6940, a[0], {type}))
                for (uint32_t file = r.call(0x4b6960, a[0], {type}); file && r.next();
                     file = r.call(0x4b6980, a[0], {file}))
                    if (r.call(0x4b61b0, file) == 0x414e49) {
                        r.name(buffer, a[1], a[2], r.word(file));
                        if (r.invoke(0x4cdff0, t, {buffer, file}))
                            ++count;
                    }
        } else if (a[1] && r.byte(a[1])) {
            uint32_t root = f == 0x4cff40 ? r.createRoot(t, a[1]) : r.call(0x4f6286, t + 16, {a[1]});
            if (root) {
                uint32_t ok = r.method(root, f == 0x4cff40 ? 0x28 : 0x3c, {a[0]});
                if (f == 0x4d0120 && ok == 0xffffffff) {
                    r.free(buffer);
                    return 0xffffffff;
                }
                if (r.word(root + 24))
                    ++count;
                else if (f == 0x4cff40)
                    r.method(t, 0x54, {a[1]});
            } else if (f == 0x4cff40)
                return 0;
        }
        r.free(buffer);
        return count;
    }
    if (f == 0x4d6260) {
        r.put(t + 12, 0xffff);
        r.put(t, 0x50becc);
        if (a[0] & 1)
            r.free(t);
        return t;
    }
    if (f == 0x4d6210 || f == 0x4ce2d0) {
        uint32_t arrayOffset = f == 0x4d6210 ? 8 : 16;
        for (uint32_t i = 0; si(i) < si(r.word(t + arrayOffset + 8)) && r.next(); ++i) {
            uint32_t item = r.word(r.word(t + arrayOffset + 4) + i * 4);
            if (item)
                r.method(item, 4, {1});
        }
        if (f == 0x4d6210) {
            if (r.word(t + 28)) {
                r.free(r.word(t + 28));
                r.put(t + 28, 0);
            }
        }
        r.array(0x4f5915, t + arrayOffset, 0, 0xffffffff);
        if (f == 0x4ce2d0) {
            r.put(t + 100, 99999);
            r.put(t + 104, 0);
        }
        return 0;
    }
    if (f == 0x4ce270 || f == 0x4d0310) {
        bool ani = f == 0x4ce270;
        r.put(t, ani ? 0x513a58 : 0x513cf8);
        r.invoke(ani ? 0x4d6210 : 0x4ce2d0, t, {});
        r.array(0x4f58de, t + (ani ? 8 : 16));
        if (!ani) {
            r.put(t + 4, 0xffffffff);
            r.put(t + 8, 0);
            r.put(t + 12, 0);
        }
        r.put(t, 0x50becc);
        return 0;
    }
    if (f == 0x4ce250 || f == 0x4d02f0) {
        r.invoke(f == 0x4ce250 ? 0x4ce270 : 0x4d0310, t, {});
        if (a[0] & 1)
            r.free(t);
        return t;
    }
    r.fail(2);
    return 0;
}
} // namespace
extern "C" uint32_t claw_image_registry_function(uint32_t v, uint32_t slot) {
    if (v == 0x513b88) {
        switch (slot) {
        case 0x14:
            return 0x4cf080;
        case 0x24:
            return 0x4cfdb0;
        case 0x28:
            return 0x4cff20;
        case 0x2c:
            return 0x4cff00;
        case 0x30:
            return 0x4cfca0;
        case 0x34:
            return 0x4cfee0;
        case 0x38:
            return 0x4cfaa0;
        case 0x3c:
            return 0x4cfec0;
        case 0x40:
            return 0x4cfba0;
        case 0x44:
            return 0x4cf1f0;
        case 0x48:
            return 0x4cff40;
        case 0x4c:
            return 0x4d0120;
        case 0x54:
            return 0x4cf230;
        default:
            return 0;
        }
    }
    if (v == 0x513cf8) {
        switch (slot) {
        case 4:
            return 0x4d02f0;
        case 0x14:
            return 0x4cf080;
        case 0x1c:
            return 0x4ce2d0;
        case 0x24:
            return 0x4d0380;
        case 0x28:
            return 0x4ce5e0;
        case 0x2c:
            return 0x4ce530;
        case 0x30:
            return 0x4ce480;
        case 0x34:
            return 0x4ce3d0;
        case 0x38:
            return 0x4ce320;
        case 0x3c:
            return 0x4ce670;
        case 0x40:
            return 0x4ce770;
        default:
            return 0;
        }
    }
    if (v == 0x513a70) {
        switch (slot) {
        case 4:
            return 0x4ce8e0;
        case 0x24:
            return 0x4d2540;
        case 0x28:
            return 0x4d2410;
        case 0x2c:
            return 0x4d2380;
        case 0x30:
            return 0x4d22f0;
        case 0x34:
            return 0x4d27a0;
        default:
            return 0;
        }
    }
    if (v == 0x513a58 && slot == 4)
        return 0x4ce250;
    if (v == 0x513df8 && slot == 4)
        return 0x4d6260;
    return 0;
}
extern "C" uint32_t claw_image_registry_entry(uint32_t f, uint32_t t, ClawImageRegistryArguments a,
                                              ClawImageRegistryContext *c, uint32_t *result) {
    if (!c || !supported(f))
        return 0;
    uint32_t n = 0;
    switch (f) {
    case 0x4d0380:
    case 0x4ce5e0:
    case 0x4ce670:
    case 0x4cf230:
    case 0x4d6260:
    case 0x4ce250:
    case 0x4d02f0:
        n = 1;
        break;
    case 0x4cdff0:
    case 0x4d2380:
    case 0x4d76e0:
    case 0x4cf1f0:
        n = 2;
        break;
    case 0x4cff40:
    case 0x4d0120:
    case 0x4ce0d0:
    case 0x4d61b0:
    case 0x4d6070:
    case 0x4ce320:
    case 0x4ce770:
        n = 3;
        break;
    case 0x4cfaa0:
    case 0x4cfba0:
    case 0x4cfee0:
    case 0x4cfec0:
    case 0x4ce480:
    case 0x4ce530:
        n = 4;
        break;
    case 0x4cfca0:
    case 0x4cfdb0:
    case 0x4cff00:
    case 0x4cff20:
        n = 5;
        break;
    default:
        break;
    }
    if (a.count != n) {
        c->fault = 2;
        return 0;
    }
    Run r{c};
    uint32_t value = entry(r, f, t, a.words);
    if (result)
        *result = value;
    return c->fault ? 0 : 1;
}
