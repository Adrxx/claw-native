#ifndef CLAW_MESSAGE_DRAWING_RUNTIME_H
#define CLAW_MESSAGE_DRAWING_RUNTIME_H
#include "GameFrameServices.h"
#include "PlayerDeathServices.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef ClawGameFrameServiceCall ClawMessageDrawingCall;
typedef struct ClawMessageDrawingContext {
    ClawSceneActorHost scene;
    uint32_t emptyStringToken; /* shared CString empty data identity, normally52e1c4 */
    uint32_t composeStrings;   /* frozen4f6449/4f6584;0 keeps exact rich services */
    uint32_t textLimit;        /* host safety bound only,0→65536; not original buffer size */
    uint32_t fault;
} ClawMessageDrawingContext;
typedef uint32_t (*ClawMessageDrawingDependency)(ClawMessageDrawingContext *, ClawMessageDrawingCall, void *);
/* Controls only CString composition/host guard; no config/font/timer defaults. */
void claw_message_drawing_defaults(ClawMessageDrawingContext *);
/* Whole4226b0 thiscall(config56bytes, signed requestedLines,HDC,RECT*,flags).
   args[2] is the raw RECT token; if0, localRect may supply its normalized
   automatic-storage16bytes, as in frozen46ca50. nullptr withtoken0 remains a
   genuine null RECT passed through to the physical DrawTextA service.
   Live global534ef8 is host-addressable raw bytes. Source newline5250d8 is
   appended between requested iterations, preserving missing-node asymmetry.
   The routine performs no font-height/layout/wrapping math: caller RECT/flags
   and physical GDI semantics own it. Direct slots54691c SelectObject and
   546d30 DrawTextA are explicit named address services; saved nonzero font is
   restored even forFFFFFFFF. DrawTextA return is ignored; meaningful result1.
   Local CString service receiver is0/mask256/buffer4; locked-copy4f66cc uses
   the same convention. DrawTextA local RECT is arg3/mask8/buffer16; global
   text bytes are an extra payload after marked buffers, with raw arg1 token.
   Return1 completed,0 unsupported/fault; result is original meaningful EAX.
   Fault1 missingspan,2 host text guard,3 missingservice,4 invalidargument shape.
   Clear fault before each call. Timer4224f0/queue creation/removal remain the
   existing GameFrameServices/PlayerStartupRuntime responsibilities. */
uint32_t claw_message_drawing_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                    uint32_t argumentCount, uint32_t *localRect, ClawMessageDrawingContext *,
                                    ClawMessageDrawingDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
