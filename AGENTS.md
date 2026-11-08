# Claw iPad reconstruction

Read `CLAUDE.md`. It is the entry point for every agent, whatever the model. Then read `docs/OPERATING.md` and run `make next`.

Facts that stay true:

- Reference binary: v1.0 `CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Every tool that reads it checks the hash. Use `Tests.clawparity.program.claw()`.
- Reference assets: the original disc `CLAW.REZ`, SHA-256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
- Python is `work/test-env/bin/python`. Create this virtual environment with Python 3 before running tooling.
- Research tools live under ignored `work/` and `research/node_modules/`. See `docs/RESEARCH.md`.
