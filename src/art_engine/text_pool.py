import re
from typing import List, Tuple

def build_text_pool(
    name: str,
    years_experience: str | int | None = None,
    specialization: str | None = None,
    achievements_text: str | None = None
) -> List[Tuple[str, int]]:
    """
    Builds a weighted list of words/phrases: [(phrase, weight_priority)]
    Higher weight phrases are placed in prominent/dense areas.
    """
    pool: List[Tuple[str, int]] = []

    # Clean name
    clean_name = name.strip()
    if not clean_name.lower().startswith("dr.") and not clean_name.lower().startswith("dr "):
        formatted_name = f"Dr. {clean_name}"
    else:
        formatted_name = clean_name

    # Priority 1: Full name and name parts
    pool.append((formatted_name.upper(), 5))
    for part in clean_name.split():
        if len(part) > 2 and part.lower() not in ["dr", "dr."]:
            pool.append((part.upper(), 4))

    # Priority 2: Experience
    if years_experience is not None:
        exp_str = f"{years_experience} Years Experience"
        pool.append((exp_str.upper(), 4))
        pool.append((f"{years_experience}+ YRS", 3))

    # Priority 3: Specialization
    if specialization:
        spec_clean = specialization.strip()
        pool.append((spec_clean.upper(), 4))
        for spec_word in spec_clean.split():
            if len(spec_word) > 2:
                pool.append((spec_word.upper(), 3))

    # Priority 4: Achievements
    if achievements_text:
        # Split by punctuation / newlines
        items = re.split(r'[,;\n\.\-\|]+', achievements_text)
        for item in items:
            item_clean = item.strip()
            if len(item_clean) > 2:
                pool.append((item_clean.upper(), 3))
                for word in item_clean.split():
                    if len(word) > 3:
                        pool.append((word.upper(), 2))

    # Generic filler words if pool is small
    default_fillers = ["HEALING", "CARE", "COMPASSION", "SERVICE", "HEALTH", "EXCELLENCE", "TRUST", "DEDICATION", "WELLNESS"]
    for filler in default_fillers:
        pool.append((filler, 1))

    return pool
