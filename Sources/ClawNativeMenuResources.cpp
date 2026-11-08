#include "ClawNativeMenuResources.h"
#include <string>
uint32_t claw_native_menu_substring(ClawHost *host,uint32_t token,uint32_t needle,uint32_t *out) {
    if (!host || !host->bytes || !out) return 0;
    auto read=[host](uint32_t start,std::string &text) {
        for (uint32_t offset=0;offset<0x100000;++offset) {
            if (start>UINT32_MAX-offset) return false;
            auto byte=host->bytes(host->user,start+offset,1);
            if (!byte) return false;
            if (!*byte) return true;
            text.push_back(char(*byte));
        }
        return false;
    };
    std::string pattern,text;
    if (!read(needle,pattern)) return 0;
    if (pattern.empty()) { *out=token;return 1; }
    if (!read(token,text)) return 0;
    auto at=text.find(pattern);
    *out=at==std::string::npos ? 0:token+uint32_t(at);
    return 1;
}
uint32_t claw_native_menu_byte_search(ClawHost *host,uint32_t token,uint32_t value,uint32_t last,uint32_t *out) {
    if (!host || !host->bytes || !out || last > 1) return 0;
    uint32_t found=0;
    for (uint32_t offset=0;offset<0x100000;++offset) {
        if (token>UINT32_MAX-offset) return 0;
        auto byte=host->bytes(host->user,token+offset,1);
        if (!byte) return 0;
        if (*byte==uint8_t(value)) {
            found=token+offset;
            if (!last) { *out=found;return 1; }
        }
        if (!*byte) { *out=found;return 1; }
    }
    return 0;
}
extern "C" {
uint32_t claw_native_menu_audio_list_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_paper_transition_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_resource_archive_loading_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_resource_namespace_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_resource_table_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_resource_data_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_application_startup_zero_hook_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
}
uint32_t claw_native_menu_resource_entry(uint32_t f,uint32_t self,const uint32_t *a,uint32_t n,ClawHost *host,uint32_t *out) {
    // Resource owners run before the interface fallback. Normalize here too,
    // or the shared no-op owner rejects bird-state calls before that fallback.
    n = claw_native_menu_argument_count(f,n);
    const ClawEntry owners[] = {claw_resource_archive_loading_canonical_entry,
        claw_resource_namespace_canonical_entry,claw_native_menu_resource_table_entry,
        claw_resource_data_canonical_entry,claw_application_startup_zero_hook_entry,
        claw_native_menu_audio_list_entry,claw_menu_paper_transition_entry};
    for (auto entry : owners) {
        if (entry(f,self,a,n,host,out)) return 1;
        if (host->fault) return 0;
    }
    return 0;
}
