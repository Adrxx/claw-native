#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
mkdir -p work
# All app lanes share this checkout. Hold an OS-released lock across the
# build so two scripts waiting for load cannot start compilers together.
if [[ -z ${CLAW_BUILD_LOCK_HELD:-} ]]; then
  exec python3 -c 'import fcntl, os, subprocess, sys
with open("work/.claw-app-build.lock", "a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    os.environ["CLAW_BUILD_LOCK_HELD"] = "1"
    raise SystemExit(subprocess.call(["/bin/zsh", *sys.argv[1:]]))' "$0" "$@"
fi
# Builds and opens the playable app in the Release configuration (Swift -O,
# whole module; C++ -O2 with floating-point contraction disabled),
# which runs the menu and Level 1 at the original 17 ms frame pacing.
# CLAW_CONFIG=Debug builds the unoptimized app (about 10 frames per second) that the
# comparison checks in work/new-game/COMMANDS.md launch by default. Both keep every
# runtime check; the configurations differ only in optimization.
config="${CLAW_CONFIG:-Release}"
# Wait (up to 30 minutes) while the 1-minute load is 16 or more; the owner's Mac runs hot beyond that.
for i in {1..30}; do
  (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') < 16 )) && break
  echo "run-mac.sh: load $(sysctl -n vm.loadavg | awk '{print $2}'), waiting" >&2; sleep 60
done
work/test-env/bin/python scripts/prepare-menu-assets.py
xcodebuild -project Claw.xcodeproj -scheme Claw -configuration "$config" \
  -destination 'platform=macOS,variant=Mac Catalyst' \
  -derivedDataPath ${CLAW_DERIVED_DATA:-work/MacCatalyst} -jobs 1 CODE_SIGNING_ALLOWED=NO build
codesign --force --sign - "${CLAW_DERIVED_DATA:-work/MacCatalyst}/Build/Products/$config-maccatalyst/Claw.app"
# --version-only (used by work/new-game/COMMANDS.md) means build only; the app has no such flag and would just run.
(( ${@[(Ie)--version-only]} )) && exit 0
# Agent runs (CLAW_AGENT=1, set by the dispatcher) never open a plain, audible window: with no arguments the script only
# builds, and any launch it makes is muted.
if [[ -n ${CLAW_AGENT:-} ]]; then
  (( $# == 0 )) && exit 0
  set -- --mute "$@"
fi
open -n "${CLAW_DERIVED_DATA:-work/MacCatalyst}/Build/Products/$config-maccatalyst/Claw.app" --args "$@"
