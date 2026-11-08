# Original PCX creation and native factory

`PCXCreationRuntime` owns whole fingerprinted original v1.0 `4be810`, with
receiver and four arguments `(manager,data,fileLength,loadFlags)`, RET16. It
borrows the frozen PCX context and composes GameImage initialization and the
existing decoder/conversion bodies over the same raw heap and globals. The
original EXE SHA256 is
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

Initialization is elected through the live surface vtable+0c. Coordinates are
signed16-bit differences; planes1/3 and target-depth admission retain the source
order. Indexed palette publication uses global541fb0; the direct loader uses
541bb0. A changed-depth odd width is rejected after palette publication and
surface initialization, before temporary allocation. Same-depth odd widths
remain accepted. Temporary buffers request exactly width×height×1or3 bytes.
Source allocation, lock, conversion, unlock, free and failure ordering survive.
Physical CreateSurface/GetDesc/Lock/Unlock, diagnostics and unrecovered16-bit
converters remain declared addressed services.

Root `Tests/compare_pcx_creation_runtime.py` passes596 whole original calls and
2311 ordered full heap/global/event snapshots, including469 retail files. The
1289 instrumented source.text locations are not instruction-coverage or
game-completion measures. This corpus retains the decoder's explicit Seed721
neighboring bytes for the measured three-plane overreads; no retail allocator
identity or exact-file success is inferred from those profiles.

After running `Tests/capture_pcx_image_spans.py` and the creation comparison,
`Tests/check_pcx_creation_asan.py` passes469 exact declared-span creation/repeat
profiles,58 tight-file source prefixes and16 exact-sized changed-depth
allocation/conversion profiles under ASAN/UBSAN. The C++ replay and generator
are deliverables; original assets and generated captures remain ignored.

Native Display now calls whole `4bc520→4bf9c0(type2)→4be810`, deriving dimensions
from the original header. The `4bc520` argument tuple is
`(data,imageType,fileLength,loadFlags,colorKey)`. Source4bdad0 is type1 BMP,
not PCX. The indexed host shares its GameImage globals and source allocator,
uses actual188-byte surfaces and source list insertion/destruction, and rejects
exact input EOF even when the native token heap has word padding.

`CLAW_NATIVE_ASAN=1 scripts/check-native-player.sh --pcx-factory-only` passes313
indexed retail files, including299 STATES images, every original-captured
visible pixel, repeated distinct factory objects, list counts and source owner
cleanup. It also checks rejected planes, the exact130-byte direct-loader EOF
prefix, frame resumption and graph release. The color-key test uses maxUInt32,
so no physical SetColorKey behavior is established. Three-plane native palette
conversion,16-bit source bodies, live image-controller/menu/Story election,
full retail presentation and physical-device identity remain unfinished.
