# Security

Agency Garden is a local research runtime. It is not a sandbox for untrusted Python and is not designed as a public multi-tenant service.

Custom worlds and policies execute with your account's permissions. Review extension files and their dependencies before using `--plugin-file`. Keep provider keys in environment variables; do not put them in experiment configuration or source control.

Run databases contain private observations, participant memory and model responses. Default reports omit these fields, but actions and game-defined outcomes can still disclose information. Private reports include sensitive records explicitly. Review exports before publishing research artifacts.

The journal detects inconsistencies between recorded history and current state. It is not a digital signature or protection against an attacker rewriting the complete database. Retain independently stored hashes or signed archives when your research requires stronger custody guarantees.

## Reporting a vulnerability

Report security issues privately to **laurentiu@ymail.dev** with “Agency Garden security” in the subject. Include the affected version, reproduction steps and expected impact. Do not publish secrets or private research records in a GitHub issue.

Security fixes target the latest alpha release. Earlier alpha versions do not have a separate maintenance commitment. No response-time guarantee is currently offered.
