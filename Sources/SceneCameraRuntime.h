#ifndef CLAW_SCENE_CAMERA_RUNTIME_H
#define CLAW_SCENE_CAMERA_RUNTIME_H
#include "SceneActorRuntime.h"
#include "SpriteGeometry.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_ORIGINAL_GAMEPLAY_VIEWPORT_WIDTH 640u
#define CLAW_ORIGINAL_GAMEPLAY_VIEWPORT_HEIGHT 480u
typedef struct ClawSceneCameraGlobals {
    uint32_t playerToken, inputDeviceToken, inputMappingToken;
    uint32_t stageDelta, menuBlocked, animationNow, animationDelta;
    uint32_t forcedX, forcedY, detachedMode, shakeUntil, detachedOwnerToken;
} ClawSceneCameraGlobals;
// Platform service identity is the original IAT slot, not a Windows address.
// For cursor/joystick writes, buffer is an adapted pointed-to word span;
// bufferToken is 0 for the discarded local cursor POINT, otherwise raw token.
// arguments omit the pointer represented by buffer. Callback preserves actual
// ordered key reads, low-bit consumption, and caller-owned device profiles.
typedef struct ClawSceneCameraPlatformCall {
    uint32_t importSlot, arguments[4], argumentCount, bufferToken;
    uint32_t *buffer;
    uint32_t bufferWords;
} ClawSceneCameraPlatformCall;
typedef uint32_t (*ClawSceneCameraPlatform)(void *, ClawSceneCameraPlatformCall);
typedef struct ClawSceneCameraHost {
    ClawSceneActorHost heap;
    void *platformContext;
    ClawSceneCameraPlatform platform;
} ClawSceneCameraHost;
// Functions46c860 input-stage;430ec0/431300 input mapping poll/reset;
//4b3490/4b3ab0 keyboard/mouse/joystick device poll/reset;486240 camera actor;
//486d70 detached follow;486d30 cancel;42d5f0 world follow;4d0a60 plane clamp;
//4d0c50 plane viewport setup. argument0/1 are worldX/Y or viewport rect token.
//430d30/430d80 restore original mapping defaults;4b3430 device mode(arg0).
// Camera callback486240 is cdecl actorToken; others follow their observed ABI.
// Fault1 missing span/service;2 invalid float/wrap metadata/native loop bound.
uint32_t claw_scene_camera_entry(uint32_t function, uint32_t receiver, uint32_t argument0, uint32_t argument1,
                                 ClawSceneCameraGlobals *, ClawSceneCameraHost, uint32_t *fault, uint32_t *result);
// Exact plane fields consumed by frozen SpriteGeometry4c96d0 projection.
uint32_t claw_scene_camera_projection(uint32_t planeToken, ClawSceneActorHost, ClawSpriteProjection *, uint32_t *fault);
#ifdef __cplusplus
}
#endif
#endif
