# GrowCalc V0.5 Beta

GrowCalc is a transparent fertilizer-formulation calculator for greenhouse,
hydroponic, and horticultural nutrient-solution workflows.

## Copyright and source-use notice

Copyright © 2026 Cole Newman / GrowCalc. All rights reserved.

The source code in this repository is publicly viewable for transparency, beta testing, and development history. **No open-source license is granted.** Except as permitted by applicable law and GitHub's Terms of Service, no permission is granted to copy, redistribute, modify, sublicense, sell, or commercially use GrowCalc's source code or other original project materials without prior written permission from the copyright holder.

Third-party references, fertilizer analyses, scientific publications, product names, trademarks, and other third-party materials remain the property of their respective owners and are subject to their own terms.

## V0.5 release features
- Guided Grow with source-backed crop starting profiles
- Total-N mode
- Advanced nitrate-N / ammonium-N targeting
- Source-water nutrient correction
- Verified/source-linked calcium nitrate and potassium nitrate analyses
- Custom fertilizer entry with nitrogen-form fields
- N, P, K, Ca, Mg, S formulation
- Direct-mix and injector/stock modes
- Conservative calcium/phosphate/sulfate concentrate warnings
- A/B separation suggestion
- Full calculation audit trail
- Per-fertilizer nutrient contribution table
- JSON and CSV export
- Automated validation tests
- Streamlit Community Cloud-ready repository layout

## Run locally
```bash
pip install -r requirements.txt
streamlit run growcalc_app.py
```

## Deploy on Streamlit Community Cloud
1. Put the files in this folder into a GitHub repository.
2. Connect that GitHub account to Streamlit Community Cloud.
3. Create a new app and select `growcalc_app.py` as the entrypoint.
4. Choose the desired `streamlit.app` subdomain.
5. Deploy.

No secrets, database, or external API keys are required for V0.5.

## Scientific / safety positioning
GrowCalc does deterministic math. It does **not** use a language model to invent
fertilizer doses.

This beta is still not a substitute for:
- fertilizer product labels,
- water testing,
- solubility checks,
- injector calibration,
- EC/pH measurements,
- crop-specific professional guidance,
- production-scale validation.

## Next validation priorities after launch
- Gather anonymous usability feedback
- Add more manufacturer-verified soluble fertilizer products
- Decide whether users actually want saved recipes/accounts
- Add micronutrient formulation only after equivalent validation work
- Consider alkalinity/acid tools as a separate calculator rather than hiding them here
