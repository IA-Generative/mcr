---
name: debug-production-issue
description: Structured production-debugging workflow with explicit quality-control checkpoints. Use this skill whenever the user opens a production-issue investigation — Sentry/Datadog/PagerDuty alerts, "X is slow in prod", "find the root cause of Y", a request for a "debug plan" or "investigation plan", or a request to triage an on-call incident. Strongly prefer this skill over ad-hoc debugging when the cause is unknown and observable in production. Do NOT use for local development bugs the user can already reproduce, for issues whose root cause is already named, or for simple "fix this typo" tasks.
argument-hint: "[issue ID, alert URL, or 1-line description of the prod symptom]"
---

You are debugging a production issue whose root cause is unknown. The single most common failure mode in this kind of work is **acting on the first plausible hypothesis before the data has eliminated the others**. This skill exists to slow that reflex down: characterize the issue with data, falsify hypotheses one at a time, and only propose fixes once the cause is identified — not the symptom.

The workflow has five phases. Each phase has a quality-control checkpoint at the end; do not advance until the check passes.

---

## Phase 1 — Pull authoritative context

Never work from a screenshot, paraphrase, or summary. Fetch the actual error.

- Sentry / similar: pull the issue with full stack trace, occurrence count, time range, environments, tags, request URL/method, and trace ID.
- For an alert without an error: pull the underlying metric series (Grafana/Prometheus/CloudWatch) — the actual numbers, not the dashboard rendering.
- For a slow endpoint: pull a recent failing or slow trace ID and walk it.

State plainly to the user what you fetched and what's in it. If the source system is misconfigured, unreachable, or the issue ID doesn't resolve, stop and ask — do not fabricate context from the symptom name.

**QC checkpoint:** You can name the failing call site (file:line), the exception type, the first-seen / last-seen timestamps, and at least one tag (environment, release, server) before continuing.

---

## Phase 2 — Identify call sites

Find every caller of the failing endpoint or function. The set of callers often *is* the answer — a 500 on `/api/X/start` with one programmatic caller (a Celery prerun signal handler) means a very different thing than a 500 with a frontend caller.

- Grep for the function name, the URL path, and the message constants the failure produces.
- Distinguish: user-driven (frontend, public API), programmatic (background workers, signal handlers, retries), scheduled (cron, periodic tasks).
- For each caller, note: what triggers it, how often, what timeout/retry policy it has, and whether it can fire concurrently with itself.

**QC checkpoint:** You have a labelled list of all callers and you know which one is producing the events in Sentry (via URL, server name, or tag). If only one caller exists and the failure rate is high, the bug usually lives in the *contract* between caller and callee — flag that.

---

## Phase 3 — Characterize with data, not anecdote

Translate the symptom into measurable distributions before reasoning about cause.

- Write the SQL/log query that produces the metric the alert claims is bad. Aggregations: count, P50, P95, P99, max. Bucket by category (status, platform, version) and time.
- Compute base rates. "569 errors in 4 months" means nothing without "out of how many requests".
- For latency: P50 and P99 are different stories. Heavy right-skew (P50 ≪ P99) implies a tail; uniform slowness implies structural cost.

When the result reframes the problem (e.g. "the slow tail is on *short* inputs, not long"), pause and re-state what the new picture is before continuing. The reframing is usually the most valuable output of this phase.

**QC checkpoint:** You can show the user a small table of numbers (per-category counts, percentile distribution, base rate) — not a verbal claim. Without numbers, do not move on.

---

## Phase 4 — Disambiguate

You almost always end Phase 3 with two or three plausible hypotheses that fit the data so far. The job in this phase is to design the next query (or experiment) that distinguishes them.

Common disambiguation patterns:

- **Symptom-class queries.** "Was this slow because the same task ran multiple times, or because one attempt was slow?" → query for retry/redelivery markers (extra status transitions, log lines from N workers). Until the result is in, do not write any code.
- **Selection-bias correction.** Items that appear in error logs are biased samples of the long tail. Compute the same statistic on the full population. If the picture flips (e.g. P50 in the broader population is fast and only the Sentry-sampled set is slow), update the model accordingly.
- **Ground-truth verification.** When a recorded value is implausible (a 15-second meeting taking 67 minutes to "transcribe"), pull the underlying artifact (audio file, payload, image) and verify it with a neutral tool (`ffprobe`, file size, hash). Don't trust derived columns when the original is available.
- **Local instrumentation.** Build a minimum-viable local reproduction that runs each pipeline stage with `time.perf_counter` (or your stack's equivalent) against the actual artifact you pulled. The PROD/local discrepancy *ratio*, computed across multiple inputs, tells you whether the bug lives in the code or in the environment:
  - Roughly constant ratio across input sizes → environment (slower CPU/network, contention, shared resource).
  - Ratio that grows for some input characteristic → code path triggered conditionally on that characteristic.
  - Ratio that explodes by 100×+ → almost always a hang on an unbounded operation, not slow compute.

**QC checkpoint:** You have ruled out at least one hypothesis with evidence. If two hypotheses still both fit the data, you are not done with this phase yet — design another query. Do not move on with multiple unfalsified hypotheses.

---

## Phase 5 — Find the cause and plan the fix

By now the data has narrowed the search. Read code with **one specific question**, not generally.

- "Where could this hang?" → grep for HTTP/LLM/IO/DB clients without explicit `timeout=`. Note default behavior of the SDK in question (e.g. OpenAI SDK defaults to 600s read timeout; httpx defaults to 5s).
- "Where could this loop?" → grep for retries without bounded `max_retries`, recursive validators, polling loops without exit conditions.
- "Where could state diverge?" → grep for the writes that should be transactional but aren't, signal handlers that update state independently of the body.

Separate symptom from cause explicitly. The alert that fires is often the *last* thing that happens. Build a wall-clock breakdown for the failing case: "T0: prerun ran. T0+ε: body started. T0+~10s: real work done. T0+~60min: visibility timeout fired and message redelivered. T0+~67min: second worker completed." If your model of where time goes doesn't match the observed wall-clock, your hypothesis is incomplete.

### Plan the fix BEFORE coding

For every proposed change, write down (in this order, in a plan document or in chat):

1. **Files modified** with file:line refs.
2. **Unit / integration test** that proves the change does what it claims.
3. **Manual reproduction** — what command, what input, what expected outcome. If a manual repro requires temporarily mutilating production code (e.g. setting a 60s timeout to test a 90min default), write the *revert* step in the same plan.
4. **What's intentionally NOT being done** in this PR — e.g. "we are skipping idempotency at the orchestrator; consequence is that redelivered preruns will return 409 instead of 500, verify post-deploy that Sentry's CeleryIntegration doesn't capture 4xx as warnings".

Present the plan to the user and ask which fixes to keep before implementing. The user often rejects a step or modifies a parameter; doing this before code is written saves rework.

### Implement one step at a time

After each step, run the test gate (lint + type-check + tests) and fix any regression before starting the next step. Cross-effects between steps (e.g. a new exception type breaks an unrelated catch site that was relying on the old type) surface here.

### Don't overfit observability to the fix

Once the active errors are silenced (via idempotency, graceful degradation, or 4xx mapping), instruments that **only fire on errors** become useless. Sentry breadcrumbs without a corresponding span/transaction or structured log fire only when an event actually ships — silence the events and the breadcrumbs ship nowhere.

When adding observability as part of the fix, choose telemetry that survives the fix:
- **Sentry spans** on existing transactions if `traces_sample_rate > 0`.
- **Structured logs** with stage durations as fields, ingested by the log aggregator. Always emitted.
- **Breadcrumbs** are appropriate where you're *swallowing* an error that an operator might still want context for if a downstream failure fires — a narrow, intentional use, not a general "stage timing" pattern.

**QC checkpoint:** The fix plan has been agreed with the user, each step has its own test, and the observability you're adding survives the fix you're shipping.

---

## Output format

Throughout the investigation, emit short, scannable reports rather than walls of prose. After each phase, post:

```
### Phase N — <what you found>
**Data:** <table or 2-line summary of the numbers>
**Hypotheses now eliminated:** <list>
**Hypotheses still on the table:** <list>
**Next:** <the specific query, file read, or experiment that comes next>
```

When proposing the final fix, post a markdown investigation summary to the repo (alongside any data files used) so the team can re-read it asynchronously. Cover: issue link + short symptom, investigation arc with the data tables, root-cause model, recommended fixes ordered by leverage, what's verified vs hypothesis, and what external verifications still need to be done after deploy.

---

## Anti-patterns to avoid

- **Don't propose a fix until you've characterized the data.** If you can't write a 2×N table of numbers describing the issue, you're not ready to fix it.
- **Don't claim a regression without a base rate.** "569 errors" is not a regression unless you also know the total request count and the historical baseline.
- **Don't conflate the symptom alert with the underlying cause.** The Sentry 500 is downstream. The wall-clock breakdown should explain every minute of the elapsed time, including the parts where nothing user-visible was happening.
- **Don't add observability that only fires when the code path you just silenced fires.** Choose telemetry that ships even when everything is healthy.
- **Don't skip the disambiguation phase.** The first plausible hypothesis is wrong often enough that anchoring on it costs more time than designing one more query.
- **Don't conflate the meetings/users/requests in the error sample with the typical population.** Selection bias is the rule, not the exception, in any error log.
- **Don't read code at random.** Once you have a hypothesis class ("this hangs"), grep for that specific pattern. Random reading rarely yields the smoking gun in time.
- **Don't ship cross-cutting changes in one PR if they can be split.** But if they're tightly coupled (e.g. a new exception type + the catch sites that depend on it), bundling is correct — let the test gate decide.

---

## When this skill does NOT apply

- The bug is already reproduced locally and the cause is named — go fix it.
- The user is debugging a feature they're actively writing — that's standard development, not production debugging.
- The "issue" is a UX or design question, not an error or performance regression.
- A simple lint/type/test failure on a known PR — run the tool, fix the output.

If the user invokes the skill but the situation matches one of the above, say so and ask whether to continue with the heavyweight workflow anyway or drop to direct work.
