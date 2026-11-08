# Native indexed factory, copies, Flip and palette fades

The physical indexed surface host now composes frozen whole source factories
and surface operations over actual native heap allocations. The source owns
188-byte surfaces, list insertion/removal, pixel loading, key convenience,
HRESULT diagnostics and destruction. The physical memory backend owns indexed
rectangle copying, inclusive color-key ranges, horizontal/vertical mirrors and
overlap snapshots. Equal-sized copies are supported; stretching and unsupported
effects return an explicit HRESULT. No live actor/menu election is claimed.

The full original disc has6,423 uncompressed PID images; the earlier922 images
were the CLAW/GAME/Level1 laboratory subset. Retained original whole-loader
capture verifies every visible source pixel and native source factory checks
compare every asset plus keyed/plain cropped copies and source list cleanup.
Original assets and oracle captures stay under ignored local directories.

Whole original4b98b0 owns Flip call/result/restore ordering. The native physical
endpoint copies the attached back surface or explicitly supplied same-size
indexed surface into front memory. It preserves the renderer's retained back
allocation. This is a declared memory presentation transport, not a hardware
VRAM swap or proof of display-driver identity. Live scene presentation still
requires its application election. The native save-message overlay now installs
GetDC/ReleaseDC on the existing DD table and preserves the display-owned surface
identity, rather than substituting a temporary text-only interface. Primary
readback uses the physical descriptor because its source cached pitch need not
be initialized until Lock.

Whole palette4bbd90 is blocking and retains original integer RGB interpolation,
snapshot ownership and final4bb800 update. Native calls use monotonic uptime
milliseconds. Headless checks can borrow a stepped clock and synchronous palette
observer; these overrides do not change source duration or interpolation.
Original menu1000ms and Story750ms durations are preserved.4bbb70 only updates
an already source-configured scheduled fade; this host invents no setup.
4bbd20 and4bb8c0 keep source cancel/finalize and backup restoration ownership.
Live menu/Story calls, visual timing and audio/pixel/device identity remain
unaccepted until their genuine startup flows elect these hosts.

Focused native ASAN commands:

```sh
CLAW_NATIVE_ASAN=1 scripts/check-native-player.sh --surface-only
work/native-player-check/player-tests App/GameData --pid-factory-only
work/native-player-check/player-tests App/GameData --surface-flip-only
work/native-player-check/player-tests App/GameData --palette-fade-only
```

Factory captures must exist under ignored work/root-native-pid-surfaces and
original inputs must be locally available. Checkpoint verification logs record
actual command outcomes; the commands above alone do not establish acceptance.
