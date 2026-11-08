#!/usr/bin/env python3
"""Check both app registry elections without changing pinned module bodies.

Stub exports identify which native owner the generated registry dispatches to;
actual body behavior is covered by the original admissions and v1.3 checks.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    header = (ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
    symbols = sorted(set(re.findall(r'uint32_t (claw_\w+_entry)\(uint32_t, uint32_t, const uint32_t \*, uint32_t, ClawHost \*, uint32_t \*\);', header)))
    exports = '\n'.join(f'extern "C" uint32_t {name}(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*) {{return 1;}}' for name in symbols)
    source = '#include "ClawCanonicalDispatch.h"\n#include <cassert>\n' + exports + r'''
int main() {
    struct Choice {uint32_t address;ClawEntry original,modern;};
    Choice choices[] = {
        {0x43f120,claw_level_one_batch_enemy_callee_03_entry,claw_v13_cheat_native_entry},
        {0x4208e0,claw_audio_events_entry,claw_v13_native_overlay_entry},
        {0x462350,claw_level_one_object_actions_02_entry,claw_v13_enemy_lifecycle_compat_entry},
        {0x415ce0,claw_player_startup_canonical_entry,claw_v13_player_startup_compat_entry},
        {0x4908b0,claw_level_one_hud_timers_01_entry,claw_v13_score_compat_entry}
    };
    for (const char *version : {"1.0","1.3"}) {
        setenv("CLAW_GAME_VERSION",version,1);
        bool modern = strcmp(version,"1.3")==0;
        assert(bool(claw_native_v13_enabled())==modern);
        for (auto &choice:choices) {
            auto *entry=claw_canonical_lookup(choice.address);
            assert(entry && entry->entry==(modern?choice.modern:choice.original));
        }
        assert(!claw_canonical_lookup(0x12345678));
    }
    unsetenv("CLAW_GAME_VERSION");
    assert(claw_native_v13_enabled());
    for (auto &choice:choices) assert(claw_canonical_lookup(choice.address)->entry==choice.modern);
}
'''
    source = source.replace('#include <cassert>', '#include <cassert>\n#include <initializer_list>')
    with tempfile.TemporaryDirectory(prefix='claw-version-') as temporary:
        folder=Path(temporary)
        cpp=folder/'check.cpp';cpp.write_text(source)
        binary=folder/'check'
        subprocess.run(['clang++','-std=c++17','-O0','-I',str(ROOT/'Sources'),str(cpp),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
    print(json.dumps(dict(check='game-version',status='pass',profiles=['1.0','1.3','default-1.3'],registry_routes=['enemy-death','audio','enemy-lifecycle','startup','score'],limitation='Registry election check; original admissions prove selected body behavior.')))


if __name__ == '__main__':
    main()
