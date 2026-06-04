# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| `main`  | Yes       |

## Reporting a vulnerability

**Do not** open a public GitHub issue for security-sensitive reports.

1. Use [GitHub private vulnerability reporting](https://github.com/adriannoes/pipefy-agent-bridge/security/advisories/new) on this repository (available when the repo is public), **or**
2. Contact the maintainers through a private channel you already use with the project owner.

Include:

- A clear description of the issue and impact
- Steps to reproduce (or a minimal proof of concept)
- Affected versions or commits, if known

We aim to acknowledge reports within a few business days. Fixes and coordinated disclosure timelines depend on severity and complexity.

## Secrets and credentials

- Never commit API keys, tokens, or `.env` files.
- Use `.env.example` as the template; keep real values in local `.env` only.
- Rotate any credential that was accidentally exposed immediately.
