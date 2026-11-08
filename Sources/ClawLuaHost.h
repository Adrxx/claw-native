#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawLuaHost ClawLuaHost;
// All identities are session handles. No address from Lua is dereferenced.
// 0 read, 1 write, 2 built-in, 3 create, 4 destroy, 5 validate,
// 6 rename, 7 current player. Keys/values have finite native schemas.
typedef int (*ClawLuaService)(void *, int, uint32_t, const char *, double, double *, char *, size_t);
ClawLuaHost *claw_lua_create(void *, ClawLuaService);
void claw_lua_close(ClawLuaHost *);
int claw_lua_file(ClawLuaHost *, const char *, const char *, size_t);
int claw_lua_save_root(ClawLuaHost *, const char *, const char *);
int claw_lua_data_file(ClawLuaHost *, const char *, const char *, size_t);
int claw_lua_start(ClawLuaHost *);
int claw_lua_hook(ClawLuaHost *, const char *);
int claw_lua_object(ClawLuaHost *, uint32_t, const char *, const char *, uint32_t);
int claw_lua_eval(ClawLuaHost *, const char *);
const char *claw_lua_error(ClawLuaHost *);
#ifdef __cplusplus
}
#endif
