# Operating manual

This replaces every earlier workflow document. It applies to Codex, Claude and any other agent. Keep sessions bounded and recover game logic rather than platform code.

## Roles

The agent that takes a task from the queue is the coordinator for that task. It may build and run the Mac app, start sub-agents for family work, and add follow-up tasks to `tools/queue.json`. A sub-agent ("worker") does one role for one family, as described in `tools/workflows/roles/`, and never edits `tools/`, `Tests/clawparity/` or the queue.

## Every session

1. Run `make next`. It prints the first open task that is not waiting for the owner. Agents work on the uncommitted tree; do not wait for a commit.
2. Run `make take ID=<id>`. It refuses a task someone else holds.
3. Read only what the task's `start_with` names, plus the files you change.
4. Do the task. Check your result with the command in its `done_when`.
5. Record the outcome in one sentence and end the session:

   ```sh
   make finish ID=<id> NOTE="<what is now true, with the command that shows it>"
   make block ID=<id> NOTE="<what is needed, from whom>"
   ```

   If a session died holding a task, `make reopen ID=<id> NOTE="<why>"` frees it.

If a task turns out larger than one session, finish the part you did, add the rest as a new task in `tools/queue.json`, and end the session. "Larger than one session" means you have worked about an hour or used about 100 turns, or the rest needs another task's result first. Do not stop after a short checkpoint and split the remainder: every new session pays to re-read the docs and the code, so keep going while the next step is clear.

Migrating a legacy family to canonical form is ordinary family work: the coordinator runs the pipeline below with fresh workers in the same session. "Measured, not admitted" from the gate is work to do, not a reason to block.

When recovery finds callees nobody owns, do not add one task per function. List what is missing first (trace the original under Unicorn or map the call graph), then add tasks that each recover a batch of 5 to 15 related functions, naming their addresses.

## Session budget

A session that runs long re-reads its whole history on every turn. That is the most expensive habit in this project.

- End a session at 150 turns or about 30 million tokens, whichever comes first, even mid-task. Record where you are with `queue block` and stop.
- Heavy means anything that runs the emulator or a compiler: gates, comparisons, measurements, builds. A coordinator does not stay alive across tasks. It starts fresh for each one.
- Workers start fresh for each family and each role.
- `make usage` shows recent Codex sessions and fails if any session started since the budget existed went over it. It does not see Claude sessions.
- Tasks are normally started by `tools/claw/dispatch.py`, one fresh Codex run per task. You do not need to run a long session yourself.
- Up to three dispatcher lanes run at once (`--lane 1`, `2`, `3`). Each lane claims its task before starting Codex. Family admissions, batches and recoveries run side by side; any other task runs only while no other such task is taken. With three lanes, each session runs one heavy job at a time (the gate uses one mutation job). The dispatcher starts admissions, batches and recoveries on the cheaper model and retries one on the strong model if the cheaper run blocks; harness changes (`"exclusive": true`) run alone on the strong model. A task blocked on queued prerequisites is reopened automatically.


## Which model does what

| Queue `model` | Codex | Claude | Used for |
| --- | --- | --- | --- |
| `cheaper` | GPT-6.1 Sol, low or medium effort | Sonnet | Test cases, translation, diagnosis |
| `strong` | GPT-6 Astra, high effort | Opus | Boundary review, triage, harness changes, app integration |
| `owner` | | | Waits for the owner; `make next` skips it |

Drafting, gating, status and cleanup are scripts and need no model.

Use the strong model only where a wrong decision would make the comparison check the wrong thing. Everything the comparison can judge goes to the cheaper model.

## What to recover, and what not

Recover game code: the code that decides what happens in the game. The platform layer is replaced by native code, not recovered instruction by instruction:

- Windows and DirectX calls, listed in `docs/PLATFORM-BOUNDARY.md`.
- The C runtime and MFC, approximately the code at `0x4a1300` to `0x4b3400` and from `0x4f0000` up.

The draft command refuses platform-layer functions unless `--library-reason` says why native code will not do. The families already recovered from the platform layer (`crt_*`, `mfc_*`, `static_*` and most `application_*`) stay as they are. Do not extend them, and do not certify them further.

The app does not run the original `WinMain` or MFC startup. It starts natively, provides what that startup would have provided, and calls game code from there.

## What counts as evidence

- A family is verified when `make gate FAMILY=<id> ARGS=--record` admits it. Nothing else is needed and nothing else is accepted.
- No milestone runs, retained-hash snapshots, audits of snapshots or full-suite re-runs. `make milestone` is retired.
- When native code joins two families at a new boundary, check the join with the smallest comparison that exercises it. Re-run a suite only when one of its inputs changed and the task depends on it.
- Build success, a comparison passing, the app showing something on screen and device acceptance are four different results. Say which one you have.

## Disk

- `make disk` shows `work/` against its 25 GB budget and fails when over. Remove regenerable intermediates when space is tight.
- Never copy the source tree per run. Use the content-hashed build cache under `work/build/`.
- Delete what your task created under `work/` when it is no longer needed, except evidence a family's gate references.
- `make cleanup` lists regenerable leftovers.

## Writing

- Results go into `queue finish` and into generated files (`make status`, `make progress`). Do not write new handoff or status documents.
- Instruction files stay short. `make lint-docs` must pass: `CLAUDE.md` under 60 lines, `AGENTS.md` under 30, this file under 260, and no numbers glued to words.
- Plain sentences. Spell out what a number counts.

## Recovering a family

When a canonical family needs another admitted family's implementation, declare `shared_sources` with that family and its paths (see `Tests/clawparity/README.md`), leaving `sources` and `canonical_sources` for files the new family owns.

The pipeline is unchanged. The details are in `tools/workflows/roles/` and `Tests/clawparity/README.md`.

1. `make backlog` lists object classes with no code. Other targets come from the queue.
2. Draft: `work/test-env/bin/python -m tools.claw draft --id <id> --title "<title>" --seeds <address> [--object-logic]`. If it lists `needs_review` points, the strong model settles them with `tools/workflows/roles/boundary.md`.
3. Test cases: a fresh cheaper-model worker with `tools/workflows/roles/case-author.md`. Done when `make cases-check FAMILY=<id>` passes with full coverage, then `make seal FAMILY=<id> ROLE=case-author`.
4. Translation: a fresh cheaper-model worker with `tools/workflows/roles/translator.md`. Done when `make oracle` and `make guard ROLE=translator` pass.
5. Triage only if translation is blocked: the strong model with `tools/workflows/roles/triage.md`.
6. `make gate FAMILY=<id> ARGS=--record`. If rejected for weak tests, send the case author back with `work/gate/<id>/gate.json`.

Give each worker only this:

```text
Repository: the current checkout. Your role is described in tools/workflows/roles/<role>.md. Read that file first and follow it exactly.
Family id: <id>. Specification: Tests/families/<id>.json. Packet directory: work/packets/<id>/.
Touch only the files your role allows. Never run git commands that change anything. Return the result your role asks for and stop.
```

## Integration

`tools/workflows/NATIVE-INTEGRATION.md` describes the native host mechanisms already in the code (`ClawNativeCanonicalHost`, typed source edges, the shared allocator). Use it as reference when touching that code. It is not the plan; the queue is.

## Decisions the owner has made

- Movies: play the original movies, converted to HEVC or H.264 with AAC, through AVFoundation, at their original timing and resolution.
- Music: keep the original XMI events and play them through AVAudioUnitSampler with the original disc's SoundFont.
- Dialogs: native sheets that keep the original values, cancel and confirm behavior.
- Goal order: menu, New Game, Level 1, results, back to the menu. Then all 14 levels. Then the iPad.

## Hard rules

- A worker never edits a specification, another role's file, `Tests/clawparity/` or `tools/`.
- Nobody calls a family admitted. The gate does.
- Do not lower a threshold in `Tests/clawparity/gate.py`. Record a justified exemption in the specification, done by the coordinator after checking the reason.
- Decompiled and disassembled text stays under ignored `work/`.
