"""Mapping between GrowGrid crop names and data.gov.in commodity names.

The data.gov.in AGMARKNET API uses specific commodity names that differ from
the crop names in our crop_master.csv. This module provides the mapping.
"""

from __future__ import annotations

# GrowGrid crop_name (lowercased) → data.gov.in commodity filter value
CROP_TO_DATAGOV_COMMODITY: dict[str, str] = {
    # Fruits
    "mango": "Mango",
    "guava": "Guava",
    "pomegranate": "Pomegranate",
    "lemon": "Lemon",
    "acid lime": "Lime",
    "dragon fruit": "Dragon Fruit",
    "banana": "Banana",
    "papaya": "Papaya",
    "amla (indian gooseberry)": "Amla(Indian Gooseberry)",
    "litchi": "Litchi",
    "grapes": "Grape",
    "coconut": "Coconut",
    "apple": "Apple",
    # Cereals
    "wheat": "Wheat",
    "maize": "Maize",
    "rice (paddy)": "Paddy(Dhan)(Common)",
    "barley": "Barley(Jau)",
    "sorghum (fodder)": "Sorghum(Jawar)",
    # Millets
    "bajra (pearl millet)": "Bajra(Pearl Millet/Cumbu)",
    "jowar (sorghum)": "Sorghum(Jawar)",
    "ragi (finger millet)": "Ragi(Finger Millet)",
    # Pulses
    "chickpea (gram)": "Bengal Gram(Gram)(Whole)",
    "arhar/tur (pigeonpea)": "Arhar (Tur/Red Gram)(Whole)",
    "lentil (masoor)": "Masoor Dal",
    "field pea (dry)": "Peas(Dry)",
    "moong (green gram)": "Green Gram (Moong)(Whole)",
    "urad (black gram)": "Black Gram (Urd Beans)(Whole)",
    # Oilseeds
    "mustard": "Mustard",
    "soybean": "Soyabean",
    "sunflower": "Sunflower",
    "sesame (til)": "Sesamum(Sesame,Gingelly,Til)",
    "groundnut": "Groundnut",
    # Vegetables
    "potato": "Potato",
    "onion": "Onion",
    "tomato": "Tomato",
    "okra (bhindi)": "Bhindi(Ladies Finger)",
    "brinjal (eggplant)": "Brinjal",
    "cabbage": "Cabbage",
    "cauliflower": "Cauliflower",
    "carrot": "Carrot",
    "radish": "Radish",
    "spinach (palak)": "Spinach",
    "coriander (leaf)": "Coriander(Leaves)",
    "cucumber (open-field)": "Cucumber(Kakadi)",
    "bitter gourd": "Bitter gourd",
    "bottle gourd": "Bottle gourd",
    "pumpkin": "Pumpkin",
    "watermelon": "Water Melon",
    "muskmelon": "Musk Melon",
    "french bean": "French Beans (Frasbean)",
    "green pea (vegetable)": "Peas(Green)",
    # Spices
    "turmeric": "Turmeric",
    "ginger": "Ginger(Green)",
    "garlic": "Garlic",
    "cumin": "Cumin Seed(Jeera)",
    "coriander (seed)": "Coriander Seed",
    "chilli": "Chillies(Green)",
    "fenugreek (methi)": "Methi(Fenugreek Leaves)",
    "fennel (saunf)": "Soanf",
    "ajwain (carom)": "Ajwan",
    # Commercial
    "sugarcane": "Sugarcane",
    "cotton": "Cotton",
    "potato (seed)": "Potato",
    "jute": "Jute",
    # Protected crops (map to same open-field commodity)
    "capsicum (protected)": "Capsicum",
    "cucumber (protected)": "Cucumber(Kakadi)",
    "tomato (protected)": "Tomato",
    "strawberry (protected)": "Strawberry",
    "lettuce (protected)": "Lettuce",
    # Flowers
    "marigold": "Marigold(Calcutta)",
    "rose (protected)": "Rose",
    "gerbera (protected)": "Gerbera",
}


def resolve_commodity_name(crop_name: str) -> str | None:
    """Resolve a GrowGrid crop name to a data.gov.in commodity name.

    Returns None if no mapping is found — caller should fall back to Tavily.
    """
    key = crop_name.lower().strip()
    if not key:
        return None

    # Exact match
    if key in CROP_TO_DATAGOV_COMMODITY:
        return CROP_TO_DATAGOV_COMMODITY[key]

    # Substring match: check if any mapping key is contained in the crop name
    for map_key, commodity in CROP_TO_DATAGOV_COMMODITY.items():
        if map_key in key or key in map_key:
            return commodity

    return None
