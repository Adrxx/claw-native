#ifndef CLAW_SPATIAL_GRID_RUNTIME_H
#define CLAW_SPATIAL_GRID_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSpatialGridArguments {
    uint32_t words[8];
    uint32_t count;
} ClawSpatialGridArguments;
// Raw original plane (at least45 words; +b0 grid), grid28, layer17,
// actor128 and original scene/list/node/cell tokens use SceneActorHost.
// Entries4d1fd0/4d2000 noargs;4d4b50/4d4d10(centerX,centerY);
//4d51a0(actor);4f4630(actor+88);4f46b0(left,top,right,bottom,remove);
//4f4490(left,top,right,bottom,cellWidth,cellHeight);
//4d4890(sceneActors,rectToken,sixPairTokens);4d1620(recordToken,count);
//4d2050 and4d4b00 noargs;4d4a90(deleteFlag);4f45f0 noargs.
//4cb040 world viewport/default grid sizes(width,height);4cb0e0(rectToken).
//4d2030 plane startup activation;4d4c40 grid startup activation;4d50e0
//grid dormant actor destruction. Iterator17-word entries4f4860(layer,remove),
//4f48a0(layer,left,top,right,bottom,remove),4f49c0 noargs;
//4f4680 removes a member from its recorded owning cell (memberToken).
// Lifecycle/gameplay callbacks retain original function/receiver/arguments.
// The bounded record decoder4d17e0 remains an explicit heap.call service.
// Fault1 missing span/service;2 invalid metadata/allocation/loop safety bound.
// Supported returns1; original meaningful return is written through result.
uint32_t claw_spatial_grid_entry(uint32_t function, uint32_t receiver, ClawSpatialGridArguments arguments,
                                 ClawSceneActorHost host, uint32_t *fault, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
