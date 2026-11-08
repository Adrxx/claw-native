// Test-only access to the facade's optional internal CString routing. This
// translation unit is not a native source API and is absent from Sources/.
#include "../Sources/PlayerMenuManagementRuntime.cpp"
extern "C" uint32_t claw_test_menu_assignment_probe(uint32_t receiver,uint32_t source,
 ClawPlayerMenuManagementContext *context,ClawPlayerMenuManagementDependency dependency,
 void *user,uint32_t *result){if(!context||!result)return 0;try{Run run{*context,dependency,user};*result=run.invoke(0x4f66cc,receiver,{source});return 1;}catch(Failure&){return 0;}}
