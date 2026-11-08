// Popup and resource context construction, translated from the original entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x438c40:
    case 0x423840:
        return 3;
    case 0x4399d0:
        return 1;
    case 0x4236c0:
        return 2;
    case 0x424b90:
    case 0x424ca0:
        return 0;
    default:
        return -1;
    }
}

uint32_t callAt(Run &run, int32_t offset, uint32_t target, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.automatic(offset);
    return run.call(target, receiver, arguments);
}

uint32_t virtualAt(Run &run, int32_t offset, uint32_t receiver, uint32_t slot,
                   std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.automatic(offset);
    return run.vcall(receiver, slot, arguments);
}

// 0x4236c0. Base popup, embedded map +0x278, CString words +0x2ac/+0x2b0.
uint32_t construct(Run &run, uint32_t receiver, uint32_t context, uint32_t parent) {
    callAt(run, -0x2c, 0x4e1b20, receiver, {context, parent});
    callAt(run, -0x28, 0x4f5e89, receiver + 0x278, {10});
    callAt(run, -0x24, 0x4f6439, receiver + 0x2ac);
    callAt(run, -0x24, 0x4f6439, receiver + 0x2b0);
    run.put(receiver, 0x50bc6c);
    // Image, owner, resource manager and selected directory.
    run.put(receiver + 0x29c, 0);
    run.put(receiver + 0x2a0, 0);
    run.put(receiver + 0x2a4, 0);
    run.put(receiver + 0x2a8, 0);
    callAt(run, -0x28, 0x4f66cc, receiver + 0x2ac, {0x534938});
    callAt(run, -0x28, 0x4f66cc, receiver + 0x2b0, {0x534938});
    // Initialization flags and centered position.
    run.put(receiver + 0x2b4, 0);
    run.put(receiver + 0x2b8, 0);
    run.put(receiver + 0x294, 0);
    run.put(receiver + 0x298, 0);
    run.put(0x52545c, 0xffffffff);
    return receiver;
}

// 0x4399d0. +0x160 owns the selected popup; +4/+8 hold application/resources.
uint32_t createSelected(Run &run, uint32_t receiver, uint32_t mode) {
    uint32_t previous = run.get(receiver + 0x160);
    if (previous) {
        virtualAt(run, -0x28, previous, 0x0, {1});
        run.put(receiver + 0x160, 0);
    }
    uint32_t context = run.get(run.get(run.get(receiver + 0x4) + 0x4) + 0x4);
    uint32_t name = run.automatic(-0x10);
    callAt(run, -0x24, 0x4f6439, name);
    if (mode > 7) {
        callAt(run, -0x24, 0x4f6584, name);
        return 0;
    }
    const uint32_t sizes[] = {0x2c4, 0x2bc, 0x2bc, 0x2bc, 0x304, 0x2bc, 0x2bc, 0x2d4};
    const uint32_t tables[] = {0x50d794, 0x50ce74, 0x50cc2c, 0x50d54c, 0x50c9e4, 0x50d0bc, 0x50d304};
    const uint32_t names[] = {0x526f14, 0x526edc, 0x526ed0, 0x525454, 0x526ec4, 0x526eec, 0x526ef4, 0x526f08};
    uint32_t popup = callAt(run, -0x28, 0x4f63ec, 0, {sizes[mode]});
    if (popup) {
        if (mode == 7) {
            popup = callAt(run, -0x2c, 0x499e70, popup, {context, 0});
        } else {
            uint32_t outerFrame = run.frame;
            run.frame = run.automatic(-0x2c);
            construct(run, popup, context, 0);
            run.frame = outerFrame;
            if (mode == 4) {
                // Twelve player-edit CString fields precede the derived vtable.
                for (uint32_t offset = 0x2d4; offset <= 0x300; offset += 4)
                    callAt(run, -0x24, 0x4f6439, popup + offset);
            }
            run.put(popup, tables[mode]);
            if (mode == 4) {
                run.put(popup + 0x2bc, 0);
                run.put(popup + 0x2c0, 0);
                run.put(popup + 0x2c4, 0);
                run.put(popup + 0x2c8, 0);
                run.put(popup + 0x2cc, 0);
                run.put(popup + 0x2d0, 0);
            }
        }
    }
    run.put(receiver + 0x160, popup);
    callAt(run, -0x28, 0x4f66cc, name, {names[mode]});
    if (!run.get(receiver + 0x160)) {
        callAt(run, -0x24, 0x4f6584, name);
        return 0;
    }
    uint32_t copiedName = run.automatic(-0x24);
    callAt(run, -0x2c, 0x4f6449, copiedName, {name});
    uint32_t result = virtualAt(run, -0x30, run.get(receiver + 0x160), 0x1c8,
                                {receiver, run.get(receiver + 0x8), run.get(copiedName)});
    callAt(run, -0x24, 0x4f6584, name);
    return result;
}

// 0x438c40. State +0x164, cursor +0x154, mode +0x158, cursor offsets +0x174/+0x178.
uint32_t initializeMenu(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = run.get(receiver + 0x164);
    if (!state)
        state = callAt(run, -0x18, 0x42bfd0, arguments[0]);
    run.put(receiver + 0x164, state);
    run.put(receiver + 0x154, 0);
    run.put(receiver + 0x15c, 0);
    run.put(receiver + 0x160, 0);
    run.put(receiver + 0x168, 0);
    run.put(receiver + 0x16c, run.get(0x528a60));
    run.put(receiver + 0x174, 0);
    run.put(receiver + 0x178, 0);
    run.put(0x5375bc, 0);
    if (!run.get(receiver + 0x164))
        return 0;
    if (!callAt(run, -0x24, 0x48f0d0, receiver, {arguments[0], arguments[1], arguments[2]}))
        return 0;
    uint32_t mode = run.get(receiver + 0x158);
    uint32_t outerFrame = run.frame;
    run.frame = run.automatic(-0x1c);
    uint32_t selected = createSelected(run, receiver, mode);
    run.frame = outerFrame;
    if (!selected)
        return 0;
    callAt(run, -0x18, 0x43a760, receiver);
    if (!callAt(run, -0x18, 0x439480, receiver))
        return 0;
    uint32_t point = run.automatic(-0x8);
    callAt(run, -0x1c, 0x546cd0, 0, {point});
    uint32_t cursor = callAt(run, -0x30, 0x4c8da0, run.get(run.get(receiver + 0xc) + 0x8),
                             {0, 0xffffff9c, 0xffffff9c, 0x4e1e, 0x522658, 0});
    run.put(receiver + 0x154, cursor);
    bool inGame = virtualAt(run, -0x18, run.get(receiver + 0x164), 0x10) == 11;
    if (!inGame)
        inGame = virtualAt(run, -0x18, run.get(receiver + 0x164), 0x10) == 3;
    if (!inGame)
        inGame = virtualAt(run, -0x18, run.get(receiver + 0x164), 0x10) == 4;
    callAt(run, -0x1c, 0x4c7970, run.get(receiver + 0x154), {inGame ? 0x526d90u : 0x526dacu});
    callAt(run, -0x20, 0x4c79e0, run.get(receiver + 0x154), {inGame ? 0x526d90u : 0x526d9cu, 0});
    cursor = run.get(receiver + 0x154);
    uint32_t image = run.get(cursor + 0x174);
    if (image) {
        run.put(receiver + 0x174, uint32_t(run.gets(image + 0x10) / 2));
        run.put(receiver + 0x178, uint32_t(run.gets(image + 0x14) / 2));
    }
    uint32_t y = run.get(point + 0x4) + run.get(receiver + 0x178);
    run.put(point + 0x4, y);
    run.put(cursor + 0x4c, run.get(receiver + 0x174) + run.get(point));
    run.put(run.get(receiver + 0x154) + 0x50, run.get(point + 0x4));
    run.put(0x5375bc, receiver);
    return 1;
}

// 0x423840. Incoming CString is consumed on every return path.
uint32_t initializePopup(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t incoming = run.automatic(0xc);
    run.put(incoming, arguments[2]);
    uint32_t result = 0;
    if (arguments[0] && arguments[1] && run.get(arguments[2] - 0x8)) {
        run.put(receiver + 0x2a4, arguments[1]);
        run.put(receiver + 0x2a0, arguments[0]);
        run.put(receiver + 0x29c, 0);
        run.put(receiver + 0x2a8, 0);
        callAt(run, -0x24, 0x4f667d, receiver + 0x2ac, {incoming});
        uint32_t temporary = callAt(run, -0x2c, 0x4f684d, 0,
                                    {run.automatic(0x4), 0x52549c, receiver + 0x2ac});
        callAt(run, -0x24, 0x4f667d, receiver + 0x2b0, {temporary});
        callAt(run, -0x20, 0x4f6584, run.automatic(0x4));
        run.put(receiver + 0x2b4, 1);
        run.put(receiver + 0x2b8, 0);
        run.put(receiver + 0x294, 0);
        run.put(receiver + 0x298, 0);
        run.put(0x52545c, 0xffffffff);
        if (virtualAt(run, -0x20, receiver, 0x21c) &&
            virtualAt(run, -0x20, receiver, 0x228) &&
            virtualAt(run, -0x20, receiver, 0x22c) &&
            virtualAt(run, -0x20, receiver, 0x230) &&
            callAt(run, -0x24, 0x4e2090, receiver, {run.get(incoming)})) {
            uint32_t application = run.get(0x5371fc);
            uint32_t width = run.get(application + 0x7c);
            uint32_t height = run.get(application + 0x80);
            // +0x6c..+0x78 is the popup rectangle.
            uint32_t popupWidth = run.get(receiver + 0x74) - run.get(receiver + 0x6c);
            uint32_t popupHeight = run.get(receiver + 0x78) - run.get(receiver + 0x70);
            uint32_t halfWidth = uint32_t(s32(popupWidth) / 2);
            run.put(run.automatic(0x4), halfWidth);
            run.put(receiver + 0x294, uint32_t(s32(width) / 2) - halfWidth);
            run.put(receiver + 0x298, uint32_t(s32(height) / 2) - uint32_t(s32(popupHeight) / 2));
            if (virtualAt(run, -0x20, receiver, 0x220) && virtualAt(run, -0x20, receiver, 0x224))
                result = 1;
        }
    }
    callAt(run, -0x20, 0x4f6584, incoming);
    return result;
}

// 0x424b90. Select the state-specific directory through the original archive lookup.
uint32_t selectDirectory(Run &run, uint32_t receiver) {
    if (!run.get(receiver + 0x2a4) || !run.get(receiver + 0x2a0))
        return 0;
    uint32_t name = run.automatic(-0x10);
    callAt(run, -0x1c, 0x4f65f2, name, {0x5254f4});
    bool inGame = virtualAt(run, -0x18, run.get(run.get(receiver + 0x2a0) + 0x164), 0x10) == 11;
    if (!inGame)
        inGame = virtualAt(run, -0x18, run.get(run.get(receiver + 0x2a0) + 0x164), 0x10) == 3;
    if (!inGame)
        inGame = virtualAt(run, -0x18, run.get(run.get(receiver + 0x2a0) + 0x164), 0x10) == 4;
    if (inGame)
        callAt(run, -0x1c, 0x4f66cc, name, {0x5254ec});
    uint32_t directory = callAt(run, -0x1c, 0x4b7f20, run.get(receiver + 0x2a4), {run.get(name)});
    run.put(receiver + 0x2a8, directory);
    callAt(run, -0x18, 0x4f6584, name);
    return directory != 0;
}

// 0x424ca0. Resolve image metadata and its signed frame range, selecting frame 1.
uint32_t resolveImage(Run &run, uint32_t receiver) {
    uint32_t directory = run.get(receiver + 0x2a8);
    if (!directory || !run.get(receiver + 0x2a0))
        return 0;
    uint32_t resource = callAt(run, -0x1c, 0x4b7cd0, directory, {run.get(receiver + 0x2b0)});
    uint32_t output = run.automatic(-0x4);
    run.put(output, resource);
    if (!resource)
        return 0;
    uint32_t services = run.get(run.get(receiver + 0x2a0) + 0xc);
    uint32_t manager = run.get(services + 0x10);
    uint32_t method = run.get(run.get(manager) + 0x48);
    uint32_t buffer = callAt(run, -0x20, 0x4f6974, receiver + 0x2ac, {1});
    callAt(run, -0x24, method, manager, {run.get(output), buffer, 0x523728});
    uint32_t name = run.get(receiver + 0x2ac);
    uint32_t map = run.get(services + 0x10) + 0x10;
    run.put(output, 0);
    callAt(run, -0x20, 0x4f6286, map, {name, output});
    uint32_t metadata = run.get(output);
    uint32_t image = 0;
    if (metadata && run.gets(metadata + 0x64) <= 1 && run.gets(metadata + 0x68) >= 1)
        image = run.get(run.get(metadata + 0x14) + 0x4);
    run.put(receiver + 0x29c, image);
    return image != 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x438c40:
        return initializeMenu(run, receiver, arguments);
    case 0x4399d0:
        return createSelected(run, receiver, arguments[0]);
    case 0x4236c0:
        return construct(run, receiver, arguments[0], arguments[1]);
    case 0x423840:
        return initializePopup(run, receiver, arguments);
    case 0x424b90:
        return selectDirectory(run, receiver);
    case 0x424ca0:
        return resolveImage(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_menu_popup_construction_entry, owned, body)
