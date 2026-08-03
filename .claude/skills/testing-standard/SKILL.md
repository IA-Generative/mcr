---
name: testing-standard
description: The MCR testing standard — use it to plan, write, and review tests. Apply when writing or planning new tests, deciding what a test should assert, or reviewing and auditing existing test files anywhere in the MCR codebase — backend (mcr-core, mcr-gateway, mcr-generation) or the mcr-frontend specs. Ensures tests protect business invariants rather than just running green.
---

# MCR testing standard

<purpose>
A test earns its place by stating a business invariant and failing exactly when that invariant is violated — ideally legibly enough that a Product Manager could read its name and agree it is a rule the product must uphold. Coverage proves a line ran; this standard proves a test would catch the bug that matters.

Test the business invariant *behind* a change, never the mechanism the diff just touched. Tells of a mechanism test (all worthless): it asserts a config value, `assert_called_once` alone, a wiring fact ("the handler is registered", "a log does not produce a Sentry event"), or you must drive a third-party library's internals to assert anything — that difficulty is itself the signal it's not a behavior test. For an observability/config change, the testable rule is the *product* consequence (resilience, an API contract); if the only effect is a monitoring-config value, it is verified by review + post-deploy, not a unit test.

Use it two ways:

- Writing or planning: follow `<authoring>`, classify the layer, target the invariant and its failure directions, and steer clear of the fatal flags. Do this **before** writing the test, not after — deciding the invariant from the code you already wrote produces mechanism tests.
- Reviewing: run the four steps and return the output format at the end.
  </purpose>

<authoring>
Step 0 — before writing. These constrain how a test comes into being; the rest of this standard judges the result.

- **TDD is mandatory.** The failing test is written and seen red before the implementation.
- **The red must be the behavioral one.** A collection error, an `ImportError`, or a signature mismatch is *not* a red: the assertion never ran, so nothing proved it can fail for the reason it names. Write the test against the intended signature and stub the symbol if you must, then watch the assertion itself fail. Confirm the same way after going green (break the fix, watch it go red).
- **Never let the TDD gate manufacture a test.** If you have to author a rationale for why an assertion matters — or you derive the invariant from the diff you just wrote — there is no invariant, and the honest output is no test. Mandatory TDD obliges you to write the test before the code, not to produce one for every change.
- **A pre-written design weakens TDD.** When the implementation is already settled — a plan, a snippet handed to you — writing the test first is transcription, not design pressure, and mechanism tests slip through precisely there. In that case state the invariant explicitly before the first assertion, and treat `no-invariant` as the live risk.
- **Never add a production seam just to make a test mockable.** A `_now()` wrapper introduced only to dodge a library's internal clock reads distorts prod code and usually means the test is at the wrong level — move the assertion to the unit that owns the behavior instead of reshaping prod.
- **When your change turns an existing test red, that red is a diagnostic.** If a test broke because a collaborator gained an internal step, it was coupled to that collaborator's internals (`refactor-proof`). Fix the coupling. Extending its mocks to restore green converts a diagnostic into debt.
  </authoring>

<classify>
Step 1 — classify by role. The layer decides what the test must prove. Classify by what the code is for, not its path — the locations in the table are mcr-core examples, not the definition. Read the code under test if the name or location misleads; record any mismatch (it feeds `refactor-proof`).

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

- **`no-invariant`** — the test pins no business rule. It asserts a config or monitoring value, a wiring fact ("the handler is registered", "a log does not produce a Sentry event"), or it needs a third-party library's internals driven (a hand-built framework event/hook payload) to assert anything. Equivalently: it would score 0 on `invariant`. A high `catches-mutants` score does **not** redeem it — a tight mechanism test is the expected profile, not a mitigation. If the change's only observable effect is a monitoring-config value, it is verified by review + post-deploy and needs no unit test at all. Origin tell: a docstring describing behavior the assertions below never exercise means the test was manufactured to clear the TDD gate — the rationale had to be authored because there was no invariant to state.
- **`tests-a-copy`** — the test drives a copy or reimplementation of the code under test, not its real entry point. A helper that calls the real function is fine; one that duplicates its body is fatal.
- **`cannot-fail`** — the test cannot fail for the reason it claims: bare `pytest.raises(Exception)`, a signature mismatch that raises before the code runs, asserting a mock's own return value, no assertion, a failure-path test whose failure never actually triggers (see escalation), or an arrangement too narrow to discriminate correct behavior from a no-op (the assertion would hold even if the behavior did nothing — e.g. a filter/pagination/search asserted with a single candidate present). Mechanical trigger: if the behavior the test names is not what determines pass/fail, it is `cannot-fail` — regardless of how its other dimensions would score.
- **`mocks-the-point`** — the test mocks the very thing its layer verifies. For infra, mocking the client is fine only if the request params, response mapping, and error translation are asserted; asserting only `assert_called_once()` trips this. For a use-case, stubbing out the domain guards it is supposed to prove gate the I/O trips it too.
  </fatal-flags>

<scoring>
Step 3 — score the dimensions. Rate each applicable dimension 2 full / 1 partial / 0 weak, or — if not applicable.

- Primary (weight 3):
  - **`invariant`** — pins a business rule, not a mechanic. A 0 here is disqualifying: report `no-invariant` and stop.
  - **`legible-name`** — the name states the rule in PM language.
  - **`catches-mutants`** — a subtle logic change would fail it; enumerate each value the code computes or forwards — an output no assertion names can be arbitrarily wrong and stay green; a full-output assertion over the complete input space is full marks even for a trivial function.
- Integrity (weight 2):
  - **`failure-directions`** — failure paths covered, with direction.
  - **`side-effects`** — assert every side effect the flow produces — including secondary bookkeeping writes such as audit/transition records — in both directions: created, and absent after rollback or guard-reject.
  - **`refactor-proof`** — asserts behavior not call order; claimed level matches reality (label honesty).
- Hygiene (weight 1):
  - **`clear-arrange`** — only causal fields explicit; a reader can follow the test without loading a large test-only apparatus (bespoke subclasses, mirror models, elaborate fixtures). Minimal necessary scaffolding is fine; excess that taxes comprehension is a dock even when each assertion is behavioral.
  - **`one-reason`** — one reason to fail.

Applicability per layer (2 central · 1 lighter · — not applicable; score only cells that apply):

| Dimension            | domain | use-case | infra | api |
| -------------------- | ------ | -------- | ----- | --- |
| `invariant`          | 2      | 2        | 2     | 2   |
| `legible-name`       | 2      | 2        | 1     | 2   |
| `catches-mutants`    | 2      | 2        | 2     | 1   |
| `failure-directions` | 2      | 2        | 2     | 1   |
| `side-effects`       | —      | 2        | —     | 1   |
| `refactor-proof`     | 2      | 2        | 2     | 2   |
| `clear-arrange`      | 2      | 2        | 2     | 2   |
| `one-reason`         | 2      | 2        | 2     | 2   |

`failure-directions` per layer — use-case: a pre-commit failure must roll back with no partial state; a post-commit or best-effort failure must leave the core outcome intact (test both). domain: error and boundary inputs. infra: errors translated correctly.

Orchestration decomposition (use-case) — a use-case coordinates a domain guard, db writes, and infra calls; assert each against its own layer's rule, not as one blob. The load-bearing case is guard-before-IO: assert the domain guard is correct and that when it rejects, no db or infra side effect happened (the fakes recorded nothing). Proving the happy orchestration but never proving the guard gates the IO is a `failure-directions` weakness. Stubbing those guards out instead is `mocks-the-point`.

Scope appropriateness — test each invariant at the level that targets it with the least coupling and the best readability; scope is a deliberate choice, not a default. Trivial glue (a thin service, a simple mapping, a pass-through) barely holds an invariant at the unit, and its unit test couples to a function likely to be refactored away — cover it through the orchestration that uses it; a file that only pins trivial glue in isolation is dead weight (docks `refactor-proof`). Complex logic (rich branching, an algorithm) belongs in a focused unit — covering it only through an orchestration sprawls the test and hurts failure-localization and readability (docks `clear-arrange`). A scope mismatch either way is a real quality issue, independent of how well the assertions are written.
</scoring>

<caveats>
Step 4 — confidence caveats and escalation. Caveats qualify what a green test proves; they do not change the score except via escalation.

- **`env-parity`** — the assertion relies on behavior the test environment cannot reproduce, so green here is not green in prod. Instances: SQLite standing in for Postgres (FK enforcement, constraint/type rejection, isolation, locking, real COMMIT vs nested savepoint); a mock server or stubbed API standing in for the real service (status codes, headers, error shapes). Enforce the invariant where the real environment can, or assert it explicitly at the app layer.
- **`double-fidelity`** — rate the doubles on a ladder: real-interface behavioral fake (models a real owned contract; preferred) > inert replay stub (canned data) > fabricated-external-contract fake (hand-builds a third-party shape) > logic-bearing fake (reimplements production logic inside the double). A fabricated-external-contract fake is a liability unless anchored — some test must verify the real dependency produces that shape, or the assertion rests on fiction. It escalates (caps the file at usable, a `refactor-proof` weakness) only when all three hold: it is load-bearing for a surviving assertion, the shape is volatile or complex (a third-party lib's internals, an evolving wire format), and it is not a cross-service contract (those are noted, not scored — see Step 1). A trivial, stable, ubiquitous shape (an axios error, an HTTP status), an inert fake no assertion rests on, or a cross-service contract is a note, not an escalation. A logic-bearing fake escalates like `tests-a-copy` regardless: production logic living in a double drifts silently. Tell for both: a test-only abstraction with no production counterpart, built to fabricate contracts or paper over scattered wiring.

Escalation — separate reachability from parity. If a failure-path test's failure never actually triggers (e.g. injected before the guarded block runs), the recovery logic never ran and the assertion passes because nothing failed. That is not an `env-parity` footnote — escalate to `cannot-fail` if the path was the whole point, else a hard `failure-directions`. Parity (the path runs but SQLite cannot vouch) stays `env-parity`.
</caveats>

<output>
Review output:

- Layer: <layer> (+ any name/location mismatch)
- Per test: `name` → FATAL(flag) reason, or a line of 2/1/0/— per applicable dimension
- File verdict (rates test quality; the one coverage condition is the exemplar core gate in step 4) — derive it in order, do not eyeball it:
  1. fatally-flawed — a file-wide `tests-a-copy`, or a majority of tests gated by a fatal flag.
  2. weak — else, if a majority of surviving tests are weak on the primary dimensions.
  3. usable — else, if there is any fatal test, any `double-fidelity` escalation (a load-bearing volatile fabricated-contract, or a logic-bearing fake), a non-trivial core left unexercised, or a cluster (a third or more) of tests weak on the primaries.
  4. exemplar — none of the above: no fatal test, no `double-fidelity` escalation, the unit's non-trivial core behavior exercised, (near-)all tests full on the primaries with failure directions covered. A lone low-leverage test, or trivial glue left to upstream coverage, does not by itself drop a file from exemplar.
- Caveats: `env-parity` / `double-fidelity` instances, escalations called out
- Untested surface: behaviors of the unit that no test exercises — name them; an untested non-trivial core caps the verdict (step 4), other gaps do not lower it
- Highest-leverage fix: one sentence
  </output>
