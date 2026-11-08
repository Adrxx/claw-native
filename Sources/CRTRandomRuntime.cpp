#include "CRTRandomRuntime.h"
#include "WorldLootRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawCRTRandomContext &context;
    ClawCRTRandomDependency dependency;
    void *user;
    uint32_t *span(uint32_t token, uint32_t words = 1) {
        auto &h = context.host;
        auto p = h.lookup ? h.lookup(h.context, token, words) : nullptr;
        if (!p) {
            context.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t read(uint32_t token) {
        return *span(token);
    }
    void write(uint32_t token, uint32_t value) {
        *span(token) = value;
    }
    uint32_t call(uint32_t function, std::initializer_list<uint32_t> arguments = {}) {
        ClawCRTRandomCall e{};
        e.function = function;
        e.argumentCount = uint32_t(arguments.size());
        std::copy(arguments.begin(), arguments.end(), e.arguments);
        uint32_t result;
        if (dependency)
            result = dependency(&context, &e, user);
        else if (context.host.call) {
            ClawSceneActorCall q{};
            q.function = function;
            q.argumentCount = e.argumentCount;
            std::copy_n(e.arguments, e.argumentCount, q.arguments);
            result = context.host.call(context.host.context, q);
        } else {
            context.fault = 1;
            throw Failure{};
        }
        if (context.fault)
            throw Failure{};
        return result;
    }
    uint32_t initialize(uint32_t thread) {
        write(thread + 0x50, 0x5312e8);
        write(thread + 0x14, 1);
        return thread;
    }
    uint32_t thread() {
        const uint32_t error = call(0x546b0c);
        uint32_t value = call(0x546a7c, {context.globals->tlsIndex});
        if (!value) {
            value = call(0x4adf50, {1, 0x74});
            if (value && call(0x546a84, {context.globals->tlsIndex, value})) {
                initialize(value);
                uint32_t id = call(0x5469c0);
                write(value, id);
                write(value + 4, 0xffffffff);
                call(0x546ab8, {error});
                return value;
            }
            call(0x4a4860, {16});
        }
        call(0x546ab8, {error});
        return value;
    }
    uint32_t initializeTLS() {
        call(0x4a7b90);
        uint32_t index = call(0x546a90);
        context.globals->tlsIndex = index;
        if (index == 0xffffffff)
            return 0;
        uint32_t value = call(0x4adf50, {1, 0x74});
        if (!value)
            return 0;
        if (!call(0x546a84, {context.globals->tlsIndex, value}))
            return 0;
        initialize(value);
        uint32_t id = call(0x5469c0);
        write(value, id);
        write(value + 4, 0xffffffff);
        return 1;
    }
    uint32_t cleanup(uint32_t value) {
        if (context.globals->tlsIndex == 0xffffffff)
            return 0xffffffff;
        if (!value)
            value = call(0x546a7c, {context.globals->tlsIndex});
        if (value) {
            for (uint32_t offset : {0x24u, 0x28u, 0x30u, 0x38u, 0x40u, 0x44u}) {
                uint32_t allocation = read(value + offset);
                if (allocation)
                    call(0x4a49b0, {allocation});
            }
            uint32_t locale = read(value + 0x50);
            if (locale != 0x5312e8)
                call(0x4a49b0, {locale});
            call(0x4a49b0, {value});
        }
        return call(0x546a84, {context.globals->tlsIndex, 0});
    }
};
} // namespace
extern "C" void claw_crt_random_defaults(ClawCRTRandomGlobals *g) {
    if (g)
        g->tlsIndex = 0xffffffff;
}
extern "C" uint32_t claw_crt_random_entry(uint32_t function, const uint32_t *arguments, uint32_t argumentCount,
                                          ClawCRTRandomContext *context, ClawCRTRandomDependency dependency, void *user,
                                          uint32_t *result) {
    uint32_t expected;
    switch (function) {
    case 0x4a3040:
    case 0x4a7da0:
    case 0x4a7e40:
        expected = 1;
        break;
    case 0x4a3050:
    case 0x4a7dc0:
    case 0x4a7d40:
        expected = 0;
        break;
    default:
        return 0;
    }
    if (!context || !context->globals)
        return 0;
    if (argumentCount != expected || (!arguments && expected)) {
        context->fault = 2;
        return 0;
    }
    if (context->fault)
        return 0;
    Run r{*context, dependency, user};
    uint32_t value = 0;
    try {
        switch (function) {
        case 0x4a3040:
            value = r.thread();
            r.write(value + 0x14, arguments[0]);
            break;
        case 0x4a3050: {
            uint32_t thread = r.thread();
            value = claw_world_loot_next_random(r.span(thread + 0x14));
            break;
        }
        case 0x4a7da0:
            value = r.initialize(arguments[0]);
            break;
        case 0x4a7dc0:
            value = r.thread();
            break;
        case 0x4a7d40:
            value = r.initializeTLS();
            break;
        case 0x4a7e40:
            value = r.cleanup(arguments[0]);
            break;
        default:
            break;
        }
    } catch (Failure &) {
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
