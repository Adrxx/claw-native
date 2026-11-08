# Original display resize methods

`SceneDisplayResizeRuntime.h/.cpp` recovers the whole pinned original v1.0 methods **4d4280 (226 bytes)** and **4d5720 (218 bytes)**. Both are thiscall `(width,height,depth)` with **RET12**. The executable SHA-256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private decompiler logs and disassembly boundary verification are retained under `work/scene-display-resize-agent/`.

The new module owns only these two methods. SceneDisplayRuntime, GraphicsManagerLifecycleRuntime, GameImageRuntime, CArray/list implementations and lifecycle/destructors remain frozen modules. Physical DirectDraw interfaces and allocation/free are named transports, not fabricated native gameplay bodies. No application build, GUI, device, hardware resize or retail startup acceptance is claimed.

## Exact behavior

Both methods first compare stored width+10, height+14 and depth+18. All three equal returns1 immediately, including inadmissible dimensions/depth or an absent backing surface. The source does not repair an unready surface in this branch.

Changed dimensions replace the backing surface **before** checking signed positive width/height and depth membership8/16/24/32. A later failure preserves surface/list/device/error changes already reached and keeps the prior geometry; no rollback or early validation is inserted. Auxiliary ownership latch+30 is preserved, unlike its separate initialization body.

| Method | Changed branch |
| --- | --- |
|4d4280, auxiliary52bytes/VT50e8e4+28|Call4bc4f0(scene+1c,oldSurface), clear+2c. Type+4==1 requests4bcf80(scene+1c,scene+4→holder+10→primary+2c,4). Re-read type after attachment; if no longer1, also request4bc670(manager,width,height,depth,0,FFFFFFFF), replacing the attached pointer without an invented free. Other types use that blank factory directly. Null factory returns0. Admission then stores origin0/0, dimensions, depth and rectangle right/bottom=width/height.|
|4d5720, primary48bytes/VT5138d8+28|Cache scene+1c manager; null returns0 preserving old pointer. Remove old surface and clear+2c. Call4bd1c0(manager,width,height,depth); **HRESULT0** is success, nonzero returns0. Read fresh scene+34 flag2 to elect4bc890(manager,2 or1), retain returned surface, require its virtual+14 readiness, then admit and store geometry. The manager stays cached even if the mode callback changes the scene graph.|

The caller rectangle fields are +1c/+20 origin and +24/+28 right/bottom, stored as source width/height, without an invented inclusive-minus-one conversion. Source write order is preserved: auxiliary clears origin first; primary stores depth first.

## Stable C11 API

```c
uint32_t claw_scene_display_resize_entry(uint32_t function, uint32_t receiver,
    const uint32_t *args, uint32_t count, ClawSceneDisplayResizeContext *context,
    ClawSceneDisplayResizeDependency dependency, void *user,
    uint32_t *originalResult);
```

Context contains a raw frozen SceneActorHost, optional borrowed SceneDisplay/Graphics contexts, operation budget and fault. The caller supplies exact-sized spans and original32-bit token identities. A call is recognized/completed separately from original EAX. Unknown entries return0 and preserve result/fault. Known entries require three arguments and a result pointer. Initialize fault0; faults1/2/3 are missing spans/services, invalid ABI/unsafe prefix and budget limits. Null/missing-graph diagnostics are native safety extensions, with matched original reached prefixes where tested.

The rich dependency is the frozen SceneDisplay call shape: function, receiver, eight argument words/count, localMask, and two synchronous writable buffers. COM receiver is0 and its interface token is argument0. Source-local pointers normalize to0/mask bits; heap pointers retain tokens. Only synchronous use of the buffers is valid.

Supplying `display` composes elected frozen wrappers/factories, removal, surface descriptors and cleanup. Its optional GameImage context composes actual create/describe/color-key/list registration bodies. Supplying `graphics` composes4bd1c0 and source device/mask/error logic; the shared globals pointer must correspond to raw541398/541374 and channel aliases54135c..541370. Optional contexts are copied as views; the resize module preserves their host/context storage while their pointed raw/global state remains live. The root host is responsible for publishing/importing raw alias views at callback boundaries when using an external global representation.

## Evidence

`Tests/compare_scene_display_resize_runtime.py` executes unchanged original instructions and compares complete262,144-byte heap plus196,608-byte writable image aliases, every ordered dependency receiver/argument/local-buffer input and full snapshot, meaningful EAX, and exact SP.

The complete method matrix includes invalid/equal dimensions, signed boundary coordinates, all admitted depths, invalid depths, factory/HRESULT/readiness failures, null primary manager and callback mutations of type or scene flags. Composed histories execute real frozen factories, surface deletion, list removal/insertion, device mode/pixel-mask code, GameImage surface creation/descriptors/color-key, and repeated valid→invalid→valid requests. They include auxiliary attached and blank paths and primary modes1/2. Random uninitialized words remain observable in every fresh profile.

The final suite passes **1,872 whole original calls /5,568 ordered full snapshots**, plus six matched unsafe prefixes. Instrumentation observes1,093 addresses;1,086 fall within pinned PE.text401000..50adb5. These counts describe bounded observed execution, not full body or game coverage. **54 exact-size ASAN/UBSAN replays /258 snapshots**, strict C++/C11, normalized Swift import and Python checks pass. Final counts are retained in `work/scene-display-resize-agent/verification.json`. The six failure-prefix tests cover source malloc failure in each factory and missing old backing surface in each method family. They match original heap/global/callback prefixes at4bd036,4bc6da,4bc8f6 and4bc4fb; the native implementation stops with fault1 instead of claiming a normal original return.

Exact-size ASAN/UBSAN uses primary48, auxiliary52, holder28, scene60, manager2180, surfaces188 and actual pooled/list allocation sizes. Its54 original-paired cases retain the declared physical CRT free storage through each replay; source free order is verified, physical allocator reuse is not claimed. Private `check.sh` reproduces comparisons, corpus, strict C++/C11, normalized Swift import and sanitizer checks.

The physical profile supplies COM SetDisplayMode/GetDisplayMode/CreateSurface/GetAttachedSurface/GetSurfaceDesc/SetColorKey and release results, with complete descriptors/buffers and explicit HRESULT failures. The isolated profile separately adapts source factories and readiness to test method-level boundary mutations. Those profiles are labeled separately and do not establish real DirectDraw availability or a rendered window resize. No codec is elected by these two bodies; PCX codecs remain owned by the separate PCXImageRuntime task.
