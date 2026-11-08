# Source status-message drawing

`MessageDrawingRuntime` recovers the complete347-byte original v1.0 entry **4226b0**, config-message concatenation and GDI call ordering. Original executable SHA-256: `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. No shared native scene, UI, project, or frozen module is changed.

## Actual source graph

`4226b0` is thiscall(config, signed requestedLines, HDC, RECT pointer, DrawText flags), RET16, meaningful result0/1. It directly calls only CString copy constructor4f6449/destructor4f6584 and imported SelectObject/DrawTextA. List iteration and strcat-style copies are inline; there is no reachable separate font or iteration wrapper to recover. Construction, insertion/removal and timers remain frozen `PlayerStartupRuntime` and `GameFrameServices`.

Config is56bytes: CStringList first7words (head4, tail8, signed countc), auxiliary CString1c, timers20/24/28/2c/30, font34. Nodes are12bytes (next0, previous4, CString data8). The original startup caller at426185 pushes **5000 duration /2000 delay** to4222a0. Its source initializer uses CreateFontA14args `(12,8,0,0,100,0,0,0,1,0,0,0,0,ARIAL5250b0)`, with null-face fallback; it belongs to frozen PlayerStartupRuntime and is only composed in retained tests here.

The exact draw sequence:

1. Return0 for HDC0, signed config.count≤0, or signed `min(requestedLines, count)`≤0. Global text/font/list are not touched by those gates.
2. Clear only the first byte of raw global **534ef8**. Capture the current head pointer and selected count.
3. For each selected iteration, when node is nonnull, capture its next pointer **before** copying its CString. Append its bytes including NUL; append immutable literal5250d8 (`"\n"`) whenever the iteration is before selectedCount−1; destroy the temporary CString. Null nodes still consume iterations. A truncated chain can therefore leave a trailing newline. Callback mutation of head/count/next cannot replace the already captured count/next.
4. Read live config.font34 after strings; if nonzero call **IAT54691c SelectObject(HDC,font)** and save the returned object.
5. Rescan live534ef8 after font selection; call **IAT546d30 DrawTextA(HDC,534ef8,byteLength,RECT,flags)**. Ignore its return, including0/negative failure.
6. Restore a saved **nonzero** font with SelectObject, includingFFFFFFFF; return1. No implicit font reset or GDI success heuristic is added.

Source copies use forward DWORD chunks followed by remainder bytes. The native body preserves this order, including an explicitly adapted overlapping global-text alias profile; replacing it with byte-only copies or a bulk memmove changes that profile. Unwritten global text bytes remain unchanged, and early gates do not clear a previous buffer.

**The routine performs no height, line wrapping, font rasterization, color, or viewport calculation.** It forwards caller RECT and flags to physical GDI. Source46ca50 first advances4224f0 by stage53720c, then builds `(overlay.left, overlay.top+110, overlay.right, overlay.top+174)` with wrapped32-bit additions and calls4226b0 `(1,HDC,localRECT,1)`. Overlay globals are5370c8..5370d7. Source46c2c0 owns DDGetDC/release, color/background setup and overlay dispatch; that remains the frozen frame service/physical transport graph.

## Stable native adapter

Use `claw_message_drawing_entry(0x4226b0,config,args,4,localRect,context,dependency,user,result)`. Arguments are the four actual source words. `args[2]` is a raw RECT token; if0 and `localRect` is supplied, it represents normalized automatic16-byte storage. With0 and no local storage, the original null RECT is forwarded to GDI. No new rectangle, default font, timer, queue, or display state is fabricated.

The root adapter for frozen46ca50's rich4226b0 call passes its arguments and `buffers[0]` RECT when localMask bit2 is set. The public dependency packet deliberately reuses `ClawGameFrameServiceCall` layout (104bytes):

| Service | Raw arguments and payload |
| --- | --- |
|54691c|receiver0, `(HDC,fontToken)`; return prior font token|
|546d30|receiver0, `(HDC,534ef8,length,rectToken-or0,flags)`; local RECT is arg3/mask8/buffer16; current global text bytes are an extra payload after marked buffers|
|4f66cc locked CString storage|receiver0/mask256/local temporary4bytes, raw source-data token argument|
|4f6449/4f6584 when composition disabled|receiver0/mask256/local temporary4bytes, source CString-object token for copy|
|4f6428|cdecl free(headerToken), emitted by frozen destruction|

Marked buffer order is argument order then local receiver; unmarked shared payloads follow. Buffers are synchronous borrowed storage, and GDI can mutate RECT and live global bytes at the source boundary. `DrawTextA` source input is an ANSI byte sequence/byte length. Its Unicode/code-page/font/pixel interpretation remains physical host rendering, not source-proven glyph behavior.

The raw global534ef8 must be addressable through `ClawSceneActorHost`. **Its original declared capacity was not recovered.** `textLimit` is an explicit host safety bound, with0 choosing65536. Root can publish1024bytes with textLimit1024; that is a host guard, not a source capacity claim. No buffer is silently detached or zero-filled beyond the original first-byte store.

CString composition defaults to1. It reuses frozen PlayerDeathServices4f6449 and ActorDestruction4f6584 with an internal automatic local cell; the internal virtual cell token is never published to the parent. Shared empty-data identity is caller-provided (normally52e1c4; original header identity52e1c8 points12bytes earlier). Locked-copy assignment4f66cc/storage and physical allocation remain exact-address services. Optional composition0 exposes full copy/destruction boundaries instead. Frozen CString arithmetic and the original Windows InterlockedIncrement/Decrement adapters are verified in a single-thread oracle; this is not a new concurrency guarantee.

Fault1 missing span,2 text safety bound,3 missing service,4 bad argument shape. Clear fault before each entry. Failed/unsupported calls preserve result unless a completed source result exists. Exact reached-prefix comparisons cover unmapped CString storage, text guard before copying, canceled locked storage/draw services, and missing GDI. Those are distinct from successful original return paths.

## Measured evidence and limits

`Tests/compare_message_drawing_runtime.py` executes unchanged hash-pinned original instructions. It compares complete128KiB heap +192KiB global buffers and16-byte caller-local RECT, ordered normalized service inputs/live buffers and meaningful EAX. The original single-thread Interlocked imports are legitimate numeric transport adapters; source CString bodies are executed for the drawer's normal/locked branches. Retained queue integration keeps its frozen module's CString assignment/copy/destruction transports explicit. Copy-constructor destination locals are output-only; their undefined pre-copy contents are normalized, while source/local input values and post-copy/destructor ownership are retained.

Whole-call coverage includes signed request/count gates, empty/ANSI/newline strings, missing-node asymmetry, font0/ordinary/FFFFFFFF, ignored GDI failures, mutable raw/local RECT, font/text/count mutations, captured-next mutation, locked/shared/refcount-edge CString paths, null RECT, and forward DWORD copy overlap. Twenty retained histories compose actual startup5000/2000ms initialization, queue insertion/replacement, source timer/RemoveHead/FreeNode ownership, and46ca50→4226b0 draw. Both actual checkpoint literals5253a8 (`Your game has been saved`) and5253c4 (cheat rejection) pass replacement→draw→5000ms expiry. Wrapped stage deltas and auxiliary10,000ms timer gates are included. These are finite source-message histories, not a full window/event-loop or gameplay proof.

Final evidence: **488 whole original calls**, **1,146 ordered full snapshots**, **573 distinct original executed instruction addresses**, **20 retained queue histories**, and **5 guarded original prefixes**. Strict C11 passes; C++ ASAN/UBSAN passes15 original-verified replay calls/33 source events; Swift ASAN passes the raw config/CString/global-text/local-RECT/font-restoration ABI smoke. Counts/checks are recorded in `work/message-drawing-agent/verification.json`. Reproduce with:

```
work/test-env/bin/python Tests/compare_message_drawing_runtime.py
work/test-env/bin/python work/message-drawing-agent/run-sanitizers.py
```

The private C++ ASAN/UBSAN replay uses original-verified complete raw state and recorded physical-service mutations; Swift ASAN validates the C11 config/CString/global-text/local-RECT/font-restoration ABI. Real native DD/GDI/font rasterization, disk-save/gameplay initiation, Window DC ownership, and config/font teardown remain caller/physical transports. Root owns their integration and device/build evidence separately.
