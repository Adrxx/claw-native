export const meta = {
  name: 'claw-recover-families',
  description: 'Recover families through the canonical line: boundary review only where the scripted draft is unsure (Opus), blind cases (Sonnet), translation (Sonnet), triage on failure (Opus)',
  whenToUse: 'The coordinator first runs `make draft` for each family and afterwards `make gate`. args: {pilot, mode: "recover" | "extra-cases", families: [{id, title, seeds, review: [...open points...], findings: {survivors: [...], uncovered: [...]}}]}',
  phases: [
    { title: 'Boundary', detail: 'only for families whose draft has open points', model: 'opus' },
    { title: 'Cases', detail: 'blind test cases validated on the original alone', model: 'sonnet' },
    { title: 'Translate', detail: 'fill the module until the comparison passes', model: 'sonnet' },
    { title: 'Triage', detail: 'only when translation is blocked', model: 'opus' },
  ],
}

const REPO = process.cwd()
const pilot = !!(args && args.pilot)
const mode = (args && args.mode) || 'recover'
const families = (args && args.families) || []

function paths(family) {
  if (pilot) {
    const directory = `work/pilot/${family.id}`
    return { spec: `${directory}/family.json`, module: `${directory}/Module.cpp`, cases: `${directory}/cases.py` }
  }
  const name = family.id.split('_').map(part => part[0].toUpperCase() + part.slice(1)).join('')
  return { spec: `Tests/families/${family.id}.json`, module: `Sources/${name}Runtime.cpp`, cases: `Tests/families/${family.id}.cases.py` }
}

const PILOT_NOTE = pilot
  ? '\n\nThis is a measurement run. The functions already have a verified implementation elsewhere in this repository. The measurement is only valid if you work from the corpus and the packet, so the reading restrictions in your role file are strict, and your transcript will be audited for them.'
  : ''

function intro(role, family) {
  const where = paths(family)
  return `Repository: ${REPO}. Your role is described in tools/workflows/roles/${role}.md. Read that file first and follow it exactly.

Family id: ${family.id}
Title: ${family.title}
Specification: ${where.spec}
Module: ${where.module}
Cases: ${where.cases}
Packet directory: work/packets/${family.id}/${PILOT_NOTE}

Other workers are editing other families in this checkout. Touch only the files your role allows. Never run git commands that change anything. Your final answer is the structured result only.`
}

const BOUNDARY = { type: 'object', properties: {
  status: { type: 'string', enum: ['done', 'blocked'] },
  owned: { type: 'array', items: { type: 'object', properties: { address: { type: 'string' }, convention: { type: 'string' }, argc: { type: 'number' }, returns: { type: 'string' } }, required: ['address', 'convention', 'argc', 'returns'] } },
  fixtures: { type: 'array', items: { type: 'string' } },
  changed_from_draft: { type: 'array', items: { type: 'string' }, description: 'each field of the draft you corrected, and why' },
  lint: { type: 'string', description: 'final make lint JSON line' },
  notes: { type: 'string' },
}, required: ['status', 'owned', 'fixtures', 'changed_from_draft', 'lint', 'notes'] }

const CASES = { type: 'object', properties: {
  status: { type: 'string', enum: ['done', 'blocked'] },
  cases: { type: 'number' },
  checks_run: { type: 'number' },
  final_check: { type: 'string', description: 'final make cases-check (or make oracle) JSON line' },
  unreached: { type: 'array', items: { type: 'string' } },
  specification_problems: { type: 'array', items: { type: 'string' } },
}, required: ['status', 'cases', 'checks_run', 'final_check', 'unreached', 'specification_problems'] }

const TRANSLATE = { type: 'object', properties: {
  status: { type: 'string', enum: ['pass', 'blocked'] },
  oracle_runs: { type: 'number' },
  first_run_passed: { type: 'boolean', description: 'true when the very first make oracle run had status pass' },
  final_oracle: { type: 'string', description: 'final make oracle JSON line' },
  guard: { type: 'string', description: 'make guard JSON line' },
  diagnosis: { type: 'string' },
}, required: ['status', 'oracle_runs', 'first_run_passed', 'final_oracle', 'guard', 'diagnosis'] }

const TRIAGE = { type: 'object', properties: {
  kind: { type: 'string', enum: ['translation', 'case', 'specification', 'decompile-defect', 'harness-limit'] },
  evidence: { type: 'string' },
  changed: { type: 'string' },
  final_oracle: { type: 'string' },
  passes_now: { type: 'boolean' },
}, required: ['kind', 'evidence', 'changed', 'final_oracle', 'passes_now'] }

if (mode === 'extra-cases') {
  // Second round for families the gate rejected: the coordinator passes what the gate found.
  const extra = await parallel(families.map(family => () => agent(`${intro('case-author', family)}

This is a second round. Cases already exist and the native module passes them. The admission gate found behavior the cases do not check. Add cases so that these are caught; do not remove existing cases.

Surviving mutants (a deliberate one-line error in the module that no case noticed):
${(family.findings.survivors || []).join('\n') || 'none'}

Bytes of owned functions no case executed:
${(family.findings.uncovered || []).join('\n') || 'none'}

For each surviving mutant, work out from the disassembly which input would make the original's result depend on that statement, and add a case with that input. A survivor in code that provably cannot change the result is an equivalent mutant: say so under "unreached" with the reason. Validate with make cases-check, then run make oracle FAMILY=${family.id} once to confirm the module still passes, and report its JSON line in final_check.`,
    { label: `cases2:${family.id}`, phase: 'Cases', model: 'sonnet', effort: 'medium', schema: CASES })))
  return families.map((family, index) => ({ family: family.id, extra_cases: extra[index] }))
}

const results = await pipeline(families,
  family => {
    if (!family.review || !family.review.length) return { boundary: { status: 'done', skipped: 'the scripted draft had no open points' } }
    return agent(`${intro('boundary', family)}

Seed functions: ${family.seeds.join(', ')}.
A draft specification, stubs and packet already exist. The draft could not settle these points:
${family.review.map(point => `- ${point}`).join('\n')}`,
      { label: `boundary:${family.id}`, phase: 'Boundary', model: 'opus', effort: 'medium', schema: BOUNDARY })
      .then(boundary => ({ boundary }))
  },

  (state, family) => {
    if (!state.boundary || state.boundary.status !== 'done') return state
    return agent(intro('case-author', family), { label: `cases:${family.id}`, phase: 'Cases', model: 'sonnet', effort: 'medium', schema: CASES })
      .then(cases => ({ ...state, cases }))
  },

  (state, family) => {
    if (!state.cases || state.cases.status !== 'done') return state
    return agent(intro('translator', family), { label: `translate:${family.id}`, phase: 'Translate', model: 'sonnet', effort: 'medium', schema: TRANSLATE })
      .then(translation => ({ ...state, translation }))
  },

  (state, family) => {
    if (!state.translation || state.translation.status === 'pass') return state
    return agent(`${intro('triage', family)}

The translator reported:
${JSON.stringify(state.translation, null, 1)}`,
      { label: `triage:${family.id}`, phase: 'Triage', model: 'opus', effort: 'high', schema: TRIAGE })
      .then(triage => ({ ...state, triage }))
  },
)

return families.map((family, index) => ({ family: family.id, seeds: family.seeds, ...(results[index] || { failed: true }) }))
