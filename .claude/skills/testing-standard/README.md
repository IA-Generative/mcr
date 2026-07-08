# testing-standard

Why we hold tests to a standard, and the quality-control points it applies. The operational
procedure lives in SKILL.md; this explains the reasoning behind it.

## What makes a test good

Tests fail us in two predictable ways: they stay green while the product is broken (false
confidence), or they break when nothing that matters changed (false alarms). Line coverage measures
neither — it only confirms a line executed. So this standard measures a different thing: would this
test fail exactly when a business rule is violated, and only then?

That reframing is the whole point. A test earns its place by protecting a business invariant — a rule
the product must uphold — stated legibly enough that a Product Manager could read the test's name and
agree it is such a rule. We aim there deliberately, because tests written that way tend to:

- catch the bugs that matter, because they are pinned to real product behavior rather than to whichever
  lines happen to run;
- survive refactors, because they assert observable behavior, not the implementation's internal shape;
- document the system, because the suite reads as the set of rules the product guarantees.

Tests written to raise a coverage number, or to mirror the code's structure, achieve none of these —
and worse, they look reassuring while doing so. The standard exists to tell those two kinds apart.

## The quality-control points

The standard is a small set of controls, each aimed at a specific way a test gives false confidence.

- Fatal flaws are caught before anything else. Some tests are worthless no matter how many assertions
  they carry: they exercise a copy of the code instead of the real thing, they cannot fail for the
  reason they claim, or they mock away the very behavior they exist to verify. A polished score on a
  structurally blind test is worse than no test — it certifies confidence that isn't there — so these
  are gated first and never scored.

- The bar adapts to what the code is for. A pure business rule must be pinned across its input space; an
  external-dependency wrapper must prove it translates correctly; a flow must prove its side effects and
  its rollbacks. One universal bar would over-test trivia and under-test the risky seams, so each layer
  is held to the standard that matches its job.

- Failure paths count as much as happy paths, with direction. A flow must roll back cleanly when it
  fails before committing, and must survive a best-effort failure after. Asserting the happy path while
  leaving the failure path unproven is the most common way our real bugs escape review, so it is a
  first-class control, not an afterthought — as is proving that a guard rejects before any side effect
  happens.

- Green is kept honest about its limits. Our tests run on SQLite and hand-built fakes, not the
  production database and services. A pass can rest on behavior the test environment cannot actually
  reproduce; rather than pretend otherwise, the standard flags those assertions so a green result is
  never mistaken for a production guarantee.

- A test is only as trustworthy as the reality it checks against. When a test fabricates a dependency's
  shape by hand and nothing anchors that shape to the real dependency, the pass is relative to a fiction
  — the test can stay green while production breaks. The standard requires fabricated contracts to be
  anchored, and rejects doubles that carry production logic, because those drift silently.

## Using it

Point the skill at one test file to review it, or consult the layer bar and the fatal flaws before
writing a new test. The full procedure — classification, the fatal flaws, the scored dimensions, and
the confidence caveats — is in SKILL.md.
