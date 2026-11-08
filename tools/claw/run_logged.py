"""Run an explicit command and save immutable phase timing under ignored work/.

This is telemetry, not an admission decision. Arguments and environment values
are not retained; input paths/hashes are included only when explicitly selected.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import uuid

from .paths import ROOT, WORK


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--directory", type=Path, default=WORK / "runs")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("an explicit command after -- is required")
    directory = args.directory.resolve()
    if directory != WORK.resolve() and WORK.resolve() not in directory.parents:
        parser.error("telemetry must stay under ignored work/")
    inputs = []
    for value in args.input:
        path = Path(value).resolve()
        inputs.append({"path": str(path.relative_to(ROOT)) if ROOT in path.parents else str(path),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    run_id = str(uuid.uuid4())
    utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    started_at = utc()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    error = None
    try:
        # Passthrough preserves the command's existing JSON/error interface.
        exit_code = subprocess.run(command, cwd=ROOT).returncode
    except OSError as exc:
        exit_code = 127
        error = type(exc).__name__
    wall = time.monotonic() - start
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = {"schema": 1, "run_id": run_id, "label": args.label,
              "started_at": started_at, "finished_at": utc(),
              "executable": Path(command[0]).name,
              "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
              "exit_code": exit_code, "wall_seconds": round(wall, 6),
              "child_user_seconds": round(usage_after.ru_utime - usage_before.ru_utime, 6),
              "child_system_seconds": round(usage_after.ru_stime - usage_before.ru_stime, 6),
              "inputs_before": inputs, "error_type": error,
              "scope": "Command process and waited descendants; no agent/model latency, admission or gameplay claim."}
    # One CLI invocation runs one measured command. maxrss is a high-water mark,
    # not a difference, and platform units are explicitly converted.
    record["child_peak_rss_bytes"] = int(usage_after.ru_maxrss * (1 if sys.platform == "darwin" else 1024))
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{run_id}.json"
    with destination.open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"command": "run-logged", "run_id": run_id,
                      "telemetry": str(destination.relative_to(ROOT)),
                      "exit_code": exit_code, "wall_seconds": record["wall_seconds"]}))
    return exit_code if exit_code >= 0 else 128 - exit_code


if __name__ == "__main__":
    sys.exit(main())
