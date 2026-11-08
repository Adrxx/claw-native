// Level 1 Claw death, respawn and life services
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

uint32_t copyMessagePlayerName(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t sendPlayerTextMessage(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t selectMessagePlayerAndEnsureBuffer(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t findMessagePlayerByKey(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t sendPlayerMessageRecord(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t recordAndPresentNetworkError(Run &run, uint32_t receiver, const uint32_t *arguments);

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x41ebd0:
        return 0;
    case 0x41ee40:
        return 1;
    case 0x479f10:
        return 4;
    case 0x47a220:
        return 0;
    case 0x4b7aa0:
        return 1;
    case 0x4e0c60:
        return 1;
    case 0x4e0d70:
        return 4;
    case 0x4e10d0:
        return 4;
    default:
        return -1;
    }
}

// Models the entry stack pointer of an owned callee for the length of a direct call.
struct FrameScope {
    Run &run;
    uint32_t saved;
    FrameScope(Run &r, uint32_t entry) : run(r), saved(r.frame) {
        run.frame = entry;
    }
    ~FrameScope() {
        run.frame = saved;
    }
};

// Length of a C string including its terminator (repne scasb).
uint32_t stringSize(Run &run, uint32_t text) {
    uint32_t count = 0;
    for (;;) {
        uint32_t value = run.get8(text + count);
        ++count;
        if (value == 0)
            break;
    }
    return count;
}

// rep movsd then rep movsb.
void copyBytes(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    uint32_t words = count >> 2;
    uint32_t offset = 0;
    for (uint32_t i = 0; i < words; ++i) {
        run.put(destination + offset, run.get(source + offset));
        offset += 4;
    }
    uint32_t rest = count & 3;
    for (uint32_t i = 0; i < rest; ++i) {
        run.put8(destination + offset, run.get8(source + offset));
        offset += 1;
    }
}

void copyString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = stringSize(run, source);
    copyBytes(run, destination, source, count);
}

const uint32_t kDeathText[26] = {
    0x524d00, 0x524ce8, 0x524cdc, 0x524cd4, 0x524cb4, 0x524ca0, 0x524c84, 0x524c6c, 0x524c54,
    0x524c38, 0x524c1c, 0x524c04, 0x524bf0, 0x524be0, 0x524bd0, 0x524bbc, 0x524ba4, 0x524b88,
    0x524b74, 0x524b5c, 0x524b40, 0x524b2c, 0x524b14, 0x524afc, 0x524ae4, 0x524ad4,
};

// 0x41ebd0. Picks a random death phrase and posts "<name> <phrase>" when the state is 4.
uint32_t postRandomDeathMessage(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t game = run.get(0x5371fc);
    DeathApplicationFields application{run, game};
    uint32_t manager = application.messageManager();
    uint32_t state = run.vcall(manager, DeathModeQuerySlot, {});
    if (state != DeathMessageMode)
        return state;
    uint32_t draw = run.call(0x4a3050, 0, {});
    // IDIV is signed: negative remainders take the unsigned default-table branch.
    int32_t remainder = s32(draw) % 0x1a;
    uint32_t index = uint32_t(remainder);
    uint32_t phrase = 0x524ad4;
    if (index <= 0x19)
        phrase = kDeathText[index];
    uint32_t text = run.automatic(-0x200);
    copyString(run, text, phrase);
    uint32_t game2 = run.get(0x5371fc);
    DeathApplicationFields reloadedApplication{run, game2};
    uint32_t owner = reloadedApplication.messageManager();
    PlayerMessageManagerFields messageOwner{run, owner};
    uint32_t item = messageOwner.currentPlayer();
    if (item == 0)
        return stringSize(run, phrase);
    uint32_t name = run.automatic(-0x204);
    uint32_t copied = 0;
    {
        FrameScope scope(run, run.frame - 0x214);
        const uint32_t nameArguments[] = {name};
        copied = copyMessagePlayerName(run, item, nameArguments);
    }
    uint32_t nameText = run.get(copied);
    uint32_t line = run.automatic(-0x100);
    run.call(0x4a3920, 0, {line, 0x524acc, nameText, text});
    run.call(0x4f6584, name, {});
    uint32_t sent = 0;
    {
        FrameScope scope(run, run.frame - 0x220);
        const uint32_t sendArguments[] = {line, 1, 0, 1};
        sent = sendPlayerTextMessage(run, owner, sendArguments);
    }
    return sent;
}

// 0x41ee40. Copies the string held at +0x08 into the caller's object and returns it.
uint32_t copyMessagePlayerName(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t out = arguments[0];
    run.put(run.automatic(-0x4), 0);
    run.call(0x4f6449, out, {receiver + uint32_t(offsetof(MessagePlayerPrefixLayout, nameData))});
    return out;
}

// 0x479f10. Trims and formats a message, copies it into the send record and sends it.
uint32_t sendPlayerTextMessage(Run &run, uint32_t receiver, const uint32_t *arguments) {
    PlayerMessageManagerFields managerFields{run, receiver};
    uint32_t text = arguments[0];
    uint32_t id = arguments[1];
    uint32_t prefixed = arguments[2];
    uint32_t show = arguments[3];
    if (text == 0)
        return 0;
    if (run.get8(text) == 0)
        return 0;
    uint32_t length = stringSize(run, text) - 1;
    if (s32(length) > int32_t(PlayerMessageTextLimitBytes)) {
        run.put8(text + PlayerMessageTextLimitBytes, 0);
        length = PlayerMessageTextLimitBytes;
    }
    if (s32(length) > 0) {
        if (int8_t(run.get8(text + length - 1)) < 0x20) {
            run.put8(text + length - 1, 0);
            length = length - 1;
        }
        if (s32(length) > 0) {
            if (int8_t(run.get8(text + length - 1)) < 0x20)
                run.put8(text + length - 1, 0);
        }
    }
    uint32_t found = 0;
    {
        FrameScope scope(run, run.frame - 0x118);
        found = selectMessagePlayerAndEnsureBuffer(run, receiver, nullptr);
    }
    if (found == 0)
        return 0;
    uint32_t line = run.automatic(-0x100);
    if (prefixed != 0) {
        uint32_t item = managerFields.currentPlayer();
        uint32_t name = run.automatic(-0x104);
        uint32_t copied = 0;
        {
            FrameScope scope(run, run.frame - 0x11c);
            const uint32_t nameArguments[] = {name};
            copied = copyMessagePlayerName(run, item, nameArguments);
        }
        uint32_t nameText = run.get(copied);
        run.call(0x4a3920, 0, {line, 0x52ac0c, nameText, text});
        run.call(0x4f6584, name, {});
    } else {
        copyString(run, line, text);
    }
    if (show != 0) {
        uint32_t parent = managerFields.parent();
        MessageParentFields parentFields{run, parent};
        uint32_t window = parentFields.window();
        run.call(0x422370, window, {line, 0});
    }
    uint32_t record = managerFields.sendRecord();
    PlayerMessageRecordFields recordFields{run, record};
    recordFields.id(id);
    recordFields.kind(PlayerTextMessageKind);
    uint32_t record2 = managerFields.sendRecord();
    uint32_t size = stringSize(run, line) - 1;
    // The wire header is eight bytes; size excludes the copied terminator.
    uint32_t total = size + 9;
    uint32_t destination = record2 + uint32_t(sizeof(PlayerMessageRecordPrefixLayout));
    uint32_t count = stringSize(run, line);
    copyBytes(run, destination, line, count);
    uint32_t list = managerFields.playerList();
    uint32_t current = managerFields.currentPlayer();
    {
        FrameScope scope(run, run.frame - 0x128);
        const uint32_t sendArguments[] = {current, id, record, total};
        sendPlayerMessageRecord(run, list, sendArguments);
    }
    return 1;
}

// 0x47a220. Looks up the current item by key and gives it a 0x400-byte buffer if it has none.
uint32_t selectMessagePlayerAndEnsureBuffer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    PlayerMessageManagerFields managerFields{run, receiver};
    uint32_t key = managerFields.currentPlayerKey();
    uint32_t list = managerFields.playerList();
    uint32_t item = 0;
    {
        FrameScope scope(run, run.frame - 0xc);
        const uint32_t lookupArguments[] = {key};
        item = findMessagePlayerByKey(run, list, lookupArguments);
    }
    managerFields.currentPlayer(item);
    if (item != 0) {
        MessagePlayerFields selectedPlayerFields{run, item};
        uint32_t buffer = selectedPlayerFields.buffer();
        if (buffer == 0) {
            uint32_t created = run.call(0x4f63ec, 0, {MessagePlayerBufferBytes});
            uint32_t current = managerFields.currentPlayer();
            // Allocation can publish a different current player; reload before storing.
            MessagePlayerFields currentPlayerFields{run, current};
            currentPlayerFields.buffer(created);
            currentPlayerFields.bufferBytes(MessagePlayerBufferBytes);
        }
    }
    uint32_t current = managerFields.currentPlayer();
    return current != 0 ? 1 : 0;
}

// 0x4b7aa0. Does nothing.
uint32_t returnWithoutSideEffects(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x4e0c60. Walks the list at +0x58 and returns the entry whose +0x04 equals the key.
uint32_t findMessagePlayerByKey(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    MessagePlayerListFields listFields{run, receiver};
    uint32_t node = listFields.head();
    while (node != 0) {
        MessagePlayerNodeFields nodeFields{run, node};
        uint32_t next = nodeFields.next();
        uint32_t entry = nodeFields.player();
        MessagePlayerFields playerFields{run, entry};
        if (playerFields.key() == key)
            return entry;
        node = next;
    }
    return 0;
}

// 0x4e0d70. Sends through the object's method at +0x68 and reports a failure code.
uint32_t sendPlayerMessageRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t entry = arguments[0];
    uint32_t id = arguments[1];
    uint32_t record = arguments[2];
    uint32_t size = arguments[3];
    uint32_t key = 0;
    if (entry != 0) {
        MessagePlayerFields playerFields{run, entry};
        key = playerFields.key();
    }
    MessagePlayerListFields listFields{run, receiver};
    uint32_t object = listFields.transport();
    uint32_t method = run.get(run.get(object) + PlayerMessageSendSlot);
    uint32_t result = run.call(method, 0, {object, key, 0, id, record, size});
    if (result != 0) {
        FrameScope scope(run, run.frame - 0x18);
        const uint32_t errorArguments[] = {0x533500, 0x49a, result, 0};
        recordAndPresentNetworkError(run, 0, errorArguments);
    }
    return result;
}

struct ErrorText {
    uint32_t code;
    uint32_t message;
    uint32_t detail;
};

const ErrorText kErrors[] = {
    {0x80004005, 0x533fb0, 0x533f88},
    {0x80004001, 0x533ff8, 0x533fc0},
    {0x80070057, 0x533f1c, 0x533ed8},
    {0x8007000e, 0x533f74, 0x533f30},
    {0x8877000a, 0x533e84, 0x533e48},
    {0x88770005, 0x533ebc, 0x533e98},
    {0x8877001e, 0x533dc4, 0x533d7c},
    {0x88770014, 0x533e34, 0x533ddc},
    {0x88770032, 0x533d24, 0x533d04},
    {0x88770028, 0x533d68, 0x533d3c},
    {0x88770046, 0x533cb4, 0x533c90},
    {0x8877003c, 0x533cec, 0x533ccc},
    {0x8877005a, 0x533c1c, 0x533be8},
    {0x88770050, 0x533c74, 0x533c2c},
    {0x88770082, 0x533b90, 0x533b64},
    {0x88770078, 0x533bd4, 0x533ba4},
    {0x887700a0, 0x533af4, 0x533aa4},
    {0x88770096, 0x533b50, 0x533b04},
    {0x887700be, 0x533a54, 0x533a2c},
    {0x887700aa, 0x533a90, 0x533a68},
    {0x887700d2, 0x5339a4, 0x533978},
    {0x887700c8, 0x533a14, 0x5339b4},
    {0x887700e6, 0x533920, 0x5338cc},
    {0x887700dc, 0x533964, 0x533934},
    {0x887700fa, 0x53386c, 0x533834},
    {0x887700f0, 0x5338bc, 0x533880},
    {0x88770118, 0x5337ec, 0x533790},
    {0x8877010e, 0x533828, 0x533800},
    {0x88770136, 0x533734, 0x533704},
    {0x8877012c, 0x53377c, 0x533748},
    {0x887703f2, 0x5336ac, 0x53368c},
    {0x887703e8, 0x5336ec, 0x5336c4},
    {0x88770406, 0x533634, 0x533610},
    {0x887703fc, 0x533678, 0x53364c},
    {0x8877041a, 0x533564, 0x53353c},
    {0x8877042e, 0x5335f4, 0x533580},
    {0x00000000, 0x533608, 0x532324},
};

// 0x4e10d0. Records an error code with its text and shows it in a message box.
uint32_t recordAndPresentNetworkError(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    NetworkErrorFields errorFields{run, 0x544d20};
    uint32_t code = arguments[2];
    uint32_t handle = arguments[3];
    errorFields.lowCode(code & 0xffff);
    uint32_t beep = errorFields.beep();
    errorFields.code(code);
    if (beep != 0)
        run.icall(0x546ca4, {0x30});
    copyString(run, 0x544d78, 0x532434);
    run.call(0x4a3920, 0, {0x544d38, 0x532420});
    uint32_t text = run.automatic(-0x200);
    copyString(run, text, 0x534938);
    for (const ErrorText &error : kErrors) {
        if (error.code == code) {
            copyString(run, 0x544d38, error.message);
            copyString(run, 0x544d78, error.detail);
            break;
        }
    }
    uint32_t first = errorFields.formatDetails();
    bool proceed = true;
    if (first == 0) {
        uint32_t second = errorFields.showDialog();
        if (second == 0) {
            uint32_t third = errorFields.unknown_0xc();
            if (third == 0)
                proceed = false;
        }
    }
    if (!proceed)
        return 0;
    uint32_t file = arguments[0];
    uint32_t number = arguments[1];
    if (first != 0) {
        if (file != 0 && s32(number) > 0) {
            uint32_t value = errorFields.lowCode();
            run.call(0x4a3920, 0, {text, 0x5322e4, file, number, 0x544d38, value, 0x544d78});
        } else {
            uint32_t value = errorFields.lowCode();
            run.call(0x4a3920, 0, {text, 0x5322d4, 0x544d38, value, 0x544d78});
        }
    }
    uint32_t again = errorFields.showDialog();
    if (again == 0)
        return 0;
    if (file != 0 && s32(number) > 0) {
        uint32_t value = errorFields.lowCode();
        run.call(0x4a3920, 0, {text, 0x5322b8, file, number, 0x544d38, value, 0x544d78});
    } else {
        uint32_t value = errorFields.lowCode();
        run.call(0x4a3920, 0, {text, 0x5322ac, 0x544d38, value, 0x544d78});
    }
    return run.icall(0x546d48, {handle, text, 0x533530, 0x30});
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41ebd0:
        return postRandomDeathMessage(run, receiver, arguments);
    case 0x41ee40:
        return copyMessagePlayerName(run, receiver, arguments);
    case 0x479f10:
        return sendPlayerTextMessage(run, receiver, arguments);
    case 0x47a220:
        return selectMessagePlayerAndEnsureBuffer(run, receiver, arguments);
    case 0x4b7aa0:
        return returnWithoutSideEffects(run, receiver, arguments);
    case 0x4e0c60:
        return findMessagePlayerByKey(run, receiver, arguments);
    case 0x4e0d70:
        return sendPlayerMessageRecord(run, receiver, arguments);
    case 0x4e10d0:
        return recordAndPresentNetworkError(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_claw_death_01_entry, owned, body)
