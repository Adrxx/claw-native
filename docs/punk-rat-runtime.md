# Retail PunkRat controller

`PunkRatRuntime` recovers registered PunkRat474330, its CEnemy-derived constructor, specialized state methods, startup and destruction. The pinned original is `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. All Ghidra work used the private project under `work/punk-rat-agent`; logs were checked for script errors. The original instruction oracle changes no recovered function instructions.

The all14-world inventory contains **28 PunkRat records:8 in Level2 and20 in Level8**, none elsewhere. All use LEVEL_PUNKRAT. Their full71-word WWD records, strings, source hashes and image/ANI inventory are in `work/punk-rat-agent/inventory.json`. Both levels contain16 sparse PIDs (FRAME001..014 plus550/560) and HOME,IDLE,RECOIL,STAND,STRIKE,WALK ANI. The test resource transport decodes original ANI records and PID geometry; no substitute animation is used.

| Entry | Whole bytes | Source role |
| --- | --- | --- |
| 474330 |180| Registered cdecl(actor) wrapper |
| 4743f0 |765| Thiscall(actor) constructor |
| 4746f0 |30| Scalar delete(mode) |
| 474710 |108| Destructor |
| 4747e0 |272| Specialized class dispatch(state) |
| 474bc0 |144| Startup and immediate GroundCannon callback |
| 474c50 /474d00 |169 each| Moving left/right update |
| 474db0 |82| Strike update; cannon fire then recoil |
| 474e10 |73| Recoil entry |
| 474e60 |84| Recoil update |
| 474ec0 |10| Hit virtual forwarding death(mode0) |
| 414640 |23| Direct cannon horizontal/vertical fire selector |
| 414660 /414860 |71 each| Direct cannon firing state-entry setters |
| 414a60 |188| Direct cannon mirror/sign conversion |

Private allocation is **0x410=1040 bytes /260 words**, not Rat's padded264-word view and not CHuman. The source base is4332f0, not47c910. The constructor and startup leave private40c unchanged. Compatibility padding in the frozen GenericEnemy264-word model stays local and is not exported into raw private storage.

VT50eee4 contains exactly **43 function words /172 bytes**, ending at slotA8=474e10. The following517120 is data, not another virtual method. `claw_punk_rat_function` exposes only those verified slots. The source class array538458 spans2000..2031 after bootstrap; specialized bindings are MOVINGLEFT2006→474c50, MOVINGRIGHT2007→474d00, STRIKE2003→474db0, RECOIL2031→474e60. Other cells use the CEnemy537638 fallback. Source IDs and allocated CString name identities come from the frozen whole401000 registration profile, never invented state numbers or literal-pointer substitutions.

## Raw API and composition

`Sources/PunkRatRuntime.h` offers `claw_punk_rat_entry(function,receiver,args,count,context,dependency,user,&result)`, private-size and vtable-slot queries. Context88 bytes, globals28 bytes and rich call72 bytes are checked by C11 and Swift. Borrow a live SceneActorHost, GenericEnemyContext and GenericEnemyStatesContext; refresh their actual player, attacker, resource and state views before entry. The actor/common snapshots use the frozen128/93-word compatibility ABI; the actual PunkRat private span remains260 words.

Wrapper474330 is cdecl: receiver0,args{actor},count1. Constructor4743f0 is thiscall: receiverprivate,args{actor},count1. Dispatcher takes one state ID; scalar delete takes one mode. Specialized updates, startup, destructor and direct cannon helpers take no stack argument. **Scheduler4dc870 public ABI is actual cdecl(private)**: receiver0,args{private},count1. Inherited pre404fc0/post4063b0 take one state-name argument. Typed404dd0/404eb0/440e20 and death43f120 take one argument;43e9e0 dedup and most shared state updates take none.

Completion is separate from meaningful EAX: wrapper1, constructor/private delete receiver, specialized updates/fire setters0, scheduler1. Source void incidental EAX is not claimed. Clear context.fault before entry. Missing spans/services yield1, unchecked allocation/composed failures2, invalid ABI/unsupported metadata domain3. Unknown entries return0 unchanged. These diagnostics report partial source execution rather than fabricated success.

The module composes frozen GenericEnemy,GenericEnemyStates,CommonEnemyEntries,ActorWrapperRuntime,ActorResourceBindings,ActorAnimationRuntime and ActorDestruction at actual calls. CommonEnemyEntries uses a temporary compatible pointer view for its CEnemy fields; this does not run a Human constructor or assert a Human allocation. Multiargument common strike/motion helpers outside the exposed shared list remain exact-address dependencies for their frozen owners.

Raw name-array lookup metadata5376b8 is cleared before the frozen Generic scheduler. This bridge validates the ordinary initialized, in-range CString profile (refs<=1,capacity>=0); unusual name-array growth/copy-on-write requires additional source transport and gives fault3. The inherited CEnemy dispatch bridge similarly validates its actual initialized2000..2018 array and clears537658; it rejects inherited growth rather than treating an unbound state as successful deletion. Own PunkRat dispatcher growth/error calls4db6e0/4db5f0/4db4d0 retain their exact rich packets. Parent hosts should supply the actual raw class/name arrays alongside the model projection.

## Constructor and behavior

The wrapper writes primary.state1000 before operator-new4f63ec(410), constructs, invokes private.virtual10, then publishes private at primary+18. States29/30 call virtual20/1c;1000 skips; other states use source scheduler. Null private allocation is unchecked in the source; the native API stops at that prefix with fault2.

Constructor order includes:

- Frozen CEnemy4332f0, VT50eee4 and LEVEL_PUNKRAT image binding.
- Default damage/private2e4=10 only when zero; default actor148=500 only when zero.
- X limits from current physics position minus live original doubles50eec8=30 and50eed0=-15, producing x-30/x+15. Their raw words are00000000/403e0000 and00000000/c02e0000.
- Actor.health10c reset2, then truncating conversion of2×live float5262b4; gravity0 and velocityX60.
- WALK,IDLE,STAND,STRIKE,HOME,RECOIL bindings with GAME_NULL fallback; GAME_EEHH at private404 and GAME_MOUSEKILL at3a4.
- Source43fd60(60), actor.mode2, actual STAND ANI selection/advance, bit1 set, actor.flags40, type4,attackMask3000032, hit rectangle[-20,-40,20,40] and move rectangle[-40,-40,40,40].

WALK uses4061b0 on the actual ANI registry; other getters use4062e0 on embedded wrapper private128. Those frozen wrappers preserve the dictionary's output semantics. Image default selection composes the frozen binder. Resource transports normalize the original stack output-local pointer to the returned raw token and decoded name; stack identity is not claimed.

Movement advances ANI, then polls source rand4a3050 unless global541334 disables it. It uses **signed remainder %100<10**, including negative adapter values, before optional GAME_EEHH playback. Audio gate532c0c and volume532c10 are live. At the relevant bound it enters strike when visualflags2 and powerup534eac/26b7 allow it, otherwise elects the opposite60-speed movement entry. Actual assembly tests x87 **C3 only**, so equality **or unordered NaN** takes the bound branch. The implementation preserves that behavior, not the misleading decompiled `==` alone.

Startup sets depth3800/dirty flag20000, creates GroundCannon522d0c at x+(mirrored?-20:0),y+15,z-1,flags40000, stores it at private408, and immediately invokes its primary+10 cdecl(actor) callback. It then mirrors the actual child private if its own visualflags2 is set. Null child creation is an unchecked source prefix; there is no replacement actor.

At strike ANI completion (done1a4!=0 and loop19c==0), it calls414640(child private), then own virtualA8/recoil entry. The fire selector uses child private70 to choose414660 or414860; setters preserve previous state, resolve LS_FIRING2027 or LS_VERTFIRING2032, select child private4c/50 ANI and zero58. Recoil entry selects private400 ANI and records/resolves LS_RECOIL. At recoil ANI completion it resumes the facing-dependent60-speed movement.

Child mirror414a60 preserves signed32 wrapping, INT_MIN rectangle sentinels, read/store order, visualflags2 and conditional velocity signs. PunkRat destructor destroys the bitset and two CStrings, ending VT50b014; scalar delete optionally frees. **It does not delete or mark private408's GroundCannon**, and preserves both408 and40c. Cleanup43e9b0 delegates the source held-actor alias service48cf50, not automatic child deletion.

## Child and physical boundaries

GroundCannon is a distinct registered family:4493c0 allocates0x7c/31 words,449480 derives from414030,VT50dfd4. Constructor resource names LEVEL_CANNON,LEVEL_CANNON_FIRING and LEVEL_CANNON_HOME were traced. The **whole child wrapper/constructor/update/firing/CannonBall414b20 graph is not ported here**. Its immediate startup is an explicit4493c0 service in these comparisons; the fixture supplies source-compatible actor/private identities and real CANNON ANI. Owned fire setters prove state publication and ANI ordering; they do not substitute physical cannonball output. Source firing updates4146b0/4148b0 remain a concrete refill target.

Other explicit transports include physical scene creation/list ownership, allocation/free, dictionaries, LogicHit/LogicAttack binders, audio4b45f0/4208e0, speech420370, FX461a00, and uncommon generic entries delegated by their exact address/argument packet. No RNG or timestep surrogate exists in this module; rand is injected through the shared source service. The oracle's deterministic scripted values prove call order/signed branches, not whole startup RNG consumption or physical voice output.

## Evidence

Final differential result: **7,850 complete original/native calls,20,358 paired full snapshots,3,338 executed instruction addresses and3 unsafe prefixes**. Every paired snapshot compares all2MiB of raw heap plus520000..54ffff (**2,293,760 bytes**), including parent/child/resource/registry histories. Meaningful EAX and ordered dependency packets compare separately. CPU stack/SEH records, unrelated PE bytes and physical raster/audio output are excluded.

- 90 constructors cover failed resources, health scales, defaults and unsigned clock boundaries.
- 1,080 directed specialized/direct-child method calls cover signed RNG, audio gates,26b7,NaNs/large positions, animation callback mutation, mirrored/sentinel/wrapped rectangles and horizontal/vertical selector.
- All28 actual WWD records run230 retained frames with real Level2/8 cells/descriptors/PID/ANI. They reach strike, cannon fire publication, recoil and movement.
- Each record then runs elected common hit43e9e0, equal-serial dedup, PunkRat hit/death virtual, source terminal delete flag, cleanup and free. Source2 health−25 damage gives−23; repeated serial does not award another hit. The contact election/attacker placement is an explicit fixture, not a claimed full retail scanner replay.
- Actual original4cbb60 and tile helpers execute against both retail worlds; native transport composes frozen CollisionResponse/TileCollision. Other scene actors are absent from the fixture list. Win32 rectangle imports are exact numeric slot adapters; no GDI raster claim.
- Null private allocation, null cannon creation and failed own-array growth with returning diagnostics compare complete reached unsafe prefixes.

The C++ASAN/UBSAN replay passes **18 whole calls/155 complete snapshots** with independently allocated exact260-word PunkRat and31-word cannon blocks and extent checks. Strict C11 passes. SwiftASAN checks the raw ABI and exact260/31-word aliases through strike→fire→recoil and the final unwritten word. Reports, per-asset hashes, corpus and reproducible commands live under the owned worker directory.

```
work/test-env/bin/python Tests/compare_punk_rat_runtime.py
work/test-env/bin/python work/punk-rat-agent/compile_replay.py
clang -std=c11 -Wall -Wextra -Werror -I Sources work/punk-rat-agent/abi.c -o work/punk-rat-agent/abi
swiftc -sanitize=address -import-objc-header Sources/PunkRatRuntime.h -Xcc -I -Xcc Sources work/punk-rat-agent/abi.swift -L work/punk-rat-agent -lPunkRat -Xlinker -rpath -Xlinker "$PWD/work/punk-rat-agent" -o work/punk-rat-agent/swift-abi
work/punk-rat-agent/swift-abi
```

This handoff establishes the bounded PunkRat source graph and explicit child services; it does not establish complete GroundCannon gameplay or whole-game parity.
