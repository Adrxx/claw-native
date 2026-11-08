"""Validate real main-run-loop heartbeat samples, including boundary gaps."""

def check_heartbeats(records, required=()):
    errors = []
    if not records:
        return ["missing main-thread heartbeat records"]
    names = {row.get("scope") for row in records}
    for name in required:
        if name not in names:
            errors.append(f"missing heartbeat scope {name}")
    for row in records:
        gap = row.get("max_gap_ms", float("inf"))
        if not 0 <= gap < 250:
            errors.append(f"{row.get('scope')}: heartbeat gap {gap:.1f} ms (requires <250)")
        if row.get("seconds", 0) >= .25 and row.get("beats", 0) == 0:
            errors.append(f"{row.get('scope')}: timer never fired during blocking call")
    return errors
