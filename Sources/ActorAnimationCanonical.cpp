// Original actor animation selection and callers, translated from the packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x420970: return 1;
    case 0x420a10: return 2;
    case 0x4c79e0: return 2;
    case 0x4c7a40: return 1;
    case 0x4c8210: return 0;
    case 0x4c8220: return 1;
    case 0x4c8260: return 1;
    case 0x4c82a0: return 1;
    case 0x4c87f0: return 1;
    case 0x4c8810: return 0;
    default: return -1;
    }
}

struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, uint32_t descent) : run(run), saved(run.frame) {
        run.frame -= descent;
    }
    ~Frame() {
        run.frame = saved;
    }
};

// 0x4c87f0. Sequence +0x10 signed count, +0x0c raw record-token table.
uint32_t record(Run &run, uint32_t sequence, uint32_t index) {
    if (s32(index) < 0 || s32(index) >= s32(run.get(sequence + 0x10)))
        return 0;
    return run.get(run.get(sequence + 0x0c) + index * 4);
}

// 0x4c8810. Actor +0x170 image manager, +0x16c ID, +0x174 image token.
void lastImage(Run &run, uint32_t actor) {
    uint32_t manager = run.get(actor + 0x170);
    if (!manager)
        return;
    uint32_t id = run.get(manager + 0x68);
    run.put(actor + 0x16c, id);
    uint32_t image = 0;
    if (s32(id) >= s32(run.get(manager + 0x64)) && s32(id) <= s32(run.get(manager + 0x68)))
        image = run.get(run.get(manager + 0x14) + id * 4);
    run.put(actor + 0x174, image);
}

// 0x420970. State +0x08 sequence, +0x0c record, +0x10 index,
// +0x14 delay, +0x1c stopped, +0x20 current result, +0x24 previous result.
void seek(Run &run, uint32_t state, uint32_t index) {
    uint32_t sequence = run.get(state + 0x08);
    run.put(state + 0x10, index);
    uint32_t token = record(run, sequence, index);
    run.put(state + 0x0c, token);
    if (!token) {
        run.put(state + 0x10, 0);
        uint32_t first = 0;
        if (s32(run.get(sequence + 0x10)) > 0)
            first = run.get(run.get(sequence + 0x0c));
        run.put(state + 0x0c, first);
    }
    token = run.get(state + 0x0c);
    if (token) {
        uint32_t previous = run.get(state + 0x20);
        run.put(state + 0x1c, 0);
        run.put(state + 0x14, 0);
        run.put(state + 0x24, previous);
        run.put(state + 0x20, run.get(token + 0x1c));
    }
}

// 0x4c8210. Clear exactly actor, sequence, record pointers.
void clear(Run &run, uint32_t state) {
    run.put(state + 0x04, 0);
    run.put(state + 0x08, 0);
    run.put(state + 0x0c, 0);
}

// 0x4c8220. State +0x28 speed bits; record +0x1c result.
void select(Run &run, uint32_t state, uint32_t sequence) {
    run.put(state + 0x08, sequence);
    if (!sequence)
        return;
    run.put(state + 0x10, 0);
    uint32_t token = 0;
    if (s32(run.get(sequence + 0x10)) > 0)
        token = run.get(run.get(sequence + 0x0c));
    run.put(state + 0x0c, token);
    run.put(state + 0x14, 0);
    run.put(state + 0x1c, 0);
    uint32_t result = run.get(token + 0x1c);
    run.put(state + 0x20, result);
    run.put(state + 0x24, result);
    run.put(state + 0x28, 0x3f800000);
}

// 0x4c8260.
void reset(Run &run, uint32_t state, uint32_t clearDelay) {
    uint32_t sequence = run.get(state + 0x08);
    if (!sequence)
        return;
    run.put(state + 0x10, 0);
    uint32_t token = 0;
    if (s32(run.get(sequence + 0x10)) > 0)
        token = run.get(run.get(sequence + 0x0c));
    run.put(state + 0x0c, token);
    run.put(state + 0x1c, 0);
    uint32_t result = run.get(token + 0x1c);
    run.put(state + 0x28, 0x3f800000);
    run.put(state + 0x20, result);
    run.put(state + 0x24, result);
    if (clearDelay)
        run.put(state + 0x14, 0);
}

// 0x4c82a0. State +0x04 actor, +0x18 timed-delay flag.
// Record +0x04 flags, +0x08 image command, +0x0c control, +0x10 motion,
// +0x14 image operand, +0x18 duration, +0x20/+0x24 motion, +0x2c sound.
uint32_t update(Run &run, uint32_t state, uint32_t delta) {
    if (!run.get(state + 0x08))
        return 0xffffffff;
    uint32_t delay = run.get(state + 0x14);
    if (delay) {
        if (!run.get(state + 0x18)) {
            run.put(state + 0x14, delay - 1);
            return run.get(state + 0x24);
        }
        if (delta < delay) {
            run.put(state + 0x14, delay - delta);
            return run.get(state + 0x24);
        }
        uint32_t current = run.get(state + 0x20);
        run.put(state + 0x14, 0);
        run.put(state + 0x24, current);
    } else {
        run.put(state + 0x24, run.get(state + 0x20));
    }
    if (run.get(state + 0x1c))
        return run.get(state + 0x20);
    uint32_t token = run.get(state + 0x0c);
    uint32_t command = run.get(token + 0x08);
    if (command - 1 <= 6) {
        uint32_t actor = run.get(state + 0x04);
        uint32_t operand = 0;
        if (command == 3 || command == 6 || command == 7)
            operand = run.get(token + 0x14);
        uint32_t manager = run.get(actor + 0x170);
        if (manager) {
            uint32_t id = 0;
            uint32_t image = 0;
            switch (command) {
            case 1:
                id = run.get(actor + 0x16c) + 1;
                run.put(actor + 0x16c, id);
                image = run.call(0x40f680, manager, {id});
                run.put(actor + 0x174, image);
                if (!image) {
                    manager = run.get(actor + 0x170);
                    id = run.get(manager + 0x64);
                    run.put(actor + 0x16c, id);
                    image = run.call(0x40f680, manager, {id});
                    run.put(actor + 0x174, image);
                }
                break;
            case 2:
                id = run.get(actor + 0x16c);
                if (id == run.get(manager + 0x64))
                    run.put(actor + 0x16c, run.get(manager + 0x68));
                else
                    run.put(actor + 0x16c, id - 1);
                id = run.get(actor + 0x16c);
                image = run.call(0x40f680, manager, {id});
                run.put(actor + 0x174, image);
                break;
            case 3:
                image = run.call(0x40f680, manager, {operand});
                run.put(actor + 0x174, image);
                run.put(actor + 0x16c, operand);
                break;
            case 4:
            case 5:
                id = run.get(manager + (command == 4 ? 0x64 : 0x68));
                run.put(actor + 0x16c, id);
                image = run.call(0x40f680, manager, {id});
                run.put(actor + 0x174, image);
                break;
            case 6:
            case 7:
                id = run.get(actor + 0x16c);
                id = command == 6 ? id + operand : id - operand;
                run.put(actor + 0x16c, id);
                image = run.call(0x40f680, manager, {id});
                run.put(actor + 0x174, image);
                if (!image) {
                    if (command == 6) {
                        Frame frame(run, 0x1c);
                        lastImage(run, actor);
                    } else {
                        run.call(0x47e1d0, actor);
                    }
                }
                break;
            }
        }
    }
    uint32_t actor = run.get(state + 0x04);
    run.put(actor + 0x10, 0);
    run.put(actor + 0x14, 0);
    token = run.get(state + 0x0c);
    uint32_t motion = run.get(token + 0x10);
    if (motion == 1) {
        uint32_t y = run.get(token + 0x24);
        actor = run.get(state + 0x04);
        uint32_t x = run.get(token + 0x20);
        run.put(actor + 0x10, x);
        run.put(actor + 0x14, y);
    } else if (motion == 2) {
        actor = run.get(state + 0x04);
        uint32_t orientation = run.get8(actor + 0x40);
        uint32_t x = run.get(actor + 0x4c);
        uint32_t dy = run.get(token + 0x24);
        uint32_t dx = run.get(token + 0x20);
        x = orientation & 2 ? x - dx : x + dx;
        uint32_t y = run.get(actor + 0x50) + dy;
        run.put(actor + 0x4c, x);
        run.put(actor + 0x50, y);
    } else if (motion == 3) {
        actor = run.get(state + 0x04);
        run.put(actor + 0x4c, run.get(token + 0x20));
        token = run.get(state + 0x0c);
        actor = run.get(state + 0x04);
        run.put(actor + 0x50, run.get(token + 0x24));
    }
    token = run.get(state + 0x0c);
    if (run.get8(token + 0x04) & 4) {
        actor = run.get(state + 0x04);
        uint32_t sound = run.get(token + 0x2c);
        uint32_t x = run.get(actor + 0x4c);
        if (sound)
            run.call(0x4c88e0, sound, {x, 0, 0, 0});
    } else {
        uint32_t sound = run.get(token + 0x2c);
        if (sound)
            run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
    }
    token = run.get(state + 0x0c);
    uint32_t speed = run.get(state + 0x28);
    uint32_t duration = run.get(token + 0x18);
    run.put(state + 0x14, duration);
    uint32_t timed = (~run.get8(token + 0x04)) & 1;
    run.put(state + 0x18, timed);
    if (speed != 0x3f800000) {
        run.put(run.automatic(-8), duration);
        run.put(run.automatic(-4), 0);
        double scaled = double(duration) * double(run.getf(state + 0x28));
        uint32_t converted = run.call_x87(0x4a30e0, 0, scaled);
        run.put(state + 0x14, converted);
    }
    uint32_t control = run.get(token + 0x0c);
    uint32_t kind = control & 0xffff;
    bool advance = false;
    if (kind == 0)
        advance = control != 9;
    else if (kind >= 1 && kind <= 5) {
        actor = run.get(state + 0x04);
        uint32_t target = 0;
        if (kind == 1) {
            target = run.get(token + 0x14);
        } else {
            uint32_t manager = run.get(actor + 0x170);
            uint32_t id = run.get(actor + 0x16c);
            if (kind == 2 || kind == 4)
                target = run.get(manager + 0x64);
            else
                target = run.get(manager + 0x68);
            if (kind == 4)
                target += 1;
            if (kind == 5)
                target -= 1;
            advance = id == target && control != 9;
        }
        if (kind == 1)
            advance = run.get(actor + 0x16c) == target && control != 9;
    }
    if (advance || kind == 7) {
        uint32_t index = kind == 7 ? 1 : run.get(state + 0x10) + 1;
        uint32_t sequence = run.get(state + 0x08);
        run.put(state + 0x10, index);
        uint32_t next;
        {
            Frame frame(run, 0x20);
            next = record(run, sequence, index);
        }
        run.put(state + 0x0c, next);
        if (!next) {
            if (kind <= 2 || kind == 7)
                sequence = run.get(state + 0x08);
            run.put(state + 0x10, 0);
            {
                Frame frame(run, 0x20);
                next = record(run, sequence, 0);
            }
            run.put(state + 0x0c, next);
        }
        next = run.get(state + 0x0c);
        if (next) {
            uint32_t previous = run.get(state + 0x20);
            if (kind == 7) {
                run.put(state + 0x1c, 0);
                run.put(state + 0x14, 0);
            }
            run.put(state + 0x24, previous);
            run.put(state + 0x20, run.get(next + 0x1c));
        }
    } else if (kind == 8) {
        uint32_t sequence = run.get(state + 0x08);
        if (sequence) {
            run.put(state + 0x10, 0);
            uint32_t next;
            {
                Frame frame(run, 0x20);
                next = record(run, sequence, 0);
            }
            run.put(state + 0x0c, next);
            run.put(state + 0x1c, 0);
            uint32_t result = run.get(next + 0x1c);
            run.put(state + 0x28, 0x3f800000);
            run.put(state + 0x20, result);
            run.put(state + 0x24, result);
        }
    } else if (kind == 9) {
        run.put(state + 0x1c, 1);
    }
    if (run.get(state + 0x14))
        return run.get(state + 0x24);
    return run.get(state + 0x20);
}

// 0x420a10. Actor +0x188 embedded animation state.
void setSequence(Run &run, uint32_t actor, uint32_t sequence, uint32_t immediate) {
    {
        Frame frame(run, 0x0c);
        select(run, actor + 0x188, sequence);
    }
    if (immediate) {
        Frame frame(run, 0x0c);
        update(run, actor + 0x188, run.get(0x5430c4));
    }
}

// 0x4c79e0, 0x4c7a40. Actor +0x0c resources; container +0x28/+0x2c
// action/sequence manager; manager +0x10 original dictionary.
uint32_t named(Run &run, uint32_t actor, uint32_t name, uint32_t immediate, bool action) {
    uint32_t container = run.get(actor + 0x0c);
    uint32_t output = run.automatic(-4);
    run.put(output, 0);
    uint32_t dictionary = run.get(container + (action ? 0x28 : 0x2c)) + 0x10;
    run.call(0x4f6286, dictionary, {name, output});
    uint32_t value = run.get(output);
    if (!value)
        return 0;
    if (action) {
        run.put(actor + 0x184, value);
    } else {
        {
            Frame frame(run, 0x10);
            select(run, actor + 0x188, value);
        }
        if (immediate) {
            Frame frame(run, 0x10);
            update(run, actor + 0x188, run.get(0x5430c4));
        }
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x420970:
        seek(run, receiver, arguments[0]);
        return 0;
    case 0x420a10:
        setSequence(run, receiver, arguments[0], arguments[1]);
        return 0;
    case 0x4c79e0:
        return named(run, receiver, arguments[0], arguments[1], false);
    case 0x4c7a40:
        return named(run, receiver, arguments[0], 0, true);
    case 0x4c8210:
        clear(run, receiver);
        return 0;
    case 0x4c8220:
        select(run, receiver, arguments[0]);
        return 0;
    case 0x4c8260:
        reset(run, receiver, arguments[0]);
        return 0;
    case 0x4c82a0:
        return update(run, receiver, arguments[0]);
    case 0x4c87f0:
        return record(run, receiver, arguments[0]);
    case 0x4c8810:
        lastImage(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_actor_animation_canonical_entry, owned, body)
