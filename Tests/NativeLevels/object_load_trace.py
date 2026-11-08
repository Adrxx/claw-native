"""Observe original named-object lookup during ordinary later-level progression.

This observer never changes guest registers, memory, callbacks or game decisions.
The inherited platform adapter supplies MFC maps; original registration and
world loading execute normally. A short run certifies loading only, not a route.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unicorn import UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP)
from Tests.NativeLevels import ROOT
from Tests.NativeLevels.trace import Blocked
from Tests.NativeLevels.xmidi_clock import TempoClockTrace


REGISTERS = dict(eax=UC_X86_REG_EAX, ebx=UC_X86_REG_EBX, ecx=UC_X86_REG_ECX,
    edx=UC_X86_REG_EDX, esi=UC_X86_REG_ESI, edi=UC_X86_REG_EDI,
    ebp=UC_X86_REG_EBP, esp=UC_X86_REG_ESP)
WATCH = {'Sign', 'Aquatis', 'AquatisCrack', 'AquatisDynamite',
         'AquatisStalactite', 'Tentacle', 'Stalactite'}


class ObjectLoadTrace(TempoClockTrace):
    def __init__(self, *, destination=12, evidence_dir, checkpoint_each_level=False,
                 stop_after_checkpoint=None, **kwargs):
        super().__init__(**kwargs)
        self.destination = destination
        self.evidence_dir = evidence_dir
        self.checkpoint_each_level = checkpoint_each_level
        self.stop_after_checkpoint = stop_after_checkpoint
        self.object_lookups = []
        self.pending_lookups = []
        self.sign_steps = []
        self.watch_steps = 0

    def checkpoint_inputs(self):
        return {**super().checkpoint_inputs(),
            'Original/retail-assets/LEVEL12/WORLDS/WORLD.WWD': hashlib.sha256(
                (ROOT/'Original/retail-assets/LEVEL12/WORLDS/WORLD.WWD').read_bytes()).hexdigest(),
            'Tests/NativeLevels/object_load_trace.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def hook(self, machine, address, size, user):
        sp = machine.reg_read(UC_X86_REG_ESP) if address == 0x4f6286 or self.pending_lookups else 0
        for event in self.pending_lookups[:]:
            if address == event['caller'] and sp == event['sp']+12:
                event['return'] = machine.reg_read(UC_X86_REG_EAX)
                event['value'] = self.word(event['output'])
                self.pending_lookups.remove(event)
                if event['name'] == 'Sign':
                    print(json.dumps(dict(event='sign-lookup-return', **event)), flush=True)
        if address == 0x4f6286:
            name = self.bytestring(self.word(sp+4)).decode('ascii', errors='replace')
            if name in WATCH:
                event = dict(name=name, phase=self.phase, caller=self.word(sp), sp=sp,
                    receiver=machine.reg_read(UC_X86_REG_ECX), output=self.word(sp+8),
                    instructions=self.instructions)
                if name == 'Sign':
                    event['registers'] = {n:machine.reg_read(r) for n,r in REGISTERS.items()}
                    event['memory'] = {}
                    for name_, pointer in event['registers'].items():
                        try:
                            event['memory'][name_] = bytes(machine.mem_read(pointer, 512)).hex()
                        except UcError:
                            pass
                    self.watch_steps = 400
                self.object_lookups.append(event)
                self.pending_lookups.append(event)
        if self.watch_steps:
            self.sign_steps.append(dict(address=address,
                registers={n:machine.reg_read(r) for n,r in REGISTERS.items()}))
            self.watch_steps -= 1
        super().hook(machine, address, size, user)

    def retain_start(self, level):
        previous = self.target_level
        self.target_level = level
        self.checkpoint_inputs_sha256 = self.checkpoint_inputs()
        self.checkpoint_path = self.evidence_dir/f'level-{level}.checkpoint'
        self.save_checkpoint()
        self.checkpoint_path = None
        self.target_level = previous

    def complete_level(self, application, level):
        super().complete_level(application, level)
        if self.checkpoint_each_level or level in (10, 11):
            self.retain_start(level+1)
            if self.stop_after_checkpoint == level+1:
                raise Blocked(f'Retained requested Level {level+1} checkpoint')

    def play_target(self, application):
        for level in range(self.target_level, self.destination):
            # Result validation follows the level being advanced, including
            # when a fresh loading observer resumes an intermediate checkpoint.
            self.target_level = level
            self.complete_level(application, level)
        self.target_level = self.destination
        super().play_target(application)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--paper-startup', action='store_true')
    parser.add_argument('--from-level', type=int, default=12)
    parser.add_argument('--checkpoint-each-level', action='store_true')
    parser.add_argument('--stop-after-checkpoint', type=int, choices=range(2, 13))
    parser.add_argument('--output-dir', type=Path, default=ROOT/'work/level-12-sign-discovery')
    args = parser.parse_args()
    if args.stop_after_checkpoint is not None and not args.checkpoint_each_level:
        parser.error('--stop-after-checkpoint requires --checkpoint-each-level')
    out = args.output_dir.resolve()
    assert out.is_relative_to(ROOT/'work')
    out.mkdir(parents=True, exist_ok=True)
    tracer = ObjectLoadTrace(level=args.from_level, evidence_dir=out,
        checkpoint_each_level=args.checkpoint_each_level, stop_after_checkpoint=args.stop_after_checkpoint,
        instruction_limit=15_000_000_000, deny_platform=None, route=[], play_ms=0,
        startup_paper=args.paper_startup)
    try:
        if args.resume:
            tracer.resume_target(args.resume.resolve())
        else:
            tracer.execute()
    except (Blocked, UcError) as error:
        if tracer.stop is None:
            tracer.stop = dict(reason=str(error), phase=tracer.phase)
    finally:
        for stream in tracer.files.values():
            stream.close()
    report = dict(startup_paper=tracer.startup_paper, startup_profile=tracer.startup_profile,
        clock_query_ms=1 if tracer.startup_paper else None, startup_context=tracer.startup_evidence,
        schema=1, level=tracer.target_level, executable_sha256=tracer.program.sha256,
        inputs_sha256=tracer.checkpoint_inputs(), loaded=tracer.loaded, stop=tracer.stop,
        object_lookups=tracer.object_lookups, sign_steps=tracer.sign_steps,
        completions=tracer.completions, cheat_keys=tracer.cheat_keys,
        state_transitions=tracer.state_transitions,
        status='pass' if tracer.loaded and tracer.stop is None else 'blocked',
        scope='Original object-loading boundary only; no sixty-second route or native join')
    (out/'object-loading.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status', 'level', 'loaded', 'stop')}), flush=True)
    return 0 if report['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
