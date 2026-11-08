# Original plain actor creation

`PlainActorRuntime.h/.cpp` recover whole original4c8a20 and named4c8b90 from fingerprinted v1.0 CLAW.EXE (SHA-256350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263). This is the creator used by CaptainClawScreenPosition, rather than the animated actor creator.

The C11 API composes the shared WorldObject constructor/initializer and real sorted SceneActor insertion. It requests0x168 bytes for the plain90-word actor and0x174 bytes for93-word primary logic, installs5137b0, initializes position through the original path, and preserves callback/allocation ordering. Flag200000 invokes the initial gameplay callback immediately. Native snapshot storage reserves128 words while preserving padding outside the original allocation.

`Tests/compare_plain_actor_runtime.py` independently passed1,501 complete calls covering395 original instruction addresses. Fixtures compare complete heaps and ordered dependency calls, including zero/upper flag bits, retained insertion, constructor and allocation failures. Gameplay/resource/destruction calls in this creator fixture are explicit services. Complete plain destruction4c9e60/4c9e80 is separately recovered and compared by ActorDestruction, whose expanded suite passes3,610 calls/11,742 events/729 addresses.

Missing named registry metadata is outside the normal complete comparison domain: the original reaches an unmapped read at4c7e85 after construction; the native implementation reports fault1 before that unsafe access. A separate probe records this safety extension. It must not be described as malformed-input parity.

The native camera now uses this creator and its correct plain vtable. Original physical allocation policy, full startup configuration and whole-game behavior remain broader recovery work.
