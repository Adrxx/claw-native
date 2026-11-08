// Observed Level 1 level object actions batch 3
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46caf0:
        return 0;
    case 0x46cb40:
        return 1;
    case 0x46d520:
        return 1;
    case 0x473630:
        return 1;
    case 0x473660:
        return 2;
    case 0x473ae0:
        return 1;
    case 0x473b10:
        return 1;
    case 0x486940:
        return 5;
    default:
        return -1;
    }
}

// Pure mapping used by the jump tables at 0x46d520, 0x473b10 and 0x46cb40:
// an object kind maps to a counter slot 0..8, or -1.
uint32_t categoryOf(uint32_t kind) {
    if (kind - 1 > 0x33)
        return 0xffffffffu;
    switch (kind) {
    case 0x21:
        return 0;
    case 1:
        return 1;
    case 2:
    case 3:
    case 4:
    case 5:
        return 2;
    case 0x29:
    case 0x2a:
    case 0x2b:
    case 0x2c:
        return 3;
    case 7:
    case 8:
    case 9:
    case 10:
        return 4;
    case 0xb:
    case 0xc:
    case 0xd:
    case 0xe:
        return 5;
    case 0xf:
    case 0x10:
    case 0x11:
    case 0x12:
        return 6;
    case 0x2d:
    case 0x2e:
    case 0x2f:
    case 0x30:
        return 7;
    case 0x31:
    case 0x32:
    case 0x33:
    case 0x34:
        return 8;
    default:
        return 0xffffffffu;
    }
}

// Increments counter `slot` of the nine dwords at 0x5381e0 when 0 <= slot < 9.
void bump(Run &run, uint32_t slot) {
    if (s32(slot) < 0)
        return;
    if (s32(slot) >= 9)
        return;
    uint32_t count = run.get(0x5381e0 + slot * 4);
    run.put(0x5381e0 + slot * 4, count + 1);
}

// 0x46d520. Maps the argument as a kind to a counter slot.
uint32_t function_46d520(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    return categoryOf(arguments[0]);
}

// 0x473b10. Finds the object in the table at 0x537ec8 and maps its index.
uint32_t function_473b10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    if (object == 0)
        return 0xffffffffu;
    uint32_t count = run.get(0x52a190);
    uint32_t index = 0;
    if (s32(count) <= 0)
        return 0xffffffffu;
    uint32_t entry = 0x537ec8;
    while (run.get(entry) != object) {
        index = index + 1;
        entry = entry + 4;
        if (s32(index) >= s32(count))
            return 0xffffffffu;
    }
    if (index == 0)
        index = 0x21;
    return categoryOf(index);
}

// 0x46cb40. Registered callback: counts the kind of one object, and of the
// kinds held by its action record, in the table at 0x5381e0.
uint32_t function_46cb40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    if (object == 0)
        return 0;
    // Virtual method at vtable +0x20 returns the object class; 5 is wanted.
    uint32_t objectClass = run.vcall(object, 0x20);
    if (objectClass != 5)
        return 0;
    uint32_t record = run.get(object + 0x6c);
    if (record == 0)
        return 0;
    uint32_t handler = run.get(record + 0x10);
    if (handler == 0x49ee30)
        return 0;
    if (handler == 0x471530 || handler == 0x471720 || handler == 0x471750) {
        uint32_t kind = run.get(object + 0x100);
        if (kind == 0)
            kind = 0x21;
        bump(run, categoryOf(kind));
        return 0;
    }
    uint32_t target = 0;
    bool lookup = false;
    if (handler == 0x46fd10) {
        lookup = true;
    } else if (handler == 0x470100) {
        lookup = true;
    } else if (handler == 0x470430) {
        lookup = true;
    } else if (handler == 0x471330) {
        lookup = true;
    } else if (handler == 0x470d00) {
        lookup = true;
    } else if (handler == 0x470f00) {
        lookup = true;
    } else if (handler == 0x471100) {
        lookup = true;
    }
    if (lookup) {
        target = run.get(object + 0x170);
        uint32_t slot = function_473b10(run, 0, &target);
        bump(run, slot);
        return 0;
    }
    // Any other handler: count the object's own kind and the six-plus kinds
    // stored in the record at +0xf0..+0x10c.
    uint32_t kind = run.get(object + 0x100);
    bump(run, categoryOf(kind));
    kind = run.get(record + 0xf0);
    bump(run, categoryOf(kind));
    kind = run.get(record + 0xf4);
    bump(run, categoryOf(kind));
    kind = run.get(record + 0xf8);
    bump(run, categoryOf(kind));
    kind = run.get(record + 0xfc);
    bump(run, categoryOf(kind));
    kind = run.get(record + 0x100);
    bump(run, function_46d520(run, 0, &kind));
    kind = run.get(record + 0x104);
    bump(run, function_46d520(run, 0, &kind));
    kind = run.get(record + 0x108);
    bump(run, function_46d520(run, 0, &kind));
    kind = run.get(record + 0x10c);
    bump(run, function_46d520(run, 0, &kind));
    return 0;
}

// 0x46caf0. thiscall. Clears the nine counters, then walks the level's
// action list with the counting callback.
uint32_t function_46caf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0xc) == 0)
        return 0;
    for (uint32_t i = 0; i < 9; ++i)
        run.put(0x5381e0 + i * 4, 0);
    uint32_t level = run.get(receiver + 0xc);
    uint32_t owner = run.get(level + 0x24);
    if (owner == 0)
        return 0;
    uint32_t list = run.get(owner + 0x5c);
    if (list == 0)
        return 0;
    uint32_t walker = run.get(list + 0xb0);
    if (walker == 0)
        return 0;
    run.call(0x4d51f0, walker, {0x46cb40});
    return 0;
}

// 0x473630. Name of entry `index` (object + 0x24), or the fallback string.
uint32_t function_473630(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t index = arguments[0];
    uint32_t count = run.get(0x52a190);
    if (s32(index) >= s32(count))
        return 0x5279b8;
    if (s32(index) < 0)
        return 0x5279b8;
    return run.get(0x537ec8 + index * 4) + 0x24;
}

// 0x473660. Installs the handler of table entry `index` into the object's
// record and calls it with the object.
uint32_t function_473660(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t index = arguments[1];
    uint32_t count = run.get(0x52a190);
    if (s32(index) >= s32(count))
        return 0;
    if (s32(index) < 0)
        return 0;
    uint32_t entry = run.get(0x538208 + index * 4);
    uint32_t record = run.get(object + 0x6c);
    uint32_t handler = run.get(entry + 0x10);
    run.put(record + 0x10, handler);
    record = run.get(object + 0x6c);
    run.put(record + 0x1c, 0);
    record = run.get(object + 0x6c);
    run.call(run.get(record + 0x10), 0, {object});
    return 1;
}

// 0x473ae0. Flags the object: +0x164 |= 0x200 and +8 |= 1.
uint32_t function_473ae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t flags = run.get(object + 0x164);
    run.put(object + 0x164, flags | 0x200);
    uint32_t state = run.get(object + 8);
    run.put(object + 8, state | 1);
    return 1;
}

// Moves a signed coordinate toward its target by the scaled delta, clamped.
// `step` is (delta * [0x5430c4]) * 0x10624dd3 >> 38 (unsigned high half).
uint32_t scaledStep(Run &run, uint32_t delta) {
    uint32_t scaled = delta * run.get(0x5430c4);
    uint64_t product = uint64_t(scaled) * 0x10624dd3u;
    return uint32_t(product >> 32) >> 6;
}

// 0x486940. Moves the point {x, y} at arg3 toward the target {+8, +0xc}.
uint32_t function_486940(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t point = arguments[2];
    uint32_t xDelta = arguments[3];
    uint32_t yDelta = arguments[4];
    uint32_t fixedX = run.get(0x52be14);
    if (fixedX != 0xffffffffu) {
        run.put(point + 8, fixedX);
        uint32_t fixedY = run.get(0x52be18);
        run.put(point + 0xc, fixedY);
    }
    uint32_t x = run.get(point);
    uint32_t targetX = run.get(point + 8);
    if (s32(x) < s32(targetX)) {
        uint32_t next = scaledStep(run, xDelta) + x;
        run.put(point, next);
        if (s32(next) > s32(targetX))
            run.put(point, targetX);
    } else if (s32(x) > s32(targetX)) {
        uint32_t next = x - scaledStep(run, xDelta);
        run.put(point, next);
        if (s32(next) < s32(targetX))
            run.put(point, targetX);
    }
    uint32_t y = run.get(point + 4);
    uint32_t targetY = run.get(point + 0xc);
    if (s32(y) < s32(targetY)) {
        uint32_t next = scaledStep(run, yDelta) + y;
        run.put(point + 4, next);
        if (s32(next) > s32(targetY))
            run.put(point + 4, targetY);
        return 0;
    }
    if (s32(y) > s32(targetY)) {
        uint32_t next = y - scaledStep(run, yDelta);
        run.put(point + 4, next);
        if (s32(next) < s32(targetY))
            run.put(point + 4, targetY);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46caf0:
        return function_46caf0(run, receiver, arguments);
    case 0x46cb40:
        return function_46cb40(run, receiver, arguments);
    case 0x46d520:
        return function_46d520(run, receiver, arguments);
    case 0x473630:
        return function_473630(run, receiver, arguments);
    case 0x473660:
        return function_473660(run, receiver, arguments);
    case 0x473ae0:
        return function_473ae0(run, receiver, arguments);
    case 0x473b10:
        return function_473b10(run, receiver, arguments);
    case 0x486940:
        return function_486940(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_object_actions_03_entry, owned, body)
