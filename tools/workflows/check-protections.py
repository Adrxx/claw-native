"""Adversarial checks of role protection and blind feedback; no originals needed."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.claw import packet


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        work = root / "work"
        task = work / "packets" / "guard_probe"
        task.mkdir(parents=True)
        spec_path = root / "family.json"
        module = root / "Module.cpp"
        cases = root / "cases.py"
        spec = {"id": "guard_probe", "sources": ["Module.cpp"], "oracle": {"cases": "cases.py"}}
        spec_path.write_text(json.dumps(spec))
        module.write_text("original module")
        cases.write_text("original cases")

        def record(path):
            return {"path": str(path.relative_to(root)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        baseline = {"case-author": {"spec": record(spec_path), "module": record(module)},
                    "translator": {"spec": record(spec_path), "cases": record(cases)}}
        (task / "protected.json").write_text(json.dumps(baseline))
        with patch.object(packet, "ROOT", root), patch.object(packet, "WORK", work):
            assert packet.guard(spec_path, "case-author")["status"] == "pass"
            module.write_text("unauthorized changed module")
            assert packet.guard(spec_path, "case-author")["status"] == "fail"
            module.write_text("original module")
            cases.write_text("sealed new cases")
            packet.seal(spec_path, "case-author")
            assert packet.guard(spec_path, "translator")["status"] == "pass"
            cases.write_text("unauthorized changed cases")
            assert packet.guard(spec_path, "translator")["status"] == "fail"
            spec_path.write_text(json.dumps({**spec, "title": "unauthorized spec change"}))
            assert packet.guard(spec_path, "case-author")["status"] == "fail"
            spec_path.write_text(json.dumps(spec))
            gate = work / "gate" / "guard_probe"
            gate.mkdir(parents=True)
            (gate / "gate.json").write_text(json.dumps({"status": "rejected", "checks": {
                "mutants": {"score": 0.5, "survived": [{"line": 7, "operator": "shift-offset",
                                                          "text": "NATIVE SOURCE MARKER"}]},
                "first_failures": [{"detail": "NATIVE DIFFERENCE MARKER"}]}}))
            packet.feedback(spec_path)
            feedback = (gate / "case-author-feedback.json").read_text()
            assert "MARKER" not in feedback
            assert json.loads(feedback)["survivors"] == [{"line": 7, "operator": "shift-offset"}]
    print(json.dumps({"command": "workflow-check", "status": "pass", "checks": [
        "unsealed module tampering", "sealed cases tampering", "specification tampering",
        "blind feedback excludes native snippets"]}))


if __name__ == "__main__":
    main()
