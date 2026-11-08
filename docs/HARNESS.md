# Verification tooling

`make help` lists the commands. `docs/ADMISSION.md` defines family admission;
`Tests/clawparity/README.md` documents the comparison library and fixtures.

| Component | Location | Purpose |
| --- | --- | --- |
| Commands | `Makefile`, `tools/claw/` | Run recovery and verification commands. |
| Function corpus | ignored `work/corpus/` | Local analysis of the hash-pinned original. Never publish the corpus. |
| Symbols | `Tests/symbols.json` | Name original imports and registered game classes. |
| Family manifests | `Tests/families/` | Declare ownership, compiler contracts and evidence. |
| Status | `docs/STATUS.md` | Generated family status (`make status`). |
| Comparison library | `Tests/clawparity/` | Compare native and original calls, memory and return values. |
| Admission gate | `make gate` | Check independent seeds, coverage, sanitizers and mutation sensitivity. |
| Recovery workflow | `tools/workflows/` | Separate case-author, translator and review roles. |
| Project generation | `make project` | Generate Xcode source membership and native dispatch. |
| Self-test | `make selftest` | Test the comparison library on synthetic inputs. |

Original binaries, analysis output, transcripts and run evidence remain local in
ignored directories. Tests needing the original require the reference files
listed in `AGENTS.md`. App builds use the approved tables in `App/OriginalTables/`
and locally prepared game data.
