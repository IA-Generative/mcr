---
name: commit
description: Commit staged/unstaged changes following team conventions (gitmoji, ticket number, concise description)
argument-hint: "[optional: description of what was done]"
---

You are committing changes that have already been made. Follow the team's commit conventions strictly.

## Commit message format

```
:gitmoji: (TICKET_NUMBER): concise description
```

Or if no ticket number is found on the branch:

```
:gitmoji:: concise description
```

### Examples

- `:recycle: (243): VAD return list[TimeSpan] rather than list[DiarizationSegment]`
- `:recycle: (285): Modified prompt to remove repetitions`
- `:sparkles: (224): add proper audio player in frontend`
- `:bug: (301): fix off-by-one in chunk splitting`
- `:white_check_mark: (243): add unit tests for VAD utils`

## Process

### 1. Gather context

Run these in parallel:
- `git status` — see what changed
- `git diff` and `git diff --staged` — understand the actual changes
- `git branch --show-current` — extract the ticket number (the number in the branch name, e.g. `iteration/245/do_not_transcribe_very_short_audio_chunk` -> `245`)

### 2. Choose the right gitmoji

Pick the **single best** gitmoji based on the nature of the changes:

🎨 - :art: - Improve structure / format of the code.
⚡️ - :zap: - Improve performance.
🔥 - :fire: - Remove code or files.
🐛 - :bug: - Fix a bug.
🚑️ - :ambulance: - Critical hotfix.
✨ - :sparkles: - Introduce new features.
📝 - :memo: - Add or update documentation.
🚀 - :rocket: - Deploy stuff.
💄 - :lipstick: - Add or update the UI and style files.
🎉 - :tada: - Begin a project.
✅ - :white_check_mark: - Add, update, or pass tests.
🔒️ - :lock: - Fix security or privacy issues.
🔐 - :closed_lock_with_key: - Add or update secrets.
🔖 - :bookmark: - Release / Version tags.
🚨 - :rotating_light: - Fix compiler / linter warnings.
🚧 - :construction: - Work in progress.
💚 - :green_heart: - Fix CI Build.
⬇️ - :arrow_down: - Downgrade dependencies.
⬆️ - :arrow_up: - Upgrade dependencies.
📌 - :pushpin: - Pin dependencies to specific versions.
👷 - :construction_worker: - Add or update CI build system.
📈 - :chart_with_upwards_trend: - Add or update analytics or track code.
♻️ - :recycle: - Refactor code.
➕ - :heavy_plus_sign: - Add a dependency.
➖ - :heavy_minus_sign: - Remove a dependency.
🔧 - :wrench: - Add or update configuration files.
🔨 - :hammer: - Add or update development scripts.
🌐 - :globe_with_meridians: - Internationalization and localization.
✏️ - :pencil2: - Fix typos.
💩 - :poop: - Write bad code that needs to be improved.
⏪️ - :rewind: - Revert changes.
🔀 - :twisted_rightwards_arrows: - Merge branches.
📦️ - :package: - Add or update compiled files or packages.
👽️ - :alien: - Update code due to external API changes.
🚚 - :truck: - Move or rename resources (e.g.: files, paths, routes).
📄 - :page_facing_up: - Add or update license.
💥 - :boom: - Introduce breaking changes.
🍱 - :bento: - Add or update assets.
♿️ - :wheelchair: - Improve accessibility.
💡 - :bulb: - Add or update comments in source code.
🍻 - :beers: - Write code drunkenly.
💬 - :speech_balloon: - Add or update text and literals.
🗃️ - :card_file_box: - Perform database related changes.
🔊 - :loud_sound: - Add or update logs.
🔇 - :mute: - Remove logs.
👥 - :busts_in_silhouette: - Add or update contributor(s).
🚸 - :children_crossing: - Improve user experience / usability.
🏗️ - :building_construction: - Make architectural changes.
📱 - :iphone: - Work on responsive design.
🤡 - :clown_face: - Mock things.
🥚 - :egg: - Add or update an easter egg.
🙈 - :see_no_evil: - Add or update a .gitignore file.
📸 - :camera_flash: - Add or update snapshots.
⚗️ - :alembic: - Perform experiments.
🔍️ - :mag: - Improve SEO.
🏷️ - :label: - Add or update types.
🌱 - :seedling: - Add or update seed files.
🚩 - :triangular_flag_on_post: - Add, update, or remove feature flags.
🥅 - :goal_net: - Catch errors.
💫 - :dizzy: - Add or update animations and transitions.
🗑️ - :wastebasket: - Deprecate code that needs to be cleaned up.
🛂 - :passport_control: - Work on code related to authorization, roles and permissions.
🩹 - :adhesive_bandage: - Simple fix for a non-critical issue.
🧐 - :monocle_face: - Data exploration/inspection.
⚰️ - :coffin: - Remove dead code.
🧪 - :test_tube: - Add a failing test.
👔 - :necktie: - Add or update business logic.
🩺 - :stethoscope: - Add or update healthcheck.
🧱 - :bricks: - Infrastructure related changes.
🧑‍💻 - :technologist: - Improve developer experience.
💸 - :money_with_wings: - Add sponsorships or money related infrastructure.
🧵 - :thread: - Add or update code related to multithreading or concurrency.
🦺 - :safety_vest: - Add or update code related to validation.
✈️ - :airplane: - Improve offline support.

### 3. Extract ticket number

- Parse the current branch name for a number (e.g. `iteration/245/...` -> `245`, `fix/301/...` -> `301`)
- If the branch contains no number (e.g. `main`, `feat/add-logging`), ask the user if they want to include a ticket number in the commit message. If yes, ask them to provide it.

### 4. Write the commit description

- Short, lowercase, direct — describe **what** was done
- No period at the end
- If the user provided a description as argument, use it (refine if needed)
- If not, infer from the diff

### 5. Stage and commit

- Stage all relevant changed files (prefer explicit file paths over `git add -A`)
- Do NOT stage files that look like secrets (`.env`, credentials, etc.)
- Create the commit using a HEREDOC for proper formatting:

```bash
git commit -m "$(cat <<'EOF'
:gitmoji: (NUMBER) description
EOF
)"
```

### 6. Show the result

- Run `git log -1 --oneline` to confirm the commit
- Display the final commit message to the user

## Rules

- NEVER amend an existing commit unless the user explicitly asks
- NEVER push to remote — only commit locally
- If there are no changes to commit, tell the user and stop
- If you are unsure about the gitmoji or description, propose the commit message and ask the user to confirm before committing
