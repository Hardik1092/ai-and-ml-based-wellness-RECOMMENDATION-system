"""No-training compatibility gate and two-setting activation/rollback."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai-ml'))
E=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check():
    import joblib,pandas as pd,sklearn,subprocess
    from app.features.engineering import FEATURE_NAMES
    from app.preprocessing.validation import validate_features
    from app.utils.constants import CATEGORY_LABELS
    p=ROOT/'ai-ml/models/cep-20k-v1/model.pkl'
    m=json.loads(p.with_name('feature_metadata.json').read_text())
    model=joblib.load(p)
    assert sha(p)==m['model_sha256']=='4d131cc7cbd2b8350cc1338adf8cc2f6447a6f3b889feb18b8e4fe7b0ef7729e'
    assert type(model).__name__==m['model_type']=='HistGradientBoostingClassifier'
    assert list(model.feature_names_in_)==m['features']==FEATURE_NAMES
    assert set(model.classes_)==set(CATEGORY_LABELS)
    assert sklearn.__version__==m['versions']['scikit-learn']
    profiles=json.loads(subprocess.run(['node',str(E/'runtime_profiles.cjs')],cwd=ROOT,capture_output=True,text=True,check=True).stdout)['rows']
    previous=json.loads((E/'runtime_audit.json').read_text())['rows']
    for row,old in zip(profiles,previous):
        assert row['id']==old['id'] and row['features']==old['features'] and old['raw_preprocessing_parity']
        x=validate_features(pd.DataFrame([row['features']]))
        probs={str(c):round(float(v),4) for c,v in zip(model.classes_,model.predict_proba(x)[0])}
        assert str(model.predict(x)[0])==old['candidate']['category'] and probs==old['candidate']['probabilities']
    result={'passed':True,'model_path':str(p.resolve()),'model_sha256':sha(p),'model_type':type(model).__name__,'features':FEATURE_NAMES,'classes':list(model.classes_),'sklearn':sklearn.__version__,'profiles_checked':len(profiles),'preprocessing':'Unscaled existing engineered features; recorded raw/backend parity reconfirmed','original_model_sha256':sha(ROOT/'ai-ml/models/model.pkl')}
    (E/'activation_preflight.json').write_text(json.dumps(result,indent=2))
    return result
def switch(rollback=False):
    path=ROOT/'ai-ml/.env'; original=path.read_bytes(); updated=original
    pairs={'MODEL_PATH':('models/model.pkl','models/cep-20k-v1/model.pkl'),'METADATA_PATH':('models/feature_metadata.json','models/cep-20k-v1/feature_metadata.json')}
    for key,(old,new) in pairs.items():
        if rollback:old,new=new,old
        pattern=rb'(?m)^'+key.encode()+rb'='+re.escape(old.encode())+rb'(?=\r?$)'
        updated,n=re.subn(pattern,key.encode()+b'='+new.encode(),updated)
        assert n==1,f'{key} is not the expected setting; refusing overwrite'
    path.write_bytes(updated)
    result={'action':'rollback' if rollback else 'activate','before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':sha(path),'settings':{k:v[0 if rollback else 1] for k,v in pairs.items()}}
    (E/('activation_rollback.json' if rollback else 'activation_config.json')).write_text(json.dumps(result,indent=2))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['check','activate','rollback']);args=p.parse_args()
    if args.action=='rollback':result=switch(True)
    else:
        result=check()
        if args.action=='activate':result['config']=switch()
    print(json.dumps(result,indent=2))
