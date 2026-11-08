// Pause menu key, pointer and command handlers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x450460:
        return 2;
    case 0x450850:
        return 3;
    case 0x450cf0:
        return 1;
    case 0x450c50:
        return 3;
    case 0x451e10:
        return 2;
    case 0x452050:
        return 1;
    case 0x452080:
        return 1;
    default:
        return -1;
    }
}

// Outside call at an explicit callee-entry ESP (return word included).
uint32_t callAt(Run &run, uint32_t entryEsp, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = entryEsp;
    return run.call(function, receiver, arguments);
}

uint32_t vcallAt(Run &run, uint32_t entryEsp, uint32_t object, uint32_t slotOffset) {
    uint32_t vtable = run.get(object);
    uint32_t method = run.get(vtable + slotOffset);
    return callAt(run, entryEsp, method, object);
}

// Looks up a sound by name in the table at obj+0x10 and plays it when the
// sound system is on. `sp` is the ESP before the pushes, `local` the stack
// slot receiving the found entry. obj+0x30 is a mute flag; 0x532c0c is the
// sound-enabled global and 0x532c10 the sound id passed on.
void playSound(Run &run, uint32_t sp, uint32_t obj, uint32_t name, uint32_t local) {
    if (run.get(obj + 0x30) != 0)
        return;
    run.put(local, 0);
    callAt(run, sp - 0xc, 0x4f6286, obj + 0x10, {name, local});
    uint32_t found = run.get(local);
    if (found == 0)
        return;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t soundId = run.get(0x532c10);
    if (enabled == 0)
        return;
    uint32_t target = run.get(found + 0x10);
    callAt(run, sp - 0x14, 0x4b45f0, target, {soundId, 0, 0, 0});
}

// Forward declarations of owned functions.
uint32_t function_450c50(Run &run, uint32_t receiver, uint32_t a, uint32_t wparam, uint32_t notify);
uint32_t function_450cf0(Run &run, uint32_t receiver, uint32_t a);
void function_451e10(Run &run, uint32_t receiver, uint32_t key, uint32_t unused);
uint32_t function_452050(Run &run, uint32_t receiver, uint32_t name);
void function_452080(Run &run, uint32_t receiver, uint32_t flag);

// 0x450460. thiscall, 2 stack arguments (key, second), returns u32.
// this+0x154 is the menu list; this+0x258 / +0x25c are two objects whose +0x50
// is set to the selected entry's field plus 0x11.
uint32_t function_450460(Run &run, uint32_t receiver, uint32_t key, uint32_t second) {
    uint32_t entry = run.frame;
    uint32_t list = receiver + 0x154;
    uint32_t result = 1;
    // ESP after prologue: sub 8 and four pushes.
    uint32_t sp = entry - 0x18;
    uint32_t before = callAt(run, sp - 4, 0x4dd480, list);
    uint32_t keyValue = key;
    uint32_t index = keyValue - 0xd;
    int kind = 0; // 0 default, 1 select, 2 escape, 3 left, 4 up, 5 right, 6 down
    if (index <= 0x1b) {
        switch (keyValue) {
        case 0xd:
        case 0x20:
            kind = 1;
            break;
        case 0x1b:
            kind = 2;
            break;
        case 0x25:
            kind = 3;
            break;
        case 0x26:
            kind = 4;
            break;
        case 0x27:
            kind = 5;
            break;
        case 0x28:
            kind = 6;
            break;
        default:
            kind = 0;
            break;
        }
    }
    switch (kind) {
    case 1:
        callAt(run, sp - 4, 0x4ddbc0, list);
        result = 0;
        break;
    case 2: {
        result = 0;
        uint32_t current = callAt(run, sp - 4, 0x4dd0c0, list);
        if (current != 0) {
            uint32_t savedFrame = run.frame;
            run.frame = sp - 8;
            function_450cf0(run, receiver, 0x4e21);
            run.frame = savedFrame;
        }
        break;
    }
    case 3:
    case 5: {
        uint32_t savedFrame = run.frame;
        run.frame = sp - 8;
        function_452080(run, receiver, kind == 3 ? 1 : 0);
        run.frame = savedFrame;
        break;
    }
    case 4:
        vcallAt(run, sp - 4, list, 0);
        break;
    case 6:
        vcallAt(run, sp - 4, list, 4);
        break;
    default: {
        uint32_t secondValue = second;
        uint32_t savedFrame = run.frame;
        run.frame = sp - 0xc;
        function_451e10(run, receiver, keyValue, secondValue);
        run.frame = savedFrame;
        break;
    }
    }
    if (result == 0)
        return result;
    uint32_t after = callAt(run, sp - 4, 0x4dd480, list);
    if (before == after)
        return result;
    uint32_t selectedIndex = callAt(run, sp - 4, 0x4dd480, list);
    uint32_t item = callAt(run, sp - 8, 0x4dd450, list, {selectedIndex});
    if (item == 0)
        return result;
    uint32_t globalRoot = run.get(0x5371fc);
    uint32_t level1 = run.get(globalRoot + 0x30);
    uint32_t level2 = run.get(level1 + 0x28);
    playSound(run, sp, level2, 0x524678, entry + 4);
    callAt(run, sp - 8, 0x4ded20, item, {entry - 8});
    uint32_t object1 = run.get(receiver + 0x258);
    uint32_t value1 = run.get(entry - 4);
    run.put(object1 + 0x50, value1 + 0x11);
    uint32_t value2 = run.get(entry - 4);
    uint32_t object2 = run.get(receiver + 0x25c);
    run.put(object2 + 0x50, value2 + 0x11);
    return result;
}

// 0x450850. thiscall, 3 stack arguments (ignored), returns 1.
uint32_t function_450850(Run &run, uint32_t receiver) {
    uint32_t entry = run.frame;
    uint32_t list = receiver + 0x154;
    // sub 8 and three pushes.
    uint32_t sp = entry - 0x14;
    uint32_t before = callAt(run, sp - 4, 0x4dd480, list);
    callAt(run, sp - 4, 0x4ddc30, list);
    uint32_t after = callAt(run, sp - 4, 0x4dd480, list);
    if (before == after)
        return 1;
    uint32_t selectedIndex = callAt(run, sp - 4, 0x4dd480, list);
    uint32_t item = callAt(run, sp - 8, 0x4dd450, list, {selectedIndex});
    if (item == 0)
        return 1;
    callAt(run, sp - 8, 0x4ded20, item, {entry - 8});
    uint32_t object1 = run.get(receiver + 0x258);
    uint32_t value1 = run.get(entry - 4);
    run.put(object1 + 0x50, value1 + 0x11);
    uint32_t value2 = run.get(entry - 4);
    uint32_t object2 = run.get(receiver + 0x25c);
    run.put(object2 + 0x50, value2 + 0x11);
    return 1;
}

// 0x450cf0. thiscall, 1 stack argument, returns 1.
uint32_t function_450cf0(Run &run, uint32_t receiver, uint32_t a) {
    uint32_t entry = run.frame;
    // push esi
    uint32_t sp = entry - 4;
    uint32_t command = a;
    uint32_t wparam;
    if (command == 0x4e21) {
        uint32_t level1 = run.get(receiver + 4);
        uint32_t level2 = run.get(level1 + 0x30);
        uint32_t obj = run.get(level2 + 0x28);
        playSound(run, sp, obj, 0x5279e4, entry + 4);
        run.put(receiver + 0x2a8, 1);
        wparam = 0x8036;
    } else if (command == 0x4e24) {
        uint32_t level1 = run.get(receiver + 4);
        uint32_t level2 = run.get(level1 + 0x30);
        uint32_t obj = run.get(level2 + 0x28);
        playSound(run, sp, obj, 0x5279e4, entry + 4);
        callAt(run, sp - 8, 0x4b8960, 0, {500});
        wparam = 0x8035;
    } else {
        uint32_t savedFrame = run.frame;
        run.frame = sp - 0x10;
        uint32_t value = function_450c50(run, receiver, command, 0xffffffff, 1);
        run.frame = savedFrame;
        return value;
    }
    uint32_t menu = run.get(receiver + 4);
    uint32_t window = run.get(menu + 4);
    uint32_t handle = run.get(window + 4);
    callAt(run, sp - 0x18, 0x546d50, 0, {handle, 0x111, wparam, 0});
    return 1;
}

// 0x450c50. thiscall, 3 stack arguments (a, wparam, notify), returns 1.
uint32_t function_450c50(Run &run, uint32_t receiver, uint32_t a, uint32_t wparam, uint32_t notify) {
    uint32_t entry = run.frame;
    // push ecx, push esi
    uint32_t sp = entry - 8;
    uint32_t level1 = run.get(receiver + 4);
    uint32_t level2 = run.get(level1 + 0x30);
    uint32_t obj = run.get(level2 + 0x28);
    playSound(run, sp, obj, 0x5279e4, entry - 4);
    uint32_t postParam = wparam;
    if (s32(postParam) > 0) {
        uint32_t menu = run.get(receiver + 4);
        uint32_t window = run.get(menu + 4);
        uint32_t handle = run.get(window + 4);
        callAt(run, sp - 0x14, 0x546d50, 0, {handle, 0x111, postParam, 0});
    }
    uint32_t notifyValue = notify;
    if (notifyValue != 0) {
        uint32_t first = a;
        callAt(run, sp - 8, 0x451680, receiver, {first});
    }
    return 1;
}

// 0x452050. thiscall, 1 stack argument, returns the value stored by the lookup
// in this+0x2b4 for the name, or 0.
uint32_t function_452050(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t entry = run.frame;
    // push ecx; the local lives in that slot.
    uint32_t sp = entry - 4;
    uint32_t nameValue = name;
    run.put(sp, 0);
    uint32_t found = callAt(run, sp - 0xc, 0x4f6286, receiver + 0x2b4, {nameValue, sp});
    uint32_t value = run.get(sp);
    uint32_t mask = found != 0 ? 0xffffffffu : 0;
    return mask & value;
}

// 0x452080. thiscall, 1 stack argument, returns nothing.
void function_452080(Run &run, uint32_t receiver, uint32_t flag) {
    uint32_t entry = run.frame;
    // push esi, push edi
    uint32_t sp = entry - 8;
    uint32_t list = receiver + 0x154;
    uint32_t selectedIndex = callAt(run, sp - 4, 0x4dd480, list);
    uint32_t item = callAt(run, sp - 8, 0x4dd450, list, {selectedIndex});
    if (item == 0)
        return;
    uint32_t kind = run.get(item + 0x14);
    if (kind >= 0x5aa1 && kind <= 0x5aa4) {
        uint32_t flagValue = flag;
        uint32_t direction = (flagValue != 0 ? 1u : 0u) + 1;
        callAt(run, sp - 0xc, 0x452290, receiver, {direction, kind});
        return;
    }
    if (kind >= 0x5b05 && kind <= 0x5b07) {
        uint32_t flagValue = flag;
        uint32_t direction = (flagValue != 0 ? 1u : 0u) + 1;
        callAt(run, sp - 0xc, 0x4520f0, receiver, {direction, kind});
    }
}

// 0x451e10. thiscall, 2 stack arguments (key, unused), returns nothing.
// Walks the entries of the current list and activates the one whose looked-up
// code equals the key. The original also registers an SEH frame; native code
// has no exception transport so only its stack slots are mirrored.
void function_451e10(Run &run, uint32_t receiver, uint32_t key, uint32_t unused) {
    (void)unused;
    uint32_t entry = run.frame;
    // push -1, handler, fs head; sub 0x10; four pushes.
    uint32_t sp = entry - 0x2c;
    uint32_t stateSlot = entry - 4;
    uint32_t listSlot = entry - 0x10;
    uint32_t objectSlot = entry - 0x18;
    uint32_t countSlot = entry - 0x14;
    uint32_t tempSlot = entry - 0x1c;
    run.put(stateSlot, 0xffffffff);
    run.put(entry - 8, 0x506778);
    run.put(listSlot, receiver + 0x154);
    uint32_t list = run.get(listSlot);
    uint32_t container = callAt(run, sp - 4, 0x4dd0c0, list);
    run.put(objectSlot, container);
    if (container == 0)
        return;
    uint32_t count = callAt(run, sp - 4, 0x4df480, container);
    run.put(countSlot, count);
    if (s32(count) <= 0)
        return;
    uint32_t index = 0;
    while (true) {
        uint32_t item = callAt(run, sp - 8, 0x4df260, container, {index});
        if (item != 0) {
            uint32_t holder = callAt(run, sp - 8, 0x4df460, item, {tempSlot});
            uint32_t name = run.get(holder);
            run.put(stateSlot, 0);
            uint32_t savedFrame = run.frame;
            run.frame = sp - 8;
            uint32_t code = function_452050(run, receiver, name);
            run.frame = savedFrame;
            uint32_t wanted = key;
            bool matched = code == wanted;
            run.put(stateSlot, 0xffffffff);
            callAt(run, sp - 4, 0x4f6584, tempSlot);
            if (matched) {
                uint32_t target = item + 0x3c;
                if (target != 0) {
                    uint32_t flags = callAt(run, sp - 4, 0x4ed050, target);
                    if ((flags & 0x20) == 0) {
                        uint32_t menu = run.get(listSlot);
                        callAt(run, sp - 8, 0x4dd520, menu, {target});
                        callAt(run, sp - 4, 0x4ddbc0, menu);
                    }
                }
                return;
            }
            container = run.get(objectSlot);
        }
        ++index;
        uint32_t limit = run.get(countSlot);
        if (!(s32(index) < s32(limit)))
            break;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x450460:
        return function_450460(run, receiver, arguments[0], arguments[1]);
    case 0x450850:
        return function_450850(run, receiver);
    case 0x450cf0:
        return function_450cf0(run, receiver, arguments[0]);
    case 0x450c50:
        return function_450c50(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x451e10:
        function_451e10(run, receiver, arguments[0], arguments[1]);
        return 0;
    case 0x452050:
        return function_452050(run, receiver, arguments[0]);
    case 0x452080:
        function_452080(run, receiver, arguments[0]);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pause_menu_input_entry, owned, body)
