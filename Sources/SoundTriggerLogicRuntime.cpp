#include "SoundTriggerLogicRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
int32_t si(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
struct Run {
    ClawSoundTriggerContext *c;
    ClawSoundTriggerDependency dependency;
    void *user;
    uint32_t visits = 0;
    void fail(uint32_t f = 1) {
        if (!c->fault)
            c->fault = f;
    }
    uint32_t *span(uint32_t t, uint32_t n) {
        if (c->fault)
            return nullptr;
        auto *p = c->scene.lookup ? c->scene.lookup(c->scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t read(uint32_t t) {
        auto *p = span(t, 1);
        return p ? *p : 0;
    }
    void put(uint32_t t, uint32_t v) {
        if (auto *p = span(t, 1))
            *p = v;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, uint32_t *temporary = nullptr,
                  uint32_t words = 0) {
        if (c->fault)
            return 0;
        if (!dependency || a.size() > 9) {
            fail();
            return 0;
        }
        ClawSoundTriggerCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        e.temporary = temporary;
        e.temporaryWords = words;
        std::copy(a.begin(), a.end(), e.arguments);
        return dependency(c, &e, user);
    }
    uint32_t alloc(uint32_t n) {
        if (c->fault)
            return 0;
        if (!c->scene.allocate) {
            fail();
            return 0;
        }
        return c->scene.allocate(c->scene.context, n);
    }
    void free(uint32_t t) {
        if (c->fault)
            return;
        if (!c->scene.free) {
            fail();
            return;
        }
        c->scene.free(c->scene.context, t);
    }
    bool next() {
        if (++visits > 1000000)
            fail(3);
        return !c->fault;
    }
};
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *, uint32_t * = nullptr);
uint32_t speechDependency(ClawEnemySpeechContext *, const ClawEnemySpeechCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (e->argumentCount == 0)
        return r.call(e->function, e->receiver);
    if (e->argumentCount == 1)
        return r.call(e->function, e->receiver, {e->arguments[0]});
    if (e->argumentCount == 2)
        return r.call(e->function, e->receiver, {e->arguments[0], e->arguments[1]});
    return r.call(e->function, e->receiver, {e->arguments[0], e->arguments[1], e->arguments[2], e->arguments[3]});
}
uint32_t queue(Run &r, uint32_t sound) {
    if (!r.c->composeSpeech)
        return r.call(0x48c820, 0, {sound, 0});
    ClawEnemySpeechContext s{};
    s.scene = r.c->scene;
    s.globals = r.c->globals;
    uint32_t a[2] = {sound, 0}, result = 0;
    if (!claw_enemy_speech_entry(0x48c820, 0, a, 2, &s, speechDependency, &r, &result) || s.fault)
        r.fail(s.fault ? s.fault : 2);
    return result;
}
void rectangle(Run &r, uint32_t actor, uint32_t logic, bool dialog) {
    uint32_t cb = r.read(logic + 16), left = 0xffffffc0, top = left, right = 64, bottom = 64;
    const uint32_t big = dialog ? 0x48ca40 : 0x48c410, small = dialog ? 0x48ca60 : 0x48c430,
                   huge = dialog ? 0x48ca80 : 0x48c450, tiny = dialog ? 0x48caa0 : 0x48c470,
                   tall = dialog ? 0x48cac0 : 0x48c490, wide = dialog ? 0x48cae0 : 0x48c4b0;
    if (cb == big) {
        left = top = 0xffffff80;
        right = bottom = 128;
    } else if (cb == small) {
        left = top = 0xffffffe0;
        right = bottom = 32;
    } else if (cb == huge) {
        left = top = 0xffffff00;
        right = bottom = 256;
    } else if (cb == tiny) {
        left = top = 0xfffffff0;
        right = bottom = 16;
    } else if (cb == tall) {
        left = 0xffffffe0;
        top = 0xffffff9c;
        right = 32;
        bottom = 100;
    } else if (cb == wide) {
        left = 0xffffff9c;
        top = 0xffffffe0;
        right = 100;
        bottom = 32;
    }
    r.put(actor + 0x128, left);
    r.put(actor + 0x12c, top);
    r.put(actor + 0x130, right);
    r.put(actor + 0x134, bottom);
}
bool inside(Run &r, uint32_t actor, uint32_t player) {
    const uint32_t x = r.read(actor + 0x4c), y = r.read(actor + 0x50), px = r.read(player + 0x4c),
                   py = r.read(player + 0x50);
    return si(r.read(actor + 0x128) + x) <= si(px) && si(px) <= si(r.read(actor + 0x130) + x) &&
           si(r.read(actor + 0x12c) + y) <= si(py) && si(py) <= si(r.read(actor + 0x134) + y);
}
uint32_t checkpoint(Run &r) {
    uint32_t p = r.c->globals->playerToken;
    return r.read(r.read(r.read(p + 0x6c) + 0x14) + 0x80);
}
void trigger(Run &r, uint32_t actor, bool dialog) {
    uint32_t logic = r.read(actor + 0x6c), state = r.read(logic + 0x1c);
    if (!state) {
        r.put(actor + 0xd0, 0x4000000);
        if (dialog)
            r.put(actor + 8, r.read(actor + 8) | 1);
        else
            r.put(actor + 8, (r.read(actor + 8) & ~2u) | 1);
        r.put(actor + 0x40, r.read(actor + 0x40) | 1);
        if (!r.read(actor + 0x108))
            r.put(actor + 0x108, 99999);
        rectangle(r, actor, logic, dialog);
        r.put(logic + 0x1c, 5);
        return;
    }
    uint32_t player = r.c->globals->playerToken;
    if (!player)
        return;
    if (state == 5 && inside(r, actor, player)) {
        if (dialog)
            queue(r, r.read(actor + 0x184));
        else {
            uint32_t sound = r.read(actor + 0x184);
            if (sound && r.c->globals->audioManagerToken)
                r.call(0x4b45f0, r.read(sound + 16), {r.c->masterVolume, 0, 0, 0});
        }
        uint32_t count = r.read(actor + 0x108);
        if (count == 1)
            r.put(actor + 8, r.read(actor + 8) | 0x10000);
        else if (dialog || si(count) > 1)
            r.put(actor + 0x108, count - 1);
        uint32_t mark = checkpoint(r);
        r.put(logic + 0x1c, 23);
        r.put(logic + 100, mark);
        if (!dialog && r.read(actor + 0x108) == 0xffffffff && r.read(actor + 0x184)) {
            r.put(logic + 0x1c, 11);
            r.put(logic + 32, r.read(r.read(r.read(actor + 0x184) + 16) + 40) + 100);
        }
    } else if (!dialog && state == 11 && !inside(r, actor, player))
        r.put(logic + 0x1c, 5);
    else if (state == 23 && r.read(logic + 100) != checkpoint(r))
        r.put(logic + 0x1c, 5);
}
bool strictRectangle(Run &r, uint32_t t, uint32_t x, uint32_t y) {
    return si(r.read(t)) < si(x) && si(x) < si(r.read(t + 8)) && si(r.read(t + 4)) < si(y) &&
           si(y) < si(r.read(t + 12));
}
uint32_t volume(Run &r, uint32_t t, uint32_t percentage) {
    uint32_t base = r.read(t + 12);
    if (si(base) > 5)
        base -= 15;
    uint32_t value = uint32_t(si(base * percentage) / 100);
    uint32_t scale = r.read(t + 16);
    if (si(scale) > 0)
        value = uint32_t(si(value * scale) / 100);
    return uint32_t(std::clamp(si(value), 0, 100));
}
// 0x4026a0: master volume is +0xc, independently of the live +8 percentage.
void setMasterVolume(Run &r, uint32_t t, uint32_t master) {
    if (r.read(t + 0xc) == master)
        return;
    r.put(t + 0xc, master);
    uint32_t value = volume(r, t, r.read(t + 8));
    r.call(0x4b3f40, r.read(t + 4), {value});
}
// 0x4024e0: publish before cleanup, then retain each next node across calls.
void setManagerMasterVolume(Run &r, uint32_t t, uint32_t master) {
    uint32_t audio = r.read(t);
    r.put(t + 4, master);
    uint32_t cleanup = r.read(audio + 0x2c);
    if (cleanup)
        r.call(0x4b4c10, cleanup);
    for (uint32_t node = r.read(t + 0xc); node && r.next();) {
        uint32_t next = r.read(node);
        uint32_t object = r.read(node + 8);
        if (object)
            setMasterVolume(r, object, master);
        node = next;
    }
}
void setVolume(Run &r, uint32_t t, uint32_t percent, uint32_t delay, uint32_t stop) {
    r.put(t + 8, percent);
    uint32_t v = volume(r, t, percent);
    if (!delay)
        r.call(0x4b3f40, r.read(t + 4), {v});
    else
        r.call(0x4b3fe0, r.read(t + 4), {v, delay, stop});
}
bool audioGate(Run &r) {
    uint32_t manager = r.c->globals->managerToken;
    return r.read(manager + 16) && r.read(r.read(manager + 0x5c) + 0x24);
}
void switchPlay(Run &r, uint32_t t, uint32_t play, uint32_t percent, uint32_t delay) {
    uint32_t sound = r.read(t + 4);
    if (!sound)
        return;
    if (!play) {
        if (r.read(t + 20)) {
            if (!delay)
                r.call(0x4b3e30, sound);
            else {
                r.put(t + 8, 0);
                r.call(0x4b3fe0, sound, {0, delay, 1});
            }
            r.put(t + 20, 0);
        }
        return;
    }
    if (!r.read(t + 20) && audioGate(r)) {
        r.call(0x4b3dc0, sound, {1, r.read(t + 56), 0, 1});
        setVolume(r, t, percent, delay, 0);
        r.put(t + 8, percent);
        r.put(t + 20, 1);
    }
}
uint32_t choice(Run &r, uint32_t minimum, uint32_t maximum) {
    uint32_t divisor = maximum - minimum + 1, random = r.call(0x4a3050, 0);
    if (!divisor)
        return (random & 1) ? minimum : maximum;
    if (si(divisor) == -1 && si(random) == INT32_MIN) {
        r.fail(3);
        return 0;
    }
    return uint32_t(si(random) % si(divisor)) + minimum;
}
uint32_t createAmbient(Run &r, uint32_t f, uint32_t manager, const uint32_t *a, uint32_t *temporary) {
    uint32_t object = r.alloc(f == 0x4022f0 ? 64 : f == 0x402370 ? 72 : 88);
    if (!object)
        return 0;
    r.put(object, f == 0x4022f0 ? 0x50b004 : f == 0x402370 ? 0x50b01c : 0x50b02c);
    r.put(object + 4, 0);
    r.put(object + 8, 100);
    r.put(object + 20, 0);
    r.put(object + 60, 0);
    uint32_t init[5] = {a[0], a[1], r.read(manager + 4), a[2], a[3]};
    if (!entry(r, f == 0x402370 ? 0x402a60 : 0x402610, object, init, temporary)) {
        uint32_t deleteArg[1] = {1};
        entry(r, 0x4022d0, object, deleteArg);
        return 0;
    }
    if (f == 0x402400) {
        for (uint32_t i = 0; i < 4; ++i)
            r.put(object + 64 + i * 4, a[4 + i]);
        r.put(object + 80, choice(r, a[6], a[7]));
        r.put(object + 84, 1);
    }
    r.put(object + 60, r.call(0x4f51c5, manager + 8, {object}));
    return object;
}
void ambientActor(Run &r, uint32_t actor, bool spot) {
    uint32_t logic = r.read(actor + 0x6c), mode = r.read(logic + 28);
    if (!mode) {
        uint32_t flags = r.read(actor + 8);
        r.put(actor + 64, r.read(actor + 64) | 1);
        if (spot) {
            r.put(actor + 8, (flags & ~2u) | 0x100001);
            r.put(logic + 0x168, 0);
        } else {
            r.put(actor + 8, flags | 1);
            r.put(actor + 8, r.read(logic + 16) == 0x402ca0 ? (flags | 3) : ((flags & ~2u) | 1));
        }
        uint32_t sound = r.read(actor + 0x184), manager = r.c->globals->managerToken;
        if (sound && manager) {
            uint32_t owner = r.read(manager + 0x5c);
            if (owner) {
                uint32_t temporary[4];
                uint32_t args[9] = {r.read(sound + 16), 100, 0, r.read(actor + 0x104), 0, 0, 0, 0, 0};
                if (spot) {
                    temporary[0] = r.read(actor + 76);
                    temporary[1] = r.read(actor + 80);
                    uint32_t object = createAmbient(r, 0x402370, owner, args, temporary);
                    if (object)
                        r.put(logic + 0x168, object);
                } else {
                    for (uint32_t i = 0; i < 4; ++i)
                        temporary[i] = r.read(actor + 0x128 + i * 4);
                    if (si(r.read(logic + 44)) > 0 || si(r.read(logic + 48)) > 0) {
                        temporary[0] = r.read(logic + 44);
                        temporary[1] = r.read(logic + 52);
                        temporary[2] = r.read(logic + 48);
                        temporary[3] = r.read(logic + 56);
                    }
                    uint32_t factory = 0x4022f0;
                    if (si(r.read(actor + 0x11c)) > 0) {
                        factory = 0x402400;
                        for (uint32_t i = 0; i < 4; ++i)
                            args[4 + i] = r.read(actor + 0x118 + i * 4);
                    }
                    uint32_t object = createAmbient(r, factory, owner, args, temporary);
                    if (object && si(r.read(actor + 0x13c)) > 0)
                        for (uint32_t i = 0; i < 4; ++i)
                            r.put(object + 40 + i * 4, r.read(actor + 0x138 + i * 4));
                }
            }
        }
        if (!spot)
            r.put(actor + 8, r.read(actor + 8) | 0x10000);
        r.put(logic + 28, 5);
    } else if (spot && mode == 30) {
        uint32_t object = r.read(logic + 0x168);
        if (object) {
            uint32_t owner = r.read(r.c->globals->managerToken + 0x5c);
            if (r.read(object + 4)) {
                r.call(0x4b3e30, r.read(object + 4));
                r.put(object + 20, 0);
            }
            if (r.read(object + 60)) {
                r.call(0x4f5212, owner + 8, {r.read(object + 60)});
                uint32_t arg[1] = {1};
                entry(r, 0x4022d0, object, arg);
            }
            r.put(logic + 0x168, 0);
            r.put(logic + 28, 0);
        }
    }
}
void rectangularUpdate(Run &r, uint32_t t, const uint32_t *a, bool repeat) {
    bool global = r.read(t + 24) == 0x80000000;
    bool inside = global || strictRectangle(r, t + 24, a[0], a[1]) ||
                  (r.read(t + 40) != 0x80000000 && strictRectangle(r, t + 40, a[0], a[1]));
    if (!repeat) {
        if (global) {
            if (r.read(t + 20) || !r.read(t + 4) || !r.read(t + 8) || !audioGate(r))
                return;
        } else {
            if (r.read(t + 20)) {
                if (!inside)
                    switchPlay(r, t, 0, 0, 1000);
                return;
            }
            if (!inside || !audioGate(r))
                return;
            if (!a[2]) {
                switchPlay(r, t, 1, 100, 1000);
                return;
            }
            if (!r.read(t + 4))
                return;
        }
        r.call(0x4b3dc0, r.read(t + 4), {1, r.read(t + 56), 0, 1});
        setVolume(r, t, 100, 0, 0);
        r.put(t + 8, 100);
        r.put(t + 20, 1);
        return;
    }
    if (!inside) {
        if (r.read(t + 20) && r.read(t + 4)) {
            setVolume(r, t, 0, 1000, 1);
            r.put(t + 20, 0);
        }
        r.put(t + 84, 0);
        return;
    }
    if (!a[2] || !r.read(t + 84)) {
        uint32_t time = r.read(t + 80), delta = r.c->globals->stageDelta;
        r.put(t + 80, delta < time ? time - delta : 0);
        if (!r.read(t + 80)) {
            uint32_t bit = r.read(t + 84) ^ 1;
            r.put(t + 84, bit);
            uint32_t minimum = r.read(t + (bit ? 64 : 72)), maximum = r.read(t + (bit ? 68 : 76));
            r.put(t + 80, choice(r, minimum, maximum));
            switchPlay(r, t, bit ? 1 : 0, 100, 1000);
        }
    } else if (r.read(t + 4) && !r.read(t + 20) && audioGate(r)) {
        r.call(0x4b3dc0, r.read(t + 4), {1, r.read(t + 56), 0, 1});
        setVolume(r, t, 100, 0, 0);
        r.put(t + 8, 100);
        r.put(t + 20, 1);
    }
}
void positionalUpdate(Run &r, uint32_t t, const uint32_t *a) {
    uint32_t ox = r.read(t + 64), dx = ox - a[0], dy = r.read(t + 68) - a[1];
    uint32_t sign = si(dx) < 0 ? 0xffffffff : 0;
    dx = (dx ^ sign) - sign;
    sign = si(dy) < 0 ? 0xffffffff : 0;
    dy = (dy ^ sign) - sign;
    if (si(dx) <= 640 && si(dy) <= 640) {
        uint32_t square = dx * dx + dy * dy;
        uint32_t distance = si(square) < 0 ? 0 : uint32_t(std::sqrt(double(si(square))));
        uint32_t percentage = uint32_t(std::clamp(100 - si(distance) / 12, 0, 100));
        uint32_t pan = uint32_t(std::clamp(si(dx) / 4, 0, 100));
        if (si(ox) < si(a[0]))
            pan = 0 - pan;
        r.put(t + 8, percentage);
        uint32_t v = volume(r, t, percentage);
        r.call(0x4b3f40, r.read(t + 4), {v});
        r.put(t + 56, pan);
        r.call(0x4b4110, r.read(t + 4), {pan});
        if (!r.read(t + 20) && r.read(t + 4) && audioGate(r)) {
            r.call(0x4b3dc0, r.read(t + 4), {1, r.read(t + 56), 0, 1});
            setVolume(r, t, percentage, 0, 0);
            r.put(t + 8, percentage);
            r.put(t + 20, 1);
        }
    } else if (r.read(t + 4) && r.read(t + 20)) {
        r.call(0x4b3e30, r.read(t + 4));
        r.put(t + 20, 0);
    }
}
void ambientVirtual(Run &r, uint32_t object, const uint32_t *a, bool destroy) {
    uint32_t vtable = r.read(object), f = 0;
    if (vtable == 0x50b004)
        f = destroy ? 0x4022d0 : 0x402720;
    else if (vtable == 0x50b01c)
        f = destroy ? 0x4022d0 : 0x402ac0;
    else if (vtable == 0x50b02c)
        f = destroy ? 0x4022d0 : 0x402f10;
    else
        f = r.read(vtable + (destroy ? 0 : 4));
    if (f == 0x4022d0 || f == 0x402720 || f == 0x402ac0 || f == 0x402f10)
        entry(r, f, object, a);
    else if (destroy)
        r.call(f, object, {a[0]});
    else
        r.call(f, object, {a[0], a[1], a[2]});
}
void ambientManager(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    if (f == 0x402270 || f == 0x402520) {
        uint32_t audio = r.read(t);
        if (audio && r.read(audio + 44))
            r.call(0x4b4c10, r.read(audio + 44));
    }
    if (f == 0x4025c0) {
        r.put(t + 40, a[0]);
        r.put(t + 44, a[1]);
    }
    uint32_t x = r.read(t + 40), y = r.read(t + 44);
    for (uint32_t node = r.read(t + 12); node && r.next();) {
        uint32_t object = r.read(node + 8);
        node = r.read(node);
        if (object) {
            if (f == 0x402270 || f == 0x4022a0) {
                uint32_t args[1] = {1};
                ambientVirtual(r, object, args, true);
            } else if (f == 0x402520) {
                if (r.read(object + 4)) {
                    r.call(0x4b3e30, r.read(object + 4));
                    r.put(object + 20, 0);
                }
            } else {
                if (f == 0x402570)
                    r.put(object + 20, 0);
                uint32_t args[3] = {f == 0x402570 ? r.read(t + 40) : x, f == 0x402570 ? r.read(t + 44) : y,
                                    f == 0x402570 ? 1u : 0u};
                ambientVirtual(r, object, args, false);
            }
        }
    }
    if (f == 0x402270 || f == 0x4022a0) {
        r.call(0x4f5172, t + 8);
        if (f == 0x402270)
            r.put(t, 0);
    } else if (f == 0x4025c0 || f == 0x402570) {
        uint32_t audio = r.read(t);
        if (r.read(audio + 44))
            r.call(0x4b4b80, r.read(audio + 44));
    }
}
bool actorCallback(uint32_t f) {
    return f == 0x48c1e0 || f == 0x48c8f0 || f == 0x402cc0 || f == 0x402e20 || f == 0x402ca0 || f == 0x402e00 ||
           (f >= 0x48c410 && f <= 0x48c4b0 && (f - 0x48c410) % 32 == 0) ||
           (f >= 0x48ca40 && f <= 0x48cae0 && (f - 0x48ca40) % 32 == 0);
}
uint32_t entry(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t *temporary) {
    if (actorCallback(f)) {
        if (f >= 0x48c410 && f <= 0x48c4b0)
            r.c->triggerProfile = (f - 0x48c410) / 32 + 1;
        if (f >= 0x48ca40 && f <= 0x48cae0)
            r.c->triggerProfile = (f - 0x48ca40) / 32 + 7;
        if (f == 0x402ca0)
            r.c->ambientProfile = 1;
        if (f == 0x402e00)
            r.c->ambientProfile = 2;
        if (f == 0x402ca0 || f == 0x402cc0 || f == 0x402e00 || f == 0x402e20)
            ambientActor(r, a[0], f == 0x402e00 || f == 0x402e20);
        else
            trigger(r, a[0], f == 0x48c8f0 || f >= 0x48ca40);
        return 1;
    }
    if (f == 0x48c4d0 || f == 0x48cb00) {
        rectangle(r, a[0], a[1], f == 0x48cb00);
        return 0;
    }
    if (f == 0x4022f0 || f == 0x402370 || f == 0x402400)
        return createAmbient(r, f, t, a, temporary);
    if (f == 0x402610 || f == 0x402a60) {
        if (!a[0] || (f == 0x402a60 && !a[3] && !temporary))
            return 0;
        for (uint32_t i = 0; i < 4; ++i)
            r.put(t + 4 + i * 4, a[i == 0 ? 0 : i == 1 ? 1 : i == 2 ? 2 : 4]);
        r.put(t + 56, 0);
        r.put(t + 20, 0);
        uint32_t *p = temporary ? temporary : (a[3] ? r.span(a[3], f == 0x402610 ? 4 : 2) : nullptr);
        if (r.c->fault)
            return 0;
        if (f == 0x402a60) {
            r.put(t + 64, p[0]);
            r.put(t + 68, p[1]);
            return 1;
        }
        if (p)
            for (uint32_t i = 0; i < 4; ++i)
                r.put(t + 24 + i * 4, p[i]);
        else
            r.put(t + 24, 0x80000000);
        if (!r.read(t + 24) && !r.read(t + 28) && !r.read(t + 32) && !r.read(t + 36))
            r.put(t + 24, 0x80000000);
        r.put(t + 40, 0x80000000);
        return 1;
    }
    if (f == 0x4023f0 || f == 0x4022d0) {
        r.put(t, 0x50b014);
        r.put(t + 4, 0);
        r.put(t + 60, 0);
        if (f == 0x4022d0) {
            if (a[0] & 1)
                r.free(t);
            return t;
        }
        return 0;
    }
    if (f == 0x4f5133) {
        for (uint32_t off : {12u, 16u, 8u, 4u, 20u})
            r.put(t + off, 0);
        r.put(t, 0x51000c);
        r.put(t + 24, a[0]);
        return t;
    }
    if (f == 0x402240) {
        if (!a[0])
            return 0;
        r.put(t, a[0]);
        r.put(t + 4, a[1]);
        r.put(t + 36, 1);
        r.put(t + 40, 0);
        r.put(t + 44, 0);
        return 1;
    }
    if (f == 0x4024e0) {
        setManagerMasterVolume(r, t, a[0]);
        return 0;
    }
    if (f == 0x4026a0) {
        setMasterVolume(r, t, a[0]);
        return 0;
    }
    if (f == 0x402270 || f == 0x4022a0 || f == 0x402520 || f == 0x402570 || f == 0x4025c0) {
        ambientManager(r, f, t, a);
        return 0;
    }
    if (f == 0x402720 || f == 0x402f10) {
        rectangularUpdate(r, t, a, f == 0x402f10);
        return 0;
    }
    if (f == 0x402ac0) {
        positionalUpdate(r, t, a);
        return 0;
    }
    if (f == 0x402840) {
        setVolume(r, t, a[0], a[1], a[2]);
        return 0;
    }
    if (f == 0x4028c0) {
        switchPlay(r, t, a[0], a[1], a[2]);
        return 0;
    }
    r.fail(2);
    return 0;
}
} // namespace
extern "C" uint32_t claw_sound_trigger_entry(uint32_t f, uint32_t t, ClawSoundTriggerArguments a,
                                             ClawSoundTriggerContext *c, ClawSoundTriggerDependency dependency,
                                             void *user, uint32_t *result) {
    uint32_t n = 0;
    if (actorCallback(f))
        n = 1;
    else
        switch (f) {
        case 0x48c4d0:
        case 0x48cb00:
        case 0x402240:
        case 0x4025c0:
            n = 2;
            break;
        case 0x4022f0:
        case 0x402370:
        case 0x402610:
        case 0x402a60:
            n = 5;
            break;
        case 0x402400:
            n = 9;
            break;
        case 0x4022d0:
        case 0x4024e0:
        case 0x4026a0:
        case 0x4f5133:
            n = 1;
            break;
        case 0x4023f0:
        case 0x402270:
        case 0x4022a0:
        case 0x402520:
        case 0x402570:
            break;
        case 0x402840:
        case 0x4028c0:
        case 0x402720:
        case 0x402ac0:
        case 0x402f10:
            n = 3;
            break;
        default:
            return 0;
        }
    if (!c || !c->globals)
        return 0;
    if (a.count != n) {
        c->fault = 2;
        return 0;
    }
    Run r{c, dependency, user};
    uint32_t value = entry(r, f, t, a.words);
    if (result)
        *result = value;
    return c->fault ? 0 : 1;
}

extern "C" uint32_t claw_sound_trigger_construct_manager(uint32_t t, ClawSoundTriggerContext *c) {
    if (!c || c->fault)
        return 0;
    Run r{c, nullptr, nullptr};
    uint32_t args[1] = {10};
    entry(r, 0x4f5133, t + 8, args);
    r.put(t, 0);
    r.put(t + 4, 100);
    return c->fault ? 0 : 1;
}
