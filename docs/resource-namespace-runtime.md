# Original resource namespace lookup

`ResourceNamespaceRuntime.h/.cpp` recovers the original v1.0 resource root,
path, typed lookup and directory iteration closure. This is a read-only lookup
module. It returns the original borrowed folder/type/resource token; it neither
constructs a parallel namespace nor owns those objects.

The input is the hash-pinned original `CLAW.EXE` SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private decompilation and verified assembly boundaries are in
`work/resource-namespace-agent/{core,leaves,tables,hash}.c` and their logs.
No source port or filename-derived namespace rule is used.

## API and exact entries

`claw_resource_namespace_entry(function, receiver, args, count, context,
dependency, user, result)` returns1 only for a recognized completed entry.
`result` receives meaningful original EAX. Initialize `context.fault=0` before
each call. Tokens are32-bit original identities. The host lookup provides
aligned word spans; byte reads use the containing aligned word plus byte offset.
Thus a string's final containing word must be readable, including any physical
allocator padding needed by a word-only host. No unaligned typed pointer is
requested. Borrowed tokens, map nodes and globals must remain live during calls.

| Entry | Original arguments | Behavior |
|---|---|---|
|4b7540|none|controller+24 root getter, RET0|
|4b7f20|path|root getter then folder-path lookup, RET4|
|4b7f00|path,type|root getter then typed file-path lookup, RET8|
|4b7cd0|path|recursive folder path, RET4|
|4b7dc0|path,type|split folder/leaf and typed lookup, RET8|
|4b68c0|name|direct folder lookup, RET4|
|4b67f0|name,type|direct typed resource lookup, RET8|
|4b8170 /4b7f80|name,ignoreCase|folder/resource hash-chain lookup, RET8|
|4b80e0|type|type hash-chain lookup, RET4|
|4b8140 /4b7f50|name (cdecl)|byte length modulo5/19, null→0|
|4b80d0 /4b8060|value (cdecl)|unsigned modulo9/19|
|4d54f0|bucket|raw bucket-head lookup, RET4|
|4d54c0 /4d5350|none|first/next hash iterator, RET0|
|4b68e0 /4b6920|none|first folder/type, RET0|
|4b6900 /4b6940|previous folder/type|next folder/type, RET4|
|4b6960 /4b6980|type /previous resource|first/next resource, RET4|

The cdecl helpers leave their stack argument in place. These23 entries do not
allocate or free. Resource acquisition4b61c0/release4b6230 and physical REZ access
remain addressed services in their respective callers.

## Original raw table recipe

A folder is76bytes: name pointer+0, embedded parent iterator+24,
child-name map+3c, type map+44. A type is44bytes: type scalar+0,
embedded parent iterator+4, ID resource map+1c, name resource map+24.
A resource view is96bytes for this closure: name+0, resourceID+4,
embedded ID iterator+48. These are minimum views used by this module, not a claim
that its fixture constructed the entire original resource classes.

Each map header is two words: bucket count, bucket-table token. Buckets are16
bytes; bucket+8 holds `nodeToken+4`, or0. A24-byte node has next+4
(also `nextNodeToken+4`), map owner+0c, bucket index+10, value+14.
The embedded iterators carry those same next/owner/index fields. The fixture
builds both type ID and name maps, preserving disc record order within a bucket.
Original folder hashes use byte length%5; type hash uses unsigned tag%9;
resource name hash uses byte length%19. The type is the raw four-byte REZ tag,
for example `DIP\0`, not a filename extension string pointer. Source iteration
scans ascending buckets and follows collision chains.

Physical REZ directory decoding and these raw table constructors remain an
explicit host adapter. This task proves the complete original lookup/iteration
bodies over that declared table profile, not original archive loading or retail
boot registration order. The native host can borrow a root at controller+24 and
use4b7f20 for `STATES_BOOTY` /`STATES_CREDITS`, then direct folder lookups or
iteration for images/animations/sound children. No LEVEL1/GAME-only special case
is required by these original methods.

## Parsing and CRT details

Allowed bytes are20..2e,30..39,41..5a,61..7a. Everything else separates
components, including underscore, slash, backslash and bytes80..ff. If length>1
and the first byte is disallowed, exactly one leading byte is skipped. Consecutive
later separators are skipped together. Empty names are looked up; an empty
folder path does not return self automatically. Trailing separators return the
last resolved child.

File lookup scans backward to the last separator. A bare filename returns0.
A separator at index<=1 elects direct lookup in the supplied folder, ignoring
the short prefix. An empty file path reads `path[-1]` before checking its negative
index; the preserved predecessor can change its outcome. Tests exercise both
allowed and disallowed predecessor bytes, and genuine null-pointer fault prefixes.

Original file scratch has a32-byte leaf followed by256-byte folder storage.
Long leaves can overwrite folder scratch; the later folder copy can overwrite
the leaf tail. This finite overlap is preserved through a288-byte native local
region, including admitted31/32/33/64/255/287-byte leaves. Native fault2 stops
copies beyond that region, folder lengths>=256, or folder-path components>=64.
Those three diagnostics are safety guards, not matched successful original
behavior or a claim of emulating original stack corruption.

Default CRT locale `540e88=0` elects the original ASCII4a3cf0 comparison, composed
here with the same unsigned-byte folding and meaningful0/±1 result. Nonzero
locale delegates exact cdecl4a3cf0 through the rich dependency ABI. This boundary
may implement actual locale locks/tables elsewhere; the oracle explicitly
supplies an ASCII locale transport and records every comparison with full state.
Local argument identities are normalized to0, `localMask` marks argument bits,
and buffers appear in ascending argument order with NUL included. Raw arguments
retain their original tokens. The buffers are synchronous borrowed names and
must not be retained. Source lookup re-reads a matched node value after the
callback; a directed alias mutation confirms this behavior.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_resource_namespace_runtime.py` and
`work/resource-namespace-agent/check-abi.sh`. The final suite passes26,580 whole original calls /26,606 complete snapshots,
with3 matched unchecked-pointer prefixes,46 exact-size ASAN/UBSAN replays,
and723 instrumented addresses within the original PE text range. That address
count includes the adapted nonzero-locale comparison entry; it does not assert
that every instrumented address executed an unchanged body.
The private report/log contains final counts. Whole original instructions execute every normal lookup, hash,
iterator and wrapper body. The default CRT branch executes unchanged original
4a3cf0; only the nonzero-locale transport is adapted.

The normal suite compares full4MiB heap plus64KiB original globals, meaningful
EAX, exact stack cleanup and ordered callback name/state snapshots. It covers
the fingerprinted disc's1384folders and13077resource records, including full
folder/type/resource iteration and direct lookups, generated separators/signed
bytes, duplicates, sensitive/folded names, missing names/types, null names,
all unsigned hash boundaries, actual BOOTY/CREDITS and all14LEVEL profiles.
47 folder names containing their own underscore cannot be addressed by a
flattened path through original4b7cd0; direct4b68c0 and enumeration resolve them.
The test preserves that measured result instead of manufacturing an alias.

Three genuine original unchecked-pointer faults match native failure prefixes
and unchanged complete heap/events. The exact-size sanitizer corpus uses each
fixture object in a separate allocation with only its declared aligned span;
strings include their final containing word and query paths have an explicit
four-byte predecessor. Strict C++17/C11, Swift import, ASAN and UBSAN checks are
private command-line checks. They do not establish physical archive transport,
full application boot, native screen presentation or complete game identity.
