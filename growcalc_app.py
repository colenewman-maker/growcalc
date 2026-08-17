import streamlit as st
import pandas as pd
from io import StringIO
from urllib.parse import quote
from growcalc_engine import *
from crop_profiles import CROP_PROFILES

st.set_page_config(page_title="GrowCalc", page_icon="🌱", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root { --gc-green:#3f7d55; --gc-soft:rgba(63,125,85,.10); }
.block-container{max-width:880px;padding-top:1.4rem;padding-bottom:4rem}
#MainMenu, footer {visibility:hidden}
.gc-nav{display:flex;align-items:center;justify-content:space-between;margin:.15rem 0 1.4rem;padding:.1rem .15rem}
.gc-brand{font-size:1.15rem;font-weight:800;letter-spacing:-.02em}.gc-brand span{opacity:.48;font-weight:600}
.gc-beta{font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;opacity:.55;border:1px solid rgba(128,128,128,.25);padding:.3rem .55rem;border-radius:999px}
.gc-hero{padding:2.25rem 2.25rem 2.05rem;border:1px solid rgba(128,128,128,.16);border-radius:28px;margin-bottom:1.4rem;background:linear-gradient(145deg,rgba(63,125,85,.13),rgba(63,125,85,.025) 55%,transparent);box-shadow:0 10px 35px rgba(0,0,0,.04)}
.gc-eyebrow{font-size:.75rem;font-weight:800;letter-spacing:.10em;text-transform:uppercase;opacity:.55;margin-bottom:.55rem}
.gc-title{font-size:2.75rem;font-weight:850;line-height:1.03;letter-spacing:-.045em;margin:0 0 .7rem;max-width:700px}
.gc-sub{font-size:1.08rem;line-height:1.55;opacity:.72;max-width:680px;margin:0}
.gc-section{font-size:.72rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;opacity:.48;margin-top:.8rem;margin-bottom:-.25rem}
.gc-note{padding:.9rem 1rem;border-radius:14px;background:rgba(128,128,128,.07);font-size:.9rem;line-height:1.45;opacity:.82;margin:.4rem 0 1rem}
.gc-profile{padding:1.05rem 1.1rem;border:1px solid rgba(128,128,128,.16);border-radius:18px;margin:.35rem 0 1.1rem;background:rgba(128,128,128,.025)}
.gc-profile-title{font-size:.8rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;opacity:.55;margin-bottom:.2rem}
.gc-profile-name{font-size:1.18rem;font-weight:750;margin-bottom:.25rem}
.gc-footer{text-align:center;opacity:.52;font-size:.78rem;line-height:1.5;padding-top:1.5rem}
[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.15);padding:13px 14px;border-radius:16px;background:rgba(128,128,128,.025)}
[data-testid="stMetricLabel"]{opacity:.65}
div[data-testid="stExpander"]{border-radius:15px;border-color:rgba(128,128,128,.15)}
div[data-testid="stDataFrame"]{border-radius:15px;overflow:hidden}
div.stButton > button[kind="primary"]{border-radius:13px;min-height:3.1rem;font-weight:750}
div.stButton > button:not([kind="primary"]), div[data-testid="stLinkButton"] a{border-radius:13px}
hr{opacity:.18;margin:2.2rem 0}
@media(max-width:650px){.gc-hero{padding:1.55rem 1.35rem;border-radius:22px}.gc-title{font-size:2.1rem}.gc-sub{font-size:1rem}.block-container{padding-left:1rem;padding-right:1rem}.gc-nav{margin-bottom:1rem}}
</style>
<div class="gc-nav"><div class="gc-brand">🌱 GrowCalc <span>/ nutrition tools</span></div><div class="gc-beta">Public beta</div></div>
<div class="gc-hero">
<div class="gc-eyebrow">Transparent plant nutrition</div>
<div class="gc-title">From crop to nutrient recipe, without the guesswork.</div>
<p class="gc-sub">Start with a published crop target or formulate directly from elemental ppm. GrowCalc keeps the calculation visible, sourced, and exportable.</p>
</div>
""", unsafe_allow_html=True)

mode_choice=st.segmented_control("Choose your workspace",["🌱 Guided Grow","🧪 Advanced Formulation"],default="🌱 Guided Grow",selection_mode="single")
if not mode_choice: mode_choice="🌱 Guided Grow"
st.caption("Guided Grow starts with published crop targets. Advanced Formulation gives you direct control over elemental ppm.")

with st.expander("Beta use & verification"):
    st.write("GrowCalc is a formulation aid, not a replacement for fertilizer labels, water testing, solubility checks, injector calibration, final EC/pH measurements, or crop observation. Verify a recipe before production use.")

def section(kicker,title):
    st.markdown(f'<div class="gc-section">{kicker}</div>',unsafe_allow_html=True); st.header(title)

def choose_volume(prefix="",guided=False):
    a,b=st.columns([1,1])
    with a: unit=st.radio("Unit",["Gallons","Liters"],horizontal=True,key=prefix+"unit")
    with b: volume=st.number_input("Solution volume",min_value=.01,value=5.0 if guided else 100.0,key=prefix+"vol")
    return volume,unit,gallons_to_liters(volume) if unit=="Gallons" else volume

def choose_water(target_mode="total",prefix=""):
    water={}
    if st.toggle("Use a source-water analysis",key=prefix+"water_toggle"):
        st.caption("Enter nutrients already present in the water. They will be credited toward the target.")
        if target_mode=="total": water["TOTAL_N"]=st.number_input("Total N in water (ppm)",0.0,value=0.0,key=prefix+"wn")
        else:
            a,b=st.columns(2)
            with a: water["NO3_N"]=st.number_input("Nitrate-N in water",0.0,value=0.0,key=prefix+"wno3")
            with b: water["NH4_N"]=st.number_input("Ammonium-N in water",0.0,value=0.0,key=prefix+"wnh4")
        cols=st.columns(3)
        for i,n in enumerate(MACROS):
            with cols[i%3]: water[n]=st.number_input(f"{n} in water",0.0,value=0.0,key=prefix+"w"+n)
    else: st.caption("No water test? Leave this off. GrowCalc will assume zero nutrient contribution from the source water.")
    return water

def choose_fertilizers(prefix="",beginner=False):
    selected=[]
    defaults=("calcium_nitrate","potassium_nitrate","mkp","magnesium_sulfate","ammonium_nitrate") if beginner else ("calcium_nitrate","potassium_nitrate","mkp","magnesium_sulfate")
    st.caption("Select products you have on hand. Always compare GrowCalc's analysis with your actual label.")
    for key,f in FERTILIZERS.items():
        if st.checkbox(f"{f.name}  ·  {f.label}",value=key in defaults,key=prefix+key): selected.append(f)
    with st.expander("＋ Add a fertilizer from my label"):
        pname=st.text_input("Product name",key=prefix+"pname")
        a,b,c=st.columns(3)
        with a:
            no3=st.number_input("Nitrate-N %",0.,100.,0.,key=prefix+"no3"); nh4=st.number_input("Ammoniacal-N %",0.,100.,0.,key=prefix+"nh4"); p=st.number_input("P₂O₅ %",0.,100.,0.,key=prefix+"p")
        with b:
            k=st.number_input("K₂O %",0.,100.,0.,key=prefix+"k"); ca=st.number_input("Ca %",0.,100.,0.,key=prefix+"ca")
        with c:
            mg=st.number_input("Mg %",0.,100.,0.,key=prefix+"mg"); s=st.number_input("S %",0.,100.,0.,key=prefix+"s")
        if st.checkbox("Include this product",key=prefix+"custom_on"):
            if pname.strip(): selected.append(custom_fertilizer_from_label(pname,no3,nh4,p,k,ca,mg,s))
            else: st.warning("Give the product a name first.")
    return selected

def show_result(r,recipe_name,delivery="Direct final-solution mix",ratio=None,stock_l=None,guided=False,profile=None):
    st.divider(); st.markdown('<div class="gc-section">Result</div>',unsafe_allow_html=True); st.header("Your nutrient recipe")
    if r["feasible"]: st.success("✓ Target profile matched within GrowCalc's current tolerance.")
    elif guided: st.warning("Closest achievable recipe with the selected fertilizers. Review the nutrient check for differences from the starting target.")
    else: st.warning("Exact target profile not reached. Review the diagnostics below.")
    for d in r["diagnostics"]:
        if "matched" not in d.lower(): st.caption(d)

    st.subheader("What to add")
    amounts=pd.DataFrame([{"Fertilizer":n,"Grams":round(g,2),"Ounces":round(g/28.349523125,3)} for n,g in r["fertilizer_masses_g"].items() if g>0.0001])
    st.dataframe(amounts,hide_index=True,use_container_width=True)

    rows=[]; labels={"TOTAL_N":"Total N","NO3_N":"Nitrate-N","NH4_N":"Ammonium-N"}
    for n,v in r["nutrients"].items(): rows.append({"Nutrient":labels.get(n,n),"Target":round(v["target_ppm"],1),"Water":round(v["source_water_ppm"],1),"Fertilizer":round(v["fertilizer_supplied_ppm"],1),"Final":round(v["achieved_ppm"],1),"Δ":round(v["error_ppm"],1)})
    st.subheader("Nutrient check")
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

    if guided and profile:
        st.subheader("Before you feed")
        a,b=st.columns(2)
        with a: st.metric("Published pH guidance",profile.get("pH","See source"))
        with b: st.metric("Published EC guidance",profile.get("EC","See source"))
        st.caption("EC checks overall solution strength; it does not confirm every individual nutrient concentration.")
    if r["nitrogen_mode"]=="split": st.metric("Final total N",f'{r["total_n_final_ppm"]:.1f} ppm')

    if delivery.startswith("Concentrated"):
        stock=stock_solution_amounts(r,ratio,stock_l); st.subheader("Stock recipe")
        st.dataframe(pd.DataFrame([{"Fertilizer":n,"Grams in stock":round(g,2)} for n,g in stock.items() if g>0.0001]),hide_index=True,use_container_width=True)
        warnings=compatibility_warnings(r["fertilizers"],stock,True)
        for w in warnings: st.error(w)
        if warnings:
            split=suggested_ab_split(r["fertilizers"],stock); a,b=st.columns(2)
            with a:
                st.markdown("**Stock A**")
                for n,g in split["A"]: st.write(f"{n} · {g:.2f} g")
            with b:
                st.markdown("**Stock B**")
                for n,g in split["B"]: st.write(f"{n} · {g:.2f} g")

    st.subheader("Inspect the recipe")
    tab1,tab2=st.tabs(["Calculation","Sources"])
    with tab1:
        for x in build_math_steps(r): st.write(x)
        st.caption("Per-fertilizer nutrient contribution (ppm)")
        st.dataframe(pd.DataFrame(r["contributions_ppm"]).T.round(3),use_container_width=True)
    with tab2:
        if guided and profile:
            st.markdown(f"**Crop starting target** · {profile['source']}"); st.write(profile["source_url"]); st.caption(profile["note"]); st.divider()
        for f in r["fertilizers"]:
            if r["fertilizer_masses_g"].get(f.name,0)>0.0001:
                st.markdown(f"**{f.name}**"); st.caption(f"{f.source_name} · {f.source_note}")
                if f.source_url: st.write(f.source_url)

    payload=result_to_json(r,recipe_name); csv=StringIO(); pd.DataFrame(rows).to_csv(csv,index=False)
    st.subheader("Take it with you")
    a,b=st.columns(2)
    with a: st.download_button("↓ Recipe JSON",payload,"growcalc_recipe.json","application/json",use_container_width=True)
    with b: st.download_button("↓ Nutrient CSV",csv.getvalue(),"growcalc_nutrients.csv","text/csv",use_container_width=True)

if mode_choice.startswith("🌱"):
    section("01 · Crop","Build from a published starting point")
    a,b=st.columns(2)
    with a: crop=st.selectbox("Crop",list(CROP_PROFILES.keys()))
    profile=CROP_PROFILES[crop]
    with b: stage=st.selectbox("Growth stage",list(profile["stages"].keys()))
    targets=profile["stages"][stage].copy()
    st.markdown(f'<div class="gc-profile"><div class="gc-profile-title">Selected profile</div><div class="gc-profile-name">{crop} · {stage}</div><div style="opacity:.68;font-size:.9rem">A source-backed starting target—not a universal prescription.</div></div>',unsafe_allow_html=True)
    cols=st.columns(6)
    for col,(n,v) in zip(cols,[("N",targets["TOTAL_N"]),("P",targets["P"]),("K",targets["K"]),("Ca",targets["Ca"]),("Mg",targets["Mg"]),("S",targets["S"])]):
        with col: st.metric(n,f"{v:g}")
    with st.expander("About this crop target"):
        st.write(profile["note"]); st.markdown(f"**Source:** {profile['source']}"); st.write(profile["source_url"])

    section("02 · Volume","How much solution are you making?")
    volume,unit,volume_l=choose_volume("g_",True)
    section("03 · Water","Account for what's already there")
    water=choose_water("total","g_")
    section("04 · Products","Choose the fertilizers you have")
    selected=choose_fertilizers("g_",True)
    st.markdown("<br>",unsafe_allow_html=True)
    if st.button("Build my recipe →",type="primary",use_container_width=True):
        try:
            st.session_state.guided_result=formulate(targets,volume_l,selected,water,"total"); st.session_state.guided_name=f"{crop} — {stage}"; st.session_state.guided_profile=profile
        except ValueError as e: st.error(str(e))
    if "guided_result" in st.session_state: show_result(st.session_state.guided_result,st.session_state.guided_name,guided=True,profile=st.session_state.guided_profile)
else:
    section("Advanced workspace","Formulate directly from elemental targets")
    name=st.text_input("Recipe name","My nutrient recipe")
    volume,unit,volume_l=choose_volume("a_",False)
    st.subheader("Elemental targets")
    nmode=st.radio("Nitrogen target",["Total N only","Split nitrate-N / ammonium-N"],horizontal=True); targets={}
    if nmode=="Total N only": targets["TOTAL_N"]=st.number_input("Total N (ppm)",0.0,value=150.0); calc_mode="total"
    else:
        a,b=st.columns(2)
        with a: targets["NO3_N"]=st.number_input("Nitrate-N (ppm)",0.0,value=140.0)
        with b: targets["NH4_N"]=st.number_input("Ammonium-N (ppm)",0.0,value=10.0)
        calc_mode="split"
    defaults={"P":31.,"K":210.,"Ca":90.,"Mg":24.,"S":32.}; cols=st.columns(5)
    for col,n in zip(cols,MACROS):
        with col: targets[n]=st.number_input(n,0.0,value=defaults[n],key="a_t"+n)
    st.subheader("Source water"); water=choose_water(calc_mode,"a_")
    st.subheader("Fertilizers"); selected=choose_fertilizers("a_",False)
    st.subheader("Delivery")
    delivery=st.radio("Recipe type",["Direct final-solution mix","Concentrated stock + injector"],horizontal=True); ratio=stock_l=None
    if delivery.startswith("Concentrated"):
        a,b=st.columns(2)
        with a: ratio=st.number_input("Injector ratio (1 : X)",2.0,value=100.0)
        with b: stock_l=st.number_input("Stock volume (L)",.01,value=4.0)
    st.markdown("<br>",unsafe_allow_html=True)
    if st.button("Calculate formulation →",type="primary",use_container_width=True):
        try:
            st.session_state.advanced_result=formulate(targets,volume_l,selected,water,calc_mode); st.session_state.advanced_name=name; st.session_state.delivery=delivery; st.session_state.ratio=ratio; st.session_state.stock_l=stock_l
        except ValueError as e: st.error(str(e))
    if "advanced_result" in st.session_state: show_result(st.session_state.advanced_result,st.session_state.advanced_name,st.session_state.delivery,st.session_state.ratio,st.session_state.stock_l)

st.divider(); section("Public beta","Help us make GrowCalc useful")
st.write("Used GrowCalc for a real or test recipe? Tell us what felt useful, confusing, missing, or wrong. That feedback decides what gets built next.")
feedback_body=quote("GrowCalc beta feedback\n\nMode: Guided / Advanced\nCrop (if Guided):\nWas it useful? Yes / Not yet\n\nWhat were you trying to calculate?\n\nWhat was confusing or missing?\n\nAnything you think is wrong?\n")
feedback_url=f"https://github.com/colenewman-maker/growcalc/issues/new?title=GrowCalc%20beta%20feedback&body={feedback_body}"
st.link_button("Send beta feedback ↗",feedback_url,use_container_width=True)
st.caption("Opens a GitHub issue. Don't include private information or sensitive farm/business data.")
st.markdown('<div class="gc-footer">GrowCalc · Public Beta<br>Deterministic fertilizer math · source-backed crop targets · transparent assumptions</div>',unsafe_allow_html=True)
