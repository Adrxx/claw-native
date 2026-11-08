#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_EXECUTION_LANE_CHECK_DIR:-work/native-execution-lane-check}"
mkdir -p "$task_verify_dir"
# Native foundation only: no project generation, original binary, app, or device.
# UBSAN covers both the real CRT implementation and nested C++ borrow fixture.
xcrun clang++ -std=c++17 -fsanitize=address,undefined -fno-sanitize-recover=all \
  -fno-omit-frame-pointer -I Sources -I Tests/NativeExecutionLane \
  -c Tests/NativeExecutionLane/BorrowProbe.cpp -o "$task_verify_dir/borrow.o"
xcrun clang++ -std=c++17 -fsanitize=address,undefined -fno-sanitize-recover=all \
  -fno-omit-frame-pointer -I Sources -c Sources/CRTRandomRuntime.cpp -o "$task_verify_dir/random.o"
xcrun clang++ -std=c++17 -fsanitize=address,undefined -fno-sanitize-recover=all \
  -fno-omit-frame-pointer -I Sources -c Sources/WorldLootRuntime.cpp -o "$task_verify_dir/loot.o"
# Same-file test extension can exercise private predicates in deterministic order.
cat Sources/ClawNativeExecutionLane.swift Tests/NativeExecutionLane/MailboxRaces.swift > "$task_verify_dir/LaneAndRaceTests.swift"
for version in 5 6; do
  xcrun swiftc -parse-as-library -swift-version "$version" -strict-concurrency=complete \
    -warnings-as-errors -sanitize=address -import-objc-header Tests/NativeExecutionLane/Bridge.h -I Sources \
    "$task_verify_dir/LaneAndRaceTests.swift" Sources/ClawTokenHeap.swift Sources/ClawNativeRandom.swift \
    Tests/NativeExecutionLane/main.swift "$task_verify_dir/borrow.o" "$task_verify_dir/random.o" "$task_verify_dir/loot.o" \
    -Xlinker -dead_strip -lc++ -o "$task_verify_dir/lane-tests-swift$version"
  ASAN_OPTIONS=detect_stack_use_after_return=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$task_verify_dir/lane-tests-swift$version"
done
for fixture in RejectedStateEscape RejectedPointerEscape; do
  if xcrun swiftc -swift-version 6 -strict-concurrency=complete -warnings-as-errors \
      -typecheck Sources/ClawNativeExecutionLane.swift "Tests/NativeExecutionLane/$fixture.swift" \
      > "$task_verify_dir/$fixture.log" 2>&1; then
    print -u2 "Unsafe boundary unexpectedly compiled: $fixture"
    exit 1
  fi
  rg -q 'Sendable' "$task_verify_dir/$fixture.log"
done
print 'native-execution-lane: non-Sendable state/pointer escape rejected by compiler'
