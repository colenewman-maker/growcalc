import streamlit as st
import pandas as pd
from io import StringIO
from growcalc_engine import *

st.set_page_config(page_title="GrowCalc",page_icon="🌱",layout="centered")
st.markdown("""<style>.block-container{max-width:980px;padding-top:1.3rem}.hero{padding:1.35rem;border:1px solid rgba(128,128,128,.23);border-radius:20px;margin-bottom:1.2rem}.title{font-size:2.15rem;font-weight:800}</style><div class='hero'><div>GrowCalc · V0.5 beta</div><div class='title'>Build nutrient recipes you can inspect.</div><p>Elemental fertilizer formulation for greenhouse, hydroponic, and horticultural workflows.</p></div>""",unsafe_allow_html=True)
st.warning("Beta tool: verify fertilizer labels, water analysis, solubility, injector calibration, final EC/pH, and crop response before production use.")
name=st.text_input("Recipe name","My nutrient recipe")
st.header("1 · Final solution")
c1,c2=st.columns(2)
with c1: unit=st.radio("Unit",["Gallons","Liters"],horizontal=True)
with c2: volume=st.number_input("Final solution volume",min_value=.01,value=100.0)
volume_l=gallons_to_liters(volume) if unit=="Gallons" else volume

st.header("2 · Nitrogen")
nmode=st.radio("Nitrogen target mode",["Total N only","Split nitrate-N / ammonium-N"])
targets={}
if nmode=="Total N only": targets["TOTAL_N"]=st.number_input("Total N target (ppm)",0.0,value=150.0); mode="total"
else:
    a,b=st.columns(2)
    with a: targets["NO3_N"]=st.number_input("Nitrate-N target (ppm)",0.0,value=140.0)
    with b: targets["NH4_N"]=st.number_input("Ammonium-N target (ppm)",0.0,value=10.0)
    mode="split"

st.header("3 · Other elemental targets")
defaults={"P":31.0,"K":210.0,"Ca":90.0,"Mg":24.0,"S":32.0}; cols=st.columns(3)
for i,n in enumerate(MACROS):
    with cols[i%3]: targets[n]=st.number_input(f"{n} target (ppm)",0.0,value=defaults[n],key="t"+n)

st.header("4 · Source water")
water={}
if st.toggle("Use water analysis"):
    if mode=="total": water["TOTAL_N"]=st.number_input("Total N in water",0.0,value=0.0)
    else:
        water["NO3_N"]=st.number_input("Nitrate-N in water",0.0,value=0.0); water["NH4_N"]=st.number_input("Ammonium-N in water",0.0,value=0.0)
    for n in MACROS: water[n]=st.number_input(f"{n} in water",0.0,value=0.0,key="w"+n)

st.header("5 · Fertilizers")
selected=[]
for key,f in FERTILIZERS.items():
    if st.checkbox(f"{f.name} — {f.label}",value=key in ("calcium_nitrate","potassium_nitrate","mkp","magnesium_sulfate"),key=key): selected.append(f)
with st.expander("＋ Add custom fertilizer"):
    pname=st.text_input("Product name"); a,b,c=st.columns(3)
    with a: no3=st.number_input("Nitrate-N %",0.,100.,0.); nh4=st.number_input("Ammoniacal-N %",0.,100.,0.); p=st.number_input("P₂O₅ %",0.,100.,0.)
    with b: k=st.number_input("K₂O %",0.,100.,0.); ca=st.number_input("Ca %",0.,100.,0.)
    with c: mg=st.number_input("Mg %",0.,100.,0.); s=st.number_input("S %",0.,100.,0.)
    if st.checkbox("Include custom product") and pname.strip(): selected.append(custom_fertilizer_from_label(pname,no3,nh4,p,k,ca,mg,s))

st.header("6 · Delivery")
delivery=st.radio("Recipe type",["Direct final-solution mix","Concentrated stock + injector"]); ratio=stock_l=None
if delivery.startswith("Concentrated"):
    ratio=st.number_input("Injector 1 : X",2.0,value=100.0); stock=st.number_input("Stock volume (L)",.01,value=4.0); stock_l=stock

if st.button("Calculate recipe",type="primary",use_container_width=True):
    try: st.session_state.r=formulate(targets,volume_l,selected,water,mode); st.session_state.name=name; st.session_state.delivery=delivery; st.session_state.ratio=ratio; st.session_state.stock_l=stock_l
    except ValueError as e: st.error(str(e))

if "r" in st.session_state:
    r=st.session_state.r; st.header("Result")
    (st.success if r["feasible"] else st.warning)("✓ Target profile matched within GrowCalc tolerance." if r["feasible"] else "Exact target profile not reached. Review diagnostics and audit trail.")
    for d in r["diagnostics"]: st.write("• "+d)
    amounts=pd.DataFrame([{"Fertilizer":n,"grams":round(g,2),"ounces":round(g/28.349523125,3)} for n,g in r["fertilizer_masses_g"].items()]); st.subheader("Fertilizer amounts"); st.dataframe(amounts,hide_index=True,use_container_width=True)
    rows=[]
    for n,v in r["nutrients"].items(): rows.append({"Nutrient":{"TOTAL_N":"Total N","NO3_N":"Nitrate-N","NH4_N":"Ammonium-N"}.get(n,n),"Target":round(v["target_ppm"],2),"Water":round(v["source_water_ppm"],2),"From fertilizer":round(v["fertilizer_supplied_ppm"],2),"Final":round(v["achieved_ppm"],2),"Error":round(v["error_ppm"],2)})
    st.subheader("Nutrient accounting"); st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    if r["nitrogen_mode"]=="split": st.metric("Final total N",f'{r["total_n_final_ppm"]:.1f} ppm')
    if st.session_state.delivery.startswith("Concentrated"):
        stock=stock_solution_amounts(r,st.session_state.ratio,st.session_state.stock_l); st.subheader("Stock recipe"); st.dataframe(pd.DataFrame([{"Fertilizer":n,"grams in stock":round(g,2)} for n,g in stock.items()]),hide_index=True)
        for w in compatibility_warnings(r["fertilizers"],stock,True): st.error(w)
    with st.expander("Show the math"):
        for x in build_math_steps(r): st.write(x)
        st.dataframe(pd.DataFrame(r["contributions_ppm"]).T.round(3),use_container_width=True)
    with st.expander("Sources and fertilizer assumptions"):
        for f in r["fertilizers"]: st.markdown(f"**{f.name}** — {f.source_name}"); st.caption(f.source_note); st.write(f.source_url) if f.source_url else None
    payload=result_to_json(r,st.session_state.name); csv=StringIO(); pd.DataFrame(rows).to_csv(csv,index=False)
    c1,c2=st.columns(2)
    with c1: st.download_button("Download recipe JSON",payload,"growcalc_recipe.json","application/json",use_container_width=True)
    with c2: st.download_button("Download nutrient CSV",csv.getvalue(),"growcalc_nutrients.csv","text/csv",use_container_width=True)

st.divider(); st.caption("GrowCalc V0.5 beta · Transparent math, source-linked assumptions, no AI-generated fertilizer doses.")
