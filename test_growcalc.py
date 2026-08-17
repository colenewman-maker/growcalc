import json
from growcalc_engine import *

def close(a,b,t=.05): assert abs(a-b)<=t,(a,b)

def test_calcinit():
 f=FERTILIZERS['calcium_nitrate']; close(f.analysis['NO3_N'],14.4,.001); close(f.analysis['NH4_N'],1.1,.001); close(f.total_n_percent,15.5,.001)
def test_kno3(): assert FERTILIZERS['potassium_nitrate'].analysis['NO3_N']==13.0
def test_split():
 r=formulate({'NO3_N':140,'NH4_N':10,'P':31,'K':210,'Ca':90,'Mg':24,'S':32},gallons_to_liters(100),[FERTILIZERS[k] for k in ('calcium_nitrate','potassium_nitrate','mkp','magnesium_sulfate','ammonium_nitrate')],nitrogen_mode='split'); assert r['total_n_final_ppm']>0
def test_sonneveld():
 r=formulate({'TOTAL_N':150,'P':31,'K':210,'Ca':90,'Mg':24,'S':32},gallons_to_liters(100),[FERTILIZERS[k] for k in ('calcium_nitrate','potassium_nitrate','mkp','magnesium_sulfate','ammonium_nitrate')]);
 for n,t in {'TOTAL_N':150,'P':31,'K':210,'Ca':90,'Mg':24}.items(): assert abs(r['nutrients'][n]['achieved_ppm']-t)<1
def test_custom():
 f=custom_fertilizer_from_label('Test',10,5,10,20,2,1,3); assert f.total_n_percent==15; close(f.analysis['P'],10/2.3,.0001); assert not f.verified_library_entry
def test_stock_warning():
 fs=[FERTILIZERS['calcium_nitrate'],FERTILIZERS['mkp'],FERTILIZERS['magnesium_sulfate']]; m={f.name:100 for f in fs}; assert len(compatibility_warnings(fs,m,True))==2
def test_json():
 r=formulate({'TOTAL_N':100,'Ca':100},100,[FERTILIZERS['calcium_nitrate']]); assert json.loads(result_to_json(r,'Test'))['schema_version']=='0.5'

if __name__=='__main__':
 fs=[v for k,v in globals().copy().items() if k.startswith('test_') and callable(v)]
 for f in fs:f()
 print(f'All GrowCalc V0.5 tests passed ({len(fs)} tests).')
