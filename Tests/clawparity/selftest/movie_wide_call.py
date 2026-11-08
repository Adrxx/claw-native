"""Read-only entry witnesses for the unchanged original 31-word movie callee.

Runs the existing movie cases without changing their setup, fixtures or source.
The observer checks copied native metadata against the physical x86 entry and
then compares that entry with the original caller's entry, including word 31.
"""
import json
import sys
from types import SimpleNamespace
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from .. import runner
from ..env import Env


def check():
    observations = []

    class ObservedEnv(Env):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.machine.uc.hook_add(UC_HOOK_CODE, self.observe, begin=0x4f0000, end=0x4f0000)

        def _begin_case(self, random_source):
            super()._begin_case(random_source)
            self.entries = {'native': [], 'original': []}
            self.metadata = []

        def observe(self, uc, pc, size, user):
            esp = uc.reg_read(UC_X86_REG_ESP)
            self.entries[self.side].append((uc.reg_read(UC_X86_REG_ECX), esp,
                                            tuple(self.machine.words(esp + 4, 31))))

        def _bridge(self, call, *args, **kwargs):
            if call.function == 0x4f0000:
                self.metadata.append((call.receiver, call.stack_pointer, call.arguments))
            return super()._bridge(call, *args, **kwargs)

        def run_original(self, *args, **kwargs):
            result = super().run_original(*args, **kwargs)
            if self.entries['original'] or self.metadata:
                observations.append(dict(
                    all_31_words_preserved=self.metadata == self.entries['native'] == self.entries['original'],
                    native_entries=len(self.entries['native']), original_entries=len(self.entries['original']),
                    argument_counts=[len(row[2]) for row in self.metadata],
                    final_words=[row[2][-1] for row in self.metadata]))
            return result

    previous_env, previous_cases = runner.Env, runner.load_cases
    # The existing case module uses the public clawparity package spelling.
    sys.path.insert(0, str(runner.ROOT / 'Tests'))
    runner.Env = ObservedEnv
    def movie_cases(spec):
        cases = previous_cases(spec)
        return SimpleNamespace(cases=lambda rng: (c for c in cases.cases(rng) if c.function == 0x42b140))
    runner.load_cases = movie_cases
    try:
        result = runner.run(runner.ROOT / 'Tests/families/booty_progression.json')
    finally:
        runner.Env, runner.load_cases = previous_env, previous_cases
        sys.path.pop(0)
    passed = (len(observations) == 9 and all(o['all_31_words_preserved'] and
        o['argument_counts'] == [31] and o['native_entries'] == o['original_entries'] == 1 for o in observations)
        and any(o['final_words'] == [0x89abcdef] for o in observations))
    return dict(passed=passed, observed_cases=len(observations), observations=observations,
                comparison={k: result.get(k) for k in ('status', 'cases', 'passed', 'failed', 'failures')})


if __name__ == '__main__':
    result = check()
    print(json.dumps(result))
    raise SystemExit(not result['passed'])
