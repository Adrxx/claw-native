#ifndef CLAW_MENU_DIAGNOSTIC_POLICY_RUNTIME_H
#define CLAW_MENU_DIAGNOSTIC_POLICY_RUNTIME_H
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
uint32_t claw_menu_diagnostic_policy_entry(uint32_t function, uint32_t receiver,
    const uint32_t *arguments, uint32_t argumentCount, ClawHost *host, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
