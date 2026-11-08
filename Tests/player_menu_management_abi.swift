import PlayerMenuManagement
let entry: @convention(c) (UInt32, UInt32, UnsafePointer<UInt32>?, UInt32, UnsafeMutablePointer<ClawPlayerMenuManagementContext>?, ClawPlayerMenuManagementDependency?, UnsafeMutableRawPointer?, UnsafeMutablePointer<UInt32>?) -> UInt32 = claw_player_menu_management_entry
precondition(MemoryLayout<ClawPlayerMenuManagementContext>.size == 88)
precondition(MemoryLayout<ClawPlayerMenuManagementCall>.size == 232)
let context = UnsafeMutablePointer<ClawPlayerMenuManagementContext>.allocate(capacity: 1)
context.initialize(to: ClawPlayerMenuManagementContext())
var result: UInt32 = 123
precondition(entry(0,0,nil,0,context,nil,nil,&result) == 0 && context.pointee.fault == 0 && result == 123)
context.deinitialize(count: 1)
context.deallocate()
