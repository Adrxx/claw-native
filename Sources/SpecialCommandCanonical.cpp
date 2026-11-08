// Original application commands, single-player travel, results and fade wrappers
// Recovered from the reviewed original disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40ac20:
        return 3;
    case 0x40b120:
        return 1;
    case 0x415d90:
        return 1;
    case 0x42abf0:
        return 0;
    case 0x46b7b0:
        return 0;
    case 0x46bbc0:
        return 0;
    case 0x46c630:
        return 0;
    case 0x46c7b0:
        return 1;
    case 0x46c900:
        return 0;
    case 0x48fda0:
        return 3;
    case 0x48feb0:
        return 3;
    case 0x4ecc00:
        return 0;
    default:
        return -1;
    }
}

// Calls retain the physical entry ESP so original descendants use their real locals.
uint32_t external(Run &run, int32_t offset, uint32_t target, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    uint32_t saved = run.stackPointer;
    run.stackPointer = run.automatic(offset);
    uint32_t value = run.call(target, receiver, args);
    run.stackPointer = saved;
    return value;
}

struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, int32_t offset) : run(run), saved(run.frame) {
        run.frame = run.automatic(offset);
    }
    ~Frame() {
        run.frame = saved;
    }
};

uint32_t function_46c7b0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_46bbc0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_48fda0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_48feb0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ecc00(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x40ac20. State +4 app, +8 archive, +0xc scene; +0x154 child.
uint32_t function_40ac20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (arguments[2] != 3) return 0;
    if (!external(run, -0x20, 0x42bfd0, arguments[0])) return 0;
    if (!external(run, -0x2c, 0x48f0d0, receiver, {arguments[0], arguments[1], 3})) return 0;
    if (!external(run, -0x20, 0x42af50, run.get(receiver + 0x04))) {
        external(run, -0x24, 0x42a000, run.get(receiver + 0x04), {0});
    }
    uint32_t app = run.get(receiver + 0x04);
    run.put(receiver + 0x15c, run.get(app + 0x68));
    external(run, -0x2c, 0x429ed0, app, {0x0a, 0, 1});
    uint32_t resource = external(run, -0x24, 0x4b7f20, run.get(receiver + 0x08), {0x523b1c});
    run.put(receiver + 0x20, resource);
    if (!resource) return 0;
    resource = external(run, -0x24, 0x4b7f20, run.get(receiver + 0x08), {0x523734});
    run.put(receiver + 0x24, resource);
    if (!resource) return 0;
    external(run, -0x20, 0x4c89e0, run.get(run.get(receiver + 0x0c) + 0x08));
    external(run, -0x20, 0x4ca300, run.get(run.get(receiver + 0x0c) + 0x28));
    resource = external(run, -0x24, 0x4b68c0, run.get(receiver + 0x20), {0x52372c});
    if (!resource) return 0;
    external(run, -0x2c, 0x4ca440, run.get(run.get(receiver + 0x0c) + 0x28), {resource, 0x523b14, 0x523728});
    do {
        resource = external(run, -0x24, 0x546d54, 0, {0});
    } while (s32(resource) >= 0);
    external(run, -0x28, 0x4b8910, run.get(run.get(receiver + 0x04) + 0x04), {0x100, 0x40});
    bool large = run.get(run.get(receiver + 0x04) + 0x130) != 0;
    uint32_t child = external(run, -0x24, 0x4f63ec, 0, {large ? 0x184u : 0x158u});
    if (child) {
        if (large) {
            run.put(child, 0x50b4ec);
        }
        run.put(child + 0x04, 0);
        run.put(child + 0x08, 0);
        run.put(child + 0x0c, 0);
        run.put(child + 0x1c, 0);
        run.put(child + 0x20, 0);
        run.put(child + 0x24, 0);
        run.put(child + 0x2c, 0);
        run.put(child + 0x30, 0);
        run.put(child + 0x3c, 0);
        run.put(child + 0x40, 0);
        run.put(child + 0x34, 0);
        run.put8(child + 0x4c, 0);
        run.put(child + 0x18, 0);
        run.put(child + 0x150, 0);
        if (large) {
            external(run, -0x20, 0x4f6439, child + 0x180);
            run.put(child, 0x50b494);
            run.put(child + 0x154, 0);
            run.put(child + 0x158, 0);
            for (uint32_t offset = 0x15c; offset < 0x180; offset += 4) {
                run.put(child + offset, 0);
            }
        } else {
            run.put(child, 0x50b43c);
            run.put(child + 0x154, 0);
        }
    }
    run.put(receiver + 0x154, child);
    child = run.get(receiver + 0x154);
    if (!external(run, -0x2c, run.get(run.get(child) + 0x04), child, {arguments[0], arguments[1], 3})) return 0;
    run.put(receiver + 0x158, 0);
    external(run, -0x20, 0x4b3ab0, run.get(0x537200));
    return 1;
}

// 0x40b120. Child activation virtual +0x24.
uint32_t function_40b120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t child = run.get(receiver + 0x154);
    if (!child) return 1;
    return external(run, -0x08, run.get(run.get(child) + 0x24), child, {arguments[0]});
}

// 0x415d90. Player +0x6c logic, logic +0x14 data; score/health +0xf8/+0x10c.
uint32_t function_415d90(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t player = arguments[0];
    if (!player) return 0;
    uint32_t logic = run.get(player + 0x6c);
    if (!logic) return 0;
    uint32_t data = run.get(logic + 0x14);
    if (!data) return 0;
    run.put(data + 0x44, run.get(player + 0xf8));
    run.put(data + 0x48, run.get(player + 0x10c));
    run.put(data + 0x04, 0);
    for (uint32_t offset = 0; offset < 0x138; offset += 4) {
        run.put(0x534c80 + offset, run.get(data + offset));
    }
    uint32_t app = run.get(0x5371fc);
    uint32_t state = run.get(app + 0x2c);
    if (state && external(run, -0x10, 0x42a630, app)) {
        Frame frame(run, -0x14);
        function_46c7b0(run, state, arguments);
    }
    return 0;
}

// 0x42abf0. App +0x30 scene, global frame baselines and player timer.
uint32_t function_42abf0(Run &run, uint32_t receiver, const uint32_t *) {
    external(run, -0x08, 0x4b83d0, receiver);
    if (run.get(receiver + 0x30)) {
        uint32_t time = external(run, -0x08, 0x546df0, 0);
        run.put(0x5430c8, time);
        run.put(0x5430c4, 0);
    }
    uint32_t first = run.get(0x541328);
    uint32_t second = run.get(0x54132c);
    run.put(0x537208, first);
    uint32_t player = run.get(0x537e88);
    run.put(0x53720c, second);
    if (player) {
        uint32_t data = run.get(run.get(player + 0x6c) + 0x14);
        if (data) {
            run.put(data + 0x120, 0x4e20);
        }
    }
    return 0;
}

// 0x46b7b0. State resource handles +0x768/+0x76c/+0x770/+0x150.
uint32_t function_46b7b0(Run &run, uint32_t receiver, const uint32_t *) {
    {
        Frame frame(run, -0x10);
        function_46bbc0(run, receiver, nullptr);
    }
    uint32_t args[] = {run.get(0x537e88)};
    {
        Frame frame(run, -0x14);
        function_415d90(run, 0, args);
    }
    uint32_t app = run.get(receiver + 0x04);
    if (app) {
        uint32_t manager = run.get(app + 0x58);
        if (manager) {
            for (uint32_t offset : {0x768u, 0x76cu, 0x770u, 0x150u}) {
                uint32_t handle = run.get(receiver + offset);
                if (handle) {
                    external(run, -0x14, 0x4c7510, manager, {handle});
                    run.put(receiver + offset, 0);
                }
            }
        }
    }
    uint32_t scene = run.get(receiver + 0x0c);
    if (scene) {
        uint32_t backend = run.get(run.get(scene + 0x28) + 0x2c);
        if (backend) external(run, -0x10, 0x4b4b40, backend);
        external(run, -0x10, 0x4ca300, run.get(run.get(receiver + 0x0c) + 0x28));
    }
    app = run.get(receiver + 0x04);
    if (app && run.get(app + 0x3c)) {
        external(run, -0x10, 0x4b5c10, run.get(app + 0x3c));
        run.put(run.get(run.get(receiver + 0x04) + 0x3c) + 0x44, 0);
    }
    app = run.get(receiver + 0x04);
    if (app) {
        external(run, -0x10, 0x4b5340, run.get(app + 0x50));
        external(run, -0x10, 0x4022a0, run.get(run.get(receiver + 0x04) + 0x5c));
    }
    scene = run.get(receiver + 0x0c);
    if (scene) {
        uint32_t object = run.get(scene + 0x10);
        external(run, -0x10, run.get(run.get(object) + 0x58), object);
    }
    scene = run.get(receiver + 0x0c);
    if (scene) external(run, -0x10, 0x4cdf40, run.get(scene + 0x2c));
    scene = run.get(receiver + 0x0c);
    if (scene) {
        uint32_t object = run.get(scene + 0x24);
        external(run, -0x10, run.get(run.get(object) + 0x44), object);
    }
    scene = run.get(receiver + 0x0c);
    if (scene) external(run, -0x10, 0x4c89e0, run.get(scene + 0x08));
    app = run.get(receiver + 0x04);
    if (app && run.get(app + 0x4c)) external(run, -0x10, 0x422350, run.get(app + 0x4c));
    run.put(0x537e88, 0);
    return 0;
}

// 0x46bbc0. Settings +0x38, viewport +0x68; settings captured for both writes.
uint32_t function_46bbc0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!external(run, -0x08, run.get(run.get(receiver) + 0x0c), receiver)) return 0;
    uint32_t app = run.get(receiver + 0x04);
    if (!app) return 0;
    uint32_t settings = run.get(app + 0x38);
    if (!settings) return 0;
    external(run, -0x10, 0x4b5e50, settings, {0x5258a8, run.get(app + 0x68)});
    external(run, -0x10, 0x4b5e50, settings, {0x525860, run.get(0x525518)});
    return 0;
}

// 0x46c630. Pending coordinates, scene renderer +0x24 and subrenderer +0x5c.
uint32_t function_46c630(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t x = run.get(0x529fa0);
    if (s32(x) <= 0 || s32(run.get(0x529fa4)) <= 0) return 0;
    uint32_t player = run.get(0x537e88);
    if (!player) return 0;
    run.put(player + 0x4c, x);
    run.put(run.get(0x537e88) + 0x50, run.get(0x529fa4));
    run.put(0x529fa0, 0xffffffff);
    run.put(0x529fa4, 0xffffffff);
    uint32_t audio = run.get(run.get(receiver + 0x0c) + 0x28);
    if (!run.get(audio + 0x30)) {
        uint32_t local = run.automatic(-0x04);
        run.put(local, 0);
        external(run, -0x18, 0x4f6286, audio + 0x10, {0x52a07c, local});
        uint32_t sound = run.get(local);
        if (sound) external(run, -0x20, 0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
    }
    uint32_t fadeArgs[] = {0x50, 0x5aa, 0};
    {
        Frame frame(run, -0x1c);
        function_48feb0(run, receiver, fadeArgs);
    }
    {
        Frame frame(run, -0x10);
        function_42abf0(run, run.get(receiver + 0x04), nullptr);
    }
    for (uint32_t index = 0; index < 2; ++index) {
        uint32_t renderer = run.get(run.get(run.get(receiver + 0x0c) + 0x24) + 0x5c);
        if (renderer) external(run, -0x10, 0x4d2000, renderer);
        renderer = run.get(run.get(run.get(receiver + 0x0c) + 0x24) + 0x5c);
        if (renderer) external(run, -0x10, 0x4d1fd0, renderer);
        uint32_t objects = run.get(run.get(receiver + 0x0c) + 0x08);
        external(run, -0x14, run.get(run.get(objects) + 0x24), objects, {1});
    }
    uint32_t scene = run.get(receiver + 0x0c);
    external(run, -0x18, 0x4cb9b0, run.get(scene + 0x24), {run.get(run.get(scene + 0x04) + 0x14), run.get(scene + 0x08)});
    scene = run.get(receiver + 0x0c);
    uint32_t interface = run.get(scene + 0x0c);
    uint32_t display = run.get(scene + 0x04);
    external(run, -0x18, run.get(run.get(interface) + 0x34), interface, {run.get(display + 0x14), run.get(display + 0x18)});
    uint32_t result;
    {
        Frame frame(run, -0x1c);
        result = function_48fda0(run, receiver, fadeArgs);
    }
    if (!result) return 0;
    {
        Frame frame(run, -0x10);
        function_42abf0(run, run.get(receiver + 0x04), nullptr);
    }
    return 1;
}

// 0x46c7b0. Level-strided score/time/flags at +0x160/+0x164/+0x168.
uint32_t function_46c7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t player = arguments[0];
    if (!player) return 0;
    uint32_t level = run.get(receiver + 0x14);
    if (s32(level) <= 0 || s32(level) > 0x0e) return 0;
    uint32_t row = receiver + level * 0x10;
    if (run.get(row + 0x164)) return 0;
    uint32_t score = run.get(receiver + 0x160);
    uint32_t time = run.get(receiver + 0x164);
    run.put(receiver + 0x160, run.get(player + 0xf8));
    run.put(receiver + 0x164, time + run.get(0x537210));
    run.put(row + 0x160, run.get(player + 0xf8) - score);
    run.put(row + 0x164, run.get(0x537210));
    if (run.get(run.get(run.get(receiver + 0x04) + 0x48) + 0x128)) {
        run.put(row + 0x168, run.get(row + 0x168) | 1);
        run.put(receiver + 0x168, run.get(receiver + 0x168) | 1);
    }
    return 0;
}

// 0x46c900. Loading +0x258, finish flag +0x25c, application mode +0x9c.
uint32_t function_46c900(Run &run, uint32_t receiver, const uint32_t *) {
    {
        Frame frame(run, -0x0c);
        function_46b7b0(run, receiver, nullptr);
    }
    run.put(0x537e88, 0);
    if (!run.get(receiver + 0x258)) {
        external(run, -0x18, 0x46d620, receiver, {0, 0, 3});
        external(run, -0x0c, 0x49bbc0, run.get(run.get(receiver + 0x04) + 0x60));
    }
    uint32_t level = run.get(receiver + 0x14);
    if (level == 0x0e) {
        run.put(receiver + 0x25c, 1);
    }
    uint32_t app = run.get(receiver + 0x04);
    if (run.get(app + 0x9c)) {
        if (run.get(receiver + 0x25c)) {
            if (run.get(receiver + 0x0c) && run.get(receiver + 0x2c)) {
                external(run, -0x0c, 0x4bb870, run.get(run.get(receiver + 0x2c) + 0x10));
                external(run, -0x24, 0x4bb990, run.get(run.get(receiver + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, 0x1f4});
                for (uint32_t index = 0; index < 2; ++index) {
                    uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
                    external(run, -0x10, 0x4b97c0, run.get(run.get(display + 0x14) + 0x2c), {0});
                    external(run, -0x10, 0x4b98b0, run.get(run.get(display + 0x10) + 0x2c), {0});
                }
            }
            external(run, -0x0c, 0x42b910, run.get(receiver + 0x04));
            external(run, -0x0c, 0x42abb0, run.get(receiver + 0x04));
        } else {
            external(run, -0x1c, 0x546d50, 0, {run.get(run.get(app + 0x04) + 0x04), 0x111, 0x8075, 0});
        }
        return 1;
    }
    if (!external(run, -0x1c, 0x428c40, app, {0x0a, level, 1, 0})) {
        external(run, -0x14, 0x429e10, run.get(receiver + 0x04), {0x8005, 0x702});
        return 0;
    }
    return 1;
}

// 0x48fda0. Five-word addressed descriptor at entry ESP-0x14.
uint32_t function_48fda0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t manager = run.get(receiver + 0x10);
    if (!manager) return 0;
    uint32_t scene = run.get(receiver + 0x0c);
    if (!run.get(scene + 0x1c)) return 0;
    uint32_t display = run.get(scene + 0x04);
    uint32_t primary = run.get(run.get(display + 0x10) + 0x2c);
    if (!primary) return 0;
    uint32_t secondary = run.get(run.get(display + 0x14) + 0x2c);
    if (!secondary) return 0;
    uint32_t local = run.automatic(-0x14);
    {
        Frame frame(run, -0x28);
        function_4ecc00(run, local, nullptr);
    }
    run.put(local + 0x0c, 0);
    run.put(local + 0x10, arguments[0]);
    run.put(local + 0x04, primary);
    run.put(local + 0x08, secondary);
    uint32_t fade = external(run, -0x30, 0x4ec050, manager, {2, local});
    if (!fade) return 0;
    external(run, -0x28, 0x42d420, run.get(receiver + 0x04));
    if (!run.get(0x537238)) {
        external(run, -0x34, 0x4ec9c0, fade, {arguments[1], arguments[2], 0});
    } else {
        external(run, -0x2c, 0x4b8960, 0, {arguments[1]});
        external(run, -0x2c, 0x4b9c50, run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x2c), {secondary});
    }
    external(run, -0x28, 0x42d440, run.get(receiver + 0x04));
    external(run, -0x2c, 0x4ec600, manager, {fade});
    return 1;
}

// 0x48feb0. Fade-out descriptor has no secondary surface.
uint32_t function_48feb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t manager = run.get(receiver + 0x10);
    if (!manager) return 0;
    uint32_t scene = run.get(receiver + 0x0c);
    if (!run.get(scene + 0x1c)) return 0;
    uint32_t primary = run.get(run.get(run.get(scene + 0x04) + 0x10) + 0x2c);
    if (!primary) return 0;
    uint32_t local = run.automatic(-0x14);
    {
        Frame frame(run, -0x24);
        function_4ecc00(run, local, nullptr);
    }
    run.put(local + 0x0c, 1);
    run.put(local + 0x10, arguments[0]);
    run.put(local + 0x04, primary);
    run.put(local + 0x08, 0);
    uint32_t fade = external(run, -0x2c, 0x4ec050, manager, {2, local});
    if (!fade) return 0;
    external(run, -0x24, 0x42d420, run.get(receiver + 0x04));
    if (!run.get(0x537238)) {
        external(run, -0x30, 0x4ec9c0, fade, {arguments[1], arguments[2], 0});
    } else {
        external(run, -0x28, 0x4b8960, 0, {arguments[1]});
        external(run, -0x28, 0x4b97c0, run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x2c), {0});
    }
    external(run, -0x24, 0x42d440, run.get(receiver + 0x04));
    external(run, -0x28, 0x4ec600, manager, {fade});
    return 1;
}

// 0x4ecc00. Map-fader descriptor kind, two surfaces, direction and gradient.
uint32_t function_4ecc00(Run &run, uint32_t receiver, const uint32_t *) {
    external(run, -0x08, 0x4ecb30, receiver);
    run.put(receiver, 3);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 1);
    run.put(receiver + 0x10, 0x0f);
    return receiver;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40ac20:
        return function_40ac20(run, receiver, arguments);
    case 0x40b120:
        return function_40b120(run, receiver, arguments);
    case 0x415d90:
        return function_415d90(run, receiver, arguments);
    case 0x42abf0:
        return function_42abf0(run, receiver, arguments);
    case 0x46b7b0:
        return function_46b7b0(run, receiver, arguments);
    case 0x46bbc0:
        return function_46bbc0(run, receiver, arguments);
    case 0x46c630:
        return function_46c630(run, receiver, arguments);
    case 0x46c7b0:
        return function_46c7b0(run, receiver, arguments);
    case 0x46c900:
        return function_46c900(run, receiver, arguments);
    case 0x48fda0:
        return function_48fda0(run, receiver, arguments);
    case 0x48feb0:
        return function_48feb0(run, receiver, arguments);
    case 0x4ecc00:
        return function_4ecc00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_special_command_entry, owned, body)
