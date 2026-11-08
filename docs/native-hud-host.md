# Native original HUD hierarchy

ClawNativeHUD creates MultiStats with the exact frozen4c8f60 collection creator
and source arguments (0,0,0,9999,52297c,200000). The source491ed0 callback owns
its five frame children, their order and seventeen StatusNumberDigit children.
Child actors stay in the source collection list; the parent is an engine actor,
outside all1479 WWD records. Source HUD objects are0x60 bytes/24 words.

Frozen PlayerHUD/CheckpointTimer/ActorAnimation/ActorResourceBindings compose
initialization, heartbeat, weapon/ammo changes, digits, timer visibility, score
thresholds, draw dispatch and whole collection teardown. The generic actor draw
wrapper already composed in PlaneRenderer is exposed for collection children.
Actual GAME interface PID/ANI resources use the native registry transport.
The source640x480 bounds and source manager mode2 are retained; optional
checkpoint timed mode is not enabled. Font adapters for save messages are separate.

The focused native AddressSanitizer check covers ordinary source updates/draws,
allthree weapon images/ammo selections, score2.5million awarding one life per
callback, life cap10, timer show/floor/hide and scheduler-driven collection/digit
teardown. Score/private/timer inputs are explicitly synthetic. Source-owned
private-player writes now survive the subsequent interaction scanner and next
frame; snapshot transport no longer overwrites them from an older Swift cache.

Dictionary identity, zero-initialized native allocation with explicit portable
actor padding, indexed raster/Canvas presentation and physical audio remain
transport boundaries. Initial score/health derive from the current native player
profile; full selected-save initialization and source startup ordering remain
pending. This integration does not establish complete gameplay or device parity.

Run CLAW_NATIVE_ASAN=1 scripts/check-native-player.sh --hud-only. The complete
regression also invokes that retained fixture. Original source-only HUD evidence
and exact callback semantics are documented in player-hud-runtime.md.
