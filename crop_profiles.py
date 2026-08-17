CROP_PROFILES = {
    "Tomato": {
        "source": "UF/IFAS — Nutrient Solution Formulation for Hydroponic Tomatoes in Florida",
        "source_url": "https://ask.ifas.ufl.edu/publication/CV216",
        "note": "Florida greenhouse starting targets. Climate, irrigation frequency, cultivar, water quality, and production system can change appropriate concentrations.",
        "stages": {
            "Transplant to 1st fruit cluster": {"TOTAL_N":70,"P":50,"K":120,"Ca":150,"Mg":40,"S":50},
            "1st to 2nd fruit cluster": {"TOTAL_N":80,"P":50,"K":120,"Ca":150,"Mg":40,"S":50},
            "2nd to 3rd fruit cluster": {"TOTAL_N":100,"P":50,"K":150,"Ca":150,"Mg":40,"S":50},
            "3rd to 5th fruit cluster": {"TOTAL_N":120,"P":50,"K":150,"Ca":150,"Mg":50,"S":60},
            "5th fruit cluster to finish": {"TOTAL_N":150,"P":50,"K":200,"Ca":150,"Mg":50,"S":60},
        },
        "pH": "5.8–6.2",
    },
    "Bell pepper": {
        "source": "UF/IFAS — Growing Bell Peppers in Soilless Culture under Open Shade Structures",
        "source_url": "https://ask.ifas.ufl.edu/publication/HS368",
        "note": "Published soilless pepper trial targets; use as a starting point rather than a universal recipe.",
        "stages": {
            "Transplant to first flower": {"TOTAL_N":80,"P":50,"K":120,"Ca":150,"Mg":40,"S":50},
            "After first flower / fruiting": {"TOTAL_N":130,"P":50,"K":200,"Ca":150,"Mg":50,"S":60},
        },
        "pH": "About 5.5–6.5",
    },
    "Lettuce / leafy greens": {
        "source": "UF/IFAS — Fertilizer Management for Greenhouse Vegetables, Formula 3 (Leafy vegetables)",
        "source_url": "https://ask.ifas.ufl.edu/publication/CV265",
        "note": "Published leafy-vegetable profile. UF/IFAS lettuce guidance separately recommends monitoring EC, commonly about 1.4–1.8 mS/cm for small hydroponic systems.",
        "stages": {
            "Production": {"TOTAL_N":200,"P":62,"K":150,"Ca":210,"Mg":50,"S":70},
        },
        "pH": "About 6.0–7.0 in UF/IFAS small-system lettuce guidance",
        "EC": "About 1.4–1.8 mS/cm (small hydroponic lettuce guidance)",
    },
}
