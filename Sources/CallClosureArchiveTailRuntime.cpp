// Recursive archive updates and message presentation tail
//
// Recovered original archive updates, index serialization and message policy.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b6260:
        return 1;
    case 0x4b62d0:
        return 2;
    case 0x4b6350:
        return 1;
    case 0x4b63e0:
        return 0;
    case 0x4b6480:
        return 0;
    case 0x4b6820:
        return 1;
    case 0x4b6c50:
        return 2;
    case 0x4bd090:
        return 1;
    case 0x47c4b0:
        return 2;
    case 0x42a690:
        return 2;
    default:
        return -1;
    }
}

uint32_t function_4b6820(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x4b6480 ArchiveEntry::touchTimestamp.
uint32_t function_4b6480(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t savedStack = run.stackPointer;
    run.stackPointer = run.automatic(-0x8);
    const uint32_t timestamp = run.call(0x4b7cc0, 0);
    run.stackPointer = savedStack;
    const uint32_t parent = run.get(receiver + 0x24);
    run.put(receiver + 0x10, timestamp);
    run.put(parent + 0x14, timestamp);
    run.put(run.get(run.get(receiver + 0x24) + 0x18) + 0x28, timestamp);
    return 0;
}

// 0x4b6260 ArchiveEntry::resizeData.
uint32_t function_4b6260(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t oldSize = run.get(receiver + 0x14);
    run.call(0x4b6230, receiver);
    const uint32_t parent = run.get(receiver + 0x24);
    if (run.get(parent + 0x20)) {
        const uint32_t recurse[] = {0};
        function_4b6820(run, parent, recurse);
    }
    run.put(receiver + 0x14, arguments[0]);
    const uint32_t data = run.call(0x4f63ec, 0, {arguments[0]});
    const uint32_t size = run.get(receiver + 0x14);
    run.put(receiver + 0x18, data);
    const uint32_t totalParent = run.get(receiver + 0x24);
    run.put(receiver + 0x28, 0);
    run.put(totalParent + 0x10, run.get(totalParent + 0x10) + size);
    const uint32_t subtractParent = run.get(receiver + 0x24);
    run.put(subtractParent + 0x10, run.get(subtractParent + 0x10) - oldSize);
    run.put(run.get(run.get(receiver + 0x24) + 0x18) + 0x4, 0);
    const uint32_t savedFrame = run.frame;
    run.frame -= 0xc;
    function_4b6480(run, receiver, nullptr);
    run.frame = savedFrame;
    return run.get(receiver + 0x18);
}

// 0x4b62d0 ArchiveEntry::setIndex.
uint32_t function_4b62d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t capacity = run.get(receiver + 0x1c);
    const uint32_t index = arguments[0];
    if (index >= capacity) {
        const uint32_t newCapacity = index + 1;
        run.put(receiver + 0x1c, newCapacity);
        const uint32_t data = run.call(0x4f63ec, 0, {newCapacity * 4});
        if (run.get(receiver + 0x20)) {
            for (uint32_t i = 0; i < capacity; ++i) {
                const uint32_t oldData = run.get(receiver + 0x20);
                run.put(data + i * 4, run.get(oldData + i * 4));
            }
            run.call(0x4f6428, 0, {run.get(receiver + 0x20)});
        }
        const uint32_t parent = run.get(receiver + 0x24);
        run.put(receiver + 0x20, data);
        const uint32_t archive = run.get(parent + 0x18);
        if (run.get(archive + 0x34) <= index) {
            run.put(archive + 0x34, newCapacity);
        }
    }
    run.put(run.get(receiver + 0x20) + index * 4, arguments[1]);
    return 0;
}

uint32_t stringBytes(Run &run, uint32_t string) {
    uint32_t length = 0;
    while (run.get8(string + length++)) {}
    return length;
}

// 0x4b6350 ArchiveEntry::setName.
uint32_t function_4b6350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t oldName = run.get(receiver + 0xc);
    if (oldName) {
        run.call(0x4f6428, 0, {oldName});
    }
    uint32_t length = 0;
    const uint32_t input = arguments[0];
    if (input) {
        length = stringBytes(run, input);
        const uint32_t name = run.call(0x4f63ec, 0, {length});
        run.put(receiver + 0xc, name);
        const uint32_t copyLength = stringBytes(run, input);
        const uint32_t destination = run.get(receiver + 0xc);
        uint32_t i = 0;
        for (; i + 4 <= copyLength; i += 4) {
            run.put(destination + i, run.get(input + i));
        }
        for (; i < copyLength; ++i) {
            run.put8(destination + i, run.get8(input + i));
        }
    } else {
        run.put(receiver + 0xc, 0);
    }
    const uint32_t archive = run.get(run.get(receiver + 0x24) + 0x18);
    if (run.get(archive + 0x40) < length) {
        run.put(archive + 0x34, length);
    }
    return 1;
}

// 0x4b63e0 ArchiveEntry::flushData.
uint32_t function_4b63e0(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t initialSize = run.get(receiver + 0x14);
    if (!initialSize) {
        return 1;
    }
    const uint32_t offset = run.get(receiver + 0x28);
    if (!offset) {
        run.put(run.get(run.get(receiver + 0x24) + 0x18) + 0x4, 0);
        const uint32_t parent = run.get(receiver + 0x24);
        const uint32_t size = run.get(receiver + 0x14);
        const uint32_t data = run.get(receiver + 0x18);
        const uint32_t archive = run.get(parent + 0x18);
        const uint32_t written = run.call(0x4b7b40, archive, {run.get(archive + 0x1c), size, data});
        if (written != size) {
            return 0;
        }
        const uint32_t updatedParent = run.get(receiver + 0x24);
        run.put(receiver + 0x28, run.get(run.get(updatedParent + 0x18) + 0x1c));
        const uint32_t updatedArchive = run.get(updatedParent + 0x18);
        run.put(updatedArchive + 0x1c, run.get(updatedArchive + 0x1c) + size);
    } else {
        const uint32_t data = run.get(receiver + 0x18);
        const uint32_t archive = run.get(run.get(receiver + 0x24) + 0x18);
        const uint32_t written = run.call(0x4b7b40, archive, {offset, initialSize, data});
        if (written != run.get(receiver + 0x14)) {
            return 0;
        }
    }
    const uint32_t savedFrame = run.frame;
    run.frame -= 0xc;
    function_4b6480(run, receiver, nullptr);
    run.frame = savedFrame;
    return 1;
}

// 0x4b6820 ArchiveDirectory::releaseData.
uint32_t function_4b6820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t cache = run.get(receiver + 0x20);
    if (cache) {
        run.call(0x4f6428, 0, {cache});
        run.put(receiver + 0x20, 0);
    } else {
        uint32_t bucket = run.call(0x4b6920, receiver);
        while (bucket) {
            uint32_t entry = run.call(0x4b6960, receiver, {bucket});
            while (entry) {
                run.call(0x4b6230, entry);
                entry = run.call(0x4b6980, receiver, {entry});
            }
            bucket = run.call(0x4b6940, receiver, {bucket});
        }
    }
    if (arguments[0]) {
        uint32_t node = run.call(0x4d54c0, receiver + 0x3c);
        while (node) {
            const uint32_t recurse[] = {1};
            function_4b6820(run, run.get(node + 0x14), recurse);
            node = run.call(0x4d5350, node);
        }
    }
    return 1;
}

// 0x4b6c50 ArchiveDirectory::writeIndex.
uint32_t function_4b6c50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t zero = run.automatic(-0x29);
    const uint32_t tag = run.automatic(-0x1c);
    run.put8(zero, 0);
    run.put(tag, 1);
    uint32_t position = arguments[0];
    uint32_t node = run.call(0x4d54c0, receiver + 0x3c);
    while (node) {
        const uint32_t directory = run.get(node + 0x14);
        run.put(run.automatic(-0x18), run.get(directory + 0x4));
        run.put(run.automatic(-0x14), run.get(directory + 0x8));
        run.put(run.automatic(-0x10), run.get(directory + 0x14));
        position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, tag});
        position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x18)});
        position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x14)});
        position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x10)});
        const uint32_t name = run.get(directory);
        const uint32_t bytes = name ? stringBytes(run, name) : 1;
        position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, bytes, name ? name : zero});
        node = run.call(0x4d5350, node);
    }
    run.put(tag, 0);
    uint32_t bucket = run.call(0x4d54c0, receiver + 0x44);
    run.put(run.automatic(-0x28), bucket);
    while (bucket) {
        uint32_t entryNode = run.call(0x4d54c0, run.get(bucket + 0x14) + 0x1c);
        run.put(run.automatic(-0x24), entryNode);
        while (entryNode) {
            const uint32_t entry = run.get(entryNode + 0x14);
            run.put(run.automatic(-0x18), run.get(entry + 0x28));
            run.put(run.automatic(-0x14), run.get(entry + 0x14));
            run.put(run.automatic(-0x10), run.get(entry + 0x10));
            run.put(run.automatic(-0xc), run.get(entry + 0x4));
            run.put(run.automatic(-0x8), run.get(run.get(bucket + 0x14)));
            run.put(run.automatic(-0x4), run.get(entry + 0x1c));
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, tag});
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x18)});
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x14)});
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x10)});
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0xc)});
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x8)});
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x4)});
            const uint32_t name = run.get(entry);
            const uint32_t nameLength = name ? stringBytes(run, name) : 1;
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, nameLength, name ? name : zero});
            const uint32_t alias = run.get(entry + 0xc);
            const uint32_t aliasLength = alias ? stringBytes(run, alias) : 1;
            position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, aliasLength, alias ? alias : zero});
            for (uint32_t i = 0; i < run.get(entry + 0x1c); ++i) {
                run.put(run.automatic(-0x20), run.get(run.get(entry + 0x20) + i * 4));
                position += run.call(0x4b7b40, run.get(receiver + 0x18), {position, 4, run.automatic(-0x20)});
            }
            entryNode = run.call(0x4d5350, run.get(run.automatic(-0x24)));
            run.put(run.automatic(-0x24), entryNode);
            bucket = run.get(run.automatic(-0x28));
        }
        bucket = run.call(0x4d5350, bucket);
        run.put(run.automatic(-0x28), bucket);
    }
    run.put(run.get(receiver + 0x18) + 0x1c, position);
    run.put(arguments[1], position - arguments[0]);
    return 1;
}

// 0x4bd090 Image::setErrorCallback.
uint32_t function_4bd090(Run &run, uint32_t, const uint32_t *arguments) {
    run.put(0x54138c, arguments[0]);
    return 0;
}

// 0x42a690 Application::showMessage.
uint32_t function_42a690(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver + 0x30)) {
        const uint32_t render = run.get(run.get(receiver + 0x30) + 0x4);
        run.call(0x4ca9e0, render, {run.get(render + 0x14)});
        const uint32_t surface = run.get(run.get(run.get(receiver + 0x30) + 0x1c));
        run.call(run.get(run.get(surface) + 0x28), 0, {surface});
    }
    const uint32_t first = run.icall(0x546d54, {1});
    while (s32(run.icall(0x546d54, {1})) < 0) {}
    const uint32_t answer = run.icall(0x546d48, {run.get(run.get(receiver + 0x4) + 0x4), arguments[0], 0x524eec, arguments[1]});
    if (s32(first) <= 0) {
        while (s32(run.icall(0x546d54, {0})) >= 0) {}
    }
    return answer;
}

// 0x47c4b0 Multiplayer::showMessage.
uint32_t function_47c4b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t text = arguments[0];
    if (text && run.get8(text) && run.get(receiver + 0x4)) {
        if (s32(arguments[1]) > 0) {
            const uint32_t formatted = run.automatic(-0x200);
            run.call(0x4a3920, 0, {formatted, 0x52afd0, text, arguments[1]});
            const uint32_t message[] = {formatted, 0};
            function_42a690(run, run.get(receiver + 0x4), message);
        } else {
            const uint32_t message[] = {text, 0};
            function_42a690(run, run.get(receiver + 0x4), message);
        }
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b6260:
        return function_4b6260(run, receiver, arguments);
    case 0x4b62d0:
        return function_4b62d0(run, receiver, arguments);
    case 0x4b6350:
        return function_4b6350(run, receiver, arguments);
    case 0x4b63e0:
        return function_4b63e0(run, receiver, arguments);
    case 0x4b6480:
        return function_4b6480(run, receiver, arguments);
    case 0x4b6820:
        return function_4b6820(run, receiver, arguments);
    case 0x4b6c50:
        return function_4b6c50(run, receiver, arguments);
    case 0x4bd090:
        return function_4bd090(run, receiver, arguments);
    case 0x47c4b0:
        return function_47c4b0(run, receiver, arguments);
    case 0x42a690:
        return function_42a690(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_call_closure_archive_tail_entry, owned, body)
