---
description: This instruction file provides main procedure to manage GitHub projects, tasks, milestones, labels, pull requests...
applyTo: Anytime you interact with GitHub.
---

<critical>Note: This is a living document and will be updated as we refine our processes. Always refer back to this for the latest guidelines. Update whenever necessary.</critical>

<critical>When creating a pull request from an issue, always mention the issue number in the PR description using `Fixes #N`, `Closes #N`, or `Resolves #N`.</critical>

# GitHub Workflow — H³ Project Management

## Project Board IDs

| Resource | ID |
|----------|-----|
| Project (org-level, #1) | `PVT_kwDOD_yaZ84BRv-S` |
| Status field | `PVTSSF_lADOD_yaZ84BRv-Szg_fF9E` |
| Priority field | `PVTSSF_lADOD_yaZ84BRv-Szg_f9RA` |
| Complexity field | `PVTSSF_lADOD_yaZ84BRv-Szg_45es` |

### Status Options

| Status | Option ID |
|--------|-----------|
| Backlog | `fd182097` |
| Ready | `3a8dc8b6` |
| Blocked | `fbfa34a2` |
| In Progress | `7ede3e2f` |
| In Review | `68f37177` |
| Done | `fa71c4c1` |

### Priority Options

| Priority | Option ID |
|----------|-----------|
| High | `ddb9c762` |
| Medium | `3a0d1cdb` |
| Low | `a5ab890a` |

### Complexity Options

Complexity indicates the intrinsic implementation difficulty of a task. It is used to select the appropriate LLM for implementation (e.g., Trivial/Low → lighter models, Medium/High → stronger models). **Any LLM refining or creating tasks MUST calculate and set this field**, just like Status and Priority.

| Complexity | Option ID | Description |
|------------|-----------|-------------|
| Trivial | `da06bf4b` | Config changes, typos, one-liners, boilerplate-only tasks |
| Low | `a2f911d6` | Single-file or single-module changes, straightforward implementations |
| Medium | `2554780f` | Multi-file changes, cross-layer work, moderate domain understanding needed |
| High | `1e0692fb` | Cross-service/repo changes, architectural decisions, complex algorithms |

## Creating an Issue

1. Create the issue with proper labels, milestone, and conventional commit title:

```bash
gh issue create \
  --repo Hexadian-Corporation/<repo> \
  --title "<type>(<scope>): <short description>" \
  --body "<markdown body>" \
  --label "backend,feature,priority:high" \
  --milestone "M1: Hauling Contracts - Domain & API"
```

2. Add to project board:

```bash
gh project item-add 1 --owner Hexadian-Corporation --url <issue-url>
```

3. **Always set Status and Priority** on the project board item using GraphQL mutations:

```bash
# Get the item ID (filter from item-list)
gh project item-list 1 --owner Hexadian-Corporation --format json | \
  ConvertFrom-Json | ForEach-Object { $_.items } | \
  Where-Object { $_.title -match "<ISSUE_TITLE>" } | \
  Select-Object -ExpandProperty id

# Set Status (e.g., Ready)
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwDOD_yaZ84BRv-S",
    itemId: "<ITEM_ID>",
    fieldId: "PVTSSF_lADOD_yaZ84BRv-Szg_fF9E",
    value: { singleSelectOptionId: "<STATUS_OPTION_ID>" }
  }) { projectV2Item { id } }
}'

# Set Priority (e.g., Medium)
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwDOD_yaZ84BRv-S",
    itemId: "<ITEM_ID>",
    fieldId: "PVTSSF_lADOD_yaZ84BRv-Szg_f9RA",
    value: { singleSelectOptionId: "<PRIORITY_OPTION_ID>" }
  }) { projectV2Item { id } }
}'

# Set Complexity (e.g., Medium)
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwDOD_yaZ84BRv-S",
    itemId: "<ITEM_ID>",
    fieldId: "PVTSSF_lADOD_yaZ84BRv-Szg_45es",
    value: { singleSelectOptionId: "<COMPLEXITY_OPTION_ID>" }
  }) { projectV2Item { id } }
}'
```

4. **Set blocking relationships** if the issue depends on other issues (see [Issue Relationships](#issue-relationships-blocking--blocked-by) below).

<critical>
**Mandatory Issue Checklist** — Every issue MUST have ALL of the following before it is considered properly created:

1. ✅ **Created with labels, milestone, and conventional title** (`gh issue create`)
2. ✅ **Added to org project board #1** (`gh project item-add 1 --owner Hexadian-Corporation --url <url>`)
3. ✅ **Status set on the board** — `Ready` if no dependencies, `Blocked` if it depends on other issues
4. ✅ **Priority set on the board** — `High`, `Medium`, or `Low`
5. ✅ **Complexity set on the board** — `Trivial`, `Low`, `Medium`, or `High` (calculated by analyzing the task's scope, number of files/services affected, and domain knowledge required)
6. ✅ **Blocking relationships set** via GraphQL `addBlockedBy` mutation (if applicable)

Skipping any of these steps results in orphaned issues that don't appear on the board, have no priority, or silently ignore dependencies. The auto-unblock workflow relies on native blocking relationships — body text like "Depends on #X" is **ignored**.
</critical>

## Status Transitions

| Action | Set Status to |
|--------|---------------|
| New task, not yet prioritized | Backlog |
| Task is ready to pick up (dependencies met, well-defined) | Ready |
| Task has unmet dependencies (waiting on other tasks) | Blocked |
| Work has started (branch created, coding) | In Progress |
| PR opened, awaiting review | In Review |
| PR merged and issue closed | Done |

## Issue & PR Title Convention

Issues and PRs follow **conventional commits**: `<type>(<scope>): <description>`

This format is intentionally identical for both issue titles and PR titles. When Copilot (or any developer) creates a PR from an issue, the issue title is copied directly as the PR title — no manual reformatting needed. Since squash merge uses the PR title as the commit message, this also ensures a clean `main` history.

**Allowed types:** `chore`, `fix`, `ci`, `docs`, `feat`, `refactor`, `test`, `build`, `perf`, `style`, `revert`

**Scope** is a lowercase identifier for the affected area. Use the repo's conventional scope:

| Repo | Scope | Example |
|------|-------|--------|
| hhh-contracts-service | `contracts` | `feat(contracts): enrich domain model` |
| hhh-ships-service | `ships` | `feat(ships): add ship CRUD` |
| hhh-maps-service | `maps` | `feat(maps): seed test locations` |
| hhh-graphs-service | `graphs` | `feat(graphs): add graph model` |
| hhh-routes-service | `routes` | `feat(routes): route optimization` |
| hexadian-auth-service | `auth` | `feat(auth): RSI verification` |
| hexadian-auth-common | `auth-common` | `feat(auth-common): scaffold package` |
| hhh-commodities-service | `commodities` | `feat(commodities): add commodity CRUD` |
| hhh-dataminer | `dataminer` | `feat(dataminer): add data source adapter` |
| hhh-frontend | `frontend` | `feat(frontend): landing page` |
| hhh-backoffice-frontend | `backoffice` | `feat(backoffice): contract list page` |
| hexadian-hauling-helper | `main` | `ci(main): add auto-unblock workflow` |

> **Regex enforced by CI:** `^(chore|fix|ci|docs|feat|refactor|test|build|perf|style|revert)\([a-z][a-z0-9-]*\): .+$`

## Labels

Apply labels from the synced set: `domain`, `api`, `persistence`, `backend`, `frontend`, `setup`, `testing`, `feature`, `enhancement`, `backoffice`, `priority:high`, `priority:medium`, `priority:low`, `project-management`

## Pull Request Workflow

1. Create feature branch from `main` (convention: `copilot/<issue-slug>` or `feature/<issue-slug>`)
2. Set issue status to **In Progress**
3. Open PR referencing the issue (`Fixes #N` in body)
4. Set issue status to **In Review**
5. After merge, set issue status to **Done**

## CI / Continuous Integration

Every repo has a `.github/workflows/ci.yml` that runs on PRs to `main`.

### Python services (contracts, ships, maps, graphs, routes, auth, commodities, dataminer)

| Job | Name | What it does |
|-----|------|-------------|
| `lint` | Lint & Format | `ruff check .` + `ruff format --check .` |
| `test` | Tests & Coverage | `pytest --cov=src --cov-report=xml --cov-report=term-missing` then `diff-cover coverage.xml --compare-branch=origin/main --fail-under=90` |
| `copilot-fix` | Request Copilot Fix | On failure → posts a copy-paste `@copilot` suggestion comment on the PR |

### Frontends (frontend, backoffice-frontend)

| Job | Name | What it does |
|-----|------|-------------|
| `lint` | Lint & Type Check | `npm run lint` + `npx tsc --noEmit` |
| `test` | Tests & Coverage | `npm test` (vitest with cobertura reporter) then `pipx run diff-cover coverage/cobertura-coverage.xml --compare-branch=origin/main --fail-under=90` |
| `copilot-fix` | Request Copilot Fix | On failure → posts a copy-paste `@copilot` suggestion comment on the PR |

### Coverage requirements

- **Minimum 90% on changed lines** — coverage is enforced only on lines added/modified in the PR, not the entire repo.
- Uses `diff-cover` to compare coverage against `origin/main`.
- Python: `pytest-cov` generates XML report → `diff-cover` checks changed lines.
- Frontends: `@vitest/coverage-v8` generates cobertura report → `diff-cover` (via `pipx`) checks changed lines.
- The `test` job uses `fetch-depth: 0` on checkout so `diff-cover` can access git history.

### @copilot auto-fix

When `lint` or `test` jobs fail, the `copilot-fix` job posts a PR comment with the list of failed checks and a code block containing `@copilot Please fix the CI failures listed above.` that the user can copy-paste as a new comment to trigger Copilot.

### Submodule Ref Sync

Submodule refs in `hexadian-hauling-helper` are **automatically updated** when any submodule pushes to `main`:

- **Each submodule** has a thin `notify-main.yml` caller → calls `notify-main-reusable.yml` in the `.github` repo → sends a `repository_dispatch` (`submodule-updated`) to `hexadian-hauling-helper`.
- **`hexadian-hauling-helper`** has `sync-submodules.yml` — triggered by `repository_dispatch` (or manually via `workflow_dispatch`), runs `git submodule update --remote --merge`, commits and pushes the updated refs.
- `.gitmodules` has `branch = main` for all submodules so `--remote` knows which branch to track.

### Reusable Workflows (org-level)

The `Hexadian-Corporation/.github` repo hosts **reusable workflows** that all repos call via thin callers. This keeps logic centralized in a single source of truth.

| Reusable workflow | Purpose | Caller trigger |
|-------------------|---------|----------------|
| `auto-status-reusable.yml` | Updates project board status based on PR lifecycle events | `pull_request` |
| `secret-scan-reusable.yml` | Runs gitleaks secret detection | `pull_request` |
| `pr-title-reusable.yml` | Validates PR title format (accepts `example` and `scopes` inputs) | `pull_request` |
| `copilot-fix-reusable.yml` | Posts CI failure report on PR with `@copilot` fix prompt (accepts `stack` input: `python`/`node`/`mixed`) | `workflow_call` from ci.yml `copilot-fix` job |
| `notify-main-reusable.yml` | Dispatches `submodule-updated` to hexadian-hauling-helper | `push` to `main` |
| `auto-unblock.yml` | Two-phase blocked/unblocked task management (not reusable — runs on schedule + dispatch) | `schedule`, `repository_dispatch`, `workflow_dispatch` |

**Caller pattern** — Each repo has thin workflow files that delegate to the reusable ones:

```yaml
# Example: auto-status.yml in any repo
name: Auto-status
on:
  pull_request:
    branches: [main]
    types: [opened, reopened, ready_for_review, converted_to_draft, closed]
jobs:
  auto-status:
    uses: Hexadian-Corporation/.github/.github/workflows/auto-status-reusable.yml@main
    secrets:
      PROJECT_TOKEN: ${{ secrets.PROJECT_TOKEN }}
```

**Check name format** — With reusable workflows, status check names follow the pattern `<caller_job> / <called_job>`. Required checks use this format:
- `pr-title / Validate PR Title` (was `Validate PR Title`)
- `secret-scan / Secret Scan` (was `Secret Scan`)
- `Request Copilot Fix / CI Failure Report` (copilot-fix reusable workflow, only runs on CI failure)
- CI checks remain unchanged (ci.yml is per-repo, not reusable)

### Secret Scan

**`secret-scan-reusable.yml`** (in `.github` repo, called by all repos) — runs [gitleaks](https://github.com/gitleaks/gitleaks-action) on every PR to detect accidentally committed secrets, API keys, or tokens.

Free for public org repos. Uses `GITHUB_TOKEN` only — no additional secrets required.

### PR Title Validation (reusable)

**`pr-title-reusable.yml`** (in `.github` repo, called by all repos) — validates conventional commit format.

Accepts two optional inputs:
- `example` — Example PR title shown in error message (default: `fix(scope): short description`)
- `scopes` — Comma-separated scope list shown in error message (default: all HHH scopes)

hexadian-auth-client overrides with `scopes: "auth-core, auth-react, auth-client"`.

### Copilot Fix (reusable)

**`copilot-fix-reusable.yml`** (in `.github` repo, called by all 11 repos with ci.yml) — When lint/test jobs fail, posts a structured CI failure report as a PR comment with log excerpts and a `@copilot` prompt.

Accepts one input:
- `stack` — `python` (default), `node`, or `mixed` (for repos with both Python and Node.js stacks)

Caller job pattern:
```yaml
copilot-fix:
  name: Request Copilot Fix
  needs: [lint, test]
  if: failure()
  uses: Hexadian-Corporation/.github/.github/workflows/copilot-fix-reusable.yml@main
  with:
    stack: python  # or node, or mixed
```

Stack assignments: `python` for all Python backend services + auth-common, `node` for frontend + backoffice-frontend + auth-client, `mixed` for auth-service (multiple sub-projects).

### Auto-status & Unblock

**`auto-status-reusable.yml`** (in `.github` repo, called by all 12 repos with PRs) — Reacts to PR lifecycle events and moves the linked issue(s) on the project board:

| PR Event | Status |
|----------|--------|
| Opened/reopened (draft) | In Progress |
| Opened/reopened (non-draft) | In Review |
| Converted to draft | In Progress |
| Ready for review | In Review |
| Closed + merged | Done + closes linked issues (fallback) + dispatches `unblock-check` to `.github` repo |

The workflow extracts linked issue numbers (`Fixes #N`, `Closes #N`, `Resolves #N`) from the PR body. On merge, it also closes any linked issues that are still open as a fallback — this protects against GitHub's native `closingIssuesReferences` mechanism breaking (see BUG-014).

**`auto-unblock.yml`** (in `.github` repo, runs directly — not reusable) — Three-phase check that runs on every cycle:

1. **Phase 1 — Unblock:** Checks all "Blocked" tasks. If all `blockedBy` issues are closed → moves to "Ready".
2. **Phase 2 — Auto-block:** Checks all non-blocked open items. If any has open `blockedBy` dependencies → moves to "Blocked".
3. **Phase 3 — Reopened-issue fix:** Checks all OPEN items still marked "Done" (e.g., reopened issues). Moves them to "Ready" (or "Blocked" if they have open dependencies).

> **Why not a built-in project workflow?** GitHub Projects v2 built-in workflows only support simple "set field to value" actions. auto-unblock requires iterating items, querying blocking relationships, and conditional logic — this can only be done as a GitHub Actions workflow. The `.github` org repo is the correct home because the workflow operates on the org project board, not on a specific repo.

Runs:
- **Immediately** via `repository_dispatch` (`unblock-check`) when any task is marked Done
- **Every 15 minutes** via cron as a safety net
- **Manually** via `workflow_dispatch`

### Submodule Notification (reusable)

**`notify-main-reusable.yml`** (in `.github` repo, called by 8 submodule repos) — On push to `main`, dispatches `submodule-updated` event to hexadian-hauling-helper to trigger `sync-submodules.yml`.

### Built-in Project Board Workflows

The org project (#1) has built-in workflows configured at `Settings > Workflows`:

| Workflow | Enabled | Action |
|----------|---------|--------|
| Auto-add sub-issues to project | ✅ Yes | Automatically adds sub-issues when parent is on the board |
| Item added to project | ✅ Yes | Sets Status → **Backlog** for new items |
| Item closed | ✅ Yes | Sets Status → **Done** (safety net for manually-closed issues) |
| Auto-archive items | ✅ Yes | Automatically archives closed/Done items after a period |
| Auto-close issue | ❌ No | — (dangerous: accidental Done drag would close issues) |
| Pull request merged | ❌ No | — (auto-status.yml handles this more granularly + dispatches unblock-check) |
| Pull request linked to issue | ❌ No | — (auto-status.yml handles draft vs non-draft distinction) |

> **Note:** Built-in project workflows cannot be configured via API — only through the GitHub web UI at the project's Settings > Workflows page.

## Repository Settings

All repos are configured with:

| Setting | Value |
|---------|-------|
| Merge strategy | **Squash merge only** (merge commits and rebase disabled) |
| Delete branch on merge | `true` — PR branches are automatically deleted after merge |
| Allow auto-merge | `true` — PRs can be set to auto-merge once all checks pass + review approved |

Since squash merge uses the **PR title as the commit message**, the PR title validation workflow ensures a clean `main` history.

## Branch Protection

All repos have `main` branch protection with:

| Rule | Value |
|------|-------|
| Required status checks | ✅ `Lint & Format` + `Tests & Coverage` + `Validate PR Title` + `Secret Scan` |
| Approving reviews required | ✅ 1+ approval from CODEOWNERS (@Arkaivos, @christianlc00, @naldwax) |
| Push restricted to | ✅ 3 authorized users only (Arkaivos, christianlc00, naldwax) |
| Require branches up to date (`strict`) | ✅ Yes — PR branch must be updated before merging |
| Required linear history | ✅ Yes — no merge commits on `main` |
| Force pushes allowed | ❌ No |
| Allow deletions | ❌ No |
| Enforce on admins | ❌ No (admins can bypass, but still need CODEOWNERS approval) |

<critical>
**Required status checks MUST use `app_id: 15368`** (GitHub Actions). Never set `app_id: null` — it causes checks to freeze as "Expected — Waiting for status" when the check name hasn't been previously reported on `main`. This is especially critical when renaming CI jobs or adding new required checks. See BUG-011 in `bug-history.instructions.md`.
</critical>

### Required Status Checks per Repo Type

| Repo type | Required checks |
|-----------|----------------|
| Python backend services | `Lint & Format`, `Tests & Coverage`, `pr-title / Validate PR Title`, `secret-scan / Secret Scan` |
| Frontend repos | `Lint & Type Check`, `Tests & Coverage`, `pr-title / Validate PR Title`, `secret-scan / Secret Scan` |
| hexadian-auth-service | `Lint & Format`, `Tests & Coverage`, `pr-title / Validate PR Title`, `secret-scan / Secret Scan`, `Auth Portal Lint & Type Check`, `Auth Portal Tests`, `Backoffice: Lint & Type Check`, `Backoffice: Tests` |
| hexadian-hauling-helper | `pr-title / Validate PR Title`, `secret-scan / Secret Scan` |

**PR Merge Flow (enforced):**
1. Developer opens PR from feature branch
2. CI checks pass (Lint, Tests, PR Title validation, Secret Scan)
3. A CODEOWNER reviews and approves the PR
4. Only the CODEOWNER (or another authorized user) can click "Merge"
5. Merge is squashed, branch deleted, commit message = PR title

To update required status checks via API:

```bash
# IMPORTANT: Always specify app_id: 15368 for GitHub Actions checks.
# Using app_id: null causes checks to freeze for new/renamed check names.

# Python backend service example (write BOM-free JSON for gh CLI)
cat > /tmp/bp-checks.json << 'EOF'
{
  "strict": true,
  "checks": [
    {"context": "Lint & Format", "app_id": 15368},
    {"context": "Tests & Coverage", "app_id": 15368},
    {"context": "pr-title / Validate PR Title", "app_id": 15368},
    {"context": "secret-scan / Secret Scan", "app_id": 15368}
  ]
}
EOF

gh api repos/Hexadian-Corporation/<repo>/branches/main/protection/required_status_checks \
  --method PATCH --input /tmp/bp-checks.json
```

To update full branch protection (restrictions + reviews):

```bash
# Complete branch protection configuration
gh api repos/Hexadian-Corporation/<repo>/branches/main/protection \
  --method PATCH \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f required_pull_request_reviews.require_code_owner_reviews=true \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f 'restrictions[users][0]=Arkaivos' \
  -f 'restrictions[users][1]=christianlc00' \
  -f 'restrictions[users][2]=naldwax'
```

## PR Title Validation

Every repo has `.github/workflows/pr-title.yml` that validates the PR title format:

**Required format:** `<type>(<scope>): description`

- Example: `feat(contracts): enrich domain model`
- Example: `fix(maps): resolve seed data mutation bug`
- Example: `ci(backoffice): add diff-cover to CI pipeline`

Allowed conventional types: `chore`, `fix`, `ci`, `docs`, `feat`, `refactor`, `test`, `build`, `perf`, `style`, `revert`

Scope must be lowercase, starting with a letter, followed by letters, digits, or hyphens.

The issue title and PR title use the **same format** — Copilot copies the issue title directly as the PR title.

Since squash merge uses the PR title as the commit message, this ensures a clean, traceable `main` history.

## Issue Relationships (Blocking / Blocked By)

Dependencies between issues are managed using **native GitHub issue relationships**, not body text.

Each issue has two relationship fields visible in the sidebar:
- **Blocked by** — issues that must be completed before this one can start
- **Blocking** — issues that this one is preventing from starting

### Adding relationships via GraphQL

Use the `addBlockedBy` mutation. The `issueId` is the **blocked** issue, and `blockingIssueId` is the **blocker**:

```bash
# First, get the node IDs of both issues
BLOCKED_ID=$(gh api graphql -f query='query {
  repository(owner: "Hexadian-Corporation", name: "<REPO>") {
    issue(number: <N>) { id }
  }
}' --jq '.data.repository.issue.id')

BLOCKER_ID=$(gh api graphql -f query='query {
  repository(owner: "Hexadian-Corporation", name: "<REPO>") {
    issue(number: <N>) { id }
  }
}' --jq '.data.repository.issue.id')

# Add the relationship
gh api graphql -f query='mutation {
  addBlockedBy(input: {
    issueId: "'"$BLOCKED_ID"'",
    blockingIssueId: "'"$BLOCKER_ID"'"
  }) { clientMutationId }
}'
```

> **Note:** Cross-repo relationships are supported (e.g., BO-2 blocked by CS-2).

### Querying relationships

```bash
# Check what blocks an issue
gh api graphql -f query='query {
  repository(owner: "Hexadian-Corporation", name: "<REPO>") {
    issue(number: <N>) {
      blockedBy(first: 10) { nodes { number state repository { name } } }
      blocking(first: 10) { nodes { number state repository { name } } }
    }
  }
}'
```

### Removing relationships

```bash
gh api graphql -f query='mutation {
  removeBlockedBy(input: {
    issueId: "'"$BLOCKED_ID"'",
    blockingIssueId: "'"$BLOCKER_ID"'"
  }) { clientMutationId }
}'
```

### Rules

- **Never** use body text (`**Depends on:**`, `**Blocks:**`, task lists) to express dependencies — always use native GitHub issue relationships via the GraphQL `addBlockedBy` mutation.
- When creating a new issue that depends on another, add the `addBlockedBy` relationship **immediately** after creation — do not defer this to a later step.
- Set the issue status to **Blocked** on the project board when it has unresolved blocking relationships. The `auto-unblock.yml` Phase 2 will also auto-detect and block items with open dependencies during each cycle, but setting it explicitly at creation time avoids any delay.
- When creating issues in bulk (e.g., a new milestone with many issues), set **all** blocking relationships in the same session. Do not leave relationships for later — they will be forgotten.
- Cross-repo relationships are fully supported (e.g., `hhh-frontend#34` blocked by `hexadian-auth-service#28`). Use the full node IDs from each repo.

## Auto-Unblock Workflow

`Hexadian-Corporation/.github` has `.github/workflows/auto-unblock.yml` — an **org-level** workflow that manages blocking/unblocking for ALL projects across the organization.

**Phase 1 — Unblock:**
1. Lists all **Blocked** items on the project board
2. For each blocked issue, queries its `blockedBy` relationships via GraphQL
3. If **all** blocking issues are **CLOSED**, moves the item to **Ready**

**Phase 2 — Auto-block:**
1. Lists all non-blocked open items on the project board
2. For each, queries its `blockedBy` relationships
3. If **any** blocking issue is still **OPEN**, moves the item to **Blocked**

Requires a `PROJECT_TOKEN` secret with `repo` + `project` scopes (set on the `.github` repo).

## Repository Security Configuration

When setting up a new public repository, apply the standard security controls:

### 1. Ensure Public Visibility

```bash
gh repo edit Hexadian-Corporation/<repo> --visibility public
```

### 2. Create CODEOWNERS File

At the root of the repository, create `CODEOWNERS` file with:

```
* @Arkaivos @christianlc00 @naldwax
```

Push to `main`:

```bash
echo "* @Arkaivos @christianlc00 @naldwax" > CODEOWNERS
git add CODEOWNERS
git commit -m "docs: add CODEOWNERS for review requirements"
git push origin main
```

### 3. Configure Branch Protection on main

```bash
# Set up branch protection with CODEOWNERS review requirement
gh api repos/Hexadian-Corporation/<repo>/branches/main/protection \
  --method PATCH \
  -f 'restrictions[users][0]=Arkaivos' \
  -f 'restrictions[users][1]=christianlc00' \
  -f 'restrictions[users][2]=naldwax' \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f required_pull_request_reviews.require_code_owner_reviews=true
```

Then set required status checks with **explicit `app_id: 15368`** (see BUG-011):

```bash
cat > /tmp/bp-checks.json << 'EOF'
{
  "strict": true,
  "checks": [
    {"context": "Lint & Format", "app_id": 15368},
    {"context": "Tests & Coverage", "app_id": 15368},
    {"context": "pr-title / Validate PR Title", "app_id": 15368},
    {"context": "secret-scan / Secret Scan", "app_id": 15368}
  ]
}
EOF

gh api repos/Hexadian-Corporation/<repo>/branches/main/protection/required_status_checks \
  --method PATCH --input /tmp/bp-checks.json
```

**What this does:**
- ✅ Restricts push to only 3 users (prevents direct commits)
- ✅ Requires 1+ approval from CODEOWNERS before merge
- ✅ Requires linear history (no merge commits)
- ✅ Prevents force pushes and deletions

### 4. Verify Configuration

```bash
# Check that restrictions are in place
gh api repos/Hexadian-Corporation/<repo>/branches/main/protection/restrictions

# Expected output: Users Arkaivos, christianlc00, naldwax listed
```

### Bulk Configuration Script (PowerShell)

To apply security changes to multiple repos at once:

```powershell
$repos = @(
  "repo1",
  "repo2",
  "repo3"
)

$users = @("Arkaivos", "christianlc00", "naldwax")

foreach ($repo in $repos) {
  Write-Host "Configuring $repo..."
  
  # Create CODEOWNERS via API
  $codeowners = "* @Arkaivos @christianlc00 @naldwax"
  $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($codeowners))
  
  $payload = @{
    message = "docs: add CODEOWNERS for review requirements"
    content = $encoded
    branch = "main"
  } | ConvertTo-Json
  
  $tmpFile = [System.IO.Path]::GetTempFileName()
  $payload | Set-Content -Path $tmpFile -Encoding UTF8
  
  # Apply CODEOWNERS
  gh api repos/Hexadian-Corporation/$repo/contents/CODEOWNERS --method PUT --input $tmpFile 2>&1 | Out-Null
  
  # Apply branch protection with CODEOWNERS review requirement
  $tmpFile2 = [System.IO.Path]::GetTempFileName()
  @{
    restrictions = @{
      users = $users
      teams = @()
      apps = @()
    }
    required_pull_request_reviews = @{
      required_approving_review_count = 1
      require_code_owner_reviews = $true
      dismiss_stale_reviews = $false
      require_last_push_approval = $false
    }
  } | ConvertTo-Json | Set-Content -Path $tmpFile2 -Encoding UTF8
  
  gh api repos/Hexadian-Corporation/$repo/branches/main/protection --method PATCH --input $tmpFile2 2>&1 | Out-Null
  
  Remove-Item $tmpFile, $tmpFile2 -ErrorAction SilentlyContinue
  Write-Host "✅ Done"
}
```

---

## Bulk Issue Operations — PowerShell + GraphQL Best Practices

When creating many issues at once (e.g., a new milestone), use scripted bulk operations. The following patterns have been validated.

### Working pattern: JSON file + `--input`

The **only reliable way** to pass GraphQL mutations from PowerShell to `gh api graphql` is via a JSON file:

```powershell
# Build the JSON payload as a PowerShell string
$json = '{"query": "mutation { updateProjectV2ItemFieldValue(input: { projectId: \"PVT_kwDOD_yaZ84BRv-S\", itemId: \"' + $itemId + '\", fieldId: \"' + $fieldId + '\", value: { singleSelectOptionId: \"' + $optionId + '\" } }) { projectV2Item { id } } }"}'

# Write BOM-free UTF-8 (critical for gh CLI)
$filePath = Join-Path $PSScriptRoot "mutation.json"
[System.IO.File]::WriteAllText($filePath, $json)

# Execute
gh api graphql --input $filePath
```

### Patterns that DO NOT work in PowerShell

| Pattern | Problem |
|---------|---------|
| `-f query='mutation { ... }'` | Single quotes are not string delimiters in PowerShell; the query gets mangled |
| `-f query="mutation { ... }"` | Double quotes require complex escaping of all inner quotes; fragile and error-prone |
| `@$queryFile` (GraphQL file reference) | The `@` is parsed as a PowerShell splatting operator or GraphQL directive |
| Pipe JSON via stdin (`$json \| gh api graphql --input -`) | Results in `HTTP 400: Problems parsing JSON` due to encoding/BOM issues |
| `Out-File -Encoding utf8NoBOM` | Only works in PowerShell 7+; `powershell -File` uses PS 5.1 which doesn't support this encoding |

### Key lessons

- **Always use `[System.IO.File]::WriteAllText()`** for writing JSON files — it produces BOM-free UTF-8 in both PS 5.1 and PS 7. `Out-File` and `Set-Content` add a BOM in PS 5.1, which breaks `gh api graphql --input`.
- **Use `$PSScriptRoot`** for file paths when running scripts via `powershell -File` — relative paths resolve to the caller's CWD, not the script's directory.
- **Use `--input <file>`** instead of `-f query=` for any mutation with complex quoting (IDs, nested objects).
- **Batch by concern**: first `gh project item-add` (all issues), then set Status (all issues), then set Priority (all issues), then set blocking relationships. This makes failures easy to identify and retry.
- **Log results**: print `[OK]` / `[FAIL]` per operation with the issue identifier so you can quickly spot and retry failures.

### Bulk blocking relationships

To set many blocking relationships at once, pre-fetch all issue node IDs, then loop through the relationship pairs:

```powershell
# Pre-fetch node ID for an issue
$nodeId = gh api graphql -f query='query {
  repository(owner: "Hexadian-Corporation", name: "<REPO>") {
    issue(number: <N>) { id }
  }
}' --jq '.data.repository.issue.id'

# Set blocking relationship (write JSON to file, use --input)
$json = '{"query": "mutation { addBlockedBy(input: { issueId: \"' + $blockedId + '\", blockingIssueId: \"' + $blockerId + '\" }) { clientMutationId } }"}'
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot "rel.json"), $json)
gh api graphql --input (Join-Path $PSScriptRoot "rel.json")
```

> **Tip:** When setting 40+ relationships, use a data array and loop. Expect ~1 second per GraphQL call. Log each result to track progress.