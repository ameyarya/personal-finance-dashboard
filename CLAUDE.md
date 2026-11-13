# Rules for anyone (or any AI assistant) working in this repository

## Personal information never goes into git

This project handles a real household's money. Nothing that identifies a person or their finances may be
committed, pushed, put in a commit message, a screenshot, a test, a comment, a README or an issue.

- That means names, employers, landlords, streets and towns, merchants that point to a person, account or
  card digits, balances and transactions, email addresses, phone numbers, folder paths with a user name,
  home-network addresses, passwords, tokens, certificates, statements and exports.
- Use invented data everywhere in the repo: "Person A", "ACME CO", "Maple Street", round made-up amounts.
  Screenshots must come from the built-in example data, never from the real data folder.
- Real values live only in `data/`, `.privacy-terms.local` and other `*.local` files. They are git-ignored.
  Importer rules for real merchants go in a local rules file (see `tools/rules.example.json`).
- Before every commit run the tests, then `python3 tools/privacy_scan.py --staged`. The git hooks in
  `.githooks/` run the same scan on commit, commit message and push. Turn them on with `sh tools/install-hooks.sh`.
- Never bypass the checks: no `--no-verify`, no editing the hooks or the scanner to let something through.
  A false alarm is fixed by changing the text, or by adding `privacy: allow` to that one line.
- If personal information has already been committed or pushed, stop and tell the owner. Rewriting history
  and force-pushing needs the owner's explicit say-so each time.
- When writing a new importer rule, test or example, ask: could a stranger learn who this is from it? If yes, replace it.
