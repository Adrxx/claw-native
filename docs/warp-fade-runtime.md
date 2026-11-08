# Original type2 warp fade

`WarpFadeRuntime` adds the missing original type2 factory/private/pixel bodies, without editing the frozen type1 circle, blend, special-command or native host modules. Source is hash-pinned Captain Claw v1.0 executable SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Original instructions are the oracle; no game-port implementation or guessed opacity is used.

## Stable raw API and actual object graph

`ClawWarpFadeContext` points to the existing caller-owned `ClawPlayerFadeBlendContext` and contains only a native loop-operation diagnostic bound. The common fade host, clock import services, bypass global alias, CString scratch and live token heap are shared. `claw_warp_fade_entry` recognizes the entries below, returning1 for covered completed execution and0 for unsupported/faulted profiles. Meaningful source EAX is returned separately; incidental void-function registers are excluded. Faults are stored in `common->fade->fault`:1 missing span/service,2 reached unsafe/stalled bound,3 unsupported profile. They preserve the reached prefix and do not imply an original safe return.

| Original entry | ABI / complete body |
| --- | --- |
|4ec050|Thiscall factory `(2, descriptorOr0)`, RET8; complete type2 branch and common append/failure paths|
|4ed060|No-argument constructor, actual32092-byte allocation; VT514228|
|4ed0b0|Initializer `(five-word descriptor)`, RET4|
|4ed1a0|Pixel step `(stepNumber)`, RET4|
|4ed5d0|No-argument maximum step|
|4ed080|Deleting wrapper `(flags)`, RET4|
|4ed0a0|No-argument derived/base destruction|
|4ecc00|No-argument five-word descriptor constructor|
|4efb00|Cdecl column permutation `(output, low, high, initial)`|
|4efc40|Cdecl original primality predicate `(candidate)`; returns1 for every signed candidate<=2|
|4ec9c0 /4ec600|Frozen whole common runner `(duration, initialWait, pumpFlag)` / manager removal `(effect)` composed through exact new virtual entries|

Actual VT514228 contains five entries:4ed080 deleting,4ed1a0 step,4ed5d0 maximum,4c96b0 pre/post no-ops. Allocate **0x7d5c bytes /8023 words**, preserving seeded untouched words. Constructor composes frozen4ec8d0/4c61d0, installs the derived table and clears4c/50; it does not zero the entire object. Raw readable immutable vtable spans must be supplied through host.lookup.

Manager is the existing type1/type2 fade manager: words0/4 default target/source surface tokens; embedded five-word CArray starts10, data14/count18/capacity1c/grow20, physical graphics holder24. Its append uses frozen original CArray4f5915. Common runner dispatches new virtual bodies through the dependency bridge; no frozen runner source change is required. Common removal4ec600 deletes the first matching entry and composes the actual derived deleting wrapper. Embedded palette/list cleanup reuses frozen PlayerFadeBlendRuntime. No new palette table is allocated by this fader's ordinary initializer.

The descriptor is `[3, targetSurface, sourceSurface, clearFlag, percent]`. A zero target/source selects manager defaults after base binding. Source missing forces clearFlag1. Null descriptor is constructed through4ecc00 as `[3,0,0,1,15]`. SpecialCommand48feb0/48fda0 supplies the actual stack packet `[3, back, frontOr0, outward, 80]`; its rich localMask2/buffer5 can be materialized in caller-owned synchronous scratch and passed here. This scratch is not an original heap allocation. A false factory/init result must remain false.

Target/source tokens are the **raw original graphics surface objects**, not PID headers or CGImages. Source reads height14, width18, byte stride1c, DD interface8, bytes-per-pixelac. Lock4b9730(surface,0) returns a live pixel token; source locks target then source, and unlocks each live surface via its DD interface virtual80 `(interface,0)`. The physical lock/Unlock implementations and hardware surface identity remain exact-address transport services. Pixel writes, row selection, copy direction and ordering are recovered here. HRESULTs are not interpreted into invented fader error paths.

## Initialization, numerical and pixel behavior

Initializer resets20, resolves target/source and clear flag, copies dimensions and accepts **signed** percent0..100. It stores percent58 and gradient54=`ftol(percent * Float(0.009999999776482582) * signedHeight)`. At the real640×480 warp percent80 this is **383**, maximum863. Percent100 can likewise truncate one below height; substituting a percentage integer division changes source behavior.

Four2000-word arrays at5c,1f9c,3edc,5e1c hold integer row progress, column cursor, fractional Float accumulation and column permutation. It clears the progress/fraction/permutation entries and consumes **exactly2000 shared CRT4a3050 draws** for initial cursors. Width is captured before each random call, as original instructions do; callbacks changing the raw width cannot retroactively alter that draw's remainder. Route4a3050 into frozenCRTRandomRuntime with the same raw TLS thread+14 seed as gameplay. This module never seeds or privately clones the RNG.

4efb00 chooses the first original predicate-approved modulus at/above high-low below100000, finds the source multiplicative generator using an allocated marker array, writes clamped output values with the source inclusive comparison, then frees the marker allocation. Small moduli preserve the original allocation-token-as-multiplier quirk. Failed marker allocation silently leaves the already cleared permutation and still allows initializer success. These are actual source quirks, not validated mathematical substitutions.

Each nonzero step locks surfaces, stores pixel44/48, computes Float ratio(width/gradient), visits the finite moving gradient band, and applies the original sine count. The exact source sine literal514240 is **Float1.5707950592041016**, not pi/2. The original sequence is unsigned64 progress/ signed gradient, multiply source Float literal, FSIN, signed width multiply, divide stored Float ratio, source FTOL. Native libm supplies the numerical calculation; its resulting integer counts are separately checked against original FSIN→FTOL instruction fragments across the measured profile. This is bounded numerical evidence, not a universal assertion of every x87/libm input.

Sequential pixels advance the row's cursor, wrap only when cursor>width, read the source permutation and clear every byte of that selected pixel or copy source bytes forward. Fractional accumulation uses actual Float stores and original integral extraction order. Additional random pixels consume source RNG draws after the sequential batch. The final loop completes rows behind the band, clears/copies only width*bpp bytes, sets20 to the supplied step and unlocks target/source in source order. Zero step does nothing; repeated/reversed steps preserve their actual counter effects. Copy operations preserve shifted buffer aliases by reading after earlier stores.

Source permutation/index conventions can select column width for some sizes and affect row padding or neighboring rows. The adapter checks provided memory spans, **not a guessed visible rectangle**, and does not clip those writes away. Caller transport must represent actual buffer capacity and guard/padding ownership. A diagnosed missing span stops the native prefix; it is not evidence that the original would avoid an unsafe write.

Whole common4ec9c0 retains the original physical clock sequence, initial wait, Float clock conversion, step selection, optional DD transport and final step/frame-count field. This module adds no synthetic step, sleep, event-pump or fadeBypass switch. Clock repeats/wrap can fail to complete: native clock/operation guards stop at measured original prefixes rather than return fake success. Original duration0 can stall and is not silently fixed.

## Ownership and failure prefixes

Factory validates descriptor tag3 before allocation. Wrong tag and failed init run the frozen diagnostic CString construct/release path; common temporaryStringToken/emptyStringToken must be valid. Null object allocation reaches the original unchecked base-binding store4ecb08 after the allocation event; native fault1 matches that reached prefix. Zero width reaches original signed IDIV4ed160 after the first shared random draw; native fault2 preserves it. There is no speculative rollback.

Deleting wrapper first restores derived VT, then frozen4ec920/embedded palette-owner destruction, and frees the object only when flags&1. Surface identities are borrowed, not released by an invented new surface destructor. Inline arrays have no independent heap lifetime. Retained manager removal and raw allocator ordering are tested.

## Evidence and limits

Run `work/test-env/bin/python Tests/compare_warp_fade_runtime.py`. All compiled artifacts, private source probes, Ghidra clone and reports live in `work/warp-fade-agent`. The differential oracle executes the unchanged whole original factory, constructor/init/step/max/destructors/permutation/prime, common runner/CArray/CString/palette ownership and **actual original CRT random/getter bodies**. Only physical surfaces, Windows clocks/TLS/CString interlocked/string transport and allocators are adapted with exact call identities and ordering. Every comparison hashes the complete1.125MiB fixture heap, including the entire0x7d5c fader, pixel payload/padding/guards/allocator spans/TLS thread, plus114688 mutable original global bytes and ordered full-state snapshots; meaningful EAX and stack pops also match. Synchronous temporary descriptor/CString cells are normalized separately because original callers use stack storage.

The final combined suite passes **512 whole original/native calls,4 stopped unsafe prefixes,449008 ordered full-state snapshots and1101 original instruction addresses**. Additional private default-descriptor/manager-growth/diagnostic checks pass6 calls/12014 snapshots; source RNG callback-width mutation checks pass5 calls/12035 snapshots (reported separately, not added to the combined address union).

Measured phase evidence includes1..4 bytes/pixel, signed percent gates, dimensions1/2/odd shapes, source-only clear override, allocations/null/diagnostic paths, primitive-root edge cases, repeated/decreased steps, shifted aliases and unequal source pitch. Both retained640×480 directions use a byte-identical indexed frame derived from actual Level1 MAIN.PAL provenance; it is a representative buffer, not a captured full retail scene. The original pixels do not read palette RGB. Shared-clock repeated/Float-conversion/near-wrap trajectories and stalled/wrapped unsafe prefixes are verified. No type1 implementation or gameplay source was copied.

Independent C11 and Swift imports check the raw ABI; strict C++17 builds warning-clean. Native ASAN/UBSAN uses64 exact-size fader histories with partial/terminal1..4-byte clear/copy steps, explicitly provided pixel padding/guards and actual cleanup. Separate source FSIN→FTOL fragment verification passes13107 numerical profiles, including every640/383 moving-band progress value and additional widths/gradients through1999. This establishes those measured numerical/pixel outputs; broader corrupt descriptor/overflow/unbounded geometry domains remain native diagnostic or unmeasured domains. Physical presentation, full WM_COMMAND805c→ordinary retail scene joining and device acceptance remain parent integration work.
