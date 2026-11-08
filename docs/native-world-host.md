# Native whole world-file host

`ClawNativeWorld.swift` executes frozen WorldFileRuntime's actual constructor
4cace0, whole load4cb200, cleanup4cb5f0/4cb180 and destruction4cdd30/4cdd10.
It composes frozen CArray, WorldPlane, SceneCamera and SpatialGrid bodies.
The wrapper supplies native heap/codec/resource seams, rather than reconstructing
plane fields from the format reader. `ClawWorld` is used only as a format
comparison in the private test.

## Caller contract

Initialize with the existing `ClawTokenHeap`, caller-owned56-word world token,
parent scene token, lifetime-valid `ClawSceneActorHost`, nonempty
`populationPolicy`, and hooks:

- `imageRoot(name)` resolves the original synchronous plane name to an image-set
  token. A nil result is the original lookup miss, not invented success. Thrown
  resource failures are native diagnostics. Plane flag16 paths require the
  original image-manager/header spans for derived tile dimensions.
- `gridSetup(GridBatch)` must run actual4d1620 and its ordered4d17e0 record
  callbacks. The batch contains the plane, original first record token/count,
  and owned copies of each raw record's exact bytes and71 words. Negative signed
  counts retain their original raw value while producing an empty copy list,
  matching the source grid caller's skip branch. Root may map each copied record
  before calling its existing `constructPlaneGrid(plane,record,count)`.
- `service(call)` routes true spatial/actor/resource lifecycle dependencies by
  original address. Return nil for unavailable bodies; the wrapper diagnoses
  them. In particular, real populated-world teardown requires the actual actor
  deleting callbacks emitted by4d50e0, not a successful no-op.

WorldFileContext.composeSpatial is zero because the caller must establish its
record map before source4d1620. This delegates that complete source body through
`gridSetup`; it does not remove the source grid initialization call. CArray mode0
preserves the explicit physical allocation/free profile. The host's callbacks
and scene graph must remain alive until explicit cleanup/destruction completes.
Swift deinit only releases wrapper context storage; it does not call into a
dying scene. Use weak hook captures if the scene retains the wrapper.

If source SinglePlayerSceneRuntime already ran the world constructor, pass
`alreadyConstructed:true`. Otherwise call `construct(id:flags:)` once on fresh
world storage. Do not run a second constructor over a loaded object's owned
arrays. The caller's parent+24 world link and parent+8 actor-container/+10 image
registry links must describe the actual scene. Actor population and its skipped
objects belong to the explicitly declared caller policy.

`load(compressedWWD:viewportWidth:viewportHeight:)` takes the original file bytes.
It configures the inclusive viewport/default pairs through real4cb040, then
calls complete4cb200. It also accepts actual uncompressed files when their
original header flags say so. Never pass a Swift-decoded stream that still has
compression flag2. Read `planeTokens`, `mainPlaneToken`, `mainIndex`, `flags` and
`descriptionTokens` from the resulting raw world arrays, not from format guesses.
`cleanup(resetViewport:)` retains the world allocation for reload; `destroy`
executes the source base destructor, optionally freeing that allocation.

## Codec and ownership

All allocations made through the source context retain their logical byte sizes.
The original codec call advertises declared decoded length as its source length;
the native zlib backend instead uses the actual remaining compressed file bytes
in that owned allocation. It preserves original destination capacity, callback
address/arguments, output count and return bits. Level1 advertises647102 bytes
while the actual compressed payload has25676 bytes. No oversized readable span
is manufactured. `codecInputLengths` records both values. Native zlib's internal
allocator and corrupt-stream errors are a platform boundary; frozen original
codec evidence establishes output parity on all14 valid source payloads.

The decoded temporary and input file buffers are freed after source loading;
raw record tokens expire at that boundary. GridBatch records own their Data and
remain readable afterward. Successful planes own tiles, row offsets, copied
names and pointer arrays; descriptions own their scalar fields and type3 masks.
Image-set resources referenced by plane arrays remain owned by their registry.
Cleanup/reload retains source ordering and partial-load state. Truncated inputs
with fewer than188 readable header words are rejected as a native adapter fault;
this does not claim malformed original crash-side-effect equivalence. Source
ordinary return-zero failures are distinct from `fault`/unavailable services.

## Verification

Run `work/native-world-agent/check-native-world.sh`. It extracts all14 exact
compressed WORLD.WWD files from the SHA-pinned original REZ into private work
storage and compiles a standalone native Swift/C++ fixture. Its population policy
is **inspection only**: all actual4d17e0 callbacks execute and compare exact raw
bytes/order/advance, but no gameplay actors are claimed created. The real grid
constructor/allocations/lifecycle run; source objects are not silently counted
as implemented actors.

The native fixture passes all14 files and34,784 ordered raw record callbacks,
then verifies every world/grid allocation is released. Level1 uses the actual
native asset resolver and confirms its input equals the original REZ file;
flags3, three planes, main index1 and center689/4723,938 complete owned
simple/rectangular descriptions,1479 callbacks, raw tile/row equality, original
cell counts4608/576/18432, decoded-record token expiration, registry resource
retention, retained reload and world destruction pass. Synthetic source records
verify unaligned type3→owned16-byte mask, exact mask release, viewport reset,
cleanup-before-invalid-header failure, zero-declared decode failure before the
codec, and uncompressed ownership. Whole original loader/codec instruction
comparisons remain the frozen WorldFileRuntime suite, independently rerun by
Root; this wrapper's format comparisons do not supply reference gameplay.

Full retail startup, file/REZ internals, other levels' actual image registries,
and gameplay for the34,784 object records are not established by the inspection
profile. Root integration must supply its supported actors and visible skips.

The complete same fixture also passes AddressSanitizer for Swift and all linked
C++ modules: `CLAW_NATIVE_ASAN=1 work/native-world-agent/check-native-world.sh`.
The private smoke uses a minimal world/resource module set; it does not drive
Xcode, a simulator, a device or the shared scene. Its SceneActorHost must provide
lookup/allocation/free services; nil physical memory callbacks are a caller
contract error, never successful ownership release.
