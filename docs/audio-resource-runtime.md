# Original audio resource metadata and voice pool

`Sources/AudioResourceRuntime.h/.cpp` recover the bounded resource creator,
RIFF parser, duplicate-voice allocator, and selector from original v1.0
`Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Entry points and callees were verified against actual instruction flow; the
private Ghidra output is supporting evidence and is not copied gameplay source.

| Entry | Recovered behavior |
| --- | --- |
| `0x4b4e30` | RIFF/WAVE chunk parsing and output semantics. |
| `0x4b48b0` | PCM DirectSound buffer creation, resource construction, manager-list insertion, duration/data-size metadata. |
| `0x4b42e0` | Allocate/construct/duplicate a voice, insert at pool head, apply reusable argument. |
| `0x4b4430` | Select a stopped eligible voice or allocate another, restore raw defaults on reuse, move selected node to tail. |

Original constructors `0x4b3cb0`, `0x4b4200`, `0x4b46b0`, status query
`0x4b3e70`, raw setters, and intrusive list entries `0x4b5210/0x4b5240/0x4b5270`
are included in native behavior and execute unmodified in the comparisons.

## Resource loading path and scope

The observed sound-resource loader `0x4c8850` obtains its bytes through resource
service `0x4b61c0`, calls the scene's audio manager at `0x4b4a20`, writes the
returned pool token at sound resource `+0x10`, and releases the bytes through
`0x4b6230`. The manager loader parses through `0x4b4e30`, creates through
`0x4b48b0`, and transfers data through `0x4b44f0`. That transfer locks the
DirectSound buffer, copies the data across one or two returned memory segments,
then unlocks it. Failure calls resource teardown `0x4b4ae0`.

The new API implements parsing, creation metadata, allocation, and selection.
File/resource acquisition, sample transfer, resource teardown/release, and the
complete `0x4b4a20/0x4c8850` loader wrappers are not implemented by this module.
It does not decode MP3 or add a native mixer. A host using the creator must
populate the actual PCM buffer through its own explicit transfer boundary.

## RIFF parsing

The original checks `RIFF` and `WAVE`, scans chunks from offset 12, and advances
past unknown or `fmt ` chunks by `8 + ((chunkSize+1) & ~1)`. The latest `fmt `
before the first `data` chunk is selected. It stops at that first data chunk,
writes its pointer and size, and returns success only if a preceding format
pointer is present. It never scans later chunks to repair data-before-format.

Invalid RIFF/WAVE signatures preserve all existing output words. Once the
header is accepted, format/data outputs are cleared but the data-size output
remains unchanged until a `data` chunk is seen. A format without data leaves
the format output set and returns zero. Zero-length data can parse successfully
but is rejected by resource creation.

The portable parser uses relative offsets and explicit readable buffer bounds;
fault 1 identifies an unsupported input read. Parity tests use ordinary bounded
RIFF buffers with no original virtual-address wrap. Malformed pointer overflow,
unreadable headers, and original unbounded memory access are not successful
portable parsing cases. Neither the original parser nor this metadata parser
validates all format/data payload lengths before returning offsets; callers
must ensure a readable 18-byte format and data payload before creating/loading.

## PCM assumptions and exact duration

The creator rejects a null format, zero data size, unavailable device, or
format tag other than **1 (PCM)**. It does not independently validate channel
count, bit depth, block alignment, sample rate, or header consistency. The
external DirectSound CreateSoundBuffer service may reject such formats.

It copies the first 16 bytes of WAVEFORMATEX and forces its trailing `cbSize`
word to zero. The DirectSound descriptor has size `0x14`, flags `0xe0`, buffer
bytes equal to data-chunk size, zero reserved word, and that copied format.
Creation failure reports original line `0x2d6` with normalized error 1 and
returns zero. A successful call producing a null buffer also returns zero.

After the 56-byte pool is allocated and constructed, it is inserted at the
manager resource-list head. The exact metadata calculation is:

```
durationMilliseconds = uint32(dataBytes * 1000) / nAvgBytesPerSec
pool+0x28 = durationMilliseconds
pool+0x2c = dataBytes
```

The unsigned multiplication wraps **before** unsigned division; fractional
milliseconds truncate. The divisor is WAVEFORMATEX `+8` (`nAvgBytesPerSec`),
not merely sample rate, and the original does not verify that it matches the
other format fields. Zero divisor triggers an actual integer divide fault
after construction/list insertion, before either final metadata store.

SpeechActor reads this pool `+0x28` field when processing state 1001. An
AVFoundation estimate of MP3 duration does not prove the same value. The
currently inspected CD-rip archive has separate lossy MP3 sounds; their decoded
samples, original PCM byte counts, original WAV headers, and exact durations
cannot be established from this recovery. No original PCM identity is claimed.

## Object construction and lists

The base constructor writes vtable `0x513508`, source buffer at `+0xc`, manager
token at `+0x10`, flags `+0x14=0`, and duration `+0x28=0`. For a nonnull buffer,
it queries frequency, pan, and volume in that order through DirectSound slots
`+0x20/+0x1c/+0x18`. Frequency is copied from `+0x18` to current frequency
`+0x24` after the query, including values written by a failing query. Each
failure reports normalized error 1 at lines `0x46/0x4a/0x4d`; none prevents
later queries or completion. Unwritten words retain allocated-memory contents.

Pool construction changes vtable to `0x51350c` and initializes its voice-list
head/tail at `+0x30/+0x34` to zero. The manager resource-list head/tail occupy
manager `+4/+8`. Voice construction changes vtable to `0x513510`, writes its
parent pool at `+0x34`, and initially sets reusable `+0x30=1`.

Every list node is embedded at object `+4`: node next is object `+4`, node
previous is object `+8`, and head/tail hold **object token + 4**. Head insertion
and selected-node tail movement preserve these exact links. The host lookup
returns all 14 original words for each opaque object token; it must keep the
allocated memory and existing objects valid throughout a call.

## Allocation and selection

Duplicate allocation requires an available device, requests 56 bytes, runs
the voice constructor using the pool's original source buffer, and then calls
DirectSound DuplicateSoundBuffer (device slot `+0x14`). The constructor's
frequency/pan/volume queries occur **before duplication**, against the source
buffer. Successful duplication replaces voice `+0xc`, inserts the node at the
pool head, and finally stores the allocator's reusable argument at `+0x30`.
The selector supplies argument 1.

Allocation failure returns zero without construction. Duplication failure
reports line `0x179` with normalized error 1 and returns zero; the allocated
voice remains constructed and is not freed or inserted. The tests compare
that unlinked allocation's entire buffer too.

Selection scans head to tail. Voices with `+0x30=0` are skipped without status
queries. For eligible voices, GetStatus (buffer slot `+0x24`) considers bit 0
the playing flag. Other status bits do not independently prevent reuse. A
failed query reports line `0x88` with normalized error 1 and returns false,
so that voice is treated as stopped and selected.

The first stopped eligible voice receives raw default volume from pool
`+0x20`, raw pan from `+0x1c`, and frequency from `+0x18`, in that order.
These are raw DirectSound values; volume-table conversion and percentage pitch
are not applied during restoration. Failures do not short-circuit. Volume/pan
errors normalize to 1 at `0xaf/0xf6`; frequency errors preserve the HRESULT
at `0x12a`. Only successful frequency restoration changes voice `+0x24`.
Loop flags and other private words remain intact.

If no voice is eligible/stopped, selection allocates another duplicate.
There is no voice-count cap or playing-voice stealing in this callback.
The selected or newly allocated node is removed from its current list position
and appended at the tail. Stopped eligible voices consequently rotate in list
order; an all-playing list grows while allocation succeeds.

## Faults and host dependencies

The original selector passes a null node to list removal after allocation or
duplication returns zero. The original creator likewise inserts a null node
after allocation failure. These are actual null-memory failures, not graceful
original return-zero paths. The portable API returns zero with fault 2 after
preserving the observable earlier allocation/COM/report/object side effects.
Fault 1 represents divide-by-zero in creation; fault 3 identifies an invalid
host token lookup. These diagnostic outputs are explicit host extensions.

Device availability and identity are stable inputs during one call. The
original routines reread manager fields; concurrent device destruction or
host callbacks mutating those fields is outside this context's contract.
Allocation is external, but object construction and complete list semantics
are recovered. DirectSound, allocation failure policy, device behavior,
mixing/scheduling, and byte identity remain external boundaries.

## Validation

Run `work/test-env/bin/python Tests/compare_audio_resource_runtime.py`. It
compiles its own dylib under `work/audio-resource-agent` and maps the
fingerprint-pinned executable in Unicorn. An initialized Windows FS/SEH segment
is provided with a nonzero base and the null page remains unmapped, allowing
the original null-node accesses to fail at their actual instructions.

Tests compare every word of original/new pool and voice objects, complete
manager buffers, exact external call order/arguments/errors, and returned
tokens. Coverage includes 4,000 creator calls, 3,000 direct allocations,
5,000 selections, 5,000 RIFF parsers, 64 chained resource creations, 20
null-format calls, and 96 chained voice selections. The latter prove stopped
order and growth beyond the initial list while all statuses remain playing.
Fresh CPUs verify real original divide/null-node faults and all pre-fault
buffer changes. The original constructors, status helper, raw setters, and
list functions execute; they are not substituted by native model stubs.
