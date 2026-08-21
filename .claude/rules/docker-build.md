---
paths:
  - "**/Dockerfile*"
  - "**/docker/**"
  - "**/.dockerignore"
  - "docker-compose*.{yml,yaml}"
  - ".gitlab-ci-dso.yml"
---

# Docker builds

Images are built by **kaniko** in the DSO pipeline (`.gitlab-ci-dso.yml`). Local
`docker compose build` uses BuildKit, so every Dockerfile must work under both — kaniko is the
constraint.

A service package keeps its docker assets in `<package>/docker/` (`mcr-core/docker/Dockerfile`,
`docker-entrypoint.sh`, `docker-entrypoint.dev.sh`), while the build context stays the package root
(`mcr-core/`) — so `.dockerignore` belongs at `mcr-core/.dockerignore`, never inside `docker/`.

- **No `RUN --mount=type=cache|bind|secret`.** Kaniko doesn't implement BuildKit's mount flags, and
  an unknown `RUN` flag is a parse error, not a no-op. Works locally ≠ ships.
- **Build against the lockfile**: `uv sync --locked` with `uv.lock` in the build context. A bare
  `uv sync` resolves fresh at build time, so images drift from each other and from local.
- **Copy `pyproject.toml` + `uv.lock` and install deps *before* copying source.** Layer order is the
  caching mechanism; source ahead of deps invalidates the dependency layer on every commit. The
  pipeline passes `--cache=true --cache-repo=$IMAGE_REPOSITORY/cache`, so that order is what makes a
  source-only commit skip the dependency install instead of paying for it again.
- **Pin every `FROM` by digest**, keeping the tag for readability
  (`FROM python:3.12.10-slim@sha256:…`). A tag is mutable: when upstream moves it, every cache key
  derived from it changes and an image rebuilt for a release stops matching the one staging tested.
  There is no Renovate/Dependabot here, so bumps are deliberate — refresh with
  `docker buildx imagetools inspect <image>:<tag> --format '{{.Manifest.Digest}}'` and commit the
  new digest.
- **Keep build tooling out of the runtime image** with named-stage `COPY --from=builder`.
- **One runtime image per service package, role dispatched at run time.**
  `docker/docker-entrypoint.sh` maps a role (`api` | `worker` | `migrate`, plus arbitrary-command
  passthrough) to its process; `CMD ["api"]` is the default; compose/k8s pick the role via
  `command:` / `args:`. Never reintroduce per-role final stages — two digests off one dependency set
  let api and worker drift to different commits.
- **The entrypoint must `exec`** so the process stays PID 1 and signal remapping
  (`REMAP_SIGTERM=SIGQUIT`, cold shutdown) keeps working.
- **Dev mirrors the role names, not the process semantics.** The `dev` stage has its own
  `docker/docker-entrypoint.dev.sh` exposing the same roles, so `command: ["worker"]` means the same thing
  locally and in prod; keep the two role lists in sync by hand. Dev's `worker` runs under
  `watchmedo` (PID 1 is watchmedo), so never validate the shutdown path in dev.
- **Settle build claims with a build, not from memory** — kaniko behaviour, whether a toolchain is
  still needed, image size. Measure on `linux/amd64`; arm64 results don't transfer.
