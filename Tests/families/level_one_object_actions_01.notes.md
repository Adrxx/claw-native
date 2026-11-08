# Level 1 object actions batch 1: boundary decisions

## 2026-10-18, harness-mfc-callee-caller-frame

- `0x4dbd60` (bit set assignment) stays original code on both sides, now declared
  `kind: whole`, thiscall, one argument, with `caller_frame`. Its allocation-failure
  path calls `0x4dc680`, which returns the word at the caller's EBP plus 4. At the
  owned call sites EBP is not a frame pointer: in `0x4332f0` (CALL `0x43366b`) it holds
  receiver + `0x128`, in `0x44c000` (CALL `0x44c1f4`) receiver + `0x230`. The harness
  checks both rules against the original at every declared site and gives native
  bridges the same EBP. Before this, case `ctor 4332f0 allocation fails from call 2`
  faulted on the native side only.
- `0x4a9070` (C runtime realloc) is a stand-in (`reallocate`), like malloc and free.
  The table grow `0x4db6e0` reaches it, and with an existing table it ends in the
  HeapReAlloc import.
- Import `0x546a40` (IsBadReadPtr) is a stand-in (`is-bad-read-ptr`). The C runtime
  typeid `0x4a36f0` calls it once the receiver has a real vtable from the image. A
  receiver whose first word is not a vtable faults inside `0x4a36f0`; the original
  would raise a C++ exception there, which the ordinary comparison does not carry.
- Not reachable without a crash: in `0x44c840`, the ranges after `0x4db6e0` returns 0
  (`0x44c895-0x44c8c3`, `0x44c8de-0x44c8f5`, `0x44c90f-0x44c942`). `0x4db6e0` returns
  0 only after its realloc fails. It then calls `0x4dc680` with its own EBP still 0,
  so the original reads address 4 and stops with an access violation. The second
  grow call is reachable only after that first failure. Covering these needs a
  coverage exemption, which the batch coordinator records with this reason; no stand-in
  can reach them honestly.
