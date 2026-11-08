#include "PegLogicRuntime.h"
#include "AudioEvents.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawPegContext *c;
    ClawPegDependency dependency;
    void *user;
};
int32_t signedWord(uint32_t v) {
    int32_t out;
    std::memcpy(&out, &v, 4);
    return out;
}
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t read(Run &r, uint32_t t) {
    if (bad(r))
        return 0;
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, 1) : nullptr;
    if (!p) {
        r.c->fault = 1;
        return 0;
    }
    return *p;
}
void write(Run &r, uint32_t t, uint32_t v) {
    if (bad(r))
        return;
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, 1) : nullptr;
    if (!p) {
        r.c->fault = 1;
        return;
    }
    *p = v;
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x52dd04:
        return "GAME_FORWARD50";
    case 0x52dd14:
        return "GAME_BACKWARD50";
    case 0x52dd24:
        return "LEVEL_PEGCRUMBLE";
    case 0x528a3c:
        return "LEVEL_PEGSLIDE";
    default:
        return nullptr;
    }
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (bad(r))
        return 0;
    if (!r.dependency) {
        r.c->fault = 1;
        return 0;
    }
    ClawPegCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.name = name;
    std::copy(args.begin(), args.end(), e.arguments);
    return r.dependency(r.c, &e, r.user);
}
uint32_t *animationLookup(void *u, uint32_t t, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    if (bad(r))
        return nullptr;
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t animationCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    if (e.argumentCount == 1)
        return call(r, e.function, e.receiver, {e.arguments[0]},
                    e.function == 0x4f6286 ? label(e.arguments[0]) : nullptr);
    if (e.argumentCount == 4)
        return call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
    r.c->fault = 3;
    return 0;
}
uint32_t animation(Run &r, uint32_t f, uint32_t actor, uint32_t a, uint32_t b = 0) {
    if (bad(r))
        return 0;
    if (!r.c->composeAnimation) {
        if (f == 0x4c79e0)
            return call(r, f, actor, {a, b}, label(a));
        return call(r, f, actor + 0x188, {a});
    }
    auto h = r.c->scene;
    h.context = &r;
    h.lookup = animationLookup;
    h.call = animationCall;
    ClawActorAnimationGlobals g{r.c->globals->animationDelta, r.c->globals->audioVolume};
    uint32_t fault = 0, result = 0;
    const uint32_t supported =
        claw_actor_animation_entry(f, f == 0x4c79e0 ? actor : actor + 0x188, a, b, &g, h, &fault, &result);
    if (!supported || fault)
        r.c->fault = fault ? fault : 3;
    return result;
}
void initialImage(Run &r, uint32_t actor) {
    const uint32_t root = read(r, actor + 0x170);
    if (!root || bad(r))
        return;
    const uint32_t index = read(r, root + 0x64);
    write(r, actor + 0x16c, index);
    const uint32_t min = read(r, root + 0x64), max = read(r, root + 0x68);
    uint32_t image = 0;
    if (signedWord(index) >= signedWord(min) && signedWord(index) <= signedWord(max))
        image = read(r, read(r, root + 0x14) + index * 4);
    write(r, actor + 0x174, image);
}
void profileRect(Run &r, uint32_t actor, uint32_t offset) {
    const uint32_t token = r.c->globals->defaultsToken + offset;
    for (uint32_t i = 0; i < 16; i += 4) {
        const uint32_t v = read(r, token + i);
        write(r, actor + 0x128 + i, v);
    }
}
void midpoint(Run &r, uint32_t actor, uint32_t p) {
    const uint32_t root = read(r, actor + 0x170);
    if (!root || bad(r))
        return;
    const uint32_t sum = read(r, root + 0x64) + read(r, root + 0x68);
    write(r, p + 0x64, uint32_t(signedWord(sum) / 2));
}
uint32_t resetWord(Run &r) {
    const uint32_t primary = read(r, r.c->globals->playerToken + 0x6c), priv = read(r, primary + 0x14);
    return read(r, priv + 0x80);
}
bool supported(Run &r, uint32_t actor) {
    if (!(read(r, r.c->globals->playerToken + 8) & 0x10) || bad(r))
        return false;
    return read(r, r.c->globals->playerToken + 0x80) == actor && !bad(r);
}
void arm(Run &r, uint32_t actor, uint32_t p) {
    const uint32_t wait = read(r, actor + 0x148);
    write(r, p + 0x1c, 1002);
    write(r, p + 0x20, wait);
}
uint32_t poolPlay(void *u, uint32_t pool, ClawAudioRequest v) {
    auto &r = *static_cast<Run *>(u);
    return call(r, 0x4b45f0, pool, {v.volume, v.pan, v.pitchPercent, v.looping});
}
void direct(Run &r, uint32_t resource) {
    if (!r.c->globals->audioManagerToken || bad(r))
        return;
    const uint32_t pool = read(r, resource + 0x10);
    if (bad(r))
        return;
    ClawAudioRouting routing{};
    routing.managerAvailable = 1;
    ClawAudioSound sound{resource, pool};
    claw_audio_play_direct(&routing, &sound, {r.c->globals->audioVolume, 0, 0, 0}, {&r, nullptr, poolPlay});
}
uint32_t slide(Run &r, uint32_t receiver, uint32_t name, uint32_t x, uint32_t clamp, uint32_t pan) {
    const uint32_t scene = read(r, receiver + 0xc), collision = read(r, scene + 0x24);
    if (!collision || bad(r))
        return 0;
    const uint32_t plane = read(r, collision + 0x5c);
    if (!plane || bad(r))
        return 0;
    if (read(r, receiver + 0x30) || bad(r))
        return 0;
    const uint32_t sound = call(r, 0x4f6286, receiver + 16, {name}, label(name));
    if (!sound || bad(r))
        return 0;
    return call(r, 0x4c88e0, sound, {x, 0xffffffff, clamp, pan});
}
void crumbleSound(Run &r, uint32_t actor) {
    const uint32_t scene = read(r, actor + 0xc), registry = read(r, scene + 0x28);
    if (bad(r) || read(r, registry + 0x30))
        return;
    const uint32_t sound = call(r, 0x4f6286, registry + 16, {0x52dd24}, "LEVEL_PEGCRUMBLE");
    if (sound && !bad(r))
        direct(r, sound);
}
void crumble(Run &r, uint32_t actor, bool respawn) {
    const uint32_t p = read(r, actor + 0x6c), mode = read(r, p + 0x1c);
    if (bad(r))
        return;
    switch (mode) {
    case 0: {
        initialImage(r, actor);
        write(r, actor + 0xd0, 0x80);
        write(r, actor + 8, read(r, actor + 8) | 1);
        animation(r, 0x4c79e0, actor, 0x52dd04);
        if (bad(r))
            return;
        write(r, actor + 0x158, 0);
        write(r, actor + 0x15c, 0);
        profileRect(r, actor, 0x78);
        if (respawn)
            write(r, actor + 0x40, read(r, actor + 0x40) & ~1u);
        write(r, actor + 0x134, read(r, actor + 0x134) + 32);
        write(r, actor + 0x164, read(r, actor + 0x164) | 0x8000);
        if (!read(r, actor + 0x64)) {
            write(r, actor + 0x64, 2000);
            write(r, actor + 8, read(r, actor + 8) | 0x20000);
        }
        if (!read(r, actor + 0x148))
            write(r, actor + 0x148, 25);
        if (respawn && !read(r, actor + 0x110))
            write(r, actor + 0x110, 4);
        write(r, p + 0x1c, 5);
        midpoint(r, actor, p);
        break;
    }
    case 5:
        if (!r.c->globals->gate && supported(r, actor) && !bad(r))
            arm(r, actor, p);
        break;
    case 23:
        if (respawn) {
            const uint32_t prior = read(r, p + 0x64), now = resetWord(r);
            if (!bad(r) && signedWord(prior) < signedWord(now))
                write(r, p + 0x1c, 0);
        }
        break;
    case 1002:
        crumbleSound(r, actor);
        write(r, p + 0x1c, 1005);
        break;
    case 1005:
        animation(r, 0x4c82a0, actor, r.c->globals->animationDelta);
        if (bad(r))
            return;
        if (read(r, actor + 0x16c) == read(r, p + 0x64))
            write(r, actor + 0xd0, 1);
        if (read(r, actor + 0x1a4) && !read(r, actor + 0x19c) && !bad(r)) {
            if (respawn) {
                write(r, actor + 0x40, read(r, actor + 0x40) | 1);
                write(r, p + 0x1c, 23);
                const uint32_t value = resetWord(r);
                write(r, p + 0x64, value);
            } else
                write(r, actor + 8, read(r, actor + 8) | 0x10000);
        }
        break;
    case 1111:
        if (!r.c->globals->gate)
            arm(r, actor, p);
        break;
    default:
        break;
    }
}
void toggleInit(Run &r, uint32_t actor, uint32_t p) {
    if (!read(r, actor + 0x148))
        write(r, actor + 0x148, 1500);
    if (!read(r, actor + 0x14c))
        write(r, actor + 0x14c, 1500);
    const uint32_t b = read(r, actor + 0x14c), a = read(r, actor + 0x148);
    write(r, p + 0x4c, a + b);
}
uint32_t visible(Run &r, uint32_t actor, uint32_t p, uint32_t tick) {
    const uint32_t offset = read(r, p + 0xbc), period = read(r, p + 0x4c);
    if (bad(r))
        return 0;
    if (!period) {
        r.c->fault = 2;
        return 0;
    }
    const uint32_t remainder = (tick - offset) % period;
    const uint32_t wait = read(r, actor + 0x148);
    return uint32_t(signedWord(remainder) <= signedWord(wait));
}
void toggle(Run &r, uint32_t actor) {
    const uint32_t p = read(r, actor + 0x6c), mode = read(r, p + 0x1c);
    if (bad(r))
        return;
    switch (mode) {
    case 0: {
        const uint32_t root = read(r, actor + 0x170);
        write(r, actor + 0x158, 0);
        write(r, actor + 0x15c, 0);
        if (root && !bad(r))
            initialImage(r, actor);
        const uint32_t flags = read(r, actor + 8);
        write(r, actor + 0xd0, 0x80);
        write(r, actor + 8, flags | 1);
        profileRect(r, actor, 0x58);
        write(r, actor + 0x134, read(r, actor + 0x134) + 32);
        if (!read(r, actor + 0x64)) {
            write(r, actor + 0x64, 2000);
            write(r, actor + 8, flags | 0x20001);
        }
        const uint32_t callback = read(r, p + 0x10);
        if (callback == 0x49e7b0)
            write(r, p + 0xbc, 750);
        else if (callback == 0x49e7d0)
            write(r, p + 0xbc, 1500);
        else if (callback == 0x49e7f0)
            write(r, p + 0xbc, 2250);
        toggleInit(r, actor, p);
        write(r, p + 0x1c, 1006);
        midpoint(r, actor, p);
        if (r.c->globals->gate || read(r, actor + 0x108) == 1)
            write(r, p + 0x1c, 5);
        break;
    }
    case 1002: {
        const uint32_t registry = read(r, read(r, actor + 0xc) + 0x28), x = read(r, actor + 0x4c);
        slide(r, registry, 0x528a3c, x, 0, 0);
        write(r, p + 0x1c, 1005);
        break;
    }
    case 1003:
        animation(r, 0x4c82a0, actor, r.c->globals->animationDelta);
        if (bad(r))
            return;
        if (read(r, actor + 0x16c) == read(r, p + 0x64))
            write(r, actor + 0xd0, 1);
        if (read(r, actor + 0x1a4) && !read(r, actor + 0x19c) && !bad(r)) {
            write(r, actor + 0xd0, 1);
            animation(r, 0x4c79e0, actor, 0x52dd14);
            write(r, p + 0x1c, 1007);
        }
        break;
    case 1004: {
        write(r, actor + 0xd0, 1);
        animation(r, 0x4c79e0, actor, 0x52dd04);
        const uint32_t registry = read(r, read(r, actor + 0xc) + 0x28), x = read(r, actor + 0x4c);
        slide(r, registry, 0x528a3c, x, 0, 0);
        write(r, p + 0x1c, 1003);
        break;
    }
    case 1005:
        animation(r, 0x4c82a0, actor, r.c->globals->animationDelta);
        if (bad(r))
            return;
        if (read(r, actor + 0x16c) == read(r, p + 0x64))
            write(r, actor + 0xd0, 0x80);
        if (read(r, actor + 0x1a4) && !read(r, actor + 0x19c) && !bad(r)) {
            write(r, actor + 0xd0, 0x80);
            animation(r, 0x4c79e0, actor, 0x52dd04);
            write(r, p + 0x1c, 1006);
        }
        break;
    case 1006: {
        const uint32_t yes = visible(r, actor, p, r.c->globals->tick);
        if (!yes && !bad(r))
            write(r, p + 0x1c, 1004);
        break;
    }
    case 1007: {
        const uint32_t yes = visible(r, actor, p, r.c->globals->tick);
        if (yes && !bad(r))
            write(r, p + 0x1c, 1002);
        break;
    }
    default:
        break;
    }
}
} // namespace
extern "C" uint32_t claw_peg_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n, ClawPegContext *c,
                                   ClawPegDependency dependency, void *user, uint32_t *result) {
    if (!c || !c->globals)
        return 0;
    uint32_t count = 1;
    switch (f) {
    case 0x49d860:
    case 0x49d620:
    case 0x49e4e0:
    case 0x49e7b0:
    case 0x49e7d0:
    case 0x49e7f0:
        break;
    case 0x49e470:
        count = 2;
        break;
    case 0x49e4b0:
        count = 3;
        break;
    case 0x4ca610:
        count = 4;
        break;
    default:
        return 0;
    }
    if (!args || n != count) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{c, dependency, user};
    uint32_t value = 1;
    switch (f) {
    case 0x49d860:
    case 0x49d620:
        crumble(r, args[0], f == 0x49d860);
        break;
    case 0x49e470:
        toggleInit(r, args[0], args[1]);
        value = 0;
        break;
    case 0x49e4b0:
        value = visible(r, args[0], args[1], args[2]);
        break;
    case 0x4ca610:
        value = slide(r, receiver, args[0], args[1], args[2], args[3]);
        break;
    default:
        if (f != 0x49e4e0)
            c->globals->wrapperMode = f == 0x49e7b0 ? 2 : f == 0x49e7d0 ? 3 : 4;
        toggle(r, args[0]);
        break;
    }
    if (result)
        *result = value;
    return 1;
}
