# Admission rules

A family is **admitted** when `make gate FAMILY=<id>` prints status `admitted`. The gate is a script. No person or model decides admission, and nobody calls a family admitted on a worker's word.

## Canonical families

All of these must hold.

1. **Cases pass with the worker's seed.** The plain comparison passes.
2. **Cases pass with a seed nobody chose.** The gate draws a fresh random seed, records it, and the comparison passes again.
3. **Cases pass in an unoptimized build.** The module is rebuilt without optimization and the comparison passes.
4. **Every owned function is called directly** by at least one case.
5. **Every byte of every owned function is executed** by the original side, or is listed under `oracle.coverage_exempt` in the specification with a reason.
6. **The sanitizer run is clean.** The module is rebuilt with address and undefined-behavior checks that stop at the first finding, and the error stream is empty.
7. **Mutation score of at least 0.9.** The gate makes small deliberate errors in the module, one at a time. At least nine in ten must make a case fail. Survivors are listed in the result. A coordinator may record a provably equivalent mutant under `oracle.equivalent_mutants`, with its line, operator, exact source and mutant SHA-256 hashes, and a reason checked against the original instructions. A surviving test run alone is not a proof. Only matching reviewed survivors are excluded from the score; stale, duplicate, unmatched or contradicted reviews reject admission. If no non-equivalent valid mutants remain, the score is undefined and admission is rejected.
8. **No input is ignored by git.** The specification, the cases and the module live in the tracked tree.

The specification lint (`make lint`) must also pass before any worker starts.

A stand-in can still be wrong in a way both sides share. The rules above do not detect that. It is limited by keeping stand-ins at the import boundary and at the allocator, and it is checked later when the wired-up game path is compared as a whole.

## Admission fingerprint

The recorded `build_inputs_sha256` binds the family contract (excluding evidence and integration), owned sources and headers, cases and their statically imported local helpers, fixtures, common runtime headers, symbols, and the harness modules on its gate path. Borrowers also depend on their selected shared sources and the owner's current admission inputs. Changes to consumed corpus ranges count; unrelated corpus rows do not, except where whole-body or guest validation uses them as instruction anchors.

`Tests/clawparity/admission_inputs.py` is the explicit, reviewed dependency list. Common inputs include the runner, emulator, native host, ABI, fixtures, build, mutation review and gate. Optional guest and whole-body paths add their own dependencies. Every module added to an execution path must be added to that list; family helper imports must be static or declared among the family's sources. Unknown program profiles fail closed.

Profile implementations stay in separate modules. v1.0 uses `program.py`; v1.3 additionally uses `program_v13.py` and `profiles.py`. Editing either v1.3-only module leaves v1.0 admissions fresh unless their cases or borrowed sources explicitly depend on it. Shared loader or dispatch changes still invalidate both profiles. Documentation, self-tests for unused profiles, and orchestration outside the gate path are not admission inputs. Files on the selected path are hashed in full, without dropping branches or learning dependencies from a particular seed.

Missing or old fingerprints require a real gate run, except for the owner-authorized one-time migration from commit `1ec3830`. Run `work/test-env/bin/python -m tools.claw.migrate_admissions --record` to audit that exception. It requires unchanged named inputs bound to the last admission record and byte-identical selected harness modules against that commit. A newer admission's old digest must be reproducible; an absent or changed module fails the proof. The script never treats a profile-only branch or fingerprint-bookkeeping edit as whole-file byte identity. It records each family's checks in `work/regate/migration.json` and leaves every unproven admission untouched for normal re-gating.

`work/test-env/bin/python -m tools.claw.regate_stale --dry-run` lists stale families and their count. The non-dry run prints that count before launching any gate. Migration cannot make a changed execution path fresh without a real gate.

Run the isolated freshness controls with `work/test-env/bin/python -m Tests.clawparity.selftest.admission_fingerprint`. They edit temporary inputs and check the exact dry-run family list for profile, runner, source, case, fixture, helper, sharing and corpus changes; they do not modify live admissions.

## Legacy families

The 148 Codex-era families keep their own tests. `make regate FAMILY=<id>` measures them without editing anything: it runs each comparison in a private copy of the tree, once as written and once with every random seed changed, and records which original functions were called directly and how many of their bytes ran.

A legacy family is not admitted by this measurement. Its level stays `legacy-frozen` or `provisional`, and the measurement is recorded in its manifest. To be admitted, a family is re-specified as canonical.

## Evidence levels

| Level | Meaning |
| --- | --- |
| `none` | No comparison against the original exists. |
| `provisional` | A comparison exists. Nobody independent has checked it. |
| `legacy-frozen` | Codex's coordinator re-ran the worker's own comparison. |
| `admitted` | Passed the gate above. |

Evidence level says nothing about integration. That is a separate scale in each manifest: `source-only`, `compiled`, `elected`, `live`.
