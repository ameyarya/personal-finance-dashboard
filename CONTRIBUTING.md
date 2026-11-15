# Working on this project

Start here if you have just cloned it.

```bash
make setup     # virtual environment, dependencies, test browser, privacy hooks
make run       # http://localhost:8770/ with made-up example data
make test      # everything: about 4 minutes
```

`make` on its own lists every command. No `make`? The recipes in the [Makefile](Makefile) are plain shell.

## The one rule

This project handles a real household's money. **Nothing personal goes into git**: no names, merchants, account
digits, balances, statements, paths with a user name. Use invented data ("Person A", "ACME CO", round amounts).
`make setup` turns on hooks that scan every commit and push; never bypass them. Full rules: [CLAUDE.md](CLAUDE.md).
Real data lives only in `data/` and `*.local` files, which git ignores.

## How it fits together

| File | What it does |
|---|---|
| `server.py` | The server (standard library only): JSON storage in `data/data.json`, the API, folder sync, static files |
| `statements.py` | Reads statement PDFs: one reader per bank, balance checks, and the audit behind the **Data** page |
| `llm.py` | Optional local-model (Ollama) fallback for statements the readers cannot handle; off by default |
| `auth.py` | Optional sign-in |
| `public/app.js` | The whole page: state, rendering, forms (no framework, no build step) |
| `public/app.css`, `public/index.html` | Styles (light and dark) and the page shell |
| `tools/` | Privacy scanner, statement importer, coverage and screenshot scripts |
| `tests/` | pytest suites; `tests/TEST_CASES.md` lists every flow covered |

There is no build step: edit a file and reload.

## Day to day

- Change something, then `make test`. The suite drives the page in a real browser, including a sweep of every page
  at phone, tablet and desktop widths, so layout and "undefined on screen" bugs show up.
- Tests run their own throwaway servers with the date pinned to 2026-11-12. They never touch `data/`.
- Adding a statement reader: copy the closest parser in `statements.py`, add it to `PARSERS`, and write a test with
  invented text shaped like the statement. `tests/test_data_check.py` shows how.
- Changing the look: `make shots` refreshes the README screenshots (example data only).
- Coverage is held at 100% for Python: `make coverage`.

## Before you commit

1. `make test` passes.
2. `python3 tools/privacy_scan.py --staged` is clean (the hook runs it too).
3. No attribution lines or personal details in the commit message.
