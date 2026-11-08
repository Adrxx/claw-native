// v1.3 enemy callback allocation and lifecycle event routing
//
// The v1.3 callbacks retain their whole original constructors and dispatcher.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40a020:
        return 1;
    case 0x422290:
        return 1;
    case 0x435ba0:
        return 1;
    case 0x439170:
        return 1;
    case 0x443020:
        return 1;
    case 0x44b500:
        return 1;
    case 0x461e50:
        return 1;
    case 0x464850:
        return 1;
    case 0x467ae0:
        return 1;
    case 0x46ac10:
        return 1;
    case 0x475e90:
        return 1;
    case 0x47f0c0:
        return 1;
    default:
        return -1;
    }
}

// 0x40a020 BearSailor lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_40a020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x4c8});
        if (instance != 0) {
            instance = run.call(0x40a190, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x422290 Chameleon lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_422290(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x4b0});
        if (instance != 0) {
            instance = run.call(0x422850, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x435ba0 CrazyHook lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_435ba0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x4c0});
        if (instance != 0) {
            instance = run.call(0x435d10, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x439170 CutThroat lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_439170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x4a8});
        if (instance != 0) {
            instance = run.call(0x4392e0, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x443020 Fish lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_443020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x458});
        if (instance != 0) {
            instance = run.call(0x4435f0, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x44b500 HermitCrab lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_44b500(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x460});
        if (instance != 0) {
            instance = run.call(0x44bce0, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x461e50 Mercat lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_461e50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x508});
        if (instance != 0) {
            instance = run.call(0x461fc0, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x464850 Officer lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_464850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x498});
        if (instance != 0) {
            instance = run.call(0x4649c0, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x467ae0 Parrot lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_467ae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x478});
        if (instance != 0) {
            instance = run.call(0x467c50, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x46ac10 PegLeg lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_46ac10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x510});
        if (instance != 0) {
            instance = run.call(0x46b1e0, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x475e90 PunkRat lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_475e90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x438});
        if (instance != 0) {
            instance = run.call(0x476000, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}

// 0x47f0c0 Rat lifecycle callback. cdecl, 1 stack argument(s), returns u32.
uint32_t function_47f0c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t world = arguments[0];
    const uint32_t logic = run.get(world + 0x7c); // World logic record.
    const uint32_t event = run.get(logic + 0x1c); // Current event.
    switch (event) {
    case 0: {
        run.put(logic + 0x1c, 1000);
        uint32_t instance = run.call(0x4fcaea, 0, {0x448});
        if (instance != 0) {
            instance = run.call(0x47f230, instance, {world});
        }
        // Allocation failure still reads the null instance's vtable.
        run.vcall(instance, 0x18);
        run.put(logic + 0x18, instance); // Publish only after initialization.
        return 1;
    }
    case 0x1d:
        run.vcall(run.get(logic + 0x18), 0x2c);
        return 1;
    case 0x1e:
        run.vcall(run.get(logic + 0x18), 0x28);
        return 1;
    case 0x50:
        run.vcall(run.get(logic + 0x18), 0x38);
        return 1;
    case 0x51:
        run.vcall(run.get(logic + 0x18), 0x34);
        return 1;
    case 0x52:
        run.vcall(run.get(logic + 0x18), 0x30);
        return 1;
    case 0x53:
        run.vcall(run.get(logic + 0x18), 0x3c);
        return 1;
    case 1000:
        return 1;
    default:
        run.call(0x4def40, 0, {run.get(logic + 0x18)});
        return 1;
    }
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40a020:
        return function_40a020(run, receiver, arguments);
    case 0x422290:
        return function_422290(run, receiver, arguments);
    case 0x435ba0:
        return function_435ba0(run, receiver, arguments);
    case 0x439170:
        return function_439170(run, receiver, arguments);
    case 0x443020:
        return function_443020(run, receiver, arguments);
    case 0x44b500:
        return function_44b500(run, receiver, arguments);
    case 0x461e50:
        return function_461e50(run, receiver, arguments);
    case 0x464850:
        return function_464850(run, receiver, arguments);
    case 0x467ae0:
        return function_467ae0(run, receiver, arguments);
    case 0x46ac10:
        return function_46ac10(run, receiver, arguments);
    case 0x475e90:
        return function_475e90(run, receiver, arguments);
    case 0x47f0c0:
        return function_47f0c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_v13_enemy_lifecycle_entry, owned, body)
