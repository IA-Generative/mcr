---
paths:
  - "**/mcr_meeting/app/infrastructure/*.py"
---

# Infra resilience

Each infra file wraps one external dependency; make transient network blips survivable.

- **Rename at the source.** Catch the raw transport error in the wrapper and rename it there — a transient blip to a `TransientInfraError` subclass, a legitimate absence to `None`, anything else to its business error. Never re-label an error as it bubbles; layers above let it propagate untouched.
- **Choose the retry scope per operation:**
  - _Fully idempotent_ (replaying is safe): retry on the whole transient set.
  - _Connection-only_ (replaying could double the effect): retry only on connection-phase failures, which prove the request never reached the server — never on an ambiguous post-send failure.
- **The rename bridges two retry levels:**
  - In a Celery task the net is double — the in-process call-site retry absorbs a short blip, then `autoretry_for=(TransientInfraError,)` re-queues through a prolonged outage.
  - Off-task (synchronous request path) only the call-site retry applies; a persistent failure surfaces to the caller.

An idempotent op that runs in a task but isn't renamed to `TransientInfraError` silently loses its second net.
