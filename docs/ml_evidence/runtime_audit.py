"""Inspect saved models and exercise FastAPI in-process; never start/train/activate a service."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai-ml'))
import joblib,pandas as pd,httpx
from fastapi.testclient import TestClient
from app.config import MODEL_PATH,METADATA_PATH,ML_ENABLED
from app.main import app
from app.prediction import predictor
from app.features.engineering import FEATURE_NAMES,build_feature_row
from app.preprocessing.pipeline import impute_raw
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=json.loads(subprocess.run(['node',str(Path(__file__).with_name('runtime_profiles.cjs'))],cwd=ROOT,capture_output=True,text=True,check=True).stdout)
report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'scope':'Isolated in-process FastAPI TestClient, not an already running server','backend':inputs['backend'],'ml_enabled':ML_ENABLED,'features':FEATURE_NAMES,'live_requests':[]}
with httpx.Client(timeout=3,trust_env=False) as client:
    for url in [inputs['backend']['mlServiceUrl']+'/health',inputs['backend']['mlServiceUrl']+'/model/metadata','http://127.0.0.1:5000/api/health','http://127.0.0.1:5173/']:
        try:
            r=client.get(url); report['live_requests'].append({'url':url,'status':r.status_code})
        except httpx.HTTPError as e: report['live_requests'].append({'url':url,'error_type':type(e).__name__,'error':str(e)})
runtime,meta=predictor.load_model()
assert runtime is not None
candidate_path=ROOT/'ai-ml/models/cep-20k-v1/model.pkl'
candidate=joblib.load(candidate_path)
report['artifacts']={}
for name,path,model in [('configured_runtime',MODEL_PATH,runtime),('latest_training',candidate_path,candidate)]:
    report['artifacts'][name]={'path':str(path.resolve()),'sha256':sha(path),'type':type(model).__name__,'features':list(model.feature_names_in_),'classes':list(model.classes_),'feature_order_matches':list(model.feature_names_in_)==FEATURE_NAMES}
report['runtime_metadata']={'path':str(METADATA_PATH.resolve()),'sha256':sha(METADATA_PATH),'declared_type':meta.get('model_type'),'has_model_checksum':bool(meta.get('model_sha256'))}
report['same_path']=MODEL_PATH.resolve()==candidate_path.resolve()
report['same_hash']=sha(MODEL_PATH)==sha(candidate_path)
report['legacy_fallback_sha256']=sha(ROOT/'ai-ml/models/random_forest_model.joblib')
report['rows']=[]
with TestClient(app) as client:
    schema=client.get('/openapi.json').json()
    Path(__file__).with_name('runtime_openapi.json').write_text(json.dumps(schema,indent=2),encoding='utf8')
    for row in inputs['rows']:
        t=time.perf_counter();res=client.post('/predict',json={'features':row['features']});latency=(time.perf_counter()-t)*1000
        body=res.json();frame=pd.DataFrame([row['features']],columns=FEATURE_NAMES)
        direct={str(c):round(float(p),4) for c,p in zip(runtime.classes_,runtime.predict_proba(frame)[0])}
        cp={str(c):round(float(p),4) for c,p in zip(candidate.classes_,candidate.predict_proba(frame)[0])}
        raw={'bmi':row['metrics']['bmi'],'age':row['profile']['age'],'gender':row['profile']['gender'],'goal':row['profile']['goal'],'activity_level':row['profile']['activity_level'],'sleep_hours':row['summary']['avg_sleep'],'water_ml':row['summary']['avg_water'],'water_target_ml':row['metrics']['water_target_ml'],'exercise_minutes':row['summary']['avg_exercise_minutes'],'steps':row['summary']['avg_steps'],'calories':row['summary']['avg_calories'],'calorie_target':row['metrics']['calorie_target'],'stress_level':row['profile']['stress_level']}
        rawres=client.post('/predict',json={'raw':raw})
        report['rows'].append({**row,'http_status':res.status_code,'api':body,'latency_ms':latency,'matches_direct_runtime':body.get('probabilities')==direct,'raw_preprocessing_parity':build_feature_row(impute_raw(raw))==row['features'],'raw_endpoint_matches':rawres.json()==body,'candidate':{'category':str(candidate.predict(frame)[0]),'probabilities':cp}})
    report['invalid_requests']=[{'payload':p,'http_status':(r:=client.post('/predict',json=p)).status_code,'body':r.json()} for p in ({'features':{'bmi':22}},{'features':[]},{'raw':{'age':30,'bmi':22,'sleep_hours':25}})]
    report['repeated_request_identical']=client.post('/predict',json={'features':inputs['rows'][0]['features']}).json()==report['rows'][0]['api']
report['config_hashes']={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'backend/.env',ROOT/'ai-ml/.env',ROOT/'backend/src/config/env.js',ROOT/'ai-ml/app/config.py']}
Path(__file__).with_name('runtime_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'artifacts':report['artifacts'],'live_requests':report['live_requests'],'rows':[{k:r[k] for k in ['id','http_status','matches_direct_runtime','raw_preprocessing_parity','raw_endpoint_matches']}|{'category':r['api'].get('category'),'confidence':r['api'].get('confidence'),'candidate':r['candidate']['category']} for r in report['rows']]},indent=2))
