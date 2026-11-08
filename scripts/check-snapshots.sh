#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
task_verify_dir="work/snapshot-check"
mkdir -p "$task_verify_dir"
# Focused native storage/clock/RNG check. No emulator and no shared harness.
for name in GameTiming CRTRandomRuntime WorldLootRuntime; do
  xcrun clang++ -std=c++17 -O2 -ffp-contract=off -I Sources -c "Sources/$name.cpp" -o "$task_verify_dir/$name.o"
done
xcrun swiftc -O -import-objc-header Tests/NativeSnapshots/Bridge.h -I Sources \
  Sources/ClawTokenHeap.swift Sources/ClawSnapshot.swift Sources/ClawFrameClock.swift \
  Sources/ClawNativeRandom.swift Tests/NativeSnapshots/main.swift \
  "$task_verify_dir/GameTiming.o" "$task_verify_dir/CRTRandomRuntime.o" "$task_verify_dir/WorldLootRuntime.o" \
  -lc++ -Xlinker -dead_strip -o "$task_verify_dir/snapshot-tests"
"$task_verify_dir/snapshot-tests" "$task_verify_dir"
# A second process proves the slot is read from disk, not the in-memory cache.
"$task_verify_dir/snapshot-tests" "$task_verify_dir" --relaunch
