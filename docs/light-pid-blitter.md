# Original compressed eight-bit lighting pixels

`LightPIDBlitter` recovers effect mode 2 of the original compressed eight-bit dispatcher and its four elected pixel bodies. It composes frozen `PIDBlitter` for mode 1. This is indexed-byte table lookup, including the original clipping and row-doubling behavior, rather than a CG alpha or additive-color approximation. Physical DirectDraw lock/unlock remains a transport boundary.

The differential oracle is unchanged v1.0 `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The actual assets are from the separately pinned retail archive used by the existing resource decoders; original-version asset identity remains a separate question. No reference gameplay or pixel-loop implementation was used.

## Exact entries and raw state

`4bffa0` is thiscall ECX=40-byte compressed object, five stack arguments `(destinationRect, surface, sourceRect, flipX, flipY)`, RET 20. Its source bounds reject only negative left, right above width-1, negative top, or top above height-1. It does not validate bottom, ordering, or destination right.

| Mode | No flip | X | Y | XY |
| --- | --- | --- | --- | --- |
| 1 | `4c00b0` | `4c0450` | `4c0920` | `4c0cc0` |
| Other, eight-bit | `4c1190` | `4c25b0` | `4c3800` | `4c4c20` |

Each pixel body is thiscall with three stack arguments `(destinationRect, surface, sourceRect)`, RET 12. The table-mode bodies first check compressed `+1c`: a null table returns without locking or writing, while the dispatcher still returns one. Otherwise `4b9730(surface,0)` locks, the finite body draws, and surface `+8` DirectDraw interface virtual `+80` is invoked `(dd,0)` to unlock. The original routine does not elect a separate table-active gate.

Relevant compressed words are `+0` render word, `+4/+8` width/height, `+c/+10` encoded pointer/length, `+14` mode, `+18` effect value, `+1c` table object, and `+24` low-byte format. The table is the exact three-word `{active, byteLength, payloadToken}` object from `LightPaletteRuntime`. The pixel body reads **table+8**, ignoring its active and length fields; native capacity validation is separate. Ordinary source constructor `4bfbf0` sets render word zero and format byte one.

Mode 2 snapshots each literal run's existing destination bytes to original global scratch `542bb0`, then writes:

```
newIndex = tablePayload[(oldDestinationIndex << 8) + spriteLiteralIndex]
```

Literal zero still writes through the table. High-bit transparent runs move the scan counters without pixel or scratch stores. Horizontal mirroring retains the original extra destination column: the initial decreasing counter is width, not width-1. The scratch run is copied in ascending physical address order even for reverse stores, and its unwritten tail remains live across calls.

When compressed `+0 != 0`, mode 2 elects its source alternate-row branch. The parity gate uses wrapping `(sourceScanRow + destination.top) & 1`. Selected runs use the same row's snapshotted destination and write each result to both the current address and **address + stride**, even when the vertical scan moves upward. Thus the second row is not independently blended. Skipped rows still consume the encoded grammar and advance the source loop. This preserves original neighboring-row effects, padding writes and aliases from a stride narrower than a decoded row.

## Clipping and stack identity

The source loop retains distinct branches rather than decoding a rectangle and reflecting it. Left-zero full rows include bottom. Left-zero clipped-right forward writes use an exclusive right threshold. A nonzero left in the forward path ignores right and excludes bottom; mirrored nonzero-left branches ignore right and include bottom. Mirrored left-zero clipped-right X excludes bottom while XY includes it. Run-boundary partial tails and physical offsets are preserved, including writes beyond the nominal rectangle when still inside the supplied buffer.

The table XY body has a distinct source bug: `4c4c63` reads an unwritten local counter at entry stack pointer minus `0x24` during top skipping. This is **not** the normal mode-1 XY source-pointer seed. `bothTopSkipSeed` supplies that exact initial value. Whole-dispatch tests seed the original caller stack before executing the unchanged routine and verify the value at entry. Positive zero/small/token seeds and bounded negative-one histories are covered. Some overflow/negative seed plus rectangle combinations consume beyond the encoded stream; those are native atomic safety rejections, not successful original returns. A native zero seed is an explicit caller-stack profile, not a claim that all original call chains initialize that local to zero.

## Stable C11/native integration

`claw_light_pid_blit8` accepts the full compressed PID bytes, frozen `ClawPIDBlitCommand`, `ClawLightPIDBlitState`, optional `ClawLightPIDBlitTable`, indexed destination/optional coverage, capacity/stride, and caller-owned 128-byte scratch. The raw state holds render word, mode, effect value, low-byte format and XY seed. Table `words[2]` preserves original payload identity; `data` and `capacity` expose the actual mapped payload bytes to this finite native adapter. Do not substitute a table-object address for its payload.

Keep all input/output/coverage/scratch buffers separate. The source writes must fit the full supplied physical buffer, including row padding and adjacent-row spills; do not constrain validation to a guessed destination rectangle. Coverage marks actual writes, including writes of zero; transparent runs preserve prior coverage. Full-image presentation should use the complete visible covered buffer after blending into the current indexed frame.

Return one means an accepted supported profile; zero can mean original rejection, unsupported mode/format, or a native safety rejection. Native rejection leaves output, coverage, scratch and info untouched. Accepted null-table mode 2 leaves buffers untouched and reports zero lock/unlock/writes. `Info.consumed` is a native encoded-cursor diagnostic; write counts are compared with original actual byte stores, and lock/unlock counts with original ordered services. It is not an original ABI field. Native temporary storage enables atomic rejection before committing output; it is a bounds-safety extension, not original allocator behavior.

Mode 1 delegates frozen `claw_pid_blit8` and retains its source-rect-address profile. All supported destination formats have low-byte format one. The original mode-1 dispatcher also accepts other format bytes, but their multi-byte loops are outside this eight-bit API.

The original table bodies and helper `4c5e80` also contain modes 4, 8, 22 (`0x16`) and 50 (`0x32`). Instruction inventory shows fixed-effect table selection in 4, source-index table selection in 8, fixed index fill in 22, and rank-table interpolation in 50. Their branch-specific row/scratch/index quirks are **not recovered by this API** and must remain explicit unsupported services. Unknown table-mode numbers may be accepted by the original dispatcher with no literal stores; this module does not report them as recovered success. General color palettes and native RGBA conversion remain outside these indexed pixel bodies.

## Measured evidence

`Tests/compare_light_pid_blitter.py` verifies **7,084 whole original dispatcher/native pairs**, **14,120 ordered lock/unlock snapshots**, **9,279,820 actual byte stores**, and **4,044 distinct original instruction addresses**, excluding adapted lock/unlock and the harness stop. Complete 1 MiB heap and 320 KiB global image are compared after permitting only destination and the actual 128-byte scratch stores. Encoded input, raw compressed object, rectangles, table object/data and unrelated state remain unchanged. Full destination buffers, padding, guards, actual-write coverage, repeated store count and scratch tail are compared.

Coverage includes the complete valid rectangle matrix for a 7×4 mixed literal-zero/transparent fixture, all four flips and both render-word branches; supplied stack seeds; 300 generated grammar/odd-offset/overlapping-row profiles; source rejects, inverted rectangles and null tables; frozen mode-1 composition; **both actual Flare and Wolvington LFX PIDs with all 28 actual 64 KiB LIGHT/AVERAGE CLTs**, 2,240 full/clipped draws; and 128 retained draws into previously lit buffers. The 16 KiB SHADE tables are not misrepresented as full mode-2 table inputs.

Strict C11 and Swift import/link pass. `work/light-pid-blit-agent/smoke.py` runs 96 additional whole-original-derived exact-buffer fixtures under ASAN/UBSAN, with separate guards around input, 64 KiB table, destination, coverage and scratch, plus atomic malformed/capacity/table safety checks. Logs and `verification.json` remain in the private work directory. This is finite source pixel and native memory evidence; no complete-game, physical DirectDraw, simulator, Mac UI or iPad rendering acceptance is claimed by the worker.
