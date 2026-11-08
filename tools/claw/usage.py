"""Token use of one workflow run, by stage and model, read from its transcripts. Prints a table and one JSON line.

    python -m tools.claw.usage <workflow transcript directory> [--audit]

Agent labels are "<stage>:<family>". --audit also lists tool calls that touched files a pilot worker must not read.
"""
import collections
import json
import re
import sys
from pathlib import Path

KINDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
FORBIDDEN = re.compile(r"Sources/(?!ClawRuntime)\w+\.(cpp|h)\b|Tests/(compare_\w+|\w+_helpers)\.py|docs/[a-z0-9-]+-(runtime|logic|host)\.md"
                       r"|\bgit\s+(log|show|diff|blame|grep)\b")


def read(directory):
    directory = Path(directory)
    labels = {}
    for line in (directory / "journal.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "started":
            labels[event["agentId"]] = event["label"]
    agents = {}
    for agent, label in labels.items():
        path = directory / f"agent-{agent}.jsonl"
        if not path.exists():
            continue
        tokens, turns, model, tool_inputs = collections.Counter(), 0, None, []
        for line in path.read_text().splitlines():
            try:
                message = json.loads(line).get("message") or {}
            except ValueError:
                continue
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            usage = message.get("usage") or {}
            if usage:
                turns += 1
                model = message.get("model", model)
                for kind in KINDS:
                    tokens[kind] += usage.get(kind) or 0
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_inputs.append(json.dumps(block.get("input", {})))
        agents[label] = {"model": model, "turns": turns, "tokens": dict(tokens), "tool_inputs": tool_inputs}
    return agents


def main(argv):
    agents = read(argv[0])
    stages = collections.defaultdict(lambda: {"agents": 0, "turns": 0, "model": None, **{k: 0 for k in KINDS}})
    families = set()
    for label, agent in agents.items():
        stage, _, family = label.partition(":")
        families.add(family)
        row = stages[stage]
        row["agents"] += 1
        row["turns"] += agent["turns"]
        row["model"] = agent["model"]
        for kind in KINDS:
            row[kind] += agent["tokens"].get(kind, 0)
    print(f"{'stage':10s} {'model':20s} {'agents':>6s} {'turns':>6s} {'new input':>11s} {'cached read':>12s} {'output':>8s}")
    total = collections.Counter()
    for stage, row in stages.items():
        new_input = row["input_tokens"] + row["cache_creation_input_tokens"]
        print(f"{stage:10s} {str(row['model'])[:20]:20s} {row['agents']:6d} {row['turns']:6d} {new_input:11,d} "
              f"{row['cache_read_input_tokens']:12,d} {row['output_tokens']:8,d}")
        total["new_input"] += new_input
        total["cached_read"] += row["cache_read_input_tokens"]
        total["output"] += row["output_tokens"]
        key = "sonnet" if "sonnet" in str(row["model"]) else "strong"
        total[f"new_input_{key}"] += new_input
    count = max(len(families), 1)
    summary = {"command": "usage", "families": len(families), "agents": len(agents), **total,
               "per_family": {k: round(total[k] / count) for k in ("new_input", "cached_read", "output")}}
    if "--audit" in argv:
        hits = [(label, text[:140]) for label, agent in agents.items() for text in agent["tool_inputs"] if FORBIDDEN.search(text)]
        for label, text in hits[:20]:
            print(f"AUDIT {label}: {text}")
        summary["forbidden_reads"] = len(hits)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
