"""Object classes that still have no code, most-placed first. Prints a table and one JSON line.

A class is listed when the level files place it and no family owns its registered callback. Classes that share one
callback are listed together.
"""
import json
import sys

from . import index, progress_page


def main(argv):
    data = progress_page.build()
    functions = index.functions()
    groups = {}
    for entry in data["classes"]:
        if entry["status"] == "missing" and entry["address"]:
            group = groups.setdefault(int(entry["address"], 16), {"classes": [], "placed": 0})
            group["classes"].append(entry["name"])
            group["placed"] += entry["total"]
    rows = []
    for address, group in sorted(groups.items(), key=lambda item: -item[1]["placed"]):
        function = functions.get(address, {})
        reliable = bool(function.get("decompile_ok")) and not function.get("unaff_count") and not function.get("jumptable_warning")
        rows.append({"callback": f"{address:#x}", "classes": group["classes"], "placed": group["placed"],
                     "bytes": function.get("size"), "decompile_reliable": reliable})
    print(f"{'callback':10s} {'bytes':>6s} {'placed':>7s}  classes")
    for row in rows:
        print(f"{row['callback']:10s} {str(row['bytes']):>6s} {row['placed']:7d}  {', '.join(row['classes'])}"
              f"{'' if row['decompile_reliable'] else '   (read the disassembly: decompile unreliable)'}")
    print(json.dumps({"command": "backlog", "callbacks": len(rows), "classes": sum(len(r["classes"]) for r in rows),
                      "placed_objects": sum(r["placed"] for r in rows), "status": "pass"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
