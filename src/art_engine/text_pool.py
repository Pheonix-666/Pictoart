"""
text_pool.py — Weighted word/phrase pool builder for PICTOART typographic renderer.

Public API:

    build_text_pool(name, state=None, district=None, place=None, extra_filler=None)
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


# ── Public API ───────────────────────────────────────────────────────────────

def build_text_pool(
    name: str,
    state: Optional[str] = None,
    district: Optional[str] = None,
    place: Optional[str] = None,
    extra_filler: Optional[list] = None,
    # Legacy params kept for backward-compat but ignored
    specialization: Optional[str] = None,
    years_experience: Optional[int] = None,
    achievements_text: Optional[str] = None,
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
    "DR. NAME" full string              weight 10  (main identity phrase)
    Name without prefix                 weight  9
    Individual first / last name words  weight  7
    State name                          weight  6
    District name                       weight  5
    Place / city name                   weight  5
    Individual location words           weight  4
    Built-in BIG_WORDS                  weight  3
    Built-in SHORT_WORDS                weight  2
    Extra filler words                  weight  2
    """
    pool: dict[str, int] = {}

    def add(phrase: str, weight: int) -> None:
        phrase = _clean_upper(phrase)
        if not phrase:
            return
        if phrase not in pool or pool[phrase] < weight:
            pool[phrase] = weight

    # ── Doctor Name ───────────────────────────────────────────────────────────
    if name and name.strip():
        clean = _clean_upper(name)

        # Normalise "DR." prefix
        no_prefix = re.sub(r"^DR\.?\s*", "", clean).strip()

        if clean.startswith("DR.") or clean.startswith("DR "):
            dr_name = clean
        else:
            dr_name = f"DR. {clean}"

        add(dr_name, 10)            # "DR. RAJESH KUMAR"  — highest
        add(no_prefix, 9)           # "RAJESH KUMAR"
        add(f"DR. {no_prefix}", 10) # insurance: always have the prefixed form

        # Individual name tokens scatter at smaller sizes
        tokens = re.split(r"\s+", no_prefix)
        for token in tokens:
            token = token.strip(".,")
            if len(token) >= 3:     # skip bare initials like "P."
                add(token, 7)

    # ── Location — State ──────────────────────────────────────────────────────
    if state and state.strip():
        st = _clean_upper(state)
        add(st, 6)
        # Individual words in multi-word state names (e.g. "ANDHRA PRADESH")
        for w in st.split():
            if len(w) >= 4:
                add(w, 4)

    # ── Location — District ───────────────────────────────────────────────────
    if district and district.strip():
        dist = _clean_upper(district)
        add(dist, 5)
        for w in dist.split():
            if len(w) >= 4:
                add(w, 4)

    # ── Location — Place / City ───────────────────────────────────────────────
    if place and place.strip():
        pl = _clean_upper(place)
        add(pl, 5)
        for w in pl.split():
            if len(w) >= 4:
                add(w, 4)

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
