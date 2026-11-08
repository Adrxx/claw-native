// Level one state registry entries, batch 1
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
    case 0x4db6c0:
        return 0;
    case 0x4dbd60:
        return 1;
    case 0x4dbe10:
        return 2;
    case 0x4dc180:
        return 0;
    case 0x4dc560:
        return 2;
    case 0x4dc7b0:
        return 1;
    default:
        return -1;
    }
}

// Objects used here. Registry object ("owner"): +0x00 vtable, +0x04 handler object,
// +0x08 bit count, +0x0c inline bits (up to 0x20 bits) or pointer to the bit buffer.
// Callback table: 0x544b98, 32 slots of 12 bytes (+0 key, +4 value, +8 halfword); count at 0x544d18.

// Sign extension of a char, as the original pushes it.
uint32_t sx8(uint32_t value) {
    return uint32_t(int32_t(int8_t(value & 0xff)));
}

uint32_t is_space(Run &run, uint32_t address) {
    return run.call(0x4b0d60, 0, {sx8(run.get8(address))});
}

uint32_t is_digit(Run &run, uint32_t address) {
    return run.call(0x4b0d30, 0, {sx8(run.get8(address))});
}

// 0x4dc680 through its explicit compiler context: returns the word at [ebp + 4].
// `pc` is the original return address of the call site.
uint32_t diagnostic(Run &run, uint32_t pc, uint32_t ebp) {
    ClawCompilerContext context{};
    context.size = sizeof(context);
    context.version = CLAW_CONTEXT_VERSION;
    context.inputMask = 0x5c1;
    context.outputMask = 0x5c1;
    context.ebp = ebp;
    context.esp = run.automatic(-0x80);
    context.eip = 0x4dc680;
    context.continuation = pc;
    context.fsHead = 0xffffffff;
    run.put(context.esp, pc);
    return run.context_call(0x4dc680, context);
}

// Report an error through the handler object: 0x544b14 = diagnostic word, then 0x4db4d0.
// `entryStack` is the callee-entry ESP of the 0x4db4d0 call (the handler may
// pass a pointer into that frame to its message callback).
void report(Run &run, uint32_t object, uint32_t message, uint32_t code, uint32_t pc, uint32_t ebp,
            uint32_t entryStack, bool callerFrame) {
    uint32_t location;
    if (callerFrame)
        location = run.call(0x4dc680, 0, {});
    else
        location = diagnostic(run, pc, ebp);
    run.put(0x544b14, location);
    run.stackPointer = entryStack;
    run.call(0x4db4d0, run.get(object + 0x04), {object, message, code});
    run.stackPointer = 0;
}

// 0x4dc7b0. Sizes the bit set to `bits` bits and clears it. Returns 1, or 0 when
// the allocation fails.
uint32_t function_4dc7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t bits = arguments[0];
    if (bits <= 0x20) {
        run.put(receiver + 0x0c, 0);
        run.put(receiver + 0x08, 0x20);
        return 1;
    }
    uint32_t words = (bits >> 5) + ((bits & 0x1f) != 0 ? 1 : 0);
    run.put(receiver + 0x08, words);
    uint32_t buffer = run.call(0x4a48e0, 0, {words * 4});
    run.put(receiver + 0x0c, buffer);
    if (buffer == 0)
        return 0;
    uint32_t count = (run.get(receiver + 0x08) << 2) >> 2;
    while (count != 0) {
        run.put(buffer, 0);
        buffer += 4;
        count -= 1;
    }
    run.put(receiver + 0x08, run.get(receiver + 0x08) << 5);
    return 1;
}

// 0x4dc560. Callback table: finds `key` (0x4dc3d0 leaves the insertion index in
// the handler's +4), then removes it (value 0), replaces its value, or inserts it.
// Returns the previous value, or 0.
uint32_t function_4dc560(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    uint32_t value = arguments[1];
    uint32_t count = run.get(0x544d18);
    if (value != 0 && s32(count) >= 0x20)
        return 0;
    uint32_t found;
    if (count == 0) {
        found = 0xffffffff;
    } else {
        found = run.call(0x4dc3d0, receiver, {key});
        count = run.get(0x544d18);
    }
    if (found == 0xffffffff) {
        if (value == 0)
            return 0;
        if (count != 0) {
            uint32_t index = run.get(receiver + 0x04);
            uint32_t offset = index * 12;
            run.call(0x4a5290, 0, {0x544ba4 + offset, 0x544b98 + offset, count * 12 - offset});
            count = run.get(0x544d18);
        }
        count += 1;
        run.put(run.get(receiver + 0x04) * 12 + 0x544b9c, value);
        run.put(run.get(receiver + 0x04) * 12 + 0x544b98, key);
        uint32_t index = run.get(receiver + 0x04);
        run.put(0x544d18, count);
        run.put16(index * 12 + 0x544ba0, 0);
        return 0;
    }
    uint32_t previous = run.get(found * 12 + 0x544b9c);
    if (value != 0) {
        run.put(found * 12 + 0x544b9c, value);
        return previous;
    }
    uint32_t index = run.get(receiver + 0x04);
    uint32_t tail = count * 12 - (index + 1) * 12;
    run.call(0x4a5290, 0, {index * 12 + 0x544b98, index * 12 + 0x544ba4, tail});
    run.put(0x544d18, run.get(0x544d18) - 1);
    return previous;
}

// 0x4db6c0. Registry object destructor: installs vtable 0x513e28 and removes
// the object's entry from the callback table.
uint32_t function_4db6c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x513e28);
    uint32_t handler = run.get(receiver + 0x04);
    const uint32_t removal[] = {receiver, 0};
    function_4dc560(run, handler, removal);
    return 0;
}

// 0x4dbd60. Assignment of one bit set to another. Returns the receiver.
uint32_t function_4dbd60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t other = arguments[0];
    if (receiver == other)
        return receiver;
    uint32_t mine = run.get(receiver + 0x08);
    if (mine != run.get(other + 0x08)) {
        if (mine > 0x20)
            run.call(0x4f6428, 0, {run.get(receiver + 0x0c)});
        uint32_t bits = run.get(other + 0x08);
        if (bits > 0x20) {
            uint32_t buffer = run.call(0x4a48e0, 0, {(bits >> 5) << 2});
            run.put(receiver + 0x0c, buffer);
            if (buffer == 0) {
                // EBP is still the caller entry EBP here.
                uint32_t message = run.get(0x544b4c);
                report(run, receiver, message, 0x0c, 0x4dbdb4, 0, run.frame - 24, true);
                run.put(receiver + 0x08, 0x20);
                return receiver;
            }
        }
        run.put(receiver + 0x08, run.get(other + 0x08));
    }
    uint32_t source;
    if (run.get(other + 0x08) > 0x20)
        source = run.get(other + 0x0c);
    else
        source = other + 0x0c;
    uint32_t size = run.get(receiver + 0x08);
    uint32_t destination;
    if (size > 0x20)
        destination = run.get(receiver + 0x0c);
    else
        destination = receiver + 0x0c;
    run.call(0x4a5290, 0, {destination, source, size >> 3});
    return receiver;
}

// 0x4dbe10 helper: address of the word holding bit `bit` of the set.
uint32_t bit_word(Run &run, uint32_t object, uint32_t bit) {
    uint32_t base = object + 0x0c;
    if (run.get(object + 0x08) > 0x20)
        base = run.get(base);
    return base + (bit >> 5) * 4;
}

// 0x4dc180. Default constructor: 0x4db620 with the global handler, vtable
// 0x513e34, then the bit set sized to the default at 0x533470. Returns the receiver.
uint32_t function_4dc180(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4db620, receiver, {0x544b68});
    run.put(receiver + 0x00, 0x513e34);
    const uint32_t sizing[] = {run.get(0x533470)};
    uint32_t sized = function_4dc7b0(run, receiver, sizing);
    if (sized == 0) {
        uint32_t message = run.get(0x544b4c);
        report(run, receiver, message, 0x0c, 0x4dc1d2, 0, run.frame - 40, true);
    }
    return receiver;
}

// 0x4dbe10. Constructor from text such as "1,3-7 9": numbers separated by
// commas or spaces, ranges with '-'. `maximum` is the largest number seen (and at
// least the requested size). EBP in the original holds the last number parsed
// and is what the diagnostic reads; before any number it is the caller's EBP, not modelled here (0).
uint32_t function_4dbe10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t text = arguments[0];
    uint32_t size = arguments[1];
    uint32_t ebp = 0;
    bool callerFrame = true;
    run.call(0x4db620, receiver, {0x544b68});
    run.put(receiver + 0x00, 0x513e34);
    if (text == 0) {
        report(run, receiver, run.get(0x544b3c), 0x16, 0x4dc141, ebp, run.frame - 52, callerFrame);
        return receiver;
    }
    if (size == 0)
        size = run.get(0x533470);
    uint32_t maximum = 0;
    while (is_space(run, text) != 0)
        text += 1;
    if (run.get8(text) == 0) {
        if (function_4dc7b0(run, receiver, &size) != 0)
            return receiver;
        report(run, receiver, run.get(0x544b4c), 0x0c, 0x4dbf9f, ebp, run.frame - 52, callerFrame);
        return receiver;
    }
    if (is_digit(run, text) == 0) {
        report(run, receiver, run.get(0x544b44), 0x16, 0x4dc141, ebp, run.frame - 52, callerFrame);
        return receiver;
    }
    uint32_t start = text;
    callerFrame = false;
    while (run.get8(text) != 0) {
        ebp = 0;
        uint32_t seen = 0;
        while (is_digit(run, text) != 0) {
            uint32_t digit = sx8(run.get8(text));
            text += 1;
            ebp = digit + ebp * 10 - 0x30;
        }
        if (ebp > maximum)
            maximum = ebp;
        if (run.get8(text) == 0)
            break;
        if (is_digit(run, text) == 0) {
            while (run.get8(text) != 0) {
                if (seen != 0 && run.get8(text) != 0x20) {
                    report(run, receiver, run.get(0x544b44), 0x16, 0x4dc141, ebp, run.frame - 52, callerFrame);
                    return receiver;
                }
                uint32_t separator = run.call(0x4a3a20, 0, {0x53346c, sx8(run.get8(text))});
                if (separator == 0) {
                    report(run, receiver, run.get(0x544b44), 0x16, 0x4dc141, ebp, run.frame - 52, callerFrame);
                    return receiver;
                }
                if (run.get8(text) != 0x20)
                    seen = 1;
                text += 1;
                if (is_digit(run, text) != 0)
                    break;
            }
        }
    }
    if (size > maximum)
        maximum = size;
    if (function_4dc7b0(run, receiver, &maximum) == 0) {
        report(run, receiver, run.get(0x544b4c), 0x0c, 0x4dbf9f, ebp, run.frame - 52, callerFrame);
        return receiver;
    }
    text = start;
    if (run.get8(text) == 0)
        return receiver;
    for (;;) {
        uint32_t number = 0;
        while (is_digit(run, text) != 0) {
            uint32_t digit = sx8(run.get8(text));
            text += 1;
            number = digit + number * 10 - 0x30;
        }
        uint32_t word = bit_word(run, receiver, number);
        ebp = run.get(word) | (1u << (number & 0x1f));
        run.put(word, ebp);
        if (run.get8(text) == 0)
            return receiver;
        while (is_space(run, text) != 0)
            text += 1;
        uint32_t separator = run.get8(text);
        text += 1;
        while (is_space(run, text) != 0)
            text += 1;
        if ((separator & 0xff) == 0x2d) {
            uint32_t last = 0;
            if (run.get8(text) == 0)
                return receiver;
            while (is_digit(run, text) != 0) {
                uint32_t digit = sx8(run.get8(text));
                text += 1;
                last = digit + last * 10 - 0x30;
            }
            ebp = last;
            uint32_t low = number;
            if (low > last) {
                low = last;
                last = number;
                ebp = last;
            }
            low += 1;
            while (low <= last) {
                uint32_t rangeWord = bit_word(run, receiver, low);
                run.put(rangeWord, run.get(rangeWord) | (1u << (low & 0x1f)));
                low += 1;
            }
            if (run.get8(text) == 0)
                return receiver;
            while (is_digit(run, text) == 0) {
                uint32_t next = run.get8(text + 1);
                text += 1;
                if (next == 0)
                    break;
            }
        }
        if (run.get8(text) == 0)
            return receiver;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4db6c0:
        return function_4db6c0(run, receiver, arguments);
    case 0x4dbd60:
        return function_4dbd60(run, receiver, arguments);
    case 0x4dbe10:
        return function_4dbe10(run, receiver, arguments);
    case 0x4dc180:
        return function_4dc180(run, receiver, arguments);
    case 0x4dc560:
        return function_4dc560(run, receiver, arguments);
    case 0x4dc7b0:
        return function_4dc7b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_state_registry_01_entry, owned, body)
