# Native read-only source archive host

`ClawNativeResourceArchive` runs the actual source72-byte archive constructor,
whole4b72e0 opener,4b6b60/4b6ed0 recursive directory grammar and frozen table,
namespace and payload ownership modules over one native32-bit token heap. Its
only archive input is the original file path. It does not supply a resource
list, synthesized sorted table or successful source-loader result.

Physical `fopen("rb")`, `fseek`, `fread` and `fclose` use native libc. Tokens
identify the FILE separately from host pointers. The source168-byte automatic
header is transported as an exact synchronous mutable buffer. All malloc calls
request the original byte count; final containing-word padding is declared for
legacy word-only views, while directory/copy/file byte access checks exact spans.
Immutable original method metadata and zero C-locale flag are exposed explicitly.
The common42a680 XOR EAX/RET leaf is the default zero retry outcome.

Source destruction elects fclose twice because it leaves the original stream
handle stale. The host records both source calls, returns EOF for the already
closed FILE, and calls actual libc only while the FILE is live. It preserves the
retry election without invoking undefined host libc behavior. Filesystem writes,
archive editor/compaction and general locale operation remain unsupported.

The original namespace path parser treats underscores as separators. For
example LEVEL8\IMAGES\ARROWSIGN_UP is not a literal full-path query for that
folder. The host preserves4b7f20 and exposes original4b68c0 child lookup for raw
component names. It does not manufacture aliases or change the source grammar.

Root native ASAN/UBSAN checks pass the complete actual original archive:

- 1,384 folders: raw names, offsets/lengths/timestamps, parent/controller/self
 aliases, original child iteration and hash-bucket prepend order.
- 13,077 resources: names, IDs, type tags, metadata, offsets/lengths/timestamps,
 both actual embedded ID/name node orders and source hierarchy ownership.
- 117,018,527 payload bytes: every independently captured SHA256, cached repeated
 acquisition with no extra FILE read, source release and a retained cached
 payload released by the complete source destructor.
- All source allocations removed; original two close calls/one retry preserved.

The independent inventory is captured from the hash-pinned original REZ's raw
records; it is used by the test only. It never enters the native loader. The
archive fingerprint is
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
The original-source finite bodies also retain their separate450-call/6052-snapshot
unchanged-original differential proof. Complete native archive acceptance is not
an original full-boot behavior comparison or a live menu/scene handoff.

To reproduce after restoring ignored original inputs:

```sh
python3 Tests/capture_native_resource_inventory.py
scripts/check-native-resource-archive.sh Original/claw-disc/files/DATA/CLAW.REZ work/native-resource-archive-check/retail-inventory.json
```

The test links native Swift plus the complete nine-source recovered resource
closure. It is a standalone native transport gate; the currently packaged Mac
movement laboratory has not elected this archive host. Menu/image-controller/
full scene dispatch still need joining on the same heap and source aliases.
