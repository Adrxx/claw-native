# Captain Claw reconstruction harness. Every target prints one line of JSON as its last line.
PY := work/test-env/bin/python
CLAW := $(PY) -m tools.claw
ROLE ?= translator

.PHONY: help next take finish block reopen usage lint-docs disk platform-boundary oracle gate lint skeleton packet feedback guard seal mutants cases-check manifests sync status baseline regate \
        selftest workflow-check corpus-check symbols-check project project-check format-check cleanup progress backlog milestone

help:
	@echo "Start here:"
	@echo "  make next       the next task from tools/queue.json (one task per session)"
	@echo "  make take ID=<id>, make finish ID=<id> NOTE=\"...\", make block ID=<id> NOTE=\"...\""
	@echo "  make usage      token use of recent agent sessions; flags sessions over budget"
	@echo "  make lint-docs  instruction files short and readable"
	@echo "  make disk       size of work/ against its budget"
	@echo "  make platform-boundary  what game code needs from the native platform layer"
	@echo "Per family (FAMILY=<id>):"
	@echo "  make oracle     run the family's comparison against the original"
	@echo "  make gate       admission gate: unseen seed, coverage, sanitizer, mutants (ARGS=--record stores the result)"
	@echo "  make lint       check a canonical specification against the disassembly"
	@echo "  (draft)         work/test-env/bin/python -m tools.claw draft --help: write a specification from the disassembly"
	@echo "  make skeleton   generate module and cases stubs from a specification"
	@echo "  make packet     build the worker task packet under work/packets/"
	@echo "  make feedback   write case-author feedback without native source snippets"
	@echo "  make cases-check  run the cases on the original alone; reports errors and coverage"
	@echo "  make seal       ROLE=...: record the file your role owns as finished"
	@echo "  make guard      ROLE=translator|case-author: protected files unchanged?"
	@echo "  make mutants    mutation score of the family's cases"
	@echo "Whole repository:"
	@echo "  make manifests  validate every family manifest"
	@echo "  make sync       refresh generated manifest fields from the tree"
	@echo "  make status     regenerate docs/STATUS.md from the manifests"
	@echo "  make baseline   re-run every legacy comparison once"
	@echo "  make regate     measure legacy families: unseen seeds and coverage"
	@echo "  make selftest   test the harness itself on a synthetic program (no originals needed)"
	@echo "  make workflow-check  test role guards and blind feedback (no originals needed)"
	@echo "  make project    regenerate Xcode membership; project-check verifies it"
	@echo "  make corpus-check symbols-check format-check"
	@echo "  make backlog    object classes that still have no code, most-placed first"
	@echo "  make progress   rebuild the progress page (work/progress/claw-progress.html, or OUT=<path>)"
	@echo "  make cleanup    list build leftovers under work/ (deletes nothing)"

oracle:   ; @$(CLAW) oracle $(FAMILY) $(ARGS)
gate:     ; @$(CLAW) gate $(FAMILY) $(ARGS)
lint:     ; @$(CLAW) lint $(FAMILY)
skeleton: ; @$(CLAW) skeleton $(FAMILY)
packet:   ; @$(CLAW) packet $(FAMILY)
feedback: ; @$(CLAW) feedback $(FAMILY)
guard:    ; @$(CLAW) guard $(FAMILY) $(ROLE)
seal:     ; @$(CLAW) seal $(FAMILY) $(ROLE)
mutants:  ; @$(CLAW) mutants $(FAMILY) $(ARGS)
cases-check: ; @$(CLAW) cases-check $(FAMILY) $(ARGS)
manifests: ; @$(CLAW) manifests
sync:     ; @$(CLAW) sync
status:   ; @$(CLAW) status
baseline: ; @$(CLAW) baseline --output work/baseline/baseline-$$(date +%F).jsonl $(ARGS)
regate:   ; @$(CLAW) regate $(ARGS)
selftest: ; @cd Tests && ../$(PY) -m clawparity.selftest
workflow-check: ; @$(PY) tools/workflows/check-protections.py
corpus-check:  ; @$(PY) -m tools.claw.corpus check
symbols-check: ; @$(PY) -m tools.claw.symbols check
project:       ; @$(PY) -m tools.claw.gen_project write
project-check: ; @$(PY) -m tools.claw.gen_project check
format-check:  ; @$(PY) -m tools.claw.format_guard check
cleanup:       ; @$(PY) -m tools.claw.cleanup
backlog:       ; @$(CLAW) backlog
next:          ; @$(CLAW) queue next
take:          ; @$(CLAW) queue start $(ID)
finish:        ; @$(CLAW) queue finish $(ID) "$(NOTE)"
block:         ; @$(CLAW) queue block $(ID) "$(NOTE)"
reopen:        ; @$(CLAW) queue reopen $(ID) "$(NOTE)"
usage:         ; @$(CLAW) usage
lint-docs:     ; @$(CLAW) lint-docs
platform-boundary: ; @$(CLAW) platform-boundary
disk:          ; @$(CLAW) disk
progress:      ; @$(PY) -m tools.claw.progress_page $(OUT)
milestone:     ; @echo '{"command": "milestone", "status": "retired", "detail": "the admission gate is the evidence; see docs/OPERATING.md"}'
