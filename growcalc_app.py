import streamlit as st
import pandas as pd
from io import StringIO
from urllib.parse import quote
from growcalc_engine import *
from crop_profiles import CROP_PROFILES

st.set_page_config(page_title="GrowCalc", page_icon="🌱", layout="centered")

st.markdown("""
<style>
.block-container{max-width:920px;padding-top:2rem;padding-bottom:4rem}
.gc-hero{padding:1.7rem 1.8rem;border:1px solid rgba(128,128,128,.20);border-radius:22px;margin-bottom:1.25rem;background:linear-gradient(135deg,rgba(46,125,50,.10),rgba(46,125,50,.02))}
.gc-kicker{font-size:.78rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;opacity:.65}
.gc-title{font-size:2.35rem;font-weight:800;line-height:1.08;margin:.2rem 0 .45rem}
.gc-sub{font-size:1.02rem;opacity:.78;max-width:700px;margin:0}
.gc-step{font-size:.78rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;opacity:.55;margin-top:.35rem}
[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.18);padding:12px;border-radius:14px}
div[data-testid="stExpander"]{border-radius:14px}
</style>
<div class="gc-hero">
<div class="gc-kicker">GrowCalc · Public beta</div>
<div class="gc-title">Plant nutrition without the spreadsheet gymnastics.</div>
<p class="gc-sub">Use Guided Grow for a source-backed starting target, or Advanced Formulation when you already know the elemental ppm you want.</p>
</div>
""", unsafe_allow_html=True)

mode_choice = st.radio(
    "How do you want to use GrowCalc?",
    ["🌱 Guided Grow", "🧪 Advanced Formulation"],
    horizontal=True,
)

st.info("Beta: always verify fertilizer labels, water analysis, solubility, injector calibration, final EC/pH, and crop response before production use.")

# ---------- Shared helpers ----------
def choose_volume(prefix=""):
    a,b=st.columns(2)
    with a: unit=st.radio("Unit",["Gallons","Liters"],horizontal=True,key=prefix+"unit")
    with b: volume=st.number_input("Final solution volume",min_value=.01,value=5.0 if prefix else 100.0,key=prefix+"vol")
    return volume, unit, gallons_to_liters(volume) if unit=="Gallons" else volume

def choose_water(target_mode="total", prefix=""):
    water={}
    if st.toggle("I have a water analysis", key=prefix+"water_toggle"):
        st.caption("Enter nutrients already present in your source water. GrowCalc credits them toward the final target.")
        if target_mode=="total": water["TOTAL_N"]=st.number_input("Total N in water (ppm)",0.0,value=0.0,key=prefix+"wn")
        else:
            a,b=st.columns(2)
            with a: water["NO3_N"]=st.number_input("Nitrate-N in water (ppm)",0.0,value=0.0,key=prefix+"wno3")
            with b: water["NH4_N"]=st.number_input("Ammonium-N in water (ppm)",0.0,value=0.0,key=prefix+"wnh4")
        cols=st.columns(3)
        for i,n in enumerate(MACROS):
            with cols[i%3]: water[n]=st.number_input(f"{n} in water (ppm)",0.0,value=0.0,key=prefix+"w"+n)
    else:
        st.caption("No water analysis? GrowCalc assumes zero nutrient contribution from the source water.")
    return water

def choose_fertilizers(prefix="", beginner=False):
    selected=[]
    st.caption("Choose only products you actually have. Compare every analysis with your own fertilizer label.")
    defaults=("calcium_nitrate","potassium_nitrate","mkp","magnesium_sulfate","ammonium_nitrate") if beginner else ("calcium_nitrate","potassium_nitrate","mkp","magnesium_sulfate")
    for key,f in FERTILIZERS.items():
        if st.checkbox(f"{f.name} — {f.label}",value=key in defaults,key=prefix+key): selected.append(f)
    with st.expander("Add a custom fertilizer from its label"):
        pname=st.text_input("Product name",key=prefix+"pname")
        a,b,c=st.columns(3)
        with a:
            no3=st.number_input("Nitrate-N %",0.,100.,0.,key=prefix+"no3")
            nh4=st.number_input("Ammoniacal-N %",0.,100.,0.,key=prefix+"nh4")
            p=st.number_input("P₂O₅ %",0.,100.,0.,key=prefix+"p")
        with b:
            k=st.number_input("K₂O %",0.,100.,0.,key=prefix+"k")
            ca=st.number_input("Ca %",0.,100.,0.,key=prefix+"ca")
        with c:
            mg=st.number_input("Mg %",0.,100.,0.,key=prefix+"mg")
            s=st.number_input("S %",0.,100.,0.,key=prefix+"s")
        if st.checkbox("Include this custom product",key=prefix+"custom_on"):
            if pname.strip(): selected.append(custom_fertilizer_from_label(pname,no3,nh4,p,k,ca,mg,s))
            else: st.warning("Enter the product name before including it.")
    return selected

def show_result(r, recipe_name, delivery="Direct final-solution mix", ratio=None, stock_l=None, guided=False, profile=None):
    st.divider(); st.header("Your formulation")
    if r["feasible"]:
        st.success("Target profile matched within GrowCalc's current tolerance.")
    elif guided:
        st.warning("GrowCalc found the closest recipe possible with the fertilizers you selected. Some nutrient targets differ from the published starting profile; check the Nutrient check below.")
    else:
        st.warning("Exact target profile not reached. Review the diagnostics before using this formulation.")
    for d in r["diagnostics"]: st.write("• "+d)

    amounts=pd.DataFrame([{"Fertilizer":n,"grams":round(g,2),"ounces":round(g/28.349523125,3)} for n,g in r["fertilizer_masses_g"].items()])
    st.subheader("What to add")
    st.dataframe(amounts,hide_index=True,use_container_width=True)

    rows=[]; labels={"TOTAL_N":"Total N","NO3_N":"Nitrate-N","NH4_N":"Ammonium-N"}
    for n,v in r["nutrients"].items():
        rows.append({"Nutrient":labels.get(n,n),"Target":round(v["target_ppm"],2),"Water":round(v["source_water_ppm"],2),"From fertilizer":round(v["fertilizer_supplied_ppm"],2),"Final":round(v["achieved_ppm"],2),"Error":round(v["error_ppm"],2)})
    st.subheader("Nutrient check")
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

    if guided and profile:
        st.subheader("Practical checkpoints")
        st.write(f"**Published pH guidance:** {profile.get('pH','See source')}")
        if profile.get("EC"): st.write(f"**Published EC guidance:** {profile['EC']}")
        st.caption("EC is a useful overall strength check, but it does not prove that each individual nutrient is at its target concentration.")

    if r["nitrogen_mode"]=="split": st.metric("Final total N",f'{r["total_n_final_ppm"]:.1f} ppm')

    if delivery.startswith("Concentrated"):
        stock=stock_solution_amounts(r,ratio,stock_l)
        st.subheader("Stock recipe")
        st.dataframe(pd.DataFrame([{"Fertilizer":n,"grams in stock":round(g,2)} for n,g in stock.items()]),hide_index=True,use_container_width=True)
        warnings=compatibility_warnings(r["fertilizers"],stock,True)
        for w in warnings: st.error(w)
        if warnings:
            split=suggested_ab_split(r["fertilizers"],stock)
            a,b=st.columns(2)
            with a:
                st.markdown("**Suggested Stock A**")
                for n,g in split["A"]: st.write(f"• {n}: {g:.2f} g")
            with b:
                st.markdown("**Suggested Stock B**")
                for n,g in split["B"]: st.write(f"• {n}: {g:.2f} g")

    with st.expander("Show the math"):
        for x in build_math_steps(r): st.write(x)
        st.dataframe(pd.DataFrame(r["contributions_ppm"]).T.round(3),use_container_width=True)

    with st.expander("Sources and fertilizer assumptions"):
        if guided and profile:
            st.markdown(f"**Crop starting target:** {profile['source']}")
            st.write(profile["source_url"])
            st.caption(profile["note"])
        for f in r["fertilizers"]:
            st.markdown(f"**{f.name}** — {f.source_name}")
            st.caption(f.source_note)
            if f.source_url: st.write(f.source_url)

    payload=result_to_json(r,recipe_name); csv=StringIO(); pd.DataFrame(rows).to_csv(csv,index=False)
    st.subheader("Export")
    a,b=st.columns(2)
    with a: st.download_button("Download recipe JSON",payload,"growcalc_recipe.json","application/json",use_container_width=True)
    with b: st.download_button("Download nutrient CSV",csv.getvalue(),"growcalc_nutrients.csv","text/csv",use_container_width=True)

# ---------- Guided Grow ----------
if mode_choice.startswith("🌱"):
    st.markdown('<div class="gc-step">Step 1</div>', unsafe_allow_html=True)
    st.header("What are you growing?")
    crop=st.selectbox("Crop",list(CROP_PROFILES.keys()))
    profile=CROP_PROFILES[crop]
    stage=st.selectbox("Growth stage",list(profile["stages"].keys()))
    targets=profile["stages"][stage].copy()

    st.markdown(f"**GrowCalc starting target — {crop}, {stage}**")
    target_cols=st.columns(3)
    display=[("N",targets["TOTAL_N"]),("P",targets["P"]),("K",targets["K"]),("Ca",targets["Ca"]),("Mg",targets["Mg"]),("S",targets["S"])]
    for i,(n,v) in enumerate(display):
        with target_cols[i%3]: st.metric(n,f"{v:g} ppm")
    st.caption(profile["note"])
    with st.expander("Why this target?"):
        st.write(profile["source"]); st.write(profile["source_url"])

    st.markdown('<div class="gc-step">Step 2</div>', unsafe_allow_html=True)
    st.header("How much solution are you making?")
    volume,unit,volume_l=choose_volume("g_")

    st.markdown('<div class="gc-step">Step 3</div>', unsafe_allow_html=True)
    st.header("Do you know what's in your water?")
    water=choose_water("total","g_")

    st.markdown('<div class="gc-step">Step 4</div>', unsafe_allow_html=True)
    st.header("What fertilizers do you have?")
    selected=choose_fertilizers("g_",True)

    if st.button("Build my starting recipe",type="primary",use_container_width=True):
        try:
            st.session_state.guided_result=formulate(targets,volume_l,selected,water,"total")
            st.session_state.guided_name=f"{crop} — {stage}"
            st.session_state.guided_profile=profile
        except ValueError as e: st.error(str(e))

    if "guided_result" in st.session_state:
        show_result(st.session_state.guided_result,st.session_state.guided_name,guided=True,profile=st.session_state.guided_profile)

# ---------- Advanced ----------
else:
    name=st.text_input("Recipe name","My nutrient recipe")
    st.markdown('<div class="gc-step">Step 1</div>', unsafe_allow_html=True); st.header("Solution volume")
    volume,unit,volume_l=choose_volume("a_")

    st.markdown('<div class="gc-step">Step 2</div>', unsafe_allow_html=True); st.header("Elemental nutrient targets")
    nmode=st.radio("Nitrogen target mode",["Total N only","Split nitrate-N / ammonium-N"])
    targets={}
    if nmode=="Total N only":
        targets["TOTAL_N"]=st.number_input("Total N target (ppm)",0.0,value=150.0); calc_mode="total"
    else:
        a,b=st.columns(2)
        with a: targets["NO3_N"]=st.number_input("Nitrate-N target (ppm)",0.0,value=140.0)
        with b: targets["NH4_N"]=st.number_input("Ammonium-N target (ppm)",0.0,value=10.0)
        calc_mode="split"
    defaults={"P":31.0,"K":210.0,"Ca":90.0,"Mg":24.0,"S":32.0}; cols=st.columns(3)
    for i,n in enumerate(MACROS):
        with cols[i%3]: targets[n]=st.number_input(f"{n} target (ppm)",0.0,value=defaults[n],key="a_t"+n)

    st.markdown('<div class="gc-step">Step 3</div>', unsafe_allow_html=True); st.header("Source water")
    water=choose_water(calc_mode,"a_")

    st.markdown('<div class="gc-step">Step 4</div>', unsafe_allow_html=True); st.header("Fertilizers")
    selected=choose_fertilizers("a_",False)

    st.markdown('<div class="gc-step">Step 5</div>', unsafe_allow_html=True); st.header("Delivery method")
    delivery=st.radio("Recipe type",["Direct final-solution mix","Concentrated stock + injector"]); ratio=stock_l=None
    if delivery.startswith("Concentrated"):
        a,b=st.columns(2)
        with a: ratio=st.number_input("Injector ratio (1 : X)",2.0,value=100.0)
        with b: stock_l=st.number_input("Stock volume (L)",.01,value=4.0)

    if st.button("Calculate recipe",type="primary",use_container_width=True):
        try:
            st.session_state.advanced_result=formulate(targets,volume_l,selected,water,calc_mode)
            st.session_state.advanced_name=name; st.session_state.delivery=delivery; st.session_state.ratio=ratio; st.session_state.stock_l=stock_l
        except ValueError as e: st.error(str(e))
    if "advanced_result" in st.session_state:
        show_result(st.session_state.advanced_result,st.session_state.advanced_name,st.session_state.delivery,st.session_state.ratio,st.session_state.stock_l)

st.divider(); st.header("Help shape GrowCalc")
st.write("Tried it? Tell me what was useful, confusing, missing, or wrong. Grower feedback decides what gets built next.")
feedback_body=quote("GrowCalc feedback\n\nMode used: Guided / Advanced\nCrop (if Guided):\nWas it useful? Yes / Not yet\n\nWhat were you trying to calculate?\n\nWhat was confusing or missing?\n\nAnything you think is wrong?\n")
feedback_url=f"https://github.com/colenewman-maker/growcalc/issues/new?title=GrowCalc%20beta%20feedback&body={feedback_body}"
st.link_button("Send beta feedback",feedback_url,use_container_width=True)
st.caption("Feedback opens a GitHub issue. Please don't include private information or sensitive farm/business data.")
st.divider(); st.caption("GrowCalc Guided Beta + Advanced Formulation · Source-backed starting targets and deterministic fertilizer math.")
