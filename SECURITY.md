# Security Policy

Muninn stores personal information: where people keep their documents, who owes
them money, their doctor appointments. We take security seriously.

## Reporting a vulnerability

**Please don't open a public issue for security problems.**

Report privately through
[GitHub private vulnerability reporting](https://github.com/DaniPopov/muninn/security/advisories/new).

Please include:
- What the issue is and where it lives (file, endpoint, configuration)
- Steps to reproduce
- The impact you think it has

You'll get a reply within **7 days**. We'll keep you updated and credit you in the fix
if you want.

## Supported versions

Muninn hasn't been released yet. Once it has, only the latest release gets security fixes.

## Security goals (what we promise to build toward)

- Data encrypted at rest on the user's own server
- Secrets (API keys, encryption keys) only in environment variables, never in the repo or logs
- Voice notes deleted after transcription unless the user chooses to keep them
- Easy full export and full delete of a user's data
