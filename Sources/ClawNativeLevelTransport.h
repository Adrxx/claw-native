#ifndef CLAW_NATIVE_LEVEL_TRANSPORT_H
#define CLAW_NATIVE_LEVEL_TRANSPORT_H
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Contextual call transports of the native Level 1 join
   (Tests/NativeLevelOne/native_join.py LevelOneNativeJoin), as pure checks
   the app host applies around its own invoke. No guest code; every request
   outside these shapes is refused by the caller. Checked by
   scripts/check-level-one-transports.py. */

/* Registry facts of one admitted owner (ClawNativeMenuInterface.cpp). */
typedef struct ClawLevelOwner {
    uint32_t owned, sourceCapability, inputMask, outputMask, preserveMask, returnsX87;
} ClawLevelOwner;
uint32_t claw_level_owner(uint32_t function, ClawLevelOwner *owner);
/* Native platform providers on the same guest heap. Invalid storage is refused;
   string work is bounded to eight MiB. These do not execute recovered code. */
uint32_t claw_level_native_type_info(ClawHost *host, uint32_t object, uint32_t *result);
uint32_t claw_level_native_strncat(ClawHost *host, uint32_t destination, uint32_t source,
                                 uint32_t count, uint32_t *result);
uint32_t claw_level_x87_environment(uint32_t function);
uint32_t claw_level_x87_environment_invoke(ClawEntry entry, uint32_t function, uint32_t receiver,
    const uint32_t *arguments, uint32_t count, ClawHost *host, ClawX87State *state, uint32_t *result);

enum { CLAW_LEVEL_STOP = 0x70000080u, CLAW_LEVEL_DEFAULT_GAP = 0x400u };
/* Recovered game code: the game ranges plus the reviewed game-owned bodies
   inside the CRT/MFC range (spatial grid, 0x4f4490..0x4f4aa0). */
uint32_t claw_level_game_range(uint32_t function);
uint32_t claw_level_is_game(uint32_t function);

/* Root frame for a source-contract entry reached without a caller context:
   the join's NativeJoin.invoke CPU (ESP, EIP, ECX, EFLAGS 2, FS head). */
void claw_level_root_source(ClawSourceContext *cpu, const ClawLevelOwner *owner, uint32_t stack,
                            uint32_t function, uint32_t receiver, uint32_t fsHead);
/* Caller edge vs callee contract: 0 identical, 1 narrowed into *adapted,
   2 incompatible (callee needs an input the caller did not supply, writes an
   output the caller does not accept, or drops a register the caller keeps). */
enum { CLAW_LEVEL_SOURCE_SAME = 0, CLAW_LEVEL_SOURCE_NARROWED = 1, CLAW_LEVEL_SOURCE_INCOMPATIBLE = 2 };
uint32_t claw_level_narrow_source(const ClawSourceContext *caller, const ClawLevelOwner *owner,
                                  ClawSourceContext *adapted);
/* A dynamically checked alternative when static narrowing is insufficient.
   Missing inputs are still refused. The host must check the returned CPU with
   claw_level_source_return_ok before publishing any register to the caller. */
uint32_t claw_level_checked_source_adapt(const ClawSourceContext *caller, const ClawLevelOwner *owner,
                                         ClawSourceContext *adapted);
/* Check every unselected or preserved caller register against the real callee
   return; never manufacture preserved values by overwriting a changed output. */
uint32_t claw_level_source_return_ok(const ClawSourceContext *before, const ClawSourceContext *after);
/* Copies the adapted CPU (EAX..FS head) back to the caller's context. */
void claw_level_restore_source(ClawSourceContext *caller, const ClawSourceContext *adapted);

/* Zero-argument source tail JMP. request_ok checks the versioned request and
   that the frame holds the caller continuation (returnWord = word at ESP);
   receipt checks the target returned to that continuation (EIP = return PC,
   ESP = entry + 4) and fills the Disposition. */
uint32_t claw_level_tail_request_ok(const ClawCall *call, uint32_t returnWord);
uint32_t claw_level_tail_receipt(const ClawCall *call, uint32_t entryStack);

/* Physical stand-ins the join serves from a source context (their tracer
   fixtures change only EAX, EIP and ESP). Returns 1 with the callee's
   argument pop bytes for an elected target, else 0. */
uint32_t claw_level_physical_source_pop(uint32_t function, uint32_t argumentCount, uint32_t *pop);
/* Validates the source frame and publishes the physical return. */
uint32_t claw_level_physical_source_frame_ok(const ClawCall *call, uint32_t returnWord);
void claw_level_physical_source_return(ClawSourceContext *cpu, uint32_t returnPC, uint32_t pop, uint32_t eax);

/* Plain source CALL into an admitted ordinary game owner (no source contract, no x87
   result), as 0x4141f0 calls a logic state through the global table: the caller's
   edge may keep only callee-saved registers (EBX, ESI, EDI, EBP, FS head), which an
   ordinary owner preserves by its ABI; the frame must hold the caller continuation.
   Returns 1 with the callee's argument pop bytes (stdcall and thiscall pop their
   stack words, cdecl none; convention and count from claw_level_owner_abi); the host then runs the owner without the context and
   publishes EAX, EIP and ESP with claw_level_physical_source_return. */
uint32_t claw_level_ordinary_source_ok(const ClawCall *call, uint32_t returnWord, const ClawLevelOwner *owner,
                                       uint32_t convention, uint32_t argumentCount, uint32_t *pop);
/* Registry calling convention (CLAW_CANONICAL_*) and stack argument count of an owner. */
uint32_t claw_level_owner_abi(uint32_t function, uint32_t *convention, uint32_t *argumentCount);
/* Ordinary calls whose x87 result the caller discards (X87_DISCARD). */
uint32_t claw_level_x87_discard_elected(uint32_t caller, uint32_t function);
/* Empty-stack owned-result request used for an elected discard call. */
void claw_level_x87_empty_request(ClawX87State *state);
/* Exact x87 game call: 0 refused, 1 balanced (pop 0, push 0, ordinary owner),
   2 owned x87 result (pop 0, push 1, x87-result owner, count < 8). */
enum { CLAW_LEVEL_X87_REFUSED = 0, CLAW_LEVEL_X87_BALANCED = 1, CLAW_LEVEL_X87_OWNED = 2 };
uint32_t claw_level_x87_exact_kind(const ClawX87State *state, uint32_t returnsX87);
/* Owned x87 result through ENTRY/RESULT (claw_canonical_x87_invoke contract). */
uint32_t claw_level_x87_owned_invoke(ClawEntry entry, uint32_t function, uint32_t receiver,
                                     const uint32_t *arguments, uint32_t argumentCount,
                                     ClawHost *host, ClawX87State *state, uint32_t *result);

/* Vtable tail-only owner: reached only from the innermost elected thunk
   (MOV r,[ECX]; JMP [r+slot]) with the receiver's own vtable word, no
   operands and no context. slot 0 means the innermost entry is no thunk. */
uint32_t claw_level_tail_only_ok(const ClawCall *call, uint32_t slot, uint32_t vtableWord);
/* Direct ordinary virtual call of a tail-only elected owner. The host proves
   membership in the receiver's vtable, then uses its normal plain/source CALL
   transport. Source frame and ABI validation still apply there. */
uint32_t claw_level_tail_direct_ok(const ClawCall *call, uint32_t caller, uint32_t receiverHasTarget);
/* An authenticated original immediate CALL can name an inherited base body
   absent from the derived receiver's vtable. The asset builder supplies the
   caller/target relation; ordinary source/ABI checks still apply afterward. */
uint32_t claw_level_original_direct_ok(const ClawCall *call, uint32_t caller,
                                       uint32_t originalEdge, uint32_t argumentCount);
/* Enemy lift overrides call the shared base with the same receiver. */
uint32_t claw_level_enemy_lift_base_ok(const ClawCall *call, uint32_t caller, uint32_t overrideWord);
/* Projectile state +8 overrides call the shared base dispatcher on a table miss. */
uint32_t claw_level_state_base_call_ok(const ClawCall *call, uint32_t caller, uint32_t overrideWord);
/* Le Rauxe's override calls the shared base implementation directly. */
/* Red Tail Pirate +0x58 override directly calls its original base response. */
uint32_t claw_level_pirate_base_call_ok(const ClawCall *call, uint32_t caller,
                                      uint32_t receiverVtable, uint32_t overrideWord);
uint32_t claw_level_boss_base_call_ok(const ClawCall *call, uint32_t caller,
                                      uint32_t receiverVtable, uint32_t overrideWord);
/* Child frame gap below the caller's original prologue extent. */
uint32_t claw_level_child_gap(uint32_t extent);
#ifdef __cplusplus
}
#endif
#endif
