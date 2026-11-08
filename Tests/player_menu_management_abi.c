#include "PlayerMenuManagementRuntime.h"
#include <stddef.h>
#include <assert.h>
_Static_assert(sizeof(ClawPlayerMenuManagementContext)==88,"arm64 context ABI");
_Static_assert(sizeof(ClawPlayerMenuManagementCall)==232,"rich callback ABI");
_Static_assert(offsetof(ClawPlayerMenuManagementContext,automaticToken)==72,"scratch ABI");
int main(void){ClawPlayerMenuManagementContext c={0};uint32_t out=123;assert(!claw_player_menu_management_entry(0,0,0,0,&c,0,0,&out));assert(!c.fault&&out==123);return 0;}
