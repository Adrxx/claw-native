#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
# These player assertions are v1.0 original values (3 lives, 1,000,000 threshold); run the v1.0 rules, as the
# other v1.0-reference checks do, since the app defaults to v1.3.
export CLAW_LIVES_BOSS_PROFILE="${CLAW_LIVES_BOSS_PROFILE:-claw-v1.0}"
task_verify_dir="${CLAW_NATIVE_CHECK_DIR:-work/native-player-check}"
task_asset_root=App/GameData
task_binary="$task_verify_dir/player-tests"
# Snapshot disk checks fingerprint their executable. Concurrent app checks may
# replace player-tests between the two processes; give each snapshot route its
# own binary while sharing the content-hashed C++ objects in this directory.
for task_snapshot_route in actors owners player bindings adapters; do
  if [[ " $* " == *" --snapshot-$task_snapshot_route-only "* ]]; then
    task_binary="$task_verify_dir/snapshot-$task_snapshot_route-tests"
  fi
done
mkdir -p "$task_verify_dir"
if [[ ( " $* " == *" --snapshot-owners-only "* || " $* " == *" --snapshot-actors-only "* || " $* " == *" --snapshot-bindings-only "* || " $* " == *" --snapshot-adapters-only "* ) && ! -d App/GameData/LEVEL2/WORLDS ]]; then
  work/test-env/bin/python scripts/prepare-reference-assets.py Original/retail-assets --level 2
fi
# --level N selects a focused world/object-load check, separate from Level 1 fixtures.
if [[ "${1:-}" == "--level" ]]; then
  if [[ ( $# != 2 && $# != 3 ) || "$2" != <1-14> || ( $# == 3 && "$3" != "--world-only" ) ]]; then
    print -u2 'usage: scripts/check-native-player.sh --level <1-14> [--world-only]'
    exit 2
  fi
  if [[ ! -d "App/GameData/LEVEL$2/WORLDS" ]]; then
    work/test-env/bin/python scripts/prepare-reference-assets.py Original/retail-assets --level "$2"
  fi
fi
# Run the complete menu join with one native build and serial comparisons.
# Each phase writes fresh Swift witnesses before its original-side comparison.
if [[ "$*" == "--menu-join-only" ]]; then
  export CLAW_MENU_FULL_INITIALIZER=1
  export CLAW_MENU_FRAMES=0 CLAW_MENU_ROUTES=0 CLAW_MENU_RESIZE=0
fi
if [[ " $* " == *" --raw-actor-only "* ]]; then
  export CLAW_NATIVE_RAW_ACTOR_WITNESS="$task_verify_dir/raw-actor-witness.json"
fi
if [[ " $* " == *" --raw-pid-only "* ]]; then
  export CLAW_NATIVE_RAW_PID_WITNESS="$task_verify_dir/raw-pid-witness.json"
fi
if [[ " $* " == *" --diagnostic-routes-only "* ]]; then
  PYTHONPATH=. work/test-env/bin/python scripts/prepare-diagnostic-assets.py
fi
if [[ "${CLAW_MENU_ROUTES:-0}" == 1 || "${CLAW_MENU_RESIZE:-0}" == 1 || "$*" == "--menu-join-only" ]]; then
  PYTHONPATH=. work/test-env/bin/python scripts/prepare-diagnostic-assets.py
fi
# The C++ module list is generated (scripts/native-gate-sources.txt, same membership as the app).
# Objects are compiled in parallel and reused when nothing they depend on changed.
swift_sanitizers=()
swift_optimization=(-whole-module-optimization)
object_arguments=()
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then
  swift_optimization=(-whole-module-optimization -O)
fi
if [[ "${CLAW_NATIVE_ASAN:-0}" == 1 ]]; then
  object_arguments=(--asan)
  swift_sanitizers=(-sanitize=address)
fi
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_verify_dir" $object_arguments)"})
# Elected object adapters present in Sources/ join the player build by election.
object_adapters=(${(f)"$(work/test-env/bin/python Tests/NativeObjectConnections/compare.py adapters)"})
xcrun swiftc $swift_sanitizers $swift_optimization -import-objc-header Sources/Claw-Bridging-Header.h \
  Sources/ClawAssets.swift Sources/ClawWorld.swift Sources/ClawCollision.swift \
  Sources/ClawLevelScene.swift Sources/ClawLevelRenderer.swift \
  Sources/ClawAnimationPlayback.swift Sources/ClawPlayerAssets.swift \
  Sources/ClawNativeAudio.swift Sources/ClawNativeDiagnostics.swift Sources/ClawNativeMovieStateServices.swift Sources/ClawNativeMoviePlayback.swift Sources/ClawOriginalResourceNames.swift \
  Sources/ClawNativePlayer.swift Sources/ClawPlayerDrawing.swift \
  Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
  Sources/ClawTokenHeap.swift Sources/ClawSnapshot.swift Sources/ClawNativeWindowInputQueue.swift Sources/ClawNativePlayerView.swift Sources/ClawFrameClock.swift Sources/ClawNativeScene.swift Sources/ClawNativeMenuResources.swift Sources/ClawNativeMenuInterface.swift Sources/ClawNativeMenuMusic.swift Sources/ClawNativeScreenDump.swift Sources/ClawNativeObjectConnections.swift $object_adapters Sources/ClawNativeCanonicalHost.swift \
  Sources/ClawActorResources.swift Sources/ClawCapturedEnemyStates.swift \
  Sources/ClawNativeEnemy.swift Sources/ClawNativeObjectLoader.swift \
  Sources/ClawIndexedDrawing.swift Sources/ClawNativeEnemyDrawing.swift \
  Sources/ClawOriginalLifecycleVTables.swift Sources/ClawNativeCamera.swift Sources/ClawNativeRendering.swift Sources/ClawNativeFrame.swift Sources/ClawFastIndexedDrawing.swift Sources/ClawNativeRespawn.swift Sources/ClawNativePlayerServices.swift Sources/ClawNativeWorld.swift Sources/ClawNativeHumanoid.swift Sources/ClawNativeBullet.swift Sources/ClawNativeLoot.swift Sources/ClawNativePickup.swift Sources/ClawNativeEffects.swift Sources/ClawNativeSpeech.swift Sources/ClawNativePlatforms.swift Sources/ClawNativePegs.swift Sources/ClawNativeSoundTriggers.swift Sources/ClawNativeSingleCrates.swift Sources/ClawNativeCheckpoints.swift Sources/ClawNativeAmbientAudio.swift Sources/ClawNativeCurses.swift Sources/ClawNativeBreakables.swift Sources/ClawBreakableVTables.swift Sources/ClawNativeCarry.swift Sources/ClawNativeRandom.swift Sources/ClawNativeSpecialPowerups.swift \
  Sources/ClawNativeSave.swift Sources/ClawNativeStatusMessages.swift Sources/ClawNativeHUD.swift Sources/ClawNativeProjectiles.swift Sources/ClawPlayerProjectileVTables.swift Sources/ClawNativeFlare.swift Sources/ClawNativeLightPalette.swift Sources/ClawNativePaletteResources.swift Sources/ClawNativeDisplay.swift Sources/ClawOriginalDisplayVTables.swift Sources/ClawNativeWarpFade.swift Tests/NativeDiagnosticRoutes.swift Tests/NativeWindowInputRoutes.swift Tests/NativeRawPID.swift Tests/NativeRawActor.swift Tests/NativeMenuInterface.swift Tests/NativeSnapshots/Player.swift Tests/NativeSnapshots/Owners.swift Tests/NativePlayer/main.swift $objects -lc++ -lz \
  -o "$task_binary"
if [[ " $* " == *" --menu-base-only "* || " $* " == *" --menu-interface-only "* || "$*" == "--menu-join-only" ]]; then
  task_asset_root=Original/retail-assets
  export CLAW_NATIVE_MENU_WITNESS="$task_verify_dir/menu-base-witness.json"
  export CLAW_NATIVE_MENU_LITERALS="$task_verify_dir/menu-base-literals.json"
  work/test-env/bin/python - "$CLAW_NATIVE_MENU_LITERALS" <<'PYDATA'
import hashlib, json, sys
from pathlib import Path
from Tests.clawparity.program import claw
program = claw()  # Enforces the pinned retail SHA-256.
with Path('Original/claw-disc/files/DATA/CLAW.REZ').open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
profile = json.loads(Path('Tests/state_five_interface_profile.json').read_text())
assert hashlib.sha256(Path('Original/retail-assets/STATES/MENU/CLAW.IFC').read_bytes()).hexdigest() == profile['assetSHA256']
literals = {}
for address in (0x5334f0, 0x52a004, 0x52c69c, 0x528b08, 0x52372c, 0x523ce0):
    section = next(s for s in program.sections if s.address <= address < s.address + s.size)
    data = section.data[address-section.address:].split(b"\0", 1)[0] + b"\0"
    literals[f"{address:x}"] = list(data)
with open(sys.argv[1], "w") as stream:
    json.dump(literals, stream)
PYDATA
fi
if [[ "$*" == "--menu-join-only" ]]; then
  "$task_binary" "$task_asset_root" --menu-base-only
  PYTHONPATH=. work/test-env/bin/python Tests/NativeMenuBase/compare.py "$CLAW_NATIVE_MENU_WITNESS" "$task_asset_root"
  work/test-env/bin/python -m Tests.NativeMenuResources.compare --prepare-interface
  "$task_binary" "$task_asset_root" --menu-interface-only
  work/test-env/bin/python -m Tests.NativeMenuResources.initializer_compare
  CLAW_MENU_FRAMES=1 "$task_binary" "$task_asset_root" --menu-interface-only
  work/test-env/bin/python -m Tests.NativeMenuResources.frames_compare
  CLAW_MENU_ROUTES=1 "$task_binary" "$task_asset_root" --menu-interface-only
  work/test-env/bin/python -m Tests.NativeMenuResources.routes_compare
  CLAW_MENU_RESIZE=1 "$task_binary" "$task_asset_root" --menu-interface-only
  work/test-env/bin/python -m Tests.NativeMenuResources.resize_compare
  print 'PASS native menu join: base, original resources, full construction, 61 frames, routes, resize/error and cleanup controls'
  exit 0
fi
if [[ " $* " == *" --menu-interface-only "* ]]; then
  work/test-env/bin/python -m Tests.NativeMenuResources.compare --prepare-interface
fi
"$task_binary" "$task_asset_root" "$@"
if [[ " $* " == *" --snapshot-owners-only "* || " $* " == *" --snapshot-actors-only "* || " $* " == *" --snapshot-bindings-only "* || " $* " == *" --snapshot-adapters-only "* ]]; then
  "$task_binary" "$task_asset_root" "$@" --relaunch
fi
if [[ " $* " == *" --raw-pid-only "* ]]; then
  PYTHONPATH=. work/test-env/bin/python Tests/NativeRawPID/compare.py "$CLAW_NATIVE_RAW_PID_WITNESS"
fi

if [[ " $* " == *" --menu-base-only "* ]]; then
  PYTHONPATH=. work/test-env/bin/python Tests/NativeMenuBase/compare.py "$CLAW_NATIVE_MENU_WITNESS" "$task_asset_root"
fi
if [[ " $* " == *" --menu-interface-only "* ]]; then
  if [[ "${CLAW_MENU_RESIZE:-0}" == 1 ]]; then
    work/test-env/bin/python -m Tests.NativeMenuResources.resize_compare
  elif [[ "${CLAW_MENU_ROUTES:-0}" == 1 ]]; then
    work/test-env/bin/python -m Tests.NativeMenuResources.routes_compare
  elif [[ "${CLAW_MENU_FRAMES:-0}" == 1 ]]; then
    work/test-env/bin/python -m Tests.NativeMenuResources.frames_compare
  elif [[ "${CLAW_MENU_FULL_INITIALIZER:-0}" == 1 ]]; then
    work/test-env/bin/python -m Tests.NativeMenuResources.initializer_compare
  else
    work/test-env/bin/python -m Tests.NativeMenuResources.interface_compare
  fi
fi

if [[ " $* " == *" --raw-actor-only "* ]]; then
  PYTHONPATH=. work/test-env/bin/python Tests/NativeRawActor/compare.py "$CLAW_NATIVE_RAW_ACTOR_WITNESS"
fi
