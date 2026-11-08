#ifndef CLAW_GAME_FRAME_SERVICES_H
#define CLAW_GAME_FRAME_SERVICES_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawGameFrameServiceGlobals {
    uint32_t stageDelta, playerToken, accumulatedTick, debugFlags;
    uint32_t overlayRect[4]; /*5370c8..5370d7; top is preserved/unused.*/
    uint32_t posePacket[5], lastPose[4], rankingTimer;
    uint32_t audioEnabled, overallVolume;
} ClawGameFrameServiceGlobals;
typedef struct ClawGameFrameServiceCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    /* Original automatic-storage pointers are represented by zero tokens.
       localMask bit i marks argument i; bit8 marks a temporary receiver.
       buffer j is the jth marked pointer, in argument order, then receiver.
       Shared/global payloads may also be exposed after marked buffers. */
    uint32_t localMask, bufferCount;
    void *buffers[4];
    uint32_t bufferBytes[4];
} ClawGameFrameServiceCall;
typedef struct ClawGameFrameServiceContext {
    ClawSceneActorHost host;
    ClawGameFrameServiceGlobals *globals;
    uint32_t composeMessages, fault;
} ClawGameFrameServiceContext;
typedef uint32_t (*ClawGameFrameServiceDependency)(ClawGameFrameServiceContext *, ClawGameFrameServiceCall, void *);
/* Only controls composition; no invented owner/session defaults. */
void claw_game_frame_service_defaults(ClawGameFrameServiceContext *);
/* Complete4774f0/477840/478290/46c2c0/4224f0/46ca50 control flow.
   Also exact virtual probes40af90/4750d0/4750e0/4bb030. argument is
   force-rank refresh for478290, delta for4224f0, HDC for46ca50.
   result is meaningful for477840 (processed count) and the four probes.
   Known probe and46ca50 virtual targets compose automatically.
   Fault1 missing span,2 bounded local text overflow,3 missing service;
   these safe native fault exits are outside original parity claims.
   Owner: network routines need offsets through+c04 (770words), overlay
   needs+14c; precise span reads preserve unrelated words. */
uint32_t claw_game_frame_service_entry(uint32_t function, uint32_t receiver, uint32_t argument,
                                       ClawGameFrameServiceContext *, ClawGameFrameServiceDependency, void *,
                                       uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
