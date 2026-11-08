#include "ClawNativeLevelTransport.h"
#include "ClawCanonicalDispatch.h"
#include <cstring>

// Native host transports, in the order and with the conditions of
// Tests/NativeLevelOne/native_join.py LevelOneNativeJoin.service/invoke.

uint32_t claw_level_game_range(uint32_t f) {
    return (f >= 0x401000u && f < 0x4a1300u) || (f >= 0x4b3400u && f < 0x4f0000u);
}
uint32_t claw_level_is_game(uint32_t f) {
    return claw_level_game_range(f) || (f >= 0x4f4490u && f < 0x4f4a8cu) || (f >= 0x4f4a90u && f < 0x4f4aa0u);
}

void claw_level_root_source(ClawSourceContext *cpu, const ClawLevelOwner *owner, uint32_t stack,
                            uint32_t function, uint32_t receiver, uint32_t fsHead) {
    std::memset(cpu, 0, sizeof(*cpu));
    cpu->size = sizeof(*cpu); cpu->version = 1;
    cpu->inputMask = owner->inputMask; cpu->outputMask = owner->outputMask; cpu->preserveMask = owner->preserveMask;
    cpu->esp = stack; cpu->eip = function; cpu->ecx = receiver; cpu->eflags = 2; cpu->fsHead = fsHead;
}

uint32_t claw_level_narrow_source(const ClawSourceContext *caller, const ClawLevelOwner *owner,
                                  ClawSourceContext *adapted) {
    if (caller->inputMask == owner->inputMask && caller->outputMask == owner->outputMask &&
        caller->preserveMask == owner->preserveMask) return CLAW_LEVEL_SOURCE_SAME;
    if ((owner->inputMask & ~caller->inputMask) || (owner->outputMask & ~caller->outputMask) ||
        (caller->preserveMask & ~owner->preserveMask)) return CLAW_LEVEL_SOURCE_INCOMPATIBLE;
    *adapted = *caller;
    adapted->inputMask = owner->inputMask; adapted->outputMask = owner->outputMask;
    adapted->preserveMask = owner->preserveMask;
    return CLAW_LEVEL_SOURCE_NARROWED;
}
uint32_t claw_level_checked_source_adapt(const ClawSourceContext *caller, const ClawLevelOwner *owner,
                                         ClawSourceContext *adapted) {
    if (owner->inputMask & ~caller->inputMask) return 0;
    *adapted = *caller;
    adapted->inputMask = owner->inputMask; adapted->outputMask = owner->outputMask;
    adapted->preserveMask = owner->preserveMask;
    return 1;
}
uint32_t claw_level_source_return_ok(const ClawSourceContext *before, const ClawSourceContext *after) {
    // A wider callee output contract or a weaker preserve guarantee is safe
    // only when this particular return satisfies the caller's full contract.
    uint32_t a[11], b[11];
    std::memcpy(a, &before->eax, sizeof(a));
    std::memcpy(b, &after->eax, sizeof(b));
    for (uint32_t i = 0; i < 11; ++i)
        if ((!(before->outputMask & (1u << i)) || (before->preserveMask & (1u << i))) && a[i] != b[i]) return 0;
    return 1;
}
void claw_level_restore_source(ClawSourceContext *caller, const ClawSourceContext *adapted) {
    std::memcpy(&caller->eax, &adapted->eax, 11 * sizeof(uint32_t));
}

uint32_t claw_level_tail_request_ok(const ClawCall *q, uint32_t returnWord) {
    if (q->sourceTransferVersion != CLAW_SOURCE_TRANSFER_VERSION || q->sourceTransferKind != CLAW_SOURCE_TAIL_JMP ||
        !q->sourceDisposition || !q->sourceContext || q->argumentCount || q->compilerContext ||
        q->callbackCPU || !q->sourceReturnPC || q->x87ArgumentCount || q->x87State) return 0;
    const ClawSourceContext *cpu = q->sourceContext;
    return cpu->esp == q->stackPointer && returnWord == q->sourceReturnPC;
}
uint32_t claw_level_tail_receipt(const ClawCall *q, uint32_t entryStack) {
    const ClawSourceContext *cpu = q->sourceContext;
    if (cpu->eip != q->sourceReturnPC || cpu->esp != entryStack + 4) return 0;
    ClawSourceDisposition *receipt = q->sourceDisposition;
    receipt->size = sizeof(*receipt); receipt->version = 1; receipt->disposition = CLAW_SOURCE_DISPOSITION_RETURNED;
    receipt->callerFunction = q->sourceCallerFunction; receipt->sourceSite = q->sourceTransferSite;
    receipt->targetFunction = q->function; receipt->entryStackPointer = entryStack;
    receipt->returnPC = q->sourceReturnPC; receipt->request = q;
    return 1;
}

uint32_t claw_level_physical_source_pop(uint32_t function, uint32_t count, uint32_t *pop) {
    // Tracer fixtures (Tests/NativeMenuBase/trace.py): CRT atexit and malloc
    // are cdecl; CPtrArray and CString default constructors take no stack
    // argument; the CString text constructor pops its one argument;
    // timeGetTime takes none. Native CRT rand/srand are cdecl too: the
    // TownGuard2 idle source CALL at 0x4979c5 reaches rand on Level 6.
    static const struct {uint32_t function, count, pop;} elected[] = {
        {0x4a35f0u, 1, 0}, {0x4a48e0u, 1, 0}, {0x4f54eau, 0, 0},
        {0x4f6439u, 0, 0}, {0x4f65f2u, 1, 4}, {0x546df0u, 0, 0},
        {0x4a3050u, 0, 0}, {0x4a3040u, 1, 0},
        // Native operator new, RTTI type_info lookup and strncat are cdecl.
        {0x4f63ecu, 1, 0}, {0x4a36f0u, 1, 0}, {0x4f2060u, 3, 0},
        // DialogBoxParamA and PostMessageA retain their IAT identities and
        // stdcall stack cleanup on the player-cache source entrances.
        {0x546d2cu, 5, 20}, {0x546d50u, 4, 16}};
    for (const auto &e : elected)
        if (e.function == function && e.count == count) {*pop = e.pop; return 1;}
    return 0;
}

uint32_t claw_level_native_type_info(ClawHost *host, uint32_t object, uint32_t *result) {
    if (!host || !host->bytes || !object || !result) return 0;
    auto word = [host](uint32_t at, uint32_t &value) {
        const auto *p = host->bytes(host->user, at, 4);
        if (!p) return false;
        std::memcpy(&value, p, 4);
        return true;
    };
    uint32_t table = 0, locator = 0, descriptor = 0;
    if (!word(object, table) || table < 4 || !word(table - 4, locator) || !locator || locator > UINT32_MAX - 12 ||
        !word(locator + 12, descriptor) || !descriptor || !host->bytes(host->user, descriptor, 8)) return 0;
    *result = descriptor;
    return 1;
}

uint32_t claw_level_native_strncat(ClawHost *host, uint32_t destination, uint32_t source,
                                 uint32_t count, uint32_t *result) {
    if (!host || !host->bytes || !result) return 0;
    // Like the original, count zero returns without dereferencing either word.
    if (!count) { *result = destination; return 1; }
    constexpr uint32_t limit = 0x800000;
    uint32_t length = 0;
    for (; length < limit; ++length) {
        if (destination > UINT32_MAX - length) return 0;
        const auto *p = host->bytes(host->user, destination + length, 1);
        if (!p) return 0;
        if (!*p) break;
    }
    if (length == limit) return 0;
    uint32_t copied = 0;
    for (; copied < count && copied < limit - length; ++copied) {
        if (source > UINT32_MAX - copied || destination > UINT32_MAX - length - copied) return 0;
        const auto *from = host->bytes(host->user, source + copied, 1);
        if (!from) return 0;
        auto *to = host->bytes(host->user, destination + length + copied, 1);
        if (!to) return 0;
        *to = *from;
        if (!*from) { *result = destination; return 1; }
    }
    if (copied == limit - length || destination > UINT32_MAX - length - copied) return 0;
    auto *end = host->bytes(host->user, destination + length + copied, 1);
    if (!end) return 0;
    *end = 0;
    *result = destination;
    return 1;
}
uint32_t claw_level_physical_source_frame_ok(const ClawCall *q, uint32_t returnWord) {
    const ClawSourceContext *cpu = q->sourceContext;
    return cpu && !q->compilerContext && !q->callbackCPU && !q->x87ArgumentCount && !q->x87State &&
        q->sourceReturnPC && cpu->esp == q->stackPointer && returnWord == q->sourceReturnPC;
}
void claw_level_physical_source_return(ClawSourceContext *cpu, uint32_t returnPC, uint32_t pop, uint32_t eax) {
    cpu->eax = eax; cpu->eip = returnPC; cpu->esp += 4 + pop;
}

uint32_t claw_level_ordinary_source_ok(const ClawCall *q, uint32_t returnWord, const ClawLevelOwner *owner,
                                       uint32_t convention, uint32_t argumentCount, uint32_t *pop) {
    if (!claw_level_physical_source_frame_ok(q, returnWord) || !claw_level_game_range(q->function) || !owner->owned ||
        owner->sourceCapability || owner->returnsX87 ||
        (convention != CLAW_CANONICAL_CDECL && convention != CLAW_CANONICAL_STDCALL && convention != CLAW_CANONICAL_THISCALL) ||
        q->argumentCount != argumentCount || q->receiver2 || q->sourceTransferVersion ||
        (q->sourceContext->preserveMask & ~(uint32_t)CLAW_SOURCE_PRESERVABLE) ||
        (convention == CLAW_CANONICAL_THISCALL ? q->sourceContext->ecx != q->receiver : q->receiver != 0)) return 0;
    *pop = convention == CLAW_CANONICAL_CDECL ? 0 : 4 * q->argumentCount;
    return 1;
}
uint32_t claw_level_x87_discard_elected(uint32_t caller, uint32_t function) {
    // At each call site every earlier value was stored with FSTP, so the x87
    // stack is empty, and the pushed ST(0) is later discarded.
    return function == 0x420dd0u &&
        (caller == 0x415df0u || caller == 0x418120u || caller == 0x41b630u || caller == 0x41e710u ||
         caller == 0x4181c0u); // Rope jump-off: empty stack at the call; return immediately discarded.
}
void claw_level_x87_empty_request(ClawX87State *s) {
    std::memset(s, 0, sizeof(*s));
    s->size = sizeof(*s); s->version = CLAW_X87_VERSION; s->control = 0x023f; s->pushCount = 1;
}
uint32_t claw_level_x87_exact_kind(const ClawX87State *s, uint32_t returnsX87) {
    if (!s || s->returned || s->eax || s->edx || s->count > 8) return CLAW_LEVEL_X87_REFUSED;
    if (!s->popCount && s->pushCount == 1 && returnsX87 && s->count < 8) return CLAW_LEVEL_X87_OWNED;
    if (!s->popCount && !s->pushCount && !returnsX87) return CLAW_LEVEL_X87_BALANCED;
    return CLAW_LEVEL_X87_REFUSED;
}
uint32_t claw_level_x87_owned_invoke(ClawEntry entry, uint32_t function, uint32_t receiver,
                                     const uint32_t *arguments, uint32_t count,
                                     ClawHost *host, ClawX87State *state, uint32_t *result) {
    if (!entry || !host || !state || count > CLAW_CALL_ARGUMENT_CAPACITY) return 0;
    ClawCall call{};
    call.function = function; call.receiver = receiver; call.argumentCount = count;
    for (uint32_t i = 0; i < count; ++i) call.arguments[i] = arguments[i];
    call.x87ArgumentCount = CLAW_X87_EXACT; call.x87State = state;
    if (!claw_canonical_x87_request_ok(&call)) return 0;
    ClawCanonicalEntry owner{};
    owner.address = function; owner.returnKind = CLAW_CANONICAL_RETURN_X87; owner.entry = entry;
    return claw_canonical_x87_invoke(&call, &owner, host, result);
}

uint32_t claw_level_tail_only_ok(const ClawCall *q, uint32_t slot, uint32_t vtableWord) {
    return q && q->receiver && !q->receiver2 && slot && !q->argumentCount &&
        !q->sourceContext && !q->x87ArgumentCount && !q->x87State &&
        !q->compilerContext && !q->sourceTransferVersion && !q->callbackCPU && vtableWord == q->function;
}
uint32_t claw_level_tail_direct_ok(const ClawCall *q, uint32_t caller, uint32_t receiverHasTarget) {
    return q && claw_level_game_range(caller) && q->receiver && receiverHasTarget == 1 &&
        !q->compilerContext && !q->callbackCPU && !q->x87ArgumentCount && !q->x87State &&
        !q->sourceTransferVersion && !q->sourceTransferKind && !q->sourceTransferSite &&
        !q->sourceCallerFunction && !q->sourceDisposition;
}
uint32_t claw_level_original_direct_ok(const ClawCall *q, uint32_t caller,
                                       uint32_t originalEdge, uint32_t argumentCount) {
    return q && originalEdge == 1 && claw_level_game_range(caller) &&
        q->receiver && !q->receiver2 && q->argumentCount == argumentCount &&
        !q->compilerContext && !q->callbackCPU && !q->callbackActivation &&
        !q->x87ArgumentCount && !q->x87Argument && !q->x87State && !q->x87Operation &&
        (q->sourceContext || !q->sourceReturnPC) &&
        !q->sourceTransferVersion && !q->sourceTransferKind && !q->sourceTransferSite &&
        !q->sourceCallerFunction && !q->sourceDisposition;
}
uint32_t claw_level_enemy_lift_base_ok(const ClawCall *q, uint32_t caller, uint32_t overrideWord) {
    // Original officer calls at 0x463358/0x463394 and Red Tail Pirate at
    // 0x484238. Their +0x88 overrides replace the base lift wrapper's slot.
    return q && (caller == 0x463310u || caller == 0x484210u) && overrideWord == caller &&
        q->function == 0x44df10u && q->receiver && !q->receiver2 && !q->argumentCount &&
        !q->sourceContext && !q->compilerContext && !q->callbackCPU && !q->callbackActivation &&
        !q->x87ArgumentCount && !q->x87Argument && !q->x87State && !q->x87Operation && !q->sourceReturnPC &&
        !q->sourceTransferVersion && !q->sourceTransferKind && !q->sourceTransferSite &&
        !q->sourceCallerFunction && !q->sourceDisposition;
}
uint32_t claw_level_state_base_call_ok(const ClawCall *q, uint32_t caller, uint32_t overrideWord) {
    // All original direct CALLs to the shared state fallback: crab, dynamite,
    // Gabriel bomb and lava projectile dispatchers. Their +8 slot overrides
    // the base handler, so receiver membership in the base target is false.
    const bool dispatcher = caller == 0x431df0u || caller == 0x43ad20u ||
        caller == 0x445af0u || caller == 0x456c20u;
    return q && dispatcher && q->function == 0x408580u && overrideWord == caller &&
        q->receiver && !q->receiver2 && q->argumentCount == 1 &&
        !q->sourceContext && !q->compilerContext && !q->callbackCPU && !q->callbackActivation &&
        !q->x87ArgumentCount && !q->x87Argument && !q->x87State && !q->x87Operation && !q->sourceReturnPC &&
        !q->sourceTransferVersion && !q->sourceTransferKind && !q->sourceTransferSite &&
        !q->sourceCallerFunction && !q->sourceDisposition;
}
uint32_t claw_level_x87_environment_invoke(ClawEntry entry, uint32_t function, uint32_t receiver,
    const uint32_t *arguments, uint32_t count, ClawHost *host, ClawX87State *state, uint32_t *result) {
    if (!entry || !host || !state || count > CLAW_CALL_ARGUMENT_CAPACITY) return 0;
    ClawCall call{};
    call.function = function; call.receiver = receiver; call.argumentCount = count;
    for (uint32_t i = 0; i < count; ++i) call.arguments[i] = arguments[i];
    call.x87ArgumentCount = CLAW_X87_EXACT; call.x87State = state;
    if (!claw_canonical_x87_environment_request_ok(&call)) return 0;
    ClawCanonicalEntry owner{};
    owner.address = function; owner.entry = entry; owner.x87Environment = 1;
    return claw_canonical_x87_invoke(&call, &owner, host, result);
}
uint32_t claw_level_child_gap(uint32_t extent) {
    const uint32_t gap = (extent + 0x4fu) & ~0xfu;
    return gap > CLAW_LEVEL_DEFAULT_GAP ? gap : CLAW_LEVEL_DEFAULT_GAP;
}
uint32_t claw_level_boss_base_call_ok(const ClawCall *q, uint32_t caller,
                                      uint32_t receiverVtable, uint32_t overrideWord) {
    // Raux, Katherine, Wolvington, Gabriel and Marrow override +0x5c and directly call the original base
    // death handler with the same receiver and one argument (ret 4).
    const bool reviewedOverride = (caller == 0x40e660u && receiverVtable == 0x50f1acu) ||
        (caller == 0x40e660u && receiverVtable == 0x50e2a4u) ||
        (caller == 0x40e660u && receiverVtable == 0x50de1cu) ||
        (caller == 0x40e660u && receiverVtable == 0x50ff2cu) ||
        (caller == 0x40e660u && receiverVtable == 0x50e7acu);
    return q && reviewedOverride && q->function == 0x44e0c0u && overrideWord == caller &&
        q->receiver && !q->receiver2 && q->argumentCount == 1 &&
        !q->sourceContext && !q->compilerContext && !q->callbackCPU && !q->callbackActivation &&
        !q->x87ArgumentCount && q->x87Argument == 0 && !q->x87State && !q->x87Operation && !q->sourceReturnPC &&
        !q->sourceTransferVersion && !q->sourceTransferKind &&
        !q->sourceTransferSite && !q->sourceCallerFunction && !q->sourceDisposition;
}

uint32_t claw_level_pirate_base_call_ok(const ClawCall *q, uint32_t caller,
                                      uint32_t receiverVtable, uint32_t overrideWord) {
    // Original base calls: attack at 0x48429e (+0x58 override), death at
    // 0x483e2e (+0x5c override, same receiver and one stack argument).
    const bool reviewedCall = q &&
        ((caller == 0x484260u && q->function == 0x43efe0u && !q->argumentCount) ||
         (caller == 0x483e10u && q->function == 0x44e0c0u && q->argumentCount == 1));
    return q && reviewedCall && receiverVtable == 0x50f394u && overrideWord == caller &&
        q->receiver && !q->receiver2 &&
        !q->sourceContext && !q->compilerContext && !q->callbackCPU && !q->callbackActivation &&
        !q->x87ArgumentCount && q->x87Argument == 0 && !q->x87State && !q->x87Operation && !q->sourceReturnPC &&
        !q->sourceTransferVersion && !q->sourceTransferKind && !q->sourceTransferSite &&
        !q->sourceCallerFunction && !q->sourceDisposition;
}
