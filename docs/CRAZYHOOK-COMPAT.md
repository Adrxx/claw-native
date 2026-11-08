# CrazyHook level compatibility

Plan completed for `plan-crazyhook-compat`, 2026-11-02. Implement every level capability that can run without external Windows plugin code. This document plans implementation; it does not certify that the sampled levels currently play in the native app. The unmodified retail game keeps its behavior. Compatibility changes belong to a custom-level session and must be undone when that session ends.

## Evidence and counting

The local census is `work/crazyhook/features.json`. It contains download URLs, archive hashes, per-map structures and logic counts, script paths and line references, per-feature sample membership, native strategies and task assignments. The 30 downloaded archives are in `work/custom-levels/crazyhook-sample/`; they contain 31 WWD maps because Creep Diving includes a Lite variant. An archive counts once for each feature, including when both variants use it.

Selection deliberately spans 2016-2026 CrazyHook releases, different authors and tilesets, asset-only maps, boss-heavy maps, alternative game modes, and four unmodded controls. There are 26 catalogue-labelled CrazyHook packages and four controls: Creep Diving, Assassin, UnderSeaWorld and Flying Carpet Ride. This is a compatibility sample, not a popularity estimate or a complete census of the site's collection. Off-site-only large packs were not sampled. The [Recluse catalogue](https://captainclaw.net/en/customall.html) supplies the labels and download links.

Counts mean supplied runtime-resource candidates, serialized map properties or lexical references in level scripts. They do not prove that every bundled file or branch executes. Lua comments are removed; both parenthesized and shorthand string/table calls are counted. Editor `.pidstudio` palettes and standalone map screenshots are excluded from runtime counts. Pre2Claw's bundled old `CrazyHook.lua` is counted separately from its level scripts. No downloaded script, DLL or EXE was executed. Every map was decompressed and parsed, with bounds and declared decompressed-size checks.

Research inspected both the [published CrazyHook source](https://github.com/tylkosxd/CrazyHook/tree/8398b0aeae93a1f2ea20f0b571e280b2e339ec1c) at commit `8398b0aeae93a1f2ea20f0b571e280b2e339ec1c` and Lua/modules from the [1.4.5.4 release archive](https://captainclaw.net/dl/CLAW-1.4.5.4.zip). The source identifies itself as 1.4.5.3, so the release takes precedence when they differ. Original bytes, third-party source, documentation and downloaded levels remain under ignored `work/`; none is copied into tracked implementation or this document.

The [release announcements](https://captainclaw.net/en/archive.html) identify dynamic palettes and custom checkpoints in 1.4.5.0, additional APIs in 1.4.5.3, and input changes in 1.4.5.4. The public site points to Discord for the detailed changelog; it was not retrieved. Pejti's [designer guide](https://captainclaw.net/dl/ClawLDG_Pejti.zip), English parts 6 and 7, supplies resource and script examples. Its linked forum thread and an old ReadTheDocs project were unavailable; neither is treated as independently verified documentation.

## What is portable

The DLL used to install CrazyHook into Windows Claw is an implementation mechanism, not a reason to reject the level features it exposes. Likewise, a `.lua` file called a plugin is not automatically Windows-only. The [published plugin loader](https://github.com/tylkosxd/CrazyHook/blob/8398b0aeae93a1f2ea20f0b571e280b2e339ec1c/Lua/Assets/GAME/MODULES/game_plugins.lua) loads Lua modules and invokes callbacks; classification must inspect the required operations.

Use an interpreted Lua 5.1-compatible host with native bindings, per-level environments and the necessary bit operations. The [Lua host API](https://www.lua.org/manual/5.1/manual.html) supports this embedding. Ordinary Lua does not supply LuaJIT's [FFI facility](https://luajit.org/ext_ffi.html); provide typed value and game-service adapters instead of assuming that installing Lua makes the existing scripts work.

There are three distinct cases:

- Plain Lua, object methods, rectangles, flags, timers, resources and game services: implement natively. Preserve arbitrary per-object Lua fields, zero-based game arrays, mutable rectangles/flags, original logic dispatch and callback lifetime.
- Legacy access to a game address, object private state or a known gameplay patch: identify the semantic operation and provide a native adapter. Thirteen sampled packages contain such access; eight construct FFI values, with overlap. Arcana's projectile patch and Aquatis's throw timer are portable gameplay requirements. Do not classify them as external DLL dependencies.
- A required external Windows DLL/native Lua module or arbitrary injected machine code: unsupported execution. Identify the dependency precisely. No sampled level script loads an external library, and no selected archive contains a DLL/EXE. Negative acceptance fixtures must therefore be labelled synthetic, not misreported as real sampled failures.

Unknown semantics remain `not implemented` or `needs investigation`, not `Windows-only`. Preserve a finite operation registry for legacy references; never map numbers to live host pointers or treat an unrecognized operation as a successful no-op. Pure Lua modules and additional portable APIs remain in scope even if this sample has zero usage. Optional multiplayer code must not prevent single-player play; network transport itself is outside this single-player project.

## Resource behavior

A level is its WWD plus its same-stem companion directory, imported together on Mac and through iPad Files/open-in. Reproduce case-insensitive Windows path lookup inside that package. The release's `custom_assets.lua` maps `IMAGES`, `SOUNDS` and `ANIS` through `CUSTOM`, mixed `LEVEL` contents through `LEVEL`, and `TILES` through their tileset names. Respect numeric image-frame ordering, base fallback, name collisions and cross-level overrides. The [asset module](https://github.com/tylkosxd/CrazyHook/blob/8398b0aeae93a1f2ea20f0b571e280b2e339ec1c/Lua/Assets/GAME/MODULES/custom_assets.lua) is the behavior reference; the older guide's simplified tile-prefix description is not sufficient on its own.

Required formats observed in resource folders include PID/BMP images, PCX loading screens, ANI animations, WAV sounds and XMI music. Preserve ANI timing, frame selection and sound events. Map named music and LEVEL/BOSS/POWERUP behavior, including the LEVEL-to-PLAY alias, and restore replaced audio on exit. Check audio offline with all app launches muted. Five packages also contain PNGs inside resource trees; file presence alone does not establish that CrazyHook consumes them. Resolve their references and decoder/fallback behavior in the assets task.

Six packages supply custom splash images. Nineteen supply loading screens. Arcana supplies `MAIN.PAL`, `LIGHT.CLT` and `AVERAGE.CLT`; City in the Depth calls palette APIs. The newer release accepts named CLT files. Support documented MAIN.ACT/MAIN.TXT variants and palette/image color operations even though the selected runtime palettes are PAL/CLT. Do not mistake Midnight Espionage's editor palette for a level palette. No sampled package supplies OGG/MP3 music or a custom movie.

## Scripts, objects and game behavior

Twenty-two packages supply level Lua scripts and serialize `CustomLogic`. Dispatch by the object's name, including recursive directory names separated by colons. Preserve per-script locals, the shared `main.lua` environment, initialization and main/hit/attack/destroy callbacks, map-load hooks, gameplay updates and level-end cleanup. See the [logic loader](https://github.com/tylkosxd/CrazyHook/blob/8398b0aeae93a1f2ea20f0b571e280b2e339ec1c/Lua/Assets/GAME/MODULES/custom_logics.lua). Arcana explicitly requires version 1454; a version number must not falsely advertise implemented semantics during rollout.

Eighteen packages call existing built-in logics from scripts. Pixelcove wraps HermitCrab; Las Almenas adjusts CrumblingPeg, Seagull and SpringBoard. These are useful initial integration examples. The broader object API enables Cat Entertainment Mine's conveyors, timed pegs, falling dynamite and enemies; custom bosses, physics, powerups, camera sequences, HUDs and entirely different game modes follow from the same services. The inventory retains each map's custom-logic names and example object positions, plus each referenced API's sample membership.

The release also supplies helper logics such as its custom-powerup handler and text helpers. Implement their behavior where used, and the native equivalents of supported helper APIs, without redistributing downloaded scripts. Do not confuse the retail pirate enemy named CrazyHook with the mod. `CannonSwitch`, `SkullCannon` and `OneTimeStartSteppingStone` occur in maps but are absent from the published BuiltInLogics table; that omission alone does not make them new mod logics. Resolve their existing original/native registration in the gameplay task.

Legacy patterns include named `LevelBasedData` fields, `PData` aliases, flag structs, game-state arrays, death-sound changes, audio handles, boss-stage coordinates, viewport reads and projectile changes. Keep a per-operation mapping with type, read/write/call behavior and an affected sample check. Pre2Claw's readme requests its bundled core replacement only for old CrazyHook versions; this does not justify executing that replacement or rejecting the level outright.

Four packages implement their own text-file persistence: City in the Depth, Raid on the Spanish Armada, Arcana and Claw Tower. Support their save, achievement, star-map, score and combo files through a level-scoped writable store that accepts the legacy paths. Keep package assets read-only. The release's automatic custom checkpoint system explicitly yields to a level containing `LOGICS/SaveSystem.lua`. Its [save module](https://github.com/tylkosxd/CrazyHook/blob/8398b0aeae93a1f2ea20f0b571e280b2e339ec1c/Lua/Assets/GAME/MODULES/game_csaves/csaves_main.lua), checked against the newer release, guides that join. Sixteen packages contain super checkpoints; add completion/perfect bookkeeping and restore retail profile behavior when leaving the custom level. These per-map saves are separate from the completed `app-custom-checkpoint-snapshot` replay slot and its Command+3 shortcuts. Preserve that feature and slots 1 and 2; coordinate Lua clock/RNG and script file side effects with deterministic replay rather than repurposing the snapshot slot.

## WWD and rendering findings

All 31 maps use a 1524-byte header, header flags 3 and 160-byte plane records. Twenty packages have more than three planes; Autumn has 13. Five packages exceed 10,000 serialized objects; Creep Diving has 25,676 in each variant. These are measured sizes, not evidence for an invented original limit or a CrazyHook-specific raised cap. The [WapMap format definitions](https://github.com/Zax37/WapMap/blob/master/shared/cWWD.h) and [parser](https://github.com/Zax37/WapMap/blob/master/shared/cWWD.cpp) explain the ordinary fields, tile-attribute forms and editor metadata embedded in object names.

Arcana and The Poisonous Caves use type 3 tile masks. Arcana has 16-pixel star planes; full Creep Diving has a 1-pixel background. Nineteen packages use filled tiles. Preserve all planes, z order, wrapping, offsets, parallax, image-set aliases, ordinary object user fields and collision attributes. Arcana also edits tiles during play, including its ladder sequence; tile writes must update collision as well as graphics.

Nine packages contain plane bits outside the documented low five bits, including 0x20, 0x40 and 0x80. The unmodded Creep Diving control contains them too. Their semantics need reference investigation in the planes task; neither blanket rejection as CrazyHook nor blanket stripping is justified. No distinct CrazyHook WWD header or universal new object flag was established. Do not confuse editor metadata or original runtime flags exposed to Lua with a new disk format.

Creep Diving's water behavior, the large Assassin map and the old multi-plane controls prevent attributing every unusual map feature to the mod. They are included in native compatibility checks alongside true CrazyHook additions.

## Measured feature inventory

Each count below is out of 30 archives. Rows overlap. Detailed paths, script line references, per-map counts and native strategies are in `work/crazyhook/features.json`. Zero means not observed in this sample, not impossible in other levels.

| Feature evidence | Archives | Implementation group |
| --- | ---: | --- |
| `images` | 23 | `assets` |
| `lua-scripts` | 22 | `lua` |
| `wwd-customlogic` | 22 | `lua` |
| `sound-files` | 21 | `audio` |
| `sounds` | 21 | `audio` |
| `animation-files` | 20 | `assets` |
| `bmp-files` | 20 | `assets` |
| `more-than-three-planes` | 20 | `planes` |
| `fill-tiles` | 19 | `planes` |
| `level-overrides` | 19 | `assets` |
| `loading-screen` | 19 | `assets` |
| `object-api` | 19 | `gameplay` |
| `pcx-files` | 19 | `assets` |
| `builtin-dispatch` | 18 | `lua` |
| `pid-files` | 18 | `assets` |
| `ffi-or-memory` | 17 | `bindings` |
| `tiles` | 17 | `assets` |
| `audio-api` | 16 | `audio` |
| `music` | 16 | `audio` |
| `super-checkpoint` | 16 | `checkpoints` |
| `xmi-files` | 16 | `audio` |
| `player-physics` | 14 | `gameplay` |
| `ffi-address-access` | 13 | `bindings` |
| `lifecycle-hooks` | 12 | `lua` |
| `animations` | 11 | `assets` |
| `input-api` | 10 | `presentation` |
| `presentation-api` | 10 | `presentation` |
| `camera-api` | 9 | `presentation` |
| `unknown-wwd-header-plane-flags` | 9 | `planes` |
| `ffi-struct-values` | 8 | `lua` |
| `custom-splash` | 6 | `assets` |
| `more-than-10000-objects` | 5 | `planes` |
| `png-files` | 5 | `assets` |
| `script-persistence` | 4 | `persistence` |
| `game-control-api` | 3 | `gameplay` |
| `mask-tile-attributes` | 2 | `planes` |
| `non-64-tiles` | 2 | `planes` |
| `bundled-core-script` | 1 | `lua` |
| `code-patching` | 1 | `bindings` |
| `palette-api` | 1 | `palettes` |
| `palette-files` | 1 | `palettes` |
| `palettes` | 1 | `palettes` |
| `plane-api` | 1 | `planes` |
| `asset-mapping-api` | 0 | `assets` |
| `module-loading` | 0 | `lua` |
| `native-binary-files` | 0 | `diagnostics` |
| `native-library-load` | 0 | `diagnostics` |
| `plugin-request` | 0 | `diagnostics` |

## Implementation order

The queue contains the following ten supportable groups, ordered by descending affected-package count, then the final diagnostics task. Dependencies describe required services; they do not turn an early group's focused acceptance into whole-level certification. Each task creates its matching mode in `scripts/check-crazyhook-compat.py`, retains local evidence, runs only directly affected checks and ends with a fresh Release build. No task changes `Tests/clawparity/`; all are app tasks with `parallel: false` and `exclusive: false`.

| Order | Task | Archives | Representative acceptance |
| ---: | --- | ---: | --- |
| 1 | `app-crazyhook-assets` | 25 | Cannonballin', Heart of the Woods, Murky Valley |
| 2 | `app-crazyhook-lua` | 22 | Pixelcove, Las Almenas, Pre2Claw |
| 3 | `app-crazyhook-audio` | 21 | Las Almenas, Claw's Clone, Christmas Eve Adventure |
| 4 | `app-crazyhook-planes` | 20 | Heart of the Woods, Murky Valley, Creep Diving |
| 5 | `app-crazyhook-gameplay` | 19 | Cat Entertainment Mine, Christmas Eve Adventure, Cultist Island |
| 6 | `app-crazyhook-checkpoints` | 16 | Just Keep Calm, Las Almenas, Arcana v1.3 |
| 7 | `app-crazyhook-bindings` | 13 | Aquatis's Day Out, Puerto Shipyards Battle (8+2+6), Midnight Espionage |
| 8 | `app-crazyhook-presentation` | 12 | ClawoPiano, Get the Coin, Bricks |
| 9 | `app-crazyhook-persistence` | 4 | City in the Depth, Raid on the Spanish Armada, Arcana v1.3 |
| 10 | `app-crazyhook-palettes` | 2 | Arcana v1.3, City in the Depth |
| 11 | `app-crazyhook-diagnostics` | All 30 | Precise failures, Arcana and City in the Depth integration |

The task entries carry the complete implementation scope and acceptance criteria. In particular:

- Start with Cannonballin' image replacement, Pixelcove's Crab1 and Las Almenas's wrappers. These exercise package loading and Lua delegation before complex scripted worlds.
- Use Heart of the Woods and Murky Valley for plane composition, Creep Diving/Assassin for measured scale, and Arcana/The Poisonous Caves for mask collision. Unknown high flags need an explanation grounded in reference behavior.
- Exercise actual scripted interactions, not just successful spawning: Cat Entertainment Mine's pegs/conveyor/projectiles; Aquatis's timer; ClawoPiano's keys and offline notes; Bricks's board; checkpoint and script-save restart paths; and palette restoration.
- Final integration loads Arcana and City in the Depth and records a later scripted interaction in each. Reuse prior focused evidence for the other groups; no full regression-suite run is requested. When completing a map, use the owner-approved MPSCULLY route.

## Precise rejection and acceptance

`app-crazyhook-diagnostics` replaces the blanket “needs CrazyHook” message with the specific requirement shared by Load Custom Level and Files/open-in. For missing assets, name the resource and companion path. For a script problem, name the file, line, object/callback and API or legacy operation. Distinguish malformed data, missing files, portable-but-unimplemented operations and external Windows code. Return safely to the menu and restore all session state after failure.

Static inspection cannot prove all dependencies of arbitrary Lua. Use the package inventory for preflight and guarded native callbacks for dynamically discovered requirements. A required DLL/native module or unknown machine-code operation gets a precise unsupported-execution message. An unrelated bundled executable or optional plugin reference is not enough to reject a playable level. There are no real DLL-dependent positive examples in this corpus, so test that branch with clearly synthetic copies.

Final acceptance requires that every sampled portable operation has an implementation and focused behavioral evidence; reclassifying missing work as DLL-only or returning dummy results is not completion. Planned support, a successful build, a loading screen, real-input play, and owner/device acceptance remain separate claims.

## Sample manifest

The entries below are the actual downloaded archives. Full URLs, checksums and internal filenames are retained locally in the census. Object/plane counts are serialized evidence, not play results.

| Package | Maps | Objects per map | Planes per map | Level Lua files |
| --- | ---: | --- | --- | ---: |
| Puerto Shipyards Battle (8+2+6) | 1 | 5917 | 7 | 1 |
| Cat Entertainment Mine | 1 | 4627 | 3 | 26 |
| Midnight Espionage | 1 | 11031 | 7 | 13 |
| Heart of the Woods | 1 | 4185 | 10 | 0 |
| Las Almenas | 1 | 3509 | 3 | 4 |
| Aquatis's Day Out | 1 | 11396 | 7 | 1 |
| Pixelcove | 1 | 3869 | 3 | 1 |
| City in the Depth | 1 | 5351 | 8 | 85 |
| Arcana v1.3 | 1 | 5909 | 11 | 84 |
| ClawoPiano | 1 | 43 | 3 | 37 |
| The Poisonous Caves | 1 | 12110 | 10 | 23 |
| Christmas Eve Adventure | 1 | 3839 | 4 | 10 |
| Cannonballin' | 1 | 1594 | 3 | 0 |
| Cultist Island | 1 | 5885 | 3 | 19 |
| Autumn v1.2 | 1 | 4575 | 13 | 25 |
| Get the Coin | 1 | 415 | 5 | 13 |
| Invasion of Lumberjacks v2.0 | 1 | 3622 | 6 | 7 |
| Total War | 1 | 16 | 3 | 38 |
| Bricks | 1 | 38 | 4 | 40 |
| Murky Valley | 1 | 2391 | 7 | 0 |
| Claw's Clone | 1 | 4767 | 5 | 2 |
| Raid on the Spanish Armada | 1 | 7483 | 7 | 27 |
| Xmas with Claw | 1 | 2423 | 9 | 15 |
| Claw Tower | 1 | 42 | 3 | 47 |
| Pre2Claw | 1 | 2165 | 4 | 61 |
| Just Keep Calm | 1 | 5706 | 6 | 0 |
| Creep Diving | 2 | 25676, 25676 | 5, 3 | 0 |
| Assassin | 1 | 11651 | 7 | 0 |
| UnderSeaWorld | 1 | 4372 | 2 | 0 |
| Flying Carpet Ride | 1 | 197 | 3 | 0 |

## Reproduce and check this plan

Run from the repository root:

```sh
work/test-env/bin/python work/crazyhook/download_sample.py
work/test-env/bin/python work/crazyhook/inventory.py
work/test-env/bin/python work/crazyhook/build_plan.py
work/test-env/bin/python work/crazyhook/validate_plan.py
```

The downloader reuses the existing selected archives. The scanner never executes their content. `build_plan.py` rebuilds the local feature and task artifacts; it does not change the queue or this document. The validator checks archive hashes, 30-package/31-map coverage, feature counts/evidence membership, task order/dependencies, and the document tables against the live queue. This is a plan consistency check, not a new admission gate. This task changes no app code and runs no app build, gameplay test or regression suite.


## Script text persistence

The native Lua host resolves `Custom/<current map>/...` and backslash paths
inside `ScriptSaves/v1/<WWD SHA256>-<map name SHA256>` below the selected save
directory. Relative names address the same area. Other map prefixes, absolute
paths, traversal, symbolic links and hard links are denied. Each file is bounded
to 1 MiB, with at most 64 open streams and 128 writable files per map. Package
TXT resources are read-only snapshots; root-level files such as Tower's bundled
best scores seed reads until an independent writable overlay exists. Scripts
cannot write into resource subdirectories. No saved text is compiled as Lua.
Automatic CrazyHook checkpoints and the manual app snapshot keep their own paths;
SaveSystem levels retain automatic-checkpoint suppression.

Missing reads return nil, so City and Raid's `LOGICS/SaveSystem.lua` lines 37-45
create two zero-filled records; Arcana's equivalent lines 156-175 creates its
flags and three records. City `Achievements.lua` lines 149-169 and Raid's lines
103-121 likewise create absent achievement files. Tower ships its initial
BestScore/BestCombo/BestFloor text files and reads them with `file:lines()`.
These are observations of the unchanged downloaded scripts, not guessed native
save formats. Malformed input remains data: truncated SaveSystem files reach the
scripts' missing-line parsing errors; nonnumeric fields become nil via tonumber.
The host reports the script error and does not repair, execute or overwrite the
bad file on read. Short nonempty achievement strings use the scripts' own zero
padding for missing bits; empty files may fault on the first nil line. There is
no universal corruption recovery policy in those scripts.

`work/test-env/bin/python scripts/check-crazyhook-compat.py --group persistence`
records its actual acceptance marks and limitations in
`work/crazyhook/checks/persistence.json`, using isolated save directories.

The save adapters also expose the release's named collected-treasure fields and
legacy player array over the same native inventory. The sampled `field_AC` and
`LoadBaseLevDefaults` requests use the existing native level profile initializer;
changes are restored with the Lua session. `RemoveSound`/`RestoreSound` swap the
session sound registry against `GAME_NULL` and restore the original records on
exit. The version value identifies the 1.4.5.4 API dialect; an unavailable service
still raises a precise error. Tower's 50 by 9,999 grid retains the same total-cell
and coordinate bounds as other maps.
