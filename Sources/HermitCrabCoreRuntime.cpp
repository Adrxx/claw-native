// Hermit crab core: resource construction, state dispatch and behavior updates.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x449d60:
        return 1;
    case 0x44a380:
        return 1;
    case 0x44aa90:
        return 1;
    case 0x44ac40:
        return 1;
    case 0x44ac60:
        return 0;
    case 0x44acd0:
        return 1;
    case 0x44ad10:
        return 2;
    case 0x44ade0:
        return 0;
    case 0x44ae30:
        return 0;
    case 0x44aef0:
        return 0;
    case 0x44af70:
        return 0;
    case 0x44afd0:
        return 0;
    default:
        return -1;
    }
}

// State fields: +0x10 world, +0x12c sprite, +0x184 behavior,
// +0x410 last hide tick, +0x414 hide interval, +0x428 bomber variant.
uint32_t function_44aa90(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_44acd0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_44ae30(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_44ac60(Run &run, uint32_t receiver, const uint32_t *arguments);

// The registry keeps signed bounds at +0x8/+0xc, storage at +0x10,
// a fallback element at +0x14 and the element stride at +0x18.
uint32_t vectorElement(Run &run, uint32_t index, uint32_t returnAddress) {
    if (s32(index) < s32(run.get(0x537850)) || s32(index) > s32(run.get(0x537854))) {
        if (!run.call(0x4db6e0, 0x537848, {index, 0})) {
            uint32_t message = run.get(0x544b4c);
            // This callee returns its caller PC; retain this call site
            // explicitly when publishing the diagnostic origin.
            run.call(0x4db5f0, 0);
            run.put(0x544b14, returnAddress);
            run.call(0x4db4d0, run.get(0x53784c), {0x537848, message, 0xc});
            return run.get(0x53785c);
        }
    }
    return (index - run.get(0x537850)) * run.get(0x537860) + run.get(0x537858);
}

// 0x449d60. Dispatch the registry entry, or the base state handler.
uint32_t function_449d60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x537868, 0);
    uint32_t entry = vectorElement(run, arguments[0], 0x449dc0);
    if (run.get(entry)) {
        run.put(0x537868, 0);
        entry = vectorElement(run, arguments[0], 0x449e3a);
        run.call(run.get(entry), receiver);
    } else {
        run.call(0x43d490, receiver, {arguments[0]});
    }
    return 0;
}

// 0x44aa90. Facade +4 reaches the image dictionary through its context.
uint32_t function_44aa90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t output = run.automatic(-0x4);
    run.put(output, 0);
    uint32_t map = run.get(run.get(run.get(receiver + 0x4) + 0xc) + 0x2c) + 0x10;
    run.call(0x4f6286, map, {arguments[0], output});
    uint32_t result = run.get(output);
    if (!result) {
        output = run.automatic(0x4);
        run.put(output, 0);
        map = run.get(run.get(run.get(receiver + 0x4) + 0xc) + 0x2c) + 0x10;
        run.call(0x4f6286, map, {0x5234b4, output});
        result = run.get(output);
    }
    return result;
}

// 0x44ac40. Scalar deleting destructor.
uint32_t function_44ac40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_44ac60(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x44ac60. Release the bitset and the two string members.
uint32_t function_44ac60(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x44acd0. Select the sprite resource for the supplied variant.
uint32_t function_44acd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x428, arguments[0]);
    run.call(0x4c7970, run.get(receiver + 0x12c), {arguments[0] ? 0x527d20u : 0x527d0cu});
    return 0;
}

// 0x44ad10. Start hiding and regenerate the interval only after expiry.
uint32_t function_44ad10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(0x537210) - run.get(receiver + 0x410) >= run.get(receiver + 0x414)) {
        uint32_t width = arguments[1] - arguments[0] + 1;
        uint32_t random = run.call(0x4a3050, 0);
        uint32_t duration;
        if (!width) {
            duration = (random & 1) ? arguments[0] : arguments[1];
        } else {
            duration = uint32_t(int64_t(s32(random)) % int64_t(s32(width))) + arguments[0];
        }
        run.put(receiver + 0x414, duration);
        run.put(receiver + 0x410, run.get(0x537210));
    }
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x527b88});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(receiver + 0x408)});
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x164, run.get(sprite + 0x164) | 1);
    return 0;
}

// 0x44ade0. Animate hiding and probabilistically leave an expired hide.
uint32_t function_44ade0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x537210) - run.get(receiver + 0x410) >= run.get(receiver + 0x414)) {
        if (s32(run.call(0x4a3050, 0)) % 100 < 90) {
            run.vcall(receiver, 0x44);
        }
    }
    return 0;
}

// 0x44ae30. Restore orientation and enter HOME.
uint32_t function_44ae30(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sprite = run.get(receiver + 0x12c);
    bool mirrored = (run.get8(sprite + 0x40) & 2) != 0;
    bool wanted = run.get(receiver + 0x18c) == 2;
    if (mirrored != wanted) {
        uint32_t left = run.get(receiver + 0x138);
        uint32_t right = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - right);
        run.put(receiver + 0x140, 0u - left);
        uint32_t flags = run.get(sprite + 0x40);
        run.put(sprite + 0x40, wanted ? flags | 2 : flags & ~2u);
        sprite = run.get(receiver + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x527b90});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x164, run.get(sprite + 0x164) & ~1u);
    return 0;
}

// 0x44af70. Enter DEFENSE and install its animation.
uint32_t function_44af70(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x527b7c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(receiver + 0x40c)});
    return 0;
}

// 0x44aef0. Choose hide or defense after the animation update.
uint32_t function_44aef0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t state = run.get(receiver + 0x184);
    if (state > 6) {
        return 0;
    }
    if (state < 2 || state > 4) {
        if (s32(run.call(0x4a3050, 0)) % 100 < 40) {
            const uint32_t limits[] = {1000, 3000};
            function_44ad10(run, receiver, limits);
            return 0;
        }
    }
    function_44af70(run, receiver, nullptr);
    return 0;
}

// 0x44afd0. Choose the next action once the defense animation completes.
uint32_t function_44afd0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (!run.get(animation + 0x1c) || run.get(animation + 0x14)) {
        return 0;
    }
    uint32_t state = run.get(receiver + 0x184);
    if (state > 4) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    bool bomber = run.get(receiver + 0x428) != 0;
    int hide;
    int action;
    switch (state) {
    case 0:
    case 1:
        hide = bomber ? 10 : 50;
        action = bomber ? 0 : 20;
        break;
    case 2:
        hide = bomber ? 10 : 30;
        action = bomber ? 10 : 40;
        break;
    case 3:
        hide = 20;
        action = bomber ? 20 : 30;
        break;
    default:
        hide = bomber ? 40 : 10;
        action = bomber ? 40 : 20;
        break;
    }
    if (s32(run.call(0x4a3050, 0)) % 100 < hide) {
        const uint32_t limits[] = {1000, 3000};
        function_44ad10(run, receiver, limits);
    } else if (s32(run.call(0x4a3050, 0)) % 100 < action) {
        uint32_t sound = run.get(receiver + 0x400);
        if (sound && run.get(0x532c0c)) {
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        }
        run.vcall(receiver, 0x64);
    } else {
        run.call(0x44b130, receiver);
    }
    return 0;
}

// 0x44a380. Construct the base, facade and hermit-crab behavior members.
uint32_t function_44a380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44bc60, receiver, {arguments[0]});
    uint32_t facade = receiver + 0x128;
    run.call(0x44aaf0, facade, {arguments[0]});
    run.call(0x4f6439, receiver + 0x1a4);
    run.call(0x4f6439, receiver + 0x1a8);
    run.call(0x4dc180, receiver + 0x2f4);
    run.put(receiver + 0x3c8, 0);
    run.put(receiver + 0x3cc, 0);
    run.put(receiver + 0x3d0, 0);
    run.put(receiver + 0x3d4, 0);
    run.put(receiver + 0x3d8, 0);
    run.put(receiver + 0x3dc, 0);
    run.put(receiver + 0x3e0, 0);
    run.put(receiver + 0x3e4, 0);
    run.put(receiver + 0x3e8, 0);
    run.put(receiver + 0x3ec, 0);
    run.put(receiver + 0x3f0, 0);
    run.put(receiver + 0x3f4, 0);
    run.put(receiver + 0x3f8, 0);
    run.put(receiver + 0x3fc, 0);
    run.put(receiver, 0x50b16c);
    uint32_t object = run.get(receiver + 0xc);
    run.put(object + 0x8, run.get(object + 0x8) | 0x80000);
    run.put(receiver + 0x4, run.get(run.get(receiver + 0x10) + 0x168));
    run.put(receiver + 0x184, 6);
    run.put(receiver + 0x188, 0);
    run.put(receiver + 0x288, 0);
    run.put(receiver + 0x28c, 400);
    run.put(receiver + 0x290, 50);
    run.put(receiver + 0x29c, 300);
    run.put(receiver + 0x2a0, 50);
    run.put(receiver + 0x2a4, 200);
    run.put(receiver + 0x2a8, 50);
    run.put(receiver + 0x2ac, 100);
    run.put(receiver + 0x2b0, 50);
    run.put(receiver + 0x2e4, run.get(run.get(receiver + 0xc) + 0x108));
    run.put(receiver + 0x2e8, run.get(run.get(receiver + 0xc) + 0x114));
    run.put(receiver + 0x2ec, run.get(run.get(receiver + 0x10) + 0x68));
    run.put(receiver + 0x2f0, run.get(run.get(receiver + 0x10) + 0x68));
    run.put(receiver + 0x19c, 0xffffffff);
    run.put(receiver + 0x1a0, 0);
    run.icall(0x546cdc, {receiver + 0x210});
    run.icall(0x546cdc, {receiver + 0x220});
    run.icall(0x546cdc, {receiver + 0x230});
    run.icall(0x546cdc, {receiver + 0x240});
    run.icall(0x546cdc, {receiver + 0x250});
    run.icall(0x546cdc, {receiver + 0x260});
    uint32_t temporary = run.automatic(-0x1c);
    run.call(0x4dbe10, temporary, {0x534938, 0});
    run.call(0x4dbd60, receiver + 0x2f4, {temporary});
    run.call(0x4dbcd0, temporary);
    if (run.gets(run.get(receiver + 0x10) + 0x64) > 0) {
        run.call(0x420fc0, receiver + 0x2f4, {2});
    }
    run.call(0x420fc0, receiver + 0x2f4, {9});
    run.put(receiver + 0x2b4, 0);
    run.put(receiver + 0x2b8, 0);
    run.put(receiver + 0x2bc, 0);
    run.put(receiver + 0x2c0, 0);
    run.put(receiver + 0x2c4, 0);
    run.put(receiver + 0x2c8, 0);
    run.put(receiver + 0x1ac, 0);
    run.put(receiver + 0x2cc, 0);
    run.put(receiver + 0x2d0, 0);
    run.put(receiver + 0x308, 0);
    run.put(receiver + 0x30c, 0);
    run.put(receiver + 0x310, 0);
    run.put(receiver + 0x314, 0);
    run.put(receiver + 0x318, 0);
    run.put(receiver + 0x31c, 0);
    run.put(receiver + 0x320, 0);
    run.put(receiver + 0x32c, 0);
    run.put(receiver + 0x330, 0);
    run.put(receiver + 0x334, 0);
    run.put(receiver + 0x338, 0);
    run.put(receiver + 0x33c, 0);
    run.put(receiver + 0x340, 0);
    run.put(receiver + 0x344, 0);
    run.put(receiver + 0x348, 0);
    run.put(receiver + 0x34c, 0);
    run.put(receiver + 0x350, 0);
    run.put(receiver + 0x354, 0);
    run.put(receiver + 0x358, 0);
    run.put(receiver + 0x35c, 0);
    run.put(receiver + 0x360, 0);
    run.put(receiver + 0x364, 0);
    run.put(receiver + 0x368, 0);
    run.put(receiver + 0x36c, 0);
    run.put(receiver + 0x370, 0);
    run.put(receiver + 0x374, 0);
    run.put(receiver + 0x378, 0);
    run.put(receiver + 0x37c, 0);
    run.put(receiver + 0x380, 0);
    run.put(receiver + 0x384, 0);
    run.put(receiver + 0x388, 0);
    run.put(receiver + 0x38c, run.call(0x40f780, facade, {0x5266ec}));
    run.put(receiver + 0x390, run.call(0x40f780, facade, {0x524870}));
    run.put(receiver + 0x394, run.call(0x40f780, facade, {0x524864}));
    run.put(receiver + 0x398, run.call(0x40f780, facade, {0x524858}));
    run.put(receiver + 0x39c, run.call(0x40f780, facade, {0x52484c}));
    run.put(receiver + 0x148, run.call(0x40f780, facade, {0x5266dc}));
    run.put(receiver + 0x3a0, 0);
    run.put(receiver + 0x3a4, 0);
    run.put(receiver + 0x3a8, 0);
    run.put(receiver + 0x3ac, 0);
    run.put(receiver + 0x3b0, 0);
    run.put(receiver + 0x3b4, 0);
    run.put(receiver + 0x3b8, 0);
    run.put(receiver + 0x3bc, 0);
    run.put(receiver + 0x3c0, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0x409f4000);
    object = run.get(receiver + 0x12c);
    run.put(object + 0x164, run.get(object + 0x164) & ~1u);
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) {
        run.call(0x4357a0, facade);
    }
    run.put(receiver + 0x410, 0);
    run.put(receiver + 0x414, 0);
    run.put(receiver + 0x418, 0);
    run.put(receiver + 0x41c, 0);
    run.put(receiver + 0x420, 0);
    run.put(receiver + 0x424, 0);
    run.put(receiver, 0x50e014);
    run.putd(receiver + 0x70, run.getd(receiver + 0x70) - run.getd(0x50dff8));
    run.put(receiver + 0x2d0, 15);
    run.put(receiver + 0x2c0, 0);
    run.put(receiver + 0x2c4, 0xfffffff6);
    run.put(receiver + 0x2c8, 0xfffffff1);
    run.put(receiver + 0x2b4, 10);
    run.put(receiver + 0x2b8, 0xfffffff6);
    run.put(receiver + 0x2bc, 0xffffffbb);
    uint32_t variant[] = {run.get(run.get(receiver + 0x10) + 0x64)};
    function_44acd0(run, receiver, variant);
    run.put(receiver + 0x42c, 0);
    uint32_t animation;
    animation = run.call(0x4062e0, facade, {0x527cec});
    if (!animation) {
        animation = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x308, animation);
    animation = run.call(0x4062e0, facade, {0x527cd0});
    if (!animation) {
        animation = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x40c, animation);
    animation = run.call(0x4062e0, facade, {0x527cb8});
    if (!animation) {
        animation = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x408, animation);
    animation = run.call(0x4062e0, facade, {0x527c9c});
    if (!animation) {
        animation = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x310, animation);
    animation = run.call(0x4062e0, facade, {0x527c80});
    if (!animation) {
        animation = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x374, animation);
    animation = run.call(0x4062e0, facade, {0x527c68});
    if (!animation) {
        animation = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x364, animation);
    // The owned lookup entry follows saved frame/locals, its argument and
    // return address (0x44a8bd through 0x44a8f3). Keep its fallback output in
    // that nested argument slot rather than the constructor argument slot.
    uint32_t constructorFrame = run.frame;
    run.frame = constructorFrame - 0x48;
    uint32_t name[] = {0x527c50};
    run.put(receiver + 0x380, function_44aa90(run, facade, name));
    name[0] = 0x527c38;
    run.put(receiver + 0x378, function_44aa90(run, facade, name));
    name[0] = 0x527cb8;
    run.put(receiver + 0x37c, function_44aa90(run, facade, name));
    name[0] = 0x527c50;
    run.put(receiver + 0x32c, function_44aa90(run, facade, name));
    run.frame = constructorFrame;
    uint32_t soundName = run.get(receiver + 0x428) ? 0x527c28 : 0x527c0c;
    run.put(receiver + 0x3a0, run.call(0x40f780, facade, {soundName}));
    run.put(receiver + 0x3a4, run.call(0x40f780, facade, {0x527bf0}));
    run.put(receiver + 0x400, run.call(0x40f780, facade, {0x527bd4}));
    run.put(receiver + 0x404, run.call(0x40f780, facade, {0x527bc4}));
    run.call(0x420fc0, receiver + 0x2f4, {3});
    run.call(0x420fc0, receiver + 0x2f4, {0});
    object = run.get(receiver + 0x12c);
    run.put(object + 0x8, run.get(object + 0x8) | 0x40);
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000022);
    uint32_t rectangle = run.automatic(-0x2c);
    run.call(0x4061e0, run.get(receiver + 0x12c), {rectangle});
    run.put(rectangle + 0x4, run.get(rectangle + 0x4) + 10);
    run.put(rectangle + 0xc, run.get(rectangle + 0xc) + 5);
    run.call(0x40abb0, facade, {rectangle});
    run.call(0x406240, run.get(receiver + 0x12c));
    run.put(receiver + 0x28c, 400);
    run.put(receiver + 0x290, 50);
    run.put(receiver + 0x29c, 300);
    run.put(receiver + 0x2a0, 50);
    run.put(receiver + 0x2a4, 100);
    run.put(receiver + 0x2a8, 50);
    run.put(receiver + 0x2ac, 50);
    run.put(receiver + 0x2b0, 50);
    run.put(receiver + 0x430, 0);
    object = run.get(receiver + 0xc);
    if (!run.get(object + 0x104)) {
        run.put(object + 0x104, 5);
    }
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x220});
    run.icall(0x546d24, {receiver + 0x220, 15, 10});
    run.call(0x4296f0, receiver + 0x210, {0xffffffff, 0xffffffff, 1, 1});
    run.call(0x40abf0, facade);
    function_44ae30(run, receiver, nullptr);
    return receiver;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x449d60:
        return function_449d60(run, receiver, arguments);
    case 0x44a380:
        return function_44a380(run, receiver, arguments);
    case 0x44aa90:
        return function_44aa90(run, receiver, arguments);
    case 0x44ac40:
        return function_44ac40(run, receiver, arguments);
    case 0x44ac60:
        return function_44ac60(run, receiver, arguments);
    case 0x44acd0:
        return function_44acd0(run, receiver, arguments);
    case 0x44ad10:
        return function_44ad10(run, receiver, arguments);
    case 0x44ade0:
        return function_44ade0(run, receiver, arguments);
    case 0x44ae30:
        return function_44ae30(run, receiver, arguments);
    case 0x44aef0:
        return function_44aef0(run, receiver, arguments);
    case 0x44af70:
        return function_44af70(run, receiver, arguments);
    case 0x44afd0:
        return function_44afd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_hermit_crab_core_entry, owned, body)
