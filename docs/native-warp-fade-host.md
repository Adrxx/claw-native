# Native indexed warp-fader host

`ClawNativeWarpFade` composes the frozen original type2 fader with the existing
native token heap and **the gameplay CRT thread**. It does not seed a second RNG
or elect travel commands. The verified source fader/factory/common runner own
all pixel selection, Float progression, random consumption and deletion.

The native profile supplies two188-byte surface views: DD interface at+8,
height480 at+14, width640 at+18, pitch640 at+1c and one byte/pixel at+ac. Lock
4b9730 returns live heap pixel storage; the actual DD virtual80 unlock consumes
its original `(interface,0)` packet. An extra640-byte row represents owned source
spill capacity; writes are not clipped to a guessed rectangle. These views are
physical format transports, not a whole source surface constructor or retail
startup proof. The caller can supply the same physical clock closure as gameplay.

A source4ebf80 manager constructor and the actual514228 five-entry table support
source4ec050(type2,descriptor), partial4ed1a0, maximum4ed5d0, whole4ec9c0 and
removal4ec600. Source alloc/free events retain ownership in the common heap.
Removing each effect and recovered CArray SetSize(0) release all source-owned
allocations; outer surface/manager/scratch profiles are native transport-owned.
This is not a whole4ebfc0 manager-destructor claim.

Run `CLAW_NATIVE_ASAN=1 scripts/check-native-player.sh --warp-fade-only`.
The focused native ASAN history renders the actual Level1 ordinary source frame,
uses its640×480 persistent indexed bytes, and checks both directions through
partial and full clock-driven source steps. Each initializer consumes exactly
2000 calls on the same gameplay CRT seed, with the expected source LCG final
state. Percent80 produces gradient383/maximum863. Fade-out ends in all zero
indices; fade-in restores every307200 visible byte, preserving its source image.
Lock/unlock counts balance, effects and source array storage are released, and
ordinary scene frames resume without a fault. Its16ms physical-clock trajectory
and surface profiles are explicitly controlled fixture inputs.

This host is currently exercised by native verification. It does not replace the
live scene's existing front/back identities or draw/palette/GDI interface. Normal
WM_COMMAND805c dispatch, source SpecialCommand globals, fade packet materialization,
intermediate presentation and source world/camera/actor refresh remain the next
integration. Map/Booty/next-level execution remains distinct. The finite original
fader comparisons are in `warp-fade-runtime.md`; neither those comparisons nor
this host test establish whole-game behavior identity or device acceptance.

Full updated native ASAN regression and fresh Mac/generic simulator builds pass.
The signed app passes strict verification after archive extraction. This adds
verified host source and tests; normal WM805c travel remains pending.
