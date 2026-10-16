"""Real loopback HTTP checks against the activated service; no training or writes."""
import json,time,hashlib
from pathlib import Path
import httpx
E=Path(__file__).parent
audit=json.loads((E/'runtime_audit.json').read_text())
identity=json.loads((E/'activation_runtime.json').read_text())
with httpx.Client(base_url='http://127.0.0.1:8000',trust_env=False,timeout=10) as c:
    h=c.get('/health');h.raise_for_status()
    meta=c.get('/model/metadata');meta.raise_for_status();m=meta.json()
    assert m['available'] and m['model_sha256']==identity['model_sha256']
    assert m['model_type']==identity['actual_model_type']=='HistGradientBoostingClassifier'
    results=[]
    for row in audit['rows']:
        start=time.perf_counter();r=c.post('/predict',json={'features':row['features']});r.raise_for_status();b=r.json()
        assert b['available'] and b['model_type']==b['modelType']=='HistGradientBoostingClassifier'
        assert b['category']==row['candidate']['category'] and b['probabilities']==row['candidate']['probabilities']
        assert b['categoryLabel']==b['category_label'] and b['topFeatures']==b['top_features']
        results.append({'id':row['id'],'features':row['features'],'http_status':r.status_code,'prediction':b,'latency_ms':(time.perf_counter()-start)*1000,'matches_saved_candidate':True})
    raw=c.post('/predict',json={'raw':{'bmi':22.86,'age':30,'gender':'male','goal':'general_wellness','activity_level':'moderate','sleep_hours':5,'water_ml':2950,'water_target_ml':2950,'exercise_minutes':30,'steps':8000,'calories':2500,'calorie_target':2500,'stress_level':3}})
    assert raw.status_code==200 and raw.json()['category']=='sleep_focus'
    invalid=c.post('/predict',json={'features':{'bmi':22}})
    assert invalid.status_code==200 and invalid.json()['available'] is False
    repeated=c.post('/predict',json={'features':audit['rows'][0]['features']}).json()
    assert repeated==results[0]['prediction']
output={'url':'http://127.0.0.1:8000','identity':identity,'health':h.json(),'metadata':m,'rows':results,'raw_request':{'status':raw.status_code,'body':raw.json()},'invalid_request':{'status':invalid.status_code,'body':invalid.json()},'repeat_identical':True}
(E/'activation_api.json').write_text(json.dumps(output,indent=2))
print(json.dumps({'valid_profiles':len(results),'all_match_candidate':True,'identity':identity,'predictions':[{ 'id':r['id'],'category':r['prediction']['category'],'confidence':r['prediction']['confidence']} for r in results]},indent=2))
