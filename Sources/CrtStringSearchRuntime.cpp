// Original CRT byte string search
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4a3990:
        return 2;
    case 0x4a3a20:
        return 2;
    default:
        return -1;
    }
}

// 0x4a3a26. Shared character-search tail, entered in the caller's frame.
uint32_t searchCharacter(Run &run, uint32_t cursor, uint8_t character) {
    while (cursor & 3u) {
        uint8_t value = run.get8(cursor);
        ++cursor;
        if (value == character)
            return cursor - 1;
        if (!value)
            return 0;
    }
    uint32_t repeated = uint32_t(character) * 0x01010101u;
    for (;;) {
        uint32_t word = run.get(cursor);
        uint32_t difference = word ^ repeated;
        uint32_t zeroSum = word + 0x7efefeffu;
        uint32_t matchSentinel = (~difference ^ (difference + 0x7efefeffu)) & 0x81010100u;
        uint32_t zeroSentinel = (~word ^ zeroSum) & 0x81010100u;
        cursor += 4;
        if (matchSentinel) {
            word = run.get(cursor - 4);
            for (uint32_t offset = 0; offset < 4; ++offset) {
                uint8_t value = uint8_t(word >> (offset * 8));
                if (value == character)
                    return cursor - 4 + offset;
                if (!value)
                    return 0;
            }
        } else if (zeroSentinel) {
            if ((zeroSentinel & 0x01010100u) || !(zeroSum & 0x80000000u))
                return 0;
        }
    }
}

// 0x4a3990. Byte-paired substring scan; the single-byte path shares the tail.
uint32_t function_4a3990(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t haystack = arguments[0];
    uint32_t needle = arguments[1];
    uint8_t first = run.get8(needle);
    if (!first)
        return haystack;
    uint8_t second = run.get8(needle + 1);
    if (!second)
        return searchCharacter(run, haystack, first);
    uint32_t restart = haystack;
    for (;;) {
        uint32_t cursor = restart;
        uint32_t pattern = needle;
        uint8_t value = run.get8(restart);
        ++cursor;
        for (;;) {
            if (value == first) {
                value = run.get8(cursor);
                ++cursor;
                if (value == second)
                    break;
                continue;
            }
            if (!value)
                return 0;
            value = run.get8(cursor);
            ++cursor;
        }
        restart = cursor - 1;
        for (;;) {
            uint8_t next = run.get8(pattern + 2);
            if (!next)
                return restart - 1;
            value = run.get8(cursor);
            cursor += 2;
            if (value != next)
                break;
            next = run.get8(pattern + 3);
            if (!next)
                return restart - 1;
            value = run.get8(cursor - 1);
            pattern += 2;
            if (value != next)
                break;
        }
    }
}

// 0x4a3a20. cdecl, 2 stack argument(s), returns u32.
uint32_t function_4a3a20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return searchCharacter(run, arguments[0], uint8_t(arguments[1]));
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a3990:
        return function_4a3990(run, receiver, arguments);
    case 0x4a3a20:
        return function_4a3a20(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_crt_string_search_entry, owned, body)
