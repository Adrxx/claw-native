#include "ClawLuaHost.h"
extern "C" {
#include "Lua51/lua.h"
#include "Lua51/lauxlib.h"
#include "Lua51/lualib.h"
}
#include <dirent.h>
#include <cstdio>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <string>
#include <map>
#include <stdint.h>
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cmath>
struct ClawLuaHost {
    lua_State *L;
    void *context;
    ClawLuaService service;
    std::map<std::string,std::string> files;
    std::string error;
    size_t used = 0;
    int saveRoot = -1;
    int openFiles = 0;
    std::string mapName;
    std::map<std::string,std::string> dataFiles;
};
namespace {
void *allocate(void *context,void *pointer,size_t old,size_t size) {
    auto h=static_cast<ClawLuaHost *>(context);
    old=pointer?old:0;
    if(size==0){std::free(pointer);h->used-=old;return nullptr;}
    if(size>32*1024*1024 || h->used-old>32*1024*1024-size) return nullptr;
    void *result=std::realloc(pointer,size);
    if(result) h->used=h->used-old+size;
    return result;
}
ClawLuaHost *owner(lua_State *L) { return static_cast<ClawLuaHost *>(lua_touserdata(L,lua_upvalueindex(1))); }
int service(lua_State *L) {
    auto h=owner(L); double out=0; char error[512]={};
    double id=luaL_checknumber(L,2);
    if(!std::isfinite(id) || id<0 || id>UINT32_MAX || std::floor(id)!=id) return luaL_error(L,"ValueType: object handle");
    if (!h->service || !h->service(h->context,luaL_checkint(L,1),uint32_t(id),luaL_checkstring(L,3),luaL_optnumber(L,4,0),&out,error,sizeof error))
        return luaL_error(L,"%s",error[0]?error:"NotImplemented: host service");
    lua_pushnumber(L,out); return 1;
}
int proxy(lua_State *L) {
    luaL_checktype(L,1,LUA_TTABLE);
    lua_pushliteral(L,"typed game value");lua_setfield(L,1,"__metatable");
    lua_newuserdata(L,0);lua_pushvalue(L,1);lua_setmetatable(L,-2);return 1;
}
int source(lua_State *L) {
    auto h=owner(L); const char *name=luaL_checkstring(L,1); std::string folded=name;
    std::transform(folded.begin(),folded.end(),folded.begin(),[](unsigned char c){return std::toupper(c);}); auto i=h->files.find(folded);
    if(i==h->files.end()) {lua_pushnil(L); return 1;}
    if(!i->second.empty() && uint8_t(i->second[0])==27) return luaL_error(L,"UnsupportedExecution: binary Lua chunk %s",name);
    if(luaL_loadbuffer(L,i->second.data(),i->second.size(),("@"+folded).c_str())) return lua_error(L);
    return 1;
}
int bit(lua_State *L) {
    int op=lua_tointeger(L,lua_upvalueindex(1));
    uint32_t a=uint32_t(int64_t(luaL_checknumber(L,1))), b=uint32_t(int64_t(luaL_optnumber(L,2,0)));
    uint32_t v=a;
    if(op==0 || op==1 || op==2) for(int i=2;i<=lua_gettop(L);++i) {
        b=uint32_t(int64_t(luaL_checknumber(L,i))); v=op==0?v&b:op==1?v|b:v^b;
    }
    if(op==3) v=~a;
    if(op==4) v=a<<(b&31);
    if(op==5) v=a>>(b&31);
    if(op==6) v=uint32_t(int32_t(a)>>(b&31));
    lua_pushnumber(L,int32_t(v));return 1;
}
void budget(lua_State *L,lua_Debug *) { luaL_error(L,"ScriptLimit: callback instruction budget exceeded"); }
int finish(ClawLuaHost *h,int status) {
    if(status) {const char *e=lua_tostring(h->L,-1);h->error=e?e:"LuaError";lua_pop(h->L,1);return 0;} return 1;
}
int traceback(lua_State *L) {
    std::string message=lua_tostring(L,1)?lua_tostring(L,1):"LuaError";
    lua_Debug frame;
    for(int depth=1;depth<12 && lua_getstack(L,depth,&frame);++depth) {
        lua_getinfo(L,"Sl",&frame);
        if(frame.currentline>0) message+="\n"+std::string(frame.short_src)+":"+std::to_string(frame.currentline);
    }
    lua_pushlstring(L,message.data(),message.size());return 1;
}
int call(ClawLuaHost *h,int args=0,int returns=0) {
    auto previous=lua_gethook(h->L);int mask=lua_gethookmask(h->L),count=lua_gethookcount(h->L);
    // City's domain effect performs twelve complete indexed-palette transforms
    // in one callback. Keep a finite limit that admits this shipped workload.
    lua_sethook(h->L,budget,LUA_MASKCOUNT,5000000);
    int handler=lua_gettop(h->L)-args;
    lua_pushcfunction(h->L,traceback);lua_insert(h->L,handler);
    int result=finish(h,lua_pcall(h->L,args,returns,handler));
    lua_remove(h->L,handler);
    lua_sethook(h->L,previous,mask,count);return result;
}
#include "ClawLuaFiles.inc"
const char bootstrap[] =
#include "ClawLuaBootstrap.inc"
#include "ClawLuaBindings.inc"
;
}
extern "C" ClawLuaHost *claw_lua_create(void *context,ClawLuaService callback) {
    auto h=new ClawLuaHost{nullptr,context,callback,{},{}};
    h->L=lua_newstate(allocate,h);
    if(!h->L) {delete h;return nullptr;} auto L=h->L;
    luaopen_base(L);lua_settop(L,0);
    luaopen_table(L);lua_settop(L,0);luaopen_string(L);lua_settop(L,0);luaopen_math(L);lua_settop(L,0);
    // No OS, process streams, debug, native loader or downloaded core is installed.
    for(auto key:{"dofile","loadfile","loadstring","load","collectgarbage","newproxy"}) {lua_pushnil(L);lua_setglobal(L,key);}
    lua_pushlightuserdata(L,h);lua_pushcclosure(L,service,1);lua_setglobal(L,"_host");
    lua_pushlightuserdata(L,h);lua_pushcclosure(L,source,1);lua_setglobal(L,"_source");
    installFiles(h);
    lua_pushcfunction(L,proxy);lua_setglobal(L,"_proxy");
    lua_newtable(L);const char *names[]={"band","bor","bxor","bnot","lshift","rshift","arshift"};
    for(int i=0;i<7;++i){lua_pushinteger(L,i);lua_pushcclosure(L,bit,1);lua_setfield(L,-2,names[i]);}
    lua_setglobal(L,"bit");
    if(luaL_loadbuffer(L,bootstrap,sizeof(bootstrap)-1,"@native-lua-host") || !call(h)) {claw_lua_close(h);return nullptr;}
    return h;
}
extern "C" void claw_lua_close(ClawLuaHost *h){if(h){lua_close(h->L);if(h->saveRoot>=0)close(h->saveRoot);delete h;}}
extern "C" int claw_lua_file(ClawLuaHost *h,const char *name,const char *data,size_t size){
    if(!h || size>1024*1024) return 0;
    h->files[name]=std::string(data,size);return 1;
}
extern "C" int claw_lua_start(ClawLuaHost *h){
    auto L=h->L;lua_getglobal(L,"_start");lua_newtable(L);int i=0;
    for(auto &f:h->files){lua_pushstring(L,f.first.c_str());lua_rawseti(L,-2,++i);}
    return call(h,1);
}
extern "C" int claw_lua_hook(ClawLuaHost *h,const char *hook){lua_getglobal(h->L,"_hook");lua_pushstring(h->L,hook);return call(h,1);}
extern "C" int claw_lua_object(ClawLuaHost *h,uint32_t handle,const char *logic,const char *event,uint32_t other){
    auto L=h->L;lua_getglobal(L,"_dispatch");lua_pushnumber(L,handle);lua_pushstring(L,logic);lua_pushstring(L,event);lua_pushnumber(L,other);return call(h,4);
}
extern "C" int claw_lua_eval(ClawLuaHost *h,const char *text){
    if(luaL_loadstring(h->L,text)) return finish(h,1);return call(h);
}
extern "C" const char *claw_lua_error(ClawLuaHost *h){return h?h->error.c_str():"Lua allocation failure";}

extern "C" int claw_lua_save_root(ClawLuaHost *h,const char *path,const char *map){
    int fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW);if(fd<0)return 0;
    if(h->saveRoot>=0)close(h->saveRoot);h->saveRoot=fd;h->mapName=map;return 1;
}
extern "C" int claw_lua_data_file(ClawLuaHost *h,const char *path,const char *bytes,size_t size){
    if(size>1024*1024)return 0;h->dataFiles[path]=std::string(bytes,size);return 1;
}
