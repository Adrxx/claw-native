#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
# Reuse the dispatcher's build folder; never create another derived-data tree.
for attempt in {1..30}; do
  (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') < 16 )) && break
  print -u2 "snapshot iOS build: load is high, waiting"
  sleep 60
done
(( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') < 16 )) || exit 1
xcodebuild -project Claw.xcodeproj -scheme Claw -configuration Release \
  -destination 'generic/platform=iOS' -derivedDataPath "${CLAW_DERIVED_DATA:-work/MacCatalyst}" \
  -jobs 1 CODE_SIGNING_ALLOWED=NO build
