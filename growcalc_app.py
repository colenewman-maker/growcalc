import streamlit as st
import pandas as pd
from io import StringIO
from urllib.parse import quote
from growcalc_engine import *

st.set_page_config(page_title="GrowCalc", page_icon="🌱", layout="centered")

st.markdown("""
<style>
.block-container{max-width:900px;padding-top:2rem;padding-bottom:4rem}
.gc-hero{padding:1.7rem 1.8rem;border:1px solid rgba(128,128,128,.20);border-radius:22px;margin-bottom:1.25rem;background:linear-gradient(135deg,rgba(46,125,50,.09),rgba(46,125,50,.02))}
.gc-kicker{font-size:.78rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;opacity:.65}
.gc-title{font-size:2.35rem;font-weight:800;line-height:1.08;margin:.2rem 0 .45rem}
.gc-sub{font-size:1.02rem;opacity:.78;max-width:700px;margin:0}
.gc-step{font-size:.78rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;opacity:.55;margin-top:.35rem}
[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.18);padding:12px;border-radius:14px}
div[data-testid="stExpander"]{border-radius:14px}
</style>
<div class="gc-hero">
<div class="gc-kicker">GrowCalc · Public beta</div>
<div class="gc-title">Build a nutrient recipe you can actually inspect.</div>
<p class="gc-sub">Enter your targets, water analysis, and fertilizer products. GrowCalc solves the formulation and shows exactly how it got there.</p>
</div>
""", unsafe_allow_html=True)

st.info("Beta: verify fertilizer labels, water analysis, solubility, injector calibration, final EC/pH, and crop response before production use.")

name = st.text_input("Recipe name", "My nutrient recipe")

st.markdown('<div class="gc-step">Step 1</div>', unsafe_allow_html=True)
st.header("Solution volume")
c1,c2=st.columns(2)
with c1: unit=st.radio("Unit",["Gallons","Liters"],horizontal=True)
with c2: volume=st.number_input("Final solution volume",min_value=.01,value=100.0)
volume_l=gallons_to_liters(volume) if unit=="Gallons" else volume

st.markdown('<div class="gc-step">Step 2</div>', unsafe_allow_html=True)
st.header("Nutrient targets")
nmode=st.radio("Nitrogen target mode",["Total N only","Split nitrate-N / ammonium-N"],help="Total N is simplest. Split mode is useful when you need to control nitrogen form.")
targets={}
if nmode=="Total N only":
    targets["TOTAL_N"]=st.number_input("Total N target (ppm)",0.0,value=150.0)
    mode="total"
else:
    a,b=st.columns(2)
    with a: targets["NO3_N"]=st.number_input("Nitrate-N target (ppm)",0.0,value=140.0)
    with b: targets["NH4_N"]=st.number_input("Ammonium-N target (ppm)",0.0,value=10.0)
    mode="split"
    total_n=targets["NO3_N"]+targets["NH4_N"]
    st.caption(f"Total nitrogen target: {total_n:.1f} ppm")

defaults={"P":31.0,"K":210.0,"Ca":90.0,"Mg":24.0,"S":32.0}
cols=st.columns(3)
for i,n in enumerate(MACROS):
    with cols[i%3]: targets[n]=st.number_input(f"{n} target (ppm)",0.0,value=defaults[n],key="t"+n)

st.markdown('<div class="gc-step">Step 3</div>', unsafe_allow_html=True)
st.header("Source water")
water={}
use_water=st.toggle("I have a water analysis")
if use_water:
    st.caption("Enter nutrients already present in your source water. GrowCalc credits them toward the final target.")
    if mode=="total": water["TOTAL_N"]=st.number_input("Total N in water (ppm)",0.0,value=0.0)
    else:
        a,b=st.columns(2)
        with a: water["NO3_N"]=st.number_input("Nitrate-N in water (ppm)",0.0,value=0.0)
        with b: water["NH4_N"]=st.number_input("Ammonium-N in water (ppm)",0.0,value=0.0)
    cols=st.columns(3)
    for i,n in enumerate(MACROS):
        with cols[i%3]: water[n]=st.number_input(f"{n} in water (ppm)",0.0,value=0.0,key="w"+n)
else:
    st.caption("No water analysis? Leave this off and GrowCalc assumes zero nutrient contribution from the source water.")

st.markdown('<div class="gc-step">Step 4</div>', unsafe_allow_html=True)
st.header("Fertilizers")
st.caption("Choose only products you actually have. Source-linked products use the analysis shown in GrowCalc; always compare it with your own label.")
selected=[]
for key,f in FERTILIZERS.items():
    if st.checkbox(f"{f.name} — {f.label}",value=key in ("calcium_nitrate","potassium_nitrate","mkp","magnesium_sulfate"),key=key): selected.append(f)

with st.expander("Add a custom fertilizer from its label"):
    pname=st.text_input("Product name")
    a,b,c=st.columns(3)
    with a:
        no3=st.number_input("Nitrate-N %",0.,100.,0.)
        nh4=st.number_input("Ammoniacal-N %",0.,100.,0.)
        p=st.number_input("P₂O₅ %",0.,100.,0.)
    with b:
        k=st.number_input("K₂O %",0.,100.,0.)
        ca=st.number_input("Ca %",0.,100.,0.)
    with c:
        mg=st.number_input("Mg %",0.,100.,0.)
        s=st.number_input("S %",0.,100.,0.)
    if st.checkbox("Include this custom product"):
        if pname.strip(): selected.append(custom_fertilizer_from_label(pname,no3,nh4,p,k,ca,mg,s))
        else: st.warning("Enter the product name before including it.")

st.markdown('<div class="gc-step">Step 5</div>', unsafe_allow_html=True)
st.header("Delivery method")
delivery=st.radio("Recipe type",["Direct final-solution mix","Concentrated stock + injector"])
ratio=stock_l=None
if delivery.startswith("Concentrated"):
    a,b=st.columns(2)
    with a: ratio=st.number_input("Injector ratio (1 : X)",2.0,value=100.0)
    with b: stock_l=st.number_input("Stock volume (L)",.01,value=4.0)
    st.caption("GrowCalc will scale the direct formulation into the selected stock concentration and screen for basic concentrate incompatibilities.")

if st.button("Calculate recipe",type="primary",use_container_width=True):
    try:
        st.session_state.r=formulate(targets,volume_l,selected,water,mode)
        st.session_state.name=name
        st.session_state.delivery=delivery
        st.session_state.ratio=ratio
        st.session_state.stock_l=stock_l
    except ValueError as e:
        st.error(str(e))

if "r" in st.session_state:
    r=st.session_state.r
    st.divider()
    st.header("Your formulation")
    if r["feasible"]:
        st.success("Target profile matched within GrowCalc's current tolerance.")
    else:
        st.warning("Exact target profile not reached. Review the diagnostics before using this formulation.")
    for d in r["diagnostics"]: st.write("• "+d)

    amounts=pd.DataFrame([{"Fertilizer":n,"grams":round(g,2),"ounces":round(g/28.349523125,3)} for n,g in r["fertilizer_masses_g"].items()])
    st.subheader("What to add")
    st.dataframe(amounts,hide_index=True,use_container_width=True)

    rows=[]
    labels={"TOTAL_N":"Total N","NO3_N":"Nitrate-N","NH4_N":"Ammonium-N"}
    for n,v in r["nutrients"].items():
        rows.append({"Nutrient":labels.get(n,n),"Target":round(v["target_ppm"],2),"Water":round(v["source_water_ppm"],2),"From fertilizer":round(v["fertilizer_supplied_ppm"],2),"Final":round(v["achieved_ppm"],2),"Error":round(v["error_ppm"],2)})
    st.subheader("Nutrient check")
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

    if r["nitrogen_mode"]=="split": st.metric("Final total N",f'{r["total_n_final_ppm"]:.1f} ppm')

    if st.session_state.delivery.startswith("Concentrated"):
        stock=stock_solution_amounts(r,st.session_state.ratio,st.session_state.stock_l)
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
        for f in r["fertilizers"]:
            st.markdown(f"**{f.name}** — {f.source_name}")
            st.caption(f.source_note)
            if f.source_url: st.write(f.source_url)

    payload=result_to_json(r,st.session_state.name)
    csv=StringIO(); pd.DataFrame(rows).to_csv(csv,index=False)
    st.subheader("Export")
    c1,c2=st.columns(2)
    with c1: st.download_button("Download recipe JSON",payload,"growcalc_recipe.json","application/json",use_container_width=True)
    with c2: st.download_button("Download nutrient CSV",csv.getvalue(),"growcalc_nutrients.csv","text/csv",use_container_width=True)

st.divider()
st.header("Help shape GrowCalc")
st.write("If you tried the calculator, I'd genuinely like to know what was useful, confusing, missing, or wrong. This is an early beta and grower feedback will decide what gets built next.")
feedback_body=quote("GrowCalc feedback\n\nWas it useful? Yes / Not yet\n\nWhat were you trying to calculate?\n\nWhat was confusing or missing?\n\nAnything you think is wrong?\n")
feedback_url=f"https://github.com/colenewman-maker/growcalc/issues/new?title=GrowCalc%20beta%20feedback&body={feedback_body}"
st.link_button("Send beta feedback",feedback_url,use_container_width=True)
st.caption("Feedback opens a GitHub issue. Please don't include private information or sensitive farm/business data.")

st.divider()
st.caption("GrowCalc V0.5 beta · Deterministic fertilizer math with source-linked assumptions. Verify before production use.")
