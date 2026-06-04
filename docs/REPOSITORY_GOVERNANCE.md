# Repository governance

Minimal protections for when this repository is **public** (or on GitHub Pro while private).

## Default branch: `main`

The default branch is **`main`**. CI runs on pushes to `main` and on all pull requests (see [.github/workflows/ci.yml](../.github/workflows/ci.yml)).

## What is already in the repo

| Mechanism | Purpose |
| --------- | ------- |
| [`.github/dependabot.yml`](../.github/dependabot.yml) | Weekly PRs for `pip` (via `pyproject.toml` / lockfile) and GitHub Actions |
| [`SECURITY.md`](../SECURITY.md) | Vulnerability reporting policy |
| [`.github/rulesets/protect-main.json`](../.github/rulesets/protect-main.json) | Ruleset as code: block force-push and branch deletion; require **`lint`** CI on merges |
| [`scripts/apply-github-governance.sh`](../scripts/apply-github-governance.sh) | Creates or updates the ruleset via `gh` |

## Apply branch rules (after making the repo public)

GitHub **rulesets** and classic **branch protection** are not available on **private** repositories with a free plan. After you switch the repository to **public**:

```bash
chmod +x scripts/apply-github-governance.sh
./scripts/apply-github-governance.sh
```

Or from the GitHub UI: **Settings → Rules → Rulesets → New ruleset**, and import the rules from `.github/rulesets/protect-main.json`.

### What the ruleset enforces

- **No force-push** to the default branch (`non_fast_forward`)
- **No branch deletion** for the default branch
- **Required status check** `lint` (must be green before merging a PR; strict: branch must be up to date with `main`)

Direct pushes to `main` are still allowed (no mandatory PR). That keeps solo maintenance simple; add a `pull_request` rule later if you want review-only merges.

## Optional hardening when opening to the public

- Enable **Private vulnerability reporting** (Settings → Security → Code security).
- Review **Dependabot** security alerts and enable **secret scanning** (automatic on public repos).
- Consider requiring pull requests via an extra rule in `protect-main.json` if you accept external contributions.
