#ifndef CLAW_RUNTIME_HPP
#define CLAW_RUNTIME_HPP
// C++ helpers for canonical modules. Include this from the module's .cpp only.
#include "ClawRuntime.h"
#ifdef CLAW_ENABLE_GUEST_TRANSFER
#include "ClawGuestTransfer.h"
#endif
#include <cstring>
#include <initializer_list>
#include <atomic>

namespace claw {

class Run;
class SourceEntryActivation;
class SourceTailReturned {
    friend class Run;
    const Run *owner;
    uint64_t activation;
    SourceTailReturned(const Run *run, uint64_t token) : owner(run), activation(token) {}
};

struct Failure {};
struct GuestControl {}; // Private control flow, caught before leaving a C export.
struct GuestCallScope {
    ClawHost &host;
    const ClawCall &call;
    bool leased = false;
    GuestCallScope(ClawHost &h, const ClawCall &c) : host(h), call(c) {
#ifdef CLAW_ENABLE_GUEST_TRANSFER
        if (host.guestSession) leased = claw_guest_lease_enter(&host, &call) != 0;
#endif
    }
    ~GuestCallScope() {
#ifdef CLAW_ENABLE_GUEST_TRANSFER
        if (leased) claw_guest_lease_leave(&host, &call);
#endif
    }
};

inline int32_t s32(uint32_t value) {
    int32_t result;
    std::memcpy(&result, &value, 4);
    return result;
}

// One outermost call into a module. Every read, write and outward call is
// bounds-checked by the host and counted against the operation budget.
class Run {
  public:
    explicit Run(ClawHost &host) : host(host), frame(host.entryStackPointer ? host.entryStackPointer : CLAW_STACK_TOP) {}

    [[noreturn]] void fail(uint32_t code, uint32_t address = 0) const {
        if (!host.fault) {
            host.fault = code;
            host.faultAddress = address;
        }
        throw Failure{};
    }

    void check_guest() const {
        if (host.fault) throw Failure{};
        if (!host.guestSession) return;
#ifdef CLAW_ENABLE_GUEST_TRANSFER
        const auto status = claw_guest_status(&host);
        if (host.fault || status == 2) throw Failure{};
        if (status == 1) throw GuestControl{};
#else
        fail(CLAW_FAULT_ABI);
#endif
    }

    void tick() {
        if (host.fault)
            throw Failure{};
        if (host.remainingOperations) {
            if (!*host.remainingOperations)
                fail(CLAW_FAULT_BUDGET);
            --*host.remainingOperations;
        } else {
            uint32_t limit = host.maximumOperations ? host.maximumOperations : 200000000u;
            if (operations >= limit)
                fail(CLAW_FAULT_BUDGET);
        }
        ++operations;
    }

    uint8_t *span(uint32_t token, uint32_t count) {
        tick();
        uint8_t *memory = host.bytes ? host.bytes(host.user, token, count) : nullptr;
        check_guest();
        if (!memory)
            fail(CLAW_FAULT_MEMORY, token);
        return memory;
    }

    template <typename T> T load(uint32_t token) {
        T value;
        std::memcpy(&value, span(token, sizeof(T)), sizeof(T));
        return value;
    }
    template <typename T> void store(uint32_t token, T value) { std::memcpy(span(token, sizeof(T)), &value, sizeof(T)); }

    uint32_t get(uint32_t token) { return load<uint32_t>(token); }
    int32_t gets(uint32_t token) { return load<int32_t>(token); }
    uint16_t get16(uint32_t token) { return load<uint16_t>(token); }
    uint8_t get8(uint32_t token) { return load<uint8_t>(token); }
    float getf(uint32_t token) { return load<float>(token); }
    double getd(uint32_t token) { return load<double>(token); }
    void put(uint32_t token, uint32_t value) { store<uint32_t>(token, value); }
    void put16(uint32_t token, uint16_t value) { store<uint16_t>(token, value); }
    void put8(uint32_t token, uint8_t value) { store<uint8_t>(token, value); }
    void putf(uint32_t token, float value) { store<float>(token, value); }
    void putd(uint32_t token, double value) { store<double>(token, value); }

    // A call to a function this module does not own. `receiver` is ECX for a
    // thiscall callee and must be 0 for stdcall and cdecl callees.
    uint32_t call(uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
        return dispatch(function, receiver, 0, arguments);
    }
    uint32_t fastcall(uint32_t function, uint32_t ecx, uint32_t edx, std::initializer_list<uint32_t> arguments = {}) {
        return dispatch(function, ecx, edx, arguments);
    }
    // Pass one binary64-representable operand in ST(0) to an original callee.
    // The host executes that callee, including its rounding/conversion logic.
    uint32_t call_x87(uint32_t function, uint32_t receiver, double st0,
                      std::initializer_list<uint32_t> arguments = {}) {
        return dispatch(function, receiver, 0, arguments, 1, st0);
    }
    void validate_x87(const ClawX87State &state, uint32_t function, uint32_t pushLimit = 1) const {
        if (state.size != sizeof(state) || state.version != CLAW_X87_VERSION ||
            state.reserved0 || state.reserved1 || state.control > 0xffff || state.status > 0xffff ||
            (state.control & 0x3f) != 0x3f || (state.control & ~0x1f7f) ||
            (state.control & 0x300) == 0x100 || state.count > 8 ||
            state.popCount > 8 || state.pushCount > pushLimit)
            fail(CLAW_FAULT_ABI, function);
        for (uint32_t i = 0; i < 8; ++i) {
            const auto &v = state.slots[i];
            if (v.reserved || v.signExponent > 0xffff ||
                (i >= state.count && (v.significand || v.signExponent))) fail(CLAW_FAULT_ABI, function);
        }
    }
    // Full extended stack, callee pops/result, CW/SW and EDX:EAX. The host must
    // explicitly publish a checked return; an unaware host cannot succeed.
    uint32_t call_x87_exact(uint32_t function, uint32_t receiver, ClawX87State &state,
                            std::initializer_list<uint32_t> arguments = {}) {
        if (!function) fail(CLAW_FAULT_ABI, function);
        return x87_transfer(function, receiver, state, arguments);
    }
    // Owned arithmetic stays an explicit sequence of x87 primitives. This
    // comparison capability never selects a guest address or executes a body.
    // A shipping host must elect a precision-compatible implementation first.
    // Returns EDX:EAX: the stored binary64 bits for ST_F64/STP_F64, else 0.
    // Compare forms leave the instruction's actual SW in state.status.
    uint64_t x87_step(uint32_t operation, ClawX87State &state,
                      std::initializer_list<uint32_t> operands = {}) {
        uint32_t pop = 0, push = 1, argc = 0, minimum = 0;
        switch (operation) {
        case CLAW_X87_LN2: break;
        case CLAW_X87_I32: argc = 1; break;
        case CLAW_X87_F64: argc = 2; break;
        case CLAW_X87_YL2X: pop = minimum = 2; break;
        case CLAW_X87_DIV_ST1:
        case CLAW_X87_ADD_ST1: pop = 1; minimum = 2; break;
        case CLAW_X87_POP: pop = minimum = 1; push = 0; break;
        case CLAW_X87_CHS:
        case CLAW_X87_ROUND_F64:
        case CLAW_X87_SQRT:
        case CLAW_X87_ABS:
        case CLAW_X87_SIN:
        case CLAW_X87_COS:
        case CLAW_X87_ST_F64: pop = minimum = 1; break;
        case CLAW_X87_STP_F64: pop = minimum = 1; push = 0; break;
        case CLAW_X87_COMPP: pop = minimum = 2; push = 0; break;
        case CLAW_X87_COM_F64: minimum = 1; push = 0; argc = 2; break;
        case CLAW_X87_COMP_F64: pop = minimum = 1; push = 0; argc = 2; break;
        case CLAW_X87_SUBR_F64:
        case CLAW_X87_MUL_F64:
        case CLAW_X87_DIV_F64:
        case CLAW_X87_ADD_F64:
        case CLAW_X87_SUB_F64: pop = minimum = 1; argc = 2; break;
        default: {
            const uint32_t form = operation & ~7u, k = (operation & 7u) + 1;
            minimum = k;
            switch (form) {
            case CLAW_X87_LD_ST: break;
            case CLAW_X87_COM_ST: push = 0; break;
            case CLAW_X87_COMP_ST: pop = 1; push = 0; break;
            case CLAW_X87_ADD_TO0: case CLAW_X87_MUL_TO0: case CLAW_X87_SUB_TO0:
            case CLAW_X87_SUBR_TO0: case CLAW_X87_DIV_TO0: case CLAW_X87_DIVR_TO0: pop = 1; break;
            case CLAW_X87_XCH_ST: case CLAW_X87_ST_ST:
            case CLAW_X87_ADD_TOI: case CLAW_X87_MUL_TOI: case CLAW_X87_SUBR_TOI:
            case CLAW_X87_SUB_TOI: case CLAW_X87_DIVR_TOI: case CLAW_X87_DIV_TOI: pop = push = k; break;
            case CLAW_X87_STP_ST:
            case CLAW_X87_ADDP: case CLAW_X87_MULP: case CLAW_X87_SUBRP:
            case CLAW_X87_SUBP: case CLAW_X87_DIVRP: case CLAW_X87_DIVP: pop = k; push = k - 1; break;
            default: fail(CLAW_FAULT_ABI);
            }
        }
        }
        // The comparison host preserves masked PC 24/53/64 and every RC mode.
        if ((state.control & 0x3f) != 0x3f || (state.control & ~0x0f3f) ||
            (state.control & 0x300) == 0x100 || operands.size() != argc || state.count < minimum ||
            state.count - pop + push > 8) fail(CLAW_FAULT_ABI);
        state.popCount = pop; state.pushCount = push;
        state.returned = state.eax = state.edx = 0;
        const bool stores = operation == CLAW_X87_ST_F64 || operation == CLAW_X87_STP_F64;
        const uint32_t low = x87_transfer(0, 0, state, operands, operation, stores);
        return uint64_t(low) | (uint64_t(state.edx) << 32);
    }
    uint32_t x87_transfer(uint32_t function, uint32_t receiver, ClawX87State &state,
                          std::initializer_list<uint32_t> arguments, uint32_t operation = 0,
                          bool stores = false) {
        tick();
        const uint32_t pushLimit = operation ? 8 : 1;
        validate_x87(state, function, pushLimit);
        if (!host.call || host.compilerContext || host.sourceContext || host.guestSession ||
            state.returned || state.eax || state.edx || state.count < state.popCount ||
            state.count - state.popCount + state.pushCount > 8 || arguments.size() > CLAW_CALL_ARGUMENT_CAPACITY)
            fail(CLAW_FAULT_ABI, function);
        const auto before = state;
        ClawCall call{};
        call.function = function; call.receiver = receiver; call.stackPointer = operation ? 0 : stackPointer;
        call.argumentCount = uint32_t(arguments.size());
        uint32_t i = 0;
        for (auto argument : arguments) call.arguments[i++] = argument;
        call.x87ArgumentCount = operation ? CLAW_X87_STEP : CLAW_X87_EXACT;
        call.x87State = &state; call.x87Operation = operation;
        const auto issued = call;
        uint32_t value = host.call(host.user, &call);
        if (host.fault) throw Failure{};
        validate_x87(state, function, pushLimit);
        if (std::memcmp(&call, &issued, sizeof(call)) || state.size != before.size ||
            state.version != before.version || state.control != before.control ||
            state.popCount != before.popCount || state.pushCount != before.pushCount ||
            state.returned != 1 || state.eax != value || (operation && !stores && (value || state.edx)) ||
            state.count != before.count - before.popCount + before.pushCount ||
            ((state.status >> 11) & 7) != (((before.status >> 11) + before.popCount - before.pushCount) & 7))
            fail(CLAW_FAULT_ABI, function);
        for (uint32_t j = before.popCount; j < before.count; ++j)
            if (std::memcmp(&before.slots[j], &state.slots[j - before.popCount + before.pushCount],
                            sizeof(ClawX87Value))) fail(CLAW_FAULT_ABI, function);
        return value;
    }
    // Explicitly declared owned outer x87 result or inherited environment.
    // Read once at entry; publish once as the last outside call. x87_return
    // adds ST(0); x87_finish preserves the entry live stack and publishes SW.
    // The host compares the complete final environment against the original.
    ClawX87State x87_entry(uint32_t function) {
        ClawX87State state{};
        state.size = sizeof(state); state.version = CLAW_X87_VERSION;
        x87_outer(function, state, CLAW_X87_ENTRY);
        if (state.popCount || state.pushCount) fail(CLAW_FAULT_ABI, function);
        state.returned = 0;
        return state;
    }
    void x87_return(uint32_t function, ClawX87State &state) {
        validate_x87(state, function);
        if (!state.count) fail(CLAW_FAULT_ABI, function);
        x87_publish(function, state, 1);
    }
    void x87_finish(uint32_t function, ClawX87State &state) {
        validate_x87(state, function);
        x87_publish(function, state, 0);
    }
    void x87_publish(uint32_t function, ClawX87State &state, uint32_t push) {
        state.popCount = 0; state.pushCount = push;
        state.returned = state.eax = state.edx = 0;
        const auto before = state;
        x87_outer(function, state, CLAW_X87_RESULT);
        auto published = state;
        published.returned = 0;
        if (std::memcmp(&before, &published, sizeof(state))) fail(CLAW_FAULT_ABI, function);
    }
    void x87_outer(uint32_t function, ClawX87State &state, uint32_t kind) {
        tick();
        if (!host.call || !function || host.compilerContext || host.sourceContext || host.guestSession)
            fail(CLAW_FAULT_ABI, function);
        ClawCall call{};
        call.function = function; call.x87ArgumentCount = kind; call.x87State = &state;
        const auto issued = call;
        const uint32_t value = host.call(host.user, &call);
        if (host.fault) throw Failure{};
        validate_x87(state, function);
        if (value || std::memcmp(&call, &issued, sizeof(call)) || state.returned != 1 || state.eax || state.edx)
            fail(CLAW_FAULT_ABI, function);
    }
    // A call through an import-table slot: `call dword ptr [slot]`.
    uint32_t icall(uint32_t importSlot, std::initializer_list<uint32_t> arguments = {}) {
        return dispatch(importSlot, 0, 0, arguments);
    }
    // A virtual call: reads the function from the object's vtable.
    uint32_t vcall(uint32_t object, uint32_t slotOffset, std::initializer_list<uint32_t> arguments = {}) {
        return dispatch(get(get(object) + slotOffset), object, 0, arguments);
    }

    // Token of a stack local of the current owned function, given its offset
    // from that function's entry stack pointer (negative for locals).
    uint32_t automatic(int32_t entryRelative) const {
        int64_t token = int64_t(frame) + entryRelative;
        if (token < CLAW_STACK_BASE || token > CLAW_STACK_END)
            fail(CLAW_FAULT_MEMORY, uint32_t(token));
        return uint32_t(token);
    }

    // Validation is shared by special entries and calls. Code identity is also
    // checked against executable program ranges by the host.
    void validate_context(const ClawCompilerContext &context, uint32_t function, bool returned = false) const {
        const uint32_t flags = 0x000008d7u; // arithmetic flags plus fixed bit 1
        const uint32_t expected = returned ? context.continuation : function;
        if (context.size != sizeof(ClawCompilerContext) || context.version != CLAW_CONTEXT_VERSION ||
            context.reserved0 || context.reserved1 ||
            (context.inputMask & ~CLAW_CONTEXT_ALL) || (context.outputMask & ~CLAW_CONTEXT_ALL) ||
            (context.inputMask & CLAW_CONTEXT_REQUIRED) != CLAW_CONTEXT_REQUIRED ||
            (context.outputMask & CLAW_CONTEXT_REQUIRED) != CLAW_CONTEXT_REQUIRED ||
            !context.continuation || context.continuation == CLAW_STACK_RETURN_SENTINEL ||
            (context.continuation >= CLAW_STACK_BASE && context.continuation < CLAW_STACK_END) ||
            context.eip != expected ||
            context.esp < CLAW_STACK_BASE || uint64_t(context.esp) + (returned ? 0 : 4) > CLAW_STACK_END ||
            (context.esp & 3) ||
            (context.fsHead != 0xffffffffu &&
             ((context.fsHead & 3) || context.fsHead < CLAW_STACK_BASE ||
              uint64_t(context.fsHead) + 12 > CLAW_STACK_END)) ||
            ((context.inputMask | context.outputMask) & CLAW_CONTEXT_EFLAGS &&
             ((context.eflags & ~flags) || !(context.eflags & 2))))
            fail(CLAW_FAULT_ABI, function);
    }

    void validate_context_output(const ClawCompilerContext &context, const ClawCompilerContext &before,
                                 uint32_t function) const {
        if (context.size != before.size || context.version != before.version ||
            context.inputMask != before.inputMask || context.outputMask != before.outputMask ||
            context.continuation != before.continuation)
            fail(CLAW_FAULT_ABI, function);
        const uint32_t values[] = {context.eax, context.ebx, context.ecx, context.edx, context.esi, context.edi,
                                   context.ebp, context.esp, context.eip, context.eflags, context.fsHead};
        const uint32_t previous[] = {before.eax, before.ebx, before.ecx, before.edx, before.esi, before.edi,
                                     before.ebp, before.esp, before.eip, before.eflags, before.fsHead};
        for (uint32_t index = 0; index < 11; ++index)
            if (!(before.outputMask & (1u << index)) && values[index] != previous[index])
                fail(CLAW_FAULT_ABI, function);
        validate_context(context, function, true);
    }

    uint32_t context_call(uint32_t function, ClawCompilerContext &context) {
        tick();
        validate_context(context, function);
        if (!host.call)
            fail(CLAW_FAULT_ABI, function);
        const ClawCompilerContext before = context;
        ClawCall call{};
        call.function = function;
        call.compilerContext = &context;
        host.call(host.user, &call);
        if (host.fault)
            throw Failure{};
        validate_context_output(context, before, function);
        return context.eax;
    }

    void validate_source(const ClawSourceContext &context, uint32_t function, uint32_t returnPC,
                         bool returned = false) const {
        if (context.size != sizeof(ClawSourceContext) || context.version != 1 || context.reserved0 ||
            context.reserved1 || (context.inputMask & ~CLAW_CONTEXT_ALL) ||
            (context.outputMask & ~CLAW_CONTEXT_ALL) ||
            (context.inputMask & CLAW_SOURCE_INPUT_REQUIRED) != CLAW_SOURCE_INPUT_REQUIRED ||
            (context.outputMask & CLAW_SOURCE_OUTPUT_REQUIRED) != CLAW_SOURCE_OUTPUT_REQUIRED ||
            (context.preserveMask & ~CLAW_SOURCE_PRESERVABLE) ||
            (context.preserveMask & context.inputMask) != context.preserveMask ||
            (context.preserveMask & context.outputMask) != context.preserveMask ||
            !returnPC || returnPC == CLAW_STACK_RETURN_SENTINEL ||
            (returnPC >= CLAW_STACK_BASE && returnPC < CLAW_STACK_END) ||
            context.eip != (returned ? returnPC : function) || (context.esp & 3) ||
            context.esp < CLAW_STACK_BASE || uint64_t(context.esp) + (returned ? 0 : 4) > CLAW_STACK_END ||
            (context.fsHead != 0xffffffffu && ((context.fsHead & 3) || context.fsHead < CLAW_STACK_BASE ||
                                              uint64_t(context.fsHead) + 12 > CLAW_STACK_END)) ||
            ((context.inputMask | context.outputMask) & CLAW_CONTEXT_EFLAGS &&
             ((context.eflags & ~0x8d7u) || !(context.eflags & 2))))
            fail(CLAW_FAULT_ABI, function);
    }

    void validate_source_output(const ClawSourceContext &context, const ClawSourceContext &before,
                                uint32_t function, uint32_t returnPC, uint32_t popBytes) const {
        if (context.size != before.size || context.version != before.version ||
            context.inputMask != before.inputMask || context.outputMask != before.outputMask ||
            context.preserveMask != before.preserveMask || context.reserved0 != before.reserved0 ||
            context.reserved1 != before.reserved1 || popBytes > 4 * CLAW_CALL_ARGUMENT_CAPACITY || (popBytes & 3) ||
            uint64_t(before.esp) + 4 + popBytes != context.esp)
            fail(CLAW_FAULT_ABI, function);
        uint32_t values[11], previous[11];
        std::memcpy(values, &context.eax, sizeof(values));
        std::memcpy(previous, &before.eax, sizeof(previous));
        for (uint32_t i = 0; i < 11; ++i)
            if ((!(before.outputMask & (1u << i)) || (before.preserveMask & (1u << i))) &&
                values[i] != previous[i])
                fail(CLAW_FAULT_ABI, function);
        validate_source(context, function, returnPC, true);
    }

    void normalize_source_inputs(ClawSourceContext &context) const {
        uint32_t values[11];
        std::memcpy(values, &context.eax, sizeof(values));
        for (uint32_t i = 0; i < 11; ++i)
            if (!(context.inputMask & (1u << i))) values[i] = i == 9 ? 2u : 0u;
        std::memcpy(&context.eax, values, sizeof(values));
    }
    void retain_source_unselected(ClawSourceContext &context, const ClawSourceContext &before) const {
        uint32_t values[11], previous[11];
        std::memcpy(values, &context.eax, sizeof(values));
        std::memcpy(previous, &before.eax, sizeof(previous));
        for (uint32_t i = 0; i < 11; ++i)
            if (!(before.outputMask & (1u << i))) values[i] = previous[i];
        std::memcpy(&context.eax, values, sizeof(values));
    }

    ClawSourceContext &source() const {
        if (!host.sourceContext || host.compilerContext || host.callbackCPU || !host.sourceReturnPC)
            fail(CLAW_FAULT_ABI);
        return *host.sourceContext;
    }

    ClawSourceContext &callback_cpu() const {
        auto *c = host.callbackCPU;
        if (!c || c->size != sizeof(*c) || c->version != 1 || !c->activation ||
            c->entryStackPointer != frame || host.sourceContext || host.sourceReturnPC ||
            host.compilerContext || host.guestSession || c->cpu.size != sizeof(c->cpu) ||
            c->cpu.version != 1 || c->cpu.inputMask != CLAW_CONTEXT_ALL ||
            c->cpu.outputMask != CLAW_CONTEXT_ALL || c->cpu.preserveMask != CLAW_SOURCE_PRESERVABLE ||
            c->cpu.reserved0 || c->cpu.reserved1)
            fail(CLAW_FAULT_ABI);
        return c->cpu;
    }

    void validate_callback_entry(uint32_t function, uint32_t receiver,
                                 const uint32_t *arguments, uint32_t count) {
        if (!host.callbackCPU) return;
        auto &cpu = callback_cpu();
        if (host.callbackCPU->target != function || receiver || count != 4 ||
            cpu.eip != function || cpu.esp != frame)
            fail(CLAW_FAULT_ABI, function);
        for (uint32_t i = 0; i < count; ++i)
            if (get(frame + 4 + 4 * i) != arguments[i]) fail(CLAW_FAULT_ABI, function);
    }

    uint32_t callback_call(uint32_t function, uint32_t receiver, uint32_t returnPC,
                           std::initializer_list<uint32_t> arguments = {}, uint32_t popBytes = 0) {
        auto &cpu = callback_cpu();
        cpu.eip = function;
        auto child = cpu;
        auto value = source_call(function, receiver, returnPC, child, arguments, 0, popBytes);
        copySourceCPU(cpu, child);
        return value;
    }

    uint32_t source_call(uint32_t function, uint32_t receiver, uint32_t returnPC, ClawSourceContext &context,
                         std::initializer_list<uint32_t> arguments = {}, uint32_t receiver2 = 0,
                         uint32_t returnPopBytes = 0) {
        tick();
        if ((!host.sourceContext && !host.compilerContext && !host.callbackCPU) || !host.call || arguments.size() > CLAW_CALL_ARGUMENT_CAPACITY ||
            (host.sourceContext == &context) || returnPopBytes > 4 * arguments.size() ||
            uint64_t(context.esp) + 4 * (1 + arguments.size()) > CLAW_STACK_END)
            fail(CLAW_FAULT_ABI, function);
        validate_source(context, function, returnPC);
        const auto before = context;
        ClawCall call{};
        call.function = function;
        call.receiver = receiver;
        call.receiver2 = receiver2;
        call.argumentCount = uint32_t(arguments.size());
        uint32_t i = 0;
        for (auto argument : arguments) call.arguments[i++] = argument;
        call.stackPointer = context.esp;
        call.sourceContext = &context;
        call.sourceReturnPC = returnPC;
        if (host.callbackCPU) {
            auto &cpu = callback_cpu();
            if (std::memcmp(&cpu.eax, &context.eax, 11 * sizeof(uint32_t))) fail(CLAW_FAULT_ABI, function);
            call.callbackCPU = host.callbackCPU;
            call.callbackActivation = host.callbackCPU->activation;
        }
        check_guest();
        GuestCallScope lease(host, call);
        check_guest();
        host.call(host.user, &call);
        check_guest();
        validate_source_output(context, before, function, returnPC, returnPopBytes);
        return context.eax;
    }

    // A tail never materializes a frame and never returns to translated code.
    // The parent activation, not a body-supplied caller/return PC, owns it.
    [[noreturn]] void source_tail(uint32_t function, uint32_t receiver, uint32_t sourceSite,
                                 ClawSourceContext &child) {
        tick();
        auto *parent = host.sourceContext;
        if (!sourceCaller || tailIssued || !parent || parent != sourceParent || &child == parent ||
            !host.call || host.compilerContext || host.guestSession || sourceArgumentCount || sourcePopBytes ||
            parent->inputMask != CLAW_CONTEXT_ALL || parent->outputMask != CLAW_CONTEXT_ALL ||
            child.inputMask != CLAW_CONTEXT_ALL || child.outputMask != CLAW_CONTEXT_ALL ||
            parent->eip != sourceSite || child.esp != parent->esp || child.esp != frame ||
            host.entryStackPointer != frame || host.sourceReturnPC != sourceReturn ||
            (receiver && child.ecx != receiver)) fail(CLAW_FAULT_ABI, function);
        if (!sameSourceHeader(*parent, sourceOriginal)) fail(CLAW_FAULT_ABI, function);
        validate_source(child, function, sourceReturn);
        const uint32_t *a = &parent->eax, *b = &child.eax;
        for (uint32_t i = 0; i < 11; ++i)
            if (i != 8 && a[i] != b[i]) fail(CLAW_FAULT_ABI, function);
        const auto childBefore = child;
        const auto parentBefore = *parent;
        const auto hostBefore = host;
        if (get(frame) != sourceReturn || !sameSourceScope(host, hostBefore) ||
            std::memcmp(parent, &parentBefore, sizeof(parentBefore)) ||
            std::memcmp(&child, &childBefore, sizeof(childBefore))) fail(CLAW_FAULT_ABI, function);
        ClawSourceDisposition disposition{};
        ClawCall call{};
        call.function = function; call.receiver = receiver; call.stackPointer = child.esp;
        call.sourceContext = &child; call.sourceReturnPC = sourceReturn;
        call.sourceTransferVersion = CLAW_SOURCE_TRANSFER_VERSION;
        call.sourceTransferKind = CLAW_SOURCE_TAIL_JMP;
        call.sourceTransferSite = sourceSite; call.sourceCallerFunction = sourceCaller;
        call.sourceDisposition = &disposition;
        const auto issued = call;
        tailIssued = true;
        host.call(host.user, &call);
        const bool scopeValid = sameSourceScope(host, hostBefore) &&
            !std::memcmp(&call, &issued, sizeof(call)) && sameSourceHeader(child, childBefore) &&
            !std::memcmp(parent, &parentBefore, sizeof(parentBefore));
        if (!scopeValid) fail(CLAW_FAULT_ABI, function);
        sourceTailOutput = child;
        sourceTailScope = hostBefore;
        copySourceCPU(*parent, sourceTailOutput);
        if (host.fault) {
            // Failed children retain their actual deepest CPU prefix; neither
            // immutable root header nor a returned disposition is adopted.
            throw Failure{};
        }
        validate_source_output(child, childBefore, function, sourceReturn, 0);
        if (disposition.size != sizeof(disposition) || disposition.version != CLAW_SOURCE_TRANSFER_VERSION ||
            disposition.disposition != CLAW_SOURCE_DISPOSITION_RETURNED ||
            disposition.callerFunction != sourceCaller || disposition.sourceSite != sourceSite ||
            disposition.targetFunction != function || disposition.entryStackPointer != childBefore.esp ||
            disposition.returnPC != sourceReturn || disposition.request != &call ||
            get(frame) != sourceReturn || !sameSourceScope(host, hostBefore) ||
            std::memcmp(&child, &sourceTailOutput, sizeof(child)) ||
            std::memcmp(&parent->eax, &sourceTailOutput.eax, 11 * sizeof(uint32_t))) fail(CLAW_FAULT_ABI, function);
        disposition.disposition = CLAW_SOURCE_DISPOSITION_NONE;
        tailReady = true;
        throw SourceTailReturned(this, sourceActivation);
    }

    void complete_source_tail(const SourceTailReturned &terminal, ClawSourceContext &context,
                              const ClawSourceContext &before, uint32_t returnPC) {
        if (terminal.owner != this || terminal.activation != sourceActivation || !tailReady || tailConsumed ||
            host.fault || host.guestSession || host.sourceContext != &context || &context != sourceParent ||
            host.sourceReturnPC != returnPC || returnPC != sourceReturn ||
            !sameSourceScope(host, sourceTailScope) ||
            !sameSourceHeader(context, before) ||
            std::memcmp(&context.eax, &sourceTailOutput.eax, 11 * sizeof(uint32_t))) fail(CLAW_FAULT_ABI, sourceCaller);
        tailConsumed = true;
        validate_source_output(context, before, sourceCaller, returnPC, 0);
    }
    void require_ordinary_source_return() const {
        if (tailIssued) fail(CLAW_FAULT_ABI, sourceCaller);
    }

    ClawHost &host;
    uint64_t operations = 0;
    uint32_t frame;            // entry stack pointer of the current owned function
    uint32_t stackPointer = 0; // explicitly tracked callee-entry ESP, never inferred from frame

  private:
    friend class SourceEntryActivation;
    uint32_t sourceCaller = 0, sourceArgumentCount = 0, sourcePopBytes = 0, sourceReturn = 0;
    uint64_t sourceActivation = 0;
    ClawSourceContext *sourceParent = nullptr;
    ClawSourceContext sourceOriginal{};
    ClawSourceContext sourceTailOutput{};
    ClawHost sourceTailScope{};
    bool tailIssued = false, tailReady = false, tailConsumed = false;
    static bool sameSourceHeader(const ClawSourceContext &a, const ClawSourceContext &b) {
        return a.size == b.size && a.version == b.version && a.inputMask == b.inputMask &&
            a.outputMask == b.outputMask && a.preserveMask == b.preserveMask &&
            a.reserved0 == b.reserved0 && a.reserved1 == b.reserved1;
    }
    static void copySourceCPU(ClawSourceContext &to, const ClawSourceContext &from) {
        std::memcpy(&to.eax, &from.eax, 11 * sizeof(uint32_t));
    }
    static bool sameSourceScope(const ClawHost &a, const ClawHost &b) {
        return a.user == b.user && a.bytes == b.bytes && a.call == b.call &&
            a.maximumOperations == b.maximumOperations && a.entryStackPointer == b.entryStackPointer &&
            a.remainingOperations == b.remainingOperations && a.compilerContext == b.compilerContext &&
            a.sourceContext == b.sourceContext && a.sourceReturnPC == b.sourceReturnPC && a.guestSession == b.guestSession && a.callbackCPU == b.callbackCPU;
    }
    uint32_t dispatch(uint32_t function, uint32_t ecx, uint32_t edx, std::initializer_list<uint32_t> arguments,
                      uint32_t x87ArgumentCount = 0, double x87Argument = 0) {
        tick();
        if (!host.call || arguments.size() > CLAW_CALL_ARGUMENT_CAPACITY)
            fail(CLAW_FAULT_ABI, function);
        ClawCall call{};
        call.function = function;
        call.receiver = ecx;
        call.receiver2 = edx;
        call.argumentCount = uint32_t(arguments.size());
        uint32_t index = 0;
        for (uint32_t argument : arguments)
            call.arguments[index++] = argument;
        call.stackPointer = stackPointer;
        call.x87ArgumentCount = x87ArgumentCount;
        call.x87Argument = x87Argument;
        uint32_t value = host.call(host.user, &call);
        if (host.fault)
            throw Failure{};
        return value;
    }
};

// The entry macro binds this before entering translated body code. No tail API
// accepts a caller identity, and an activation cannot be rebound on the Run.
class SourceEntryActivation {
  public:
    SourceEntryActivation(Run &run, uint32_t function, uint32_t arguments,
                          const ClawSourceContract &contract, ClawSourceContext &context, uint32_t returnPC) {
        if (run.sourceCaller) run.fail(CLAW_FAULT_ABI, function);
        static std::atomic<uint64_t> next{1};
        run.sourceActivation = next.fetch_add(1, std::memory_order_relaxed);
        if (!run.sourceActivation) run.fail(CLAW_FAULT_ABI, function);
        run.sourceCaller = function; run.sourceArgumentCount = arguments;
        run.sourcePopBytes = contract.returnPopBytes; run.sourceReturn = returnPC;
        run.sourceParent = &context; run.sourceOriginal = context;
    }
};

} // namespace claw

// Defines the exported entry. `owned(function)` returns the stack-argument
// count of an owned function or -1; `body(run, function, receiver, arguments)`
// runs it and returns EAX.
#define CLAW_MODULE_ENTRY(symbol, owned, body)                                                                         \
    extern "C" uint32_t symbol(uint32_t function, uint32_t receiver, const uint32_t *arguments,                        \
                               uint32_t argumentCount, ClawHost *host, uint32_t *result) {                             \
        if (!host || !result || host->fault)                                                                           \
            return 0;                                                                                                  \
        int expected = owned(function);                                                                                \
        if (expected < 0)                                                                                              \
            return 0;                                                                                                  \
        if (host->guestSession || host->compilerContext || host->sourceContext || host->sourceReturnPC || uint32_t(expected) != argumentCount || argumentCount > CLAW_CALL_ARGUMENT_CAPACITY || (argumentCount && !arguments)) {                                    \
            host->fault = CLAW_FAULT_ABI;                                                                              \
            host->faultAddress = function;                                                                             \
            return 0;                                                                                                  \
        }                                                                                                              \
        try {                                                                                                          \
            claw::Run run(*host);                                                                                      \
            run.validate_callback_entry(function, receiver, arguments, argumentCount);                                \
            *result = body(run, function, receiver, arguments);                                                        \
            return host->fault ? 0 : 1;                                                                                \
        } catch (claw::Failure &) {                                                                                    \
            return 0;                                                                                                  \
        }                                                                                                              \
    }


// Compiler entries use the ordinary exported function signature but require an
// explicit context and zero ordinary operands. They cannot run as cdecl0.
#define CLAW_COMPILER_MODULE_ENTRY(symbol, owned, body) \
    extern "C" uint32_t symbol(uint32_t function, uint32_t receiver, const uint32_t *, \
                               uint32_t argumentCount, ClawHost *host, uint32_t *result) { \
        if (!host || !result || host->fault || !owned(function)) \
            return 0; \
        try { \
            claw::Run run(*host); \
            if (host->guestSession || !host->compilerContext || host->sourceContext || host->sourceReturnPC || host->callbackCPU || receiver || argumentCount) \
                run.fail(CLAW_FAULT_ABI, function); \
            auto &context = *host->compilerContext; \
            run.validate_context(context, function); \
            const auto before = context; \
            body(run, function, context); \
            run.validate_context_output(context, before, function); \
            *result = context.eax; \
            return host->fault ? 0 : 1; \
        } catch (claw::Failure &) { \
            return 0; \
        } \
    }

// Each selected ordinary entry explicitly declares its source-state contract.
// The body models prologue/epilogue and leaves ESP at its original entry slot.
#define CLAW_SOURCE_MODULE_ENTRY_IMPL(symbol, owned, contract, body, guest) \
    extern "C" uint32_t symbol(uint32_t function, uint32_t receiver, const uint32_t *arguments, \
                               uint32_t argumentCount, ClawHost *host, uint32_t *result) { \
        if (!host || !result || host->fault || owned(function) < 0) return 0; \
        try { \
            claw::Run run(*host); \
            if ((!guest && host->guestSession) || host->compilerContext || uint32_t(owned(function)) != argumentCount || argumentCount > CLAW_CALL_ARGUMENT_CAPACITY || \
                (argumentCount && !arguments)) run.fail(CLAW_FAULT_ABI, function); \
            run.check_guest(); \
            const auto declared = contract(function); \
            if (!declared.inputMask && !declared.outputMask && !declared.preserveMask && !declared.returnPopBytes) { \
                if (host->guestSession || host->sourceContext || host->sourceReturnPC) run.fail(CLAW_FAULT_ABI, function); \
                run.validate_callback_entry(function, receiver, arguments, argumentCount); \
                *result = body(run, function, receiver, arguments); \
                return host->fault ? 0 : 1; \
            } \
            if (!host->sourceContext || !host->sourceReturnPC || host->callbackCPU) run.fail(CLAW_FAULT_ABI, function); \
            auto &context = run.source(); \
            const uint32_t returnPC = host->sourceReturnPC; \
            run.validate_source(context, function, returnPC); \
            if (context.inputMask != declared.inputMask || context.outputMask != declared.outputMask || \
                context.preserveMask != declared.preserveMask || declared.returnPopBytes > 4 * argumentCount || \
                run.frame != context.esp || uint64_t(context.esp) + 4u * (1u + argumentCount) > CLAW_STACK_END || \
                run.get(context.esp) != returnPC) run.fail(CLAW_FAULT_ABI, function); \
            for (uint32_t i = 0; i < argumentCount; ++i) \
                if (run.get(context.esp + 4u * (1u + i)) != arguments[i]) run.fail(CLAW_FAULT_ABI, function); \
            const auto before = context; \
            claw::SourceEntryActivation sourceActivation(run, function, argumentCount, declared, context, returnPC); \
            run.normalize_source_inputs(context); \
            uint32_t value = 0; \
            try { value = body(run, function, receiver, arguments); } \
            catch (const claw::SourceTailReturned &terminal) { \
                run.complete_source_tail(terminal, context, before, returnPC); \
                *result = context.eax; return 1; \
            } \
            run.require_ordinary_source_return(); \
            run.check_guest(); \
            if (host->sourceContext != &context || host->sourceReturnPC != returnPC || context.esp != before.esp || \
                run.get(context.esp) != returnPC) run.fail(CLAW_FAULT_ABI, function); \
            context.eax = value; \
            context.eip = returnPC; \
            context.esp += 4 + declared.returnPopBytes; \
            run.retain_source_unselected(context, before); \
            run.validate_source_output(context, before, function, returnPC, declared.returnPopBytes); \
            *result = value; \
            return host->fault ? 0 : 1; \
        } catch (claw::Failure &) { return 0; } \
          catch (claw::GuestControl &) { return 0; } \
          catch (...) { if (!host->fault) host->fault = CLAW_FAULT_HOST; return 0; } \
    }

#define CLAW_SOURCE_MODULE_ENTRY(symbol, owned, contract, body) \
    CLAW_SOURCE_MODULE_ENTRY_IMPL(symbol, owned, contract, body, false)
#ifdef CLAW_ENABLE_GUEST_TRANSFER
#define CLAW_GUEST_SOURCE_MODULE_ENTRY(symbol, owned, contract, body) \
    CLAW_SOURCE_MODULE_ENTRY_IMPL(symbol, owned, contract, body, true)
#define CLAW_GUEST_FUNCLET_ENTRY(symbol, body) \
    extern "C" uint32_t symbol(const ClawGuestEHInvocation *invocation, ClawHost *host) { \
        if (!host || host->fault) return 0; \
        try { \
            claw::Run run(*host); \
            if (!claw_guest_validate_eh(host, invocation)) run.fail(CLAW_FAULT_ABI); \
            body(run, *invocation); \
            run.check_guest(); \
            run.fail(CLAW_FAULT_ABI, invocation->entryPC); \
        } catch (claw::Failure &) { return 0; } \
          catch (claw::GuestControl &) { return 0; } \
          catch (...) { if (!host->fault) host->fault = CLAW_FAULT_HOST; return 0; } \
    }
#endif

// Optional capability retains two independently compared bodies. A caller
// never gets invented CPU state when selecting the ordinary ABI. Required
// entries remain strict even in a module containing optional entries.
#define CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(symbol, owned, contract, optional, ordinary_body, source_body) \
    CLAW_MODULE_ENTRY(symbol##_ordinary_capability, owned, ordinary_body) \
    CLAW_SOURCE_MODULE_ENTRY(symbol##_source_capability, owned, contract, source_body) \
    extern "C" uint32_t symbol(uint32_t function, uint32_t receiver, const uint32_t *arguments, \
                               uint32_t argumentCount, ClawHost *host, uint32_t *result) { \
        if (!host) return 0; \
        if (host->sourceContext || host->sourceReturnPC || !optional(function)) \
            return symbol##_source_capability(function, receiver, arguments, argumentCount, host, result); \
        return symbol##_ordinary_capability(function, receiver, arguments, argumentCount, host, result); \
    }

#endif
