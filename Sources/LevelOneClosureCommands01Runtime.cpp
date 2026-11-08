// Level 1 closure: level end, special command and application command helpers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Records the callee-entry ESP for the next outgoing call. `esp` is the
// original ESP, relative to this function's entry ESP, just before its CALL.
void enter(Run &run, int32_t esp) {
    run.stackPointer = run.automatic(esp - 4);
}

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46bc90:
        return 0;
    case 0x46bcf0:
        return 0;
    case 0x46bdb0:
        return 0;
    case 0x42abb0:
        return 0;
    case 0x42b910:
        return 0;
    case 0x42d520:
        return 1;
    case 0x42a570:
        return 1;
    case 0x4b5c00:
        return 2;
    case 0x4b5c10:
        return 0;
    case 0x4b5e50:
        return 2;
    case 0x4373d0:
        return 2;
    case 0x49c860:
        return 2;
    default:
        return -1;
    }
}

// 0x42abb0. Object fields: +0x04 window owner (its +0x04 is the window),
// +0x08 application (its +0x244 is a flag), +0xa0 closing flag.
uint32_t function_42abb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0xa0) != 0)
        return 0;
    uint32_t application = run.get(receiver + 0x8);
    run.put(receiver + 0xa0, 1);
    if (application != 0)
        run.put(application + 0x244, 0);
    uint32_t owner = run.get(receiver + 0x4);
    if (owner == 0)
        return 0;
    uint32_t window = run.get(owner + 0x4);
    enter(run, -0x10);
    run.icall(0x546d50, {window, 0x10, 0, 0});
    return 0;
}

// 0x46bdb0. Object fields: +0x04 owner (+0x60 and +0x64 helper objects),
// +0x164 value, +0x168 flags (bit 0), +0x258 busy flag.
uint32_t function_46bdb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t global = run.get(0x537e88);
    if (global == 0)
        return 0;
    enter(run, -0x54);
    run.call(0x415d90, 0, {global});
    uint32_t helper = run.get(run.get(receiver + 0x4) + 0x64);
    if (helper != 0 && run.get(receiver + 0x258) == 0) {
        // Local record of 0x44 bytes at entry ESP - 0x44, cleared dword by dword.
        uint32_t record = run.automatic(-0x44);
        for (uint32_t index = 0; index < 0x11; ++index)
            run.put(record + index * 4, 0);
        enter(run, -0x5c);
        run.call(0x49a9d0, 0, {record, 0x534d30, run.get(receiver + 0x164)});
        if ((run.get8(receiver + 0x168) & 1) == 0) {
            enter(run, -0x58);
            uint32_t found = run.call(0x49a800, helper, {0, record});
            if (found != 0) {
                enter(run, -0x50);
                run.call(0x49bbc0, run.get(run.get(receiver + 0x4) + 0x60), {});
            }
        }
    }
    return 1;
}

// 0x46bcf0. Ends by waiting until four seconds after the first clock read.
uint32_t function_46bcf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t mode = 4;
    if ((run.get8(receiver + 0x168) & 1) != 0)
        mode = 3;
    uint32_t outer = run.get(receiver + 0xc);
    enter(run, -0x24);
    uint32_t object = run.call(0x4c8da0, run.get(outer + 0x8), {mode, 0, 0, 0x1869f, 0x522604, 0x200000});
    outer = run.get(receiver + 0xc);
    uint32_t second = run.get(outer + 0x8);
    uint32_t inner = run.get(outer + 0x4);
    enter(run, -0x14);
    run.call(0x4cb9b0, run.get(outer + 0x24), {run.get(inner + 0x14), second});
    outer = run.get(receiver + 0xc);
    uint32_t sink = run.get(outer + 0xc);
    inner = run.get(outer + 0x4);
    uint32_t height = run.get(inner + 0x18);
    uint32_t width = run.get(inner + 0x14);
    enter(run, -0x14);
    run.vcall(sink, 0x34, {width, height});
    if (object != 0) {
        enter(run, -0xc);
        run.call(0x46ddf0, receiver, {});
        outer = run.get(receiver + 0xc);
        inner = run.get(outer + 0x4);
        enter(run, -0x10);
        run.vcall(object, 0x2c, {run.get(inner + 0x14)});
    }
    uint32_t context = run.get(receiver + 0xc);
    uint32_t part = run.get(run.get(context + 0x4) + 0x10);
    enter(run, -0x10);
    run.call(0x4b98b0, run.get(part + 0x2c), {0});
    enter(run, -0xc);
    uint32_t start = run.icall(0x546df0);
    uint32_t deadline = start + 0xfa0;
    enter(run, -0xc);
    uint32_t now = run.icall(0x546df0);
    if (now < deadline) {
        enter(run, -0x10);
        run.call(0x4b8960, 0, {deadline - now});
    }
    return 1;
}

// 0x46bc90. Object +0x04 owner; owner +0x9c done flag, +0xc0 string member.
uint32_t function_46bc90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(run.get(receiver + 0x4) + 0x9c) == 0) {
        uint32_t outer = run.frame;
        run.frame = run.automatic(-0x8);
        uint32_t ready = function_46bdb0(run, receiver, nullptr);
        run.frame = outer;
        if (ready == 0)
            return 0;
        run.frame = run.automatic(-0x8);
        uint32_t shown = function_46bcf0(run, receiver, nullptr);
        run.frame = outer;
        if (shown == 0)
            return 0;
    }
    enter(run, -0x4);
    run.call(0x4f650f, run.get(receiver + 0x4) + 0xc0, {});
    uint32_t owner = run.get(receiver + 0x4);
    if (run.get(owner + 0x9c) != 0) {
        uint32_t outer = run.frame;
        run.frame = run.automatic(-0x8);
        function_42abb0(run, owner, nullptr);
        run.frame = outer;
    }
    return 1;
}

// 0x42b910. Object +0x9c flag.
uint32_t function_42b910(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x9c) == 0)
        return 0;
    enter(run, -0x4);
    return run.call(0x42b140, receiver, {0xfffffffe});
}

// 0x42d520. Calls the destructor body, then frees the object when bit 0 of
// the argument is set. Returns the object.
uint32_t function_42d520(Run &run, uint32_t receiver, const uint32_t *arguments) {
    enter(run, -0x4);
    run.call(0x42d4c0, receiver, {});
    if ((arguments[0] & 0xff & 1) != 0) {
        enter(run, -0x8);
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x42a570. Object fields: +0x08 application (+0x244 flag), +0x10 and +0x14
// flags, +0x2c player object, +0x30 list owner, +0x50 toolbar, +0x5c entry list.
uint32_t function_42a570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t argument = arguments[0];
    if (argument != 0) {
        uint32_t list = run.get(receiver + 0x5c);
        if (list != 0) {
            enter(run, -0x8);
            run.call(0x402520, list, {});
        }
        uint32_t first = run.get(receiver + 0x30);
        if (first != 0) {
            uint32_t second = run.get(first + 0x28);
            if (second != 0) {
                uint32_t third = run.get(second + 0x2c);
                if (third != 0) {
                    enter(run, -0x8);
                    run.call(0x4b4b40, third, {});
                }
            }
        }
        uint32_t toolbar = run.get(receiver + 0x50);
        uint32_t part = run.get(toolbar + 0x1c);
        uint32_t status = 0;
        if (part != 0) {
            enter(run, -0x8);
            status = run.call(0x4b5bd0, part, {});
        }
        if (status != 0) {
            enter(run, -0x8);
            run.call(0x4b55a0, run.get(receiver + 0x50), {});
        }
        uint32_t player = run.get(receiver + 0x2c);
        enter(run, -0x8);
        run.vcall(player, 0x4c, {});
        uint32_t application = run.get(receiver + 0x8);
        run.put(application + 0x244, 0);
        return 1;
    }
    if (run.get(receiver + 0x14) != 0) {
        enter(run, -0x8);
        uint32_t ready = run.call(0x42a630, receiver, {});
        if (ready != 0) {
            enter(run, -0xc);
            run.call(0x4b55b0, run.get(receiver + 0x50), {1});
        }
    }
    if (run.get(receiver + 0x10) != 0) {
        enter(run, -0x8);
        run.call(0x402570, run.get(receiver + 0x5c), {});
    }
    uint32_t application = run.get(receiver + 0x8);
    run.put(application + 0x244, 1);
    enter(run, -0x8);
    run.call(0x4b3ab0, run.get(0x537200), {});
    enter(run, -0x8);
    run.call(0x42abf0, receiver, {});
    return 1;
}

// 0x4b5c00. Empty stdcall stub.
uint32_t function_4b5c00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x4b5c10. Object fields: +0x18 device id, +0x40 open flag.
uint32_t function_4b5c10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x40) != 0) {
        enter(run, -0x14);
        uint32_t error = run.icall(0x546dec, {run.get(receiver + 0x18), 0x808, 2, 0});
        if (error == 0)
            return 1;
        uint32_t pair[2] = {error, 0x53245c};
        function_4b5c00(run, 0, pair);
    }
    return 0;
}

// 0x4b5e50. Object fields: +0x00 open flag, +0x18 key. The value written is
// the second stack argument, passed to the import by address.
uint32_t function_4b5e50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver) == 0)
        return 0;
    uint32_t name = arguments[0];
    if (name == 0)
        return 0;
    uint32_t value = run.automatic(0x8);
    enter(run, -0x18);
    uint32_t result = run.icall(0x546824, {run.get(receiver + 0x18), name, 0, 4, value, 4});
    if (result != 0)
        return 0;
    return 1;
}

// 0x4373d0. Builds a string in the result slot from the name argument: a name
// longer than four characters is copied to a global buffer, four characters
// are cut off and only the part after the last backslash is kept.
// Frame offsets from entry ESP: +0x04 result, +0x08 name string, -0x04 unwind
// state, -0x10 flag, -0x14 local string.
uint32_t function_4373d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t result = arguments[0];
    uint32_t name = run.automatic(0x8);
    uint32_t local = run.automatic(-0x14);
    run.put(run.automatic(-0x10), 0);
    run.put(run.automatic(-0x4), 1);
    enter(run, -0x24);
    run.call(0x4f6449, local, {name});
    run.put8(run.automatic(-0x4), 2);
    uint32_t text = run.get(name);
    uint32_t length = run.get(text - 0x8);
    if (length == 0) {
        enter(run, -0x24);
        run.call(0x4f6449, result, {local});
        run.put(run.automatic(-0x10), 1);
    } else {
        if (s32(length) > 4) {
            uint32_t count = 0;
            while (run.get8(text + count) != 0)
                ++count;
            ++count;
            uint32_t destination = 0x537368;
            uint32_t source = text;
            for (uint32_t words = count >> 2; words != 0; --words) {
                run.put(destination, run.get(source));
                source += 4;
                destination += 4;
            }
            for (uint32_t rest = count & 3; rest != 0; --rest) {
                run.put8(destination, run.get8(source));
                source += 1;
                destination += 1;
            }
            uint32_t copied = 0;
            while (run.get8(0x537368 + copied) != 0)
                ++copied;
            if (s32(copied) >= 5) {
                run.put8(copied + 0x537364, 0);
                uint32_t trimmed = 0;
                while (run.get8(0x537368 + trimmed) != 0)
                    ++trimmed;
                if (s32(trimmed) >= 1) {
                    int32_t index = s32(trimmed) - 1;
                    while (index >= 0 && run.get8(0x537368 + uint32_t(index)) != 0x5c)
                        --index;
                    enter(run, -0x24);
                    run.call(0x4f66cc, local, {0x537369 + uint32_t(index)});
                }
            }
        }
        enter(run, -0x24);
        run.call(0x4f6449, result, {local});
        run.put(run.automatic(-0x10), 1);
    }
    run.put8(run.automatic(-0x4), 1);
    enter(run, -0x20);
    run.call(0x4f6584, local, {});
    run.put8(run.automatic(-0x4), 0);
    enter(run, -0x20);
    run.call(0x4f6584, name, {});
    return result;
}

// 0x49c860. Formats a millisecond count as hours:minutes:seconds into a
// 64-byte local buffer, turns that into a string and copies it to the result.
// Frame offsets from entry ESP: +0x04 result, +0x08 milliseconds (reused as a
// string slot), -0x04 unwind state, -0x4c buffer, -0x50 flag.
uint32_t function_49c860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t result = arguments[0];
    uint32_t milliseconds = arguments[1];
    uint32_t slot = run.automatic(0x8);
    uint32_t buffer = run.automatic(-0x4c);
    run.put(run.automatic(-0x4), 0xffffffff);
    uint32_t hours = milliseconds / 3600000;
    uint32_t rest = milliseconds - hours * 3600000;
    run.put(run.automatic(-0x50), 0);
    uint32_t minutes = rest / 60000;
    rest = rest - minutes * 60000;
    uint32_t seconds = rest / 1000;
    enter(run, -0x6c);
    run.call(0x4a3920, 0, {buffer, 0x52dcf4, hours, minutes, seconds});
    enter(run, -0x5c);
    run.call(0x4f65f2, slot, {buffer});
    run.put(run.automatic(-0x4), 1);
    enter(run, -0x5c);
    run.call(0x4f6449, result, {slot});
    run.put(run.automatic(-0x50), 1);
    run.put8(run.automatic(-0x4), 0);
    enter(run, -0x58);
    run.call(0x4f6584, slot, {});
    return result;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46bc90:
        return function_46bc90(run, receiver, arguments);
    case 0x46bcf0:
        return function_46bcf0(run, receiver, arguments);
    case 0x46bdb0:
        return function_46bdb0(run, receiver, arguments);
    case 0x42abb0:
        return function_42abb0(run, receiver, arguments);
    case 0x42b910:
        return function_42b910(run, receiver, arguments);
    case 0x42d520:
        return function_42d520(run, receiver, arguments);
    case 0x42a570:
        return function_42a570(run, receiver, arguments);
    case 0x4b5c00:
        return function_4b5c00(run, receiver, arguments);
    case 0x4b5c10:
        return function_4b5c10(run, receiver, arguments);
    case 0x4b5e50:
        return function_4b5e50(run, receiver, arguments);
    case 0x4373d0:
        return function_4373d0(run, receiver, arguments);
    case 0x49c860:
        return function_49c860(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_commands_01_entry, owned, body)
