#ifndef CLAW_RUNTIME_H
#define CLAW_RUNTIME_H
/* The one interface every canonical recovered module is built on.

   A module implements original functions over the original's own 32-bit
   address space. It never holds host pointers across calls. All memory access
   and every call to a function the module does not own go through ClawHost,
   so the same module runs unchanged under the comparison harness and inside
   the app. Addresses are called tokens. */
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Entry value of the stack pointer for the outermost owned call. A stack
   local whose address escapes lives at this value plus its offset from the
   entry stack pointer, exactly where the original put it. */
#define CLAW_STACK_TOP 0x02008000u
#define CLAW_STACK_BASE 0x01ff0000u
#define CLAW_STACK_END 0x02010000u
/* A transport sentinel, not an original caller's instruction address. */
#define CLAW_STACK_RETURN_SENTINEL 0x0200f000u

enum {
    CLAW_FAULT_NONE = 0,
    CLAW_FAULT_MEMORY = 1,        /* a token did not resolve to memory the module may touch */
    CLAW_FAULT_HALT = 2,          /* the host stopped the call at a service that cannot run */
    CLAW_FAULT_BUDGET = 3,        /* the operation budget ran out */
    CLAW_FAULT_UNIMPLEMENTED = 4, /* a generated stub that nobody has filled in yet */
    CLAW_FAULT_ABI = 5,           /* wrong argument count or an entry the module does not own */
    CLAW_FAULT_HOST = 6           /* the host itself failed while serving a call */
};

/* Explicit synchronous compiler register/frame transport. No exception outcome
   is encoded here: all CLAW_FAULT_* values remain native safety failures. */
enum {
    CLAW_CONTEXT_VERSION = 1,
    CLAW_CONTEXT_EAX = 1u << 0, CLAW_CONTEXT_EBX = 1u << 1,
    CLAW_CONTEXT_ECX = 1u << 2, CLAW_CONTEXT_EDX = 1u << 3,
    CLAW_CONTEXT_ESI = 1u << 4, CLAW_CONTEXT_EDI = 1u << 5,
    CLAW_CONTEXT_EBP = 1u << 6, CLAW_CONTEXT_ESP = 1u << 7,
    CLAW_CONTEXT_EIP = 1u << 8, CLAW_CONTEXT_EFLAGS = 1u << 9,
    CLAW_CONTEXT_FS_HEAD = 1u << 10,
    CLAW_CONTEXT_ALL = (1u << 11) - 1,
    CLAW_CONTEXT_REQUIRED = CLAW_CONTEXT_EAX | CLAW_CONTEXT_EBP | CLAW_CONTEXT_ESP |
                            CLAW_CONTEXT_EIP | CLAW_CONTEXT_FS_HEAD
};

typedef struct ClawCompilerContext {
    uint32_t size, version, inputMask, outputMask;
    uint32_t eax, ebx, ecx, edx, esi, edi, ebp, esp, eip, eflags, fsHead;
    uint32_t continuation; /* genuine caller PC, never the transport STOP token */
    uint32_t reserved0, reserved1;
} ClawCompilerContext;

/* Ordinary ABI capability. CPU values are data, never memory permissions.
   Pointers are borrowed for one synchronous host-owned source graph. */
enum {
    CLAW_SOURCE_INPUT_REQUIRED = CLAW_CONTEXT_EBP | CLAW_CONTEXT_ESP | CLAW_CONTEXT_EIP | CLAW_CONTEXT_FS_HEAD,
    CLAW_SOURCE_OUTPUT_REQUIRED = CLAW_CONTEXT_EAX | CLAW_CONTEXT_ESP | CLAW_CONTEXT_EIP | CLAW_CONTEXT_FS_HEAD,
    CLAW_SOURCE_PRESERVABLE = CLAW_CONTEXT_EBX | CLAW_CONTEXT_ESI | CLAW_CONTEXT_EDI | CLAW_CONTEXT_EBP | CLAW_CONTEXT_FS_HEAD
};
typedef struct ClawSourceContext {
    uint32_t size, version, inputMask, outputMask;
    uint32_t eax, ebx, ecx, edx, esi, edi, ebp, esp, eip, eflags, fsHead;
    uint32_t preserveMask, reserved0, reserved1;
} ClawSourceContext;
typedef struct ClawSourceContract {
    uint32_t inputMask, outputMask, preserveMask, returnPopBytes;
} ClawSourceContract;

/* Host-issued synchronous OS callback CPU. This is not source-entry authority:
   its synthetic return belongs to the dispatcher. activation is a one-use
   lifetime identity; descendants borrow both the exact pointer and identity. */
typedef struct ClawCallbackCPU {
    uint32_t size, version, target, entryStackPointer;
    uint64_t activation;
    ClawSourceContext cpu;
} ClawCallbackCPU;

enum { CLAW_SOURCE_TRANSFER_VERSION = 1, CLAW_SOURCE_CALL = 0, CLAW_SOURCE_TAIL_JMP = 1 };
enum { CLAW_SOURCE_DISPOSITION_NONE = 0, CLAW_SOURCE_DISPOSITION_RETURNED = 1 };
struct ClawCall;
/* Borrowed output for one explicitly elected zero-argument source tail.
   Publish RETURNED only after the target's actual RET0 and ownership checks. */
typedef struct ClawSourceDisposition {
    uint32_t size, version, disposition, callerFunction, sourceSite, targetFunction;
    uint32_t entryStackPointer, returnPC;
    const struct ClawCall *request;
} ClawSourceDisposition;

/* Exact x87 boundary, independent of the host long-double representation.
   Slots are logical ST(0)..ST(count-1), contiguous; inactive slots are zero.
   status retains physical TOP. Only masked exceptions are supported.
   Exact calls consume 0..8 values and return 0..1; pop 0/push 0 is a
   balanced call that returns SW and EDX:EAX only. Ordinary stack arguments
   are independent. Result depth is <= 8.
   ENTRY and RESULT serve explicitly declared owned ordinary outer entries.
   ENTRY reads the inherited stack/CW/SW. RESULT publishes the entry stack
   plus one ST(0) for x87_result, or the unchanged live stack with actual SW
   for x87_environment, once, as the entry's last outside call. */
enum { CLAW_X87_VERSION = 1, CLAW_X87_EXACT = 2, CLAW_X87_STEP = 3,
       CLAW_X87_ENTRY = 4, CLAW_X87_RESULT = 5 };
enum {
    CLAW_X87_LN2 = 1, CLAW_X87_I32 = 2, CLAW_X87_F64 = 3,
    CLAW_X87_YL2X = 4, CLAW_X87_DIV_ST1 = 5, CLAW_X87_POP = 6,
    CLAW_X87_CHS = 7, CLAW_X87_SUBR_F64 = 8, CLAW_X87_MUL_F64 = 9,
    CLAW_X87_ROUND_F64 = 10, CLAW_X87_DIV_F64 = 11,
    CLAW_X87_ADD_ST1 = 12, CLAW_X87_ADD_F64 = 13,
    /* DE D9, D9 FA, D9 E1; DC /2, DC /3, DC /4 m64 take low/high words.
       FST/FSTP m64 return the stored binary64 bits as EDX:EAX. */
    CLAW_X87_COMPP = 14, CLAW_X87_SQRT = 15, CLAW_X87_ABS = 16,
    CLAW_X87_COM_F64 = 17, CLAW_X87_COMP_F64 = 18, CLAW_X87_SUB_F64 = 19,
    CLAW_X87_ST_F64 = 20, CLAW_X87_STP_F64 = 21,
    /* D9 FE / D9 FF: replace ST(0), retaining the actual range/status result. */
    CLAW_X87_SIN = 22, CLAW_X87_COS = 23,
    /* Register forms: add i (0..7) to select ST(i); see CLAW_X87_ST(). */
    CLAW_X87_LD_ST = 0x100,     /* D9 C0+i  FLD ST(i) */
    CLAW_X87_XCH_ST = 0x108,    /* D9 C8+i  FXCH ST(i) */
    CLAW_X87_ST_ST = 0x110,     /* DD D0+i  FST ST(i) */
    CLAW_X87_STP_ST = 0x118,    /* DD D8+i  FSTP ST(i) */
    CLAW_X87_COM_ST = 0x120,    /* D8 D0+i  FCOM ST(i) */
    CLAW_X87_COMP_ST = 0x128,   /* D8 D8+i  FCOMP ST(i) */
    CLAW_X87_ADD_TO0 = 0x130,   /* D8 C0+i  FADD ST(0), ST(i) */
    CLAW_X87_MUL_TO0 = 0x138,   /* D8 C8+i  FMUL ST(0), ST(i) */
    CLAW_X87_SUB_TO0 = 0x140,   /* D8 E0+i  FSUB ST(0), ST(i) */
    CLAW_X87_SUBR_TO0 = 0x148,  /* D8 E8+i  FSUBR ST(0), ST(i) */
    CLAW_X87_DIV_TO0 = 0x150,   /* D8 F0+i  FDIV ST(0), ST(i) */
    CLAW_X87_DIVR_TO0 = 0x158,  /* D8 F8+i  FDIVR ST(0), ST(i) */
    CLAW_X87_ADD_TOI = 0x160,   /* DC C0+i  FADD ST(i), ST(0) */
    CLAW_X87_MUL_TOI = 0x168,   /* DC C8+i  FMUL ST(i), ST(0) */
    CLAW_X87_SUBR_TOI = 0x170,  /* DC E0+i  FSUBR ST(i), ST(0) */
    CLAW_X87_SUB_TOI = 0x178,   /* DC E8+i  FSUB ST(i), ST(0) */
    CLAW_X87_DIVR_TOI = 0x180,  /* DC F0+i  FDIVR ST(i), ST(0) */
    CLAW_X87_DIV_TOI = 0x188,   /* DC F8+i  FDIV ST(i), ST(0) */
    CLAW_X87_ADDP = 0x190,      /* DE C0+i  FADDP ST(i), ST(0) */
    CLAW_X87_MULP = 0x198,      /* DE C8+i  FMULP ST(i), ST(0) */
    CLAW_X87_SUBRP = 0x1a0,     /* DE E0+i  FSUBRP ST(i), ST(0) */
    CLAW_X87_SUBP = 0x1a8,      /* DE E8+i  FSUBP ST(i), ST(0) */
    CLAW_X87_DIVRP = 0x1b0,     /* DE F0+i  FDIVRP ST(i), ST(0) */
    CLAW_X87_DIVP = 0x1b8       /* DE F8+i  FDIVP ST(i), ST(0) */
};
#define CLAW_X87_ST(form, i) ((uint32_t)(form) + (uint32_t)(i))
typedef struct ClawX87Value {
    uint64_t significand;
    uint32_t signExponent, reserved;
} ClawX87Value;
typedef struct ClawX87State {
    uint32_t size, version, control, status, count, popCount, pushCount, returned;
    uint32_t eax, edx, reserved0, reserved1;
    ClawX87Value slots[8];
} ClawX87State;

/* Maximum number of 32-bit stack words, including by-value aggregates.
   All native modules and host bindings must be rebuilt when this changes. */
enum { CLAW_CALL_ARGUMENT_CAPACITY = 32 };

typedef struct ClawCall {
    uint32_t function;      /* original address of the callee; for an import, its import-table slot */
    uint32_t receiver;      /* ECX for thiscall and fastcall, otherwise 0 */
    uint32_t receiver2;     /* EDX for fastcall, otherwise 0 */
    uint32_t argumentCount; /* stack arguments only */
    uint32_t arguments[CLAW_CALL_ARGUMENT_CAPACITY];
    uint32_t stackPointer;  /* tracked callee-entry ESP: return word at ESP, arguments at ESP+4; otherwise 0 */
    uint32_t x87ArgumentCount; /* 0: absent; 1: binary64; EXACT/STEP/ENTRY/RESULT: x87State */
    double x87Argument;
    ClawCompilerContext *compilerContext; /* borrowed in/out; NULL selects ordinary ABI */
    ClawSourceContext *sourceContext; /* explicit ordinary entry state; never compiler selection */
    uint32_t sourceReturnPC; /* real caller continuation; zero only without sourceContext */
    /* CALL is zero-initialized legacy transport. Tail fields are explicit,
       versioned, and borrowed only for the synchronous source callback. */
    uint32_t sourceTransferVersion, sourceTransferKind, sourceTransferSite, sourceCallerFunction;
    ClawSourceDisposition *sourceDisposition;
    ClawX87State *x87State; /* borrowed synchronous in/out for declared x87 modes */
    uint32_t x87Operation; /* bounded arithmetic primitive; zero for calls */
    ClawCallbackCPU *callbackCPU;
    uint64_t callbackActivation;
} ClawCall;

typedef struct ClawHost {
    void *user;
    /* Exact byte span for [token, token + count), or NULL. */
    uint8_t *(*bytes)(void *user, uint32_t token, uint32_t count);
    /* Every call to a function the module does not own. Returns EAX. */
    uint32_t (*call)(void *user, const ClawCall *call);
    uint32_t maximumOperations; /* 0 selects the default budget */
    uint32_t fault;             /* CLAW_FAULT_*; once set the module stops */
    uint32_t faultAddress;      /* token or function that caused the fault */
    double floatResult;         /* x87 return value for functions that return one */
    uint32_t entryStackPointer; /* current entry ESP; 0 preserves the outer CLAW_STACK_TOP default */
    /* Optional synchronous call-graph budget. NULL preserves per-Run limits.
       The owner initializes and pins this counter; zero means exhausted. */
    uint64_t *remainingOperations;
    ClawCompilerContext *compilerContext; /* borrowed active entry context, or NULL */
    ClawSourceContext *sourceContext; /* borrowed active ordinary state, or NULL */
    uint32_t sourceReturnPC; /* active ordinary entry continuation */
    struct ClawGuestSession *guestSession; /* opt-in, graph-owned; NULL for legacy entries */
    ClawCallbackCPU *callbackCPU; /* borrowed only while an owned OS callback runs */
} ClawHost;

/* Returns 1 when the function ran to completion and stores EAX in *result.
   Returns 0 when the module does not own `function` or when it faulted;
   host->fault tells which. A fault is a native safety diagnostic, never a
   value the original would have returned. */
typedef uint32_t (*ClawEntry)(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                              uint32_t argumentCount, ClawHost *host, uint32_t *result);

#ifdef __cplusplus
}
#endif
#endif
