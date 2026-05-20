---
name: testing-standard
description: The MCR testing standard — use it to plan, write, and review tests. Apply when writing or planning new tests, deciding what a test should assert, or reviewing and auditing existing test files anywhere in the MCR codebase — backend (mcr-core, mcr-gateway, mcr-generation) or the mcr-frontend specs. Ensures tests protect business invariants rather than just running green.
---

# MCR testing standard

<purpose>
A test earns its place by stating a business invariant and failing exactly when that invariant is violated — ideally legibly enough that a Product Manager could read its name and agree it is a rule the product must uphold. Coverage proves a line ran; this standard proves a test would catch the bug that matters.

Use it two ways:

- Writing or planning: classify the layer, target the invariant and its failure directions, and steer clear of the fatal flags.
- Reviewing: run the four steps and return the output format at the end.
  </purpose>

<classify>
Step 1 — classify by role. The layer decides what the test must prove. Classify by what the code is for, not its path — the locations in the table are mcr-core examples, not the definition. Read the code under test if the name or location misleads; record any mismatch (it feeds D6).

| Layer    | Path                                               | The test must prove                                                                            |
| -------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| domain   | app/domain/\*\*                                    | the business rule across its input space; zero I/O                                             |
| use-case | app/use_cases/\*\*                                 | observable outcomes + side-effect discipline (persist, enqueue, rollback, best-effort)         |
| infra    | app/infrastructure/\*_, legacy services/_\_service | the translation to/from one external dep (request params, response mapping, error translation) |
| api      | app/api/\*\*                                       | input validation and wiring only                                                               |

Outside mcr-core (mcr-generation, mcr-frontend, gateway), map by function: a pure function/validator → domain; an orchestration flow (a Celery task, an LLM map-reduce) → use-case; a single-dependency client/wrapper (a frontend HTTP service) → infra; a thin request handler or a UI component that only wires props to render → api. Cross-service contract testing is not yet in place; note it, do not score it.
</classify>

<fatal-flags>
Step 2 — fatal flags. Any one makes the test worthless regardless of its assertions. In review, report FATAL(flag) and skip scoring that test.

- F1 SUT substitution — the test drives a copy or reimplementation of the code under test, not its real entry point. A helper that calls the real function is fine; one that duplicates its body is fatal.
- F2 vacuous — the test cannot fail for the reason it claims: bare `pytest.raises(Exception)`, a signature mismatch that raises before the code runs, asserting a mock's own return value, no assertion, a failure-path test whose failure never actually triggers (see escalation), or an arrangement too narrow to discriminate correct behavior from a no-op (the assertion would hold even if the behavior did nothing — e.g. a filter/pagination/search asserted with a single candidate present). Mechanical trigger: if the behavior the test names is not what determines pass/fail, it is F2 — regardless of how its other dimensions would score.
- F3 value mocked away — the test mocks the very thing its layer verifies. For infra, mocking the client is fine only if the request params, response mapping, and error translation are asserted; asserting only `assert_called_once()` trips F3.
  </fatal-flags>

<scoring>
Step 3 — score D1–D8. Rate each applicable dimension 2 full / 1 partial / 0 weak, or — if not applicable.

- Primary (weight 3): D1 invariant clarity (pins a rule, not a mechanic) · D2 BDD legibility (name states the rule in PM language) · D3 mutant survival (a subtle logic change would fail it; enumerate each value the code computes or forwards — an output no assertion names can be arbitrarily wrong and stay green; a full-output assertion over the complete input space is full marks even for a trivial function).
- Integrity (weight 2): D4 directional failure paths · D5 side-effect / transaction discipline (assert every side effect the flow produces — including secondary bookkeeping writes such as audit/transition records — in both directions: created, and absent after rollback or guard-reject) · D6 refactor-resilience + label honesty (asserts behavior not call order; claimed level matches reality).
- Hygiene (weight 1): D7 arrange clarity (only causal fields explicit; and a reader can follow the test without loading a large test-only apparatus — bespoke subclasses, mirror models, elaborate fixtures. Minimal necessary scaffolding is fine; excess that taxes comprehension is a dock even when each assertion is behavioral) · D8 one reason to fail.

Applicability per layer (2 central · 1 lighter · — not applicable; score only cells that apply):

| Layer    | D1  | D2  | D3  | D4  | D5  | D6  | D7  | D8  |
| -------- | --- | --- | --- | --- | --- | --- | --- | --- |
| domain   | 2   | 2   | 2   | 2   | —   | 2   | 2   | 2   |
| use-case | 2   | 2   | 2   | 2   | 2   | 2   | 2   | 2   |
| infra    | 2   | 1   | 2   | 2   | —   | 2   | 2   | 2   |
| api      | 2   | 2   | 1   | 1   | 1   | 2   | 2   | 2   |

D4 direction — use-case: a pre-commit failure must roll back with no partial state; a post-commit or best-effort failure must leave the core outcome intact (test both). domain: error and boundary inputs. infra: errors translated correctly.

Orchestration decomposition (use-case) — a use-case coordinates a domain guard, db writes, and infra calls; assert each against its own layer's rule, not as one blob. The load-bearing case is guard-before-IO: assert the domain guard is correct and that when it rejects, no db or infra side effect happened (the fakes recorded nothing). Proving the happy orchestration but never proving the guard gates the IO is a D4 weakness.

Scope appropriateness — test each invariant at the level that targets it with the least coupling and the best readability; scope is a deliberate choice, not a default. Trivial glue (a thin service, a simple mapping, a pass-through) barely holds an invariant at the unit, and its unit test couples to a function likely to be refactored away — cover it through the orchestration that uses it; a file that only pins trivial glue in isolation is dead weight (docks D6). Complex logic (rich branching, an algorithm) belongs in a focused unit — covering it only through an orchestration sprawls the test and hurts failure-localization and readability (docks D7). A scope mismatch either way is a real quality issue, independent of how well the assertions are written.
</scoring>

<caveats>
Step 4 — confidence caveats and escalation. Caveats qualify what a green test proves; they do not change the score except via escalation.

- C1 environment parity — the assertion relies on behavior the test environment cannot reproduce, so green here is not green in prod. Instances: SQLite standing in for Postgres (FK enforcement, constraint/type rejection, isolation, locking, real COMMIT vs nested savepoint); a mock server or stubbed API standing in for the real service (status codes, headers, error shapes). Enforce the invariant where the real environment can, or assert it explicitly at the app layer.
- C2 double fidelity — rate the doubles on a ladder: real-interface behavioral fake (models a real owned contract; preferred) > inert replay stub (canned data) > fabricated-external-contract fake (hand-builds a third-party shape) > logic-bearing fake (reimplements production logic inside the double). A fabricated-external-contract fake is a liability unless anchored — some test must verify the real dependency produces that shape, or the assertion rests on fiction. It escalates (caps the file at usable, a D6 weakness) only when all three hold: it is load-bearing for a surviving assertion, the shape is volatile or complex (a third-party lib's internals, an evolving wire format), and it is not a cross-service contract (those are noted, not scored — see Step 1). A trivial, stable, ubiquitous shape (an axios error, an HTTP status), an inert fake no assertion rests on, or a cross-service contract is a note, not an escalation. A logic-bearing fake escalates like F1 regardless: production logic living in a double drifts silently. Tell for both: a test-only abstraction with no production counterpart, built to fabricate contracts or paper over scattered wiring.

Escalation — separate reachability from parity. If a failure-path test's failure never actually triggers (e.g. injected before the guarded block runs), the recovery logic never ran and the assertion passes because nothing failed. That is not a C1 footnote — escalate to F2 if the path was the whole point, else a hard D4. Parity (the path runs but SQLite cannot vouch) stays C1.
</caveats>

<output>
Review output:

- Layer: <layer> (+ any name/location mismatch)
- Per test: `name` → FATAL(Fx) reason, or a D1–D8 line of 2/1/0/— per applicable dimension
- File verdict (rates test quality; the one coverage condition is the exemplar core gate in step 4) — derive it in order, do not eyeball it:
  1. fatally-flawed — a file-wide F1, or a majority of tests gated by a fatal flag.
  2. weak — else, if a majority of surviving tests are weak on the primary dimensions (D1–D3).
  3. usable — else, if there is any fatal test, any C2 escalation (a load-bearing volatile fabricated-contract, or a logic-bearing fake), a non-trivial core left unexercised, or a cluster (a third or more) of tests weak on the primaries.
  4. exemplar — none of the above: no fatal test, no C2 escalation, the unit's non-trivial core behavior exercised, (near-)all tests full on D1–D3 with failure directions covered. A lone low-leverage test, or trivial glue left to upstream coverage, does not by itself drop a file from exemplar.
- Caveats: C1/C2 instances, escalations called out
- Untested surface: behaviors of the unit that no test exercises — name them; an untested non-trivial core caps the verdict (step 4), other gaps do not lower it
- Highest-leverage fix: one sentence
  </output>
