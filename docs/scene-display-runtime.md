# Original surface holder and renderer queue

`SceneDisplayRuntime.{h,cpp}` recovers original v1.0 holder initialization/readiness/cleanup, its finite default wrapper and surface-factory graph, and renderer queue drain4d63c0. It composes frozen GraphicsManagerLifecycleRuntime, GameImageRuntime, SinglePlayerSceneRuntime's45fde0 constructor, CPtrList and raw-array constructor bodies. Source queue drain is separate from physical presentation: this module does not replace DirectDraw with a fake successful present.

Evidence uses unchanged `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private bounded decompilation and source-table capture live in `work/scene-display-agent/`; physical imported functions are adapter boundaries, while source bodies execute unchanged in the oracle.

## Raw graph and initial setup

The frozen scene initializer4cea10 allocates a **28-byte holder**, stores it at scene+4, initializes base fields through45fde0(scene,0,0), installs VT513c68, and zeros holder+10/+14/+18. Holder+c points back to that **60-byte scene**. Scene+1c is the **2180-byte graphics manager**, scene+30 HWND and scene+34 original flags; scene+38 is the sticky scene error.

Holder4ca6f0 takes `(width,height,depth,flags)`, RET16. It allocates and initializes, in order:

| Holder field | Exact allocation | Source initialization |
| --- | --- | --- |
| +10 | 48 bytes |4cab90(parent,0,0), VT5138d8, +2c=0. |
| +14 | 52 bytes |Frozen45fde0(parent,1,0), +10=0, VT50e8e4, +2c=0,+30=1. |
| +18 | 52 bytes |Frozen45fde0(parent,2,0), +10=0, VT50e8e4, +2c=0,+30=1. |

Other allocation-seed words remain untouched until elected source routines write them. It invokes primary virtual+2c=4d5510(width,height,depth), then first auxiliary virtual+24=4d4000(width,height), then the second auxiliary initializer unless the supplied **flags&1** is set. Failure sets scene error2001/2002/2003 only if scene+38 iszero; lower called routines may already have supplied a more specific error. Reinitializing a live holder replaces its pointers without deleting the old wrappers; no extra cleanup is inserted.

Readiness4cf730 checks only that all three wrapper pointers are nonzero, in +14,+18,+10 order. It does not invoke child readiness. With successful third allocation and flags1, it returns1 even though the second auxiliary's source initialization was skipped. Conversely third allocation failure with flags1 permits initialization return1 but readiness return0; that source behavior is tested. GetType4cf750 returns **15**, distinct from readiness and image format kinds.

The primary4d5510 first writes wrapper+10/+14/+18 to the requested width/height/depth, captures scene+c and manager+1c, and invokes frozen4bc220 with these **six arguments**:

1. HWND=scene+30.
2. Raw GUID argument=`(scene+34 & 10hex) ? 2 : 0`.
3. Width.
4. Height.
5. Depth.
6. Cooperative flags=`signed(width)>320 ? 11hex : 51hex` (17/81 decimal).

The raw GUID value2 is preserved as source transport; this code does not invent a GUID object. Source4bc220 controls HRESULT/error and display globals. On failure, graphics sticky1001..1005 map to scene80e9..80ed; other/zero errors map3001, with prior scene error retained. On success it rereads scene flags and invokes primary factory4bc890(manager, `(flags&2)?2:1`), stores wrapper+2c and tests the surface's actual VT+14 readiness. Missing/nonready primary sets scene3002.

## Surface creation and ownership

All finite factories here allocate **188-byte / 47-word surfaces**, call the frozen five-word array constructor at+90, zero exactly +8,+4,+78,+a4,+b4, and preserve other allocation-seed words. Actual source vtables and virtual calls stay in the raw heap.

| Entry | Arguments | Whole source behavior |
| --- | --- | --- |
|4bc890 |Primary/backbuffer count |VT5136c0; virtual+24=4bfb80(manager,24,33,count), append to manager surface list, copy surface+a4 to manager+474. |
|4bcf80 |Existing primary surface,caps |Calls its DirectDraw interface GetAttachedSurface VT+30; allocates VT513588 and calls4b91f0(returned DD interface), appends it. |
|4bc670 |Width,height,depth,flags,color key |VT513690; virtual+2c=4bf970(manager,args), appends it. |
|4bc4f0 |Surface token |Removes node at surface+4 from manager+3b8, then calls actual surface virtual slot0 deleting callback(1). |

4bc890's4bfb80 zeros its108-byte descriptor at+c, sets descriptor size108, flags33, caps `(24|200hex)` and backbuffer count, then source4b9150→frozen4b9380 performs physical surface creation and metadata. Blank4bf970 composes frozen4b9180 with flags|40hex, and frozen4b9990 only if color-key argument is not FFFFFFFF. FrozenGameImage4bc490 performs the exact source append/node store and composes the recovered CPtrList AddTail through this bridge.

Attached4bcf80 exposes two synchronous **four-byte local buffers** for COM arguments1/2: caps initialized from caller and output interface initialized0; normalized arguments are0 and localMask=6. HRESULT!=0 calls diagnostic4bd260(532524,64a,hr) then returns0, without invented cleanup of an output written on error. Success calls4b91f0, which stores DD+8, clears108 descriptor bytes, sets size108 and calls actual DD GetSurfaceDesc VT+58 with a real surface+c pointer. A nonzero result diagnoses(5324dc,7b,hr) but continues source metadata construction and returns1. It derives source+a4 depth, +a8 row bytes, +ac bytes-per-pixel, +b0 pitch pixels, bounds and total bytes from actual descriptor fields, then sets borrowed mask1 at+78. Metadata arithmetic wraps as source UInt32; no format or alpha default is invented.

4d4000 enforces signed positive dimensions and sets source geometry rectangle fields. Type1 obtains the attached surface from scene+4→holder+10→primary+2c using caps4. Its failure sets scene4003. If callbacks change the wrapper type, the source rereads it and may additionally take the ordinary allocation path. Other types call4bc670(width,height,0,0,FFFFFFFF), failure4004. Bad sizes set4001(type1) or4002(other), preserving prior errors. Success sets wrapper+30=1.

4d4160 unlinks/deletes wrapper+2c only when both it and ownership word+30 are nonzero; then clears+2c. Borrowed wrappers preserve that pointer and always clear width+10. 45fe60 installs VT50e8e4, invokes4d4160, clears original base fields and finishes VT50becc;45fe40 additionally frees when flags&1. Primary4cabe0→45fec0 clears base fields/free wrapper only: it does **not** release the primary surface or tear down the graphics manager. The manager's source surface list retains ownership of that primary.

Holder4ca8b0 deletes primary then auxiliary1 then auxiliary2 through virtual+4(1), zeroing each slot after return and rereading later slots after callbacks. Derived4cf780 installs VT513c68 before cleanup, then +4=FFFFFFFF,+8=0,+c=0,VT50becc. Deleting4cf760 conditionally frees holder and returns its token. Separate manager destructor4bc1b0 elects restore flag1 through frozen4bc400; holder cleanup does not invent a display restore or manager destruction call.

Default primary/base surface deleting wrappers4bc810/4bb060 and destructors4bc830/4bb080 are exported. Their complete source stores/callee effects match the frozen4bc610 body: install VT513588, complete base4b9540, then array4f551d; deleting flags&1 free the object. All four entries have independent original full-buffer comparisons. Other polymorphic targets remain exact services.

## Queue semantics

Renderer VT513be8 virtual+34 selects **4d63c0(surface,arg2), RET8**. Its seven-word CPtrList starts at renderer+10, head+14. Each node is three words(next,prev,payload). Child must expose virtual+28 draw, virtual+4 deleting destructor and at least word+64 remaining count.

It captures the current payload and node.next before calling child virtual+28(surface,arg2). It then rereads child+64, subtracts1 with UInt32 wrap, stores it, and calls **arg2 virtual+14**. If that result is nonzero, or the reread count is signed<=0, it removes the captured node through frozen4f5212 and invokes child virtual+4(1). The second count read occurs after readiness callback; callback writes can prevent or elect removal. Captured next remains authoritative after drawing/removal callbacks. A nonempty queue requires both child and arg2 valid; an empty queue returns without dereferencing either supplied argument.

The specialized child's actual draw and deleting routines remain source-address services. Queue comparison callbacks provide declared writes/returns and do not pretend to recover particle, fade or image drawing bodies. Story's already-frozen4ca9e0/4caa90/4caa20 are untouched and compose externally; resize/source leaves4d4280/4d5720 are not exported here. Physical presentation is still a separate elected caller/COM operation.

## API and evidence

Provide the real raw token heap through `ClawSceneActorHost`, optional shared GraphicsManagerLifecycleContext and GameImageGlobals, and a synchronous rich dependency. With those optional contexts absent, their exact addresses remain named services. Shared graphics541398/541374/channel globals must remain the same aliases as native PAL/image handling. Physical COM has receiver0 and interface argument0; heap pointer arguments retain actual tokens, while local pointer arguments are mask-marked zeroes with writable buffers. Faults1/2/3 are native missing-span/domain/traversal diagnostics, not original successful exits.

`work/test-env/bin/python Tests/compare_scene_display_runtime.py` passes **769 whole unchanged-original calls +4 stopped unsafe prefixes**, **3,638 ordered full snapshots**, **1,699 original-image addresses**. Every callback compares the entire262,144-byte heap,294,912-byte global range, allocation liveness and free history. Meaningful EAX and stack-pop ABI are checked. Profiles cover source flags, signed sizes/depths, positive/negative HRESULTs, parent sticky errors, all readiness pointer combinations, owned/borrowed wrappers, default surface deletion, forward-overlapping descriptor copies, retained queue counts/wrap/readiness and callback mutation of later holder slots or a just-decremented lifetime. Callback mutation of linked next pointers is verified for one safe complete call; intentionally corrupted subsequent list histories are not promoted to valid source domains.

Four allocation-failure comparisons stop before the original unchecked virtual dereferences: first/second/third holder wrapper at4ca7e2/4ca821/4ca85c, and primary188 allocation at4bc8f6. Native failure preserves reached whole heap/events and is not called a safe original error result. The flags1/null second auxiliary successful initializer is separately tested rather than conflated with these prefixes.

`work/test-env/bin/python work/scene-display-agent/checks.py` passes strict C11, warning-clean/pedantic C++17, Swift ABI and **64 exact28/48/52/188/2180-byte ASAN+UBSAN retained startup→holder deletion→manager deletion graphs**. Physical descriptors are explicit640×480 indexed test transport, not measured hardware output; no original asset pixel rendering is claimed by this lifecycle module. All private checks are standalone; no Xcode/device/shared Swift/project files were edited. Remaining physical device/COM/window/descriptor/allocator/diagnostic and specialized queue callbacks remain declared boundaries.

Address-count clarification: the reported address union includes physical test
callback and return-stop addresses. It is a total instrumented-address count,
not original instruction coverage. Whole unchanged-original call counts, full
heap/global/liveness snapshots, ABI and sanitizer evidence are unaffected.
The pinned original executable .text range is401000..50adb5; future reports
separate instrumented text addresses from total instrumented addresses.
