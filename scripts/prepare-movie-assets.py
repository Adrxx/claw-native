"""Copy locally verified conversions into ignored app assets by original movie ID.

This does not choose game scenes or silently substitute a missing conversion.
Run the original FEC index and conversion audits before preparing these files.
"""
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
media = root / "work/media"
index = json.loads((media / "original-fec-index.json").read_text())
conversions = json.loads((media / "startup-movie-conversions.json").read_text())
assert index["status"] == "pass" and index["count"] == 12
with (media / "source/CLAW.FEC").open("rb") as source:
    assert hashlib.file_digest(source, "sha256").hexdigest() == index["source_sha256"]
output = root / "App/GameData/MOVIES"
output.mkdir(parents=True, exist_ok=True)
entries = []
for conversion in conversions:
    member = index["members"][conversion["ordinal"]]
    assert member["movie_id"] == conversion["ordinal"] + 1
    assert conversion["source_sha256"] == member["sha256"]
    assert conversion["complete_decode"] == "pass" and conversion["frame_count_and_cadence"] == "pass"
    source = root / conversion["output"]
    with source.open("rb") as encoded:
        assert hashlib.file_digest(encoded, "sha256").hexdigest() == conversion["sha256"]
    video = next(stream for stream in conversion["probe"]["streams"] if stream["codec_type"] == "video")
    name = f"movie-{member['movie_id']:02d}.mp4"
    destination = output / name
    shutil.copyfile(source, destination)
    with destination.open("rb") as encoded:
        assert hashlib.file_digest(encoded, "sha256").hexdigest() == conversion["sha256"]
    entries.append({"movieID": member["movie_id"], "file": name,
                    "width": video["width"], "height": video["height"],
                    "bytes": source.stat().st_size, "sha256": conversion["sha256"],
                    "originalPayloadSHA256": member["sha256"]})
manifest = {"schema": 1, "originalMovieCount": index["count"],
            "originalContainerSHA256": index["source_sha256"], "entries": entries}
(output / "movies.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"status": "pass", "preparedMovieIDs": [entry["movieID"] for entry in entries],
                  "bytes": sum(entry["bytes"] for entry in entries), "output": str(output),
                  "scope": "Local prepared media only; game scene selection and live app playback remain pending"}))
