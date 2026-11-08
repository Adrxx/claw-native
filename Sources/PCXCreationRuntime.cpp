#include "PCXCreationRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawPCXImageContext &c;
    ClawPCXImageDependency dependency;
    void *user;
    uint32_t *words(uint32_t token, uint32_t count = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, token, count) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t token, uint32_t offset = 0) {
        return *words(token + offset);
    }
    uint8_t *byte(uint32_t token) {
        if (c.bytes) {
            auto *p = c.bytes(c.byteContext, token, 1);
            if (p)
                return p;
            c.fault = 1;
            throw Failure{};
        }
        return reinterpret_cast<uint8_t *>(words(token & ~3u)) + (token & 3);
    }
    uint8_t read(uint32_t token) {
        return *byte(token);
    }
    void write(uint32_t token, uint8_t value) {
        *byte(token) = value;
    }
    int32_t shortSigned(uint32_t token) {
        uint16_t u = uint16_t(read(token)) | uint16_t(read(token + 1)) << 8;
        int16_t s;
        std::memcpy(&s, &u, 2);
        return s;
    }
    uint32_t service(ClawPCXImageCall &q) {
        if (dependency)
            return dependency(&c, &q, user);
        if (!q.source && !q.destination && q.argumentCount <= 4 && c.scene.call) {
            ClawSceneActorCall e{};
            e.function = q.function;
            e.receiver = q.receiver;
            e.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, e.arguments);
            return c.scene.call(c.scene.context, e);
        }
        c.fault = 1;
        throw Failure{};
    }
    static uint32_t imageService(void *context, ClawGameImageCall e) {
        auto &r = *static_cast<Run *>(context);
        ClawPCXImageCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        q.source = e.source;
        q.destination = e.destination;
        return r.service(q);
    }
    uint32_t invoke(uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> args) {
        uint32_t values[8]{};
        std::copy(args.begin(), args.end(), values);
        uint32_t out = 0;
        switch (function) {
        case 0x4babe0:
        case 0x4bad30:
        case 0x4bef50:
        case 0x4bf070:
        case 0x4b9e90:
            if (!claw_pcx_image_entry(function, receiver, values, uint32_t(args.size()), &c, dependency, user, &out) ||
                c.fault) {
                if (!c.fault)
                    c.fault = 2;
                throw Failure{};
            }
            return out;
        case 0x4b9180:
            if (c.composeImage) {
                ClawGameImageArguments a{};
                a.count = uint32_t(args.size());
                std::copy_n(values, a.count, a.words);
                ClawGameImageHost host{c.scene, this, imageService};
                uint32_t fault = 0;
                if (!claw_game_image_entry(function, receiver, a, c.image, host, &fault, &out) || fault) {
                    c.fault = fault ? fault : 2;
                    throw Failure{};
                }
                return out;
            }
            break;
        default:
            break;
        }
        ClawPCXImageCall q{};
        q.function = function;
        q.receiver = receiver;
        q.argumentCount = uint32_t(args.size());
        std::copy_n(values, q.argumentCount, q.arguments);
        return service(q);
    }
    uint32_t run(uint32_t receiver, const uint32_t *a) {
        uint32_t manager = a[0], data = a[1];
        if (!data)
            return 0;
        uint32_t width = uint32_t(shortSigned(data + 8) - shortSigned(data + 4) + 1);
        uint32_t height = uint32_t(shortSigned(data + 10) - shortSigned(data + 6) + 1);
        uint8_t planes = read(data + 65);
        uint32_t depth = planes == 1 ? 8u : planes == 3 ? 24u : 0u;
        if (!depth)
            return 0;
        uint32_t target = get(manager, 0x474);
        bool change = target != depth;
        if (change && target == 8 && !get(manager, 0x878))
            return 0;
        uint32_t palette = 0;
        if (change) {
            if (depth == 8) {
                uint32_t source = data + a[2] - 768;
                for (uint32_t i = 0; i < 256; ++i) {
                    write(0x541fb0 + i * 4, read(source++));
                    write(0x541fb0 + i * 4 + 1, read(source++));
                    write(0x541fb0 + i * 4 + 2, read(source++));
                    write(0x541fb0 + i * 4 + 3, 0);
                }
                palette = 0x541fb0;
            } else if (target == 8 && get(manager, 0x878))
                palette = manager + 0x478;
        }
        uint32_t initialize = get(get(receiver), 12);
        if (!invoke(initialize, receiver, {manager, width, height, 0, a[3]}))
            return 0;
        uint32_t temporary = 0, decoded = 0;
        if (change) {
            //Source tests signed width%2 after initialization and palette publication.
            if (width & 1)
                return 0;
            temporary = invoke(0x4f63ec, 0, {width * height * (depth == 8 ? 1u : 3u)});
            if (!temporary)
                return 0;
            decoded = invoke(depth == 8 ? 0x4bef50 : 0x4bf070, receiver, {temporary, data + 128, width, height});
            if (!decoded) {
                invoke(0x4f6428, 0, {temporary});
                return 0;
            }
        } else if (!invoke(depth == 8 ? 0x4babe0 : 0x4bad30, receiver, {data + 128}))
            return 0;
        if (change && !invoke(0x4b9e90, receiver, {temporary, depth, palette, 1})) {
            invoke(0x4f6428, 0, {temporary});
            return 0;
        }
        if (temporary)
            invoke(0x4f6428, 0, {temporary});
        return 1;
    }
};
} // namespace
extern "C" uint32_t claw_pcx_creation_entry(uint32_t receiver, const uint32_t *a, uint32_t n, ClawPCXImageContext *c,
                                            ClawPCXImageDependency d, void *user, uint32_t *out) {
    if (!c || !out || !a || n != 4 || c->fault)
        return 0;
    Run r{*c, d, user};
    try {
        *out = r.run(receiver, a);
    } catch (Failure &) {
    }
    return c->fault ? 0 : 1;
}
