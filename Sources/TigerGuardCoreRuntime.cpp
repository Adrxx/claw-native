#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch (function) {
    case 0x493fd0:
    case 0x494460:
    case 0x494a80:
    case 0x494b10:
        return 1;
    case 0x494aa0:
    case 0x494cc0:
    case 0x494d40:
    case 0x495000:
    case 0x495130:
        return 0;
    default:
        return -1;
    }
}
// Dispatch table bounds, storage, fallback and stride.
uint32_t dispatchCell(Run &run, uint32_t key) {
    run.put(0x53ca60, 0);
    if (s32(key) < run.gets(0x53ca48) || s32(key) > run.gets(0x53ca4c)) {
        if (!run.call(0x4db6e0, 0x53ca40, {key, 0})) {
            uint32_t description = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x53ca44), {0x53ca40, description, 0xc});
            return run.get(0x53ca54);
        }
    }
    return (key - run.get(0x53ca48)) * run.get(0x53ca58) + run.get(0x53ca50);
}
// 0x493fd0.
uint32_t function_493fd0(Run &run, uint32_t object, uint32_t key) {
    uint32_t cell = dispatchCell(run, key);
    if (run.get(cell)) {
        cell = dispatchCell(run, key);
        run.call(run.get(cell), object);
    } else {
        run.call(0x44c840, object, {key});
    }
    return 0;
}
// 0x494aa0. Embedded map +0x2f4 and strings +0x1a8/+0x1a4.
uint32_t function_494aa0(Run &run, uint32_t object) {
    run.put(object, 0x50b16c);
    run.call(0x4dbcd0, object + 0x2f4);
    run.call(0x4f6584, object + 0x1a8);
    run.call(0x4f6584, object + 0x1a4);
    run.put(object, 0x50b014);
    return 0;
}
// 0x494a80.
uint32_t function_494a80(Run &run, uint32_t object, uint32_t flags) {
    function_494aa0(run, object);
    if (flags & 1) {
        run.call(0x4f6428, 0, {object});
    }
    return object;
}
// Sprite +0x12c; facing +0x18c; horizontal bounds +0x138/+0x140.
void faceTarget(Run &run, uint32_t object) {
    if (run.get(object + 0x18c) == 2) {
        uint32_t sprite = run.get(object + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(object + 0x138);
            run.put(object + 0x138, 0u - run.get(object + 0x140));
            run.put(object + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            run.call(0x4060b0, run.get(object + 0x12c));
        }
    } else {
        run.call(0x406310, object + 0x128);
    }
}
// 0x494cc0. Actor +0x0c; attack timing +0x104; idle animation +0x350.
uint32_t function_494cc0(Run &run, uint32_t object) {
    run.put(run.get(object + 0x0c) + 0x104, 10);
    uint32_t actor = run.get(object + 0x0c);
    uint32_t timing = run.call_x87(0x4a30e0, 0, double(run.gets(actor + 0x104)) * double(run.getf(0x5262b0)));
    run.put(actor + 0x104, timing);
    run.put(object + 0x4dc, 0);
    run.call(0x44d9f0, object);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x350)});
    sprite = run.get(object + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) & 0xfffffffe);
    return 0;
}
// 0x495130. Lunge flag +0x4dc, velocities +0x50/+0x54, target X +0x4c0.
uint32_t function_495130(Run &run, uint32_t object) {
    faceTarget(run, object);
    run.put(object + 0x4dc, 1);
    run.put(object + 0x50, 0);
    run.put(object + 0x54, 0);
    run.put(object + 0x4cc, run.get(object + 0x18c) == 3 ? uint32_t(-300) : 300);
    run.put(object + 0x4c0, run.get(run.get(0x537e88) + 0x4c));
    uint32_t sound = run.get(object + 0x490);
    if (sound && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52ca88});
    run.put(run.get(object + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x45c)});
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    run.icall(0x546d5c, {object + 0x220, uint32_t(-0x4a), uint32_t(-0x27), uint32_t(-1), 0xf});
    run.put(run.get(object + 0x0c) + 0x104, 0x14);
    uint32_t actor = run.get(object + 0x0c);
    uint32_t timing = run.call_x87(0x4a30e0, 0, double(run.gets(actor + 0x104)) * double(run.getf(0x5262b0)));
    run.put(actor + 0x104, timing);
    return 0;
}
// 0x495000. Attack cooldown +0x498/+0x49c.
uint32_t function_495000(Run &run, uint32_t object) {
    if (run.get(0x537210) - run.get(object + 0x498) < run.get(object + 0x49c)) {
        run.vcall(object, 0x44);
        return 0;
    }
    uint32_t random = run.call(0x4a3050, 0);
    run.put(object + 0x49c, uint32_t(s32(random) % 0x2ef) + 0x4e2);
    run.put(object + 0x498, run.get(0x537210));
    run.put(object + 0x50, 0);
    run.put(object + 0x54, 0);
    uint32_t sprite = run.get(object + 0x12c);
    bool facingLeft = run.get(object + 0x18c) == 2;
    if (bool(run.get8(sprite + 0x40) & 2) != facingLeft) {
        uint32_t left = run.get(object + 0x138);
        run.put(object + 0x138, 0u - run.get(object + 0x140));
        run.put(object + 0x140, 0u - left);
        run.put(sprite + 0x40, facingLeft ? run.get(sprite + 0x40) | 2 : run.get(sprite + 0x40) & 0xfffffffd);
        sprite = run.get(object + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    random = run.call(0x4a3050, 0);
    int32_t choice = s32(random) % 0x65;
    if (choice < 0x28) {
        function_495130(run, object);
    } else if (choice < 0x50) {
        random = run.call(0x4a3050, 0);
        run.call(0x4953b0, object, {uint32_t(s32(random) % 3) + 2});
    } else {
        run.call(0x4955c0, object, {1});
    }
    return 0;
}

// 0x494b10. State string comparisons, then conditional defensive response.
uint32_t function_494b10(Run &run, uint32_t object, uint32_t argument) {
    run.call(0x44d000, object, {argument});
    uint32_t string = run.call(0x406020, 0x537698, {run.get(run.get(object + 0x10) + 0x1c)});
    if (!run.call(0x4a3810, 0, {run.get(string), 0x52ca98})) {
        return 1;
    }
    string = run.call(0x406020, 0x537698, {run.get(run.get(object + 0x10) + 0x1c)});
    if (!run.call(0x4a3810, 0, {run.get(string), 0x52ca78})) {
        return 1;
    }
    for (uint32_t name : {0x526a38u, 0x52ca88u}) {
        string = run.call(0x441030, 0x537698, {run.get(run.get(object + 0x10) + 0x1c)});
        uint32_t item = run.get(0x5376b4);
        uint32_t count = run.get(0x5376b8);
        while (count) {
            if (item) {
                run.call(0x4f6439, item);
            }
            item += 4;
            --count;
        }
        if (!run.call(0x4a3810, 0, {run.get(string), name})) {
            return 1;
        }
    }
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    uint32_t result = run.get(player + 0x04);
    if (!result) {
        return result;
    }
    result = run.get(object + 0x18c);
    if (!((result == 3 && run.get(player)) || (result == 2 && !run.get(player)))) {
        return result;
    }
    result = run.get(object + 0x184);
    if (result != 3 && result != 4) {
        return result;
    }
    result = run.get(0x537210) - run.get(object + 0x4a8);
    if (result < run.get(object + 0x4ac)) {
        return result;
    }
    uint32_t chance = run.get(object + 0x4c8);
    uint32_t random = run.call(0x4a3050, 0);
    result = uint32_t(s32(random) / 100);
    if (s32(random) % 100 < s32(chance)) {
        if (run.gets(object + 0x20) >= 2) {
            run.put(object + 0x14, 0x44e620);
        }
        run.put(object + 0x4ac, 500);
        run.put(object + 0x4a8, run.get(0x537210));
    }
    return result;
}
// 0x494460. Constructor: animation handles +0x308..+0x458 and sound handles +0x460..+0x494.
uint32_t function_494460(Run &run, uint32_t object, uint32_t argument) {
    run.call(0x44c000, object, {argument});
    run.put(object + 0x498, 0);
    run.put(object + 0x49c, 0);
    run.put(object + 0x4a0, 0);
    run.put(object + 0x4a4, 0);
    run.put(object + 0x4a8, 0);
    run.put(object + 0x4ac, 0);
    run.put(object + 0x4b0, 0);
    run.put(object + 0x4b4, 0);
    run.put(object + 0x4b8, 0);
    run.put(object + 0x4bc, 0);
    run.put(object, 0x50f9b4);
    run.call(0x4c7970, run.get(object + 0x12c), {0x52cdb4});
    uint32_t name = run.get(run.get(object + 0x0c) + 0x108) == 1 ? 0x52cda0 : 0x52cdb4;
    run.call(0x4c7970, run.get(object + 0x12c), {name});
    uint32_t value;
    value = run.call(0x4062e0, object + 0x128, {0x52cd8c});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x344, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd74});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x308, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd74});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x34c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd74});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x30c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd60});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x338, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd4c});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x334, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd38});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x350, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd24});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x33c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd0c});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x32c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cd0c});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x374, value);
    value = run.call(0x4062e0, object + 0x128, {0x52ccf8});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x378, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cce4});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x37c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52ccd0});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x310, value);
    value = run.call(0x4062e0, object + 0x128, {0x52ccbc});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x45c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cca8});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x380, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cca8});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x36c, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cc90});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x450, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cc78});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x454, value);
    value = run.call(0x4062e0, object + 0x128, {0x52cc64});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    run.put(object + 0x458, value);
    uint32_t local = run.automatic(0x04);
    run.put(local, 0);
    run.call(0x4f6286, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28) + 0x10, {0x52cc48, local});
    run.put(object + 0x3a4, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28) + 0x10, {0x52cc2c, local});
    run.put(object + 0x468, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28) + 0x10, {0x52cc10, local});
    run.put(object + 0x46c, run.get(local));
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cbf4});
    run.put(object + 0x490, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cbd8});
    run.put(object + 0x470, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cbbc});
    run.put(object + 0x474, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cba0});
    run.put(object + 0x478, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cb84});
    run.put(object + 0x47c, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cb68});
    run.put(object + 0x480, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cb4c});
    run.put(object + 0x484, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cb30});
    run.put(object + 0x488, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cb14});
    run.put(object + 0x48c, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cafc});
    run.put(object + 0x494, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cae4});
    run.put(object + 0x460, value);
    value = run.call(0x4061b0, run.get(run.get(run.get(object + 0x12c) + 0x0c) + 0x28), {0x52cacc});
    run.put(object + 0x464, value);
    run.call(0x4208b0, run.get(object + 0x12c), {uint32_t(-0x14), uint32_t(-0x32), 0x14, 0x32});
    run.call(0x406290, run.get(object + 0x12c));
    run.call(0x4296f0, object + 0x260, {uint32_t(-0x3a), uint32_t(-0x1b), 0x31, 0xf});
    run.put(object + 0x404, 0xb4);
    run.put(object + 0x400, 0xb4);
    value = run.call_x87(0x4a30e0, 0, run.getd(object + 0x68));
    run.put(object + 0x4c0, value);
    run.put(object + 0x4d0, 0);
    run.put(object + 0x4d4, 0);
    run.put(object + 0x4d8, 0);
    run.put(object + 0x4c8, 0x28);
    run.put(object + 0x4cc, 0);
    run.put(object + 0x4dc, 0);
    run.put(object + 0x2e4, 0x32);
    value = run.call_x87(0x4a30e0, 0, double(run.getf(0x5262b8)) * double(run.getf(0x50f9a8)));
    if (value <= 0x63) {
        value = 0x63;
    }
    run.put(object + 0x2e4, value);
    run.put(run.get(object + 0x0c) + 0x10c, 0xf);
    uint32_t actor = run.get(object + 0x0c);
    value = run.call_x87(0x4a30e0, 0, double(run.gets(actor + 0x10c)) * double(run.getf(0x5262b4)));
    run.put(actor + 0x10c, value);
    run.put(run.get(object + 0x0c) + 0x104, 10);
    actor = run.get(object + 0x0c);
    value = run.call_x87(0x4a30e0, 0, double(run.gets(actor + 0x104)) * double(run.getf(0x5262b0)));
    run.put(actor + 0x104, value);
    run.call(0x40abf0, object + 0x128);
    function_494cc0(run, object);
    return object;
}
// Visibility from navigation +0x190 and position +0x194.
bool targetVisible(Run &run, uint32_t object) {
    if (run.get(0x534eac) == 0x26b7) {
        return false;
    }
    uint32_t targetX = run.get(run.get(0x537e88) + 0x4c);
    uint32_t position = run.get(object + 0x194);
    uint32_t y = run.get(position + 0x50);
    uint32_t x = run.get(position + 0x4c);
    uint32_t navigation = run.get(run.get(run.get(object + 0x190) + 0x0c) + 0x24);
    if (!run.call(0x4cda10, navigation, {x, y, targetX, 0x20})) {
        return false;
    }
    position = run.get(object + 0x194);
    y = run.get(position + 0x50);
    uint32_t targetY = run.get(run.get(0x537e88) + 0x50);
    if (s32(targetY) >= s32(y + 0x32) || s32(targetY) <= s32(y - 0x32)) {
        return false;
    }
    return run.get(position + 0x38) != 0xffffffff;
}
// 0x494d40. Home state; alert +0x4d0, initial detection +0x4d4.
uint32_t function_494d40(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (!run.get(object + 0x4d0)) {
        if (!run.get(object + 0x4d4) && targetVisible(run, object)) {
            uint32_t random = run.call(0x4a3050, 0);
            if (s32(random) % 0x65 < 0x32) {
                random = run.call(0x4a3050, 0);
                uint32_t sound = run.get(object + 0x480 + uint32_t(s32(random) % 3) * 4);
                run.call(0x48ce40, 0, {run.get(object + 0x0c), sound, 0});
            }
            run.put(object + 0x4d4, 1);
        }
    }
    if (run.get(object + 0x4d0) && targetVisible(run, object)) {
        run.call(0x48ce40, 0, {run.get(object + 0x0c), run.get(object + 0x48c), 0});
        run.put(object + 0x4d0, 0);
        uint32_t random = run.call(0x4a3050, 0);
        if (s32(random) % 0x65 > 0x31) {
            random = run.call(0x4a3050, 0);
            run.call(0x4953b0, object, {uint32_t(s32(random) % 3) + 2});
        } else {
            function_495130(run, object);
        }
        return 0;
    }
    faceTarget(run, object);
    switch (run.get(object + 0x184)) {
    case 0:
    case 1:
        if (s32(run.call(0x4a3050, 0)) % 0x65 < 0x50) {
            run.call(0x44ebb0, object);
            return 0;
        }
        break;
    case 2:
        if (s32(run.call(0x4a3050, 0)) % 0x65 > 0x45) {
            run.call(0x44ebb0, object);
            return 0;
        }
        break;
    case 3:
    case 4:
        if (s32(run.call(0x4a3050, 0)) % 0x65 < 10) {
            run.call(0x4957f0, object);
            return 0;
        }
        break;
    case 5:
    case 6:
        run.call(0x44edd0, object);
        return 0;
    default:
        return 0;
    }
    run.vcall(object, 0x58);
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x493fd0:
        return function_493fd0(run, receiver, arguments[0]);
    case 0x494460:
        return function_494460(run, receiver, arguments[0]);
    case 0x494a80:
        return function_494a80(run, receiver, arguments[0]);
    case 0x494aa0:
        return function_494aa0(run, receiver);
    case 0x494b10:
        return function_494b10(run, receiver, arguments[0]);
    case 0x494cc0:
        return function_494cc0(run, receiver);
    case 0x494d40:
        return function_494d40(run, receiver);
    case 0x495000:
        return function_495000(run, receiver);
    case 0x495130:
        return function_495130(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_tiger_guard_core_entry, owned, body)
