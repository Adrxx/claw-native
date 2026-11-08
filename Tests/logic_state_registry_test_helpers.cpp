// Test-only access to the private name CString assignment used by registration.
#include "../Sources/LogicStateRegistry.cpp"
extern "C" uint32_t claw_logic_state_test_assign(ClawLogicStateRegistry* s,
 ClawLogicStateContext* c,uint32_t cell,const char* name,
 ClawLogicStateDependency dependency,void* user){
 Run run{s,c,dependency,user};stringAssign(run,cell,name);normalize(run);
 return read(run,cell);
}
