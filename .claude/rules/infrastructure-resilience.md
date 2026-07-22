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

Make transient network blips survivable.

- **Rename at the source.** Catch the raw transport error in the wrapper and rename it there — a transient blip to a `TransientInfraError` subclass, a legitimate absence to `None`, anything else to its business error. Never re-label an error as it bubbles; layers above let it propagate untouched.
- **Choose the retry scope per operation:**
  - _Fully idempotent_ (replaying is safe): retry on the whole transient set.
  - _Connection-only_ (replaying could double the effect): retry only on connection-phase failures, which prove the request never reached the server — never on an ambiguous post-send failure.
- **The rename bridges two retry levels:**
  - In a Celery task the net is double — the in-process call-site retry absorbs a short blip, then `autoretry_for=(TransientInfraError,)` re-queues through a prolonged outage.
  - Off-task (synchronous request path) only the call-site retry applies; a persistent failure surfaces to the caller.

An idempotent op that runs in a task but isn't renamed to `TransientInfraError` silently loses its second net.
</content>
