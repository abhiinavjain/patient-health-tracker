"""Regenerate protected_words.txt: real English words the spelling corrector must never 'fix' into a drug/condition.

    python -m app.nlp.build_protected_words [/usr/share/dict/words]

Run after changing the drug/condition vocabulary. Needs a system word list at build time only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from . import local


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/dict/words")
    local._protected_words.cache_clear()
    local.PROTECTED_WORDS_PATH.write_text("")  # build against an empty list
    local._protected_words.cache_clear()
    ex = local.LocalExtractor(action_model=False)
    words = {w.strip().lower() for w in src.read_text(errors="ignore").split() if re.fullmatch(r"[A-Za-z]{6,}", w.strip())}
    words -= ex._vocab
    protected = sorted(w for w in words if local.spelling_candidates(ex._vocab, w))
    local.PROTECTED_WORDS_PATH.write_text("\n".join(protected) + "\n")
    print(f"{len(protected)} protected words written to {local.PROTECTED_WORDS_PATH}")


if __name__ == "__main__":
    main()
