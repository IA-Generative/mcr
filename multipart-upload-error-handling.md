# Audio import (multipart upload) — error handling & observability

Analysis of three production incidents in the audio-import flow and the frontend error-capture architecture that addresses them. The import flow uploads a meeting's audio to S3 via a browser-driven multipart upload (`init → sign → PUT part → complete`, with `abort` on failure), proxied through `mcr-gateway` to `mcr-core` (presigned URLs; the part PUTs go **browser → Scaleway S3 directly**).

Objectives:
- One legible Sentry event per failed upload, carrying enough context to classify the failure — never a context-less unhandled rejection.
- Telemetry that fails toward noise, not silence: data-layer errors are captured by default.
- A single module owning the Sentry SDK; domain code depends on an abstraction.
- No secrets (presigned-URL signatures, auth tokens) reaching Sentry.

---

## 1. The incidents

| | A — `mcr-meeting 17518` | B — `mcr-meeting 17521` | C — `mcr-meeting 17449` (Sentry [`MCR-FRONTEND-6Z`](https://sentry-dev.mirai-hp.cpin.numerique-interieur.com/organizations/sentry/issues/MCR-FRONTEND-6Z)) |
|---|---|---|---|
| Evidence | mcr-core logs | mcr-core logs | Sentry issue + breadcrumbs |
| Sequence | `init` → **6× `sign`** (1 + 5 retries) → `abort 204` | `init` → **1× `sign`** → nothing → next-day `GET` polling | part 1 PUT 200 → part 2 PUT **`status 0`** → 5× re-`sign` 500 → 6× `abort` 500 |
| Network mode | PUTs failed in ~150 ms → **connection-level reject** (egress/DNS/CORS); the browser reached our API but not `scw.cloud` | tab closed mid-upload (single sign, no retry) | part 2 **stalled ~3 min then dropped** |
| End state | upload failed, **abort cleaned up** → no S3 object (correct) | **neither `complete` nor `abort`** → orphaned incomplete multipart upload in S3 + meeting stuck `IMPORT_PENDING` | user deleted the meeting mid-upload → orphaned retries 500'd |
| Reached Sentry | no (gateway is uninstrumented) | no (no `onError` fired) | yes — as a context-less `unhandledrejection` |

"No file in S3" in A is the **expected** result of an aborted multipart upload (abort discards uploaded parts), not a separate defect. In B the upload is genuinely orphaned: an incomplete multipart upload lingers in S3 (invisible as an object, but billable until aborted/expired) and the meeting row never leaves `IMPORT_PENDING`.

## 2. Root causes

1. **Failures surfaced as unhandled rejections.** Each multipart mutation `throw`ew inside its TanStack-Query `onError` callback. A throw inside `onError` is a floating rejected promise that escapes the caller's `try/catch` and is auto-captured by `@sentry/vue` as a context-less `onunhandledrejection` (issue 2028). The mechanism is independent of *why* the upload failed — every failure mode above collapses to the same useless event.
2. **Browser-owned lifecycle with no server guarantee.** `complete`/`abort` only run if the browser cooperates. Closing the tab, losing the network, or hitting an error leaves the upload orphaned in both S3 and the DB. There is no server-side reaper and no S3 lifecycle rule.
3. **Observability blind spots.** The failing leg (`PUT` browser → S3) is never instrumented, so A's root cause is invisible; `mcr-gateway` has no `sentry_sdk.init`, so its 5xx (C's re-sign/abort) are invisible server-side.

Client-side note: a blocked-egress PUT and a dropped connection are **indistinguishable** from JS — both surface as `status 0` / `ERR_NETWORK` with no reason (browsers hide it by design). The actionable signal is not the *reason* but the *classification*: HTTP status vs `0`, the axios `error.code`, the attempt duration (fast-reject vs stall), and the fact that `sign` (our origin) succeeded while the `PUT` (S3) failed.

---

## 3. Implemented solution (mcr-frontend)

Layered capture — exactly one layer captures each error; the others opt out, so there are no duplicate events.

| Layer | Mechanism | Role |
|---|---|---|
| Bedrock | `@sentry/vue` global handlers (init in `initSentry`) | truly *unhandled* errors / crashes |
| Floor | `MutationCache` / `QueryCache` `onError` | capture-by-default for data-layer errors; can't be forgotten |
| Enrichment | `reportError()` once at a domain boundary | rich, single event for flows that warrant it (multipart); those mutations opt the floor out via `meta.skipReport` |

Separation of concerns: **control-flow** (reject/propagate) · **user feedback** (toaster, in the component) · **telemetry** (`reportError`).

### 3.1 Single Sentry seam — `src/services/observability/sentry.ts`

The only module importing `@sentry/vue`. Exposes `initSentry(app)`, `reportError(error, opts)`, and the report contract types (`Feature`, `UploadContext`, `ReportOptions`). `reportError` uses the scoped-callback form so tags/contexts never leak to the global scope:

```ts
export function reportError(error: unknown, opts: ReportOptions): void {
  Sentry.captureException(error, (scope) => {
    scope.setTag('feature', opts.feature);
    if (opts.level) scope.setLevel(opts.level);
    if (opts.tags) for (const [k, v] of Object.entries(opts.tags)) scope.setTag(k, v);
    if (opts.contexts) for (const [k, v] of Object.entries(opts.contexts)) scope.setContext(k, v ?? null);
    return scope;
  });
}
```

`ReportOptions` is discriminated on `feature`: a `meeting.upload` report **must** carry a typed `UploadContext`, so a call site can't omit or misname a field.

`initSentry` also scrubs secrets before anything ships — presigned-URL query strings (which were appearing in xhr breadcrumbs) and auth headers:

```ts
function redactQueryString(url?: string) {
  if (!url) return url;
  const q = url.indexOf('?');
  return q === -1 ? url : `${url.slice(0, q)}?[redacted]`;
}
// beforeBreadcrumb: redact xhr/fetch breadcrumb url query
// beforeSend: redact event.request.url query; delete Authorization / X-User-Access-Token headers
```

Doc: <https://docs.sentry.io/platforms/javascript/guides/vue/configuration/filtering/>

`main.ts` is reduced to a single call after `createApp`: `initSentry(app);`.

### 3.2 The floor — `src/plugins/vue-query.ts`

The `QueryClient` is built with cache-level `onError` handlers. They report by default but **skip expected client errors** (4xx that the UI already handles) and respect `meta.skipReport`:

```ts
export function handleMutationError(error: unknown, meta: AppErrorMeta | undefined): void {
  if (meta?.skipReport || !isUnexpectedHttpError(error)) return;
  reportError(error, { feature: meta?.feature ?? 'mutation' });
}
// queryCache uses the same guard at level 'warning'
```

`isUnexpectedHttpError` (`src/services/http/http.utils.ts`) reports 5xx, network and non-HTTP errors; it skips 400/401/403/404/409/410/415/422. This keeps routine errors out of Sentry while guaranteeing unexpected ones are never silently dropped.

Doc: <https://tanstack.com/query/latest/docs/reference/MutationCache>

### 3.3 Typed `meta` — `src/services/observability/error-meta.ts`

Sentry-agnostic. Augments TanStack's `Register` so `meta` is typed at every `useMutation`/`useQuery` and in the cache handlers. `feature` excludes `meeting.upload` (uploads self-report at their boundary):

```ts
export interface AppErrorMeta {
  feature?: Exclude<Feature, 'meeting.upload'>;
  skipReport?: boolean;
}
declare module '@tanstack/vue-query' {
  interface Register {
    mutationMeta: AppErrorMeta & Record<string, unknown>;
    queryMeta: AppErrorMeta & Record<string, unknown>;
  }
}
```

### 3.4 The upload boundary — `src/composables/use-multipart.ts`

- The four sub-mutations (`init`, `sign+PUT`, `complete`, `abort`) carry `meta: { skipReport: true }` and no longer `throw` in `onError`.
- Each step is wrapped so a failure self-describes its phase (no mutable phase variable):

```ts
export class UploadStepError extends Error {
  constructor(readonly phase: UploadPhase, readonly cause: unknown, readonly partNumber?: number) {
    super(`Multipart upload failed during ${phase}`);
    this.name = 'UploadStepError';
  }
}
async function step<T>(phase, fn, partNumber?) {
  try { return await fn(); }
  catch (cause) { throw new UploadStepError(phase, cause, partNumber); }
}
```

- One `try/catch` at the orchestration boundary: best-effort **silent** abort, **one** `reportError` built from the error, then re-throw the original cause for control-flow:

```ts
} catch (error) {
  if (uploadId && objectKey) await abortMultipartUpload({ meetingId, uploadId, objectKey }).catch(() => {});
  const stepError = error instanceof UploadStepError ? error : new UploadStepError('init', error);
  reportError(stepError.cause, buildUploadReport(stepError, { meetingId, totalParts, fileSize, bytesSent, durationMs }));
  throw stepError.cause instanceof Error ? stepError.cause : stepError;
}
```

The captured `upload` context — `phase`, `partNumber`, `totalParts`, `fileSize`, `bytesSent`, `durationMs`, `httpStatus`, `axiosCode`, `online`, `effectiveType` — is what makes the next occurrence legible: it distinguishes incident A (`axiosCode: ERR_NETWORK`, tiny `durationMs`, `phase: sign-put`) from incident C (`status 0` after a multi-minute `durationMs`). `effectiveType` is Chromium-only (`null` on the Firefox users actually affected) — see <https://developer.mozilla.org/en-US/docs/Web/API/Network_Information_API>.

### 3.5 Component toasts — `TableHeaderActions.vue` / `MeetingTiles.vue`

`uploadFileWithMultipart` shows exactly one accurate toast: `error.meeting-creation` if creation fails, `error.file-upload` if the upload fails (previously it showed both, and mislabeled upload failures as creation failures).

---

## 4. Validation

Frontend dev server runs under docker `--watch`. Commands run from `mcr-frontend/`.

### V1. Unit tests

```bash
pnpm exec vitest run src/services/observability/sentry.spec.ts src/plugins/vue-query.spec.ts src/composables/use-multipart.spec.ts
```

**Expected.** All pass, including: `use-multipart` produces **no `unhandledrejection`** and exactly **one** `reportError` on a part failure (the 2028 regression); the floor reports 5xx but **not** 4xx; `initSentry` redacts presigned URLs and strips auth headers.

### V2. Full suite + type-check

```bash
pnpm exec vitest run && pnpm type-check
```

**Expected.** Suite green; type-check reports no errors.

### V3. Manual — failing upload

In the browser, open the import modal, select a > 50 MB audio file, then block `s3.fr-par.scw.cloud` in DevTools → Network (or go offline) and submit.

**Expected.** Exactly one error toast; **no** unhandled rejection in the console; **one** Sentry event tagged `feature=meeting.upload` carrying the `upload` context (`httpStatus`/`axiosCode`/`phase`/`partNumber`/`bytesSent`/`online`). Unblock and re-upload → succeeds, emits no event.

---

## 5. Not addressed here (follow-ups)

These are out of scope of the frontend capture work and tracked separately:

- **Server-side lifecycle (incident B).** Celery reaper for meetings stuck in `IMPORT_PENDING` + an S3 `AbortIncompleteMultipartUpload` lifecycle rule (<https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html>) + UI stuck-state instead of infinite polling.
- **Gateway observability (confirms incident C).** Add `sentry_sdk.init` to `mcr-gateway` and stop returning `str(e)` in 500 detail; the re-sign/abort 500s are currently invisible server-side.
- **Upload resilience.** Stall-based abort + `AbortController` cancellation on meeting delete / modal close / unmount; stop overriding the global retry guard with a flat `retry: MAX_RETRIES`.
- **Sentry decoupling hardening.** Migrate the scattered captures in `use-recording-*` / `use-chunk-upload` onto `reportError`, then ESLint-ban `@sentry/vue` imports outside `sentry.ts` and drop it from the vite auto-import list.
- **Cost.** Raw WAV at 200 imports/day is ~140–200 GB/day (~4–6 TB/month) — consider rejecting/transcoding WAV and a retention policy.

## 6. Verified vs hypothesis

- **Verified:** the unhandled-rejection mechanism and its fix; incident A's "API reachable, S3 not"; B's orphaned upload + stuck meeting; the absence of a reaper / lifecycle rule.
- **Hypothesis (unconfirmed):** incident C's re-sign/abort returning **500** rather than 404 — most consistent with `mcr-gateway`'s generic-`except` path, but unverifiable until the gateway is instrumented (follow-up above).
