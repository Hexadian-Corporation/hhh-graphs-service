---
description: Development workflow — branch strategy, PR requirements, and commit policy. Applies to all files and tasks.
applyTo: "**"
---

<critical>Note: This is a living document and will be updated as we refine our processes. Always refer back to this for the latest guidelines. Update whenever necessary.</critical>

# Development Workflow — Branch & PR Policy

## The Golden Rule

**All code changes must go through a feature branch and a pull request targeting `main`.**

Never commit or push directly to `main` unless the user explicitly instructs it (e.g., *"commit this directly to main"*, *"push directly to main"*, *"no PR needed"*). When in doubt, use a branch and open a PR.

## Branch Naming

Use the format `<type>/<short-slug>`, matching the conventional-commit type of the change:

| Branch prefix | When to use | Example |
|--------------|-------------|---------|
| `feature/` | New functionality | `feature/contract-list-page` |
| `fix/` | Bug fix | `fix/cors-missing-middleware` |
| `ci/` | CI/CD changes | `ci/add-secret-scan` |
| `docs/` | Documentation only | `docs/update-readme` |
| `refactor/` | Code restructuring | `refactor/extract-mapper` |
| `chore/` | Maintenance tasks | `chore/update-deps` |
| `copilot/` | Copilot-generated branch | `copilot/auth-rsi-verification` |

## Step-by-Step Workflow

1. **Start from the latest `main`:**
   ```bash
   git checkout main && git pull origin main
   git checkout -b feature/<slug>
   ```

2. **Commit with conventional messages:**
   ```bash
   git add .
   git commit -m "feat(<scope>): short description"
   ```

3. **Push and open a PR:**
   ```bash
   git push -u origin feature/<slug>
   gh pr create --title "<type>(<scope>): description" --body "Fixes #N" --base main
   ```

4. **Ensure CI passes** — all required checks must be green before merge:
   - `Lint & Format` / `Lint & Type Check`
   - `Tests & Coverage` (≥90% on changed lines via `diff-cover`)
   - `Validate PR Title`
   - `Secret Scan`

5. **CODEOWNER approval** — 1 approval from @Arkaivos, @christianlc00, or @naldwax is required.

6. **Squash merge** — the PR title becomes the commit message on `main`. The branch is deleted automatically.

## PR Checklist

Before requesting review, ensure:

- [ ] PR title matches `<type>(<scope>): description` — identical to the linked issue title
- [ ] PR body contains `Fixes #N` (or `Closes #N` / `Resolves #N`) to auto-close the issue on merge
- [ ] All CI checks pass
- [ ] Branch is up to date with `main` (merge or rebase if behind)
- [ ] No secrets or credentials in the diff

## When Direct Commits to `main` Are Allowed

Only when the user **explicitly** says so, using phrases such as:

- *"commit this directly to main"*
- *"push directly to main"*
- *"no PR needed for this"*

Even then, GitHub push restrictions apply — only @Arkaivos, @christianlc00, and @naldwax can push to `main` directly. All other contributors must go through PRs regardless.

## Why This Workflow Matters

Every PR triggers the full CI pipeline:

- **Lint & Tests** — prevents broken or unformatted code reaching `main`
- **Coverage enforcement** — `diff-cover` ensures ≥90% coverage on changed lines
- **PR title validation** — squash merge uses the PR title as the commit message, keeping `main` history clean
- **CODEOWNER review** — at least one human reviews every change before it lands
- **Branch up-to-date enforcement** — prevents silent integration failures

Bypassing this workflow risks merging untested, unreviewed, or incorrectly formatted code directly into `main`.
