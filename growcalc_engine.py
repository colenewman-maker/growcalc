from dataclasses import dataclass
from typing import Dict, Iterable, Optional, List
from datetime import datetime, timezone
import json
import numpy as np
from scipy.optimize import nnls

MACROS=("P","K","Ca","Mg","S")
P2O5_TO_P_DIVISOR=2.3
K2O_TO_K_DIVISOR=1.2

@dataclass(frozen=True)
class Fertilizer:
    key:str; name:str; analysis:Dict[str,float]; label:str; source_name:str; source_url:str; source_note:str
    verified_library_entry:bool=True; contains_calcium:bool=False; contains_phosphate:bool=False; contains_sulfate:bool=False
    @property
    def total_n_percent(self): return self.analysis.get("NO3_N",0)+self.analysis.get("NH4_N",0)

FERTILIZERS={
"calcium_nitrate":Fertilizer("calcium_nitrate","Calcium nitrate (YaraLiva Calcinit basis)",{"NO3_N":14.4,"NH4_N":1.1,"Ca":18.9},"15.5-0-0 + 18.9% Ca","Yara — YaraLiva Calcinit guaranteed analysis","https://www.yara.us/contentassets/d5795b868531401e9ce37f0adb6b54b2/yaraliva-calcinit-1200kg-glo_new.pdf","15.5% total N = 14.4% nitrate-N + 1.1% ammoniacal-N; 18.9% Ca.",contains_calcium=True),
"potassium_nitrate":Fertilizer("potassium_nitrate","Potassium nitrate",{"NO3_N":13.0,"K":46/K2O_TO_K_DIVISOR},"13-0-46","Haifa Group — Multi-K Classic","https://www.haifa-group.com/multi-k%E2%84%A2-classic","13% nitrate-N; 46% K2O converted to elemental K."),
"mkp":Fertilizer("mkp","Monopotassium phosphate (MKP)",{"P":52/P2O5_TO_P_DIVISOR,"K":34/K2O_TO_K_DIVISOR},"0-52-34","Penn State Extension","https://extension.psu.edu/hydroponics-systems-using-the-two-basic-equations-to-calculate-a-nutrient-solution-recipe/","P2O5 and K2O converted to elemental P and K.",contains_phosphate=True),
"magnesium_sulfate":Fertilizer("magnesium_sulfate","Magnesium sulfate (Epsom salt)",{"Mg":9.8,"S":12.9},"9.8% Mg + 12.9% S","Horticultural reference grade","","Typical heptahydrate analysis; verify actual product label.",contains_sulfate=True),
"ammonium_sulfate":Fertilizer("ammonium_sulfate","Ammonium sulfate",{"NH4_N":21.0,"S":24.0},"21-0-0 + 24% S","Standard fertilizer grade","","Verify product label.",contains_sulfate=True),
"ammonium_nitrate":Fertilizer("ammonium_nitrate","Ammonium nitrate",{"NO3_N":17.0,"NH4_N":17.0},"34-0-0","Oklahoma State University Extension","https://extension.okstate.edu/fact-sheets/oklahoma-soil-fertility-handbook-full","Approximately half nitrate-N and half ammoniacal-N.")}

def gallons_to_liters(g): return g*3.785411784
def p2o5_to_elemental_p(x): return x/P2O5_TO_P_DIVISOR
def k2o_to_elemental_k(x): return x/K2O_TO_K_DIVISOR

def custom_fertilizer_from_label(name,nitrate_n_percent=0,ammonium_n_percent=0,p2o5_percent=0,k2o_percent=0,ca_percent=0,mg_percent=0,s_percent=0):
    vals=[nitrate_n_percent,ammonium_n_percent,p2o5_percent,k2o_percent,ca_percent,mg_percent,s_percent]
    if any(v<0 or v>100 for v in vals): raise ValueError("Fertilizer analysis percentages must be between 0 and 100.")
    a={}
    for k,v in (("NO3_N",nitrate_n_percent),("NH4_N",ammonium_n_percent),("Ca",ca_percent),("Mg",mg_percent),("S",s_percent)):
        if v:a[k]=float(v)
    if p2o5_percent:a["P"]=p2o5_to_elemental_p(p2o5_percent)
    if k2o_percent:a["K"]=k2o_to_elemental_k(k2o_percent)
    return Fertilizer("custom",name or "Custom fertilizer",a,f"{nitrate_n_percent+ammonium_n_percent:g}-{p2o5_percent:g}-{k2o_percent:g}","User-entered product label","","Verify guaranteed analysis and nitrogen forms.",False,ca_percent>0,p2o5_percent>0,s_percent>0)

def ppm_contribution(m,pct,vol): return m*1000*(pct/100)/vol
def _pct(f,d): return f.total_n_percent if d=="TOTAL_N" else f.analysis.get(d,0)

def formulate(targets_ppm,volume_l,fertilizers,source_water_ppm=None,nitrogen_mode="total"):
    fs=list(fertilizers); water0=source_water_ppm or {}
    if volume_l<=0: raise ValueError("Final solution volume must be positive.")
    if not fs: raise ValueError("Select at least one fertilizer.")
    dims=(["NO3_N","NH4_N"] if nitrogen_mode=="split" else ["TOTAL_N"])+[n for n in MACROS if n in targets_ppm]
    targets={d:max(0,float(targets_ppm.get(d,0))) for d in dims}; water={d:max(0,float(water0.get(d,0))) for d in dims}
    req={d:max(0,targets[d]-water[d]) for d in dims}
    A=np.array([[ppm_contribution(1,_pct(f,d),volume_l) for f in fs] for d in dims],float)
    masses,res=nnls(A,np.array([req[d] for d in dims],float)); fert=A@masses; final=fert+np.array([water[d] for d in dims]); tv=np.array([targets[d] for d in dims]); err=final-tv
    details={d:{"target_ppm":float(tv[i]),"source_water_ppm":water[d],"fertilizer_needed_ppm":req[d],"fertilizer_supplied_ppm":float(fert[i]),"achieved_ppm":float(final[i]),"error_ppm":float(err[i]),"error_percent":float(err[i]/tv[i]*100) if tv[i] else None} for i,d in enumerate(dims)}
    water_ex=[d for d in dims if water[d]>targets[d]+1e-9]; unsup=[d for d in dims if req[d]>0 and all(_pct(f,d)<=0 for f in fs)]
    feasible=all(abs(v["error_ppm"])<=.5 or (v["error_percent"] is not None and abs(v["error_percent"])<=.5) for v in details.values()) and not water_ex and not unsup
    diag=[]
    if water_ex:diag.append("Source water already exceeds target for: "+", ".join(water_ex)+".")
    if unsup:diag.append("Selected fertilizers cannot supply: "+", ".join(unsup)+".")
    if feasible:diag.append("All requested nutrient targets are matched within current tolerance.")
    contrib={f.name:{d:ppm_contribution(float(masses[j]),_pct(f,d),volume_l) for d in dims} for j,f in enumerate(fs)}
    total=details["NO3_N"]["achieved_ppm"]+details["NH4_N"]["achieved_ppm"] if nitrogen_mode=="split" else details["TOTAL_N"]["achieved_ppm"]
    nitrate=(details["NO3_N"]["achieved_ppm"]/total*100 if total else None) if nitrogen_mode=="split" else None
    return {"created_utc":datetime.now(timezone.utc).isoformat(),"nitrogen_mode":nitrogen_mode,"volume_l":float(volume_l),"targets_ppm":targets,"source_water_ppm":water,"fertilizer_masses_g":{f.name:float(m) for f,m in zip(fs,masses)},"fertilizers":fs,"nutrients":details,"contributions_ppm":contrib,"total_n_final_ppm":total,"nitrate_fraction_percent":nitrate,"residual_norm":float(res),"feasible":bool(feasible),"diagnostics":diag}

def stock_solution_amounts(r,ratio,stock_l):
    if ratio<=1 or stock_l<=0: raise ValueError("Check injector ratio and stock volume.")
    scale=stock_l*ratio/r["volume_l"]; return {n:g*scale for n,g in r["fertilizer_masses_g"].items()}

def compatibility_warnings(fs,masses,concentrated_stock):
    if not concentrated_stock:return []
    active=[f for f in fs if masses.get(f.name,0)>1e-9]; c=any(f.contains_calcium for f in active); p=any(f.contains_phosphate for f in active); s=any(f.contains_sulfate for f in active); out=[]
    if c and p:out.append("Separate calcium-containing fertilizer(s) from phosphate-containing fertilizer(s) in concentrated stocks.")
    if c and s:out.append("Separate calcium-containing fertilizer(s) from sulfate-containing fertilizer(s) in concentrated stocks.")
    return out

def suggested_ab_split(fs,masses):
    A=[];B=[]
    for f in fs:
        g=masses.get(f.name,0)
        if g<=1e-9:continue
        (B if f.contains_phosphate or f.contains_sulfate else A).append((f.name,g))
    return {"A":A,"B":B}

def result_to_json(r,recipe_name="Untitled recipe"):
    x={k:v for k,v in r.items() if k!="fertilizers"}; x.update({"schema_version":"0.5","recipe_name":recipe_name,"fertilizers":[{"name":f.name,"label":f.label,"analysis_elemental_percent":f.analysis,"source_name":f.source_name,"source_url":f.source_url,"verified_library_entry":f.verified_library_entry} for f in r["fertilizers"]]}); return json.dumps(x,indent=2)

def build_math_steps(r):
    return ["1. Concentrations are elemental ppm (mg/L).","2. Source water is credited first: fertilizer requirement = max(target − source water, 0).","3. ppm = mass_g × 1000 × (elemental nutrient % / 100) ÷ final volume_L","4. GrowCalc solves coupled nutrient equations with non-negative least squares.","5. Final ppm = source-water ppm + fertilizer contributions."]
