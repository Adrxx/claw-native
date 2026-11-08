# Original player lifting and throwing

`LiftThrowRuntime.h/.cpp` provides a raw-token host for the missing player lift/throw bodies and composes the previously frozen inherited enemy bodies. It preserves original state/bitset/physics/rectangle/animation ordering. It introduces no fuse, bounce, proximity, duration, or controller rule.

The source executable SHA256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra projects/logs are under `work/lift-throw-agent/`; the player, cleanup and resize logs were inspected and contain no SCRIPT ERROR. Complete verified new boundaries are 41dc50 (298 bytes), 41a850 (2449), 41b1f0 (138), 41b280 (941), 421010 (21), 420fc0 (66), 4dbd20 (64), 4207a0 (8), and 4dc6d0 (211). The independently observed 420b60 single-axis physics body is already covered by frozen EnemyMotionAux; it is not duplicated.

## Entry inventory and composition

| Function | ABI | Implementation |
|---|---|---|
| 41dc50 | cdecl(actor,primary,private,target) | Whole new lift entry |
| 41a850 | cdecl(actor,primary,private) | Whole new player logic5000 update |
| 41b1f0 | cdecl(actor,primary,private) | Whole new throw entry |
| 41b280 | cdecl(actor,primary,private) | Whole new player logic5001 update |
| 41c4e0 | cdecl(actor,primary,private) | Exact armed and unarmed movement cleanup over live raw fields |
| 4171d0 | cdecl(actor,primary,private) | Frozen PlayerLocomotion standing entry with live commits/reloads |
| 41d850 | cdecl(actor,primary,private) | Frozen PlayerAttackInput selector, now composing the real lift entry |
| 421010 | thiscall(private,callback,minimumStatus) | Whole callback setter |
| 420fc0 | thiscall(bitset,index) | Whole bit setter |
| 4dbd20 | thiscall(bitset,index) | Whole resize-then-set wrapper |
| 4dc6d0 | thiscall(bitset,newBitCount) | Whole backing growth body, explicit physical allocator/handler calls |
| 4207a0 | thiscall(private) | Original tail dispatch to the actual vtable slot94 |
| 440120/440420/4407d0/4409d0/440410 | thiscall(private) | Frozen EnemyMotionAux throw/lift/flail/drop/marker |
| 440350/440710 | thiscall(private) | Frozen EnemyMotionAux release callbacks |
| 440260/4405b0/440870/440a50 | thiscall(private) | Frozen GenericEnemyStates through EnemyMotionAux |
| 440b20/440c90/404e00 | thiscall(private), argument only for404e00 | Frozen CommonEnemyEntries block/strength methods |

No frozen sources are edited. Inherited calls use a GenericEnemy/Human pointer view over live raw buffers; a deliberately unused Human tail satisfies the frozen common entry API for the supported methods, which never read it. Only the represented common words are committed. Actual Human-specific throw wrappers and private-tail writes remain their owning module's responsibility.

## Player entry and state order

Lift41dc50 first stores primary1c=5000. Target164 bit4 chooses CLAW_DUCKLIFT524888 versus CLAW_LIFT52487c, selected without an eager update. It sets player mode1, clears movement velocities148/14c and private8/c, stores target actor at private12c, writes timer100000 and charge0. A nonempty target bitset XORs bit0, including actual backing for counts>32. Target owner depth becomes player depth+1 with flag20000 only when changed. The actual target-private vtable88 then runs. Finally the player movement rectangle is saved at private d8..e4, its top is reduced25, and the complete player physics remainders are zeroed.

Player and enemy offsets12c have distinct meanings: player-private12c holds the target actor; enemy-private12c is the embedded bound actor identity. These bodies do not write the separate global holder53c9ac/held53c9b0 aliases. No global binding is invented.

Logic5000 captures player x/y before input processing. Once private8 is set, held left/right select lift walking at ±30 and update facing/idle timer with original precedence. Animation return1 skips physics; otherwise the frozen whole physics body advances using **stage** delta and exact pixel-X conversion. Platform movement is read from actual platform158/15c, then 4cbb60(world,actor,x,y,24) resolves movement.

On support, completed lift animation or stopped carrying selects CLAW_LIFT2 and enables private8/c. Pressed22 requests throw after restoring the saved movement rectangle. The same update still processes its timeout afterward: animation delta decreases privatef0 while smaller; expiry installs callback4207a0, marks target bit0, clears private12c, restores the rectangle and enters source standing. This ordering is preserved even when throw was requested in that update.

Falling while carrying installs target callback4207a0 only for signed-positive target status20. Its horizontal physics velocity becomes +225/-225/0 from the current player velocity sign; bit0 is marked, the held pointer clears and the player rectangle restores. Source fall25 entry selects or queues CLAW_FALL according to private3c, writes mode4, clears movement/platform flag10, restores hit/movement rectangles, clears private40, and sets player velocityY0/accelerationY2250. Armed cleanup is now real raw field/bitset logic rather than the earlier disabled weapon service.

Throw41b1f0 stores logic5001, selects CLAW_THROW524774 without eager animation, clears movement, and chooses image44 when the image manager's signed range includes it; a present root still stores ID44 even when its image token is missing. It invokes actual target-private virtuala0 (held marker for the common/keg profile).

Logic5001 applies platform offsets and facing, then resolves movement. Falling clears the held pointer and enters source fall using the original dictionary lookup path. Otherwise **held**22 increases unsigned privatef4 by animation delta while charge<3000 and returns before animation. On release or threshold, animation return1 with a held object marks bit0, invokes actual virtual80 with wrapped `(charge*100)/3000`, invokes virtual84, clears the pointer, then looks up/plays CLAW_GRUNTTHROW unless the sound registry is disabled. Completed throw animation clears the pointer and performs the original inline standing reset. Pressed and held masks are not interchanged.

## Inherited enemy and keg behavior

The frozen inherited throw computes signed32 velocities from strength1ac: normal X magnitude `weight*3+200`, Y `-600-weight*2`; strong throw537224 uses `(weight+2)*100` and `-600-weight*20`. Arithmetic wraps before conversion to double; private facing determines X sign. Strong-throw input is read after resource/registry services, and live callbacks can change it. Lift's Y-1 single-axis retargeting, stopped/remainder/default bound stores, saved rectangles, release restoration and mirrored flailing offsets retain their frozen original ordering.

Generic dropped4409d0 has its original1000-tick controller fields. **PowderKeg virtual94 is46fbe0**, which has different source semantics and is forwarded to frozen BreakableObjectRuntime by the host. It does not inherit an invented generic fuse/countdown. The private oracle observes the whole original46fbe0 body while the native host composes its frozen counterpart. Root must route keg-specific methods/states to their actual identities, including the existing breakable landing/explosion graph.

## Bitset growth and failure behavior

421010 stores callback14 iff signed minimumStatus<=status20. 420fc0 ORs the indexed bit using unsigned count/index rules, invoking4dbd20 only when count<=index. 4dbd20 requests4dc6d0(index+1) and, on success, chooses inline/backing from the resulting count before setting the bit.

Resize4dc6d0 computes rounded word count from the requested bits. Old counts<=32 call physical malloc4a48e0, zero the returned words, and copy the old inline word. Larger counts call realloc4a9070 and zero the suffix using the original floor(oldCount/32) and wrapping count arithmetic. Successful growth stores the returned pointer and rounded bit count.

The original small-growth quirk is preserved: it allocates/stores a pointer even when rounded count remains32, after which the setter treats the pointer word as inline bits. No ownership repair or implicit conversion is introduced. Valid original constructed enemies start with32 bits, so ordinary bit0 marking avoids this path.

Failure is also unusual:4dc6d0 repurposes EBP as wordCount, then4dc680 reads raw address `wordCount+4`. Native code assembles that unaligned read through aligned host word spans, writes shared core.words[0] at544b14, then calls4db4d0(handler,[bitset,message544b4c,12]). Core.errorLocation is **not** used for this body. Without a supplied readable low virtual page, the native guard reports fault1; original execution can fault before diagnostic stores. The fixture's mapped-zero low page is declared explicitly and is not asserted to exist in retail startup. Shrinking below the old floor word count can underflow a huge zeroing loop; native traversal/domain bounds report fault2 rather than claiming parity for that malformed path.

## Host ABI and aliases

`ClawLiftThrowContext` borrows a SceneActorHost, shared globals, complete player physics, optional existing attack context, and optional existing core globals. Clear fault before entry. Raw32-bit tokens remain identities. Native support/completion and meaningful original EAX are separate; void player updates/cleanup/setters do not claim incidental EAX. Original standing returns private facing; selector returns its original result; inherited methods return0. Unknown entries preserve output/state; wrong arity is fault2; missing spans/services fault1.

Globals mirror player537e88, input pointer537204, stage53720c, animation5430c4, absolute tick537210, powerup534eac, pixel scratch544e8c, audio532c0c, overall volume532c10, strong throw537224 and physics defaults513e10..513e6f. Physics is the live534db8 object. Enemy raw word count is at least260; keg260 and Rat264 are valid. The supported inherited profile requires owner actor+c equal embedded actor+12c; unsupported alias graphs are an explicit native fault2. Larger private tails stay untouched.

`composeAnimation=1` composes frozen ActorAnimationRuntime over live root/sequence/record/image spans. With0, exact animation calls are dependencies. The selector requires `context.attack`; its pressed mask refreshes from raw input+4. Difficulty53725c, damage100537218 and damage0 537228 remain the caller's existing attack-context aliases. Target query41d750 emits receiver0 plus actor/primary/private arguments; return is the signed distance bits, and the host fills attack.targetToken/targetActor through that declared output adapter. Root can use its already frozen nearest-target implementation. Target-query transport is not silently treated as an empty world.

Rich dependencies carry function/receiver/all12 arguments/optional name and uint64 returns. Resource/dictionary transport, RNG, speech, audio, movement collision, placement, physical malloc/realloc and diagnostic handler remain explicit. Keg-specific virtual overrides stay explicit services that can compose frozen BreakableObjectRuntime. Native commits/reloads actor/private/logic/physics and target views at every composed dependency boundary, including nested inherited callbacks.

## Evidence

Run `work/test-env/bin/python Tests/compare_lift_throw_runtime.py`, followed by `work/lift-throw-agent/run-sanitizers.sh`. The private verification JSON/log and replay corpus record instruction identities, counts and services.

The suite passes3042 whole entry/helper/selector calls,58 whole derived PowderKeg constructor calls,6067 ordered full snapshots, and2984 original instruction addresses excluding observed/adapted service entries. Each main comparison checks a complete262144-byte heap and196608-byte mutable global image, ordered function/receiver/argument snapshots and meaningful results. All58 actual Level1 PowderKeg records reconstruct their exact sized strings/raw hash, then retain input→lift→carry→charge→throw→flight/release histories. Signed/wrapped strength, simultaneous directional input, separate stage/animation clocks, complete physics bounds, status thresholds, inline/allocated bits, allocator outcomes and timeout/fall paths are directed checks. Two unsafe original pointer/failure prefixes compare separately from completed bodies.

Derived constructor comparisons use the frozen generic constructor and complete bindings as an explicitly source-backed service at4332f0. That body has independent prior original comparisons; this suite does **not** count substituting that service as a new whole-binary proof of4332f0. Resource/image/geometry and4cd800 ground placement remain declared constructor services. The58 profiles are actual WWD data under this bounded caller graph, not full retail creation or ground-placement proof.

Eight additional histories use disc-identical ANIS/LIFT.ANI, decoded16 times through the actual original record decoder and frozen native decoder. They exercise the real raw animation bridge for96 retained ticks. Indexed image identities are a declared resource-table profile; pixel/resource enumeration equality is not claimed. The initial sanitizer corpus replays127 source-verified raw histories with ordered recorded service effects, including actual ANI composition; physical service bodies are not executed by that replay. C11/C++ warnings and source-boundary checks are separate validation. Full scene scheduling415df0, player epilogue, retail startup, humanoid-specific throw wrappers, all external resource/lifecycle bodies and full-game equivalence remain outside this bounded handoff.
