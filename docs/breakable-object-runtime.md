# Original breakable-object routines

`Sources/BreakableObjectRuntime.h/.cpp` is an additive raw-token C11 API. It implements the finite original routines below from the unmodified v1.0 `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The disassembly and private Ghidra project are under `work/breakable-agent/`. No reference gameplay implementation, CrazyHook table or inferred crate contents were used.

This is a bounded breakable layer, not proof of a complete game or of every inherited enemy controller. The same declared shared/resource/scene/graphics/audio service results are supplied to original machine code and native code. Their ordering and the complete surrounding state are compared. An adapted callback is not counted as recovery of its implementation.

## Stable host contract

`claw_breakable_entry(function,receiver,args,count,context,dependency,user,result)` returns native support/completion separately from original meaningful EAX. Cdecl actor callbacks have receiver0 and actor as one stack argument. Thiscall methods use the raw object token as receiver. All pointers in raw storage are 32-bit tokens; no native pointer truncation.

Context owns the frozen `ClawSceneActorHost`, a breakable-global view and a frozen `ClawWorldLootGlobals` pointer. The dependency call has twelve arguments, optional human-readable literal name, and UInt64 return (these recovered calls use low32 scalar results). `4f6286` resolves metadata: its original output-pointer transport is represented by the returned token, so the logical adapter argument list contains only the original name token. Other resource/factory arguments retain actual source identities/order.

The host must provide correctly sized raw actor128/common logic93 storage and private allocations:

| Family | Allocation | Vtable |
| --- | ---: | --- |
| PowderKeg | `0x410` bytes / 260 words | `0x50edd4` |
| Spawned Crate | `0x418` / 262 words | `0x50c77c` |
| Stacked parent | `0x4c` / 19 words | front `0x50f824`, back `0x50f84c` |

The frozen generic API has a portable264-word buffer. A raw bridge copies only the actual260/262 words into and out of these objects, preserving the frozen API's unused portable tail. Constructor stores do not clear an original allocation's seed wholesale: PowderKeg+40c and Crate+414 remain unwritten by the subclass constructor.

Global correspondence:

- animationDelta5430c4, audioEnabled532c0c, audioPosition532c10, crateImageChoice52a194.
- damageScale5262b0 and healthScale5262b4 are Float32; original arithmetic uses x87 configured to53-bit precision before original FTOL low32 conversion. No minimum-health clamp is added.
- `kegStates[10]` is raw537ea0..537ec7; `crateStates[10]` is537308..53732f. They include the nine-word range object plus a preserved following word. Backing pointers and actual function identities must come from the recovered `LogicStateRegistry`, which already includes both classes. Do not assign state IDs from test numbers.
- `loot` is the real frozen341-word537ec8 table plus itemCount52a190/highLaunch53721c. Successful ordinary initialization has62 records. The source loader/resource adapter remains responsible for actual image/logic/sound identities.

## Entry inventory and source behavior

| Complete entry | Actual ABI / purpose |
| --- | --- |
|46f1e0,433070,48d560,48d620|cdecl(actor); PowderKeg/Crate/front-stack/back-stack wrapper |
|46f2a0,433130|thiscall(actor); specific constructors after the identified shared4332f0 call |
|48d6e0|thiscall(actor,defaultZ); complete stacked constructor/creation loop |
|48de40|thiscall(childActor); stacked child's inherited payload/reset |
|471720,471750,471530|cdecl(actor); front/behind/single controller |
|4717e0|cdecl(actor); registered single CrateHit |
|46f6a0,433ad0|thiscall(state); override table lookup then shared dispatch |
|46fc60,434050|thiscall(); keg/spawned-crate hit overrides |
|46fc90|thiscall(damageReason); keg-specific reason2 explosion, otherwise shared hurt |
|46fbe0,46fc20,46fa90|thiscall(); keg dropped transition, thrown/dropped update, explosion update |
|433ed0,433f30,433f70,433fb0|thiscall(); unlink/damage transition, damage animation, fall start(arg), fall update |
|434170,434180|thiscall(); actual tail dispatch to slotsb0/ac |
|46f5d0,433a00,46f5b0,4339e0|thiscall(); private cleanup/deleting cleanup (deleting argument uses low byte) |
|473610|cdecl(itemID); actual signed image-root getter |
|40f450|cdecl(scene,itemID,x,y,z,vx,vy); whole BouncingGoodie launch helper |
|4735b0|cdecl(scene,x,y,z,itemID); initialize loot if needed, clamp negative item to0, validate and launch |
|40f540|cdecl(sourceActor,x,y,z); nine-slot item collection, filtering and launches |

Wrappers set primary state1000 before allocation, invoke private vslot10 before storing primary+18, dispatch states29/30 through vslots20/1c, leave1000 idle, and otherwise call **cdecl4dc870(private)**. Allocation failure does not silently create a replacement object.

Single front/behind callbacks write image-choice5/4 and primary+64=1 before the common controller. State0 selects the manager's minimum image, sets actor type200/mask3000072, binds CrateHit, derives the inclusive image rectangle, chooses default Z5000(front) or1100(other) only if Z0, and sets health to1/2 unless signed health>998. The source state becomes5. State5 subtracts animationDelta from the unsigned cooldown with saturation0 then animates; state31 animates and goes10 at stopped/currentRecord0; state10 goes5 and conditionally marks deletion using primary+64.

CrateHit marks attacker flag10000 for type20 even if the cooldown rejects damage. With cooldown0 it decrements health. A nonfatal hit chooses damage sound, advances/wraps the original image pointer and stores cooldown500. A fatal hit selects `LEVEL_CRATEBREAK`, actor flag4/state31, then creates loot before random break-audio selection. The source does not put a guessed treasure count into the callback.

The stacked constructor sets the parent actor flag1/render flag1, spawns1–9 `Crate` actors at original z+1+ordinal and y−40*ordinal, and fills their actual content field. Actor+100 is the first slot, falling back to primary+f0; f0 is added again only when actor+100 is nonzero. Remaining f4..10c nonzero fields are additional slots. Content32 copies source actor148/14c and sets childFC26ae. Child primaryf0..10c are cleared before invoking its callback. After initialization each child private404 points to its lower predecessor, predecessor400 points upward, child408 stores ordinal and child40c stores parent Y. The final upper pointer is0; parent is marked10000. Creating a child is not an optional guessed behavior.

The spawned crate fall update sets the next upper child's minimumY to own physicalY−40, grounds the lowest child's minimumY at private40c, and tests **exact Double equality**. At equality velocityY>200 multiplies by−0.5; otherwise it zeros velocityY, stops physics and clears actor flag2. It does not use a tolerance or a generic host bounce. Its hit handler restores the actual break ANI, marks flags4/2, calls vslota8 unlink, deletes type20 attacker, drops the private loot inventory, then chooses break audio.

The keg constructor binds `LEVEL_POWDERKEG`, resolves lifted/lifted2/thrown/explode ANI with actual GAME_NULL fallbacks, resolves LEVEL_KEGBOOM, sets the literal movement/attack/hit/carry rectangles and damage20×scale, sets bit0, actor type4/mask1000020, flags40 and actor164 bits1/4, moves actorY−32 and calls **4cd800(map,actor,0)**. The zero is pushed early at46f4f1 and actor later at46f55d; the original callee RET8 is preserved in the dependency ABI. State becomes named LS_IDLE.

Keg hit sets flag4, marks type20 attacker for deletion, then invokes shared explosion slot7c (`43ffa0`). That frozen source body changes type1000000, flag2/4 and164 bit2000, chooses LS_EXPLODING/ANI and audio. The private oracle actually composes the frozen native body while executing the original shared instructions. The keg explosion update sets flag80; only when animation returns1 and private1a0 is0 does it mark that word1, call **486e70(500)**, derive the current image's inclusive attack rectangle and apply the source horizontal mirror negation. It then clears flag80. Stopped/currentRecord0 marks deletion. **486e70(500) remains an identified FX/global service, not a claimed fuse duration, sleep or radius.** No separate keg-specific countdown was observed; inherited lift/throw/other controller clocks are not claimed recovered by this module.

## Hit election and unresolved bodies

Original registered LogicHit4dc830 takes actor cdecl, resolves actor6c→primary18 and calls private vslot14:46fc60(keg) or434050(spawned crate). Single crates bind4717e0 directly. LogicAttack4dc850 similarly calls slot18; stack parent slot14/18 is the source no-op. `ActorInteractions` already owns the complete mask/flag/inclusive-rectangle election and actor74/7c stores. Calling a breakable handler directly does not prove that a real pair was elected in every scene profile; this suite does not replace that engine or add collision gates.

Dependencies remain explicit: generic4332f0 constructor,4dc870 FSM,43d490 fallback, shared43f120 hurt, shared vslots/init/pre/post/movement, resource/image/animation bind/update, scene4c8da0 transport, WorldLoot42df90/4719e0, random TLS, audio, bitset grow/delete and CString release. Cleanup recovers actual vtable stores and exact bitset→CString1a8→CString1a4→base-vtable→optional-free ordering; physical/shared destructor bodies can compose frozen ActorDestruction.

Shared inherited lift/throw helpers440120/440420/4407d0/4409d0/440410 are traced in private `shared-keg-helpers.c` but remain unsupported here. They need an additive follow-up, not a guessed implementation. The three subclass override tables and constructors do not cover every inherited state body.

State lookup supports both in-range and successful actual range-growth service effects, including re-reading mutated descriptors between repeated lookups. A failed4db6e0 reaches original diagnostics/default-cell logic; that path is a declared native fault2 boundary rather than fabricated diagnostic/default callback success. Invalid native ABI/count, missing spans/services, and loot indices beyond supplied341 words similarly reject. Original valid source profiles and stopped invalid-dereference prefixes are reported separately.

## Verification

Run `work/test-env/bin/python Tests/compare_breakable_object_runtime.py` from the repo. The helper builds only a private dynamic library, checks the original EXE hash, executes original instructions in Unicorn and compares full384KiB token heaps, full192KiB original image/global spans and every ordered service snapshot. Mutable allocation/create state and meaningful EAX are compared; incidental void EAX is excluded. The only platform rectangle adapter is exact SetRect writes; original instructions are otherwise executed for the owned routines. Full shared base bodies are not replaced by guessed native implementations: the main oracle declares the4332f0/shared-controller service seam, and joined explosion separately composes the frozen shared43ffa0 body.

Level1 evidence includes all58 PowderKeg and56 crate-family WWD records (22 stacked parents,34 single crates), extracted read-only from the archive pinned to SHA256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596` and fed through frozen WorldObjectRuntime. Record hashes, actual payloads and spawn counts are in private `level1-inventory.json`. Asset-archive identity is separate from v1.0 executable identity; no original CD version equivalence is claimed.

Final differential result: **5,521 complete original calls, 16,013 ordered snapshots, 2,258 original instruction addresses and five stopped failure prefixes.** Private `verification.json` records exact totals/instruction addresses. Directed coverage includes signed/unsigned health/Z/clock boundaries, all states, null/missing image/resource/sound, signed random branches, inline/backing/growing bitsets, scale NaN/infinity/large values, range growth, stack1–9 children and link changes, retained keg and crate histories, and every62-item metadata/getter/launch profile plus four unused62..65 index rejections. Five failure-prefix comparisons stop at the first original invalid dereference for null private allocation or stacked child creation. Their native fault result is not an original successful return.

C11 syntax, Swift Clang-module import, warning-clean C++17 and private ASAN+UBSAN smoke are independent headless checks. No Xcode/UI/device tests were performed by this worker.
