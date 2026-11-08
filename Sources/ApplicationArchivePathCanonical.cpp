// Application archive path selection and file existence checks.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x42cab0:
        return 0;
    case 0x48c190:
        return 1;
    default:
        return -1;
    }
}

// 0x48c190. The OFSTRUCT is an uninitialized 136-byte stack local.
uint32_t archivePathExists(Run &run, uint32_t path) {
    if (!path)
        return 0;
    if (!run.get8(path))
        return 0;
    run.stackPointer = run.automatic(-0x98);
    return run.icall(0x546a30, {path, run.automatic(-0x88), 0x4000}) != 0xffffffffu;
}

// Calls the owned entry with its original internal frame below the resolver.
uint32_t resolverPathExists(Run &run, uint32_t path) {
    uint32_t parentFrame = run.frame;
    uint32_t parentStack = run.stackPointer;
    run.frame = run.automatic(-0x138);
    uint32_t result = archivePathExists(run, path);
    run.frame = parentFrame;
    run.stackPointer = parentStack;
    return result;
}

void formatPath(Run &run, uint32_t target, uint32_t format, uint32_t first, uint32_t second) {
    run.stackPointer = run.automatic(-0x144);
    run.call(0x4f4f58, 0, {target, format, first, second});
}

// 0x42cab0. +0xf8/+0xfc/+0x100 are the data/high-resolution/movie CStrings.
// +0x104 requires high resolution; +0x108 records matching cached drive;
// +0x10c/+0x110/+0x114 record successful fallback locations.
uint32_t resolveArchivePaths(Run &run, uint32_t receiver) {
    run.put(receiver + 0x104, run.get(0x53724c) || run.get(0x537250) ? 1 : 0);
    uint32_t directory = run.automatic(-0x10c);
    run.stackPointer = run.automatic(-0x13c);
    if (!run.icall(0x546a28, {0xff, directory}))
        return 0;
    run.stackPointer = run.automatic(-0x134);
    uint32_t drive = run.call(0x42b020, receiver) & 0xff;
    run.put(receiver + 0x108, drive == run.get8(directory));
    run.put(receiver + 0x10c, 0);
    run.put(receiver + 0x110, 0);
    run.put(receiver + 0x114, 0);
    uint32_t data = run.automatic(-0x120);
    uint32_t high = run.automatic(-0x11c);
    uint32_t movie = run.automatic(-0x118);
    run.stackPointer = run.automatic(-0x138);
    run.call(0x4f65f2, data, {0x526244});
    run.put(run.automatic(-0x4), 0);
    run.call(0x4f65f2, high, {0x526238});
    run.put8(run.automatic(-0x4), 1);
    run.call(0x4f65f2, movie, {0x52622c});
    run.put8(run.automatic(-0x4), 2);
    formatPath(run, receiver + 0xf8, 0x525f78, directory, run.get(data));
    formatPath(run, receiver + 0xfc, 0x525f78, directory, run.get(high));
    formatPath(run, receiver + 0x100, 0x525f78, directory, run.get(movie));
    run.put(run.automatic(-0x114), 1);
    run.put(run.automatic(-0x110), 1);
    uint32_t signedDrive = drive < 0x80 ? drive : drive | 0xffffff00u;
    if (!resolverPathExists(run, run.get(receiver + 0xfc))) {
        bool found = false;
        if (!run.get(receiver + 0x108) && drive) {
            formatPath(run, receiver + 0xfc, 0x52621c, signedDrive, run.get(high));
            if (resolverPathExists(run, run.get(receiver + 0xfc))) {
                run.put(receiver + 0x110, 1);
                found = true;
            }
        }
        if (!found)
            run.put(run.automatic(-0x114), 0);
    }
    if (!resolverPathExists(run, run.get(receiver + 0xf8))) {
        bool found = false;
        if (!run.get(receiver + 0x108) && drive) {
            formatPath(run, receiver + 0xf8, 0x526210, signedDrive, run.get(data));
            if (resolverPathExists(run, run.get(receiver + 0xf8))) {
                run.put(receiver + 0x10c, 1);
                found = true;
            }
        }
        if (!found)
            run.put(run.automatic(-0x110), 0);
    }
    if (!resolverPathExists(run, run.get(receiver + 0x100)) && !run.get(receiver + 0x108) && drive) {
        formatPath(run, receiver + 0x100, 0x526200, signedDrive, run.get(movie));
        if (resolverPathExists(run, run.get(receiver + 0x100)))
            run.put(receiver + 0x114, 1);
    }
    uint32_t error = 0;
    if (run.get(receiver + 0x104) && !run.get(run.automatic(-0x114))) {
        run.stackPointer = run.automatic(-0x138);
        if (!run.call(0x42ce90, receiver, {8}))
            error = 0x8010;
    } else if (!run.get(run.automatic(-0x110))) {
        error = 0x800b;
    }
    if (error) {
        run.stackPointer = run.automatic(-0x13c);
        run.call(0x429e10, receiver, {error, 0x3eb});
    }
    run.put8(run.automatic(-0x4), 1);
    run.stackPointer = run.automatic(-0x134);
    run.call(0x4f6584, movie);
    run.put8(run.automatic(-0x4), 0);
    run.call(0x4f6584, high);
    run.put(run.automatic(-0x4), 0xffffffffu);
    run.call(0x4f6584, data);
    return error ? 0 : 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42cab0:
        return resolveArchivePaths(run, receiver);
    case 0x48c190:
        return archivePathExists(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_application_archive_path_canonical_entry, owned, body)
