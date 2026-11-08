// Original game audio trigger and speech-marker decisions.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x48bfd0:
        return 0;
    case 0x48c1e0:
    case 0x48c410:
    case 0x48c430:
    case 0x48c630:
    case 0x48c8f0:
    case 0x48ca40:
    case 0x48ca60:
    case 0x48cc60:
        return 1;
    case 0x490130:
        return 3;
    default:
        return -1;
    }
}

// Actor fields: +0x6c logic, +0x4c/+0x50 position, +0x128..0x134
// trigger rectangle; logic +0x1c state and +0x64 checkpoint identity.
bool inside(Run &run, uint32_t actor, uint32_t player) {
    uint32_t x = run.get(actor + 0x4c);
    uint32_t px = run.get(player + 0x4c);
    if (s32(px) < s32(run.get(actor + 0x128) + x))
        return false;
    if (s32(px) > s32(run.get(actor + 0x130) + x))
        return false;
    uint32_t py = run.get(player + 0x50);
    uint32_t y = run.get(actor + 0x50);
    if (s32(py) < s32(run.get(actor + 0x12c) + y))
        return false;
    return s32(py) <= s32(run.get(actor + 0x134) + y);
}

uint32_t checkpoint(Run &run) {
    return run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80);
}

// 0x48bfd0.
uint32_t function_48bfd0(Run &run, uint32_t, const uint32_t *) {
    return run.get(0x53c988);
}

// 0x48c1e0. Actor +0x08 flags, +0x40 visibility, +0xd0 category,
// +0x108 remaining activations, +0x184 sound; logic +0x20 cooldown.
uint32_t function_48c1e0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        uint32_t flags = (run.get(actor + 0x08) & 0xfffffffdu) | 1;
        uint32_t visibility = run.get(actor + 0x40) | 1;
        uint32_t count = run.get(actor + 0x108);
        run.put(actor + 0xd0, 0x4000000);
        run.put(actor + 0x40, visibility);
        run.put(actor + 0x08, flags);
        if (!count)
            run.put(actor + 0x108, 99999);
        run.call(0x48c4d0, 0, {actor, logic});
        run.put(logic + 0x1c, 5);
    } else if (state == 5) {
        uint32_t player = run.get(0x537e88);
        if (!player || !inside(run, actor, player))
            return 1;
        uint32_t sound = run.get(actor + 0x184);
        if (sound && run.get(0x532c0c))
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        uint32_t count = run.get(actor + 0x108);
        if (count == 1)
            run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000);
        else if (s32(count) > 1)
            run.put(actor + 0x108, count - 1);
        uint32_t mark = checkpoint(run);
        run.put(logic + 0x1c, 0x17);
        run.put(logic + 0x64, mark);
        if (run.get(actor + 0x108) == 0xffffffffu && run.get(actor + 0x184)) {
            run.put(logic + 0x1c, 0xb);
            run.put(logic + 0x20, run.get(run.get(run.get(actor + 0x184) + 0x10) + 0x28) + 0x64);
        }
    } else if (state == 0x17) {
        if (run.get(0x537e88) && run.get(logic + 0x64) != checkpoint(run))
            run.put(logic + 0x1c, 5);
    } else if (state == 0xb) {
        uint32_t player = run.get(0x537e88);
        if (player && !inside(run, actor, player))
            run.put(logic + 0x1c, 5);
    }
    return 1;
}

// 0x48c410.
uint32_t function_48c410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x53c9b4, 1);
    return function_48c1e0(run, receiver, arguments);
}

// 0x48c430.
uint32_t function_48c430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x53c9b4, 2);
    return function_48c1e0(run, receiver, arguments);
}

// Shared original marker placement: +0x11c height and +0x64 drawing order.
void follow(Run &run, uint32_t actor, uint32_t sourceGlobal) {
    run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffeu);
    run.put(actor + 0x4c, run.get(run.get(sourceGlobal) + 0x4c));
    uint32_t source = run.get(sourceGlobal);
    uint32_t y = run.get(source + 0x50);
    uint32_t height = run.get(source + 0x11c);
    run.put(actor + 0x50, y + height - 0x1e);
    uint32_t order = run.get(run.get(sourceGlobal) + 0x64) + 1;
    if (run.get(actor + 0x64) != order) {
        run.put(actor + 0x64, order);
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x20000);
    }
}

void expire(Run &run, uint32_t actor, uint32_t logic) {
    uint32_t remaining = run.get(logic + 0x130);
    uint32_t delta = run.get(0x53720c);
    if (delta >= remaining)
        run.put(logic + 0x130, 0);
    else
        run.put(logic + 0x130, remaining - delta);
    if (!run.get(logic + 0x130)) {
        run.put(actor + 0x184, 0);
        run.put(logic + 0x1c, 5);
    }
}

// Original state 1001 shared by 0x48c630 and 0x48cc60.
void startSpeech(Run &run, uint32_t actor, uint32_t logic, uint32_t boost) {
    uint32_t sound = run.get(actor + 0x184);
    if (!sound || !run.get(run.get(0x5371fc) + 0x118)) {
        run.put(logic + 0x1c, 5);
        run.put(actor + 0x184, 0);
        return;
    }
    uint32_t duration = run.get(run.get(sound + 0x10) + 0x28);
    run.put(logic + 0x1c, 0xf);
    run.put(logic + 0x130, duration);
    sound = run.get(actor + 0x184);
    if (!sound)
        return;
    uint32_t volume = run.get(run.get(0x5371fc) + 0x12c) + boost;
    if (s32(volume) >= 100)
        volume = 100;
    if (run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
}

// 0x48c630. Logic +0x130 remaining speech milliseconds.
uint32_t function_48c630(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        run.put(actor + 0x08, run.get(actor + 0x08) | 0xc0003);
        run.put(actor + 0xd0, 0x4000000);
        run.call(0x4c7970, actor, {0x52c580});
        run.put(logic + 0x1c, 5);
        run.put(0x53c9a4, actor);
    } else if (state == 5) {
        run.put(0x53c9a0, 0);
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
    } else if (state == 0x1d) {
        run.put(0x53c9a4, 0);
    } else if (state == 0x3e9) {
        startSpeech(run, actor, logic, 0x14);
    } else if (state == 0xf && run.get(0x537e88)) {
        run.put(0x53c9a0, 1);
        follow(run, actor, 0x537e88);
        uint32_t playerState = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x1c);
        if (playerState == 0x138c || playerState == 0x138d)
            run.put(logic + 0x130, 0);
        expire(run, actor, logic);
    }
    return 1;
}

// 0x48c8f0.
uint32_t function_48c8f0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        uint32_t flags = run.get(actor + 0x08) | 1;
        uint32_t visibility = run.get(actor + 0x40) | 1;
        uint32_t count = run.get(actor + 0x108);
        run.put(actor + 0xd0, 0x4000000);
        run.put(actor + 0x08, flags);
        run.put(actor + 0x40, visibility);
        if (!count)
            run.put(actor + 0x108, 99999);
        run.call(0x48cb00, 0, {actor, logic});
        run.put(logic + 0x1c, 5);
    } else if (state == 5) {
        uint32_t player = run.get(0x537e88);
        if (!player || !inside(run, actor, player))
            return 1;
        run.call(0x48c820, 0, {run.get(actor + 0x184), 0});
        uint32_t count = run.get(actor + 0x108);
        if (count == 1)
            run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000);
        else
            run.put(actor + 0x108, count - 1);
        uint32_t mark = checkpoint(run);
        run.put(logic + 0x1c, 0x17);
        run.put(logic + 0x64, mark);
    } else if (state == 0x17) {
        if (run.get(0x537e88) && run.get(logic + 0x64) != checkpoint(run))
            run.put(logic + 0x1c, 5);
    }
    return 1;
}

// 0x48ca40.
uint32_t function_48ca40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x53c9b4, 7);
    return function_48c8f0(run, receiver, arguments);
}

// 0x48ca60.
uint32_t function_48ca60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x53c9b4, 8);
    return function_48c8f0(run, receiver, arguments);
}

// 0x48cc60.
uint32_t function_48cc60(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        run.put(actor + 0x08, run.get(actor + 0x08) | 0xc0003);
        run.put(actor + 0xd0, 0x4000000);
        run.call(0x4c7970, actor, {0x52c580});
        run.put(logic + 0x1c, 5);
        run.put(0x53c9ac, actor);
    } else if (state == 5) {
        run.put(0x53c9a8, 0);
        run.put(0x53c9b0, 0);
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
    } else if (state == 0x1d) {
        run.put(0x53c9ac, 0);
    } else if (state == 0x3e9) {
        startSpeech(run, actor, logic, 0xa);
    } else if (state == 0xf) {
        uint32_t speaker = run.get(0x53c9b0);
        run.put(0x53c9a8, 1);
        if (speaker && (run.get(speaker + 0x08) & 0x10000)) {
            run.put(0x53c9b0, 0);
            run.put(logic + 0x130, 0);
            speaker = 0;
        }
        if (speaker)
            follow(run, actor, 0x53c9b0);
        else
            run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        expire(run, actor, logic);
    }
    return 1;
}

// 0x490130. Receiver +0x04 game, +0x0c scene, +0x10 fader manager,
// +0x2c transition definition, +0x3c/+0x40 temporary rendering surfaces.
uint32_t function_490130(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t manager = run.get(receiver + 0x10);
    if (!manager)
        return 0;
    uint32_t scene = run.get(receiver + 0x0c);
    uint32_t renderer = run.get(scene + 0x1c);
    if (!renderer)
        return 0;
    if (!run.get(receiver + 0x2c))
        return 0;
    uint32_t resources = run.get(scene + 0x04);
    uint32_t background = run.get(run.get(resources + 0x10) + 0x2c);
    if (!background)
        return 0;
    uint32_t paletteOwner = run.get(resources + 0x14);
    uint32_t width = run.get(background + 0x18);
    uint32_t height = run.get(background + 0x14);
    uint32_t format = run.get(background + 0xa4);
    if (!paletteOwner)
        return 0;
    uint32_t palette = run.get(paletteOwner + 0x2c);
    if (!palette)
        return 0;
    uint32_t surface = run.call(0x4bc670, renderer, {width, height, format, 0x800, 0xffffffffu});
    run.put(receiver + 0x3c, surface);
    if (!surface)
        return 0;
    run.call(0x4b9c50, surface, {palette});
    run.put(receiver + 0x40, 0);
    run.call(0x42a4f0, run.get(receiver + 0x04));
    uint32_t descriptor = run.automatic(-0x38);
    run.call(0x4ecb40, descriptor);
    uint32_t primary = run.get(receiver + 0x3c);
    uint32_t secondary = run.get(receiver + 0x40);
    uint32_t definition = run.get(receiver + 0x2c);
    run.put(descriptor + 0x04, background);
    run.put(descriptor + 0x08, primary);
    run.put(descriptor + 0x0c, secondary);
    run.put(descriptor + 0x10, 0x32);
    run.put(descriptor + 0x14, 1);
    run.put(descriptor + 0x18, 1);
    run.put(descriptor + 0x1c, 1);
    run.put(descriptor + 0x20, 0);
    run.put(descriptor + 0x28, run.get(definition + 0x10));
    uint32_t fader = run.call(0x4ec050, manager, {0, descriptor});
    if (!fader) {
        run.call(0x4f6584, run.automatic(-0x14));
        return 0;
    }
    run.call(0x42d420, run.get(receiver + 0x04));
    uint32_t registry = run.get(run.get(receiver + 0x0c) + 0x28);
    if (!run.get(registry + 0x30)) {
        uint32_t output = run.automatic(-0x40);
        run.put(output, 0);
        run.call(0x4f6286, registry + 0x10, {0x5246b4, output});
        uint32_t sound = run.get(output);
        if (sound && run.get(0x532c0c))
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    if (run.get(0x537238)) {
        run.call(0x4b8960, 0, {arguments[2]});
        uint32_t currentScene = run.get(receiver + 0x0c);
        uint32_t currentSurface = run.get(receiver + 0x3c);
        uint32_t currentResources = run.get(currentScene + 0x04);
        uint32_t currentImages = run.get(currentResources + 0x10);
        if (currentSurface)
            run.call(0x4b9c50, run.get(currentImages + 0x2c), {currentSurface});
    } else {
        run.call(0x4ec9c0, fader, {arguments[2], arguments[1], 0});
    }
    run.call(0x42d440, run.get(receiver + 0x04));
    run.call(0x4ec600, manager, {fader});
    primary = run.get(receiver + 0x3c);
    if (primary)
        run.call(0x4bc4f0, renderer, {primary});
    secondary = run.get(receiver + 0x40);
    run.put(receiver + 0x3c, 0);
    if (secondary)
        run.call(0x4bc4f0, renderer, {secondary});
    run.put(receiver + 0x40, 0);
    run.call(0x4f6584, run.automatic(-0x14));
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48bfd0:
        return function_48bfd0(run, receiver, arguments);
    case 0x48c1e0:
        return function_48c1e0(run, receiver, arguments);
    case 0x48c410:
        return function_48c410(run, receiver, arguments);
    case 0x48c430:
        return function_48c430(run, receiver, arguments);
    case 0x48c630:
        return function_48c630(run, receiver, arguments);
    case 0x48c8f0:
        return function_48c8f0(run, receiver, arguments);
    case 0x48ca40:
        return function_48ca40(run, receiver, arguments);
    case 0x48ca60:
        return function_48ca60(run, receiver, arguments);
    case 0x48cc60:
        return function_48cc60(run, receiver, arguments);
    case 0x490130:
        return function_490130(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_one_audio_events_01_entry, owned, body)
