#!/bin/sh
# Turn on the privacy checks for this clone. Run once after cloning.
cd "$(dirname "$0")/.." || exit 1
git config core.hooksPath .githooks
[ -f .privacy-terms.local ] || cp tools/privacy-terms.example .privacy-terms.local
echo "Privacy hooks are on. Put your own private terms (names, employer, street, ...) in .privacy-terms.local."
