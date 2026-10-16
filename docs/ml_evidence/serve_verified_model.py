"""Run the unmodified app in one process, recording the loader's actual cached object."""
import hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai-ml'))
from app.config import MODEL_PATH,METADATA_PATH,ML_ENABLED
from app.prediction import predictor
from app.main import app
import uvicorn
expected=ROOT/'ai-ml/models/cep-20k-v1/model.pkl'
assert MODEL_PATH.resolve()==expected.resolve() and ML_ENABLED
before=hashlib.sha256(expected.read_bytes()).hexdigest()
model,meta=predictor.load_model()
after=hashlib.sha256(expected.read_bytes()).hexdigest()
assert model is predictor._state['model'] and model is not None
assert before==after==meta['model_sha256']=='4d131cc7cbd2b8350cc1338adf8cc2f6447a6f3b889feb18b8e4fe7b0ef7729e'
assert type(model).__name__=='HistGradientBoostingClassifier'
evidence={'pid':os.getpid(),'loaded_at_utc':datetime.now(timezone.utc).isoformat(),'resolved_model_path':str(MODEL_PATH.resolve()),'resolved_metadata_path':str(METADATA_PATH.resolve()),'model_sha256':after,'actual_model_type':type(model).__name__,'features':list(model.feature_names_in_),'classes':list(model.classes_),'host':'127.0.0.1','port':8000,'same_process_cached_object':True,'workers':1,'reload':False}
Path(__file__).with_name('activation_runtime.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence),flush=True)
uvicorn.run(app,host='127.0.0.1',port=8000,workers=1)
