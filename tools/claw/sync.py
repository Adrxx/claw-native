"""Refreshes the generated parts of every manifest from the tree and from the latest measurements. One JSON line.

Generated: source hashes, integration level, comparison commands (via the importer's refresh), and the result of the
most recent baseline run. Everything a person curated is left alone.
"""
import json
import sys

from . import import_legacy, manifest
from .paths import ROOT, WORK


def latest_baseline():
    files = sorted((WORK / "baseline").glob("baseline-*.jsonl"))
    if not files:
        return None, {}
    records = {}
    for line in files[-1].read_text().splitlines():
        record = json.loads(line)
        records[record["script"]] = record  # a later line for the same script replaces an earlier one
    return files[-1].stem.replace("baseline-", ""), records


def main(argv):
    import contextlib
    import io

    # The importer knows only legacy families. Canonical manifests are written by the pipeline and must survive it.
    canonical = {name: spec for name, spec in manifest.load_all().items() if spec.get("abi") == "canonical"}
    with contextlib.redirect_stdout(io.StringIO()):
        import_legacy.main(["--refresh"])
    for spec in canonical.values():
        manifest.save(spec)
    date, baseline = latest_baseline()
    updated = 0
    for name, spec in manifest.load_all().items():
        before = json.dumps(spec, sort_keys=True)
        scripts = [c["script"] for c in spec["oracle"].get("commands", [])]
        if spec["oracle"]["kind"] == "none" and spec["evidence"]["level"] != "none":
            spec["evidence"]["level"] = "none"
        found = [baseline[s] for s in scripts if s in baseline]
        if found:
            spec["evidence"]["baseline"] = {
                "date": date,
                "status": "pass" if len(found) == len(scripts) and all(r["status"] == "pass" for r in found) else "fail",
                "scripts": {r["script"]: r["status"] for r in found},
                "seconds": round(sum(r["seconds"] for r in found), 1),
            }
        if json.dumps(spec, sort_keys=True) != before:
            manifest.save(spec)
            updated += 1
    check = manifest.check_all()
    print(json.dumps({"command": "sync", "families": check["families"], "updated": updated, "baseline": date,
                      "manifest_status": check["status"], "error_count": check["error_count"]}))
    return 0 if check["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
