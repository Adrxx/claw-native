#include "PlayerDeathServices.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawPlayerDeathServiceContext *c;
    ClawPlayerDeathServiceDependency dependency;
    void *user;
};
bool bad(const Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t token, uint32_t count) {
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, token, count) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t word(Run &r, uint32_t token) {
    auto *p = span(r, token, 1);
    return p ? *p : 0;
}
void store(Run &r, uint32_t token, uint32_t value) {
    auto *p = span(r, token, 1);
    if (p)
        *p = value;
}
uint8_t *bytes(Run &r, uint32_t token, uint32_t count) {
    const uint32_t off = token & 3;
    auto *p = span(r, token - off, (off + count + 3) / 4);
    return p ? reinterpret_cast<uint8_t *>(p) + off : nullptr;
}
uint32_t service(Run &r, uint32_t fn, uint32_t receiver, std::initializer_list<uint32_t> args, uint8_t *a = nullptr,
                 uint32_t aBytes = 0, uint8_t *b = nullptr, uint32_t bBytes = 0) {
    if (bad(r))
        return 0;
    ClawPlayerDeathServiceCall call{};
    call.function = fn;
    call.receiver = receiver;
    call.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), call.arguments);
    call.buffers[0] = a;
    call.buffers[1] = b;
    call.bufferBytes[0] = aBytes;
    call.bufferBytes[1] = bBytes;
    if (r.dependency)
        return r.dependency(r.c, &call, r.user);
    if (!a && !b && r.c->scene.call) {
        ClawSceneActorCall generic{};
        generic.function = fn;
        generic.receiver = receiver;
        generic.argumentCount = call.argumentCount;
        std::copy_n(call.arguments, call.argumentCount, generic.arguments);
        return r.c->scene.call(r.c->scene.context, generic);
    }
    r.c->fault = 1;
    return 0;
}
uint32_t length(Run &r, const uint8_t *data, uint32_t capacity) {
    if (!data) {
        r.c->fault = 1;
        return 0;
    }
    for (uint32_t i = 0; i < capacity; ++i)
        if (!data[i])
            return i;
    r.c->fault = 2;
    return 0;
}
uint32_t rawLength(Run &r, uint32_t token) {
    for (uint32_t i = 0; i < 4096; ++i) {
        auto *p = bytes(r, token + i, 1);
        if (!p || !*p)
            return i;
    }
    r.c->fault = 2;
    return 0;
}
uint32_t copyString(Run &r, uint32_t destination, uint32_t sourceObject) {
    const uint32_t data = word(r, sourceObject), refs = word(r, data - 12);
    if (bad(r))
        return 0;
    if (int32_t(refs) < 0) {
        store(r, destination, r.c->globals->emptyStringToken);
        service(r, 0x4f66cc, destination, {word(r, sourceObject)});
    } else {
        store(r, destination, data);
        store(r, data - 12, refs + 1);
    }
    return destination;
}
uint32_t nameString(Run &r, uint32_t receiver, uint32_t destination) {
    copyString(r, destination, receiver + 8);
    return destination;
}
void releaseString(Run &r, uint32_t string) {
    ClawActorDestructionGlobals g{};
    g.emptyStringToken = r.c->globals->emptyStringToken;
    uint32_t result = 0;
    claw_actor_destruction_entry(0x4f6584, string, 0, &g, r.c->scene, &r.c->fault, &result);
}
void format(Run &r, uint8_t *out, uint8_t *input, uint32_t owner, uint32_t formatToken, uint32_t inputToken = 0,
            uint32_t inputBytes = 256) {
    const uint32_t temporary = r.c->temporaryStringToken;
    if (!temporary) {
        r.c->fault = 1;
        return;
    }
    nameString(r, word(r, owner + 0x784), temporary);
    service(r, 0x4a3920, 0, {0, formatToken, word(r, temporary), inputToken}, out, 256, input, inputBytes);
    if (!bad(r))
        releaseString(r, temporary);
}
uint32_t gate(Run &r, uint32_t owner) {
    const uint32_t client = service(r, 0x4e0c60, word(r, owner + 0x780), {word(r, owner + 0x788)});
    store(r, owner + 0x784, client);
    if (client && !word(r, client + 0x18)) {
        uint32_t allocated = 0;
        if (r.c->scene.allocate)
            allocated = r.c->scene.allocate(r.c->scene.context, 1024);
        else
            allocated = service(r, 0x4f63ec, 0, {1024});
        const uint32_t current = word(r, owner + 0x784);
        store(r, current + 0x18, allocated);
        store(r, current + 0x1c, 1024);
    }
    return word(r, owner + 0x784) != 0;
}
uint32_t send(Run &r, uint32_t owner, uint8_t *input, uint32_t capacity, uint32_t kind, uint32_t prepend,
              uint32_t display, uint32_t inputToken = 0, bool publicFrame = false) {
    if (!input)
        return 0;
    uint32_t count = length(r, input, capacity);
    if (bad(r) || !count)
        return 0;
    if (count > 128) {
        input[128] = 0;
        count = 128;
    }
    if (count && int8_t(input[count - 1]) < 32) {
        input[count - 1] = 0;
        --count;
    }
    if (count && int8_t(input[count - 1]) < 32)
        input[count - 1] = 0;
    if (!gate(r, owner) || bad(r))
        return 0;
    uint8_t output[256];
    if (prepend)
        format(r, output, input, owner, 0x52ac0c, inputToken, capacity);
    else {
        const uint32_t n = length(r, input, capacity);
        if (bad(r))
            return 0;
        std::memcpy(output, input, n + 1);
    }
    if (bad(r))
        return 0;
    if (display)
        service(r, 0x422370, word(r, word(r, owner + 4) + 0x4c), {0, 0}, output, 256);
    const uint32_t packet = word(r, owner + 0xbc8);
    store(r, packet + 4, kind);
    store(r, packet, 0x3f0);
    const uint32_t n = length(r, output, 256);
    if (bad(r))
        return 0;
    const uint32_t destinationToken = word(r, owner + 0xbc8) + 8;
    auto *destination = bytes(r, destinationToken, n + 1);
    if (!destination)
        return 0;
    //479f10 reuses its dead local CString cell as the packet text pointer.
    //For nested notification sends its separate native local is not the outer
    //41ebd0 scratch cell. Public raw calls expose the correct local alias.
    if (publicFrame && r.c->temporaryStringToken)
        store(r, r.c->temporaryStringToken, destinationToken);
    std::memcpy(destination, output, n + 1);
    service(r, 0x4e0d70, word(r, owner + 0x780), {word(r, owner + 0x784), kind, packet, n + 9});
    return 1;
}
const char *phrases[26] = {"is now in kitty heaven...",
                           "didn't quite make it...",
                           "is dead...",
                           "died...",
                           "took a turn for the worst...",
                           "bought the farm...",
                           "hung from the yardarm...",
                           "is having problems...",
                           "had a minor setback...",
                           "is having a hard time...",
                           "is visiting Davey Jones...",
                           "bought the big one...",
                           "walked the plank...",
                           "sunk the ship!",
                           "got the boom...",
                           "swabbed the deck...",
                           "abandoned the ship...",
                           "went down with the ship...",
                           "was blown down...",
                           "was fed to the sharks!",
                           "got battened in the hatches",
                           "was keel hauled...",
                           "is a pirate potroast!",
                           "is riding the dinghy...",
                           "let out the mainsail...",
                           "was capsized..."};
void notify(Run &r) {
    const uint32_t owner = word(r, r.c->globals->managerToken + 0x2c), vt = word(r, owner);
    if (service(r, word(r, vt + 0x10), owner, {}) != 4 || bad(r))
        return;
    const int32_t random = int32_t(service(r, 0x4a3050, 0, {})), choice = random % 26;
    uint8_t phrase[256], message[256];
    const char *literal = phrases[choice >= 0 && choice < 26 ? choice : 25];
    std::memcpy(phrase, literal, std::strlen(literal) + 1);
    const uint32_t current = word(r, r.c->globals->managerToken + 0x2c);
    if (word(r, current + 0x784)) {
        format(r, message, phrase, current, 0x524acc);
        if (!bad(r))
            send(r, current, message, 256, 1, 0, 1);
    }
}
} // namespace
extern "C" uint32_t claw_player_death_service_entry(uint32_t fn, uint32_t receiver, const uint32_t *args,
                                                    uint32_t count, ClawPlayerDeathServiceContext *context,
                                                    ClawPlayerDeathServiceDependency dependency, void *user,
                                                    uint32_t *result) {
    if (result)
        *result = 0;
    if (!context || !context->globals)
        return 0;
    Run r{context, dependency, user};
    uint32_t required;
    switch (fn) {
    case 0x41ebd0:
    case 0x47a220:
        required = 0;
        break;
    case 0x4b7aa0:
    case 0x41ee40:
    case 0x4f6449:
        required = 1;
        break;
    case 0x479f10:
        required = 4;
        break;
    default:
        return 0;
    }
    if (count != required || (count && !args)) {
        context->fault = 2;
        return 0;
    }
    if (bad(r))
        return 0;
    uint32_t value = 0;
    switch (fn) {
    case 0x41ebd0:
        notify(r);
        break;
    case 0x41ee40:
        value = nameString(r, receiver, args[0]);
        break;
    case 0x4f6449:
        value = copyString(r, receiver, args[0]);
        break;
    case 0x47a220:
        value = gate(r, receiver);
        break;
    case 0x479f10:
        if (args[0]) {
            const uint32_t n = rawLength(r, args[0]);
            if (!bad(r))
                value = send(r, receiver, bytes(r, args[0], n + 1), n + 1, args[1], args[2], args[3], args[0], true);
        }
        break;
    default:
        break;
    }
    if (result)
        *result = value;
    return !bad(r);
}
