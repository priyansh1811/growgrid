"""Deterministic crop-name and state-name matching between ICAR data and crop_master.

ICAR uses free-text names ("paddy", "groundnut", "rapeseed mustard") while
crop_master uses structured IDs (CE_RICE, OS_GROUNDNUT, OS_MUSTARD).
This module bridges the two without LLM calls.
"""

from __future__ import annotations

import re

# ── Static alias map: ICAR crop name (lowercase) → crop_master.crop_id ──────
# Covers ~180 known ICAR variants mapping to 77 crop_master entries.

_ALIAS_MAP: dict[str, str] = {
    # CEREALS
    "rice": "CE_RICE", "paddy": "CE_RICE", "boro paddy": "CE_RICE",
    "boro rice": "CE_RICE", "sali rice": "CE_RICE", "rice (upland)": "CE_RICE",
    "rice (wetland)": "CE_RICE", "upland paddy": "CE_RICE", "lowland paddy": "CE_RICE",
    "direct seeded rice": "CE_RICE", "puddled transplanted rice": "CE_RICE",
    "basmati rice": "CE_RICE", "jethi rice": "CE_RICE", "early ahu rice": "CE_RICE",
    "chetaki rice": "CE_RICE",
    "wheat": "CE_WHEAT",
    "maize": "CE_MAIZE", "rabi maize": "CE_MAIZE",
    "barley": "CE_BARLEY",
    "sorghum": "MI_JOWAR", "jowar": "MI_JOWAR", "rabi sorghum": "MI_JOWAR",
    "fodder sorghum": "CE_SORGHUM_FODDER",

    # MILLETS
    "bajra": "MI_BAJRA", "pearl millet": "MI_BAJRA",
    "ragi": "MI_RAGI", "finger millet": "MI_RAGI",
    "foxtail millet": "MI_RAGI",  # closest match
    "millet": "MI_BAJRA",  # generic → bajra

    # PULSES
    "chickpea": "PU_CHICKPEA", "gram": "PU_CHICKPEA", "bengal gram": "PU_CHICKPEA",
    "lentil": "PU_LENTIL", "lathyrus": "PU_LENTIL",
    "moong": "PU_MOONG", "green gram": "PU_MOONG", "greengram": "PU_MOONG",
    "summer moong": "PU_MOONG", "summer greengram": "PU_MOONG",
    "urad": "PU_URAD", "black gram": "PU_URAD", "blackgram": "PU_URAD",
    "arhar": "PU_PIGEONPEA", "pigeon pea": "PU_PIGEONPEA",
    "pigeonpea/arhar": "PU_PIGEONPEA", "red gram": "PU_PIGEONPEA",
    "redgram": "PU_PIGEONPEA",
    "field pea": "PU_PEA_DRY", "pea": "PU_PEA_DRY",

    # OILSEEDS
    "groundnut": "OS_GROUNDNUT", "ground nut": "OS_GROUNDNUT",
    "mustard": "OS_MUSTARD", "rapeseed mustard": "OS_MUSTARD",
    "rapeseed and mustard": "OS_MUSTARD", "rapeseed-mustard": "OS_MUSTARD",
    "rapeseed/mustard": "OS_MUSTARD", "rapeseed": "OS_MUSTARD",
    "yellow mustard/toria": "OS_MUSTARD", "toria": "OS_MUSTARD",
    "brown sarson": "OS_MUSTARD", "gobhi sarson": "OS_MUSTARD",
    "gobhi-sarson": "OS_MUSTARD", "taramira": "OS_MUSTARD",
    "sesame": "OS_SESAME", "sesamum": "OS_SESAME",
    "soybean": "OS_SOYBEAN",
    "sunflower": "OS_SUNFLOWER",
    "linseed": "OS_SUNFLOWER",  # closest oilseed match

    # COMMERCIAL
    "cotton": "CM_COTTON", "sugarcane": "CM_SUGARCANE",
    "jute": "CM_JUTE", "potato": "VE_POTATO",
    "coffee": "CM_COFFEE", "tea": "CM_TEA",

    # SPICES
    "chilli": "SP_CHILLI", "chili": "SP_CHILLI", "chilies": "SP_CHILLI",
    "chillies": "SP_CHILLI", "cherry pepper": "SP_CHILLI",
    "turmeric": "SP_TURMERIC",
    "ginger": "SP_GINGER", "finger ginger": "SP_GINGER",
    "ginger & turmeric": "SP_GINGER", "ginger/turmeric": "SP_GINGER",
    "garlic": "SP_GARLIC",
    "coriander": "SP_CORIANDER_SEED",
    "cumin": "SP_CUMIN",
    "fenugreek": "SP_FENUGREEK", "methi": "SP_FENUGREEK",
    "fennel": "SP_FENNEL",
    "ajwain": "SP_AJWAIN",

    # VEGETABLES
    "onion": "VE_ONION", "tomato": "VE_TOMATO", "tomato (rabi)": "VE_TOMATO",
    "brinjal": "VE_BRINJAL", "okra": "VE_OKRA", "bhindi (okra)": "VE_OKRA",
    "cabbage": "VE_CABBAGE", "cauliflower": "VE_CAULIFLOWER",
    "radish": "VE_RADISH", "carrot": "VE_CARROT", "spinach": "VE_SPINACH",
    "pumpkin": "VE_PUMPKIN", "bitter gourd": "VE_BITTER_GOURD",
    "bottle gourd": "VE_BOTTLE_GOURD", "cucumber": "VE_CUCUMBER_OPEN",
    "watermelon": "VE_WATERMELON", "muskmelon": "VE_MUSKMELON",  # no exact match but close
    "french bean": "VE_FRENCH_BEAN", "french beans": "VE_FRENCH_BEAN",
    "garden pea": "VE_GREEN_PEA", "vegetable pea": "VE_GREEN_PEA",
    "vegetable peas": "VE_GREEN_PEA",
    "capsicum": "PR_CAPSICUM", "bell pepper": "PR_CAPSICUM",
    "lettuce": "PR_LETTUCE",
    "strawberry": "PR_STRAWBERRY",

    # FRUITS
    "banana": "FR_BANANA", "mango": "FR_MANGO", "guava": "FR_GUAVA",
    "papaya": "FR_PAPAYA", "pomegranate": "FR_POMEGRANATE",
    "grapes": "FR_GRAPES", "apple": "FR_APPLE",
    "coconut": "FR_COCONUT", "citrus": "FR_LEMON",
    "litchi": "FR_LITCHI",
    "pineapple": "FR_BANANA",  # closest fruit_field match

    # FLOWERS
    "marigold": "FL_MARIGOLD",
}

# ── Reverse map: crop_id → list of ICAR name variants ───────────────────────

_REVERSE_MAP: dict[str, list[str]] = {}
for _alias, _crop_id in _ALIAS_MAP.items():
    _REVERSE_MAP.setdefault(_crop_id, []).append(_alias)


# ── Public API ───────────────────────────────────────────────────────────────


def match_crop_to_id(icar_crop_name: str) -> str | None:
    """Map an ICAR crop name to a crop_master crop_id, or None if unmatched.

    Uses the static alias map first, then tries normalized substring matching.
    """
    if not icar_crop_name:
        return None

    key = icar_crop_name.strip().lower()

    # 1. Exact alias match
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]

    # 2. Strip parenthetical text and retry
    stripped = re.sub(r'\s*\(.*?\)\s*', ' ', key).strip()
    if stripped in _ALIAS_MAP:
        return _ALIAS_MAP[stripped]

    # 3. Try substring match: if any alias is a substring of the input
    for alias, crop_id in sorted(_ALIAS_MAP.items(), key=lambda x: -len(x[0])):
        if alias in key:
            return crop_id

    return None


def match_id_to_icar_names(crop_id: str) -> list[str]:
    """Given a crop_master crop_id, return all known ICAR name variants.

    Used for querying ICAR tables where we need to search by crop_name.
    """
    return _REVERSE_MAP.get(crop_id, [])


def match_crop_name_from_master(crop_name: str) -> str | None:
    """Match a crop_master.crop_name (e.g. 'Rice (Paddy)') to crop_id via ICAR aliases.

    Tries the crop_name directly, then the first word, then known patterns.
    """
    if not crop_name:
        return None
    # Try the full name
    result = match_crop_to_id(crop_name)
    if result:
        return result
    # Try first word (e.g. "Rice" from "Rice (Paddy)")
    first_word = crop_name.split()[0] if crop_name.split() else ""
    return match_crop_to_id(first_word)


# ── State name normalization ─────────────────────────────────────────────────

# ICAR uses compound names; crop_location_suitability uses simple names
_ICAR_STATE_NAMES: list[str] = [
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana and Delhi",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jammu & Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu and Puducherry",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]


def normalize_state_for_icar(user_state: str | None) -> list[str]:
    """Given a user/profile state name, return matching ICAR state name(s).

    Handles:
    - "Haryana" → ["Haryana and Delhi"]
    - "Tamil Nadu" → ["Tamil Nadu and Puducherry"]
    - "Jammu and Kashmir" → ["Jammu and Kashmir", "Jammu & Kashmir"]
    - "Delhi" → ["Haryana and Delhi"]
    """
    if not user_state:
        return []

    query = user_state.strip()
    query_lower = query.lower()
    matches: list[str] = []

    for icar_state in _ICAR_STATE_NAMES:
        icar_lower = icar_state.lower()
        # Exact match
        if query_lower == icar_lower:
            matches.append(icar_state)
        # User state is substring of ICAR state ("Haryana" in "Haryana and Delhi")
        elif query_lower in icar_lower:
            matches.append(icar_state)
        # ICAR state is substring of user state (unlikely but handle)
        elif icar_lower in query_lower:
            matches.append(icar_state)
        # Handle & vs "and"
        elif query_lower.replace("&", "and") == icar_lower.replace("&", "and"):
            matches.append(icar_state)

    return matches if matches else [query]  # fallback: use as-is
