#include <cstdlib>
#define TRAP(name) extern "C" void name() { std::abort(); }
TRAP(claw_single_player_scene_entry)
TRAP(claw_single_player_scene_construct)
TRAP(claw_application_state_transition)
TRAP(claw_booty_results_entry)
TRAP(claw_booty_story_entry)
TRAP(claw_carray_entry)
TRAP(claw_scene_lifecycle_entry)
TRAP(claw_special_command_entry)
