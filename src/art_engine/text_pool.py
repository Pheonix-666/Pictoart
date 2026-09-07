"""
text_pool.py — Weighted word/phrase pool builder for PICTOART typographic renderer.

Public API (matched to call sites in jobs.py and test_core.py):

    build_text_pool(name, specialization=None, years_experience=None,
                    achievements_text=None, extra_filler=None)
        -> list[tuple[str, int]]

Every entry is (UPPERCASE_PHRASE, weight). Higher weight = word appears more
often and at larger sizes in the rendered suit region.
"""
import re
from typing import Optional


from src.art_engine.words import BIG_WORDS, SHORT_WORDS


# ── Internal helpers ─────────────────────────────────────────────────────────

def _clean_upper(text: str) -> str:
    """Strip surrounding whitespace and upper-case."""
    return text.strip().upper()


def _split_achievements(achievements_text: str) -> list[str]:
    """
    Split a raw achievement string (comma / semicolon / pipe / newline
    delimited) into individual phrase tokens.
    """
    if not achievements_text or not achievements_text.strip():
        return []
    parts = re.split(r"[,;\|\n]+", achievements_text)
    return [p.strip().upper() for p in parts if p.strip()]


# ── Public API ───────────────────────────────────────────────────────────────

def build_text_pool(
    name: str,
    specialization: Optional[str] = None,
    years_experience: Optional[int] = None,
    achievements_text: Optional[str] = None,
    extra_filler: Optional[list] = None,
) -> list:
    """
    Build a weighted word pool for typographic portrait rendering.

    Returns
    -------
    list[tuple[str, int]]
        (UPPERCASE_PHRASE, weight) pairs sorted highest-weight first.
        Duplicates are collapsed, keeping the highest weight.

    Weighting scheme
    ----------------
    Full "DR. NAME" string              weight 10  (main identity phrase)
    Name without prefix                 weight  9
    Individual first / last name words  weight  7  (appear at small sizes too)
    Specialization                      weight  8
    Specialization individual words     weight  5  (multi-word specs)
    "{N} YEARS"                         weight  6
    "{N}+ YEARS OF EXCELLENCE"          weight  6
    "{N} YEARS OF EXPERIENCE"           weight  5
    Each achievement phrase             weight  4
    Words from long achievement phrases weight  3
    Built-in filler words               weight  2
    Extra filler words                  weight  2
    """
    # phrase -> weight mapping; keeps the highest weight seen
    pool: dict[str, int] = {}

    def add(phrase: str, weight: int) -> None:
        """Add (or update to max weight) a phrase into the pool."""
        phrase = _clean_upper(phrase)
        if not phrase:
            return
        if phrase not in pool or pool[phrase] < weight:
            pool[phrase] = weight

    # ── Name ─────────────────────────────────────────────────────────────────
    if name and name.strip():
        clean = _clean_upper(name)

        # Normalise DR. prefix
        no_prefix = re.sub(r"^DR\.?\s*", "", clean).strip()

        if clean.startswith("DR.") or clean.startswith("DR "):
            dr_name = clean
        else:
            dr_name = f"DR. {clean}"

        add(dr_name, 10)        # "DR. RAJESH KUMAR"  — highest
        add(no_prefix, 9)       # "RAJESH KUMAR"
        add(f"DR. {no_prefix}", 10)  # insurance: always have the prefixed form

        # Individual name tokens (first name, last name) at medium weight so
        # they scatter at smaller font sizes across the portrait
        tokens = re.split(r"\s+", no_prefix)
        for token in tokens:
            token = token.strip(".,")
            if len(token) >= 3:  # skip bare initials like "P."
                add(token, 7)

    # ── Specialization ────────────────────────────────────────────────────────
    if specialization and specialization.strip():
        spec = _clean_upper(specialization)
        add(spec, 8)

        # Sub-words of multi-word specializations (e.g. "INTERVENTIONAL CARDIOLOGY")
        spec_words = spec.split()
        for w in spec_words:
            if len(w) >= 4:
                add(w, 5)

    # ── Years experience ──────────────────────────────────────────────────────
    # (Omitted from suit artwork per design requirements)

    # ── Achievements ──────────────────────────────────────────────────────────
    if achievements_text:
        for phrase in _split_achievements(achievements_text):
            add(phrase, 4)
            # For long phrases also add individual words so they can appear at
            # small sizes without crowding
            words = phrase.split()
            if len(words) > 3:
                for w in words:
                    w = w.strip(".,+")
                    if len(w) >= 4:
                        add(w, 3)

    # ── Built-in word pools from words.py ────────────────────────────────────
    for word in BIG_WORDS:
        add(word, 3)

    for word in SHORT_WORDS:
        add(word, 2)

    # ── Extra filler ─────────────────────────────────────────────────────────
    if extra_filler:
        for item in extra_filler:
            if item and str(item).strip():
                add(str(item), 2)

    # Sort highest weight first (deterministic, helps debugging)
    result = sorted(pool.items(), key=lambda kv: -kv[1])
    return result
