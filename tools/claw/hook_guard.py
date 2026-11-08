#!/usr/bin/env python3
"""PreToolUse hook: keeps subagents away from things only the coordinator may do.

It acts only when the tool call comes from a subagent (the hook input carries
`agent_id`). The main session is never restricted. Any error in this script
allows the call: a broken guard must not stop work.

Denied for subagents:
- xcodebuild, simulators and devices, unless work/.allow-xcodebuild exists
  (the coordinator creates that file when it delegates a build task).
- git commands that change the repository.
- Edits to the harness itself (Tests/clawparity, tools, the schema, the Makefile,
  the agent entry files), unless work/.harness-maintenance exists.

This file has no effect until a PreToolUse hook in .claude/settings.json runs it.
"""
import json
import os
import re
import sys

DEVICE = re.compile(r"(^|[\s;&|(])(xcodebuild|simctl|devicectl|adb|ipb|emulator)\b|xcrun\s+(simctl|devicectl)")
GIT_CHANGE = re.compile(r"\bgit\s+(-C\s+\S+\s+)?(add|commit|push|reset|checkout|switch|restore|stash|rebase|merge|clean|rm|mv|tag|worktree|branch\s+-[dD])\b")
HARNESS = ("Tests/clawparity/", "Tests/families/schema.json", "tools/", "Makefile", "CLAUDE.md", "AGENTS.md", ".claude/",
           "docs/ADMISSION.md", "Sources/ClawRuntime.h")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def main():
    event = json.load(sys.stdin)
    if not event.get("agent_id"):
        return
    root = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    tool, data = event.get("tool_name", ""), event.get("tool_input", {}) or {}
    if tool == "Bash":
        command = data.get("command", "")
        if DEVICE.search(command) and not os.path.exists(os.path.join(root, "work", ".allow-xcodebuild")):
            deny("Only the coordinator runs xcodebuild, simulators or devices. Report what you need instead.")
        if GIT_CHANGE.search(command):
            deny("Workers do not change the git repository. Leave your files in place; the coordinator commits.")
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = os.path.realpath(data.get("file_path", ""))
        relative = os.path.relpath(path, os.path.realpath(root))
        if relative.startswith(HARNESS) and not os.path.exists(os.path.join(root, "work", ".harness-maintenance")):
            deny(f"{relative} is part of the harness. Workers never edit the harness, the schema or the agent entry "
                 f"files to make a comparison pass. Report the problem instead.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
