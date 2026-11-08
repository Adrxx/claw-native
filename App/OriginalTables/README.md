# Original app data tables

These are the data inputs previously generated locally for the native app.
Player builds copy them into `App/GameData`; they never read a Windows EXE.
No REZ, movies, music, sounds, images, levels, disassembly or decompiled text
belongs in this folder. The font JSON is the existing native monochrome
Pillow 12.0.0 atlas, not original game artwork.

Sources checked by the maintainer generator:

- v1.0 CLAW.EXE: SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
- v1.3 CLAW.EXE payload: SHA-256 `8f5069541a1c7d3f62896fb935ba591efa6fbfa4450798b96fe6f48f9cf396a0`,
  inside launcher SHA-256 `5130d7d951e4a350fc19fe3134aa447a17c3e220ae49e7834d06ec79724fa0c0`.
  The app consumes its FileVersion resource through MENU/metadata.json.

`MENU/` contains accelerator entries, literal bytes, font metrics/pixels,
menu metadata, the existing non-code image sections and elected switch-table
data spans, and native frame/dispatch transport metadata. APPLICATION/startup.json
contains startup strings and globals; DiagnosticPolicy.json contains diagnostics.
Addresses identify data in the original process, not executable code to run.

Maintainers regenerate with:

```
work/test-env/bin/python scripts/extract-original-tables.py
```

This uses the hash-pinned EXEs and existing complete Level 1 span/owner elections
under `work/native-level-one-join/`. Missing or incomplete elections fail rather
than silently removing required tables. Comparison tooling still uses the EXEs.

Players prepare their own original disc assets with:

```
python3 scripts/setup-game-data.py /path/to/CLAW.REZ
```

Or supply a folder containing CLAW.REZ, optionally CLAW.FEC, CLAW4.SF2 and
CLAW-1.4.5.4.zip. Explicit `--movies`, `--soundfont`, and `--crazyhook` paths are
also supported. Movies require ffmpeg/ffprobe and are converted locally to
H.264/AAC MP4 with the original numeric IDs, dimensions and cadence. These
assets remain ignored. Missing movies are skipped; missing original music uses
Apple's system General MIDI bank when installed, otherwise stays silent.
Missing CrazyHook helper art retains the existing unsupported-level message.
Setup replaces its output directory, so omitted extras are removed.

Then `make project` and `scripts/run-mac.sh --mute`, or open Claw.xcodeproj for
the iOS Release build. `scripts/check-rez-only-build.py --data App/GameData`
checks the loose worlds against the REZ and all packaged original tables.
