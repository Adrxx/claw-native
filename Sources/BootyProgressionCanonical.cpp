// Original default Booty movie and progression controller
//
// Recovered from the original instruction packet. The movie constructor call
// preserves its complete by-value descriptor and requires 31 argument slots.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40af20:
        return 0;
    case 0x40af30:
        return 1;
    case 0x40af40:
        return 2;
    case 0x40af50:
        return 3;
    case 0x40afa0:
        return 1;
    case 0x40afc0:
        return 0;
    case 0x40b330:
        return 0;
    case 0x40b6a0:
        return 3;
    case 0x40b700:
        return 0;
    case 0x40b720:
        return 1;
    case 0x40b740:
        return 0;
    case 0x40b780:
        return 0;
    case 0x40b7a0:
        return 0;
    case 0x40b7c0:
        return 0;
    case 0x40b7d0:
        return 2;
    case 0x42b140:
        return 1;
    case 0x42b4b0:
        return 0;
    case 0x42d4a0:
        return 0;
    case 0x42d4c0:
        return 0;
    case 0x48d320:
        return 1;
    case 0x48f180:
        return 0;
    case 0x4bb030:
        return 0;
    case 0x4bd240:
        return 0;
    case 0x4bd250:
        return 0;
    case 0x4ca930:
        return 0;
    case 0x4ce8b0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_40af20(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40af30(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40af40(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40af50(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40afa0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40afc0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b330(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b6a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b700(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b720(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b740(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b780(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b7a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b7c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40b7d0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_42b140(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_42b4b0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_42d4a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_42d4c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_48d320(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_48f180(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4bb030(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4bd240(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4bd250(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ca930(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ce8b0(Run &run, uint32_t receiver, const uint32_t *arguments);

uint32_t window(Run &run, uint32_t receiver) {
    return run.get(run.get(run.get(receiver + 0x04) + 0x04) + 0x04);
}

// Controller fields: +0x04 owner, +0x08 resources, +0x0c subsystem owner,
// +0x14 saved level/type, +0x20/+0x24 resource handles, +0x2c resource,
// +0x34 status, +0x3c/+0x40 resources, +0x154 current child or queued flag,
// +0x158 transition flag. All fields are 32-bit words.
// 0x40af20. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40af20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return run.get(receiver + 0x34);
}

// 0x40af30. stdcall, 1 stack argument(s), returns u32.
uint32_t function_40af30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 1;
}

// 0x40af40. stdcall, 2 stack argument(s), returns u32.
uint32_t function_40af40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x40af50. stdcall, 3 stack argument(s), returns u32.
uint32_t function_40af50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x40afa0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40afa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    function_40afc0(run, receiver, nullptr);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x40afc0. thiscall, 0 stack argument(s), returns void.
uint32_t function_40afc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x50b43c);
    function_40b700(run, receiver, nullptr);
    run.put(receiver, 0x50b4ec);
    function_48f180(run, receiver, nullptr);
    return 0;
}

// 0x40b330. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40b330(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t type = run.vcall(run.get(receiver + 0x154), 0x10);
    uint32_t old = run.get(receiver + 0x154);
    if (type == 1 || type == 3) {
        uint32_t child = run.call(0x4f63ec, 0, {type == 1 ? 0x184u : 0x16cu});
        if (child) {
            run.call(0x40b5c0, child);
            if (type == 1) {
                run.call(0x4f6439, child + 0x180);
                run.put(child, 0x50b494);
                run.put(child + 0x154, 0);
                run.put(child + 0x158, 0);
                for (uint32_t offset = 0x15c; offset <= 0x17c; offset += 4) {
                    run.put(child + offset, 0);
                }
            } else {
                run.call(0x4f6439, child + 0x15c);
                run.call(0x4f6439, child + 0x168);
                run.put(child, 0x50b544);
                run.put(child + 0x154, 0);
                run.put(child + 0x158, 0);
                run.put(child + 0x160, 0);
                run.put(child + 0x164, 0);
            }
        }
        run.put(receiver + 0x154, child);
    } else if (type == 2) {
        if (!run.get(receiver + 0x158)) {
            uint32_t scene = run.call(0x42bfd0, run.get(receiver + 0x04));
            if (scene && run.vcall(scene, 0x10) == 3) {
                if (run.get(scene + 0x258)) {
                    run.icall(0x546d50, {window(run, receiver), 0x111, 0x8023, 0});
                } else if (run.get(scene + 0x25c)) {
                    run.put(0x537360, 0);
                    run.icall(0x546d50, {window(run, receiver), 0x111, 0x8021, 0});
                } else {
                    run.icall(0x546d50, {window(run, receiver), 0x111, 0x8036, 0});
                    run.icall(0x546d50, {window(run, receiver), 0x111, 0x8075, 0});
                }
            }
            run.put(receiver + 0x158, 1);
            return 1;
        }
    } else {
        return 0;
    }
    uint32_t next = run.get(receiver + 0x154);
    uint32_t previousTable = run.get(old);
    uint32_t nextType = run.vcall(next, 0x10);
    run.call(run.get(previousTable + 0x28), old, {nextType});
    if (old) {
        run.vcall(old, 0x00, {1});
    }
    uint32_t value = run.get(receiver + 0x14);
    next = run.get(receiver + 0x154);
    uint32_t owner = run.get(receiver + 0x04);
    run.vcall(next, 0x04, {owner, value, type});
    next = run.get(receiver + 0x154);
    run.vcall(next, 0x24, {type});
    return 1;
}

// 0x40b6a0. thiscall, 3 stack argument(s), returns u32.
uint32_t function_40b6a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t result = run.call(0x48f0d0, receiver, {arguments[0], arguments[1], arguments[2]});
    if (!result) {
        return 0;
    }
    result = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523b1c});
    run.put(receiver + 0x20, result);
    if (!result) {
        return 0;
    }
    result = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523734});
    run.put(receiver + 0x24, result);
    return result != 0;
}

// 0x40b700. thiscall, 0 stack argument(s), returns void.
uint32_t function_40b700(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t subsystem = run.get(run.get(run.get(receiver + 0x0c) + 0x28) + 0x2c);
    if (subsystem) {
        run.call(0x4b4b40, subsystem);
    }
    function_48f180(run, receiver, nullptr);
    return 0;
}

// 0x40b720. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40b720(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t argument[] = {run.get(receiver + 0x14)};
    uint32_t previousFrame = run.frame;
    run.frame -= 0x08;
    function_42b140(run, run.get(receiver + 0x04), argument);
    run.frame = previousFrame;
    return 1;
}

// 0x40b740. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40b740(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!run.get(receiver + 0x154)) {
        uint32_t owner = run.get(receiver + 0x04);
        run.put(receiver + 0x154, 1);
        run.icall(0x546d50, {run.get(run.get(owner + 0x04) + 0x04), 0x111, 0x807c, 0});
    }
    return 1;
}

// 0x40b780. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40b780(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return function_4ca930(run, run.get(run.get(receiver + 0x0c) + 0x04), nullptr) != 0;
}

// 0x40b7a0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40b7a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!run.vcall(receiver, 0x0c)) {
        return 0;
    }
    return run.get(receiver + 0x2c) != 0;
}

// 0x40b7c0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40b7c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return run.vcall(receiver, 0x0c) != 0;
}

// 0x40b7d0. thiscall, 2 stack argument(s), returns u32.
uint32_t function_40b7d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t key = arguments[0];
    if ((key == 0x1b || key == 0x20 || key == 0x0d) && !run.get(receiver + 0x154)) {
        uint32_t owner = run.get(receiver + 0x04);
        run.put(receiver + 0x154, 1);
        run.icall(0x546d50, {run.get(run.get(owner + 0x04) + 0x04), 0x111, 0x807c, 0});
    }
    return 1;
}

// Movie-controller fields: +0x04 window, +0x30 graphics resources, +0x9c mode,
// +0x100 filename, +0x120 playback option. Locals retain original guest tokens.
// 0x42b140. thiscall, 1 stack argument(s), returns u32.
uint32_t function_42b140(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t previousStack = run.stackPointer;
    uint32_t base = run.automatic(-0x86c0);
    run.stackPointer = base - 0x08;
    uint32_t exists = run.call(0x48c190, 0, {run.get(receiver + 0x100)});
    run.stackPointer = previousStack;
    if (!exists) {
        return 0;
    }
    uint32_t index = arguments[0];
    uint32_t movieNumber;
    if (run.get(receiver + 0x9c)) {
        if (index != 0xfffffffeu) {
            return 0;
        }
        movieNumber = 1;
    } else {
        index += 1;
        if (s32(index) < 0 || s32(index) > 0x10) {
            return 0;
        }
        movieNumber = run.get(0x525520 + index * 4);
        if (s32(movieNumber) < 0) {
            return 1;
        }
    }
    run.put(base + 0x18, movieNumber);
    uint32_t helper = base + 0x550;
    uint32_t small = base + 0x869c;
    uint32_t movie = base + 0x1c;
    uint32_t previousFrame = run.frame;
    run.frame = base - 0x04;
    function_42b4b0(run, helper, nullptr);
    run.frame = previousFrame;
    function_42d4a0(run, small, nullptr);
    run.put(base + 0x1c, 0);
    run.put(base + 0x20, 0);
    run.put(base + 0x2c, 0);
    run.put(base + 0x30, 0);
    run.put(base + 0x34, 0);
    run.put(base + 0x38, 0);
    run.put(base + 0x28, 0);
    run.put(base + 0x3c, 0);
    run.put(base + 0x51c, 0);
    run.put(base + 0x524, 0);
    run.put(base + 0x534, 0);
    run.put(base + 0x538, 0);
    run.put(base + 0x544, 0);
    run.put(base + 0x53c, 0);
    run.put(base + 0x540, 0);
    run.put(base + 0x548, 0);
    run.put(base + 0x520, 0);
    run.put(base + 0x54c, 0);
    run.put(base + 0x518, 0);
    uint32_t resources = run.get(receiver + 0x30);
    uint32_t chain = run.get(run.get(resources + 0x04) + 0x10);
    uint32_t interface = run.get(run.get(resources + 0x1c));
    uint32_t option = run.get(resources + 0x20);
    uint32_t descriptor = run.get(chain + 0x2c);
    run.put(base + 0x10, interface);
    uint32_t optionalFlag = option ? run.get(option + 0x14) : 0;
    uint32_t result = 0;
    if (descriptor && interface) {
        run.put(base - 0x04, optionalFlag);
        run.put(base + 0x14, 1);
        uint32_t words[27];
        uint32_t descriptorValue = run.get(descriptor + 0x08);
        for (uint32_t i = 0; i < 27; ++i) {
            words[i] = run.get(descriptor + 0x0c + i * 4);
            run.put(base - 0x70 + i * 4, words[i]);
        }
        uint32_t hwnd = run.get(run.get(receiver + 0x04) + 0x04);
        run.stackPointer = base - 0x80;
        uint32_t initialized = run.call(0x4f0000, movie, {hwnd, interface, descriptorValue, words[0], words[1], words[2], words[3], words[4], words[5], words[6], words[7], words[8], words[9], words[10], words[11], words[12], words[13], words[14], words[15], words[16], words[17], words[18], words[19], words[20], words[21], words[22], words[23], words[24], words[25], words[26], optionalFlag});
        if (initialized) {
            uint32_t enabled = run.get(receiver + 0x120) != 0;
            uint32_t number = run.get(base + 0x18);
            uint32_t filename = run.get(receiver + 0x100);
            run.stackPointer = base - 0x1c;
            initialized = run.call(0x4f02e0, movie, {filename, number, 0, enabled, 0, 0});
            if (initialized) {
                run.stackPointer = base - 0x10;
                run.call(0x4f0380, movie, {1, 1, 0});
            }
        }
        if (!initialized) {
            run.put(base + 0x14, 0);
        }
        run.stackPointer = base - 0x04;
        run.call(0x4f0120, movie);
        run.call(0x4f0120, movie);
        function_42d4c0(run, small, nullptr);
        run.stackPointer = base - 0x04;
        run.call(0x4efcd0, helper);
        run.call(0x4f57f8, base + 0x688);
        run.call(0x4f7369, base + 0x674);
        result = run.get(base + 0x14);
    } else {
        run.stackPointer = base - 0x04;
        run.call(0x4f0120, movie);
        run.frame = base - 0x04;
        function_42d4c0(run, small, nullptr);
        run.frame = previousFrame;
        run.stackPointer = base - 0x04;
        run.call(0x4efcd0, helper);
        run.call(0x4f57f8, base + 0x688);
        run.call(0x4f7369, base + 0x674);
    }
    run.stackPointer = previousStack;
    return result;
}

// Helper object: +0x124 CRT member, +0x134 counter, +0x138 string member.
// 0x42b4b0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_42b4b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t previousStack = run.stackPointer;
    run.stackPointer = run.automatic(-0x1c);
    run.call(0x4f72c9, receiver + 0x124);
    run.call(0x4f57c5, receiver + 0x138);
    run.put(receiver, 0);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x134, 0);
    run.stackPointer = run.automatic(-0x20);
    uint32_t time = run.call(0x4a3b10, 0, {0});
    run.call(0x4a3040, 0, {time});
    run.stackPointer = previousStack;
    return receiver;
}

// 0x42d4a0. thiscall, 0 stack argument(s), returns void.
uint32_t function_42d4a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x50c364);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x08, 0);
    return 0;
}

// 0x42d4c0. thiscall, 0 stack argument(s), returns void.
uint32_t function_42d4c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x50c364);
    uint32_t allocation = run.get(receiver + 0x04);
    if (allocation) {
        run.call(0x4f6428, 0, {allocation});
    }
    run.put(receiver, 0x50becc);
    return 0;
}

// 0x48d320. thiscall, 1 stack argument(s), returns u32.
uint32_t function_48d320(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t previousStack = run.stackPointer;
    uint32_t object = run.get(receiver + 0x2c);
    if (object) {
        run.stackPointer = run.automatic(-0x24);
        run.call(0x4bb990, run.get(object + 0x10), {0, 0x100, 0, 0, 0, 0x1f4});
        run.stackPointer = run.automatic(-0x10);
        uint32_t graphics = run.get(run.get(receiver + 0x0c) + 0x04);
        run.call(0x4b97c0, run.get(run.get(graphics + 0x14) + 0x2c), {0});
        run.call(0x4b98b0, run.get(run.get(graphics + 0x10) + 0x2c), {0});
        graphics = run.get(run.get(receiver + 0x0c) + 0x04);
        run.call(0x4b97c0, run.get(run.get(graphics + 0x14) + 0x2c), {0});
        run.call(0x4b98b0, run.get(run.get(graphics + 0x10) + 0x2c), {0});
    }
    run.stackPointer = previousStack;
    return 1;
}

// 0x48f180. thiscall, 0 stack argument(s), returns void.
uint32_t function_48f180(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t owner = run.get(receiver + 0x0c);
    if (owner) {
        uint32_t resource = run.get(receiver + 0x2c);
        if (resource) {
            run.call(0x4d46f0, run.get(owner + 0x18), {resource});
            run.put(receiver + 0x2c, 0);
        }
    }
    owner = run.get(receiver + 0x0c);
    if (owner) {
        uint32_t resource = run.get(receiver + 0x3c);
        if (resource) {
            run.call(0x4bc4f0, run.get(owner + 0x1c), {resource});
            run.put(receiver + 0x3c, 0);
        }
        resource = run.get(receiver + 0x40);
        if (resource) {
            run.call(0x4bc4f0, run.get(run.get(receiver + 0x0c) + 0x1c), {resource});
            run.put(receiver + 0x40, 0);
        }
    }
    run.put(receiver + 0x34, 0);
    return 0;
}

// 0x4bb030. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4bb030(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x4bd240. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4bd240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 2;
}

// 0x4bd250. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4bd250(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 1;
}

// 0x4ca930. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4ca930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t subsystem = run.get(receiver + 0x10);
    if (subsystem && !run.call(0x4d56d0, subsystem)) {
        return 0;
    }
    subsystem = run.get(receiver + 0x18);
    if (subsystem && !run.call(0x4d4240, subsystem)) {
        return 0;
    }
    return 1;
}

// 0x4ce8b0. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4ce8b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 10;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40af20:
        return function_40af20(run, receiver, arguments);
    case 0x40af30:
        return function_40af30(run, receiver, arguments);
    case 0x40af40:
        return function_40af40(run, receiver, arguments);
    case 0x40af50:
        return function_40af50(run, receiver, arguments);
    case 0x40afa0:
        return function_40afa0(run, receiver, arguments);
    case 0x40afc0:
        return function_40afc0(run, receiver, arguments);
    case 0x40b330:
        return function_40b330(run, receiver, arguments);
    case 0x40b6a0:
        return function_40b6a0(run, receiver, arguments);
    case 0x40b700:
        return function_40b700(run, receiver, arguments);
    case 0x40b720:
        return function_40b720(run, receiver, arguments);
    case 0x40b740:
        return function_40b740(run, receiver, arguments);
    case 0x40b780:
        return function_40b780(run, receiver, arguments);
    case 0x40b7a0:
        return function_40b7a0(run, receiver, arguments);
    case 0x40b7c0:
        return function_40b7c0(run, receiver, arguments);
    case 0x40b7d0:
        return function_40b7d0(run, receiver, arguments);
    case 0x42b140:
        return function_42b140(run, receiver, arguments);
    case 0x42b4b0:
        return function_42b4b0(run, receiver, arguments);
    case 0x42d4a0:
        return function_42d4a0(run, receiver, arguments);
    case 0x42d4c0:
        return function_42d4c0(run, receiver, arguments);
    case 0x48d320:
        return function_48d320(run, receiver, arguments);
    case 0x48f180:
        return function_48f180(run, receiver, arguments);
    case 0x4bb030:
        return function_4bb030(run, receiver, arguments);
    case 0x4bd240:
        return function_4bd240(run, receiver, arguments);
    case 0x4bd250:
        return function_4bd250(run, receiver, arguments);
    case 0x4ca930:
        return function_4ca930(run, receiver, arguments);
    case 0x4ce8b0:
        return function_4ce8b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_booty_progression_entry, owned, body)
