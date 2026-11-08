# Original graphics-manager lifecycle

`GraphicsManagerLifecycleRuntime.{h,cpp}` recovers the bounded original v1.0 graphics-manager startup, display-mode inventory, reset and deletion orchestration. It composes the frozen graphics constructor, CArray, CPtrList and palette-resource bodies. Physical DirectDraw creation, COM methods, window identity, allocator transport and diagnostics remain named services. This does not establish full original application startup or physical Windows display equivalence.

The comparison executable is `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private decompilation and bounded instruction evidence are in `work/graphics-manager-lifecycle-agent/roots.c`, `leaves.c` and the repository's read-only v1.0 disassembly. Source bytes are not patched; only imported physical transport is resolved to the test adapter.

## Entry inventory

| Original entry | Raw arguments after receiver | Recovered behavior |
| --- | --- | --- |
| `4bc120` | none | Composes frozen whole 2180-byte manager constructor. |
| `4bc220` | HWND, optional GUID, width, height, depth, cooperative flags | Whole startup, RET24. |
| `4bc400` | restore display flag | Whole teardown, RET4. |
| `4bc1b0` | none | Teardown(1), embedded array/list destruction; does not free manager. |
| `4bcc50` | none | Whole enumeration, transfer and unsigned sorting. |
| `4bcda0` | descriptor token, ignored context | Actual stdcall enumeration callback, RET8. |
| `4bcde0` | mode A, mode B | Unsigned width/height/depth comparator, RET8. |
| `4bd1c0` | width, height, depth | SetDisplayMode and format setup, RET12. |
| `4bd0c0` | none | GetDisplayMode and source channel-mask globals. |
| `4bc4b0` / `4bc9d0` | none | Whole surface/palette list cleanup. |
| `4bc5f0` | deleting flags | Default surface deleting wrapper, RET4. |
| `4bc610` / `4b9540` | none | Default surface derived/base cleanup. |
| `4f551d` / `4f5192` | none | Raw array/list destructor bodies. |
| `4bc0e0` / `4bc100` | none | Actual global mode-array construction/destruction wrappers. |

The global initializer is **4bc0e0**, which tail-calls the frozen array constructor with ECX=541378. 4bcc10 is inside a different routine and is not an initializer. The enclosing static registration wrapper 4bc0d0/4bc0f0 and physical atexit transport are outside this API.

## Native object graph recipe

Allocate exactly **2180 bytes / 545 words** for the manager. Manager word0 is the DirectDraw interface token, not a manager vtable. Call frozen/source 4bc120 before startup; preserve allocation-seed bytes which that constructor does not write. Its final zero stores are +0, +470, +474, +878, +87c and +880; the two lists and array receive their actual constructors.

Provide these embedded spans in the same allocation:

| Offset | Span and role |
| --- | --- |
| +4, +140 | Two 316-byte/79-word DDCAPS buffers. |
| +3b8 | Seven-word CPtrList of surface objects, head +3bc. |
| +3d4 | Seven-word CPtrList of palette backends, head +3d8. |
| +3f0 | Five-word raw array: VT, data, size, capacity, growth. |
| +470 | Source copies `(manager[2] & 08000000)` after GetCaps. |
| +474 | Display bit depth. |
| +878, +87c | Reset to zero at each startup. |
| +880 | Sticky first startup error. |

Expose a separate mutable **five-word span at original token 541378** and initialize through API entry 4bc0e0. The enumeration callback and source arrays access that raw token; there is no independent context-owned list of modes.

`ClawGraphicsManagerLifecycleGlobals` binds the original shared device 541398, cooperative holder 541374, shifts 54135c/360/364 and reductions 541368/36c/370. Keep these aliases shared with PaletteResourceRuntime and image presentation; do not maintain divergent copies. An optional palette context must use the same raw heap and a valid globals pointer. The bridge synchronizes its cooperative holder before and after each dependency callback so mutations remain visible.

Invoke `4bc220(manager, HWND, GUID-or-zero, width, height, depth, flags)`. If 541398 is nonzero it is assigned directly to manager[0], with **no AddRef**. Otherwise actual DirectDrawCreate import slot **546850** receives `(GUID, &manager[0], 0)`; the output pointer is a real heap token. Success eventually sets 541374 to the manager.

Physical COM callbacks use receiver0 and include the interface token as argument0. Their function identity is read from the actual interface vtable. Required startup slots are +50 SetCooperativeLevel, +2c GetCaps, +20 EnumDisplayModes, +54 SetDisplayMode and +30 GetDisplayMode. Teardown uses +4c RestoreDisplayMode and +8 Release. GetDisplayMode exposes a synchronous **108-byte / 27-word local descriptor**, normalized pointer argument1=0, localMask=2; callback writes are observed by the source continuation. EnumDisplayModes receives `(DD,0,0,0,4bcda0)` and must invoke the actual supplied callback for every returned descriptor rather than replacing its allocation/copy/append behavior.

## Source behavior and ownership

HRESULT checks are `!=0`, including positive results. Failed create sets sticky1001; failed cooperative setup sets1002. Caps and enumeration diagnostics continue. Failed SetDisplayMode sets1004; failed format query after successful mode selection sets1005. Existing +880 errors survive later failures. Diagnostic 4bd260 receives the exact source filename token, line and HRESULT; its formatter/dialog body remains a service.

Width/height admission is signed and requires both positive. Mode descriptor sorting is unsigned width(+c), height(+8), then depth(+54), preserves duplicates, and follows the original pairwise swap order. Each callback allocates108 bytes, copies all27 descriptor words, and appends to global541378 using the frozen CArray body. The temporary array transfers pointers to manager+3f0, then releases only its pointer storage. Existing manager mode descriptors are freed before enumeration; array size/data are reread after callbacks.

Pixel masks are descriptor words22/23/24, while word21 is bit depth. Each channel shift is its first set-bit position, or FFFFFFFF for an empty mask. Reduction is wrapping `8 - popcount(mask)`. Empty indexed-display masks therefore produce shifts FFFFFFFF and reductions8; no RGB888 mask default is inserted by the source. The adapter must supply actual descriptor fields for its declared device profile.

Teardown optionally restores the display, frees mode records, clears surfaces then palettes, **unconditionally clears 541374**, releases manager[0] and zeros it, then clears +470. It preserves +474, +880, 541398 and channel globals. Repeated empty teardown/destruction is measured. A shared541398 interface is still released through the manager, and 541398 itself remains unchanged; transport owns that original shared-reference contract.

Surface and palette loops capture node.next **before** deleting payloads. The default surface is exactly **188 bytes / 47 words**, VT513690, deleting slot0=4bc5f0. Derived destructor4bc610 sets VT513588, calls base4b9540, and destroys its five-word array at+90. Base cleanup invokes child virtual deleting callbacks in unsigned +98 count order through data+94, rereads count after each callback, clears the array, releases DD surface+8 unless borrowed flag+78 mask1 is set, zeros +8 and +b4. Deleting flag mask1 frees the object. Other polymorphic deleting targets remain explicit exact services; this module does not assign their class behavior.

Palette cleanup composes frozen4bb2a0 on each **56-byte / 14-word** backend and then frees it. That source body clears its COM token without Release and frees its owned buffers; the adapter must preserve that source ordering. List RemoveAll composes the frozen CPtrList body and its pool ownership. The raw array destructor4f551d writes VT51079c, calls free(data) **even if null**, then writes VT50becc; it does not release CString elements or clear data/count/capacity/growth fields. List destructor4f5192 writes VT51000c, removes all, then VT50becc.

## Verification and limits

`work/test-env/bin/python Tests/compare_graphics_manager_lifecycle_runtime.py` passes **437 whole original calls + 2 stopped unsafe prefixes**, **1,766 ordered snapshots**, and **1,082 total instrumented addresses**. Each event compares the complete **262,144-byte heap**, **294,912-byte global range**, allocation liveness and free history; return values and original stack-pop ABI are checked where meaningful. It covers creation/shared-device variants, signed dimensions, 8/16/24/32-bit descriptors, positive/negative HRESULTs, sticky errors, duplicate/multi-mode sorting, zero/discontiguous/full masks, borrowed surfaces/deleting flags and all14 actual768-byte MAIN.PAL assets in retained startup→palette→surface→reset→teardown→repeat-destruction graphs.

Directed callback mutations verify captured next nodes, live child/mode count rereads, shared palette cooperative aliases, diagnostic changes to sticky error, and Release callback rebinding followed by original zeroing. The source mode callback does not check allocation failure before copying: one prefix stops before REP MOVSD at4bcdb7. A successful physical create that returns a null interface stops before the source vtable dereference at4bc25c. Native span failure preserves reached stores/events and reports fault1; neither prefix is called a successful original recovery.

`work/test-env/bin/python work/graphics-manager-lifecycle-agent/checks.py` reproduces the strict C11 header, warning-clean/pedantic C++17, Swift ABI import and sanitizer checks; they pass. A private ASAN+UBSAN smoke executes **64 exact2180-byte manager histories**, each with an exact188-byte parent/child surface chain, source deletion and startup/teardown/repeated destruction. Only this worker's standalone checks ran; no Xcode/device/shared build files were changed.

Bounds checks and traversal caps are native diagnostics, not original exception semantics. Physical DirectDraw/COM/window operation, descriptor generation, allocation transport, diagnostics4bd260 and unknown polymorphic deleting methods remain explicit services. General surface restore behavior outside these elected lifecycle bodies, SEH/MFC unwinding and complete application display startup are not claimed. The real PAL assets are used through frozen source palette conversion; test-generated display descriptors and COM return profiles are transport fixtures, not recovered Windows hardware output.

Address-count clarification: the reported address union includes physical test
callback and return-stop addresses. It is a total instrumented-address count,
not original instruction coverage. Whole unchanged-original call counts, full
heap/global/liveness snapshots, ABI and sanitizer evidence are unaffected.
The pinned original executable .text range is401000..50adb5; future reports
separate instrumented text addresses from total instrumented addresses.
