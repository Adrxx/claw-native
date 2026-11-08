# GroundCannon source runtime

The new module closes GroundCannon's specialized wrapper/constructor/class dispatch. It composes the frozen GabrielWeapons, PunkRat, GenericEnemy, ANI/image binding, spatial and destruction bodies. No shared source or host files were modified.

The oracle is the unchanged original v1.0 `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. A private Ghidra project copy supplied verified whole entries; its log contains no SCRIPT ERROR.

## Identity and complete specialized graph

| Entry | Verified bytes | Calling convention / role |
|---|---:|---|
|4493c0|177|cdecl(actor), registered GroundCannon callback|
|449480|170|thiscall(actor), private constructor|
|449590|272|thiscall(state), derived class dispatcher|
|42a680|1|literal RET, derived HOME no-op; meaningful EAX unspecified|

Registry ID29/literal522d0c resolves to4493c0. Allocation is exactly0x7c/31words. VT50dfd4 contains exactly nine function words: `484d90,4c9e30,449590,4041b0,4c96b0,4bb030,4bb030,4c96b0,4c96b0`. Following data is not a vtable extension. There is no typed-hit virtual in this nine-slot class.

Derived class537818 overrides LS_HOME with42a680. Its fallback class534bf8 maps retail bootstrap HOME2018→4145f0, FIRING2027→4146b0, VERTFIRING2032→4148b0. These IDs and CString heap-name tokens come from original registry initialization, not inferred strings. `449590` performs the derived lookup twice for a nonzero callback and otherwise delegates4141f0. Registry growth/error/default-cell services preserve raw order and arguments.

This override is consequential: **GroundCannon HOME does not execute the inherited3000ms auto-fire routine**. Init slot16 is4c96b0, a no-op. The startup wrapper first sets primary state1000, allocates/constructs, calls that init, then publishes primary private24. It leaves1000 until an explicit PunkRat firing request. State29 and30 dispatch inherited no-op slots32/28. Other states use actual cdecl4dc870(private). The Ground31 adapter imports only31 private words,109 actor words and93 primary words into the frozen GenericEnemy model, preserving callback mutations at each boundary. It does not send a31-word object through Bullet's84-word model.

Constructor449480 composes actual414030, stores VT50dfd4, binds LEVEL_CANNON (527b14), then looks up LEVEL_CANNON_FIRING (527b00) into private4c and LEVEL_CANNON_HOME (527aec) into48. It rereads actor/scene identities in original order. The inherited constructor establishes actor/primary identities, queued transition fields, offsets, speeds, depth defaults, actor flags1/40 and other exact stores. No-op init does not select HOME ANI automatically.

Private50 (vertical ANI) and54 (sound) remain zero from the inherited constructor; no retail vertical sequence or sound is invented. Request414640 chooses414860 when private70 is nonzero, else414660. Selectors update previous/current state, bind their chosen ANI and clear fire latch58. Actual4146b0/4148b0 animate, elect marker1 once, set58 **before** named creation, initialize the real CannonBall414b20, then set that private's vx/vy and zero acceleration/gravity. Completion invokes4145b0 to select HOME. Shared bodies are entirely delegated to frozen GabrielWeapons; request/mirror bodies previously recovered by PunkRat are not copied into this module.

## Retail inventory and retained evidence

All14 original-disc WWD files were inspected. None contains a placed GroundCannon row. The actual dynamic parents are eight PunkRat rows in Level2 and20 in Level8. Their real WWD profiles drive the source474bc0 startup: parent depth3800, child x+(mirrored?−20:0), y+15, z−1, name522d0c, flags40000. It publishes parent private408, invokes the real4493c0 immediately, and conditionally calls source414a60 to mirror. This parent startup body is the frozen PunkRat implementation, not a translated imitation in GroundCannon.

The resource fixture uses original CANNON and CANNONBALL PID headers/ANI records for each level. Native PID numeric geometry and ANI record decoding use frozen source APIs. Name/frame enumeration is a declared filesystem/dictionary transport; physical rasterization and audio are not asserted. Original REZ provenance remains the frozen disc hash `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.

Every actual parent creates one real CannonBall from the retail firing ANI and returns GroundCannon to HOME after31 controller visits at17ms. The shot then executes whole414b20/shared physics against its actual retail WWD tiles. Thirteen histories collide and complete through whole4c8fc0, actor/primary/private destruction and frees. Fifteen traverse open tiles and complete through whole4d4d10 flag20 out-of-window destruction. The latter use an explicitly stationary camera center at the cannon actor with source default residency extents; this is a valid directed source fixture, not a replay of the original game's physical camera/input stream. No artificial TTL or forced hit was added. Terminal assertion checks cleared actor flags, cleared private publication, raw list/cell ownership and original free order. Source cell/grid construction and insertion are executed independently and compared whole.

Both facings and both shared firing updates are tested. Retail vertical selection remains null and produces no shot. Separately labeled, explicit caller profiles publish the actual retail FIRING sequence into private50 to exercise vertical marker/spawn/velocity behavior; these are not asserted as authored vertical GroundCannon placements. State29/30, HOME silence, unsigned clock endpoints, scalar deleting flags, unknown class fallback and null resource cases are also covered.

GroundCannon stores no parent token and no owned cannonball list. Parent private408 retains the Ground actor across its29/30 controls. Frozen PunkRat destructor evidence independently establishes that parent destruction does not mark/delete that child; this suite does not rerun the entire PunkRat combat/death graph. Physical scene ownership and source flag40/20 residency remain responsible for eventual removal.

## Stable C11 API and host recipe

`ClawGroundCannonContext`, Call and Dependency alias the frozen rich GabrielWeapons ABI. Use `claw_ground_cannon_entry(function,receiver,args,count,context,dependency,user,result)` and `claw_ground_cannon_function(vtable,slot)`. Completion/support is separate from meaningful original EAX. Verified meaningful results are4493c0=1,449480=receiver, and scalar484d90=receiver. Other void/RET entries do not promise their incidental original EAX.

Route the dynamic4493c0 callback and Ground's449590 dispatch through this module. Route actual4dc870 as receiver0,args{private}; the Ground module detects VT50dfd4 and uses its31-word adapter. Keep a valid borrowed Bullet/Generic state registry context for CannonBall startup and every retained callback, including callbacks elected by SceneActorRuntime. Its lifetime must extend through the enclosing call; a temporary context from an earlier standalone invocation is insufficient.

Provide raw actor/primary/private/scene tokens, source class/name arrays and CString heap tokens. Live globals retain the frozen Raux/Gabriel ABI: stage tick537210, animation delta5430c4, manager/player identities5371fc/537e88 and audio gate/volume532c0c/532c10. Resource/ANI operations obey `composeImages`/`composeAnimation`; source factory4c8da0, dictionaries4f6286, LogicHit/LogicAttack bindings, CString data4f6974, registry error/growth and physical sound remain explicit rich services. For a named CannonBall request, preserve its literal/name and six arguments, insert/register the child, execute its callback before applying the creator's launch stores, and attach its controller to the normal scene lifecycle. No fixed timer, HOME auto-fire or substitute vertical ANI is needed.

Fault1 denotes missing raw span/service,2 an unchecked original failure prefix,3 invalid ABI or traversal bound. Failed allocation leaves primary1000 before original44941b dereferences null. Failed named CannonBall creation retains latch58=1 before source41471a/41491a dereferences null. The module diagnoses these prefixes; it does not claim original normal return or rollback.

## Checks and limits

Final differential evidence:5,272 whole original/native calls,5,833 ordered full-buffer event snapshots of4,390,912 bytes,3,467 original instruction addresses,28 retained retail parent/shot histories and three compared unsafe prefixes. The snapshot covers the entire4MiB fixture heap plus the complete original520000..550000 mutable data span. Service snapshots use SHA256 over that entire span; every completed call compares the actual complete byte buffers directly. Allocation cursor, resource arguments, source clocks and meaningful returns are checked. Scene globals are normalized through a dedicated test alias while actual static global spans remain compared.

C11 and Swift header/import checks pass. Strict C++17 `-Wall -Wextra -Werror -ffp-contract=off` passes. The owned ASAN/UBSAN replay passes48 original-matched cases and151 full-buffer service events, with actual31-word Ground,84-word CannonBall and93-word primary allocations. Frozen scene/spatial APIs require128-word actor compatibility views; these tests do not claim that compatibility allocation is the original109-word actor allocation. Exact Ground constructor/FSM imports commit109 actor words and31 private words.

The transport fixture initializes primary-only created actors and leaves LogicHit/LogicAttack resource binding as explicit services. It compares real tile collision but does not elect a live player typed-hit/award interaction. Rendering, physical audio, full original event-loop timing, input/camera election and arena population remain separate integration work. Full whole-game or all-level parity is not established by this family handoff.

Evidence: `work/ground-cannon-agent/verification.json`, `inventory.json`, `entries.c/.log`, `sanitizer.log`, `sanitizer-replay.bin.gz`, and the owned replay/ABI sources. The existing frozen PunkRat and GabrielWeapons files remain untouched.
