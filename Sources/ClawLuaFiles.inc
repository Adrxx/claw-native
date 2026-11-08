// Text-only file capabilities for a single custom-map session. Never invoke a
// shell, resolve a Lua chunk from saved data, or follow filesystem links.
namespace {
constexpr long fileLimit=1024*1024;
struct MapFile { FILE *stream; bool writable; bool append; ClawLuaHost *host; };
int fileError(lua_State *L,const char *message) {lua_pushnil(L);lua_pushstring(L,message);lua_pushinteger(L,errno);return 3;}
MapFile *fileValue(lua_State *L) {
    auto f=static_cast<MapFile *>(luaL_checkudata(L,1,"Claw.map.file"));
    luaL_argcheck(L,f->stream!=nullptr,1,"attempt to use a closed file");return f;
}
int closeFile(lua_State *L) {
    auto f=fileValue(L);int result=fclose(f->stream);f->stream=nullptr;--f->host->openFiles;
    if(result) return fileError(L,"File close failed");lua_pushboolean(L,1);return 1;
}
int collectFile(lua_State *L) {auto f=static_cast<MapFile *>(luaL_checkudata(L,1,"Claw.map.file"));if(f->stream){fclose(f->stream);f->stream=nullptr;--f->host->openFiles;}return 0;}
int readFile(lua_State *L) {
    auto f=fileValue(L);int count=lua_gettop(L);if(count==1){lua_pushliteral(L,"*l");count=2;}
    luaL_argcheck(L,count<=65,1,"too many read formats");
    luaL_checkstack(L,count+4,"file read results");
    int results=0;
    for(int i=2;i<=count;++i) {
        std::string text;bool ok=true;
        if(lua_type(L,i)==LUA_TNUMBER) {
            int n=luaL_checkint(L,i);luaL_argcheck(L,n>=0 && n<=fileLimit,i,"read exceeds file limit");
            if(n==0){int c=fgetc(f->stream);ok=c!=EOF;if(ok)ungetc(c,f->stream);}
            else {text.resize(n);text.resize(fread(&text[0],1,n,f->stream));ok=!text.empty();}
        } else {
            const char *format=luaL_checkstring(L,i);
            if(!strcmp(format,"*n")){double n;if(fscanf(f->stream,"%lf",&n)==1){lua_pushnumber(L,n);++results;continue;}ok=false;}
            else {
                bool all=!strcmp(format,"*a");
                luaL_argcheck(L,all || !strcmp(format,"*l") || !strcmp(format,"*line"),i,"invalid read format");
                int c;while((c=fgetc(f->stream))!=EOF) {if(!all && c=='\n')break;text+=char(c);if(text.size()>fileLimit)return luaL_error(L,"File read exceeds limit");}
                ok=all || c!=EOF || !text.empty();
                if(!all && !text.empty() && text.back()=='\r')text.pop_back();
            }
        }
        if(ok)lua_pushlstring(L,text.data(),text.size());else lua_pushnil(L);
        ++results;if(!ok)break;
    }
    return results;
}
int writeFile(lua_State *L) {
    auto f=fileValue(L);if(!f->writable)return fileError(L,"File is read-only");
    for(int i=2;i<=lua_gettop(L);++i){if(f->append)fseek(f->stream,0,SEEK_END);size_t n;const char *s=luaL_checklstring(L,i,&n);long p=ftell(f->stream);if(p<0 || n>fileLimit || p>fileLimit-long(n))return fileError(L,"File write exceeds limit");if(fwrite(s,1,n,f->stream)!=n)return fileError(L,"File write failed");}
    lua_pushboolean(L,1);return 1;
}
int seekFile(lua_State *L) {
    auto f=fileValue(L);const char *mode=luaL_optstring(L,2,"cur");double offset=luaL_optnumber(L,3,0);
    int whence=!strcmp(mode,"set")?SEEK_SET:!strcmp(mode,"cur")?SEEK_CUR:!strcmp(mode,"end")?SEEK_END:-1;
    luaL_argcheck(L,whence!=-1,2,"invalid seek mode");luaL_argcheck(L,std::isfinite(offset)&&floor(offset)==offset&&fabs(offset)<=fileLimit,3,"invalid seek offset");
    long old=ftell(f->stream);if(fseek(f->stream,long(offset),whence))return fileError(L,"File seek failed");long p=ftell(f->stream);
    if(p<0 || p>fileLimit){fseek(f->stream,old,SEEK_SET);return fileError(L,"File seek exceeds limit");}lua_pushnumber(L,p);return 1;
}
int flushFile(lua_State *L) {if(fflush(fileValue(L)->stream))return fileError(L,"File flush failed");lua_pushboolean(L,1);return 1;}
// Traverse only directory descriptors, rejecting links at every component.
int mapOpen(int root,const std::string &path,int flags) {
    int dir=dup(root);if(dir<0)return -1;size_t at=0;
    while(true){auto end=path.find('/',at);std::string part=path.substr(at,end-at);if(end==std::string::npos){int fd=openat(dir,part.c_str(),flags|O_NOFOLLOW|O_NONBLOCK,0600);close(dir);return fd;}
        int next=openat(dir,part.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW);close(dir);if(next<0)return -1;dir=next;at=end+1;}
}
int openFile(lua_State *L) {
    auto h=owner(L);if(h->openFiles>=64)return fileError(L,"Too many open map files");size_t length;const char *raw=luaL_checklstring(L,1,&length);std::string path(raw,length);
    std::replace(path.begin(),path.end(),'\\','/');
    auto fold=[](std::string s){std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return std::toupper(c);});return s;};
    std::string prefix="CUSTOM/"+fold(h->mapName)+"/";
    if(fold(path).compare(0,7,"CUSTOM/")==0){if(fold(path).compare(0,prefix.size(),prefix))return fileError(L,"Path denied: another map");path=path.substr(prefix.size());}
    if(path.empty() || path.size()>240 || path.find('\0')!=std::string::npos || path.find(':')!=std::string::npos)return fileError(L,"Path denied");
    size_t at=0;while(true){auto end=path.find('/',at);auto part=path.substr(at,end-at);if(part.empty()||part=="."||part=="..")return fileError(L,"Path denied");if(end==std::string::npos)break;at=end+1;}
    path=fold(path);
    std::string mode=luaL_optstring(L,2,"r");mode.erase(std::remove(mode.begin(),mode.end(),'b'),mode.end());
    bool write=mode!="r";int flags=mode=="r"?O_RDONLY:mode=="r+"?O_RDWR:mode=="w"?O_WRONLY|O_CREAT:mode=="w+"?O_RDWR|O_CREAT:mode=="a"?O_WRONLY|O_CREAT|O_APPEND:mode=="a+"?O_RDWR|O_CREAT|O_APPEND:-1;
    if(flags==-1)return luaL_argerror(L,2,"invalid file mode");
    // Resources are immutable. Root-level text files may seed an independent
    // writable overlay (the shipped Tower score files use this convention).
    auto resource=h->dataFiles.find(path);
    if(write && path.find('/')!=std::string::npos)return fileError(L,"Path denied: resource is read-only");
    if(write && h->saveRoot>=0){
        DIR *directory=fdopendir(dup(h->saveRoot));if(!directory)return fileError(L,"Save directory unavailable");
        rewinddir(directory);int entries=0;while(auto entry=readdir(directory)){if(strcmp(entry->d_name,".") && strcmp(entry->d_name,".."))++entries;}closedir(directory);
        struct stat existing;if(entries>=128 && fstatat(h->saveRoot,path.c_str(),&existing,AT_SYMLINK_NOFOLLOW))return fileError(L,"Map save file count limit");
    }
    int fd=h->saveRoot<0?-1:mapOpen(h->saveRoot,path,flags);
    if(fd<0 && !(mode=="r" && errno==ENOENT && resource!=h->dataFiles.end()))return fileError(L,"File unavailable or path denied");
    FILE *stream=nullptr;
    if(fd>=0){struct stat info;if(fstat(fd,&info)||!S_ISREG(info.st_mode)||info.st_nlink!=1||info.st_size>fileLimit){close(fd);return fileError(L,"Unsafe or oversized file");}if(mode[0]=='w' && ftruncate(fd,0)){close(fd);return fileError(L,"File truncate failed");}stream=fdopen(fd,mode.c_str());if(!stream)close(fd);}
    else {stream=tmpfile();if(stream){fwrite(resource->second.data(),1,resource->second.size(),stream);rewind(stream);}}
    if(!stream)return fileError(L,"File open failed");
    auto f=static_cast<MapFile *>(lua_newuserdata(L,sizeof(MapFile)));*f={stream,write,mode[0]=='a',h};++h->openFiles;luaL_getmetatable(L,"Claw.map.file");lua_setmetatable(L,-2);return 1;
}
int linesFile(lua_State *L) {fileValue(L);lua_getglobal(L,"_fileLines");lua_pushvalue(L,1);lua_call(L,1,1);return 1;}
void installFiles(ClawLuaHost *h) {
    auto L=h->L;luaL_newmetatable(L,"Claw.map.file");lua_pushvalue(L,-1);lua_setfield(L,-2,"__index");
    for(auto item:{std::make_pair("read",readFile),{"write",writeFile},{"seek",seekFile},{"lines",linesFile},{"flush",flushFile},{"close",closeFile},{"__gc",collectFile}}){lua_pushcfunction(L,item.second);lua_setfield(L,-2,item.first);}lua_pushliteral(L,"map file");lua_setfield(L,-2,"__metatable");lua_pop(L,1);
    lua_newtable(L);lua_pushlightuserdata(L,h);lua_pushcclosure(L,openFile,1);lua_setfield(L,-2,"open");lua_setglobal(L,"io");
}
}
