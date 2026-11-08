#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_LOGIC_STATE_MAX_TABLES 96
#define CLAW_LOGIC_STATE_MAX_LITERALS 256
// Raw original trie/indexed-object views. Arrays own nine words; trie owns
// eleven. Trailing view words may overlap the next original global object and
// are synchronized accordingly. Other unwritten words remain unchanged.
// kind 1 = name Patricia trie, 2 = ID CString array, 3 = class function array.
typedef struct {
    uint32_t token, kind, words[12];
} ClawLogicStateTable;
typedef struct {
    int32_t state;
    uint32_t literalToken;
} ClawLogicStateLiteral;
typedef struct {
    uint32_t nextId, tableCount;
    ClawLogicStateTable tables[CLAW_LOGIC_STATE_MAX_TABLES];
    uint32_t literalCount;
    ClawLogicStateLiteral literals[CLAW_LOGIC_STATE_MAX_LITERALS];
    // Original 544b14..544b4f: error location/handler and lazy message globals.
    uint32_t errorGlobals[15];
} ClawLogicStateRegistry;
typedef struct {
    uint8_t *heap;
    uint32_t heapBase, heapCapacity, heapUsed, emptyStringToken;
    uint32_t metadataReceiverToken, metadataFunctionToken, errorLocation, fault;
} ClawLogicStateContext;
typedef struct {
    uint32_t function, receiver, argumentCount, arguments[4];
    const char *name;
} ClawLogicStateCall;
// Allocation/reallocation/free, atexit and metadata bodies are services. Their
// tokens must address supplied heap storage. With no callback, bounded native
// arena allocation is used; its physical allocation policy is a host extension.
typedef uint64_t (*ClawLogicStateDependency)(ClawLogicStateRegistry *, ClawLogicStateContext *,
                                             const ClawLogicStateCall *, void *);
typedef struct {
    int32_t state;
    uint32_t function, nameToken, literalToken;
    const char *name;
} ClawLogicStateView;
// Initial image counter 2000 and shared empty CString identity 52e1c4. Does not
// clear supplied raw table words, arena, services or live identities.
void claw_logic_state_context_defaults(ClawLogicStateRegistry *, ClawLogicStateContext *);
// Actual state-related CRT constructor order, then whole 401000 state binding
// order. Separation permits inspection/mutation between the two original stages.
uint32_t claw_logic_state_initialize(ClawLogicStateRegistry *, ClawLogicStateContext *, ClawLogicStateDependency,
                                     void *);
uint32_t claw_logic_state_bootstrap(ClawLogicStateRegistry *, ClawLogicStateContext *, ClawLogicStateDependency,
                                    void *);
uint32_t claw_logic_state_find_id(ClawLogicStateRegistry *, ClawLogicStateContext *, const char *,
                                  ClawLogicStateDependency, void *);
uint32_t claw_logic_state_register(ClawLogicStateRegistry *, ClawLogicStateContext *, uint32_t classTableToken,
                                   const char *name, uint32_t originalLiteralToken, uint32_t function,
                                   ClawLogicStateDependency, void *);
// Name lookup can grow the original ID-name array (including ID1000), creating
// actual empty CString cells. Function table lookup follows the same growth ABI.
// nameToken is the allocated CString data identity; literalToken is separately
// retained host metadata for first registration. Do not substitute one for the other.
uint32_t claw_logic_state_resolve(ClawLogicStateRegistry *, ClawLogicStateContext *, uint32_t classTableToken,
                                  int32_t state, ClawLogicStateView *, ClawLogicStateDependency, void *);
uint32_t claw_logic_state_table_count(const ClawLogicStateRegistry *);
const ClawLogicStateTable *claw_logic_state_table_at(const ClawLogicStateRegistry *, uint32_t);
#ifdef __cplusplus
}
#endif
