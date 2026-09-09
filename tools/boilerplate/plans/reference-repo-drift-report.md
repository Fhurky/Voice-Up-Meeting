# Reference Repository Drift Report — `kt-console`

**Target repository for the fixes:** `kt-console` (the origin repo). This document lives in the
boilerplate repository only because the reference was read-only for the session that produced it.
Hand this file to an agent working inside `kt-console`.

**Observation window:** 2026-08-04, between 13:05 and 14:05 local time.
**Observed against:** `HEAD` = `f28f087` ("Update PRDs with current executable evidence and
implementation status"), working tree clean except `e2e/ai-mode/08-global-drawer-bridge.mjs`.

**Read this warning first.** The repository was being actively committed to during the
observation window: `e2e/package.json` and `e2e/QUALITY_MANIFEST.md` both changed under the
session's feet, and one finding that was true at 13:20 was already fixed by 13:50. **Re-verify
every finding with the command given in its "Verify" line before changing anything.** A finding
whose verification command now comes back clean has been fixed by someone else — mark it and move
on.

**Language:** English, per the origin repo's own rule that repo artifacts stay English.

---

## 1. How these were found and what "verified" means

The findings come from reading the governance surfaces (`CLAUDE.md`, `AGENTS.md`,
`.cursor/rules/*.mdc`, the three `.claude/skills/` trees) against the code, schema, scripts,
package manifests and CI workflows they describe. Nothing was inferred from a document alone: each
finding names the document that makes a claim **and** the artifact that contradicts it. No file in
`kt-console` was modified, and no build, test or migration was run there.

Two claims in this report are explicitly **not** verified, and are marked as such: whether the
repo-root virtualenv can actually run the backend suite, and whether the `kt-backend-dev` image
exists on any given machine. Both would require running things in the reference repo.

---

## 2. Root cause

Every High and Medium finding below is an instance of one mechanism: **the same rule is authored
by hand in up to four places** — the Claude directive file, the tool-agnostic agent file, the
Cursor rule file for that concern, and the skill for that concern — and the copies are kept in
sync by intention rather than by machine.

The repo already knows this is fragile. `CLAUDE.md` line 248 says the Cursor files "mirror a
subset; when they drift, **the skill is authoritative**", and `no-physical-fks/SKILL.md` closes by
naming `.cursor/rules/03-database.mdc` as "duplicate of this rule for Cursor". That convention
resolves *which copy wins* but does nothing to stop copies from diverging, and it does not help at
all when the skill itself is the stale one — which is the case in findings 1, 2, 5, 7, 10, 11
and 12.

Section 6 proposes the structural remedy. Sections 3 through 5 are the immediate work.

---

## 3. Findings

Ranked by whether an agent following the rule produces broken output.

| # | Severity | Finding | Files to change |
|---|---|---|---|
| 1 | High | Four governance files command a script that does not exist | 4 + one editor task |
| 2 | High | The API-standards code example does not import or run | 3 |
| 3 | High | Three mutually exclusive backend test commands are all documented as the rule | 5 |
| 4 | High | The mandatory soft-delete column set has two conflicting definitions, and the schema matches neither universally | 3 + a schema decision |
| 5 | Medium | Frontend type generation is documented from a running server, but the script reads a committed file | 2 |
| 6 | Medium | The migration tool and the settings object use different variable names for the same database connection | 3 + a naming decision |
| 7 | Medium | The localization skill documents a message-file layout the application does not use | 1 |
| 8 | Medium | Six specification documents are written in Turkish against an English-only rule | 6 + a policy decision |
| 9 | Medium | Three frontend skills have no Cursor mirror, including one the agent contract calls mandatory | 3 |
| 10 | Low | Two root skills reference schema directories that were consolidated away | 2 |
| 11 | Low | The testing skill's layout block and example command name a test directory that does not exist | 1 |
| 12 | Low | The backend-overview skill describes a service domain that was never built | 1 |
| 13 | Low | Stray empty directories in the frontend working tree (local only, not in origin) | 0 tracked |

---

### Finding 1 — Four governance files command a script that does not exist

**Severity:** High. An agent asked to regenerate the API contract runs a command that fails
immediately, then improvises.

**Claim.** `python scripts/generate_openapi_schema.py`, "from project root", generating
`specs/openapi/console-api.yaml`.

| File | Line |
|---|---|
| `console/backend/.claude/skills/api-standards/SKILL.md` | 19 |
| `console/backend/.cursor/rules/api-standards.mdc` | 16 |
| `console/frontend/.claude/skills/api-integration/SKILL.md` | 20 |
| `console/frontend/.cursor/rules/api-integration.mdc` | 13 |
| `.vscode/tasks.json` | 36 |

**Contradiction.** `scripts/` contains no such file. `scripts/README.md` states the rule that
explains why: "Backend-owned tooling stays in `console/backend/app/scripts/` instead
(`create_root_user`, `export_openapi`) — it needs the app settings/session." The real entry point
is `console/backend/app/scripts/export_openapi.py`.

**Fix.** Replace the command in all five locations with the actual invocation of
`export_openapi.py`. Determine the correct working directory and module form by reading that
script's own entry block — do not guess between `python -m app.scripts.export_openapi` and a path
invocation, and do not assume it takes no arguments.

**Verify:** `grep -rn "generate_openapi_schema" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv` returns nothing.

---

### Finding 2 — The API-standards code example does not import or run

**Severity:** High. This is the pattern an agent copies when adding an endpoint, and it is wrong
in two independent ways at once.

**Claim.** `console/backend/.claude/skills/api-standards/SKILL.md` lines 27–33, 104 and 124:

```
from app.core.config import settings
@router.get(f"{settings.CONSOLE_API_ROUTE_PREFIX}/notes")
```

**Contradiction, part one — the import.** `app/core/config.py` exposes no module-level `settings`
object. It defines `Settings` and an `@lru_cache`-wrapped `get_settings()` at line 393. The
documented import raises `ImportError`. This directly contradicts the rule that both `CLAUDE.md`
and the `configuration` skill state as the golden rule — always `get_settings()`.

**Contradiction, part two — the key name.** The settings field is `KT_CONSOLE_API_ROUTE_PREFIX`
(`config.py` line 52; `app/api/router.py` reads `get_settings().KT_CONSOLE_API_ROUTE_PREFIX`).
`CONSOLE_API_ROUTE_PREFIX` without the prefix does not exist, which also contradicts the rule that
every config key carries the `KT_` prefix.

**Contradiction, part three — the pattern itself.** The example decorates each route with the full
prefix inline. The application does not do this: `app/api/router.py` mounts one `APIRouter` with
the prefix and includes the domain routers under it. An agent copying the example produces
double-prefixed paths.

**Also affected by the key-name error:**

| File | Line | Text |
|---|---|---|
| `console/backend/.cursor/rules/api-standards.mdc` | 23 | `via settings.CONSOLE_API_ROUTE_PREFIX` |
| `console/backend/.claude/skills/backend-overview/SKILL.md` | 55 | `via CONSOLE_API_ROUTE_PREFIX env variable` |
| `.claude/skills/review/SKILL.md` | 41 | review checklist item asserting the wrong key |
| `.claude/skills/end-to-end-feature/SKILL.md` | 47 | `mounted on CONSOLE_API_ROUTE_PREFIX` |

Note the compounding effect: the `review` skill's checklist would make a reviewer *reject* correct
code for not using a key that does not exist.

**Fix.** In the api-standards skill, rewrite the example to `get_settings()`, the
`KT_CONSOLE_API_ROUTE_PREFIX` key, and the aggregate-router mounting pattern actually used in
`app/api/router.py`. Correct the key name in the other four locations.

**Verify:** `grep -rn "settings\.CONSOLE_API_ROUTE_PREFIX\|from app.core.config import settings\|[^_]CONSOLE_API_ROUTE_PREFIX" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git | grep -v KT_CONSOLE` returns nothing.

---

### Finding 3 — Three mutually exclusive backend test commands

**Severity:** High. Every agent hand-off runs one of these, and which one it picks depends on
which file it happened to read.

| Source | Command |
|---|---|
| `CLAUDE.md` line 220 | `docker run --rm -v $PWD/console/backend:/app -w /app kt-backend-dev sh -lc "pip install -q -r requirements.txt; python -m pytest"` — explicitly annotated **"no repo venv"** |
| `AGENTS.md` line 47 | Same Docker image path |
| `e2e/QUALITY_MANIFEST.md` line 73 | Same Docker image path, for the coverage snapshot |
| `.claude/skills/end-to-end-feature/SKILL.md` line 68 | `./.venv/bin/python -m pytest console/backend/...` — "Run from repo root with the repo-root virtualenv" |
| `console/backend/.claude/skills/testing/SKILL.md` lines 160–165 | `./.venv/bin/python -m pytest console/backend` — "**must** use the repo-root virtualenv" |
| `.github/workflows/backend-test.yml` lines 57–60 | Host Python 3.12, `pip install -r requirements.txt -r requirements-dev.txt`, then `pytest tests -v` with `working-directory: console/backend` |

The directive file says "no repo venv"; two skills say the repo venv is mandatory. `.venv/bin/pytest`
does exist in the repo root, so the venv path is not obviously dead — which is exactly why this
cannot be resolved by picking the newest-looking sentence.

**Not verified:** whether the repo-root virtualenv currently has the full dependency set to run
the suite, and whether `kt-backend-dev` is built on a given developer's machine. Both require
running things in the reference repo, which this session did not do. **Resolve this by running all
three paths once**, not by reading.

**Fix.** Decide one canonical command (see Open Question 1), state it in exactly one place, and
make every other location point at that place rather than restating it. Whatever is chosen, CI
should either run the same path or the difference should be stated explicitly as "CI installs on
the host runner; locally use X".

**Verify:** `grep -rn "kt-backend-dev\|\.venv/bin/python" CLAUDE.md AGENTS.md e2e/QUALITY_MANIFEST.md .claude/skills console/backend/.claude/skills` yields one canonical command and pointers, not three recipes.

---

### Finding 4 — Two definitions of the mandatory soft-delete column set, and the schema matches neither universally

**Severity:** High. This governs every new table.

| Source | Definition |
|---|---|
| `.claude/skills/end-to-end-feature/SKILL.md` line 28 | `deleted_at`, `deleted_by`, `delete_reason` |
| `.cursor/rules/03-database.mdc` | `deleted_at`, `deleted_by`, `delete_reason` |
| `schema/README.md` line 41 | `is_deleted`, `deleted_at`, `deleted_by` |
| `CLAUDE.md` line 100 | Names the triplet but never defines it |

**What the schema actually does.** Across `schema/verim/desired/*.sql`: 38 `CREATE TABLE`
statements, 33 carrying `is_deleted` + `deleted_at`, and `delete_reason` present on exactly 6
tables — all of them inside `91_discovery.sql`. The flagship example the docs point at,
`20_tenant.sql`, carries `is_deleted`, `deleted_at`, `deleted_by` and no `delete_reason`.

So the end-to-end and Cursor definition describes roughly one table in six, omits the
`is_deleted` flag that 33 tables actually carry, and mandates a column most tables do not have.

**A second, quieter gap.** `CLAUDE.md` line 100 says "**Every** table: soft-delete triplet + audit
quad + `props JSONB` + indexes", and the only stated exemption is the warehouse one. But
`85_audit_log.sql` and `86_query_execution.sql` deliberately carry no soft-delete columns, because
they are append-only streams — which is correct design, and the `schema-migration` skill even
lists "audit / event stream" as a `public_id` exemption. The universal-rule wording and the
schema's own correct exceptions do not agree.

**Fix.** Decide the canonical set (see Open Question 2), state it once, and add the append-only
exemption to the rule text so the schema stops being in silent violation of its own documentation.
If `delete_reason` is meant to be universal, that is a schema migration and a much larger change —
do not let a documentation fix quietly imply it.

**Verify:** every location that defines the triplet gives the same column list, and a spot check of
`20_tenant.sql` and one `91_discovery.sql` table agrees with it or is covered by a stated exemption.

---

### Finding 5 — Frontend type generation documented from a running server; the script reads a committed file

**Severity:** Medium. The documented command works but produces types from a different source than
the committed script, so two developers regenerating "the same" types can get different output.

| Source | Line | Source of truth used |
|---|---|---|
| `console/frontend/.claude/skills/api-integration/SKILL.md` | 30 | `http://localhost:8000/openapi.json` — requires the backend running |
| `console/frontend/.cursor/rules/api-integration.mdc` | 14 | Same running-server URL |
| `console/frontend/package.json` | 11 | `../../specs/openapi/console-api.yaml` — the committed artifact |

The same skill contradicts itself within eleven lines: line 23 explains that the export script
"loads the FastAPI app offline (no running server needed)" and writes the committed YAML, then
line 30 tells the reader to generate types from a live server instead.

**Fix.** Point both documents at `npm run generate-types`, and state the two-step contract once:
export the committed document, then generate types from it. That also makes the "is `api.d.ts` in
sync" check in the end-to-end skill meaningful, because both sides then reference the same file.

**Verify:** `grep -rn "openapi.json" console/frontend/.claude console/frontend/.cursor` returns nothing.

---

### Finding 6 — The migration tool and the settings object name the same connection differently

**Severity:** Medium. It works today because the values are duplicated in a gitignored file, and
it breaks silently for anyone setting up from `.env.example`.

**What Atlas reads** — `schema/verim/atlas.hcl` lines 17–20: `KT_VERIM_POSTGRES_SERVER`,
`KT_VERIM_POSTGRES_PORT`, `KT_VERIM_POSTGRES_USER`, `KT_VERIM_POSTGRES_PASSWORD` (plus `_DB`).

**What the application defines** — `app/core/config.py` lines 68–72: `KT_POSTGRES_HOST`,
`KT_POSTGRES_PORT`, `KT_POSTGRES_USER`, `KT_POSTGRES_PASSWORD`, `KT_VERIM_POSTGRES_DB`.

**What `.env.example` documents** — lines 20–24: only the five application-side names. None of the
four `KT_VERIM_POSTGRES_{SERVER,PORT,USER,PASSWORD}` names Atlas needs appear there.

**What the skill instructs** — `.claude/skills/schema-migration/SKILL.md` lines 47–62:
`export $(grep -E '^KT_VERIM_POSTGRES_' console/backend/.env | xargs)` and a required-variables
table listing all five. That export line matches exactly one variable in `.env.example`, so a
developer who created their `.env` from the example gets an Atlas command with an empty user and
password and a confusing connection error.

This is a direct violation of the sync rule the `configuration` skill states for itself: a new
setting must land in the settings class, `.env.example`, every compose env block and the Helm
values in one change.

**Fix.** Either (a) make `atlas.hcl` read the application-side names so there is one set, or
(b) keep the split deliberately and add the four Atlas-only names to `.env.example` with a comment
explaining that Atlas runs outside the settings object. See Open Question 3.

**Verify:** the variables named in `atlas.hcl` all appear in `console/backend/.env.example`, or
`atlas.hcl` reads names that already appear there.

---

### Finding 7 — The localization skill documents a layout the application does not use

**Severity:** Medium. An agent adding a string follows the documented structure and creates files
in the wrong place.

`console/frontend/.claude/skills/localization/SKILL.md` documents:

- `src/locales/messages/en.json` and `messages/tr.json` (line 25 block, and the lazy-load import at
  line 74 uses `./locales/messages/${locale}.json`)
- a consolidating `src/locales/index.ts`
- optional per-feature modules such as `src/locales/auth.messages.ts` (lines 37 and 43)

**Actual:** `console/frontend/src/locales/` contains exactly `en.json` and `tr.json`. No `messages/`
subdirectory, no `index.ts`, no `*.messages.ts` files.

**Fix.** Rewrite the structure and lazy-load sections to the flat layout in use. Drop the
per-feature module section, or mark it explicitly as a pattern not currently adopted — the current
text reads as a description of the repository, which it is not.

**Verify:** `grep -n "locales/messages\|locales/index\|messages\.ts" console/frontend/.claude/skills/localization/SKILL.md` returns nothing, or only clearly-labelled hypotheticals.

---

### Finding 8 — Six specification documents are written in Turkish against an English-only rule

**Severity:** Medium as a policy question, low as a defect.

`CLAUDE.md` line 143: "Conversation language is **Turkish**; all repo artifacts (code, comments,
docs, specs) stay English." The `prd` skill's format rules repeat it: "**LF** line endings.
**English** only."

Documents in Turkish:

| File |
|---|
| `specs/sql-studio/PRD.md` |
| `specs/authorization-hardening/PRD.md` |
| `specs/sql-editor-intellisense/PRD.md` |
| `specs/observability/PRD.md` |
| `specs/catalog-scope-descriptions/PRD.md` |
| `specs/benchmark/global-benchmark.md` |

**Fix.** This is a decision, not a cleanup (Open Question 4). Either translate them, or amend the
rule to state the actual policy — for example that specs may be authored in Turkish while code,
comments and public docs stay English. Leaving a rule that six documents openly violate teaches
agents that the rule set is advisory, which is the more expensive outcome.

**Verify:** either the six files are English, or `CLAUDE.md` and the `prd` skill state the exception.

---

### Finding 9 — Three frontend skills have no Cursor mirror, including one the agent contract calls mandatory

**Severity:** Medium. Partly intentional, but the specific gap matters.

`console/frontend/.claude/skills/` holds eight skills: `api-integration`, `frontend-overview`,
`live-verification`, `loading-states`, `localization`, `notifications`, `state-management`,
`styling`.

`console/frontend/.cursor/rules/` holds five: `api-integration`, `frontend-overview`,
`localization`, `state-management`, `styling`.

Missing from Cursor: **`live-verification`**, `loading-states`, `notifications`.

`CLAUDE.md` line 248 does say the Cursor files "mirror a subset", so the shortfall is
acknowledged in principle. But `AGENTS.md` item 10 lists the live browser pass among the
non-negotiable pre-hand-off gates, and `CLAUDE.md` line 167 calls post-change verification
mandatory including that pass. An agent working through Cursor's rule files alone never receives
the one rule the contract calls mandatory — including the detail that matters most, that the
verification target is the reverse proxy on `:8080` and never the dev server on `:3000`.

**Fix.** At minimum add a `live-verification.mdc` mirror. Better: replace "mirrors a subset" with
an explicit statement of which skills are intentionally Claude-only and why, so the gap is a
decision rather than an omission.

**Verify:** `ls console/frontend/.cursor/rules/` covers every skill that any mandatory gate depends on.

---

### Finding 10 — Two root skills reference consolidated-away schema directories

**Severity:** Low, with one wrinkle.

| File | Line | Stale reference |
|---|---|---|
| `.claude/skills/schema-comments/SKILL.md` | 3 (the `description` field) | `schema/{console,operational}/desired/*.sql` |
| `.claude/skills/prd/SKILL.md` | 28 | `schema/{console,operational}/desired/` |

Those two schema directories were consolidated into `schema/verim/` — `atlas.hcl`'s own header
comment records the merge. The wrinkle: in the schema-comments case the stale path sits in the
`description` field, which is the text used to decide whether the skill is relevant to a task. A
stale path there costs more than a stale path in the body.

**Fix.** Replace both with `schema/verim/desired/`.

**Verify:** `grep -rn "schema/{console,operational}\|schema/console/\|schema/operational/" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv` returns nothing.

---

### Finding 11 — The testing skill names a test directory that does not exist

**Severity:** Low.

`console/backend/.claude/skills/testing/SKILL.md` shows a layout block containing `tests/auth/` and
gives the example command `./.venv/bin/python -m pytest console/backend/tests/auth/test_login.py`.

**Actual** `console/backend/tests/`: `api`, `core`, `eval`, `fixtures`, `infrastructure`,
`integration`, `middleware`, `services`, `workers`. There is no `auth/`.

**Fix.** Update the layout block and pick an example path that resolves.

**Verify:** every path in the skill exists.

---

### Finding 12 — The backend-overview skill describes a service domain that was never built

**Severity:** Low.

`console/backend/.claude/skills/backend-overview/SKILL.md` line 26: "The skeleton starts with
**User & Auth** (accounts, JWT, RBAC) and **Notification**".

**Actual** `console/backend/app/services/`: `audit_service.py`, `auth_service.py`, `llm/`,
`query/`, `role_permission_service.py`, `tenant_service.py`, `user_service.py`. No notification
domain exists anywhere in the tree.

**Fix.** Describe the domains that exist, or state the sentence as a generic pattern rather than a
description of this repository.

---

### Finding 13 — Stray empty directories in the frontend working tree

**Severity:** Low, and **local only**.

`console/frontend/console/backend/` exists as a pair of empty directories, created 2026-08-03
13:08. The shape is the signature of a command run with a repo-root-relative path from inside
`console/frontend/`.

Because git does not track empty directories, this is **not in the origin repository** — it is an
artifact in one working tree. Deleting it is safe and changes nothing for anyone else.

**Fix.** `rmdir console/frontend/console/backend console/frontend/console` on the affected machine.
Optionally add a guard note to the skills that give repo-root-relative commands, since that is the
likely source.

---

## 4. Verified clean — do not chase these

Checked during the same pass and found consistent. Listed so the fixing agent does not spend a
round re-deriving them.

| Checked | Result |
|---|---|
| `console/backend/.env.example` | Exists and is current for the application-side keys. An earlier reading of this repository that claimed otherwise was wrong — `ls` without `-a` had hidden it |
| Skill inventories in `CLAUDE.md` (lines 250–254) | Match the filesystem exactly: 12 root skills, 5 backend, 8 frontend |
| `.mcp.json` and `.codex/config.toml` | Agree on the browser-driver command, arguments and output directory |
| `e2e/QUALITY_MANIFEST.md` command table and surface matrix | Currently accurate. It was stale earlier in the observation window — missing the `identity` row and still listing the administrative identity suite as pending roadmap work — and was corrected at 13:50 on 2026-08-04. This is the concurrency hazard described at the top of this document, and a useful illustration of it |
| `e2e/package.json` scripts | Nine suites, matching the manifest and the `e2e/README.md` list |
| `.gitattributes` LF enforcement, including the migration checksum file | Consistent with the LF rule stated in `CLAUDE.md`, `schema/README.md` and the coding-principles rule file |
| Logical-foreign-key rule | `CLAUDE.md`, the `no-physical-fks` skill, `.cursor/rules/03-database.mdc` and `schema/README.md` all state it identically, and no `REFERENCES` clause appears in `schema/verim/desired/` |

---

## 5. Suggested order of work

1. **Findings 1 and 2 first.** They are the two that make an agent emit broken code or run a
   failing command, and both are contained text edits with no decision attached.
2. **Findings 5, 10, 11, 12, 13.** Same character — stale text with an unambiguous correct value.
3. **Finding 9.** Add the `live-verification` mirror; decide the rest of the parity question with
   the owner.
4. **Findings 3, 4, 6, 8.** Each needs an owner decision first (section 7). Do not resolve them by
   picking whichever sentence looks newest.
5. **Section 6** last, as a separate piece of work.

Each fix in groups 1 and 2 is a documentation-only change and should not touch code. Where a
document and the code disagree, **the code is the evidence** — change the document, unless the
owner says the documented behavior is the intended one and the code is the bug. Findings 4 and 6
are the two where that could genuinely go either way.

---

## 6. Structural remedy

The immediate fixes restore consistency once. They do not stop the next divergence, because the
mechanism that produced all thirteen findings is still in place: four hand-maintained copies of
the same rules, reconciled by a convention.

The boilerplate designed in `plans/scaffolding-plan.md` (this same repository, sections 7 and 8)
resolves this structurally, and the approach ports back to `kt-console` without adopting anything
else from that plan:

1. One rule corpus — one file per rule, with machine-readable front matter carrying identity,
   scope, trigger, applicable paths, priority and which clients it is emitted into.
2. `CLAUDE.md`, `AGENTS.md`, the skills trees and the `.cursor/rules/*.mdc` files become
   **generated artifacts** with a "do not edit" banner.
3. A CI job regenerates them and fails if the working tree changes. A hand-edited generated file
   cannot survive review, and the "the skill is authoritative on drift" convention becomes
   unnecessary because divergent copies can no longer be authored.

Worth noting what this would have caught: findings 1, 2, 5, 7, 10, 11 and 12 are single-source
errors that generation alone does not fix — a wrong command in the corpus is still wrong
everywhere. What generation removes is findings 3, 4 and 9: the cases where two copies say
different things. To catch the first class as well, the corpus needs executable assertions —
every command in a rule is run, and every path in a rule is checked to exist, as part of the same
CI job. That check is cheap and would have caught findings 1, 10 and 11 mechanically.

---

## 7. Open questions for the owner

These cannot be resolved from the repository; each has a real argument on both sides.

**Open Question 1 — which backend test command is canonical?** The Docker image path (directive
file, agent file, quality manifest), the repo-root virtualenv path (two skills), or the host-pip
path (CI)? All three artifacts exist. Choosing the Docker path means deleting the venv references
and explaining why `.venv/` still sits in the repo root; choosing the venv path means correcting
the directive file's explicit "no repo venv" annotation.

**Open Question 2 — is `delete_reason` part of the mandatory block?** If yes, 32 of 38 tables are
in violation and this is a schema migration, not a documentation fix. If no, three documents need
correcting and `is_deleted` needs to be named in the canonical definition. Related: should the
append-only exemption that `audit_log` and `query_execution` already rely on be written into the
rule?

**Open Question 3 — should Atlas read the application's variable names?** Unifying on
`KT_POSTGRES_{HOST,PORT,USER,PASSWORD}` gives one set and one `.env` surface, at the cost of
editing `atlas.hcl`, the schema-migration skill and any environment where the Atlas-only names are
already exported. Keeping the split needs the four names added to `.env.example` with an
explanation.

**Open Question 4 — are Turkish specification documents an accepted exception?** Six exist. Either
they get translated, or the English-only rule is amended to describe the actual policy. Leaving
both as they are is the one option with no upside.

**Open Question 5 — how much Cursor parity is intended?** Full mirroring of all sixteen skills,
or a stated subset with the reason recorded? If a subset, `live-verification` still needs to be in
it, because a mandatory gate depends on it.

---

## 8. Verification record — 2026-08-04, 15:05

Re-ran every "Verify" line in this document against the working tree after the owner's remediation
pass. Twelve of thirteen findings are closed; one is partially closed. All five open questions were
answered by the fixes.

| # | Status | Evidence |
|---|---|---|
| 1 | Closed | No `generate_openapi_schema` reference remains; all five locations now invoke `python -m app.scripts.export_openapi` |
| 2 | Closed, and better than proposed | The api-standards skill now states the real key, states that no module-level `settings` object exists, and replaces the inline-prefix example with the actual aggregate-router pattern plus a dev-container output caveat |
| 3 | Closed | Every location converged on the Docker image path; all repo-venv references removed. CI keeps host `pip` on the runner, which is a legitimate environment difference |
| 4 | **Partially closed** — see below | Canonical set is now `is_deleted`, `deleted_at`, `deleted_by` in all four locations, `delete_reason` explicitly optional, and an append-only exemption added to both `CLAUDE.md` and `schema/README.md` |
| 5 | Closed | Both documents now point at `npm run generate-types` reading the committed YAML |
| 6 | Closed | `atlas.hcl` now reads `KT_POSTGRES_{HOST,PORT,USER,PASSWORD}` + `KT_VERIM_POSTGRES_DB`; `.env.example` and the schema-migration skill agree |
| 7 | Closed | Flat `src/locales/{en,tr}.json` layout documented; the `messages/`, `index.ts` and per-feature module sections are gone |
| 8 | Closed by rule amendment | `CLAUDE.md` lines 144–145 and the `prd` skill now state that `specs/` documents may be Turkish, one language per document, with identifiers and labels English in both |
| 9 | Closed | Full parity: eight frontend skills, eight Cursor rule files, including `live-verification.mdc` |
| 10 | Closed | No `schema/{console,operational}` reference remains |
| 11 | Closed | No `tests/auth` reference remains |
| 12 | Closed | No notification-domain claim remains |
| 13 | Closed | `console/frontend/console/` removed |

### Residual on Finding 4

`CLAUDE.md` line 100 still reads "Every table", and two exemptions are now stated — append-only
(`audit_log`, `query_execution`) and the warehouse one. Five tables sit outside both:

| Table | File | Likely exemption class, not currently stated |
|---|---|---|
| `console_permission` | `80_user.sql` | Seeded reference/lookup table |
| `console_role_permission` | `80_user.sql` | Pure junction |
| `usage_surface_daily` | `87_usage_insights.sql` | Derived rollup |
| `usage_product_daily` | `87_usage_insights.sql` | Derived rollup |
| `usage_relation_daily` | `87_usage_insights.sql` | Derived rollup |

Each is plausibly correct as built. The gap is that the rule does not name the classes they belong
to, so the next agent adding a junction or a rollup has no way to know whether omitting the triplet
is allowed. Suggested close: extend the exemption sentence to name junction tables and derived
rollup tables alongside append-only streams, or add the triplet to those five.

### Minor residual on Finding 8

`CLAUDE.md` line 55 still reads "Language: English for all code, comments, documentation" while
line 145 permits Turkish in `specs/`. Not a strict contradiction — `specs/` is not `docs/` — but
line 55 is now the loosest sentence on the subject in the file. One clarifying word would close it.

### Method note

The first verification attempt in the session that produced this report used `find -newermt` to
check whether the reference tree had changed. That flag fails silently on this platform and its
empty output was briefly mistaken for evidence of no change. Read-only `git status` and `git log`
are the sound checks and are what every statement in this section rests on.
