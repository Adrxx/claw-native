# Level 1 player actions batch 1: boundary decisions

## 2026-10-18, harness-mfc-callee-caller-frame

- `0x4a9070` (C runtime realloc) is a stand-in (`reallocate`), like malloc and free.
  The table grow `0x4db6e0` reaches it from `0x40ebe0` and `0x40f2a0`; with an existing
  table it ends in the HeapReAlloc import. This makes `0x40ec09-0x40ec22`,
  `0x40f2ee-0x40f317` and `0x40f352-0x40f366` reachable.
- Import `0x546a40` (IsBadReadPtr) is a stand-in (`is-bad-read-ptr`). The empty-slot
  path of `0x40ebe0` (`0x40ece2-0x40ecf1`) calls the C runtime typeid `0x4a36f0` on the
  receiver; with a receiver whose vtable is a real one from the image, typeid reaches
  this import and returns the type descriptor. A null or non-vtable receiver makes the
  original raise a C++ exception, which the ordinary comparison does not carry.
- Not reachable without a crash: the ranges after `0x4db6e0` returns 0
  (`0x40ec35-0x40ec63`, `0x40ec7e-0x40ec95`, `0x40ecaf-0x40ece2` in `0x40ebe0`,
  `0x40f317-0x40f340` in `0x40f2a0`). `0x4db6e0` returns 0 only after its realloc
  fails. It then calls `0x4dc680` with its own EBP still 0, so the original reads
  address 4 and stops with an access violation. The second grow call is reachable only
  after that first failure. Covering these needs a coverage exemption, which the
  batch coordinator records with this reason; no stand-in can reach them honestly.
