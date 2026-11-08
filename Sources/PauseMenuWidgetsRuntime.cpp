// Level 1 in-game pause menu: IFC widget callback 0x4529f0 and widget name lookup 0x4508d0
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4529f0:
        return 1;
    case 0x4508d0:
        return 3;
    default:
        return -1;
    }
}

// CString helpers (original code, run on both sides).
// 0x4f6439 default constructor, 0x4f6449 copy constructor, 0x4f6584 release,
// 0x4f4c93 Find(const char *), 0x4f66cc operator=(const char *), 0x4f6a1d MakeLower.

// Search `needle` (a string in the image data section) in the lower-cased copy.
bool found(Run &run, uint32_t copy, uint32_t needle) {
    uint32_t position = run.call(0x4f4c93, copy, {needle});
    return position != 0xffffffffu;
}

// Applies `*number += (flag == 0)` for a sub-test, reading the flag from the
// application object [receiver + 4] at `flagOffset`.
// The flag is read first, then the number is read again.
void adjustNumber(Run &run, uint32_t receiver, uint32_t flagOffset, uint32_t number) {
    uint32_t application = run.get(receiver + 0x4);
    uint32_t flag = run.get(application + flagOffset);
    uint32_t value = run.get(number);
    if (flag == 0)
        value = value + 1;
    run.put(number, value);
}

// 0x4508d0. thiscall, 3 stack arguments: CString by value, CString *name
// (output image set name), int *number (output). Returns 1, or 0 when the name
// matches no menu. `entry` is the callee entry stack pointer relative to the
// current owned function's frame: the by-value CString is at entry + 4 and the
// local lower-cased copy at entry - 0x10.
uint32_t lookupWidget(Run &run, uint32_t receiver, int32_t entry, uint32_t name, uint32_t number) {
    uint32_t argument = run.automatic(entry + 4);
    uint32_t copy = run.automatic(entry - 0x10);
    uint32_t result = 1;
    run.call(0x4f6449, copy, {argument});
    uint32_t atoiValue = run.call(0x4a3ce0, 0, {run.get(copy)});
    run.put(number, atoiValue);
    run.call(0x4f6a1d, copy, {});
    if (found(run, copy, 0x527fa0)) {
        run.call(0x4f66cc, name, {0x527f88});
    } else if (found(run, copy, 0x527f7c)) {
        run.call(0x4f66cc, name, {0x527f5c});
    } else if (found(run, copy, 0x527f50)) {
        run.call(0x4f66cc, name, {0x527f30});
    } else if (found(run, copy, 0x527f20)) {
        run.call(0x4f66cc, name, {0x527e60});
        uint32_t current = run.get(number);
        if (current != 0x1f && current != 0x24) {
            if (found(run, copy, 0x527f18)) {
                adjustNumber(run, receiver, 0x10, number);
            } else if (found(run, copy, 0x527f10)) {
                adjustNumber(run, receiver, 0x14, number);
            } else if (found(run, copy, 0x527f08)) {
                adjustNumber(run, receiver, 0x118, number);
            } else if (found(run, copy, 0x527efc)) {
                adjustNumber(run, receiver, 0x11c, number);
            }
        }
    } else if (found(run, copy, 0x527ee8)) {
        run.call(0x4f66cc, name, {0x527ec0});
        if (found(run, copy, 0x527eb8)) {
            adjustNumber(run, receiver, 0x128, number);
        } else if (found(run, copy, 0x527eb0)) {
            adjustNumber(run, receiver, 0x120, number);
        }
    } else if (found(run, copy, 0x527ea4)) {
        run.call(0x4f66cc, name, {0x527e84});
    } else {
        result = 0;
    }
    run.call(0x4f6584, copy, {});
    run.call(0x4f6584, argument, {});
    return result;
}

// 0x4529f0. cdecl, 1 stack argument: CString by value (released here). Looks
// up the widget image set and returns the frame's field at +0x2c, or 0.
uint32_t function_4529f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t argument = run.automatic(4);
    uint32_t name = run.automatic(-0x18);
    uint32_t index = run.automatic(-0x14);
    uint32_t copy = run.automatic(-0x30);
    uint32_t slot = run.automatic(-0x10);
    uint32_t result = 0;
    run.put(index, 0);
    run.call(0x4f6439, name, {});
    run.call(0x4f6449, copy, {argument});
    uint32_t accepted = lookupWidget(run, run.get(0x53789c), -0x34, name, index);
    int32_t number = run.gets(index);
    if (accepted != 0 && number > 0 && run.get(run.get(name) - 0x8) != 0) {
        uint32_t application = run.get(0x5371fc);
        uint32_t holder = run.get(application + 0x30);
        uint32_t map = run.get(holder + 0x10) + 0x10;
        run.put(slot, 0);
        run.call(0x4f6286, map, {run.get(name), slot});
        uint32_t set = run.get(slot);
        uint32_t frame = 0;
        if (set != 0 && number >= run.gets(set + 0x64) && number <= run.gets(set + 0x68)) {
            uint32_t table = run.get(set + 0x14);
            frame = run.get(table + uint32_t(number) * 4);
        }
        if (frame != 0)
            result = run.get(frame + 0x2c);
    }
    run.call(0x4f6584, name, {});
    run.call(0x4f6584, argument, {});
    return result;
}

// 0x4508d0 as an owned entry.
uint32_t function_4508d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return lookupWidget(run, receiver, 0, arguments[1], arguments[2]);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4529f0:
        return function_4529f0(run, receiver, arguments);
    case 0x4508d0:
        return function_4508d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pause_menu_widgets_entry, owned, body)
