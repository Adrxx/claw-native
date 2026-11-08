#include "EnemySpeechRuntime.h"
#include "SpeechActor.h"
#include "AudioEvents.h"
#include "ActorResourceBindings.h"
#include "ActorDestruction.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Run {
    ClawEnemySpeechContext *c;
    ClawEnemySpeechDependency dependency;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t read(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
void write(Run &r, uint32_t t, uint32_t v) {
    if (bad(r))
        return;
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (bad(r))
        return 0;
    if (!r.dependency) {
        r.c->fault = 1;
        return 0;
    }
    ClawEnemySpeechCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.name = name;
    std::copy(args.begin(), args.end(), e.arguments);
    return r.dependency(r.c, &e, r.user);
}
uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
ClawSpeechImage image(Run &r, uint32_t actor) {
    ClawSpeechImage out{};
    const uint32_t parent = read(r, actor + 0xc), registry = read(r, parent + 0x10) + 16;
    if (bad(r))
        return out;
    const uint32_t root = call(r, 0x4f6286, registry, {0x52c580}, "GAME_EXCLAMATION");
    if (bad(r))
        return out;
    auto *a = span(r, actor, 128);
    if (!a)
        return out;
    ClawActorBindingContext c{};
    c.imageRegistryToken = registry;
    c.image.token = root;
    uint32_t leaf = 0;
    if (root) {
        auto *h = span(r, root, 27);
        if (!h)
            return out;
        c.image.minimum = int32_t(h[25]);
        c.image.maximum = int32_t(h[26]);
        c.image.firstImageIndex = c.image.minimum;
        c.image.images = &leaf;
        c.image.imageCount = 1;
        if (c.image.minimum <= c.image.maximum)
            leaf = read(r, h[5] + uint32_t(c.image.minimum) * 4);
        if (bad(r))
            return out;
        out = {root, h[25], h[26], leaf};
    }
    ClawActorResourceBindings b{};
    std::copy_n(a, 128, b.actor);
    if (!claw_actor_bind_default_image(&b, &c, "GAME_EXCLAMATION", resolved, nullptr)) {
        r.c->fault = 1;
        return out;
    }
    std::copy_n(b.actor, 128, a);
    return out;
}
uint32_t npcQueue(Run &r, uint32_t speaker, uint32_t sound, uint32_t force) {
    auto &g = *r.c->globals;
    if (!speaker || !sound || !g.enemyActorToken || (!force && g.enemyBusy))
        return 0;
    const uint32_t logic = read(r, g.enemyActorToken + 0x6c);
    if (bad(r) || !logic)
        return 0;
    write(r, g.enemyActorToken + 0x184, sound);
    write(r, read(r, g.enemyActorToken + 0x6c) + 0x1c, 1001);
    if (bad(r))
        return 0;
    g.speakerToken = speaker;
    return 1;
}
uint32_t npcName(Run &r, uint32_t speaker, uint32_t name, uint32_t force) {
    auto &g = *r.c->globals;
    if (!speaker || !name || !g.enemyActorToken || (!force && g.enemyBusy))
        return 0;
    if (!read(r, g.enemyActorToken + 0x6c) || bad(r))
        return 0;
    const uint32_t scene = read(r, g.managerToken + 0x30), registry = read(r, scene + 0x28) + 16;
    if (bad(r))
        return 0;
    const uint32_t sound = call(r, 0x4f6286, registry, {name}, r.c->nameHint);
    if (!sound || bad(r))
        return 0;
    write(r, g.enemyActorToken + 0x184, sound);
    write(r, read(r, g.enemyActorToken + 0x6c) + 0x1c, 1001);
    if (bad(r))
        return 0;
    g.speakerToken = speaker;
    return 1;
}
uint32_t playerQueue(Run &r, uint32_t sound, uint32_t force) {
    auto &g = *r.c->globals;
    ClawAudioRouting routing{};
    routing.speechActorPresent = g.clawActorToken != 0;
    routing.speechBusy = g.clawBusy;
    if (!sound || !routing.speechActorPresent || (!force && routing.speechBusy))
        return 0;
    const uint32_t logic = read(r, g.clawActorToken + 0x6c);
    if (bad(r))
        return 0;
    routing.speechLogicPresent = logic != 0;
    if (!logic)
        return 0;
    routing.playerPresent = g.playerToken != 0;
    if (!force && g.playerToken)
        routing.playerLogicState = read(r, read(r, g.playerToken + 0x6c) + 0x1c);
    if (bad(r))
        return 0;
    const uint32_t result = claw_audio_queue_speech(&routing, sound, force);
    if (result) {
        write(r, g.clawActorToken + 0x184, routing.queuedSpeechToken);
        write(r, read(r, g.clawActorToken + 0x6c) + 0x1c, routing.speechLogicState);
    }
    return bad(r) ? 0 : result;
}
uint32_t playerName(Run &r, uint32_t name, uint32_t force, const char *hint) {
    auto &g = *r.c->globals;
    if (!name || !g.clawActorToken)
        return 0;
    const uint32_t registry = read(r, read(r, g.clawActorToken + 0xc) + 0x28) + 16;
    if (bad(r))
        return 0;
    const uint32_t sound = call(r, 0x4f6286, registry, {name}, hint);
    return sound && !bad(r) ? playerQueue(r, sound, force) : 0;
}
void enemyUpdate(Run &r, uint32_t actor) {
    auto &g = *r.c->globals;
    const uint32_t logic = read(r, actor + 0x6c), state = read(r, logic + 0x1c);
    if (bad(r))
        return;
    switch (state) {
    case 0:
        write(r, actor + 0x40, read(r, actor + 0x40) | 1);
        write(r, actor + 8, read(r, actor + 8) | 0xc0003);
        write(r, actor + 0xd0, 0x4000000);
        image(r, actor);
        if (!bad(r)) {
            write(r, logic + 0x1c, 5);
            g.enemyActorToken = actor;
        }
        break;
    case 5:
        g.enemyBusy = 0;
        g.speakerToken = 0;
        write(r, actor + 0x40, read(r, actor + 0x40) | 1);
        break;
    case 29:
        g.enemyActorToken = 0;
        break;
    case 1001: {
        const uint32_t sound = read(r, actor + 0x184);
        if (bad(r))
            break;
        if (!sound || !read(r, g.managerToken + 0x118)) {
            if (bad(r))
                break;
            write(r, logic + 0x1c, 5);
            write(r, actor + 0x184, 0);
            break;
        }
        const uint32_t pool = read(r, sound + 0x10), duration = read(r, pool + 0x28);
        if (bad(r))
            break;
        write(r, logic + 0x1c, 15);
        write(r, logic + 0x130, duration);
        const uint32_t live = read(r, actor + 0x184);
        if (!live || bad(r))
            break;
        uint32_t volume = read(r, g.managerToken + 0x12c) + 10;
        if (int32_t(volume) >= 100)
            volume = 100;
        if (g.audioManagerToken && !bad(r))
            call(r, 0x4b45f0, read(r, live + 0x10), {volume, 0, 0, 0});
        break;
    }
    case 15: {
        g.enemyBusy = 1;
        const uint32_t speaker = g.speakerToken;
        if (speaker) {
            if (read(r, speaker + 8) & 0x10000) {
                g.speakerToken = 0;
                write(r, logic + 0x130, 0);
            }
            if (bad(r))
                break;
        }
        if (!g.speakerToken)
            write(r, actor + 0x40, read(r, actor + 0x40) | 1);
        else {
            write(r, actor + 0x40, read(r, actor + 0x40) & ~1u);
            write(r, actor + 0x4c, read(r, g.speakerToken + 0x4c));
            const uint32_t py = read(r, g.speakerToken + 0x50), top = read(r, g.speakerToken + 0x11c);
            write(r, actor + 0x50, py + top - 30);
            const uint32_t z = read(r, g.speakerToken + 0x64) + 1;
            if (read(r, actor + 0x64) != z) {
                write(r, actor + 0x64, z);
                write(r, actor + 8, read(r, actor + 8) | 0x20000);
            }
        }
        const uint32_t remaining = read(r, logic + 0x130);
        write(r, logic + 0x130, g.stageDelta < remaining ? remaining - g.stageDelta : 0);
        if (!read(r, logic + 0x130) && !bad(r)) {
            write(r, actor + 0x184, 0);
            write(r, logic + 0x1c, 5);
        }
        break;
    }
    default:
        break;
    }
}
struct PlayerBridge {
    Run *run;
    ClawSpeechActor *state;
    uint32_t actor, logic;
};
void commit(PlayerBridge &b) {
    auto *a = span(*b.run, b.actor, 128), *l = span(*b.run, b.logic, 93);
    if (a && l) {
        std::copy_n(b.state->actor, 128, a);
        std::copy_n(b.state->logic, 93, l);
    }
}
void reload(PlayerBridge &b) {
    auto *a = span(*b.run, b.actor, 128), *l = span(*b.run, b.logic, 93);
    if (a && l) {
        std::copy_n(a, 128, b.state->actor);
        std::copy_n(l, 93, b.state->logic);
    }
}
void playerImage(void *u, uint32_t, uint32_t, ClawSpeechImage *out) {
    auto &b = *static_cast<PlayerBridge *>(u);
    commit(b);
    *out = image(*b.run, b.actor);
    reload(b);
}
uint32_t playerPlay(void *u, uint32_t pool, uint32_t volume, uint32_t pan, uint32_t pitch, uint32_t loop) {
    auto &b = *static_cast<PlayerBridge *>(u);
    commit(b);
    const uint32_t result = call(*b.run, 0x4b45f0, pool, {volume, pan, pitch, loop});
    reload(b);
    return result;
}
void playerUpdate(Run &r, uint32_t actor) {
    auto &g = *r.c->globals;
    const uint32_t logic = read(r, actor + 0x6c);
    auto *a = span(r, actor, 128), *l = span(r, logic, 93);
    if (!a || !l)
        return;
    ClawSpeechActor s{};
    std::copy_n(a, 128, s.actor);
    std::copy_n(l, 93, s.logic);
    const uint32_t mode = s.logic[7];
    ClawSpeechContext c{};
    c.actorToken = actor;
    c.registeredActorToken = g.clawActorToken;
    c.busy = g.clawBusy;
    c.managerAvailable = g.audioManagerToken != 0;
    c.stageDelta = g.stageDelta;
    if (mode == 1001 && s.actor[0x184 / 4]) {
        c.speechEnabled = read(r, g.managerToken + 0x118);
        if (c.speechEnabled) {
            c.queuedSoundPoolToken = read(r, s.actor[0x184 / 4] + 0x10);
            c.queuedSoundDuration = read(r, c.queuedSoundPoolToken + 0x28);
            c.speechVolume = read(r, g.managerToken + 0x12c);
        }
    }
    if (mode == 15 && g.playerToken) {
        c.playerPresent = 1;
        c.playerX = read(r, g.playerToken + 0x4c);
        c.playerY = read(r, g.playerToken + 0x50);
        c.playerHeight = read(r, g.playerToken + 0x11c);
        c.playerLayer = read(r, g.playerToken + 0x64);
        c.playerLogicState = read(r, read(r, g.playerToken + 0x6c) + 0x1c);
    }
    if (bad(r))
        return;
    PlayerBridge b{&r, &s, actor, logic};
    claw_speech_actor_update(&s, &c, {&b, playerImage, playerPlay});
    if (bad(r))
        return;
    commit(b);
    if (mode == 0 || mode == 29)
        g.clawActorToken = c.registeredActorToken;
    if (mode == 5 || (mode == 15 && c.playerPresent))
        g.clawBusy = c.busy;
}
uint32_t *hostLookup(void *u, uint32_t t, uint32_t n) {
    return span(*static_cast<Run *>(u), t, n);
}
uint32_t hostAllocate(void *u, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->scene.allocate) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->scene.allocate(r.c->scene.context, n);
}
void hostFree(void *u, uint32_t t) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->scene.free) {
        r.c->fault = 1;
        return;
    }
    r.c->scene.free(r.c->scene.context, t);
}
uint32_t hostCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    const char *name = e.function == 0x4f6286 ? (e.arguments[0] == 0x5223b8   ? "EnemyDialogSound"
                                                 : e.arguments[0] == 0x5223cc ? "ClawDialogSound"
                                                                              : nullptr)
                                              : nullptr;
    if (e.argumentCount == 1)
        return call(r, e.function, e.receiver, {e.arguments[0]}, name);
    return call(r, e.function, e.receiver);
}
const uint32_t deathNames[10] = {0x524e04, 0x524df8, 0x524dec, 0x524de0, 0x524dd4,
                                 0x524dc8, 0x524db8, 0x524da8, 0x524d98, 0x524d88};
const char *deathLabels[10] = {"CLAW_1001", "CLAW_1004A",   "CLAW_1004B",   "CLAW_1007A",   "CLAW_1007B",
                               "CLAW_1010", "CLAW_1110033", "CLAW_1110059", "CLAW_1110063", "CLAW_1110058"};
} // namespace
extern "C" uint32_t claw_enemy_speech_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n,
                                            ClawEnemySpeechContext *c, ClawEnemySpeechDependency dependency, void *user,
                                            uint32_t *result) {
    (void)receiver;
    if (!c || !c->globals)
        return 0;
    uint32_t required = (f == 0x48ce40 || f == 0x48ceb0) ? 3 : (f == 0x48c820 || f == 0x48c8a0) ? 2 : 1;
    if (f != 0x48ce40 && f != 0x48ceb0 && f != 0x48cc60 && f != 0x420370 && f != 0x48cf50 && f != 0x48cf90 &&
        f != 0x48c820 && f != 0x48c8a0 && f != 0x48c630)
        return 0;
    if (n != required || !args) {
        c->fault = 2;
        return 0;
    }
    Run r{c, dependency, user};
    if (bad(r))
        return 0;
    auto &g = *c->globals;
    uint32_t value = 0;
    switch (f) {
    case 0x48ce40:
        value = npcQueue(r, args[0], args[1], args[2]);
        break;
    case 0x48ceb0:
        value = npcName(r, args[0], args[1], args[2]);
        break;
    case 0x48cc60:
        enemyUpdate(r, args[0]);
        value = 1;
        break;
    case 0x48c630:
        playerUpdate(r, args[0]);
        value = 1;
        break;
    case 0x48c820:
        value = playerQueue(r, args[0], args[1]);
        break;
    case 0x48c8a0:
        value = playerName(r, args[0], args[1], c->nameHint);
        break;
    case 0x48cf90:
        value = uint32_t(args[0] == g.speakerToken);
        break;
    case 0x48cf50: {
        ClawActorDestructionGlobals d{g.enemyActorToken, g.speakerToken, 0};
        uint32_t fault = 0, ignored = 0;
        auto h = c->scene;
        claw_actor_destruction_entry(f, 0, args[0], &d, h, &fault, &ignored);
        if (fault)
            c->fault = 1;
        g.speakerToken = d.heldActorToken;
        break;
    }
    case 0x420370:
        if (g.playerToken && (args[0] == 2 || args[0] == 32)) {
            const int32_t choice = int32_t(call(r, 0x4a3050, 0)) % 10;
            if (choice >= 0 && !bad(r))
                playerName(r, deathNames[choice], 0, deathLabels[choice]);
        }
        break;
    }
    if (result)
        *result = value;
    return 1;
}
extern "C" uint32_t claw_enemy_speech_create(uint32_t container, uint32_t enemyProfile, ClawEnemySpeechContext *c,
                                             ClawEnemySpeechDependency dependency, void *user) {
    if (!c || !c->globals || c->fault)
        return 0;
    Run r{c, dependency, user};
    ClawSceneActorHost h{};
    h.context = &r;
    h.lookup = hostLookup;
    h.allocate = hostAllocate;
    h.free = hostFree;
    h.call = hostCall;
    uint32_t fault = 0;
    const uint32_t actor = claw_scene_actor_create_named(container, {0, 0, 0, 1000, 0, 0x40000},
                                                         enemyProfile ? 0x5223b8 : 0x5223cc, h, &fault);
    if (fault)
        c->fault = 2;
    return actor;
}
