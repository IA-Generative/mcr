---
paths:
  - "**/tests/**/*.py"
  - "**/*.spec.ts"
  - "**/*.test.ts"
  - "**/*.spec.vue"
---

# Testing

Before writing or changing a test, decide the **business invariant** it defends — a rule a Product
Manager would recognize the product must uphold — then write the test to fail exactly when that rule
is violated. Decide the invariant *first*; deriving it from code you already wrote yields mechanism tests.

- **Never add a production seam just to make a test mockable.** A `_now()` wrapper introduced only to
  dodge a library's internal clock reads is a trick that distorts prod code and usually means the test is
  at the wrong level — move the assertion to the unit that owns the behavior instead of reshaping prod.
- **Test the invariant, not the mechanism.** Never assert the mechanism a diff just touched. Tells of a
  worthless mechanism test: it asserts a config value, `assert_called_once` alone, a wiring fact
  ("the handler is registered", "a log doesn't create a Sentry event"), or you must drive a third-party
  library's internals to assert anything. For an observability/config change, test the *product*
  consequence (resilience, an API contract); if the only effect is a monitoring-config value, it is
  verified by review + post-deploy, not a unit test.
- **Classify the layer** (domain / use-case / infra / api) — it dictates what the test must prove.
- **Failure-path tests must actually fail for the named reason.** Confirm the failure triggers in-window
  (mutant check: break the fix, watch the test go red). A path injected before the guarded code runs, or
  an assertion true by absence, is worthless.
- **Assert every side effect in both directions** (created on success; absent after rollback/guard-reject),
  including secondary bookkeeping writes.

TDD is mandatory: the failing test is written and seen red before the implementation.

For planning, writing, or reviewing tests in depth — the full rubric (fatal flags, D1–D8 scoring, review
output) lives in the `testing-standard` skill (`/testing-standard`).
</content>
