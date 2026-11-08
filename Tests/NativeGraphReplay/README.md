# Shared native graph replay

Run `scripts/check-native-graph-replay.sh` for ASAN/UBSAN or
`CLAW_NATIVE_ASAN=0 CLAW_NATIVE_OPTIMIZE=1 scripts/check-native-graph-replay.sh`
for Swift -O / C++ -O2. An unchanged second run reuses its checked build cache.

The fixed sealed original factory and thread-record JSON files remain under
ignored `work/`. The runner performs 448 executions of 288 unique profiles:
160 standalone factories, 128 thread records, and 160 factories with the shared
Memory provider. It retains complete CPU/header, full 128 KiB stack, allocation,
physical frame/callback and lifetime comparisons. Subsequent same-owner
resize/free preserves the independently sealed constructor bytes. Independent
native physical-owner regressions are counted separately from original profiles.

The builder validates the finite edge table against the pinned original, requires
its observed host/manifest hashes to match captured compilation inputs, then
compiles a private read-only snapshot and private admitted registry. Cache keys
include captured inputs, explicit compiler paths/versions, SDK and flags; binaries
are verified on cache hits. Per-key locks and atomic publication protect partial
builds. All nonempty `CLAW_NATIVE_CXXFLAGS` values are rejected. Goldens are checked
by their fixed SHA-256 at replay. Reports are appended under ignored
`work/coordination/native-graph-replay-prototype-report.json`.

This is exact-byte build/replay evidence, not an atomic repository snapshot or a
replacement for family admission, existing adversarial suites, startup election
or device acceptance. Read `tools/workflows/NATIVE-INTEGRATION.md` for extension,
parallel-work and measurement rules.
