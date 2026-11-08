# Original PCM loading and cleanup

`Sources/AudioPCMTransfer.h/.cpp` recover file-byte acquisition/release,
PCM transfer, manager and sound load wrappers, and sound/pool teardown from
original v1.0 `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The new implementation composes the frozen AudioResourceRuntime parser and
creator. It does not duplicate those algorithms or change AudioEvents,
SpeechActor, native UI, or a playback backend.

| Original entry | Portable API |
| --- | --- |
| `0x4b7ab0` | `claw_audio_read_file`: seek, whole read, retry/reopen ordering. |
| `0x4b61c0` | `claw_audio_acquire_file`: mapped archive, cached bytes, allocation/read. |
| `0x4b6230` | `claw_audio_release_file`: cached allocation release. |
| `0x4b44f0` | `claw_audio_transfer_pcm`: Lock, split byte copies, Unlock. |
| `0x4b4a20` | `claw_audio_load_pcm`: parse/create/transfer, teardown on normal failure. |
| `0x4c8850` | `claw_audio_load_sound`: acquire, scene manager, load, cache release. |
| `0x4c88b0` | `claw_audio_unload_sound`: conditional manager teardown and sound reset. |
| `0x4b4ae0` | `claw_audio_destroy_resource`: fades, source buffer, voices and pool. |

Teardown includes the relevant original destructor, list, and matching-fade
paths through `0x4b4c80`, `0x4b5270`, `0x4b4240/0x4b4260`, `0x4b43e0`,
`0x4b46e0/0x4b4700`, and `0x4b3d70`. True boundaries and parameter flow were
checked in the original assembly. In particular, Ghidra's body for
`0x4b44f0` does not correctly represent its stack output parameters; the
recovery uses the actual Lock/copy/Unlock instructions.

## File bytes and retry behavior

A file/resource object retains size at `+0x14`, cached allocation at `+0x18`,
archive token at `+0x24`, and file offset at `+0x28`. Its archive retains base
file offset at `+0xc`, stream token at `+0x18`, and mapped memory base at `+0x20`.

Acquisition first checks the archive mapping. With a nonzero mapping it returns
`fileOffset - archiveBaseOffset + mappedBase`, using wrapping 32-bit arithmetic.
It performs no allocation/read and leaves the cached allocation unchanged.
Without a mapping, an existing cached allocation is returned directly. Only
then is zero size rejected. Otherwise the exact file size is allocated and
stored in the cache before reading. Allocation failure returns zero. A failed
whole read frees the allocation and writes cache zero.

The original stream read requires nonzero byte count. It seeks with whence 0;
each failed seek invokes stream vtable `+8` retry/reopen, and then repeats seek
if that callback returns nonzero. Retry may replace stream `+0xc` FILE handle,
so subsequent operations use the current handle. On a successful seek, it
calls fread with item size 1 and the full byte count. A partial/failed read
invokes retry and repeats the full read into the same destination, without an
additional seek in this routine. It never advances a partial-read destination.
It returns the requested count only for a complete read, otherwise zero after
retry is refused. The original has no fixed retry limit; host callbacks must
eventually succeed or refuse when appropriate.

Release frees only the file object's cached `+0x18` allocation, writes it zero,
and returns 1. It does not unmap the archive. If a stale cache exists while a
mapping wins acquisition, sound load still releases that cache afterward.

OS stdio seek/read, retry/reopen internals, allocation/free, and mapping setup
are explicit host services. The module recovers their caller behavior and
state, not platform filesystem or CRT internals.

## PCM transfer

Transfer returns zero immediately when the audio device is unavailable.
Otherwise it calls DirectSound buffer Lock (vtable `+0x2c`) with offset 0,
requested data size, and flags 1. The service returns first pointer/byte count
and second pointer/byte count. Lock failure reports original line `0x200`
with normalized error 1, performs no copy or Unlock, and returns zero.

On success, the original copies the first span from source, then the second
span from source plus first byte count. Both copies include complete 32-bit
words followed by remaining tail bytes; the resulting PCM bytes are preserved
exactly. Empty spans perform no memory access. The service receives the same
two pointers/counts during Unlock (vtable `+0x4c`). Successful Unlock returns
1; failure reports line `0x213` with normalized error 1 and returns zero.
PCM copies occur before Unlock, including when Unlock subsequently fails.

The portable host provides tokens and readable/writable spans for the Lock
pointers. The copy domain requires distinct source/destination storage and
valid bounded spans, as expected for file PCM and DirectSound buffers. The
original trusts service lengths; the native implementation reports fault 4
for totals exceeding the supplied source data size instead of overreading.
Shorter returned totals retain the original copy behavior. General overlapping
memory or malformed service pointers are not claimed equivalent.

## Manager and sound loading

Manager loading rejects null bytes or an unavailable device before parsing.
It invokes the recovered RIFF parser, then the recovered PCM creator. A normal
failure returns zero. Once creation succeeds, it transfers the parsed data
chunk. Normal transfer failure destroys the created pool and returns zero;
successful transfer returns the pool. The original wrapper's extra second
argument is not used in this path.

Sound load acquires file bytes first. Acquisition failure returns zero and
preserves sound `+0x10`. If scene `+0x20` has no manager, it releases the file
cache and returns zero while also preserving sound `+0x10`. When a manager
exists, its load result is stored at sound `+0x10`, including zero for normal
failure or an unavailable device. The file cache is then released, and the
wrapper returns whether the pool is nonzero. It does not first destroy an old
pool held by that sound field.

Sound unload requires both a nonzero sound pool and a nonzero scene manager.
It invokes resource destruction and then clears sound `+0x10`. With an absent
manager the old pool field remains. With a present but disabled device,
resource destruction makes no changes, but the wrapper still clears the sound
pool field. This precise disabled-device behavior is preserved.

`sourceBytes` is an explicit host bound for native parsing/loading. The original
manager API receives only a byte pointer and trusts its RIFF contents. Native
out-of-bound format/data spans produce fault 4. Faults propagate without
pretending the original returned normally or running normal failure cleanup.
Valid loader comparisons execute the complete original wrappers and callees.

## Resource teardown order

With an available device, resource destruction does the following:

1. Scan manager fade-list head to tail. Remove every fade whose `+0x10` pool
   token matches, regardless of its type at `+0xc`. Write the generic fade
   vtable `0x513518` before freeing each match. Other fades remain in order.
2. Release the pool's source buffer through IUnknown slot `+8` and clear
   pool `+0xc`. Release's return value is ignored.
3. Remove the pool's embedded node from the manager resource list.
4. Run the pool destructor: delete duplicate voices in current head order.
   Each voice buffer is released and cleared; its node is removed; its
   destructor leaves base vtable `0x513508`; the voice is freed.
5. The pool destructor leaves base vtable `0x513508`, then the pool is freed.

There are no explicit Stop calls in this cleanup path. Device/mixer effects of
Release remain external. With an unavailable device, the teardown routine
returns without modifying objects, lists, or services.

The manager fade list is exposed separately in `ClawAudioPCMContext` because
the frozen resource context already contains its resource list. Intrusive
links retain original object-token-plus-four semantics. Teardown assumes valid
objects created by the recovered pool/voice constructors, stable device state,
and one manager matching any nonzero scene `+0x20` token. Arbitrary vtable
types or concurrent manager changes are outside this bounded API contract.

## Integration and identity

The host reuses `ClawAudioResourceHost` for object lookup, allocator, creator
and metadata services, then adds byte lookup, free, seek/read/retry, and
DirectSound Lock/Unlock/Release callbacks. Byte lookup supports subranges of
the source WAV and writable Lock regions. Object lookup also supplies the raw
file, archive, stream, sound, and scene buffers. Host storage must remain
valid while a routine accesses it.

This module establishes byte transfer and cleanup behavior for supplied PCM
and exact source metadata. The parent obtained the original disc and extracted
its `DATA/CLAW.REZ` (118,033,115 bytes), SHA-256
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
Additional cases read actual WAVs from that extraction. The suite verifies the
archive hash, records the tested WAV/PCM hashes, and proves the original/native
loader preserves those payloads. Extraction/provenance and bundle integration
remain parent-owned; the suite does not independently re-extract the archive
or prove all assets' identity. Speaker output, mixing, device timing,
top-level scheduling, and native UI behavior remain separate checks.

## Verification

Run `work/test-env/bin/python Tests/compare_audio_pcm_transfer.py`. Its private
helper `Tests/audio_pcm_original.py` fingerprint-verifies the executable and
provides a Windows FS/SEH segment with the null page unmapped. The script
compiles only a private dylib under `work/audio-pcm-agent`, linking the frozen
AudioResourceRuntime source read-only.

The original file helpers, retry caller, parser, creator, memory copies,
manager/sound wrappers, list operations, and destructors all execute. Only
allocator/free, external file seek/read/retry, DirectSound COM, and error
reporting are adapted. Tests compare complete file/archive/stream/sound/scene,
pool/voice/fade, and manager buffers, all source/cache/locked bytes, and exact
ordered service arguments. Callback-time snapshots compare complete object
and manager-list state; Unlock snapshots also compare the actual copied bytes
at that boundary, including failure.

Checks cover 2,000 acquisition/release pairs, 2,000 direct reads, 3,000 split
transfers, 2,000 manager loader calls, 2,000 sound load/unload pairs, and 1,500
teardowns. Directed cases cover missing versus disabled managers, stale cached
allocations with mapped acquisition, copying before Unlock failure, and
unload behavior with disabled devices. Freed memory is retained by the test
allocator only to inspect destructor output; external heap reuse is not part
of this comparison.

The original-disc addition covers 12 full WAVs, including landing, footsteps,
idle speech, weapon, game effects, level triggers, and the stereo perfect-score
sound. It exercises all seven observed PCM format combinations: mono 8-bit at
11,025, 22,050, and 22,255 Hz; mono 16-bit at 11,025, 22,050, and 44,100 Hz;
stereo 8-bit at 22,050 Hz. There are 144 actual-disc manager/sound loader cases
with three split positions, successful/failing Unlock, mapped/cached file
acquisition, exact metadata duration, all payload bytes, and teardown. Input
and PCM hashes/durations are saved in
`work/audio-pcm-agent/original-disc-pcm-cases.json`.
