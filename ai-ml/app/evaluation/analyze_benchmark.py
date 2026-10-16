"""Postprocess recorded outputs only; never calls a provider or changes a model."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

from app.evaluation.benchmark import parse_output, safety_flags, rule_category
from app.utils.constants import ML_CATEGORIES


def score(references, predictions):
    report = classification_report(references, predictions, labels=sorted(ML_CATEGORIES), output_dict=True, zero_division=0)
    labels = sorted(ML_CATEGORIES) + (['__no_valid_output__'] if '__no_valid_output__' in predictions else [])
    return {'accuracy': float(accuracy_score(references, predictions)),
            'macro_f1': report['macro avg']['f1-score'], 'weighted_f1': report['weighted avg']['f1-score'],
            'per_class': {name: report[name] for name in sorted(ML_CATEGORIES)},
            'confusion_labels': labels, 'confusion_matrix': confusion_matrix(references,predictions,labels=labels).tolist()}


def latency(values):
    return {'count':len(values), 'median_ms':float(np.median(values)), 'p95_ms':float(np.percentile(values,95)),
            'mean_ms':float(np.mean(values)), 'total_ms':float(sum(values))} if values else None


def analyze(directory):
    directory = Path(directory)
    summary = json.loads((directory/'summary.json').read_text())
    records = [json.loads(line) for line in (directory/'outputs.jsonl').read_text().splitlines()]
    if len(records) != summary['cases'] or len({r['case_id'] for r in records}) != len(records):
        raise ValueError('Incomplete or duplicate case records')
    attempts = [a for r in records for a in r['llm'].get('attempts', [])]
    first = [r['llm'].get('attempts',[r['llm']])[0] for r in records]
    parsed, failures = [], []
    for r in records:
        llm = r['llm']
        if llm.get('output'):
            if parse_output(llm['raw_output']) != llm['output']:
                raise ValueError('Saved parsed output differs from original response')
            parsed.append(r)
        if llm['status'] != 'ok' or len(llm.get('attempts',[])) > 1:
            failures.append({'case_id':r['case_id'], 'final_status':llm['status'], 'attempts':llm.get('attempts',[])})
    refs = [r['reference'] for r in records]
    pred = lambda r: r.get('output',{}).get('category','__no_valid_output__') if r.get('status') in ('ok','unsafe_output') else '__no_valid_output__'
    full_predictions = [pred(r['llm']) for r in records]
    first_predictions = [pred(r) for r in first]
    rules = [rule_category(r['features']) for r in records]
    result = {'cases':len(records), 'run_completed_all_cases':all(r['llm']['status']!='pending' for r in records),
              'model_versions':dict(Counter(r['llm'].get('model_version','not_returned') for r in records)),
              'final_status_counts':dict(Counter(r['llm']['status'] for r in records)),
              'first_attempt_status_counts':dict(Counter(r['status'] for r in first)),
              'total_api_attempts':len(attempts), 'extra_retry_attempts':sum(max(0,len(r['llm'].get('attempts',[]))-1) for r in records),
              'attempt_http_statuses':dict(Counter(str(a.get('http_status','transport')) for a in attempts)),
              'schema_valid':len(parsed), 'schema_valid_rate_all_cases':len(parsed)/len(records),
              'automated_safety_flagged_cases':sum(bool(safety_flags(r['llm']['output'])) for r in parsed),
              'safety_screen_scope':'Limited suggestion keyword screen, not clinical validation; no flag means only no screen match.',
              'reference_rule_disagreements':sum(a!=b for a,b in zip(refs,rules)),
              'human_quality_ratings':'Not performed', 'repeated_generation_consistency':'Not measured',
              'metrics':{}, 'latency':{}}
    for name, predictions in (('ml',[r['ml']['category'] for r in records]), ('rule',rules),('llm',full_predictions),('llm_first_attempt',first_predictions)):
        result['metrics'][name] = score(refs,predictions)
        result['metrics'][name]['agreement_with_rules'] = sum(a==b for a,b in zip(predictions,rules))/len(records)
    if parsed:
        result['metrics']['llm_valid_only'] = score([r['reference'] for r in parsed],[r['llm']['output']['category'] for r in parsed])
    result['latency']['ml'] = latency([r['ml']['latency_ms'] for r in records])
    result['latency']['rule'] = latency([r['rule']['latency_ms'] for r in records])
    result['latency']['llm_successful_case_including_retries'] = latency([r['llm']['latency_ms'] for r in records if r['llm']['status']=='ok'])
    result['latency']['llm_all_attempts'] = latency([a['attempt_latency_ms'] for a in attempts])
    result['latency']['llm_successful_attempts'] = latency([a['attempt_latency_ms'] for a in attempts if a['status']=='ok'])
    usage = Counter()
    usage_count = 0
    for attempt in attempts:
        if attempt.get('usage'):
            usage_count += 1
            for field in ('promptTokenCount','candidatesTokenCount','thoughtsTokenCount','cachedContentTokenCount','totalTokenCount'):
                usage[field] += attempt['usage'].get(field,0)
    # Published standard TEXT rates, accessed 2026-10-16. Not the user's bill/tier.
    rates = {'input_usd_per_million':.30,'cached_input_usd_per_million':.03,'output_including_thoughts_usd_per_million':2.50,
             'model':'gemini-3.5-flash-lite','source':'https://ai.google.dev/gemini-api/docs/pricing','accessed':'2026-10-16'}
    estimate = ((usage['promptTokenCount']-usage['cachedContentTokenCount'])*.30+usage['cachedContentTokenCount']*.03+(usage['candidatesTokenCount']+usage['thoughtsTokenCount'])*2.50)/1e6
    result['cost'] = {'rates':rates,'usage':dict(usage),'attempts_reporting_usage':usage_count,
                      'attempts_without_usage':len(attempts)-usage_count,
                      'estimated_standard_paid_usd_known_usage':estimate,
                      'estimated_standard_paid_usd_per_case':estimate/len(records), 'actual_billed_usd':None,
                      'note':'Estimate from returned usage, not an invoice; account tier/credits unknown. Error requests without usage and separate diagnostics/smoke tests excluded.'}
    ml_pred = [r['ml']['category'] for r in records]
    b = sum(m==y and l!=y for m,l,y in zip(ml_pred,full_predictions,refs))
    c = sum(m!=y and l==y for m,l,y in zip(ml_pred,full_predictions,refs))
    result['paired_errors'] = {'ml_correct_llm_wrong':b,'ml_wrong_llm_correct':c,
        'both_correct':sum(m==l==y for m,l,y in zip(ml_pred,full_predictions,refs)),
        'both_wrong':sum(m!=y and l!=y for m,l,y in zip(ml_pred,full_predictions,refs)),
        'mcnemar_exact_two_sided_p':min(1,2*sum(math.comb(b+c,k) for k in range(min(b,c)+1))/2**(b+c)) if b+c else 1.0}
    seen = Counter()
    review = []
    for r in records:
        if seen[r['reference']] < 2:
            review.append(r)
            seen[r['reference']] += 1
    (directory/'review_sample.json').write_text(json.dumps(review,indent=2))
    (directory/'failures_and_retries.json').write_text(json.dumps(failures,indent=2))
    (directory/'analysis.json').write_text(json.dumps(result,indent=2))
    pd.DataFrame([{'case_id':r['case_id'],'reference':r['reference'],'ml':r['ml']['category'],'rule':rule_category(r['features']),
                   'llm':pred(r['llm']), 'first_attempt_llm':pred(first[i]), 'status':r['llm']['status'],
                   'attempts':len(r['llm'].get('attempts',[])),'llm_latency_ms':r['llm'].get('latency_ms'),
                   'reference_differs_from_rule':r['reference']!=rule_category(r['features'])} for i,r in enumerate(records)]).to_csv(directory/'error_analysis.csv',index=False)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    args=parser.parse_args()
    result=analyze(args.run_dir)
    print(json.dumps({k:result[k] for k in ('cases','final_status_counts','first_attempt_status_counts','total_api_attempts','cost','paired_errors')},indent=2))
