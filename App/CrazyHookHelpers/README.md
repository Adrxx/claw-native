# CrazyHook compatibility helpers

CrazyHook is a community project by Zax37 and Cubuspl42 for The Claw Recluse
community, revised by TSXD. These helpers are included for CrazyHook level
compatibility, so players supply only their original disc `CLAW.REZ`.

Source release: `CLAW-1.4.5.4.zip` (CrazyHook 1.4.5.4).
Archive SHA-256: `046a5e909c6183de30f6634031716f1c45d1c14453ded360d93d406db2e87b8d`.

Only the 27 plasma animation, image and sound helpers used by the app are
included: `HELPERANIS/`, `HELPERIMAGES/` and `HELPERSOUNDS/`. `manifest.json`
records each file's SHA-256. No executable, DLL, Lua script, other release
asset or sample level is included.

Player setup (`python3 scripts/setup-game-data.py /path/to/CLAW.REZ`) and app
build preparation copy these files to ignored `App/GameData/CRAZYHOOK/`.
They do not read or require the CrazyHook zip.

Maintainers can regenerate the helpers from a local copy of the release:

```sh
work/test-env/bin/python scripts/crazyhook_assets.py /path/to/CLAW-1.4.5.4.zip
```

The extractor verifies the archive hash and selects only the listed helpers.
Keep this README when regenerating. Check the included and prepared copies with
`work/test-env/bin/python scripts/check-rez-only-build.py` after player setup.
