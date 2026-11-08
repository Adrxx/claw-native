# Original graphics-manager construction

GraphicsManagerConstructionRuntime executes whole original4bc120 over the exact
2180-byte object and whole20-byte CStringArray constructor4f54ea. It composes
both original CPtrList4f5133 constructors at3b8/3d4 through frozen
SoundTriggerLogicRuntime, then constructs the array at3f0 and clears0/470/474/
878/87c/880. Every other allocation-seed byte is preserved. This is distinct from
existing pointer-CArray4f58ab, whose vtable differs. No existing body is duplicated.

The unchanged hash-pinned original is350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263.
Tests/compare_graphics_manager_construction.py compares1024 complete original
calls, meaningful EAX, full64KiB heap and320KiB global image. Original list/array
callees execute without stubs. The required source SEH chain has a mapped fixture
page at0; CPU stack/SEH stores are excluded from heap identity as in other source
constructor tests.64 exact2180/20-byte original-derived replays pass ASAN/UBSAN.
The native Swift bridge/import and source palette startup check execute this API.

Native missing/short-span diagnostics do not establish original clean failures.
Physical device initialization4bc220, graphics teardown4bc1b0/4bc400, source
exception unwinding and application-wide surface lifetime remain separate work.
Constructor success does not prove a complete retail graphics startup.

Reproduce: first run work/test-env/bin/python
Tests/compare_graphics_manager_construction.py, then python3
Tests/check_graphics_manager_construction_asan.py. The original comparison writes
ignored fixtures under work/graphics-manager-construction; the sanitizer script
generates/executes the exact-allocation C++ harness from those captures.
