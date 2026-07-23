---
paths:
  - "**/mcr_meeting/app/infrastructure/*.py"
---

# Infrastructure

## Dependency ownership

Each external **service SDK** has ONE owner file — the file that wraps it (`sentry_sdk` → `sentry.py`, `keycloak` → `keycloak.py`, `boto3` → `s3.py`, `redis` → `redis.py`). Don't import or instantiate that SDK anywhere else.

- Placement is decided by the **dependency imported**, not the domain noun. When adding a helper, ask *"which external package does this code instantiate?"* and put it in that package's owner file — even if the helper's subject matches another file's name. A Sentry-integration builder belongs in `sentry.py`, not `logger.py`: it constructs `sentry_sdk` objects.
- **Ambient utilities are exempt** (used everywhere, owned by no one): `loguru`, `pydantic`, `numpy`, `httpx`, stdlib. Their spread across files is fine.
- A file needing two owned SDKs is a smell — the second SDK's logic belongs in its owner file.
- Symptom this prevents: an owner file (`sentry.py`) importing a helper back from a non-owner (`logger.py`) that re-wraps the same SDK.

## Resilience

Make a flaky external dependency survivable.

- Rename at the source. In the wrapper, catch the failure and rename it there: a fleeting fault to a TransientInfraError subclass, a legitimate absence to None, anything else to its business error. This covers not just a raw transport error but a success response that carries a failed outcome (e.g. an async job polled as status failed): classify its reason at the source too. Never re-label an error as it bubbles; layers above let it propagate untouched.

- Pick a category per operation; it decides the retry level:
  - Transient, fleeting and idempotent (connect blip, 5xx before any state was created, an idempotent GET): retry both in-process and at the task level.
  - Retryable operation, where a whole-operation replay is safe but a fast in-process replay would hurt: retry at the task level only, with backoff. Use this whenever a tight local loop would amplify an outage (a backlog or overload signal) or duplicate work (an ambiguous post-send whose duplicate is non-destructive). Document that reason at the raise site.
  - Definitive, where no replay helps (4xx, missing input, unknown reason): the business error, fail loud. Default unknowns here.

- The retry level is set by which retry on= set the exception is in, not merely by being a TransientInfraError: transient and retryable-operation both subclass TransientInfraError so task-level autoretry catches both, but only transient goes in the in-process on= tuple.

An idempotent op that runs in a task but isn't renamed to TransientInfraError silently loses its second net.
</content>
