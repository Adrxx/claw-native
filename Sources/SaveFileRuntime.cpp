#include "SaveFileRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Run {
    ClawSaveFileContext *c;
    ClawSaveFileDependency d;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *words(Run &r, uint32_t t, uint32_t n = 1) {
    if (bad(r))
        return nullptr;
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint8_t *bytes(Run &r, uint32_t t, uint32_t n) {
    if (bad(r))
        return nullptr;
    auto *p = r.c->lookupBytes ? r.c->lookupBytes(r.c->scene.context, t, n)
                               : reinterpret_cast<uint8_t *>(words(r, t, (n + 3) / 4));
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = words(r, t);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    auto *p = words(r, t);
    if (p)
        *p = v;
}
uint32_t call(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawSaveFileCall e{};
    e.function = f;
    e.receiver = t;
    e.argumentCount = uint32_t(a.size());
    std::copy(a.begin(), a.end(), e.arguments);
    return r.d(r.c, &e, r.user);
}
bool guard(Run &r, uint32_t &n, uint32_t limit) {
    if (n++ >= limit) {
        r.c->fault = 4;
        return false;
    }
    return !bad(r);
}
static const uint32_t polynomials[32] = {
    0x3u,       0x6u,       0xau,       0x12u,       0x24u,       0x42u,       0x82u,       0x11cu,
    0x210u,     0x408u,     0x804u,     0x1052u,     0x201au,     0x402au,     0x8002u,     0x1002cu,
    0x20008u,   0x40026u,   0x80026u,   0x100008u,   0x200004u,   0x400002u,   0x800020u,   0x100001au,
    0x2000008u, 0x4000046u, 0x8000026u, 0x10000008u, 0x20000004u, 0x40000052u, 0x80000008u, 0x0u};
static const uint32_t checksumTable[256] = {
    0x0u,        0x77073096u, 0xee0e612cu, 0x990951bau, 0x76dc419u,  0x706af48fu, 0xe963a535u, 0x9e6495a3u, 0xedb8832u,
    0x79dcb8a4u, 0xe0d5e91eu, 0x97d2d988u, 0x9b64c2bu,  0x7eb17cbdu, 0xe7b82d07u, 0x90bf1d91u, 0x1db71064u, 0x6ab020f2u,
    0xf3b97148u, 0x84be41deu, 0x1adad47du, 0x6ddde4ebu, 0xf4d4b551u, 0x83d385c7u, 0x136c9856u, 0x646ba8c0u, 0xfd62f97au,
    0x8a65c9ecu, 0x14015c4fu, 0x63066cd9u, 0xfa0f3d63u, 0x8d080df5u, 0x3b6e20c8u, 0x4c69105eu, 0xd56041e4u, 0xa2677172u,
    0x3c03e4d1u, 0x4b04d447u, 0xd20d85fdu, 0xa50ab56bu, 0x35b5a8fau, 0x42b2986cu, 0xdbbbc9d6u, 0xacbcf940u, 0x32d86ce3u,
    0x45df5c75u, 0xdcd60dcfu, 0xabd13d59u, 0x26d930acu, 0x51de003au, 0xc8d75180u, 0xbfd06116u, 0x21b4f4b5u, 0x56b3c423u,
    0xcfba9599u, 0xb8bda50fu, 0x2802b89eu, 0x5f058808u, 0xc60cd9b2u, 0xb10be924u, 0x2f6f7c87u, 0x58684c11u, 0xc1611dabu,
    0xb6662d3du, 0x76dc4190u, 0x1db7106u,  0x98d220bcu, 0xefd5102au, 0x71b18589u, 0x6b6b51fu,  0x9fbfe4a5u, 0xe8b8d433u,
    0x7807c9a2u, 0xf00f934u,  0x9609a88eu, 0xe10e9818u, 0x7f6a0dbbu, 0x86d3d2du,  0x91646c97u, 0xe6635c01u, 0x6b6b51f4u,
    0x1c6c6162u, 0x856530d8u, 0xf262004eu, 0x6c0695edu, 0x1b01a57bu, 0x8208f4c1u, 0xf50fc457u, 0x65b0d9c6u, 0x12b7e950u,
    0x8bbeb8eau, 0xfcb9887cu, 0x62dd1ddfu, 0x15da2d49u, 0x8cd37cf3u, 0xfbd44c65u, 0x4db26158u, 0x3ab551ceu, 0xa3bc0074u,
    0xd4bb30e2u, 0x4adfa541u, 0x3dd895d7u, 0xa4d1c46du, 0xd3d6f4fbu, 0x4369e96au, 0x346ed9fcu, 0xad678846u, 0xda60b8d0u,
    0x44042d73u, 0x33031de5u, 0xaa0a4c5fu, 0xdd0d7cc9u, 0x5005713cu, 0x270241aau, 0xbe0b1010u, 0xc90c2086u, 0x5768b525u,
    0x206f85b3u, 0xb966d409u, 0xce61e49fu, 0x5edef90eu, 0x29d9c998u, 0xb0d09822u, 0xc7d7a8b4u, 0x59b33d17u, 0x2eb40d81u,
    0xb7bd5c3bu, 0xc0ba6cadu, 0xedb88320u, 0x9abfb3b6u, 0x3b6e20cu,  0x74b1d29au, 0xead54739u, 0x9dd277afu, 0x4db2615u,
    0x73dc1683u, 0xe3630b12u, 0x94643b84u, 0xd6d6a3eu,  0x7a6a5aa8u, 0xe40ecf0bu, 0x9309ff9du, 0xa00ae27u,  0x7d079eb1u,
    0xf00f9344u, 0x8708a3d2u, 0x1e01f268u, 0x6906c2feu, 0xf762575du, 0x806567cbu, 0x196c3671u, 0x6e6b06e7u, 0xfed41b76u,
    0x89d32be0u, 0x10da7a5au, 0x67dd4accu, 0xf9b9df6fu, 0x8ebeeff9u, 0x17b7be43u, 0x60b08ed5u, 0xd6d6a3e8u, 0xa1d1937eu,
    0x38d8c2c4u, 0x4fdff252u, 0xd1bb67f1u, 0xa6bc5767u, 0x3fb506ddu, 0x48b2364bu, 0xd80d2bdau, 0xaf0a1b4cu, 0x36034af6u,
    0x41047a60u, 0xdf60efc3u, 0xa867df55u, 0x316e8eefu, 0x4669be79u, 0xcb61b38cu, 0xbc66831au, 0x256fd2a0u, 0x5268e236u,
    0xcc0c7795u, 0xbb0b4703u, 0x220216b9u, 0x5505262fu, 0xc5ba3bbeu, 0xb2bd0b28u, 0x2bb45a92u, 0x5cb36a04u, 0xc2d7ffa7u,
    0xb5d0cf31u, 0x2cd99e8bu, 0x5bdeae1du, 0x9b64c2b0u, 0xec63f226u, 0x756aa39cu, 0x26d930au,  0x9c0906a9u, 0xeb0e363fu,
    0x72076785u, 0x5005713u,  0x95bf4a82u, 0xe2b87a14u, 0x7bb12baeu, 0xcb61b38u,  0x92d28e9bu, 0xe5d5be0du, 0x7cdcefb7u,
    0xbdbdf21u,  0x86d3d2d4u, 0xf1d4e242u, 0x68ddb3f8u, 0x1fda836eu, 0x81be16cdu, 0xf6b9265bu, 0x6fb077e1u, 0x18b74777u,
    0x88085ae6u, 0xff0f6a70u, 0x66063bcau, 0x11010b5cu, 0x8f659effu, 0xf862ae69u, 0x616bffd3u, 0x166ccf45u, 0xa00ae278u,
    0xd70dd2eeu, 0x4e048354u, 0x3903b3c2u, 0xa7672661u, 0xd06016f7u, 0x4969474du, 0x3e6e77dbu, 0xaed16a4au, 0xd9d65adcu,
    0x40df0b66u, 0x37d83bf0u, 0xa9bcae53u, 0xdebb9ec5u, 0x47b2cf7fu, 0x30b5ffe9u, 0xbdbdf21cu, 0xcabac28au, 0x53b39330u,
    0x24b4a3a6u, 0xbad03605u, 0xcdd70693u, 0x54de5729u, 0x23d967bfu, 0xb3667a2eu, 0xc4614ab8u, 0x5d681b02u, 0x2a6f2b94u,
    0xb40bbe37u, 0xc30c8ea1u, 0x5a05df1bu, 0x2d02ef8du,
};
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *, uint32_t, uint32_t *);
uint32_t invoke(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    uint32_t result = 0;
    entry(r, f, t, a.begin(), uint32_t(a.size()), &result);
    return result;
}
uint32_t permutation(Run &r, uint32_t t, uint32_t limit) {
    wr(r, t + 0x48, limit);
    wr(r, t + 0x4c, 2);
    uint32_t i = 0;
    while ((limit >>= 1) != 0) {
        ++i;
        wr(r, t + 0x4c, rd(r, t + 0x4c) << 1);
    }
    wr(r, t + 0x50, polynomials[i]);
    uint32_t random = call(r, 0x4a3050, 0), divisor = rd(r, t + 0x4c) - 1;
    if (!divisor) {
        r.c->fault = 2;
        return 0;
    }
    wr(r, t + 0x54, random % divisor + 1);
    return random / divisor;
}
uint32_t next(Run &r, uint32_t t) {
    const uint32_t bit = rd(r, t + 0x4c), limit = rd(r, t + 0x48);
    uint32_t n = 0;
    do {
        if (!guard(r, n, r.c->maximumSteps ? r.c->maximumSteps : 65536))
            return 0;
        uint32_t value = rd(r, t + 0x54) << 1;
        wr(r, t + 0x54, value);
        if (value & bit)
            wr(r, t + 0x54, (rd(r, t + 0x50) ^ value) | 1);
    } while (rd(r, t + 0x54) > limit && !bad(r));
    return rd(r, t + 0x54) - 1;
}
void crypt(Run &r, uint32_t t, uint32_t data, uint32_t size) {
    call(r, 0x4a3040, 0, {rd(r, t + 0x44)});
    permutation(r, t, 0x1000000);
    for (uint32_t i = 0; i < size && !bad(r); ++i) {
        uint32_t value = next(r, t);
        auto *p = bytes(r, data + i, 1);
        if (p)
            *p ^= uint8_t(value);
    }
}
uint32_t checksum(Run &r, uint32_t data, uint32_t size) {
    if (!data)
        return 0;
    uint32_t value = 0xffffffff;
    auto *p = size ? bytes(r, data, size) : nullptr;
    for (uint32_t i = 0; i < size && !bad(r); ++i)
        value ^= checksumTable[p[i]];
    return value;
}
void clear(Run &r, uint32_t t) {
    const uint32_t s = rd(r, t);
    if (rd(r, s - 8)) {
        if (int32_t(rd(r, s - 12)) >= 0)
            call(r, 0x4f64ba, t);
        else
            call(r, 0x4f66cc, t, {0x53ec90});
    }
}
uint32_t open(Run &r, uint32_t t, const uint32_t *a) {
    wr(r, t + 8, 0);
    wr(r, t + 4, 0xffffffff);
    clear(r, t + 12);
    call(r, 0x4f777f, 0, {r.c->pathScratchToken, a[0]});
    call(r, 0x4f66cc, t + 12, {r.c->pathScratchToken});
    const uint32_t flags = a[1] & 0xffff7fff, mode = flags & 3;
    uint32_t access = mode == 0 ? 0x80000000 : mode == 1 ? 0x40000000 : mode == 2 ? 0xc0000000 : a[1];
    uint32_t share;
    switch (flags & 0x70) {
    case 0:
    case 0x10:
        share = 0;
        break;
    case 0x20:
        share = 1;
        break;
    case 0x30:
        share = 2;
        break;
    case 0x40:
        share = 3;
        break;
    default:
        share = a[0];
        break;
    }
    wr(r, r.c->securityScratchToken, 12);
    wr(r, r.c->securityScratchToken + 4, 0);
    wr(r, r.c->securityScratchToken + 8, (~flags >> 7) & 1);
    uint32_t create = (flags & 0x1000) ? ((flags & 0x2000) ? 4 : 2) : 3;
    uint32_t handle = call(r, 0x546b00, 0, {a[0], access, share, r.c->securityScratchToken, create, 0x80, 0});
    if (bad(r))
        return 0;
    if (handle == 0xffffffff) {
        if (a[2]) {
            uint32_t error = call(r, 0x546b0c, 0);
            wr(r, a[2] + 12, error);
            uint32_t mapped = call(r, 0x4fc384, 0, {error});
            wr(r, a[2] + 8, mapped);
            call(r, 0x4f66cc, a[2] + 16, {a[0]});
        }
        return 0;
    }
    wr(r, t + 4, handle);
    wr(r, t + 8, 1);
    return 1;
}
void writeFile(Run &r, uint32_t t, uint32_t data, uint32_t size) {
    if (!size)
        return;
    wr(r, r.c->countScratchToken, size);
    uint32_t ok = call(r, 0x546af8, 0, {rd(r, t + 4), data, size, r.c->countScratchToken, 0});
    if (!ok && !bad(r)) {
        const uint32_t name = rd(r, t + 12), error = call(r, 0x546b0c, 0);
        call(r, 0x4fc242, 0, {error, name});
    }
    if (!bad(r) && rd(r, r.c->countScratchToken) != size)
        call(r, 0x4fc303, 0, {13, 0xffffffff, rd(r, t + 12)});
}
void close(Run &r, uint32_t t) {
    bool error = false;
    uint32_t handle = rd(r, t + 4);
    if (handle != 0xffffffff)
        error = call(r, 0x546a04, 0, {handle}) == 0;
    wr(r, t + 4, 0xffffffff);
    wr(r, t + 8, 0);
    clear(r, t + 12);
    if (error && !bad(r)) {
        uint32_t last = call(r, 0x546b0c, 0);
        call(r, 0x4fc242, 0, {last, 0});
    }
}
void destruct(Run &r, uint32_t t) {
    wr(r, t, 0x510844);
    if (rd(r, t + 4) != 0xffffffff && rd(r, t + 8))
        close(r, t);
    call(r, 0x4f6584, t + 12);
    wr(r, t, 0x50becc);
}
uint32_t writer(Run &r, uint32_t t) {
    if (!rd(r, rd(r, t + 0x1c) - 8) || bad(r))
        return 0;
    if (int32_t(rd(r, t + 0xc)) <= 0 || bad(r))
        return 0;
    const uint32_t file = r.c->fileScratchToken;
    invoke(r, 0x4f72c9, file);
    if (!invoke(r, 0x4f7448, file, {rd(r, t + 0x1c), 0x1000, 0})) {
        if (!bad(r))
            destruct(r, file);
        return 0;
    }
    close(r, file);
    if (bad(r))
        return 0;
    if (!invoke(r, 0x4f7448, file, {rd(r, t + 0x1c), 1, 0})) {
        if (!bad(r))
            destruct(r, file);
        return 0;
    }
    const uint32_t count = rd(r, t + 0xc), size = count * 0x2644;
    if (!r.c->scene.allocate) {
        r.c->fault = 1;
        return 0;
    }
    uint32_t buffer = r.c->scene.allocate(r.c->scene.context, size);
    if (!buffer) {
        if (!bad(r))
            destruct(r, file);
        return 0;
    }
    uint32_t node = rd(r, t + 4), offset = 0, loops = 0;
    while (node && !bad(r)) {
        if (!guard(r, loops, r.c->maximumTraversal ? r.c->maximumTraversal : 65536))
            return 0;
        const uint32_t current = node;
        node = rd(r, current);
        uint32_t source = rd(r, current + 8) + 4;
        auto *from = words(r, source, 0x991);
        auto *to = words(r, buffer + offset, 0x991);
        if (!from || !to)
            return 0;
        for (uint32_t i = 0; i < 0x991; ++i)
            static_cast<volatile uint32_t *>(to)[i] = static_cast<volatile uint32_t *>(from)[i];
        offset += 0x2644;
    }
    uint32_t sum = checksum(r, buffer, size);
    wr(r, t + 0x24, sum);
    wr(r, t + 0x2c, rd(r, t + 0xc));
    wr(r, t + 0x28, rd(r, t + 0x40));
    crypt(r, t, t + 0x20, 32);
    crypt(r, t, buffer, size);
    writeFile(r, file, t + 0x20, 32);
    writeFile(r, file, buffer, size);
    if (bad(r))
        return 0;
    crypt(r, t, t + 0x20, 32);
    if (bad(r))
        return 0;
    if (r.c->scene.free)
        r.c->scene.free(r.c->scene.context, buffer);
    else
        r.c->fault = 1;
    if (!bad(r))
        destruct(r, file);
    return count;
}
uint32_t entry(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t *result) {
    if (result)
        *result = 0;
    uint32_t wanted = 0;
    switch (f) {
    case 0x49bf70:
    case 0x49c030:
    case 0x49c070:
    case 0x4f75aa:
        wanted = 2;
        break;
    case 0x49bfb0:
        wanted = 1;
        break;
    case 0x4f7448:
        wanted = 3;
        break;
    case 0x49bbc0:
    case 0x49c000:
    case 0x4f72c9:
    case 0x4f7369:
    case 0x4f766e:
    case 0x4f650f:
        break;
    default:
        return 0;
    }
    if (n != wanted || (n && !a)) {
        r.c->fault = 2;
        return 0;
    }
    uint32_t value = 0;
    switch (f) {
    case 0x49bbc0:
        value = writer(r, t);
        break;
    case 0x49bf70:
        value = checksum(r, a[0], a[1]);
        break;
    case 0x49bfb0:
        value = permutation(r, t, a[0]);
        break;
    case 0x49c000:
        value = next(r, t);
        break;
    case 0x49c030:
    case 0x49c070:
        crypt(r, t, a[0], a[1]);
        break;
    case 0x4f72c9:
        wr(r, t, 0x50becc);
        wr(r, t + 12, r.c->emptyStringToken);
        wr(r, t + 4, 0xffffffff);
        wr(r, t + 8, 0);
        wr(r, t, 0x510844);
        value = t;
        break;
    case 0x4f7369:
        destruct(r, t);
        break;
    case 0x4f7448:
        value = open(r, t, a);
        break;
    case 0x4f75aa:
        writeFile(r, t, a[0], a[1]);
        break;
    case 0x4f766e:
        close(r, t);
        break;
    case 0x4f650f:
        clear(r, t);
        break;
    }
    if (result)
        *result = value;
    return 1;
}
} // namespace
uint32_t claw_save_file_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawSaveFileContext *c,
                              ClawSaveFileDependency d, void *u, uint32_t *result) {
    if (result)
        *result = 0;
    if (!c)
        return 0;
    c->fault = 0;
    Run r{c, d, u};
    return entry(r, f, t, a, n, result) && !bad(r);
}
uint32_t claw_save_file_initialize_manager(uint32_t t, ClawSaveFileContext *c) {
    if (!c)
        return 0;
    c->fault = 0;
    Run r{c, nullptr, nullptr};
    for (uint32_t i = 1; i <= 5; ++i)
        wr(r, t + 4 * i, 0);
    wr(r, t, 0x5107bc);
    wr(r, t + 0x18, 10);
    wr(r, t + 0x1c, c->emptyStringToken);
    for (uint32_t i = 0; i < 8; ++i)
        wr(r, t + 0x20 + 4 * i, 0);
    wr(r, t + 0x40, 0);
    wr(r, t + 0x44, 0x4d505255);
    return !bad(r);
}
