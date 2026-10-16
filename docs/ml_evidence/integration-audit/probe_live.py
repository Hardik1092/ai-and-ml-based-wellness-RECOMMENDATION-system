"""Read-only public health checks and synthetic inference; no authenticated data access."""
import hashlib,json,sys
from pathlib import Path
import httpx,joblib,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'ai-ml'))
from app.features.engineering import FEATURE_NAMES,build_feature_row
from app.preprocessing.pipeline import impute_raw
modelpath=ROOT/'ai-ml/models/cep-20k-v1/model.pkl'
model=joblib.load(modelpath)
report={'model_path':str(modelpath),'sha256':hashlib.sha256(modelpath.read_bytes()).hexdigest(),'type':type(model).__name__,'features':list(model.feature_names_in_),'classes':list(model.classes_),'http':[],'predictions':[]}
with httpx.Client(trust_env=False,timeout=8) as c:
    for url in ['http://127.0.0.1:8000/health','http://127.0.0.1:8000/model/metadata','http://127.0.0.1:5000/api/health','http://127.0.0.1:5000/api/ml/explanation','http://127.0.0.1:5000/api/recommendations/nutrition','http://localhost:5173']:
        try:
            r=c.get(url);item={'url':url,'status':r.status_code}
            if '8000' in url or url.endswith('/api/health'):item['body']=r.json()
            if url.endswith(':5173'):item['vite_page']='@vite/client' in r.text
            report['http'].append(item)
        except httpx.HTTPError as e:report['http'].append({'url':url,'error':type(e).__name__})
    baseline={'bmi':22.86,'age':30,'gender':'male','activity_level':'moderate','goal':'general_wellness','sleep_hours':8,'water_ml':2950,'water_target_ml':2950,'exercise_minutes':30,'steps':8000,'calories':2556,'calorie_target':2556,'stress_level':3}
    for name,changes in [('baseline',{}),('sleep_zero',{'sleep_hours':0}),('water_zero',{'water_ml':0}),('calories_zero',{'calories':0}),('low_movement',{'exercise_minutes':0,'steps':1000}),('fitness',{'goal':'improve_fitness'})]:
        raw={**baseline,**changes};f=build_feature_row(impute_raw(raw));df=pd.DataFrame([f],columns=FEATURE_NAMES)
        expected={str(k):round(float(v),4) for k,v in zip(model.classes_,model.predict_proba(df)[0])}
        er=c.post('http://127.0.0.1:8000/predict',json={'features':f});rr=c.post('http://127.0.0.1:8000/predict',json={'raw':raw})
        b,rb=er.json(),rr.json()
        report['predictions'].append({'name':name,'features':f,'engineered_status':er.status_code,'engineered':b,'raw_status':rr.status_code,'raw':rb,'matches_saved_artifact':b.get('probabilities')==expected,'raw_matches_current_preprocessing':rb.get('probabilities')==expected})
Path(__file__).with_name('live.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'artifact_sha256':report['sha256'],'engineered_matches':sum(r['matches_saved_artifact'] for r in report['predictions']),'raw_matches_current':sum(r['raw_matches_current_preprocessing'] for r in report['predictions']),'cases':len(report['predictions'])}))
