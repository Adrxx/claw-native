# Family manifests

One JSON file per family. `schema.json` defines every field. `make manifests` validates them all.

- Legacy families were imported by `tools/claw/import_legacy.py`. `make sync` refreshes their generated fields: source hashes, integration level, comparison commands and the latest plain re-run. Titles, ownership lists, limits and notes are curated and are never overwritten.
- Canonical families are written by the boundary role and checked with `make lint FAMILY=<id>`.
- `docs/STATUS.md` is generated from these files by `make status`.
