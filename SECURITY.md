# Security policy

This is a government proof of concept for K–3 teachers. It must never hold student data or secrets.

- Report a vulnerability privately to the maintainers (Team ADA) through GitHub's "Report a vulnerability" feature on this repo. Do not open a public issue.
- Never commit keys, passwords, `.env` files, or AWS credentials. CI runs gitleaks on every push.
- No student names, scores, or assessment results are stored anywhere in this system.
