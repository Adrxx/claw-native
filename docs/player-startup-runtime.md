# Original saved-player startup and message queue

This additive module recovers the missing first-start save/player bridge and checkpoint message list. It composes the already frozen whole single-player level routine instead of duplicating it. `PlayerStartupRuntime.h/.cpp`, the uniquely named oracle/helpers and `work/world-startup-agent` are the only owned artifacts. Original executable SHA256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

## Entry inventory and source boundaries

| Source entry | ABI / stack arguments | Scope |
| --- | --- | --- |
|415ce0|cdecl(), receiver0|Raw-global marshal into frozen `claw_player_construct_defaults`; whole original resets compared|
|46c790|ECX owner, noargs|Complete18-byte owner reset|
|46d8e0|ECX owner, noargs|Complete579-byte saved checkpoint/player-default/camera binding|
|49af30 /49af90|ECX full player-record, `(level,kind)` /RET8|Complete flag admission and record selection; frozen49ae60 composed|
|46aeb0|ECX owner, `(level,unused)` /RET8|Facade composing frozen2290-byte `SinglePlayerSceneRuntime` whole level entry; new first-start services intercepted|
|42af70|ECX application, `(message)` /RET4|Complete application-config wrapper|
|422370|ECX config, `(message,flagsByte)` /RET8|Complete insert/replace/cap/prepend election|
|4f5249|ECX CStringList, `(blockSize)` /RET4|Complete original7-word CStringList constructor|
|4f5288|ECX CStringList, noargs|Whole clear/destructor traversal and CPlex ownership release|
|4f52f0|ECX CStringList, `(previous,next)` /RET8|Whole CString node creation/pool/free-list/count/empty-data initialization|
|4f5382 /4f53b7|ECX CStringList, `(message)` /RET4|Whole AddHead /AddTail|
|4222a0|ECX config, `(duration,delay)` /RET8|Whole118-byte timer-field/font initialization, including second-font fallback|
|4f5359|ECX CStringList, `(node)` /RET4|Whole node release, destruction and final-empty cleanup|
|4f53eb|ECX CStringList, `(outCStringToken)` /RET4|Whole RemoveHead including two copy constructors and temporary destruction|

No function at422230 is claimed: that address falls within another entry's instruction stream. Ghidra root output and bounded original disassembly are private evidence; MFC demangled names do not substitute for actual source instruction boundaries. The application configuration constructor42614c..42616b is independently checked as an **inlined span**, not a whole425730 application-startup return.

## Defaults and saved binding

Original415ce0 zeros exactly78 DWORDs at534c80. It sets defaults12=1,18=100,28/29=10/5,30/31=3/3,59=1000000; nonzero53725c selects50/40/20/9 at28..31. It sets accumulator53c9f8 from52c6e4 and clears534ea8/534eac/534eb0. Raw values are marshaled through frozen `PlayerInitialization`; actor/private live buffers and physics are untouched by this entry.

46c790 clears exactly60 DWORDs at owner+160..24f. It preserves owner+250 onward and every preceding word.

46d8e0 first reads application=owner+4. A zero application+A8 latch, null selected player-record(application+64) or signed nonpositive owner+14 returns0 without consuming the latch. Otherwise it caches kind(application+D8), clears application+A8 and calls the actual two selectors. Admission/selection failure preserves that consumed latch; it does not roll back or invent a default checkpoint.

49af30 requires signed level>=1 and kind!=3. Kind0 rejects level1 and selects previous-level kind3 through49ae60; other kinds select current level/kind. Nonnull selected record returns its word0 **AND2**, not a normalized1. 49af90 additionally requires signed0<=level<15; kind0 again rejects level1 and uses the previous level's third slot. Thus level15/kind0 can pass flag admission using slot14 but the second selector returns0. Both whole entries preserve frozen49ae60 range and pointer arithmetic rather than normalizing indices.

A selected44-word checkpoint record supplies score(+10), health(+94), four ammo words(+98..a4) and coordinates(+4/+8). The saved flag534ca4 becomes1 when **both raw coordinate words are nonzero**, including negative signed values. The camera/tick/skip-next-super branch separately requires **both signed coordinates positive**. That branch stores owner+44/+48, sets the cached world main plane center, calls frozen4d0a60 clamp, rereads main plane+84/+88, and updates other planes in source array order with the live world main index/count. Camera center calculation uses signed integer→x87 multiply by the single factor→single store; it does not first round the integer to Float before multiplication. Flags bit1 selects direct coordinates. Each clamp is the frozen source body.

Only the positive-camera branch restores tick537210 from record+58 and sets536f00=1. Other paths preserve those globals. The source next-life threshold534d6c is `(signedScore/1000000 + 1)*1000000`, with truncation toward0 and wrapping UInt32 multiplication. It restores exactly **nine** total counters from record+28 into534d30..534d50, and, when savedFlag is true, nine level counters from+6c into534d08..534d28. The tenth counter in each ten-word array remains untouched. Finally it writes owner+160/+164 from record+10/+14 and the saved flag. Records, world pointers and main centers are cached/reloaded at the same observed boundaries, including callback mutations.

## Source caller and RNG composition

Frozen46aeb0 resets its observed globals then calls **srand(111567/0x1b3cf) at46af09**, before resource/world/actor setup. It creates CaptainClaw with `(id1,x320,y350,z100,CaptainClaw522e80,flags40002)`. Only when owner+154 is nonzero does it clear that latch and call415ce0→46c790→46d8e0, before invoking the newly created player's actual primary callback. Reinitialization with the latch clear instead writes534ca4=0. The new facade synchronizes the two globals that overlap frozen scene views: accumulatedTick537210 and word534ca4. Other component aliases remain the host's explicit synchronization responsibility.

The retained whole-level oracle executes the actual unchanged CRT getter/srand body and composes frozen `CRTRandomRuntime` on native side, using one live29-word thread token, seed+14, actual52edd8 TLS index and ordered GetLastError/TlsGetValue/SetLastError services. No private save/startup RNG clone is created. This proves the seed call and shared thread side effects in the scoped caller graph, **not full retail draw ordering**.

The remaining adapted caller boundaries include level cleanup/progress/setup46db30/46f040/46e100/46b7b0/46bb80/46e160; palette/surface/loading display; REZ group/resource/image/animation/audio/music retrieval; world-loader dispatch and its physical input/decompression; registered actor/player/HUD/dialogue creation/controller execution; saved-path/settings/movie/window/cursor services. Root can route already recovered modules for those exact addresses, but this oracle's creation/gameplay/resources are declared fixtures. Their actual resource and gameplay descendants may consume RNG, so no complete retail boot/draw-count identity follows from these16 joined level calls.

## Config, queue and native recipe

The application+4c config is56 bytes. Its first7 words are CStringList: VT510224,+4 head,+8 tail,+c count,+10 free-list,+14 CPlex chain,+18 block size. Nodes are12 bytes: next+0,previous+4,CString data+8. Source shared empty-data cell52e1cc must return the actual shared CString identity.

Actual successful application allocation/construction at42612d..42616b is:

1. Allocate0x38 bytes; do not assume the allocator zeros them.
2. Call4f5249(config,10): stores VT510224, zeroes+c/+10/+8/+4/+14 and sets+18=10; other words preserved.
3. Call4f6439(config+1c): copies the DWORD data identity from52e1cc. Caller zeroes config+30/+34; other tail words remain allocator-owned until initialization.
4. Assign application+4c=config and call4222a0(config,5000,2000).

Whole4222a0 stores duration+24/delay+28, clears+20/+2c/+30, then calls CreateFontA via actual import546918 with `(12,8,0,0,100,0,0,0,1,0,0,0,0,"ARIAL"5250b0)`. It stores+34; only if the first handle is0 does it call the same cached physical function again with face-name0. It returns1 even if both calls return0. Physical font creation remains an explicit transport. The rich callback uses function546918, argumentCount0, bufferCount1, buffers[0] holding the exact14 DWORD arguments, bufferBytes[0]=56; copy the synchronous packet if retaining it.

42af70 reads application+4c and returns0 when null; otherwise422370(config,message,4). 422370 rejects null/empty message before reading list fields. Flags are the source low-byte bits: bit1 rejects **signed** count>7, bit4 clears the complete CStringList, bit2 prepends, otherwise appends. Bits combine in that order, so flags5 can reject before replacing an over-cap list. Successful insertion returns1 and does **not** reset+20/+24/+28/+2c/+30. These timers are governed by frozen4224f0 separately.

Pool construction and CPlex release compose frozen `AmbientAudioBackendRuntime`4f5aa8/4f5ac8. NewNode builds the free-list backward, pops a node, sets links and increments count, then copies4 bytes from52e1cc into the node CString field. That bounded source4f6433 getter/CRT4a4a80 memcpy call is folded into the explicit4-byte load/store; no general memcpy recovery is claimed. CString assignment4f66cc and destruction4f6584 remain exact-address storage services. Clear reads each next pointer **after** its CString destructor callback; it then clears count/free/tail/head, frees the actual CPlex chain and finally clears+14. AddHead/Tail reload current head/tail after assignment.

RemoveHead4f53eb assumes a nonempty source list; it creates a local CString by4f6449(head+8), detaches the head, then4f5359 destroys the node's CString, pushes the node to the free-list and decrements count. The final node release invokes full clear and may free its pool **before** the output copy. The copied temporary owns the string meanwhile. It then constructs the caller's output CString from the temporary and destroys the temporary, returning the output token. Do not replace this with returning the freed node's string pointer or immediately freeing all string data.

Local copy/destructor rich service contract:

- First4f6449: receiver0/localMask256, arg0=node+8; buffer0/4 bytes is the temporary receiver output. Its prior bytes are uninitialized source stack, not an initialized heap object.
- Second4f6449: receiver=caller outCStringToken; arg0=0/localMask1; buffer0/4 bytes is the defined temporary source CString cell.
- Temporary4f6584: receiver0/localMask256,noargs,buffer0/4 bytes is that cell.
- Node4f6584 and assignment4f66cc use ordinary raw receiver tokens/args.

The platform/storage adapter must implement copy-constructor ownership/refcount behavior and exception transport, not CString assignment into an already initialized output. GameFrameServices4224f0 passes an automatic output cell; root adapts that rich local argument to a caller-owned scratch token, routes4f53eb, then destroys the resulting output CString separately. Queue text/layout4226b0, physical fonts/DC/GDI, complete config destruction and exception unwinding are outside this closure and are assigned separately.

## Interface, evidence and limits

`claw_player_startup_defaults` selects frozen cache/camera composition and a native safety bound65536. It does not construct graph objects or seed RNG. Zero composeCache/composeCamera routes exact-address services for callback/alias tests. Return1 identifies a supported entry; callers must also require fault0 for normal completion. Unsupported returns0. Result exposes meaningful returns; source void methods normalize0. Fault1 is missing span/service,2 a frozen numeric domain,3 native argument mismatch,4 bounded traversal; callback faults are preserved. None is an invented normal source failure.

Required host graph: owner478 words, application77, scene15, world56, plane86, full player record2450 words, three-plane table or actual world count, stable aligned raw global spans534c80[78],534ea8[3],53c9f8,52c6e4,53725c,537210,536f00,52e1cc and actual source literal strings. World+38 table,+3c count,+5c main,+60 main index and owner+c scene→scene+24 world must be bound. Keep default globals, checkpoint/frame/actor/audio aliases synchronized with existing views. Frozen full-level facade additionally needs its already documented physical/resource graph; this module does not synthesize one.

Run:

```sh
work/test-env/bin/python Tests/compare_player_startup_runtime.py
work/world-startup-agent/check-smoke.sh
```

Final verification: **3,999 whole original calls, plus12 inlined constructor spans /6,364 ordered complete snapshots /1,659 distinct source-image instruction addresses /7 separately stopped prefixes**. This includes16 retained whole-level calls and1,715 whole message/list/init/dequeue calls.

The oracle compares complete1MiB caller heap and192KiB mutable source image plus ordered callbacks, allocation/free sizes and lifetime, defined temporary CString values, shared thread/RNG/LastError state and actual returns/stack cleanup. Retained defaults→reset→bind→consumed-latch histories, 45-slot cache fixtures with all valid startup selector paths and source-rejected indices, signed/unsigned coordinates, threshold overflow/negative scores, camera wraps/factors, mutable main pointer/count/index, actual14 retail worlds/42 plane metadata profiles and126 start/edge cases are covered. Retail REZ archive hash is guarded; asset decoding/factor capture is an input adapter from the frozen WorldPlane proof, not original-runtime file loading in this test.

Message histories cover constructor, flags/cap order, head/tail/replace, complete pooled ownership, literal save-toast, unchanged timers, font success/first failure/both failure, retained dequeue with copy refcounts and final-empty release. Seven separately stopped prefixes cover null plane, infinite numeric domain, bounded plane loop, allocation0, blockSize0, CString assignment fault and destructor fault. Those do not claim normal completion, source exception cleanup or unsafe-state support. The12 inlined config spans stop at42616b and are not whole application startup comparisons.

Strict C11, Swift import, warning-clean C++ and ASAN/UBSAN smoke pass, including raw defaults, full record/camera binding, exact message replacement/pool ownership, both-font failure and RemoveHead temporary survival after pool free. No frozen sources, shared scripts, Swift integrations, project/bridge files, Xcode, devices or physical save files were modified. This evidence advances source save/checkpoint startup and message orchestration; it does not establish whole-game/native-device acceptance.
