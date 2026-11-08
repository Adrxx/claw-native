# Original CRT random state and TLS lifecycle

`CRTRandomRuntime` recovers whole original v1.0 `4a3040` (srand), `4a3050` (rand), `4a7da0` (thread defaults), `4a7dc0` (current CRT thread getter), `4a7d40` (CRT TLS initialization), and `4a7e40` (thread cleanup). It composes frozen `claw_world_loot_next_random` for the already verified numeric update. It creates no scalar shadow of the original RNG.

Original: `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private bounded decompiles, actual instruction callers, original import table, seed profiles, original golden outputs, and measured verification are under `work/crt-random-agent/`. Ghidra entry bodies are 13/45/19/122/92/176 bytes respectively; the private headless logs contain no script error.

## Shared state and API

`claw_crt_random_entry(function, arguments, count, context, dependency, user, result)` uses the existing raw `ClawSceneActorHost` and a borrowed `ClawCRTRandomGlobals`. Its single global is original `52edd8`, the TLS index, with pinned initial value `FFFFFFFF`. All entry points are cdecl. srand takes one UInt32; rand, getter, and CRT TLS initializer take none; thread-default initialization and cleanup take one thread token (cleanup accepts zero to select the current thread).

The source allocates **0x74 bytes / 29 words** per CRT thread with `calloc(1,0x74)`. Random access uses the live word at **+14 / word 5**. The default initializer writes locale token `5312e8` at +50 before writing seed 1 at +14, preserving all other words. Successful TLS setup then stores `GetCurrentThreadId()` at +0 and `FFFFFFFF` at +4. Random access requires six addressable words; default initialization/cleanup reach word 20; actual allocated objects remain 29 words.

Both srand and rand first execute the **whole getter**. It saves `GetLastError`, calls `TlsGetValue` with the current live index, and either returns the existing object or lazily allocates, binds, initializes, and identifies a new one. It restores the saved error before returning. If allocation or binding fails, it calls original fatal runtime service `4a4860(16)`; it does not free an invented rollback object. If a test transport deliberately returns from that normally fatal service, source fallthrough restores the error and returns the captured allocation token (possibly zero). A subsequent null seed dereference is guarded without inventing normal completion.

rand writes:

```
seed = (seed * 214013 + 2531011) modulo 2^32
result = (seed >> 16) & 0x7fff
```

Zero is a valid seed. High-bit values and multiplication overflow retain their original unsigned bit patterns. The thread token is srand's incidental EAX; rand's 0..32767 and the getter's token are meaningful. The initializer returns 1 or 0. The other source-void entries expose incidental EAX solely to allow exact original comparisons.

Cleanup gates on TLS index != FFFFFFFF. It selects its explicit object or the current TLS value, then calls free for nonzero fields +24, +28, +30, +38, +40, +44 in that order. It frees +50 whenever it differs from `5312e8` (including null), then frees the thread itself. Finally it calls `TlsSetValue(current live index,0)`, rereading the index after prior services. It does not call TlsFree or clear unrelated thread words.

## Native composition recipe

1. Borrow one live thread object for the original gameplay thread. Native TLS/heap transports initialize it through source `4a7d40` or lazy `4a7dc0`, with the source global index and actual 29-word allocation. Another native thread should have its own source thread object; the RNG is shared among consumers on a thread, not process-global across every thread.
2. Route ordinary native `nextRandom()` / source `4a3050` to this module. Route SceneFade's explicit `4a7dc0` dependency to the same getter. SceneFade's frozen WorldLoot LCG then mutates that returned object's +14 directly. WorldLoot, NPCs, speech, loot, effects, and fades must not maintain independent seeds.
3. Route the frozen `SinglePlayerSceneRuntime` `46aeb0` service call `4a3040(0x1b3cf)` **at its existing source boundary**. Preserve all subsequent original creation/controller/draw order. Do not reseed at the first visible frame after constructors have consumed random values.
4. Share the returned raw seed alias with SaveFileRuntime's explicit `4a3040`/`4a3050` services when that graph is integrated. Its own source calls can reseed the same gameplay thread.

Rich services use exact original **IAT slot identities**, verified from the original PE import table:

| Slot / entry | External service | Arguments |
|---|---|---|
| `546b0c` | GetLastError | none |
| `546a7c` | TlsGetValue | TLS index |
| `546a84` | TlsSetValue | TLS index, thread token or zero |
| `5469c0` | GetCurrentThreadId | none |
| `546ab8` | SetLastError | saved error |
| `546a90` | TlsAlloc | none |
| `4adf50` | calloc | 1, 0x74 |
| `4a49b0` | free | pointer |
| `4a7b90` | CRT lock initialization | none |
| `4a4860` | fatal runtime error | 16 |

A native Mac/iPad host supplies these identified TLS, allocation, error-register, and fatal transports; no Windows OS implementation is claimed by this module. Their ordered calls, arguments, stores, and live alias changes are preserved. Host.call fallback has the same raw argument lists. Set context fault to stop at a nonreturning/unsupported external service. Fault 1 guards a missing span/service, fault 2 rejects argument counts; callback fault codes persist. Unsupported functions return zero without mutating state/result. Context creation/default setup makes no random draw or automatic reseed.

## Source seed callsites and remaining startup order

There are **four** verified direct srand sites:

| Call instruction | Verified containing source entry | Seed / following behavior |
|---|---|---|
| `425795` | application startup `425730` | after successful `4b8280`: timeGetTime (`546df0`), then GetTickCount (`546a24`), wrapping 32-bit ADD, logical SHR 1 |
| `42b502` | constructor `42b4b0` | result of `4a3b10(NULL)` |
| `46af09` | level startup `46aeb0` | literal **0x1b3cf / 111567** |
| `49c03d` | byte-transform wrapper `49c030` | receiver +44; then `49bfb0` consumes exactly one CRT rand; following bytes use deterministic `49c000` instead |

The level seed follows original writes to owner +14, +44/+48/+764 and globals `538418`, `54316c`, `537210`, `53c9c0`, `5349dc`. It precedes viewport/save-path handling, level resources, world loading, actor creation, player initialization, auxiliary controllers, and further visible startup. It overwrites the earlier application clock seed when that level path executes.

Twenty **actual original caller prefixes** confirm the application and level boundaries, including wrapping clock pairs and existing/lazy threads. These execute the actual caller instructions through the seed return, capture their full raw frame at srand entry, and compare the complete recovered srand/getter against that frame. They are not a port or full execution claim for application/level startup.

Complete pregame random consumption is **not traced here**. Source examples that must retain caller order include Officer `462410`'s sound-choice draw, initial enemy state-controller draws, and type2 fade `4ed0b0`'s 2000 initialization draws. `42b4b0` and the byte-transform caller sites add reseeding dependencies. SaveFileRuntime is being recovered independently and composes the same RNG service; its invocation within startup remains separate. The source-profile file's large raw E8 reference candidate list is an analysis inventory, not proof that every candidate executes before gameplay. A correct seed alone does not establish first-frame identity if transport/loading/activation skips or reorders source calls.

## Verification

Run:

```
work/test-env/bin/python Tests/compare_crt_random_runtime.py
work/test-env/bin/python work/crt-random-agent/run-sanitizers.py
```

Measured: **6425 complete original RNG/TLS calls**, **19366 ordered full snapshots** of the 65536-byte raw heap and 196608-byte global image, 768 additional shared WorldLoot seed-state checks, 20 actual seed caller prefixes, two original null-thread prefixes, and six stopped fatal-service prefixes. The seed set includes zero, retail/default/extreme values, all 32 individual bits, and 128 independent UInt32 values, with retained draw histories and switched thread objects. It does not enumerate all 2^32 possible seeds.

Tests compare meaningful and incidental EAX, complete state and service ordering, last-error preservation, allocation/index/binding failures, callback alias changes, selective cleanup, and mutable cleanup callbacks. Fatal-return tests are explicitly alternate transport profiles rather than retail process-termination claims.

Strict C11 import passes. C++ ASAN/UBSAN replays 147 sampled original-verified histories / 532 recorded transport calls. A private Swift importer/native ASAN smoke runs the actual C11 API with a 29-word raw thread, source initialization/cleanup, the original-executed 16-output retail golden sequence, and shared WorldLoot/SceneFade-compatible seed pointer. Physical OS thread services, game startup, rendering, device acceptance, and full gameplay parity remain outside this evidence.

Only additive source/header, unique tests/helper, this document, and private work were written. No frozen/root/shared host, bridge, project, or device files changed.
