# Public repository checks

Run the file inventory check before publishing:

```sh
python scripts/check_public_files.py
```

CI checks the committed file inventory and scans all fetched Git history with
Gitleaks, with findings redacted. The scanner runs locally in the CI runner;
repository contents are not sent to a scanning service. Do not put real secrets
in test fixtures, issues, logs or screenshots. Ignore rules are only a first
barrier: already tracked files and forced additions still need review.

If a credential is ever published, revoke or rotate it first. Removing it in a
later commit does not remove earlier history. Assess history cleanup and copies
in forks, caches, releases and artifacts separately. Never paste a suspected
credential into a public issue.

The inventory check intentionally permits only source/documentation file types
and five explicitly reviewed publication images. Adding a new binary requires a
review of its provenance and metadata before changing that allowlist. Automated
checks detect common mistakes; they do not prove ownership or legal clearance.
