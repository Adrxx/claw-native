# Original humanoid strike overloads

`HumanoidStrikeRuntime` adds whole original common methods43ee10 and43eee0 while composing the frozen zero-argument43efe0 entry and shared strike updater43f030. It does not modify HumanEnemy, Officer, Soldier, combat, common entries or their headers. Target: retail v1.0 CLAW.EXE SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Entry boundaries/calling conventions are verified by original disassembly and the existing clean private Ghidra recovery `work/soldier-agent/common-entries.c` (202/250-byte overload bodies); private current disassembly/evidence lives in `work/humanoid-strike-agent`.

## Arguments and original stores

| Entry | Convention / arguments | Stack cleanup | Normal EAX |
| --- | --- | --- | --- |
|43ee10|thiscall enemy, `(sequenceNameToken,rectangleToken)`|RET8|0|
|43eee0|thiscall enemy, `(sequenceNameToken,rectangleToken,soundNameToken)`|RET12|0|
|43efe0|enemy receiver, no arguments; frozen common entry|RET|0|
|43f030|enemy receiver, no arguments; frozen state update|RET|0|

Both overloads write enemy+20=1, capture previous primary state into enemy+24, call4dba00 for LS_STRIKE literal52720c, and then re-read enemy.primary+10 before the state store. They copy the four raw rectangle DWORDs into enemy+220 **in source order**, so overlapping source/destination rectangles see earlier stores. They do not interpret, clamp or elect a target from the rectangle.

The sequence lookup reads the live actor at enemy+12c, its parent+0c, and the parent's sequence registry+2c+10. A zero lookup causes a second lookup for GAME_NULL literal5234b4, with the actor/parent/registry re-read. The result goes to enemy+310. The live actor's old sequence190 is saved to enemy+134, then4c8220 selects the sequence. In43eee0 only, sound lookup happens afterward through the then-live actor.parent+28+10 and stores enemy+3a0, including zero on missing sound.43ee10 preserves the existing sound field. No allocation, held-target global, weapon choice, particle or speech call occurs inside these overloads.

## Shared strike update and exit

The existing GenericEnemyStates43f030 body advances ANI with5430c4. If its result is1 and global52713c strikeCounter is nonzero, it decrements that shared counter, optionally plays enemy.sound3a0 through soundRoot+10 pool when532c0c is enabled, and only then copies the live attack rectangle to actor+138, mirroring left/right when the source actor flag40&2 is set. The sound request is `(audioPosition532c10,0,0,0)`.

Afterward, live stopped1a4 and delay19c gate completion. Completion resets the shared counter to1, calls actual virtual slot44, and writes enemy+20=2 after the exit callback. Officer and Soldier slot44 is44d9f0, whose frozen Human body stops horizontal velocity and transitions to HOME. Full original401000 tables confirm common LS_STRIKE2003→43f030; Human, Officer and Soldier class arrays have zero override and therefore reach this shared update through their actual fallback chain. NameToken is the copied CString heap identity (example fixture30010bc), not literal52720c.

**Root must share52713c across humanoids.** Separate per-component common contexts do not imply independent source counters. Borrow/publish this alias around each source call, as with shared RNG/audio globals. The ordinary Soldier firing path48b880/48ba00 remains its separate frozen projectile graph; it is not replaced by melee strike. These helpers only expose the source attack rectangle; scene election, player hit handling and collision ordering remain the frozen ActorInteractions/PlayerDamage/scene layers. No hit is synthesized here.

## C11 pointer-view ABI

`claw_humanoid_strike_entry(state,context,function,args,count,dependency,user,result)` returns native supported scope separately from original EAX. Argument counts must be exact2/3/0/0. Context points to an existing ClawHumanEnemyContext and SceneActorHost. The actor/primary/common-enemy snapshots and first20 Human tail words are live views; unrelated rectangle/resource spans come from host.lookup. It also recognizes supplied player/other/effect views by identity. Tokens are never truncated host pointers.

Sequence/sound name tokens stay in the exact callback argument list. Optional context.sequenceName/soundName labels let a native registry adapter resolve original tokens without dereferencing nonexistent host executable memory. They are transport labels, not replacements for pointer identities. Existing Root original-resource-name metadata can supply them; missing labels are allowed if the dependency resolves the raw token itself.4dba00 likewise carries literal52720c and the LS_STRIKE label. The original bool/out-pointer4f6286 transport is adapted to a returned resource token.

composeAnimation1 executes the frozen ActorAnimationRuntime over the same current actor snapshots and declared resource tables. Other resource/audio/enum services retain GenericEnemyDependency ABI and full ordered arguments. Zero entry and strike update delegate frozen CommonEnemyEntries/GenericEnemyStates rather than duplicate them. Virtual exit callbacks are caller-routed so actual Human/Officer/Soldier behavior can compose at Root. Those frozen shared bodies assume their constructed actor/primary aliases remain stable; their unrelated polymorphic pointer mutation scope is unchanged. The new overloads themselves preserve tested actor/primary pointer re-reads at service boundaries.

Clear context.fault before entry. Fault1 means missing raw spans/services; fault2 means malformed argument count or propagated animator diagnostic. A supported body may report a fault after its source prefix; inspect fault independently. These are native safety diagnostics, not original normal failure returns. Unsupported entries do not substitute another strike overload or discard extra arguments.

## Verification

Run `work/test-env/bin/python Tests/compare_humanoid_strike_runtime.py`. Strict C++17 `-Wall -Wextra -Werror -ffp-contract=off`, C11 header include and Python syntax checks pass.

Final proof: **2,735 whole original calls /2,614 ordered full snapshots /2,639 original instruction addresses**. Each comparison retains complete actor128, three primary/secondary/contact93 buffers, enemy264 plus actual Officer20/Soldier24 tails, player/other/effect/platform views, bit backing and all relevant clock/powerup/audio/strike globals. The additional393,216-byte rectangle/resource/ANI/guard heap and scene header are compared in full. Full original401000 copied CString heap/class tables remain byte-identical after every call. RET8/RET12 stack cleanup and meaningful zero returns are checked explicitly.

Directed tests cover both overloads, missing/present/fallback ANI and sound, original event argument/name identities, overlapping source rectangles, Human tail views, actor/primary/registry mutations at lookup boundaries, shared counter values0/1/2/80000000/ffffffff, sound order and stopped/delay gates. Three invalid/null-graph cases compare complete prefixes through actual original faults: null rectangle, null primary, and null attached actor. There is no allocator body in these entries; no artificial allocation-success/failure behavior is claimed for them. Constructors/resources used by the retained tests still retain their declared physical allocator/CString/bitset/resource boundaries from the frozen harness.

All42 actual Level1 records (26Officer/16Soldier) run whole original and composed frozen derived constructors with real Level1 tile grounding, then zero-argument strike entry, real retail class STRIKE.ANI updates and actual HOME exit.252 ANI records are separately checked against original4d76e0 decoding. Each isolated history starts with the declared shared counter1 and retains its consumption/reset throughout; this is not a simultaneous42-actor fight or proof of shared alias integration in the Swift host. Resource image ranges match actual class PID frame IDs, but pixels/pool playback/resource enumeration remain transport/platform services. Speech, FX, actual contact election and native UI/device acceptance are outside these bounded proofs.
