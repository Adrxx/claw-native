# Native source display graph

The native scene now reserves the original60-byte parent and executes4ce960,
using an explicit constructor camera view. Complete4cea10 scene startup and
retail application clock ordering remain separate integration work.

ClawNativeDisplay replaces the old holder/front/back profiles with source
construction:28-byte holder,48-byte primary wrapper, two52-byte auxiliary
wrappers, and three distinct188-byte surfaces. Whole4ca6f0 elects4d5510 and
graphics4bc220, primary4bc890, attached4bcf80 and blank4bc670. The frozen
GameImage descriptor bodies and source surface-list insertion execute.
Immutable virtual-method words come from the fingerprinted original v1.0.
Source4cf730 reports readiness. Native actor and status-message drawing adopt
the actual back wrapper; PAL4d6690 attaches through the actual primary graph.

DirectDraw interfaces and descriptor responses are named native transports:
640x480,8-bit indexed storage,640-byte pitch, zero RGB channel masks, and one
offscreen row. Front, attached back and spare storage have distinct identities;
the back storage aliases the native renderer's indexed allocation. This is not
hardware DirectDraw or complete source presentation acceptance. The existing
frame presentation endpoint and renderer profile remain explicitly adapted.

Physical backing and coverage both contain307840 bytes (640x481), while RGBA
presentation scans only307200 visible bytes (640x480). The whole original
compressed blitter can store the first mirrored bottom-edge byte at307200 and
the next at307199. Passing only the visible capacity rejected the entire draw,
including that valid visible byte. The new source-matched bottom-edge oracle
checks all six normal effect modes and flips, plus one extra-row control,
with full bytes, source scratch and exact visible RGBA cropping. Tight-capacity
rejections remain native safety diagnostics, not original out-of-bounds parity.
Other renderWord1 bottom-edge branches are outside this481-row profile.

Shutdown executes source holder deletion first. The graphics manager retains
the primary surface and list blocks until its whole destruction. Native
interface/storage transports finish after source surface/device cleanup.
The allocator adapter routes mode-array memory back to the host that owns it,
including allocations made by the original enumeration callback.

ARC marks an owner unavailable to `unowned` references before its destructor
finishes. The display therefore borrows the same callback context used by its
C dependencies during owner destruction; finishTransport ends that lifetime.
Later entry rejects with a native diagnostic before dereferencing that context.
The automatic-release sanitizer fixture retains the closed display/heap while
releasing the scene and owner, then verifies all source allocations are gone
and post-close entry cannot access the freed owner.

Focused ownership/PAL/recolor/cleanup and automatic-release ASAN checks pass.
The full native regression and fresh final builds are separately recorded in
STATUS.md. Native story/results/new-level dispatch, full manager/startup graph,
all-level gameplay, physical device and pixel/audio parity remain unfinished.
