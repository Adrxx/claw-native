#!/bin/zsh
# Build the two iPad icon targets in this session's existing derived-data tree.
# Run only after the Mac build completes; --simulator adds a Home screen check build.
set -euo pipefail
cd "${0:A:h:h}"
for attempt in {1..30}; do
  (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') < 16 )) && break
  print -u2 "icon iPad build: load is high, waiting"
  sleep 60
done
(( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') < 16 )) || exit 1
destination='generic/platform=iOS'
[[ ${1:-} == --simulator ]] && destination='generic/platform=iOS Simulator'
work/test-env/bin/python scripts/prepare-app-icon.py
xcodebuild -project Claw.xcodeproj -scheme Claw -configuration Release \
  -destination "$destination" -derivedDataPath "${CLAW_DERIVED_DATA:-work/MacCatalyst}" \
  -jobs 1 ARCHS=arm64 CODE_SIGNING_ALLOWED=NO build
