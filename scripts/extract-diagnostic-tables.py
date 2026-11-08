#!/usr/bin/env python3
"""Maintainer-only extraction of the permitted original diagnostic data tables."""
import json
from pathlib import Path
from Tests.clawparity.program import claw


def prepare(destination):
    program = claw()  # Verifies the pinned retail binary hash.
    # Exact diagnostic literal range, including the caller filename identities.
    # Keep byte addresses (and padding) so the recovered copy loops stay unchanged.
    spans = [(0x53228c, 0x532c08), (0x534938, 0x534939)]
    result = {}
    for begin, end in spans:
        section = next(s for s in program.sections if s.address <= begin < s.address+s.size)
        result[f"{begin:x}"] = list(section.data[begin-section.address:end-section.address])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result) + "\n")
    return destination


if __name__ == "__main__":
    import sys
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "App/OriginalTables/DiagnosticPolicy.json")
    print(json.dumps({"command": "prepare-diagnostic-assets", "path": str(prepare(destination)), "status": "pass"}))
