#include "ResourceNamespaceRuntime.h"
#include <string>
#include <cstdint>
#include <initializer_list>
#include <cstring>
namespace {
struct Fault {};
struct Name {
    uint32_t token;
    std::string value;
    bool local;
};
struct Run {
    ClawResourceNamespaceContext &c;
    ClawResourceNamespaceDependency dependency;
    void *user;
    uint32_t operations = 0;
    void fail(uint32_t f) {
        c.fault = f;
        throw Fault{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 100000))
            fail(3);
    }
    uint32_t get(uint32_t t) {
        step();
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, 1) : nullptr;
        if (!p)
            fail(1);
        return *p;
    }
    uint8_t byte(uint32_t t) {
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t & ~3u, 1) : nullptr;
        step();
        if (!p)
            fail(1);
        return reinterpret_cast<uint8_t *>(p)[t & 3];
    }
    Name name(uint32_t t) {
        Name n{t, {}, false};
        for (uint32_t i = 0;; ++i) {
            uint8_t b = byte(t + i);
            if (!b)
                return n;
            n.value.push_back(static_cast<char>(b));
        }
    }
    static bool allowed(uint8_t b) {
        return (b >= 32 && b <= 46) || (b >= 48 && b <= 57) || (b >= 65 && b <= 90) || (b >= 97 && b <= 122);
    }
    uint32_t bucket(uint32_t t, uint32_t i) {
        uint32_t p = get(get(t + 4) + 8 + 16 * i);
        return p ? p - 4 : 0;
    }
    uint32_t first(uint32_t t) {
        uint32_t count = get(t), p = get(t + 4);
        uint32_t i = 0;
        do {
            step();
            uint32_t n = get(p + 8 + 16 * i);
            if (n)
                return n - 4;
            ++i;
        } while (i < count);
        return 0;
    }
    uint32_t next(uint32_t t) {
        uint32_t p = get(t + 4);
        if (p)
            return p - 4;
        uint32_t i = get(t + 16) + 1, map = get(t + 12), count = get(map);
        if (i >= count)
            return 0;
        uint32_t table = get(map + 4);
        do {
            step();
            uint32_t n = get(table + 8 + 16 * i);
            if (n)
                return n - 4;
            ++i;
        } while (i < count);
        return 0;
    }
    static uint8_t lower(uint8_t b) {
        return b >= 65 && b <= 90 ? b + 32 : b;
    }
    uint32_t compare(const Name &a, const Name &b) {
        if (get(0x540e88) == 0) {
            size_t i = 0;
            for (;; ++i) {
                step();
                uint8_t x = i < a.value.size() ? static_cast<uint8_t>(a.value[i]) : 0,
                        y = i < b.value.size() ? static_cast<uint8_t>(b.value[i]) : 0;
                if (x == y) {
                    if (!y)
                        return 0;
                    continue;
                }
                x = lower(x);
                y = lower(y);
                if (x != y)
                    return x < y ? 0xffffffff : 1;
                if (!y)
                    return 0;
            }
        }
        if (!dependency)
            fail(1);
        ClawResourceNamespaceCall q{};
        q.function = 0x4a3cf0;
        q.argumentCount = 2;
        const Name *n[2] = {&a, &b};
        for (unsigned i = 0; i < 2; ++i) {
            q.arguments[i] = n[i]->local ? 0 : n[i]->token;
            if (n[i]->local) {
                q.localMask |= 1u << i;
                q.buffers[q.bufferCount] = n[i]->value.c_str();
                q.bufferBytes[q.bufferCount++] = static_cast<uint32_t>(n[i]->value.size() + 1);
            }
        }
        return dependency(&c, &q, user);
    }
    uint32_t findName(uint32_t t, const Name &n, uint32_t insensitive, uint32_t modulo) {
        uint32_t node = bucket(t, static_cast<uint32_t>(n.value.size()) % modulo);
        while (node) {
            step();
            uint32_t value = get(node + 20);
            Name other = name(get(value));
            if (insensitive ? compare(other, n) == 0 : other.value == n.value)
                return get(node + 20);
            uint32_t p = get(node + 4);
            node = p ? p - 4 : 0;
        }
        return 0;
    }
    uint32_t type(uint32_t t, uint32_t tag) {
        uint32_t n = bucket(t, tag % 9);
        while (n) {
            step();
            uint32_t p = get(n + 20);
            if (get(p) == tag)
                return p;
            uint32_t nextp = get(n + 4);
            n = nextp ? nextp - 4 : 0;
        }
        return 0;
    }
    uint32_t folder(uint32_t t, Name n) {
        return findName(t + 60, n, 1, 5);
    }
    uint32_t resource(uint32_t t, Name n, uint32_t tag) {
        uint32_t ty = type(t + 68, tag);
        return ty ? findName(ty + 36, n, 1, 19) : 0;
    }
    uint32_t path(uint32_t t, Name n) {
        step();
        size_t start = n.value.size() > 1 && !allowed(static_cast<uint8_t>(n.value[0])) ? 1 : 0, end = start;
        while (end < n.value.size() && allowed(static_cast<uint8_t>(n.value[end])))
            ++end;
        if (end - start >= 64)
            fail(2);
        uint32_t child = folder(t, Name{0, n.value.substr(start, end - start), true});
        if (!child || end == n.value.size())
            return child;
        while (end < n.value.size() && !allowed(static_cast<uint8_t>(n.value[end])))
            ++end;
        if (end == n.value.size())
            return child;
        return path(child, Name{0, n.value.substr(end), true});
    }
    uint32_t filePath(uint32_t t, Name n, uint32_t tag) {
        size_t start = n.value.size() > 1 && !allowed(static_cast<uint8_t>(n.value[0])) ? 1 : 0;
        int32_t index = static_cast<int32_t>(n.value.size() - start) - 1;
        // Original reads input[-1] for empty paths before checking the negative index.
        uint8_t b = index < 0 ? byte(n.token + start - 1) : static_cast<uint8_t>(n.value[start + index]);
        while (allowed(b)) {
            if (--index < 0)
                return 0;
            b = static_cast<uint8_t>(n.value[start + index]);
        }
        if (static_cast<uint32_t>(index) == n.value.size() - start)
            return 0;
        Name leaf{0, n.value.substr(start + index + 1), true};
        if (leaf.value.size() >= 288)
            fail(2);
        if (index <= 1)
            return resource(t, leaf, tag);
        if (index >= 256)
            fail(2);
        // Source leaf occupies first32 bytes of a288-byte local region. Longer
        // copies overlap folder scratch; the subsequent folder copy overwrites it.
        char local[288]{};
        std::memcpy(local, leaf.value.c_str(), leaf.value.size() + 1);
        std::memcpy(local + 32, n.value.data() + start, index);
        local[32 + index] = 0;
        uint32_t dir = path(t, Name{0, std::string(local + 32), true});
        return dir ? resource(dir, Name{0, std::string(local), true}, tag) : 0;
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        auto need = [&](uint32_t k) {
            if (n != k || (k && !a))
                fail(4);
        };
        switch (f) {
        case 0x4b7540:
            need(0);
            return get(t + 36);
        case 0x4b7f20:
            need(1);
            return path(get(t + 36), name(a[0]));
        case 0x4b7f00:
            need(2);
            return filePath(get(t + 36), name(a[0]), a[1]);
        case 0x4b7cd0:
            need(1);
            return path(t, name(a[0]));
        case 0x4b7dc0:
            need(2);
            return filePath(t, name(a[0]), a[1]);
        case 0x4b68c0:
            need(1);
            return a[0] ? folder(t, name(a[0])) : 0;
        case 0x4b67f0:
            need(2);
            {
                uint32_t ty = type(t + 68, a[1]);
                return ty && a[0] ? findName(ty + 36, name(a[0]), 1, 19) : 0;
            }
        case 0x4b8170:
        case 0x4b7f80:
            need(2);
            return a[0] ? findName(t, name(a[0]), a[1], f == 0x4b8170 ? 5 : 19) : 0;
        case 0x4b80e0:
            need(1);
            return type(t, a[0]);
        case 0x4b80d0:
        case 0x4b8060:
            need(1);
            return a[0] % (f == 0x4b80d0 ? 9 : 19);
        case 0x4b8140:
        case 0x4b7f50:
            need(1);
            return a[0] ? static_cast<uint32_t>(name(a[0]).value.size()) % (f == 0x4b8140 ? 5 : 19) : 0;
        case 0x4d54f0:
            need(1);
            return bucket(t, a[0]);
        case 0x4d54c0:
            need(0);
            return first(t);
        case 0x4d5350:
            need(0);
            return next(t);
        case 0x4b68e0:
        case 0x4b6920:
            need(0);
            {
                uint32_t p = first(t + (f == 0x4b68e0 ? 60 : 68));
                return p ? get(p + 20) : 0;
            }
        case 0x4b6900:
        case 0x4b6940:
        case 0x4b6980:
            need(1);
            {
                uint32_t p = next(a[0] + (f == 0x4b6900 ? 36 : f == 0x4b6940 ? 4 : 72));
                return p ? get(p + 20) : 0;
            }
        case 0x4b6960:
            need(1);
            {
                uint32_t p = first(a[0] + 28);
                return p ? get(p + 20) : 0;
            }
        default:
            return 0;
        }
    }
};
bool owned(uint32_t f) {
    switch (f) {
    case 0x4b7540:
    case 0x4b7f20:
    case 0x4b7f00:
    case 0x4b7cd0:
    case 0x4b7dc0:
    case 0x4b68c0:
    case 0x4b67f0:
    case 0x4b8170:
    case 0x4b7f80:
    case 0x4b80e0:
    case 0x4b80d0:
    case 0x4b8060:
    case 0x4b8140:
    case 0x4b7f50:
    case 0x4d54f0:
    case 0x4d54c0:
    case 0x4d5350:
    case 0x4b68e0:
    case 0x4b6920:
    case 0x4b6900:
    case 0x4b6940:
    case 0x4b6980:
    case 0x4b6960:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_resource_namespace_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                  ClawResourceNamespaceContext *c, ClawResourceNamespaceDependency d,
                                                  void *u, uint32_t *r) {
    if (!owned(f) || !c || !r)
        return 0;
    try {
        Run run{*c, d, u};
        *r = run.entry(f, t, a, n);
        return 1;
    } catch (const Fault &) {
        return 0;
    }
}
