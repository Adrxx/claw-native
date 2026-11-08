# Native indexed framebuffer integration

The native scene now retains a640x480 eight-bit framebuffer and129 live scratch
bytes across actor draws and frames. Original GameImage drawing selects the
compressed object's render word, effect mode/value/format and exact table token.
Frozen EffectPIDBlitter composes the recovered modes1/2/4/8/22/50. Its mode2
reads the existing destination index before applying the loaded LIGHT table;
lighting is no longer a standalone normal sprite layer.

Native presentation crops every visible covered store, including original
neighboring-row writes. Literal zero is opaque; transparent runs leave existing
indices unchanged. Each covered RGBA layer preserves the source draw order.
Uncompressed surface copies and plane fills update the same indexed frame.
Their rectangle/key/flip/clipping implementation is an explicit physical DD
transport. Palette RGB conversion and CoreGraphics presentation remain host
boundaries; this is not full physical DirectDraw/display equivalence.

Compressed image headers now execute complete source4bfbf0 and4bfc50 over the
actual PID bytes, including copied encoded payload and default metadata. The
physical filesystem namespace remains native. PIDflag64 elects mode2 through
source4c6130; Flare's source image-set binder installs the owner's loaded LIGHT
table after scene palette startup. Image loads before that startup retain the
explicit null-table profile until a source caller assigns it. Retail startup
ordering for all resource classes remains incomplete.

Source46e160 reads actual LEVEL1 LIGHT/AVERAGE CLTs and generates the rank/inverse
table through the recovered palette manager, loaders, sort and installers.
MAIN.PAL now runs through the recovered original PAL resource/backend/list graph
and source owner GetEntries prefix before CLT boot. Physical DD/file/CString-map
services remain named native transports; see native-palette-resource-host.md. The native
initial framebuffer,129-byte scratch and unwritten XY top-skip caller seed are
zero profiles. Their later writes/tails persist; the initial profile does not
prove the corresponding original machine's uninitialized stack bytes.

Tests/compare_native_indexed_composite.py checks128 retained draws on one padded
indexed frame against complete unchanged-original captures. All six modes,
flips, raw destination/scratch/coverage bytes and every cropped RGBA pixel match.
Root separately reran all13,276 EffectPID original comparisons,26,512 ordered
snapshots and7,639,666 writes. These finite profiles do not establish every
caller effect election or complete-game pixel parity.

The actual native Magic history checks Flare's mode2/table token and nonzero
source lighting writes under ASAN. The fresh Mac Catalyst app72463 was observed
with MAGIC animation, ammo3 and a visible lit projectile; it was left paused.
Both fresh Mac Catalyst and generic simulator builds succeed. This is a native
Mac GUI smoke check, not physical-iPad acceptance or original-video parity.
