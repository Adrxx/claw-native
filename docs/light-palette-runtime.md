# Original light-palette startup and tables

`LightPaletteRuntime` recovers the finite original `46e160` startup and the CLT, light, average, and palette-rank table builders. It composes the already recovered table allocation, nearest-color, pointer-array, and cleanup bodies in `PlayerFadeBlendRuntime`; those frozen implementations are not duplicated. This is source palette data and orchestration recovery. DirectDraw palette installation and rendering the tables through a physical graphics backend remain separate integration work.

The oracle is the unmodified v1.0 `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Format fixtures come from `Original/claw-disc/files/DATA/CLAW.REZ`, SHA-256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Their retail asset identity against the original v1.0 installation is a separate question. No reference gameplay implementation is used.

## Raw graph and integration recipe

All offsets below are hexadecimal byte offsets. The caller supplies a `ClawSceneActorHost` lookup over live token-backed raw words, allocation/free services, and globals. Call `claw_light_palette_defaults` on a zero-initialized context. The context's `temporaryFileToken` must address ten caller-owned words (40 bytes) when invoking the whole CLT decoder/load/startup path. It represents the original stack-local `CMemFile`, without an original heap-identity claim. Rich dependencies are synchronous; `localMask & 1` denotes that local receiver, normalized to receiver zero with its complete ten-word buffer in `buffers[0]`. Heap output arguments retain their live tokens.

| Object | Span and source fields |
| --- | --- |
| Single-player owner | 478 words / `0x778` bytes; `+4` application, `+1c` resource manager, `+360` inline 256 four-byte palette entries, `+768/+76c/+770` light/average/rank table object tokens |
| Application | Existing application object; `+78` bit depth, `+58` six-word palette manager token |
| Palette manager | 6 words / 24 bytes: active, embedded CArray vtable, data, size, capacity, growBy |
| Table | 3 words / 12 bytes: active, unsigned byte length, data token |
| Resource | Existing resource identity; `+14` byte size, lock `4b61c0`, unlock `4b6230` |
| Globals | `5430b0/b4/b8/bc` effect-table object tokens; `5430c0` comparator palette token |

`4c61d0` constructs the manager with embedded CArray vtable `5136e8`, zero data/size/capacity/growBy and active zero. `4c6260` separately sets active one and returns one. The host must preserve the real source call order rather than infer activation from allocation. A Flare's recovered `4ce850` copies `owner+768`, a **table object**, into the compressed-image side object. Read table `+8` for its payload; treating `owner+768` itself as pixel-table bytes is wrong.

The actual Level1 `MAIN.PAL` is 768 bytes, 256 sequential three-byte entries. Read-only instruction evidence at `4bb5a0` establishes its bounded source expansion: reject size below `0x300`, use the final `0x300` bytes (`data + size - 0x300`), copy each triple unchanged into entry bytes 0/1/2, and set byte 3 to zero (`4bb5db..4bb5f4`). That fourth byte is a palette-entry reserved/flags byte, not inferred alpha. Palette resource vtable `513d78+30` selects `4d6620`, then `4bcbc0` allocates the 56-byte backend object and elects `4bb5a0`; `4bb100` copies the expanded 1024 bytes and invokes physical CreatePalette with flags `0x44`. This loader graph is **instruction evidence only**, not a recovered whole-body API in this module.

The original owner palette source is the physical `GetEntries` result: `46afe9..46b000` traverses owner `+2c → paletteObject+10 → DDPalette+4` and calls COM virtual `+10` with `(palette, flags0, start0, count256, owner+360)`. Supplying directly expanded MAIN bytes is therefore a declared native format/physical-transport profile, not proof that source DirectDraw returns identical entry flags in every environment.

## Whole startup ordering

`46e160` has ECX=owner, no stack arguments. Its non-8-bit branch returns one without stores. On the 8-bit branch it first caches `app+58`; a null manager returns zero before clearing any owner table fields.

With a manager, it clears owner `+768/+76c/+770`, then looks up `PALETTES_LIGHT` (literal `52a09c`, type `434c54`) through `4b7dc0(owner+1c, name, type)`. A resource is locked, its bytes loaded with its source size, and unlocked, including a null lock result. Missing/failed light data elects `4c68e0(manager, owner+360, 256, 400, 1, 16)`; a null result returns zero without invented rollback. `PALETTES_AVERAGE` (`52a088`) follows the same pattern, with fallback `4c6d90(manager, palette, 100, 100)`. Finally `4c6fa0` always constructs the rank/inverse table.

Success installs **AVERAGE** in both `5430b0` (mode 2) and `5430b4` (mode 4), and rank in `5430bc` (mode 50). It does not install LIGHT in those globals or write `5430b8`. `4c60a0` separately maps mode 8 to `5430b8`; other mode values perform no stores. These are raw source aliases, not opacity values.

The frozen level-start caller reaches this body at `46b0e5`. Frozen cleanup `46b7b0` removes each nonzero owner table and zeroes the owner fields. Table removal itself does not clear owner fields or the effect globals. Stale global references after removal are preserved as source behavior, not silently reset by this adapter.

## Function inventory and finite arithmetic

| Entry | ABI / behavior |
| --- | --- |
| `46e160` | thiscall owner, no args; startup result 1/0 |
| `4c61d0`, `4c6260` | thiscall manager, no args; construct / activate |
| `4c7360` | thiscall manager, `(sourceBytes, size)`, RET 8; allocate table, append to manager, decode, remove on decode failure |
| `4c7850` | thiscall table, `(sourceBytes, size)`, RET 8; local memory-file construct/attach/read/destruct |
| `4c7730` | thiscall table, `(fileToken)`, RET 4; header allocation and payload read |
| `4c68e0` | thiscall manager, **five args**, RET 20: palette, gradient width, gain percent, signed integer power exponent, low-byte lift |
| `4c6d90` | thiscall manager, `(palette, weight0, weight1)`, RET 12; full 65,536-byte average table |
| `4c6fa0` | thiscall manager, `(palette)`, RET 4; 512-byte sorted indices / inverse indices |
| `4c70b0` | cdecl two byte-element pointers; weighted-brightness comparator |
| `4c60a0` | cdecl `(tableObject, effectMode)`; global installer |

The light factory allocates `gradientWidth << 8` bytes, then produces 256 rows of that width. It preserves signed width/gain/exponent conversions, float stores, the original 53-bit x87 expression order, channel clamp/low-byte behavior, and original nearest-color selection. Brightness is the low byte of the truncated weighted sum using float weights `0.5859375`, `0.296875`, `0.109375`. The normal exponent-one path needs the original CRT result: three of the 256 discrete `_CIpow(base, 1)` outputs differ by one ULP from the input. `pow-one-profile.json` records all 256 hash-pinned source outputs, embedded as immutable data. Non-normal exponents retain an explicit exact `4f1b30` numeric service: four normalized IEEE-double words `(base, exponent)`, returning 64-bit IEEE result bits. This adapts the x87 call ABI, not the arithmetic to a guessed host `pow`.

AVERAGE preserves the original integer divisions and wrapping multiplication/addition: denominator is signed `(weight0 + weight1) / 100`; each channel combines separately divided weighted source bytes, divides by that denominator, retains the low byte, then finds the nearest palette entry. Divide-by-zero/overflow profiles are stopped source prefixes, not claimed successful original returns.

Rank initially contains bytes 0..255. Its comparator reads `5430c0`, truncates the weighted palette color to an unsigned byte, and returns -1/0/+1. The private `4f1e20/4f1fd0/4f2030` byte-domain specialization preserves the original middle pivot, partition comparisons, 30-frame stack and small selection-sort swaps. Equal-color tie ordering differs from `std::sort`, so a host generic sort is not substituted. The second 256 bytes are the inverse permutation. This is not a general CRT qsort API.

Composed frozen entries are `4c76d0/4c76f0/4c7580/4dee30/4c78d0/4c76e0/4c7510/4c6270/4c61f0`. `composeCore=0` exports those exact entries as dependencies instead. Allocation/free remain `4f63ec/4f6428` services.

## Resource and error boundaries

All 42 CLTs across 14 worlds have a little-endian four-byte payload length followed by bytes. LIGHT and AVERAGE lengths are 65,536; SHADE is 16,384. No extra magic, checksum or inferred schema is introduced. The original reader ignores both read counts. Truncated reads may therefore succeed, preserving unwritten allocation seed bytes. Constructor/data-allocation failure ownership and partial startup stores remain source-ordered, including reached leaks and unchecked failure prefixes.

Physical/resource lookup-lock-unlock and MFC memory-file transport remain explicit. `4c7850` owns the finite construct/attach/read/destruct orchestration, while `4ff5f9/4ff645/4ff682` and the actual `5142f4+3c` read entry `4ff79f` are transport services. The complete local memory-file words and externally observable ordering are compared; its MFC implementation and exception machinery are not claimed recovered here. Native faults distinguish missing graph/service (1) from bounded ABI/unsafe rejection (2). Entry recognition is separate from meaningful return and `fault==0` success.

The exact local call sequence is `4ff5f9(1024)` (RET 4), `4ff645(bytes,size,0)` (RET 12), `4ff79f(table+4,4)` (RET 8), successful allocation then `4ff79f(table.data,table.size)` (RET 8), active/result store, and `4ff682()` destructor. The public reader uses the actual heap-backed file receiver instead of local normalization. A failed object allocation in `4c7360` can append null and reach unchecked decoder behavior; it is not made a successful clean rollback.

## Verification and practical limits

`Tests/compare_light_palette_runtime.py` compares complete 1 MiB heap, 320 KiB global image, allocation/live-ownership state, meaningful returns, and ordered complete snapshots at dependencies. It includes all 42 actual CLTs, retained eight-load manager histories, random/tied/reversed rank palettes, scalar comparator and nearest-color cases, finite light branches, integer exponents, source constructor/activation and independent installer modes, heap-file reads, partial reads, allocation failures, whole real startup at six levels, non-8-bit and missing-manager no-ops, and a divide-zero unsafe prefix. Final main-suite evidence is **926 paired whole calls, 4,177 ordered snapshot pairs, 1,376 distinct original instruction addresses, 256 original numeric profiles, and one unsafe prefix**, recorded in `work/light-palette-agent/verification.json` and `verify.log`.

The separate `average-check.py` executed the **entire** original 100/100 average factory and each original nearest-color body, comparing all output bytes and state: one additional paired call, three ordered snapshot pairs, 305 distinct original instruction addresses, approximately 281 seconds. `average-verification.json` and `average-original.log` retain that result. The main suite's `--full-average` flag repeats it; distinct-address counts from separate runs are not added as if disjoint.

Strict C11 import, Swift C11 import/link, and 64 guarded CLT load→rank→use→cleanup histories pass ASAN/UBSAN (`smoke.py`, `smoke.log`). Exact logical block bounds are checked in addition to physical guards. These are finite original-body and native-memory checks, not a complete-game or device rendering acceptance claim. No Xcode build, native UI, simulator, physical device, or physical palette presentation is performed by this worker.
