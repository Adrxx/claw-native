#ifndef CLAW_PLANE_RENDERER_H
#define CLAW_PLANE_RENDERER_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlaneGraphicsCall {
    uint32_t function, receiver, arguments[4], argumentCount;
    //4b9d80: arguments dstX,dstY,sourceSurface,imageKind; rectangle is source.
    //4b9ce0: arguments sourceSurface,sourceRectToken,flags,fxToken;
    //rectangle is destination. Original tile fills use0,0,01000400,plane+f4.
    //rectangleToken is0 for adapted stack rectangles, plane+60 for the live
    //interior source rectangle. Pointer is a writable four-word span; preserve
    //callback mutations/order exactly. No fabricated native stack identity.
    uint32_t rectangleToken;
    uint32_t *rectangle;
} ClawPlaneGraphicsCall;
typedef uint32_t (*ClawPlaneGraphics)(void *, ClawPlaneGraphicsCall);
typedef struct ClawPlaneRendererHost {
    ClawSceneActorHost scene;
    void *graphicsContext;
    ClawPlaneGraphics graphics;
} ClawPlaneRendererHost;
// Complete original4d0d50 tile loop. Receiver is plane86 words; target is the
// original outer surface object whose+2c is the graphics receiver.
// FFFFFFFF skips; EEEEEEEE fills; high16 manager index/low16 image ID.
// Actual4b9d80/4b9ce0 DirectDraw wrapper bodies are explicit graphics services.
uint32_t claw_plane_renderer_draw(uint32_t plane, uint32_t target, ClawPlaneRendererHost, uint32_t *fault);
// Complete original4cb9b0 plane/actor dispatch. Known container4c91d0 and
// actor4c9e00 finite wrappers compose here; image virtual+38 (4d2890 for the
// captured PID image class) calls scene.call with receiver=image,args actor,
// target. Alternative actor/container/image vtables remain explicit services.
uint32_t claw_plane_renderer_world(uint32_t world, uint32_t target, uint32_t sceneActors, ClawPlaneRendererHost,
                                   uint32_t *fault);
// Expose the already composed source actor4c9e00/virtual draw path for
// collection-owned HUD children; does not duplicate its recovered body.
uint32_t claw_plane_renderer_actor(uint32_t actor, uint32_t target, ClawPlaneRendererHost, uint32_t *fault);
// Expose the already composed container4c91d0 actor loop for cinematics.
// Captures each node.next before actor callbacks; same finite virtual routing.
uint32_t claw_plane_renderer_actor_list(uint32_t container, uint32_t target, ClawPlaneRendererHost, uint32_t *fault);
// Native returns1 on complete execution,0 for fault. Fault1 missing graph or
// service (includes original null-image dereference paths),2 native loop bound.
// Original entries are void; diagnostic support is not incidental EAX parity.
#ifdef __cplusplus
}
#endif
#endif
