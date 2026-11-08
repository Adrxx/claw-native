# Original checkpoint actor and save publication

`Sources/CheckpointLogicRuntime.h/.cpp` is an additive portable recovery of the nine Level1 checkpoint actor records, their contact binders and the bounded save-packet/cache graph. The oracle executes the hash-pinned original `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private decompiles, verified entry boundaries and disassembly are under `work/checkpoint-agent/`; its Ghidra project is a private clone.

## Registered entries and inventory

| Name | Callback | Literal token | Registration flags | Level1 records |
|---|---:|---:|---:|---:|
| Checkpoint | 422ef0 | 52284c | 2 | 7 |
| CheckpointAttack | 422ff0 | 522838 | 2 | bound contact |
| FirstSuperCheckpoint | 4232c0 | 522810 | 2 | 1 |
| SecondSuperCheckpoint | 4232e0 | 5227f8 | 2 | 1 |
| SuperCheckpointAttack | 4231a0 | 5227e0 | 2 | bound contact |
| CheckpointTimer | 491b30 | 522828 | 2 | 0, outside this module |

WWD record339 is `SecondSuperCheckpoint`,342 is `FirstSuperCheckpoint`;405,417,599,634,677,776,815 are `Checkpoint`. The source WWD names are not a generic `SuperCheckpoint` alias. All have z1000 and image indexffffffff. Geometry is taken from all13 retail `GAME/IMAGES/CHECKPOINTFLAG` or `SUPERCHECKPOINT` PID headers. Retail `GAME/ANIS/CHECKPOINT/RISE.ANI` and `WAVE.ANI` supply the retained animation histories, including `GAME_FLAGRISE` and `GAME_FLAGWAVE` sound events.

No checkpoint callback allocates a private actor buffer. Startup owns actor+78 contact binding through frozen `ActorResourceBindings`: the actual allocation is174 bytes/93 words, generic vtable513740. Contact flags initialize0 even though registry flags are2. Primary and actor allocations remain those of the frozen WWD/scene constructor. Contact allocation failure returns normally and startup still sets primary state5; it is not a fabricated deletion. Existing contacts reset callback10, free private14, and call associated18's destructor through vtable slot0. Missing metadata, zero callback, seeded unused fields, cleanup order and mutated metadata/destructor identities are compared.

## Source behavior and exact ABI

`claw_checkpoint_entry` takes a source address, raw receiver, raw arguments, `ClawSceneActorHost`, live globals and an optional rich dependency. Cdecl gameplay callbacks use receiver0 and one actor-token argument. `422ff0` is void; the API's diagnostic result0 is not an original EAX claim. `4232c0/4232e0` publish536efc=1/2 on every call and invoke423060; original EAX inherits its return1. The controller has no checkpoint-specific destructor; state29 is inert and ordinary scene/actor destruction is separately recovered.

Startup sets actor typeD0=800, flags8 OR4, fieldD8=2 and the frame-derived attack rectangle138..144. A super checkpoint additionally subtracts64 from rectangle top13c after binding. It consumes a nonzero536f00 only during state0, clears that global, enters state5 and sets actor Delete10000 without contact allocation. This module does not infer which loading path sets that global.

Contact captures primary6c, publishes sensor x and y-32 into manager2c's fields44/48, selects `GAME_CHECKPOINT_RISE`, ORs actor flags1, sets the captured primary state6, and adds52c6e8 to53c9f8 with32-bit wrapping. Neither ordinary nor super contact increments player private80 or resets pegs directly. There is no local deduplication or player health test. Re-elected contacts repeat the publication and bonus. Election and prevention of repeated contacts belong to the original spatial/interaction scanner, not this module.

States1 and6 advance embedded actor188 ANI with5430c4. State6 selects WAVE and enters1 only when actor1a4 is nonzero and actor19c is zero. Original scene primary20 delay scheduling remains external; this module adds no timer or animation period.

Super contact runs the same prefix before any save gate. It reads owner vtable+10; single-player50c264 resolves verified40af90 (`mov eax,3; ret`), composed directly. Other virtual identities are explicit services. Mode3, an empty managerC0 CString (length at token-8), and the *live* primary callback identity4232c0/4232e0 determine the save branch. Cheating at manager48+128 calls the original refusal-message service. A successful46d620 result calls49bbc0(manager60), success-message42af70(manager), then42abf0(manager). The file writer's return does not gate that message; no physical persistence success is claimed.

## Source save packet and cache

46d620 is thiscall(owner,x,y,checkpointKind), RET12. It rejects owner258, absent player, invalid positive-position kind, owner168 bit1, cheats, absent manager64 cache receiver, or absent player private pointer at6c+14. Positive-position saves use **player x/y**, not the contact sensor's published respawn x/y. Signed x<=0 and y<=0 selects the distinct end-level kind3 branch.

The44-word packet preserves exact source placement:

| Packet words | Meaning |
|---|---|
| 0 | source record flags |
| 1..2 | x/y, or0 for end-level |
| 3..19 |17-word total-treasure score/time/date/counts record |
| 20..36 |17-word current-level record |
| 37 | player actor10c health |
| 38..41 | private70/74/78/7c values |
| 42..43 | remain zero |

49a9d0 writes time into record2, copies ten counts sequentially into7..16 (overlapping copy behavior included), and computes record1 with wrapping32-bit weights `[100,500,1500,2500,5000,7500,10000,15000,25000,0]`. Record0 and6 are preserved. 49aa40 performs one timestamp construction and **three** independent localtime reads, writing month+1, day and year+1900 into3..5. The bounded original wrappers4f504f and the used null-output branch of4f5062 are composed; platform services are CRT4a3b10(time(nullptr)) and4a5c60(localtime(timestamp)). Calendar adapters return a timestamp scalar and a raw tm token, respectively. They must not assume a single shared localtime read.

`composeSaveCache=1` runs the actual cache entries, with no substituted storage policy:

- 49ae60(this,level,kind): signed level0..14, kind1/2/3; returns receiver+2d4/d24/1774+level*176.
- 49a860(this,level,record44,kind): sequential44-word copy, flags `(copiedFlags & ffffff8f) | 2 | (8 << kind)`.
- 49a800(this,level,record17): unsigned higher score wins; on equal score, smaller/equal time wins; sequential17-word copy to receiver+21c4+level*68.
- 49a720(this): resets all45 checkpoint records, preserves only each prior completed bit0, adds its kind flag10/20/40, and clears all15 best-score records. This resets the cache regions, not the complete save-manager constructor or CString/file state.

The cache mutations reach receiver+25c0. Raw manager64 must provide the real cache span; physical commit manager60 is a distinct identity. Fixtures deliberately use one shared transport/cache token and document that choice. End-level owner168-bit1 branch marks an existing kind3 record complete; ordinary positive-position saves reject this bit. 46d620 ignores cache-write returns. End-level saves additionally publish current-level and total best-score records through49a800.

## Host integration and boundaries

Globals follow header order:5371fc manager,537e88 player,5430c4 ANI delta,537210 tick,53c9f8 remaining,52c6e8 bonus,536efc super kind,536f00 one-shot skip; then default534cc8 health/534cf0..534cfc values,534d08[10],534d30[10], and532c10 audio position.52c6e8's pinned initial value is25000; timer HUD initialization/countdown491b30 is not recovered here. Do not infer a native countdown from checkpoint contact alone.

Set `composeAnimation`, `composeContactBinding`, `composeSave`, `composeSaveCache` to1 for the recovered composition. Zero exposes the corresponding exact address as a service for directed tests. The final header has34 global words and four composition flags followed by fault. Calendar/file/cache boundary events include callback-scoped spans. Stack-pointer arguments normalize to0 and `localMask` marks them; timestamp[1] and current full packet[44] or standalone record[17] are exposed for calendar comparison. Physical49bbc0, UI42af70/42abf0, generic polymorphic associated destruction and resource transport remain explicit. With cache composition enabled,49a860/49a800/49ae60 are internal source bodies, not file services.

The frozen binder uses a shadow93-word selected contact. Its identity must stay stable during cleanup callbacks; changing actor78 is rejected with fault3. Polymorphic contact vtables other than513740 are explicitly unsupported. Missing raw spans/services fault1 and unsupported args/profile fault3 are native safety extensions, not original successful-return claims. Frozen ANI rejects reentrant gameplay mutation at its audio boundary. Its audio routing is logged here; physical playback and actual filesystem/calendar/file-write behavior are not proven by these tests.

## Evidence

Run `work/test-env/bin/python Tests/compare_checkpoint_logic_runtime.py`. Final report: **1,952 whole original calls,2,525 ordered full snapshots,1,213 executed original addresses**, comparing all524,288 heap bytes and34 global words, plus complete calendar/save argument payloads and returns/stack cleanup. All9 actual WWD profiles retain startup→elected contact→RISE→WAVE→re-elected contact; real cache reset/save stores are composed.132 separately executed original ANI record decodes verify the transported sequence contents. Direct matrices cover null/failed allocation, absent metadata, zero callback, existing free/destructor order, mutable callback/resource state, super skip, mode/CString/cheat/save gates, timer wrap, score multiply wrap, overlapping copies, all cache selectors, unsigned best-score/tie-time behavior, completion-bit reset, end-level branches, and meaningful missing-identity fault prefixes.

The strict C11 header and strict C++17 compile pass. Private ASAN+UBSAN smoke loads all9 actual WWD/resource heap fixtures and executes cache initialization, startup/contact and80 retained source animation callbacks per record without a sanitizer finding. This is finite original-routine and native memory evidence, not whole-game progression, disk save/reload, native scene contact election or device acceptance.
