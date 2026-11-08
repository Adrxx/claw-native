#include "ClawRuntime.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <string>

namespace {
constexpr uint32_t root = 0x401000, child = 0x402000, caller = 0x404000, callRoot = 0x405000;
constexpr uint32_t argumentRoot = 0x406000, popRoot = 0x407000;
constexpr uint32_t frame = CLAW_STACK_TOP - 0x100;
int checks = 0;
void check(bool ok) { ++checks; assert(ok); }
struct Fixture {
    std::array<uint8_t, CLAW_STACK_END - CLAW_STACK_BASE> stack{};
    std::string mode;
    uint64_t budget = 1000;
    uint32_t callbacks = 0, tailCallbacks = 0, receiver = 0;
    bool afterJmp = false;
};
ClawSourceContext seed(uint32_t entry) {
    return {72,1,0x7ff,0x7ff,0x10,0x20,0x30,0x40,0x50,0x60,0x70,frame,entry,2,0xffffffff,0x472,0,0};
}
uint32_t word(Fixture &f,uint32_t at) {
    uint32_t v;std::memcpy(&v,f.stack.data()+at-CLAW_STACK_BASE,4);return v;
}
void put(Fixture &f,uint32_t at,uint32_t value) { std::memcpy(f.stack.data()+at-CLAW_STACK_BASE,&value,4); }
uint8_t *bytes(void *user,uint32_t at,uint32_t count) {
    auto &f=*static_cast<Fixture *>(user);
    if (at<CLAW_STACK_BASE || uint64_t(at)+count>CLAW_STACK_END) return nullptr;
    return f.stack.data()+at-CLAW_STACK_BASE;
}
int childOwned(uint32_t fn) { return fn==child ? 0 : -1; }
ClawSourceContract childContract(uint32_t) { return {0x7ff,0x7ff,0,0}; }
uint32_t childBody(claw::Run &run,uint32_t,uint32_t,const uint32_t *) {
    auto &f=*static_cast<Fixture *>(run.host.user);auto &c=run.source();
    f.receiver=c.ecx;c.eax=0x12345678;c.ecx=0xcafebabe;c.edx=0x11223344;c.eflags=0x46;
    if (f.mode=="parentPreserve") c.ebx ^= 1;
    return c.eax;
}
}
CLAW_SOURCE_MODULE_ENTRY(tail_child_entry,childOwned,childContract,childBody)

namespace {
int parentOwned(uint32_t fn) { return fn==argumentRoot ? 1 : fn==root || fn==callRoot || fn==popRoot ? 0 : -1; }
ClawSourceContract parentContract(uint32_t fn) { return {0x7ff,0x7ff,0x472,fn==popRoot ? 4u : 0u}; }
uint32_t parentBody(claw::Run &run,uint32_t fn,uint32_t,const uint32_t *) {
    auto &f=*static_cast<Fixture *>(run.host.user);auto &c=run.source();
    if (fn==callRoot) {
        c.esp -= 4;run.put(c.esp,callRoot+5);c.eip=root;
        auto nested=c;
        run.source_call(root,0,callRoot+5,nested);
        c=nested;return c.eax;
    }
    const auto initial=c;
    if (f.mode=="fakeBodyReturn") { c.esp += 4;c.eip=run.host.sourceReturnPC;return 77; }
    c.eip=root+5;auto target=c;target.eip=child;target.preserveMask=0;
    if (f.mode=="workingFrame") target.esp -= 4;
    if (f.mode=="childInput") target.inputMask ^= 1;
    if (f.mode=="alias") run.source_tail(child,0,root+5,c);
    if (f.mode=="receiver") run.source_tail(child,c.ecx+1,root+5,target);
    try { run.source_tail(child,c.ecx,root+5,target); }
    catch (const claw::SourceTailReturned &terminal) {
        if (f.mode=="swallow") return c.eax;
        if (f.mode=="repeatTail") run.source_tail(child,c.ecx,root+5,target);
        if (f.mode=="repeatCompletion") {
            run.complete_source_tail(terminal,c,initial,run.host.sourceReturnPC);
            run.complete_source_tail(terminal,c,initial,run.host.sourceReturnPC);
        }
        if (f.mode=="afterTerminalScope") run.host.entryStackPointer ^= 4;
        if (f.mode=="afterTerminalCPU") c.edx ^= 1;
        if (f.mode=="afterTerminalHeader") c.version=2;
        throw;
    }
    f.afterJmp=true;return 0;
}
}
CLAW_SOURCE_MODULE_ENTRY(tail_parent_entry,parentOwned,parentContract,parentBody)

namespace {
uint32_t callback(void *user,const ClawCall *call) {
    auto &f=*static_cast<Fixture *>(user);++f.callbacks;
    auto *h=static_cast<ClawHost *>(nullptr);
    // Tests bind the live host below; no global invocation/context aliases.
    extern thread_local ClawHost *active;
    h=active;check(h && h->sourceContext && call->sourceContext != h->sourceContext);
    const auto saved=*h;auto *parent=h->sourceContext;
    if (call->sourceTransferKind==CLAW_SOURCE_TAIL_JMP) {
        ++f.tailCallbacks;
        check(call->sourceTransferVersion==1 && call->sourceTransferSite==root+5 && call->sourceCallerFunction==root);
        check(call->argumentCount==0 && call->sourceDisposition && call->sourceDisposition->disposition==0);
        check(call->sourceContext->esp==parent->esp && call->stackPointer==h->entryStackPointer);
        check(word(f,call->stackPointer)==call->sourceReturnPC);
        if (f.mode=="fault" || f.mode=="budgetInside") {
            call->sourceContext->eip=child+7;call->sourceContext->eax=0x77;
            h->fault=f.mode=="fault" ? CLAW_FAULT_HALT : CLAW_FAULT_BUDGET;h->faultAddress=child+7;
            return 0;
        }
    } else {
        check(call->sourceTransferVersion==0 && call->sourceTransferSite==0 &&
              call->sourceCallerFunction==0 && call->sourceDisposition==nullptr);
    }
    h->sourceContext=call->sourceContext;h->entryStackPointer=call->stackPointer;h->sourceReturnPC=call->sourceReturnPC;
    uint32_t value=0;
    const uint32_t completed=call->function==child ?
        tail_child_entry(child,call->receiver,nullptr,0,h,&value) :
        tail_parent_entry(root,0,nullptr,0,h,&value);
    h->sourceContext=saved.sourceContext;h->entryStackPointer=saved.entryStackPointer;h->sourceReturnPC=saved.sourceReturnPC;
    if (!completed || h->fault) return 0;
    if (call->sourceTransferKind==CLAW_SOURCE_TAIL_JMP && f.mode!="missingReceipt") {
        *call->sourceDisposition={sizeof(ClawSourceDisposition),1,CLAW_SOURCE_DISPOSITION_RETURNED,
            call->sourceCallerFunction,call->sourceTransferSite,call->function,call->stackPointer,call->sourceReturnPC,call};
        auto &d=*call->sourceDisposition;
        if (f.mode=="receiptSize") d.size=0;
        if (f.mode=="receiptVersion") d.version=2;
        if (f.mode=="receiptDisposition") d.disposition=7;
        if (f.mode=="receiptCaller") d.callerFunction ^= 4;
        if (f.mode=="receiptSite") d.sourceSite ^= 4;
        if (f.mode=="receiptTarget") d.targetFunction ^= 4;
        if (f.mode=="receiptFrame") d.entryStackPointer -= 4;
        if (f.mode=="receiptReturn") d.returnPC ^= 4;
        if (f.mode=="receiptRequest") d.request=nullptr;
        if (f.mode=="wrongPop") call->sourceContext->esp += 4;
        if (f.mode=="childHeader") call->sourceContext->version=2;
        if (f.mode=="parentHeader") parent->preserveMask=0;
        if (f.mode=="hostScope") h->sourceReturnPC ^= 4;
        if (f.mode=="returnWord") put(f,call->stackPointer,0xdeadbeef);
        if (f.mode=="requestKind") const_cast<ClawCall *>(call)->sourceTransferKind=CLAW_SOURCE_CALL;
        if (f.mode=="requestCaller") const_cast<ClawCall *>(call)->sourceCallerFunction ^= 4;
        if (f.mode=="requestDisposition") const_cast<ClawCall *>(call)->sourceDisposition=nullptr;
    }
    return value;
}
thread_local ClawHost *active=nullptr;
void run(const std::string &mode,bool success,uint32_t entry=root) {
    Fixture f;f.mode=mode;
    if (mode=="budgetBefore") f.budget=1;
    auto cpu=seed(entry);const auto original=cpu;
    put(f,frame,caller);put(f,frame+4,0xaabbccdd);put(f,frame+8,0x11223344);
    const auto before=f.stack;
    ClawHost h{};h.user=&f;h.bytes=bytes;h.call=callback;h.entryStackPointer=frame;
    h.remainingOperations=&f.budget;h.sourceContext=&cpu;h.sourceReturnPC=caller;
    if (mode=="guest") h.guestSession=reinterpret_cast<ClawGuestSession *>(uintptr_t(1));
    active=&h;uint32_t value=0xfeedface;
    const uint32_t argument=0xaabbccdd;
    uint32_t completed=tail_parent_entry(entry,0,entry==argumentRoot ? &argument : nullptr,entry==argumentRoot ? 1 : 0,&h,&value);active=nullptr;
    check(bool(completed)==success && !f.afterJmp);
    if (success) {
        check(!h.fault && value==0x12345678 && cpu.eax==value && cpu.esp==frame+4 && cpu.eip==caller);
        check(cpu.preserveMask==original.preserveMask && cpu.inputMask==0x7ff && cpu.outputMask==0x7ff);
        check(cpu.ebx==original.ebx && cpu.esi==original.esi && cpu.edi==original.edi && cpu.ebp==original.ebp && cpu.fsHead==original.fsHead);
        check(f.tailCallbacks==1 && f.callbacks==(entry==callRoot ? 2u : 1u));
        check(f.receiver==original.ecx && word(f,frame+4)==0xaabbccdd && word(f,frame+8)==0x11223344);
        if (entry==root) check(f.stack==before);
        else check(word(f,frame-4)==callRoot+5 && word(f,frame)==caller);
    } else {
        check(h.fault && value==0xfeedface && word(f,frame+4)==0xaabbccdd);
        if (mode=="fault" || mode=="budgetInside") check(cpu.eip==child+7 && cpu.eax==0x77 && cpu.esp==frame);
        if (mode=="budgetBefore" || mode=="guest" || mode=="alias" || mode=="receiver" || mode=="workingFrame" || mode=="childInput" || mode=="fakeBodyReturn") check(f.callbacks==0);
        if (mode=="repeatTail" || mode=="repeatCompletion" || mode=="swallow") check(f.tailCallbacks==1 && cpu.esp==frame+4);
        if (entry==argumentRoot || entry==popRoot) check(f.callbacks==0);
    }
}
}
int main() {
    run("positive",true);run("positive",true,callRoot);
    run("arguments",false,argumentRoot);run("pop",false,popRoot);
    for (const auto *mode:{"missingReceipt","receiptSize","receiptVersion","receiptDisposition","receiptCaller","receiptSite",
         "receiptTarget","receiptFrame","receiptReturn","receiptRequest","wrongPop","childHeader","parentHeader","hostScope",
         "returnWord","workingFrame","childInput","alias","receiver","fakeBodyReturn","parentPreserve","swallow",
         "repeatTail","repeatCompletion","afterTerminalScope","afterTerminalCPU","afterTerminalHeader",
         "requestKind","requestCaller","requestDisposition","budgetBefore","budgetInside","fault","guest"}) run(mode,false);
    std::printf("{\"status\":\"pass\",\"checks\":%d,\"call_size\":%zu,\"host_size\":%zu,\"disposition_size\":%zu,"
        "\"version_offset\":%zu,\"kind_offset\":%zu,\"site_offset\":%zu,\"caller_offset\":%zu,\"disposition_offset\":%zu,\"request_offset\":%zu}\n",
        checks,sizeof(ClawCall),sizeof(ClawHost),sizeof(ClawSourceDisposition),offsetof(ClawCall,sourceTransferVersion),
        offsetof(ClawCall,sourceTransferKind),offsetof(ClawCall,sourceTransferSite),offsetof(ClawCall,sourceCallerFunction),
        offsetof(ClawCall,sourceDisposition),offsetof(ClawSourceDisposition,request));
}
