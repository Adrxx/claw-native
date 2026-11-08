#ifndef CLAW_NATIVE_MENU_INTERFACE_H
#define CLAW_NATIVE_MENU_INTERFACE_H
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
uint32_t claw_native_menu_interface_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_math_service(const ClawCall *,uint32_t *);
ClawEntry claw_level_x87_entry(uint32_t);
#ifdef __cplusplus
}
#endif
#endif
